---
title: "Manage Desktop Automations With Chezmoi"
date: 2026-05-13
agent: "Codex (GPT-5)"
status: accepted
updated_at: 2026-10-03
updated_by_agent_model: "Claude Opus 5.5 (claude-opus-5-5)"
---

# Context

Codex Desktop stores recurring automations under `~/.codex/automations/`. Some files in that tree are stable definitions, while others are runtime state. Claude Desktop / Claude Code also writes task-related files under `~/.claude/tasks`, but those files are UUID-scoped execution records with locks and high-water marks.

Persistent automation setup should be reproducible across machines, but applying transient execution state through chezmoi would risk copying stale locks, replay metadata, or machine-local scheduling noise.

# Decision

- Manage stable, secret-free Desktop automation definitions in this dotfiles repository through chezmoi.
- Treat Codex Desktop `~/.codex/automations/<automation-id>/automation.toml` as the canonical managed definition.
- Treat Codex Desktop `~/.codex/automations/<automation-id>/memory.md` as runtime operating context by default because it can change after each run.
- Ignore runtime state such as `.run-jitter-salt`, locks, high-water marks, logs, session history, and UUID-scoped task state.
- Keep Claude `~/.claude/tasks` unmanaged unless a future version exposes a stable declarative schedule file distinct from runtime execution records.

# Consequences

New automations can be restored with `chezmoi apply` when they are declarative and secret-free. Machine-local execution state and frequently updated operating notes remain local, reducing the chance of stale or invalid scheduler behavior after restore.

# Addendum (2026-10-03, ADR-0069)

- `claude-github-daily-sync` を管理対象の automation に加えた。定義は `dot_codex/automations/claude-github-daily-sync/automation.toml.tmpl`、実行する script は `~/.local/bin/claude-github-daily-sync`（`dot_local/bin/executable_claude-github-daily-sync`）。script を `.context` に置かない
- `~/.codex/rules/automation-network.rules`（`dot_codex/rules/automation-network.rules.tmpl`）も管理対象にする。automation の sandbox で DNS が遮断される問題への対策として、同期コマンドと対象パッケージの `brew` 操作だけを prefix rule で allow する。Codex が承認時に書き込む `default.rules` は引き続き管理対象外とする
- `memory.md` は従来どおり runtime state として管理しない。肥大化の対策は automation の prompt で上限（20KB）と要約方法を指示して行う
