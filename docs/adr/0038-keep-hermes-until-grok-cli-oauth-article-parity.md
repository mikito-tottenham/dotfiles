---
title: "ADR 0038: Grok CLI OAuth は Article 取得 parity まで Hermes 代替にしない"
status: accepted
date: 2026-05-26
worked_at: 2026-05-26 13:58 JST
agent_model: GPT-5 Codex
---

# ADR 0038: Grok CLI OAuth は Article 取得 parity まで Hermes 代替にしない

## Context

公式 `@xai-official/grok` CLI 0.1.219 を API key 経路と OAuth 経路で smoke した。
API key 経路では `grok-4.3` の通常回答は動くが、X URL retrieval は露出しなかった。
OAuth 経路では `grok.com` ログインとして動き、public X post に対して `x_thread_fetch` が使われ、本文と visible engagement counts は取得できた。

一方で、X Article 直リンクと Article 添付 post を使った smoke では、Article 本文全文や完全性判定を安定して取得できなかった。
また、ログイン済み X Bookmarks については bookmark 専用 tool が見えず、アクセス不可と判断した。

## Decision

- 現時点では `grok-cli-runner` の Hermes backend を公式 Grok CLI OAuth backend で代替しない。
- X Article 本文全文が公式 Grok CLI OAuth で安定取得できるようになった場合に、Hermes 代替を再検討する。
- X Bookmarks が公式 Grok CLI OAuth で取得できるようになった場合は、全面代替ではなく Bookmarks 用の部分利用として扱う。
- public X post の本文、thread、visible counts の answer-mode 補助 backend としては、将来 `grok-cli-oauth` backend を追加候補にできる。
- `x-search-results.json` 全体の再現は必須要件にしないが、Article 本文全文と取得完全性は代替判断の必須要件にする。

## Consequences

- `x-raw` や X Article を含む調査では、引き続き Hermes `x_search_tool` または同等の raw / Article 取得 backend を使う。
- 公式 Grok CLI OAuth は public post/thread/count の簡易取得には有望だが、Article と Bookmarks の要件を満たすまで既定 backend にはしない。
- 将来の再評価では、Article 直リンクと Article 添付 post の両方で本文全文、文字数、truncation evidence、limitation を検証する。
- Bookmarks は private / account-scoped data として扱い、明示的な bookmark tool または endpoint が確認できるまで Grok CLI OAuth では扱わない。
