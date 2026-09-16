---
title: gws-account プロファイル運用
updated_at: 2026-09-15
source: 旧 agents-common.md「Google Workspace (gws) アカウント運用」節から移設（ADR-0062）
---

# gws-account プロファイル運用

常時ルール（agents-common.md に残る下限ルール）: gws は必ず `gws-account <profile> ...` で実行し、素の `gws` はアカウント境界のある作業で使わない（ADR-0048）。実メールアドレスは git 管理下の文書やコミットメッセージに書かない。

## プロファイル対応（この環境）

| profile | 組織 | 備考 |
|---|---|---|
| `taskell` | taskell.ai | Taskell Management 共有ドライブを含む |
| `ges-claude` | yoake-entertainment.jp | Claude の MCP コネクタ（Gmail / Drive / Calendar / Slack）と同じアカウント |
| `twinplanet` | twinplanet.co.jp | TWIN PLANET 作業 |
| `amicitia` | amicitia.jp | 個人 Gmail のカレンダーに owner 権限を持つ |

- 実メールアドレスは `gws-account <profile> auth status` の `user` フィールドで実行時に確認する
- 個人 Gmail アカウントには専用プロファイルが無い。個人カレンダーの操作は `amicitia` 経由で行う（2026-09-09 実測）

## 再認証

- 各プロファイルの OAuth クライアントは所属組織の internal 設定。別組織のアカウントを選ぶと `403 org_internal` になる。他環境（Manzoku）の作業アカウントはこの環境のブラウザでは選択できないため、リポジトリ文書に書かれた作業アカウント名をそのまま再ログイン先として案内しない
- 再認証をユーザーへ依頼する前に、`gws-account <profile> auth status` で有効な別プロファイル（`token_valid`）による代替可否を確認する。1 プロファイルの失効は全プロファイルの失効ではない。ただし別アカウントへの自動切り替えを復旧経路にしない
- 依頼するときは、対象プロファイル（`gws-account <profile> auth login` の形まで）と、ブラウザのアカウント選択画面で選ぶべきメールアドレスを明示する

## カレンダー共有 ACL

- `calendar-acl plan` で差分を確認してから `calendar-acl apply` で変更する。`gws calendar acl` の直接実行や Web UI での個別変更を混ぜない
- ポリシー実値は 1Password 管理で `opmaterialize restore` で復元する（ADR-0059）
- 外部宛 ACL は `acl list` で実効 role を再確認する
