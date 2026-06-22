---
title: "opmaterialize の field 方式シークレット対応"
date: 2026-06-22
agent_model: "Claude Code"
status: accepted
---

# ADR 0046: opmaterialize の field 方式シークレット対応

## Context

ADR 0036 で 1Password ベースの `opmaterialize` ワークフローを定めたが、その記述は 1Password の **Document** アイテム前提だった。`Secrets Manifest` も各シークレットファイルも Document として `op document get` で取得する想定である。

しかし実際の `Dotfiles Secrets` vault は **field 方式**で構築されていた。

- `Secrets Manifest` は Secure Note で、マニフェスト TSV はその `notesPlain` フィールドに入っている。
- 各シークレットファイルは Secure Note で、本体はカスタムフィールド `content` に入っている。
- マニフェストの行 type は `field`。

`opmaterialize` は `type=document` しか実装しておらず、マニフェストも `op document get` で読むため、`restore`/`diff` は `op` のエラー `<id> is not a document` で即座に失敗していた。web bootstrap（ADR 0045）はこれを `onepassword: skipped: opmaterialize restore 失敗` として記録していた。

## Decision

1Password vault は変更せず、`opmaterialize` の skill スクリプト（`skills/onepassword-secret-materialize/scripts/opmaterialize`。`dot_*` のラッパーが呼ぶ実体ロジック）を拡張し、`restore` と `diff` を field 方式に対応させる。

- マニフェストは `op document get` ではなく `op read "op://<vault>/<manifest-item>/notesPlain"` で Secure Note の `notesPlain` フィールドから読む。
- `type=field` の行ハンドラを追加する。アイテム名に `/` が含まれ得て `op://` パスで不正になるため、`op item get --format json`（`jq` 必須）で不変の item id を解決し、`op read "op://<vault>/<id>/<field>"` でフィールドを読む。フィールドラベルの既定は `content` で、`OP_DOTFILES_MATERIALIZE_FIELD_LABEL` で上書きできる。
- 後方互換のため `type=document` も維持する。
- `add` は Document 方式のまま。Document を orphan 化したりマニフェストを中途半端に更新したりしないよう、マニフェストアイテムが Document でない場合は `add` は早期に拒否する。field 方式の登録は、field 対応の `add` が実装されるまでは 1Password 上で手動で行う（`content` フィールドを持つ Secure Note ＋ `field` 行をマニフェストに追加）。

シークレットの実値・マニフェスト・個別のアイテム名は ADR 0036 と同様に git の管理外に保つ。

## Consequences

- 既存の field 方式 `Dotfiles Secrets` vault に対して `opmaterialize restore`/`diff` が動作し、web bootstrap の step 5 が skip されずに完了できる。
- `type=field` 行には `jq` が必須（対象環境では既に利用可能）。
- マニフェストアイテム名や field 方式アイテムのタイトルは `op://` 参照を壊してはならない。アイテム本体は不変の id で読むため、タイトルに `/` を含んでも安全。
- `add` は field 方式について意図的に未対応であり、既知の follow-up として skill に明記している。
- デプロイ済みの `~/.local/bin/opmaterialize` ラッパーは不変（`dot_*`、Codex 管理）。変更したのは skill のロジックと docs のみ。インストール済みの skill コピーは通常の skill install / web bootstrap 経路で更新される。
