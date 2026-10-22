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

`source_branch` complements `source_drift` by asking where the recorded path came from, across `~/.claude/skills`, `~/.agents/skills`, and `~/.codex/skills`:
- `SOURCE_BRANCH_OK`: `metadata.local-path` is under the `chezmoi source-path` checkout and not inside a branch worktree
- `SOURCE_BRANCH_WORKTREE` (warn): `metadata.local-path` contains `/.claude/worktrees/`, i.e. the skill was installed from a branch worktree (for example while a new skill was under review). Acceptable until the branch merges; then reinstall from the publisher source with `gh skill install . <name> --from-local --agent <agent> --scope user --force`. The path is not resolved strictly, so a removed worktree still reports this code (together with `LOCAL_PATH_MISSING` from `source_drift`)
- `SOURCE_BRANCH_OUTSIDE_SOURCE` (warn): `metadata.local-path` is outside the `chezmoi source-path` checkout altogether (a second clone, a `.context/` copy); same remediation as `SOURCE_PATH_STALE`
- `SOURCE_PATH_UNRESOLVED` (warn): the publisher source could not be resolved, so the check was skipped

The script also cross-checks retirement declarations and Codex sync across `~/.claude/skills`, `~/.agents/skills`, and `~/.codex/skills`. It reads the install manifest at `<chezmoi source-path>/docs/skills-install-manifest.md` (override with `SKILL_MANAGER_MANIFEST`; `~/.agents` with `SKILL_MANAGER_AGENTS_HOME`) and prints progress lines on stderr:

- `retired_skills`:
  - `RETIRED_STILL_DEPLOYED` (warn): a deployed skill matches a manifest heading marked `（撤去済み）`, including globs such as `gws-*`. Active first-party skills in the publisher source are never matched by a glob
  - `FIRST_PARTY_NOT_IN_SOURCE` (warn): the install carries `metadata.local-path` but `skills/<name>` no longer exists in the publisher source (merged or retired first-party skill, e.g. a model-specific tuning skill folded into another)
  - `RETIRED_IN_LOCK` (warn): `~/.agents/.skill-lock.json` still has an entry for a retired skill
  - `MANIFEST_UNRESOLVED` (warn): no manifest found, so retirement checks were skipped
- `first_party_sync`:
  - `FIRST_PARTY_MISSING` (fail): the manifest installs the skill for an agent (`codex` covers both `~/.agents/skills` and `~/.codex/skills`) but the directory is missing
  - `FIRST_PARTY_CONTENT_STALE` (warn): the deployed copy differs from the publisher source (description, body, or any bundled file; install-time `metadata` is ignored)
  - `CODEX_MIRROR_STALE` (warn): `~/.codex/skills/<name>` differs from `~/.agents/skills/<name>`, i.e. the manifest's rsync step was skipped after `gh skill install --agent codex`

Remediation stays user-approved and follows the repository policy, not this skill:

1. Retired skills: move each flagged directory out of all three deployment directories into a dated retire directory (or `gh skill remove <name> --agent <agent> --scope user`). For `RETIRED_IN_LOCK`, back up the lock file first and remove only the matching entries with a JSON-aware tool (`jq` / `python3`), never by text substitution.
2. Codex sync: from `cd "$(chezmoi source-path)"`, rerun the manifest's Codex block (`gh skill install . <name> --from-local --agent codex --scope user --force`), then `rsync -a --delete ~/.agents/skills/<name>/ ~/.codex/skills/<name>/` per skill. Copy the existing `~/.codex/skills/<name>` aside first if it may hold local edits. Leave Codex-only skills (e.g. bundled ones such as `hatch-pet`) and `.system` untouched.
3. Rerun `doctor` and confirm `retired_skills` and `first_party_sync` report `NO_ISSUES`.

### `parity`

Check whether the dotfiles source and the agent environments still match (formerly the `agent-env-parity` skill). The checks themselves live in existing scripts; this command only decides which check runs where and how the result is summarized. Do not reimplement a check or write a new comparison script; if a check is missing, propose it as a change to the owning script.

Premises:
- The source of truth is the checkout returned by `chezmoi source-path`. Cloud sessions clone the default branch of origin, so local unpushed changes do not exist in the cloud.
- Every step is read-only. Remediation (delete, move aside, reinstall, `chezmoi apply`, push) happens only after showing the result and getting the user's approval, through the owner in the table below.
- A worktree created by the Agent tool's `isolation: "remote"` (or any `.claude/worktrees/` worktree) is not a cloud environment. Treat only results taken inside an actual cloud session as cloud measurements; never infer cloud state from a local run.

| Aspect | Check | Runs | Remediation owner |
|---|---|---|---|
| Source checkout vs origin | `git -C "$(chezmoi source-path)" fetch origin`, then `git -C "$(chezmoi source-path)" rev-list --left-right --count HEAD...origin/HEAD` and `git status --short` | local | user decision (pull / push need approval) |
| Skill deployment (retired skills still deployed, drift from source, `~/.codex/skills` mirror gaps, branch-worktree installs) | `doctor` (`retired_skills` / `first_party_sync` / `source_drift` / `source_branch`) | local | `doctor` remediation steps above |
| Local dotfiles (Claude / Codex config and other managed files) vs the real files | `scripts/chezmoi-drift` (no arguments) and `scripts/chezmoi-drift --check-ignore` | local | dotfile-update skill; `--apply` / `--restore` change state and need approval |
| Cloud environment reproduction (skills / CLIs / MCP / presence of secrets) | `scripts/verify-cloud-parity --json` | inside a cloud session (locally, cloud-only items show `N/A`) | keep `scripts/bootstrap-web` and `docs/skills-install-manifest.md` in sync (dotfiles `AGENTS.md`, skill management section) |

Steps:
1. Decide the aspects (one row when the request names one aspect; all rows top to bottom for "check everything") and create `.context/<task>/` (`agent-env-parity-<YYYY-MM-DD>` when no task name is given).
2. Record the source checkout location and its ahead/behind count against origin. When it is not in sync, state in the report that "drift from source" below means drift from the local checkout, not from origin.
3. Run `bash <skill-dir>/scripts/executable_doctor.sh > .context/<task>/doctor.json 2> .context/<task>/doctor.log`, then extract the non-pass items of `retired_skills`, `first_party_sync`, `source_drift`, and `source_branch`. Other categories (plugins and so on) are out of scope; keep only their counts.
4. From the dotfiles checkout root run `scripts/chezmoi-drift` and `scripts/chezmoi-drift --check-ignore` and save the output. Without options they only list; they never apply or restore.
5. Inside a cloud session run `scripts/verify-cloud-parity --json` and save it. A local run only confirms local prerequisites (CLIs, chezmoi layout) and must not be written up as a cloud result.
6. Summarize everything in one table.

Output: `.context/<task>/parity-report.md` with Front Matter `task` / `phase_or_step` / `created_at`, containing:
- a verdict per aspect (`OK` / `drift` / `not checked`, with the reason)
- the list of gaps: aspect, subject (skill name, file, CLI), check code (for example `RETIRED_STILL_DEPLOYED`, `CODEX_MIRROR_STALE`, `SOURCE_BRANCH_WORKTREE`, `MISSING`), remediation owner
- proposed remediation, not executed; mark every operation that needs approval (delete, move aside, reinstall, `chezmoi apply`, push)
- the path of each check's raw output

Never print secret values. `verify-cloud-parity` reports only the presence of secrets, so its output may be pasted as is.

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
