---
title: 経費プロファイル（repo 側に置く設定）
---

# 経費プロファイル

会社ごとの値は repo 側の 1 ファイルにまとめ、repo の `AGENTS.md` から場所を指す。推奨パスは `governance/expense-profile.md` または `docs/expense-profile.md`。既存の skill や方針文書に値がある場合は、そこへの参照で済ませてよい。

フォルダ ID は機密ではないが、会社の Drive 構造を表すので private repo に置く。口座番号・カード番号・個人の住所は書かない。

## キー

| キー | 内容 |
|---|---|
| `company` | 会社名（略称でよい） |
| `gws_profile` | Drive / Gmail 操作に使う `gws-account` profile |
| `mail_sources` | 領収書が届くメールアカウントと、そのアカウントでの取り込み方法（Apps Script のプロジェクトを使うなら、その場所と entry point） |
| `expense_year` | 証憑の格納に使う年度の区切り（例: 10 月〜9 月）。決算期と違う場合は両方を書く |
| `drive_folders` | 経費ルート、年度、月フォルダ、アーカイブ、対象外フォルダの ID 表 |
| `naming_exceptions` | 命名規約の会社固有の例外（ベンダー名の表記など） |
| `ledger_system` | `moneyforward` / `freee`、事業所の確認方法 |
| `account_rules` | ベンダー・種別 → 借方勘定科目の推定ルール。勘定科目コードを使う場合はそのマスタの場所 |
| `credit_assumption` | 貸方の既定（立替なら役員借入金・未払金など）と、その前提 |
| `tax_rules` | 税区分の既定（国内 10%、海外は対象外など）と未検証事項 |
| `masters` | 取り込み前検証に使うマスタ（勘定科目、部門、部門マッピング）のパス |
| `reconcile_tolerance` | 合計突合の許容差 |
| `access_policy` | 会計 MCP の読み取り / 書き込みの許可範囲を定めた文書 |
| `output_dir` | 3 点セットの保管先（Drive の年度フォルダなど） |

