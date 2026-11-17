---
title: "Present Notes in the Reply Body Instead of Handing the User Markdown Files"
date: 2026-11-17
agent_model: "Claude Code (Claude Opus 5.5)"
status: accepted
---

# ADR 0079: Present Notes in the Reply Body Instead of Handing the User Markdown Files

## Context

Agent はメモ・調査結果・計画などを `.context/` や `docs/` に `.md` で保存し、そのファイルの
リンクやパスだけを示して「こちらを参照」と返すことが多かった。Claude Desktop ではファイル
カードやファイルペインで `.md` を開く形になり、ユーザーにとっては生の Markdown を読むことに
なって見づらい。

2026-11-17 にユーザーから、保存は `.md` のままでよいが、ユーザーへの提示に `.md` ファイルを
使わないルールを dotfiles で全リポジトリに適用するよう指示があった。

## Decision

共通ルール（`.chezmoitemplates/agents-common.md`）に「ユーザーへの提示」の節を追加し、
Claude Code と Codex の両方に次を適用する。

1. メモ・調査結果・要約・計画・レビュー結果などは、内容を返答本文に書いて提示する。
   `.md` ファイルのリンクやパスで参照させる形、`SendUserFile` などで `.md` を送る・開く形は禁止。
2. `.md` での保存は従来どおり可。保存した場合も内容は本文に書き、保存先パスは 1 行添えるだけにする。
3. 本文に収まらない長さの場合は要点を本文に書き、全文が必要なときは HTML（Artifact など）の
   レンダリングされた形で提示する。
4. 例外は、ユーザーが `.md` ファイルそのものを求めた場合と、リポジトリの文書を編集する作業で
   変更対象のファイルを示す場合に限る。

## Alternatives Considered

- **`~/Claude/AGENTS.md` や各リポジトリの指示ファイルに書く**: 一部の作業ディレクトリにしか
  効かない。ユーザーの指示は全リポジトリ対象なので、共通ルールに置く。
- **保存形式も `.md` 以外に変える**: ユーザーは保存は `.md` でよいと明示しており、artifact gate
  （Front Matter 必須）とも整合しないため採らない。
- **hook で `.md` の提示を機械的に止める**: 「提示しているか」は意味の判断であり、hook に
  意味判断を持たせない既存方針（`~/.claude/CLAUDE.md`）に反するため採らない。

## Consequences

- ユーザーはチャット上のレンダリング済みの文面で内容を読める。
- 返答本文が長くなる場合がある。その場合はルール 3 で要点と HTML 提示に分ける。
- Claude Desktop のシステムプロンプトにある「ファイルはリンクで示す」案内とは、`.md` の
  メモ提示に限ってこのルールを優先する。コードファイルの参照リンクは対象外。
