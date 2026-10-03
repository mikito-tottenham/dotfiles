"""Shared helpers for the fleet_* scripts (repo-wide branch / PR / worktree hygiene).

Standard library only. git is called with ``git -C <repo>``; GitHub is reached only
through ``ghrun gh`` so the materialized 1Password token is used.
"""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

START = time.time()
SESSION_WORKTREE_MARK = "/.claude/worktrees/"
MERGED_CLASSES = {"MERGED", "PR_MERGED", "CONTENT_IN_DEFAULT"}


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S} +{int(time.time() - START)}s] {msg}", flush=True)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run(args: list[str], cwd: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def git(repo: str | Path, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return run(["git", "-C", str(repo), *args], timeout=timeout)


def ok(repo: str | Path, *args: str) -> bool:
    return git(repo, *args).returncode == 0


def out(repo: str | Path, *args: str) -> str | None:
    p = git(repo, *args)
    return p.stdout.strip() if p.returncode == 0 else None


def gh(*args: str, timeout: int = 90) -> subprocess.CompletedProcess:
    return run(["ghrun", "gh", *args], timeout=timeout)


def default_branch(repo: str | Path) -> str:
    name = (out(repo, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD") or "").removeprefix("origin/")
    if name:
        return name
    for cand in ("main", "master"):
        if ok(repo, "rev-parse", "--verify", "-q", f"origin/{cand}"):
            return cand
    return "main"


def is_ancestor(repo: str | Path, a: str, b: str) -> bool:
    return ok(repo, "merge-base", "--is-ancestor", a, b)


def content_in_default(repo: str | Path, ref: str, default_ref: str) -> bool:
    """Merging ref into default_ref leaves the tree unchanged (detects most squash merges)."""
    p = git(repo, "merge-tree", "--write-tree", default_ref, ref)
    if p.returncode != 0:
        return False
    tree = p.stdout.split("\n", 1)[0].strip()
    return tree == out(repo, "rev-parse", f"{default_ref}^{{tree}}")


def worktrees(repo: str | Path) -> list[dict]:
    """Parse ``git worktree list --porcelain``; the first entry is the main checkout."""
    items, cur = [], {}
    for line in (out(repo, "worktree", "list", "--porcelain") or "").splitlines() + [""]:
        if not line:
            if cur:
                items.append(cur)
            cur = {}
            continue
        k, _, v = line.partition(" ")
        cur[k] = v or True
    return items


def checked_out_branches(repo: str | Path) -> set[str]:
    """Branches checked out in any worktree, including worktrees whose directory is gone."""
    return {str(w["branch"]).removeprefix("refs/heads/") for w in worktrees(repo) if isinstance(w.get("branch"), str)}


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, doc: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
