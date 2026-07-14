---
title: "Seed Codex Config Without Owning Desktop State"
date: 2026-07-14
agent: "Codex (GPT-5)"
status: accepted
---

# Context

Codex CLI と Codex Desktop は同じ `~/.codex/config.toml` を使用する。モデル、service tier、外部 MCP server などは新しい環境へ復元したい一方、Codex Desktop は同じファイルへ node REPL、computer-use、plugin、marketplace、画面設定などを書き込む。このファイル全体を通常の chezmoi template として収束させると、Desktop が追加した現行設定を `chezmoi apply` で削除し、継続的な drift も発生する。

project trust は machine-local な利用履歴になりやすい。グローバル運用ルールでは `[projects."<path>"]` を常用せず、project-scoped `.codex/config.toml` を読む必要がある repository または worktree だけを例外として許可している。2026-07-14 の実機候補には、この例外条件を満たす project 設定が確認できなかった。

# Decision

- Codex config の chezmoi source を通常の private template から `create_` 属性付き private template へ変更する。
- source は、target が存在しない新規環境でだけ secret-free な初期設定を作成する。
- 初期設定では `gpt-5.6-sol`、default service tier、既存の基本設定と feature flags、Pencil MCP、Money Forward Cloud Accounting MCP を宣言する。
- Codex Desktop が管理・更新する node REPL とその内部環境、computer-use、plugin enable 状態、`[desktop]`、`[marketplaces.*]` は source に固定しない。
- `[projects.*]` は初期設定に固定しない。将来 project-scoped Codex config が必要になった場合だけ、対象 path を個別に再評価する。
- 既存 target は chezmoi で書き換えない。実機にある稼働中の MCP、trust、Desktop/plugin state はそのまま保持する。

# Consequences

新しい環境には再現に必要な Codex CLI の baseline を配置できる。配置後は Codex 自身と Desktop がファイルを更新しても chezmoi drift にならず、app 内部の値や machine-local trust を別のマシンへ持ち込まない。

一方、既存 target に対する宣言的な値の継続的強制は行わない。model、service tier、外部 MCP server を後から変更する場合は、source baseline と必要な実機設定を意図的に更新し、両者を別々に検証する必要がある。
