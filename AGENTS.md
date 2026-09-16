# このファイルについて

- 共通ルール（作業姿勢、恒久指示の反映、Phase / Step artifact、委譲、secret 運用）の正本は `.chezmoitemplates/agents-common.md` であり、`~/.codex/AGENTS-common.md` / `~/.claude/CLAUDE.md` 経由で毎セッション読み込まれる。本ファイルには dotfiles リポジトリ固有の差分だけを書き、共通ルールを再掲しないこと
- 恒久指示の反映先: 共通ルールなら `.chezmoitemplates/agents-common.md`、dotfiles 固有の運用なら本ファイル、背景・採用理由は `docs/adr/`、反復手順は対応 Skill

# リポジトリ管理ルール

- このリポジトリ（dotfiles）の管理責任は Codex が持つ
- `dot_*` 配下のファイルは chezmoi により環境へ配置される成果物として扱う
- `dot_*` 配下の変更時は必ず `dotfile-update` スキルを使用すること
- dotfile 変更前に [chezmoi-knowledge/SKILL.md](.claude/skills/chezmoi-knowledge/SKILL.md) と [semantics.md](.claude/skills/chezmoi-knowledge/references/semantics.md) を確認し、source / target / ignore の前提を外さないこと
- `chezmoi apply` の前とドリフト確認時は `scripts/chezmoi-drift --check-ignore` 相当の `.chezmoiignore` 整合確認を行い、意図せず無効化された source がないことを確認すること
- ファイル探索は `rg --files`、内容検索は `rg` を第一候補とし、`rg` が使えない場合だけ `ag`、最後に `grep` を使うこと

# Desktop 自動実行設定管理

- Codex Desktop の automation は `dot_codex/automations/<automation-id>/automation.toml.tmpl` を正本とすること
- 自動実行の `memory.md`、lock、jitter salt、highwatermark、実行ログ、セッション履歴、UUID ごとの task 実行状態は machine-local state として `.chezmoiignore` で管理対象外にすること
- Claude Desktop / Claude Code の `~/.claude/tasks` は、安定した宣言的 schedule ではなく実行 state として扱い、明示的に管理対象へ昇格する根拠が確認できるまで chezmoi で管理しないこと
- 新しい Desktop 自動実行設定を追加するときは、source / target の対応を確認し、secret・token・認証情報が含まれないことを点検してから git 管理へ追加すること

# スキル管理

- 本リポジトリではリポジトリ専用の Claude Code 用スキル（`.claude/skills/`）も管理対象に含む
- `.claude/skills/` 配下のファイルは repo ローカル用途とし、chezmoi でグローバル配備しない
- 配布する repo オリジナル skill は publisher layout の `skills/` 配下を正本として git 管理すること
- publisher layout の skill は `gh skill install --from-local <repo-root> <skill> --agent <agent> --scope user` を標準配備経路とし、chezmoi で `~/.claude/skills/` や `~/.codex/skills/` へ直接配備しないこと
- 新しいマシン向けの復元情報は当面 script 化せず、`docs/skills-install-manifest.md` の docs-only manifest を正本として保存すること
- ただしクラウドの ephemeral 環境（Claude Code on the web / Codex cloud）に限り、`scripts/bootstrap-web` と SessionStart hook（`.claude/hooks/session-start.sh`、Claude のみ）で `chezmoi apply` とスキル再インストールを自動化してよい（ADR-0045・ADR-0058）。これはセッション起動時の再現専用で、ローカル / macOS の標準配備は引き続き `gh skill install` と docs-only manifest を正本とすること
- `scripts/bootstrap-web` では first-party skill を必須（欠落で `exit 1`）、公開 third-party skill を best-effort（取得失敗は skip）として扱い、結果を `$BOOTSTRAP_WEB_STATUS` に機械可読で残すこと。`chezmoi apply --force` がハーネス書き込みの `~/.gitconfig` も上書きし、web セッションのコミットが dotfiles の git identity になる点は意識的受容事項として ADR-0045 に記録すること
- `scripts/bootstrap-web` はプラットフォーム非依存に保ち、source の固定は `BOOTSTRAP_REPO_DIR` で行うこと（`CLAUDE_PROJECT_DIR` は Claude 固有のため前提にしない、ADR-0058）
- skill / CLI / MCP を増減したときは `docs/skills-install-manifest.md`・`scripts/bootstrap-web`・`scripts/verify-cloud-parity` の 3 箇所を同期すること。期待リストの正本は `bootstrap-web` の配列とし、検証側でリストを再定義しないこと
- クラウド環境の再現差分は `scripts/verify-cloud-parity` で検査すること。`MISSING` は移植差分、`N/A` はその環境の対象外を意味し、secret は有無だけを検査して実値を出力しないこと
- headless で再現できない要素（ローカルアプリ依存の MCP、対話 OAuth 必須の連携）は再現対象に含めず、対象外である理由を配列コメントと手順書に残すこと
- external skill はこの repo に vendoring せず、`gh skill` による install / update / remove を標準運用とすること
- ただし fork 元 `rmanzoku/dotfiles` の publisher layout skill は external ではなく repo オリジナル skill と同格に扱い、同一 path `skills/<name>` へ verbatim copy で取り込み、first-party として `docs/skills-install-manifest.md` と `scripts/bootstrap-web` を同期すること（fork sync との整合が目的）
- third-party external skill が upstream publisher layout を持たない場合は、`docs/skills-install-manifest.md` に `fetch + gh skill install --from-local` 手順を残して管理すること
- Codex `.system/skill-installer` は Codex-only の補助入口として認識し、恒久的な外部 skill 管理は `gh skill` と `docs/skills-install-manifest.md` を正本にすること
- 各 AI ツール間のスキル同期は skill-manager スキルの責務であり、本リポジトリでは扱わない
- `dotfile-update` は chezmoi 管理の dotfile 更新専用とし、repo ローカル skill の編集責務を持たせない
- `.claude/skills/` 配下の repo ローカル skill と `skills/` 配下の publisher skill を追加・更新・構成変更する場合は、既存 Skill の更新であっても `skill-creator` スキルの手順に従うこと
- Skill 更新時は `SKILL.md` だけでなく、必要に応じて `scripts/`、`references/`、`assets/`、`agents/openai.yaml` の整合も確認すること
- Skill 更新後は repo ローカルの `scripts/skill-quick-validate <skill-dir>` を実行して基本妥当性を確認すること
