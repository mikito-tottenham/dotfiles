#!/usr/bin/env python3
"""提案資料の書き出しに使うツールの有無を確認する（読み取り専用）。

確認するもの: pandoc / soffice（LibreOffice）/ marp（起動できるか）/ Chromium 系ブラウザ /
poppler（pdftoppm・pdffonts）/ Python の pypdf・python-pptx / markitdown / 日本語フォント。
不足していてもインストールはしない。導入コマンドの候補を表示するだけ。
Python モジュールは実行した interpreter で確認する。venv を使う repo では `.venv/bin/python3` で実行する。
marp は cwd の `node_modules/.bin/marp` を PATH より優先するので、repo ルートで実行する。

usage: preflight_doc_toolchain.py [--route marp,pptx,pdf,inspect] [--json-out <path>]
  route marp   : Marp で HTML / PDF / PPTX を書き出す
  route pptx   : PPTX を作る・PDF 化して検品する
  route pdf    : Markdown / HTML から PDF を作る
  route inspect: 書き出した PDF / PPTX の検品
exit code: 0 = 指定 route がすべて使える / 1 = 使えない route がある / 2 = 使い方エラー
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

T0 = time.monotonic()
IS_MAC = sys.platform == "darwin"
ROUTES = ("marp", "pptx", "pdf", "inspect")
ROUTE_KEYS = {
    "marp": {"marp", "browser", "jp-font"},
    "pptx": {"python-pptx", "marp", "browser", "soffice", "jp-font"},
    "pdf": {"pandoc", "browser", "jp-font"},
    "inspect": {"poppler", "pypdf", "markitdown"},
}

HINTS = {
    "pandoc": ("brew install pandoc", "sudo apt-get install -y pandoc"),
    "soffice": ("brew install --cask libreoffice", "sudo apt-get install -y libreoffice-impress"),
    "marp": ("npm i -g @marp-team/marp-cli（または repo の devDependencies で npx marp）", "npm i -g @marp-team/marp-cli"),
    "browser": ("Google Chrome / Microsoft Edge を入れるか、CHROME_PATH にブラウザ実行ファイルを指定", "sudo apt-get install -y chromium"),
    "poppler": ("brew install poppler", "sudo apt-get install -y poppler-utils"),
    "pypdf": ("python3 -m venv .venv && .venv/bin/pip install pypdf（Homebrew の python は PEP 668 で直接の導入を拒否する）",) * 2,
    "python-pptx": (".venv/bin/pip install python-pptx",) * 2,
    "markitdown": (".venv/bin/pip install 'markitdown[pptx]'",) * 2,
    "jp-font": ("macOS 標準のヒラギノで足りる。追加するなら brew install --cask font-noto-sans-cjk-jp",
                "sudo apt-get install -y fonts-noto-cjk（または fonts-ipaexfont）"),
}

found: dict[str, dict] = {}


def log(msg: str) -> None:
    print(f"[{time.monotonic() - T0:5.1f}s] {msg}", flush=True)


def hint(key: str) -> str:
    mac, other = HINTS[key]
    return mac if IS_MAC else other


def note(key: str, ok: bool, detail: str) -> None:
    found[key] = {"ok": ok, "detail": detail, "install_hint": "" if ok else hint(key)}
    log(f"{'OK  ' if ok else 'MISS'} {key}: {detail}")


def version(cmd: list[str], timeout: int = 20) -> tuple[bool, str]:
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except (FileNotFoundError, PermissionError):
        return False, "見つからない"
    except subprocess.TimeoutExpired:
        return False, f"{timeout} 秒で応答しない"
    text = (cp.stdout or cp.stderr).strip().splitlines()
    first = text[0][:100] if text else ""
    if cp.returncode != 0:
        last = text[-1][:120] if text else ""
        return False, f"起動に失敗 rc={cp.returncode}: {last}"
    return True, first


def which_any(names: list[str], paths: list[str]) -> str:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    for p in paths:
        if Path(p).exists():
            return p
    return ""


def check_commands() -> None:
    p = shutil.which("pandoc")
    note("pandoc", bool(p), version([p, "--version"])[1] if p else "見つからない")

    p = which_any(["soffice", "libreoffice"], ["/Applications/LibreOffice.app/Contents/MacOS/soffice"])
    if p:
        ok, d = version([p, "--version"], 40)
        note("soffice", ok, f"{p}: {d}")
    else:
        note("soffice", False, "見つからない")

    local_marp = Path.cwd() / "node_modules/.bin/marp"
    p = str(local_marp) if local_marp.exists() else shutil.which("marp")
    if p:
        ok, d = version([p, "--version"])
        note("marp", ok, f"{p}: {d}")
    else:
        note("marp", False, "見つからない（repo の node_modules/.bin と PATH を確認）")

    env_path = os.environ.get("CHROME_PATH", "")
    candidates = [env_path] if env_path else []
    if IS_MAC:
        candidates += [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
    p = which_any(["google-chrome", "chromium", "chromium-browser", "microsoft-edge"], [c for c in candidates if c])
    detail = p or "見つからない"
    if p and "Brave" in p and not env_path:
        detail += "（Marp は自動検出しないため CHROME_PATH に指定する）"
    note("browser", bool(p), detail)

    p1, p2 = shutil.which("pdftoppm"), shutil.which("pdffonts")
    note("poppler", bool(p1 and p2), f"pdftoppm={'あり' if p1 else 'なし'} pdffonts={'あり' if p2 else 'なし'}")

    if IS_MAC:
        keynote = Path("/Applications/Keynote.app").exists()
        log(f"INFO keynote: {'あり（PPTX の描画確認に使える）' if keynote else 'なし'}")
        found["keynote"] = {"ok": keynote, "detail": "optional", "install_hint": ""}


def check_python() -> None:
    for key, mod in (("pypdf", "pypdf"), ("python-pptx", "pptx"), ("markitdown", "markitdown")):
        spec = importlib.util.find_spec(mod)
        cli = shutil.which(key) if key == "markitdown" else None
        ok = bool(spec or cli)
        note(key, ok, f"{sys.executable} で import {'可' if spec else '不可'}" + (f"、CLI {cli}" if cli else ""))


def check_fonts() -> None:
    families: set[str] = set()
    fc = shutil.which("fc-list")
    if fc:
        try:
            cp = subprocess.run([fc, ":lang=ja", "family"], capture_output=True, text=True, timeout=30)
            for line in cp.stdout.splitlines():
                name = line.split(",")[0].strip()
                if name and not name.startswith("."):
                    families.add(name)
        except subprocess.TimeoutExpired:
            log("WARN fc-list が 30 秒で応答しない")
    if IS_MAC and not families:
        for d in ("/System/Library/Fonts", "/Library/Fonts", str(Path.home() / "Library/Fonts")):
            for f in Path(d).glob("*"):
                if any(k in f.name for k in ("ヒラギノ", "Hiragino", "NotoSansCJK", "NotoSansJP", "IPAex", "BIZUD")):
                    families.add(f.stem)
    preferred = [f for f in sorted(families) if any(k in f for k in ("Hiragino", "ヒラギノ", "Noto Sans CJK JP", "Noto Sans JP", "IPAex", "BIZ UD"))]
    note("jp-font", bool(families),
         f"日本語対応 {len(families)} 種。推奨候補: {', '.join(preferred[:4]) or 'なし'}")


def route_status() -> dict[str, tuple[bool, list[str]]]:
    def ok(k: str) -> bool:
        return found.get(k, {}).get("ok", False)

    return {
        "marp": (ok("marp") and ok("browser") and ok("jp-font"), ["marp", "browser", "jp-font"]),
        "pptx": ((ok("python-pptx") or (ok("marp") and ok("browser"))) and (ok("soffice") or ok("keynote")) and ok("jp-font"),
                 ["python-pptx か marp+browser", "soffice か keynote", "jp-font"]),
        "pdf": (ok("pandoc") and (ok("browser") or bool(shutil.which("wkhtmltopdf"))) and ok("jp-font"),
                ["pandoc", "browser か wkhtmltopdf", "jp-font"]),
        "inspect": (ok("poppler") and ok("pypdf"), ["poppler", "pypdf", "（PPTX 本文照合は markitdown）"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--route", default=",".join(ROUTES), help="確認する route（カンマ区切り）")
    ap.add_argument("--json-out", help="結果 JSON の保存先（.context/ 配下を推奨）")
    args = ap.parse_args()
    routes = [r.strip() for r in args.route.split(",") if r.strip()]
    bad = [r for r in routes if r not in ROUTES]
    if bad:
        print(f"unknown route: {', '.join(bad)}", file=sys.stderr)
        return 2

    log(f"start os={platform.system()} python={sys.executable} cwd={Path.cwd()} routes={','.join(routes)}")
    log("step 1/3 commands")
    check_commands()
    log("step 2/3 python modules")
    check_python()
    log("step 3/3 japanese fonts")
    check_fonts()

    status = route_status()
    print("\n== route ==")
    failed = []
    for r in routes:
        usable, needs = status[r]
        print(f"{'OK  ' if usable else 'NG  '} {r}: 必要 = {' / '.join(needs)}")
        if not usable:
            failed.append(r)
    relevant = set().union(*(ROUTE_KEYS[r] for r in routes))
    missing = [k for k, v in found.items() if not v["ok"] and v["install_hint"] and k in relevant]
    if missing:
        print("\n== 不足しているもの（自動インストールはしない。必要なものだけユーザーに確認して導入する） ==")
        for k in missing:
            print(f"- {k}: {found[k]['detail']}\n    導入例: {found[k]['install_hint']}")
    log(f"done usable={len(routes) - len(failed)}/{len(routes)}")

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"tools": found, "routes": {r: status[r][0] for r in routes}},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"wrote {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
