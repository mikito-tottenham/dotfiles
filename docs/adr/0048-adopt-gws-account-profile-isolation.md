---
title: "Adopt gws-account Profile Isolation for Google Workspace CLI"
date: 2026-07-23
agent_model: "Claude Code (Claude Fable 5)"
status: accepted
---

# ADR 0048: Adopt gws-account Profile Isolation for Google Workspace CLI

## Context

Google Workspace 操作は複数の法人・事業コンテキストにまたがり、CLI のデフォルト
OAuth 状態のまま実行すると誤った principal で実行するリスクがある。

本 fork はこれまで `scripts/gws-as` を使い、`gws auth export --unmasked` 出力の
フラットな credential ファイル（`~/.config/gws/accounts/<name>.json`）を
`GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` で切り替えていた。この方式には
次の弱点があった。

- 切り替え対象が credential ファイルだけで、`token_cache.json` や `cache/` などの
  実行時 state はデフォルト config dir（`~/.config/gws/` 直下）をアカウント間で共有する。
- env はファイルより優先されるため、古い `GOOGLE_WORKSPACE_CLI_TOKEN` /
  `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` が残っていると選択したアカウントを
  黙って上書きできる（運用注意として文書化するだけで、実行時ガードが無い）。

upstream（rmanzoku/dotfiles）は ADR 0045 "Manage Multi-Account OAuth Profiles" で
この問題に対する設計を確立しており、`gws-account` ラッパーと `gws-cli-runner`
Skill として実装済みである。

## Decision

upstream の思想と実装をそのまま採用し、`gws-as` 方式を廃止する。

- `dot_local/bin/executable_gws-account`（upstream 実装を移植）を唯一の実行経路とする。
  `gws-account <profile> ...` が `GOOGLE_WORKSPACE_CLI_CONFIG_DIR` を
  `~/.config/gws/accounts/<profile>` に向け、config dir（credential・token cache・
  実行時 state を含む）をプロファイル単位で丸ごと分離する。
- アカウント選択は常にコマンドラインに明示され、デフォルト OAuth 状態には依存しない。
- ラッパーは ambient な `GOOGLE_WORKSPACE_CLI_TOKEN` を検出したら実行拒否（exit 78）し、
  ambient な `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` は明示的な
  `GWS_ACCOUNT_CREDENTIALS_FILE` 指定が無い限り拒否する。
- fallback は同一 principal・同一プロファイル内の復旧（restore / 再ログイン）だけを許可し、
  別アカウント・別プロファイルへの自動切り替えを禁止する。拒否後に素の `gws` で
  再試行することも禁止する。
- リポジトリは具体的なアカウント識別子・プロファイル名・責任ラベルを定義しない。
  それらはこのリポジトリの外（Personal・各作業リポジトリ・machine-local state）が所有する。
- 再現が必要なファイルは `~/.config/gws/accounts/<profile>/client_secret.json` と
  `credentials.json`（`gws auth export --unmasked` 出力。可搬）で、既存の
  `opmaterialize` / `Secrets Manifest` ワークフローで 1Password から復元する。
  `credentials.enc` はマシン固有の暗号化 state、`token_cache.json` / `cache/` は
  実行時 state であり、いずれも 1Password 登録対象外とする。
- agent 側の運用契約（プロファイルを推測しない・同一プロファイル内でのみ復旧する等）は
  upstream の `skills/gws-cli-runner` を first-party skill として取り込み正本とする。

## Migration

- export 済み JSON が `<profile>/credentials.json` としてそのまま有効なことを
  実機検証済み（`gws auth status` / `drive files list` 成功、再ログイン不要）。
- 既存のフラット構成（`accounts/<name>.json` + `<name>.d/client_secret.json`）は
  `accounts/<profile>/{client_secret,credentials}.json` へ移設し、`Secrets Manifest` の
  out_path を新パスへ更新する。旧パスの manifest 行と旧 1Password item は削除する。
- Claude web 環境 UI の Setup script（git 外）は `gws-as` の symlink を
  `gws-account` へ手動で更新する（正本スニペットは
  `docs/web-session-runner-setup.md`）。

## Consequences

- アカウント選択がコマンドラインで可視化され、誤アカウント実行と env 汚染による
  黙った上書きが実行時に防がれる。
- プロファイルごとに GCP プロジェクト＋OAuth クライアント＋1 回のログインが必要になるが、
  この初期コストは cross-account 事故の低減と引き換えに許容する。
- upstream 実装をそのまま使うため、upstream の改善を diff 最小で取り込める。
