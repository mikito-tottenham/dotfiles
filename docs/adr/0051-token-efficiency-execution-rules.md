---
title: "トークン効率化のための実行ループ・スクリプト化・handoff 分割ルールの導入"
date: 2026-07-25
agent_model: "起案・仕様確定 = Claude Fable 5 (claude-fable-5)、実装 = Codex (gpt-5.6-sol)"
status: accepted
---

# ADR 0051: トークン効率化のための実行ループ・スクリプト化・handoff 分割ルールの導入

## Context

2026-05-29〜2026-07-25 の Claude Code 28 セッション集計では、output 3.9M /
cache_creation 18.7M / cache_read 465M トークンだった。上位5セッションが
cache_read の約64%を占め、いずれも「250k〜370k に肥大したコンテキストで
150〜450 ターンの実行ループ(ブラウザ収集・環境設定・リサーチ)を親が直接完走」
する構造だった。Sonnet / Haiku の使用は 0 で、Codex は Pro plan の使用率が
ほぼ 0% と余力が大きかった。

## Decision

- `AGENTS.md` の共通ルールへ、反復作業のスクリプト化、約 150k トークンでの
  handoff、リサーチのファンアウトに関する3ルールを追加する
- `agent-orchestrator` の分類 step に、実行ループの兆候を検出した際の
  スクリプト化または worker role への切り替えを追加する
- model registry の tier 選択の目安に script-first を追加する
- 実装・調査系の委譲は registry の既定どおり、同 tier 内で Codex に寄せる運用を
  主経路とする
- 閾値の根拠: cache_read は「コンテキスト長 × 残ターン数」で効くため、実測上位の
  250k〜370k / 150〜450 ターンに対し、分割コスト(handoff 作成 + 再ロード)を
  上回る効果が見込める運用値として 150k / 10 回を置く。モデル窓の上限に由来する
  値ではなく、次期集計で見直す。数値閾値の正本は `AGENTS.md` とし、
  SKILL.md / registry は参照のみとする

## Consequences

- 親(Fable)はオーケストレーション専任に近づき、cache_read の主因だった
  メガセッションが分割される
- 次期間のセッション集計で、maxctx 分布、モデル別呼び出し、
  browser ツール呼び出し数を確認して効果を検証する
- 効果検証は 2026-09-01 を目安に `scripts/ai-usage-aggregate.py` を再実行し、
  maxctx 分布・モデル別呼び出し・browser ツール呼び出し数を本 ADR の Context の
  実測値(baseline)と比較して行う
