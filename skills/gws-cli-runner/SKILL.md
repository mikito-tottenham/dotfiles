---
name: gws-cli-runner
description: Run Google Workspace CLI (`gws`) through the repository-managed account-scoped wrapper. Use when Claude Code or Codex needs to execute, configure, debug, or propose `gws` commands, especially where OAuth profile selection, credential paths, Personal-owned account mapping, `.env` account cache, 1Password restore, fallback policy, or avoidance of wrong Google principals matters. Also use whenever a `gws` auth error appears — `invalid_rapt`, `invalid_grant`, `403 org_internal`, `token_valid` false, expired or missing credentials — before attempting any manual recovery.
---

# GWS CLI Runner

Use `gws-account <profile> ...` as the normal execution path for Google Workspace CLI work.
Do not call `gws` directly for account-scoped work unless the user explicitly asks for raw `gws` behavior or the task is only inspecting local help/version output.

## Responsibilities

This Skill owns the agent workflow around account-scoped `gws` use.
The wrapper owns final local enforcement.

This Skill exists because a thin wrapper can reject unsafe local execution, but it cannot make the agent choose the account source, consult repository-local cache rules, or recover through the same-profile restore/login path before execution.

- Preserve explicit profile selection.
- Avoid silent fallback to another Google principal.
- Respect caller-provided environment such as repository-local `.env`.
- Restore or relogin only for the same selected profile.
- Keep concrete account identifiers, profile names, responsibility labels, credential paths, and real 1Password references out of git-managed files.

## Workflow

1. Determine the intended local profile from the user's request, the working repository's docs, or environment already provided by the caller.
2. If no profile is available, ask the user instead of guessing.
3. If a working repository defines how to load `.env`, use that repository's rule. Do not invent a new `.env` contract from this Skill; if no rule is available, ask the user.
4. If Personal is the source of account mapping or credential location, ask Personal for the non-secret profile/path decision only. Do not pass secret values, secret references, tokens, or authenticated session data to Personal. If a Personal agent/tool is unavailable, ask the user instead of simulating Personal.
5. Run `gws-account <profile> <gws args...>`.
6. If credentials are missing or expired, recover only within the same profile, following the Recovery Runbook below for the observed error shape:
   - Use the repository's existing 1Password materialization flow when it exists.
   - Otherwise run `gws-account <profile> auth login` when interactive login is appropriate.
7. Record any persistent workflow change in the working repository docs or the relevant Skill, not in ad hoc memory.

## Environment Contract

The wrapper uses these inputs when present:

- `GWS_ACCOUNT_CONFIG_DIR`: override the selected profile config directory.
- `GWS_ACCOUNT_CREDENTIALS_FILE`: explicitly provide a portable credentials file for the selected profile.

The wrapper refuses these unsafe ambient overrides:

- `GOOGLE_WORKSPACE_CLI_TOKEN`
- ambient `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` when `GWS_ACCOUNT_CREDENTIALS_FILE` was not explicitly set

## Fallback Policy

Allowed recovery paths:

- Restore credentials for the same selected profile.
- Re-run OAuth login for the same selected profile.
- Inspect `auth status`, `auth login`, `schema`, or help commands when credentials are not yet present.

Forbidden recovery paths:

- Switching to another Google account or local profile.
- Retrying with raw `gws` after `gws-account` rejects the environment.
- Treating another account's successful command as a fallback.
- Writing account names, profile names, credential paths, or secret references into git-managed docs unless the working repository explicitly owns that data.

## Recovery Runbook

Classify the observed failure shape first, then follow the matching recovery. All recovery stays within the selected profile; another profile is acceptable only when that profile's own account boundary already matches the task, never as a substitute principal for the failed profile.

| Observed shape | Meaning | Recovery |
|---|---|---|
| `auth status` shows `"token_valid": false` with `reauth related error (invalid_rapt)`, or API calls return `401 invalid_grant: reauth related error (invalid_rapt)` | The selected profile's OAuth token expired; interactive reauth is required | 1. Confirm with `gws-account <profile> auth status`. 2. Check `auth status` of other profiles; if a still-valid profile matches the task's account boundary, continue that boundary's work while reauth waits. 3. Run `gws-account <profile> auth login` in the foreground and tell the user exactly which email to choose on the browser account picker. 4. Resume only after `auth status` shows `"token_valid": true`. |
| Browser shows `403 org_internal` during login; the CLI itself reports nothing | An out-of-organization account was chosen on the browser account picker | Re-run `gws-account <profile> auth login` for the same profile and state the correct email explicitly. Never quote a working-account name from another environment's docs as the login target. |
| Wrapper exit `66` | Credentials/config missing for the selected profile | Follow the wrapper's message: use the repository's 1Password materialization flow when it exists, otherwise `gws-account <profile> auth login`. |
| Wrapper exit `78` | Unsafe ambient credential override present | Unset the ambient variable and re-run through the wrapper. Do not retry with raw `gws`. |
| `401 invalid_client` | Legacy ambient `GOOGLE_WORKSPACE_CLI_*` environment from a pre-wrapper setup | Should not recur under the wrapper (exit `78` guard). If seen, inspect and remove legacy ambient variables instead of re-running auth setup. |

Known-useless moves — each observed to fail; do not repeat them:

- Running `auth login` in the background. It hangs waiting for the browser; always run it foreground.
- Inventing environment-variable switches such as `GWS_ACCOUNT=...`. Profile selection exists only as the wrapper argument.
- Re-running `gws auth setup` for token expiry. It has side effects and does not refresh tokens.
- Retrying the same failed command after waiting; token expiry never self-heals.
- Adding `--full` / `--scopes` to `auth login` for expiry recovery; those flags are for scope expansion only.

## Command Patterns

Use file-backed prompts or `.context/` artifacts for complex handoffs and long command plans.
For simple commands, run the wrapper directly:

```bash
gws-account <profile> auth status
gws-account <profile> auth login
gws-account <profile> drive files list --params '{"pageSize": 5}'
```

When a command fails, classify the failure before continuing:

- Exit `66` / exit `78` / auth errors: follow the Recovery Runbook above.
- Exit `127`: `gws` is not installed or not in `PATH`.
- `rg` exit `1` during local checks means no matches, not a command failure.
