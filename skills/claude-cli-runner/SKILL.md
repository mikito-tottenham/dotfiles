---
name: claude-cli-runner
description: Run `claude -p` through an observable file-backed wrapper with timeout and failure artifacts. Use when Codex must invoke Claude Code CLI as a subprocess; ordinary research or review that does not require Claude CLI should use its owning workflow. Use when asked to ClaudeをCLIで呼ぶ or Claude CLIをサブプロセス実行する.
---

# Claude CLI Runner

Use this skill to invoke Claude Code CLI from Codex without losing observability during long-running work. Treat it as the standard wrapper for model-registry calls that delegate research, review, generation, or other CLI work to `claude -p`.

Shared runner contract (outcome-first delegation, prompt files, expected-artifact resolution, wrapper artifacts, success/failure semantics, No-API validation): read [references/runner-common.md](references/runner-common.md). This file covers only Claude-specific behavior.

## Execution Policy

- Treat this skill as a reusable Claude CLI wrapper, not as the owner of higher-level orchestration policy.
- Treat model resolver outputs as role/model metadata, not as permission to hand-build raw `claude -p` commands.
- When a workflow previously said "run Claude via resolver", resolve the requested Claude model/effort if needed, then execute Claude through this skill and its wrapper.
- Let the calling workflow decide whether this skill is run directly or through a subagent; that policy belongs to the caller, not here.

## Core Rules

- Do not use normal text output for long-running `claude -p` tasks. It can keep stdout/stderr empty until completion and look hung.
- Use the wrapper's 600-second timeout default, or pass an explicit timeout override when the task needs a shorter or longer limit.
- The wrapper always passes `--permission-mode bypassPermissions` because the run is non-interactive (no TTY to answer permission prompts); constrain side effects through the source prompt's allowed-side-effects contract and, when needed, `--extra-claude-arg=--tools <list>` or `--add-dir`.
- For research tasks, explicitly limit WebSearch/WebFetch counts, timeout, and output lines in the prompt.

## Caller Checklist

In addition to the shared contract, decide these explicitly before running Claude:

- Defaults: omit `--model` and `--effort` unless the caller, model registry, or role explicitly requires an override. `--effort` accepts `low|medium|high|xhigh|max` (`claude --help`, 2026-09-15) and is passed through unchanged.
- Timeout and budget: rely on the 600-second timeout default and omit `--budget-usd` unless the caller explicitly needs a budget guard.
- Prompt profile: use `--prompt-profile auto` by default; pass `--prompt-profile none` only when the source prompt already contains a complete Claude-specific launch contract.

## Standard Command Shape

Use this form, with `<prompt>` kept short and pointing to the prompt file:

```bash
timeout 600 claude -p --permission-mode bypassPermissions --verbose --output-format stream-json --include-partial-messages "<prompt>" > <artifact>.stream.jsonl 2> <artifact>.err
```

For repeatable runs, prefer the bundled wrapper:

```bash
python3 <skill-dir>/scripts/run_claude_cli.py \
  --prompt-file .context/<task>/prompt.md \
  --output-dir .context/<task> \
  --expected-artifact <expected-file>
```

Add `--model <model>` or `--effort <low|medium|high|xhigh|max>` to the wrapper only when overriding the CLI defaults.
Add `--timeout-seconds <seconds>` only when overriding the 600-second default.
Add `--budget-usd <amount>` only when an explicit API budget guard is required. Omit it for subscription-based Claude CLI usage.

Beyond the shared artifact set, the wrapper writes:

- `run.stream.jsonl`: Claude stream-json stdout
- `summary.json` extras: parsed result/error status from the final stream-json object

## Prompt Profiles

The wrapper writes a short launch prompt at `.context/<task>/run.prompt.md`, then passes only a file-reference prompt to `claude -p`.

Default behavior:

- `--prompt-profile auto` is the default and applies the Claude adapter.
- `--prompt-profile claude` forces the Claude adapter.
- `--prompt-profile none` suppresses prompt adaptation.

The Claude adapter is short, model-agnostic, and positive. It tells Claude to execute the source prompt literally, avoid fixed progress scaffolding, avoid unnecessary subagents/tool calls, preserve coverage in review/finding phases, respect explicit tool/output limits, and rely on the CLI `--effort` setting instead of prompt magic words. The adapter does not branch on the model name; `--model` and `--effort` come from the caller (normally the model registry) and are passed through unchanged.

## Success Criteria

Claude-specific signal on top of the shared checks:

- The stream-json log has a final JSON object with `type=result` and `subtype=success`.

## Failure Criteria

Claude-specific failure signals on top of the shared list:

- stream-json contains a `type=result` object whose `subtype` starts with `error`, including values such as `error_max_budget_usd`.
- `failure.md` includes the last stream-json result or error.

## Prompt Pattern

Create `.context/<task>/prompt.md` with the real assignment, constraints, and expected artifact paths. Then invoke Claude with a short prompt like:

```text
Read and follow the prompt in /absolute/path/to/.context/<task>/prompt.md. Write the requested artifacts exactly where specified.
```

For Claude researcher roles, include:

- max WebSearch/WebFetch calls
- max output lines or words
- timeout expectation
- exact output artifact path
- instruction to stop and write findings instead of continuing if blocked

## Wrapper Notes

- Use `--extra-claude-arg` for narrow additions such as `--tools` or `--add-dir` when needed.

## No-API Validation

Claude-specific fake behavior for the shared No-API patterns:

- The fake Claude CLI must write stream-json stdout ending with `{"type":"result","subtype":"success"}` and create the expected artifact. Minimal behavior: exit `0`, print `{"type":"result","subtype":"success"}` as the final stdout line, and write the requested expected artifact such as `result.md`.

## Validation

```bash
scripts/skill-quick-validate skills/claude-cli-runner
python3 <skill-dir>/scripts/run_claude_cli.py --help
```

Runtime checks: a short smoke prompt, a prompt that reads and writes a file, a small WebSearch prompt with strict tool, timeout, and output limits, and a forced timeout prompt that must generate `failure.md`.
