---
name: grok-cli-runner
description: Run Grok through the file-backed Hermes/xAI wrapper, or retrieve evidence for supplied X/Twitter URLs. Use when a caller or resolver selects Grok, and for X-post/thread inspection; unrelated web research should use its owning research workflow. Use when asked to GrokをCLIで呼ぶ.
---

# Grok CLI Runner

Use this skill when delegating work to Grok through a file-based runner contract. The default backend is Hermes Agent with `xai-oauth`, backed by a SuperGrok subscription. Use direct xAI Responses API only when explicitly requested or when the task specifically needs API-key behavior. Keep the request, response, summary, stderr, and failure notes under `.context/<task>/` so the call can be audited and replayed.

Frame each delegation as an outcome-first contract: request artifact, expected response artifact, timeout, success criteria, model defaulting, allowed tools, schema expectations, and failure handling. Keep final judgment, editing, and irreversible side effects in the caller.

This runner has two distinct modes:

- `--retrieval-mode x-raw`: fetch as much raw public data as possible for supplied X URLs and return it to the caller in `x-search-results.json` plus the response artifact. Use this when the caller needs source evidence, quote eligibility, Article/card data, counts, or raw context before deciding how to use it.
- `--retrieval-mode answer`: prepare a Grok final answer for the supplied task using available X and web context. This is the default for backward compatibility.

## Core Rules

- Put every run under `.context/<task>/`.
- Save the Grok request as `.context/<task>/grok-request.json`.
- Do not inline large JSON request bodies into shell arguments.
- Do not ask for per-run approval solely because the call may use API billing, subscription quota, or local Hermes auth/session state.
- Use the wrapper's 600-second process timeout default, or pass an explicit timeout override when the task needs a shorter or longer limit.
- Direct Hermes `x_search_tool` probes use a separate per-query timeout default of 120 seconds; override with `--x-search-timeout-seconds` only when a specific X retrieval needs more or less time.
- After direct X search produces `x-search-results.json`, Hermes final-answer materialization uses a response watchdog default of 180 seconds; override with `--response-watchdog-seconds` or pass `0` to disable.
- Use `--dry-run` for request-shape validation; it does not call the API and intentionally does not create a response artifact.
- In `--dry-run`, `--response-artifact` still records the intended response path, but success is checked through `summary.json.dry_run_payload`; do not require `grok-response.json` to exist for dry-run success.
- Require `XAI_API_KEY` for real direct API calls. SuperGrok access alone is not direct API access.
- Require Hermes Agent setup and `xai-oauth` login for real Hermes calls. `XAI_API_KEY` is not required for this backend.
- Do not treat 0-byte `run.err` or a missing response artifact alone as a hang; use exit code, timeout, summary fields, and failure reasons.
- When the user provides an X-related URL, this skill must be used. X-related URL includes `x.com`, `twitter.com`, `mobile.twitter.com`, X/Twitter post URLs, thread URLs, quote-post URLs, reply URLs, and common X mirrors such as Nitter URLs.
- When the caller needs raw X evidence, use `--retrieval-mode x-raw`; do not infer raw evidence from the default final-answer prose.

## Conditional References

- Before any real or dry-run invocation, read [references/runner-contract.md](references/runner-contract.md) for arguments, timeout units, artifacts, success/failure semantics, and validation.
- For an X/Twitter URL, or when Hermes setup/authentication is the task, also read [references/x-retrieval.md](references/x-retrieval.md). Preserve its raw-evidence and engagement-snapshot rules for X retrieval.
- Read [references/schema.md](references/schema.md) only when creating or validating request, response, or X-search JSON artifacts.
