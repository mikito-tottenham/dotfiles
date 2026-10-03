#!/usr/bin/env python3
"""Fetch a Drive file listing with md5 for duplicate detection. Read-only.

usage:
  drive_index.py --profile <gws-profile> --out .context/<d>/drive-index-<profile>.json
                 [--drive-id <shared-drive-id>] [--folder-id <id>] [--all-mimes]

Scope:
- default: files in My Drive owned by the profile's account ('me' in owners)
- --drive-id: every file in that shared drive (find the id with
  ``gws-account <profile> drive drives list --params '{"pageSize":50}'``)
- --folder-id: only direct children of that folder
By default only PDF / pptx / docx / xlsx are listed; --all-mimes lists every non-folder file.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gws_common import FOLDER_MIME, OFFICE_MIMES, gws, log, now_iso, write_json  # noqa: E402

FIELDS = "nextPageToken,files(id,name,mimeType,md5Checksum,size,parents,modifiedTime,webViewLink,driveId)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--drive-id")
    ap.add_argument("--folder-id")
    ap.add_argument("--all-mimes", action="store_true")
    ap.add_argument("--page-size", type=int, default=1000)
    args = ap.parse_args()

    conds = ["trashed=false", f"mimeType!='{FOLDER_MIME}'"]
    if not args.all_mimes:
        conds.append("(" + " or ".join(f"mimeType='{m}'" for m in OFFICE_MIMES.values()) + ")")
    if args.folder_id:
        conds.append(f"'{args.folder_id}' in parents")
    elif not args.drive_id:
        conds.append("'me' in owners")
    base = {"q": " and ".join(conds), "includeItemsFromAllDrives": True, "supportsAllDrives": True,
            "pageSize": args.page_size, "fields": FIELDS}
    if args.drive_id:
        base.update(corpora="drive", driveId=args.drive_id)
    else:
        base.update(corpora="user")

    scope = f"drive={args.drive_id}" if args.drive_id else ("folder" if args.folder_id else "mydrive")
    log(f"start profile={args.profile} scope={scope}")
    files, token, page = [], None, 0
    while True:
        params = dict(base, **({"pageToken": token} if token else {}))
        d = gws(args.profile, ["drive", "files", "list", "--params", json.dumps(params)])
        files += d.get("files", [])
        page += 1
        log(f"progress page={page} total={len(files)}")
        token = d.get("nextPageToken")
        if not token:
            break

    write_json(args.out, {"task": "deliverable-closeout", "phase_or_step": "drive-index", "created_at": now_iso(),
                          "profile": args.profile, "scope": scope, "drive_id": args.drive_id,
                          "folder_id": args.folder_id, "files": files})
    log(f"done files={len(files)} with_md5={sum(1 for f in files if f.get('md5Checksum'))} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
