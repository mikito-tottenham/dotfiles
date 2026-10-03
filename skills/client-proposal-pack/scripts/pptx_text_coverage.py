#!/usr/bin/env python3
"""原稿 Markdown の本文が、PPTX から書き出したテキストにすべて含まれるかを照合する（読み取り専用）。

usage: pptx_text_coverage.py <原稿.md> <pptx のテキスト.md> [--section '## 本文']
  <pptx のテキスト.md> は `markitdown deck.pptx > .context/<task>/deck.md` などで作る。
  --section を指定すると、原稿のその見出し以降だけを照合する（既定は全文。Front Matter は除く）。

空白を除いた文字列で照合し、長い文は句点で分けて照合する。見出し番号と本文が別テキストボックスに
分かれる箇所は MISSING と出ることがあるので、内容の欠落だけを見る。
exit code: 0 = MISSING なし / 1 = MISSING あり / 2 = 使い方エラー

取り込み元: taskell-management repo の bin/pptx-text-coverage.py（旧 owner 側 checkout）。
"""
import argparse
import re
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="原稿 Markdown")
    ap.add_argument("deck_text", help="PPTX から書き出したテキスト")
    ap.add_argument("--section", help="照合を始める見出し行（例: '## 本文'）")
    a = ap.parse_args()

    src = Path(a.source).read_text(encoding="utf-8")
    src = re.sub(r"\A---\n.*?\n---\n", "", src, flags=re.S)
    if a.section:
        if a.section not in src:
            print(f"section not found: {a.section}", file=sys.stderr)
            return 2
        src = src.split(a.section, 1)[1]
    deck = re.sub(r"\s+", "", Path(a.deck_text).read_text(encoding="utf-8"))

    checked = missing = 0
    for line in src.splitlines():
        t = line.strip()
        if not t or t == "---" or t.startswith("|---") or t.startswith("<!--"):
            continue
        t = re.sub(r"^(#{1,6}\s+|[-*]\s+|\d+\.\s+|>\s*)", "", t)
        cells = [c for c in t.split("|")] if t.startswith("|") else [t]
        for cell in cells:
            c = re.sub(r"\*\*|`", "", cell)
            c = re.sub(r"\s+", "", c)
            if len(c) < 2:
                continue
            for part in [p for p in re.split(r"(?<=。)", c) if p]:
                checked += 1
                if part not in deck:
                    missing += 1
                    print("MISSING:", part[:80])
    print(f"[done] checked={checked} missing={missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
