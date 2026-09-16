---
name: chezmoi-knowledge
description: Explain this repository's chezmoi source/target mapping, source attributes, ignore rules, and symlink semantics. Use when one of those semantics affects a decision; use `dotfile-update` for the edit and apply workflow.
---

# Chezmoi Knowledge

Use this skill to resolve repo-specific chezmoi semantics. It does not own the edit or apply procedure.

## Canonical Reference

Read [references/semantics.md](references/semantics.md) only when source/target mapping, attributes, ignore behavior, or symlink handling matters. Treat it as canonical.

## Essential Boundary

- Decide whether the path is managed source or a repo-local helper before treating it as deployable.
- `.chezmoiignore` matches target paths.
- `private_` is a permission attribute; `symlink_` represents a target symlink.
- `chezmoi add --follow` imports the referent as a regular file.

If a task changes dotfiles, establish any needed semantics here, then follow `dotfile-update` for execution.
