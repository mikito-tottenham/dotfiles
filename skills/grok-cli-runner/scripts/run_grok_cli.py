#!/usr/bin/env python3
"""Run a Grok handoff with request/response artifacts and failure summaries."""

from __future__ import annotations

import argparse
import json
import os
import re
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
X_URL_RE = re.compile(
    r"https?://(?:www\.|mobile\.)?(?:x\.com|twitter\.com)/[^\s<>()\"']+|"
    r"https?://nitter\.[^\s/]+/[^\s<>()\"']+",
    re.IGNORECASE,
)
HERMES_SITE_PACKAGES = "/opt/homebrew/Cellar/hermes-agent/2026.5.16/libexec/lib/python3.14/site-packages"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a Grok request artifact through Hermes/SuperGrok OAuth or explicit xAI Responses API."
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
        help="Model override. Omit to use request.model, GROK_MODEL, GROK_X_RESEARCH_MODEL, or default.",
    )
    parser.add_argument(
        "--backend",
        choices=("xai-api", "hermes"),
        default=os.getenv("GROK_BACKEND", "hermes"),
        help="Backend to use for real calls. Defaults to GROK_BACKEND or hermes.",
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
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--confirm-hermes-quota",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--hermes-bin",
        default=os.getenv("HERMES_BIN", "hermes"),
        help="Hermes executable for --backend hermes. Defaults to HERMES_BIN or hermes.",
    )
    parser.add_argument(
        "--hermes-provider",
        default=os.getenv("HERMES_PROVIDER", "xai-oauth"),
        help="Hermes provider for --backend hermes. Defaults to HERMES_PROVIDER or xai-oauth.",
    )
    parser.add_argument(
        "--hermes-toolsets",
        default=None,
        help="Optional comma-separated Hermes toolsets passed to hermes chat-compatible one-shot mode.",
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


def iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(iter_strings(item))
        return strings
    if isinstance(value, list):
        strings = []
        for item in value:
            strings.extend(iter_strings(item))
        return strings
    return []


def extract_x_urls(value: Any) -> list[str]:
    urls: list[str] = []
    for text in iter_strings(value):
        urls.extend(match.group(0).rstrip(".,;:!?)]}") for match in X_URL_RE.finditer(text))
    return sorted(set(urls))


def content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
                else:
                    parts.append(compact_json(item))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return compact_json(content)


def payload_to_hermes_prompt(payload: dict[str, Any]) -> str:
    lines = [
        "Handle this Grok handoff request and return only the final answer requested by the user.",
        "",
    ]
    request_input = payload.get("input")
    if isinstance(request_input, str):
        lines.extend(["User request:", request_input])
    elif isinstance(request_input, list):
        lines.append("Conversation:")
        for item in request_input:
            if isinstance(item, dict):
                role = item.get("role", "message")
                lines.append(f"[{role}]")
                lines.append(content_to_text(item.get("content", "")))
            else:
                lines.append(content_to_text(item))
    else:
        lines.extend(["Input:", content_to_text(request_input)])

    passthrough_fields = {
        key: value
        for key, value in payload.items()
        if key not in {"input", "model"} and value not in (None, [], {})
    }
    if passthrough_fields:
        lines.extend(
            [
                "",
                "Additional request fields to honor when applicable:",
                compact_json(passthrough_fields),
            ]
        )
    x_urls = extract_x_urls(payload)
    if x_urls:
        lines.extend(
            [
                "",
                "X URL retrieval requirements:",
                "- Treat these as X/Twitter URLs that require source retrieval before answering.",
                "- Retrieve the post text, author/display name/handle, timestamp, visible media or quoted links, and visible engagement counts.",
                "- Retrieve the surrounding conversation, including parent posts and the rest of the thread when available.",
                "- Retrieve visible replies, quote posts, repost/reply/like/view counts, and notable reactions or context when available.",
                "- Treat engagement counts as a time-varying snapshot; mention snapshot drift when exact counts matter.",
                "- For reactions, include a compact top 3-5 notable replies, quote posts, or community reactions when available.",
                "- If aggregate counts and surfaced reaction items disagree, report the count and item evidence separately instead of forcing them to match.",
                "- Include concrete surfaced items from any successful exact_url_counts, thread_context, or reaction_search query when relevant; label the source query if another structured list is empty.",
                "- Classify surrounding posts by evidence: reply-to metadata as parent, embedded quoted content as quoted post, and same-author nearby posts as thread or surrounding author context unless the relationship is explicit.",
                "- Use available web, browser, and X-search tools. If access is limited by login, deletion, rate limits, or dynamic rendering, state the limitation and preserve partial evidence.",
                "URLs:",
                "\n".join(f"- {url}" for url in x_urls),
            ]
        )
    return "\n".join(lines).strip()


def strip_code_fence(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return value


def load_json_from_answer(answer: str) -> Any:
    value = strip_code_fence(answer)
    try:
        return json.loads(value)
    except Exception:
        return None


def direct_x_search_available() -> bool:
    try:
        if HERMES_SITE_PACKAGES not in sys.path:
            sys.path.insert(0, HERMES_SITE_PACKAGES)
        from tools.x_search_tool import check_x_search_requirements  # type: ignore

        return bool(check_x_search_requirements())
    except Exception:
        return False


def call_hermes_x_search(query: str) -> dict[str, Any]:
    if HERMES_SITE_PACKAGES not in sys.path:
        sys.path.insert(0, HERMES_SITE_PACKAGES)
    from tools.x_search_tool import x_search_tool  # type: ignore

    raw = x_search_tool(query=query)
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {"success": False, "raw": raw}
    if isinstance(parsed, dict):
        return parsed
    return {"success": False, "raw": parsed}


def build_x_search_queries(x_urls: list[str]) -> list[dict[str, str]]:
    queries: list[dict[str, str]] = []
    for url in x_urls:
        queries.append(
            {
                "kind": "exact_url_counts",
                "url": url,
                "query": (
                    "Fetch the exact X post at this URL and return every public engagement field available. "
                    "Return JSON if possible with author, handle, post_id, created_at, text, reply_count, "
                    "repost_count, quote_count, like_count, view_count, bookmark_count, thread_posts, "
                    "top_replies, quote_posts, and citations. URL: "
                    f"{url}"
                ),
            }
        )
        post_id_match = re.search(r"/status/(\d+)", url)
        if post_id_match:
            post_id = post_id_match.group(1)
            queries.append(
                {
                    "kind": "thread_context",
                    "url": url,
                    "query": (
                        f"Fetch the X thread for post id {post_id}. Include the target post, parent/quoted posts, "
                        "earlier and later thread posts, replies, quote posts, and visible engagement counts. "
                        "Classify each surrounding post as parent, quoted post, thread post, or surrounding author context based on available relationship evidence. "
                        "Return unavailable fields as null with a reason."
                    ),
                }
            )
            queries.append(
                {
                    "kind": "reaction_search",
                    "url": url,
                    "query": (
                        f"Search X for reactions, quote posts, and replies to X post {post_id}. "
                        "Summarize the top 3-5 notable replies, quote posts, or community reactions when available. "
                        "Include any available reply/repost/quote/like/view counts and state that counts are a time-varying snapshot. "
                        "If quote_count or reply_count indicates items that are not fully surfaced, report that limitation separately. "
                        "If this query surfaces a concrete quote post or reaction that another structured query omits, keep it as partial source-labeled evidence."
                    ),
                }
            )
    return queries


def representative_engagement_from_queries(queries: list[Any]) -> dict[str, Any] | None:
    for query in queries:
        if not isinstance(query, dict) or query.get("kind") != "exact_url_counts":
            continue
        parsed = query.get("parsed_answer")
        if not isinstance(parsed, dict):
            continue
        fields = [
            "author",
            "handle",
            "post_id",
            "created_at",
            "text",
            "reply_count",
            "repost_count",
            "quote_count",
            "like_count",
            "view_count",
            "bookmark_count",
        ]
        engagement = {field: parsed.get(field) for field in fields if field in parsed}
        if engagement:
            engagement["source_query_kind"] = query.get("kind")
            engagement["source_url"] = query.get("url")
            engagement["selection_rule"] = "first structured exact_url_counts parsed_answer"
            engagement["snapshot_note"] = "engagement counts are a time-varying snapshot from x_search exact_url_counts"
            return engagement
    return None


def run_direct_x_search(x_urls: list[str], output_dir: Path) -> dict[str, Any] | None:
    if not x_urls:
        return None
    result: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tool": "hermes_x_search_tool",
        "x_urls": x_urls,
        "available": direct_x_search_available(),
        "queries": [],
    }
    if not result["available"]:
        result["error"] = "Hermes x_search_tool is not available. Check `hermes auth status xai-oauth` and `hermes tools`."
        write_json(output_dir / "x-search-results.json", result)
        return result

    for item in build_x_search_queries(x_urls):
        response = call_hermes_x_search(item["query"])
        answer = response.get("answer") if isinstance(response, dict) else None
        parsed_answer = load_json_from_answer(answer) if isinstance(answer, str) else None
        result["queries"].append(
            {
                "kind": item["kind"],
                "url": item["url"],
                "query": item["query"],
                "response": response,
                "parsed_answer": parsed_answer,
            }
        )
    result["representative_engagement"] = representative_engagement_from_queries(result["queries"])
    write_json(output_dir / "x-search-results.json", result)
    return result


def x_search_context_for_prompt(result: dict[str, Any] | None) -> str | None:
    if not result:
        return None
    compact_queries: list[dict[str, Any]] = []
    for query in result.get("queries", []) or []:
        response = query.get("response") if isinstance(query, dict) else {}
        if not isinstance(response, dict):
            response = {}
        compact_queries.append(
            {
                "kind": query.get("kind"),
                "url": query.get("url"),
                "success": response.get("success"),
                "credential_source": response.get("credential_source"),
                "model": response.get("model"),
                "parsed_answer": query.get("parsed_answer"),
                "answer": response.get("answer"),
                "citations": response.get("citations"),
                "inline_citations": response.get("inline_citations"),
            }
        )
    return compact_json(
        {
            "tool": result.get("tool"),
            "available": result.get("available"),
            "x_urls": result.get("x_urls"),
                "queries": compact_queries,
                "representative_engagement": result.get("representative_engagement"),
                "error": result.get("error"),
            }
        )


def merge_toolsets(raw: str | None, required: list[str]) -> str:
    items: list[str] = []
    for item in (raw or "").split(","):
        value = item.strip()
        if value and value not in items:
            items.append(value)
    for item in required:
        if item not in items:
            items.append(item)
    return ",".join(items)


def effective_hermes_toolsets(payload: dict[str, Any], raw: str | None) -> str | None:
    if extract_x_urls(payload):
        return merge_toolsets(raw, ["web", "browser", "x_search"])
    return raw


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


def run_hermes_backend(
    args: argparse.Namespace,
    timeout_bin: str,
    request_artifact: dict[str, Any],
    payload: dict[str, Any],
    response_path: Path,
    stderr_path: Path,
    x_search_result: dict[str, Any] | None,
) -> int:
    if not shutil.which(args.hermes_bin):
        raise RuntimeError(
            f"Hermes executable not found: {args.hermes_bin}. Install with `brew install hermes-agent` "
            "and authenticate with `hermes auth add xai-oauth`."
        )
    prompt = payload_to_hermes_prompt(payload)
    x_context = x_search_context_for_prompt(x_search_result)
    if x_context:
        prompt = "\n\n".join(
            [
                prompt,
                "Direct Hermes x_search_tool artifact context:",
                x_context,
                "Use the direct x_search artifact as primary evidence for engagement counts, thread context, replies, quote posts, and reactions.",
            ]
        )
    command = [
        timeout_bin,
        str(args.timeout_seconds),
        args.hermes_bin,
        "--oneshot",
        prompt,
        "--provider",
        args.hermes_provider,
        "-m",
        str(payload.get("model")),
    ]
    hermes_toolsets = effective_hermes_toolsets(payload, args.hermes_toolsets)
    if hermes_toolsets:
        command.extend(["--toolsets", hermes_toolsets])
    with stderr_path.open("wb") as stderr_fh:
        proc = subprocess.run(
            command,
            cwd=str(Path(args.cwd).expanduser().resolve()),
            stdout=subprocess.PIPE,
            stderr=stderr_fh,
            check=False,
        )
    if proc.returncode != 0:
        return proc.returncode
    output_text = proc.stdout.decode("utf-8", errors="replace").strip()
    artifact = {
        "task": require_string(request_artifact, "task"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "meta": request_artifact.get("meta"),
        "request": payload,
        "response": {
            "type": "hermes_final_response",
            "provider": args.hermes_provider,
            "toolsets": hermes_toolsets,
            "stdout_bytes": len(proc.stdout),
        },
        "output_text": output_text or None,
        "response_id": None,
        "model": payload.get("model"),
        "backend": "hermes",
    }
    write_json(response_path, artifact)
    return 0


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
        "--backend",
        args.backend,
    ]
    if args.model:
        command.extend(["--model", args.model])
    if args.dry_run:
        command.append("--dry-run")
    if args.confirm_api_cost:
        command.append("--confirm-api-cost")
    if args.confirm_hermes_quota:
        command.append("--confirm-hermes-quota")
    if args.hermes_bin != os.getenv("HERMES_BIN", "hermes"):
        command.extend(["--hermes-bin", args.hermes_bin])
    if args.hermes_provider != os.getenv("HERMES_PROVIDER", "xai-oauth"):
        command.extend(["--hermes-provider", args.hermes_provider])
    if args.hermes_toolsets:
        command.extend(["--hermes-toolsets", args.hermes_toolsets])

    start = time.monotonic()
    failure_reasons: list[str] = []
    api_error: dict[str, Any] | None = None
    dry_run_payload: dict[str, Any] | None = None
    exit_code = 0
    model_used = args.model or os.getenv("GROK_MODEL") or os.getenv("GROK_X_RESEARCH_MODEL") or DEFAULT_MODEL
    x_urls_detected: list[str] = []
    hermes_toolsets_effective: str | None = None

    try:
        request_data = load_json(request_path)
        model = resolve_model(request_data, args.model)
        model_used = model
        payload = load_request_payload(request_data, model=model)
        x_urls_detected = extract_x_urls(payload)
        if args.backend == "hermes":
            hermes_toolsets_effective = effective_hermes_toolsets(payload, args.hermes_toolsets)
        if args.dry_run:
            dry_run_payload = payload
            stderr_path.write_text("", encoding="utf-8")
        elif args.backend == "hermes":
            x_search_result = run_direct_x_search(x_urls_detected, output_dir)
            exit_code = run_hermes_backend(
                args,
                timeout_bin,
                request_data,
                payload,
                response_path,
                stderr_path,
                x_search_result,
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
        elif "Hermes executable not found" in message:
            failure_reasons.append("missing_hermes")
        elif "input" in message or "request artifact" in message or "instructions" in message:
            failure_reasons.append("invalid_request")
        else:
            failure_reasons.append("api_or_backend_error")
    if (
        not args.dry_run
        and not response_non_empty
        and "missing_hermes" not in failure_reasons
    ):
        failure_reasons.append("missing_response_artifact")

    if "timeout" in failure_reasons:
        recommended = "Inspect request size and backend status, then rerun with a smaller request or larger timeout."
    elif "missing_api_key" in failure_reasons:
        recommended = "Set XAI_API_KEY for direct API calls, use --backend hermes after Hermes xAI OAuth setup, or use --dry-run for request validation only."
    elif "missing_hermes" in failure_reasons:
        recommended = "Install Hermes with `brew install hermes-agent`, authenticate with `hermes auth add xai-oauth`, then rerun."
    elif "invalid_request" in failure_reasons:
        recommended = "Fix grok-request.json against references/schema.md, then rerun with --dry-run before a real call."
    elif args.backend == "hermes" and "missing_response_artifact" in failure_reasons:
        recommended = "Run `brew install hermes-agent` if needed, authenticate with `hermes auth add xai-oauth`, inspect run.err, then rerun."
    elif "missing_response_artifact" in failure_reasons:
        recommended = "Inspect run.err and API/backend output, then rerun after fixing environment, model, provider, auth, rate-limit, or request shape."
    else:
        recommended = "Inspect summary.json and grok-response.json, then integrate the response in the caller."

    summary = {
        "command": command,
        "cwd": str(Path(args.cwd).expanduser().resolve()),
        "request_file": str(request_path),
        "response_artifact": str(response_path),
        "output_dir": str(output_dir),
        "model": model_used,
        "backend": args.backend,
        "base_url": args.base_url,
        "hermes_provider": args.hermes_provider if args.backend == "hermes" else None,
        "hermes_toolsets": hermes_toolsets_effective if args.backend == "hermes" else None,
        "x_urls_detected": x_urls_detected,
        "x_search_results_artifact": (
            str(output_dir / "x-search-results.json")
            if x_urls_detected and args.backend == "hermes" and not args.dry_run
            else None
        ),
        "dry_run": args.dry_run,
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
