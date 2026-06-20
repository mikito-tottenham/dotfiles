#!/bin/bash
set -euo pipefail

# SessionStart hook: Claude Code on the web の ephemeral 環境でのみ rmanzoku 環境を再現する。
# ローカルや非 remote 実行では何もしない。
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
exec "$REPO_DIR/scripts/bootstrap-web"
