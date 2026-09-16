---
name: agent-orchestration-evaluator
description: Audit or tune agent orchestration boundaries and role resolution. Use for self-vs-subagent execution, Self-Elision, model resolvers, runner ownership, delegated review prompts, or fallback/remediation behavior.
---

# Agent Orchestration Evaluator

Evaluate or tune agent workflow instructions so they separate orchestration from delegated work. The core pattern is: `self` means parent-orchestrator direct execution for orchestration work only; concrete task execution belongs to delegated roles. Aliased AI roles such as researcher, reviewer, creator, worker, or judge should be delegated to a subagent when they resolve to the current provider/model, and to an observable runner or CLI subprocess when they resolve elsewhere.

## Modes

Choose the narrowest mode that matches the user request:

- `audit`: Report issues and recommended changes only. Use by default for "review", "evaluate", "diagnose", or "どう思う".
- `tune`: Edit the target files when the user asks to "切り出す", "反映", "修正", "更新", "skill にする", or otherwise requests implementation.
- `extract-skill`: Create or update a reusable skill from a project-specific resolver or orchestration rule. Use skill-creator rules for new skills; keep the extracted skill model-agnostic, preserve orchestration definitions and completion/verification criteria, and write ADR/docs only for durable architectural decisions rather than one-off examples.

When tuning, keep edits scoped to orchestration instructions, skill text, resolver docs, ADRs, and prompt harnesses. Do not change model IDs, tool permissions, or production code unless the user explicitly asks for that.

## Core Model

Use these terms consistently:

| Term | Meaning |
|---|---|
| Parent orchestrator | The entrypoint agent coordinating the task, artifacts, parallel workers, synthesis, and final response. |
| `self` | An explicit role assignment meaning the parent orchestrator directly performs orchestration work for the phase. Reserve for intent clarification, planning, delegation, artifact checks, synthesis, adjudication, and final output. Do not use for concrete task execution that can be delegated. |
| AI agent role | A delegated role such as researcher, reviewer, creator, worker, judge, analyzer, verifier, or implementation slice owner. |
| Self-Elision | Runtime optimization when a delegated role resolves to the same provider/model as the parent. Skip external CLI, but still delegate to a same-provider/model subagent. |
| Runner skill | A wrapper skill for observable Claude / Codex / Gemini / Grok CLI or API-backed subprocess execution, stream logs, timeouts, expected artifacts, and failure reports. |
| Resolver | Logic that maps role -> alias -> provider/model/config/execution mode. It should not become a raw command cookbook when runner skills exist. |
| Bypass remediation review | The permanent-fix review defined by the target repo's canonical instruction file (in these dotfiles, the AGENTS-common 恒久対策レビュー rule). That rule owns the trigger conditions and required fields; this skill only checks that workflows invoke it. |
| Promotion candidate | A repeated orchestration failure or waste pattern that may deserve a durable home such as resolver policy, runner hardening, AGENTS guidance, a skill, a script, a test, or an evaluator backlog item. |

## Invariants

Flag or fix violations of these invariants:

1. `self` and Self-Elision are not equivalent.
2. `self` is the only direct parent execution mode.
3. Parent orchestrators do not own concrete task execution. They clarify, plan, delegate, monitor artifacts, synthesize, adjudicate, and report.
4. Aliased AI agent roles are not performed by the parent orchestrator merely because the model matches.
5. Delegation should prefer subagents whenever the environment supports them, including for same-provider Self-Elision and for wrapping cross-provider runner-skill calls.
6. Self-Elision means "do not spawn an external CLI subprocess; spawn a same-provider subagent instead."
7. Cross-provider roles use a runner skill when available; otherwise use the resolver's CLI command contract. This includes Claude, Codex, Gemini, and Grok runner skills.
8. Runner skills own subprocess mechanics: prompt files, stream logs, timeout defaults, expected artifacts, summary, and failure reports.
9. Resolver docs own role/provider/model/config selection and execution-mode semantics, not wrapper internals.
10. Skills should reference the resolver/registry for concrete provider, model ID, effort, and config. Do not hard-code model names or effort settings in skill text except as examples clearly marked non-authoritative.
11. The rule is entrypoint-independent: Claude Code, Codex, Gemini, or another agent should follow the same logical resolver semantics.
12. Every fallback from subagent delegation must be explicit. Do not silently fall back to parent execution for delegated AI roles.
13. Delegated agents must not perform synthesis, final report editing, or orchestration decisions unless their role explicitly says so.
14. Execution-only roles such as `creator`, `apply_consensus`, formatter, or renderer should default to lightweight model settings such as low effort unless the resolver documents an eval-backed reason for a heavier setting.
15. Review and finding roles should not filter findings by vague importance bars during the discovery phase. Prefer coverage-first finding prompts, then rank, dedupe, or verify in a separate role or phase.
16. Tool-use policy should be explicit enough for required evidence gathering, but should not force fixed tool-call counts or stale progress scaffolds that fight newer model tool-triggering behavior.
17. Long-running delegated work must leave enough artifacts, summaries, and failure reports for the parent orchestrator to recover after context compaction or a runner restart.
18. Error bypasses must not silently become the accepted workflow: workflows must invoke the canonical bypass remediation review rule, and a delegated review proposal is verified by the parent against source-of-truth files before adoption.
19. Repeated fallback, subline execution, delegated-role confusion, or runner bypass observed in session history or an AI-usage coach report is evidence for an orchestration audit, not proof of an orchestration defect by itself.

## Audit Workflow

1. **Find sources of truth**
   - Inspect agent guidance files such as `AGENTS.md`, `CLAUDE.md`, `.codex/`, `.agents/`, `.claude/skills/**/SKILL.md`, `rules/**`, `docs/adr/**`, `prompts/**`, and slash command definitions.
   - Identify the canonical model registry or resolver if present.
   - Record assumptions in `.context/agent-orchestration-evaluator/<task>/scope.md` for non-trivial audits unless the user explicitly forbids file edits; in no-edit audits, include assumptions in the response instead.

2. **Map role resolution**
   - Build a table: skill/command, phase, role, role type, configured alias/model/provider, execution mode, artifact contract, fallback.
   - Classify each role as `self`, delegated AI agent role, runner invocation, or non-agent tool work.
   - Treat role names like `researcher_*`, `reviewer_*`, `creator`, `worker`, `judge`, `agent`, `subagent`, and `assistant` as likely delegated AI roles unless the local docs clearly define otherwise.
   - Identify execution-only roles that consume an already planned prompt or consensus output, such as `creator`, `apply_consensus`, doc renderer, formatter, or conversion worker.

3. **Check boundaries**
   Test each invariant against the sources. Wording that usually signals a violation, keyed to the invariant number:
   - (1, 6) Self-Elision described as "current agent directly executes", "execute as self", "親が兼任", or similar.
   - (3) `self` phases that perform concrete task execution instead of orchestration.
   - (7, 8) raw CLI construction inside skills when a runner skill exists.
   - (12) subagent fallbacks that silently become direct parent execution.
   - (13) delegated prompts that allow Phase C/D synthesis, final edits, or reading other workers' outputs without an explicit reason.
   - (10) hard-coded model names, provider names, effort settings, timeout defaults, or CLI flags that should come from a resolver/registry or runner skill.
   - (15) finding roles told to report only high-severity, important, or certain issues before a separate ranking or verification phase.
   - (16) fixed tool-call quotas, forced progress checkpoints, or stale "always use tools" language.
   - (18) "find another way", "work around", "skip", "continue anyway", "ignore", or "use a fallback" after errors, or bypassable failures (tests, tools, permissions, dependencies, auth, hooks, subagents/runners) without invoking the canonical bypass remediation review rule.
   - (19) When a coach report, session audit, or structured usage report identifies repeated fallback or wasted subline execution, trace it back to resolver semantics, runner contracts, prompts, and docs before deciding whether the durable home is orchestration policy, a skill, a script, a test, or no promotion.

4. **Evaluate model and effort policy**
   - Check whether skills only name logical roles and resolver paths, not concrete model IDs.
   - Check whether the resolver assigns lightweight settings to execution-only roles that mainly follow an existing plan.
   - Require a documented reason, eval result, or risk argument before `creator`-like roles use high/xhigh/deep reasoning by default.
   - For review, researcher, and judge roles, check whether effort escalation is tied to task risk, evidence needs, or eval results rather than prompt magic words.
   - Keep model allocation changes in the resolver/registry, not scattered across skill text.

5. **Evaluate execution contracts**
   - Delegated work should have an outcome-first prompt, source prompt file when large, expected artifacts, success criteria, allowed side effects, evidence rules, timeout/budget guard, and blocked-state reporting.
   - CLI runner calls should preserve observability: stream logs, stderr, summary, failure artifact, elapsed time, and expected artifact checks.
   - Check Claude, Codex, Gemini, and Grok roles for available runner skills before accepting raw `claude`, `codex`, `gemini`, `grok`, direct API, or ad hoc wrapper calls inside skill text.
   - Same-provider subagents should have a bounded responsibility and a clear return artifact or final report shape.
   - Long-running roles should write summaries, blocked-state reports, and expected artifacts in stable paths so compaction does not make the work unrecoverable.
   - Bypass remediation reviews follow the canonical rule's field list; check that the rule exists in the target repo and that a delegated review prompt forbids direct adoption of its proposal (invariant 18).
   - Treat promotion candidates as review inputs. Require recurrence, friction, risk, portability, and future-value evidence before recommending a reusable orchestration rule or skill.

6. **Report or tune**
   - In `audit` mode, produce findings first with path references and recommended wording.
   - In `tune` mode, patch the canonical resolver first, then dependent skills/prompts, then ADR or durable rationale if the change is architectural.

## Tuning Patterns

Read [references/tuning-patterns.md](references/tuning-patterns.md) only when drafting or applying a correction. Audit-only work can use the invariants and boundary checks above without loading the examples.

## Output Format

For audits, return:

```markdown
## Findings

- [P1] <short title> — <path:line>
  <why it breaks orchestration boundaries and what to change>

## Role Map

| Skill/Command | Role | Current mode | Expected mode | Notes |
|---|---|---|---|---|

## Recommended Changes

- <canonical resolver change>
- <dependent skill/prompt changes>

## Verification

- <lint/validation/searches run>
- <remaining risks>
```

For tuning, also list files changed and validation commands run.

## Completion Rules

Stop only when:

- The canonical resolver or equivalent guidance clearly distinguishes `self` from Self-Elision.
- Delegated AI roles have an explicit subagent or runner path.
- Parent `self` phases are limited to orchestration responsibilities, not concrete task execution.
- Skills reference resolver/registry paths instead of hard-coding concrete model names, effort, or provider config.
- Claude, Codex, Gemini, and Grok cross-provider invocations use available runner skills instead of raw command or ad hoc API calls.
- Execution-only roles such as `creator` use lightweight defaults unless a documented reason says otherwise.
- Fallbacks are explicit and do not silently assign worker roles to the parent orchestrator.
- Dependent skills/prompts no longer contradict the canonical resolver.
- Review/finding roles preserve discovery coverage before final filtering.
- Long-running runner or subagent roles leave recoverable artifacts for compaction or restart.
- Error bypasses invoke the canonical bypass remediation review rule instead of a locally redefined one.
- Durable architectural changes are recorded in the target repo's ADR or equivalent long-lived documentation when the repo requires it.
