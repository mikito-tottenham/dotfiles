---
title: "task-sweep ソースプロファイル（repo 側に置く設定）の雛形と、ソースごとの読み取り規則"
updated_at: 2026-10-23
---

# ソースプロファイルと読み取り規則

組織ごとに違う値（gws profile、slack-account profile、Chatwork MCP の接続、対象 repo）は、この skill に持たず作業 repo 側のプロファイル 1 ファイルにまとめ、repo の `AGENTS.md` から場所を指す。推奨パスは `docs/task-sweep-sources.md`。プロファイルが無い repo では、下の雛形の値をユーザーに確認してから始める。

プロファイルにも実メールアドレス・token・個人名は書かない。profile 名と repo 名だけで足りる。

## プロファイルの雛形

```markdown
## task-sweep ソースプロファイル

- organization: <組織の呼称>
- gws_profile: <gws-profile>            # gws-account のプロファイル名
- slack_profile: <slack-profile>        # oprun slack-account のプロファイル名。無ければ none
- chatwork: <chatwork-mcp>              # Chatwork MCP の接続名（repo の project MCP 等）。無ければ none
- repo: <repo>                          # 一次証拠・補助証拠を持つ git repo（ghq 名）
- default_branch: <default>             # origin 側の既定ブランチ
- period_days: 30                       # 既定の対象期間
- connectors_not_to_use: <理由つきで列挙>  # 別組織に接続している MCP コネクタなど
```

## 経路と疎通確認（`01-preflight`）

各ソースは下表の経路だけで読み、失敗したら `01-preflight` に理由を記録して `判定不能（ソース不通）` の根拠にする。別アカウント・別経路（別組織に接続した MCP コネクタ、他プロファイル、素の `gws` 等）への暗黙 fallback はしない。認証の復旧は `gws-cli-runner`（gws）と `op-cli-runner`（`oprun` / 1Password）の Skill に従う。コマンドの細かい引数は各 CLI の `--help` で確かめる。

| ソース | 経路 | 疎通確認 | 備考 |
|---|---|---|---|
| Slack | `oprun slack-account <slack-profile> ...` | `oprun slack-account <slack-profile> auth status` | `auth status` の team 表示が対象組織であることを記録する。MCP の Slack コネクタは 1 ワークスペース固定なので、接続先が違えば使わない |
| Chatwork | `<chatwork-mcp>` | `get_me` | 誰のアカウントで読んでいるかを `get_me` の結果で記録する（表示名のみ。token は書かない） |
| Gmail | `gws-account <gws-profile> gmail ...` | `gws-account <gws-profile> auth status` の後、`gmail users messages list` を `maxResults: 1` で 1 回 | MCP の Gmail コネクタが別アカウント接続なら使わない |
| Calendar | `gws-account <gws-profile> calendar ...` | `calendar calendarList list` を 1 回 | MCP の Calendar コネクタに対象組織のカレンダーが入っていないことがある |
| Drive | `gws-account <gws-profile> drive ...` | `drive files list` を `pageSize: 1` と共有ドライブ用パラメータ付きで 1 回 | 共有ドライブは `supportsAllDrives` / `includeItemsFromAllDrives` が要る。詳細は `gws-cli-runner` の `references/drive.md` |
| リポジトリ | `<repo>` の checkout（`ghq list --full-path <repo>` で解決）で `git fetch origin` 後の `origin/<default>` と未マージブランチ | `git -C <path> fetch origin` と `git -C <path> rev-parse origin/<default>` | ローカルの既定ブランチは古いことがあるので `origin/<default>` を見る。fetch はリモートを変えない |

## 使ってよい操作（読み取りのみ）

- **Slack**: `auth status`、`users find`、`channels list`、`read <permalink>`、`api` は `conversations.history` / `conversations.replies` / `conversations.info` / `search.messages` / `users.info` だけ。`slack-account` の `api` には allowlist が無く、プロファイルの token が書込 scope を持つことがあるため、この一覧に無い method は呼ばない
- **Chatwork**: `get_*` / `list_*` 系（`get_me`、`list_rooms`、`list_room_messages`、`get_room_message`、`list_my_tasks`、`list_room_tasks`、`get_room_task`、`list_room_files`、`get_room_file` など）
- **Gmail**: `users messages list` / `users messages get` / `users threads list` / `users threads get` / `+read`
- **Calendar**: `calendarList list`、`events list`、`events get`、`+agenda`
- **Drive**: `files list`、`files get`、`drives list`。本文の確認が要るときは export / download 系の読み取りだけを使う
- **git**: `fetch`、`log`、`show`、`grep`、`branch -r --no-merged`、`diff`（いずれも参照のみ）

## 使わない操作

- Slack: `post`、`upload`、`dm open`、`chat.*` / `reactions.*` / `pins.*` / `conversations.mark` など状態を変える method
- Chatwork: `post_*` / `update_*` / `create_*` / `delete_*` / `accept_*` / `reject_*`、および既読状態を変える `read_room_messages` / `unread_room_message`
- Gmail: `+send` / `+reply` / `+reply-all` / `+forward` / `+watch`、drafts、`modify` / `trash` / `delete`（ラベル・既読の変更を含む）
- Calendar: `+insert`、`events insert` / `update` / `patch` / `delete`、`acl`
- Drive: `files create` / `update` / `copy` / `delete`、`permissions` の変更、`+upload`
- git: `pull`、`checkout` / `switch`、`commit`、`push`、`merge`、`reset`、作業ツリーの変更

## 抽出のコツ（ツールの既知の癖）

- **Slack**: 日本語名で `users find` が当たらないことがある。ローマ字でも探す。`search.messages` は期間を `after:YYYY-MM-DD` で絞り、自分の発言（`from:me`）と自分宛てのメンションの両方を見る。`search.messages` は user token が必要で、bot token のプロファイル（`auth status` の `token_type`）では `conversations.history` / `conversations.replies` を使う。根拠には permalink を残す
- **Chatwork**: `list_my_tasks` が空でも、メッセージ中の依頼・約束を拾う。メッセージ取得 API は 1 ルームにつき最新 100 件までしか返さない。期間内に 100 件を超えるルームは「それより古いものは未確認」と探索範囲に書く。差分取得の挙動で前回取得分が返らないことがあるため、取得件数が不自然に少ないときは最新 100 件を強制取得するオプションの有無を確かめる
- **Gmail**: 受信だけでなく送信済み（`in:sent`）も見る。約束・依頼は送信側に残っていることが多い。完了の一次証拠になりやすいのは、受付完了・締結完了・支払完了などの自動通知メール
- **Calendar**: 予定が過ぎていることは実施の証拠にならない。実施の証拠は議事録・フォローアップのメール・Slack などで別に探す
- **Drive**: 成果物の存在は `完了` の一次証拠になりうるが、下書きか最終版かはファイル名・更新日時・共有状態から判断し、断定できなければ `進行中` か `判定不能` にする
- **リポジトリ**: commit・マージ済み PR の差分は一次証拠。リポジトリ内の議事録・メモ・先送り事項の一覧などは補助証拠。根拠は `origin/<default>:<path>:<line>` や commit hash で書く
- 同じ種類の取得（ルームごと・スレッドごとの本文取得など）が 10 回を超えるなら、進捗ログ（開始・各反復・完了・失敗、件数と現在位置）付きスクリプトを `.context/` に書いて実行する
