#!/usr/bin/env python3
"""Re-verify remote merged branches from 02-plan.json and print per-repo delete commands. Never deletes.

usage:
  fleet_verify_remote.py --plan .context/<d>/02-plan.json --out .context/<d>/05-remote-verified.json \
      [--list remote_delete_mine] [--repo <slug-substring> ...] [--no-fetch]

Checks per branch: still on origin with the same tip, not the head/base of an open PR, not checked out
in a Desktop session worktree (.claude/worktrees/), and contained in origin/<default> (ancestor or the
head of a merged PR recorded at scan time). Branches checked out in other local worktrees are kept
in the list but reported, so the user can decide.
Lines prefixed with ``CMD`` are the commands to show the user. Run each one on its own (never chain
them with && or ;) and only after the user approved remote deletion for that repo.
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fleet_common import (SESSION_WORKTREE_MARK, default_branch, gh, git, is_ancestor, load_json, log,  # noqa: E402
                          now_iso, worktrees, write_json)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--list", default="remote_delete_mine", choices=["remote_delete_mine", "remote_merged_others"])
    ap.add_argument("--repo", action="append", default=[], help="limit to slugs containing this (repeatable)")
    ap.add_argument("--no-fetch", action="store_true", help="skip git fetch origin (no --prune is ever used here)")
    args = ap.parse_args()

    items = load_json(args.plan)[args.list]
    if args.repo:
        items = [it for it in items if any(x in it["repo"] for x in args.repo)]
    by_repo: dict[tuple[str, str], list[dict]] = {}
    for it in items:
        by_repo.setdefault((it["repo"], it["path"]), []).append(it)
    log(f"start: {len(items)} branches in {len(by_repo)} repos (list={args.list})")

    doc = {"task": "branch-fleet", "phase_or_step": "05-remote-verified", "created_at": now_iso(),
           "list": args.list, "repos": []}
    for n, ((slug, path), its) in enumerate(by_repo.items(), 1):
        log(f"({n}/{len(by_repo)}) {slug}")
        if not args.no_fetch:
            git(path, "fetch", "--quiet", "origin", timeout=180)
        dref = f"origin/{default_branch(path)}"
        p = gh("pr", "list", "-R", slug, "--state", "open", "--limit", "300", "--json", "headRefName,baseRefName")
        if p.returncode != 0:
            log(f"    gh failed, repo skipped (no commands emitted): {p.stderr.strip()[:200]}")
            doc["repos"].append({"repo": slug, "path": path, "delete": [], "skipped": [], "error": "gh failed"})
            continue
        open_prs = json.loads(p.stdout)
        busy = {x["headRefName"] for x in open_prs} | {x["baseRefName"] for x in open_prs}
        local_wt = {str(w["branch"]).removeprefix("refs/heads/"): str(w.get("worktree"))
                    for w in worktrees(path) if isinstance(w.get("branch"), str)}
        ok_list, skipped = [], []
        for it in its:
            br = it["branch"]
            tip = git(path, "rev-parse", "-q", "--verify", f"refs/remotes/origin/{br}").stdout.strip()
            if not tip:
                reason = "already gone on origin"
            elif not tip.startswith(it["tip"]) and not it["tip"].startswith(tip):
                reason = f"tip moved {it['tip'][:8]} -> {tip[:8]}"
            elif br in busy:
                reason = "head/base of an open PR"
            elif SESSION_WORKTREE_MARK in local_wt.get(br, ""):
                reason = "checked out in a Desktop session worktree (.claude/worktrees/)"
            elif not (is_ancestor(path, tip, dref) or tip in it.get("merged_pr_heads", [])):
                reason = f"not contained in {dref} and not a merged PR head"
            else:
                reason = None
            if reason:
                skipped.append({"branch": br, "reason": reason})
            else:
                ok_list.append({"branch": br, "tip": tip, "local_worktree": local_wt.get(br)})
            note = f" (still checked out locally at {local_wt[br]})" if not reason and br in local_wt else ""
            log(f"    {br} -> {'OK' if not reason else 'skip: ' + reason}{note}")
        doc["repos"].append({"repo": slug, "path": path, "delete": ok_list, "skipped": skipped})

    write_json(args.out, doc)
    total_ok = sum(len(r["delete"]) for r in doc["repos"])
    log(f"done: ok={total_ok} skipped={sum(len(r['skipped']) for r in doc['repos'])} -> {args.out}")
    for r in doc["repos"]:
        if r["delete"]:
            branches = " ".join(shlex.quote(x["branch"]) for x in r["delete"])
            print(f"CMD\tgit -C {shlex.quote(r['path'])} push origin --delete {branches}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
