# Runner Common Contract

Shared contract for the `codex-cli-runner`, `claude-cli-runner`, `gemini-cli-runner`, and `copilot-cli-runner` skills. Each skill ships an identical copy of this file so it stays usable when installed alone; `scripts/skill-quick-validate` in the dotfiles repo checks that the copies match. Provider-specific behavior (CLI flags, stream formats, watchdogs, cwd handling, extra failure signals) stays in each skill's `SKILL.md`.

Read this file once per delegation session; the `SKILL.md` of each runner assumes it.

## Delegation Contract

- Frame each delegation as an outcome-first contract: source prompt, expected artifacts, timeout, success criteria, allowed side effects, evidence rules, output shape, and failure handling.
- Let caller-provided model, effort, profile, and CLI config do model selection and permission policy. Do not encode model behavior with magic words in the source prompt.
- Do not add "think hard", fixed progress-update scaffolds, or mandatory step-by-step narration to simulate effort. Pass effort or thinking controls only as explicit CLI/config overrides when the caller asks for them.
- Keep final orchestration in the caller. A runner skill only runs the CLI and records observable artifacts.

## Prompt Files

- Put every run under `.context/<task>/`.
- Save the real assignment as `.context/<task>/prompt.md` with the outcome, artifact paths, success criteria, allowed side effects, evidence rules, and stop condition. If an expected artifact path is absolute, put that same absolute path in the source prompt; `--expected-artifact` only verifies materialization.
- Do not pass a large prompt body as an inline shell argument. The wrapper writes the launch prompt to `.context/<task>/run.prompt.md` (including any prompt profile adapter) and passes only a short instruction that tells the CLI to read that file.
- Pass `--cwd <project-root>` when the target repository matters. `summary.json` records the resolved cwd; the shell directory that launched the wrapper is not recorded as a separate field.
- Resolve `<skill-dir>` from the location of the skill's `SKILL.md`.

## Expected Artifacts

- Pass every required output with `--expected-artifact`; relative paths resolve from `--output-dir`, so use absolute paths for artifacts that must be written outside `.context/<task>/`. If the artifact is directly inside `.context/<task>/`, pass only the filename.
- When `--output-dir .context/<task>` is used, pass `--expected-artifact result.md`, not `--expected-artifact .context/<task>/result.md`; the latter resolves under `.context/<task>/.context/<task>/`.

## Defaults And Overrides

- Omit `--model`, `--effort`, and other provider selectors by default so the CLI uses its configured defaults.
- Pass `--model <model>` and `--effort <level>` from the caller only when a model registry, role, or task explicitly requires overrides. The wrapper passes those values through unchanged and does not branch on the model name.
- Extra CLI args: pass each CLI token as its own `--extra-<tool>-arg=<token>` value, especially for leading-hyphen tokens. Use them only for narrow, explicitly required additions.
- Do not treat a 0-byte stream log or `run.err` as a hang by itself.

## Wrapper Artifacts

Every wrapper writes, under `--output-dir`:

- `run.prompt.md`: launch prompt sent to the CLI, including any prompt profile adapter
- `run.events.jsonl` or `run.stream.jsonl`: CLI stdout events
- `run.err`: stderr
- `summary.json`: command, resolved cwd, exit code, elapsed time, byte counts, parsed errors, prompt profile, `failure_reasons`, `recommended_next_action`, and `expected_artifacts`
- `failure.md`: only when the wrapper run fails, with the executed command, exit code, elapsed time, output sizes, last error or event, expected artifact status, and recommended next action

Do not hand-edit `summary.json`, `run.*`, `last-message.md`, or `failure.md`. If a controlled test needs explanation, write a separate `notes.md` next to the wrapper artifacts.

## Success Criteria

Require all applicable checks:

- Process exit code is `0`.
- The stream/events log exists and is non-empty.
- Every expected artifact exists and is non-empty.
- Parsed stream records do not contain obvious error records.
- `summary.json.success` is `true`, `summary.json.failure_reasons` is empty, and every item in `summary.json.expected_artifacts` has `exists=true` and `non_empty=true`.

These checks prove runner execution and non-empty artifact materialization only. The caller must still evaluate task-specific artifact quality against the source prompt.

## Failure Criteria

Treat any of these as failure:

- Timeout exit, normally exit code `124`.
- Non-zero process exit for any reason other than an explicitly accepted test case.
- stderr contains authentication, model, permission, quota, or rate-limit error patterns and the run lacks an independent success signal.
- Parsed stream records contain obvious error records.
- The stream/events log is missing or empty.
- Expected artifacts are missing or empty.

On failure, inspect `.context/<task>/summary.json` first (`command`, cwd, `exit_code`, `elapsed_seconds`, byte counts, `failure_reasons`, last error or event, `expected_artifacts`, `recommended_next_action`), then `failure.md` for the expanded evidence.

If a higher-level workflow needs a downstream blocked artifact, create it in the caller using that workflow's schema or template. Do not invent a downstream schema in the runner and do not modify runner evidence artifacts. If no caller schema was supplied, report the runner as blocked with links to `summary.json` and `failure.md` instead of fabricating an artifact format.

## No-API Validation

Use these patterns when testing a wrapper itself without spending API budget:

- For command-construction checks only, pass `--timeout-bin /usr/bin/true`. This bypasses the CLI entirely and should fail wrapper success checks because no stream output, final message, or expected artifact is produced.
- For end-to-end wrapper success without API spend, create a small fake CLI executable under `.context/<task>/bin/` and pass it with `--<tool>-bin <path-to-fake-cli>`. The fake CLI must write the provider's stream format to stdout and create the expected artifact; the minimal fake output for each provider is listed in its `SKILL.md`.
- Prefer an absolute `--<tool>-bin` path for fake CLIs unless you have verified the relative path resolves from the wrapper's process cwd.
- Keep fake CLIs under `.context/<task>/bin/` and use them only in validation. Do not use `--<tool>-bin` for real delegation.

## Validation

After changing a runner skill, run `scripts/skill-quick-validate skills/<runner>` and `python3 <skill-dir>/scripts/run_<tool>_cli.py --help`, then the runtime checks listed in that skill's Validation section (no-API command construction, no-API fake CLI success, forced timeout failure, and any provider-specific checks).
