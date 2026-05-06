---
name: grok-cli-runner
description: Run Grok handoffs through a CLI-runner style artifact wrapper with observable request and response files, timeouts, model defaults, dry-run support, and artifact-based failure handling. Use when Claude Code or Codex needs to call Grok, GrokをCLIで呼ぶ, invoke a future `grok` CLI, or delegate research, review, generation, or schema-constrained output to Grok while preserving reproducible context task artifacts. Current backend is xAI Responses API because no local Grok CLI is available.
---

# Grok CLI Runner

Use this skill when delegating work to Grok through a file-based runner contract. The current backend is xAI Responses API, not a local Grok CLI, because no `grok` executable is currently available. Keep the request, response, summary, stderr, and failure notes under `.context/<task>/` so the call can be audited and replayed.

Frame each delegation as an outcome-first contract: request artifact, expected response artifact, timeout, success criteria, model defaulting, allowed tools, schema expectations, and failure handling. Keep final judgment, editing, and irreversible side effects in the caller.

## Core Rules

- Put every run under `.context/<task>/`.
- Save the Grok request as `.context/<task>/grok-request.json`.
- Do not inline large JSON request bodies into shell arguments.
- Before any real non-`--dry-run` Grok call, tell the user that xAI API usage may incur cost and ask for explicit approval in the conversation.
- Run real calls only after explicit user approval, and pass `--confirm-api-cost` to record that approval. Do not infer approval from the presence of `XAI_API_KEY`.
- Use the wrapper's 600-second process timeout default, or pass an explicit timeout override when the task needs a shorter or longer limit.
- Use `--dry-run` for request-shape validation; it does not call the API and intentionally does not create a response artifact.
- Require `XAI_API_KEY` for real calls. Premium+ access alone is not API access.
- Do not treat 0-byte `run.err` or a missing response artifact alone as a hang; use exit code, timeout, summary fields, and failure reasons.

## Caller Checklist

Before running Grok, make these decisions explicitly:

- Task directory: choose `.context/<task>/`.
- Request artifact: write `.context/<task>/grok-request.json` with top-level `task` and `request`.
- Response artifact: pass `--response-artifact grok-response.json` unless a different response filename is required.
- API cost confirmation: for real calls, ask the user for explicit approval first, then pass `--confirm-api-cost`; for validation without approval or cost, use `--dry-run`.
- Model: omit `--model` unless the caller, model registry, or role explicitly requires an override. The wrapper defaults to `GROK_MODEL`, then `GROK_X_RESEARCH_MODEL`, then `grok-4.3`.
- Timeout: rely on the 600-second wrapper default unless the task contract says otherwise. The HTTP timeout defaults to the same value unless `--http-timeout-seconds` is provided.
- Tools: include `web_search`, `x_search`, or other xAI tools in `request.tools` only when the task needs them; set explicit limits in the prompt/request text when doing research.
- Structured output: put schema constraints under `request.response_format`, then validate `output_text` in the caller.
- Expected artifacts: if other files must be created by the caller after reading Grok output, track those outside this wrapper; this wrapper only guarantees the response artifact.
- Workflow validation: after model-default changes, run at least one no-API validation and, when API cost/auth is approved, a short real call before relying on the new default for long sequential tool workflows.

Do not add "think hard", fixed progress-update scaffolds, or mandatory step-by-step narration to simulate model effort. Use model selection, request fields, and explicit success criteria instead.

## Standard Command Shape

For repeatable runs, use the bundled wrapper:

```bash
python3 <skill-dir>/scripts/run_grok_cli.py \
  --request-file .context/<task>/grok-request.json \
  --output-dir .context/<task> \
  --response-artifact grok-response.json \
  --confirm-api-cost
```

Add `--model <model>` only when overriding environment/config defaults.
Add `--timeout-seconds <seconds>` only when overriding the 600-second process timeout.
Add `--http-timeout-seconds <seconds>` only when the HTTP request needs a different timeout from the process guard.
Omit `--confirm-api-cost` for `--dry-run`; it is required only for real API calls after user approval.

The wrapper writes:

- `grok-request.json`: caller-authored request artifact
- `grok-response.json`: normalized response artifact for real successful calls
- `run.err`: stderr and local wrapper diagnostics
- `summary.json`: command, exit code, elapsed time, byte counts, model, dry-run flag, API cost confirmation flag, response status, `failure_reasons`, and `recommended_next_action`
- `failure.md`: only when the wrapper run fails

For request-shape validation without API spend:

```bash
python3 <skill-dir>/scripts/run_grok_cli.py \
  --request-file .context/<task>/grok-request.json \
  --output-dir .context/<task> \
  --response-artifact grok-response.json \
  --dry-run
```

## Request Contract

Read `references/schema.md` when creating or validating request/response artifacts.

Required request artifact fields:

- `task`: stable task identifier
- `request`: object sent to xAI's `/responses` endpoint after minimal defaulting

Important request rules:

- `request.input` is required.
- `request.model` is optional; wrapper model defaulting fills it when omitted.
- `request.instructions` is rejected because xAI Responses API does not support it in this wrapper.
- `meta` is optional and stays local; it is not sent to xAI.
- Keep one API job per request artifact.

## Success Criteria

Require all applicable checks:

- Process exit code is `0`.
- For real runs, `grok-response.json` exists and is non-empty.
- Response artifact contains `request`, `response`, `model`, and either `output_text` or a raw `response` object sufficient for the caller to inspect.
- `summary.json.success` is `true`, `summary.json.failure_reasons` is empty, and `summary.json.response_non_empty` is `true`.
- For `--dry-run`, success means the outbound payload validated and was written to `summary.json.dry_run_payload`; no response artifact is expected.

## Failure Criteria

Treat any of these as failure:

- Timeout exit, normally exit code `124`.
- Non-zero process exit.
- Missing or invalid request artifact.
- Missing `request.input`.
- Missing `--confirm-api-cost` on a real non-`--dry-run` call.
- Missing `XAI_API_KEY` on a real call.
- HTTP/API authentication, model, permission, quota, policy, or rate-limit errors.
- Real run response artifact is missing or empty.

On failure, inspect `.context/<task>/summary.json` first:

- `command`
- `exit_code`
- `elapsed_seconds`
- `request_bytes`, `response_bytes`, and `stderr_bytes`
- `model`
- `dry_run`
- `api_cost_confirmed`
- `failure_reasons`
- `api_error`
- `response_non_empty`
- `recommended_next_action`

The wrapper also writes `.context/<task>/failure.md` with:

- executed command
- exit code
- elapsed time
- request/response/stderr sizes
- API or validation error
- response artifact status
- recommended next action

## No-API Validation

Use these patterns when testing the wrapper itself without spending xAI API budget:

- Run `--dry-run` with a valid request artifact. It should exit `0`, write `summary.json`, and not require `XAI_API_KEY`.
- Run without `--dry-run` and without `--confirm-api-cost` only as a guard test. It should fail before any API request and write `summary.json.failure_reasons` containing `api_cost_not_confirmed`.
- Run with an invalid request artifact to confirm `failure.md` and `summary.json.failure_reasons` are generated.
- Run with a fake backend script via `--backend-script <path>` only for controlled tests. Do not use fake backend scripts for real Grok delegation.
- Do not hand-edit `summary.json`, `run.err`, `grok-response.json`, or `failure.md`. If a controlled test needs explanation, write a separate `notes.md`.

## Wrapper Notes

- Resolve `<skill-dir>` from the location of this `SKILL.md`.
- Pass `--cwd <project-root>` when the caller wants the backend process launched from a specific repository.
- Omit `--model` by default so environment/model registry defaults apply.
- Pass `--base-url` only when targeting a non-default xAI-compatible endpoint.
- Keep final orchestration in the caller. This skill only calls Grok and records observable artifacts.
- If an official Grok CLI becomes available later, preserve this `.context/<task>/` contract unless there is a compelling migration reason.

## Validation

Validate the skill and wrapper after changes:

```bash
scripts/skill-quick-validate skills/grok-cli-runner
python3 <skill-dir>/scripts/run_grok_cli.py --help
```

For runtime validation, run:

- no-API dry-run success
- no-API missing `--confirm-api-cost` guard failure
- invalid request failure
- optional real API smoke only when API/auth cost is explicitly acceptable
- representative long-tool workflow smoke before using a new default model for production-like delegation
