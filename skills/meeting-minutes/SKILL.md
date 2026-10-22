---
name: meeting-minutes
description: "Turn a meeting recording or transcript into repo-conformant minutes: retrieve transcripts and summaries from Soundcore Work / Soundcore AI (ai.soundcore.com) through an authenticated browser session, map speakers, normalize proper nouns, write the minutes in the target repo's own format and location, update its index, and extract decisions and action items. Use when asked to Soundcoreから議事録を取得, 録音の文字起こしを取得, 議事録として保存, 文字起こしです保存して, 議事録にして, 話者を対応付けて, 決定事項とタスクを抜き出して, or この会議のネクストアクション."
---

# Meeting Minutes

録音・文字起こしを受け取り、保存先 repo の規約どおりの議事録にして索引へ載せ、決定事項とタスクを取り出すまでを扱う。Soundcore Web UI からの取得が要る場合は、[references/soundcore-retrieval.md](references/soundcore-retrieval.md) の手順で取得してから下の手順に入る。

ユーザーが「文字起こしファイル + 話者の対応 + 保存して」だけを渡しても、定型の追加指示なしで最後まで進められることをこの skill の完了基準とする。

## 共通の規則

- 文字起こしの内容を `/tmp` や無関係なフォルダへ書かない。中間物は作業 repo の `.context/<date>-minutes-<slug>/` に置く。transcript を repo ファイルや `.context/` に残すのは、ユーザーが file artifact を求めた場合、または repo の規約が全文保存を定める場合だけ
- 文字起こしに無い日時・参加者・担当・期限・出典は `未確認` と書く。推測で埋めない
- 内容は文字起こしにあることだけで書く。過去の会話や記憶から文脈を補わない（ユーザーが別資料との統合を指示した場合を除く）

## 入力の受け取り

| 入力 | 扱い |
|---|---|
| Soundcore の取得結果 | [references/soundcore-retrieval.md](references/soundcore-retrieval.md) で取得したものをそのまま一次情報にする。録音のタイトル・日時・`note_id`（または `https://ai.soundcore.com/file/<note_id>`）を出典として控える |
| 貼り付けテキスト | 一次情報にする。出典は「チャット貼り付け」と記録する |
| ファイル（`~/Downloads/*.txt`、docx、md など） | docx は markitdown 等でテキスト化してから読む。ファイル名に会議名・日付があれば候補として使う |
| 音声ファイルだけ | この skill の範囲外。repo に文字起こしの代替手順があればそれに従い、無ければユーザーに確認する。音声だけの文字起こしは話者分離できない前提で扱う |

- 同じ依頼に複数の会議が含まれる場合は、会議ごとに 1 件ずつ最後まで処理する。件数が多く長くなる場合は handoff skill で区切る
- 書き始める前に、その会議が取り込み済みでないかを確かめる。`git fetch` のあと、**origin の既定ブランチ**（`origin/<default>`）を録音の識別子（Soundcore の URL・`note_id`）、会議名ラベル、開始時刻（秒まで）で `git grep` する。既存の議事録は会議名ラベルと違う題で置かれていることが多いため、識別子と時刻でも引く。ローカルのチェックアウトは別ブランチや遅れた main のことがあり、そこと突き合わせると取り込み済みを新規と誤判定する（2026-10-08 に、99 件中 81 件の取り込み済みを新規と誤判定した）。repo が統合・移転して正本が別 repo へ移っていないかも、ADR と README で確かめる

## 手順

### 1. 保存先 repo の規約を読む

保存先 repo（作業ディレクトリ、またはユーザーが指定した repo）の規約を、書き始める前に読む。議事録の書式・保存先・機密の扱いは repo ごとに違うため、この skill に書かれた既定より repo の文書を優先する。

読む順番と、拾う項目のチェックリストは [references/repo-profile.md](references/repo-profile.md) にある。読み終えたら、拾った項目を `.context/<date>-minutes-<slug>/01-profile.md`（Front Matter: `task` / `phase_or_step` / `created_at`）にまとめる。

- repo に議事録の規約が見当たらない場合は、保存先と命名をユーザーに確認する。書式は [references/repo-profile.md](references/repo-profile.md) の既定書式（[references/output-formats.md](references/output-formats.md) の Standard Minutes を基にしたもの）を使い、新しい規約を repo 文書へ書き足すことはしない
- 分類先（会議体ごとのサブフォルダなど）を判定基準で決めきれない場合は、ユーザーに確認する

### 2. 話者を対応付ける

- `Speaker1` / `speaker 2` などの番号は会議ごとに振り直される。前回の対応を流用しない
- ユーザーが対応を示した場合はそれに従う。示されていない場合は、呼びかけ、依頼する側か受ける側か、既存の議事録との整合から推定し、根拠を 1 行ずつ添える
- 対応表（ラベル / 人物 / 根拠 / 確度）を `01-profile.md` に残す。確度が低い話者がいるときは、議事録を書く前にユーザーへ確認する
- 文字起こしに話者ラベルが無い場合は、名前を作らずに発言内容だけで書く

### 3. 固有名詞を正規化する

- repo に補正辞書があれば、先に適用する
- 辞書に無い誤変換は、repo の既存文書を `rg` で突き合わせてから直す。推測だけで確定させない
- 直した内容は、repo の書式に「表記上の注意」に当たる欄があればそこへ書く。直しきれない箇所は本文に「表記ママ」「要確認」と残し、末尾の要確認事項に集める
- 新しく見つかった誤変換は、辞書の追記ルール（載せてよい範囲・載せない情報）に従って追記する。追記してよいか迷う場合は追記案として報告するに留める

### 4. 議事録を書く

- repo が指定する書式・テンプレート・Front Matter の必須キーに従う。メタデータは本文に書かず Front Matter に置く
- 決定事項とアクションは、本文に明示された発言を根拠にする。推定で補ったものは「推定」と明記する
- Soundcore の AI 要約と文字起こしが食い違う場合は、文字起こしを正として食い違いを抽出メモに書く。別々のアクションは、文字起こしが明らかに支持する場合だけ 1 つにまとめる
- 口頭由来の数値・日付は、repo にラベル規約があればそれに従い、無ければ `要確認` を付ける
- repo の機密規約（実名・金額・関係性の評価・個人連絡先を本文に載せない、raw は git 管理外、など）を守る。規約で本文に載せられない情報は、repo が指定する git 管理外の置き場へ分ける
- 文字起こし全文も保存する規約の repo では、全文は要約・整形せず原文のまま保存し、話者ラベルとタイムスタンプを Soundcore の表示どおりに残す

### 5. 読みやすさを整える

保存前に、議事録の本文（要約・議論メモ・決定事項・アクションの文）を `natural-japanese` のクイックモードで整える。

- 対象は議事録本文だけ。文字起こし全文、引用した発言、固有名詞、数値、日付、担当、期限は変えない
- 文意が変わる書き換えはしない。読みやすさのために事実関係が曖昧になる場合は元の表現を残す
- repo の文体規約（敬語の使い方、常体・敬体など）がある場合は、そちらを優先する

### 6. 索引と台帳を更新する

- repo の索引（議事録フォルダの README、一覧ファイルなど）に 1 行追記する。書式は既存の行に合わせる
- タスク台帳の更新タイミングを repo が決めている場合（例: 定例ハーネスの確定時だけ更新する）は、台帳を直接書き換えず、議事録側や別レポートに「台帳への反映案」として書く
- 正本と複製の repo が文書で決まっている場合だけ、複製先への配置を行う。決まっていない repo へは複製しない
- 外部のタスク管理サービスへの登録・更新はしない。必要なら登録案を報告に書く

### 7. 検証してコミットする

- Front Matter の必須キーがそろっていること
- 索引のリンクが切れていないこと（repo にリンクチェックの script があればそれを使う）
- 文字起こし全文を保存した場合は、元のテキストと保存したファイルの本文が一致すること（文字数の比較など。Soundcore からの取得分は [references/soundcore-retrieval.md](references/soundcore-retrieval.md) の checksum 検証）
- repo の機密規約に反する情報（規約で除外すべき実名・金額・連絡先・secret）が git 管理下のファイルに入っていないこと
- `git diff` で、この会議の議事録・索引・辞書以外の変更を含めていないこと

検証が済んだら、グローバルルールに従ってその repo でコミットし、push・PR 作成・マージまで進める。

## 最終報告

[references/repo-profile.md](references/repo-profile.md) の「最終報告の型」に従い、次をまとめて返す。

- 出典（録音タイトルと日時、`note_id` / URL、またはファイル名）
- 保存したファイルの path と索引の更新箇所
- 話者の対応表と、確度の低い対応
- 決定事項とアクション（担当・期限・根拠の発言時刻）
- 要確認事項、辞書への追記・追記案、台帳への反映案
- 抽出の欠落（読めなかった文字起こし区間、話者ラベル欠落、部分読み込み）
- コミットのハッシュ（コミットした場合）

議事録だけを求められ、保存先 repo が無い場合は、[references/output-formats.md](references/output-formats.md) の Standard Minutes で回答する。

## 範囲外

- 会議前の準備資料づくり（`meeting-prep-brief`）、議事録をもとにした提案書・報告書の作成: それぞれの作業の skill
- 議事録の対外送付やチャット投稿: ユーザーの明示指示がある場合だけ、別作業として行う

## Validation

When updating this skill, run:

```bash
scripts/skill-quick-validate skills/meeting-minutes
```
