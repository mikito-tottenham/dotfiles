---
name: docs-evaluator
description: "Produce a report-only broad audit of a repository's documentation system. Use for source-of-truth conflicts, reachability, stale docs, instruction consistency, metadata, or cross-document gap analysis; use docs-entrypoint-check for lightweight README/index/bootstrap checks."
---

# Docs Evaluator

Produce an evidence-backed evaluation report for a repository's documentation system. Do not create patches, delete docs, rewrite canonical sources, or make commits. Recommendations should describe the ideal target state and identify gaps clearly enough for a later implementation pass.

Use `docs-entrypoint-check` instead when the user only wants a lightweight check for README/docs index/agent entrypoints or bootstrap skeleton suggestions.

## Core Rules

- Treat this skill as report-only. Provide findings, risks, scores, inventories, and recommended directions; do not implement them.
- Prefer CLI inspection (`rg`, `find`, `git`, link extraction commands) over MCP unless the user explicitly asks for MCP.
- Do not mutate the evaluated source tree except for evaluation artifacts written under `.context/docs-evaluator/<task>/`. Treat this artifact directory as the only planned target-local mutation allowed by this skill; ignored cache/output writes from checks must be recorded as observed side effects, not silently assumed harmless.
- Use confidence labels. Do not make whole-repo claims from narrow sampling without marking them provisional.
- Scope rules for exclusions, gitignored/private files, which text files count as documentation, canonical-vs-historical separation, `.context/` sampling, and sampling plans are in `references/modes.md` (`Scope and Inventory Rules`); apply them at steps 1-4.

## Modes

Nine modes exist: `documentation-system-evaluation` (broad, summary-first) and eight narrow modes (`source-of-truth-review`, `reachability-audit`, `entrypoint-conflict-review`, `stale-docs-review`, `todo-governance-review`, `guidance-consistency-review`, `metadata-hygiene-review`, `reference-integrity-review`). The catalog, the decision order, and the per-mode required report sections live in `references/modes.md`; read it before step 1 and again before step 7.

## Workflow

1. **Set task and artifact directory**
   - Choose the mode with the catalog and decision order in `references/modes.md`; if the request is only a lightweight README/index/bootstrap check, stop and use `docs-entrypoint-check`.
   - Create `.context/docs-evaluator/<task>/`. Use `<YYYYMMDD>-<target-slug>` when no task name is given; if the directory already exists, append `-2`, `-3`, and so on instead of overwriting prior artifacts.
   - Record target, mode, requested scope, exclusions, assumptions, and whether the user requested all text files or documentation-like files.

2. **Inventory documentation text**
   - Enumerate candidate text documents with `rg --files` or `find`, applying default exclusions and honoring `.gitignore` by default. Use `rg --files -uuu` or equivalent only when the user explicitly asks to include ignored files or a path-level governance question requires it, and keep private/secret output redacted.
   - Classify each relevant file as `entrypoint`, `index`, `canonical`, `policy`, `spec`, `skill`, `historical`, `temporary`, `task-tracking`, `deprecated`, `generated`, or `out-of-scope`.
   - Save `.context/docs-evaluator/<task>/inventory.md`.

3. **Build the navigation and reachability map**
   - Read repository entrypoints first: `README*`, `AGENTS.md`, AI-specific guidance, docs index, and skill indexes when present.
   - Extract local Markdown and HTML links, plus plain-text references where links are missing but paths are named.
   - Mark documents reachable from canonical entrypoints, documents only reachable from historical/temporary notes, orphaned documents, competing first-read paths, broken anchors, and references that leave the worktree.
   - Save `.context/docs-evaluator/<task>/reachability.md`.

4. **Classify source-of-truth boundaries**
   - Identify canonical docs for active rules, specs, architecture, service ownership, operational procedures, and skills.
   - Identify temporary or historical docs: ADRs, workbench notes, migration notes, task scratchpads, and `.context/` artifacts.
   - Check whether temporary or historical content is being used as current policy, whether accepted decisions have not been reflected into canonical docs, and whether multiple docs claim canonical authority for the same topic.
   - Save `.context/docs-evaluator/<task>/source-of-truth.md`.

5. **Evaluate quality and consistency**
   - Read `references/evaluation-rubric.md`.
   - When evaluating knowledge-base directories, durable notes, agent-readable knowledge systems, or reusable context stores, read `references/knowledge-system-patterns.md`.
   - Work through the `Evaluation Checklist` in `references/modes.md`; it lists every dimension this skill is expected to cover.
   - Save raw evidence to `.context/docs-evaluator/<task>/raw-findings.md`.

6. **Run checks with mutation guard**
   - Run link checks, markdown lint/readability checks, or custom inventory scripts only when useful and available without formatters, autofixers, generators, installers, or dependency changes; prefer the repo's `scripts/docs-link-check` when present.
   - Record `git status --short` before and after checks; stop and report if a check writes tracked or review-relevant files.
   - Full rules for external URL verification, ignored cache writes, and forbidden commands are in `references/modes.md` (`Check Mutation Guard`).
   - Save commands, exit status, and skipped checks to `.context/docs-evaluator/<task>/checks.md`.
7. **Write final report**
   - Read `references/report-template.md` and the `Required Report Properties` for the selected mode in `references/modes.md`.
   - Save the full report to `.context/docs-evaluator/<task>/report.md`.
   - Include `Evidence Coverage` in `report.md`. A standalone evidence-coverage artifact is optional, not required.
   - Return a concise chat summary with the report path, top risks, score/confidence, and checks run/not run.

## Boundaries

- This skill evaluates documentation systems, not source implementation quality; use `code-evaluator` for codebase health, dependency, security, framework, or license evaluation.
- Do not treat ADRs, workbench files, or `.context/` artifacts as canonical, and do not declare a document obsolete, only because of its age or wording.
- Do not expand into prose proofreading, SEO/readability formulas, code execution, secrets/PII scanning, auto-fixes, pull requests, or document deletion.
- Full boundary rules, including how to handle metadata hygiene on legacy docs and contract-verification limits, are in `references/modes.md`.

## References

- Read `references/modes.md` for mode selection, the evaluation checklist, required report properties, and full boundaries.
- Read `references/evaluation-rubric.md` before evaluating findings.
- Read `references/knowledge-system-patterns.md` when evaluating knowledge-base directories, durable notes, agent-readable knowledge systems, or documentation intended to preserve reusable context.
- Read `references/report-template.md` before writing the final report.

## Validation

```bash
scripts/skill-quick-validate skills/docs-evaluator
```

Run validation from the publisher source repository root, not from the installed skill directory.
