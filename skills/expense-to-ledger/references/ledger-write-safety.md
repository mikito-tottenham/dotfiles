---
title: 会計システムへの書き込みの安全手順
---

# 会計システムへの書き込み

## 操作の区分

### マネーフォワード クラウド会計（MCP `mfc_ca`）

| 区分 | ツール | 扱い |
|---|---|---|
| 読み取り | `mfc_ca_currentOffice`、`mfc_ca_getTermSettings`、`mfc_ca_getAccounts`、`mfc_ca_getSubAccounts`、`mfc_ca_getTaxes`、`mfc_ca_getDepartments`、`mfc_ca_getJournals`、`mfc_ca_getJournalById`、`mfc_ca_getTransactions`、`mfc_ca_getConnectedAccounts`、`mfc_ca_getTradePartners`、`mfc_ca_getReports*` | 分析・照合のために実行してよい。ページングがある取得は件数をユーザーに確認する |
| 書き込み | `mfc_ca_postJournals`、`mfc_ca_putJournals`、`mfc_ca_postTransactions`、`mfc_ca_postTransactionJournalize`、`mfc_ca_postTradePartners` | 下記の確認手順を通し、ユーザーの明示承認を得てから実行する |
| 実行しない | 削除・取消に類する操作、決算確定・税務申告に関わる操作、承認の無い一括書き込み | ユーザーに画面での操作を依頼する |

認証（`mfc_ca_authorize`）で得たトークンはそのセッション内だけで使い、ファイルやログに書かない。repo に `access_policy` があれば、そちらの許可範囲を優先する。

### freee（freee-mcp / freee API）

- 一覧・詳細の取得（事業所、勘定科目、税区分、口座、取引、経費申請、取引先）は読み取りとして扱う
- 取引（deals）、経費申請、取引先の作成・更新（POST / PUT）は書き込みとして扱い、下記の確認手順を通す
- API の使い方は freee 公式の skill / リファレンス（repo に配備されていればそれ）を参照する

## 書き込み前の確認手順

1. 対象の事業所を読み取り系の操作で確認し、名称を提示する
2. 書き込む内容を表で提示する: 件数、日付範囲、借方合計・貸方合計、勘定科目別の件数と金額、税区分別の件数、要確認として除外した件数
3. 1 件目の payload（取引日、科目、金額、税区分、摘要）を例として見せる
4. ユーザーの明示的な承認（「はい」「実行して」など）を待つ。承認は今回提示した範囲だけに有効で、次の書き込みには再度承認を取る
5. 大量の書き込みはバッチに分け、各バッチの開始・件数・成功・失敗をログに出す。途中で失敗したら止め、成功分と失敗分を報告する。失敗分を別の経路（別ツール・画面操作の自動化）で黙って補わない
6. 書き込み後に読み取り系の操作で件数と合計を照合し、結果を `.context/<task>/` に記録する

## 取引先の新規登録

- 照合して見つからない場合は、表記揺れの可能性も含めてユーザーに確認してから登録する
- 住所・郵便番号は原本に明記されたものだけを使い、推測で補わない
