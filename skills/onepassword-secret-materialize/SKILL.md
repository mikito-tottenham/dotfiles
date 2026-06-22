---
name: onepassword-secret-materialize
description: Manage this dotfiles repository's 1Password-backed secret file workflow. Use when the user asks to save, register, restore, diff, check, or materialize secret-backed files such as VPN configs, env files, API-key dotenv files, or other local config files through 1Password, especially with `opmaterialize`, `Secrets Manifest`, `Dotfiles Secrets`, `OP_ACCOUNT`, or paths under `~/.config`.
---

# Onepassword Secret Materialize

Use this skill for file-based secrets that should be reproducible on other machines without storing secret values or individual secret item names in git.

The repository owns the generic tool and policy. 1Password owns the sensitive manifest and file contents.

## Default Model

- Account selector: `my.1password.com`
- Vault: `Dotfiles Secrets`
- Manifest item: `Secrets Manifest`
- Managed restore tool source: `scripts/opmaterialize` inside this skill
- Optional deployed wrapper after `chezmoi apply`: `~/.local/bin/opmaterialize`
- Generated local files remain ignored by `.chezmoiignore`

Do not print secret file contents. Do not add materialized files, manifest rows, VPN configs, API keys, tokens, private keys, or real `op://...` references to git.

## Manifest Layout

The manifest is a TSV with columns `type  item  out_path  mode  vault`, stored in the `notesPlain` field of the `Secrets Manifest` Secure Note. Each row's `type` is one of:

- `field`: the file body is a Secure Note field (default label `content`, override with `OP_DOTFILES_MATERIALIZE_FIELD_LABEL`). This is the default layout for `Dotfiles Secrets`.
- `document`: the file body is a 1Password Document.

`restore` and `diff` support both types. `add` is document-based only and refuses against a field-based (Secure Note) manifest; register field-based secrets manually in 1Password (a Secure Note with a `content` field plus a `field` manifest row).

## Stable Invocation

Before any live 1Password operation, verify the command path and authentication state without printing secret material:

```bash
command -v opmaterialize
OP_ACCOUNT=my.1password.com op account get
OP_ACCOUNT=my.1password.com op vault get "Dotfiles Secrets"
```

If `opmaterialize` is not on `PATH`, use the bundled script form shown below. If `op` is not authenticated from the current agent process, stop after the readiness probe and ask the user to unlock or sign in from their normal terminal; repeated AI-side permission approvals are not a stable recovery path.

Run `opmaterialize add` for one file at a time. Do not pass multiple secret-backed files to one `add` invocation.

## Choose The Operation

### Save Or Register A Local Secret-Backed File

Use this when the user says a file is ready and should be saved for other PCs.

> Note: `add` is document-based and refuses against the field-based default vault (see Manifest Layout). Register field-based secrets manually for now.

1. Confirm the file exists without printing its contents:

   ```bash
   test -r <path>
   ```

2. Register it with 1Password and update `Secrets Manifest`:

   ```bash
   opmaterialize add <path>
   ```

   Run one `add` command per file.

   If the deployed command is not available in the current shell, run the bundled script:

   ```bash
   OP_ACCOUNT=my.1password.com \
   OP_DOTFILES_MATERIALIZE_VAULT="Dotfiles Secrets" \
   sh ~/.codex/skills/onepassword-secret-materialize/scripts/opmaterialize add <path>
   ```

3. Report only the created/updated item name and manifest status from command output. Do not show file contents.

Use `--item`, `--out-path`, `--mode`, or `--vault` only when the user asks for an override or the default path/name would be wrong.

### Check Restore Impact

Run this before restore when the user wants to know what would change, or when restore might overwrite existing local files.

```bash
opmaterialize diff
```

Interpretation:

- `missing`: a manifest-declared file is absent locally
- `changed`: local file differs from the stored 1Password secret
- `unchanged`: local file already matches
- exit `1`: at least one file is missing or changed
- exit `0`: no differences

The diff command must not print secret contents or write target files.

### Restore Secret-Backed Files

Use this when setting up a new machine or rehydrating ignored local config files.

1. Check first unless the user explicitly asks to restore immediately:

   ```bash
   opmaterialize diff
   ```

2. Restore:

   ```bash
   opmaterialize restore
   ```

3. If restore stops because a target differs, do not force overwrite silently. Explain the path and ask whether to use:

   ```bash
   opmaterialize restore --force
   ```

## Troubleshooting

- If `op` reports multiple accounts, use `OP_ACCOUNT=my.1password.com`.
- If `op` requires authentication, let the user unlock/sign in to 1Password from their normal terminal; do not ask them to paste secrets into chat, and do not keep retrying AI-side permission prompts after the readiness probe still fails.
- If `opmaterialize` exits `127` or the wrapper is not found, use the bundled script with `OP_ACCOUNT=my.1password.com` and `OP_DOTFILES_MATERIALIZE_VAULT="Dotfiles Secrets"`.
- If `Dotfiles Secrets` or `Secrets Manifest` is missing, create or ask the user to create it in 1Password rather than storing its content in git.
- If `op document get` reports `<id> is not a document`, the item is a Secure Note, not a Document. The manifest and field-based files use Secure Notes; rely on `opmaterialize` (which reads `notesPlain` and `type=field` rows), not a bare `op document get`.
- If `opmaterialize add` fails after multiple positional paths, retry as separate one-file `add` invocations.
- If a requested generated path is not ignored, update `.chezmoiignore` before registering the file.
- If changing the managed script, README, ADR, `.chezmoiignore`, or deployed dotfiles, follow the repository `dotfile-update` workflow.
- If changing this skill, follow `skill-creator` and run `scripts/skill-quick-validate`.

## Validation For Script Or Policy Changes

After editing the workflow implementation or docs, run:

```bash
shellcheck skills/onepassword-secret-materialize/scripts/opmaterialize dot_local/bin/executable_opmaterialize dot_local/bin/executable_oprun
git diff --check -- . ':(exclude).context'
scripts/chezmoi-drift --check-ignore
scripts/skill-quick-validate skills/onepassword-secret-materialize
```

For behavior changes, use a fake `op` in `.context/` to test `diff`, `restore`, and `add` without touching live 1Password.
