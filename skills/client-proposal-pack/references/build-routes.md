---
title: 書き出し経路と検品
updated: "2026-10-03"
source: taskell-management の marp-slides Skill、taskell-advisor-proposals の scripts/build_proposal.py、yoake-finance の scripts/build_pdf.sh、taskell-management（旧 owner 側）の bin/pptx-*
---

# 書き出し経路と検品

正本は Markdown（または差し込みデータ + テンプレート）に置き、PDF / PPTX / HTML は生成物として扱う。経路を選ぶ前に `scripts/preflight_doc_toolchain.py --route <route>` を実行する。

## 経路の選び方

| 求められている形 | 経路 | 備考 |
|---|---|---|
| スライド（PDF で送付） | Marp | repo に Marp の仕組み（`slides/<deck>/deck.md`、`theme.css`、npm scripts）があればそれに従う |
| 顧客が編集できる PowerPoint | Marp の `--pptx`、または built-in の pptx Skill | Marp の PPTX は既定で各ページが画像になり、文字を編集できない（編集可能な出力は Marp の実験的機能で LibreOffice が要る）。編集可能な PPTX が要るなら pptx Skill を使う |
| 文書型の提案書（A4 縦） | Markdown → pandoc → HTML → PDF | 表・長文が中心の場合 |
| 同じ型を複数の顧客へ | 差し込みデータ + 固定テンプレート | 下の「差し込み型」 |

## Marp

- 構成は `slides/<deck>/{README.md, deck.md, theme.css, assets/, dist/}`。`deck.md` と `theme.css` が正本。
- 書き出し: `marp deck.md --html -o dist/index.html`、`marp deck.md --pdf -o dist/deck.pdf`、`marp deck.md --pptx -o dist/deck.pptx`。repo の npm scripts があればそちらを使う。
- PDF / PPTX の書き出しには Chromium 系ブラウザが要る。Chrome / Edge が無い環境では `CHROME_PATH` にブラウザ実行ファイルを指定する。
- 日本語フォントは `theme.css` で明示する（例: `font-family: "Hiragino Sans", "Noto Sans CJK JP", "BIZ UDPGothic", sans-serif;`）。指定しないと環境によって欧文フォントに落ち、行送りが崩れる。
- 画像は `assets/` に置いて相対参照する。生成画像に文字を入れず、文字は Marp 側で書く。

## pandoc → PDF（文書型）

```bash
pandoc draft.md -s --embed-resources --css style.css --metadata title="<タイトル>" -o .context/<task>/draft.html
# Chromium 系で PDF 化（ヘッダ・フッタなし）
"<browser>" --headless=new --disable-gpu --no-pdf-header-footer --print-to-pdf=dist/draft.pdf .context/<task>/draft.html
```

- `style.css` の `font-family` に日本語フォントを入れる。Linux では `fonts-noto-cjk` などを先に入れる。
- wkhtmltopdf を使う場合は `LANG=C.UTF-8` を付け、`--enable-local-file-access` を指定する。

## 差し込み型（複数顧客へ同じ型）

`build_proposal.py` の型を一般化したもの。

- 共通の固定部はテンプレート 1 つだけに置き、顧客ごとの差し込み部（事実と出典、確認事項、ユースケース）は `content.json` などのデータに分ける。顧客間で固定部がずれる事故を構造で防ぐ。
- 置換後に `{{` が残っていたら失敗させる。
- 警告表示（「社内ドラフト・承認前」など）は差し込みで厳しくすることだけを許し、緩める差し込みを受け付けない。
- 出力は HTML / Markdown / PDF の 3 つ。Markdown 版の Front Matter に正本データとテンプレートの path を書く。

## 検品

1. 描画: PPTX は `scripts/render_pptx.sh <deck.pptx> [keynote|soffice]` で `render/slide-NN.jpg` を作り、全ページを目で見る。PDF は `pdftoppm -jpeg -r 110 deck.pdf .context/<task>/slide`。
2. フォント: `pdffonts deck.pdf` で日本語フォントが埋め込まれている（`emb` が `yes`）ことを確かめる。代替フォントに落ちていたら、テーマ・CSS のフォント指定と環境のフォントを直す。
3. 本文の欠落: 原稿と PPTX の本文を照合する。`markitdown deck.pptx > .context/<task>/deck.md` の後、`scripts/pptx_text_coverage.py <原稿.md> .context/<task>/deck.md --section '## 本文'`。
4. 文字数・ページ数: `pypdf` でページ数とテキスト抽出を確かめ、はみ出し（ページ数の想定外の増加）を見つける。
5. 対外表現: 他の顧客名・内部計画値・社内向けの言い回し・目標値と実績値の混同・出典の無い数値が無いかを、最終ゲートとして `doc-grill` の送付前検品に通す。
