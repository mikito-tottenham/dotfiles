---
name: contract-review
description: Review a contract (NDA, service agreement, outsourcing, license, memorandum) from our position as client (甲・委託側) or contractor (乙・受託側), using a shared checklist, position-based stances, optional independent multi-reviewer runs, and a repository profile for ledgers, escalation thresholds, and house rules. Advisory only, never legal advice or signing. Use when asked to 契約書をレビューして, この契約を確認して, NDAをチェックして, 業務委託契約を見て, 受注契約・発注契約を確認, or when a contract PDF or an e-contract notice (CloudSign, DocuSign, GMOサイン) arrives — before giving any opinion on it.
---

# contract-review

契約書を受け取ったら、所感を述べる前にこの手順に入る。PDF を開いて「サインして大丈夫」と口頭で答えることはしない。

本 skill は骨格（入力の取り方、共通チェックリスト、立場ごとの標準判断、複数レビュアーの統合、報告形式）だけを持つ。台帳の場所、エスカレーション基準、自社の資本金、業界固有のチェック、過去の判断基準は repo 側の **契約レビュープロファイル** に置く。

## 引数

| 引数 | 値 | 既定 |
|---|---|---|
| 立場 | `甲` / `委託側` または `乙` / `受託側` | プロファイルの `default_position`。無ければユーザーに確認する |
| モード | `single` / `multi` | プロファイルの `review_mode`。無ければ `single` |
| 対象 | ファイルパス、Drive / Docs URL、本文テキスト | 必須 |

当社が当事者でない契約の参考レビューを頼まれたら、立場を `参考（非当事者）` とし、有利度の評価は `N/A` にする。

## 前提: 守ること

- 本レビューは AI による助言で、法的助言ではない。最終判断は人（プロファイルの `decision_maker`）が行う
- 署名・締結の判断と操作には関与しない
- 法的リスクが高い条項は弁護士への相談を推奨する
- 契約書の機密情報（金額の詳細、口座、個人の住所・電話・マイナンバー）を repo の git 管理ファイルに書かない。原本は Drive に置く
- 契約書本文やプロンプトは `.context/contract-<相手方略称>/` の実ファイルで受け渡し、コマンド引数や here-doc に展開しない
- 外部 CLI のレビュアーに本文を渡すときは、個人情報を必要最小限に絞る。機密性が極めて高い契約では multi モードを使わず、ユーザーに相談する

## 手順

### Step 0: プロファイルを読む

repo の `AGENTS.md` または `CLAUDE.md` が指す契約レビュープロファイルを読む。キーの一覧は [references/repo-profile.md](references/repo-profile.md)。

- プロファイルが無い repo では、ユーザーに立場・判断者・記録先を確認し、記録は `.context/contract-<相手方略称>/` に留める
- プロファイルに既存レビュー履歴や交渉メモの場所があれば、同じ相手方の過去レビューを先に確認する

### Step 1: 本文を取得する

`.context/contract-<相手方略称>/ocr.txt` に保存し、ユーザーに提示して正確性の確認を得てから Step 2 へ進む。本文テキストを直接受け取った場合だけ確認を省ける。

| 優先 | 入力 | 方法 |
|---|---|---|
| 1 | 原文テキスト（docx / PDF）をユーザーから受領 | 最優先で依頼する |
| 2 | テキスト埋め込み PDF | `pdftotext "<file.pdf>" .context/contract-<略称>/ocr.txt` |
| 3 | `.docx` / `.doc` | `textutil -convert txt -stdout "<file>" > .context/contract-<略称>/ocr.txt` |
| 4 | スキャン PDF・画像・文字化け PDF | `pdf-extract` skill に委譲する（プロンプト: 契約書を忠実に書き起こす、推測・補完しない） |
| 5 | Google Docs / Drive | `gws-cli-runner` の手順で、プロファイルが指す `gws-account` profile を使って取得する |
| 禁止 | 親エージェントの画像認識による日本語 OCR | 会社名・金額・条項の誤読が致命的になるため使わない |

- 読めない箇所は `[不明瞭: 候補A / 候補B]` と書き、推測で埋めない
- ローカル受領した原本は、プロファイルの `original_storage` に従って Drive へ保管する（既に Drive にある、またはユーザーが不要と言った場合を除く）。保管はアップロードを伴うので、実行前にユーザーの了承を得る

### Step 2: 基本情報と契約種類を判定する

契約の種類、当事者、目的・対象業務、金額の有無とレンジ、期間、当社側の契約名義（プロファイルに名義の扱いがあればそれに従う）を特定する。契約種類に応じて、共通チェックリストに加える追加チェック（プロファイルの `extra_checklists`）を決め、出力冒頭に明示する。

### Step 3: レビューする

- 共通チェックリスト A〜J と下請法（中小受託取引適正化法）の適用判定: [references/checklist.md](references/checklist.md)
- 立場ごとの標準判断: [references/position-stances.md](references/position-stances.md)。プロファイルの `house_rules` が同じ論点を扱う場合はプロファイルを優先する
- 各指摘には条項番号・問題点・推奨対応を付け、高 / 中 / 低に分ける。欠落条項も挙げる

`multi` モードでは、独立したレビュアーを並べてから統合する。手順は [references/multi-reviewer.md](references/multi-reviewer.md)。

### Step 4: 報告する

[references/output-format.md](references/output-format.md) の形式で日本語で出力する。冒頭にエスカレーション警告（プロファイルの `escalation` に該当するもの）と、助言であって法的助言ではない旨を置く。

### Step 5: 記録する

プロファイルの `review_record_dir` に `YYYY-MM-DD-<相手方>-review.md` で保存する。Front Matter に `review_date`、`counterparty`、`contract_type`、`our_position`、`reviewers`（実行時のモデル ID）、`prior_review` を入れる。同名ファイルがあれば追記か `-v2` かをユーザーに確認する。機密は記録に残さない。

締結が確定したら、プロファイルの `ledger` の手順で台帳を更新する。署名済み原本の配置は人が行う。

## やらないこと

- skill を通さずに「サイン OK」「リスクは低い」と答える
- 外部レビュアーの指摘を、プロファイルの判断基準と突合しないまま採用する、または黙って捨てる
- モデル名・effort・CLI フラグをこの skill やプロファイルに書く（`agent-orchestrator/rules/model_registry.yaml` で解決する）
