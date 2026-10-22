# Docs Modes, Scope Rules, Report Properties, and Boundaries

Detail for the `docs:*` family of `repo-evaluator`. Read the section you need: `Mode Selection` at Workflow step 1, `Scope and Inventory Rules` at steps 1-4, `Evaluation Checklist` at step 5, `Required Report Properties` at step 7, and `Boundaries` whenever a finding could cross into the `code:*` family or another skill. Core rules, the Check Mutation Guard, and the `P0`-`P3` scale are in `SKILL.md` and are not repeated here.

## Mode Selection

Select the narrowest mode that matches the request:

- `docs:system`: Health check for a repository's documentation graph. Summary-first output with pillar scores, inventory coverage, reachability, source-of-truth boundaries, prioritized issues, and ideal-state recommendations.
- `docs:source-of-truth`: Canonical vs historical/temporary boundaries, ADR misuse, unreflected decisions, and whether README/docs index/agent guidance identifies current policy correctly.
- `docs:reachability`: Whether all active docs can be reached from README, AGENTS/CLAUDE.md, docs index, skill indexes, or other canonical entrypoints without search.
- `docs:entrypoint-conflict`: Competing "read first" claims, multiple active entrypoints, navigation branching, and whether the first-hop path is unambiguous for AI agents.
- `docs:stale`: Deprecated docs, obsolete skills, duplicated guidance, contradictory docs, and docs that still look active after replacement.
- `docs:todo`: TODO, Deferred Work, known gaps, follow-up notes, owners, expiry, and whether task memory is stored in the right canonical place.
- `docs:guidance`: Canonical claim conflicts, instruction-strength drift, terminology consistency, and separation between shared guidance and agent-specific guidance.
- `docs:metadata`: Markdown front matter, ADR metadata, skill metadata, metadata accidentally embedded in body text, and schema consistency for documentation artifacts.
- `docs:reference`: External references, documented dependencies, spec/contract traceability, and freshness signals without validating source implementation correctness.

Mode decision order:

1. Use an explicitly requested mode when present.
2. If the request is only a lightweight README/docs index/agent-entrypoint check or a bootstrap skeleton request, use `entrypoint-check` / `bootstrap` instead of a `docs:*` mode.
3. If the user asks for a broad docs audit, contradiction/gap analysis across multiple doc types, or multiple narrow concerns at once, use `docs:system`.
4. If multiple narrow modes are primary concerns and no explicit mode is provided, use `docs:system`. Keep a narrow mode only when the request has a clear primary target, and record secondary concerns in `Residual Gaps`.
5. Otherwise choose the narrow mode matching the primary risk: navigation/linking -> `docs:reachability`; competing first-read claims -> `docs:entrypoint-conflict`; current truth vs history -> `docs:source-of-truth`; stale/deprecated active docs -> `docs:stale`; TODO/follow-up governance -> `docs:todo`; instruction drift or agent-specific separation -> `docs:guidance`; front matter/schema issues -> `docs:metadata`; external reference/spec traceability -> `docs:reference`.

## Evaluation Checklist

Apply at Workflow step 5 together with the docs pillars in `evaluation-rubric.md`:

Check reachability, entrypoint conflicts, AI readability, necessity/sufficiency, contradictions, instruction-strength drift, stale/deprecated docs or skills, freshness governance, knowledge-system structure, primary-home/resolver clarity, current-truth-vs-history separation, provenance/confidence/freshness, typed entity and relationship hygiene, raw-source-vs-curated-synthesis boundaries, privacy/data-boundary clarity, TODO/deferred work governance, duplicated policy, agent-specific guidance separation, skill contract precedence, artifact contract hygiene, schema source-of-truth drift, machine-check boundary clarity, naming taxonomy documentation, stable selector vs implementation-name separation, metadata/front matter hygiene, external reference clarity, documented dependency clarity, spec/contract traceability, canonical-vs-temporary separation, unreflected gaps, terminology consistency, and qualitative reading burden.

## Scope and Inventory Rules

Apply at Workflow steps 1-4, on top of the default exclusions in `SKILL.md`:

- Include repository documentation text broadly: `README*`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `QWEN.md`, `SKILL.md`, `docs/`, `specs/`, `skills/`, workbench/planning docs, and text-like files such as `.md`, `.mdx`, `.txt`, `.rst`, `.adoc`, `.html`, `.htm`, `.yaml`, `.yml`, `.json`, and `.toml` when they function as documentation or policy. Generated API docs, vendored docs, and package caches stay excluded.
- Enumerate with `rg --files` or `find`, honoring `.gitignore` by default. Use `rg --files -uuu` or equivalent only when the user explicitly asks to include ignored files or a path-level governance question requires it, and keep private/secret output redacted.
- If the user asks for every text file, include all non-generated, non-ignored text files in the inventory, then mark code/config files that are not documentation as out of scoring scope.
- Separate current canonical instructions from historical records. ADRs, dated workbench notes, `.context/`, and migration notes are evidence/history unless an active entrypoint explicitly promotes them to canonical policy. Keep `.context/` excluded from normal inventory, but sample it when the user asks about temporary-to-canonical gaps, task-memory governance, or an active entrypoint explicitly references it. `.context/` sampling defaults to path-level inventory for relevant task directories plus limited deep reads of the latest or directly related artifacts; broad `.context/` traversal requires an explicit user request.
- Prioritize entrypoints, canonical docs, and mode-relevant docs in the sampling plan; sample remaining classes intentionally and report unread ranges in `Evidence Coverage` with their confidence impact.

## Required Report Properties

- For `docs:system`, include `Executive Summary`, `Overall Score`, `Pillar Scores`, `Evidence Coverage`, `Inventory Summary`, `Entrypoint Conflicts`, `Reachability`, `Source-of-Truth Boundaries`, `Instruction Strength Drift`, `Agent-Specific Guidance`, `Skill Contract Precedence`, `Metadata / Front Matter Hygiene`, `Reference Integrity`, `AI Readability`, `Positive Signals`, `Contradictions & Drift`, `TODO / Deferred Work`, `Deprecated or Stale Docs`, `Temporary-to-Canonical Gaps`, `Checks Run`, `Checks Not Run`, `Issues & Risks`, and `Recommended Next Actions`. Start with summary and scores.
- For narrower modes, include `Findings`, `Evidence Coverage`, mode-specific sections, `Checks Run / Not Run`, `Residual Gaps`, and `Summary`. Start with findings ordered by severity.
- Mode-specific sections: `Source-of-Truth Boundaries` and `Temporary-to-Canonical Gaps` for `docs:source-of-truth`; `Reachability` and `Entrypoint Conflicts` for `docs:reachability` and `docs:entrypoint-conflict`; `Deprecated or Stale Docs` and `Freshness Governance` for `docs:stale`; `TODO / Deferred Work` and `Temporary-to-Canonical Gaps` for `docs:todo`; `Instruction Strength Drift`, `Agent-Specific Guidance`, `Skill Contract Precedence`, and `Contradictions & Drift` for `docs:guidance`; `Metadata / Front Matter Hygiene` for `docs:metadata`; `Reference Integrity` for `docs:reference`.
- Distinguish "missing canonical doc" from "canonical doc exists but is not linked" and from "historical note contains unreflected policy".

## Boundaries

- The `docs:*` family evaluates documentation systems, not source implementation quality; route codebase health, dependency, security, framework, or license questions to `code:*`.
- Do not declare a document obsolete only because it is old. Look for replacement links, deprecation wording, git history, manifest changes, and whether active entrypoints still route to it.
- Do not require one universal docs structure. Evaluate whether the repo's own canonical entrypoints make the current structure explicit and efficient.
- Do not verify whether code implements a documented contract; only evaluate whether docs identify the relevant specs, contracts, manifests, or implementation references clearly enough for a later code review.
- Treat instruction-strength drift, terminology consistency, metadata hygiene, and reading burden as evidence-based docs risks, not style nitpicks or exact quantitative scores.
- For metadata/front matter and other policy hygiene, apply current canonical repo rules. If it is unclear whether a rule applies retroactively to older ADRs or legacy docs, record the uncertainty as residual risk or an open question instead of declaring a violation.
- Do not treat every Markdown file without front matter as a violation. Missing front matter is a finding only when the repo declares required metadata for that document type, such as ADRs or `SKILL.md`. For generic README, AGENTS, or docs pages, evaluate misplaced body metadata only when metadata is actually present or explicitly required.
