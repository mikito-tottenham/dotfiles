---
title: "Cloud Session Runner & 1Password Setup Runbook"
updated_at: 2026-09-01
---

# Cloud Session Runner & 1Password Setup Runbook

クラウドの ephemeral セッションで、runner CLI（codex / gemini / ghq / gh / gws / copilot /
jq / rg）と 1Password 由来の secret を再現するための運用手順。対象は
**Claude Code on the web** と **Codex cloud** の 2 つ。設計判断の正本は ADR-0045 / ADR-0058、
本書はそれを「迷わず実行する」ための手順書。

2 つのクラウドは env / secret の注入タイミングが逆なので、environment 設定は流用せず
それぞれの節に従うこと。再現差分の確認は `scripts/verify-cloud-parity` で行う。

## 全体像

クラウドセッションは毎回まっさらな VM で起動し、リポジトリを clone し直す。永続するのは
git に push した内容だけ。そこで以下の3層で環境を再現する（**Claude Code on the web** の場合。
Codex cloud には SessionStart hook 相当が無いため Setup script と on-demand restore の 2 層になる）。

| 層 | 適用範囲 | キャッシュ | secret 復元 | 設定場所 |
| :-- | :-- | :-- | :-- | :-- |
| **Setup script** | 全リポジトリ | される | しない（op 導入まで） | environment UI |
| **SessionStart hook** | dotfiles セッションのみ | されない | する（token あり） | repo `.claude/settings.json` |
| **on-demand restore** | 全リポジトリ | — | する（手動 1 コマンド） | セッション内で実行 |

実ロジックはすべて git 管理の `scripts/bootstrap-web` に集約され、hook / Setup script は
それを呼ぶ薄いラッパー。

### 重要な制約（ハマりどころ）

以下は **Claude Code on the web** の制約。Codex cloud は env / secret の注入タイミングが逆なので、
「Codex cloud の environment 設定（UI）」節に従うこと。

- **environment 変数は Setup script（プロビジョニング）フェーズには注入されない。** Claude の
  セッション側にのみ入る。そのため Setup script から `opmaterialize restore`（token 必須）は
  できない。op の**導入**は token 不要なので Setup script で行い、**restore** はセッション側
  （token あり）に委ねる。
- **Setup script はキャッシュ（スナップショット）される。** secret を restore するとスナップ
  ショットに焼き込まれるため、Setup script では `BOOTSTRAP_WEB_SKIP_OP=true` で restore を
  必ず skip する。
- **キャッシュは Setup script か allowed network hosts を変更したときに再ビルド**される。
  dotfiles のコードを更新しても、Setup script を編集しない限り古い clone が使われ続ける。
  新コードを反映したいときは Setup script を一度編集して再ビルドを誘発する。
- **GitHub は git（proxy）と MCP ツールですでに触れる。** `gh` CLI（`GH_TOKEN`）は別物で、
  web では基本不要（skill 配置は bootstrap-web がファイルコピー、PR/issue/CI/release は MCP）。

## Claude Code on the web の environment 設定（UI）

環境セレクタ（クラウドアイコン）→ 対象 environment の歯車（編集）で以下を設定する。

### 1. Environment variables（`.env` 形式・クォートで囲まない）

```
OP_SERVICE_ACCOUNT_TOKEN=ops_xxxxxxxx   # 1Password service account（Dotfiles Secrets vault の read 限定推奨）
CODEX_AUTH_JSON={...}                    # Mac の ~/.codex/auth.json の中身（codex 認証）
```

> 平文で保存され environment を編集できる人に見える。権限は最小に絞り、不要時は revoke する。
> `GEMINI_API_KEY` / `GH_TOKEN` / `COPILOT_GITHUB_TOKEN` は対応 runner を使う場合のみ追加。

### 2. Network access（Custom）

allowed domains に以下を追加し、「Also include default list of common package managers」も有効化する。

```
cache.agilebits.com       # op バイナリ配布
downloads.1password.com   # op バイナリ配布（手動確認用。現状 install_op は cache.agilebits.com のみ使用）
*.1password.com           # op 実行時の 1Password API
```

### 3. Setup script（全リポジトリ対応の正本スニペット）

```bash
#!/bin/bash
set -uo pipefail
DOTFILES=/opt/dotfiles
if [ ! -d "$DOTFILES/.git" ]; then
  git clone --depth 1 https://github.com/mikito-tottenham/dotfiles.git "$DOTFILES" \
    || { echo "[setup] dotfiles clone failed"; exit 0; }
fi
ln -sf "$DOTFILES/dot_local/bin/executable_gws-account" /usr/local/bin/gws-account 2>/dev/null || true
# bootstrap-web の REPO_DIR は BOOTSTRAP_REPO_DIR > CLAUDE_PROJECT_DIR > スクリプト位置 の順に
# 解決される。source を /opt/dotfiles に固定するため BOOTSTRAP_REPO_DIR を渡す
# （CLAUDE_PROJECT_DIR がセッション repo を指していると別プロジェクトが source になる）。
BOOTSTRAP_REPO_DIR="$DOTFILES" BOOTSTRAP_WEB_SKIP_OP=true "$DOTFILES/scripts/bootstrap-web" \
  || echo "[setup] bootstrap-web non-zero (継続)"
exit 0
```

### 4. 設定は environment ごとに独立している

Claude Code on the web は environment を複数持てる（既定の `Default` と任意の追加分）。
**設定は environment 間でコピーされない。上記 1〜3 は「実際に使う environment」に必ず入れる。**

- Network access は **`Custom` + 上記 2 の allowlist** にする。既定の `Trusted` は
  「検証済みパッケージ配布元のみ」で `cache.agilebits.com` / `*.1password.com` に届かず、
  op の導入も restore もできない。
- Environment variables（token 類）は environment ごとの個別設定で、他からコピーされない。
- environment を複数使い分けるなら、そのすべてに 1〜3 を入れる。使わない environment は対象外。

> 2026-09-01 実測: 既定の `Default` は未設定（Network access=`Trusted`・env 空・Setup script 空）
> だった。設定済みの environment を選んでいる限り問題ないが、environment を切り替えると
> 環境再現は一切効かなくなる。どの environment でセッションを開いているかは常に意識する。

## Codex cloud の environment 設定（UI）

Codex settings → Environments → 対象 environment で設定する（repo 内ファイルからは設定できない）。
**Claude Code on the web とは env / secret の注入タイミングが逆**なので、設定を流用しないこと。

| 項目 | Claude Code on the web | Codex cloud |
| :-- | :-- | :-- |
| env var の注入先 | agent phase のみ | setup script + agent phase |
| secret 専用枠 | なし（env var のみ） | あり（**setup のみ**・agent phase 開始前に削除） |
| setup 中の network | allowlist に従う | 常に有効 |
| agent phase の network | 管理 proxy 経由 | **既定 off**（allowlist で許可） |
| キャッシュ無効化 | Setup script / allowed hosts の変更 | 12h 経過、または setup / maintenance script・env・secret の変更 |

出典: [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment.md)。

### 1. Environment variables（secret 枠は使わない）

`OP_SERVICE_ACCOUNT_TOKEN` は **secret 枠ではなく environment variables 枠**に置く。
secret 枠は setup script でしか読めず agent phase 開始前に削除されるため、セッション内の
on-demand restore ができない。env var 枠なら agent phase でも `opmaterialize restore` が通り、
Claude 側と同じ「setup では restore しない・セッション内で restore する」運用に揃う。

```
OP_SERVICE_ACCOUNT_TOKEN=ops_xxxxxxxx   # 1Password service account（read 限定推奨）
```

> secret 枠に置いて setup script で restore する方法もあるが、復元結果がコンテナ
> スナップショットに焼き込まれる（最大 12h 残る）。既定では採らない。
> `GEMINI_API_KEY` / `GH_TOKEN` / `COPILOT_GITHUB_TOKEN` は対応 runner を使う場合のみ追加。

### 2. Internet access（agent phase の allowlist）

agent phase は既定で遮断される。setup phase は常に network があるので設定不要。
セッション内で restore と runner 実行をするため、以下を allowlist に加える。

```
cache.agilebits.com              # op バイナリ配布
*.1password.com                  # op 実行時の 1Password API
github.com                       # skill / CLI の取得
objects.githubusercontent.com    # GitHub release アセット
registry.npmjs.org               # codex / gemini / copilot CLI
proxy.golang.org                 # ghq (go install)
```

### 3. Setup script

```bash
#!/bin/bash
set -uo pipefail
DOTFILES=/opt/dotfiles
if [ ! -d "$DOTFILES/.git" ]; then
  git clone --depth 1 https://github.com/mikito-tottenham/dotfiles.git "$DOTFILES" \
    || { echo "[setup] dotfiles clone failed"; exit 0; }
fi
ln -sf "$DOTFILES/dot_local/bin/executable_gws-account" /usr/local/bin/gws-account 2>/dev/null || true
# Codex cloud には CLAUDE_PROJECT_DIR が無いため BOOTSTRAP_REPO_DIR で source を固定する。
# secret をスナップショットへ焼き込まないため restore は skip し、agent phase の
# on-demand `opmaterialize restore` に委ねる。
BOOTSTRAP_REPO_DIR="$DOTFILES" BOOTSTRAP_WEB_SKIP_OP=true "$DOTFILES/scripts/bootstrap-web" \
  || echo "[setup] bootstrap-web non-zero (継続)"
exit 0
```

### 4. Maintenance script（キャッシュ再開時）

Codex cloud はコンテナをキャッシュ（最大 12h）し、再開時に maintenance script を走らせる。
これを設定しないと、dotfiles を更新してもキャッシュ内の古い clone が使われ続ける
（Claude 側で「Setup script を編集しないと再ビルドされない」のと同じハマりどころ）。

```bash
#!/bin/bash
set -uo pipefail
DOTFILES=/opt/dotfiles
if [ -d "$DOTFILES/.git" ]; then
  git -C "$DOTFILES" pull --ff-only >/dev/null 2>&1 || echo "[maint] dotfiles pull failed (継続)"
fi
BOOTSTRAP_REPO_DIR="$DOTFILES" BOOTSTRAP_WEB_SKIP_OP=true "$DOTFILES/scripts/bootstrap-web" \
  || echo "[maint] bootstrap-web non-zero (継続)"
exit 0
```

`bootstrap-web` は冪等なので再実行して問題ない。ここでも `BOOTSTRAP_WEB_SKIP_OP=true` を
維持し、secret はキャッシュへ焼き込まない。

### 5. 既知の差分

- Codex cloud には Claude Code の SessionStart hook に相当する仕組みが無いため、
  dotfiles セッションでも自動 restore はされない。restore は毎回 on-demand で実行する。
- MCP 登録ステップ（`ensure_mcp_servers`）は `claude` CLI がある環境でのみ動く。
  Codex cloud では skip され、`status.json` の `mcp_skipped` に理由が残る。

## parity 検証（両クラウド共通）

`scripts/verify-cloud-parity` が、ローカルとクラウドの再現差分を実環境から検査する。
期待リスト（skill / MCP）の正本は `scripts/bootstrap-web` の配列で、検証側は再定義しない。

```bash
BOOTSTRAP_REPO_DIR=/opt/dotfiles /opt/dotfiles/scripts/verify-cloud-parity          # 表形式
BOOTSTRAP_REPO_DIR=/opt/dotfiles /opt/dotfiles/scripts/verify-cloud-parity --json   # 機械可読
BOOTSTRAP_REPO_DIR=/opt/dotfiles /opt/dotfiles/scripts/verify-cloud-parity --quiet  # サマリ行のみ
```

判定は `OK` / `MISSING`（= 移植差分）/ `N/A`（この環境では対象外）。`MISSING` が 1 件でも
あれば exit 1。secret の実値は出力せず有無だけを見る。

検査対象: skill（claude / codex）、CLI、設定ファイル、private subagent、認証材料
（`dotfiles.env` / gws プロファイル / `codex auth.json` / `OP_SERVICE_ACCOUNT_TOKEN` の有無）、
MCP、plugin、`bootstrap-web` の `status.json`。

`MISSING` が出たときの復旧:

```bash
BOOTSTRAP_REPO_DIR=/opt/dotfiles /opt/dotfiles/scripts/bootstrap-web
opmaterialize restore
```

## セッション内での secret 復元（on-demand）

dotfiles 以外のセッションでは、secret が要るときにセッション内で復元する（token はセッションに
ある、op は Setup script 導入済み）。

```bash
opmaterialize restore
gws-account <profile> drive files list
```

dotfiles リポジトリのセッションは SessionStart hook が自動でフル restore するため、この手順は不要。

## gws（Google Workspace）マルチアカウント

各 Google アカウントを**別々の GCP プロジェクト + 別 OAuth クライアント**で分離し、
プロファイルごとに config dir を丸ごと分ける（`~/.config/gws/accounts/<profile>/`、ADR-0048）。
認証情報は 1Password 管理にする。アカウントごとに 1 回、Mac（ブラウザ）で実施する。

実行は常に `gws-account <profile> ...` を通す。素の `gws` はデフォルト認証状態
（`~/.config/gws/` 直下）で動くため、アカウント境界のある作業では使わない。

### 手順（アカウントごと）

1. **そのアカウントで** GCP Console にログイン → 専用プロジェクト作成
2. 「API とサービス」→「ライブラリ」で必要 API を有効化（Drive 等）
3. **OAuth 同意画面（Google Auth Platform）**:
   - 「使ってみる（Get started）」ウィザード →「Audience（対象）」で User type を選ぶ
     - Workspace 組織アカウント → **Internal**（7日失効なし・警告なし・審査不要。推奨）
     - 個人 Gmail → **External**（テストユーザーに自分を追加。本番化しないと refresh token が7日失効）
   - 使うスコープ（Drive / Calendar / Gmail 等）を登録
4. **認証情報** →「OAuth クライアント ID」→ 種類 **デスクトップ アプリ** → 作成 → **JSON をダウンロード**
5. ダウンロードした JSON をプロファイル dir に**そのまま配置**（手編集しない）:
   ```bash
   mkdir -p ~/.config/gws/accounts/<profile>
   chmod 700 ~/.config/gws/accounts/<profile>
   cp ~/Downloads/client_secret_*.json ~/.config/gws/accounts/<profile>/client_secret.json
   chmod 600 ~/.config/gws/accounts/<profile>/client_secret.json
   ```
   > 既定位置 `~/.config/gws/client_secret.json` への上書きは他アカウントのクライアントを
   > 壊すのでしない。gws は config dir の `client_secret.json` 内 `project_id` を
   > quota project（`x-goog-user-project`）として API に送るため、プロジェクトが違う
   > アカウントは config dir ごと分けないと 403（他プロジェクトへの権限なし）になる。
6. 認証（**そのアカウントで**ブラウザ同意。使うサービスを指定）:
   ```bash
   gws-account <profile> auth login --services drive,calendar,gmail
   ```
7. 認証情報を可搬な自己完結 JSON にエクスポートして 1Password 管理にする:
   ```bash
   gws-account <profile> auth export --unmasked > ~/.config/gws/accounts/<profile>/credentials.json
   chmod 600 ~/.config/gws/accounts/<profile>/credentials.json
   opmaterialize add ~/.config/gws/accounts/<profile>/client_secret.json
   opmaterialize add ~/.config/gws/accounts/<profile>/credentials.json
   ```
   > 注: 現在の `Dotfiles Secrets` は field 方式で運用しており、`opmaterialize add`（Document 方式）は拒否される。その場合は 1Password 上で手動登録する（`content` フィールドを持つ Secure Note を作成し、マニフェストに `field` 行を追加）。詳細は ADR 0046 と onepassword-secret-materialize skill を参照。
   >
   > `auth login` が同 dir に作る `credentials.enc` はマシン固有の暗号化 state（他マシンへ持ち出さない）、
   > `token_cache.json` / `cache/` は実行時 state で、いずれも 1Password 登録対象外。
8. 選択して使う:
   ```bash
   gws-account <profile> drive files list
   ```

`<profile>` はアカウントの呼び名（半角英数字・`.` `_` `-`、例 `work` / `personal`）。重複させない。
具体的なプロファイル名や実アカウント識別子は git 管理ファイルに書かない（ADR-0048）。

登録済みプロファイルとアカウントの対応表は、このリポジトリの外（Personal・各作業
リポジトリ・auto memory 等の machine-local state）が所有し、このリポジトリには
置かない（ADR-0048）。

各 OAuth クライアントは所属組織の Internal 設定のため、`auth login` のアカウント
選択画面で別組織のアカウントを選ぶと `403 org_internal` になる（2026-07-17:
リポジトリ文書記載の他環境用アカウント名を再ログイン先として誤案内した事例あり）。
再認証を依頼するときは、対象プロファイルと選ぶべきメールアドレスを明示する。

### gws のよくある失敗

- **`Error 401: invalid_client / The OAuth client was not found`**: 送っている client_id が
  実在クライアントと不一致。原因の順:
  1. env の `GOOGLE_WORKSPACE_CLI_CLIENT_ID` に古い値が残っている（`unset` する。env はファイルより優先）
  2. `~/.config/gws/accounts/<profile>/client_secret.json` の client_id が古い／`<` `>` 等の不要文字混入
     （Console の JSON で丸ごと上書きし直す。手編集しない）
  3. クライアント種別が「ウェブ」になっている（gws はループバックを使うので**デスクトップ**で作り直す）
  4. 作成直後の反映待ち（数分待つ）
- **「アクセスをブロック: 認証エラー / 確認されていません」**: 同意画面が「テスト」で test user
  未登録、または未本番化。Internal にするか、External なら test user 追加 + 本番化。
- **`403: Caller does not have required permission to use project <別プロファイルの project>`**:
  quota project が、使われた config dir の `client_secret.json` から別プロジェクトの値で
  拾われている。素の `gws`（既定 config dir）で実行していないか確認し、必ず
  `gws-account <profile>` で正しいプロファイル dir を使う（手順 5 の注を参照）。
- **`gws-account` の exit code**: `66` = 選択プロファイルの認証情報が無い（同一プロファイルで
  restore / `auth login` する。**別アカウントへの切り替えは復旧経路ではない**）、
  `78` = ambient な `GOOGLE_WORKSPACE_CLI_TOKEN` / `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` を検出して
  実行拒否（該当 env を `unset` する。明示的に渡す場合のみ `GWS_ACCOUNT_CREDENTIALS_FILE` を使う）、
  `127` = gws 未導入。拒否された後に素の `gws` で再試行しない。

## runner 認証リファレンス

| CLI | バイナリ | 認証材料 | 標準セットアップ |
| :-- | :-- | :-- | :-- |
| ghq | bootstrap-web | 不要 | なし |
| op | bootstrap-web（token 非依存） | `OP_SERVICE_ACCOUNT_TOKEN`（env） | env 登録済み |
| codex | bootstrap-web | `CODEX_AUTH_JSON`（env）→ `~/.codex/auth.json` | env 登録済み |
| gws | bootstrap-web | `~/.config/gws/accounts/<profile>/{client_secret,credentials}.json`（1Password） | 上記 gws 手順 |
| gemini | bootstrap-web | `GEMINI_API_KEY` | 1Password → dotfiles.env 参照 → `oprun gemini` |
| gh | bootstrap-web | `GH_TOKEN` | web では基本不要（git=proxy / PR 等=MCP）。`gh` 固有コマンドを使う時のみ env 登録 |
| copilot | bootstrap-web | `COPILOT_GITHUB_TOKEN`（+ Copilot 契約） | 1Password → env |

API キー系は 1Password に保存し `~/.config/op/dotfiles.env` に `KEY=op://<vault>/<item>/<field>`
を書き、`oprun <cmd>` で注入する（規約準拠）。secret 実値は git に置かない。

## 動作確認（新しいクラウドセッションで）

```bash
# 一括確認（推奨）: 期待リストとの差分を出す
BOOTSTRAP_REPO_DIR=/opt/dotfiles /opt/dotfiles/scripts/verify-cloud-parity

# 個別確認: Setup script が走ったか
cat ~/.cache/bootstrap-web/status.json        # overall_success:true / onepassword:"op-installed: ..."
command -v op gws gws-account codex jq rg      # 導入確認

# secret 復元（dotfiles 以外のセッション）
opmaterialize restore
gws-account <profile> drive files list         # Drive 一覧が返れば成功
codex login status                             # "Logged in" 確認
```

`status.json` の `onepassword` が `skipped: op 未導入 (network policy で 1Password 配布が遮断?)`
の場合は、setup フェーズで 1Password 配布元への network が通っていない。その場合は in-session で
（source 固定のため `CLAUDE_PROJECT_DIR` を上書きして）bootstrap-web を 1 回実行し op を導入する
（token がセッションにあるのでそのまま restore まで通る）。対処後に network policy / Setup script
を見直す。

```bash
CLAUDE_PROJECT_DIR=/opt/dotfiles /opt/dotfiles/scripts/bootstrap-web
```

## runner skill の実態確認（CLI 導入 × 認証 × egress）

runner 系 skill の実用可否は「背後 CLI の導入 × 認証材料 × network egress（backend 到達性）」で
決まる。codex の egress は **経路で分けて理解する**こと: web セッションのコンテナは直接の外部
egress を持たず、通信は Claude Code 管理 proxy 経由になる（`CLAUDE_CODE_PROXY_RESOLVES_HOSTS`）。
一般 HTTP では `api.openai.com` / `chatgpt.com` に到達できない（2026-06-22 実測。挙動はセッション/
環境依存で、**proxy 経由で 403** になる場合と **proxy 有無とも DNS 解決不可** になる場合がある。
いずれも素の egress では openai 不達という点は共通）。**ただし** Claude Code の `openai-codex` プラグインの
companion runtime（`CODEX_COMPANION_SESSION_ID`）経由では codex CLI が実行できる（実測で
`codex exec` 成功・web セッション内で Codex レビューを実行できている）。詳細は ADR-0045 参照。
新しいクラウドセッションで以下を流すと導入・認証の一覧を確認できる。

```bash
for c in codex gemini copilot grok op gws gws-account gh ghq opmaterialize jq; do
  printf '%-14s %s\n' "$c" "$(command -v "$c" 2>/dev/null || echo '未導入')"
done
codex login status 2>&1 | head -1                      # codex 認証
gh auth status 2>&1 | head -1                            # gh 認証（web では未認証が既定）
ls ~/.config/gws/accounts/*/credentials.json 2>/dev/null | wc -l    # gws プロファイル数（restore 後に増える）
```

期待状態（スコープ内 = 既定で揃える / 任意 = 使う時だけ認証を足す）:

| skill | 背後 CLI | 認証材料 | 既定の扱い |
| :-- | :-- | :-- | :-- |
| codex-cli-runner | codex | `CODEX_AUTH_JSON` → `~/.codex/auth.json`（+ openai-codex companion runtime） | スコープ内・認証済。素のコンテナ egress では openai 不達だが、openai-codex プラグイン proxy 経由なら実行可（ADR-0045） |
| op-cli-runner | op | `OP_SERVICE_ACCOUNT_TOKEN` | スコープ内・認証済 |
| onepassword-secret-materialize | opmaterialize + op + jq | 上記 op に依存（field 方式は `jq` 必須） | スコープ内・認証済 |
| gws-cli-runner / gws-drive / -upload / -shared | gws (+ gws-account) | `~/.config/gws/accounts/<profile>/`（restore 後） | スコープ内・restore 後に有効 |
| ghq-repo-placement | ghq | 不要 | スコープ内・常時可 |
| skill-manager | gh（`gh skill`） | `GH_TOKEN` / `GITHUB_TOKEN`（web では未設定） | 下記参照 |
| gemini-cli-runner | gemini | `GEMINI_API_KEY` | 任意（導入のみ・使う時に認証） |
| copilot-cli-runner | copilot | `COPILOT_GITHUB_TOKEN` / `GH_TOKEN` / `GITHUB_TOKEN` | 任意（導入のみ・使う時に認証） |
| grok-cli-runner | （bootstrap 対象外） | xAI OAuth（Hermes） | 任意・**bootstrap 未導入**（headless 経路なし） |

> gemini / copilot は「導入はされるが未認証」が既定で、使う時だけ environment 変数または
> 1Password 経由で認証材料を足す。grok は headless 認証経路が無いため bootstrap-web の導入対象外で、
> 使うなら別途 CLI 導入 + xAI OAuth が要る（ADR-0045）。

### skill-manager と gh skill の扱い

`gh`（2.90.0+）には `gh skill` サブコマンドがあり起動自体はできるが、web セッションでは
gh CLI が未認証（`GH_TOKEN` / `GITHUB_TOKEN` 無し）のため `gh skill search/install/update` の
ような GitHub 操作はできない。`dot_gitconfig` の credential helper（`!gh auth git-credential`）は
git 認証用で、gh CLI を `gh skill` 向けに認証するものではない。

これは想定どおりで、**web での skill 配置は bootstrap-web のファイルコピー
（`docs/skills-install-manifest.md` が正本）**で行うため `gh skill` の認証は不要。
web セッション内で `gh skill` を直接叩きたい場合のみ `GH_TOKEN` / `GITHUB_TOKEN` を登録する
（最小構成では不要）。

## 関連

- 設計判断: `docs/adr/0045-reproduce-web-session-environment-via-session-start-hook.md`
- Codex cloud 対応と parity 検証: `docs/adr/0058-extend-cloud-parity-to-codex-cloud.md`
- parity 検証スクリプト: `scripts/verify-cloud-parity`
- 1Password CLI 認証: `docs/adr/0044-use-op-cli-runner-for-1password-cli-auth.md`
- field 方式 secret: `docs/adr/0046-support-field-based-secrets-in-opmaterialize.md`
- skill 配備の正本: `docs/skills-install-manifest.md`
- secret ファイル運用: `onepassword-secret-materialize` skill
- アカウント選択方針: `docs/adr/0048-adopt-gws-account-profile-isolation.md`
- アカウント選択ラッパー: `dot_local/bin/executable_gws-account`（`~/.local/bin/gws-account`）
- agent 側の運用契約: `skills/gws-cli-runner`
