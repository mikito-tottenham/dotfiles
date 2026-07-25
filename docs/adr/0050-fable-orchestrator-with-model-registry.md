---
title: "Route Delegated Work Through agent-orchestrator and a Model Registry"
date: 2026-07-25
agent_model: "Claude Code (Claude Fable 5)"
status: accepted
---

# ADR 0050: Route Delegated Work Through agent-orchestrator and a Model Registry

## Context

runner skill 群(codex / gemini / copilot / grok / claude-cli-runner)と
`agent-orchestration-evaluator` は「role → provider/model は resolver / registry を
参照する」前提で書かれていたが、resolver の実体がどこにも存在しなかった。
そのため親エージェント(Fable / Claude Code)がどのタスクをどのモデルへ
委譲するかは毎回のアドホック判断で、モデル指定も session ごとにばらついていた。

ユーザー要求は「Fable を司令塔にし、余っている Codex クレジットを最高モデルで
使いながら、タスク特性に応じて他モデルへ振り分ける仕組み」。2026-07-25 に
以下を確定した:

- 実装形態: resolver(model registry) + orchestrator skill を publisher layout で新規作成
- Codex メイン実行役: `gpt-5.6-sol` / effort `high`
- 役割分担: 実装・Web 調査・大規模コンテキスト読解・GitHub 連携を含む実行系は
  Codex に集約 / Claude subagent(tech・biz)=レビュー・設計評価・事業判断 /
  Fable=司令塔のみ(同日修正: 当初案にあった Gemini / Grok / Copilot への
  ルーティングはユーザー判断で取りやめ)
- 発動: 常時ルール(CLAUDE.md の委譲基準) + 明示 skill 呼び出しの併用

## Decision

- `skills/agent-orchestrator/` を first-party publisher skill として新設する
  - `rules/model_registry.yaml` を role → provider/model/effort/実行モードの**唯一の正本**
    とする。SKILL.md 本文・他 skill・委譲 prompt にモデル名をハードコードしない
    (evaluator invariant 10)
  - 実行モードは `self`(orchestration 作業のみ)/ `agent_tool`(同 provider subagent、
    Self-Elision)/ `cli_runner`(runner skill 経由の外部 CLI)の 3 種とする
  - subprocess 機構(prompt file / stream log / timeout / summary / failure)は
    引き続き各 runner skill が所有し、registry は選択のみを所有する
- 初期 role: orchestrator(self)、worker(codex 最高モデル・high、Web 調査・
  GitHub 連携を含む実行系全般)、worker_light(同モデル・low、実行専用)、
  reviewer_tech / reviewer_biz / secretary(claude subagent)、
  committer(claude opus、実行系委譲のユーザー指示を registry へ昇格)
- Gemini / Grok / Copilot へは route しない。対応 role が無い依頼
  (例: X(Twitter) 固有調査)は暗黙 fallback せず route 不在として blocked 報告する。
  各 runner skill(gemini / copilot / grok-cli-runner)は他用途のため残置する
- 配備は Claude Code のみ(`gh skill install . agent-orchestrator --from-local
  --agent claude-code --scope user`)。Codex を親にする運用が必要になったら
  codex 配備を別途判断する
- 常時の委譲判断基準は `dot_claude/CLAUDE.md`(Claude Code 固有ルール)に追記し、
  詳細は skill と registry を参照させる。`dot_*` のためこの追記は Codex へ委譲して
  実施する(repo ルール準拠。同時に codex-cli-runner + gpt-5.6-sol 経路の E2E 検証を兼ねる)

## Consequences

- モデル割り当ての変更は registry 1 ファイルの編集 + 再 install に集約され、
  skill 本文の書き換えが不要になる
- 親エージェントの責務が orchestration に限定され、worker 成果物は
  `.context/<task>/` に観測可能な形で残る
- registry は正本(chezmoi repo)と配備先(~/.claude/skills/)の 2 箇所に実体を持つ。
  配備先の直接編集は禁止で、drift は再 install で解消する運用とする
- Codex 側 config(`~/.codex/config.toml`)の既定は変更しない。最高モデル指定は
  委譲時の明示 override として渡すため、対話的な Codex 利用には影響しない
- `docs/skills-install-manifest.md` と `scripts/bootstrap-web` の first-party リスト
  (Claude Code 側)に agent-orchestrator を追加した
