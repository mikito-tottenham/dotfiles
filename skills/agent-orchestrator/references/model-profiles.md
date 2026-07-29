---
title: "Model Profiles — worker tier ladder の判断補助"
updated_at: 2026-07-28
---

# Model Profiles

tier ladder(`rules/model_registry.yaml` の `tiers`)に載っているモデルの特性メモ。
**tier / モデルの割り当ての正本は registry** であり、このファイルは
親オーケストレータ(Claude Code / Codex)が柔軟判断するときの判断材料に徹する。

living document として運用する: 委譲の実測(得意・不得意・失敗パターン)に
気づいたら「実測メモ」へ追記し、恒久的な傾向が見えたら registry の
`intent` や tier 割り当てへ昇格する。

## 実行経路の違い(モデル以前に効く差)

列→実行経路の対応は親相対で決まる(正本: registry `providers.*.self_elision`)。
親と同じ provider の列は agent_tool(subagent 機構)、異なる provider の列は
cli_runner になる。

| 観点 | cli_runner(親と異なる provider の列) | agent_tool(親と同じ provider の列) |
|---|---|---|
| 実行形態 | 外部 CLI subprocess。`.context/` に prompt / JSONL / summary / failure が残る | 同一ハーネス内 subagent |
| ツール | 委譲先 CLI 側の設定・ツール(web search 可)。親の MCP は使えない | **親と同じ MCP・ブラウザ・ローカルツール・権限を継承** |
| コンテキスト | 完全分離。背景は prompt.md に書き直す必要あり | 分離だが subagent prompt で軽量に受け渡せる |
| コスト | 委譲先 provider の利用枠(Codex クレジットは現在余剰) | 親セッションと同じ利用枠・プール |
| 向き | 独立した大きめの作業、大量並列 WP、観測可能性が欲しい作業 | セッション文脈・ローカル環境に密着した作業 |

## モデル別プロファイル

### gpt-5.6-sol(Codex 列 S/A/B、effort がダイヤル)

- OpenAI の最上位 agentic coding モデル("Latest frontier agentic coding model")。
  context 272k。effort は low〜ultra まで(xhigh 超は runner の extra-arg 経由)。
- 得意: 長時間の自律コーディング、大規模実装、リポジトリ横断作業、Web 調査込みの実調査。
- 留意: effort を上げるほど実行時間が伸びる。600 秒 timeout を超えそうな契約では
  runner の timeout override を検討。

### gpt-5.6-luna(Codex 列 C)

- 高速・低コスト("Fast and affordable")。機械的な変換・整形・抽出向け。
- 留意: 判断を要する作業を任せない。仕様が完全に確定してから渡す。

### fable / Claude Fable 5(Claude 列 S)

- Mythos クラス。この構成で最も賢く、最も高価。親(司令塔)と同一モデル。
- 得意: 曖昧さの裁定、相反する制約の統合、最高難度の設計・レビュー。
- 留意: 使用は最小限に。「worker に落とせない判断」だけを渡す。

### opus / Claude Opus 5(Claude 列 A)

- Claude の実行系最上位。ニュアンスの効いた文章、コンテキスト理解、
  堅実なコード品質。committer role の pin 先。
- 得意: MCP・ブラウザ等ハーネス前提の実行、日本語の対外文書、
  セッション文脈に近い作業、Codex 成果物のクロスチェック。

### sonnet / Claude Sonnet 5(Claude 列 B)

- バランス型。定型実装・整理・下書きを十分な品質でこなす。
- secretary role の既定。

### haiku / Claude Haiku 4.5(Claude 列 C)

- 最速・最安の Claude。分類・抽出・整形・短文生成。
- 留意: 長い推論や設計判断は不可。luna と同様、確定手順の実行専用。

## 使い分けヒント(tier が同じとき)

- 大量・長時間・並列の実装/調査 → Codex 列(クレジット余剰。Claude 親からは cli_runner の観測可能な artifact も利点)
- 親の MCP・ブラウザ・ローカル権限・セッション文脈が要る → 親と同 provider の列(agent_tool)
- 日本語の対外文書・ニュアンス重視の執筆 → Claude 列
- agentic coding の一点突破 → Codex 列(sol)
- クロスモデルレビュー(worker と別 provider による品質検証) → 親と異なる
  provider の列を明示選択する(registry の目安からの逸脱として理由を記録)

## 実測メモ

- 2026-07-25 sol/high(cli_runner): dot_claude/CLAUDE.md 追記委譲。245 秒。
  指示逐語遵守・検証まで完璧。lock 競合を恒久対策レビュー付きで報告する品質。
- 2026-07-25 sol/low(cli_runner): 1 行修正委譲。108 秒。正確。
  仕様確定済みの小変更なら low で十分。
