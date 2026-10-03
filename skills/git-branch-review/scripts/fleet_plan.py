#!/usr/bin/env python3
"""Build a cleanup plan (02-plan.json / 02-plan.md) from fleet_scan.py output. Read-only.

usage:
  fleet_plan.py --scan .context/<d>/01-scan.json [--scan more.json] --out-dir .context/<d> \
      [--me <email-or-login-substring> ...] [--exclude <slug-or-alias-substring> ...]

The plan only lists candidates. Deletion needs explicit user approval and runs through
fleet_delete_local.py (local branches) or the commands printed by fleet_verify_remote.py.
Protected and never listed for deletion:
- branches checked out in any worktree, including Claude Desktop session worktrees under .claude/worktrees/
- the worktrees under .claude/worktrees/ themselves (counted only)
- remote branches used as the base of an open PR
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fleet_common import MERGED_CLASSES, SESSION_WORKTREE_MARK, load_json, log, now_iso, write_json  # noqa: E402

LISTS = ("local_delete", "worktree_prune", "remote_delete_mine", "remote_merged_others", "open_prs",
         "seq_conflicts", "unmerged_local_only", "unmerged_remote_no_pr", "closed_pr_leftovers",
         "kept_as_pr_base", "dirty_repos", "scan_errors")


def default_me(scan_docs: list[dict]) -> list[str]:
    marks = {d.get("gh_user") for d in scan_docs if d.get("gh_user")}
    p = subprocess.run(["git", "config", "--global", "user.email"], capture_output=True, text=True)
    if p.returncode == 0 and p.stdout.strip():
        marks.add(p.stdout.strip())
    return sorted(m for m in marks if m)


def build(scan_docs: list[dict], me: list[str], exclude: list[str]) -> dict:
    plan: dict = {"task": "branch-fleet", "phase_or_step": "02-plan", "created_at": now_iso(),
                  "me_marks": me, **{k: [] for k in LISTS}, "session_worktrees": 0}
    repos = []
    for d in scan_docs:
        for r in d["repos"]:
            if any(x in r["alias"] or x == r.get("slug") for x in exclude):
                continue
            if "error" in r:
                plan["scan_errors"].append({"repo": r["alias"], "path": r["path"], "error": r["error"]})
                continue
            repos.append(r)

    seen_slugs: set[str] = set()
    for r in repos:
        if r["dirty"]:
            plan["dirty_repos"].append({"repo": r["alias"], "path": r["path"], "dirty": r["dirty"], "current": r["current"]})
        for w in r["worktrees"]:
            if w.get("session_worktree") or SESSION_WORKTREE_MARK in w["path"]:
                plan["session_worktrees"] += 1
                continue
            if w["prunable"] or not w["exists"]:
                plan["worktree_prune"].append({"repo": r["alias"], "path": r["path"], "worktree": w["path"]})
        for b in r["local"]:
            base = {"repo": r["alias"], "path": r["path"], "branch": b["name"], "date": b["date"],
                    "class": b["class"], "subject": b["subject"], "ahead": b["ahead_of_default"]}
            if b["class"] in MERGED_CLASSES and not b["is_current"] and not b["in_worktree"]:
                plan["local_delete"].append({**base, "tip": b["tip"], "merged_pr_heads": b.get("merged_pr_heads", [])})
            elif b["class"] in ("NO_PR_UNMERGED", "PR_MERGED_BUT_NEWER_COMMITS") and (b["upstream_gone"] or not b["upstream"]):
                plan["unmerged_local_only"].append({**base, "in_worktree": bool(b["in_worktree"])})
            elif b["class"] == "PR_CLOSED_UNMERGED":
                plan["closed_pr_leftovers"].append({**base, "where": "local", "prs": b["prs"]})

        # remote side is counted once per GitHub repo (the first / primary checkout, also across scan files)
        if r.get("duplicate_of") or not r.get("slug") or r["slug"] in seen_slugs:
            continue
        seen_slugs.add(r["slug"])
        for p in r["open_prs"]:
            plan["open_prs"].append({"repo": r["slug"], **{k: p[k] for k in (
                "number", "title", "head", "base", "author", "draft", "mergeable", "updated", "age_days", "url")}})
            for c in p.get("seq_conflicts", []):
                plan["seq_conflicts"].append({"repo": r["slug"], "pr": p["number"], **c})
        for num, files in (r.get("seq_duplicates_in_default") or {}).items():
            plan["seq_conflicts"].append({"repo": r["slug"], "pr": None, "number": num, "pr_files": [], "default_files": files})
        pr_bases = {p["base"] for p in r["open_prs"]}
        for b in r["remote"]:
            if b["name"] in pr_bases:
                plan["kept_as_pr_base"].append({"repo": r["slug"], "branch": b["name"]})
                continue
            mine = any(m and m in b["author"] for m in me)
            base = {"repo": r["slug"], "path": r["path"], "branch": b["name"], "date": b["date"], "author": b["author"],
                    "class": b["class"], "subject": b["subject"], "ahead": b["ahead_of_default"], "tip": b["tip"],
                    "merged_pr_heads": b.get("merged_pr_heads", [])}
            if b["class"] in MERGED_CLASSES:
                plan["remote_delete_mine" if mine else "remote_merged_others"].append(base)
            elif b["class"] in ("NO_PR_UNMERGED", "PR_MERGED_BUT_NEWER_COMMITS"):
                plan["unmerged_remote_no_pr"].append({**base, "mine": mine})
            elif b["class"] == "PR_CLOSED_UNMERGED":
                plan["closed_pr_leftovers"].append({**base, "where": "remote", "prs": b["prs"], "mine": mine})
    return plan


def tbl(rows: list[dict], cols: list[str]) -> str:
    if not rows:
        return "（なし）\n"
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for x in rows:
        lines.append("| " + " | ".join(str(x.get(c, "")).replace("|", "/").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines) + "\n"


def render_md(plan: dict, sources: list[str]) -> str:
    srt = lambda rows, *keys: sorted(rows, key=lambda x: tuple(str(x.get(k, "")) for k in keys))  # noqa: E731
    remote_merged = plan["remote_delete_mine"] + plan["remote_merged_others"]
    parts = [
        f"---\ntask: branch-fleet\nphase_or_step: 02-plan\ncreated_at: {plan['created_at']}\nsource: {', '.join(sources)}\n---",
        "# ブランチ / PR / worktree 整理計画\n",
        "この計画は候補の一覧で、削除・クローズ・マージはユーザーの明示承認後に区分ごとに実行する。\n",
        f"## A. ローカルのマージ済みブランチ（{len(plan['local_delete'])} 本）\n"
        "origin の default に取り込み済み（祖先 / tree 不変 / マージ済み PR の head 一致）。現在ブランチと worktree で checkout 中のものは除外。\n",
        tbl(srt(plan["local_delete"], "repo", "date"), ["repo", "branch", "date", "class", "subject"]),
        f"## B. リモートのマージ済みブランチ（自分 {len(plan['remote_delete_mine'])} 本 / 他者 {len(plan['remote_merged_others'])} 本）\n"
        "削除は承認後に fleet_verify_remote.py で再検証し、出力された repo ごとのコマンドを 1 つずつ単独実行する。他者のブランチは原則提案のみ。\n",
        tbl(srt(remote_merged, "repo", "date"), ["repo", "branch", "date", "author", "class"]),
        f"## C. Open PR（{len(plan['open_prs'])} 件）\n",
        tbl(srt(plan["open_prs"], "repo", "number"),
            ["repo", "number", "title", "author", "draft", "mergeable", "base", "updated", "age_days"]),
        f"## D. 連番ファイルの衝突（{len(plan['seq_conflicts'])} 件）\n"
        "PR が追加する連番（既定 docs/adr/NNNN-）が default 側と重なるもの、default 内で既に重複しているもの。マージ前に振り直す。\n",
        tbl(plan["seq_conflicts"], ["repo", "pr", "number", "pr_files", "default_files"]),
        f"## E. PR が無い未マージのリモートブランチ（{len(plan['unmerged_remote_no_pr'])} 本）\n",
        tbl(srt(plan["unmerged_remote_no_pr"], "repo", "date"), ["repo", "branch", "date", "mine", "ahead", "subject"]),
        f"## F. PR をクローズ済みで未マージのブランチ（{len(plan['closed_pr_leftovers'])} 件）\n",
        tbl(plan["closed_pr_leftovers"], ["repo", "where", "branch", "date", "prs", "ahead"]),
        f"## G. 未 push / upstream 無しの未マージローカルブランチ（{len(plan['unmerged_local_only'])} 本）\n",
        tbl(srt(plan["unmerged_local_only"], "repo", "date"), ["repo", "branch", "date", "in_worktree", "ahead", "subject"]),
        f"## H. 未コミット変更のある作業ツリー（{len(plan['dirty_repos'])} 件）\n",
        tbl(plan["dirty_repos"], ["repo", "current", "dirty", "path"]),
        f"## I. ディレクトリが消えた worktree の登録（{len(plan['worktree_prune'])} 件）\n"
        "`git worktree prune` の候補。`.claude/worktrees/` 配下は除外済み。\n",
        tbl(plan["worktree_prune"], ["repo", "worktree"]),
        f"## J. 保護対象\n- Desktop セッションの worktree（`.claude/worktrees/`）: {plan['session_worktrees']} 件。"
        "ここで checkout 中のブランチと worktree は整理対象にしない（片付けはセッションのアーカイブで行う）\n"
        f"- open PR の base として残すリモートブランチ: {len(plan['kept_as_pr_base'])} 本\n",
        f"## K. スキャン失敗（{len(plan['scan_errors'])} 件）\n",
        tbl(plan["scan_errors"], ["repo", "path", "error"]),
    ]
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scan", action="append", required=True, help="01-scan.json from fleet_scan.py (repeatable)")
    ap.add_argument("--out-dir", required=True, help="directory for 02-plan.json / 02-plan.md")
    ap.add_argument("--me", action="append", default=None,
                    help="substring of your commit author email (repeatable). Default: gh login + global user.email")
    ap.add_argument("--exclude", action="append", default=[], help="slug or alias substring to leave out (repeatable)")
    args = ap.parse_args()

    docs = [load_json(p) for p in args.scan]
    me = args.me if args.me is not None else default_me(docs)
    plan = build(docs, me, args.exclude)
    out_dir = Path(args.out_dir)
    write_json(out_dir / "02-plan.json", plan)
    (out_dir / "02-plan.md").write_text(render_md(plan, [Path(p).name for p in args.scan]), encoding="utf-8")
    for k in LISTS:
        log(f"{k}: {len(plan[k])}")
    log(f"session_worktrees (protected): {plan['session_worktrees']}")
    log(f"wrote {out_dir / '02-plan.json'} and 02-plan.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
