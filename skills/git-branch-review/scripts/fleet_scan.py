#!/usr/bin/env python3
"""Inventory branches / PRs / worktrees across many repositories (read-only).

Writes one JSON document (01-scan.json) with raw data and a per-branch class.
Nothing is deleted. The only state change is ``git fetch`` of remote-tracking refs,
and only when --fetch or --prune is given.

usage:
  fleet_scan.py --root ~/Claude/ghq --root ~/ghq --out .context/<date>-branch-fleet/01-scan.json
  fleet_scan.py --root /path/to/one/repo --out ... --no-pr

Roots may be a repository itself, a ghq root (host/owner/repo), or a directory of
symlinks such as ~/Claude/repos. The first root that contains a GitHub slug is the
primary checkout; later checkouts of the same slug are marked ``duplicate_of``.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fleet_common import (SESSION_WORKTREE_MARK, content_in_default, default_branch, gh, git,  # noqa: E402
                          is_ancestor, log, now_iso, ok, out, worktrees, write_json)

SKIP_DIRS = {".git", ".claude", ".context", "node_modules", ".venv", "venv", "go", "__pycache__"}
PR_FIELDS = ("number,state,headRefName,headRefOid,title,createdAt,updatedAt,mergedAt,closedAt,"
             "author,isDraft,url,baseRefName,isCrossRepository,mergeable")


def discover(roots: list[str], max_depth: int) -> list[tuple[Path, str]]:
    """Return (realpath, alias) for main checkouts (``.git`` is a directory) under the roots."""
    found: dict[Path, str] = {}
    for raw in roots:
        root = Path(os.path.expanduser(raw))
        if not root.exists():
            log(f"root not found, skipped: {root}")
            continue
        if (root / ".git").is_dir():
            found.setdefault(root.resolve(), raw.rstrip("/"))
            continue
        base_depth = len(root.parts)
        for dirpath, dirnames, _ in os.walk(root, followlinks=True):
            d = Path(dirpath)
            if (d / ".git").is_dir():
                found.setdefault(d.resolve(), f"{raw.rstrip('/')}:{d.relative_to(root)}")
                dirnames[:] = []
                continue
            if len(d.parts) - base_depth >= max_depth:
                dirnames[:] = []
                continue
            dirnames[:] = sorted(x for x in dirnames if x not in SKIP_DIRS)
    return list(found.items())


def slug_of(repo: Path) -> str:
    url = out(repo, "remote", "get-url", "origin") or ""
    if "github.com" not in url:
        return ""
    return url.split("github.com")[-1].lstrip(":/").removesuffix(".git")


def fetch_prs(slug: str) -> tuple[list[dict] | None, str | None]:
    p = gh("pr", "list", "-R", slug, "--state", "all", "--limit", "300", "--json", PR_FIELDS)
    if p.returncode != 0:
        return None, (p.stderr.strip() or "gh failed")[:300]
    return json.loads(p.stdout), None


def classify_ref(repo: Path, ref: str, tip: str, default_ref: str, prs: list[dict]) -> tuple[str, dict]:
    open_prs = [x for x in prs if x["state"] == "OPEN"]
    merged_prs = [x for x in prs if x["state"] == "MERGED"]
    closed_prs = [x for x in prs if x["state"] == "CLOSED"]
    ahead = int(out(repo, "rev-list", "--count", f"{default_ref}..{ref}") or 0)
    info = {"ahead_of_default": ahead,
            "prs": [f"#{x['number']} {x['state']}" for x in prs],
            "merged_pr_heads": [x["headRefOid"] for x in merged_prs]}
    if open_prs:
        return "OPEN_PR", info
    if ahead == 0:
        return "MERGED", info
    for x in merged_prs:
        # squash merge: the branch tip equals (or is behind) the head of a merged PR
        if tip == x["headRefOid"] or is_ancestor(repo, tip, x["headRefOid"]):
            return "PR_MERGED", info
    if content_in_default(repo, ref, default_ref):
        return "CONTENT_IN_DEFAULT", info
    if merged_prs:
        return "PR_MERGED_BUT_NEWER_COMMITS", info
    if closed_prs:
        return "PR_CLOSED_UNMERGED", info
    return "NO_PR_UNMERGED", info


def seq_numbers(paths: list[str], patterns: list[re.Pattern]) -> dict[str, list[str]]:
    nums: dict[str, list[str]] = {}
    for p in paths:
        for pat in patterns:
            m = pat.search(p)
            if m:
                nums.setdefault(m.group(1), []).append(p)
    return nums


def scan(real: Path, alias: str, args, patterns: list[re.Pattern]) -> dict:
    r: dict = {"alias": alias, "path": str(real), "slug": slug_of(real)}
    r["fetch_error"] = None
    if args.fetch or args.prune:
        fetch_args = ["fetch", "--quiet", "origin"] + (["--prune"] if args.prune else [])
        f = git(real, *fetch_args, timeout=180)
        r["fetch_error"] = f.stderr.strip()[:300] if f.returncode != 0 else None
    default = default_branch(real)
    default_ref = f"origin/{default}"
    r["default"] = default
    r["current"] = out(real, "branch", "--show-current")
    r["dirty"] = len((out(real, "status", "--porcelain") or "").splitlines())
    r["stash"] = len((out(real, "stash", "list") or "").splitlines())

    if args.no_pr or not r["slug"]:
        prs, err = [], ("skipped (--no-pr)" if args.no_pr else "no github origin")
    else:
        prs, err = fetch_prs(r["slug"])
    r["pr_error"] = err
    prs = prs or []
    prs_by_head: dict[str, list[dict]] = {}
    for x in prs:
        if not x.get("isCrossRepository"):
            prs_by_head.setdefault(x["headRefName"], []).append(x)

    now = datetime.now(timezone.utc)
    default_seq = {}
    open_prs = [x for x in prs if x["state"] == "OPEN"]
    if patterns and open_prs:
        default_seq = seq_numbers((out(real, "ls-tree", "-r", "--name-only", default_ref) or "").splitlines(), patterns)
    r["seq_duplicates_in_default"] = {k: v for k, v in default_seq.items() if len(v) > 1}
    r["open_prs"] = []
    for x in open_prs:
        entry = {
            "number": x["number"], "title": x["title"], "head": x["headRefName"], "base": x["baseRefName"],
            "author": x["author"]["login"], "draft": x["isDraft"], "mergeable": x.get("mergeable"),
            "created": x["createdAt"][:10], "updated": x["updatedAt"][:10],
            "age_days": (now - datetime.fromisoformat(x["updatedAt"].replace("Z", "+00:00"))).days,
            "url": x["url"], "cross_repo": bool(x.get("isCrossRepository")),
            "head_in_default": (out(real, "rev-parse", "-q", "--verify", x["headRefOid"]) is not None
                                and is_ancestor(real, x["headRefOid"], default_ref)),
            "seq_conflicts": [],
        }
        head_ref = f"origin/{x['headRefName']}"
        if patterns and not entry["cross_repo"] and ok(real, "rev-parse", "-q", "--verify", head_ref):
            added = (out(real, "diff", "--name-only", "--diff-filter=A", f"{default_ref}...{head_ref}") or "").splitlines()
            for num, files in seq_numbers(added, patterns).items():
                if num in default_seq:
                    entry["seq_conflicts"].append({"number": num, "pr_files": files, "default_files": default_seq[num]})
        r["open_prs"].append(entry)

    r["worktrees"] = []
    wt_branches: dict[str, dict] = {}
    for w in worktrees(real)[1:]:
        path = str(w.get("worktree"))
        br = str(w.get("branch") or "").removeprefix("refs/heads/")
        exists = os.path.isdir(path)
        entry = {"path": path, "branch": br or None, "exists": exists, "prunable": bool(w.get("prunable")),
                 "locked": bool(w.get("locked")), "session_worktree": SESSION_WORKTREE_MARK in path,
                 "dirty": len((out(path, "status", "--porcelain") or "").splitlines()) if exists else None,
                 "last": out(path, "log", "-1", "--format=%cs") if exists else None}
        r["worktrees"].append(entry)
        if br:
            wt_branches[br] = entry

    r["local"] = []
    fmt = "%(refname:short)\t%(objectname)\t%(upstream:short)\t%(upstream:track)\t%(committerdate:short)\t%(subject)"
    for line in (out(real, "for-each-ref", f"--format={fmt}", "refs/heads/") or "").splitlines():
        name, tip, up, track, date, subj = (line.split("\t") + [""] * 6)[:6]
        if name == default:
            continue
        cls, info = classify_ref(real, name, tip, default_ref, prs_by_head.get(name, []))
        pushed = bool(up) and "gone" not in track and ok(real, "rev-parse", "-q", "--verify", up)
        unpushed = int(out(real, "rev-list", "--count", f"{up}..{name}") or 0) if pushed else None
        wt = wt_branches.get(name)
        r["local"].append({"name": name, "tip": tip, "upstream": up or None, "track": track,
                           "upstream_gone": "gone" in track, "unpushed_vs_upstream": unpushed,
                           "date": date, "subject": subj[:80], "class": cls,
                           "is_current": name == r["current"],
                           "in_worktree": wt["path"] if wt else None,
                           "in_session_worktree": bool(wt and wt["session_worktree"]), **info})

    r["remote"] = []
    fmt = "%(refname:short)\t%(objectname)\t%(committerdate:short)\t%(authoremail)\t%(subject)"
    for line in (out(real, "for-each-ref", f"--format={fmt}", "refs/remotes/origin/") or "").splitlines():
        ref, tip, date, email, subj = (line.split("\t") + [""] * 5)[:5]
        name = ref.removeprefix("origin/")
        if name in ("HEAD", default) or ref == "origin":
            continue
        cls, info = classify_ref(real, ref, tip, default_ref, prs_by_head.get(name, []))
        r["remote"].append({"name": name, "tip": tip, "date": date, "author": email.strip("<>"),
                            "subject": subj[:80], "class": cls, **info})
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", action="append", required=True, help="repo, ghq root, or symlink dir (repeatable)")
    ap.add_argument("--out", required=True, help="output JSON path (put it under .context/)")
    ap.add_argument("--max-depth", type=int, default=3, help="directory depth searched under each root (ghq = 3)")
    ap.add_argument("--exclude", action="append", default=[], help="slug or alias substring to skip (repeatable)")
    ap.add_argument("--fetch", action="store_true", help="git fetch origin before inspecting")
    ap.add_argument("--prune", action="store_true", help="git fetch --prune (needed for accurate 'upstream gone')")
    ap.add_argument("--no-pr", action="store_true", help="skip GitHub PR lookups")
    ap.add_argument("--seq-pattern", action="append", default=None,
                    help=r"regex with one group for numbered files (default: ^docs/adr/(\d{3,4})-); '' disables")
    args = ap.parse_args()
    raw_patterns = args.seq_pattern if args.seq_pattern is not None else [r"^docs/adr/(\d{3,4})-"]
    patterns = [re.compile(p) for p in raw_patterns if p]

    me = None
    if not args.no_pr:
        p = gh("api", "user", "--jq", ".login")
        me = p.stdout.strip() if p.returncode == 0 else None
        if not me:
            log("gh user lookup failed; PR data will be marked as gaps. If ghrun reports 401 or a missing token, "
                "ask the user to run `ghrun --refresh` in a normal terminal.")
    targets = [(real, alias) for real, alias in discover(args.root, args.max_depth)
               if not any(x in alias or x == slug_of(real) for x in args.exclude)]
    log(f"start: {len(targets)} repos, roots={args.root}, fetch={'prune' if args.prune else args.fetch}, gh_user={me}")
    results, seen_slugs = [], {}
    for i, (real, alias) in enumerate(targets, 1):
        log(f"({i}/{len(targets)}) {alias} ...")
        try:
            r = scan(real, alias, args, patterns)
            if r["slug"] and r["slug"] in seen_slugs:
                r["duplicate_of"] = seen_slugs[r["slug"]]
            elif r["slug"]:
                seen_slugs[r["slug"]] = r["path"]
            log(f"    local={len(r['local'])} remote={len(r['remote'])} open_prs={len(r['open_prs'])} "
                f"worktrees={len(r['worktrees'])} dirty={r['dirty']} fetch_err={bool(r['fetch_error'])} "
                f"pr_err={r['pr_error'] or False} dup={bool(r.get('duplicate_of'))}")
        except Exception as e:  # one failing repo must not stop the inventory; keep the failure visible
            log(f"    FAILED: {e}")
            r = {"alias": alias, "path": str(real), "error": str(e)[:300]}
        results.append(r)
    doc = {"task": "branch-fleet", "phase_or_step": "01-scan", "created_at": now_iso(),
           "roots": args.root, "gh_user": me, "repos": results}
    write_json(args.out, doc)
    log(f"done -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
