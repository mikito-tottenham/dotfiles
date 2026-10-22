---
name: evaluation-rubric
description: Shared issue format, confidence, and scoring rules plus the code and docs pillars for repo-evaluator.
---

# Evaluation Rubric

Shared rules first, then the pillars for the family in use. `code:*` modes read `Shared Rules` and `Code Pillars`; `docs:*` modes read `Shared Rules` and `Docs Pillars`. `entrypoint-check` / `bootstrap` use only the `Issue Format` and `Confidence` sections.

## Shared Rules

### Issue Format

Each issue must contain:

```md
### [P1] Short title

Evidence:
- `path/file.ext`: observed fact or short excerpt

Impact:
- Why this matters for correctness, maintainability, security, license, distribution, documentation reachability, or AI ergonomics.

Recommended next action:
- Ideal-state direction or investigation target.

Confidence:
- High | Medium | Low
```

Use file/line references when available. Do not invent precision; use path-only evidence when line numbers are not practical. Priority (`P0`-`P3`) is defined in `SKILL.md`.

### Confidence

- `high`: directly supported by multiple files, an explicit source-of-truth rule, or inspected evidence plus relevant checks.
- `medium`: directly supported by one source plus repository structure, or representative sampling with important checks or surfaces skipped.
- `low`: plausible from naming, age, absence of links, or narrow sampling; needs human confirmation.

Cap confidence by evidence coverage. If evidence cannot support an overall score, report scoped findings instead of forcing a whole-repo score.

### Scoring

- Mark scores `provisional` when sampling is narrow or checks were not run, and attach a confidence label.
- Let prioritized issues and next actions drive decisions; scores are a summary, not the main deliverable.
- `code:*`: `0-10` for the overall assessment and each code pillar.
- `docs:*`: `0-100` overall with per-pillar notes. `90-100` strong documentation graph with clear separation of entrypoints, canonical sources, and history; `75-89` good structure with a few reachability or canonicality gaps; `60-74` usable but agents must search or infer too often; `40-59` fragile, important docs missing, orphaned, stale, contradictory, or only in historical notes; `0-39` no trustworthy path from entrypoints to current policy or specs.

## Code Pillars

Use for `code:*` modes.

1. **Architecture and boundaries**
   - Separation of concerns, dependency direction, layering, module ownership, circular dependencies, and hidden globals.
   - Pattern fit: avoid both under-structured coupling and unnecessary architecture.
   - Directory and package grain should match ownership and exported responsibility well enough for navigation, without requiring one universal structure.

2. **Implementation quality and maintainability**
   - Readability, simple control flow, robust error handling, observability, validation, security hygiene, performance hygiene, operational readiness signals, and testability.
   - Prefer idiomatic use of language/framework features over custom abstractions without clear benefit.
   - Public component, directory, function, and module names should describe responsibility or ownership, not authoring method, AI involvement, or generator provenance.
   - Semantic UI object names should own the object contract they imply, such as relevant state, variants, accessibility, interaction, layout/composition, and data/source responsibility; leaf text, formatter, wrapper, or selector helpers should use names and placement that reflect their narrower role.

3. **Tests and verification**
   - Critical behavior coverage, edge cases, deterministic tests, test isolation, useful fixtures, checks that can run in CI, and local/CI parity.
   - Report checks not run and how that affects confidence.
   - Local audit/lint checks should enforce current low-false-positive invariants and avoid broad regex guesses for semantic ownership.
   - Stable test selectors and automation contracts may intentionally keep historical wording; evaluate them separately from internal implementation responsibility names.

4. **Documentation and project knowledge**
   - README, architecture docs, ADRs, API contracts, comments that explain intent, and alignment between docs and code.
   - Separate project-specific compliance from general best practice.
   - When AI-assisted work is part of the workflow, missing or ambiguous entry-gate and artifact contracts are maintainability risks, not only documentation gaps.

5. **Dependency necessity and ecosystem fit**
   - Whether dependencies are necessary, official, maintained, license-compatible for the use context, and used idiomatically.
   - Prefer standard APIs or small internal code for commodity behavior when safe.

6. **Security and reliability**
   - Secrets handling, input trust boundaries, auth, data validation, logging of sensitive values, graceful degradation, idempotency, supply-chain exposure, deployment reproducibility, runtime configuration, observability, and runbook/on-call posture when visible.
   - Do not declare the system secure. Report visible hygiene failures and label findings `static-review-only` when no scanner, dynamic test, or targeted security tool was run.

7. **AI/LLM ergonomics**
   - Clear structure, chunkable files, explicit interfaces/types, predictable naming, low boilerplate, focused modules, and tests/docs that let future agents reason with limited context.
   - Treat this as supplementary to human readability, domain idiom, and maintainability; do not reward AI convenience at their expense.
   - Future agents should be able to identify source taxonomy, ownership layer, canonical docs, and verification gates before editing.

### Dependency Triage

Classify important dependencies:

| Class | Meaning | Default treatment |
|---|---|---|
| `platform/core` | React, React Native, Expo, language/runtime/framework core | Usually acceptable; check idiomatic use and version health |
| `official/spec-driven` | Official SDK/client or implementation needed for protocol/spec compliance | Usually acceptable; verify it is official and configured correctly |
| `specialized/hard-to-rebuild` | Crypto, auth, database driver, native bridge, media codec, payment, timezone/runtime complexity | Prefer proven dependencies; scrutinize security and maintenance |
| `community/non-official` | Non-official package from ecosystem | Not automatically bad; issue only when need, maintenance, license, security, distribution, or replaceability risk overlaps |
| `commodity/replaceable` | HTTP wrappers, tiny utilities, formatting helpers, shallow retry/glue code | Yellow sign; consider standard APIs or small internal implementation |
| `duplicative` | Multiple libraries for the same role | Consolidation candidate |
| `license-sensitive` | License or distribution context matters | Apply `license-triage.md` |
| `unknown/unlicensed` | Missing/unclear license or provenance | Blocker or needs-confirmation |

Do not over-rotate into "AI can write it, so always build it." Keep external dependencies for security-critical, spec-heavy, official, or hard-to-rebuild domains.

Treat "zero direct imports found" as a review signal, not removal proof. Peer dependencies, native autolinking, build-time plugins, app config, generated code, and runtime reflection can justify a dependency that a shallow source search does not find.

### Positive Signals

Include a short section for what should likely be preserved:

- Clear boundaries worth keeping.
- Tests or docs that are effective.
- Official/spec-driven dependencies used appropriately.
- Evidence of dependency/license remediation.
- Simple internal code replacing unnecessary commodity dependencies.

### What Not To Preserve

Call out existing structures that should not constrain future improvement:

- Thin wrappers around commodity dependencies.
- Cross-layer imports or abstractions that encode accidental history.
- Duplicate libraries for one purpose.
- Design choices that match current code but conflict with ideal architecture.
- Public names that encode authoring method or generator status instead of responsibility.
- Regex gates that appear to enforce semantic ownership but cannot do so with low false positives.

This section is design opinion, not a deletion or refactor mandate. Do not apply it to product behavior, public APIs, data migrations, security boundaries, or legal obligations without explicit caution.

## Docs Pillars

Use for `docs:*` modes. Score the documentation system as a graph of active guidance, canonical sources, and historical records.

### Coverage

- All repository documentation text is inventoried or explicitly excluded.
- The inventory includes README, agent instructions, AI-specific guidance, docs, specs, skills, workbench/planning notes, ADRs, and text-like documentation files.
- Generated/vendor/cache docs are excluded by policy and listed only when relevant to distribution or discoverability.
- External references, documented dependencies, specs, contracts, manifests, and implementation reference paths are inventoried when docs rely on them.

### Reachability

- Canonical entrypoints link to the documents an AI must read.
- No active canonical document is reachable only by guesswork or repository search.
- Orphaned documents are either intentionally deprecated/out-of-scope or linked from the correct index.
- Competing first-read claims are detected separately from ordinary reachability gaps.
- Local anchors, relative paths, and worktree boundaries are clear enough that links do not send agents to dead headings or unrelated source trees.

### Source-of-Truth Boundaries

- Active policy/spec/architecture lives in canonical docs.
- ADRs and historical records explain why decisions happened, but are not the only current source of an active rule.
- Temporary notes, workbench docs, and `.context/` artifacts do not carry unreflected policy.
- Multiple files do not claim canonical authority for the same topic unless the precedence rule is explicit.
- Canonical claims name the current source, not just historical rationale.
- Detailed schemas for skills, gates, artifacts, or workflow contracts have one identifiable canonical owner; summaries and ADRs link to or summarize that owner instead of repeating the full schema.

### AI Readability

- Documents are necessary and sufficient for an AI agent to complete common tasks without reading excessive unrelated history.
- Reading order is explicit enough to avoid both missed rules and unnecessary deep dives.
- Documents are chunkable: scoped headings, concise sections, stable names, and structured lists where useful.
- The required reading path has a reasonable qualitative burden and does not force agents through irrelevant history.
- Gate or phase artifacts expose machine-checkable status fields when docs say work cannot proceed on `FAIL` or `QUESTION`; prose-only completion claims are a risk when downstream agents or validators need stable state.
- Docs separate low-false-positive static checks from semantic human/agent review instead of asking scripts to infer task-local intent or ownership without context.

### Consistency

- Duplicate rules do not conflict.
- Skill descriptions, AGENTS/CLAUDE guidance, README/docs index, and spec docs agree on triggers, responsibilities, and canonical paths.
- Deprecated docs or skills are removed, marked deprecated, or isolated from active navigation.
- Instruction strength is consistent: MUST/SHOULD/MAY and 必須/推奨/任意/禁止/原則禁止 do not drift across docs for the same rule.
- Shared guidance and agent-specific guidance are separated intentionally across AGENTS, CLAUDE.md, GEMINI.md, QWEN.md, Codex guidance, and skill docs.
- Skill docs explain whether they inherit repo rules, override a specific procedure, or provide a narrower contract.
- Terminology for repeated operational concepts is stable enough that agents can match equivalent rules without guessing; do not treat general prose style as a finding.
- Naming taxonomy docs distinguish responsibility/ownership names from authoring-method labels and generated-artifact labels.
- Stable external selectors, test IDs, public automation contracts, and implementation responsibility names are documented as separate concerns when renaming one would break the other.

### Reference Integrity

- External links, external tool references, package or manifest references, and local implementation paths are explicit enough to follow.
- Docs identify the relevant spec, contract, manifest, schema, script, or source path when they depend on one.
- Freshness signals such as deprecation wording, replacement links, accepted ADR status, manifest membership, or git history are considered before declaring stale risk.
- The evaluator does not verify source implementation correctness; it reports missing or unclear documentation traceability.

### Task and Gap Governance

- TODO, Deferred Work, known gaps, and follow-up tasks have an owner, status, destination, or expiry.
- Follow-up notes are not scattered across ADRs, scratchpads, comments, and docs without a canonical tracker.
- Temporary findings that should change canonical docs are tracked until reflected or explicitly rejected.
- Gate artifacts use explicit fields such as status, blocking failures, and open questions when the workflow needs deterministic continuation rules.

### Metadata Hygiene

- Markdown metadata lives in front matter where the repo requires it.
- ADRs include required status/date/worked_at/agent_model fields when the repo expects them.
- Skills include valid `name` and `description` front matter and keep UI metadata in `agents/openai.yaml`.
- Body text does not carry stale metadata blocks that should be machine-readable.
- Metadata findings are limited to repo-declared requirements and active documentation contracts.
- Legacy or older documents are only violations when current canonical policy clearly applies to them. Otherwise, report uncertainty or grandfathering risk.
- Absence of front matter is only a finding for document types with declared required metadata, such as ADRs or `SKILL.md`. Generic README, AGENTS, or docs pages do not need front matter unless the repo explicitly requires it.

### Docs Issue Categories

- `inventory-gap`: relevant text documents were not inventoried or are hard to classify.
- `reachability-gap`: a necessary document is not linked from canonical entrypoints.
- `entrypoint-conflict`: multiple active documents compete as the first-read or routing authority.
- `overreach`: navigation forces agents through unnecessary or low-value docs.
- `source-of-truth-gap`: active guidance exists only in ADR/history/temporary notes.
- `canonical-claim-conflict`: multiple docs claim canonical authority for the same topic without precedence.
- `schema-drift`: detailed schemas are copied across skills, rules, ADRs, or other docs without a single canonical owner.
- `artifact-contract`: workflow, phase, or gate artifacts lack explicit fields needed for deterministic continuation or validation.
- `machine-check-boundary`: docs blur what scripts can safely check with regex/static rules and what requires semantic review.
- `temporary-gap`: temporary content has not been reflected, tracked, or expired.
- `contradiction`: docs conflict on active behavior, rules, paths, or responsibilities.
- `instruction-strength-drift`: the same rule changes strength across docs.
- `agent-guidance-separation`: shared and agent-specific guidance are misplaced or only present in one agent file.
- `skill-contract-precedence`: a skill contract does not state how it relates to repo-level rules when conflict is plausible.
- `metadata-hygiene`: front matter, ADR metadata, skill metadata, or body-embedded metadata is invalid or inconsistent.
- `reference-integrity`: external references, local implementation paths, manifests, specs, or contracts are missing, stale, or too ambiguous to follow.
- `freshness-governance`: stale risk lacks replacement, deprecation, status, or update signals.
- `knowledge-structure`: durable knowledge lacks primary-home rules, resolver/index entrypoints, clear raw-vs-curated boundaries, or maintainable retrieval granularity.
- `provenance-gap`: important knowledge claims lack source, observation date, confidence, or enough context to distinguish direct, inferred, synthesized, and external claims.
- `relationship-graph-hygiene`: links, backlinks, aliases, or entity relationships are missing, duplicated, untyped, or too vague for agent traversal.
- `current-history-blur`: current truth, accepted policy, timeline evidence, historical notes, and temporary task context are mixed without a clear boundary.
- `privacy-boundary`: public, internal, private, confidential, or machine-local knowledge boundaries are unclear to agents that may quote, index, commit, or expose content.
- `contract-traceability`: docs mention a contract/spec/implementation dependency but do not identify the canonical artifact to inspect.
- `stale-or-deprecated`: obsolete docs or skills remain discoverable as active.
- `todo-governance`: TODO/deferred work is scattered, ownerless, statusless, or expiry-less.
- `ai-readability`: document shape makes agent reading inefficient or error-prone.
- `reference-quality`: anchors, relative paths, named paths, or worktree-crossing references are ambiguous or broken.
- `terminology-drift`: repeated concepts use inconsistent terms that obscure whether rules are equivalent.
- `naming-taxonomy`: docs blur responsibility names, authoring-method labels, generated-artifact labels, or stable external selectors.
- `reading-cost`: required docs path is qualitatively too long or indirect for the task it supports; do not assign pseudo-precise token or minute estimates.
