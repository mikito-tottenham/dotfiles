---
title: "Keep Deliverables Sharp When Zoomed: Text and Diagrams as Vector, Not Images"
date: 2026-11-17
agent_model: "Claude Code (Claude Fable 5.2)"
status: accepted
---

# ADR 0080: Keep Deliverables Sharp When Zoomed: Text and Diagrams as Vector, Not Images

## Context

2026-11-17 にユーザーから、Agent が作る資料が拡大すると掠れるので、掠れない作り方をルールにして
全 PC に適用するよう指示があった。

同日、作業ルート配下の全リポジトリにある PDF 210 件・PPTX 65 件を走査した（`.context`・worktree・
受領物のディレクトリは除外）。生成ツール由来と判定できた PDF 127 件のうち、

- 13 件は全ページが 1 枚の画像で、文字データを持たない（例: 1672×941px の JPEG を 96ppi で全面配置）
- 43 件は文字はベクターだが、200ppi 未満の画像を含む
- 71 件は全ベクター、または 200ppi 以上の画像だけ

PPTX は 65 件のうち 16 件が全スライド画像、7 件が一部のスライドが画像だけだった。

掠れの原因は次の 3 つに分かれる。

1. スライドを丸ごと画像にする経路。画像生成 AI に文字入りのスライドを描かせて貼る、Marp の既定の
   `--pptx`（各ページが画像になる）など。
2. 図解を PNG にして貼る経路。文字はベクターでも、図の中の文字と線は拡大でにじむ。
3. 写真・ロゴ・アイコンの解像度不足（全面配置の写真が 1920px、アイコンが 192px など）。

4. Chromium 系ブラウザが出す PDF の Type 3 フォント。Skia は CFF アウトラインのフォント（ヒラギノ）、
   可変フォント（Noto Sans JP など）、合成ボールド（Bold の実体が無い太字指定）を Type 3 として
   埋め込む。Type 3 はビューア側でヒンティングと文字用アンチエイリアスが効かず、Acrobat・Chrome・
   Drive のプレビューで本文が細く掠れる。静的 TrueType を `@font-face` で読み込むと CID TrueType に
   なり、掠れない。

4 は 2026-10-20 に業務リポジトリ側で原因が特定され、そのリポジトリの ADR と検査 script で対処済み
だったが、dotfiles の共通ルールと `client-proposal-pack` のフォント例（ヒラギノ）には反映されて
いなかった。本 ADR の初版（同日）は、poppler と macOS の Quartz での拡大描画だけを比べて Type 3 を
原因から外していた。掠れるのは Acrobat・Chrome・Drive のプレビューであり、その判断は誤りだったので
同日中に改めた。この Mac で 8 種の `font-family` 指定を試すと、インストール済みの書体が無いものは
すべてヒラギノへ落ちて Type 3 になった。

## Decision

共通ルール（`.chezmoitemplates/agents-common.md`）に「成果物の鮮明さ」の節を追加し、Claude Code と
Codex の両方に適用する。

1. 文字・表・図解・グラフは文字データとベクターで組み、画像にして貼らない。
2. ページ・スライドを丸ごと画像にする経路を、送付・投影する成果物に使わない。画像生成は文字を
   含まない写真・イラストに限る。
3. ラスターしか無い素材は配置サイズで 200ppi 以上を確保し、足りない場合は引き伸ばさず報告する。
4. Chromium 系で PDF を作るときは、静的 TrueType（Regular と Bold の実体）を `@font-face` で読み込む。
   ヒラギノ・游ゴシック・Noto Sans JP / CJK を使わず、fallback にも並べない。
5. 渡す前に `skills/doc-grill/scripts/check_sharpness.py` で検査する。Type 3 フォント・未埋め込み
   フォント、画像だけのページ・スライド（背景画像として貼った形を含む）、200ppi 未満の画像を
   不合格（exit 1）にする。

`doc-grill` の送付前検品チェックリストに「拡大時の鮮明さ」を加え、`client-proposal-pack` の
書き出し経路から Marp の `--pptx` を外す。

全 PC への適用は既存の配備機構に乗せる。共通ルールは chezmoi が `~/.codex/AGENTS-common.md` として
配備し、skill は `scripts/deploy-skills` が配備する。クラウドセッションは `scripts/bootstrap-web` が
origin/main から同じものを入れる。

## Alternatives Considered

- **画像の解像度を上げるだけにする（2 倍・3 倍で書き出す）**: 掠れ始める倍率が上がるだけで、
  ファイルが大きくなり、文字の検索・コピー・編集もできないままなので採らない。写真など
  ラスターしか無い素材にだけ下限を設ける。
- **フォントを OS にインストールして名前で参照する（Brewfile に足す）**: 入っていないマシンや
  クラウドセッションで黙って fallback に落ち、Type 3 の PDF が出る。フォントファイルを資料の
  リポジトリに置いて `@font-face` で読み込み、検査 script で止める。
- **hook で成果物の生成を機械的に止める**: どのファイルが「渡す成果物」かは意味の判断であり、
  hook に意味判断を持たせない方針に反する。検査は script にし、実行を規則で求める。
- **200ppi より高い下限（300ppi）**: 全面配置の 16:9 スライドで横 4,000px が要り、手に入る写真素材
  では満たせないことが多い。画面で 2 倍に拡大しても崩れない 200ppi を下限にする。

## Consequences

- 画像生成 AI で文字入りのスライドを作る手順は、成果物には使えなくなる。レイアウトは HTML / CSS や
  Office の図形で組み、画像生成は挿絵に限る。
- 全面配置の写真は横 2,700px 以上の素材が要る。足りない場合は小さく配置するか、例外として理由を
  報告する。
- 既存の成果物は自動では直らない。再出力が要るものは個別に作り直す。
- PDF にする資料のリポジトリは、静的 TrueType のフォントファイルを持つ必要がある。書体が
  変わるので、既存のテーマを切り替えると行の折り返しが動く。
- 検査 script は画像の中に文字があるかどうかまでは判定しない。200ppi 以上の PNG に描いた図解は
  script を通るので、規則 1 と目視で補う。
