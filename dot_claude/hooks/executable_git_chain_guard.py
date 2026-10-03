#!/usr/bin/env python3
"""PreToolUse(Bash) hook: merge / push を他コマンドと連結した実行を警告する。

agents-common の「マージなどの状態変更コマンドは `&&`・`;`・パイプで連結せず単独で実行する」
ルール（dotfiles ADR-0057）の補助 enforcement。判定はコマンド文字列の機械的な分解だけで、
意味理解は持たない。ブロックはせず（exit 0）、警告を Claude のコンテキスト（additionalContext）と
ユーザー向け表示（systemMessage）へ出し、同じ文面を stderr（debug log）にも書く。

対象: `gh pr merge` / `git merge` / `git push`（`ghrun` / `oprun` / `timeout N` / 環境変数前置きを含む）。
連結とみなす演算子: `&&` `||` `;` `|` `|&` `&` 改行。
"""

from __future__ import annotations

import json
import re
import shlex
import sys

SEPARATORS = {"&&", "||", ";", "|", "|&", "&", "\n", ";;"}
WRAPPERS = {"ghrun", "oprun", "command", "env", "nohup", "time", "exec"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def tokenize(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars="();<>|&\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        return command.split()


def segments(tokens: list[str]) -> list[list[str]]:
    result: list[list[str]] = [[]]
    for tok in tokens:
        if tok in SEPARATORS:
            if result[-1]:
                result.append([])
            continue
        if tok in ("(", ")"):
            continue
        result[-1].append(tok)
    return [seg for seg in result if seg]


def strip_prefix(seg: list[str]) -> list[str]:
    i = 0
    while i < len(seg):
        tok = seg[i]
        if ASSIGNMENT.match(tok) or tok in WRAPPERS:
            i += 1
            continue
        if tok == "timeout":
            i += 1
            while i < len(seg) and (seg[i].startswith("-") or re.match(r"^\d+[smhd]?$", seg[i])):
                i += 1
            continue
        break
    return seg[i:]


def state_change(seg: list[str]) -> str | None:
    seg = strip_prefix(seg)
    if not seg:
        return None
    head = seg[0].rsplit("/", 1)[-1]
    if head == "gh" and seg[1:3] == ["pr", "merge"]:
        return "gh pr merge"
    if head != "git":
        return None
    j = 1
    while j < len(seg) and seg[j].startswith("-"):
        j += 2 if seg[j] in ("-C", "-c") else 1
    if j < len(seg) and seg[j] in ("merge", "push"):
        return f"git {seg[j]}"
    return None


def check(command: str) -> list[str]:
    segs = segments(tokenize(command))
    if len(segs) < 2:
        return []
    return sorted({hit for seg in segs if (hit := state_change(seg))})


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
    hits = check(command)
    if not hits:
        return 0
    message = (
        f"[git-chain-guard] {' / '.join(hits)} が他のコマンドと連結されています（&& ; | など）。"
        "agents-common / ADR-0057 のとおり、merge / push は単独のコマンドとして実行し、"
        "結果確認（gh pr view、git log など）は後続の別コマンドで行ってください。"
        "連結すると permission の allow ルールが一致せず、auto mode の classifier に止められます。"
        "`cd <dir> &&` の代わりに `git -C <dir>` や `--repo <owner>/<repo>` を使ってください。"
    )
    print(message, file=sys.stderr)
    print(json.dumps({
        "systemMessage": message,
        "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": message},
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
