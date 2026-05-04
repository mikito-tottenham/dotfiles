---
name: gemini-cli-runner
description: Run Gemini CLI subprocesses with observable stream-json logs, timeouts, config-preserving model and approval controls, prompt profiles, and artifact-based failure handling. Use when Claude Code or Codex needs to invoke `gemini -p`, call Gemini from the CLI, GeminiをCLIで呼ぶ, Gemini CLIをサブプロセス実行する, or delegate long-running research, review, generation, or file work to Gemini while distinguishing real hangs from silent execution.
---

# Gemini CLI Runner

Use this skill when delegating work to Gemini CLI through non-interactive `gemini -p`. Keep the source prompt, launch prompt, stream-json output, stderr, summary, and failure notes under `.context/<task>/`.

Frame each delegation as an outcome-first contract: source prompt, expected artifacts, timeout, success criteria, allowed side effects, evidence rules, output shape, and failure handling. Let caller-provided model, approval mode, Gemini config, and explicit extra args control model selection and permission policy.

## Core Rules

- Use `gemini -p <prompt> --output-format stream-json` for observable non-interactive runs.
- Put every run under `.context/<task>/`.
- Save the real assignment as `.context/<task>/prompt.md`.
- Do not pass a large prompt body as an inline shell argument. Pass a short instruction that tells Gemini to read `.context/<task>/run.prompt.md`.
- Use the wrapper's 600-second timeout default, or pass an explicit timeout override when the task needs a shorter or longer limit.
- Do not force `--sandbox`, `--yolo`, `--approval-mode`, trust, policy, or tool flags by default. Let Gemini config decide unless the caller explicitly requests an override.
- Do not treat 0-byte `run.stream.jsonl` or `run.err` as a hang by itself.

## Caller Checklist

Before running Gemini, make these decisions explicitly:

- Task directory: choose `.context/<task>/`.
- Source prompt: write `.context/<task>/prompt.md` with the outcome, artifact paths, success criteria, allowed side effects, evidence rules, and stop condition.
- Working directory: pass `--cwd <project-root>` when the target repository matters.
- Expected artifacts: pass every required output with `--expected-artifact`; relative paths resolve from `--output-dir`, so use absolute paths for artifacts that must be written outside `.context/<task>/`.
- When `--output-dir .context/<task>` is used, pass `--expected-artifact result.md`, not `--expected-artifact .context/<task>/result.md`; the latter resolves under `.context/<task>/.context/<task>/`.
- Defaults: omit `--model` and `--approval-mode` unless the caller, model registry, role, or task explicitly requires an override.
- Timeout: rely on the 600-second wrapper default unless the task contract says otherwise.
- Prompt profile: use `--prompt-profile auto` by default; pass `--prompt-profile none` only when the source prompt already contains a complete Gemini-specific launch contract.
- Extra Gemini args: pass each Gemini CLI token as its own `--extra-gemini-arg=<token>` value, especially for leading-hyphen tokens.

Do not add "think hard", fixed progress-update scaffolds, or mandatory step-by-step narration to simulate model effort. If the Gemini CLI later exposes an effort or thinking control, pass it as an explicit CLI/config override rather than prompt magic words.

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

The wrapper writes:

- `run.prompt.md`: launch prompt sent to Gemini, including any prompt profile adapter
- `run.stream.jsonl`: Gemini stream-json stdout
- `run.err`: stderr
- `summary.json`: command, exit code, elapsed time, byte counts, parsed errors, prompt profile, `failure_reasons`, `recommended_next_action`, and `expected_artifacts`
- `failure.md`: only when the wrapper run fails

## Prompt Profiles

The wrapper writes `.context/<task>/run.prompt.md`, then passes only a file-reference prompt to `gemini -p`.

Default behavior:

- `--prompt-profile auto` is the default and applies the Gemini adapter.
- `--prompt-profile gemini` forces the Gemini adapter.
- `--prompt-profile none` suppresses prompt adaptation.

The Gemini adapter is short and outcome-first. It tells Gemini to execute the source prompt literally, write requested artifacts exactly where specified, respect allowed side effects, keep output concise unless the source prompt asks otherwise, and stop when the source contract is complete or blocked.

## Success Criteria

Require all applicable checks:

- Process exit code is `0`.
- `run.stream.jsonl` exists and is non-empty.
- Every expected artifact exists and is non-empty.
- Parsed stream-json records do not contain obvious error records.
- `summary.json.success` is `true`, `summary.json.failure_reasons` is empty, and every item in `summary.json.expected_artifacts` has `exists=true` and `non_empty=true`.

## Failure Criteria

Treat any of these as failure:

- Timeout exit, normally exit code `124`.
- Non-zero process exit.
- stderr contains authentication, model, permission, quota, trust, policy, or rate-limit errors.
- Parsed stream-json records contain obvious error records.
- `run.stream.jsonl` is missing or empty.
- Expected artifacts are missing or empty.

On failure, inspect `.context/<task>/summary.json` first:

- `command`
- `exit_code`
- `elapsed_seconds`
- `stream_bytes` and `stderr_bytes`
- `failure_reasons`
- `last_error_record` or `last_stream_record`
- `expected_artifacts`
- `recommended_next_action`

The wrapper also writes `.context/<task>/failure.md` with:

- executed command
- exit code
- elapsed time
- stream/stderr sizes
- last error or stream record
- expected artifact status
- recommended next action

## No-API Validation

Use these patterns when testing the wrapper itself without spending Gemini API budget:

- For command-construction checks only, pass `--timeout-bin /usr/bin/true`. This bypasses Gemini entirely and should fail wrapper success checks because no stream-json output or expected artifact is produced.
- For end-to-end wrapper success without API spend, create a small fake Gemini executable under `.context/<task>/bin/` and pass it with `--gemini-bin <path-to-fake-gemini>`. The fake CLI must write JSONL stdout and create the expected artifact.
- Keep fake CLIs under `.context/<task>/bin/` and use them only in validation. Do not use `--gemini-bin` for real Gemini delegation.
- Do not hand-edit `summary.json`, `run.stream.jsonl`, `run.err`, or `failure.md`. If a controlled test needs explanation, write a separate `notes.md`.

## Wrapper Notes

- Resolve `<skill-dir>` from the location of this `SKILL.md`.
- Pass `--cwd <project-root>` when Gemini should run from a specific repository.
- Omit `--model` and `--approval-mode` by default so Gemini CLI uses its configured defaults.
- Pass `--model <model>` and `--approval-mode <mode>` from the caller when a model registry, role, or task explicitly requires overrides.
- Pass each expected output as `--expected-artifact`; use an absolute path or a path relative to the wrapper output directory. If the artifact is directly inside `.context/<task>/`, pass only the filename.
- Use `--extra-gemini-arg` for narrow additions when explicitly required. Pass one Gemini CLI token per wrapper argument, for example `--extra-gemini-arg=--sandbox`, `--extra-gemini-arg=--include-directories --extra-gemini-arg=/path/to/dir`, or `--extra-gemini-arg=--policy --extra-gemini-arg=/path/to/policy.md`.
- Keep final orchestration in the caller. This skill only runs Gemini and records observable artifacts.

## Validation

Validate the skill and wrapper after changes:

```bash
scripts/skill-quick-validate skills/gemini-cli-runner
python3 <skill-dir>/scripts/run_gemini_cli.py --help
```

For runtime validation, run:

- no-API command construction
- no-API fake Gemini success
- optional real short smoke prompt when API/auth cost is acceptable
- forced timeout failure
