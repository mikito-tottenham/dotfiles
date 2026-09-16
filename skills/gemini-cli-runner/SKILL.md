---
name: gemini-cli-runner
description: Run `gemini -p` through an observable file-backed wrapper with timeout, approval-mode, and failure artifacts. Use when Claude Code or Codex must invoke Gemini CLI as a subprocess; ordinary research, review, or file work that does not require Gemini CLI should use its owning workflow. Use when asked to GeminiをCLIで呼ぶ or Gemini CLIをサブプロセス実行する.
---

# Gemini CLI Runner

Use this skill when delegating work to Gemini CLI through non-interactive `gemini -p`. Keep the source prompt, launch prompt, stream-json output, stderr, summary, and failure notes under `.context/<task>/`.

Shared runner contract (outcome-first delegation, prompt files, expected-artifact resolution, wrapper artifacts, success/failure semantics, No-API validation): read [references/runner-common.md](references/runner-common.md). This file covers only Gemini-specific behavior.

## Core Rules

- Use `gemini -p <prompt> --output-format stream-json` for observable non-interactive runs.
- The wrapper embeds the source prompt inside `.context/<task>/run.prompt.md`, starts Gemini from that output directory, and passes only a short instruction to read `./run.prompt.md`.
- Use the wrapper's 600-second timeout default, or pass an explicit timeout override when the task needs a shorter or longer limit.
- Do not force `--sandbox`, `--yolo`, `--approval-mode`, trust, policy, or tool flags by default. Let Gemini config decide unless the caller explicitly requests an override.

## Caller Checklist

In addition to the shared contract, decide these explicitly before running Gemini:

- Working directory: `--cwd <project-root>` is recorded as `target_cwd`; the wrapper starts the Gemini process from the run output directory so hidden `.context` artifacts are readable by relative path, and includes the target directory with `--include-directories` unless the caller already supplied that flag.
- Defaults: omit `--model` and `--approval-mode` unless the caller, model registry, role, or task explicitly requires an override.
- Timeout: rely on the 600-second wrapper default unless the task contract says otherwise.
- Prompt profile: use `--prompt-profile auto` by default; pass `--prompt-profile none` only when the source prompt already contains a complete Gemini-specific launch contract.
- Extra Gemini args: one token per `--extra-gemini-arg=<token>`.

If the Gemini CLI later exposes an effort or thinking control, pass it as an explicit CLI/config override rather than prompt magic words.

## Standard Command Shape

Use this form, with `<prompt>` kept short and pointing to the generated launch prompt:

```bash
timeout 600 gemini -p "<prompt>" --output-format stream-json > <artifact>.stream.jsonl 2> <artifact>.err
```

For repeatable runs, prefer the bundled wrapper:

```bash
python3 <skill-dir>/scripts/run_gemini_cli.py \
  --prompt-file .context/<task>/prompt.md \
  --output-dir .context/<task> \
  --expected-artifact <expected-file>
```

Add `--model <model>` or `--approval-mode <default|auto_edit|yolo|plan>` only when overriding Gemini CLI defaults.
Add `--timeout-seconds <seconds>` only when overriding the 600-second default.

Beyond the shared artifact set, the wrapper writes:

- `run.stream.jsonl`: Gemini stream-json stdout
- `summary.json` extras: `target_cwd`, `process_cwd`, `final_stream_success`, `nonfatal_reasons`, `raw_mode_tty_error`, `stream_bytes`, `stderr_bytes`, `last_error_record` or `last_stream_record`

## Prompt Profiles

The wrapper writes `.context/<task>/run.prompt.md`, embeds the complete source prompt in that launch file, then starts Gemini from the run output directory and passes only a relative file-reference prompt to `gemini -p`.

This cwd relocation is intentional: Gemini may reject absolute paths under hidden directories such as `.context` as ignored files, while it can read `./run.prompt.md` when the process cwd is the run directory.

Default behavior:

- `--prompt-profile auto` is the default and applies the Gemini adapter.
- `--prompt-profile gemini` forces the Gemini adapter.
- `--prompt-profile none` suppresses prompt adaptation.

The Gemini adapter is short and outcome-first. It tells Gemini to execute the embedded source prompt literally, write requested artifacts exactly where specified, preserve absolute artifact paths, avoid side effects outside those artifacts unless explicitly allowed, avoid unavailable shell tools such as `run_shell_command`, keep output concise unless the source prompt asks otherwise, and stop when the source contract is complete or blocked.

## Success Criteria

Gemini-specific signals on top of the shared checks:

- The last parsed stream-json record is a final success result: `type=result` and `status=success`.
- Intermediate error records are acceptable only when followed by a final success result with all expected artifacts materialized; the wrapper records them in `summary.json.nonfatal_reasons`.

## Failure Criteria

Gemini-specific failure signals on top of the shared list:

- `run.stream.jsonl` or `run.err` contains `setRawMode EIO` or `setRawMode EBADF`; treat this as `raw_mode_tty_error`, a noninteractive TTY failure, not as task output.
- stderr contains fatal authentication, model resolution, permission, quota, trust, policy, or rate-limit errors that do not recover into exit `0`, a final success result, and non-empty expected artifacts. Non-empty stderr and recovered CLI warnings alone are not failures when the process exits `0`, stream output is present, the final stream result is successful, and expected artifacts are non-empty.
- The final stream-json record is not a success result.

## No-API Validation

Gemini-specific fake behavior for the shared No-API patterns:

- The fake Gemini CLI must write JSONL stdout and create the expected artifact. Minimal behavior: exit `0`, print one final success JSON object such as `{"type":"result","status":"success"}`, and write the requested expected artifact such as `result.md`.
- Fake Gemini executables run with `process_cwd=--output-dir`, so a relative expected artifact such as `--expected-artifact result.md` can be created by writing `result.md` in the fake script. For wrapper-only validation, the source `prompt.md` may be a minimal valid task contract such as "Write result.md."
- Real Gemini runs also execute with `process_cwd=--output-dir`; verify relative `--gemini-bin` paths against that directory.

## Wrapper Notes

- The wrapper passes `stdin=DEVNULL` to keep `gemini -p` on a noninteractive subprocess path.
- Use `--extra-gemini-arg` for narrow additions when explicitly required. Pass one Gemini CLI token per wrapper argument, for example `--extra-gemini-arg=--sandbox`, `--extra-gemini-arg=--include-directories --extra-gemini-arg=/path/to/dir`, or `--extra-gemini-arg=--policy --extra-gemini-arg=/path/to/policy.md`. If you pass `--include-directories` yourself, include every directory Gemini should access because the wrapper will not add its default target directory include.

## Validation

```bash
scripts/skill-quick-validate skills/gemini-cli-runner
python3 <skill-dir>/scripts/run_gemini_cli.py --help
```

Runtime checks: no-API command construction, no-API fake Gemini success, optional real short smoke prompt when API/auth cost is acceptable, forced timeout failure.
