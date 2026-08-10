#!/usr/bin/env python3
"""Claude Code statusline: 現在のコンテキスト量を可視化する。

stdin に渡される Status JSON から transcript_path を読み、直近の assistant
メッセージの usage から現在のコンテキスト長を算出して表示する。

    opus-5 │ ~/Claude │ ctx 168k ⚠ handoff  │ $2.41

コンテキスト量はコスト(ctx × 残ターン数)とレートリミット消費に直結するため、
150k(AGENTS.md の handoff 閾値)を超えたら赤で警告する。
"""
import json
import os
import sys

WARN = 100_000       # 黄: そろそろ意識する
HANDOFF = 150_000    # 赤: AGENTS.md の handoff 閾値
TAIL_BYTES = 512 * 1024

GREEN, YELLOW, RED, DIM, RESET = (
    "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m")


def latest_context(path: str) -> int | None:
    """transcript の末尾から直近の usage を探し、コンテキスト総量を返す。"""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            if size > TAIL_BYTES:
                fh.seek(size - TAIL_BYTES)
                fh.readline()  # 途中で切れた行を捨てる
            lines = fh.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None

    for line in reversed(lines):
        if '"usage"' not in line:
            continue
        try:
            u = (json.loads(line).get("message") or {}).get("usage")
        except json.JSONDecodeError:
            continue
        if not u:
            continue
        return ((u.get("input_tokens") or 0)
                + (u.get("cache_read_input_tokens") or 0)
                + (u.get("cache_creation_input_tokens") or 0))
    return None


def shorten(path: str) -> str:
    home = os.path.expanduser("~")
    return "~" + path[len(home):] if path.startswith(home) else path


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}

    parts = []

    model = (data.get("model") or {}).get("display_name")
    if model:
        parts.append(model)

    cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd")
    if cwd:
        parts.append(f"{DIM}{shorten(cwd)}{RESET}")

    ctx = latest_context(data.get("transcript_path") or "")
    if ctx is not None:
        if ctx >= HANDOFF:
            color, note = RED, " ⚠ handoff"
        elif ctx >= WARN:
            color, note = YELLOW, ""
        else:
            color, note = GREEN, ""
        parts.append(f"{color}ctx {ctx // 1000}k{note}{RESET}")

    usd = (data.get("cost") or {}).get("total_cost_usd")
    if isinstance(usd, (int, float)) and usd > 0:
        parts.append(f"{DIM}${usd:.2f}{RESET}")

    print(f" {DIM}│{RESET} ".join(parts))


if __name__ == "__main__":
    main()
