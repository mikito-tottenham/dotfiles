---
title: "Skill Inventory 2026-10: New Skills, Consolidation, and Deployment Cleanup"
date: 2026-10-03
worked_at: 2026-10-03 JST
agent_model: "Claude Opus 5.5 (claude-opus-5-5)"
status: proposed
related_adr: ["0016", "0032", "0045", "0057", "0058", "0062", "0064"]
---

# ADR 0069: 2026-10 の Skill 棚卸しに基づく新設・統合・配備整理

## Context

2026-10-02 に、Claude Code 302 セッション（2026-07-16〜10-02）、Codex 1,495 セッション、`~/Claude/.context`、
Skill の正本と配備先、dotfiles の ADR、各 repo の repo ローカル skill を棚卸しした
（作業 artifact: `~/Claude/.context/2026-10-02-skill-proposals/20-proposal.md`。件数はキーワード分類の目安）。

1. **ADR-0062 の撤去決定が配備先に反映されていなかった。** 撤去済み 6 skill が `~/.claude/skills`・
   `~/.agents/skills`・`~/.codex/skills` に残り、`~/.codex/skills` は同期漏れ（model-tuning / external-report の欠落、
   旧版の model registry）だった。Codex では撤去済みの `grill-me` が 69 回読み込まれていた。
2. **同じ工程が skill 化されずに繰り返されていた。**
   - 文字起こしからの議事録化: Claude 54 / Codex 23 セッション、4 repo に同じ工程
   - 文書の敵対レビュー（grill）: Codex 148 回（58 タスク、うち 19 タスクが 3 ラウンド以上）、Claude 28〜33 回
   - 締め作業（commit → PR → Drive 保存 → 索引リンク）: 65 セッション。手順と script が `.context` にあり、
     `~/Claude/AGENTS.md` がそこを参照していた
   - 複数 repo のブランチ / PR / worktree 整理: 関連 13 セッション、script の作り直し 5 回
   - 提案書作成 44、会議準備 39、認証断の対処 約 59、契約レビュー 19、会計 22、日程調整 21
3. **repo ローカル skill が分岐していた。** `pdf-extract` は 5 系統のコピーに分かれ、旧モデル名の直書き、
   Claude → Codex の機械置換で壊れたコピーがあった。`contract-review` も 2 repo で別実装だった。
4. **運用面の欠落。** ADR の連番重複（origin/main の 0048、main checkout の 0055）、merge / push を他コマンドと
   連結したことによる classifier block（172 件 / 71 セッション）、Codex automation の sandbox で DNS が遮断される問題、
   日次同期 script が `.context` にしか無いこと。

## Decision

1. **撤去済み skill は削除せず退避する。** 6 skill を 3 配備先から `~/.local/share/skill-retired/2026-10-03/` へ移した
   （18 件）。`~/.codex/skills` は manifest の Codex 節の手順（install → rsync）で再同期した。
   再発防止として `skill-manager` の `doctor` に `retired_skills`（manifest の撤去済み見出しと配備先・lock の突合）と
   `first_party_sync`（manifest の install 行を期待値にした正本・配備コピー・rsync 漏れの検査）を追加した。
2. **first-party skill を 11 本新設する。** 期待リストの正本は `scripts/bootstrap-web` の配列で、
   `docs/skills-install-manifest.md` と同期した（`verify-cloud-parity` は配列を読むため変更不要）。

   | 優先 | skill | 役割 |
   |---|---|---|
   | P1 | `meeting-minutes-ingest` | 文字起こし → 話者対応 → repo 別書式 → 索引 → タスク抽出。`soundcore-minutes` の後工程 |
   | P1 | `doc-grill` | 作成者と別 provider による敵対レビュー → 裁定表 → 整合レビューの反復。最終ゲートに送付前検品 |
   | P1 | `deliverable-closeout` | commit → PR → 組織別 Drive 保存 → 索引リンク。`.context` の script を skill の `scripts/` へ昇格 |
   | P2 | `client-proposal-pack` | 提案書の事前情報 → 骨格 → `doc-grill` → 出力 → `deliverable-closeout` |
   | P2 | `meeting-prep-brief` | カレンダー・議事録・チャット・メールのチェックリスト収集 |
   | P2 | `auth-preflight` | 1Password / gws / gh / Slack / MF の「エラー → 対処」表と preflight |
   | P2 | `agent-env-parity` | 正本・配備・ローカル・クラウドのドリフト検査の入口（既存 doctor / chezmoi-drift / verify-cloud-parity を呼び分ける） |
   | P3 | `contract-review` / `pdf-extract` | repo ローカル実装を横断 skill に昇格。会社固有値は repo プロファイルへ分離 |
   | P3 | `expense-to-ledger` / `multi-account-scheduling` | 同上 |

3. **repo 固有の値は skill に書かない。** dotfiles は公開 repo のため、会社名・repo 名・ID・メールアドレスは
   repo 側のプロファイル（`references/repo-profile.md` の形式）に置き、skill には汎用手順だけを置く。
   業種固有のプロンプトテンプレート（`pdf-extract`）も repo 側に残す。
4. **モデルは registry の role / tier で解決する。** 新規 skill はモデル名を書かない。`pdf-extract` は
   `agent-orchestrator/rules/model_registry.yaml` の `tiers.<tier>.codex` から解決し、Codex は codex-cli-runner 経由で起動する。
   親が Codex の場合は registry の `providers.codex.self_elision` に従い script を使わず agent_tool で抽出する
   （Codex の配備一覧には codex-cli-runner を入れない。script は runner 不在で exit 2 のまま止め、暗黙 fallback は足さない）。
   `contract-review` の複数レビューは registry の 2026-07-25 判断に従い Gemini を route に使わない。
5. **既存 skill を拡張する。**
   - `git-branch-review` に Fleet Mode（`scripts/fleet_*.py`）を追加し、2026-09-26 の `.context` script を取り込む。
     リモートブランチは再検証して削除コマンドを提示するだけで、削除はユーザー承認後に単独実行する
   - 日本語トリガー語を `git-branch-review` / `op-cli-runner` / `gws-cli-runner` / `soundcore-minutes` / `code-evaluator` に追加
   - `model-tuning` に Opus 5.5 の reference、`ai-usage-coach` に `scripts/ai-usage-aggregate.py` の参照を追加
6. **`auth-preflight` は既定で生体認証を誘発しない。** `op` サブコマンドと `oprun` は `--with-op` のときだけ実行する
   （2026-10-03 に `op whoami` が 15 秒応答せず timeout した観測による）。
7. **ADR 連番の重複を機械検査する。** `scripts/adr-number-check` を追加し、Claude / Codex の repo ローカル hook で
   `git commit` 時に新規の衝突だけを止める（exit 2）。既存の重複（0048）はリネームせず報告に留める。
8. **merge / push の連結は警告に留める。** `~/.claude/hooks/git_chain_guard.py` は `gh pr merge` / `git merge` / `git push` が
   他コマンドと連結されていれば `additionalContext` と `systemMessage` で警告する。権限判定は変えない
   （ADR-0057 の単独実行ルールの補助。承認後の実行経路を塞がないため、ADR-0062 決定 7 と同じ理由で block にしない）。
9. **artifact gate のグローバル版は Claude 側だけ、warn 既定とする。** repo に `scripts/phase_artifact_hook.py` があれば
   従来どおり block、無ければ `~/.claude/hooks/phase_artifact_hook.py --mode warn` を実行する。Codex のグローバル hook には
   入れない（ADR-0016 の「Codex の `~/.codex/hooks.json` に repo enforcement を載せない」を維持）。
10. **Codex automation の sandbox 対策は prefix rule で限定する。** `~/.codex/rules/automation-network.rules` に、
    日次同期コマンドと対象パッケージの `brew` 操作だけを allow で列挙する。`sandbox_workspace_write.network_access = true`
    は全 sandbox のネットワークを開けるため採らない。`default.rules` は Codex が承認時に書き込むため別ファイルにする。
    日次同期 script は `~/.local/bin/claude-github-daily-sync`（chezmoi 管理）へ移し、automation 定義も chezmoi 管理にする（ADR-0032 追補）。
11. **classifier への教示は `autoMode.allow` の自然言語規則で行う。** 読み取りだけなのに止められた約 15 件
    （git / gh の読み取り、設定済み remote からの fetch、gws の get / list）を対象にし、`permissions.allow` には入れない
    （ADR-0064 と同じ方針）。状態変更・credential・設定の自己変更・heredoc は対象外。

## Consequences

- 配備は main への取り込み後、`chezmoi source-path` の root から manifest どおり `gh skill install`（Codex は rsync まで）を
  やり直すまで反映されない。退避した旧 skill は `~/.local/share/skill-retired/2026-10-03/` に残る。
- `pdf-extract` と `contract-review` は global と repo ローカルの同名 skill が並ぶ。repo 側の置き換えと配備の順序は
  repo ごとに決める。
- `client-proposal-pack` は `doc-grill` と `deliverable-closeout` に名前で依存する。どちらかの名前や手順を変えたら合わせる。
- artifact gate のグローバル warn と git_chain_guard は警告のみのため、classifier の文脈依存の判断は規則だけでは防ぎきれない。
- Desktop automation で `~/.codex/rules/*.rules` が読み込まれるかは文書に記載が無く未検証。apply 後の次回実行で
  sandbox の DNS 失敗が消えたかを memory で確認する。
- 再検討条件: trigger eval で新規 skill の発火率が低い場合、`doctor` の `retired_skills` / `first_party_sync` が
  再び不整合を検出した場合、Codex に codex-cli-runner を配備する判断をした場合（`pdf-extract` の Codex 親経路を見直す）。

## Verification

- `scripts/skill-quick-validate` を `skills/` 配下の全 first-party skill に実行して valid
- manifest の Claude Code / Codex 節の install 行と `scripts/bootstrap-web` の `claude_skills` / `codex_skills` が一致し、
  `skills/` 配下のディレクトリがすべてどちらかの配列に含まれること
- `scripts/adr-number-check` が新規の重複を報告しないこと（既存 0048 のみ）
- `skill-manager` の `doctor` で `retired_skills` / `first_party_sync` が NO_ISSUES（2026-10-03 の退避・再同期後に確認済み）
- `pdf-extract`: runner 不在で exit 2 と Codex 親経路の案内、`codex` 不在で exit 127 と `fallback_required` を返すこと
- 新規 skill 配下に実名・メールアドレス・secret・モデル名の直書きが無いこと（grep）
