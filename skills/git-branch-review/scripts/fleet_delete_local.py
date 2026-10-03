#!/usr/bin/env python3
"""Delete the local merged branches listed in 02-plan.json ``local_delete`` (dry-run by default).

usage:
  fleet_delete_local.py --plan .context/<d>/02-plan.json --out .context/<d>/03-local-delete.json            # dry-run
  fleet_delete_local.py --plan ... --out ... --execute [--repo <alias-substring> ...]   # only after user approval

Every branch is re-verified immediately before deletion and skipped when any check fails:
- the branch still exists and its tip is unchanged since the scan
- it is not checked out in any worktree (main checkout, ad hoc worktrees, .claude/worktrees/ sessions)
- it is contained in origin/<default>: ancestor, merge leaves the tree unchanged, or the tip equals
  the head of a merged PR recorded at scan time (squash merge)
The output JSON keeps the full SHA so a deleted branch can be restored with
``git -C <path> branch <branch> <full_tip>``. Remote branches are never touched.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fleet_common import (checked_out_branches, content_in_default, default_branch, git, is_ancestor,  # noqa: E402
                          load_json, log, now_iso, write_json)


def verify(it: dict) -> tuple[str | None, str]:
    repo, br = it["path"], it["branch"]
    tip = git(repo, "rev-parse", "-q", "--verify", f"refs/heads/{br}").stdout.strip()
    if not tip:
        return "skip: already gone", tip
    if not tip.startswith(it["tip"]) and not it["tip"].startswith(tip):
        return f"skip: tip moved {it['tip'][:8]} -> {tip[:8]}", tip
    if br in checked_out_branches(repo):
        return "skip: checked out in a worktree", tip
    dref = f"origin/{default_branch(repo)}"
    if is_ancestor(repo, br, dref) or content_in_default(repo, br, dref) or tip in it.get("merged_pr_heads", []):
        return None, tip
    return f"skip: no longer contained in {dref} and not a merged PR head", tip


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True, help="result JSON (restore SHAs are recorded here)")
    ap.add_argument("--execute", action="store_true", help="actually run git branch -D; omit for a dry-run")
    ap.add_argument("--repo", action="append", default=[], help="limit to plan entries whose repo contains this (repeatable)")
    args = ap.parse_args()

    items = load_json(args.plan)["local_delete"]
    if args.repo:
        items = [it for it in items if any(x in it["repo"] for x in args.repo)]
    mode = "EXECUTE" if args.execute else "DRY-RUN"
    log(f"start {mode}: {len(items)} branches")
    results = []
    for i, it in enumerate(items, 1):
        reason, tip = verify(it)
        if reason:
            status = reason
        elif not args.execute:
            status = "would delete"
        else:
            p = git(it["path"], "branch", "-D", it["branch"])
            status = "deleted" if p.returncode == 0 else f"error: {p.stderr.strip()[:200]}"
        log(f"({i}/{len(items)}) {it['repo']} {it['branch']} [{tip[:8]}] -> {status}")
        results.append({**it, "full_tip": tip, "status": status})

    write_json(args.out, {"task": "branch-fleet", "phase_or_step": "03-local-delete", "created_at": now_iso(),
                          "mode": mode, "note": "restore: git -C <path> branch <branch> <full_tip>", "results": results})
    counts: dict[str, int] = {}
    for r in results:
        key = r["status"].split(":")[0]
        counts[key] = counts.get(key, 0) + 1
    log(f"done {mode}: {counts} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
