# 旧世代: Claude Opus 4.8

旧 `opus-4-8-tuning` skill から移したモデル固有の内容。Opus 4.8 を対象にした整備、または 4.8 世代の文書を 5 系へ移行するときの「移行元の前提」確認に使う。現行世代（Fable 5.1 / Opus 5）に対する正本ではない。

## 参照していた公式ソース

作業時は Claude Developer Platform の What's new / Prompting best practices / Migration guide / Adaptive thinking / Effort / Fast mode / Prompt caching の各ページを確認していた。世代固定 URL は現行ページへ置き換わっている可能性があるため、入口から辿り直す。

## Opus 4.8 で押さえていた項目

1. **Opus 4.7 prompt 互換**
   4.7 で動いているプロンプトは原則そのまま動く。全面 rewrite より、4.8 で問題が出る箇所と stale な 4.7 固有記述だけを最小修正する。
2. **Effort が最重要レバー**
   4.8 の既定 effort は `high`。coding / agentic use case は `xhigh` 起点、知能要求タスクは最低 `high`、`low` は短く明確な latency-sensitive タスクに限定する。複雑タスクで浅い場合は prompt magic word より先に effort を上げる。
3. **Adaptive thinking は明示有効化**
   thinking は `thinking: {"type": "adaptive"}` を明示しない限り off。固定 `budget_tokens` は使わない。
4. **Sampling parameter は使わない**
   `temperature` / `top_p` / `top_k` の非デフォルト指定は避け、出力揺れや文体はプロンプト、例、評価で調整する。
5. **Tool triggering 改善を踏まえる**
   4.8 は必要な tool call を飛ばしにくいが、tool 必須タスクでは「いつ・なぜ使うか」を明示する。古い対策としての過剰な tool 強制や N 回ごとの固定 tool 促進は削る。
6. **Code review harness は coverage-first**
   finding phase で「high severity のみ」「保守的に」などの曖昧なフィルタをかけると recall が落ちる。発見段階は uncertain / low severity も含めて出し、別段で ranking / dedupe / verification する。
7. **Long context と compaction 回復**
   長時間 agentic work では、artifact、summary、failure report、再開条件が compaction 後も読めるようにする。会話履歴だけを正本にしない。
8. **Mid-conversation system messages**
   長い API 会話で更新指示を追加する場合に使える。prompt cache を壊さず後続指示を足す用途に限定する。
9. **Fast mode は API 側の選択肢**
   `speed: "fast"` は research preview。運用文書では latency / cost tradeoff と eval 対象として扱い、CLI runner へ勝手に引数追加しない。
10. **Refusal stop details**
    refusal 分岐を扱うアプリや harness は `stop_details` を確認する。通常の agent 運用文書では blocked / refused / failed を混同しないことだけ明示する。
11. **Vision / computer use**
    最大 2576px / 3.75MP まで扱えるが、1080p が性能とコストの良い起点。cost-sensitive なら 720p / 1366x768 を評価する。

## 4.8 固有の典型兆候

- 「Opus 4.7 では」「推奨デフォルト xhigh」などが 4.8 migration 文脈で正本化されている → 4.8 既定 `high` と coding / agentic 推奨 `xhigh` を分けて書く。
- 旧解像度上限や座標変換前提が残っている → 上記 11 の値に更新する。
- 過剰な boilerplate prompt や古い anti-pattern 指示で frontend / design の創造性を潰している → product context、desired aesthetic、avoid generic AI look を短く明確に書く。

## 完了条件（4.8 対象時）

- 対象ファイルに stale な 4.7 専用 tuning 方針が残っていない。
- 上記 11 項目が公式ドキュメントと矛盾しない。
