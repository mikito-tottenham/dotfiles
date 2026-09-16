---
name: ghq-repo-placement
description: "Resolve where to clone, pull, inspect, or open an external Git/GitHub/GitLab repository. Use for any repository URL, `git clone` request, or repository placement question; place checkouts under `ghq root` instead of ad hoc paths unless the user explicitly needs a project-local vendor, submodule, fixture, or temporary checkout."
---

# Ghq Repo Placement

Use `ghq` as the default local placement authority for project-independent repositories.
Do not clone external repositories into the current working repo just because that is where the request started.

## Decision Rules

1. If the user provides a Git URL or asks to clone/pull/open an external repo, resolve it through `ghq`.
2. If the repo is meant to be vendored, added as a submodule, used as a test fixture, or checked out under a specific project path, follow that explicit project-local intent instead.
3. The only placement root is the path returned by `ghq root`. Run it before cloning; when the environment sets `GHQ_ROOT` (this environment does, in `~/.zshenv.local`), `ghq root` must return that path, and a shell that returns something else must be corrected with an explicit `GHQ_ROOT=...` before `ghq get`. Use `ghq get` as the clone/update command.
4. If `ghq` is missing but Homebrew is available, install `ghq` from the repo's `Brewfile` path or with `brew install ghq` before cloning.
5. If `ghq` cannot be used or `ghq root` cannot be made to return the expected path, stop and ask the user. Do not invent an alternative placement path.

## Commands

Inspect placement:

```bash
command -v ghq
ghq root
ghq list -p | rg '<owner>/<repo>$|<repo>$'
```

Clone or update:

```bash
ghq get <repository-url-or-host-path>
ghq get -u <repository-url-or-host-path>
```

Open the resolved repo:

```bash
repo_path="$(ghq list -p | rg '/<owner>/<repo>$' | sed -n '1p')"
cd "$repo_path"
```

For GitHub repositories, `ghq get owner/repo` is acceptable when the host is clearly GitHub.
Use the full URL when the host, protocol, or account is ambiguous.

## Output Contract

When acting on a repo URL, report:

- `repo`: normalized URL or host path
- `placement`: the `ghq root` path used
- `path`: resolved local checkout path
- `action`: cloned, updated, already present, or blocked
- `reason`: only when blocked

Keep clone placement stable across turns and machines. Environment-specific follow-ups (for example adding a symlink into a `repos/` directory) belong to that environment's own instruction file, not to this skill.
