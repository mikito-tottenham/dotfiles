---
title: "ADR 0029: grok skill を廃止し grok-cli-runner へ移行する"
status: accepted
date: 2026-05-04
worked_at: 2026-05-04 10:44 JST
agent_model: GPT-5 Codex
---

# ADR 0029: grok skill を廃止し grok-cli-runner へ移行する

## Context

`grok` skill は xAI Responses API を file-based wrapper として呼ぶために使っていた。
その後、Claude / Codex / Gemini / Copilot と同じ runner 系の命名・artifact 契約へ寄せる方針になった。

ローカルには現時点で `grok` executable は存在しないため、`grok-cli-runner` の backend は xAI Responses API のままとする。
ただし利用者が期待する運用契約は CLI runner 系と同じく、`.context/<task>/` 配下の request / response / summary / failure artifact を正本にする。

## Decision

- publisher skill `skills/grok/` は廃止する。
- Claude Code / Codex の user scope から旧 `grok` skill を削除する。
- 現行の Grok 呼び出し正本は `skills/grok-cli-runner/` とする。
- install manifest は `grok-cli-runner` のみを復元対象にする。
- runner mapping や orchestration 評価では、Grok CLI / API-backed handoff の preferred runner を `grok-cli-runner` に一本化する。
- 将来公式 Grok CLI が利用可能になった場合も、まず `grok-cli-runner` の backend 差し替えとして扱い、旧 `grok` skill 名は復活させない。

## Consequences

- `$grok` ではなく `$grok-cli-runner` が明示的な呼び出し名になる。
- 旧 `grok` skill 由来の曖昧な互換運用をやめ、runner 系の timeout / summary / failure artifact 契約へ揃う。
- 既存の xAI Responses API backend は維持されるため、実 API 呼び出し能力は失われない。
- ドキュメントや評価 skill に残る `grok` wrapper fallback は削除対象になる。
