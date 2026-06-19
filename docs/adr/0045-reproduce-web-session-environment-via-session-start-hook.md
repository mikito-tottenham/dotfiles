---
title: "Reproduce Web Session Environment Via SessionStart Hook"
date: 2026-06-19
agent_model: "Claude Code"
status: accepted
---

# ADR 0045: Reproduce Web Session Environment Via SessionStart Hook

## Context

Claude Code on the web は ephemeral なコンテナでセッションを実行する。コンテナは起動ごとにリポジトリを clone し直し、一定時間後に回収されるため、`chezmoi apply` の結果やインストール済みスキルなどの派生状態は毎回失われる。永続するのは git に push された内容だけである。

`AGENTS.md` のスキル管理ルールは、配布スキルの復元を当面 script 化せず `docs/skills-install-manifest.md` の docs-only manifest を正本とし、`gh skill install --from-local` を標準配備経路と定めている。しかし web の ephemeral 環境には `gh` / `gh skill` が無く、毎セッション手動で `chezmoi apply` とスキル復元を行うのは非現実的である。

## Decision

Claude Code on the web の ephemeral 環境に限定した自動再現を導入する。

- `scripts/bootstrap-web` を追加し、(1) chezmoi の用意、(2) `.chezmoiignore` 整合確認後の `chezmoi apply --force`、(3) スキルの再インストールを冪等に行う。
- 再現対象は **web で復元可能なサブセット**であり、`docs/skills-install-manifest.md` 全体ではない。`empirical-prompt-tuning` は upstream 不在（404）のため対象外とする。
- スキルは required と best-effort を分ける。**first-party（repo `skills/`）は必須**で、欠落・インストール後検証失敗があれば最後に `exit 1` する。**公開 third-party（`gws-*`, `grill-me`）は best-effort** で、取得失敗は skip して継続する（一過性のネットワーク失敗で SessionStart 全体を止めないため）。
- runner スキルが叩く CLI のうち、認証不要（`ghq`）または env 由来の認証で headless 完走できるもの（`codex`＝`CODEX_AUTH_JSON` から `~/.codex/auth.json` を materialize、`gemini`＝実行時 `GEMINI_API_KEY`）を best-effort で導入する。`gh`／`gh skill`・`gws`・`grok` は入手経路・OAuth headless 不可・契約必須のため自動導入対象外とし、各 runner の `SKILL.md` / docs-only manifest の手動セットアップに委ねる。
- フル 1Password 化: `OP_SERVICE_ACCOUNT_TOKEN` があれば `op` を best-effort 導入し（`OP_CLI_VERSION` で version 上書き可）、`op whoami` 確認後に `opmaterialize restore` を実行して、`~/.config/op/dotfiles.env`（`op://` 参照）・secret-backed file・private subagent（personal/biz/tech）を一括復元する。API キー（`GEMINI_API_KEY` 等）は 1Password に置き dotfiles.env に参照を書き、各 runner は `oprun` 経由で実行する（規約準拠）。トークン未設定・op 未導入時は skip し status に理由を残す。
- 実行結果は `$BOOTSTRAP_WEB_STATUS`（既定 `~/.cache/bootstrap-web/status.json`）に機械可読で書き、`overall_success`・`failure_stage`・`failure_reason`・`first_party_failed`・`third_party_installed`・`third_party_skipped`・`runner_cli_installed`・`runner_cli_skipped`・`onepassword` を残す。`chezmoi apply` 失敗等の早期致命終了でも `EXIT` trap が失敗ステータスを書く。サマリも標準出力へ出す（静かな成功・静かな部分失敗を作らない）。
- `.claude/hooks/session-start.sh` を SessionStart hook として `.claude/settings.json` に登録し、`CLAUDE_CODE_REMOTE=true` のときだけ `bootstrap-web` を実行する。
- chezmoi の用意は公式 installer を主経路とし、network policy 等で失敗した場合は warn を出してから go build へ切り替える。各経路は標準出力に観測ログを残す。
- 一時ディレクトリは登録制 + 単一の `EXIT` trap で、失敗・abort 時も後始末する。
- 1Password 由来の secret 実値・secret-backed file・private subagent（personal / biz / tech）はこの自動化の対象外とし、サインイン後の `opmaterialize restore` による手動復元を維持する。秘密は git に置かない。

ローカル / macOS の標準配備は従来どおり `gh skill install` と docs-only manifest を正本とする。本自動化は web セッション起動時の再現専用の例外である。

## Consequences

- web セッションでは起動時に環境が自動再現され、手動セットアップが不要になる。
- 規約（docs-only manifest / `gh skill` 標準）と `bootstrap-web` のスキルリストが二重管理になるため、スキル追加・削除時は両者を同期する必要がある。
- SessionStart hook を同期実行する場合、初回の chezmoi build 分だけセッション起動が遅くなる。レイテンシが問題なら async 化を検討する。
- `chezmoi apply --force` は、ハーネスが session 起動時に書き込む `~/.gitconfig` などの target も上書きする。hook の実行順序によってはハーネス提供の git identity を上書き／巻き戻すため、**bootstrap 後のコミットは dotfiles の git identity（`rmanzoku`）・署名設定で行われる**。web セッションでハーネス側の identity を保ちたい場合は、bootstrap から `.gitconfig` を除外するか、bootstrap 後に identity を復元する必要がある。この上書きは意識的な受容事項として扱う。
- third-party を best-effort にしたため、ネットワーク不調時は一部スキルが欠けたまま `overall_success=true` になりうる。欠落は status ファイルと標準出力サマリの `third_party_skipped` で観測する。
- フル 1Password 化（step 5）を web で有効にするには、(1) network policy で 1Password 配布元（`cache.agilebits.com` / `downloads.1password.com`）を許可、(2) `OP_SERVICE_ACCOUNT_TOKEN` を environment 変数に追加、(3) `GEMINI_API_KEY` 等を 1Password に保存し `~/.config/op/dotfiles.env` の `op://` 参照を Secrets Manifest に登録、の3点が必要。いずれか欠けると step 5 は skip される（`onepassword` に理由を記録）。2026-06-19 時点の制限ポリシーでは 1Password 配布元が 403 で遮断され op を導入できないため、この環境では未稼働。
- このリポジトリの管理責任は Codex が持つため、本 ADR と `AGENTS.md` の例外条項は Codex によるレビュー対象として扱う。
