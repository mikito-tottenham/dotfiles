---
title: Drive 保存計画と結果の形式
updated_at: 2026-10-03
source: ~/Claude/.context/2026-09-24-drive-output-links の upload.py / 05-upload-plan.json / 08-link-brief.md を汎用化
---

# Drive 保存計画と結果の形式

## 計画（`10-upload-plan.json`）

```json
{
  "task": "<task>",
  "phase_or_step": "10-upload-plan",
  "created_at": "<ISO8601>",
  "items": [
    {
      "id": "<repo>:<repo 相対 path>",
      "src": "/abs/path/to/file.pdf",
      "profile": "<gws-account profile>",
      "drive_id": null,
      "folder_path": ["Claude Code 成果物", "<repo>", "<repo 相対 dir>"],
      "name": "file.pdf"
    }
  ]
}
```

- `folder_path` の要素に `a/b` のような区切りを含めた場合は `a`, `b` に分けて扱う
- `drive_id` が `null` ならマイドライブの root 配下に `folder_path` を順に作る。共有ドライブに置くときは共有ドライブ ID を入れ、`folder_path` は共有ドライブ直下からの名前の列にする
- `folder_path` と `name` は保存先規約（~/Claude/AGENTS.md の「成果物の Drive 保存」節と repo 文書）から決める。`.context/` 配下を例外的に保存するときは dir 名を `_context` にする
- 下書きを保存するときは `name` に規約の接頭辞（例 `【ドラフト・配布不可】`）を付ける
- 顧客名などの実名を含む path / name は `.context/` 内の計画にだけ書き、git 管理下へ写さない

## 結果（`11-upload-dryrun.json` / `12-upload-results.json`）

`results.<id>` に 1 件ずつ記録される。

| status | 意味 | 次の動き |
|---|---|---|
| `dry-run` | 保存先に同名が無く、アップロード予定 | 承認バンドルに載せる |
| `exists-same` | 保存先フォルダに同名・同 md5 がある | 既存リンクを使う |
| `exists-elsewhere` | `--index` の一覧に同 md5 が別名・別フォルダである | 既存リンクを使う（再アップロードしない） |
| `uploaded` | アップロード済みで md5 一致 | リンクを索引へ |
| `conflict` | 同名で md5 が違う | 上書きしない。新版として別名にするか、ユーザーに確認 |
| `md5-mismatch` | アップロード後の md5 が一致しない | 失敗として報告し、再実行前にユーザーに確認 |
| `error` | gws 失敗、classifier の拒否など | 内容を報告。PII による拒否は迂回せずユーザーに確認 |

## repo 索引の書式

- 既存の出力索引があればそこへ追記し、無ければ `docs/` に索引ファイル（例 `docs/drive-outputs.md`）を作り、README から 1 行で誘導する
- 表の列は原則「成果物 | Drive | 保存場所 | 元（正本） | 備考」。備考には「今回 Drive 保存（YYYY-MM-DD）」「既存」「ドラフト・配布不可」「元 md は未マージのブランチ <名> のみ」などを書く
- repo の AGENTS.md に実名や会議資料へのリンクの制限があればそれに従う（例: 実名が入るフォルダは個別ファイル名を書かずフォルダリンクだけにする）
- 追記後は `check_links.py` で相対リンクの実在、Drive URL の件数、禁止語、秘密情報らしき語を確認する
