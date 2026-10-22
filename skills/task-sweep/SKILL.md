---
name: task-sweep
description: Re-derive, read-only, whether the user's own tasks are really done by pulling evidence from every connected source of one organization (Slack, Chatwork, Gmail, Calendar, Drive, and the git repository), then report each task as one of five states with cited evidence. Use before handing work to someone else, when a task list or memo claims items are done or not started, or when asked タスクが本当に終わってるか, タスク照合, タスクの棚卸し, 完了確認, 終わったか確認して, 渡す前に未完了か確かめて. Never sends, drafts, labels, or edits anything.
---

# Task Sweep

ユーザー本人のタスクが「本当に終わっているか」を、繋がっている全ソースから毎回拾い直して判定する。
口頭・メモ・議事録の「済み」「未着手」をそのまま信じず、ソース上の一次証拠で裏付けた状態一覧を出す。
典型的な使いどころは、事務作業を他の担当者へ渡す前に、渡す対象が本当に未完了かを確かめる場面。

## 前提（変えない決定）

- **対象は 1 回の実行で 1 組織。** 読む経路（gws profile、slack-account profile、Chatwork MCP、対象 repo）は作業 repo 側のソースプロファイル（[references/sources-profile-template.md](references/sources-profile-template.md) の雛形。repo の `AGENTS.md` から場所を指す）で決め、別組織のワークスペース・アカウントは読まない。プロファイルが無ければ値をユーザーに確認してから始める。この skill には組織固有の値を持たない
- **台帳を持たない。** 前回の結果を正本として引き継がず、毎回ソースから抽出し直す。前回の `04-report` は「比較用の補助証拠」としてだけ読んでよい
- **手動実行のみ。** scheduler・cron・hook から呼ばない
- **読み取り専用。** 送信、下書き作成、ラベル・既読状態の変更、Chatwork 書き込み、カレンダー変更、Drive 変更、git の commit / push はしない。ソースごとに使ってよい操作は [references/sources-profile-template.md](references/sources-profile-template.md) の範囲に限る

## 入力（すべて任意）

- 確認対象のタスク一覧ファイル: 渡されたら各項目の判定を優先し、加えてソースから見つかった未完了タスクを「新規候補」として出す
- 対象期間: 既定は直近 30 日
- 人物フィルタ: 例「バックオフィス担当が既に着手・完了したもの」を見る

入力が無ければ、期間 30 日・全タスクで進める。確認のために止まらない。

## 手順

artifact は作業中のリポジトリの `.context/task-sweep/<YYYY-MM-DD>/` に置く。書く前に `git check-ignore -q .context/x` で `.context/` が gitignore されていることを確かめ、されていなければ書かずにユーザーへ確認する。
各 artifact は Front Matter に `task: task-sweep`、`phase_or_step`、`created_at` を持ち、**その artifact を保存してから次の Phase へ進む**。各 artifact の書式は [references/output-format.md](references/output-format.md) にまとめてある。

1. **`01-preflight.md`** — ソースプロファイルの値で [references/sources-profile-template.md](references/sources-profile-template.md) の疎通確認をソースごとに実行し、`OK` / `失敗（理由）` を記録する。失敗したソースは別アカウント・別経路へ切り替えず、以後そのソースに依存する判定を `判定不能（ソース不通）` にする。認証の復旧手順は `gws-cli-runner` / `op-cli-runner` の Skill に従い、ここでは再掲しない
2. **`02-candidates-<source>.md`** — ソースごとにタスク候補（依頼・約束・期限・完了報告）を抽出する。ソース単位でサブエージェントへファンアウトしてよい。その場合は読み取り専用の範囲と機密の扱いを指示文に明記し、親には出典つきの構造化結論だけを戻させる。同種の取得が 10 回を超える見込みなら、進捗ログ付きスクリプトを `.context/` に書いて実行する
3. **`03-resolution.md`** — 候補を名寄せし（同じタスクが Slack とメールに出る等）、各タスクの状態を全ソース横断で判定する
4. **`04-report.md`** — 人が読む一覧を [references/output-format.md](references/output-format.md) の形で書き、最終回答でも要点を返す

## 判定ルール

状態は 5 区分だけを使う。

| 状態 | 付けてよい条件 |
|---|---|
| `完了` | 完了を示す一次証拠が 1 つ以上ある（締結通知、受付・完了メール、成果物ファイルの存在、本人や担当者の完了報告など） |
| `進行中` | 着手の一次証拠があり、完了の証拠が無い。誰が・どこまで進めたかを書く |
| `未着手` | 探した範囲に着手の証拠が無い。根拠として「どこを探したか」を書く |
| `不要になった` | 取りやめ・不要の決定が一次証拠で確認できる |
| `判定不能` | 証拠が食い違う、ソースが不通、または証拠が足りない |

- 「やると言った」「依頼した」は完了ではない。依頼の送信は、相手の着手を示す証拠にもならない
- 証拠どうしが食い違うときは `判定不能` にし、食い違う証拠を両方とも出典つきで書く（例: ある日に「受ける」と返信済み vs 後日に取りやめを決めた記録）
- メモ、auto memory、議事録、入力のタスク一覧の記述は補助証拠として扱う。一次証拠と矛盾したら一次証拠を優先し、矛盾があったことを明記する
- 推測で事実を作らない。証拠の無い項目は `判定不能` か `未着手（根拠: 〜を探したが無い）` とし、探した範囲を残す。これは、台帳を持たない設計では「見落とし」と「本当に無い」を後から区別できる手がかりが探索範囲の記録しかないためである

## 機密

- 口座番号、認証情報、ワンタイムコード、個人番号、パスワードは artifact に転記しない。必要なら「〇〇の口座情報あり（メール件名・日付）」のように所在だけを書く
- メール本文などの生データを `.context/` に保存した場合は、その場所と「不要になったら削除」を `04-report` と最終回答に明記する
