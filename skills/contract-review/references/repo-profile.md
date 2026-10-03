---
title: 契約レビュープロファイル（repo 側に置く設定）
---

# 契約レビュープロファイル

会社・案件ごとに違う値は repo 側の 1 ファイルにまとめ、repo の `AGENTS.md` から場所を指す。推奨パスは `legal/contracts/contract-review-profile.md`。既存の方針文書（例: `legal/contracts/contract-review-policy.md`）があれば、そこに下記の節を足してプロファイルとして指してもよい。

顧客名・金額・口座などの機密はプロファイルにも書かない。

## キー

| キー | 内容 | 例 |
|---|---|---|
| `company` | 当社の呼称（正式名称の正本ファイルへの参照でもよい） | `README.md の「会社概要」` |
| `default_position` | 通常の立場 | `乙（受託側）` |
| `decision_maker` | 最終判断者の役職 | `代表取締役` |
| `review_mode` | `single` / `multi` と、multi を使ってよい条件 | `single（multi は ADR 承認後）` |
| `escalation` | 冒頭に警告を出す条件と文言 | `全件 代表確認必須` / `100 万円以上は承認必須` |
| `capital_source` | 下請法判定に使う自社資本金の正本ファイル | `company/overview.md` |
| `extra_checklists` | 契約種類ごとの追加チェック（repo 内のファイルか節） | `BPO 業務委託固有チェック`、`暗号資産固有チェック` |
| `house_rules` | 過去のレビューや経営判断で確定した判断基準。position-stances.md より優先する | `NDA の損害賠償上限なしは許容` |
| `own_entry_sources` | 当社側の記入事項（氏名の正字、住所、口座）の正本と、repo に置かないものの扱い | `口座は会計システム上の値を正とする` |
| `existing_reviews` | 過去レビューと交渉メモの場所 | `legal/contracts/reviews/`、`negotiation-notes.md` |
| `review_record_dir` | レビュー記録の保存先 | `legal/contracts/reviews/` |
| `ledger` | 締結時に更新する台帳と手順 | `contract-register.md に追記、交渉メモをアーカイブ` |
| `original_storage` | 原本の保管先（Drive フォルダ規約）と `gws-account` profile | `契約前フォルダ YYYY-MM-DD_相手方_種別/` |
| `templates` | 自社雛形との比較に使うファイル | `legal/contracts/templates/` |

## 書き方の例

```markdown
## 契約レビュープロファイル

- default_position: 乙（受託側）
- decision_maker: 代表取締役
- review_mode: single
- escalation:
  - 全件: 「代表取締役の確認必須」
  - 個人情報・機微情報の取扱い: 「代表取締役の判断が必要」
- capital_source: company/overview.md
- extra_checklists:
  - BPO 業務委託: 本ファイルの「BPO 業務委託固有チェック」
- house_rules: 本ファイルの「判断基準」節
- review_record_dir: legal/contracts/reviews/
- ledger: legal/contracts/active/contract-register.md
- original_storage: Drive 契約前フォルダ（gws-account <profile>）
```
