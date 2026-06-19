---
title: "Skill Install Manifest"
updated_at: 2026-06-16
---

# Skill Install Manifest

新しいマシンで配布 skill を復元するときは、この一覧を正本として `gh skill install` を実行する。

当面は script を作らず、docs-only の install manifest として維持する。
将来 `gh` 側に manifest 機能が入ったら、そちらへ移行を検討する。

Claude Code on the web の ephemeral 環境に限り、`scripts/bootstrap-web`（SessionStart hook 経由）が **web で復元可能なサブセット**を自動再インストールする（ADR-0045）。サブセットは「first-party 全部（必須）＋ 公開 third-party のうち取得できたもの（best-effort）」で、manifest 全体とは一致しない。first-party の欠落は bootstrap を失敗させ、third-party の取得失敗は skip して継続する。upstream 不在の skill（下記 `empirical-prompt-tuning`）は対象外。スキルを追加・削除したときは、この manifest と `scripts/bootstrap-web` のリストを同期すること。

## First-party publisher skills

repo root を install source にして実行する。

### Claude Code

```bash
gh skill install . skill-manager --from-local --agent claude-code --scope user
gh skill install . docs-entrypoint-check --from-local --agent claude-code --scope user
gh skill install . docs-evaluator --from-local --agent claude-code --scope user
gh skill install . grok-cli-runner --from-local --agent claude-code --scope user
gh skill install . code-evaluator --from-local --agent claude-code --scope user
gh skill install . opus-4-7-tuning --from-local --agent claude-code --scope user
gh skill install . opus-4-8-tuning --from-local --agent claude-code --scope user
gh skill install . gpt-5-5-tuning --from-local --agent claude-code --scope user
gh skill install . codex-cli-runner --from-local --agent claude-code --scope user
gh skill install . gemini-cli-runner --from-local --agent claude-code --scope user
gh skill install . copilot-cli-runner --from-local --agent claude-code --scope user
gh skill install . agent-orchestration-evaluator --from-local --agent claude-code --scope user
gh skill install . ai-usage-coach --from-local --agent claude-code --scope user
gh skill install . soundcore-minutes --from-local --agent claude-code --scope user
gh skill install . ghq-repo-placement --from-local --agent claude-code --scope user
gh skill install . op-cli-runner --from-local --agent claude-code --scope user
gh skill install . onepassword-secret-materialize --from-local --agent claude-code --scope user
gh skill install . handoff --from-local --agent claude-code --scope user
gh skill install . git-branch-review --from-local --agent claude-code --scope user
```

### Codex

```bash
gh skill install . skill-manager --from-local --agent codex --scope user
gh skill install . docs-entrypoint-check --from-local --agent codex --scope user
gh skill install . docs-evaluator --from-local --agent codex --scope user
gh skill install . grok-cli-runner --from-local --agent codex --scope user
gh skill install . code-evaluator --from-local --agent codex --scope user
gh skill install . opus-4-7-tuning --from-local --agent codex --scope user
gh skill install . opus-4-8-tuning --from-local --agent codex --scope user
gh skill install . gpt-5-5-tuning --from-local --agent codex --scope user
gh skill install . claude-cli-runner --from-local --agent codex --scope user
gh skill install . gemini-cli-runner --from-local --agent codex --scope user
gh skill install . copilot-cli-runner --from-local --agent codex --scope user
gh skill install . ai-usage-coach --from-local --agent codex --scope user
gh skill install . soundcore-minutes --from-local --agent codex --scope user
gh skill install . ghq-repo-placement --from-local --agent codex --scope user
gh skill install . op-cli-runner --from-local --agent codex --scope user
gh skill install . onepassword-secret-materialize --from-local --agent codex --scope user
gh skill install . handoff --from-local --agent codex --scope user
gh skill install . git-branch-review --from-local --agent codex --scope user
```

## Third-party external skills

third-party external skill はここへ追加で列挙する。

### `gws-*`

- upstream: [googleworkspace/cli `skills/`](https://github.com/googleworkspace/cli/tree/main/skills)
- status: installed globally for Claude Code and Codex
- install mode: direct `gh skill install` from upstream GitHub repository
- pin: `v0.22.5`
- reason: upstream provides official per-service gws skills; keep them external and do not vendor them into this repo
- scope: install only `gws-shared`, `gws-drive`, and `gws-drive-upload`
- prerequisite: `googleworkspace-cli` must be installed; managed by `Brewfile` on macOS, and installed from the GitHub release (`v0.22.5`, gnu build) by `scripts/bootstrap-web` in web sessions
- update note: keep the skill pin aligned with the installed `googleworkspace-cli` version

#### Claude Code / Codex refresh

repo root で実行する。

```bash
skills=(
  gws-drive
  gws-drive-upload
  gws-shared
)

for agent in claude-code codex; do
  for skill in "${skills[@]}"; do
    gh skill install googleworkspace/cli "$skill" --pin v0.22.5 --agent "$agent" --scope user --force
  done
done
```

### `empirical-prompt-tuning`

- upstream: [mizchi/chezmoi-dotfiles `dot_claude/skills/empirical-prompt-tuning/SKILL.md`](https://github.com/mizchi/chezmoi-dotfiles/blob/main/dot_claude%2Fskills%2Fempirical-prompt-tuning%2FSKILL.md)
- status: **unavailable (upstream removed)**。2026-06-19 時点で upstream raw URL が HTTP 404 を返し、`mizchi/chezmoi-dotfiles` main から削除されている。
- 復元可否: 現在は復元不可。`scripts/bootstrap-web`（web サブセット）の対象外であり、グローバルにもインストールされていない前提で扱う。
- install mode: fetch upstream `SKILL.md`, stage it locally, then install with `gh skill --from-local`
- reason: upstream repo is not a publisher-layout repo, so direct `gh skill install OWNER/REPO skill` is unavailable
- update note: upstream が復活したら下記 refresh 手順で再導入し、status を戻すこと。それまで refresh 手順は失敗する。

#### Claude Code / Codex refresh

repo root で実行する。

```bash
mkdir -p .context/skill-bootstrap/empirical-prompt-tuning/skills/empirical-prompt-tuning
curl -L --fail --silent --show-error \
  'https://raw.githubusercontent.com/mizchi/chezmoi-dotfiles/main/dot_claude/skills/empirical-prompt-tuning/SKILL.md' \
  -o .context/skill-bootstrap/empirical-prompt-tuning/skills/empirical-prompt-tuning/SKILL.md
gh skill install ./.context/skill-bootstrap/empirical-prompt-tuning empirical-prompt-tuning --from-local --agent claude-code --scope user --force
gh skill install ./.context/skill-bootstrap/empirical-prompt-tuning empirical-prompt-tuning --from-local --agent codex --scope user --force
```

### `grill-me`

- upstream: [mattpocock/skills `skills/productivity/grill-me`](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me)
- status: installed globally for Claude Code and Codex
- install mode: direct `gh skill install` from upstream GitHub repository
- reason: upstream is publisher-discoverable on GitHub, so direct external install is the standard path
- update note: inspect changes with `gh skill preview mattpocock/skills grill-me` before running `gh skill update grill-me`

#### Claude Code / Codex install

repo root で実行する。

```bash
gh skill install mattpocock/skills grill-me --agent claude-code --scope user
gh skill install mattpocock/skills grill-me --agent codex --scope user
```
