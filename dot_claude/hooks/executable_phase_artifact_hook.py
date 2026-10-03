#!/usr/bin/env python3
"""Minimal artifact gate shared by Claude Code and Codex hooks.

配置: 正本は dotfiles の `dot_claude/hooks/executable_phase_artifact_hook.py`
（chezmoi で `~/.claude/hooks/phase_artifact_hook.py` に配備）。dotfiles repo の
`scripts/phase_artifact_hook.py` はこのファイルへの symlink。

--mode block（既定）: repo ローカル enforcement。artifact が無ければ exit 2 で止める。
--mode warn: グローバル hook 用。止めずに警告だけを Claude のコンテキストへ渡す（exit 0）。
  Phase 作業でない通常作業をブロックしないため、repo ローカルに hook script が無い場所では
  こちらを使う。検査内容は block と同じ（artifact 存在・初期必須キー・単発例外ファイル）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_KEYS = ("task", "phase_or_step", "created_at")
TRANSITION_PATTERNS = (
    re.compile(r"\bcodex\s+(exec|review)\b"),
    re.compile(r"\bquick_validate\.py\b"),
    re.compile(r"\bgit\s+commit\b"),
    re.compile(r"\bchezmoi\s+apply\b"),
    re.compile(r"\bscripts/chezmoi-drift\s+--(apply|restore)\b"),
)
STOP_MARKERS = ("<proposed_plan>",)
SUCCESS_TEXT = "artifact check passed"
ERROR_TEXT = "artifact required but missing"


@dataclass(order=True)
class Artifact:
    mtime: float
    path: Path
    data: dict[str, Any]


def load_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw}


def parse_iso8601(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    result: dict[str, Any] = {}
    lines = text.splitlines()
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"')
    return result


def parse_artifact(path: Path) -> Artifact | None:
    try:
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix == ".md":
            data = parse_frontmatter(path.read_text(encoding="utf-8"))
        else:
            return None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if not all(str(data.get(key, "")).strip() for key in REQUIRED_KEYS):
        return None
    if parse_iso8601(str(data.get("created_at", ""))) is None:
        return None
    return Artifact(path.stat().st_mtime, path, data)


def has_artifact(context_dir: Path) -> bool:
    """有効な artifact が 1 件でもあれば True（走査を早期終了する）。"""
    if not context_dir.is_dir():
        return False
    for path in context_dir.rglob("*"):
        if "single-step" in path.parts or not path.is_file():
            continue
        if parse_artifact(path) is not None:
            return True
    return False


def valid_single_step_exception(context_dir: Path) -> bool:
    single_step_dir = context_dir / "single-step"
    if not single_step_dir.is_dir():
        return False
    now = datetime.now(timezone.utc)
    for path in sorted(single_step_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("enabled") is not True:
            continue
        if not all(str(data.get(key, "")).strip() for key in ("task", "reason", "expires_at")):
            continue
        expires_at = parse_iso8601(str(data.get("expires_at", "")))
        if expires_at is None or expires_at <= now:
            continue
        return True
    return False


def extract_command(payload: dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str):
            return command
    command = payload.get("command")
    return command if isinstance(command, str) else ""


def should_gate_command(command: str) -> bool:
    normalized = command.strip()
    return bool(normalized) and any(pattern.search(normalized) for pattern in TRANSITION_PATTERNS)


def should_gate_stop(payload: dict[str, Any]) -> bool:
    message = payload.get("last_assistant_message")
    if not isinstance(message, str):
        return False
    lowered = message.lower()
    return any(marker in message for marker in STOP_MARKERS) or "proposed plan" in lowered


def emit_codex_stop_pass() -> int:
    print(json.dumps({}))
    return 0


def emit_codex_stop_block() -> int:
    print(json.dumps({"decision": "block", "reason": ERROR_TEXT}))
    return 0


def emit_pretool_warning() -> int:
    message = (
        f"[artifact-gate warn] {ERROR_TEXT}: .context/ に task / phase_or_step / created_at を持つ "
        "artifact がありません。Phase / Step を持つ作業なら、遷移前に .context/<task>/<nn>-<phase>.md を"
        "保存してください。非 Phase 作業ならこの警告は無視してよく、明示的にバイパスする場合は "
        ".context/single-step/<task>.json（enabled / task / reason / expires_at）を使います。"
    )
    print(message, file=sys.stderr)
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": message},
    }, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", choices=("pretool", "stop"), required=True)
    parser.add_argument("--mode", choices=("block", "warn"), default="block")
    args = parser.parse_args()

    repo_root = Path.cwd()
    context_dir = repo_root / ".context"
    payload = load_payload()

    if args.event == "pretool":
        command = extract_command(payload)
        if not should_gate_command(command):
            return 0
        if valid_single_step_exception(context_dir) or has_artifact(context_dir):
            if args.mode == "block":
                print(SUCCESS_TEXT)
            return 0
        if args.mode == "warn":
            return emit_pretool_warning()
        print(ERROR_TEXT, file=sys.stderr)
        return 2

    if not should_gate_stop(payload):
        return emit_codex_stop_pass()
    if valid_single_step_exception(context_dir) or has_artifact(context_dir):
        return emit_codex_stop_pass()
    if args.mode == "warn":
        return emit_codex_stop_pass()
    return emit_codex_stop_block()


if __name__ == "__main__":
    raise SystemExit(main())
