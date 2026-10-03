---
name: git-branch-review
description: Inspect fresh Git branch state across local machines and collaborators. Use when Codex needs to fetch recent remote refs, decide whether a clean local branch can be fast-forwarded from origin, compare local branches with upstream/default branches, check whether branches are merged, or correlate local branches with GitHub PR state.
---

# Git Branch Review

## Overview

Build a current, conservative view of local and remote Git branch state before deciding what to update, merge, delete, or hand off. Prefer CLI inspection over assumptions, and never hide dirty worktree state.

## Workflow

1. Confirm the target repository path and run all commands from that repository root.
2. Inspect current state before changing anything:
   - `git status --short --branch`
   - `git remote -v`
   - `git branch --show-current`
3. Refresh remote knowledge with `git fetch --all --prune` unless the user explicitly asks for offline inspection.
4. If the user wants the current branch updated from origin, fast-forward only when all conditions are true:
   - worktree is clean by `git status --porcelain`
   - the current branch has an upstream
   - local ahead count is `0`
   - remote behind count is greater than `0`
   - `git pull --ff-only` succeeds
5. Summarize local branches with upstream, ahead/behind counts, merge status relative to `origin/HEAD` or `origin/main`, and latest commit subject.
6. When GitHub context is available, correlate local branch names with PRs using `gh pr list --state all --head <branch>`. Treat missing `gh` auth or missing PRs as information gaps, not proof that no review happened.
7. Report recommended next actions separately from facts. Do not delete, rebase, force-push, or merge branches unless the user explicitly asks after seeing the branch review.

## Script

Use the bundled script for the standard report:

```bash
python skills/git-branch-review/scripts/executable_git_branch_review.py /path/to/repo
```

For this repository when the skill is installed outside the target repo, resolve the script path from the skill folder first.

Useful options:

- `--fast-forward-clean`: update only the current branch, and only when the safety conditions above hold.
- `--no-fetch`: inspect without refreshing remotes.
- `--no-pr`: skip `gh pr list` calls.

The script prints progress before network-sensitive work and emits a Markdown report. It uses only `git`, optional `gh`, and the Python standard library.

## Fleet Mode (many repositories)

Use this mode when the user asks to review or clean up branches, PRs, or worktrees across many repositories (for example 「全部のブランチや PR を整理」「漏れてる PR は」「ブランチを main だけに」). Follow `references/fleet-cleanup.md` and its bundled scripts:

1. `scripts/fleet_scan.py --root <dir> ... --out <.context/...>/01-scan.json` inventories repos read-only. Roots may be a single repo, a ghq root, or a symlink directory; pass both `~/Claude/ghq` and `~/ghq` to cover legacy checkouts.
2. `scripts/fleet_plan.py` turns the scan into `02-plan.json` / `02-plan.md` with categories (merged local, merged remote, open PRs, numbered-file conflicts, unmerged leftovers, dirty trees, protected items).
3. Ask the user once which categories to execute. Nothing is deleted before that approval.
4. `scripts/fleet_delete_local.py` deletes approved local branches (dry-run unless `--execute`) after re-verifying each branch. `scripts/fleet_verify_remote.py` only re-verifies remote branches and prints per-repo delete commands for the user to approve.

Hard rules in this mode:

- Never delete worktrees under `.claude/worktrees/` or branches checked out there; they belong to Claude Desktop sessions.
- Detect squash merges by matching the branch tip to a merged PR head (or an unchanged tree after merge), not by ancestry alone.
- Remote branch deletion, PR close, and PR merge require explicit user approval per category or PR; run each such command alone, never chained with `&&`, `;`, or pipes. Do not route around an auto mode classifier denial.
- Call GitHub only through `ghrun gh`. On 401 or a missing token, ask the user to run `ghrun --refresh` in a normal terminal.
- Before merging old PRs, check numbered files such as `docs/adr/NNNN-*` for collisions with the default branch.

For onboarding new repositories use `ghq-repo-placement`; routine fast-forward sync of checkouts is handled by the dotfiles-managed `repo-sync` command (see the last section of the reference).

## Output Contract

Include:

- current branch, upstream, worktree cleanliness, ahead/behind counts, and whether a fast-forward ran or was skipped
- local branch table with upstream, ahead/behind, merged/not merged relative to default remote ref, PR status, last update, tip SHA, and subject
- explicit gaps such as `gh unavailable`, fetch failure, no upstream, detached HEAD, or ambiguous default branch
- concrete next actions, for example `pull --ff-only`, inspect a dirty diff, push an unpublished branch, close a merged PR branch, or ask a collaborator about an unmerged branch

Do not present inferred PR state as certain when `gh` could not query GitHub.
