---
title: "Adopt Cautious Minimal Agent Workflow"
date: 2026-05-22
agent: "Codex GPT-5"
status: "accepted"
---

# Context

The user asked to incorporate the operating philosophy from `multica-ai/andrej-karpathy-skills` `CLAUDE.md`.
The useful parts are tool-agnostic: clarify assumptions before coding, avoid speculative complexity, keep edits tightly scoped, and define verifiable completion criteria.

This repository already has detailed rules for persistence, artifacts, chezmoi, secrets, and cross-agent synchronization.
The new guidance should strengthen day-to-day agent behavior without duplicating those procedural rules.

# Decision

Add a shared common-rule block to the managed AI instruction files:

- `dot_claude/CLAUDE.md`
- `dot_codex/AGENTS.md`
- `dot_qwen/QWEN.md`
- `dot_gemini/GEMINI.md`

Also add the same operating stance to the repository-local `AGENTS.md` so work inside this dotfiles repo follows the same expectation.

The adopted rule is intentionally phrased as a behavior contract rather than a copied upstream document:

- Surface assumptions, uncertainty, multiple interpretations, and important tradeoffs before implementation, without inventing durable product behavior, API contracts, or data formats unless they are grounded in existing implementation, tests, documentation, or explicit user confirmation. When the missing information would determine such durable behavior, return the open questions and verification plan instead of presenting a hypothetical implementation, diff, or code example.
- Prefer the minimum implementation that satisfies the request.
- Touch only lines directly needed for the user's request.
- Define success criteria in a verifiable form and check them before considering work complete.
- For reproduction tests, lock down observed failures and existing contracts, not unconfirmed return values, error types, or output formats.

# Consequences

- Agents should ask or explicitly narrow scope when the request has materially different interpretations.
- Agents should avoid adding unrequested features, abstractions, configuration, or speculative future support.
- Unrelated cleanup remains something to mention, not something to silently perform.
- Completion claims should be backed by concrete checks such as tests, reproduction steps, diffs, or targeted review.
