#!/usr/bin/env python3
"""List deliverable files (PDF / Office by default) under a directory with git status and md5. Read-only.

usage:
  deliverable_inventory.py --root <repo-or-dir> --out .context/<d>/01-inventory.json [--ext pdf,pptx,docx,xlsx]
                           [--include-context] [--exclude-dir name ...]

Each entry: path (relative to --root), real path, repo top-level, git status
(tracked / ignored / untracked / no-repo), size, mtime, md5. ``.context/`` is skipped by default
because it holds intermediate versions; pass --include-context to list them for review.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gws_common import log, md5, now_iso, write_json  # noqa: E402

DEFAULT_EXCLUDES = {".git", "node_modules", ".venv", "venv", "go", "__pycache__", ".claude"}


def repo_top(d: str, cache: dict[str, str | None]) -> str | None:
    if d not in cache:
        r = subprocess.run(["git", "-C", d, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        cache[d] = r.stdout.strip() if r.returncode == 0 else None
    return cache[d]


def git_status(top: str, rel: str) -> str:
    if subprocess.run(["git", "-C", top, "ls-files", "--error-unmatch", "--", rel], capture_output=True).returncode == 0:
        return "tracked"
    if subprocess.run(["git", "-C", top, "check-ignore", "-q", "--", rel]).returncode == 0:
        return "ignored"
    return "untracked"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ext", default="pdf,pptx,docx,xlsx")
    ap.add_argument("--include-context", action="store_true", help="also list files under .context/")
    ap.add_argument("--exclude-dir", action="append", default=[], help="directory name to skip (repeatable)")
    args = ap.parse_args()

    root = Path(os.path.expanduser(args.root)).resolve()
    exts = {"." + e.strip().lower().lstrip(".") for e in args.ext.split(",") if e.strip()}
    excludes = DEFAULT_EXCLUDES | set(args.exclude_dir) | (set() if args.include_context else {".context"})
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in excludes)
        files += [os.path.join(dirpath, f) for f in sorted(filenames) if os.path.splitext(f)[1].lower() in exts]
    log(f"start: {len(files)} files under {root} ext={sorted(exts)}")

    cache: dict[str, str | None] = {}
    items, t0 = [], time.time()
    for i, p in enumerate(files, 1):
        real = os.path.realpath(p)
        top = repo_top(os.path.dirname(real), cache)
        st = os.stat(real)
        items.append({"path": os.path.relpath(p, root), "real": real, "repo": top,
                      "status": git_status(top, os.path.relpath(real, top)) if top else "no-repo",
                      "size": st.st_size, "mtime": time.strftime("%Y-%m-%d", time.localtime(st.st_mtime)),
                      "md5": md5(real)})
        if i % 50 == 0 or i == len(files):
            log(f"progress {i}/{len(files)} elapsed={time.time() - t0:.1f}s")

    write_json(args.out, {"task": "deliverable-closeout", "phase_or_step": "01-inventory", "created_at": now_iso(),
                          "root": str(root), "items": items})
    counts: dict[str, int] = {}
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    log(f"done: {counts} unique_md5={len({it['md5'] for it in items})} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
