---
name: client-proposal-pack
description: Produce a client-facing proposal deck or document end to end, for example for accounting or tax firms - gather prior context and existing materials, draft a skeleton, apply a size-based template, run an adversarial review through doc-grill, export to Marp, PPTX, or PDF after a toolchain preflight, inspect the rendering and fonts, close out through deliverable-closeout, and draft a thank-you email. Use when asked to 提案資料を作って, 事務所向け提案書, 顧問先向けの提案, 資料骨格, 提案の PPT 化, スライドにして, PDF にして送れるように, テンプレート抽出, or お礼メールの文案.
---

# Client Proposal Pack

顧客向け提案資料を「事前情報 → 骨格 → 規模別テンプレート → 敵対レビュー → 書き出し → 検品 → 締め → お礼メール」の順で作る。各工程は既存の Skill に任せ、この Skill は順番・artifact・ゲートを決める。

## 前提

- 顧客名・料金・事例・実績値はこの Skill に持たない。作業 repo の正本（料金表、事例の承認記録、議事録、顧客フォルダ）から引く。
- 作業 repo に提案専用の仕組み（Marp の `slides/` と npm scripts、マスター資料の変更禁止ルール、差し込み型のビルド script）があれば、そちらを優先する。この Skill はその上の手順として使う。
- 対外送付・Drive の共有設定・メール送信は Agent が行わない。ユーザーが行う前提で、成果物と文案を用意する。

## Phase と artifact

`.context/<YYYY-MM-DD>-<client-slug>-proposal/` に各 Phase の artifact を保存してから次へ進む。Front Matter に `task` / `phase_or_step` / `created_at` を入れる。`<client-slug>` は repo の慣習に従う（実名を避ける repo では匿名 slug にする）。

### Phase 1 事前情報 → `01-research.md`

1. 既存資料を先に探す。対象と順番は [references/skeleton-templates.md](references/skeleton-templates.md) の「生成前に探すもの」。
2. 顧客の事実を集める: 過去の議事録・ヒアリングメモ、送付済み資料、公開情報（会社概要・拠点・人数・業務範囲）。公開情報は URL と取得日を付ける。
3. 規模（小・中・大）と決裁の構造を見立てる。分からない点は「確認事項」として残す。
4. 探した場所と見つからなかったものを書く。

### Phase 2 骨格 → `02-skeleton.md`

1. [references/skeleton-templates.md](references/skeleton-templates.md) の共通骨格に、規模別テンプレート（A / B / C）の差分を当てる。
2. スライドごとに「主張（タイトル）・中身・素材の出典」を表で書く。数値には出典を付け、目標値と実績値を分ける。
3. 骨格の段階でユーザーに見せ、方向を確認してから本文に進む。

### Phase 3 本文 → `03-draft.md`（または repo の `deck.md`）

- 骨格どおりに本文を書く。読みやすさは `natural-japanese`（クイックモード）を通す。
- 差し込み型の仕組みがある repo では、固定部を変えず差し込みデータだけを作る。

### Phase 4 敵対レビュー → `04-grill.md`

- `doc-grill` Skill で、別モデルによる敵対レビュー → 指摘ごとの採否表 → 修正 → 整合確認を行う。委譲先の解決は doc-grill の手順に従う。
- 採否表と修正後の差分を `04-grill.md` に残す。

### Phase 5 書き出し → `05-export.md`

1. `python3 <skill-dir>/scripts/preflight_doc_toolchain.py --route <marp|pptx|pdf|inspect> --json-out .context/<task>/toolchain.json` を repo ルートで実行する。不足があれば導入例を示してユーザーに確認し、Agent は自動でインストールしない。
2. 経路は [references/build-routes.md](references/build-routes.md) で選ぶ（Marp / 編集可能な PPTX / pandoc → PDF / 差し込み型）。
3. 生成物の path・コマンド・所要時間を `05-export.md` に書く。

### Phase 6 検品 → `06-inspection.md`

[references/build-routes.md](references/build-routes.md) の「検品」を全部行う。

- 全ページの描画を目で見る（`scripts/render_pptx.sh`、`pdftoppm`）
- `pdffonts` で日本語フォントの埋め込みを確かめる
- PPTX は `scripts/pptx_text_coverage.py` で原稿との本文照合をする
- 最後に `doc-grill` の送付前検品（他の顧客名・内部向け表現・出典の無い数値・目標値と実績値の混同）を通す

問題が見つかったら Phase 3 か 5 へ戻り、`06-inspection.md` に指摘と修正を記録する。

### Phase 7 締め → `07-closeout.md`

`deliverable-closeout` Skill で commit → PR 本文案 → 組織別の Drive 保存（承認前はドラフト表示の接頭辞）→ repo 索引へのリンク追記 → URL 一覧を行う。push・PR・Drive への保存はその Skill の承認手順に従う。

### Phase 8 お礼メール → `08-thank-you-email.md`

[references/thank-you-email.md](references/thank-you-email.md) の型で文案を作り、`japanese-business-writing` で敬語・宛名・約束の確認をし、`natural-japanese` で読みやすさを整える。送信はユーザーが行う。

## 完了チェック

- [ ] `01`〜`08` の artifact がそろっている（使わなかった Phase は理由を書く）
- [ ] 数値・料金・事例に出典があり、掲載の承認が確認できる
- [ ] doc-grill の採否表と送付前検品の結果がある
- [ ] 全ページの描画、フォント埋め込み、本文照合を確かめた
- [ ] 成果物・artifact・コミットに他の顧客名、メールアドレス、secret が入っていない
