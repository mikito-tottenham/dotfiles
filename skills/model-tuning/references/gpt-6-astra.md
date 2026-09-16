# GPT-6 Astra 差分メモ

対象: GPT-6 Astra（OpenAI。Codex 側の次世代モデル）。本ファイルは SKILL.md の共通手順に対するモデル固有の差分だけを持つ。

## この環境で確認済みの事実

- `docs/adr/0053-split-agents-common-and-trim-fixed-context.md` は、2026-09-15 の skill 精密化の一次根拠として OpenAI blog「Rethinking skills and prompts for GPT-6 Astra」を挙げ、要点を trigger 精度、progressive disclosure、過剰 scaffolding の削減としている。
- `skills/agent-orchestrator/rules/model_registry.yaml` の Codex 列は現時点で `gpt-5.6-sol`（S/A/B、effort がダイヤル）と `gpt-5.6-luna`（C）を使っており、GPT-6 Astra への registry 切替は未実施。
- 同 ADR の `agent_model_history` に「GPT-6 Astra (parent); GPT-5.6 Sol (editing worker)」の記録があり、親セッションとしての利用実績はある。

## 監査時に確認する項目

| 項目 | 状態 | 監査時の扱い |
|---|---|---|
| skill description は trigger 精度を優先し、本文詳細は progressive disclosure で分離する | 確認済み（ADR-0053） | パターン L と D を優先適用。description に本文で足りる要点列挙が載っていたら分離を提案 |
| `reasoning.effort` の既定値と escalation 条件 | 未検証 | GPT-5.5 世代の `medium` 起点を引き継がない。registry の effort を SoT にする |
| `text.verbosity` の扱い | 未検証 | パターン I は provider 非依存に適用し、パラメータ名の正否は公式確認 |
| Structured Outputs / prompt caching の推奨 | 未検証 | パターン J は provider 非依存に適用 |
| Responses API の `phase` / assistant item replay | 未検証 | 該当記述は「5.5 世代の契約。6 系で要確認」と注記 |
| image detail の既定と推奨 | 未検証 | 旧値が残っていても削除せず「要確認」 |
| 旧 GPT-5.x 固有の記述（`gpt-5.4-mini` の役割分担例、`gpt-5.5-pro` 等） | 該当あり得る | パターン A として報告 |

## 参照する公式ソース

世代固定 URL は書かない。作業時に次の入口から現行ページをたどり、確認した URL と `verified_at` を artifact に残す。

- OpenAI Developers の Models 一覧と対象モデルのガイド
- Prompt guidance / Reasoning / Structured outputs / Prompt caching / Images and vision の各ガイド
- 上記 blog「Rethinking skills and prompts for GPT-6 Astra」

Codex 環境で `openai-docs` 等の `.system` skill が使える場合は最新仕様の確認に使ってよいが、Claude 側には存在しないため本文の手順を依存させない。

## 旧世代からの差分候補

`legacy-gpt-5-5.md` の 10 項目（fresh baseline、outcome-first、`medium` 起点、高 effort の限界、verbosity 分離、literal instruction following、tool description への寄せ、state 管理、structured outputs / caching、image detail）のうち、outcome-first と tool description への寄せは ADR-0053 の方向性と一致するため継続して適用してよい。パラメータ名・既定値・API 契約に関わる項目は公式確認前に書き換えない。
