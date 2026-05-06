---
title: "ADR 0030: grok-cli-runner の既定モデルを Grok 4.3 に更新する"
status: accepted
date: 2026-05-06
worked_at: 2026-05-06 12:31 JST
agent_model: GPT-5 Codex
---

# ADR 0030: grok-cli-runner の既定モデルを Grok 4.3 に更新する

## Context

2026-05-06 時点で、xAI 公式 docs は Responses API の例で `grok-4.3` を示し、Grok 4.3 を reasoning / knowledge work / tool use 向けモデルとして掲載している。
Grok 4.3 で X の告知と反応を確認したところ、価格性能・agentic benchmark への好意的反応が多い一方、長い連続 tool workflow では実ワークフロー検証を残すべきという caveat があった。

同時に確認した OpenAI GPT-5.5 Instant については、OpenAI の告知や X 反応は ChatGPT/API 側の話であり、この PC の Codex CLI 0.128.0 の `codex debug models` では別 slug の `instant` や `chat-latest` は model catalog に出ていない。
そのため、`agent-orchestration-evaluator` の Creator role 方針はこの時点では変更しない。

## Decision

- `grok-cli-runner` wrapper の xAI デフォルトモデルは `grok-4.3` に更新する。
- `GROK_MODEL`、`GROK_X_RESEARCH_MODEL`、request-level `request.model`、明示 `--model` override は従来通り優先し、既存利用者が固定モデルを選べる状態を維持する。
- Grok 4.3 を長い sequential tool workflow に使う前には、no-API validation に加えて、API cost / auth が許容される場合に代表 workflow の smoke を行う。
- Codex CLI に Instant 系の明示 model slug が出るまでは、Creator role の置き換え方針は `agent-orchestration-evaluator` に反映しない。

## Consequences

- Grok runner の model 指定を省略した実行は `grok-4.3` を使う。
- 古い `grok-4.20-reasoning` が必要な場合は、resolver、環境変数、request artifact、または `--model` で明示する。
- GPT-5.5 Instant 由来の Creator role 置き換え判断は、Codex CLI の model catalog に対応 slug が出てから再検討する。
