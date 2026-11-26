---
title: "Chatwork と Slack の token を taskell-management の配布方式にそろえて Touch ID を止める"
date: 2026-11-26
agent_model: "Claude Opus 5.5 (claude-opus-5-5)"
status: accepted
supersedes_in_part: ["ADR 0061", "ADR 0062", "ADR 0068", "ADR 0081"]
updated_at: 2026-11-26
updated_by_agent_model: "Claude Fable 5.2 (claude-fable-5-2)"
---

# ADR 0082: Chatwork と Slack の token を taskell-management の配布方式にそろえて Touch ID を止める

## Context

2026-11-26、ユーザーから「アクセスリクエストの指紋認証が多すぎる」と指摘があった。ADR-0063 で GitHub の
token は対象から外したが、まだ次の経路が呼ばれるたびに `op run` を通っていた。

- **Chatwork MCP（Claude Code）**: ADR-0062 決定 8 で `~/.claude.json` の user スコープを
  `oprun npx -y @chatwork/mcp-server` にしたため、Claude Code のセッションを開くたびに `op run` が走る。
- **Chatwork MCP（Codex）**: ADR-0081 で Codex にも同じ `oprun` 起動を登録したため、Codex を起動するたび
  （`codex exec` による委譲を含む）に `op run` が走る。
- **Slack（`oprun slack-account <profile> ...`）**: Agent が 1 回呼ぶごとに `op run` が走る。

1Password CLI の認可は tty 単位で、10 分無操作で失効する（設定では変更できない。ADR-0063）。Agent の
Bash や MCP の起動は tty を持たないため、ほぼ毎回新しい認可になり、そのたびに Touch ID を求められていた。

一方、taskell-management（Taskell の経営管理リポジトリ）の ADR-0060 決定 5 は、Chatwork の token を
**1Password を正本とし、`op run` を 1 回だけ通して各クライアントの設定へ配る**方式を定めている
（`op run --env-file="$HOME/.config/op/dotfiles.env" -- python3 bin/sync-mcp-secrets.py`）。配布先は
repo の `.env`、Claude Desktop の `claude_desktop_config.json`、`~/.claude.json` の user スコープだった。
dotfiles 側（ADR-0062）はこれを「平文 token」として `oprun` 起動に置き換えていた。そのため 2 つの方式が
互いの設定を上書きし合っていた。実際、ADR-0062 で 9/25 に `oprun` へ切り替えた Desktop の設定は、
配布スクリプトの再実行で token を直接書いた形に戻っていた（2026-11-26 確認）。

ユーザーの指示は「全部（taskell-management の）方式でそろえて」だった。

## Decision

- **Chatwork（Claude Code・Claude Desktop）は taskell-management の `bin/sync-mcp-secrets.py` を唯一の
  配布経路とする。** 配布スクリプトには手を入れず、そのまま使う（ユーザー指示。いったん配布先に Codex を
  加えた taskell-ai/taskell-management#546 は #547 で取り消した）。
- **Codex の Chatwork は dotfiles の `codex-chatwork-sync` で配る。** 配布スクリプトの対象に Codex が
  無いため、同じ考え方（`op run` を 1 回だけ通して設定へ書く）の小さなスクリプトを dotfiles 側に置く。
  `oprun` で token を解決し、`codex mcp add chatwork --env CHATWORK_API_TOKEN=... -- npx -y @chatwork/mcp-server`
  で `~/.codex/config.toml` へ登録し直す。Claude Code・Claude Desktop・Codex のどれも、起動時には
  1Password を呼ばない。
  - dotfiles の Codex 初期設定 template（`dot_codex/create_private_config.toml.tmpl`）から chatwork を外す。
    token を含む登録は template に書けないため、`codex-chatwork-sync` に任せる。
  - Chatwork の token を配る経路は 2 本になる。ローテート時は両方を実行する。
  - クラウド（`bootstrap-web`）は `oprun` 起動のまま変えない。service account 認証なので Touch ID が出ず、
    クラウドに taskell-management の checkout がある保証も無いため。
- **Slack も同じ考え方にそろえ、token を 1 回だけ配って普段はそこから読む。** `slack-account --refresh` が
  `oprun` を 1 回通して `~/.config/op/injected/slack.env`（0600）を原子的に書き換える。`slack-account` は
  token を「環境変数 `SLACK_<PROFILE>_TOKEN` → `slack.env`」の順で探し、先に見つかった方だけを使う。
  - 環境変数を優先するのは、クラウドや明示的な `oprun slack-account ...` を壊さないため。どちらにも無ければ
    exit 1 で `--refresh` を案内する。401 を検知して 1Password へ取りに行く処理は入れない（ADR-0063 と同じく、
    主経路の失敗を隠す暗黙 fallback を作らない）。
  - `--refresh` と `codex-chatwork-sync` は Agent から実行しない。tty の無い環境では認可が安定しないため、
    ユーザーが通常のターミナルで実行する（`ghrun --refresh` と同じ扱い）。
- `op-cli-runner` の preflight（`auth_preflight.py`）は、`slack.env` があれば `slack-account <p> auth status` を
  既定で実行する（1Password を呼ばない）。`slack.env` が無いときだけ、従来どおり `--with-op` で `oprun` を使う。

### 採用しなかった案

- **dotfiles 側で wrapper を作り、chatwork の token を `~/.config/op/injected/` から読む（ghrun 型）**:
  設定ファイルに token を書かずに済む利点がある。ただ、taskell-management の配布スクリプトと別の経路になり、
  2 つの方式が上書きし合う状態が残る。ユーザーは配布方式にそろえることを選んだ。
- **ローカルでも Service Account トークンを使う**: ADR-0063 と同じ理由で採らない。

## Consequences

- Claude Code や Codex のセッションを開いても、Slack を呼んでも、Touch ID は出ない。Touch ID が要るのは、
  初回と token のローテート後に、配布スクリプト・`codex-chatwork-sync`・`slack-account --refresh` を
  実行するときだけになる。
- **トレードオフ**: Chatwork の token は `~/.claude.json`・`claude_desktop_config.json`・`~/.codex/config.toml`・
  taskell-management の `.env` に直接書かれる（taskell-management ADR-0060 が受け入れている扱い）。Slack の
  token は `slack.env`（0600）に置かれる。どちらも同じユーザーのプロセスからは読める。ADR-0062 決定 8 が
  目的にしていた「設定ファイルに平文 token を置かない」は、Chatwork については取り下げる。
- 1Password 側で token をローテートしたら、Chatwork は配布スクリプトと `codex-chatwork-sync` の両方、
  Slack は `slack-account --refresh` を再実行する。
  再実行を忘れると古い token が残り、401 / `invalid_auth` になる。
- Gemini（`oprun gemini`）と Copilot（`COPILOT_GITHUB_TOKEN`）は引き続き `oprun` を通るため、それらを使うと
  Touch ID が出る。利用頻度が低いため今回は対象外とした。
- 新しいマシンでは、`ghrun --refresh` に加えて `slack-account --refresh`・配布スクリプト・
  `codex-chatwork-sync` を 1 回ずつ実行する。
- taskell-management の project 設定（`.codex/config.toml`）は chatwork を `oprun` 経由で起動する
  （taskell-ai/taskell-management#545）。project 設定は user 設定より優先されるため、そのリポジトリで
  Codex を起動したときは、引き続き Touch ID を求められる。ここは taskell-management 側の設定であり、
  この ADR では変えていない。

## Verification

2026-11-26 に以下を実施した。

- 偽の `oprun` を使った `slack-account` のテスト 12 件（1Password には触れない）: すべて通過。`--refresh` による
  生成と 0600、出力に token が出ないこと、一時ファイルが残らないこと、不正な token や `op` の失敗では既存ファイルを
  変えないこと、ファイルからの読み込み（user / bot）、環境変数の優先、`op://` の拒否、未設定時に `--refresh` を
  案内して exit 1 になること。
- `codex-chatwork-sync`: 偽の `oprun` と隔離した `CODEX_HOME`（`~/.codex/config.toml` の写し）で 8 項目を
  確認した。chatwork が `command = "npx"` と `env.CHATWORK_API_TOKEN` になること、再実行で token が
  置き換わること、`op` の失敗・`op://` のままの値・空の値では既存の登録を変えないこと、出力に token が
  出ないこと、ほかの設定が残ること。`shellcheck` は問題なし。
- 実機: ユーザーが通常のターミナルで配布を実行したあと、偽の `op` を PATH の先頭に置いた状態で
  `slack-account taskell|twin auth status` と `claude mcp get chatwork`（Connected）が通り、`op` の呼び出しが
  0 回であることを確認した。Claude Code・Claude Desktop・Codex・taskell-management の `.env` の token が
  同じ値であることをハッシュで照合した。
