---
name: grok-cli-runner-schema
description: Request and response artifact contract for the grok-cli-runner skill.
---

# Artifact Schema

Use UTF-8 JSON files under `.context/<task>/`.
Prefer stable field names over prompt-only conventions so orchestrators can diff and re-run requests safely.

## Request Artifact

Recommended path: `.context/<task>/grok-request.json`

Required top-level fields:

- `task`: stable task identifier
- `request`: object sent to the selected backend after minimal defaulting. The default Hermes backend converts this Responses-style object into a `hermes --oneshot` prompt; explicit `--backend xai-api` sends it to xAI's `/responses` endpoint.

Optional top-level fields:

- `meta`: object for local orchestration notes that should not be sent to xAI

### Request Example

```json
{
  "task": "grok-api-summarize-release-notes",
  "request": {
    "model": "grok-4.3",
    "input": [
      {
        "role": "system",
        "content": "You summarize technical changes tersely."
      },
      {
        "role": "user",
        "content": "次の更新内容を 5 行で要約して: ..."
      }
    ],
    "tools": [
      {
        "type": "web_search"
      }
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "summary",
        "schema": {
          "type": "object",
          "properties": {
            "summary": {
              "type": "string"
            }
          },
          "required": [
            "summary"
          ],
          "additionalProperties": false
        }
      }
    }
  },
  "meta": {
    "purpose": "release note draft"
  }
}
```

### Request Notes

- `request` is passed through almost as-is for explicit direct xAI API calls. For the default Hermes backend, use official xAI Responses API-like fields and shapes so the wrapper can convert them predictably into a one-shot Hermes prompt.
- If `request.model` is omitted, the wrapper fills it from `--model`, then `GROK_MODEL`, then `GROK_X_RESEARCH_MODEL`, then `grok-4.3`.
- `request.input` is required by the wrapper for both Hermes prompt conversion and direct xAI Responses API calls.
- For schema-constrained JSON, use `request.response_format`; the wrapper passes it through and does not validate returned JSON.
- If `request.input` contains X-related URLs such as `x.com`, `twitter.com`, `mobile.twitter.com`, or Nitter URLs, the Hermes prompt conversion adds retrieval requirements for the post text, thread, replies, quote posts, engagement counts, and notable reactions.
- For Hermes runs with X-related URLs, the wrapper writes `x-search-results.json` with direct Hermes `x_search_tool` results before generating `grok-response.json`.
- `meta` stays local in the artifact and is never sent to xAI.

## Response Artifact

Recommended path: `.context/<task>/grok-response.json`

Required fields:

- `task`: copied from the request artifact
- `created_at`: UTC timestamp for the wrapper run
- `meta`: copied from the request artifact when present
- `request`: normalized payload used by the selected backend
- `response`: raw xAI API response object for direct API calls, or synthetic Hermes response metadata for Hermes calls
- `output_text`: extracted or captured final response text when available
- `response_id`: copied from `response.id` when present
- `model`: copied from `response.model` when present, otherwise from `request.model`
- `backend`: present for Hermes responses and set to `hermes`

### Response Notes

- `output_text` may be `null` when the response does not contain plain text output.
- The wrapper does not attempt to coerce structured output beyond extracting `output_text`.
- Hermes responses are normalized from final stdout into a synthetic `response` object with `type: hermes_final_response`.
- For Hermes responses, `response.toolsets` records any per-invocation toolsets automatically added for retrieval, such as `web,browser,x_search` for X URLs.
- If you request schema-constrained JSON with `request.response_format`, parse `output_text` in the orchestrator and handle validation there.

## X Search Artifact

Recommended path: `.context/<task>/x-search-results.json`

Written only when X-related URLs are detected and the selected backend is Hermes.

Fields:

- `created_at`: UTC timestamp
- `tool`: `hermes_x_search_tool`
- `x_urls`: detected X-related URLs
- `available`: whether Hermes `x_search_tool` credentials/checks passed
- `queries`: direct `x_search_tool` probes, normally `exact_url_counts`, `thread_context`, and `reaction_search`
- `queries[].response`: JSON returned by Hermes `x_search_tool`, including `credential_source`, `model`, `answer`, `citations`, and `inline_citations`
- `queries[].parsed_answer`: parsed JSON when Grok returned JSON in `answer`, otherwise `null`
- `representative_engagement`: default engagement/count source selected from the first structured `exact_url_counts` parsed answer
- `representative_engagement.snapshot_note`: reminder that engagement counts are a time-varying snapshot

`reaction_search` should aim to capture a compact top 3-5 notable replies, quote posts, or community reactions when available. Some X responses only expose aggregate counts; preserve that limitation in the final answer.

When aggregate counts and surfaced items disagree, do not overwrite the count or invent missing items. Use `representative_engagement` for the count snapshot and describe surfaced items as partial examples from `thread_context` or `reaction_search`.

Final prose should include concrete surfaced items from any successful query when relevant. If `exact_url_counts.quote_posts` is empty but `reaction_search` surfaces a quote post, report it as source-labeled partial evidence from `reaction_search`.

Use this artifact as the source of truth for engagement counts when present.
