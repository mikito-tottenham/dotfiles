---
title: "Reproduce Web Session Environment Via SessionStart Hook"
date: 2026-06-19
agent_model: "Claude Code"
status: accepted
updated_at: "2026-06-22"
updated_by: "Claude Code"
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
- runner スキルが叩く CLI を best-effort で導入する。いずれも headless 認証経路があるものに限る: `ghq`（認証不要、`go install`）、`codex`（`CODEX_AUTH_JSON`→`~/.codex/auth.json` materialize）、`gemini`（実行時 `GEMINI_API_KEY`）、`gh`（GitHub release、2.90+ で `gh skill` 標準搭載、認証 `GH_TOKEN`/`GITHUB_TOKEN`）、`gws`＝`google-workspace-cli`（GitHub release `v0.22.5` pin、`GWS_CLI_VERSION` 上書き可、認証は `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` が指す OAuth credential JSON＝`gws auth export --unmasked` 出力で非対話。複数 Google アカウントはアカウントごとに別 GCP プロジェクト＋別 OAuth クライアントで分離し、`~/.config/gws/accounts/<name>.json` に置いて `scripts/gws-as <name>` で切り替える）、`copilot`（npm `@github/copilot`、認証 `COPILOT_GITHUB_TOKEN`/`GH_TOKEN`/`GITHUB_TOKEN`、要 Copilot 契約）。トークン/クレデンシャル未設定時は導入だけ行い実行時認証が要る旨を warn する。認証材料（GitHub トークン・gws OAuth credential JSON）は 1Password に置き step 5 の `opmaterialize restore` で復元する想定。`grok`（xAI OAuth）・`soundcore`（対話ブラウザ必須）は headless 経路が無いため対象外。
- フル 1Password 化: **op の導入（token 非依存・`cache.agilebits.com` への network のみ）と `opmaterialize restore`（token 必須）を分離する**。`op` を best-effort 導入し（`OP_CLI_VERSION` で version 上書き可）、その後 `OP_SERVICE_ACCOUNT_TOKEN` が見えるときだけ `op whoami` 確認後に `opmaterialize restore` を実行して `~/.config/op/dotfiles.env`（`op://` 参照）・secret-backed file・private subagent（personal/biz/tech）を一括復元する。**environment 変数は Setup script（プロビジョニング）フェーズには注入されず Claude のセッション側にのみ入る**ため、Setup script から呼ぶと token が無く restore できない。そこでも op だけは導入しておき、restore は token の見えるセッションでの on-demand 実行（`opmaterialize restore`）か、dotfiles の SessionStart hook（セッション内で走るので token あり）に委ねる。`BOOTSTRAP_WEB_SKIP_OP=true` のときは op 導入はするが restore は決して行わない（Setup script 用。token 有無に依らず secret をスナップショットに焼き込まないことを保証）。API キー（`GEMINI_API_KEY` 等）は 1Password に置き dotfiles.env に参照を書き、各 runner は `oprun` 経由で実行する（規約準拠）。op 未導入時・token 未設定時・SKIP_OP 時は理由を status に残す。
- 実行結果は `$BOOTSTRAP_WEB_STATUS`（既定 `~/.cache/bootstrap-web/status.json`）に機械可読で書き、`overall_success`・`failure_stage`・`failure_reason`・`first_party_failed`・`third_party_installed`・`third_party_skipped`・`runner_cli_installed`・`runner_cli_skipped`・`onepassword` を残す。`chezmoi apply` 失敗等の早期致命終了でも `EXIT` trap が失敗ステータスを書く。サマリも標準出力へ出す（静かな成功・静かな部分失敗を作らない）。
- `.claude/hooks/session-start.sh` を SessionStart hook として `.claude/settings.json` に登録し、`CLAUDE_CODE_REMOTE=true` のときだけ `bootstrap-web` を実行する。この hook は **dotfiles リポジトリのセッションでのみ**走る（hook は repo scope のため）。
- dotfiles 以外のリポジトリ（workspace 等）のセッションでも再現したい場合は、environment の **Setup script**（repo 非依存・全セッション・キャッシュ対象）から dotfiles を clone して `BOOTSTRAP_WEB_SKIP_OP=true "$DOTFILES/scripts/bootstrap-web"` を実行する。Setup script はキャッシュ（スナップショット焼き込み）され、かつ environment 変数（token）が注入されないフェーズなので、ここでは **op 導入・CLI・chezmoi・skill の導入だけをキャッシュ**し、restore は行わない。secret の復元は token の見えるセッションでの on-demand `opmaterialize restore`（op は導入済み）に委ねる。dotfiles セッションは SessionStart hook がセッション内で走り token があるためフル restore される。Setup script は環境 UI に置く最小スニペット（clone → `gws-as` を PATH へ symlink → `BOOTSTRAP_WEB_SKIP_OP=true` で `bootstrap-web` 実行）に留め、実ロジックは git 管理の `bootstrap-web` に集約する。
- chezmoi の用意は公式 installer を主経路とし、network policy 等で失敗した場合は warn を出してから go build へ切り替える。各経路は標準出力に観測ログを残す。
- 一時ディレクトリは登録制 + 単一の `EXIT` trap で、失敗・abort 時も後始末する。
- 1Password 由来の secret 実値・secret-backed file・private subagent（personal / biz / tech）は **git に置かない**。これらの復元は step 5 の `opmaterialize restore` が担い、`OP_SERVICE_ACCOUNT_TOKEN`・op 導入・network 許可の3条件が揃えば**自動復元**、いずれか欠ければ status に理由を残して **skip し、op が使える環境での手動 `opmaterialize restore` に委ねる**。secret 実値そのものは常にこの自動化のリポジトリ管理対象外（1Password に置く）であり、自動化されるのは「restore の実行」だけである。

ローカル / macOS の標準配備は従来どおり `gh skill install` と docs-only manifest を正本とする。本自動化は web セッション起動時の再現専用の例外である。

## Consequences

- web セッションでは起動時に環境が自動再現され、手動セットアップが不要になる。
- 規約（docs-only manifest / `gh skill` 標準）と `bootstrap-web` のスキルリストが二重管理になるため、スキル追加・削除時は両者を同期する必要がある。
- SessionStart hook を同期実行する場合、初回の chezmoi build 分だけセッション起動が遅くなる。レイテンシが問題なら async 化を検討する。
- `chezmoi apply --force` は、ハーネスが session 起動時に書き込む `~/.gitconfig` などの target も上書きする。hook の実行順序によってはハーネス提供の git identity を上書き／巻き戻すため、**bootstrap 後のコミットは dotfiles の git identity（`mikito-tottenham`、2026-06-22 に `rmanzoku` から変更）・署名設定で行われる**。web セッションでハーネス側の identity を保ちたい場合は、bootstrap から `.gitconfig` を除外するか、bootstrap 後に identity を復元する必要がある。この上書きは意識的な受容事項として扱う。
- third-party を best-effort にしたため、ネットワーク不調時は一部スキルが欠けたまま `overall_success=true` になりうる。欠落は status ファイルと標準出力サマリの `third_party_skipped` で観測する。
- フル 1Password 化（step 5）を web で有効にするには、(1) network policy で 1Password 配布元（`cache.agilebits.com` / `downloads.1password.com`）を許可、(2) `OP_SERVICE_ACCOUNT_TOKEN` を environment 変数に追加、(3) `GEMINI_API_KEY` 等を 1Password に保存し `~/.config/op/dotfiles.env` の `op://` 参照を Secrets Manifest に登録、の3点が必要。op は実行時に 1Password API（`*.1password.com`）へも到達する必要があるため、network policy にこのドメインも含める。いずれか欠けると step 5 は skip される（`onepassword` に理由を記録）。2026-06-19 時点では既定の制限ポリシーで 1Password 配布元が 403 遮断され未稼働だったが、同日 network policy に上記ドメインを追加して `cache.agilebits.com` の 200 到達を実測で確認し、稼働対象になった。
- web セッションのコンテナは直接の外部 egress を持たず、通信は Claude Code 管理 proxy 経由になる（`CLAUDE_CODE_PROXY_RESOLVES_HOSTS`）。一般 HTTP では proxy が `api.openai.com` / `chatgpt.com` を拒否する（2026-06-22 実測: proxy 経由で 403、proxy を外す（`--noproxy '*'`）と DNS 解決自体が不可）。**ただし** Claude Code の `openai-codex` プラグインの companion runtime（`CODEX_COMPANION_SESSION_ID`）経由では Codex CLI（0.141.0、ChatGPT ログイン済み）が実行でき、現に web セッション内で Codex を呼んでレビュー・調査を実行できることを実測で確認した（`codex exec` 成功）。したがって **素のコンテナ外部 egress 経路では openai に到達不可だが、openai-codex プラグイン companion runtime 経由なら Codex CLI は実行可能**。プラグインを介さない直接の `api.openai.com` 通信に依存する処理は依然不可。`dot_*`（Codex 管理対象）の変更を web で Codex に委譲する場合は、この plugin proxy 経路が有効なセッションに限る。
- このリポジトリの管理責任は Codex が持つため、本 ADR と `AGENTS.md` の例外条項は Codex によるレビュー対象として扱う。

## 追記 (2026-06-22, Claude Code / claude-sonnet-4-6)

- 当初は「web では `api.openai.com` / `chatgpt.com` が 403 で Codex CLI 実行不可・web セッション内で Codex に委譲できない」と記していたが、web セッション内での実測で訂正した。コンテナ直接 egress は遮断（proxy 経由 403 / proxy なしで DNS 解決不可）だが、`openai-codex` プラグイン companion runtime 経由では `codex exec` が成功し、本セッションでも Codex によるレビューを複数回実行できた。
- 根拠 env（値は記録しない）: `CLAUDE_CODE_PROXY_RESOLVES_HOSTS`、`CODEX_COMPANION_SESSION_ID`、`CLAUDE_PLUGIN_DATA`、PATH 上の `openai-codex` プラグイン。
- Codex 自身による独立実測でも同結論（plugin proxy 経由で実行可能）。本訂正は Codex レビュー対象。
