---
title: "Bootstrap Workspace Under Ghq Root"
status: "accepted"
date: "2026-05-15"
worked_at: "2026-05-15T07:52:18Z"
agent_model: "GPT-5"
updated_at: "2026-06-18T10:56:00+09:00"
updated_by: "GPT-5.5 Codex"
---

# ADR-0034: Bootstrap Workspace Under Ghq Root

## Context

This Mac historically used a Conductor-first path layout such as `/Users/rmanzoku/conductor/repos`.
Future project-independent local repositories should move toward a shared clone root instead of being tied to a specific orchestration tool.

`ghq` is already managed by `Brewfile`.
When `ghq` is available, its configured root is the best local source of truth for repository placement.

## Decision

Add `scripts/bootstrap-workspace` as the standard bootstrap entrypoint for the project-independent workspace repository.
The script clones or fast-forward pulls `https://github.com/mikito-tottenham/workspace.git`.

Placement rules:

- use `ghq root` when `ghq` is installed and configured
- fall back to `~/workspace/github.com/mikito-tottenham/workspace` when `ghq` is unavailable
- allow explicit overrides with `WORKSPACE_ROOT`, `WORKSPACE_TARGET`, and `WORKSPACE_REPO_URL`

Codex trust includes `/Users/mikito/workspace/github.com/rmanzoku` for existing dotfiles work and can rely on explicit per-run trust for newly cloned workspace tasks when needed.
Existing Conductor paths remain trusted during the migration period.

## Consequences

New machines can restore the dotfiles, install packages, and then clone or update `mikito-tottenham/workspace` without depending on a project-specific checkout.
Conductor paths remain usable for old repositories, but new project-independent clone automation should prefer the ghq/workspace layout.
