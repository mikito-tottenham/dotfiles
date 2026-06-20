---
title: "0046 Switch opmaterialize Storage to Secure Note Field for Service Account Compatibility"
date: 2026-06-20
status: accepted
agent: claude-sonnet-4-6
---

# 0046 Switch opmaterialize Storage to Secure Note Field for Service Account Compatibility

## Context

ADR 0045 established that the Claude Code web session bootstrap uses `OP_SERVICE_ACCOUNT_TOKEN` to run `opmaterialize restore` at session start, restoring secret files (Google service account JSON, dotenv files) from 1Password.

However, after implementation, `opmaterialize restore` failed with **403 Forbidden** on every execution:

```
[ERROR] 2026/06/20 ...
[ERROR] could not retrieve item: the request failed: 403
```

Investigation revealed the root cause: **1Password personal plan service accounts cannot access Document file attachments** regardless of `read_items` / `write_items` permissions. The `op document get` command, used by both manifest download and content file download, returns 403 for service accounts on personal plans. This is a 1Password platform-level restriction, not a service account configuration issue.

Additionally, service accounts on personal plans cannot create or edit items (`op item create`, `op item edit` both return error 101), so the entire `opmaterialize add` workflow also fails.

## Decision

Switch `opmaterialize` storage from **1Password Document items** to **Secure Note items with a `content` text field**. The manifest is stored as the Secure Note's `notesPlain` field.

**Why Secure Note fields work:**
`op read "op://vault/item/field"` reads field values via the items API, which service accounts can access with `read_items` permission. Document attachments use a separate binary assets API that personal plan service accounts cannot reach.

### Changes to `opmaterialize`

**Manifest storage:** Stored as `notesPlain` of a Secure Note item.
- `download_manifest`: tries `op read op://vault/item/notesPlain` first; falls back to `op document get` for personal account environments (backward compatible).
- `upload_manifest`: uses `op item edit ... "notesPlain=..."` or `op item create --category "Secure Note" ...`.

**Content file storage:** Stored as `content[text]` field of a Secure Note item.
- Manifest row type changes from `document` to `field`.
- `process_manifest` dispatches on `kind`: `field` → `op read op://vault/item/content`, `document` → `op document get` (legacy, still supported for read).

**`add` command:** Creates/updates Secure Note with `content[text]` field instead of Document.

### Manifest format (new)

```tsv
# type	item	out_path	mode	vault
field	dotfiles:$HOME/.config/gws/accounts/ges-claude.json	$HOME/.config/gws/accounts/ges-claude.json	0600	Dotfiles Secrets
field	dotfiles:$HOME/.config/op/dotfiles.env	$HOME/.config/op/dotfiles.env	0600	Dotfiles Secrets
```

### Migration (one-time, requires personal account auth)

A migration script at `.context/opmaterialize-field-migration/02-migrate-local.sh` performs the one-time conversion:

1. Download current Document manifest with `op document get` (personal auth).
2. For each `document` entry: download content, archive Document item, create Secure Note with `content[text]` field.
3. Archive the Document manifest item.
4. Create Secure Note manifest with `notesPlain`.
5. Verify with `op read op://vault/manifest/notesPlain`.

This script must be run locally (not from a remote container) because service accounts cannot create or delete items.

## Consequences

**Positive:**
- `opmaterialize restore` works with `OP_SERVICE_ACCOUNT_TOKEN` in remote Claude Code sessions.
- Service account needs only `read_items` permission (write operations stay local).
- Backward compatible: `download_manifest` falls back to `op document get` for personal account sessions.
- `document` type rows remain readable for any legacy items not yet migrated.

**Negative:**
- One-time migration required; must be run locally with personal 1Password auth.
- `opmaterialize add` still requires personal account auth (service accounts cannot write items on personal plan).
- Secure Note `content` field is a plain text field; no binary file support (acceptable for text config files).

## References

- ADR 0045: web session bootstrap with `OP_SERVICE_ACCOUNT_TOKEN`
- ADR 0036: 1Password as secret handoff mechanism
- Migration script: `.context/opmaterialize-field-migration/02-migrate-local.sh`
