---
name: auth-preflight
description: Triage authentication and account-boundary failures across 1Password (`op`, `oprun`), GitHub (`ghrun gh`), Google Workspace (`gws-account`), Slack (`slack-account`, MCP connectors), Chatwork MCP, and MoneyForward MCP, and run a read-only preflight before work that depends on them. Use before multi-service work, or on errors such as `account is not signed in`, `401 Bad credentials`, `invalid_grant`, `invalid_rapt`, `403 org_internal`, `not_authed`, `invalid_auth`, or `invalid or expired access token`. Use when asked to 認証を確認して, 認証が切れた, ログインし直し, トークン失効, 1Password が通らない, gh が 401, gws が invalid_grant, Slack が繋がらない, MF の MCP が切れた, or 作業前に接続確認.
---

# Auth Preflight

認証断を「症状 → 一次切り分け → 対処 → ユーザーに依頼すること」で素早く分類し、作業前に読み取り専用で接続状態を確かめる入口。個別ツールの実行規約は各正本に任せ、この Skill は横断の索引と preflight だけを持つ。

## 正本（ここでは再掲しない）

| 対象 | 正本 |
|---|---|
| 認証の大原則（1Password 経由、別ストアへ実値を置かない、一次切り分けは 1Password 側、1Password 依存は認証が要る操作だけ） | グローバル指示 `agents-common.md` の認証節 |
| 1Password CLI の実行と失敗分類 | `op-cli-runner` Skill、ADR-0036 / 0044 / 0055 |
| GitHub token（`ghrun`、`ghrun --refresh`） | ADR-0063 |
| gws のプロファイル、再認証手順 | `gws-cli-runner` Skill（Recovery Runbook、`references/account-profiles.md`）、ADR-0048 / 0060 |
| Slack の複数ワークスペース | ADR-0061 |
| Chatwork / MoneyForward MCP、クラウドの認証経路 | ADR-0062 / 0068 |
| 会社 → アカウント → 経路の対応（環境固有） | 作業ルートの `AGENTS.md`「アカウント境界」節 |

## 手順

1. 作業対象の会社・ワークスペースを決め、作業ルートの `AGENTS.md` のアカウント境界節で使う経路（gws プロファイル、slack-account プロファイル、MCP コネクタ）を確認する。
2. preflight を実行する（既定は読み取り専用で、Touch ID を誘発しない）。

   ```bash
   python3 <skill-dir>/scripts/auth_preflight.py --json-out .context/<task>/auth-preflight.json
   ```

   - `--only gh,gws` で対象を絞る。`--profile <name>` で gws プロファイルを限定する。
   - `--offline` はネットワークを使う確認（`ghrun gh api user`、`gws-account <p> auth status`）を省く。
   - `--with-op` を付けたときだけ `op whoami` と `oprun slack-account <p> auth status` を実行する。どちらも 1Password の承認を求める可能性があるため、ユーザーがその場で承認できるときに限る。
   - 出力はステータス・ドメイン・ワークスペース名だけで、token・op:// reference・メールアドレスは伏せる。exit 1 は FAIL がある状態。
3. MCP コネクタは script から検査できない。下の「MCP コネクタの確認」で読み取りツールを 1 回呼び、接続先が目的の組織と一致するかを確かめる。
4. FAIL / WARN は下の症状表で分類し、「ユーザーに依頼すること」の列をそのまま依頼文の材料にする。Agent が代わりに実行しない操作は依頼に回し、別アカウントや別経路への切り替えで作業を続けない。

## MCP コネクタの確認

コネクタは 1 コネクタ 1 アカウントで、接続先が違っても認証エラーにならず空の結果を返すことがある。結果を信頼する前に、自分自身の情報を返す読み取りツールで接続先を確かめる。

| コネクタ | 確認方法（読み取りのみ） | 一致の判断 |
|---|---|---|
| Google Calendar | カレンダー一覧を取得し、primary の ID のドメインを見る | 目的の組織ドメインと一致するか |
| Gmail / Drive | 直近の受信メール 1 件の宛先ドメイン、または自分が owner のファイル 1 件の owner ドメインを見る | 同上 |
| Slack | 自分のプロフィールを読み、ワークスペース名を見る | 目的のワークスペースか |
| Chatwork | `get_me` を呼ぶ | 目的のアカウントか |
| MoneyForward（`mfc_ca`） | `currentOffice` を呼ぶ | 目的の事業者か。`access token is required` / `invalid or expired access token` なら下表 |

ツール名の接頭辞は接続ごとに変わる。ToolSearch でツール名から解決する。

## 症状表

| 症状 | 一次切り分け | 対処（Agent） | ユーザーに依頼すること |
|---|---|---|---|
| `op` / `oprun` が `account is not signed in` | デスクトップ統合では未認可の間この表示になる。アプリのロック、CLI 統合の無効化も同じ表示 | 認証が要る操作の直前だけ `op-cli-runner` で 1 回実行し、`summary.json` の分類を報告する。再試行を重ねない | 1Password アプリのロック解除。設定 → 開発者 →「1Password CLI と統合する」が有効か |
| `op` が応答しない、`authorization timeout` / `prompt dismissed` | Touch ID の承認待ち、または承認の見落とし | 待たずに止め、何の操作で承認が要るかを伝える | 承認ダイアログへの応答。Agent の Bash は tty が無く毎回承認になる点を共有する |
| `oprun` が `env file not readable` | `~/.config/op/dotfiles.env` が無い | 作成しない（実値も reference も Agent が書かない） | `dotfiles.env.example` を元にした作成。中身は `op://` reference だけ |
| `ghrun` exit 66（token ファイルが無い） | materialize 未実行 | 作業を止める | 通常のターミナルで `ghrun --refresh`（Touch ID 1 回） |
| `ghrun gh` が `401 Bad credentials` | 1Password 側の token ローテーション後に stale | Agent から `ghrun --refresh` を実行しない。素の `gh` や `gh auth login` に切り替えない | 通常のターミナルで `ghrun --refresh` |
| 素の `gh` が別アカウント・keyring token で動く | `alias gh='ghrun gh'` は非対話 shell で効かない | 必ず `ghrun gh ...` と明示して再実行する | なし |
| gws `token_valid: false`、`invalid_grant`、`invalid_rapt` | 該当プロファイルの OAuth 失効。他プロファイルは有効なことが多い | preflight で他プロファイルの状態を確認し、境界が一致する作業だけ続ける。`gws-cli-runner` の Recovery Runbook に従う | `gws-account <profile> auth login` をフォアグラウンドで実行し、ブラウザで選ぶアカウントのドメインを明示して依頼 |
| gws ログイン時にブラウザで `403 org_internal` | 別組織のアカウントを選んだ | 同じプロファイルで再ログインを依頼し直す | 正しいドメインのアカウントを選び直す |
| gws-account exit 78 | `GOOGLE_WORKSPACE_CLI_*` の ambient 変数 | 変数を unset して wrapper で再実行。素の `gws` に切り替えない | なし |
| `slack-account` exit 1（token 未設定、`op://` のまま） | `oprun` を通さずに実行した、または `dotfiles.env` にキーが無い | `oprun slack-account <profile> ...` で実行する。キー欠落なら止める | 1Password 項目と `dotfiles.env` のキー追加 |
| `slack-account` exit 2 で `invalid_auth` / `token_revoked` / `not_authed` | Slack App の token 失効・取り消し | 止める。別ワークスペースや MCP で代替しない | Slack App の token 再発行と 1Password 項目の更新 |
| Slack MCP コネクタが未認証、または目的と違うワークスペース | コネクタは 1 ワークスペース固定 | slack-account のプロファイルがあればそちらを使う。無ければ止める | claude.ai のコネクタ設定での再接続 |
| Chatwork MCP が起動しない・ツールが出ない | MCP は `oprun` 経由で起動するため、起動時に 1Password の承認が要る | `/mcp` の状態を伝える | 1Password の承認後に `/mcp` から再接続 |
| MoneyForward MCP が `access token is required` / `invalid or expired access token` | MCP の OAuth token 失効 | authorize 系ツールで認可 URL を発行してユーザーに渡し、ユーザーがログインした後に exchange 系ツールで完了させる。ログイン操作は代行しない | 認可 URL を開き、MoneyForward にログインして承認する |
| MCP が認証エラーを出さずに空の結果を返す | 接続アカウントが目的の組織と違う | 上の「MCP コネクタの確認」で接続先を確かめ、違えば CLI 経路（`gws-account`、`slack-account`）へ切り替える | なし（経路の対応は `AGENTS.md`） |

## 禁止

- 1Password 以外のストア（`gh auth login` の keyring、手作りの token file、`.env` への実値、MCP 設定への平文 token）へ実値を置く回避策を提案・実行しない。
- 失敗したアカウントの代わりに別アカウント・別ワークスペースの成功結果を使わない。
- `ghrun --refresh`、`gws-account <p> auth login`、MCP の再ログインなどの対話認証を Agent が background で走らせない。
- preflight の結果や依頼文に token、`op://` reference、メールアドレスを書かない。

## 検証

- `python3 <skill-dir>/scripts/auth_preflight.py --offline` が exit 0 / 1 で終わり、出力にメールアドレス・token 形式・`op://` の値が含まれないこと。
- `--with-op` の分岐は、`PATH` の先頭に偽の `op` / `oprun` を置いて確認できる（1Password には触れない）。
