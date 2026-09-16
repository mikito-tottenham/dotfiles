---
name: copilot-cli-runner
description: Run `copilot -p` through an observable file-backed wrapper with timeout, permission, and failure artifacts. Use when Claude Code or Codex must invoke GitHub Copilot CLI as a subprocess; ordinary research, review, or file work that does not require Copilot CLI should use its owning workflow. Use when asked to CopilotをCLIで呼ぶ or Copilot CLIをサブプロセス実行する.
---

# Copilot CLI Runner

Use this skill when delegating work to GitHub Copilot CLI through non-interactive `copilot -p`. Keep the source prompt, launch prompt, JSONL output, stderr, summary, and failure notes under `.context/<task>/`.

Shared runner contract (outcome-first delegation, prompt files, expected-artifact resolution, wrapper artifacts, success/failure semantics, No-API validation): read [references/runner-common.md](references/runner-common.md). This file covers only Copilot-specific behavior.

## Core Rules

- Use `copilot -p <prompt> --output-format json` for observable non-interactive runs.
- Use the wrapper's 600-second timeout default, or pass an explicit timeout override when the task needs a shorter or longer limit.
- Do not force `--allow-all`, `--allow-all-tools`, `--allow-all-paths`, `--allow-all-urls`, `--yolo`, or broad permissions by default. Let Copilot config decide unless the caller explicitly requests an override.

## Caller Checklist

In addition to the shared contract, decide these explicitly before running Copilot:

- Defaults: omit `--model`, `--effort`, and `--agent` unless the caller, model registry, role, or task explicitly requires an override.
- Permissions: add `--allow-tool`, `--allow-url`, `--add-dir`, or broader flags only when explicitly required by the caller. Non-interactive tasks that need tools should receive explicit narrow grants; prefer those over `--allow-all`.
- Timeout: rely on the 600-second wrapper default unless the task contract says otherwise.
- Prompt profile: use `--prompt-profile auto` by default; pass `--prompt-profile none` only when the source prompt already contains a complete Copilot-specific launch contract.
- Extra Copilot args: one token per `--extra-copilot-arg=<token>`.

## Standard Command Shape

Use this form, with `<prompt>` kept short and pointing to the generated launch prompt:

```bash
timeout 600 copilot -p "<prompt>" --output-format json > <artifact>.events.jsonl 2> <artifact>.err
```

For repeatable runs, prefer the bundled wrapper:

```bash
python3 <skill-dir>/scripts/run_copilot_cli.py \
  --prompt-file .context/<task>/prompt.md \
  --output-dir .context/<task> \
  --expected-artifact <expected-file>
```

Add `--model <model>`, `--effort <low|medium|high|xhigh>`, or `--agent <agent>` only when overriding Copilot CLI defaults.
Add `--timeout-seconds <seconds>` only when overriding the 600-second default.

Beyond the shared artifact set, the wrapper writes:

- `run.events.jsonl`: Copilot JSONL stdout events
- `summary.json` extras: `events_bytes`, `stderr_bytes`, `last_error_event` or `last_event`

## Prompt Profiles

The wrapper writes `.context/<task>/run.prompt.md`, then passes only a file-reference prompt to `copilot -p`.

Default behavior:

- `--prompt-profile auto` is the default and applies the Copilot adapter.
- `--prompt-profile copilot` forces the Copilot adapter.
- `--prompt-profile none` suppresses prompt adaptation.

The Copilot adapter is short and outcome-first. It tells Copilot to execute the source prompt literally, write requested artifacts exactly where specified, respect allowed side effects, keep output concise unless the source prompt asks otherwise, and stop when the source contract is complete or blocked.

## Failure Criteria

Copilot-specific failure signals on top of the shared list:

- stderr contains authentication, login, model, permission, quota, policy, path, tool, URL, or rate-limit errors.
- Copilot exits because a required non-interactive tool, path, or URL permission was not granted.

## No-API Validation

Copilot-specific fake behavior for the shared No-API patterns:

- The fake Copilot CLI must write JSONL stdout and create the expected artifact.

## Wrapper Notes

- Pass `--model <model>`, `--effort <level>`, and `--agent <agent>` from the caller when a model registry, role, or task explicitly requires overrides.
- Use `--extra-copilot-arg` for narrow additions when explicitly required. Pass one Copilot CLI token per wrapper argument, for example `--extra-copilot-arg=--allow-tool --extra-copilot-arg=shell(git)`, `--extra-copilot-arg=--add-dir --extra-copilot-arg=/path/to/dir`, or `--extra-copilot-arg=--allow-url --extra-copilot-arg=github.com`.

## Validation

```bash
scripts/skill-quick-validate skills/copilot-cli-runner
python3 <skill-dir>/scripts/run_copilot_cli.py --help
```

Runtime checks: no-API command construction, no-API fake Copilot success, optional real short smoke prompt when auth/cost is acceptable, forced timeout failure.
