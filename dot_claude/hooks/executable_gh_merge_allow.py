#!/usr/bin/env python3
"""PreToolUse(Bash) hook: 条件を満たす単独の `ghrun gh pr merge` を許可する。

agents-common の「作業指示で作った PR は、チェックがすべて成功し `mergeStateStatus` が `CLEAN` なら
マージする」（dotfiles ADR-0071）を、auto mode の classifier の判断に任せず決定的に通すための hook
（ADR-0075）。`permissions.allow` の `Bash(ghrun gh pr merge *)` は auto mode で判定を決めず、
classifier が「レビューなしのマージ」として止める例が残ったため、この hook に置き換えた。

次をすべて満たすときだけ `permissionDecision: "allow"` を返す。1 つでも外れたら許可を返さず、
通常の permission 判定（allow / deny ルール、auto mode の classifier）に任せる。

- コマンドが連結・リダイレクト・変数展開・クォートを含まない 1 つで、`ghrun gh pr merge <番号>` で始まる
  （前置きは `timeout <秒>` だけ可）
- オプションは `--merge` / `--squash` / `--rebase` のどれか 1 つと、`--repo` / `-R`、
  `--match-head-commit`、`--delete-branch=false` だけ（`--admin`、`--auto`、`--delete-branch` は不可）
- GitHub 上で PR が OPEN・draft でない・`mergeStateStatus` が `CLEAN`・作者が token の持ち主

リポ側の `deny` ルールは hook の allow より優先されるため、マージさせたくないリポは
`.claude/settings.json` の `permissions.deny` に `Bash(ghrun gh pr merge *)` を書けば止められる。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

SAFE_CHARS = re.compile(r"^[A-Za-z0-9 _./=-]+$")
METHOD_FLAGS = {"--merge", "-m", "--squash", "-s", "--rebase", "-r"}
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA = re.compile(r"^[0-9a-fA-F]{7,40}$")
GH_TIMEOUT = 8


def parse(command: str) -> dict | None:
    """許可対象のマージコマンドなら {number, repo} を返す。対象外なら None。"""
    if not SAFE_CHARS.match(command):
        return None
    args = command.split()
    if args[:1] == ["timeout"]:
        if len(args) < 2 or not re.fullmatch(r"\d+[smh]?", args[1]):
            return None
        args = args[2:]
    if args[:4] != ["ghrun", "gh", "pr", "merge"]:
        return None
    number = repo = None
    methods = 0
    rest = args[4:]
    i = 0
    while i < len(rest):
        arg = rest[i]
        value = None
        if "=" in arg and arg.startswith("--"):
            arg, value = arg.split("=", 1)
        if arg in METHOD_FLAGS and value is None:
            methods += 1
        elif arg in ("--repo", "-R"):
            if value is None:
                i += 1
                value = rest[i] if i < len(rest) else ""
            if not REPO.match(value):
                return None
            repo = value
        elif arg == "--match-head-commit":
            if value is None:
                i += 1
                value = rest[i] if i < len(rest) else ""
            if not SHA.match(value):
                return None
        elif arg == "--delete-branch" and value == "false":
            pass
        elif value is None and re.fullmatch(r"\d+", arg) and number is None:
            number = arg
        else:
            return None
        i += 1
    if number is None or methods != 1:
        return None
    return {"number": number, "repo": repo}


def gh(ghrun: str, args: list[str], cwd: str | None) -> str:
    result = subprocess.run(
        [ghrun, "gh", *args], cwd=cwd, capture_output=True, text=True, timeout=GH_TIMEOUT
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip()[:200])
    return result.stdout


def refusal(target: dict, cwd: str | None) -> str | None:
    """PR の状態が許可条件を満たせば None、満たさなければ理由を返す。"""
    ghrun = os.path.expanduser("~/.local/bin/ghrun")
    if not os.access(ghrun, os.X_OK):
        ghrun = shutil.which("ghrun") or ""
    if not ghrun:
        return "ghrun が見つからない"
    view = ["pr", "view", target["number"], "--json", "state,isDraft,mergeStateStatus,author"]
    if target["repo"]:
        view += ["--repo", target["repo"]]
    try:
        pr = json.loads(gh(ghrun, view, cwd))
        viewer = gh(ghrun, ["api", "user", "--jq", ".login"], cwd).strip()
    except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return f"PR の状態を取得できない（{exc}）"
    if pr.get("state") != "OPEN" or pr.get("isDraft"):
        return f"PR が OPEN でないか draft（state={pr.get('state')}, isDraft={pr.get('isDraft')}）"
    if pr.get("mergeStateStatus") != "CLEAN":
        return f"mergeStateStatus が {pr.get('mergeStateStatus')}（CLEAN でない）"
    author = (pr.get("author") or {}).get("login")
    if author != viewer:
        return f"PR の作者 {author} が token の持ち主 {viewer} と違う"
    return None


def main() -> int:
    raw = sys.stdin.read().strip()
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return 0
    tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return 0
    target = parse(command.strip())
    if target is None:
        return 0
    cwd = payload.get("cwd")
    reason = refusal(target, cwd if isinstance(cwd, str) and os.path.isdir(cwd) else None)
    if reason:
        message = (
            f"[gh-merge-allow] PR #{target['number']} は自動許可の条件を満たさないため、"
            f"通常の permission 判定に回します: {reason}"
        )
        print(message, file=sys.stderr)
        print(json.dumps({
            "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": message},
        }, ensure_ascii=False))
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": (
                f"[gh-merge-allow] PR #{target['number']} は OPEN・CLEAN・自分の PR（ADR-0075）"
            ),
        },
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
