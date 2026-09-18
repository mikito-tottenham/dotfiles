---
name: soundcore-minutes
description: Retrieve transcripts, summaries, and meeting minutes from Anker Soundcore Work or Soundcore AI at ai.soundcore.com using an authenticated browser session. Use when the user mentions Soundcore Work, Soundcore AI, Anker AI voice recorder, ai.soundcore.com, or asks Codex or Claude in Chrome to collect minutes from the Soundcore web UI where no external API is available.
---

# Soundcore Minutes

Use this skill to operate the Soundcore AI web UI and turn a selected recording into usable minutes. The site has no public API, so treat the browser UI as the source of truth and avoid inventing fields that are not visible.

## Tool Choice

- Prefer Chrome when the user likely needs their existing login session, cookies, password manager, or MFA state.
- Use Codex App Browser when the user explicitly asks for it, is already logged in there, or wants the work done in the in-app browser.
- If neither browser session is authenticated, open `https://ai.soundcore.com/home`, pause for the user to complete login, then continue after the UI is available.
- Do not ask for Soundcore credentials. Let the user perform authentication directly in the browser.

## Workflow

1. Open `https://ai.soundcore.com/home` in the selected browser tool.
2. Confirm the page is authenticated and shows the recording library or equivalent home view.
3. Identify the target recording from the user's criteria: title, date, time, duration, participants, matter name, or the most recent recording.
4. Open the target recording and wait until the transcript and summary panes finish loading.
5. Capture visible metadata, summary, action items, topics, speakers, and transcript text.
6. If the UI paginates, lazy-loads, collapses, or virtualizes the transcript, scroll through the entire transcript area and collect all visible segments.
7. Produce minutes from extracted content only. Mark unavailable fields as `未確認` instead of guessing.
8. Include the source recording identifier in the final answer: visible title plus date/time or URL when available.

## Extraction Rules

- Preserve speaker labels and timestamps when Soundcore provides them.
- Keep the raw transcript separate from the cleaned minutes when the user asks for both.
- If Soundcore provides both an AI summary and full transcript, use the transcript to verify and enrich the summary.
- When multiple recordings match the user's criteria, list the candidates and ask the user to choose before extracting confidential content.
- Do not store transcript content in repo files, `.context/`, or logs unless the user explicitly asks for a file artifact.
- If creating a file artifact, ask for or infer a destination inside the current workspace; do not write sensitive minutes to `/tmp` or unrelated folders.
- If the browser tool cannot read a virtualized transcript reliably, use the site's visible export, copy, or download controls when available. Confirm with the user before triggering downloads.

## Extraction Notes

Observed on the Soundcore Online Hub (`https://ai.soundcore.com/home`) with Claude in Chrome on 2026-09-18. They refine the Workflow above for that combination; re-check them if the UI or the browser tool changes.

- Each row in the recording list shows `YYYY-MM-DD HH:MM:SS | <duration>`. Identify the target by date and time (Workflow step 3) and reuse the meeting-name label exactly as Soundcore displays it.
- A recording without a transcript shows a 「生成」 (generate) button. Generating consumes the user's transcription quota in minutes, so never click it without an explicit instruction from the user.
- Opening a recording shows only the AI summary. Click the rightmost icon in the top-right icon row (tooltip 「文字起こしを表示／非表示」) to open the speaker-labeled transcript in the right pane; this is the pane Workflow step 4 waits for. Reloading the page closes it again.
- The transcript pane is not virtualized: every segment was already in the DOM (186 segments for a 34-minute recording), so the scroll-through in Workflow step 6 was not needed. To get one segment block, start from a leaf element whose text matches `/^speaker\s?\d+$/` and walk up its ancestors until `innerText` has at least three non-empty lines (speaker, `HH:MM:SS` timestamp, body).
- `javascript_tool` return values are cut at about 1,000 characters (`[TRUNCATED]`), values containing URLs or query strings such as `outerHTML` come back as `[BLOCKED: Cookie/query string data]`, and returning an async IIFE directly yields `{}`; use top-level `await`, or store the result in a `window` variable and read it in a separate call.
- To read the full transcript in one call, insert the formatted segments as a temporary `<article>` (one `<p>` per segment) at the start of `document.body`, read it with `get_page_text` (about 16,000 characters came back untruncated), then remove the element.
- Do not pass text to the local side through `navigator.clipboard.writeText` or `document.execCommand('copy')`: without a user gesture the write fails and the user's clipboard stays unchanged.
- When the user asked for a file artifact (for example a TSV of speaker, time, and text) and needs a verbatim guarantee, compute per segment the UTF-16 code unit count and the sum of code units mod 9973 from the saved file, embed that checksum list in the JS you run, compare it against the DOM in the browser, and return only the mismatching indexes so the result stays short enough not to be truncated. 186/186 segments matched in the observed run.

## Output

For normal meeting minutes, use the concise Japanese format in [references/output-formats.md](references/output-formats.md). Load that reference when writing final minutes, creating a reusable template, or deciding how to handle missing fields.

Default final response:

- State the source recording.
- Provide the minutes in Japanese unless the user requested another language.
- Separate decisions, action items, open issues, and notable discussion points.
- Mention any extraction gaps, such as inaccessible transcript sections, missing speaker labels, or partial loading.

## Validation

When updating this skill, run:

```bash
scripts/skill-quick-validate skills/soundcore-minutes
```
