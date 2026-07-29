---
title: "Make agent-orchestrator Independent of the Parent Provider"
date: 2026-07-28
agent_model: "Codex (GPT-5)"
orchestration_agent_model: "Claude Fable 5"
status: accepted
---

# ADR 0052: Make agent-orchestrator Independent of the Parent Provider

## Context

ADR-0050 は Claude Code（Fable）を親司令塔とし、agent-orchestrator を
Claude Code のみに配備する前提だった。

本 ADR は ADR-0050 の以下の条項を改訂する:

- 「配備は Claude Code のみ。Codex を親にする運用が必要になったら codex 配備を
  別途判断する」から、codex 配備を実施する。
- 「常時の委譲判断基準は `dot_claude/CLAUDE.md`（Claude Code 固有ルール）に追記」
  から、`dot_codex/AGENTS.md` の共通ルールへ移設する。
- 「manifest / bootstrap-web の first-party リスト（Claude Code 側）に追加」から、
  Codex 側リストにも追加する。
- reviewer_tech / reviewer_biz / secretary / committer の claude 固定を
  `provider: parent` へ改訂する。ただし committer の Claude 親 tier A pin は維持する。

2026-07-28、ユーザーは「Codex セッションの親は Codex のままとし、ツール間で
親子を作らず、Codex も Claude Code と同等の司令塔として使う」と判断した。
このため、role の論理的な割り当てを維持しつつ、実行経路を親 provider に対して
相対的に解決する必要がある。

## Decision

- registry の role に `provider: parent` を導入し、親と同じ provider の
  subagent 機構で role を実行する。
- `providers.codex.self_elision` を追加し、Claude Code と Codex の
  Self-Elision を対称化する。同 provider は subagent 機構、異なる provider は
  対応する cli_runner を使う。
- reviewer_tech、reviewer_biz、secretary は親 provider の custom agent と
  親 provider 列の tier で解決する。
- committer は Claude Code 親では従来どおり Claude Code 列 tier A に固定する。
  Codex 親では未固定とし、tier B を目安にする。
- agent-orchestrator と agent-orchestration-evaluator を Codex の first-party
  install 対象へ追加する。
- 司令塔の共通ルールを `~/.codex/AGENTS.md` の管理元へ移し、
  `~/.claude/CLAUDE.md` はその共通ルールを import する。

## Consequences

- Claude Code と Codex は、それぞれ自身を親としたまま同じ registry 契約で
  オーケストレーションできる。
- Codex 親から Claude Code 列へ解決した作業は claude-cli-runner を使い、
  Claude Code 親から Codex 列へ解決した作業は codex-cli-runner を使う。
- Codex 親では spawn 時の model / reasoning effort の明示指定で親 provider 列の
  tier を適用する。agent file 側の値は spawn 指定より優先されるため
  `~/.codex/agents/*.toml` には pin しない（解決順の正本は registry の
  `harness_notes`）。必要な context は custom agent の暗黙継承に依存せず
  明示的に渡す。
- install manifest と `AGENTS.md` / `CLAUDE.md` の責務配置が変わる。
- Codex 親では worker も reviewer も同 provider に寄り、クロスモデルレビューの
  性質が失われる。これは意図したトレードオフであり、必要な場合は registry の
  逸脱規則に従い親と異なる provider 列を明示選択する。
- Gemini / Qwen は親 provider として対象外とする。self_elision・runner・skill
  配備が未設計であり、共通ルールの既存 drift は本件と別件として扱う。

## Unresolved

- Codex 親の committer role の model / effort pin はユーザー判断待ち。
- Codex custom agent の model / effort override の live spawn 実挙動は未検証で、
  manual と agent file 状態からの推論に留まる。
- `spawn_agent` callable schema の fork 制約はハーネス版依存の観測であり、
  Codex 更新で無効化されうる。
