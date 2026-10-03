---
name: multi-account-scheduling
description: Schedule across several Google accounts and organizations — compute common free slots from free/busy over multiple gws-account profiles while stating which calendars were actually read, adjust Google Calendar booking pages and free/busy sharing (re-checking effective ACL roles for external recipients), and draft the reply. Sending email, creating events, saving booking pages, and changing sharing all wait for explicit user approval. Use when asked to 空いてるスロットを出して, 〇〇さんと私の空き時間, 日程調整して, リスケして, 予約リンクを更新, 予約ページにアドレス追加, 会議リンクを私発信で, カレンダー共有を設定, or 候補日を返信する文面.
---

# multi-account-scheduling

本人が複数の組織・アカウントのカレンダーを併用している前提で、空き枠の算出から返信文案までを扱う。読み取り（空き枠の算出、ACL の確認）は確認なしで進めてよい。外部に見える変更（メール送信、予定作成・招待、予約ページの保存、共有設定の変更）は、内容を提示してユーザーの明示承認を得てから 1 操作ずつ実行する。

## 正本の参照先

- 会社・組織とアカウントの対応、MCP コネクタがどのアカウントに接続しているか: 作業ルートの `AGENTS.md`（「アカウント境界」節）
- `gws-account` の profile 一覧、再認証、カレンダー共有 ACL の運用: `gws-cli-runner` skill の `references/account-profiles.md`
- 上記の表をこの skill に写さない。毎回参照する

## Step 0: 対象とアカウントを決める（preflight）

1. 依頼から参加者と、それぞれの予定がどのカレンダーにあるかを整理する。本人については、関係する組織のカレンダーをすべて対象にする
2. 正本の対応表から、各カレンダーを読む `gws-account` profile を決める。迷ったらユーザーに確認する。MCP のカレンダーコネクタは接続アカウントが限られるので、横断の算出には使わない
3. 使う profile ごとに `gws-account <profile> auth status` を実行し、`user` が目的の組織であること、token が有効であることを確かめる。失効していたら `gws-cli-runner` の手順で同じ profile を復旧する。別の profile へ黙って切り替えない
4. 相手方（社外の人）のカレンダーは、`freeBusyReader` 以上で共有されていない限り読めない。読めない相手の予定は推測しない

## Step 1: 共通の空き枠を出す

```bash
python3 <skill-dir>/scripts/free_slots.py \
  --source <profile-A> --source <profile-B>:primary --source <profile-A>:<共有されたカレンダー ID> \
  --from YYYY-MM-DD --to YYYY-MM-DD --start-hour 10 --end-hour 18 --slot-min 30 --buffer-min 15 \
  > .context/<task>/free-slots.md
```

- `--source <profile>` はその profile が購読している全カレンダー、`:primary` は主カレンダーだけ、`:<ID>` は特定のカレンダー
- 出力の「参照したカレンダー」表を必ず確認する。exit 3 は参照できなかったカレンダーがあることを示す
- 回答には「どのカレンダーを参照できたか / できなかったか」を必ず書く。相手方のカレンダーを参照できていない場合は「こちら側の空きのみ」と明記し、相手の空きとして提示しない
- 移動時間・対面の前後余白が要る場合は `--buffer-min` で足す。オンラインと対面で分けたいときは条件を変えて 2 回出す
- カレンダー ID や予定の中身を git 管理ファイルに書かない。結果は `.context/<task>/` に置く

## Step 2: 予約ページ・共有設定を調整する（必要な場合）

Google カレンダーの予約スケジュール（予約ページ）を使う場合の制約と手順は [references/booking-pages.md](references/booking-pages.md)。要点:

- 予約ページの設定に API は無い。画面での操作になるので、ブラウザ操作で行う場合も保存の前に変更内容を提示して承認を得る。ユーザー本人に操作してもらう方が早い場合はそう案内する
- 別組織のカレンダーを空き判定に入れるには、そのカレンダーを予約ページの所有アカウントへ `freeBusyReader`（予定の時間枠のみ表示）で共有し、購読してから予約ページの「空き状況を確認するカレンダー」に追加する
- 共有設定の変更は `calendar-acl plan` で差分を出し、ユーザーの承認後に `calendar-acl apply` で反映する。`gws calendar acl` の直接実行や画面での個別変更を混ぜない
- 外部宛（他組織・個人アドレス）の共有は、変更の前後に `acl list` で実効 role を確認する

  ```bash
  gws-account <profile> calendar acl list --params '{"calendarId":"<calendar-id>"}' --format json
  ```

  期待した role（通常は `freeBusyReader`）より強い権限が付いていたら、apply の結果を成功扱いにせず報告する

## Step 3: 返信文案を作る

- 候補は 3〜5 枠を目安に、日付・曜日・時刻・タイムゾーン・所要時間・形式（オンライン / 対面）を書く。予約ページを使う場合はリンクを案内する
- 敬語と構成は `japanese-business-writing` に従う
- 送るのはユーザー。下書きをメールボックスに作るのも、ユーザーが求めた場合に限る。その場合も送信元アカウントが目的の組織であることを確かめる

## Step 4: 予定を作る（承認後）

- 「私発信で」「当社名義で」など主催者の指定があれば、その名義のアカウントで作る。主催者は作成したカレンダーの所有者に固定され、後から変えられない
- 作成前に、主催アカウント、件名、日時、参加者、会議リンクの有無、招待メールを送るかを提示して承認を得る
- 作成後は予定を取得し直して、日時・参加者・会議リンクが意図どおりかを確認する。リスケは既存予定の更新として扱い、新規作成と既存予定の削除を勝手に組み合わせない

## やらないこと

- 参照できなかったカレンダーの予定を「空いている」とみなす
- 認証が切れた profile の代わりに、別アカウントや MCP コネクタで黙って算出する
- 承認なしにメール送信、予定作成・更新、予約ページの保存、共有設定の変更をする
