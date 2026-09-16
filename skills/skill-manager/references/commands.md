# Skill Manager Command Reference

Procedures for each `skill-manager` subcommand, moved out of `SKILL.md`. Read only the section for the command being run; routing, inventory rules, and validation stay in `SKILL.md`.

### `find [query]`

Search external skills.

Steps:
1. Prefer `gh skill search [query]`
2. Summarize the candidate skills
3. If the user is choosing between candidates, call out supported agents and likely fit

### `list [--global] [--json]`

Inventory installed skills, grouped by agent and provenance.

Script-backed path: `scripts/executable_list.sh [--full]` prints the merged inventory as JSON (see `Scripts` in `SKILL.md`). Use the manual steps below only when python3 is unavailable or the JSON needs cross-checking.

Preferred steps:
1. Scan vendored/manual and directly installed skill directories
   - global: `~/.claude/skills/*/SKILL.md`
   - project: `<git-root>/.claude/skills/*/SKILL.md`
   - codex global: `~/.codex/skills/*/SKILL.md` and `~/.codex/skills/*`
   - codex project: `<git-root>/.agents/skills/*`
2. Scan plugin inventories separately
   - Claude marketplace: `~/.claude/plugins/installed_plugins.json`, `known_marketplaces.json`, marketplace manifest
   - Codex plugin config: `~/.codex/config.toml`
   - Codex plugin cache: `~/.codex/plugins/cache/*/*/*/.codex-plugin/plugin.json`
   - Codex bundled marketplace manifest: `~/.codex/.tmp/bundled-marketplaces/*/.agents/plugins/marketplace.json`
3. Merge the results into one inventory

Output should show:
- skill name
- bare skill name and display name when they differ
- scope
- installed agents
- provenance
- path
- source-aware identity fields such as `source_type`, `source_id`, and stable `identity`
- Codex status such as `installed`, `missing`, `broken`, `system-preferred`
- source identity without flattening plugin / user / project / system origins into one unnamed bucket
- explicit collision records when the same bare skill name appears in multiple sources
- Codex plugin status such as `enabled`, `configured`, `cached`, `available`

Important:
- If a skill exists in Claude but not Codex, report that as inventory data, not as an error by default.
- If a skill name collides with Codex `.system`, mark it `system-preferred`.
- Treat valid direct installs in Codex as healthy even if no mirror manifest entry exists.
- Aggregate skills in a source-aware way. Preserve plugin namespace and origin metadata instead of merging entries by bare skill name.
- Treat Codex plugin-provided skills as their own source type, separate from direct installs under `~/.codex/skills`.

### `gh install <repo-or-skill> [--pin <ref>]`

Install an external skill via `gh skill install`.

Use this when the user has `gh >= 2.90.0` and wants GitHub-native skill management.

Steps:
1. Confirm `gh` version supports `gh skill`
2. Run `gh skill preview <repo-or-skill>` before installation when practical
3. Run `gh skill install <repo-or-skill> [--pin <ref>]`
4. Re-run `list` or inspect the target agent directory to confirm placement
5. Report recorded provenance metadata and whether the install remains an external skill managed outside the current repository

Guidance:
- Prefer `gh skill install` when the user values provenance, pinning, and GitHub-native update/publish behavior
- If the current repository keeps original skills in git and external skills outside the repo, preserve that boundary

### `codex install <skill-or-github-path>`

Install into Codex through the Codex `.system/skill-installer` helper only when the user explicitly wants that path.

Use this when:
- the target is Codex only
- the source is `openai/skills` curated or experimental skills
- the user provides a GitHub repo/path and does not need `gh skill` provenance or cross-agent lifecycle

Guidance:
- Prefer `gh skill install` for durable external installs, pinning, update checks, and multi-agent installs.
- Treat installed results as Codex direct installs under `$CODEX_HOME/skills`, not as `gh skill`-managed installs.
- If the skill becomes part of the user's reproducible setup, record the repo, path, ref, and reason in the local install manifest instead of relying on Codex state alone.
- Do not use `skill-installer` for Codex `.system` skills; they are preinstalled system capabilities.

### `remove <skill> [--agent <agent...>] [--global]`

Remove a `gh skill`-managed installation.

Steps:
1. Run `gh skill remove <skill> ...`
2. Re-run `list`
3. If the skill still appears because it is vendored/manual, explain that the external install was removed but a git-managed copy remains

### `check`

Check for updates to external skills.

Steps:
1. Run `gh skill update --dry-run`
2. Summarize available updates
3. If a skill is vendored in the current repository, treat upstream updates as advisory and do not overwrite the vendored copy automatically

### `update`

Update `gh skill`-managed external skills.

Steps:
1. Run `gh skill update`
2. Re-run `list`
3. Report which installs changed
4. If the updated skill is also vendored here, explicitly note that the repo copy did not change

### `publish`

Publish a skill with `gh skill publish`.

Use this when the user wants to publish a skill to GitHub in a way that validates against agentskills.io and records GitHub-native release metadata.

Guidance:
- Prefer `gh skill publish` for GitHub-hosted public distribution
- Call out that GitHub recommends inspecting skills before install and that `gh skill` does not verify prompt safety for the user
- Treat repository security checks such as tag protection, secret scanning, and code scanning as part of the release-readiness review

### `adopt <skill>`

Adopt an external skill into a git-managed repository copy when the user explicitly wants that lifecycle.

Use this flow only when the repository policy permits git-managed adoption or when the skill is confirmed to be repo-original rather than external.

Steps:
1. Confirm whether the skill is `repo-original` or `external`
2. If it is external, check whether the current repository allows adoption into git-managed copies
3. If the repository forbids adoption, stop and point back to `gh skill install` / `gh skill update` plus the local policy docs
4. If it is repo-original, manage it in the appropriate git-managed location and update docs as needed

Important:
- Do not mirror upstream content into a repository just to make an install persistent unless the user wants a git-managed fork or local derivative

### `doctor`

Audit installed skills for drift, broken references, and policy mismatches.

Check:
- broken installed paths
- broken symlinks
- stale mirror metadata
- vendored skills missing from expected agent directories
- agent-specific installs that appear accidental
- broken Codex plugin cache or config entries
- Codex plugin declarations whose `skills`, `apps`, or `mcpServers` payload is missing
- collisions with Codex `.system`
- deprecated command-format skills still present

Detection-first only.
Do not rewrite state unless the user asks.

Script-backed checks (`scripts/executable_doctor.sh`) also emit a `source_drift` category for first-party installs:
- `SOURCE_PATH_OK`: installed `metadata.local-path` equals `<chezmoi source-path>/skills/<name>`
- `SOURCE_PATH_STALE` (warn): `metadata.local-path` exists but lies outside the publisher source returned by `chezmoi source-path` (for example a second clone under `~/.local/share/chezmoi`); the fix is to reinstall from the publisher source root with `gh skill install . <name> --from-local --agent <agent> --scope user --force`
- `SOURCE_PATH_RENAMED` (warn): under the publisher source but not at `skills/<name>`
- `LOCAL_PATH_MISSING` (fail): the recorded path no longer exists
- `SOURCE_PATH_UNRESOLVED` (warn): neither `chezmoi source-path` nor `SKILL_MANAGER_SOURCE_PATH` resolved, so the check was skipped

Without the script, do the same check by hand: `chezmoi source-path`, then `grep -h 'local-path' ~/.claude/skills/*/SKILL.md ~/.codex/skills/*/SKILL.md` and compare prefixes.

### `sync codex`

Compatibility command for repo-managed mirroring into Codex.
Do not use this as the default way to understand whether a skill is healthy in Codex.
The standard Codex path is a valid install under `~/.codex/skills` or `.agents/skills`, including direct copies created by `gh skill install`.

Use only for skills whose policy is explicitly `mirror`.
Do not assume all Claude skills should sync into Codex.
Skip:
- agent-specific Claude-only skills
- Codex `.system` collisions
- trial installs that have not been adopted into git
