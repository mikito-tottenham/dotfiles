---
title: "opmaterialize add の field 方式対応"
date: 2026-07-22
agent_model: "claude-fable-5 (Claude Code)"
status: accepted
related:
  - 0046-support-field-based-secrets-in-opmaterialize.md
---

# ADR 0048: opmaterialize add の field 方式対応

## Context

ADR 0046 で `restore`/`diff` を field 方式（Secure Note の `content` フィールド）に
対応させた際、`add` は Document 方式のまま残し、field 方式 manifest に対しては
早期拒否 + 手動登録という known follow-up にしていた。

実運用で bot-nakazawa の `.env`（Chatwork API token 等）を新マシンへ再現可能に
する必要が生じ、既定 vault（`Dotfiles Secrets` = field 方式）へ `opmaterialize add`
で登録できないことがブロッカーになった。ユーザー指示により field 方式 `add` を
実装し、全マシンに適用する。

## Decision

`skills/onepassword-secret-materialize/scripts/opmaterialize` の `add` を
manifest のレイアウト追従型に拡張する。

- dispatch: 既存の category probe（`manifest_item_category`、jq 不要）で
  manifest アイテムの category を判定し、`DOCUMENT` または manifest 不在なら
  従来の Document 経路（完全後方互換）、それ以外（Secure Note）なら field 経路。
- field 経路の秘密値は argv に載せない。`jq --rawfile` と、`op` が公式に
  サポートする get → JSON template → piped edit の roundtrip だけで受け渡す。
  一時ファイルは umask 077 の work_dir 配下（restore と同じ保証）。
  - アイテムが無ければ `op item create --category "Secure Note"`（秘密値なし）で
    作成してから、`op item get --format json` を jq で `content` フィールド
    置換/追加し、stdin パイプで `op item edit` する。
  - 既存 field がある場合は value のみ差し替え、type は温存する。
  - 値はファイルの正確なバイト列（末尾改行込み）で保存し、restore
    （`op read --no-newline`）との exact roundtrip を保つ。
- manifest 行は `field` type で追加/更新する（`update_manifest_file` の kind を
  パラメータ化）。Secure Note manifest の `notesPlain` 更新も同じ
  get → jq → piped edit で行う。
- category probe が Secure Note を観測した後に manifest download が失敗した
  場合は、同名の Document manifest を新規作成して manifest を fork させず、
  明示エラーで停止する。
- field 経路は `jq` 必須（ADR 0046 の restore と同じ前提）。

## Consequences

- 既定 vault に対して `opmaterialize add <file>` が一発で使えるようになり、
  repo 外の `.env`（例: bot-nakazawa の Chatwork token）も他マシンへ
  `opmaterialize restore` で再現できる。
- ADR 0046 の「add は field 方式について意図的に未対応」という decision は
  本 ADR で置き換える（0046 の本文は履歴として書き換えない）。
- 検証: fake `op` による add（field 新規/更新、document 回帰、argv 非露出、
  diff 回帰）テスト、shellcheck、`chezmoi-drift --check-ignore`、
  `skill-quick-validate` を通過。`op item create/edit` の stdin template 対応は
  `op --help` の公式記述に基づく。初回の実 vault 実行時は `opmaterialize diff`
  での roundtrip 確認を推奨する。
- デプロイ済み skill コピー（`~/.claude/skills` / `~/.codex/skills`）は
  `gh skill install --from-local` の通常経路で更新する。
