---
title: pdf-extract の Claude 経路（Codex 不在時の代替経路）
---

# Claude 経路

## 位置づけ

- 目的: Codex CLI を使えない環境でも、同じ出口契約の artifact を作る
- 発動条件: `extract_pdf.py` が exit 127（`codex` が PATH に無い）を返したとき、またはユーザーが Claude 経路を明示したとき。exit 1（Codex は在るが実行に失敗）では発動しない。失敗原因を報告し、ユーザーの判断を待つ
- 観測: artifact の frontmatter に `extraction_backend: claude` を残す。最終報告にも「Claude 経路で抽出した」と書く
- 冪等性: cache key の backend 部分が `claude` になるので、Codex 経路の artifact と取り違えない。同じパスに Codex 経路の artifact がある場合は上書き前にユーザーに確認する
- 検証の欠落: Codex 経路と認識特性が違う。契約書・金額・固有名詞を後段で確定値として使う場合は、ユーザーの目視確認を必須にする

## 手順

1. 入口を正規化する
   - PDF の絶対パスと repo 相対パスを求める
   - 出力パスを `.context/pdf-extract/<repo 相対パス>.ocr.md` に決め、親ディレクトリを作る
2. プロンプトを読む
   - `--prompt-id` 相当なら SKILL.md の探索順でテンプレートを探して全文を読む。要約して使わない
   - `--prompt-text` 相当ならその文字列を使い、`prompt_id: inline` とする
3. PDF を開いて読む（ファイル読み取りツールで PDF を直接読む）
4. プロンプトの指示どおりに本文を組み立てる。構成は [output-format.md](output-format.md)
5. cache key を計算する

   ```python
   import hashlib
   sha = hashlib.sha256(open(pdf_path, "rb").read()).hexdigest()[:16]
   cache_key = f"{sha}_{prompt_id}_claude_{model}_null"
   ```

   `model` には実行中の自分のモデル ID を入れる。skill 本文に例として書かない

6. 出力パスに既存ファイルがあれば frontmatter の `cache_key` を比べる。一致すれば `--force` 相当の指示が無い限り再生成しない
7. frontmatter（`backend_effort: null`、`backend_tier: null`）と本文を書き出す
8. 結果を報告する

   ```json
   {"status": "success", "extraction_backend": "claude", "artifact_path": "<path>", "cache_key": "<key>", "cache_hit": false}
   ```

## やってはいけないこと

- frontmatter のキー名を変える
- `## 構造化データ` の JSON をプロンプトの指定から外す
- 判読できない値を推測で埋める
