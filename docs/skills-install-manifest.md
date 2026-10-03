---
title: "Skill Install Manifest"
updated_at: 2026-10-03
---

# Skill Install Manifest

新しいマシンで配布 skill を復元するときは、この一覧を正本として `gh skill install` を実行する。

> **install は必ず `chezmoi source-path` が返す root で実行すること。** 各行の `.` はその root（この環境では ghq 配下の dotfiles checkout）を指す。`~/.local/share/chezmoi` など別 clone や worktree から実行すると、配備コピーの `metadata.local-path` が編集中の正本と別の checkout を指す stale install になる（2026-09-15 に 43 件検出）。実行前に `cd "$(chezmoi source-path)"` し、配備後は `skill-manager` の `doctor`（`source_drift` カテゴリ）で `SOURCE_PATH_STALE` が無いことを確認する。

当面は script を作らず、docs-only の install manifest として維持する。
将来 `gh` 側に manifest 機能が入ったら、そちらへ移行を検討する。

Claude Code on the web の ephemeral 環境に限り、`scripts/bootstrap-web`（SessionStart hook 経由）が **web で復元可能なサブセット**を自動再インストールする（ADR-0045）。サブセットは「first-party 全部（必須）＋ 公開 third-party のうち取得できたもの（best-effort）」で、manifest 全体とは一致しない。first-party の欠落は bootstrap を失敗させ、third-party の取得失敗は skip して継続する。2026-09-23 時点の third-party 取得対象は `natural-japanese` と `japanese-business-writing`（いずれも commit SHA で pin）。スキルを追加・削除したときは、この manifest と `scripts/bootstrap-web` のリストを同期すること。

## クラウドで再現する CLI と MCP

クラウドでは skill のほかに CLI と MCP も `scripts/bootstrap-web` が再現する。MCP の正本は `bootstrap-web` の `mcp_servers` 配列、CLI の正本は `bootstrap-web` の導入処理で、`scripts/verify-cloud-parity` の `CLI_*` を同期させる。増減したときは、この節も合わせて更新する。

- CLI（`bootstrap-web` が導入）: `jq` `rg` `codex` `gemini` `ghq` `gh` `gws` `copilot` `op`
- CLI（chezmoi が `dot_local/bin` から配置。`verify-cloud-parity` は有無だけを見る）: `opmaterialize` `oprun` `ghrun` `gws-account` `slack-account` `slack-fetch-message` `calendar-acl`
- MCP（`claude mcp add --scope user`）: `mfc_ca`（http）、`chatwork`（stdio。`oprun` 経由で起動し、token は `dotfiles.env` の `op://` 参照から解決する。ADR-0062 決定 8）
- 対象外: `pencil`（ローカルアプリ依存）。claude.ai コネクタはクラウドホストがセッションへ渡すため、script で再現する必要が無い
- これらが通信するホストの allowlist は `docs/web-session-runner-setup.md` の Network access 節に列挙する（ADR-0068）

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
gh skill install . agent-env-parity --from-local --agent claude-code --scope user
gh skill install . meeting-minutes-ingest --from-local --agent claude-code --scope user
gh skill install . doc-grill --from-local --agent claude-code --scope user
gh skill install . deliverable-closeout --from-local --agent claude-code --scope user
gh skill install . client-proposal-pack --from-local --agent claude-code --scope user
gh skill install . meeting-prep-brief --from-local --agent claude-code --scope user
gh skill install . auth-preflight --from-local --agent claude-code --scope user
gh skill install . contract-review --from-local --agent claude-code --scope user
gh skill install . pdf-extract --from-local --agent claude-code --scope user
gh skill install . expense-to-ledger --from-local --agent claude-code --scope user
gh skill install . multi-account-scheduling --from-local --agent claude-code --scope user
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
gh skill install . agent-env-parity --from-local --agent codex --scope user
gh skill install . meeting-minutes-ingest --from-local --agent codex --scope user
gh skill install . doc-grill --from-local --agent codex --scope user
gh skill install . deliverable-closeout --from-local --agent codex --scope user
gh skill install . client-proposal-pack --from-local --agent codex --scope user
gh skill install . meeting-prep-brief --from-local --agent codex --scope user
gh skill install . auth-preflight --from-local --agent codex --scope user
gh skill install . contract-review --from-local --agent codex --scope user
gh skill install . pdf-extract --from-local --agent codex --scope user
gh skill install . expense-to-ledger --from-local --agent codex --scope user
gh skill install . multi-account-scheduling --from-local --agent codex --scope user
```

### 変更履歴（first-party）

- 2026-09-15: `opus-4-8-tuning` と `gpt-5-5-tuning` を `model-tuning` 1 本に統合（旧世代の差分は `skills/model-tuning/references/legacy-*.md`）。`opus-4-7-tuning` は ADR-0053 で退役済みのため repo からも削除。`external-report` を登録。
- 2026-10-03: 2026-10 の Skill 棚卸し（ADR-0069）に基づき 11 本を登録した。`agent-env-parity`（WP1）、`meeting-minutes-ingest` / `doc-grill`（WP2）、`deliverable-closeout`（WP3）、`client-proposal-pack` / `meeting-prep-brief` / `auth-preflight`（WP4）、`contract-review` / `pdf-extract` / `expense-to-ledger` / `multi-account-scheduling`（WP5）。既存では `git-branch-review` に Fleet Mode（`scripts/fleet_*.py`、`references/fleet-cleanup.md`）を追加し、`skill-manager` の `doctor` に `retired_skills` / `first_party_sync` を追加した
- 2026-10-03: ADR-0062 で撤去済みの 6 skill（`gws-drive` / `gws-drive-upload` / `gws-shared` / `grill-me` / `opus-4-8-tuning` / `gpt-5-5-tuning`）が `~/.claude/skills` / `~/.agents/skills` / `~/.codex/skills` に残っていたため、削除せず `~/.local/share/skill-retired/2026-10-03/` へ退避した（18 件。`~/.agents/.skill-lock.json` の該当 4 エントリも、backup を取ってから外した）。続けて `~/.codex/skills` を上記 Codex 節の手順（install → rsync）で再同期した
- 2026-10-03: `pdf-extract` の script は兄弟 skill `codex-cli-runner` を呼ぶが、Codex の一覧には `codex-cli-runner` を入れていない。Codex 親では script を使わず自分で抽出する（SKILL.md の「Codex 親の場合」節。model_registry の Self-Elision）

## Third-party external skills

third-party external skill はここへ追加で列挙する。有効な skill は先頭に、撤去済み skill は撤去記録と再導入条件として後ろに残す。撤去済み skill がまだ `~/.claude/skills` / `~/.codex/skills` に残っている場合は `gh skill remove <name> --agent <agent> --scope user` で外すか、`~/.local/share/skill-retired/<date>/` へ退避（移動）する。

### `natural-japanese`

- upstream: [coji/natural-japanese `skills/natural-japanese`](https://github.com/coji/natural-japanese/tree/main/skills/natural-japanese)（MIT）
- pin: `9a78a42964096da509b8f3e011f0085a5f080151`（main HEAD, 2026-09-04。v1.5.0 以降の「読者層の特定」step を含む）
- status: 有効（2026-09-23 導入、ADR-0066）。Claude Code / Codex の user scope
- reason: 対外文書（提案書・報告書・スライド）の構成・読みやすさ・AI 臭と翻訳調の除去。国内の公開 skill で設計の質が最も高く、書き換えすぎと捏造の歯止めを持つ
- 注意:
  - メールの型と敬語は扱わない。そこは `japanese-business-writing` が担う
  - lint 系 scripts は `uv run`（PEP 723、`sudachipy` を初回に PyPI から取得）が前提。`uv` の無い環境では skill の規定どおり `references/manual-checklist.md` で代替される
  - `scripts/semantic.py` は `sentence-transformers` / `torch` と約 1GB のモデル取得、`trust_remote_code=True` を伴う。opt-in のため既定では動かないが、実行させないこと
  - 中間ファイルを scratchpad / `mktemp -d` に置いて完了時に削除する指示は、共通ルール（`.context/` 利用・artifact 保持）が下限として優先される

### `japanese-business-writing`

- upstream: [RobTar97/japanese-writing-skills `skills/japanese-business-writing`](https://github.com/RobTar97/japanese-writing-skills/tree/main/skills/japanese-business-writing)（MIT）
- pin: `e4b1700464219c60da786f005a061bccffbbd4e3`（main HEAD, 2026-08-06）
- status: 有効（2026-09-23 導入、ADR-0066）。Claude Code / Codex の user scope
- reason: 社外メール・チャットの作法、敬語（尊敬語・謙譲語Ⅰ/Ⅱ・丁寧語）と内/外の切り替え、丁寧さの 3 段階、事実・約束を捏造しない truth ledger。`natural-japanese` が扱わない対外連絡を補う
- 注意: ★0 の新しい repo のため、pin 更新時は SKILL.md と `references/` を全文レビューしてから上げる。同 repo の `natural-japanese-writing` / `japanese-product-localization` は重複・用途外のため入れない

#### Claude Code / Codex install（`natural-japanese` / `japanese-business-writing` 共通）

```bash
gh skill install coji/natural-japanese skills/natural-japanese --pin 9a78a42964096da509b8f3e011f0085a5f080151 --agent claude-code --scope user
gh skill install coji/natural-japanese skills/natural-japanese --pin 9a78a42964096da509b8f3e011f0085a5f080151 --agent codex --scope user
gh skill install RobTar97/japanese-writing-skills skills/japanese-business-writing --pin e4b1700464219c60da786f005a061bccffbbd4e3 --agent claude-code --scope user
gh skill install RobTar97/japanese-writing-skills skills/japanese-business-writing --pin e4b1700464219c60da786f005a061bccffbbd4e3 --agent codex --scope user
rsync -a --delete ~/.agents/skills/natural-japanese/ ~/.codex/skills/natural-japanese/
rsync -a --delete ~/.agents/skills/japanese-business-writing/ ~/.codex/skills/japanese-business-writing/
```

pin を上げるときは、この節と `scripts/bootstrap-web` の `install_third_party()` を同時に更新する。skill を追加・削除するときは `scripts/verify-cloud-parity` の `THIRD_PARTY_SKILLS` も更新する。

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
