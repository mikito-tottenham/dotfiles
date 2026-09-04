---
title: "Search Local Repos and GitHub First, Escalate to Google Drive Then Web"
date: 2026-08-26
agent_model: "Claude Code (Claude Fable 5)"
status: accepted
---

# ADR 0058: Search Local Repos and GitHub First, Escalate to Google Drive Then Web

## Context

ファイルや資料の所在を探す依頼で、エージェントが最初から Google Drive・Web 検索・
複数ツールへ並行して探索を広げ、ユーザーから「毎回いろんなファイルとツールを
探しているように見える」との指摘があった（2026-08-26）。

作業対象の多くはローカルの ghq 管理リポジトリまたは GitHub 上に存在するため、
検索先の優先順位が定まっていないことが探索の無駄と観測性低下の原因だった。

## Decision

- 共通ルール正本 `.chezmoitemplates/agents-common.md` に、検索先の段階的
  エスカレーションルールを追加する。これは全リポジトリの Claude / Codex
  セッションに配備される。
  1. まずローカルの ghq 管理リポジトリと GitHub（`gh search code` /
     `gh search repos` 等の CLI）を検索する
  2. 十分な判断材料が得られなかった場合に限り Google Drive を探す
  3. それでも不足する場合に限り Web 検索へ広げる
- 最初から複数の検索先へ並行して探索を広げることを禁止する。

## Consequences

- ファイル所在の探索が Git 管理ソース優先の決定的な順序になり、
  Google Drive・Web への不要なアクセスと探索コストが減る。
- Google Drive にしか存在しない資料の場合、GitHub 検索の 1 段階分だけ
  到達が遅くなるが、判断材料不足の時点でエスカレーションするため影響は軽微。
- 既存の調査ファンアウトルール（複数観点・複数出典の調査委譲）は「誰が実行するか」
  の規定であり、本ルール（どの検索先を先に見るか）と競合しない。
