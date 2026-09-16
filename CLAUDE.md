# Claude Code 向け補足

- 共通ルールは `~/.claude/CLAUDE.md` 経由で読む `agents-common.md`（正本は本リポジトリの `.chezmoitemplates/agents-common.md`）を正本とし、本リポジトリ固有の運用は `AGENTS.md` を参照すること
- `dot_*` / `.chezmoitemplates` 配下は chezmoi によって PC 全体の設定として配置される成果物である。配備済みの指示ファイルや設定を直す必要があるときは、target の実ファイルではなくこの source 側を編集すること（agents-common の「管理元へ反映」ルールの具体化）
- `dot_*` 配下を編集したときは `dotfile-update` スキルの手順に従い、`chezmoi apply` は対象 target を明示して実行し、引数なしの全体 apply や `--force` は使わないこと（未コミットのローカル差分を巻き込むため）
- Claude Code は自身の設定ファイル（`~/.claude/settings*.json`、`~/.claude.json`、auto memory）を auto mode では直接編集できない。必要な変更は source 側の編集と、ユーザーが実行するスクリプト（`.context/` に置く）で渡すこと
