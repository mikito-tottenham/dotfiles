#!/usr/bin/env python3
"""Upload approved deliverables to Google Drive through gws-account, idempotently.

usage:
  drive_upload.py --plan .context/<d>/10-upload-plan.json --results .context/<d>/11-upload-dryrun.json --dry-run
  drive_upload.py --plan ... --results .context/<d>/12-upload-results.json [--index drive-index-*.json ...]
  drive_upload.py --results .context/<d>/12-upload-results.json --links      # print the copy-paste link list

Plan format (see references/upload-plan.md):
  {"items": [{"id": str, "src": abs path, "profile": str, "drive_id": str|null,
              "folder_path": [names...], "name": str}]}

Per item:
- same name in the destination folder with the same md5 -> exists-same (reuse that link)
- same md5 anywhere in a --index listing of the same profile -> exists-elsewhere (reuse, no upload)
- same name with a different md5 -> conflict (never overwritten; ask the user)
- otherwise create missing folders and upload; the returned md5 must match -> uploaded
Results are saved after every item, and items already uploaded / reused are skipped on re-run.
Dry-run performs read-only Drive lookups and reports what would be created. Sharing settings are
never changed (files inherit the folder's permissions).
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gws_common import FOLDER_MIME, OFFICE_MIMES, gws, load_json, log, md5, now_iso, q_escape, write_json  # noqa: E402

DONE = {"uploaded", "exists-same", "exists-elsewhere"}
folder_cache: dict[tuple, str] = {}


def list_children(profile: str, drive_id: str | None, parent: str, name: str, mime: str | None = None) -> list[dict]:
    q = f"'{parent}' in parents and name='{q_escape(name)}' and trashed=false"
    if mime:
        q += f" and mimeType='{mime}'"
    params = {"q": q, "supportsAllDrives": True, "includeItemsFromAllDrives": True,
              "fields": "files(id,name,md5Checksum,webViewLink)", "pageSize": 10}
    if drive_id:
        params.update(corpora="drive", driveId=drive_id)
    return gws(profile, ["drive", "files", "list", "--params", json.dumps(params)]).get("files", [])


def ensure_folder(profile: str, drive_id: str | None, path: list[str], dry: bool) -> str:
    parent = drive_id or "root"
    for i, name in enumerate(path):
        key = (profile, drive_id, tuple(path[: i + 1]))
        if key in folder_cache:
            parent = folder_cache[key]
            continue
        found = [] if parent.startswith("DRY:") else list_children(profile, drive_id, parent, name, FOLDER_MIME)
        if found:
            parent = found[0]["id"]
        elif dry:
            parent = "DRY:" + "/".join(path[: i + 1])
            log(f"dry-run: would create folder {'/'.join(path[: i + 1])} profile={profile}")
        else:
            body = {"name": name, "parents": [parent], "mimeType": FOLDER_MIME}
            parent = gws(profile, ["drive", "files", "create", "--params", json.dumps({"supportsAllDrives": True}),
                                   "--json", json.dumps(body, ensure_ascii=False)])["id"]
            log(f"created folder {'/'.join(path[: i + 1])} profile={profile}")
        folder_cache[key] = parent
    return parent


def load_index(paths: list[str]) -> dict[tuple[str, str], dict]:
    idx: dict[tuple[str, str], dict] = {}
    for p in paths:
        d = load_json(p)
        for f in d.get("files", []):
            if f.get("md5Checksum"):
                idx.setdefault((d["profile"], f["md5Checksum"]), f)
    return idx


def print_links(results: dict) -> None:
    rows = [r for r in results.values() if r.get("webViewLink")]
    print("\n".join(f"- {r['name']}: {r['webViewLink']}" for r in rows))
    print("\n" + "\n".join(r["webViewLink"] for r in rows))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan")
    ap.add_argument("--results", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--index", action="append", default=[], help="drive_index.py output for md5 reuse (repeatable)")
    ap.add_argument("--links", action="store_true", help="only print links from --results and exit")
    args = ap.parse_args()

    doc = load_json(args.results) if os.path.exists(args.results) else {}
    results: dict = doc.get("results", {})
    if args.links:
        print_links(results)
        return 0
    if not args.plan:
        ap.error("--plan is required unless --links is given")

    items = load_json(args.plan)["items"]
    index = load_index(args.index)
    log(f"start items={len(items)} recorded={len(results)} index_md5={len(index)} dry_run={args.dry_run}")
    counts: dict[str, int] = {}
    for n, it in enumerate(items, 1):
        prev = results.get(it["id"])
        if prev and prev.get("status") in DONE:
            counts["skip-recorded"] = counts.get("skip-recorded", 0) + 1
            continue
        folder_path = [part for seg in it["folder_path"] for part in seg.split("/") if part]  # "a/b" -> a, b
        dest = "/".join(folder_path + [it["name"]])
        rec: dict = {"name": it["name"], "dest": dest, "profile": it["profile"], "src": it["src"]}
        try:
            local_md5 = md5(it["src"])
            rec["local_md5"] = local_md5
            folder = ensure_folder(it["profile"], it.get("drive_id"), folder_path, args.dry_run)
            existing = [] if folder.startswith("DRY:") else list_children(it["profile"], it.get("drive_id"), folder, it["name"])
            same = [f for f in existing if f.get("md5Checksum") == local_md5]
            elsewhere = index.get((it["profile"], local_md5))
            if same:
                rec.update(status="exists-same", fileId=same[0]["id"], webViewLink=same[0].get("webViewLink"))
            elif existing:
                rec.update(status="conflict", existing=existing)
            elif elsewhere:
                rec.update(status="exists-elsewhere", fileId=elsewhere["id"], webViewLink=elsewhere.get("webViewLink"),
                           existing_name=elsewhere.get("name"))
            elif args.dry_run:
                rec.update(status="dry-run")
            else:
                ext = os.path.splitext(it["src"])[1].lower()
                mime = OFFICE_MIMES.get(ext) or mimetypes.guess_type(it["src"])[0] or "application/octet-stream"
                body = {"name": it["name"], "parents": [folder]}
                up = gws(it["profile"], ["drive", "files", "create",
                                         "--params", json.dumps({"supportsAllDrives": True, "fields": "id,md5Checksum,webViewLink"}),
                                         "--json", json.dumps(body, ensure_ascii=False),
                                         "--upload", os.path.basename(it["src"]), "--upload-content-type", mime],
                         cwd=os.path.dirname(it["src"]))
                rec.update(status="uploaded" if up.get("md5Checksum") == local_md5 else "md5-mismatch",
                           fileId=up["id"], webViewLink=up.get("webViewLink"))
            rec["folderId"] = folder
        except Exception as e:  # one failure must not stop the batch; it is recorded and reported
            rec.update(status="error", error=str(e)[:300])
        results[it["id"]] = rec
        counts[rec["status"]] = counts.get(rec["status"], 0) + 1
        log(f"{n}/{len(items)} id={it['id']} profile={it['profile']} dest={dest} -> {rec['status']}")
        write_json(args.results, {"task": "deliverable-closeout",
                                  "phase_or_step": "11-upload-dryrun" if args.dry_run else "12-upload-results",
                                  "created_at": now_iso(), "dry_run": args.dry_run, "results": results})
    log(f"done counts={counts} -> {args.results}")
    if any(r.get("status") in ("conflict", "md5-mismatch", "error") for r in results.values()):
        log("ATTENTION: conflict / md5-mismatch / error items need a user decision; nothing was overwritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
