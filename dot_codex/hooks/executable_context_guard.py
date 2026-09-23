#!/usr/bin/env python3
"""UserPromptSubmit hook: handoff 閾値超過時にモデルへ警告を注入する。

Codex の transcript_path 末尾にある直近 usage を機械的に確認する。
transcript 形式は安定 API ではないため、解釈できない場合は何も出力しない。
"""
import json
import os
import sys

HANDOFF = int(os.environ.get("CODEX_CTX_HANDOFF_THRESHOLD", "150000"))
TAIL_BYTES = 512 * 1024


def latest_context(path: str) -> int | None:
    """transcript の末尾から直近の usage を探し、コンテキスト総量を返す。"""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            if size > TAIL_BYTES:
                fh.seek(size - TAIL_BYTES)
                fh.readline()
            lines = fh.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None

    for line in reversed(lines):
        if '"usage"' not in line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        candidates = [record, record.get("payload") or {}, record.get("message") or {}]
        for candidate in candidates:
            usage = candidate.get("usage") if isinstance(candidate, dict) else None
            if not usage:
                continue
            return sum(
                usage.get(key) or 0
                for key in (
                    "input_tokens",
                    "cached_input_tokens",
                    "cache_read_input_tokens",
                    "cache_creation_input_tokens",
                )
            )
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    context = latest_context(data.get("transcript_path") or "")
    if context is None or context < HANDOFF:
        return
    print(
        f"[context-guard hook] 常駐コンテキストが約 {context // 1000}k トークンに達し、"
        "handoff 閾値 150k を超えている。現在の作業単位を完了させたら、"
        "handoff skill の契約に従い `.context/handoff/` へ引き継ぎ artifact を書き、"
        "ユーザーへ新セッションへの切替を提案すること。"
        "このセッションで新しい大きな作業を開始しないこと。"
    )


if __name__ == "__main__":
    main()
