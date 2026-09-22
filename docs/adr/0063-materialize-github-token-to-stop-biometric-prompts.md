---
title: "GitHub token を materialize して Touch ID の連続要求を止める（ghrun）"
date: 2026-09-21
agent_model: "Claude Opus 5 (claude-opus-5)"
status: accepted
supersedes_in_part: ["ADR 0036", "ADR 0055"]
updated_at: 2026-09-22
updated_by_agent_model: "Claude Opus 5 (claude-opus-5)"
---

# ADR 0063: GitHub token を materialize して Touch ID の連続要求を止める（ghrun）

## Context

ADR-0036 / ADR-0055 により、`gh` は `alias gh='oprun gh'`、git の HTTPS は credential helper
`!OPRUN_NO_MASKING=1 oprun gh auth git-credential` を通じて、呼ばれるたびに `op run` で
1Password から `GH_TOKEN` を受け取っていた。共通ルールも Agent に `oprun gh ...` の明示を求めていた。

この構成では作業のたびに Touch ID を求められ、ユーザーから「指紋認証なしで使えるようにしてほしい」
という要望が出た（2026-09-21）。原因は 1Password CLI の認可モデルにある。

- 認可は **tty 単位のセッション**で、**10 分無操作で失効**し、ハード上限は 12 時間。
  1Password アプリがロックすると全認可が即失効する。
- この間隔は**設定では変更できない**（[1Password app integration security](https://www.1password.dev/cli/app-integration-security/)）。
- Claude Code / Codex の Bash は呼び出しごとに新しいプロセスで tty も持たないため、Agent の
  `oprun gh` や `git push` はほぼ毎回新しい認可になる。アプリがロック中なら
  `account is not signed in` で即失敗する（2026-09-21 実測）。
- 最大の発生源は ADR-0049 の launchd `repo-sync` だった。1 時間ごとに加え、スリープ復帰や
  Wi-Fi 切替でも起動し、GitHub の 15 リポジトリを HTTPS で `git fetch` する。1 件ごとに credential
  helper が `op` を呼ぶため、ログには約 60 秒間隔の `fetch 失敗` が並んでいた
  （例: 2026-09-20 10:33:36 → 10:34:40 → 10:35:42 → 10:36:44）。Touch ID 待ちのタイムアウトであり、
  1 回の実行で最大 15 回のプロンプトが出ていたことになる。「作業を始めると指紋を求められる」という
  体感はこれと一致する。

1Password 側の設定変更では解決しない。自動ロック（当時 60 分）を緩めても 10 分ルールは残る。
生体認証を完全に外す公式経路は Service Account トークン（`OP_SERVICE_ACCOUNT_TOKEN`）で、クラウド環境では
すでに使っている（ADR-0045）。ただしローカルで使うには、vault 全体を読めるトークンを 1Password の外
（ファイルや Keychain）に常駐させる必要がある。

一方、「1Password を正本とし、実値は再生成可能な派生物としてローカルに置く」運用はすでに確立していた。

- ADR-0036 は secret-backed file を `opmaterialize` で復元する経路を定めており、gws の OAuth 認証情報
  （4 アカウント分の `credentials.json` / `client_secret.json`）はディスク上に materialize 済み。
- rmanzoku/taskell-management も `op run` は配布時の 1 回だけにし、日常は `.env` や設定ファイルから読む。

## Decision

- **GitHub の token だけ materialize し、`op` の呼び出しから外す。** 新しいラッパー
  `~/.local/bin/ghrun` は `~/.config/op/injected/github.env`（0600）を読んで `GH_TOKEN` /
  `GITHUB_TOKEN` を export し、コマンドを exec する。1Password には触れない。
- **`ghrun --refresh` を唯一の生成経路とする。** 内部で `OPRUN_NO_MASKING=1 oprun` を使って
  `~/.config/op/dotfiles.env` の既存 `op://` reference を解決し、一時ファイル経由で原子的に置き換える。
  Touch ID はこの 1 回だけになる。
- **消費側を `ghrun` に切り替える。** `alias gh='ghrun gh'`、credential helper は
  `!ghrun gh auth git-credential`、共通ルールで Agent に求める明示呼び出しも `ghrun gh ...` にする。
- **暗黙の fallback は入れない。** ファイルが無ければ `ghrun` は exit 66 で `ghrun --refresh` を案内して
  失敗する。401 を検知して自動で `op` に取りに行く処理も入れない（主経路の失敗を隠すため）。
- 共通ルールの「平文の token file は不可」に例外を明記する。1Password を正本とし 1 コマンドで
  再生成できる materialized file は禁止対象外とする。禁止しているのは 1Password を正本としない
  独自ストア（`gh auth login` の keyring、手で作った token file など）である。

### 採用しなかった案

- **secrets-manifest への登録**: `opmaterialize add` は document 型専用で、field 型 manifest には
  1Password 側の手作業が要る。さらに `dotfiles.env` の `op://` reference と値が二重管理になり、
  ローテーション時に更新漏れが起きる。`ghrun --refresh` なら正本は 1 箇所のまま、新しいマシンでも
  コマンド 1 つで再現できる。
- **ローカルでも Service Account トークンを使う**: Touch ID は完全になくなるが、`Dotfiles Secrets` vault
  全体を読めるトークンをディスクに常駐させることになり、GitHub token 1 本を置くより影響範囲が広い。
- **git-credential-cache（メモリに 12 時間）**: ディスクに書かない点は優れるが、Touch ID は
  ゼロにならず、Agent の `gh` 直叩き（別プロセス）は救えない。
- **`oprun` 自体を全 secret のキャッシュにする**: 影響は最大だが、Slack / Gemini / Copilot の token
  まで常駐させることになり、要望の範囲を超える。必要になったら同じ仕組みを個別に広げる。

## Consequences

- `gh` と git の GitHub 通信は Touch ID なしで動く。Agent の Bash からも、1Password がロック中でも動く。
- **トレードオフ**: GitHub token がディスク上（0600、同一ユーザーの全プロセスから読める）に常駐する。
  gws の認証情報と同じ水準だが、ADR-0055 にあった「1Password がロック中は GitHub 操作ができない」
  という保護は失われる。
- 1Password 側で token をローテートすると `github.env` が stale になり、`gh` / `git push` が 401 になる。
  そのときはユーザーが通常のターミナルで `ghrun --refresh` を実行する。Agent からは実行しない
  （tty が無いと認可できず、繰り返しの承認要求は安定した復旧経路にならない）。
- 新しいマシンでは `opmaterialize restore` の後に `ghrun --refresh` を 1 回実行する（README に追記）。
- クラウドでも `bootstrap-web` の `chezmoi apply --force` で `~/.gitconfig` が `ghrun` を使う helper に揃う。
  そこで `opmaterialize restore` の直後に `ghrun --refresh` を実行して `github.env` を生成する（service account
  認証なので Touch ID は不要）。失敗したら status を `restored-without-github-token: ...` にして警告する。
  セッション repo の git は harness の proxy 経由なので影響しない。`verify-cloud-parity` の対象 CLI に `ghrun` を加える。
- `COPILOT_GITHUB_TOKEN`、Slack、Gemini は引き続き `oprun` 経由のため、それらを使う操作では
  Touch ID が残る。

## Verification

2026-09-21 に以下を実施した。

- `shellcheck`（`ghrun` / `oprun` / `opmaterialize`）、`git diff --check`、`scripts/chezmoi-drift --check-ignore`: 問題なし
- 偽の `oprun` を使ったテスト 11 件（1Password には触れない）: すべて通過。ファイル欠如時の exit 66 と案内、
  `--refresh` の生成と 0600、一時ファイルが残らないこと、子プロセスへの export、`GITHUB_TOKEN` の既定値、
  不正文字 token の拒否と既存ファイルの保全、`git credential fill` が本物の `gh auth git-credential` 経由で
  token を返すこと。
- 実機: `chezmoi apply ~/.local/bin/ghrun ~/.gitconfig` → ユーザーのターミナルで `ghrun --refresh`
  （Touch ID 1 回）→ `op whoami` が `account is not signed in` を返す Agent セッションから、private
  リポジトリ 2 件に `GIT_TERMINAL_PROMPT=0 git ls-remote` が約 0.9 秒で成功した。`github.env` が無い状態では
  credential helper が約 0.5 秒で案内付きの失敗を返し、Touch ID 待ちは発生しなかった。
- `~/.zshrc`: source 側の `source <(entire completion zsh)` を `entire` がある場合だけ読むようにガードしてから
  `chezmoi apply ~/.zshrc` した（`entire` 未インストールのマシンでシェル起動ごとにエラーになるのを避けるため）。
  新しい対話 zsh が rc=0・stderr 空で起動し、`type gh` が `ghrun gh` の alias、`gh auth status` の
  active が `GH_TOKEN` になることを確認した。
- クラウド: `bootstrap-web` から `ensure_onepassword` を抜き出し、偽の `op` / `opmaterialize` / `oprun` で実行した。
  restore と refresh が成功すると status は `restored` で `github.env` が 0600 で生成され、refresh が失敗すると
  status が `restored-without-github-token: ghrun --refresh 失敗` になり警告が出た（2026-09-22）。
