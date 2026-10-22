---
name: handoff
description: "Create continuation handoffs for another agent, session, PR reviewer, or machine. Use when work must resume later or elsewhere, when the parent context is near its budget, or for PR handoff context and safe summaries of ignored local artifacts; triggers include 引き継ぎ, 新セッションへ切替, コンテキストが膨らんだ."
---

# Handoff

## Overview

Create a handoff packet that lets a fresh agent resume work without guessing. Choose the medium from the destination, persistence needs, and whether ignored artifacts or secrets are involved; the body always follows the Handoff Contract below.

## Workflow

1. Determine the destination:
   - Same worktree or same machine: write an ignored artifact under `.context/handoff/`.
   - New session, subagent, or runner because the parent context is near its budget (the AGENTS-common 150k-token rule, or a long execution phase after planning): write `.context/handoff/<date>-<task>.md`, then switch; the receiver starts by reading that file.
   - Cross-machine continuation: use a PR as the default carrier.
   - PR reviewer or collaborator: draft a PR comment unless the user explicitly asks to post it.
   - Deferred work without an open PR: write `.context/handoff/` locally and recommend the smallest durable next carrier, usually a branch or PR.
2. Inspect the repository instead of asking when the answer is discoverable from `git status --short`, recent diffs, tests, docs, existing `.context` artifacts, or PR metadata. Do not copy earlier session summaries unread.
3. Identify ignored or local-only context:
   - Same-worktree handoff: reference `.context` artifact paths directly.
   - PR or cross-machine handoff: do not assume `.context` files travel. Summarize the facts and reference only committed paths, commits, branches, PR URLs, or comments.
   - If an ignored artifact is too large or too sensitive to summarize, state the missing carrier and ask for a durable transfer choice.
4. Check for secrets (see Redaction Rules). If secret-backed files must be saved, restored, diffed, or explained, use `$onepassword-secret-materialize` and describe only the non-secret action, for example "restore secret-backed files with `$onepassword-secret-materialize` before running integration checks."
5. Write or draft the handoff. External writes such as posting PR comments, creating issues, or editing durable docs require explicit user instruction.

## Handoff Contract

This is the contract AGENTS-common means by "following the handoff skill contract". Every handoff body uses these four sections in this order, whatever the medium; a PR comment uses the same headings, with summaries in place of `.context/` paths.

```markdown
---
task: <task>
phase_or_step: <current Phase / Step>
created_at: <ISO 8601>
---

## 現状
goal; current Phase / Step; branch, worktree, or PR; what is already done with its
artifact paths; decisions already made and their source; commands already run and
their results

## 未完了
remaining work packages; blockers; open decisions, each with who or what resolves it;
commands not yet run and why; required durable anchors that are still missing

## 次の一手
the single first action the receiver takes (one command or one file read), then the
ordered remaining steps and the skills to invoke (including
`$onepassword-secret-materialize` when secret-backed files are part of the workflow)

## 参照 artifact
paths under `.context/` and committed files the receiver must read, one line each on
why it matters; for PR or cross-machine handoff, summaries of ignored artifacts the
receiver cannot open
```

Rules:

- The front matter keys are the artifact-gate keys; the receiving session uses them to locate the current Phase. In a PR comment, state `task` and `phase_or_step` in the first line instead.
- Include only information that changes the next agent's behavior. Do not duplicate committed plans, ADRs, PR descriptions, test logs, or issue text; reference them by path, commit, PR URL, or artifact path.
- Keep the scope narrow enough that the receiver can start with one command or one file read.
- Before writing, verify with `git status --short` and the latest `.context/<task>/` artifacts that `現状` matches the working tree.
- After writing a context-budget handoff, the parent session stops doing execution work. It may only report the handoff path and, when delegating, pass that path to the receiver.

## Medium Rules

`.context/handoff/`:
- Use for local same-worktree continuation, active investigation state, intermediate notes that should not be committed, and context-budget handoffs on the same machine.
- Name files `.context/handoff/<date>-<task>.md`, for example `.context/handoff/2026-06-04-topic.md`. When the same task is handed off again, write a new file rather than editing the old one; the newest `created_at` is authoritative.

PR handoff:
- Default for cross-machine continuation. Point to commits, files, tests, unresolved decisions, and next steps; do not depend on local ignored files.
- If the user asks to post the comment, use the available GitHub workflow or CLI after verifying the target PR.
- If the PR, branch, commit, or other durable anchor is unknown, say so and make confirming or creating it the first `次の一手`. Do not invent anchors or treat a local branch as cross-machine durable unless it is pushed or otherwise verified.

Durable repository docs:
- Use only for lasting policy, architecture decisions, or repeated operational knowledge, in the repository's normal docs or ADR location. Do not turn one-off session state into permanent docs.

Deferred work:
- Capture the stopping point, blockers, validation already run, and validation still needed. If no durable carrier exists and cross-machine use is likely, make PR creation or update the next action instead of forcing the output into PR comment form.

## Redaction Rules

Never include secret values, tokens, private keys, real `op://...` references, local account names, personal data, sensitive manifest rows, or unnecessary local machine details. Before finalizing, scan the handoff and replace sensitive material with a safe description of how to obtain or restore it; when the workflow depends on secret-backed local files, invoke or recommend `$onepassword-secret-materialize` instead of documenting the secret material.
