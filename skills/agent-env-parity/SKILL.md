---
name: agent-env-parity
description: "Single entry point for checking drift between the dotfiles source and the agent environments: local Claude Code / Codex config, deployed skills (~/.claude/skills, ~/.agents/skills, ~/.codex/skills), and cloud sessions. Routes to the existing checks (skill-manager doctor, scripts/chezmoi-drift, scripts/verify-cloud-parity) and reports gaps without changing state. Use when asked to 環境のずれを確認, Skill の配備を確認, Codex とのずれを確認, クラウド環境の再現確認, 撤去した Skill が残っていないか, or 環境パリティを確認."
---

# Agent Env Parity

dotfiles の正本と、各エージェント環境の実体がずれていないかを確かめる入口。検査そのものは既存の script が持つ。この skill は「どの検査を、どの順で、どこで動かすか」と結果のまとめ方だけを決める。検査ロジックをここに再実装しない。

## 前提

- 正本は `chezmoi source-path` が返す dotfiles checkout。クラウド環境は origin の既定ブランチを clone するため、ローカルの未 push 変更はクラウドに存在しない。
- 本 skill の手順はすべて読み取り専用。削除・退避・再インストール・`chezmoi apply` などの是正は、結果を示してユーザーの承認を得てから、各担当の手順（下表の「是正の担当」）で行う。
- Agent tool の `isolation: "remote"` などで作った worktree はクラウド環境ではない。クラウド側の結果は、実際のクラウドセッション内で取ったものだけをクラウドの実測として扱う。

## 検査の振り分け

| 観点 | 検査 | 実行場所 | 是正の担当 |
|---|---|---|---|
| 正本 checkout と origin の差 | `git -C "$(chezmoi source-path)" fetch origin` の後 `git -C "$(chezmoi source-path)" rev-list --left-right --count HEAD...origin/HEAD` と `git status --short` | ローカル | ユーザー判断（pull / push はユーザー承認） |
| Skill の配備（撤去済みの残存、正本との内容差、`~/.codex/skills` の同期漏れ） | skill-manager の `doctor`（`retired_skills` / `first_party_sync` / `source_drift`） | ローカル | skill-manager（`references/commands.md` の `doctor` 節の是正手順） |
| ローカル dotfiles（Claude / Codex 設定など）と実ファイルの差 | `scripts/chezmoi-drift`（引数なし）と `scripts/chezmoi-drift --check-ignore` | ローカル | dotfile-update skill。`--apply` / `--restore` は状態変更なので承認後のみ |
| クラウド環境の再現（skill / CLI / MCP / secret の有無） | `scripts/verify-cloud-parity --json` | クラウドセッション内（ローカルではクラウド専用項目が `N/A` になる） | `scripts/bootstrap-web` と `docs/skills-install-manifest.md` の同期（dotfiles の AGENTS.md「スキル管理」） |

依頼が 1 観点だけなら、その行だけを実行する。「全体を確認」なら上から順に実行する。

## 手順

1. 対象観点を決め、`.context/<task>/` を作る（task 名の指定がなければ `agent-env-parity-<YYYY-MM-DD>`）。
2. 正本 checkout の位置と origin との差を記録する。ahead / behind がある場合、以降の「正本との差」は手元の checkout との比較であり、origin とは一致しないことを結果に明記する。
3. Skill 配備を検査する。skill-manager の配備先（`~/.claude/skills/skill-manager` など）または publisher source の `skills/skill-manager` で次を実行し、JSON を artifact に保存する。

   ```bash
   bash <skill-manager-dir>/scripts/executable_doctor.sh > .context/<task>/doctor.json 2> .context/<task>/doctor.log
   ```

   `retired_skills`・`first_party_sync`・`source_drift` の非 pass 項目を抜き出す。ほかのカテゴリ（plugin など）は観点外として件数だけ残す。
4. ローカル dotfiles の差を検査する。dotfiles checkout の root で `scripts/chezmoi-drift` と `scripts/chezmoi-drift --check-ignore` を実行し、出力を保存する。オプションなしの実行は一覧表示のみで、取り込みや復元はしない。
5. クラウド環境を検査する。クラウドセッション内なら `scripts/verify-cloud-parity --json` を実行して保存する。ローカルで実行した場合は、ローカル側の前提（CLI・chezmoi 配置）の確認としてだけ扱い、クラウドの再現結果とは書かない。
6. 結果を 1 つの表にまとめる。

## 出力

`.context/<task>/parity-report.md`（Front Matter に `task` / `phase_or_step` / `created_at`）に次を書く。

- 観点ごとの判定（`OK` / `ずれあり` / `未検査` と理由）
- ずれの一覧: 観点、対象（skill 名・ファイル・CLI 名）、検査コード（例 `RETIRED_STILL_DEPLOYED`、`CODEX_MIRROR_STALE`、`MISSING`）、是正の担当
- 是正案。実行はしない。承認が要る操作（削除・退避・再インストール・`chezmoi apply`・push）を明示する
- 各検査の raw 出力の path

secret の実値は出力しない。`verify-cloud-parity` は secret の有無だけを出す設計なので、その出力をそのまま貼ってよい。

## しないこと

- 検査 script の再実装や、別の比較 script の新規作成（検査が足りなければ、担当 script の改修として提案する）
- 承認なしの是正操作
- クラウドの状態をローカルの実行結果から推測して書くこと
