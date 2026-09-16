---
title: "Skill Install Manifest"
updated_at: 2026-09-15
---

# Skill Install Manifest

新しいマシンで配布 skill を復元するときは、この一覧を正本として `gh skill install` を実行する。

> **install は必ず `chezmoi source-path` が返す root で実行すること。** 各行の `.` はその root（この環境では ghq 配下の dotfiles checkout）を指す。`~/.local/share/chezmoi` など別 clone や worktree から実行すると、配備コピーの `metadata.local-path` が編集中の正本と別の checkout を指す stale install になる（2026-09-15 に 43 件検出）。実行前に `cd "$(chezmoi source-path)"` し、配備後は `skill-manager` の `doctor`（`source_drift` カテゴリ）で `SOURCE_PATH_STALE` が無いことを確認する。

当面は script を作らず、docs-only の install manifest として維持する。
将来 `gh` 側に manifest 機能が入ったら、そちらへ移行を検討する。

Claude Code on the web の ephemeral 環境に限り、`scripts/bootstrap-web`（SessionStart hook 経由）が **web で復元可能なサブセット**を自動再インストールする（ADR-0045）。サブセットは「first-party 全部（必須）＋ 公開 third-party のうち取得できたもの（best-effort）」で、manifest 全体とは一致しない。first-party の欠落は bootstrap を失敗させ、third-party の取得失敗は skip して継続する。2026-09-15 時点で third-party は全て撤去済みのため、bootstrap-web の取得対象は first-party のみ。スキルを追加・削除したときは、この manifest と `scripts/bootstrap-web` のリストを同期すること。

## First-party publisher skills

`chezmoi source-path` の root を install source にして実行する。

### Claude Code

```bash
cd "$(chezmoi source-path)"
gh skill install . skill-manager --from-local --agent claude-code --scope user
gh skill install . docs-entrypoint-check --from-local --agent claude-code --scope user
gh skill install . docs-evaluator --from-local --agent claude-code --scope user
gh skill install . grok-cli-runner --from-local --agent claude-code --scope user
gh skill install . code-evaluator --from-local --agent claude-code --scope user
gh skill install . model-tuning --from-local --agent claude-code --scope user
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
gh skill install . dads-design --from-local --agent claude-code --scope user
gh skill install . gws-cli-runner --from-local --agent claude-code --scope user
gh skill install . agent-orchestrator --from-local --agent claude-code --scope user
gh skill install . external-report --from-local --agent claude-code --scope user
```

### Codex

> `gh skill install --agent codex` は `~/.agents/skills/`（universal 先）に書き、`~/.codex/skills/` には書かない（2026-09-15 実測、gh skill preview）。Codex は両方を読むため、install 後に `~/.codex/skills/<skill>/` を `rsync -a --delete ~/.agents/skills/<skill>/ ~/.codex/skills/<skill>/` で同期し、二重化と stale を防ぐこと。


```bash
cd "$(chezmoi source-path)"
gh skill install . skill-manager --from-local --agent codex --scope user
gh skill install . docs-entrypoint-check --from-local --agent codex --scope user
gh skill install . docs-evaluator --from-local --agent codex --scope user
gh skill install . grok-cli-runner --from-local --agent codex --scope user
gh skill install . code-evaluator --from-local --agent codex --scope user
gh skill install . model-tuning --from-local --agent codex --scope user
gh skill install . claude-cli-runner --from-local --agent codex --scope user
gh skill install . gemini-cli-runner --from-local --agent codex --scope user
gh skill install . copilot-cli-runner --from-local --agent codex --scope user
gh skill install . agent-orchestration-evaluator --from-local --agent codex --scope user
gh skill install . ai-usage-coach --from-local --agent codex --scope user
gh skill install . soundcore-minutes --from-local --agent codex --scope user
gh skill install . ghq-repo-placement --from-local --agent codex --scope user
gh skill install . op-cli-runner --from-local --agent codex --scope user
gh skill install . onepassword-secret-materialize --from-local --agent codex --scope user
gh skill install . handoff --from-local --agent codex --scope user
gh skill install . git-branch-review --from-local --agent codex --scope user
gh skill install . dads-design --from-local --agent codex --scope user
gh skill install . gws-cli-runner --from-local --agent codex --scope user
gh skill install . agent-orchestrator --from-local --agent codex --scope user
gh skill install . external-report --from-local --agent codex --scope user
```

### 変更履歴（first-party）

- 2026-09-15: `opus-4-8-tuning` と `gpt-5-5-tuning` を `model-tuning` 1 本に統合（旧世代の差分は `skills/model-tuning/references/legacy-*.md`）。`opus-4-7-tuning` は ADR-0053 で退役済みのため repo からも削除。`external-report` を登録。

## Third-party external skills

third-party external skill はここへ追加で列挙する。2026-09-15 時点では有効な third-party skill は無く、以下は撤去記録と再導入条件として残す。撤去済み skill がまだ `~/.claude/skills` / `~/.codex/skills` に残っている場合は `gh skill remove <name> --agent <agent> --scope user` で外す。

### `gws-*`（撤去済み）

- upstream: [googleworkspace/cli `skills/`](https://github.com/googleworkspace/cli/tree/main/skills)
- status: **撤去済み（2026-09-15）**。`gws-shared` / `gws-drive` / `gws-drive-upload` は first-party の `gws-cli-runner` に吸収した
- reason: upstream 本文が素の `gws auth login` を案内しており、この環境の「gws は常に `gws-account <profile>` 経由」ルール（ADR-0048）と衝突する。認証・アカウント境界を持つ `gws-cli-runner` を唯一の入口にする
- prerequisite（継続）: `googleworkspace-cli` 自体は `gws-cli-runner` が使うため引き続き必要。macOS は `Brewfile`、web セッションは `scripts/bootstrap-web` が GitHub release（`v0.22.5`, gnu build）から導入する
- 再導入条件: upstream skill が `gws-account` 相当のプロファイル指定を前提にするか、`gws-cli-runner` が upstream の per-service 手順を wrap しきれなくなった場合に再検討する。再導入時は pin を `googleworkspace-cli` のバージョンに揃える

### `empirical-prompt-tuning`

- upstream: [mizchi/chezmoi-dotfiles `dot_claude/skills/empirical-prompt-tuning/SKILL.md`](https://github.com/mizchi/chezmoi-dotfiles/blob/main/dot_claude%2Fskills%2Fempirical-prompt-tuning%2FSKILL.md)
- status: **unavailable (upstream removed)**。2026-06-19 時点で upstream raw URL が HTTP 404 を返し、`mizchi/chezmoi-dotfiles` main から削除されている。
- 復元可否: 現在は復元不可。`scripts/bootstrap-web`（web サブセット）の対象外であり、グローバルにもインストールされていない前提で扱う。
- install mode: fetch upstream `SKILL.md`, stage it locally, then install with `gh skill --from-local`
- reason: upstream repo is not a publisher-layout repo, so direct `gh skill install OWNER/REPO skill` is unavailable
- update note: upstream が復活したら下記 refresh 手順で再導入し、status を戻すこと。それまで refresh 手順は失敗する。

#### Claude Code / Codex refresh

`chezmoi source-path` の root で実行する。

```bash
mkdir -p .context/skill-bootstrap/empirical-prompt-tuning/skills/empirical-prompt-tuning
curl -L --fail --silent --show-error \
  'https://raw.githubusercontent.com/mizchi/chezmoi-dotfiles/main/dot_claude/skills/empirical-prompt-tuning/SKILL.md' \
  -o .context/skill-bootstrap/empirical-prompt-tuning/skills/empirical-prompt-tuning/SKILL.md
gh skill install ./.context/skill-bootstrap/empirical-prompt-tuning empirical-prompt-tuning --from-local --agent claude-code --scope user --force
gh skill install ./.context/skill-bootstrap/empirical-prompt-tuning empirical-prompt-tuning --from-local --agent codex --scope user --force
```

### `grill-me`（撤去済み）

- upstream: [mattpocock/skills `skills/productivity/grill-me`](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me)
- status: **撤去済み（2026-09-15）**。Claude Code は built-in `anthropic-skills:grill-me` で代替し、Codex は代替なし
- reason: upstream 本文が `/grilling` 参照のみの stub で、単体では機能しない。Claude 側は同名 built-in と `/grill-me` の解決が曖昧になり、Codex 側は壊れた stub に当たる
- 再導入条件: upstream が `grilling` 本体を同梱するか、Codex 側で複数解釈の確認フローが必要になった場合に、`gh skill preview mattpocock/skills grill-me` で本文を確認してから判断する
