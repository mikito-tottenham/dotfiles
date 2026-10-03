#!/usr/bin/env python3
"""extract_pdf.py — pdf-extract skill の Codex 経路。

入口:
  --pdf <path>                 対象 PDF（repo ルート配下）
  --prompt-id <id> | --prompt-text <text>
  --out <path>                 出力先（省略時はミラーパス）
  --tier S|A|B|C               model registry の tier（既定 B）
  --model / --effort           registry を使わず明示指定する場合
  --registry <path>            model_registry.yaml（省略時は兄弟 skill agent-orchestrator）
  --repo-root <dir>            省略時は cwd の git top-level、git 管理外なら cwd
  --prompts-dir <dir>          repo 側テンプレートの置き場
  --service-tier fast|priority 指定したときだけ Codex に渡す
  --force                      cache を無視して再生成

出口:
  artifact: <repo>/.context/pdf-extract/<PDF の repo 相対パス>.ocr.md
  run dir : <repo>/.context/pdf-extract/runs/<PDF 名>-<sha8>/（codex-cli-runner の artifact）
  stdout  : 結果サマリ JSON
  stderr  : 進捗ログ
  exit    : 0 成功 / 1 Codex 実行失敗 / 2 入力・registry・runner の不備 / 127 codex 不在

モデル名はこのファイルに書かない。registry の tiers.<tier>.codex から解決する。
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SKILLS_ROOT = SKILL_DIR.parent
DEFAULT_REGISTRY = SKILLS_ROOT / "agent-orchestrator" / "rules" / "model_registry.yaml"
RUNNER = SKILLS_ROOT / "codex-cli-runner" / "scripts" / "run_codex_cli.py"
JST = dt.timezone(dt.timedelta(hours=9))
STARTED = time.monotonic()


def log(msg: str) -> None:
    print(f"[pdf-extract +{time.monotonic() - STARTED:6.1f}s] {msg}", file=sys.stderr, flush=True)


def fail(msg: str, code: int) -> None:
    log(f"FAILED (exit {code}): {msg}")
    print(json.dumps({"status": "error", "message": msg}, ensure_ascii=False))
    sys.exit(code)


def resolve_repo_root(explicit: Path | None) -> Path:
    if explicit:
        return explicit.resolve()
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip()).resolve()
    return Path.cwd().resolve()


def resolve_from_registry(registry: Path, tier: str) -> tuple[str, str | None]:
    """tiers.<tier>.codex の model / effort を返す。解決できなければ exit 2。"""
    if not registry.is_file():
        fail(f"model registry not found: {registry} (install agent-orchestrator or pass --registry / --model)", 2)
    text = registry.read_text(encoding="utf-8")
    tiers = re.search(r"^tiers:\s*\n(.*?)(?=^\S)", text, re.S | re.M)
    if not tiers:
        fail(f"'tiers:' block not found in {registry}", 2)
    block = re.search(rf"^  {re.escape(tier)}:\s*\n(.*?)(?=^  \S|\Z)", tiers.group(1), re.S | re.M)
    if not block:
        fail(f"tier {tier} not found in {registry}", 2)
    codex = re.search(r"^\s+codex:\s*\{([^}]*)\}", block.group(1), re.M)
    if not codex:
        fail(f"tiers.{tier}.codex not found in {registry}", 2)
    fields = dict(
        (k.strip(), v.strip())
        for k, v in (part.split(":", 1) for part in codex.group(1).split(",") if ":" in part)
    )
    model = fields.get("model")
    if not model:
        fail(f"tiers.{tier}.codex.model is empty in {registry}", 2)
    return model, fields.get("effort") or None


def find_prompt(prompt_id: str, repo_root: Path, prompts_dir: Path | None) -> Path:
    candidates = []
    if prompts_dir:
        candidates.append(prompts_dir)
    candidates += [
        repo_root / ".claude" / "skills" / "pdf-extract" / "prompts",
        repo_root / ".agents" / "skills" / "pdf-extract" / "prompts",
        SKILL_DIR / "prompts",
    ]
    for base in candidates:
        path = base / f"{prompt_id}.md"
        if path.is_file():
            return path
    fail(f"prompt-id not found: {prompt_id} (searched: {', '.join(str(c) for c in candidates)})", 2)
    raise AssertionError  # unreachable


def read_existing_cache_key(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    for line in text[3:end].splitlines():
        line = line.strip()
        if line.startswith("cache_key:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return None


def render_frontmatter(meta: dict) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if v is None:
            lines.append(f"{k}: null")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        else:
            s = str(v)
            if ":" in s or "\n" in s or s.startswith(("[", "{")):
                s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                lines.append(f'{k}: "{s}"')
            else:
                lines.append(f"{k}: {s}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def build_prompt(pdf_path: Path, prompt_body: str, body_path: Path) -> str:
    return f"""# Task

Read the PDF below and write the Markdown body requested by the instructions.

- PDF: {pdf_path}
- Write the Markdown body only (no YAML frontmatter) to: {body_path}
- The calling script adds the frontmatter afterwards.
- Keep page images or text dumps out of the repository tree outside this run directory.

# Instructions

{prompt_body}
"""


def main() -> int:
    p = argparse.ArgumentParser(description="pdf-extract: Codex backend via codex-cli-runner")
    p.add_argument("--pdf", required=True, type=Path)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--prompt-id")
    g.add_argument("--prompt-text")
    p.add_argument("--out", type=Path)
    p.add_argument("--tier", default="B", choices=["S", "A", "B", "C"])
    p.add_argument("--model", help="explicit Codex model; skips registry resolution")
    p.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max", "ultra"])
    p.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    p.add_argument("--repo-root", type=Path)
    p.add_argument("--prompts-dir", type=Path)
    p.add_argument("--service-tier", choices=["fast", "priority"])
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    log("start")
    if shutil.which("codex") is None:
        log("codex CLI not found on PATH; caller may switch to the Claude path (references/claude-path.md)")
        print(json.dumps({
            "status": "fallback_required",
            "reason": "codex_not_found",
            "claude_path_doc": str(SKILL_DIR / "references" / "claude-path.md"),
        }, ensure_ascii=False))
        return 127
    if not RUNNER.is_file():
        fail(f"codex-cli-runner not found: {RUNNER} (install the codex-cli-runner skill)", 2)

    repo_root = resolve_repo_root(args.repo_root)
    pdf_path = args.pdf.resolve()
    if not pdf_path.is_file():
        fail(f"pdf not found: {pdf_path}", 2)
    try:
        pdf_rel = pdf_path.relative_to(repo_root)
    except ValueError:
        fail(f"pdf is outside repo root: {pdf_path} (repo root: {repo_root})", 2)
    artifact_path = (args.out or repo_root / ".context" / "pdf-extract" / pdf_rel.with_suffix(".ocr.md")).resolve()
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    log(f"repo_root={repo_root} pdf={pdf_rel}")

    if args.prompt_id:
        prompt_file = find_prompt(args.prompt_id, repo_root, args.prompts_dir)
        prompt_body = prompt_file.read_text(encoding="utf-8")
        prompt_id = args.prompt_id
        log(f"prompt template: {prompt_file}")
    else:
        prompt_body = args.prompt_text
        prompt_id = "inline"
        log("prompt: inline text")

    if args.model:
        model, effort, tier = args.model, args.effort, None
        log(f"model: explicit {model} effort={effort}")
    else:
        model, effort = resolve_from_registry(args.registry.resolve(), args.tier)
        if args.effort:
            effort = args.effort
        tier = args.tier
        log(f"model: registry tier {tier} -> {model} effort={effort}")

    pdf_bytes = pdf_path.read_bytes()
    pdf_sha = hashlib.sha256(pdf_bytes).hexdigest()
    cache_key = f"{pdf_sha[:16]}_{prompt_id}_codex_{model}_{effort}"

    if not args.force and read_existing_cache_key(artifact_path) == cache_key:
        log("cache hit; skip regeneration")
        print(json.dumps({
            "status": "success", "extraction_backend": "codex",
            "artifact_path": str(artifact_path), "cache_key": cache_key, "cache_hit": True,
        }, ensure_ascii=False))
        return 0

    run_dir = repo_root / ".context" / "pdf-extract" / "runs" / f"{pdf_path.stem}-{pdf_sha[:8]}"
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = run_dir / "prompt.md"
    body_path = run_dir / "body.md"  # Codex には本文だけを run dir へ書かせ、既存 artifact は成功時にだけ置き換える
    if body_path.exists():
        body_path.unlink()
    prompt_path.write_text(build_prompt(pdf_path, prompt_body, body_path), encoding="utf-8")

    cmd = [
        sys.executable, str(RUNNER),
        "--prompt-file", str(prompt_path),
        "--output-dir", str(run_dir),
        "--expected-artifact", str(body_path),
        "--cwd", str(repo_root),
        "--model", model,
        "--extra-codex-arg=--skip-git-repo-check",
    ]
    if effort:
        cmd += ["--effort", effort]
    if args.service_tier:
        cmd += ["--extra-codex-arg=-c", f"--extra-codex-arg=service_tier={args.service_tier}"]
    log(f"codex run start (run dir: {run_dir})")
    rc = subprocess.run(cmd).returncode
    log(f"codex run end (runner exit {rc})")
    if rc != 0:
        fail(f"codex-cli-runner failed (exit {rc}); see {run_dir / 'summary.json'} and {run_dir / 'failure.md'}", 1)
    if not body_path.is_file():
        fail(f"codex did not write the body: {body_path}", 1)

    body = body_path.read_text(encoding="utf-8")
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end >= 0:
            body = body[end + 4:].lstrip("\n")
    confidence = "medium"
    m = re.search(r"confidence_overall\s*[:：]\s*`?(high|medium|low)", body, re.I)
    if m:
        confidence = m.group(1).lower()

    fm = render_frontmatter({
        "source_pdf": str(pdf_rel),
        "extraction_backend": "codex",
        "backend_model": model,
        "backend_effort": effort,
        "backend_tier": tier,
        "prompt_id": prompt_id,
        "prompt_text_inline": bool(args.prompt_text),
        "generated_at": dt.datetime.now(JST).isoformat(timespec="seconds"),
        "cache_key": cache_key,
        "confidence_overall": confidence,
        "pdf_size_bytes": len(pdf_bytes),
        "pdf_sha256": pdf_sha,
        "prompt_sha256": hashlib.sha256(prompt_body.encode("utf-8")).hexdigest(),
    })
    artifact_path.write_text(fm + body.lstrip("\n"), encoding="utf-8")
    log(f"done: {artifact_path}")
    print(json.dumps({
        "status": "success", "extraction_backend": "codex",
        "artifact_path": str(artifact_path), "cache_key": cache_key, "cache_hit": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
