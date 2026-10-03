---
name: deliverable-closeout
description: Close out finished work and deliverables in one pass. Confirm target files, commit, bundle every approval-gated step (push, PR, Google Drive upload, index-link commit) into a single approval request, save final PDF/Office outputs to the organization's Drive through gws-account with md5 de-duplication, add Drive links to the repository index, and finish with a copy-paste URL list. Use when work or a deliverable is ready to wrap up. Use when asked to 締めて, PRして, GHへ入れて, Driveに入れてリンク貼って, 成果物をDriveに保存して, 索引にリンクを追加して, or そのままコピペできるリンクで.
---

# Deliverable Closeout

作業の締めを 1 回の承認で終わらせるための手順。commit はルール上確認不要、push・PR・Drive 保存は承認が必要なので、承認が要る操作をまとめて 1 回だけ提示し、承認された操作を 1 つずつ単独で実行する。

## 正本と前提

- Drive 保存先・対象外・重複判定のルールの正本は `~/Claude/AGENTS.md` の「成果物（PDF / pptx / docx / xlsx）の Drive 保存」節。毎回読み直し、repo の AGENTS.md / README に明示された置き場があればそちらを優先する。どちらにも無い場合は保存先をユーザーに確認する
- gws は必ず `gws-account <profile> ...` で実行する。profile と組織の対応、再認証の依頼方法は `gws-cli-runner` skill の `references/account-profiles.md`、Drive の API 形は同 `references/drive.md` を参照する。Claude の MCP Drive コネクタは別アカウント接続のことがあるため使わない
- git の規約（agents-common）: commit は確認不要。push・PR 作成・merge はチャットでの明示承認が操作ごとに必要。状態変更コマンドは `&&`・`;`・パイプで連結せず単独で実行する。gh は `ghrun gh` で呼ぶ
- 中間成果物は作業 worktree の `.context/<YYYY-MM-DD>-closeout/`（以下 `$D`）に置き、各 Step の artifact を次 Step へ進む条件にする

## Workflow

1. **対象の確定**（`$D/00-targets.md`）
   - `git status --short --branch` と `git branch --show-current` で対象ブランチを確認する（並行セッションが同じ checkout を使うことがある）。既定ブランチ上なら作業用のローカルブランチを切る
   - この作業で意図して変更したファイルだけを列挙する。他セッションの変更や無関係な差分は含めない
   - 成果物ファイルは `scripts/deliverable_inventory.py --root <repo> --out $D/01-inventory.json` で列挙し、最終版と対象外（`.context/` の途中版、外部から受領した原本、worktree / バックアップの重複）を分ける。件数が多い分類は agent-orchestrator の role 解決でサブエージェントへ渡してよい
2. **検証と commit**
   - テスト、リンクチェック、秘密情報・実名の混入確認を済ませてから、パスを明示して stage し commit する（`git add -A` は使わない）。確認は挟まない
3. **Drive 保存計画**（承認前に済ませる読み取り作業）
   - 組織 → profile → 保存先を正本ルールから決め、`$D/10-upload-plan.json` を作る（形式は `references/upload-plan.md`）
   - 重複判定用に `scripts/drive_index.py --profile <p> --out $D/drive-index-<p>.json`（共有ドライブは `--drive-id`）を取り、フォルダ規約は `scripts/drive_ls.py` で確かめる
   - `scripts/drive_upload.py --plan $D/10-upload-plan.json --results $D/11-upload-dryrun.json --index $D/drive-index-<p>.json --dry-run` で、新規アップロード・既存リンク流用・conflict を分ける
4. **承認バンドル**（1 回だけ提示する）
   - 承認が必要な操作を次の形でまとめて示し、明示の承認を待つ。承認はここに列挙した操作だけに効く。内容が変わったり項目が増えたりしたら、その分だけ改めて承認を取る

     ```text
     承認をお願いしたい操作（この順で 1 つずつ実行します）
     1. push: <repo> の <branch> を origin へ
     2. PR 作成: <repo> <branch> → <base>「<タイトル>」（本文案は下記）
     3. Drive 保存: 新規 N 件（<profile> / <保存先フォルダ>）、既存リンク流用 M 件、conflict K 件（上書きしない）
     4. 索引更新: <索引ファイル> に Drive リンク N+M 行を追加して commit し、同じブランチへ push（同じ PR に載ります）
     （merge はユーザーから指示があった場合だけここに載せる）
     ```
5. **実行**（承認された操作だけ、1 コマンドずつ）
   - `git -C <repo> push -u origin <branch>` → `ghrun gh pr create ...` → `scripts/drive_upload.py --plan ... --results $D/12-upload-results.json --index ...` の順に単独で実行し、各結果を確かめてから次へ進む
   - auto mode classifier に拒否されたら再試行も別の道具での迂回もせず、拒否された操作と理由を報告して止まる
   - 銀行口座などの個人情報を含む書類のアップロードが PII として拒否された場合は、その書類を保留にしてユーザーに確認する。MCP コネクタ・ブラウザ・別 profile での代替アップロードはしない
   - `conflict` / `md5-mismatch` / `error` は上書き・再送せず、ユーザーの判断を待つ
6. **索引へのリンク追記**
   - 既存の出力索引、無ければ `docs/` の索引ファイル + README から 1 行。書式と実名の扱いは `references/upload-plan.md` の「repo 索引の書式」と repo の AGENTS.md に従う
   - `scripts/check_links.py --worktree <repo> [--forbidden-file $D/forbidden.txt]` で相対リンク・Drive URL 件数・禁止語・秘密情報らしき語を確認し、commit して承認済みの push を単独で実行する
7. **URL 一覧で締める**
   - 最終返答の末尾に、そのままコピペできる一覧を付ける: PR URL、Drive リンク（`scripts/drive_upload.py --results $D/12-upload-results.json --links` の出力）、commit ハッシュ、保留・未実施の項目とその理由
   - 実行結果は `$D/90-result.md`（task / phase_or_step / created_at の Front Matter 付き）に残す

## してはいけないこと

- 承認の前に push・PR 作成・Drive 書き込みをする、または 1 回の承認を列挙外の操作や次回作業へ広げる
- merge・ブランチ削除・アーカイブなど、依頼されていない後片付けをする
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
