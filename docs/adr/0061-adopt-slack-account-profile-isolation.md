---
title: "Adopt slack-account Profile Isolation for Slack Web API"
date: 2026-09-11
agent_model: "Claude Code (Claude Fable 5.1)"
status: accepted
updated_at: 2026-09-25
updated_by_agent_model: "Claude Opus 5.5 (claude-opus-5-5)"
---

# ADR 0061: Adopt slack-account Profile Isolation for Slack Web API

## Context

Slack も Google Workspace と同様に複数の法人・事業コンテキスト（複数ワークスペース）に
またがって操作する必要がある。しかし MCP 経由の接続は 1 ワークスペースに閉じる。

- Slack 公式 MCP サーバーは Dynamic Client Registration に対応しておらず、固定の
  OAuth client（Slack App）が必須になる。
- claude.ai のコネクタは 1 コネクタ = 1 ワークスペースで、複数ワークスペースを同時に
  扱う設計になっていない。
- Claude Code は MCP の OAuth 資格情報を endpoint 単位で保存するため、同一 endpoint の
  Slack MCP を複数ワークスペースへ向けて併存させることができない。

一方、Slack Web API は token（user token `xoxp-` / bot token `xoxb-`）を渡すだけで
ワークスペースを選べる。本 fork には既に read-only の `slack-fetch-message`
（`SLACK_API_TOKEN` 1 本、permalink 読取専用）があり、書込や検索まで含めた複数
ワークスペース運用の主経路として、`gws-account`（ADR 0048）と同型のプロファイル分離
CLI を Web API 側に置くのが最も摩擦が小さい。

契約の正本は taskell-management 側の作業 artifact
（`.context/2026-09-11-yoake-github-export/06-slack-account-contract.md`）で確定した。

## Decision

- `dot_local/bin/executable_slack-account` を追加し、`slack-account <profile> <subcommand>`
  を複数ワークスペース操作の主経路とする。MCP（Slack 公式 MCP / claude.ai コネクタ）は
  1 ワークスペース限定の補助に留める。
- profile は `^[a-z0-9][a-z0-9-]*$` に限定し、token は環境変数
  `SLACK_<PROFILE>_TOKEN`（profile を大文字化、`-` → `_`。例 `SLACK_TWIN_TOKEN`）で
  供給する。実値の正本は 1Password で、`~/.config/op/dotfiles.env` には `op://` reference
  だけを置き、`op run --env-file="$HOME/.config/op/dotfiles.env" -- slack-account ...` で
  解決する。token 未設定・`op://` のまま・`xoxp-`/`xoxb-` 以外は exit 1 で拒否し、
  token 値と Authorization ヘッダは stdout / stderr / ログに出さない。
- 起動時に stderr へ `slack-account: profile=<p> token_type=<user|bot>` を 1 行出し、
  選択したプロファイルをコマンドラインと出力の両方で可視化する（gws-account と同型）。
- サブコマンドは最小セット `auth status` / `read` / `users find` / `channels list` /
  `dm open` / `post` / `upload` とし、全サブコマンドに `--json` を持つ。複数行本文は
  `--text-file` / `--comment-file` でファイル経由にする。
- `read` は既存 `slack-fetch-message` を子プロセスで exec し、`SLACK_API_TOKEN` を
  子環境にだけ渡す。実装は複製せず、単体コマンドも当面残す。
- Python 3 標準ライブラリのみで実装し、依存を追加しない。API 呼び出しごとに method 名と
  ok/error を stderr に出し、429 は Retry-After 秒待って最大 3 回だけ再試行する。
  それ以外の暗黙リトライ（特に書込 API）は行わない。
- exit code は 0 成功 / 1 使い方・設定 / 2 Slack API `ok:false` / 3 ネットワーク・HTTP。
- scope 方針は profile ごとに決める。`taskell` はユーザーがワークスペース Owner のため、Owner が
  付与できる全 user token scope（`admin.*` は Enterprise Grid 専用のため対象外）を付与する。
  他ワークスペース（yoake / twin / amicitia）は契約記載の最小 scope に留める。CLI 側は scope を
  制限せず、token の scope を唯一の制限とする。
- 汎用サブコマンド `api <method> [--params <json> | --params-file <path>]` を置き、任意の Web
  API method を同じ form-encoded POST 経路（429 再試行、`api: <method>` ログ、token 非出力）で
  呼べるようにする。allowlist は設けない（書込 method も含む）。宛先制限などの運用ガードは
  CLI ではなく各ワークスペースの接続ガイド側に書く。params の dict / list 値は JSON 文字列化
  して渡し（blocks, attachments 等）、出力はレスポンス JSON をそのまま stdout に出す。
- 各ワークスペースへ配布する Slack App は manifest（YAML）から作成する。manifest の正本は
  taskell-management `docs/slack-app-manifest.yaml`（Taskell の資産であり、本 CLI の資産では
  ないため dotfiles には置かない）。

## Consequences

- ワークスペース選択がコマンドラインに明示され、MCP の 1 ワークスペース制約に縛られずに
  Web API を複数ワークスペースへ使い分けられる。
- プロファイルごとに Slack App の作成と token の 1Password 登録が必要になる。この初期
  コストは cross-workspace 事故の低減と引き換えに許容する。
- `slack-fetch-message` と `slack-account read` の 2 入口が併存する。読取の実装は
  `slack-fetch-message` 側に一本化されているため重複は入口のみである。
- `~/.config/op/dotfiles.env` の行がプロファイル数だけ増える。例は
  `dot_config/private_op/dotfiles.env.example` に置く。
- `taskell` プロファイルの user token は書込を含む広い scope を持ち、`api` は allowlist を
  持たないため、誤操作の抑止は CLI ではなく運用（接続ガイド、`--params-file` 経由の内容確認、
  profile 名の明示）に依存する。

## 採用（2026-09-25）

- ユーザーが Slack 接続を 1Password 経由に揃える方針を示したため、本 ADR を accepted とする。
  Slack 操作の主経路は `oprun slack-account <profile> ...` とする。
- 2026-09-11 の起案後、`slack-account` と本 ADR が git 未追跡のまま `~/.local/bin` へも
  配備されておらず、主経路が実際には使えない状態だった。本更新で追跡対象に入れ、
  `chezmoi apply` で配備した。
- 1Password を通らない OAuth 経路だった Slack 公式 MCP `slack-twin`（user scope）は削除し、
  `scripts/bootstrap-web` / `scripts/verify-cloud-parity` の対象外リストからも外した。
  yoake ワークスペースは slack-account の profile が無いため、当面 claude.ai コネクタのまま残る。
- taskell-ai/twin repo の ADR（2026-08-19「Slack 複数テナント接続の方針」）は claude.ai
  コネクタを正としており、本 ADR と主経路の判断が逆になっている。twin 側 ADR の更新は
  twin repo で扱う。

## 未決

- `taskell` 以外のプロファイルで user token と bot token のどちらを使うか（投稿者名の見え方）は
  未確定。`token_type` の表示で区別できる状態に留める。2026-09-25 時点の `twin` は
  `SLACK_TWIN_TOKEN` と `SLACK_TWIN_BOT_TOKEN` が同じ 1Password 項目を指す bot token で、
  投稿者は Slack App の名前で表示される。
- `upload` の実機検証は Slack 側 token が揃ってから行う。

## 検証

- `python3 -m py_compile dot_local/bin/executable_slack-account`
- `--help` と各サブコマンドの `--help` が exit 0
- 不正 profile / token 未設定 / `op://` 値 / `xoxz-` 形式が exit 1
- ローカル HTTP サーバーの模擬 API で 429 再試行、`ok:false` の exit 2、HTTP 500 の exit 3、
  upload POST の Content-Length 固定を確認
- `api`: 模擬 API で `ok` の JSON 出力、`ok:false` の exit 2、dict 値の JSON 文字列化、
  不正 method 名 / `--params` と `--params-file` の併用が exit 1
- `op run --env-file="$HOME/.config/op/dotfiles.env" -- slack-account twin auth status`
- `op run --env-file="$HOME/.config/op/dotfiles.env" -- slack-account twin api auth.test`
- 2026-09-25: 配備後の `oprun slack-account taskell auth status`（user token）と
  `oprun slack-account twin auth status`（bot token）がいずれも `auth.test ok` で exit 0
