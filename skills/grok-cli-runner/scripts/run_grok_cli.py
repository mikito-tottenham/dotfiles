#!/usr/bin/env python3
"""Run a Grok handoff with request/response artifacts and failure summaries."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_BASE_URL = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-4.3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a Grok request artifact through the current xAI Responses API backend."
    )
    parser.add_argument("--request-file", required=True, help="Path to .context/<task>/grok-request.json.")
    parser.add_argument("--output-dir", required=True, help="Directory for run artifacts.")
    parser.add_argument(
        "--response-artifact",
        default="grok-response.json",
        help="Response artifact path. Relative paths resolve from --output-dir.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="xAI model override. Omit to use request.model, GROK_MODEL, GROK_X_RESEARCH_MODEL, or default.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("XAI_BASE_URL", DEFAULT_BASE_URL),
        help="xAI API base URL. Defaults to XAI_BASE_URL or https://api.x.ai/v1.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=600, help="Process timeout in seconds. Defaults to 600.")
    parser.add_argument(
        "--http-timeout-seconds",
        type=int,
        default=None,
        help="HTTP request timeout. Defaults to --timeout-seconds.",
    )
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory for the backend process.")
    parser.add_argument(
        "--timeout-bin",
        default=None,
        help="Timeout binary. Defaults to timeout, then gtimeout.",
    )
    parser.add_argument(
        "--backend-script",
        default=None,
        help="Backend script to execute in a subprocess. Omit to use this script's built-in xAI backend.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and record the outbound payload without calling the API.",
    )
    parser.add_argument(
        "--confirm-api-cost",
        action="store_true",
        help="Confirm the user explicitly approved a real xAI API call that may incur cost. Required unless --dry-run.",
    )
    return parser.parse_args()


def resolve_timeout_bin(explicit: str | None) -> str:
    if explicit:
        return explicit
    for candidate in ("timeout", "gtimeout"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise SystemExit("No timeout binary found. Install GNU coreutils or pass --timeout-bin.")


def artifact_path(raw: str, output_dir: Path) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = output_dir / path
    return path.resolve()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"request artifact not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"request artifact is not valid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("request artifact must be a JSON object")
    return value


def require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"request artifact must include non-empty string '{key}'")
    return value.strip()


def resolve_model(request_data: dict[str, Any], override: str | None) -> str:
    request_obj = request_data.get("request")
    if isinstance(request_obj, dict) and isinstance(request_obj.get("model"), str) and request_obj["model"].strip():
        return request_obj["model"].strip()
    return override or os.getenv("GROK_MODEL") or os.getenv("GROK_X_RESEARCH_MODEL") or DEFAULT_MODEL


def load_request_payload(data: dict[str, Any], *, model: str) -> dict[str, Any]:
    require_string(data, "task")
    request_data = data.get("request")
    if not isinstance(request_data, dict):
        raise ValueError("request artifact must include object 'request'")
    payload = dict(request_data)
    payload.setdefault("model", model)
    if "input" not in payload:
        raise ValueError("request.request must include 'input'")
    if "instructions" in payload:
        raise ValueError("request.request must not include 'instructions'; xAI Responses API does not support it")
    return payload


def api_key() -> str:
    value = os.getenv("XAI_API_KEY")
    if not value:
        raise RuntimeError("XAI_API_KEY is required. Premium+ access does not provide API access for this script.")
    return value


def post_json(url: str, payload: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    encoded = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=encoded,
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"xAI API request failed with HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"xAI API request failed: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("xAI API response was not a JSON object")
    return value


def extract_output_text(response: dict[str, Any]) -> str | None:
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    for item in response.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    return text
    return None


def build_response_artifact(
    request_artifact: dict[str, Any], payload: dict[str, Any], response: dict[str, Any]
) -> dict[str, Any]:
    return {
        "task": require_string(request_artifact, "task"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "meta": request_artifact.get("meta"),
        "request": payload,
        "response": response,
        "output_text": extract_output_text(response) if response else None,
        "response_id": response.get("id"),
        "model": response.get("model") or payload.get("model"),
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)[:4000]


def run_backend_subprocess(args: argparse.Namespace, timeout_bin: str, response_path: Path, stderr_path: Path) -> int:
    command = [
        timeout_bin,
        str(args.timeout_seconds),
        args.backend_script,
        "--request",
        str(Path(args.request_file).expanduser().resolve()),
        "--response",
        str(response_path),
        "--model",
        args.model or os.getenv("GROK_MODEL") or os.getenv("GROK_X_RESEARCH_MODEL") or DEFAULT_MODEL,
        "--base-url",
        args.base_url,
        "--timeout",
        str(args.http_timeout_seconds or args.timeout_seconds),
    ]
    if args.dry_run:
        command.append("--dry-run")
    if args.confirm_api_cost:
        command.append("--confirm-api-cost")
    with stderr_path.open("wb") as stderr_fh:
        proc = subprocess.run(command, cwd=str(Path(args.cwd).expanduser().resolve()), stderr=stderr_fh, check=False)
    return proc.returncode


def write_failure(path: Path, summary: dict[str, Any]) -> None:
    reasons = summary.get("failure_reasons", [])
    api_error = summary.get("api_error") or {}
    body = [
        "# Grok CLI Runner Failure",
        "",
        f"- Command: `{' '.join(summary['command'])}`",
        f"- Exit code: `{summary['exit_code']}`",
        f"- Elapsed seconds: `{summary['elapsed_seconds']}`",
        f"- Request bytes: `{summary['request_bytes']}`",
        f"- Response bytes: `{summary['response_bytes']}`",
        f"- Stderr bytes: `{summary['stderr_bytes']}`",
        f"- Failure reasons: {', '.join(reasons) if reasons else 'unknown'}",
        "",
        "## API Or Validation Error",
        "",
        "```json",
        compact_json(api_error),
        "```",
        "",
        "## Recommended Next Action",
        "",
        summary.get("recommended_next_action", "Inspect artifacts and rerun with adjusted request or environment."),
        "",
    ]
    path.write_text("\n".join(body), encoding="utf-8")


def main() -> int:
    args = parse_args()
    request_path = Path(args.request_file).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    response_path = artifact_path(args.response_artifact, output_dir)
    stderr_path = output_dir / "run.err"
    summary_path = output_dir / "summary.json"
    failure_path = output_dir / "failure.md"
    output_dir.mkdir(parents=True, exist_ok=True)

    timeout_bin = resolve_timeout_bin(args.timeout_bin)
    command = [
        timeout_bin,
        str(args.timeout_seconds),
        sys.executable,
        str(Path(__file__).resolve()),
        "--request-file",
        str(request_path),
        "--output-dir",
        str(output_dir),
        "--response-artifact",
        str(response_path),
    ]
    if args.model:
        command.extend(["--model", args.model])
    if args.dry_run:
        command.append("--dry-run")

    start = time.monotonic()
    failure_reasons: list[str] = []
    api_error: dict[str, Any] | None = None
    dry_run_payload: dict[str, Any] | None = None
    exit_code = 0
    model_used = args.model or os.getenv("GROK_MODEL") or os.getenv("GROK_X_RESEARCH_MODEL") or DEFAULT_MODEL

    try:
        request_data = load_json(request_path)
        model = resolve_model(request_data, args.model)
        model_used = model
        payload = load_request_payload(request_data, model=model)
        if args.dry_run:
            dry_run_payload = payload
            stderr_path.write_text("", encoding="utf-8")
        elif not args.confirm_api_cost:
            raise RuntimeError(
                "Real Grok API calls may incur xAI API cost. Ask the user for explicit approval, "
                "then rerun with --confirm-api-cost. Use --dry-run for no-cost validation."
            )
        elif args.backend_script:
            exit_code = run_backend_subprocess(args, timeout_bin, response_path, stderr_path)
        else:
            stderr_path.write_text("", encoding="utf-8")
            response = post_json(
                f"{args.base_url.rstrip('/')}/responses",
                payload,
                timeout=args.http_timeout_seconds or args.timeout_seconds,
            )
            artifact = build_response_artifact(request_data, payload, response)
            write_json(response_path, artifact)
    except Exception as exc:  # noqa: BLE001 - convert all local/API failures to artifacts
        exit_code = 1
        api_error = {"type": exc.__class__.__name__, "message": str(exc)}

    elapsed = round(time.monotonic() - start, 3)
    request_bytes = request_path.stat().st_size if request_path.exists() else 0
    response_non_empty = response_path.exists() and response_path.is_file() and response_path.stat().st_size > 0
    response_bytes = response_path.stat().st_size if response_path.exists() and response_path.is_file() else 0
    stderr_bytes = stderr_path.stat().st_size if stderr_path.exists() else 0

    if exit_code == 124:
        failure_reasons.append("timeout")
    elif exit_code != 0:
        failure_reasons.append("nonzero_exit")
    if api_error:
        message = api_error.get("message", "")
        if "XAI_API_KEY" in message:
            failure_reasons.append("missing_api_key")
        elif "--confirm-api-cost" in message:
            failure_reasons.append("api_cost_not_confirmed")
        elif "input" in message or "request artifact" in message or "instructions" in message:
            failure_reasons.append("invalid_request")
        else:
            failure_reasons.append("api_or_backend_error")
    if not args.dry_run and not response_non_empty and "api_cost_not_confirmed" not in failure_reasons:
        failure_reasons.append("missing_response_artifact")

    if "timeout" in failure_reasons:
        recommended = "Inspect request size and backend status, then rerun with a smaller request or larger timeout."
    elif "api_cost_not_confirmed" in failure_reasons:
        recommended = "Ask the user to approve the possible xAI API cost, then rerun with --confirm-api-cost; use --dry-run for no-cost validation."
    elif "missing_api_key" in failure_reasons:
        recommended = "Set XAI_API_KEY for real Grok API calls, or use --dry-run for request validation only."
    elif "invalid_request" in failure_reasons:
        recommended = "Fix grok-request.json against references/schema.md, then rerun with --dry-run before a real call."
    elif "missing_response_artifact" in failure_reasons:
        recommended = "Inspect run.err and API/backend output, then rerun after fixing environment, model, quota, or request shape."
    else:
        recommended = "Inspect summary.json and grok-response.json, then integrate the response in the caller."

    summary = {
        "command": command,
        "cwd": str(Path(args.cwd).expanduser().resolve()),
        "request_file": str(request_path),
        "response_artifact": str(response_path),
        "output_dir": str(output_dir),
        "model": model_used,
        "base_url": args.base_url,
        "dry_run": args.dry_run,
        "api_cost_confirmed": args.confirm_api_cost,
        "dry_run_payload": dry_run_payload,
        "exit_code": exit_code,
        "elapsed_seconds": elapsed,
        "request_bytes": request_bytes,
        "response_bytes": response_bytes,
        "stderr_bytes": stderr_bytes,
        "response_non_empty": response_non_empty,
        "api_error": api_error,
        "success": not failure_reasons,
        "failure_reasons": failure_reasons,
        "recommended_next_action": recommended,
    }
    write_json(summary_path, summary)

    if failure_reasons:
        write_failure(failure_path, summary)
        return 1
    if failure_path.exists():
        failure_path.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
