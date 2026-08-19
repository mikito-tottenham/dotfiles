---
title: "Run User-Directed Merge Commands Standalone for Deterministic Permission Matching"
date: 2026-08-19
agent_model: "Claude Code (Claude Fable 5)"
status: accepted
---

# ADR 0057: Run User-Directed Merge Commands Standalone for Deterministic Permission Matching

## Context

ユーザーが「マージして」と指示しても、Claude Code の auto mode セッションで
`gh pr merge` が permission classifier にブロックされ、手動実行を依頼する事例が
複数リポジトリ（taskell-management PR #130、collab-hatakeyama PR #20）で発生した。

調査の結果:

- user settings（`dot_claude/settings.json` → `~/.claude/settings.json`）には
  `Bash(gh pr merge *)` の allow ルールが配備済みで、構文も有効
  （スペース + `*` は `:*` と等価。公式 permissions docs で確認）。
- ブロックされた実行はいずれも `gh pr merge ... && gh pr view ...` や
  `gh pr merge ... | tail ... ; gh pr view ...` のような複合コマンドだった。
- Claude Code は複合コマンドをサブコマンドごとに許可判定するため、連結相手に
  allow ルールがないとコマンド全体が classifier 判定に回り、状態変更操作として
  ブロックされる。allow ルールは auto mode では機能するが、
  `bypassPermissions` モードでは無効（実行自体は通る）。

つまり設定不足ではなく、コマンドの組み立て方が原因で allow ルールが
決定的に一致しない状態だった。

## Decision

- 共通ルール正本 `.chezmoitemplates/agents-common.md` に、ユーザーが明示指示した
  マージなどの状態変更コマンド（`gh pr merge`、`git merge` 等）は `&&`・`;`・パイプで
  連結せず単独コマンドとして実行し、結果確認は後続の別コマンドで行うルールを追加する。
  これは全リポジトリの Claude / Codex セッションに配備される。
- `dot_claude/settings.json` の allow ルールは現状のまま有効とする。
  重複エントリの整理と `Bash(git merge *)` の追加は改善候補だが、
  `dot_*` は Codex 管理対象であり、本作業セッションでは Codex CLI の起動自体が
  classifier にブロックされ委譲できなかったため、実施を見送った（ユーザー判断待ち）。

## Consequences

- 「マージして」の指示に対し、エージェントが `gh pr merge <num> --repo <slug> --merge`
  を単独で実行すれば、配備済み allow ルールに一致してどのリポジトリでも実行できる。
- 結果確認（`gh pr view` 等）が 1 コマンド増えるが、許可判定が決定的になる。
- ローカルブランチの `git merge` は allow ルール未登録のため、auto mode では
  classifier 判定に依存する。頻発するなら `Bash(git merge *)` の追加を
  Codex への委譲で行う。
