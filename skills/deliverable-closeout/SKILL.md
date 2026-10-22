---
name: deliverable-closeout
description: Close out finished work and deliverables in one pass. Confirm target files, commit, push, open the PR and merge it once checks pass without per-step confirmation, ask once for the Google Drive upload, save final PDF/Office outputs to the organization's Drive through gws-account with md5 de-duplication, add Drive links to the repository index, and finish with a copy-paste URL list. Use when asked to 締めて, PRして, GHへ入れて, Driveに入れてリンク貼って, 成果物をDriveに保存して, 索引にリンクを追加して, or そのままコピペできるリンクで.
---

# Deliverable Closeout

作業の締めを途中で止まらずに終わらせるための手順。commit・push・PR 作成・マージは作業指示が承認を兼ねるため確認を挟まず、承認が必要な Drive 保存だけを 1 回まとめて提示し、承認後に実行する。

## 正本と前提

- Drive 保存先・対象外・重複判定のルールは作業ルートの `AGENTS.md` の「成果物（PDF / pptx / docx / xlsx）の Drive 保存」節を毎回読み直し、repo の AGENTS.md / README に明示された置き場があればそちらを優先する（どちらにも無ければユーザーに確認する）。gws は `gws-account <profile> ...` で実行し、profile の対応と再認証は `gws-cli-runner` の `references/account-profiles.md`、Drive の API 形は同 `references/drive.md` に従う。MCP の Drive コネクタは別アカウント接続のことがあるため使わない
- commit・push・PR 作成・マージの規則（作業指示が承認を兼ねる範囲、チェック完了と `mergeStateStatus` が `CLEAN` の確認、状態変更コマンドの単独実行、`ghrun gh`、禁止操作）は agents-common.md の git / PR / マージ節（ADR-0065 / ADR-0071）を正本とし、ここでは再掲しない。ユーザーが「PR まで」などと範囲を限ったらそれに従う
- 中間成果物は作業 worktree の `.context/<YYYY-MM-DD>-closeout/`（以下 `$D`）に置き、各 Step の artifact を次 Step へ進む条件にする

## Workflow

1. **対象の確定**（`$D/00-targets.md`）
   - `git status --short --branch` と `git branch --show-current` で対象ブランチを確認する（並行セッションが同じ checkout を使うことがある）。既定ブランチ上なら作業用のローカルブランチを切る
   - この作業で意図して変更したファイルだけを列挙する。他セッションの変更や無関係な差分は含めない
   - 成果物ファイルは `scripts/deliverable_inventory.py --root <repo> --out $D/01-inventory.json` で列挙し、最終版と対象外（`.context/` の途中版、外部から受領した原本、worktree / バックアップの重複）を分ける。件数が多い分類は agent-orchestrator の role 解決でサブエージェントへ渡してよい
2. **検証・commit・PR 作成**
   - テスト、リンクチェック、秘密情報・実名の混入確認を済ませてから、パスを明示して stage し commit する（`git add -A` は使わない）。確認は挟まない
   - 続けて `git -C <repo> push -u origin <branch>` → `ghrun gh pr create ...` を単独で実行し、各結果を確かめてから次へ進む
3. **Drive 保存計画**（承認前に済ませる読み取り作業）
   - 組織 → profile → 保存先を正本ルールから決め、`$D/10-upload-plan.json` を作る（形式は `references/upload-plan.md`）
   - 重複判定用に `scripts/drive_index.py --profile <p> --out $D/drive-index-<p>.json`（共有ドライブは `--drive-id`）を取り、フォルダ規約は `scripts/drive_ls.py` で確かめる
   - `scripts/drive_upload.py --plan $D/10-upload-plan.json --results $D/11-upload-dryrun.json --index $D/drive-index-<p>.json --dry-run` で、新規アップロード・既存リンク流用・conflict を分ける
4. **Drive 保存の承認**（1 回だけ提示する。Drive に保存する成果物が無ければ Step 4〜6 は飛ばす）
   - 次の形で示し、明示の承認を待つ。承認はここに書いた操作だけに効く。内容が変わったり項目が増えたりしたら、その分だけ改めて承認を取る

     ```text
     承認をお願いしたい操作
     - Drive 保存: 新規 N 件（<profile> / <保存先フォルダ>）、既存リンク流用 M 件、conflict K 件（上書きしない）
     （承認後、<索引ファイル> に Drive リンク N+M 行を追加して commit し、同じブランチへ push します。PR <URL> に載ります）
     ```
5. **Drive 保存の実行**（承認後、1 コマンドずつ）
   - `scripts/drive_upload.py --plan ... --results $D/12-upload-results.json --index ...` を単独で実行し、結果を確かめてから次へ進む
   - auto mode classifier に拒否されたら再試行も別の道具での迂回もせず、拒否された操作と理由を報告して止まる
   - 銀行口座などの個人情報を含む書類のアップロードが PII として拒否された場合は、その書類を保留にしてユーザーに確認する。MCP コネクタ・ブラウザ・別 profile での代替アップロードはしない
   - `conflict` / `md5-mismatch` / `error` は上書き・再送せず、ユーザーの判断を待つ
6. **索引へのリンク追記**
   - 既存の出力索引、無ければ `docs/` の索引ファイル + README から 1 行。書式と実名の扱いは `references/upload-plan.md` の「repo 索引の書式」と repo の AGENTS.md に従う
   - `scripts/check_links.py --worktree <repo> [--forbidden-file $D/forbidden.txt]` で相対リンク・Drive URL 件数・禁止語・秘密情報らしき語を確認し、commit して push を単独で実行する
7. **マージ**
   - `ghrun gh pr checks <number> --repo <slug> --watch` でチェックの完了を待ち、`ghrun gh pr view <number> --repo <slug> --json mergeStateStatus` が `CLEAN` なら、リポで許可されている方式で `ghrun gh pr merge <number> --repo <slug> --merge|--squash|--rebase` を単独で実行する（CI の無いリポはコンフリクトが無ければ可）
   - `CLEAN` にならない、またはユーザーが「PR まで」などと範囲を限った場合はマージせず、理由を報告に書く。`--admin`・`--auto`・`--delete-branch` は使わない
8. **URL 一覧で締める**
   - 最終返答の末尾に、そのままコピペできる一覧を付ける: PR URL とマージ結果、Drive リンク（`scripts/drive_upload.py --results $D/12-upload-results.json --links` の出力）、commit ハッシュ、保留・未実施の項目とその理由
   - 実行結果は `$D/90-result.md`（task / phase_or_step / created_at の Front Matter 付き）に残す

## してはいけないこと

- 承認の前に Drive 書き込みをする、または 1 回の承認を列挙外の操作や次回作業へ広げる
- チェックが未完了・失敗、または `CLEAN` でない PR をマージする
- ブランチ削除・アーカイブなど、依頼されていない後片付けをする
- Drive の共有設定を変える。ファイルはフォルダの権限をそのまま継承させる
- ローカルの原本を削除・移動する
- 顧客・取引先・個人の実名、メールアドレス、口座、金額を repo の索引やコミットメッセージに書く（repo 文書が実名を許す領域を除く）

## Scripts

すべて Python 標準ライブラリだけで動き、進捗と失敗を標準出力にログする。Drive 呼び出しは `gws-account` 経由で、失敗は 3 回まで待機付きで再試行し、最後のエラーを記録する。

| script | 用途 | 副作用 |
|---|---|---|
| `scripts/deliverable_inventory.py` | 成果物の列挙（git 状態・md5） | なし |
| `scripts/drive_index.py` | Drive のファイル一覧（md5 付き） | なし |
| `scripts/drive_ls.py` | フォルダ直下の確認 | なし |
| `scripts/drive_upload.py` | 計画に沿ったアップロード、`--dry-run`、`--links` | 承認後のみフォルダ作成・アップロード |
| `scripts/check_links.py` | 索引追記の検査 | なし |
