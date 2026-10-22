---
source_project: GBrain
source_url: https://github.com/garrytan/gbrain
primary_reference_url: https://github.com/garrytan/gbrain/blob/master/docs/GBRAIN_RECOMMENDED_SCHEMA.md
reviewed_at: 2026-05-18
scope: tool-agnostic documentation evaluation patterns, not GBrain compatibility
---

# Knowledge System Patterns

Use this reference when evaluating documentation, notes, specs, or knowledge-base
directories that are intended to preserve durable context for AI agents.

This generalizes patterns observed in GBrain, but does not require the evaluated
repository to use GBrain, a database, a runtime indexer, or GBrain-compatible
schema.

## Source Lineage

- GBrain repository: https://github.com/garrytan/gbrain
- Recommended schema: https://github.com/garrytan/gbrain/blob/master/docs/GBRAIN_RECOMMENDED_SCHEMA.md
- System-of-record contract: https://github.com/garrytan/gbrain/blob/master/docs/architecture/system-of-record.md
- Source attribution guide: https://github.com/garrytan/gbrain/blob/master/docs/guides/source-attribution.md
- Quality convention: https://github.com/garrytan/gbrain/blob/master/skills/conventions/quality.md
- Page and runtime types: https://github.com/garrytan/gbrain/blob/master/src/core/types.ts
- Facts fence shape: https://github.com/garrytan/gbrain/blob/master/src/core/facts-fence.ts
- Derived database schema: https://github.com/garrytan/gbrain/blob/master/src/core/pglite-schema.ts

Treat these as provenance and comparison points. Findings should be against the
target repository's declared purpose and conventions, not against GBrain
compatibility.

## Evaluation Lens

### Primary Home and Resolver Discipline

- Every durable knowledge item should have an obvious primary home.
- Indexes, resolver docs, or directory READMEs should explain what belongs where
  and what does not.
- Ambiguous filing rules create duplicate entity pages, scattered decisions, and
  search-only navigation.
- An inbox or scratch area is fine when it has a route to triage, promotion, or
  expiry.

### Current Truth vs Historical Timeline

- Current state, accepted policy, or compiled understanding should be separated
  from dated evidence, meeting history, migration notes, and scratch context.
- Historical notes should not masquerade as current truth.
- A strong knowledge system lets an agent answer both "what is true now?" and
  "what happened when?" without re-deriving the boundary from prose.

### Canonical Docs vs Knowledge Notes

- Canonical policy, architecture, specs, and operating rules should be
  distinguishable from personal notes, research notes, task context, and
  temporary synthesis.
- If a note contains new policy, the gap is not that the note exists; the gap is
  that the policy has no canonical destination or promotion path.

### Provenance, Confidence, and Freshness

- Important claims should identify where they came from, when they were observed,
  and whether they are direct, inferred, synthesized, or external.
- Confidence may be qualitative (`low`, `medium`, `high`) or numeric
  (`0..1`); either is acceptable if the convention is clear.
- Freshness signals may be `updated_at`, `reviewed_at`, `effective_date`,
  deprecation markers, replacement links, or explicit review cadence.
- Stale risk is highest for current-state claims about people, projects,
  products, dependencies, policies, and operations.

### Typed Entities and Relationships

- Agents should be able to identify what kind of thing each entry describes:
  person, org, project, product, decision, source, meeting, task context, concept,
  policy, spec, or other repo-specific type.
- Relationships should carry enough semantics to traverse the graph. Typed edges,
  structured front matter, link context, backlinks, or relationship tables are
  stronger than free-form links alone.
- Relationship examples include `works_at`, `founded`, `attended`,
  `documents`, `supersedes`, `depends_on`, `owned_by`, and `mentions`.

### Raw Sources vs Curated Synthesis

- Raw imports, transcripts, API responses, meeting records, and source snapshots
  should be distinguishable from curated summaries or canonical docs.
- Raw sources can be stored in sidecars, source directories, attachments, or
  external systems, but the boundary should be visible to agents.
- A curated page should cite or link to raw evidence when the evidence matters.

### Privacy and Data Boundary

- Public, internal, private, confidential, and machine-local data should not be
  mixed without labels or routing rules.
- Some systems use Git tracking, ignore rules, `db_only` paths, visibility fields,
  remote-stripping, or access policy docs to express this boundary.
- The evaluator should not require one mechanism, but should report when an agent
  cannot tell what can be quoted, shared, indexed, committed, or exposed.

### Retrieval and Maintenance Granularity

- Entries should be small and typed enough to retrieve, cite, and update without
  loading unrelated context.
- Oversized omnibus notes, hidden policy in meeting notes, and duplicated entity
  dossiers increase reading cost and drift risk.
- Maintenance loops may be manual or automated, but durable knowledge systems
  need a way to detect stale pages, orphaned links, duplicate entities, missing
  provenance, and unpromoted decisions.

## Suggested Evaluation Cues

These are examples for evaluation, not universal requirements.

```yaml
---
type: person | org | project | product | decision | source | meeting | note | spec | policy
status: active | draft | archived | superseded
created_at: YYYY-MM-DD
updated_at: YYYY-MM-DD
reviewed_at: YYYY-MM-DD
effective_date: YYYY-MM-DD
confidence: low | medium | high
sensitivity: public | internal | private | confidential
sources: []
aliases: []
related:
  people: []
  orgs: []
  projects: []
  decisions: []
  sources: []
---
```

GBrain uses different concrete shapes in places, such as numeric confidence,
`private|world` visibility in facts fences, page types such as `person`,
`company`, `deal`, `concept`, `meeting`, `email`, `slack`, `code`, and typed
link rows in a derived database. Do not treat the example above as a required
translation target.

## Review Questions

- Can an agent tell what kind of entity or artifact each entry describes?
- Can an agent identify the current source of truth without reading unrelated
  timeline or scratch history?
- Are historical events, dated evidence, and current claims separated clearly?
- Do important claims cite a source or explain whether they are inferred?
- Are confidence and freshness visible where claims can become stale?
- Are relationships typed or contextual enough for graph traversal?
- Are canonical docs and knowledge notes separated, or at least labeled?
- Are raw sources and curated summaries distinguishable?
- Are privacy and publication boundaries visible to an agent?
- Are entries granular enough for retrieval and maintenance?
- Are indexes, resolvers, or entrypoints available without relying only on search?
- Are deprecated, superseded, or untriaged entries clearly marked?

## Finding Patterns

- Missing primary-home or resolver rules for durable knowledge.
- Entity or artifact type is unclear.
- Current-state claims are mixed with historical notes.
- Canonical policy exists only inside notes, meetings, or task context.
- Important claims lack provenance or cite only vague sources.
- Confidence or freshness is absent for stale-prone claims.
- Free-form links exist without relationship semantics.
- Backlinks or reverse reachability are missing where graph traversal is expected.
- Raw sources and curated synthesis are mixed without boundary markers.
- Public, internal, private, confidential, and machine-local data are unlabeled.
- Omnibus notes are too large to retrieve or update safely.
- Duplicate entity pages or aliases make identity resolution ambiguous.
- Deprecated or superseded knowledge remains reachable as active guidance.

## Relationship to Existing Docs Evaluator Pillars

- `Coverage`: include raw sources, curated notes, canonical docs, indexes,
  resolver files, and knowledge directories when they function as durable agent
  context.
- `Reachability`: check whether knowledge entrypoints, resolver docs, and indexes
  make the system usable without repository search.
- `Source-of-Truth Boundaries`: check current truth vs timeline, canonical docs
  vs notes, and unpromoted decisions.
- `AI Readability`: check chunk size, entity typing, reading order, and retrieval
  granularity.
- `Consistency`: check duplicate entities, alias drift, relationship drift, and
  term drift across canonical docs and notes.
- `Reference Integrity`: check provenance, citation specificity, source hierarchy,
  and traceability to raw evidence.
- `Task and Gap Governance`: check triage, expiry, and promotion paths for
  inboxes, TODOs, notes, and unresolved gaps.
- `Metadata Hygiene`: check whether repo-declared front matter or structured
  metadata rules are followed where machine readability is expected.
