---
title: "Import Claude Setup Into Codex Without Managing Runtime State"
date: 2026-08-12
agent_model: "GPT-5 Codex"
status: accepted
---

# ADR 0055: Import Claude Setup Into Codex Without Managing Runtime State

## Context

Claude Code で利用していた instructions、Skills、Plugins、Hooks、recent chats と外部サービス連携を Codex でも利用したい。Codex の公式 Import はこれらを machine-local state へ取り込めるが、plugin cache、OAuth token、chat import state、SQLite、lock、Desktop state を dotfiles へ保存すると secret・端末固有状態・継続的 drift を持ち込む。

Import は repo-local Skills をコピーするため、既存の `.agents/skills/` symlink 運用と併用すると同じ Skill の正本が分岐する。Claude の global hooks には `CLAUDE_PROJECT_DIR` や `CLAUDE_CODE_REMOTE` を前提にした処理も含まれ、Codex ではそのまま永続化できない。

## Decision

- 初回移行は Codex CLI の公式 `/import` で実行し、import history と recent chats は machine-local state とする。
- repo-local Skills はコピーを保持せず、既存の `.agents/skills/` から `.claude/skills/` への symlink を正本とする。
- Codex の global hooks には共通通知と context guard だけを保存する。
- phase artifact enforcement は repo-local `.codex/hooks.json` を正本とする。global hookは、現在のrepositoryにvalidatorが存在する場合だけ呼び出す互換shimとして保持し、自然言語の完了判定は行わない。
- remote secret restoreはClaude固有の `CLAUDE_CODE_REMOTE` に依存させず、`OP_SERVICE_ACCOUNT_TOKEN` が明示された環境でだけ `opmaterialize restore` を実行する。tokenがないローカルセッションではno-opとする。
- Codex transcript は安定 API ではないため、context guard は既知の usage shape だけを保守的に読み、解釈できない場合は no-op とする。
- `[features].codex_hooks` は現行の `[features].hooks` へ移行する。
- plugin cache、OAuth state、import state、SQLite、lock、browser/computer-use/node-repl state、generated artifacts は `.chezmoiignore` で machine-local に留める。
- `~/.codex/config.toml` 全体は ADR-0047 の create-only 方針を維持し、Desktop/plugin/trust state を source へ固定しない。
- 全 repository に適用する Codex 運用ルールは `dot_codex/AGENTS.md.tmpl` と `dot_codex/AGENTS-common.md.tmpl` を正本として `~/.codex/AGENTS.md` へ配備する。repository 固有ルールは各 repository の `AGENTS.md` で追加する。
- 全 repository で使う publisher skill は `docs/skills-install-manifest.md` を正本として user scope へ導入する。dotfiles repository 固有 skill は repo-local `.agents/skills/` に留め、他 repository へ無条件に配備しない。
- 認証 token、OAuth state、session、cache は Git/chezmoi で配備せず、各 CLI の credential store または 1Password secret reference から復元する。

## Consequences

Claude の再利用可能な設定は Codex へ移る一方、認証と session state は各マシンで再作成する。Skills は単一の repo-local 正本から Claude/Codex の両方へ提供される。Codex に等価 payload がない private Claude plugin は自動移植せず、失敗を明示する。
