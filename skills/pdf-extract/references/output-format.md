---
title: pdf-extract artifact 出力形式
---

# 出力形式

Codex 経路でも Claude 経路でも同じ形式で書く。後段の parser はこの形式だけを前提にする。

## 配置パス

```
<repo>/.context/pdf-extract/<元 PDF の repo 相対パス>.ocr.md
```

- 元 PDF が `.context/<task>/data/foo.pdf` なら `.context/pdf-extract/.context/<task>/data/foo.ocr.md`
- パスはそのままミラーし、拡張子だけ `.pdf` を `.ocr.md` に置き換える。別パスの同名ファイルは衝突しない
- 1 PDF につき 1 ファイル。複数ページも 1 ファイルにまとめる

## frontmatter

必須キー:

```yaml
---
source_pdf: <repo 相対パス>                # str
extraction_backend: codex|claude          # str。実際に使った経路
backend_model: <実行時に解決したモデル ID>  # str。registry から解決した値、または明示指定値
backend_effort: <effort>|null             # str|null。Claude 経路と effort 未指定の tier は null
backend_tier: <S|A|B|C>|null              # str|null。--model 明示時と Claude 経路は null
prompt_id: <id>|inline                    # str
prompt_text_inline: true|false            # bool
generated_at: <ISO 8601, JST>             # str
cache_key: <sha16>_<prompt_id>_<backend>_<model>_<effort>  # str
confidence_overall: high|medium|low       # str。厳しめに自己評価する
---
```

任意キー: `notes_summary`（認識上の特記を短く）、`pdf_pages`、`pdf_size_bytes`、`pdf_sha256`、`prompt_sha256`

`cache_key` の形式は移行前の repo ローカル版と同じで、既存 artifact の cache を引き継げる。プロンプト本文を変えたときは `prompt_sha256` が変わるので、再生成が必要か親が判断し、必要なら `--force` を付ける。

## 本文

プロンプトが要求するフィールドは必ず該当セクションに入れる。推奨構成:

1. `## 書誌情報`: 文書種別、送信元、宛先、日付、文書番号。不明な項目は `null` と書き、省略しない
2. `## 主表`: Markdown 表。空欄にせず `—` か `null` を入れる
3. 補助表・メタ情報: 書類種別ごとにプロンプトの指示に従って見出しを切る
4. `## 手書き・余白注記`: 引用ブロックで原文を残す。再構成は最小限にする
5. `## 認識上の注意`: 判読が揺れた箇所と自己評価。必ず書く
6. `## 構造化データ`（任意）: 本文末尾に ```` ```json ```` ブロックを 1 つ置く。スキーマはプロンプトに従う

後段では、本文中の最初の ```` ```json ```` ブロックを構造化データとして取り出す。

## 不変条件

- frontmatter のキー名と型は経路に関係なく同じ
- 読めない箇所は推測で埋めず、`[不明瞭: 候補A / 候補B]` と書く
- `confidence_overall: high` を無条件に付けない
