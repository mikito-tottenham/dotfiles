---
name: grok-cli-runner-x-retrieval
description: Conditional Hermes setup and X/Twitter retrieval contract.
---

# X Retrieval Runbook

## Hermes Setup

Hermes is managed by Homebrew in this dotfiles repo:

```bash
brew install hermes-agent
```

Authenticate Grok through the SuperGrok-backed OAuth provider:

```bash
hermes auth add xai-oauth
```

If the browser cannot open automatically, use:

```bash
hermes auth add xai-oauth --no-browser
```

Useful checks after authentication:

```bash
hermes auth status xai-oauth
hermes --oneshot "Say ok." --provider xai-oauth -m grok-4.3
```

`hermes model` can also be used for the interactive provider/model picker, but the runner passes `--provider xai-oauth` and `-m grok-4.3` per invocation, so global Hermes defaults are not required for this skill.

## X URL Retrieval

When the request contains an X-related URL, build the request so Grok retrieves context before summarizing or answering. Do not answer from URL text alone.

Honor the caller's stated retrieval scope when deciding what the answer must contain and when the task is complete. The wrapper currently runs the fixed full-context probes below for every detected X URL, so a narrow request may still collect broader evidence. Treat those extra fields as incidental: do not surface or require them, and do not fail the task because replies, quote posts, engagement counts, or other out-of-scope fields are unavailable when the requested evidence is sufficient. The scope below remains the output default for full-context or content-and-reactions requests, and when the caller leaves scope unspecified.

Required retrieval scope:

- Original post text, author display name, handle, timestamp, visible media/alt text, linked cards, X Article/longform text, and quoted post.
- Parent posts and the surrounding thread, including earlier and later posts by the author when available.
- Visible replies, quote posts, repost/reply/like/view counts, and notable reactions or community context when available.
- Any access limitation such as login wall, deleted/protected post, rate limit, dynamic rendering failure, or missing engagement data.

Runner behavior:

- The wrapper detects X-related URLs in `request.input`.
- For Hermes runs, the wrapper calls Hermes `x_search_tool` directly before the one-shot summarization and writes `x-search-results.json` under the output directory.
- During direct X retrieval, the wrapper logs progress to stdout and updates `x-search-results.json` before and after each query with `status`, timestamps, and per-query responses. If a query hangs or times out, use the partially written artifact to identify the last running query.
- In `--retrieval-mode x-raw`, the wrapper skips final-answer synthesis and fails if no X URL is present, direct `x_search_tool` is unavailable, or every direct X query fails.
- In `--retrieval-mode answer`, the wrapper may still succeed when final-answer synthesis succeeds, but callers must not treat that prose as raw source evidence when `x-search-results.json.available=false`.
- When `x-search-results.json.available=false`, inspect `x-search-results.json.diagnostics` before retrying. It records Hermes auth status, selected site-packages path, import errors, credential provider, credential presence, `HOME`, `HERMES_HOME`, and `HERMES_PROFILE` so subprocess environment drift is visible. If `check_x_search_requirements()` is false but `hermes auth status xai-oauth` reports logged in, the runner still attempts direct `x_search_tool` calls and records that reason in diagnostics.
- Treat `x-search-results.json` as the primary artifact for post text, Article/card details, media metadata, and engagement counts because it preserves the direct `x_search_tool` JSON response instead of only the model's final prose.
- Use `x-search-results.json.representative_engagement` as the default count source when present. It is selected from the first structured `exact_url_full` result. Later `thread_context` or `reaction_search` answers may show different view counts because engagement changes over time; mention that drift when it matters.
- Treat engagement counts as a time-varying snapshot from the retrieval run, not durable truth. When reporting counts, preserve the artifact and mention snapshot drift if exactness matters.
- For reactions, prefer a compact list of the top 3-5 notable replies, quote posts, or community reactions when available, plus a limitation statement when only aggregate counts are visible.
- When count fields and surfaced items disagree, keep the count from `representative_engagement` as the primary count and report surfaced items as partial examples from the relevant query. Example: "quote_count=1, but concrete quote post details were only surfaced by `reaction_search`" or "count indicates quotes exist, but no quote post items were returned."
- In the final prose, include concrete surfaced items from any successful query (`exact_url_full`, `article_card_context`, `thread_context`, or `reaction_search`) when they are relevant. Label the source query when another query's structured list is empty, instead of discarding the item.
- Classify surrounding posts by relationship evidence: reply-to metadata is a parent, embedded quoted content is a quoted post, same-author nearby posts without reply/quote evidence are thread or surrounding author context. If Hermes output is ambiguous, say which relationship is inferred and why.
- For a generic "content and reactions" request, default to a concise report with: post summary, engagement snapshot, thread/quote/reply context, top 3-5 notable reactions when available, and retrieval limitations.
- For Hermes runs, it injects explicit X retrieval instructions into the one-shot prompt.
- For Hermes runs, it also injects a compact version of `x-search-results.json` into the one-shot prompt so final summaries can include counts reliably.
- For Hermes runs with X URLs, it automatically enables `web,browser,x_search` toolsets for that invocation unless already included.
- If Grok cannot retrieve the full post, Article/card content, thread, or reactions, the caller should report the limitation and preserve the partial evidence in the final answer.
