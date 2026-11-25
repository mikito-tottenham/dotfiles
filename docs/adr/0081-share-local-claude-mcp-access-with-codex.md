---
title: "Mac の Codex に Chatwork と Money Forward Alpha を登録する"
date: 2026-11-25
agent: "Codex (GPT-6)"
status: accepted
---

# 背景

Claude Code のユーザー設定には Chatwork と Money Forward Alpha があり、Codex のユーザー設定には Money Forward Beta がある。認証情報を付けない疎通確認では、Alpha は MCP の初期化に応答し、Beta は HTTP 401 を返した。既存の Beta 接続先を維持するため、Alpha は別名で登録する。

# 決定

- Mac の Codex 初期設定に `chatwork` と `mfc_ca_alpha` を追加する。Chatwork は Claude Code と同じ `oprun` と 1Password の参照を使用する。Alpha で会計データを扱う前に `currentOffice` で対象事業者を確認する。
- ADR-0047 の初回作成方式を維持する。既存の `~/.codex/config.toml` には、次のコマンドで登録を追加する。新しい Codex セッションで接続を確認する。

  ```sh
  codex mcp add chatwork --env OPRUN_NO_MASKING=1 -- "$HOME/.local/bin/oprun" npx -y @chatwork/mcp-server
  codex mcp add mfc_ca_alpha --url https://alpha.mcp.developers.biz.moneyforward.com/mcp/ca/v3
  ```

  Alpha の追加時に OAuth の案内が出たら、利用者が対象アカウントで認可する。登録後に認可を再開する場合は `codex mcp login mfc_ca_alpha` を使う。

- 対象は Mac のユーザー単位 MCP とする。プロジェクトで個別に承認された MCP はそのプロジェクトのアカウント境界を維持する。Pencil は既存の登録先の実行ファイルが見つからなかったため、配備を見送る。

# 検証

- chezmoi が生成する TOML をパースし、`oprun` 経由の設定と Money Forward の両エンドポイントを確認する。
- 実機は `codex mcp get chatwork` と `codex mcp get mfc_ca_alpha` で登録を確認し、Chatwork の `get_me` で認証を、Money Forward の `currentOffice` で認可を確認する。
