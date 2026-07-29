---
title: "Route Delegated Work Through agent-orchestrator and a Model Registry"
date: 2026-07-25
agent_model: "Claude Code (Claude Fable 5)"
status: accepted
---

# ADR 0050: Route Delegated Work Through agent-orchestrator and a Model Registry

2026-07-28: Claude 限定の条項 (codex 配備の別途判断、CLAUDE.md への追記先、claude 固定の role 定義) は ADR-0052 で改訂された。

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
- worker は固定 role→モデルではなく **worker tier ladder** とする(同日修正)。
  Claude と GPT を同一の賢さ軸に並べた S/A/B/C の 4 tier を registry に定義し、
  各 tier に codex 列(gpt-5.6-sol + effort ダイヤル、最軽量 tier のみ luna)と
  claude 列(fable / opus / sonnet / haiku)を併記する。親オーケストレータが
  タスク内容から tier を毎回推論する(基準は registry に明文化、判断は動的)
  - ladder は機械的な規則ではなく**統一軸(目安)**とする(同日修正)。親は
    skill 同梱の `references/model-profiles.md`(モデル特性の living document、
    実測メモ含む)をいつでも判断材料に参照し、柔軟に tier / provider 列を選ぶ。
    目安からの逸脱は理由を記録する
  - 目安: 迷ったら 1 段下から / blocked・品質不足で 1 段昇格して再委譲 /
    同 tier 内は codex 寄せ(クレジット余剰)、Claude Code ハーネス・日本語
    ニュアンス・クロスモデルレビュー等は claude 列 / 会話応答・軽微な単発編集は
    委譲しない(固定費が上回る)
- その他 role: orchestrator(self)、reviewer_tech / reviewer_biz(claude subagent、
  tier A、高リスク時 S へ昇格可)、secretary(claude subagent、tier B)、
  committer(claude 列 tier A = opus に pin。実行系委譲のユーザー指示を registry へ昇格)
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
