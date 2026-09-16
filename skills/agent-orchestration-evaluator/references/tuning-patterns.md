---
title: Orchestration Tuning Patterns
---

# Orchestration Tuning Patterns

### Replace Direct Self-Elision

Bad:

```text
If resolved provider/model matches current agent, execute as self and skip command construction.
```

Good:

```text
If resolved provider/model matches current agent, skip external CLI subprocess construction and delegate the role to a same-provider/model subagent. The parent orchestrator must not perform aliased AI agent roles directly.
```

### Separate `self` From Delegated Roles

Use `self` for orchestration phases. These phases may decide and synthesize, but should not perform concrete worker tasks when delegation is available:

```yaml
roles:
  understand: self
  synthesize: self
  adjudicate: self
```

Use aliases for delegated work:

```yaml
roles:
  researcher_1: { alias: claude_researcher }
  researcher_2: { alias: codex_researcher }
  reviewer_1: { alias: claude_reviewer }
```

### Keep Skills Model-Agnostic

Skills should point to the resolver or registry path:

```markdown
**Model resolution**: `rules/model_registry.yaml` -> `skills.<skill>.roles.<role>`
```

Avoid authoritative model details in skills:

```markdown
Bad: `researcher_2` uses `gpt-5.5` with `medium`.
Good: `researcher_2` resolves through `skills.research.roles.researcher_2`; concrete model and effort live in the resolver/registry.
```

If a skill includes an example command or model for illustration, mark it non-authoritative and verify it cannot drift from the resolver.

### Prefer Lightweight Execution Models

For roles that execute an already planned prompt, apply accepted changes, render artifacts, format output, or perform a bounded conversion, check that the resolver defaults to a lightweight setting such as low effort. Escalate only when there is evidence that the role must make novel design judgments, handle ambiguous requirements, or resolve conflicts.

Typical policy:

| Role type | Default expectation |
|---|---|
| `creator`, `apply_consensus`, renderer, formatter | Lightweight / low effort unless evals justify more. |
| `researcher`, `reviewer`, `judge`, architecture analyzer | Medium or higher depending on risk and evidence needs. |
| Parent `self` orchestration | No concrete model allocation inside the skill; uses the entrypoint agent. |

### Define Provider-Specific Same-Provider Delegation

Keep this as execution guidance, not model allocation:

| Current provider | Same-provider delegation |
|---|---|
| `claude_code` | Claude Code subagent / Agent tool, with the skill's artifact contract. |
| `codex` | `spawn_agent`, with explicit ownership and expected artifacts. |
| `gemini` | Gemini subagent mechanism if available; otherwise use the skill's explicit fallback. |
| Other | Define explicitly before relying on Self-Elision. |

### Preserve Runner Ownership

When a role resolves to a different provider and a runner skill exists, say:

```text
The resolver determines role/provider/model/config. The runner skill performs the subprocess execution and owns prompt-file handling, timeout, stream logs, expected artifact checks, summary, and failure reporting.
```

Avoid duplicating wrapper command lines in every skill unless no runner exists.

Expected runner mapping:

| Provider / backend | Preferred runner |
|---|---|
| Claude Code CLI | `claude-cli-runner` |
| Codex CLI | Use `codex-cli-runner` when available; do not inline `codex exec` details in dependent skills. If unavailable, keep only an explicit resolver fallback contract. |
| Gemini CLI | `gemini-cli-runner` |
| Grok CLI or API-backed handoff | `grok-cli-runner` |

Prefer runners that provide prompt-file handoff, timeout control, expected artifact checks, summary, and failure reporting. Keep the skill text at the level of "use the runner skill"; do not inline runner command details.

### Separate Finding From Filtering

For review harnesses and bug-finding roles, check whether the prompt separates broad discovery from downstream ranking:

```text
Finding role: report every plausible issue with confidence and estimated severity.
Verifier/ranker role: dedupe, rank, and decide what meets the final reporting bar.
```

Avoid vague discovery-phase filters such as "only important issues" or "be conservative" unless the role is explicitly a final reporting filter.

### Use Outcome-Based Tool Guidance

Tool guidance should describe the evidence or state required, not a fixed number of calls:

```text
Use repository search before claiming a symbol is unused. Use web fetch only for cited current external docs.
```

Avoid stale scaffolds such as mandatory progress updates every N tool calls or unconditional tool use when the task can be completed directly.

### Detect Silent Error Bypasses

Flag workflow text that lets an agent bypass errors without a durable review path:

```text
Bad: If the command fails, use another method and continue.
Good: If the command fails, use a temporary bypass only when it preserves validation. Trigger bypass remediation review when the failure may recur, skips validation, reveals missing setup, or lowers reproducibility.
```

Recommended remediation review contract:

- Error cause and observed command/tool output summary.
- Temporary bypass used and what validation it preserves or loses.
- Permanent-fix candidates across repo-managed config/docs/hooks/skills and machine-local state.
- Whether a subagent, reviewer, evaluator, or runner should investigate the permanent fix.
- Verification required before adopting the fix.

### Delegated Prompt Contract

Subagent or runner prompts should include:

- Role and scope.
- Working directory.
- Source prompt path for multi-line instructions.
- Expected artifact paths.
- Success criteria and blocked-state reporting.
- Allowed side effects.
- Evidence rules.
- Compaction/restart recovery expectations for long-running work.
- Prohibition on orchestration, synthesis, final response editing, and reading sibling worker outputs unless explicitly allowed.

