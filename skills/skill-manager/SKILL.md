---
name: skill-manager
description: "Manage or inventory agent skills across Claude Code, Codex, and other hosts. Use for skill discovery, installation, removal, updates, provenance, collisions, adoption, or cross-agent differences."
---

# Skill Manager

External skill management workflow centered on `gh skill`, with Codex `.system/skill-installer` recognized as a Codex-only helper.
This skill no longer assumes that Claude Code and Codex must have the same skill set.
Treat agent differences as normal, and track why each skill exists where it does.
When a repository has its own skill policy in `AGENTS.md`, ADRs, or equivalent docs, follow that local policy instead of hard-coding repo-specific rules into this skill.

## Core model

Manage skills with three concepts:

1. **Provenance**: where the skill came from
   - `codex-installer`: installed into Codex by the Codex `.system/skill-installer` helper
   - `vendored`: copied into a git-managed repo and managed by git
   - `manual`: hand-written local skill not tied to a remote package
   - `plugin`: bundled through another plugin system
2. **Scope**:
   - `global`: user-level install
   - `project`: repo-level install
3. **Installed agents**:
   - Claude Code only
   - Codex only
   - multiple agents

Do not assume parity across agents.
A skill may intentionally exist only in Claude, only in Codex, or in both.

## Primary backend

Use `gh skill` as the default backend for external skill discovery, installation, update, and publishing when `gh >= 2.90.0` is available.

When `gh` is version `2.90.0` or newer, `gh skill` is available in public preview as an official GitHub CLI subcommand.

Treat the tools like this:

- `gh skill`: GitHub-native preview/install/update/publish flow with provenance metadata and agent-host aware placement
- Codex `.system/skill-installer`: Codex-only helper for listing OpenAI curated/experimental skills or copying a GitHub repo path into `$CODEX_HOME/skills`

Prefer `gh skill` when the user wants:
- install provenance recorded into `SKILL.md`
- pinning and update checks tied to GitHub refs and tree SHA
- `gh skill publish` validation against agentskills.io and GitHub release-based publishing
- a new install path going forward

Use Codex `.system/skill-installer` only when the user specifically wants the Codex curated/experimental skill list or a quick Codex-only install from `openai/skills` or a GitHub path.
After such an install, inventory it as a Codex direct install and document stable external dependencies in the repository manifest when the install should be reproducible.
Do not treat `skill-installer` as the long-term cross-agent lifecycle backend.

## What this skill manages

- external skills installed via `gh skill`
- Codex direct installs created by `.system/skill-installer`, as inventory entries and reproducibility follow-up
- git-managed original skills stored in a repository
- agent-specific differences between Claude Code, Codex, Gemini CLI, Cursor, etc.
- inventory and policy decisions about whether a skill is repo-original, external, or out of scope
- Claude marketplace plugin inventory and health checks when plugin-provided skills matter
- Codex plugin inventory and health checks based on `~/.codex/config.toml`, marketplace metadata, and local plugin cache

## What this skill does not treat as the same thing

- MCP servers
- Codex `.system` skills

These can still be inventoried when useful, but they are not the primary package model for this skill.
Plugins are managed as a separate layer from `gh skill` installs and should not be flattened into the same lifecycle.

## First-party install source

First-party skills (this repository's `skills/`) are installed with `gh skill install . <name> --from-local --agent <agent> --scope user`, which records the source directory as `metadata.local-path` in the installed copy. That path is the only provenance link back to the publisher source, so:

- Always run the install from the root returned by `chezmoi source-path` (the ghq checkout of the dotfiles repository). Never run it from another clone such as `~/.local/share/chezmoi`, a worktree, or a `.context/` copy; a second clone produces installs whose `metadata.local-path` points at a checkout that drifts from the one being edited.
- `docs/skills-install-manifest.md` is the list of what to install; its `.` means that root, not the current directory.
- `doctor` flags installs whose `metadata.local-path` is outside `<chezmoi source-path>/skills` as `SOURCE_PATH_STALE`; fix them by reinstalling from the correct root with `--force`, not by editing the installed copy.

## Command routing

Parse `$ARGUMENTS` and choose one of the commands below. If the user intent is ambiguous, default to `list`. Each command's procedure is in `references/commands.md`; read only that section.

| Command | Purpose | Backend |
|---|---|---|
| `find [query]` | Search external skills | `gh skill search` |
| `list [--global] [--json]` | Inventory installed skills, plugins, and collisions | `scripts/executable_list.sh` |
| `gh install <repo-or-skill> [--pin <ref>]` | Install an external skill with provenance | `gh skill preview` / `gh skill install` |
| `codex install <skill-or-github-path>` | Codex-only install via `.system/skill-installer` | Codex helper |
| `remove <skill> [--agent ...] [--global]` | Remove a `gh skill`-managed install | `gh skill remove` |
| `check` | Dry-run update check | `gh skill update --dry-run` |
| `update` | Update external installs | `gh skill update` |
| `publish` | Publish a skill to GitHub | `gh skill publish` |
| `adopt <skill>` | Adopt an external skill into a git-managed copy | manual, policy-gated |
| `doctor` | Detect drift, broken installs, collisions, stale first-party sources | `scripts/executable_doctor.sh` |
| `sync codex` | Compatibility mirror for skills whose policy is explicitly `mirror` | manual |

## Scripts

`list` and `doctor` are backed by scripts in this skill's `scripts/` directory (about 57KB of Python; do not read them unless changing them). They need only `python3` and, for `doctor`'s source-drift check, `chezmoi` on `PATH` or `SKILL_MANAGER_SOURCE_PATH`.

```bash
bash <skill-dir>/scripts/executable_list.sh            # inventory JSON (add --full for plugin payloads)
bash <skill-dir>/scripts/executable_doctor.sh          # checks JSON with summary/pass/warn/fail
```

`<skill-dir>` is `skills/skill-manager` in the publisher source or the installed directory under `~/.claude/skills` / `~/.codex/skills`; the installed copy keeps the `executable_` filename prefix and no execute bit, so invoke through `bash`. Both scripts print JSON to stdout and never modify state. Override home directories with `SKILL_MANAGER_CLAUDE_HOME` / `SKILL_MANAGER_CODEX_HOME` when auditing another user's layout.

## Inventory rules

When presenting inventory, classify each skill into one of these states:

- `shared`: intentionally installed in multiple agents
- `agent-specific`: intentionally installed in a subset of agents
- `vendored`: repo-managed copy exists
- `trial`: installed directly for evaluation but not promoted into repo management
- `installed`: valid install exists in the target agent directory
- `missing`: no install exists in the target agent directory
- `broken`: installed path or metadata is invalid
- `system-preferred`: Codex has a `.system` skill with the same name

When multiple entries share the same bare skill name:

- keep them as separate inventory entries if their sources differ
- preserve plugin namespacing where the host exposes it
- report the collision instead of silently collapsing entries into one
- only apply hard preference automatically for Codex `.system`
- Codex plugin-provided skills count as a separate source from Codex direct installs

## Prompting guidance

When helping the user choose a management path:

- Prefer `gh skill install` for new installs
- Use Codex `.system/skill-installer` only as a Codex-only convenience path for curated/experimental OpenAI skills or one-off GitHub-path installs
- Follow repository-local policy docs for the boundary between external installs and git-managed copies
- Prefer reporting agent differences instead of automatically syncing them away
- Keep plugin management separate from skill installs, but include Claude and Codex plugins when the user is auditing actual availability
- For Codex plugins, treat `~/.codex/config.toml` plus marketplace metadata as the control plane and `~/.codex/plugins/cache` as the local realized state

## Validation

After updating this skill:

1. Run `scripts/skill-quick-validate <skill-dir>` from this repository
2. If helper scripts were changed, run `bash scripts/executable_doctor.sh | python3 -m json.tool >/dev/null` and `bash scripts/executable_list.sh >/dev/null` as smoke checks
3. Re-read the whole `SKILL.md` and remove contradictions with current tooling
4. If the repo-local validator is unavailable, use the `skill-creator` validator as a fallback and record any runtime dependency issue

For this repository's publisher source, use:

```bash
scripts/skill-quick-validate skills/skill-manager
```
