#!/usr/bin/env python3
"""Summarize local git branch state and optionally fast-forward a clean branch."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CmdResult:
    code: int
    stdout: str
    stderr: str


def run(cmd: list[str], cwd: Path, check: bool = False) -> CmdResult:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    result = CmdResult(proc.returncode, proc.stdout.strip(), proc.stderr.strip())
    if check and result.code != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {result.stderr or result.stdout}")
    return result


def git(cwd: Path, *args: str, check: bool = False) -> CmdResult:
    return run(["git", *args], cwd, check=check)


def quote_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip() or "-"


def current_branch(cwd: Path) -> str:
    result = git(cwd, "branch", "--show-current", check=True)
    return result.stdout or "(detached)"


def upstream_for(cwd: Path, branch: str) -> str:
    if branch == "(detached)":
        return ""
    result = git(cwd, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    return result.stdout if result.code == 0 else ""


def ahead_behind(cwd: Path, left: str, right: str) -> tuple[int, int] | None:
    result = git(cwd, "rev-list", "--left-right", "--count", f"{left}...{right}")
    if result.code != 0:
        return None
    left_count, right_count = result.stdout.split()
    return int(left_count), int(right_count)


def default_ref(cwd: Path) -> str:
    origin_head = git(cwd, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    if origin_head.code == 0 and origin_head.stdout:
        return origin_head.stdout
    for candidate in ("origin/main", "origin/master"):
        if git(cwd, "show-ref", "--verify", "--quiet", f"refs/remotes/{candidate}").code == 0:
            return candidate
    return ""


def local_branches(cwd: Path) -> list[dict[str, str]]:
    fmt = "%(refname:short)%00%(upstream:short)%00%(committerdate:iso8601)%00%(objectname:short)%00%(subject)"
    result = git(cwd, "for-each-ref", "refs/heads", f"--format={fmt}", "--sort=-committerdate", check=True)
    rows: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        name, upstream, updated, sha, subject = (line.split("\0") + [""] * 5)[:5]
        rows.append({"name": name, "upstream": upstream, "updated": updated, "sha": sha, "subject": subject})
    return rows


def merged_status(cwd: Path, branch: str, base_ref: str) -> str:
    if not base_ref:
        return "unknown"
    result = git(cwd, "merge-base", "--is-ancestor", branch, base_ref)
    if result.code == 0:
        return f"merged into {base_ref}"
    if result.code == 1:
        return f"not merged into {base_ref}"
    return "unknown"


def pr_for_branch(cwd: Path, branch: str) -> str:
    if shutil.which("gh") is None:
        return "gh unavailable"
    result = run(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "all",
            "--head",
            branch,
            "--json",
            "number,state,mergedAt,isDraft,url,title,baseRefName,updatedAt",
            "--limit",
            "5",
        ],
        cwd,
    )
    if result.code != 0:
        return "gh error"
    try:
        prs = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return "gh parse error"
    if not prs:
        return "no PR found"
    parts: list[str] = []
    for pr in prs:
        state = pr.get("state", "")
        if pr.get("mergedAt"):
            state = "MERGED"
        draft = " draft" if pr.get("isDraft") else ""
        parts.append(f"#{pr.get('number')} {state}{draft} {pr.get('url')}")
    return "<br>".join(parts)


def maybe_fast_forward(cwd: Path, branch: str, upstream: str) -> str:
    if not upstream:
        return "skipped: no upstream"
    if git(cwd, "status", "--porcelain").stdout:
        return "skipped: worktree dirty"
    counts = ahead_behind(cwd, "HEAD", upstream)
    if counts is None:
        return "skipped: cannot compare upstream"
    ahead, behind = counts
    if ahead > 0:
        return f"skipped: local branch is ahead by {ahead}"
    if behind == 0:
        return "skipped: already up to date"
    result = git(cwd, "pull", "--ff-only")
    if result.code == 0:
        return f"fast-forwarded {branch} from {upstream}"
    return f"failed: {result.stderr or result.stdout}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", default=".", help="Repository path, default: current directory")
    parser.add_argument("--fast-forward-clean", action="store_true", help="Fast-forward the current branch only when clean and safe")
    parser.add_argument("--no-fetch", action="store_true", help="Skip git fetch --prune")
    parser.add_argument("--no-pr", action="store_true", help="Skip GitHub PR lookup through gh")
    args = parser.parse_args()

    cwd = Path(args.repo).expanduser().resolve()
    if git(cwd, "rev-parse", "--is-inside-work-tree").code != 0:
        print(f"Not a git repository: {cwd}", file=sys.stderr)
        return 2

    print(f"[git-branch-review] repo={cwd}")
    if not args.no_fetch:
        print("[git-branch-review] fetching remotes with prune")
        fetch = git(cwd, "fetch", "--all", "--prune")
        if fetch.code != 0:
            print(f"[git-branch-review] fetch failed: {fetch.stderr or fetch.stdout}", file=sys.stderr)

    branch = current_branch(cwd)
    upstream = upstream_for(cwd, branch)
    dirty = bool(git(cwd, "status", "--porcelain").stdout)
    default_remote = default_ref(cwd)
    ff_result = "not requested"
    if args.fast_forward_clean:
        ff_result = maybe_fast_forward(cwd, branch, upstream)

    counts = ahead_behind(cwd, "HEAD", upstream) if upstream else None
    ahead = counts[0] if counts else "-"
    behind = counts[1] if counts else "-"

    print("\n# Git Branch Review\n")
    print("## Current Branch\n")
    print("| field | value |")
    print("| --- | --- |")
    print(f"| repo | {quote_cell(str(cwd))} |")
    print(f"| branch | {quote_cell(branch)} |")
    print(f"| upstream | {quote_cell(upstream)} |")
    print(f"| worktree | {'dirty' if dirty else 'clean'} |")
    print(f"| ahead | {ahead} |")
    print(f"| behind | {behind} |")
    print(f"| default remote ref | {quote_cell(default_remote)} |")
    print(f"| fast-forward | {quote_cell(ff_result)} |")

    print("\n## Local Branches\n")
    print("| branch | upstream | ahead | behind | merged | PR | updated | tip | subject |")
    print("| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |")
    for row in local_branches(cwd):
        upstream_name = row["upstream"]
        counts = ahead_behind(cwd, row["name"], upstream_name) if upstream_name else None
        row_ahead = str(counts[0]) if counts else "-"
        row_behind = str(counts[1]) if counts else "-"
        merged = merged_status(cwd, row["name"], default_remote)
        pr = "skipped" if args.no_pr else pr_for_branch(cwd, row["name"])
        print(
            "| "
            + " | ".join(
                quote_cell(value)
                for value in [
                    row["name"],
                    upstream_name,
                    row_ahead,
                    row_behind,
                    merged,
                    pr,
                    row["updated"],
                    row["sha"],
                    row["subject"],
                ]
            )
            + " |"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
