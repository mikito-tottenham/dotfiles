---
title: "Extend Cloud Parity To Local Auth Paths"
date: 2026-09-29
agent_model: "Claude Opus 5.5 (claude-opus-5-5)"
status: proposed
related_adr: ["0045", "0058", "0061", "0062", "0063"]
---

# ADR 0068: Extend Cloud Parity To Local Auth Paths

## Context

ADR-0045 / ADR-0058 で、クラウドの ephemeral セッション（Claude Code on the web / Codex cloud）を
`scripts/bootstrap-web` で再現し、`scripts/verify-cloud-parity` で差分を検査する形にした。
その後ローカルでは認証経路が増えた。

- GitHub token を `ghrun --refresh` で materialize する（ADR-0063、2026-09-21）
- Slack を `oprun slack-account <profile>` で操作する（ADR-0061、2026-09-25 accepted）
- chatwork MCP を `oprun` 経由で起動し、token を 1Password から解決する（ADR-0062 決定 8、2026-09-25）

2026-09-29 に、ローカルの認証経路とクラウドの再現機構を突き合わせた（作業 artifact:
`~/Claude/.context/2026-09-29-cloud-auth-parity/01-gap-analysis.md`）。主な差分は次のとおり。

1. **on-demand 復元の手順に `ghrun --refresh` が無い。** dotfiles 以外のセッションでは
   `opmaterialize restore` だけを案内していたため、GitHub token が生成されなかった。
   `ghrun --refresh` まで走るのは dotfiles セッションの SessionStart hook だけだった。
2. **allowlist が 1Password 系だけ。** token を復元しても Slack / Chatwork / Money Forward（mfc_ca）/
   freee / Copilot には通信できない。Claude Code on the web の既定リストにこれらは無い
   （[Default allowed domains](https://code.claude.com/docs/en/cloud-environments#default-allowed-domains)）。
   Codex cloud の `Common dependencies` には `googleapis.com` も無く、agent phase の gws が届かない
   （[Common dependencies](https://learn.chatgpt.com/docs/cloud/internet-access#common-dependencies)）。
3. **chatwork MCP を登録できない。** `bootstrap-web` の `mcp_servers` は `name|transport|url` の
   http 専用書式だった。
4. **検査が粗い。** `verify-cloud-parity` は `github.env` の有無を見ず、gws は `credentials.json` の
   件数だけを数え（空 dir や `client_secret.json` の欠けを見逃す）、`dotfiles.env` は存在だけを見ていた。
   1Password 側の `dotfiles.env` が古いと Slack / Chatwork のキーが欠けても `OK` になる。
   `slack-account` などの CLI も検査対象に無かった。
5. **文書の誤り。** claude.ai コネクタを「対話 OAuth 必須のため対象外」としていたが、公式には
   クラウドホストがセッションへ渡し、通信も Anthropic 経由で allowlist も要らない
   （[Network access](https://code.claude.com/docs/en/cloud-environments#network-access) の Note、
   [MCP](https://code.claude.com/docs/en/mcp)）。Setup script のキャッシュが約 7 日で失効する点も
   書かれていなかった（[Environment caching](https://code.claude.com/docs/en/cloud-environments#environment-caching)）。

## Decision

1. **on-demand 復元は `opmaterialize restore` → `ghrun --refresh` の 2 手順にする。** restore より前に
   起動した stdio MCP（chatwork）は token を解決できずに失敗しているため、restore の後に `/mcp` で
   再接続する。`docs/web-session-runner-setup.md` の on-demand・parity 検証・動作確認の各節と、
   `bootstrap-web` の完了メッセージをそろえる。`bootstrap-web` の再実行を正規手順にする案は
   本 ADR では採らず、手順に 1 行足す最小の変更に留める。
2. **allowlist の運用契約を更新する。** 列挙の正本は `docs/web-session-runner-setup.md` とする。
   - Claude Code on the web: 既定リスト（「Also include default list of common package managers」）を
     必須とする。gws の `*.googleapis.com` / `accounts.google.com`、`registry.npmjs.org`、
     `proxy.golang.org`、`api.github.com` がそこに入るため。追加するのは `slack.com`、`files.slack.com`、
     `api.chatwork.com`、`alpha.mcp.developers.biz.moneyforward.com`、`mcp.freee.co.jp`、
     `*.githubcopilot.com`。先頭の `*.` はサブドメインに一致する（公式）。
   - Codex cloud: Additional に `slack.com`、`files.slack.com`、`googleapis.com`、`githubcopilot.com`
     を足す。Codex の文書はワイルドカードの書き方を定めていないため、preset と同じ裸のドメインで書く
     （サブドメインに効くかは推定）。Codex 側の mfc_ca（beta URL）を使う場合だけ
     `beta.mcp.developers.biz.moneyforward.com` を足す。
3. **`mcp_servers` を stdio に対応させ、chatwork を加える。** 書式は `name|http|url` と
   `name|stdio|command [args...]|KEY=VALUE ...`。chatwork はローカルの登録（ADR-0062 決定 8）と同じ
   `$HOME/.local/bin/oprun npx -y @chatwork/mcp-server`、env `OPRUN_NO_MASKING=1` で登録する。
   `claude mcp add` の `-e` は可変長引数なので、`<name> -e KEY=VALUE -- <command>` の順で渡す。
   `verify-cloud-parity` の `eval` 抽出と `${entry%%|*}` の name 抽出はそのまま使える。
4. **`verify-cloud-parity` の検査を増やす。**
   - `~/.config/op/injected/github.env` の有無（無ければ `ghrun --refresh 未実行?`）
   - gws は `client_secret.json` と `credentials.json` がそろったプロファイルを名前つきで `OK` にし、
     1 件も無ければ `MISSING`。期待するプロファイル名は repo に持たない（ADR-0048 / ADR-0060）。
     片方しか無い dir や空 dir は数えるだけで `MISSING` にしない（ローカルには旧レイアウトの残骸 dir が
     あり、`MISSING` にすると検証が常に失敗するため）
   - `dotfiles.env` のキー名は検査しない。`dot_config/private_op/dotfiles.env.example` は書式例で、
     使っていないキーを含み、実際に使うキーの一部しか載っていないため、必須キーの一覧として扱えない。
     1Password 側の `dotfiles.env` が古いかどうかは、ローカルの `opmaterialize diff` で確かめる
   - `CLI_BASE` に `slack-account` / `slack-fetch-message` / `calendar-acl` を加える
5. **文書を直す。** claude.ai コネクタは「クラウドホストが渡すので script の再現対象外（不要）」と書く。
   キャッシュの約 7 日失効を runbook に追記する。
6. **3 箇所同期**（AGENTS.md）に従い、`docs/skills-install-manifest.md` に CLI と MCP の節を置く。
7. **Codex CLI のクラウド認証は `CODEX_AUTH_JSON`（environment 変数に置く平文の `auth.json`）を維持する。**
   共通ルールの「認証は例外なく 1Password 経由」に対する例外として、2026-09-29 にユーザーが選んだ。
   動作実績のある経路を残すためで、代わりに次のリスクを受け入れる: environment を編集できる人に値が
   見える、ChatGPT ログインの refresh token をローカルと共有するため片方の更新でもう片方が失効しうる。
   `auth.json` を Secrets Manifest に載せる案と、OpenAI API キーを `oprun codex` で使う案は採らない。
   runbook の Environment variables 節に例外であることを書く。

## 本 ADR で決めないこと

- **Gemini の認証方式**（`oauth-personal` と API キーの切り替え）。他セッションの未 commit 変更と
  衝突しうるため、先にどちらを採るかを決める必要がある。
- **Grok（Hermes）。** headless の認証経路が無い。
- **calendar-acl の `policy.yaml` と PyYAML。** CLI の有無は検査に入れたが、policy の 1Password 登録と
  PyYAML の導入は別件とする。
- **SSH。** git は https と GitHub proxy で足りる。1Password SSH agent はクラウドで使えない。
- **`opmaterialize restore` の脆さ**（1 行の失敗で全体が止まる）。挙動の変更は fallback 禁止ルールとの
  兼ね合いがあるため、別に判断する。
- **`dot_claude/settings.json` の user scope SessionStart hook。** 2026-06-25（`7bbee54`）に全 repo の
  クラウドセッションで restore するために入れた hook だが、remote で `opmaterialize restore` だけを実行し、
  ADR-0063 以降の標準である `ghrun --refresh` を含まない。`... && opmaterialize restore >/dev/null 2>&1
  && ghrun --refresh >/dev/null 2>&1 || true` にする 1 行の変更を提案したが、Claude Code の hook 設定の
  書き換えにあたるため auto mode に拒否された（2026-09-29）。ユーザーの判断を待つ。VM 内の
  `~/.claude/settings.json` の hook がクラウドセッションで実際に発火するかも未確認で、発火しない場合は
  on-demand 手順（Decision 1）で補う。
- 1Password 側の作業（`dotfiles.env` の同期、Secrets Manifest に無い gws プロファイルの登録など）。
  Agent から `opmaterialize add` を実行すると、ユーザーがチャットで承認していても auto mode classifier に
  Secret-Store Writes として拒否される（2026-09-29 実測）。1Password への登録・更新はユーザーがローカルの
  ターミナルで行う。同日の `opmaterialize diff` では、`dotfiles.env` と gws `taskell/credentials.json` が
  `changed`、`yoake/` の 2 ファイルが `missing`（ローカルは空 dir）、`ges-claude` は manifest に行が無かった。

## Consequences

- Claude Code on the web の environment に allowlist を入れれば、restore 後に Slack / Chatwork /
  mfc_ca / freee / Copilot へ通信できる前提がそろう。Codex cloud も同様に agent phase から gws と
  Slack を使える。いずれも UI 側の設定が要る。
- allowlist を広げた分だけ、prompt injection や exfiltration で使える経路が増える。必要な runner /
  MCP のホストだけを足し、増減したら runbook の一覧も更新する。
- chatwork MCP は起動のたびに `op run` を通る。クラウドでは service account 認証なので Touch ID は
  要らないが、restore 前の起動は失敗する。
- `verify-cloud-parity` の検査行が増える。ローカル（2026-09-29）では追加した行はすべて `OK` で、
  `MISSING` は変更前からある 3 件（codex 側 skill 2 件と plugin 1 件）のまま。
- 3 箇所同期の対象に MCP の stdio 書式が加わる。

## 未検証事項

1. **クラウドでの GitHub 認証の干渉。** chezmoi が配る `~/.gitconfig` は既存の helper を消して
   `!ghrun gh auth git-credential` だけにする。これがハーネスの scoped credential を壊さないか、
   `ghrun gh` の実 token が GitHub proxy の `proxy-injected` と衝突しないかは実測していない
   （ADR-0063 のクラウド検証は偽の op だけだった）。
2. **VM 内で `claude mcp add --scope user` した MCP がセッションで読まれるか。** 公式の
   "What carries over" は、ローカルの user scope が引き継がれないことしか述べていない。Setup script
   で登録した場合とセッション中に登録した場合で結果が変わるかも未確認。
3. **`codex@openai-codex` plugin の companion 経路が今も使えるか。** 公式は「クラウドは plugin を
   入れない」としており、ADR-0045（2026-06-22 実測）と食い違う。

## push 後にクラウドで行う検証

1. Claude Code on the web の、実際に使う environment の Network access に runbook の allowlist を入れ、
   既定リストを有効にする。Setup script を 1 文字編集してキャッシュを再ビルドさせる。
2. dotfiles 以外の repo の新しいセッションで次を実行する。

   ```bash
   BOOTSTRAP_REPO_DIR=/opt/dotfiles /opt/dotfiles/scripts/verify-cloud-parity   # restore 前: github.env / gws が MISSING
   opmaterialize restore
   ghrun --refresh
   BOOTSTRAP_REPO_DIR=/opt/dotfiles /opt/dotfiles/scripts/verify-cloud-parity   # 上の行が OK になる
   ```

3. `/mcp` で chatwork を再接続し、`get_me` が通るかを見る。`claude mcp list` で mfc_ca と chatwork が
   出るか（未検証事項 2）。
4. `oprun slack-account <profile> auth status` が `auth.test ok` を返すか。
5. 未検証事項 1: `git config --show-origin --get-all credential.https://github.com.helper`、
   `[ "${GH_TOKEN:-}" = proxy-injected ] && echo placeholder || echo other`（値は出さない）、
   session ブランチへの push を確認する。
6. Codex cloud: Additional allowed domains を更新した environment で restore → `ghrun --refresh` →
   `gws-account <profile> drive files list` と `oprun slack-account <profile> auth status`。
   裸のドメインがサブドメインに効くかもここで確かめる。
7. 未検証事項 3: companion runtime（`CODEX_COMPANION_SESSION_ID` が設定されているか）と
   `codex exec` の可否。

## environment UI の反映状況（2026-09-29）

ユーザーの承認を得て、Agent がブラウザで次のとおり変更した。

- Claude Code on the web: `My claude` と `Default` の allowed domains に Decision 2 の 6 件を追加した
  （既存の OpenAI 系 3 件と 1Password 系 3 件は残した）。どちらも既定リストは有効のまま。`Default` は
  Environment variables が空なので、`OP_SERVICE_ACCOUNT_TOKEN` を入れるまで restore できない。
- Codex cloud: `mikito-tottenham/dotfiles` の Additional allowed domains に Decision 2 の 4 件を追加した。
  この environment は Environment variables と Secrets が空で、`OP_SERVICE_ACCOUNT_TOKEN` が無いため
  restore できない。`mikito-tottenham/twin` は Agent internet access が Off で Setup script も Automatic の
  ため変更していない（許可ドメインの追加には internet access を On にする判断が要る）。
- token の値の入力は Agent が行わない。environment 変数の追加はユーザーが行う。

## 検証（ローカル, 2026-09-29）

- `bash -n` と `shellcheck -S warning`（`bootstrap-web` / `verify-cloud-parity`）: 警告なし
- `verify-cloud-parity`: 変更前 `OK=86 / MISSING=3 / N/A=3`（total 92）→ 変更後
  `OK=94 / MISSING=3 / N/A=3`（total 100）。`MISSING` は変更前と同じ 3 件で、追加した `github.env`、
  gws 4 プロファイル、chatwork、CLI 3 件は `OK`。`--json` は JSON として parse でき、出力に secret の
  値は含まれない
- 空の `HOME` と `CLAUDE_CODE_REMOTE=true` で疑似クラウドを作り、`github.env` 無しが
  `ghrun --refresh 未実行?`、MCP 未登録が `MISSING` になり、両ファイルのそろった gws プロファイルだけが
  名前つきで `OK` になる（片方だけの dir は数えない）ことを確認した
- `bootstrap-web` の `mcp_servers` を `verify-cloud-parity` と同じ `eval` で抽出し、name が
  `mfc_ca` / `chatwork` になることを確認した
- `ensure_mcp_servers` を一時 `HOME` で 2 回実行し、1 回目で登録、2 回目は既存で skip になること、
  登録内容（type=stdio、command、args、env のキー）がローカルの `~/.claude.json` の chatwork と
  同じ形になることを確認した
