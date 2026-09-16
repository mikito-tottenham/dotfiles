---
name: codex-cli-runner
description: Run `codex exec` through an observable file-backed wrapper with stall detection and failure artifacts. Use when an orchestrating agent must invoke Codex CLI as a subprocess; ordinary research, review, or file work that does not require Codex CLI should use its owning workflow. Use when asked to CodexをCLIで呼ぶ or Codex CLIをサブプロセス実行する.
---

# Codex CLI Runner

Use this skill when an orchestrating agent delegates work to Codex CLI through `codex exec`. Keep the source prompt, launch prompt, JSONL events, final message, stderr, summary, and failure notes under `.context/<task>/`.

Shared runner contract (outcome-first delegation, prompt files, expected-artifact resolution, wrapper artifacts, success/failure semantics, No-API validation): read [references/runner-common.md](references/runner-common.md). This file covers only Codex-specific behavior.

## Core Rules

- Use `codex exec --json -o <last-message>` for observable non-interactive runs.
- The wrapper runs without a timeout by default (`--timeout-seconds 0`; GNU timeout treats duration 0 as no limit). Pass a positive `--timeout-seconds` only when the task contract needs a hard limit.
- Keep the wrapper's stall watchdog enabled: it kills the run when `run.events.jsonl` and `run.err` both stop growing for `--stall-timeout-seconds` (default 300; 0 disables) and records `stall_timeout`.
- Do not force `--sandbox`, `--ask-for-approval`, or bypass flags by default. Let Codex config/profile decide unless the caller explicitly requests an override via extra args.

## Caller Checklist

In addition to the shared contract, decide these explicitly before running Codex:

- Defaults: omit `--model`, `--effort`, and `--profile` unless the caller, model registry, or role explicitly requires an override. `--effort` accepts `low|medium|high|xhigh|max|ultra` and is passed through unchanged.
- Timeout: none by default (unbounded run). Pass `--timeout-seconds <seconds>` only when the caller explicitly needs a bounded run; the stall watchdog, not a kill timer, is the default protection against silent hangs.
- Stall watchdog: rely on the 300-second default; raise `--stall-timeout-seconds` only for tasks whose single commands legitimately stay silent longer, and pass `0` only when a caller explicitly accepts unbounded silent runs.
- Prompt profile: use `--prompt-profile auto` by default; pass `--prompt-profile none` only when the source prompt already contains a complete Codex-specific launch contract.
- Extra Codex args: one token per `--extra-codex-arg=<token>`. Never pass `-i`/`--image` this way; see Images below.
- Web research: do not pass `--extra-codex-arg=--search` or other search flags. `codex exec` has no `--search` flag and exits `2` immediately (codex-cli 0.146.1, observed 2026-08-07); `codex features list` shows `search_tool`/`web_search_request` as removed/deprecated, and web access runs through the default-enabled `browser_use` with no extra flag.

## Standard Command Shape

Use this form, with `<prompt>` kept short and pointing to the generated launch prompt:

```bash
timeout 0 codex exec --json -o <artifact>.last-message.md "<prompt>" > <artifact>.events.jsonl 2> <artifact>.err
# duration 0 = no time limit; replace 0 with a positive number of seconds to enforce one
```

For repeatable runs, prefer the bundled wrapper:

```bash
python3 <skill-dir>/scripts/run_codex_cli.py \
  --prompt-file .context/<task>/prompt.md \
  --output-dir .context/<task> \
  --expected-artifact <expected-file>
```

Add `--model <model>`, `--effort <low|medium|high|xhigh|max|ultra>`, or `--profile <profile>` only when overriding Codex CLI defaults.
Add `--timeout-seconds <seconds>` only when a positive hard limit is required (default 0 = no timeout).
Add `--stall-timeout-seconds <seconds>` only when overriding the 300-second no-progress default (`0` disables).

Beyond the shared artifact set, the wrapper writes:

- `run.events.jsonl`: Codex JSONL stdout events
- `last-message.md`: final Codex message from `--output-last-message`
- `summary.json` extras: `stalled`, `stall_timeout_seconds`, `warnings`, `last_error_event` or `last_event`, `events_bytes`, `stderr_bytes`, `last_message_bytes`

## Timeout And Sleep Semantics

- `--timeout-seconds` (GNU `timeout`), the stall watchdog, and `elapsed_seconds` all measure awake time on macOS: none of them advance while the machine sleeps, so a run that spans sleep can stay alive far longer in wall-clock time than the configured timeout.
- The stall watchdog closes the observed gap: a stream hang (for example a `Reconnecting... (request timed out)` error with no further events) is killed after `--stall-timeout-seconds` of no growth in `run.events.jsonl` and `run.err`, via SIGTERM to the process group and SIGKILL after a grace period.
- A stall failure does not invalidate already-materialized artifacts. The wrapper never converts materialized expected artifacts into early success; on `stall_timeout`, the caller must judge from `summary.json.expected_artifacts` and the event tail whether the artifacts are usable or the run must be redone.

## Prompt Profiles

The wrapper writes `.context/<task>/run.prompt.md`, then passes only a file-reference prompt to `codex exec`.

Default behavior:

- `--prompt-profile auto` is the default and applies the Codex adapter.
- `--prompt-profile codex` forces the Codex adapter.
- `--prompt-profile none` suppresses prompt adaptation.

The Codex adapter is short, model-agnostic, and outcome-first. It tells Codex to honor the source prompt's outcome, success criteria, allowed side effects, evidence rules, output shape, and completion rule while relying on CLI/config effort rather than prompt magic words. The adapter does not branch on the model name; `--model` and `--effort` come from the caller (normally the model registry) and are passed through unchanged.

## Success Criteria

Codex-specific signals on top of the shared checks:

- `run.events.jsonl` includes `turn.completed` and no obvious error events.
- `last-message.md` exists and is non-empty.

A stderr error-pattern match alone does not fail an otherwise successful run. When the exit code is `0`, the JSONL events include `turn.completed`, `last-message.md` and every expected artifact are non-empty, and no error events exist, the wrapper records the match as `stderr_error_pattern=true` plus `warnings=["stderr_error_pattern_downgraded"]` and keeps `success=true`. Treat such matches as MCP-server stderr noise (for example rmcp transport auth errors) unless another failure signal appears.

## Failure Criteria

Codex-specific failure signals on top of the shared list:

- Timeout exit `124` is only possible when a positive `--timeout-seconds` was set; the default is unbounded.
- Stall watchdog kill: no growth in `run.events.jsonl` and `run.err` for `--stall-timeout-seconds`, recorded as `stall_timeout` with `stalled=true`.
- A stderr error pattern counts as failure only when the run lacks an independent success signal (exit `0`, a `turn.completed` event, non-empty `last-message.md`, no error events, and every expected artifact present).
- `last-message.md` is missing or empty.

## No-API Validation

Codex-specific fake behavior for the shared No-API patterns:

- The fake Codex CLI must write JSONL stdout, honor `-o <last-message>`, and create the expected artifact. Minimal behavior: exit `0`, print one non-error JSON object such as `{"type":"event","status":"ok"}`, parse `-o <path>` and write a non-empty final message there, then write the requested expected artifact such as `result.md`.
- For a stall-watchdog check, use a fake Codex that prints one event, flushes stdout, then sleeps far longer than a small `--stall-timeout-seconds` (for example `5`). Expect exit `1`, `failure_reasons` containing `stall_timeout`, `stalled=true`, and no surviving fake Codex process.

## Wrapper Notes

- Use `--extra-codex-arg` for narrow additions when explicitly required. Pass one Codex CLI token per wrapper argument, for example `--extra-codex-arg=--sandbox --extra-codex-arg=read-only`, `--extra-codex-arg=--ask-for-approval --extra-codex-arg=never`, or `--extra-codex-arg=--config --extra-codex-arg=key=value`.
- The wrapper launches Codex with stdin attached to `/dev/null`, so runs started from background shells or with piped stdin do not hang on `Reading additional input from stdin...`. Do not rely on caller-side stdin redirection.

## Images

Do not pass `-i`/`--image` through `--extra-codex-arg`. `codex exec -i/--image` takes variadic arguments, so it swallows the following positional prompt as an image path; the run then has no positional prompt and falls back to reading one from stdin (observed 2026-07-31: 0 JSONL events, hang until timeout exit `124` while stdin stayed open). The `--image=<path>` form avoids the prompt swallowing but showed the same stdin-dependent hang in background-shell runs.

For image tasks, keep images on local paths and instruct Codex in the source prompt to open them with the `view_image` tool. This is the stable path for this wrapper.

## Validation

```bash
scripts/skill-quick-validate skills/codex-cli-runner
python3 <skill-dir>/scripts/run_codex_cli.py --help
```

Runtime checks: no-API command construction, no-API fake Codex success, no-API stall watchdog kill, real short smoke prompt, real file read/write prompt, forced timeout failure (pass a small positive `--timeout-seconds`).
