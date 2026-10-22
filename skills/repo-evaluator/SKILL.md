---
name: repo-evaluator
description: "Report-only evaluation of a repository: code health (architecture, tests, dependencies, licensing, security, AI ergonomics), documentation system (source of truth, reachability, stale docs, metadata, consistency), and lightweight AI docs entrypoint checks or bootstrap skeletons for a missing README, docs index, or agent entrypoint. Not for narrow PR or diff review. Use when asked to コード評価, コードベースを評価, リポジトリ全体を評価, 依存関係を監査, ライセンス監査, ドキュメント監査, docs の正本を確認, 初期化, 雛形, ひな形, テンプレート, or 叩き台を作る."
---

# Repo Evaluator

Produce an evidence-backed, report-only evaluation of a repository, package, or subsystem. Three families share one workflow:

- `code:*` evaluates the codebase (former `code-evaluator`).
- `docs:*` evaluates the documentation system (former `docs-evaluator`).
- `entrypoint-check` / `bootstrap` check minimal AI-readable docs entrypoints and, only on explicit request, propose skeletons for missing ones (former `docs-entrypoint-check`).

Do not create patches, edit target files, delete docs, upgrade dependencies, run autofix commands, or commit. Recommendations describe the ideal target state, not the smallest human-sized diff. If the user asks for fixes during an evaluation, keep the report report-only and propose a separate implementation handoff.

## Core Rules

- Report-only: findings, risks, scores, inventories, recommended directions. Never implement them.
- Prefer CLI inspection (`rg`, `find`, `git`, package manager metadata, test commands) over MCP unless the user asks for MCP.
- The only planned target-local mutation is the artifact directory `.context/repo-evaluator/<task>/`. Ignored cache/output writes from checks are observed side effects to record, never assumed harmless.
- Exclude generated/vendor/cache outputs by default: `.git/`, `.context/`, `node_modules/`, `dist/`, `build/`, `.next/`, `coverage/`, generated code or API docs, binary artifacts, previous `.context/` runs.
- Exclude gitignored, private, secret, and machine-local files by default. Inspect them only when the user asks or a license/security/distribution/governance question needs path-level confirmation; even then report only paths, key names, record counts, redacted excerpts, validation status, and risk categories.
- Still read manifests, lockfiles, `LICENSE`/`NOTICE`, `patches/`, `overrides`/`resolutions`, and remediation notes; in `code:license` also inventory `vendor/`, `third_party/`, native/link/bundle config, and bundled assets that can enter distributed artifacts.
- Separate general engineering findings from project-specific compliance. Evaluate against repo-local rules when they exist, but do not confuse "matches current policy" with "ideal design".
- Use confidence labels (`high` / `medium` / `low`). Whole-repo claims from narrow sampling are `provisional`. If evidence cannot support an overall score, report scoped findings instead.
- For large targets, save a sampling plan before deep dives. Do not define "large" with fixed numbers; explain the scope factors and report unread ranges in `Evidence Coverage`.
- Do not treat ADRs, workbench notes, or `.context/` artifacts as canonical, and do not call a document obsolete only because of age or wording.

## Modes

Pick the narrowest mode. Family boundaries: `code:*` does not judge documentation-system quality; `docs:*` does not judge implementation quality or verify that code implements a documented contract; `entrypoint-check` / `bootstrap` stay lightweight and route anything broader to `docs:*`.

| Mode | Use for |
|---|---|
| `code:whole` | Health check of a repo/package/subsystem: pillar scores, sampling plan, coverage, positive signals, prioritized issues, ideal-state recommendations |
| `code:license` | Dependency licenses, distribution context, accepted signals, unknown/no-license blockers, remediation evidence |
| `code:framework` | Idiomatic use of a named framework/library, plus tests, boundaries, dependency necessity; record name, detected version, references consulted, idiom confidence |
| `docs:system` | Broad documentation-graph health check, summary-first |
| `docs:source-of-truth`, `docs:reachability`, `docs:entrypoint-conflict`, `docs:stale`, `docs:todo`, `docs:guidance`, `docs:metadata`, `docs:reference` | Narrow docs reviews; catalog, decision order, and scope rules in `references/docs-modes.md` |
| `entrypoint-check` | Read-only check that README, docs index, architecture/service/design-system docs, operational docs, and an agent entrypoint exist and route an agent `README → docs index → architecture → services → code` |
| `bootstrap` | `entrypoint-check` plus skeleton proposals for missing targets only, when the user explicitly asks for 初期化 / 雛形 / ひな形 / テンプレート / 叩き台 (a negated keyword such as 雛形は不要 means `entrypoint-check`) |

There is no diff/PR mode: for PR, diff, or patch review use the environment's normal review workflow (for example `/code-review`), and use this skill only when a broad assessment of the surrounding codebase is also wanted.

## Workflow

1. **Set task and artifact directory.** Choose the mode (for `docs:*` use the decision order in `references/docs-modes.md`). Create `.context/repo-evaluator/<task>/` (`<YYYYMMDD>-<target-slug>` when no name is given; append `-2`, `-3` if it exists). Record target, mode, requested scope, exclusions, and assumptions.
2. **Acquire context.** Read `AGENTS.md`, `README*`, `docs/`, architecture/rules docs first. Inventory the tree with the default exclusions. `code:*`: also manifests, lockfiles, license/notice files, test/lint/typecheck config, CI/CD, build/deploy config, core source. `docs:*`: enumerate documentation text and classify each file (`entrypoint`, `index`, `canonical`, `policy`, `spec`, `skill`, `historical`, `temporary`, `task-tracking`, `deprecated`, `generated`, `out-of-scope`). Save `inventory.md`.
3. **Plan sampling** for large targets and save `sampling-plan.md`; report inspected and uninspected areas.
4. **Map structure.** `docs:*`: build the reachability map from canonical entrypoints (links and named paths; reachable, historical-only, orphaned, competing first-read, broken anchors) and classify source-of-truth boundaries; save `reachability.md` and `source-of-truth.md`. `entrypoint-check` / `bootstrap`: apply the detection rules in `references/docs-entrypoint-bootstrap.md`.
5. **Load references and evaluate.** Read `references/evaluation-rubric.md` (shared format plus the code or docs pillars). `code:license`, or any mode with dependency manifests in scope: `references/code-license-triage.md`. `docs:*`: the `Evaluation Checklist` in `references/docs-modes.md`; knowledge bases or durable notes: `references/docs-knowledge-system-patterns.md`. Save `raw-findings.md`. Each issue needs evidence, impact, recommended next action, and confidence; tag security findings `static-review-only` when no scanner or dynamic test ran; include `What I Would Not Preserve` when existing structure should not constrain redesign.
6. **Run checks with the mutation guard** (below); save commands, exit status, and skipped checks to `checks.md`.
7. **Write the report.** Read `references/report-template.md` and the mode's required properties, save `report.md`, and return a concise chat summary: report path, top risks, score/confidence, checks run and not run. `entrypoint-check` / `bootstrap` return the fixed section order from the template instead of scores.

## Check Mutation Guard

- Run tests, lint, typecheck, build, link checks, or inventory scripts only when useful for the scope and available without install, upgrade, codegen, migration, formatter-write, autofix, or dependency changes. Prefer the repo's own `scripts/docs-link-check` for local Markdown links; a non-zero exit from broken links is evidence, not skill failure.
- Inside a git worktree, record `git status --short` before and after checks in `checks.md`; pre-existing dirtiness is baseline, not your change.
- Never run commands expected to write tracked source, docs, configs, lockfiles, snapshots, generated artifacts, or dependency state. If a check writes ignored cache/output files, record the path category and reason. If it writes tracked or review-relevant files, stop further checks and report the mutation; do not clean up or revert unless the user asks.
- Do not check external URL reachability by default; for `docs:reference` evaluate whether references document purpose, freshness signal, and verification responsibility, and verify on the web only when the user asks or external freshness is the primary risk (record `verified_at` and scope).

## Priority and Report Properties

- `P0` blocker; `P1` high design, security, license, or documentation-system risk; `P2` meaningful maintainability, dependency, or AI-readability risk; `P3` optional cleanup. Priority follows risk and design importance, not human work phasing; do not split recommendations into short/medium/long for that reason.
- Add migration cautions only for destructive data changes, public API compatibility, product behavior, security boundaries, or license/legal review.
- Required sections per mode are in `references/report-template.md` (code and entrypoint modes) and `references/docs-modes.md` (`Required Report Properties`, docs modes). Summary-first for `code:whole` / `docs:system`; findings-first for narrow modes.

## Entrypoint Check and Bootstrap Rules

- Target is the current repository only. Do not mention external services or other repositories, propose new skills or skill-system changes, or change repo config, CI, or code scaffolding; existing skills may receive description improvements only.
- `entrypoint-check` output: findings in the fixed categories (`docs-index`, `architecture`, `services`, `design-system`, `operational`, `entrypoint`, `spec-structure`, `size`), at most 3 per severity; when `critical`/`high` exist, suppress low-value style remarks. Name candidate paths and headings only; no starter paragraphs, Markdown bodies, or ready-to-paste blocks.
- `bootstrap` output adds skeletons only for targets that do not exist, limited to README, docs index, agent entrypoint, architecture overview, service index, design-system index, and operational docs/ADR. Existing files such as `README.md` or `AGENTS.md` are reported as "既存のため新規候補なし" even when the user asks for a skeleton; their content review belongs to `docs:*`. When a skeleton draws on existing docs, say so and do not present it as a replacement.
- A doc that exists under a non-recommended path is a "normalize to the recommended path" proposal, not a missing target.

## Boundaries

- Engineering triage, not legal advice; visible security hygiene, not a security or compliance certification.
- Do not declare a license safe because the name is familiar, or GPL/LGPL/MPL forbidden automatically; weigh distribution context, obligations, prior accepted signals, and remediation evidence. No-license, unclear, non-commercial-only, commercial-prohibited, and field-of-use-restricted dependencies are blockers or strong needs-confirmation items.
- Do not expand into prose proofreading, SEO/readability formulas, code execution for docs, secrets/PII scanning, auto-fixes, pull requests, or document deletion. Full docs boundaries, including metadata hygiene on legacy docs, are in `references/docs-modes.md`.

## Validation

```bash
scripts/skill-quick-validate skills/repo-evaluator
```

Run from the publisher source repository root, not from the installed skill directory.
