# Entrypoint Check and Bootstrap Rules

Detection rules and the agent-entrypoint skeleton for the `entrypoint-check` and `bootstrap` modes of `repo-evaluator`. Output constraints (no skeletons for existing files, fixed categories, no skill-system proposals) are in `SKILL.md`; the response section order is in `report-template.md`.

## Detection Rules

Inspect with `rg --files`, `find`, and `wc`; do not run a script. Evaluate in this order: `README*` -> `docs/README*` or `docs/index*` -> architecture / service / design-system docs -> operational docs -> agent guidance docs.

| Category | Present when | Missing-target proposal |
|---|---|---|
| `docs-index` | `docs/README*` or `docs/index*` exists and works as a reading order | docs index with the reading order |
| `architecture` | an architecture overview under `docs/` (for example `docs/architecture/overview.md`) | architecture overview |
| `services` | a service/module responsibility index (for example `docs/architecture/services/`) | service index |
| `design-system` | a design-system or UI-conventions index, when the repo has a UI | design-system index |
| `operational` | any of `docs/adr`, `docs/governance`, `docs/standards`, `docs/contributing`, `docs/runbooks` | operational docs or ADR directory |
| `entrypoint` | any of `AGENTS.md`, `CLAUDE.md`, `docs/agent_entrypoint.md`, `docs/agents/README.md` | agent entrypoint (skeleton below) |
| `spec-structure` | one topic per file; README/index work as navigation; architecture, services, design-system separated | normalize split or merge, named paths only |
| `size` | no Markdown/text doc over 300 lines or 12 KB | split proposal for the oversized doc |

- Fixed paths are recommendations, not the only valid answer. Search `docs/` first; when an equivalent document exists elsewhere, report "normalize to the recommended path" with `source_paths`, not "missing".
- Severity: `critical` when README or the agent entrypoint is missing, `high` when docs index or architecture docs are missing while `docs/` has content, `medium` for operational / services / design-system gaps, `low` for `spec-structure` and `size`. At most 3 findings per severity; when `critical`/`high` exist, drop low-value style remarks.

## Review Areas (both modes)

- Agent navigability: a single docs entry; the index works as a reading order; architecture / services / design-system reachable without guessing.
- Architecture description: service responsibilities, dependencies, data ownership, APIs, flows are traceable.
- Structured information: YAML, JSON, lists, and tables where they help chunking.
- Skill connection: related skills are discoverable from docs and their descriptions state trigger and purpose (description improvements only; no new skills).
- Context efficiency: granularity, redundancy, and concentration of architecture information.

## Agent Entrypoint Skeleton (`bootstrap` only, when the entrypoint is missing)

Adapt the outline to the target repo; do not paste it verbatim and do not present it when `AGENTS.md` or `CLAUDE.md` already exists.

Required sections:

1. リポジトリの目的 — main responsibilities in 3-5 bullets (app, domain logic, UI, architecture docs, skills)
2. 最初に読むべきドキュメント — `README.md`, docs index, architecture overview, services, design system, skill docs, then code
3. ドキュメント正本 — canonical paths for architecture, services, data model, flows, design system, skills
4. Agent探索ルール — do not fill design gaps by guessing; cite docs; check architecture, service ownership, related skills, and code before changing
5. 守るべき境界 — service responsibility, data ownership, public API, skill responsibility, with examples of changes that must not cross them
6. Skillルール — no new skill system; no conflict with the skill creator; description improvements allowed
7. 変更前チェック
8. 変更後チェック
