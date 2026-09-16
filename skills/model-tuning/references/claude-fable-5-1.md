# Claude Fable 5.1 差分メモ

対象: Claude Fable 5.1（model registry alias `fable`、Claude 列 S）。本ファイルは SKILL.md の共通手順に対するモデル固有の差分だけを持つ。

## この環境で確認済みの事実

- `skills/agent-orchestrator/rules/model_registry.yaml` の Claude 列 S tier が alias `fable` で解決する。親（司令塔）と同一モデルで、最も高価なため使用は最小限にする（`skills/agent-orchestrator/references/model-profiles.md`）。
- 得意領域: 曖昧さの裁定、相反する制約の統合、最高難度の設計・レビュー（同上）。
- Claude Code / Claude Desktop の親セッションとして動作し、AGENTS-common の 150k トークン handoff ルールが適用される。

## 監査時に確認する項目

各項目の「現行値」は公式ドキュメントで確認してから正本にする。確認できるまでは「未検証」として扱い、旧世代（`legacy-opus-4-8.md`）の値を暗黙に引き継がない。

| 項目 | 状態 | 監査時の扱い |
|---|---|---|
| effort の既定値と coding / agentic の推奨起点 | 未検証 | registry の tier 設定を SoT にし、prompt 側で魔法語代用していないかだけ見る |
| adaptive thinking の有効化方法と固定 budget の可否 | 未検証 | 固定 `budget_tokens` 推奨が残っていれば「要確認」で報告 |
| sampling parameter（temperature 等）の扱い | 未検証 | 非デフォルト指定を推奨する文書は「要確認」で報告 |
| tool triggering の挙動 | 未検証 | 過剰な tool 強制、固定回数促進は provider 非依存のパターン D / F として扱う |
| long context 上限と compaction 挙動 | 未検証 | artifact 保存前提（パターン H）は provider 非依存に適用 |
| fast mode / 速度オプション | 未検証 | CLI runner へ引数を勝手に足さない |
| vision / computer use の解像度上限 | 未検証 | 旧値が残っていても削除せず「要確認」 |
| プロンプト互換（4.8 → 5 系で動くか） | 未検証 | 全面 rewrite を前提にせず、問題の出た箇所だけ最小修正 |

## 参照する公式ソース

世代固定 URL は書かない。作業時に次の入口から現行ページをたどり、確認した URL と `verified_at` を artifact に残す。

- Claude Developer Platform の Models overview / What's new / Migration guide
- Prompt engineering best practices
- Effort / Thinking / Prompt caching の各ガイド

## 旧世代からの差分候補

`legacy-opus-4-8.md` にある 11 項目（effort 既定 `high`、adaptive thinking 明示、sampling 不使用、tool triggering 改善、coverage-first review、compaction 回復、fast mode、`stop_details`、vision 上限）は Fable 5.1 で継続しているか未確認。監査で該当箇所を見つけたら、削除や書き換えではなく「4.8 世代の値。5 系で要確認」と注記して報告する。
