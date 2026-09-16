---
name: dads-design
description: Apply the Digital Agency Design System (DADS) to visual deliverables. Use when DADS is requested or when choosing an accessible design system for Japanese public-sector styling; covers tokens, components, accessibility, and licensing. Use when asked for デジタル庁デザインシステム, デザイントークン, アクセシブルな配色, or 行政っぽい信頼感のあるデザイン.
---

# DADS デザイン適用スキル（dads-design）

デジタル庁デザインシステム（DADS, β版 / `https://design.digital.go.jp/dads/`）の調査結果を、成果物に**安全かつ一貫して適用する**ための知識スキル。トークンの実数値・原則・ライセンスを同梱し、毎回サイトを読み直さなくても DADS 準拠のデザインを作れる状態にする。

## いつ使うか
- レポートサイト、スライド、ドキュメント、簡易Webページ等の**見た目を作る／整える**とき。
- 配色・タイポグラフィ・余白・角丸・影・コンポーネント構成を**決める**とき。
- **アクセシブルな配色・コントラスト**が要るとき（行政・公共向けの信頼感を出したいとき）。
- 「DADS」「デジタル庁デザインシステム」「デザイントークン」に言及されたとき。

DADSと無関係な汎用UIライブラリの実装やアプリのビジネスロジックには使わない。

## DADSの中核思想（外さない3点）
1. **アクセシビリティ最優先**（「誰一人取り残されない」）。目標は JIS X 8341-3:2016 AA（=WCAG 2.0）。テキストはサイズによらずコントラスト **4.5:1 以上**。色だけで情報を伝えない。→ 詳細 `references/accessibility.md`。
2. **8pxグリッド＋限定スケール**。余白は8の倍数、フォントサイズ・行間・角丸・影は決められたスケールから選ぶ（恣意的な数値を作らない）。
3. **スタイルガイドとして再定義する前提**。DADSは汎用プラットフォーム。各組織が自ブランドに合わせ色（キーカラー）等を差し替えて「スタイルガイド」を作る、という思想。だからキーカラーは Blue 固定ではなく**差し替え可能**な変数。

## 主要トークン

具体値が必要なときだけ `references/design-tokens.md` を読み、実装では `assets/dads-tokens.css` の CSS 変数を使う。

## 適用ワークフロー
成果物に DADS を適用するときの手順。

1. **適用モードを選ぶ**
   - **(A) フルDADS**: キーカラーも含め DADS のトークンをそのまま使う。最も「行政・公共」然とした見た目。
   - **(B) DADSベースライン＋独自ブランド**: 余白8px・タイプスケール・角丸/影スケール・AAコントラスト等の**構造と原則は DADS に従い**、キーカラー（`--color-key-*`）だけをブランド色に差し替える。DADS自身が想定する「スタイルガイド」の作り方。
2. **トークンを読み込む**: 実装なら `assets/dads-tokens.css` を成果物にコピー/インポートし、`var(--color-key-700)` 等で参照。値だけ欲しいときは `references/design-tokens.md` を見る。
3. **アクセシビリティを担保**: `references/accessibility.md` 末尾のチェックリストを満たす（コントラスト・フォーカス・見出し階層・alt・ターゲットサイズ・色以外の手掛かり）。
4. **コンポーネントが要るとき**: `references/components.md` で該当コンポーネント（46種）を確認し、実装は GitHub `digital-go-jp/design-system-example-components-html` / `-react`（MIT）や Storybook を参照。本スキルは実装コードを同梱しない。
5. **クレジット**: 加工してUIに組み込む利用は出典明記不要だが、フッター等に「デジタル庁デザインシステム（DADS, β版）を参考に構築」と中立記載を推奨。**「デジタル庁が作成/公認」と誤認させない**。詳細 `references/licensing.md`。

### デザインの質を上げるとき
配色・レイアウトの審美性を高める必要があり、`frontend-design` スキルが利用可能な場合は任意で併用する。DADSはトークン・制約・a11yを担い、frontend-design は構図・余白リズム・タイポ階層の検討を補助する。

## ライセンス（要点）
- コードスニペット・デザイントークン = **MIT**、Figma = **CC BY 4.0**、Material Symbols = **Apache 2.0**。**商用・改変・再配布いずれも可**。
- 加工してUIに組み込む利用は**出典明記不要**。未編集公開時はクレジット必須。
- 同梱 `assets/LICENSE-design-tokens`（MIT全文）は削除しない。詳細は `references/licensing.md`。

## 参照ファイル
| ファイル | 内容 | 読むとき |
|---|---|---|
| `references/design-tokens.md` | 全トークンの数値（色HEX/タイポ/角丸/影/余白/レイアウト/リンク/アイコン） | 具体的な値が必要なとき |
| `references/components.md` | 46コンポーネント（名称/slug/用途/URL） | UI部品を選ぶとき |
| `references/accessibility.md` | a11y要件・コントラスト・チェックリスト | 配色確定・実装レビュー時 |
| `references/licensing.md` | ライセンス詳細・クレジット運用 | 公開・再配布前 |
| `assets/dads-tokens.css` | 実装用CSS変数（MIT, v2.0.1） | 成果物に組み込むとき |
| `assets/LICENSE-design-tokens` | 上記CSSのMITライセンス全文 | 再配布時に同梱 |

> DADSはβ版。重要な配色・サイズの確定前に最新版（npm `@digital-go-jp/design-tokens` / Figma Community / `/dads/updates-dads/`）を確認すること。
