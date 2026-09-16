# 旧世代: GPT-5.5

旧 `gpt-5-5-tuning` skill から移したモデル固有の内容。GPT-5.5 を対象にした整備、または 5.5 世代の文書を 6 系へ移行するときの「移行元の前提」確認に使う。現行世代（GPT-6 Astra）に対する正本ではない。

## 参照していた公式ソース

作業時は OpenAI Developers の Using GPT-5.5 / Prompt Guidance / Models / Reasoning / Structured outputs / Images and vision / Prompt caching / Conversation state（`phase` parameter）の各ページを確認していた。世代固定 URL は現行ページへ置き換わっている可能性があるため、入口から辿り直す。

## GPT-5.5 で押さえていた 10 項目

1. **drop-in 移行ではなく fresh baseline**
   旧プロンプトをそのまま引き継がない。product contract を保つ最小プロンプトから始め、代表例で `reasoning.effort`、`text.verbosity`、tool descriptions、output format を調整する。
2. **outcome-first prompts**
   期待成果、success criteria、許容される side effects、evidence rules、output shape を明示する。手順を細かく固定するのは、その経路自体が product 要件のときだけにする。
3. **`reasoning.effort` は `medium` 起点**
   latency-sensitive でも planning / search / tool use が必要なら `none` より先に `low` を評価する。`high` / `xhigh` は eval で品質向上が確認できた場合に使う。
4. **高 effort は万能ではない**
   矛盾した指示、弱い停止条件、無制限 tool access があるまま effort を上げると、過剰探索や品質低下を招く。まずプロンプトの矛盾、completion rule、tool boundary を直す。
5. **`text.verbosity` は最終回答長のレバー**
   reasoning quality と回答長を混同しない。簡潔さは `text.verbosity: low`、語数、節数、表幅、JSON-only などで指定する。
6. **literal and thorough な instruction following**
   曖昧・矛盾した指示を雑に選び取らず、整合を取ろうとして reasoning token を消費する。instruction priority、override scope、stopping rule を明示する。
7. **tool guidance は tool description へ寄せる**
   tool 固有の「何をするか」「いつ使うか」「必須入力」「side effects」「retry safety」「error mode」は tool description に書く。system prompt には全 tool 共通の運用方針だけを置く。
8. **long-running / tool-heavy workflow は状態管理を明示**
   Responses API の `previous_response_id`、手動 replay 時の assistant item と `phase` 保持、preamble、compaction、verification loop を運用文書に残す。
9. **structured outputs と prompt caching を前提化**
   parse-sensitive な schema は prompt に長く書くより Structured Outputs を使う。静的指示を前、動的 user context を後ろに置く。不要な current date 注入は削る。
10. **vision / computer use は `image_detail` を意図的に選ぶ**
    `auto` はより詳細を保持する。精度重視なら `original` / `high`、コスト重視なら `low` を明示し、OCR・click accuracy・dense image では縮小前提を再評価する。

## 5.5 固有の典型兆候

- 「既存の GPT-5.2 / GPT-5.4 prompt を維持して model だけ置換」と書いている → 最小 prompt から再評価する方針に置換する。
- GPT-5.5 一本化か、小型・上位モデルとの役割分担かが未定 → Phase 1 で確定し、モデル ID を文書に直書きせず registry へ寄せる。
- 手動 replay 設計なのに `phase` 保持に触れていない → assistant output item と `phase` を変更せず戻す契約を追加する。
- 常に縮小、常に `low`、または `auto` の挙動を旧モデル前提で説明している → 目的別に image detail を明示する。

## 完了条件（5.5 対象時）

- 上記 10 項目と、モデル ID、`reasoning.effort`、`text.verbosity`、image detail、`phase`、Structured Outputs、tool guidance の扱いが公式ドキュメントと矛盾しない。
