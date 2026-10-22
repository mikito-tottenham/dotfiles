---
name: report-template
description: Report templates for every repo-evaluator mode (code, docs, entrypoint-check, bootstrap).
---

# Report Template

Use these structures as output contracts for `.context/repo-evaluator/<task>/report.md`. Keep reports concise enough to act on, but include evidence paths and confidence. Required sections for `docs:*` modes are also listed in `docs-modes.md` (`Required Report Properties`).

## code:whole

```md
# Code Evaluation Report

## Executive Summary

- Overall score: X/10 (`provisional` if applicable)
- Confidence: high | medium | low
- License/distribution verdict: short triage status, not legal advice
- Top 3 risks:

## Scope and Assumptions

- Target:
- Mode:
- Mode trigger:
- Distribution context assumptions:
- Project-specific rules considered:
- Framework/library versions and references consulted, if applicable:

## Sampling Plan

- Core areas:
- Boundary areas:
- High-risk areas:
- Dependency/license surfaces:
- Areas intentionally not inspected:

## Evidence Coverage

- Files/directories inspected:
- Manifests/lockfiles inspected:
- CI/CD, build, and deployment config inspected:
- Docs inspected:
- Commands run:
- Areas not inspected:
- Confidence impact:

## Checks Run

| Command | Result | Notes |
|---|---|---|

## Checks Not Run

| Check | Reason | Confidence impact |
|---|---|---|

## Pillar Scores

| Pillar | Score | Confidence | Notes |
|---|---:|---|---|
| Architecture and boundaries | X/10 | high/medium/low | |
| Implementation quality | X/10 | high/medium/low | |
| Tests and verification | X/10 | high/medium/low | |
| Documentation | X/10 | high/medium/low | |
| Dependency necessity | X/10 | high/medium/low | |
| Security and reliability | X/10 | high/medium/low | |
| AI/LLM ergonomics | X/10 | high/medium/low | |

Confidence must reflect evidence coverage: use `low` for narrow sampling or missing core areas, `medium` for representative but incomplete evidence, and `high` only when inspected evidence and relevant checks support the claim.

## Positive Signals

- ...

## Issues and Risks

### [P0/P1/P2/P3] Title

Evidence:
- ...

Impact:
- ...

Recommended next action:
- ...

Confidence:
- High | Medium | Low

## Dependency Triage

| Dependency | Class | Evidence | Concern | Recommendation | Confidence |
|---|---|---|---|---|---|

## License / Distribution Triage

| Component | Distribution context | License signal | Evidence | Status | Confidence |
|---|---|---|---|---|---|

## Project-Specific Compliance

- ...

## Spec / Policy Conflicts

- ...

## What I Would Not Preserve

Design opinion only; not a deletion/refactor mandate.

- ...

## Recommended Next Actions

Use risk/design priority, not human work phasing.

1. [P0/P1/P2/P3] ...

## Known Limitations

- ...
```

## code:license

```md
# Code Evaluation License Audit

## Executive Summary

- Verdict: accepted-signal | accepted-with-remediation-evidence | needs-confirmation | blocker
- Confidence: high | medium | low
- Distribution context:
- Top blockers or needs-confirmation items:

## Scope and Assumptions

- Target:
- Mode trigger:
- Distribution context assumptions:
- Project-specific license policy considered:
- Areas intentionally not inspected:

## Evidence Coverage

- Manifests/lockfiles inspected:
- License/notice files inspected:
- Vendored/native/bundled assets inspected:
- Build/link/bundle config inspected:
- Remediation evidence inspected:
- Confidence impact:

## Checks Run / Not Run

- ...

## Dependency Triage

| Dependency | Class | Evidence | Concern | Recommendation | Confidence |
|---|---|---|---|---|---|

## License / Distribution Triage

| Component | Distribution context | License signal | Evidence | Status | Confidence |
|---|---|---|---|---|---|

## Remediation Evidence

- ...

## Blockers and Needs-Confirmation Items

### [P0/P1/P2/P3] Title

Evidence:
- ...

Impact:
- ...

Recommended next action:
- ...

Confidence:
- High | Medium | Low

## Recommended Next Actions

1. [P0/P1/P2/P3] ...

## Known Limitations

- This is engineering triage, not legal advice.
```

## code:framework

```md
# Code Evaluation Framework Best-Practice Review

## Executive Summary

- Framework/library:
- Detected version:
- Reviewer confidence for idiom claims: high | medium | low
- Overall risk:
- Top risks:

## Scope and Assumptions

- Target:
- Mode trigger:
- Primary references consulted:
- Project-specific rules considered:
- Areas intentionally not inspected:

## Evidence Coverage

- Framework entrypoints inspected:
- Core usage patterns inspected:
- Tests/checks inspected:
- Dependency surfaces inspected:
- Commands run:
- Confidence impact:

## Checks Run / Not Run

- ...

## Findings

### [P0/P1/P2/P3] Title

Evidence:
- `path/file.ext:line`

Impact:
- ...

Recommended next action:
- ...

Confidence:
- High | Medium | Low

## Dependency Necessity

| Dependency | Role | Evidence | Concern | Recommendation | Confidence |
|---|---|---|---|---|---|

## Positive Signals

- ...

## Recommended Next Actions

1. [P0/P1/P2/P3] ...

## Known Limitations

- ...
```

## docs:system

Use the full template for `docs:system`.

```markdown
# Docs Evaluator Report

## Executive Summary

- Overall score:
- Confidence:
- Mode:
- Top risks:

## Pillar Scores

| Pillar | Score | Notes |
| --- | ---: | --- |
| Coverage |  |  |
| Reachability |  |  |
| Source-of-truth boundaries |  |  |
| AI readability |  |  |
| Consistency |  |  |
| Task and gap governance |  |  |
| Metadata hygiene |  |  |
| Reference integrity |  |  |

## Evidence Coverage

- Target:
- Inventory scope:
- Files inventoried:
- Files deeply inspected:
- Exclusions:
- Sampling limits:
- Standalone evidence artifact: optional; note path only if created.

## Inventory Summary

| Class | Count | Notes |
| --- | ---: | --- |
| entrypoint |  |  |
| canonical |  |  |
| spec |  |  |
| skill |  |  |
| historical |  |  |
| temporary |  |  |
| task-tracking |  |  |
| deprecated |  |  |
| out-of-scope |  |  |

## Reachability

- Canonical entrypoints:
- Competing first-read claims:
- Reachable active docs:
- Orphaned active docs:
- Historical-only paths:
- Navigation overreach:
- Broken anchors or path references:

## Entrypoint Conflicts

| Entrypoint | Claim | Conflicting Source | Risk | Recommendation |
| --- | --- | --- | --- | --- |

## Source-of-Truth Boundaries

- Canonical sources:
- Historical sources:
- Temporary sources:
- Boundary violations:
- Canonical claim conflicts:

## Instruction Strength Drift

| Topic | Stronger Wording | Weaker Wording | Risk | Recommendation |
| --- | --- | --- | --- | --- |

## Agent-Specific Guidance

| Topic | Shared Source | Agent-Specific Source | Separation Risk | Recommendation |
| --- | --- | --- | --- | --- |

## Skill Contract Precedence

| Skill | Contract Signal | Precedence Gap | Recommendation |
| --- | --- | --- | --- |

## Metadata / Front Matter Hygiene

| Path | Metadata Type | Issue | Recommendation |
| --- | --- | --- | --- |

## Reference Integrity

| Reference | Source Doc | Traceability Issue | Recommendation |
| --- | --- | --- | --- |

## AI Readability

- Necessary docs:
- Excessive or distracting docs:
- Missing reading order:
- Chunking and structure issues:
- Qualitative reading burden:
- Terminology consistency:

## Positive Signals

- 

## Contradictions & Drift

| Priority | Evidence | Impact | Recommendation | Confidence |
| --- | --- | --- | --- | --- |

## TODO / Deferred Work

| Location | Status Signal | Risk | Recommendation |
| --- | --- | --- | --- |

## Deprecated or Stale Docs

| Path | Evidence | Risk | Recommendation |
| --- | --- | --- | --- |

## Freshness Governance

| Path | Freshness Signal | Risk | Recommendation |
| --- | --- | --- | --- |

## Temporary-to-Canonical Gaps

| Temporary Source | Canonical Destination | Gap | Recommendation |
| --- | --- | --- | --- |

## Checks Run

| Command | Exit | Notes |
| --- | ---: | --- |

## Checks Not Run

| Check | Reason |
| --- | --- |

## Issues & Risks

### P1: Title

- Category:
- Evidence:
- Impact:
- Recommended next action:
- Confidence:

## Recommended Next Actions

1. 
2. 
3. 
```

## Narrow docs modes

Use this for `docs:source-of-truth`, `docs:reachability`,
`docs:entrypoint-conflict`, `docs:stale`, `docs:todo`,
`docs:guidance`, `docs:metadata`, and
`docs:reference`. Keep only the sections required by the selected
mode plus any directly relevant residual-gap sections.

Section selection guide for authors; do not include this table in generated
reports:

| Mode | Required Sections |
| --- | --- |
| docs:source-of-truth | Source-of-Truth Boundaries; Temporary-to-Canonical Gaps |
| docs:reachability | Reachability; Entrypoint Conflicts |
| docs:entrypoint-conflict | Entrypoint Conflicts; Reachability |
| docs:stale | Deprecated or Stale Docs; Freshness Governance |
| docs:todo | TODO / Deferred Work; Temporary-to-Canonical Gaps |
| docs:guidance | Instruction Strength Drift; Agent-Specific Guidance; Skill Contract Precedence; Contradictions & Drift |
| docs:metadata | Metadata / Front Matter Hygiene |
| docs:reference | Reference Integrity |

```markdown
# Docs Evaluator Narrow Review

## Findings

### P1: Title

- Category:
- Evidence:
- Impact:
- Recommended next action:
- Confidence:

## Evidence Coverage

- Target:
- Mode:
- Inventory scope:
- Files inventoried:
- Files deeply inspected:
- Exclusions:
- Sampling limits:
- Confidence impact:

## Source-of-Truth Boundaries

- Canonical sources:
- Historical sources:
- Temporary sources:
- Boundary violations:
- Canonical claim conflicts:

## Reachability

- Canonical entrypoints:
- Competing first-read claims:
- Reachable active docs:
- Orphaned active docs:
- Historical-only paths:
- Broken anchors or path references:

## Entrypoint Conflicts

| Entrypoint | Claim | Conflicting Source | Risk | Recommendation |
| --- | --- | --- | --- | --- |

## Deprecated or Stale Docs

| Path | Evidence | Risk | Recommendation |
| --- | --- | --- | --- |

## Freshness Governance

| Path | Freshness Signal | Risk | Recommendation |
| --- | --- | --- | --- |

## TODO / Deferred Work

| Location | Status Signal | Risk | Recommendation |
| --- | --- | --- | --- |

## Temporary-to-Canonical Gaps

| Temporary Source | Canonical Destination | Gap | Recommendation |
| --- | --- | --- | --- |

## Instruction Strength Drift

| Topic | Stronger Wording | Weaker Wording | Risk | Recommendation |
| --- | --- | --- | --- | --- |

## Agent-Specific Guidance

| Topic | Shared Source | Agent-Specific Source | Separation Risk | Recommendation |
| --- | --- | --- | --- | --- |

## Skill Contract Precedence

| Skill | Contract Signal | Precedence Gap | Recommendation |
| --- | --- | --- | --- |

## Contradictions & Drift

| Priority | Evidence | Impact | Recommendation | Confidence |
| --- | --- | --- | --- | --- |

## Metadata / Front Matter Hygiene

| Path | Metadata Type | Issue | Recommendation |
| --- | --- | --- | --- |

## Reference Integrity

| Reference | Source Doc | Traceability Issue | Recommendation |
| --- | --- | --- | --- |

## Checks Run / Not Run

- ...

## Residual Gaps

- ...

## Summary

- Overall risk:
- Confidence:
- Recommended next actions:
```

## entrypoint-check

Return these sections in this order; omit a section when there is nothing to report and do not invent findings to fill it:

1. リポジトリ全体評価
2. Agent探索評価
3. docs構造改善提案
4. 構造レベルの書き換え候補 — candidate `path`, `reason`, `priority`, `required_sections`, and `source_paths` when an existing doc should move; no starter text

## bootstrap

Return the `entrypoint-check` sections 1-2, then:

3. 提案ファイル一覧 — missing targets only; existing files are listed as「既存のため新規候補なし」
4. 各ファイルの目的
5. 必須見出し
6. starter snippets — for missing targets only; when based on existing docs, say so and do not present them as replacements
