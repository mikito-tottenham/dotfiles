---
name: grok-cli-runner-contract
description: Conditional invocation, artifact, timeout, and failure contract for grok-cli-runner.
---

# Runner Contract

## Caller Checklist

Before running Grok, make these decisions explicitly:

- Task directory: choose `.context/<task>/`.
- Request artifact: write `.context/<task>/grok-request.json` with top-level `task` and `request`.
- Response artifact: pass `--response-artifact grok-response.json` when the response belongs inside `--output-dir`; use an absolute `--response-artifact` path when the response must be written outside `--output-dir`, such as inside a target repository.
- Retrieval mode: use `--retrieval-mode x-raw` for source collection and `--retrieval-mode answer` for Grok-authored analysis or synthesis.
- Backend: default to `--backend hermes`; pass `--backend xai-api` only when direct API-key billing is explicitly intended.
- Model: omit `--model` unless the caller, model registry, or role explicitly requires an override. The wrapper defaults to `GROK_MODEL`, then `GROK_X_RESEARCH_MODEL`, then `grok-4.3`.
- Timeout: rely on the 600-second wrapper default unless the task contract says otherwise. The HTTP timeout defaults to the same value unless `--http-timeout-seconds` is provided.
- Direct X search timeout: rely on the 120-second per-query default unless the task specifically requires a different limit.
- Hermes final-response watchdog: rely on the 180-second default after direct X search, or pass `--response-watchdog-seconds` when a long final synthesis is explicitly worth waiting for.
- Tools: include `web_search`, `x_search`, or other xAI tools in `request.tools` only when the task needs them; set explicit limits in the prompt/request text when doing research. For Hermes backend, pass `--hermes-toolsets <csv>` only when Hermes toolsets are already configured and the task needs them.
- Structured output: put schema constraints under `request.response_format`, then validate `output_text` in the caller.
- Expected artifacts: if the target artifact is the Grok response itself, make it `--response-artifact`; if other files must be created by the caller after reading Grok output, track those outside this wrapper because this wrapper only guarantees the response artifact.
- Working directory: `--cwd` controls the backend process working directory. It is not a substitute for the shell's current directory when resolving the wrapper's `--request-file` or `--output-dir` arguments.
- Workflow validation: after model-default changes, run at least one no-call validation and, when credentials are available, a short real call before relying on the new default for long sequential tool workflows.

Do not add "think hard", fixed progress-update scaffolds, or mandatory step-by-step narration to simulate model effort. Use model selection, request fields, and explicit success criteria instead.

## Standard Command Shape

For subscription-backed runs through Hermes/SuperGrok OAuth, use:

```bash
python3 <skill-dir>/scripts/run_grok_cli.py \
  --request-file .context/<task>/grok-request.json \
  --output-dir .context/<task> \
  --response-artifact grok-response.json \
  --backend hermes
```

This calls `hermes --oneshot` with `--provider xai-oauth` by default and normalizes the final stdout into `grok-response.json`.

For raw X URL retrieval, use:

```bash
python3 <skill-dir>/scripts/run_grok_cli.py \
  --request-file .context/<task>/grok-request.json \
  --output-dir .context/<task> \
  --response-artifact grok-response.json \
  --backend hermes \
  --retrieval-mode x-raw
```

This writes `x-search-results.json`, embeds the raw retrieval object in `grok-response.json`, and does not ask Hermes for final prose.

For explicitly requested direct xAI API runs, use:

```bash
python3 <skill-dir>/scripts/run_grok_cli.py \
  --request-file .context/<task>/grok-request.json \
  --output-dir .context/<task> \
  --response-artifact grok-response.json \
  --backend xai-api
```

Add `--model <model>` only when overriding environment/config defaults.
Add `--timeout-seconds <seconds>` only when overriding the 600-second process timeout.
Add `--http-timeout-seconds <seconds>` only when the HTTP request needs a different timeout from the process guard.
Add `--x-search-timeout-seconds <seconds>` only when overriding the direct Hermes X-search per-query timeout.
Add `--response-watchdog-seconds <seconds>` only when overriding the Hermes final-response watchdog after direct X search.
Add `--hermes-provider <provider>` only when overriding the Hermes provider from `xai-oauth`.
Add `--hermes-bin <path>` only when the Hermes executable is not on `PATH`.

The wrapper writes:

- `grok-request.json`: caller-authored request artifact
- `x-search-results.json`: direct Hermes `x_search_tool` result artifact when X URLs are detected
- stdout progress lines: direct X retrieval start, each query start/finish, and completion/unavailable status
- resolved response artifact, normally `grok-response.json`: normalized response artifact for real successful calls; in `x-raw` mode this wraps the raw X retrieval instead of final prose
- `run.err`: stderr and local wrapper diagnostics
- `summary.json`: command, resolved `cwd`, exit code, elapsed time, byte counts, model, backend, dry-run flag, detected X URLs, effective Hermes toolsets, produced X search artifact path, response artifact path/status, `failure_reasons`, and `recommended_next_action`
- If Hermes final-answer synthesis exceeds the response watchdog after direct X search, `summary.json.failure_reasons` includes `hermes_response_watchdog_timeout`.
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

Read [schema.md](schema.md) when creating or validating request/response artifacts.

Required request artifact fields:

- `task`: stable task identifier
- `request`: Responses-style object normalized by the wrapper. The default Hermes backend converts it into a `hermes --oneshot` prompt; explicit `--backend xai-api` sends it to xAI's `/responses` endpoint.

Important request rules:

- `request.input` is required.
- `request.model` is optional; wrapper model defaulting fills it when omitted.
- `request.instructions` is rejected because xAI Responses API does not support it in this wrapper.
- `meta` is optional and stays local; it is not sent to xAI.
- Keep one backend job per request artifact.

## Success Criteria

Require all applicable checks:

- Process exit code is `0`.
- For real runs, the resolved response artifact exists and is non-empty.
- Response artifact contains `request`, `response`, `model`, and either `output_text` or a raw `response` object sufficient for the caller to inspect.
- `summary.json.success` is `true`, `summary.json.failure_reasons` is empty, and `summary.json.response_non_empty` is `true`.
- For `--retrieval-mode x-raw`, `x-search-results.json.available=true` and `summary.json.x_search_successful_query_count > 0`.
- For `--dry-run`, success means the outbound payload validated and was written to `summary.json.dry_run_payload`; no response artifact is expected.

These checks prove runner execution and non-empty response materialization only. The caller must still evaluate task-specific response quality against the request artifact.

## Failure Criteria

Treat any of these as failure:

- Timeout exit, normally exit code `124`.
- Non-zero process exit.
- Missing or invalid request artifact.
- Missing `request.input`.
- Missing `XAI_API_KEY` on a real direct API call.
- Missing `hermes` executable, missing Hermes `xai-oauth` login, or Hermes provider/model/toolset errors on a real Hermes call.
- `missing_hermes` in `summary.json.failure_reasons` means the Homebrew `hermes-agent` formula is missing or `--hermes-bin` points to the wrong executable.
- HTTP/API authentication, model, permission, policy, or rate-limit errors.
- Real run response artifact is missing or empty.
- In `--retrieval-mode x-raw`, missing X URLs, unavailable direct `x_search_tool`, or zero successful direct X queries.

On failure, inspect `.context/<task>/summary.json` first:

- `command`
- `cwd`
- `exit_code`
- `elapsed_seconds`
- `request_bytes`, `response_bytes`, and `stderr_bytes`
- `model`
- `x_urls_detected`
- `hermes_toolsets`
- `x_search_results_artifact`
- `x_search_available` and `x_search_successful_query_count`
- `x_search_timeout_seconds`
- `response_watchdog_seconds` and `hermes_final_timeout_seconds`
- `x-search-results.json.diagnostics` when direct X search is unavailable
- `dry_run`
- `failure_reasons`
- `api_error`
- `response_artifact`
- `response_non_empty`
- `recommended_next_action`

If a higher-level workflow needs a downstream blocked artifact, create it in the caller using that workflow's schema or template. Do not invent a downstream schema in this runner and do not modify runner evidence artifacts. If no caller schema was supplied, report the runner as blocked with links to `summary.json` and `failure.md` instead of fabricating an artifact format.

The wrapper also writes `.context/<task>/failure.md` with:

- executed command
- exit code
- elapsed time
- request/response/stderr sizes
- API or validation error
- response artifact status
- recommended next action

## No-Call Validation

Use these patterns when testing the wrapper itself without making a backend call:

- Run `--dry-run` with a valid request artifact. It should exit `0`, write `summary.json`, and not require `XAI_API_KEY`.
- For successful `--dry-run`, inspect `summary.json.dry_run_payload`; no `grok-response.json` is expected.
- Run with an invalid request artifact to confirm `failure.md` and `summary.json.failure_reasons` are generated.
- Run a dry-run or direct helper-level check with an X URL request to confirm prompt conversion includes X retrieval requirements.
- For X URL `--dry-run`, verify `summary.json.x_urls_detected` is non-empty and `summary.json.hermes_toolsets` includes `web`, `browser`, and `x_search`; this confirms routing without calling Hermes or xAI.
- Run `--retrieval-mode x-raw` with a real X URL and confirm `summary.json.x_search_successful_query_count > 0`.
- For any real X smoke, confirm stdout emits progress and `x-search-results.json` appears before the first direct query finishes.
- Run a real Hermes X URL smoke when credentials are available and confirm `x-search-results.json` is written with `credential_source: xai-oauth`, `available=true`, Article/card fields when present, and visible engagement counts when xAI returns them.
- Run with a fake backend script via `--backend-script <path>` only for controlled tests. Do not use fake backend scripts for real Grok delegation.
- Do not hand-edit `summary.json`, `run.err`, the response artifact, or `failure.md`. If a controlled test needs explanation, write a separate `notes.md`.

## Wrapper Notes

- Resolve `<skill-dir>` from the location of this `SKILL.md`.
- Pass `--cwd <project-root>` when the caller wants the backend process launched from a specific repository.
- `summary.json.cwd` records the resolved `--cwd`; inspect that field for backend cwd because `summary.json.command` does not include `--cwd`, and the shell directory that launched the wrapper is not recorded as a separate field.
- Omit `--model` by default so environment/model registry defaults apply.
- Pass `--base-url` only when targeting a non-default xAI-compatible endpoint.
- Pass `--backend hermes` or omit `--backend` to use Hermes Agent's `xai-oauth` provider and SuperGrok subscription quota.
- Pass `--backend xai-api` only to force direct xAI Responses API behavior.
- If Hermes is missing, install the Homebrew formula `hermes-agent`; do not install the unrelated `hermes` cask.
- Keep final orchestration in the caller. This skill only calls Grok and records observable artifacts.
- If an official Grok CLI becomes available later, preserve this `.context/<task>/` contract unless there is a compelling migration reason.

## Validation

Validate the skill and wrapper after changes:

```bash
scripts/skill-quick-validate skills/grok-cli-runner
python3 <skill-dir>/scripts/run_grok_cli.py --help
```

For wrapper behavior changes, run the applicable checks below; documentation-only or trigger-only edits need structural validation and diff review, not live calls:

- no-call dry-run success and invalid request failure when request handling changes
- X URL prompt conversion and automatic `web,browser,x_search` toolset behavior when X routing changes
- X URL direct `x-search-results.json` artifact behavior when retrieval changes
- optional real Hermes smoke when Hermes is logged in
- optional real API smoke when direct API behavior is needed
- representative long-tool workflow smoke before using a new default model for production-like delegation
