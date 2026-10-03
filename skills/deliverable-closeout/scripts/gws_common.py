"""Shared helpers for deliverable-closeout scripts. Standard library only.

Google Drive is reached only through ``gws-account <profile> drive ...`` (never bare ``gws``),
so the account boundary is explicit on every call.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

T0 = time.time()
FOLDER_MIME = "application/vnd.google-apps.folder"
OFFICE_MIMES = {
    ".pdf": "application/pdf",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S} +{time.time() - T0:6.1f}s] {msg}", flush=True)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def gws(profile: str, args: list[str], cwd: str | None = None, retries: int = 3, timeout: int = 300) -> dict:
    """Run gws-account and parse the JSON object on stdout. Retries are logged; the last error is raised."""
    last = ""
    for attempt in range(1, retries + 1):
        r = subprocess.run(["gws-account", profile, *args], capture_output=True, text=True, timeout=timeout, cwd=cwd)
        start = r.stdout.find("{")
        if r.returncode == 0 and start >= 0:
            return json.loads(r.stdout[start:])
        last = (r.stderr.strip() or r.stdout.strip())[-300:]
        log(f"retry profile={profile} op={' '.join(args[:3])} attempt={attempt}/{retries} rc={r.returncode} err={last!r}")
        if attempt < retries:
            time.sleep(3 * attempt)
    raise RuntimeError(f"gws-account {profile} {' '.join(args[:3])} failed: {last}")


def q_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def md5(path: str | Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, doc: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
