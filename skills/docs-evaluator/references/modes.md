# Docs Evaluator Modes, Report Properties, and Boundaries

Detail moved out of `SKILL.md`. Read the section you need: `Mode Selection` before step 1, `Scope and Inventory Rules` at steps 1-4, `Evaluation Checklist` at step 5, `Check Mutation Guard` at step 6, `Required Report Properties` at step 7, and `Boundaries` whenever a finding could cross into another skill's territory.

## Mode Selection

Select the narrowest mode that matches the request:

- `documentation-system-evaluation`: Health check for a repository's documentation graph. Use summary-first output with pillar scores, inventory coverage, reachability, source-of-truth boundaries, prioritized issues, and ideal-state recommendations.
- `source-of-truth-review`: Focus on canonical vs historical/temporary boundaries, ADR misuse, unreflected decisions, and whether README/docs index/agent guidance identifies current policy correctly.
- `reachability-audit`: Focus on whether all active docs can be reached from README, AGENTS/CLAUDE.md, docs index, skill indexes, or other canonical entrypoints without search.
- `entrypoint-conflict-review`: Focus on competing "read first" claims, multiple active entrypoints, navigation branching, and whether the first-hop path is unambiguous for AI agents.
- `stale-docs-review`: Focus on deprecated docs, obsolete skills, duplicated guidance, contradictory docs, and docs that still look active after replacement.
- `todo-governance-review`: Focus on TODO, Deferred Work, known gaps, follow-up notes, owners, expiry, and whether task memory is stored in the right canonical place.
- `guidance-consistency-review`: Focus on canonical claim conflicts, instruction-strength drift, terminology consistency, and separation between shared guidance and agent-specific guidance.
- `metadata-hygiene-review`: Focus on Markdown front matter, ADR metadata, skill metadata, metadata accidentally embedded in body text, and schema consistency for documentation artifacts.
- `reference-integrity-review`: Focus on external references, documented dependencies, spec/contract traceability, and freshness signals without validating source implementation correctness.

If the user gives no mode, infer it from the target and wording. If the request is only a lightweight entrypoint/bootstrap check, prefer `docs-entrypoint-check`.

Mode decision order:

1. Use an explicitly requested mode when present.
2. If the request is only a lightweight README/docs index/agent-entrypoint check or bootstrap skeleton request, use `docs-entrypoint-check` instead of this skill.
3. If the user asks for a broad docs audit, contradiction/gap analysis across multiple doc types, or multiple narrow concerns at once, use `documentation-system-evaluation`.
4. If multiple narrow modes are primary concerns and no explicit mode is provided, use `documentation-system-evaluation`. Keep a narrow mode only when the request has a clear primary target, and record secondary concerns in `Residual Gaps`.
5. Otherwise choose the narrow mode matching the primary risk: navigation/linking -> `reachability-audit`; competing first-read claims -> `entrypoint-conflict-review`; current truth vs history -> `source-of-truth-review`; stale/deprecated active docs -> `stale-docs-review`; TODO/follow-up governance -> `todo-governance-review`; instruction drift or agent-specific separation -> `guidance-consistency-review`; front matter/schema issues -> `metadata-hygiene-review`; external reference/spec traceability -> `reference-integrity-review`.

## Evaluation Checklist

Apply at Workflow step 5 together with `evaluation-rubric.md`:

Check reachability, entrypoint conflicts, AI readability, necessity/sufficiency, contradictions, instruction-strength drift, stale/deprecated docs or skills, freshness governance, knowledge-system structure, primary-home/resolver clarity, current-truth-vs-history separation, provenance/confidence/freshness, typed entity and relationship hygiene, raw-source-vs-curated-synthesis boundaries, privacy/data-boundary clarity, TODO/deferred work governance, duplicated policy, agent-specific guidance separation, skill contract precedence, artifact contract hygiene, schema source-of-truth drift, machine-check boundary clarity, naming taxonomy documentation, stable selector vs implementation-name separation, metadata/front matter hygiene, external reference clarity, documented dependency clarity, spec/contract traceability, canonical-vs-temporary separation, unreflected gaps, terminology consistency, and qualitative reading burden.

## Scope and Inventory Rules

Apply at Workflow steps 1-4:

- Exclude generated/vendor/cache outputs by default: `.git/`, `.context/`, `node_modules/`, `dist/`, `build/`, `.next/`, `coverage/`, generated API docs, vendored docs, package caches, and binary artifacts.
- Exclude gitignored, private, secret, and machine-local files from normal documentation review by default. Do not inspect or quote ignored secret/private content unless the user explicitly asks or a documentation-governance question requires path-level confirmation; even then report only paths, labels, key names, record counts, redacted excerpts, validation status, and risk categories.
- Include repository documentation text broadly: `README*`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `QWEN.md`, `SKILL.md`, `docs/`, `specs/`, `skills/`, workbench/planning docs, and text-like files such as `.md`, `.mdx`, `.txt`, `.rst`, `.adoc`, `.html`, `.htm`, `.yaml`, `.yml`, `.json`, and `.toml` when they function as documentation or policy.
- If the user asks for every text file, include all non-generated, non-ignored text files in the inventory, then mark code/config files that are not documentation as out of scoring scope. Include ignored files only when explicitly requested, and keep private/secret output redacted.
- Separate current canonical instructions from historical records. ADRs, dated workbench notes, `.context/`, and migration notes are evidence/history unless an active entrypoint explicitly promotes them to canonical policy. Keep `.context/` excluded from normal inventory, but sample it when the user asks about temporary-to-canonical gaps, task-memory governance, or an active entrypoint explicitly references it. `.context/` sampling defaults to path-level inventory for relevant task directories plus limited deep reads of the latest or directly related artifacts; broad `.context/` traversal requires an explicit user request.
- For large repositories or any review that will not deep-read all relevant docs, create and save a sampling plan before deep dives. Do not use fixed numeric thresholds as the definition of "large"; explain the scope factors, prioritize entrypoints, canonical docs, and mode-relevant docs, sample remaining classes intentionally, and report unread ranges in `Evidence Coverage` and confidence impact.

## Check Mutation Guard

Apply at Workflow step 6:

- Run link checks, markdown lint/readability checks, or custom inventory scripts only when useful for the requested scope and available without formatters, autofixers, generators, installers, or dependency changes.
- When the evaluated repository provides `scripts/docs-link-check`, prefer it for local Markdown link and anchor checks, passing the target path for narrow reviews when appropriate. If it is absent, fall back to best-effort CLI extraction and clearly mark the lower confidence.
- Treat a non-zero `scripts/docs-link-check` exit caused by broken local docs links or anchors as evaluation evidence, not as skill failure.
- Do not check external URL reachability by default. For `reference-integrity-review`, evaluate whether external references document their purpose, freshness signal, and verification responsibility. Perform web verification only when the user explicitly asks, or when external freshness is the primary review risk and primary-source confirmation is needed; then record `verified_at` and verification scope.
- If the target is inside a git worktree, record `git status --short` before and after checks in `checks.md`. Treat pre-existing dirtiness as baseline context, not your own change.
- Do not run commands expected to write tracked docs, configs, generated docs, snapshots, or dependency installation state.
- If a check writes ignored cache/output files, record the path category and reason in `checks.md`. If a check writes tracked or review-relevant files, stop running further checks and report the mutation; do not clean up or revert it unless the user explicitly asks.
- Do not run formatters, autofixers, generators, installers, or commands that rewrite docs unless the user explicitly asks.
- Save commands, exit status, and skipped checks to `.context/docs-evaluator/<task>/checks.md`.


## Required Report Properties

- For `documentation-system-evaluation`, include `Executive Summary`, `Overall Score`, `Pillar Scores`, `Evidence Coverage`, `Inventory Summary`, `Entrypoint Conflicts`, `Reachability`, `Source-of-Truth Boundaries`, `Instruction Strength Drift`, `Agent-Specific Guidance`, `Skill Contract Precedence`, `Metadata / Front Matter Hygiene`, `Reference Integrity`, `AI Readability`, `Positive Signals`, `Contradictions & Drift`, `TODO / Deferred Work`, `Deprecated or Stale Docs`, `Temporary-to-Canonical Gaps`, `Checks Run`, `Checks Not Run`, `Issues & Risks`, and `Recommended Next Actions`. Start with summary and scores.
- For narrower modes, include `Findings`, `Evidence Coverage`, mode-specific sections, `Checks Run / Not Run`, `Residual Gaps`, and `Summary`. Start with findings ordered by severity.
- Include these mode-specific sections when applicable: `Source-of-Truth Boundaries` and `Temporary-to-Canonical Gaps` for `source-of-truth-review`; `Reachability` and `Entrypoint Conflicts` for `reachability-audit` and `entrypoint-conflict-review`; `Deprecated or Stale Docs` and `Freshness Governance` for `stale-docs-review`; `TODO / Deferred Work` for `todo-governance-review`; `Instruction Strength Drift`, `Agent-Specific Guidance`, `Skill Contract Precedence`, and `Contradictions & Drift` for `guidance-consistency-review`; `Metadata / Front Matter Hygiene` for `metadata-hygiene-review`; `Reference Integrity` for `reference-integrity-review`.
- Use priority by documentation-system risk: `P0` blocker, `P1` high risk, `P2` meaningful maintainability or AI-readability risk, `P3` optional cleanup.
- Each issue must include evidence, impact, recommended next action, and confidence.
- Distinguish "missing canonical doc" from "canonical doc exists but is not linked" and from "historical note contains unreflected policy".
- Treat recommendations as ideal-state directions, not a human work breakdown.

## Boundaries

- This skill evaluates documentation systems, not source implementation quality. Use `code-evaluator` for broad codebase health, dependency, security, framework, or license evaluation.
- Do not treat ADRs, workbench files, or `.context/` artifacts as canonical merely because they contain the newest wording.
- Do not declare a document obsolete only because it is old. Look for replacement links, deprecation wording, git history, manifest changes, and whether active entrypoints still route to it.
- Do not require one universal docs structure. Evaluate whether the repo's own canonical entrypoints make the current structure explicit and efficient.
- Do not expand into prose style proofreading, SEO/readability formulas, code example execution, secrets/PII scanning, auto-fixes, pull requests, or document deletion.
- Do not verify whether code implements a documented contract; only evaluate whether docs identify the relevant specs, contracts, manifests, or implementation references clearly enough for a later code review.
- Treat instruction-strength drift, terminology consistency, metadata hygiene, and reading burden as evidence-based docs risks, not style nitpicks or exact quantitative scores.
- For metadata/front matter and other policy hygiene, apply current canonical repo rules. If it is unclear whether a rule applies retroactively to older ADRs or legacy docs, record the uncertainty as residual risk or an open question instead of declaring a violation.
- Do not treat every Markdown file without front matter as a violation by default. Missing front matter is a finding only when the repo declares required metadata for that document type, such as ADRs or `SKILL.md`. For generic README, AGENTS, or docs pages, evaluate misplaced body metadata only when metadata is actually present or explicitly required.
