---
title: "Skill Consolidation 2026-10: Reduce First-Party Skills to 21 and Trim the Harness"
date: 2026-10-23
worked_at: 2026-10-23 JST
agent_model: "Claude Fable 5.1 (claude-fable-5-1)"
status: proposed
related_adr: ["0012", "0016", "0045", "0055", "0057", "0062", "0063", "0065", "0068", "0069", "0070", "0071"]
---

# ADR 0072: 2026-10 の Skill 統合で first-party を 21 本に減らし、ハーネスを削る

## Context

2026-10-23 に、Claude Code transcript 1,840 件と Codex session 132 件を対象に first-party skill 33 本 + 未マージ 1 本
（`task-sweep`）の利用実績、Skill 間依存、グローバル規則、ハーネス（hooks / plugins / permissions）を棚卸しした
（作業 artifact: `~/Claude/.context/2026-10-23-skill-consolidation/00-inventory.md`、`10-plan.md`。
ADR-0069 の棚卸しから 3 週間後の再点検）。

1. **読まれない skill が固定費になっていた。** Skill tool の呼び出しが 0 回の skill が 11 本、1 回が 6 本あり、
   first-party 33 本の description 合計 13,831 文字（平均 419 文字）が毎セッションのコンテキストに載っていた。
   `agents-common.md` も 9,297 文字（20,970 bytes）で、日付付きの経緯説明と ADR に書いてある根拠を本文に抱えていた。
2. **同じ本文が複数 skill に重複していた。** `code-evaluator` / `docs-evaluator` / `docs-entrypoint-check` は
   Core Rules / Workflow / Mutation Guard が同文で、`auth-preflight` の症状表は共通ルールと gws Runbook の再掲、
   `multi-account-scheduling` の ACL 手順は `gws-cli-runner` と同文だった。`soundcore-minutes` と
   `meeting-minutes-ingest` は常に対で使われ、別 skill である必要が無かった。
3. **使わない runner が残っていた。** `gemini-cli-runner` / `copilot-cli-runner` は呼出 0 で、
   `agent-orchestrator` の model_registry は 2026-07-25 以降 Gemini を route に使っていない。
   fork 元（skills.sh 系）との同期は 2026-06-22 以降止まっており、fork 同期を理由に残す根拠も無い。
4. **ハーネスに動かない設定があった。** `dot_claude/settings.json` の SUPERSET notify hook（Stop / Notification /
   PostToolUse などの 5 event）は commit `aae0315`（2026-03-27「Add AI hooks and managed SSH config」）で ADR 無しに
   入ったもので、`SUPERSET_HOME_DIR` 未設定・`notify.sh` 不在のまま `PostToolUse` の `*` マッチで毎ツール呼び出しごとに
   shell を起動していた。`permissions.allow` の `Bash(gh pr merge *)` は素の `gh` を許し、ADR-0063 の `ghrun gh` 規則と
   矛盾していた。`codex@openai-codex` plugin はローカルの installPath が不在で利用 1 回だったが、ADR-0045 の
   2026-06-22 実測ではクラウドセッションの Codex 委譲が plugin proxy 経由で動くと記録されており、ADR-0068 でも
   その経路は未検証扱いのままである。
5. **未マージの skill が配備されていた。** `task-sweep`（ADR-0070）は worktree ブランチのまま配備され、
   会社固有値を直書きしていて公開 repo の規則（ADR-0069 決定 3）と衝突していた。

## Decision

1. **first-party を 33 本 + 1 本 → 21 本にする。** Claude Code / Codex の配備は各 20 本
   （差分は `codex-cli-runner` / `claude-cli-runner`。ADR-0069 決定 4 の Self-Elision を維持）。

   | 区分 | 元 | 先 |
   |---|---|---|
   | 統合 | `code-evaluator` + `docs-evaluator` + `docs-entrypoint-check` | `repo-evaluator`（`code:*` / `docs:*` モード、entrypoint-check / bootstrap モード） |
   | 統合 | `soundcore-minutes` + `meeting-minutes-ingest` | `meeting-minutes`（取得手順は `references/soundcore-retrieval.md`） |
   | 吸収 | `auth-preflight` | `op-cli-runner`（`references/preflight.md`、`scripts/auth_preflight.py`） |
   | 吸収 | `multi-account-scheduling` | `gws-cli-runner`（`references/calendar.md`、`scripts/free_slots.py`） |
   | 吸収 | `external-report` | `doc-grill`（`references/external-report-standard.md`） |
   | 吸収 | `agent-env-parity` | `skill-manager` の `parity` コマンド |
   | 吸収 | `ghq-repo-placement` | `agents-common.md` の 1 行（クラウドには `~/Claude/AGENTS.md` が無いため） |
   | 削除 | `agent-orchestration-evaluator` | 不変条件の要約を `agent-orchestrator/references/orchestration-invariants.md` へ |
   | 削除 | `model-tuning` | 修正パターンと世代差分表を `agent-orchestrator/references/model-profiles.md` へ |
   | 削除 | `ai-usage-coach` | Promotion Candidate Score を `agent-orchestrator` references へ。`scripts/ai-usage-aggregate.py` は `scripts/` に残置 |
   | 削除 | `gemini-cli-runner` / `copilot-cli-runner` | なし（CLI の導入は `bootstrap-web` に残す） |

   維持 21 本: `codex-cli-runner`、`claude-cli-runner`（Codex のみ）、`grok-cli-runner`（X 取得が固有）、
   `agent-orchestrator`、`skill-manager`、`handoff`、`dads-design`（他 repo の gate が依存）、`repo-evaluator`、
   `op-cli-runner`、`onepassword-secret-materialize`、`gws-cli-runner`、`meeting-minutes`、`meeting-prep-brief`、
   `doc-grill`、`client-proposal-pack`、`deliverable-closeout`、`git-branch-review`、`pdf-extract`、
   `contract-review`、`expense-to-ledger`、`task-sweep`。
   - `contract-review` / `expense-to-ledger` は呼出 4 / 0 だが、repo ローカル版の統合先としてユーザーが維持を決めた。
   - `task-sweep` は repo ローカルへ移す案を採らず、会社固有値（gws / Slack の profile 名、対象 repo 名）を
     repo 側 profile に分離して main へ取り込む（ADR-0070 追補）。
   - `onepassword-secret-materialize` は計画では `op-cli-runner` へ吸収する予定だったが、別セッションが
     `~/.local/bin/opmaterialize` ラッパーを編集中のため今回は維持する。吸収は次回の棚卸しで再判断する。
2. **撤去した skill は削除せず退避する。** ADR-0069 決定 1 と同じく、配備先 3 箇所のコピーは
   `~/.local/share/skill-retired/2026-10-23/` へ移す。撤去日・理由・統合先・再導入条件は
   `docs/skills-install-manifest.md` の「撤去済み（first-party）」に残す。
3. **`agents-common.md` を削る。** 認証（1Password / ghrun / gws）、git / PR / マージ、artifact gate、
   orchestration の各節から日付付きの経緯・実測メモを外し、根拠は ADR 番号（0055 / 0057 / 0062 / 0063 / 0065 / 0071）と
   skill の references への参照に置き換える。orchestration は `agent-orchestrator` skill を正本と明記して短くする。
   規則の意味は変えない。`ghq-repo-placement` の代替として配置規則を 1 行追加する。
4. **ハーネスから 2 点を外す。** SUPERSET notify hook 5 本（導入時の ADR が無いため、導入経緯と削除理由は本 ADR の
   Context 4 を正本とする。通知先が無い hook を毎ツール呼び出しで起動する固定費だけが残っていた）と、
   `permissions.allow` の素の `Bash(gh pr merge *)`（`Bash(ghrun gh pr merge *)` は ADR-0071 のとおり残す）。
   `codex@openai-codex` plugin は外さない（ADR-0012 追補）。クラウドの Codex 委譲が plugin proxy に依存する可能性が
   ADR-0045 に記録され、ADR-0068 で未検証のままだからで、ローカル cache の不在は再インストール案内に留める。
   `phase_artifact_hook` / `git_chain_guard` / `context_guard` / SessionStart の `opmaterialize`、
   agents `biz` / `personal` / `tech`、`document-skills` / `skill-creator` plugin、`autoMode.allow` の規則は
   発火実績があるため残す。
5. **再発防止のハーネスを 3 件足す。** `scripts/skill-quick-validate` に description 長の budget 検査
   （1 本 500 文字で warn、合計を表示）、`scripts/skill-usage`（transcript から Skill 呼出を集計し 90 日呼出 0 を列挙。
   今回の集計 script を昇格）、`skill-manager` doctor の `source_branch`（配備コピーの `metadata.local-path` が
   未マージ worktree を指す場合を検出）。
6. **配備リストの正本は変えない。** `scripts/bootstrap-web` の `claude_skills` / `codex_skills` 配列を正本とし、
   `docs/skills-install-manifest.md` の install 行と `docs/web-session-runner-setup.md` の skill 表を同期する。
   `scripts/verify-cloud-parity` は配列を `bootstrap-web` から eval で読むため変更しない。

## Consequences

- 配備は main への取り込み後に、`chezmoi source-path` の root から manifest どおり `gh skill install`（Codex は rsync まで）
  をやり直し、撤去分を退避してから `skill-manager` の `doctor` で `retired_skills` / `first_party_sync` / `source_branch`
  が NO_ISSUES になるまで反映されない。クラウドは次の SessionStart で `bootstrap-web` の新しい配列を使う。
- `~/.claude/settings.json` の変更（hook / permission）は Claude 自身の設定変更で、auto mode では Agent が
  適用できない（ADR-0062 決定 7）。`chezmoi apply ~/.claude/settings.json` はユーザーが実行する。
- `codex@openai-codex` plugin は settings に残るが、ローカルの install cache は無い。ローカルで plugin が要る場合は
  ADR-0012 の手順どおり `claude plugin install codex@openai-codex` を個別実行する。クラウドの Codex 委譲が実際に
  plugin proxy を必要とするかは ADR-0068 の parity 検証で確かめ、不要と分かった時点で plugin の撤去を再判断する。
- 他 repo の文書が `gemini-cli-runner` / `copilot-cli-runner` / `soundcore-minutes` / `docs-evaluator` などを名指ししている
  箇所（ow-management の AGENTS.md / ADR 群など）は dotfiles の外なので今回は直さず、履歴として残す。
  呼べば skill 不在になるだけで、他の skill に誤って解決することは無い。
- 統合先 skill の description は複数の入口（`repo-evaluator` のコード / 文書、`meeting-minutes` の Soundcore 取得 /
  文字起こし保存）を 1 本で担うため長くなる。budget 検査（決定 5）で 500 文字を上限とし、超えたら references へ下ろす。
- fork 元（skills.sh 系）の同期は 2026-06-22 以降止まっており、今回の統合で fork 元との構成の乖離はさらに広がる。
  fork 同期は再開しない前提とし、必要になれば個別 skill の references 単位で差分を取り込む。
- gemini / copilot の CLI は `bootstrap-web` が引き続き導入する。runner skill が無いため、使う場合は
  `agent-orchestrator` の registry に provider を戻してから runner を再導入する。
- 再検討条件: `skill-usage` の 90 日集計で維持した skill に呼出 0 が続く場合、`repo-evaluator` / `meeting-minutes` の
  trigger eval で発火率が落ちた場合、`onepassword-secret-materialize` のラッパー編集が終わった場合（吸収の再判断）、
  クラウドセッションで plugin proxy 無しの Codex 委譲が実測できた場合（`codex@openai-codex` plugin の撤去）。

## Verification

- `scripts/skill-quick-validate` を `skills/` 配下の全 first-party skill（21 本）に実行して valid、description が
  各 500 文字以内
- manifest の Claude Code / Codex 節の install 行と `scripts/bootstrap-web` の `claude_skills` / `codex_skills`
  （各 20 本）が一致し、`skills/` 配下のディレクトリがすべてどちらかの配列に含まれること
- `.chezmoitemplates` / `dot_codex` / `docs/skills-install-manifest.md` / `scripts/bootstrap-web` /
  `docs/web-session-runner-setup.md` / `README.md` で撤去 15 本の名前が、撤去記録と変更履歴以外に残っていないこと（grep）
- `scripts/adr-number-check` が新規の重複を報告しないこと
- `scripts/docs-link-check` が `docs/` 内のリンク切れを報告しないこと
- `bash -n scripts/bootstrap-web` が通ること
- `agents-common.md` の文字数が 9,297 → 8,000 前後に減り、`chezmoi diff ~/.codex/AGENTS-common.md` が apply 後に空であること
- 新規・変更ファイルに実名・メールアドレス・secret・モデル名の直書きが無いこと（ADR の `agent_model` を除く）
