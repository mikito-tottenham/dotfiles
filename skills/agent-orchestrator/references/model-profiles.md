---
title: "Model Profiles — worker tier ladder の判断補助"
updated_at: 2026-10-23
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

### gpt-6-astra(Codex 列 S/A、effort がダイヤル)

- Codex の現行最上位モデルで、`~/.codex/config.toml` の親既定(effort `ultra`)と同一。
  effort は low / medium / high / xhigh / max / ultra(`~/.codex/models_cache.json`、2026-09-15)。
  runner の `--effort` は registry の値をそのまま透過する。
- 得意: 設計判断を含む実装、複数ファイルにまたがる変更、本格的な調査・執筆、
  相反する制約の裁定。
- 留意: effort を上げるほど実行時間が伸びる。timeout を置く契約では runner の
  timeout override を検討。`ultra` は自動委譲を伴うため worker 用途では原則 xhigh まで。

### gpt-5.6-sol(Codex 列 B)

- 前世代の frontier agentic coding モデル("Latest frontier agentic coding model" 世代)。
  context 272k。effort は low〜ultra。
- 得意: 仕様が明確な定型実装・修正・調査、長時間の自律コーディング。
- 留意: astra 登場後は B tier(定型実装)の既定。判断を伴う設計は A 以上へ。

### gpt-5.6-luna(Codex 列 C)

- 高速・低コスト("Fast and affordable")。機械的な変換・整形・抽出向け。
- 留意: 判断を要する作業を任せない。仕様が完全に確定してから渡す。

### fable / Claude Fable 5.1(Claude 列 S)

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
- agentic coding の一点突破 → Codex 列(astra / sol)
- クロスモデルレビュー(worker と別 provider による品質検証) → 親と異なる
  provider の列を明示選択する(registry の目安からの逸脱として理由を記録)

## 実測メモ

- 2026-07-25 sol/high(cli_runner、当時の A tier): dot_claude/CLAUDE.md 追記委譲。245 秒。
  指示逐語遵守・検証まで完璧。lock 競合を恒久対策レビュー付きで報告する品質。
- 2026-07-25 sol/low(cli_runner): 1 行修正委譲。108 秒。正確。
  仕様確定済みの小変更なら low で十分。

## プロンプト・指示文書のモデル世代合わせ(典型修正パターン)

旧 model tuning skill(2026-10 統合)の要約。AGENTS.md / CLAUDE.md / SKILL.md / 委譲 prompt / eval harness が
旧世代モデル前提になっていないかを棚卸しするときの provider 共通の兆候と対応。
モデル固有の既定値は registry と下の差分表を正とし、公式文書で確認できない項目は「未検証」と残す。

| 記号 | 兆候 | 対応 |
|---|---|---|
| A | 旧世代 prompt を model 名だけ置換して持ち込む | 動く部分は残し、差分表に該当する箇所だけ最小修正 |
| B | `ultrathink` / `think hard` 等の魔法語や全件最高 effort で reasoning を代用 | effort は caller / registry 側で設定し、prompt は intent と acceptance criteria に集中 |
| C | 廃止・非対応の API parameter(sampling、固定 thinking budget)が残る | 削除し、provider の現行 effort / thinking 制御へ寄せる |
| D | N tool call ごとの進捗報告、毎ターン plan 強制などの手順固定 | outcome / success criteria / constraints / side effects / evidence / output shape 中心へ |
| E | 指示の優先順位・完了条件・blocked の扱いが曖昧 | instruction priority、completion rule、missing-context gate を短く追加 |
| F | tool を必ず多用させる、tool 必須条件が曖昧 | 使う条件と evidence rule を明示し、固定回数指定は削る |
| G | finding prompt に「high severity のみ」「be conservative」 | finding は coverage-first、ranking / dedupe / verify は後続 phase |
| H | compaction 後に再開不能(会話中の合意だけが正本) | prompt / summary / expected artifact / blocked state を `.context/` に保存 |
| I | verbosity と reasoning の混同 | 回答長は output contract、推論量は effort で別々に調整 |
| J | schema を自然言語 prompt に長文埋め込み、static の前に動的 context | structured output 機能を標準にし、static first / dynamic last |
| K | vision / computer use の旧解像度・座標前提 | 現行値へ更新。未検証なら旧値を残し「要確認」 |
| L | skill description から起動・除外条件が読めない | literal に解釈できる description へ更新し、変更前後で誤発火・不発火を確認 |

### Claude 列 A 後継世代(Opus 5.5)の差分

出典: `claude-api` skill の Current Models / Thinking & Effort と model migration(2026-10-03 確認)。
alias `opus` がこの世代を指すかは Claude Code 側の alias 定義に依存し未確認。

| 項目 | 変更点 | 監査上の扱い |
|---|---|---|
| effort 既定 | `medium`(前世代は `high`)。省略すると 1 段低く動く | 「既定 high」前提の文書・registry は effort 明示を提案(B) |
| thinking 無効化 | 不可(`disabled` / `budget_tokens` は 400) | 「考えずに答えて」型の指示は effort 下げへ置換(C) |
| 強制 tool use(`tool_choice` の `any` / `tool`) | 400。`auto` + prompt 誘導か structured outputs | tool 強制前提のハーネスは「条件を書いて呼ばれたか検査」へ(F) |
| preserved thinking | thinking ブロックが会話に結び付き、履歴編集で無効化 | 履歴を書き換えるハーネスは append-only か確認(H) |
| 安全分類器 | `bio` / `reasoning_extraction` が追加 | 推論過程を本文に書かせる指示は削除候補(C) |
