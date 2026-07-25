---
name: agent-orchestrator
description: Orchestrate multi-model AI delegation from a parent Claude Code (Fable) session. Classify work into roles, resolve provider/model/effort through rules/model_registry.yaml, and dispatch to codex-cli-runner or same-provider subagents while the parent stays orchestration-only. Use when the user asks to 司令塔として進める, オーケストレーションする, マルチモデルで分担する, Codexに実装させる, Codexへ委譲する, モデルを使い分ける, ワークパッケージで並列実行する, delegate implementation to Codex, route tasks across AI models, or run any multi-step task where implementation, research, review, or GitHub work should be delegated instead of done by the parent agent.
---

# Agent Orchestrator

親エージェント(通常 Fable / Claude Code)を司令塔として、作業を role に分類し、
resolver の解決結果に従って runner skill または subagent へ委譲する。

親は orchestration 作業(意図明確化・計画・委譲・artifact 検査・統合・裁定・最終報告)
だけを直接実行する。worker 的な具体タスクを親が兼任しない。これは品質のためでもある:
委譲は成果物を `.context/` に観測可能な形で残し、レビューと再実行を可能にする。

## Model resolution

**正本**: `rules/model_registry.yaml`(この skill ディレクトリ内)。

- role → provider / model / effort / 実行モードの解決はすべて registry を読む。
  この SKILL.md 本文や委譲 prompt にモデル名・effort を書き写さない
  (本文中にモデル名が現れる場合は非正本の例示にすぎない)。
- skill 固有の割り当てが必要な場合は `skills.<skill>.roles.<role>` を追加し、
  グローバル `roles` を既定として扱う。
- registry の変更は dotfiles repo の正本を編集し、`gh skill install` で再配備する。

## Workflow

1. **分類 (self)**: 依頼をワークパッケージに分解し、各パッケージへ registry の role を
   1 つ割り当てる。迷ったら `use_for` の記述で選ぶ。どの role にも該当しない
   会話応答・軽微な単発編集は orchestration の一部として親が扱ってよい。
2. **解決 (self)**: `rules/model_registry.yaml` を読み、role の
   provider / mode / model / effort を確定する。
3. **委譲**:
   - `mode: cli_runner` → provider 対応の runner skill を **必ず読み込み**、その契約に
     従って実行する。runner が prompt file / stream log / timeout / expected artifact /
     summary / failure report を所有する。runner のコマンド詳細をこの skill や
     委譲 prompt に複製しない。registry が model / effort を指定する role では、
     runner のモデル指定オプションでその値を渡す(`null` は省略)。
   - `mode: agent_tool` → Agent tool で subagent を起動する。registry の `subagent` は
     custom agent 名、`model` は Agent tool のモデル指定に使う。
   - `mode: self` → 親が直接行う(orchestration 作業のみ)。
4. **検査 (self)**: 各委譲の期待 artifact が実体化しているか、runner の summary が
   success かを確認する。runner の成功は「実行と artifact 実体化」だけを保証する。
   内容の品質判断は親の責務として必ず中身を読む。
5. **統合・報告 (self)**: 成果を統合し、採否を裁定し、ユーザーへ報告する。
   委譲先に統合・最終報告・他 worker 成果物の閲覧をさせない(明示した場合を除く)。

## Delegation prompt contract

委譲 prompt(runner の `prompt.md` / subagent prompt)には最低限これを含める:

- role と担当範囲、作業ディレクトリ
- 目的・背景・制約(委譲先は親の会話コンテキストを持たない前提で書く)
- 期待 artifact のパスと成功条件
- 許可する副作用(既定: 指定 artifact の生成以外の変更禁止)
- 証拠ルール(推測と事実の区別、参照したファイル/URL の明記)
- blocked 時の報告方法(勝手に仕様を発明せず blocked を明示する)

## Artifacts

- Phase / Step を持つ作業は AGENTS.md の artifact gate に従い
  `.context/<task-or-date>/<nn>-<phase-name>.(md|json)` を作ってから遷移する。
- 並列ワークパッケージは `.context/<task>/wp<n>-<name>/` に分ける。
- 各 runner run は runner 契約どおり `.context/<task>/`(または wp ディレクトリ)配下に
  ログ一式を残す。証拠 artifact は手編集しない。

## Failure handling

- runner 失敗時はまず `summary.json` の `failure_reasons` と `failure.md` を読み、
  原因を分類してから対処する(timeout / auth / モデル指定ミス / artifact 未生成 など)。
- 委譲失敗を理由に**親が黙って worker role を代行しない**。fallback は
  「別 role へ再委譲」「ユーザーへ blocked 報告」のように明示的に選び、報告に残す。
- エラーを迂回して進めた場合、再発・検証省略・環境不備の可能性があるなら
  bypass remediation review(原因 / 一時迂回 / 恒久対策候補 / 反映先 / 検証)を行う。

## 発動

- この skill の明示呼び出し(またはオーケストレーション要求の検出)でフル稼働する。
- 常時の委譲判断基準は `~/.claude/CLAUDE.md` 側のルールが担い、そこから本 skill と
  registry を参照する。両者が矛盾した場合は registry を正とする。
