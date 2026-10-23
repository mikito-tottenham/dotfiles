# shellcheck shell=bash
# shellcheck disable=SC2034  # 配列は source 側 (deploy-skills / bootstrap-web / verify-cloud-parity) が使う
# skill-lists.sh: 配布 skill の期待リストの正本。source して使う (実行しない)。
#
# 利用側:
#   scripts/deploy-skills        ローカル配備 (chezmoi apply の run_onchange から呼ばれる)
#   scripts/bootstrap-web        クラウド (Claude Code on the web / Codex cloud) の再現
#   scripts/verify-cloud-parity  再現差分の検査
#
# skill を増減・pin 更新したときは、このファイルと docs/skills-install-manifest.md の
# install 行 (+ 撤去表) を同時に更新すること。deploy-skills の preflight が両者の一致を検査し、
# skill-manager の doctor は manifest の install 行を期待値に使う。
#
# first-party skill のエージェント別リスト (repo の skills/<name> を --from-local で配備する)。
# Claude Code には codex-cli-runner、Codex には claude-cli-runner を入れる差分に注意。
claude_skills=(
  codex-cli-runner grok-cli-runner agent-orchestrator skill-manager handoff
  dads-design repo-evaluator op-cli-runner onepassword-secret-materialize gws-cli-runner
  meeting-minutes meeting-prep-brief doc-grill client-proposal-pack deliverable-closeout
  git-branch-review pdf-extract contract-review expense-to-ledger task-sweep
)
codex_skills=(
  claude-cli-runner grok-cli-runner agent-orchestrator skill-manager handoff
  dads-design repo-evaluator op-cli-runner onepassword-secret-materialize gws-cli-runner
  meeting-minutes meeting-prep-brief doc-grill client-proposal-pack deliverable-closeout
  git-branch-review pdf-extract contract-review expense-to-ledger task-sweep
)

# 公開 third-party skill の pin (Claude Code / Codex 共通)。書式:
#   "owner/repo|commit sha|repo 内の skill path|skill 名"
# 撤去済み (gws-shared / gws-drive / gws-drive-upload / grill-me / empirical-prompt-tuning) は
# docs/skills-install-manifest.md の撤去記録を正本とし、ここには載せない。
third_party_pins=(
  "coji/natural-japanese|9a78a42964096da509b8f3e011f0085a5f080151|skills/natural-japanese|natural-japanese"
  "RobTar97/japanese-writing-skills|e4b1700464219c60da786f005a061bccffbbd4e3|skills/japanese-business-writing|japanese-business-writing"
)
