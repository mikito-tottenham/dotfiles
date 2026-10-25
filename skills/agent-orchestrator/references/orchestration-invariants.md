---
title: "Orchestration Invariants — 委譲境界の監査基準"
updated_at: 2026-10-25
---

# Orchestration Invariants

orchestration 文書(SKILL.md / registry / 委譲 prompt)を監査・修正するときの不変条件。
旧 orchestration evaluator skill(2026-10 統合)の要約で、判断の正本は SKILL.md と
`rules/model_registry.yaml`。違反の兆候を見つけたら resolver → 依存 skill → ADR の順に直す。

1. `self` と Self-Elision は別物。`self` は親の直接実行で既定の実行モード(委譲条件に
   当たらない具体タスクを含む)、Self-Elision は「外部 CLI を起動せず同 provider の
   subagent へ委譲する」最適化。解決 model も親と同じなら registry `model_elision` に従う。
2. 具体タスクは親が直接実行するのが既定。委譲は委譲条件(文脈の切り離し・並列化・
   ツールや指示の分離・独立レビュー・別利用枠でのコスト優位)に当たる場合に限り、
   役割分担だけを理由に委譲しない。reviewer / judge など独立レビューの役は、モデルが
   一致しても親が兼任しない(別の文脈であること自体が役の目的のため)。
3. 委譲先が親と異なる provider なら runner skill を使い、raw CLI / API 呼び出しを skill に書かない。
4. runner は subprocess 機構(prompt file / stream log / timeout / expected artifact / summary / failure)を所有し、
   resolver は role → provider / model / effort / mode の選択だけを所有する。
5. skill 本文にモデル名・effort を正本として書かない。registry への参照で表す。
6. 委譲からの fallback はすべて明示する。親が黙って worker 役を代行しない。
7. 委譲先は統合・最終報告・他 worker 成果物の閲覧をしない(role が明示する場合を除く)。
8. 実行専用 role(formatter / renderer / apply 系)は軽量 tier を既定にし、重い設定には根拠を要求する。
9. finding role は coverage-first。発見段階で「重要なものだけ」と絞らず、ranking / dedupe / verify は別 role か別 phase で行う。
10. tool 指示は必要な証拠を述べ、固定回数や進捗 scaffold を強制しない。
11. 長時間の委譲は compaction / 再起動後に親が復旧できる artifact・summary・failure report を残す。
12. エラー迂回は恒久対策レビュー(正本: AGENTS-common)を発動し、委譲レビューの提案は親が正本ファイルで検証してから採用する。
13. セッション履歴に見える反復 fallback や委譲混乱は監査の入力であり、それ自体は欠陥の証明ではない。

## Promotion Candidate Score(反復する無駄を恒久化するか)

旧 usage coach skill(2026-10 統合)の rubric。候補を 5 軸 × 0〜5 で採点し、合計で置き場を選ぶ(人の評価には使わない)。

| 軸 | 0 | 5 |
|---|---|---|
| Recurrence | 単発 | repo / tool / 期間をまたいで反復 |
| Friction | 軽微 | 作業を止める、手戻りを生む、根本原因を隠す |
| Risk | 低影響 | secret / 安全 / 本番 / 恒久ルールに波及 |
| Portability | 局所の一事例 | repo や agent をまたいで一般化できる |
| Future Value | 再発しにくい | 再利用性の高い予防策になる |

合計 0〜6: 昇格なし(メモ止まり) / 7〜12: checklist・docs・AGENTS.md / 13〜18: script・test・repo template・evaluator backlog /
19〜25: 高優先。最小の durable home を先に選び、`skill` 化は手続き的判断・条件分岐・同梱リソースが要るときだけ。
入力が count・log・artifact でなく要約由来なら「推定」と明記し、confidence を `high` にしない。
