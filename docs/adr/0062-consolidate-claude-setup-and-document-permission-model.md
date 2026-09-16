---
title: "Consolidate Claude / Codex Setup and Document the Permission Model"
date: 2026-09-15
agent_model: "Claude Code (Claude Fable 5.1)"
status: proposed
---

# ADR 0062: Consolidate Claude / Codex Setup and Document the Permission Model

## Context

2026-09-15 に Claude Code / Codex 共用の設定全体（Skill、指示ファイル、settings、hooks、memory）を
棚卸しした（成果物は `~/Claude/.context/2026-09-15-claude-setup-review/`）。主な発見:

- Skill 正本が分岐していた。`chezmoi source-path` は ghq checkout（ADR 0056）を返すが、旧 clone
  `~/.local/share/chezmoi`（14 commit 古い）が残っており、同日 15 時台の Codex セッションがそこで
  SKILL.md 18 件の description を短縮（ADR 0053 方針）して各配備先へ `gh skill install --from-local`
  していた。ghq 正本には未反映で、`metadata.local-path` は全 first-party skill で旧 clone を指していた。
  副作用として日本語トリガー語が全 skill から消えていた。
- runner skill の prompt-profile がモデル固定（codex: GPT-5.5、claude: Opus 4.7/4.8）で、
  `model_registry.yaml`（gpt-5.6）と `~/.codex/config.toml`（gpt-6-astra）の 3 世代がずれていた。
- モデル固有 tuning skill（opus-4-7 / opus-4-8 / gpt-5-5）は骨格 8 割が同一で、対象モデルが現行より
  1 世代古く、description 長で上位 2 件を占めていた。
- third-party `gws-shared` / `gws-drive` / `gws-drive-upload` は素の `gws auth login` / service account を
  案内し、`gws-account <profile>` 強制（ADR 0048）と衝突していた。`grill-me`（mattpocock）は本文が
  存在しない `/grilling` を参照するだけの stub だった。
- `scripts/phase_artifact_hook.py` が `.context` 内の list 型 JSON で `AttributeError` を出し、
  dotfiles での毎 Bash に traceback が出ていた（exit 1 は非ブロッキングのため実害は出力のみ）。
- 固定コンテキスト（指示ファイル 4 本 + MEMORY.md）は約 28KB ≒ 10k token。agents-common の
  gws 節に参照時だけ必要な手順が含まれ、`dotfiles/AGENTS.md` の 27 bullet が agents-common と
  重複していた。auto memory 13 件のうち 8 件は既に git 管理ファイルへ反映済みだった。
- `~/.claude.json` の chatwork MCP に API token が平文で入っていた。
- 権限モデル: `~/.claude/settings.json` は `bypassPermissions` と対話プロンプト skip を組み合わせており、
  git 状態変更や外部送信の承認は agents-common の指示文と Claude 側 system prompt の確認ルールだけで
  担保している。harness 側の hook ゲートは無い。

## Decision

1. **Skill 正本は ghq checkout のみ。** 旧 clone の未コミット変更は ghq 正本へ移植し、description 短縮は
   採用した上で HEAD 版の日本語トリガー語を復元した。first-party skill の install は
   `chezmoi source-path` の root から実行することを manifest と skill-manager に明記し、旧 clone は
   廃止対象とする（削除はユーザー操作）。
2. **Codex の model registry は `~/.codex/models_cache.json` に実在する ID のみ使う。** tier A =
   `gpt-6-astra`（config.toml の既定と一致）、tier B = `gpt-5.6-sol`、tier C = `gpt-5.6-luna`。
   runner の prompt-profile はモデル固定をやめ provider 固有 adapter とし、registry の model / effort を透過する。
3. **tuning skill は `model-tuning` 1 本に統合**し、モデル差分は `references/<model>.md` に置く。
   opus-4-7-tuning は削除、旧世代は legacy references に残す。
4. **third-party gws-* 3 skill と grill-me は撤去。** Drive 操作の要点は `gws-cli-runner/references/drive.md`
   に吸収。grill-me は Claude built-in（`anthropic-skills:grill-me`）で代替し、Codex 側は代替なし。
5. **runner 4 本の共通契約は各 skill の `references/runner-common.md`（同一内容のコピー）**に集約し、
   `scripts/skill-quick-validate` で hash 一致を検査する。symlink にしないのは配備単位の独立性のため。
6. **固定コンテキスト削減:** agents-common の gws 詳細を `gws-cli-runner/references/account-profiles.md` へ
   移し、agents-common には常時ルール 3 行だけ残す。`dotfiles/AGENTS.md` は dotfiles 固有差分のみとする。
   `dotfiles/CLAUDE.md` の「Claude は dot_* 編集禁止」は撤回し、source 側編集 + target 明示 apply に改める。
7. **権限モデルは現状維持を明文化する。** `bypassPermissions` + skip 系フラグは自律運用のために維持し、
   git 状態変更・削除・外部送信の承認は agents-common の指示文（2026-09-09 ユーザー指示）と Claude 側の
   system prompt 確認ルールで担保する。harness の PreToolUse hook で git 状態変更を常時ブロックする案は、
   承認後に実行する経路が無くなるため採らない。`gh pr merge *` / `git merge *` の allow は、複合コマンドが
   classifier にブロックされる実測（2026-08-19）への対策として残す。auto mode の classifier は Claude 自身の
   設定・memory 編集を「自己変更」として拒否するため、それらはユーザーが実行するスクリプトで渡す。
8. **secret:** chatwork MCP の token は 1Password item へ移し、`~/.claude.json` は `oprun` + `op://` 参照経由に
   切り替える。実値の移送はユーザー操作。

## Consequences

- Claude / Codex 双方が同じ正本（ghq `skills/`、agents-common）を読む状態に戻る。再発防止は
  skill-manager の local-path stale 検出と manifest の実行元明記。
- 毎セッションの固定コンテキストは指示ファイル側で約 2KB + skill description 側で約 1KB 減る見込み。
  主因は MCP ツール定義のため、不要な MCP サーバー（pencil）は削除した。
- 権限モデルの再検討条件: Claude Code が「承認済み操作だけを通す」宣言ファイル式の allow を harness で
  サポートした場合、または無確認の状態変更事故が起きた場合。
- 未対応: agents（biz / personal / tech）の `model` / `tools` 指定は 1Password 管理の復元対象のため別タスク。
  `~/.agents/skills` は消費者不明のため据え置き（2026-08-12 の機械置換で 4 skill 破損あり）。

## Verification

- `scripts/skill-quick-validate` を全 first-party skill に実行して valid
- `.context/2026-09-15-claude-setup-review/skill_drift_scan.py` で正本と配備先が `identical` /
  `local_path_current` のみになること
- `scripts/phase_artifact_hook.py --event pretool` を list 型 JSON を含む `.context` で実行して traceback なし
- `chezmoi cat ~/.codex/AGENTS-common.md` がレンダリングされ、gws 節が 3 行になっていること
