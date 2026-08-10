#!/usr/bin/env python3
"""UserPromptSubmit hook: handoff 閾値超過時にモデルへ警告を注入する。

statusline (executable_statusline.py) がユーザー向け可視化を担うのに対し、
本 hook はモデル向け enforcement を担う(ADR-0054 補遺)。判定は transcript
末尾の直近 usage 合計という機械的閾値のみで、意味理解は持たない。

UserPromptSubmit ではプレーン stdout (exit 0) がそのままモデルのコンテキスト
へ追加される仕様を利用する。閾値未満なら何も出力しない。
"""
import json
import os
import sys

HANDOFF = int(os.environ.get("CLAUDE_CTX_HANDOFF_THRESHOLD", "150000"))
TAIL_BYTES = 512 * 1024


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


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    ctx = latest_context(data.get("transcript_path") or "")
    if ctx is None or ctx < HANDOFF:
        return
    print(
        f"[context-guard hook] 常駐コンテキストが約 {ctx // 1000}k トークンに達し、"
        "agents-common.md の handoff 閾値 150k を超えている。現在の作業単位を完了させたら、"
        "handoff skill の契約に従い `.context/handoff/` へ引き継ぎ artifact を書き、"
        "ユーザーへ新セッションへの切替を提案すること。"
        "このセッションで新しい大きな作業を開始しないこと。"
    )


if __name__ == "__main__":
    main()
