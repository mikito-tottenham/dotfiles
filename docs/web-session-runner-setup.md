---
title: "Web Session Runner & 1Password Setup Runbook"
updated_at: 2026-06-22
---

# Web Session Runner & 1Password Setup Runbook

Claude Code on the web（ephemeral クラウドセッション）で、runner CLI（codex / gemini /
ghq / gh / gws / copilot）と 1Password 由来の secret を再現するための運用手順。設計判断の
正本は ADR-0045、本書はそれを「迷わず実行する」ための手順書。

## 全体像

クラウドセッションは毎回まっさらな VM で起動し、リポジトリを clone し直す。永続するのは
git に push した内容だけ。そこで以下の3層で環境を再現する。

| 層 | 適用範囲 | キャッシュ | secret 復元 | 設定場所 |
| :-- | :-- | :-- | :-- | :-- |
| **Setup script** | 全リポジトリ | される | しない（op 導入まで） | environment UI |
| **SessionStart hook** | dotfiles セッションのみ | されない | する（token あり） | repo `.claude/settings.json` |
| **on-demand restore** | 全リポジトリ | — | する（手動 1 コマンド） | セッション内で実行 |

実ロジックはすべて git 管理の `scripts/bootstrap-web` に集約され、hook / Setup script は
それを呼ぶ薄いラッパー。

### 重要な制約（ハマりどころ）

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

## クラウド environment の設定（UI）

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
ln -sf "$DOTFILES/scripts/gws-as" /usr/local/bin/gws-as 2>/dev/null || true
# bootstrap-web は REPO_DIR を CLAUDE_PROJECT_DIR 優先で解決するため、source を /opt/dotfiles に
# 固定する（CLAUDE_PROJECT_DIR がセッション repo を指していると別プロジェクトが source になる）。
CLAUDE_PROJECT_DIR="$DOTFILES" BOOTSTRAP_WEB_SKIP_OP=true "$DOTFILES/scripts/bootstrap-web" \
  || echo "[setup] bootstrap-web non-zero (継続)"
exit 0
```

## セッション内での secret 復元（on-demand）

dotfiles 以外のセッションでは、secret が要るときにセッション内で復元する（token はセッションに
ある、op は Setup script 導入済み）。

```bash
opmaterialize restore
gws-as <name> drive files list
```

dotfiles リポジトリのセッションは SessionStart hook が自動でフル restore するため、この手順は不要。

## gws（Google Workspace）マルチアカウント

各 Google アカウントを**別々の GCP プロジェクト + 別 OAuth クライアント**で分離し、認証情報を
1Password 管理にする。アカウントごとに 1 回、Mac（ブラウザ）で実施する。

### 手順（アカウントごと）

1. **そのアカウントで** GCP Console にログイン → 専用プロジェクト作成
2. 「API とサービス」→「ライブラリ」で必要 API を有効化（Drive 等）
3. **OAuth 同意画面（Google Auth Platform）**:
   - 「使ってみる（Get started）」ウィザード →「Audience（対象）」で User type を選ぶ
     - Workspace 組織アカウント → **Internal**（7日失効なし・警告なし・審査不要。推奨）
     - 個人 Gmail → **External**（テストユーザーに自分を追加。本番化しないと refresh token が7日失効）
   - 使うスコープ（Drive / Calendar / Gmail 等）を登録
4. **認証情報** →「OAuth クライアント ID」→ 種類 **デスクトップ アプリ** → 作成 → **JSON をダウンロード**
5. ダウンロードした JSON を gws の設定位置に**そのまま上書き**（手編集しない）:
   ```bash
   cp ~/Downloads/client_secret_*.json ~/.config/gws/client_secret.json
   chmod 600 ~/.config/gws/client_secret.json
   ```
6. 認証（**そのアカウントで**ブラウザ同意。使うサービスを指定）:
   ```bash
   gws auth login --services drive,calendar,gmail
   ```
7. 認証情報を自己完結 JSON にエクスポートして 1Password 管理にする:
   ```bash
   mkdir -p ~/.config/gws/accounts
   gws auth export --unmasked > ~/.config/gws/accounts/<name>.json
   chmod 600 ~/.config/gws/accounts/<name>.json
   opmaterialize add ~/.config/gws/accounts/<name>.json
   ```
   > 注: 現在の `Dotfiles Secrets` は field 方式で運用しており、`opmaterialize add`（Document 方式）は拒否される。その場合は 1Password 上で手動登録する（`content` フィールドを持つ Secure Note を作成し、マニフェストに `field` 行を追加）。詳細は ADR 0046 と onepassword-secret-materialize skill を参照。
8. 切り替えて使う:
   ```bash
   gws-as <name> drive files list
   ```

`<name>` はアカウントの呼び名（半角英数字・ハイフン、例 `work` / `personal`）。重複させない。

### gws のよくある失敗

- **`Error 401: invalid_client / The OAuth client was not found`**: 送っている client_id が
  実在クライアントと不一致。原因の順:
  1. env の `GOOGLE_WORKSPACE_CLI_CLIENT_ID` に古い値が残っている（`unset` する。env はファイルより優先）
  2. `~/.config/gws/client_secret.json` の client_id が古い／`<` `>` 等の不要文字混入
     （Console の JSON で丸ごと上書きし直す。手編集しない）
  3. クライアント種別が「ウェブ」になっている（gws はループバックを使うので**デスクトップ**で作り直す）
  4. 作成直後の反映待ち（数分待つ）
- **「アクセスをブロック: 認証エラー / 確認されていません」**: 同意画面が「テスト」で test user
  未登録、または未本番化。Internal にするか、External なら test user 追加 + 本番化。
- **env はファイルより優先**。切り替えは `gws-as`（`GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` を
  セット）で行い、素の `gws` を使うときは古い env を `unset` する。

## runner 認証リファレンス

| CLI | バイナリ | 認証材料 | 標準セットアップ |
| :-- | :-- | :-- | :-- |
| ghq | bootstrap-web | 不要 | なし |
| op | bootstrap-web（token 非依存） | `OP_SERVICE_ACCOUNT_TOKEN`（env） | env 登録済み |
| codex | bootstrap-web | `CODEX_AUTH_JSON`（env）→ `~/.codex/auth.json` | env 登録済み |
| gws | bootstrap-web | `~/.config/gws/accounts/<name>.json`（1Password） | 上記 gws 手順 |
| gemini | bootstrap-web | `GEMINI_API_KEY` | 1Password → dotfiles.env 参照 → `oprun gemini` |
| gh | bootstrap-web | `GH_TOKEN` | web では基本不要（git=proxy / PR 等=MCP）。`gh` 固有コマンドを使う時のみ env 登録 |
| copilot | bootstrap-web | `COPILOT_GITHUB_TOKEN`（+ Copilot 契約） | 1Password → env |

API キー系は 1Password に保存し `~/.config/op/dotfiles.env` に `KEY=op://<vault>/<item>/<field>`
を書き、`oprun <cmd>` で注入する（規約準拠）。secret 実値は git に置かない。

## 動作確認（新しいクラウドセッションで）

```bash
# Setup script が走ったか
cat ~/.cache/bootstrap-web/status.json        # overall_success:true / onepassword:"op-installed: ..."
command -v op gws gws-as codex                 # 導入確認

# secret 復元（dotfiles 以外のセッション）
opmaterialize restore
gws-as <name> drive files list                 # Drive 一覧が返れば成功
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

## runner skill の実態確認（CLI 導入 × 認証）

runner 系 skill の実用可否は「背後 CLI が導入されているか × 認証材料が揃っているか」で決まる。
新しいクラウドセッションで以下を流すと一覧で確認できる。

```bash
for c in codex gemini copilot grok op gws gws-as gh ghq opmaterialize jq; do
  printf '%-14s %s\n' "$c" "$(command -v "$c" 2>/dev/null || echo '未導入')"
done
codex login status 2>&1 | head -1                      # codex 認証
gh auth status 2>&1 | head -1                            # gh 認証（web では未認証が既定）
ls ~/.config/gws/accounts/*.json 2>/dev/null | wc -l    # gws アカウント数（restore 後に増える）
```

期待状態（スコープ内 = 既定で揃える / 任意 = 使う時だけ認証を足す）:

| skill | 背後 CLI | 認証材料 | 既定の扱い |
| :-- | :-- | :-- | :-- |
| codex-cli-runner | codex | `CODEX_AUTH_JSON` → `~/.codex/auth.json` | スコープ内・認証済 |
| op-cli-runner | op | `OP_SERVICE_ACCOUNT_TOKEN` | スコープ内・認証済 |
| onepassword-secret-materialize | opmaterialize + op + jq | 上記 op に依存（field 方式は `jq` 必須） | スコープ内・認証済 |
| gws-drive / -upload / -shared | gws (+ gws-as) | `~/.config/gws/accounts/<name>.json`（restore 後） | スコープ内・restore 後に有効 |
| ghq-repo-placement | ghq | 不要 | スコープ内・常時可 |
| skill-manager | gh（`gh skill`） | `GH_TOKEN`（web では未設定） | 下記参照 |
| gemini-cli-runner | gemini | `GEMINI_API_KEY` | 任意（使う時のみ） |
| copilot-cli-runner | copilot | `COPILOT_GITHUB_TOKEN` | 任意（使う時のみ） |
| grok-cli-runner | grok | Hermes / xAI OAuth | 任意（使う時のみ） |

> 任意 runner（gemini / copilot / grok）は「導入はされるが未認証」が既定。使う時だけ
> environment 変数または 1Password 経由で認証材料を足す。

### skill-manager と gh skill の扱い

`gh`（2.90.0+）には `gh skill` サブコマンドがあり起動自体はできるが、web セッションでは
gh CLI が未認証（`GH_TOKEN` 無し）のため `gh skill search/install/update` のような GitHub
操作はできない。`dot_gitconfig` の credential helper（`!gh auth git-credential`）は git 認証用で、
gh CLI を `gh skill` 向けに認証するものではない。

これは想定どおりで、**web での skill 配置は bootstrap-web のファイルコピー
（`docs/skills-install-manifest.md` が正本）**で行うため `gh skill` の認証は不要。
web セッション内で `gh skill` を直接叩きたい場合のみ `GH_TOKEN` を登録する（最小構成では不要）。

## 関連

- 設計判断: `docs/adr/0045-reproduce-web-session-environment-via-session-start-hook.md`
- 1Password CLI 認証: `docs/adr/0044-use-op-cli-runner-for-1password-cli-auth.md`
- field 方式 secret: `docs/adr/0046-support-field-based-secrets-in-opmaterialize.md`
- skill 配備の正本: `docs/skills-install-manifest.md`
- secret ファイル運用: `onepassword-secret-materialize` skill
- アカウント切り替え: `scripts/gws-as`
