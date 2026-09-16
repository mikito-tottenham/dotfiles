---
title: "Drive 操作リファレンス — gws-account 経由の files / drives / permissions"
updated_at: 2026-09-15
---

# Drive 操作リファレンス

出典: googleworkspace/cli skills v0.22.5（`gws-shared` / `gws-drive` / `gws-drive-upload`）から `gws-account` 運用向けに要約。認証・プロファイル切替は SKILL.md 本文と references/account-profiles.mdを参照。third-party 側の素の `gws auth login` / service account / `GOOGLE_APPLICATION_CREDENTIALS` / `gws generate-skills` の案内はこの環境のルールと衝突するため採用しない。

## 基本形

```bash
gws-account <profile> drive <resource> <method> [flags]
gws-account <profile> drive --help                 # resource 一覧
gws-account <profile> schema drive.files.list      # params / body を確認してから組み立てる
```

| フラグ | 用途 |
|---|---|
| `--params '{...}'` | URL / query パラメータ（`fileId` などの path パラメータもここ） |
| `--json '{...}'` | リクエスト body（`create` / `update` / `copy` / `permissions create`） |
| `--upload <PATH>` / `--upload-content-type <MIME>` | multipart upload。MIME 省略時は拡張子または body の `mimeType` から推定 |
| `-o, --output <PATH>` | バイナリ応答（`alt=media` / `export`）の保存先 |
| `--format json\|table\|yaml\|csv` | 出力形式。既定 `json` |
| `--page-all` / `--page-limit <N>` / `--page-delay <MS>` | 自動ページング。1 ページ 1 行の NDJSON。既定 10 ページ / 100ms |
| `--dry-run` | API を呼ばずリクエスト形をローカル検証。write 系は先にこれで確認 |

- JSON は single quote で囲む（内側の double quote をシェルに触らせない）
- 共有ドライブを含めるときは `supportsAllDrives: true`、一覧・検索ではさらに `includeItemsFromAllDrives: true` と `corpora: "allDrives"`
- `files list` は既定でゴミ箱内も返す。`q` に `trashed = false` を入れる
- `fields` で返却項目を絞る（`about get` / `comments *` は `fields` 必須。`permissions list` は指定しないと `emailAddress` / `domain` が入らない）
- write / delete はユーザー確認後に実行。permissions の同時更新は最後の 1 件しか反映されない

## 主要 resource と method

| resource | method | 用途 |
|---|---|---|
| `files` | `list` | 一覧・検索。`q` 例: `name contains 'x'`, `'FOLDER_ID' in parents`, `mimeType = '...'`, `modifiedTime > '2026-01-01'` |
| `files` | `get` | メタデータ取得。`alt: "media"` + `-o` で Drive 保存ファイルの中身を取得 |
| `files` | `export` | Docs / Sheets / Slides を指定 MIME に変換（10MB 上限）。Docs → `application/pdf` / `text/markdown`、Sheets → `text/csv` など |
| `files` | `create` | フォルダ作成、または `--upload` でファイル作成 |
| `files` | `update` | メタデータ変更、`addParents` / `removeParents` で移動、`--upload` で内容差し替え |
| `files` | `copy` | 複製（`--json` で名前・親を同時指定） |
| `permissions` | `list` / `get` / `create` / `update` / `delete` | 共有。`type` = `user` / `group` / `domain` / `anyone`、`role` = `reader` / `commenter` / `writer` / `fileOrganizer` / `organizer`（共有ドライブ専用）/ `owner` |
| `drives` | `list` / `get` / `create` / `update` / `hide` / `unhide` | 共有ドライブ（`teamdrives` は非推奨） |
| `comments` / `replies` / `revisions` / `changes` / `about` | — | コメント・版履歴・変更フィード・利用者情報。必要時に `schema` で確認 |

## `+upload` helper（自動メタデータ）

```bash
gws-account <profile> drive +upload <file> [--parent FOLDER_ID] [--name NAME]
```

- MIME type はローカルファイルから自動判定、`name` は省略時にローカルファイル名。実体は `files create` の multipart upload
- MIME を明示したい場合や共有ドライブ向けに `supportsAllDrives` が要る場合は `files create --upload` を使う

## 代表コマンド例

```bash
# 検索（共有ドライブ含む、ゴミ箱除外、返却項目を絞る）
gws-account <profile> drive files list --params '{"q":"name contains '"'"'report'"'"' and trashed = false","pageSize":20,"fields":"nextPageToken,files(id,name,mimeType,parents,modifiedTime)","supportsAllDrives":true,"includeItemsFromAllDrives":true,"corpora":"allDrives"}'

# フォルダ直下を全ページ取得（NDJSON）
gws-account <profile> drive files list --page-all --page-limit 20 --params '{"q":"'"'"'FOLDER_ID'"'"' in parents and trashed = false","fields":"nextPageToken,files(id,name,mimeType)","supportsAllDrives":true,"includeItemsFromAllDrives":true}'

# メタデータ取得（table 出力）
gws-account <profile> drive files get --format table --params '{"fileId":"FILE_ID","fields":"id,name,mimeType,parents,owners,webViewLink","supportsAllDrives":true}'

# バイナリ保存 / Docs を PDF に export
gws-account <profile> drive files get --params '{"fileId":"FILE_ID","alt":"media","supportsAllDrives":true}' -o ./.context/file.bin
gws-account <profile> drive files export --params '{"fileId":"DOC_ID","mimeType":"application/pdf"}' -o ./.context/doc.pdf

# フォルダ作成
gws-account <profile> drive files create --params '{"supportsAllDrives":true}' --json '{"name":"New Folder","mimeType":"application/vnd.google-apps.folder","parents":["PARENT_ID"]}'

# アップロード（helper / 明示 MIME）
gws-account <profile> drive +upload ./report.pdf --parent FOLDER_ID --name 'Report 2026-09.pdf'
gws-account <profile> drive files create --params '{"supportsAllDrives":true}' --json '{"name":"notes.md","parents":["FOLDER_ID"]}' --upload ./notes.md --upload-content-type text/markdown

# 内容差し替え / 移動
gws-account <profile> drive files update --params '{"fileId":"FILE_ID","supportsAllDrives":true}' --upload ./notes.md
gws-account <profile> drive files update --params '{"fileId":"FILE_ID","addParents":"NEW_FOLDER_ID","removeParents":"OLD_FOLDER_ID","supportsAllDrives":true}'

# 複製
gws-account <profile> drive files copy --params '{"fileId":"FILE_ID","supportsAllDrives":true}' --json '{"name":"Copy of file","parents":["FOLDER_ID"]}'

# 共有: 一覧 / ユーザーへ付与（通知メールなし）/ 解除
gws-account <profile> drive permissions list --params '{"fileId":"FILE_ID","fields":"permissions(id,type,role,emailAddress,domain)","supportsAllDrives":true}'
gws-account <profile> drive permissions create --params '{"fileId":"FILE_ID","sendNotificationEmail":false,"supportsAllDrives":true}' --json '{"type":"user","role":"writer","emailAddress":"user@example.com"}'
gws-account <profile> drive permissions delete --params '{"fileId":"FILE_ID","permissionId":"PERM_ID","supportsAllDrives":true}'

# 共有ドライブ一覧
gws-account <profile> drive drives list --format table --params '{"pageSize":50}'
```
