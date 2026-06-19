#!/bin/bash
# session-start.sh — Claude Code on the web 用 skill インストーラ
#
# web のコンテナは毎回まっさらで gh も入っていないため、ローカルの
# ~/.claude/skills/ や `gh skill install` の結果を引き継げない。本フックは
# SessionStart 時に repo の skills/ (first-party publisher skill) を
# ~/.claude/skills/ へ copy し、external の grill-me (+ 依存 grilling) を upstream から
# 取得して web セッションで skill を使えるようにする。
#
# ローカルマシンでは何もしない（gh skill + chezmoi が正規経路）。
#
# 注意: AGENTS.md「スキル管理」は復元を script 化せず gh skill を標準とする方針。
# 本フックは gh 非搭載の web コンテナに限った例外であり、根拠は
# docs/adr/0045-web-session-skill-install.md (Proposed) に残す。
set -uo pipefail

# web (remote container) 以外では何もしない。ローカルは gh skill が正規経路。
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
DEST="$HOME/.claude/skills"
SRC_DIR="$REPO_DIR/skills"

# ログは stderr へ。SessionStart の stdout は session context へ注入されるため空に保つ。
log()  { printf '[skills-hook] %s\n' "$*" >&2; }
warn() { printf '[skills-hook][warn] %s\n' "$*" >&2; }

log "start: REPO_DIR=$REPO_DIR DEST=$DEST"
mkdir -p "$DEST"

# Claude Code 向けに copy しない first-party skill:
#   claude-cli-runner              -> manifest 上 Codex 専用
#   onepassword-secret-materialize -> repo-local .claude/skills/ で既に供給
SKIP_SET=" claude-cli-runner onepassword-secret-materialize "

installed=0
skipped=0
if [ -d "$SRC_DIR" ]; then
  for src in "$SRC_DIR"/*/; do
    [ -f "${src}SKILL.md" ] || continue
    name="$(basename "$src")"
    case "$SKIP_SET" in
      *" $name "*) log "skip $name (codex-only or repo-local)"; skipped=$((skipped + 1)); continue ;;
    esac
    if rm -rf "$DEST/$name" && cp -R "$SRC_DIR/$name" "$DEST/$name"; then
      installed=$((installed + 1))
    else
      warn "failed to install first-party skill: $name"
    fi
  done
  log "first-party: installed=$installed skipped=$skipped"
else
  warn "no skills/ dir at $SRC_DIR; skipped first-party install"
fi

# --- external: grill-me (+ 依存 grilling) (mattpocock/skills) ---
# AGENTS.md「スキル管理」: external skill は repo に vendoring しない。runtime で upstream 取得する。
# upstream は publisher layout (skills/<category>/<skill>) へ再編済みのため、固定パスではなく
# find で skill を探す。grill-me 本体は `/grilling` を呼ぶだけなので依存の grilling も併せて入れる。
MP_SKILLS="grill-me grilling"
if command -v git >/dev/null 2>&1; then
  TO=""
  command -v timeout >/dev/null 2>&1 && TO="timeout 60"
  tmp="$(mktemp -d)"
  if $TO git clone --depth 1 --quiet https://github.com/mattpocock/skills "$tmp/src" 2>/dev/null; then
    for s in $MP_SKILLS; do
      d="$(find "$tmp/src" -type d -name "$s" -exec test -f '{}/SKILL.md' ';' -print 2>/dev/null | head -1)"
      if [ -n "$d" ]; then
        if rm -rf "$DEST/$s" && cp -R "$d" "$DEST/$s"; then
          log "external: installed $s"
        else
          warn "failed to copy $s into $DEST"
        fi
      else
        warn "external: $s not found in mattpocock/skills (upstream layout changed?); skipped"
      fi
    done
  else
    warn "could not clone mattpocock/skills (network policy?); skipped grill-me"
  fi
  rm -rf "$tmp"
else
  warn "git not available; skipped grill-me"
fi

# NOTE: 次の skill は意図的に未対応。
#   - empirical-prompt-tuning: manifest 記載の upstream URL が現在 404。
#     Codex が manifest の正しい path を更新したら追加する。
#   - gws-*: googleworkspace-cli (Brewfile) が web コンテナに無く動作不可。

log "done: skill dirs in $DEST = $(find "$DEST" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
exit 0
