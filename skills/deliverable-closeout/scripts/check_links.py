#!/usr/bin/env python3
"""Check lines added to a repo index: relative links exist, Drive URLs counted, forbidden words absent.

usage: check_links.py --worktree <repo-or-worktree> [--base HEAD] [--forbidden-file .context/<d>/forbidden.txt]

The forbidden file holds one word per line (for example client names that a repo must not contain).
Keep it under .context/ so the words never enter git or the command line. Exit code 1 when problems > 0.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import urllib.parse

SECRET_RE = re.compile(r"(token|password|パスワード|口座|api[_-]?key|secret)", re.I)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--worktree", required=True)
    ap.add_argument("--base", default="HEAD", help="diff base; use origin/<default> to check committed changes")
    ap.add_argument("--forbidden-file")
    args = ap.parse_args()

    forbidden = []
    if args.forbidden_file:
        with open(args.forbidden_file, encoding="utf-8") as f:
            forbidden = [w.strip() for w in f if w.strip()]
    diff = subprocess.run(["git", "-C", args.worktree, "diff", "-U0", args.base], capture_output=True, text=True).stdout
    cur, added = None, []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            cur = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            added.append((cur, line[1:]))
    print(f"added lines: {len(added)}")
    drive, bad = set(), 0
    for f, line in added:
        for m in re.finditer(r"\]\(([^)]+)\)", line):
            target = m.group(1)
            if target.startswith("http"):
                if "google.com" in target:
                    drive.add(target)
                continue
            path = urllib.parse.unquote(target.split("#")[0])
            full = os.path.normpath(os.path.join(args.worktree, os.path.dirname(f), path)) if path else os.path.join(args.worktree, f)
            exists = os.path.exists(full)
            bad += 0 if exists else 1
            print(("OK  " if exists else "NG  ") + f"{f}: {target}")
        for w in forbidden:
            if w.lower() in line.lower():
                print(f"FORBIDDEN word #{forbidden.index(w) + 1} in {f}")
                bad += 1
        if SECRET_RE.search(line):
            print(f"SECRET? {f}: {line[:80]}")
    print(f"unique drive urls: {len(drive)}")
    for u in sorted(drive):
        print("  " + u)
    print(f"problems: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
