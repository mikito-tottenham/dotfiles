---
name: model-tuning
description: "Audit or rewrite AGENTS.md / CLAUDE.md / skill files / prompts / eval harnesses so they fit a specific current LLM generation (Claude Fable 5.1, Claude Opus 5, GPT-6 Astra): effort and thinking settings, tool-use guidance, verbosity, prompt caching, and stale previous-generation patterns. Use for model readiness, migration, or prompt tuning requests such as モデル向けに最適化, Fable向けに調整, Opus 5向けに調整, GPT-6向けに調整, モデル移行の棚卸し; not for SDK or application code changes."
---

# Model Tuning

リポジトリのドキュメント、スキル、プロンプト、agent harness を特定の現行 LLM 世代に合わせて整備するためのスキル。モデルごとに skill を増やさず、共通の監査・書き換え手順を本文に、モデル固有の差分を `references/` に置く。

API クライアントコードの移行は対象外。SDK や API 呼び出しの実装修正は各 provider の公式移行手順（Claude なら `claude-api` skill）へ委譲し、本スキルは人間と AI が読む運用文書・プロンプト・ハーネス設計に集中する。

## 対象モデルと参照ファイル

依頼文またはリポジトリの model registry（`skills/agent-orchestrator/rules/model_registry.yaml` の alias）から対象モデルを 1 つ決め、対応する reference だけを読む。複数モデルを同時に扱う場合は対象ごとに Phase を分ける。

| 対象 | reference | 状態 |
|---|---|---|
| Claude Fable 5.1（alias `fable`） | `references/claude-fable-5-1.md` | 現行。未検証項目あり |
| Claude Opus 5（alias `opus`） | `references/claude-opus-5.md` | 現行。未検証項目あり |
| GPT-6 Astra（Codex 側の次世代） | `references/gpt-6-astra.md` | 現行。未検証項目あり |
| Claude Opus 4.8 | `references/legacy-opus-4-8.md` | 旧世代。移行元の前提確認用 |
| GPT-5.5 | `references/legacy-gpt-5-5.md` | 旧世代。移行元の前提確認用 |

reference に「未検証」とある項目は、公式ドキュメントで確認するまで文書の正本にしない。確認できなかった項目は artifact に「未検証のまま」と残す。

## 起動する場面

- ユーザーが「<モデル> 向けに整備・最適化・調整したい」「<モデル> readiness / migration」と発話した。
- `CLAUDE.md` / `AGENTS.md` / `SKILL.md` / `docs/**` / `prompts/**` / `rules/**` / eval harness が旧世代モデル前提になっていないか棚卸しする。
- 固定 thinking budget、sampling parameter 指定、effort の魔法語代用、強制進捗 scaffolding、曖昧な tool use 指示、prompt 内 schema 長文、prompt caching を壊す配置を見直す。

## 起動しない場面

- SDK / API 呼び出しコード、tool handler、provider adapter の書き換え。
- 文書編集や監査を伴わない単発の質問応答。
- モデル registry の実値変更だけを求められた場合。ただし関連プロンプト監査を含むなら対象にする。

## 実行モード判定

依頼を受けたら、編集前に次を決め、判定結果を artifact または作業結果に 1 行残す。

1. 複数の合理的解釈がある、または設計合意が必要な場合は、対象モデル・対象範囲・API 変更の有無を確認してから再判定する。
2. 中央 model registry、`CLAUDE.md` / `AGENTS.md` の構造、既存 skill description、複数ファイル横断の破壊的変更を伴う場合は、Plan を提示してから監査フローへ進む。
3. 明確で局所的な修正なら単発処理として進め、「典型修正パターン」だけ参照して小さく直す。

## 監査フロー

Phase を持つ作業では `.context/<task>/` に artifact を残し、各 Phase の完了条件にする。task 名の指定がなければ `model-tuning-<対象短縮>` とし、理由を残す。

### Phase 1: スコープ確定

- 対象モデルと reference を確定する。
- 対象ファイル群を列挙し、除外範囲を明記する。
- 中央 model registry / resolver の有無と、モデル指定・effort 指定の所在を確認する。
- API コード側変更を対象外として切り分ける。
- 旧世代モデル名・旧パラメータ・世代固定 URL を `rg` で洗い出す。

artifact: `.context/<task>/01-scope.md`

### Phase 2: 監査

各対象を「典型修正パターン」と reference のチェック項目に照合し、`path:line`、パターン記号、理由、推奨アクションを記録する。reference で「未検証」の項目に依存する指摘は、その旨を付けて「要確認」に分類する。

artifact: `.context/<task>/02-audit.md`

### Phase 3: 改修

正規指示ファイルや model registry を SoT として、重複を増やさず最小修正する。skill description を変更する場合は起動条件が変わるため、事前確認のうえ変更前後の誤発火・不発火を確認する。

artifact: `.context/<task>/03-changes.md`

### Phase 4: 検証

- `scripts/skill-quick-validate <skill-dir>` など repo の検証を実行する。
- `rg` で旧世代前提の残存を確認する。
- API パラメータに触れた場合は公式ドキュメントの現行記述と照合し、確認できない項目は未検証として残す。
- 可能なら代表タスクで dry run またはレビューを行う。

artifact: `.context/<task>/04-verify.md`

## 典型修正パターン

provider 共通の兆候と対応。モデル固有の既定値や推奨値は reference を正とする。

### A. 旧世代プロンプトをそのまま持ち込んでいる

- 兆候: 「既存 prompt を維持して model だけ置換」、旧世代の推奨デフォルトが正本化されている。
- 対応: 動く部分は残し、reference の差分表に該当する箇所だけ最小修正する。fresh baseline を要求する provider では product contract を残した最小 prompt から再評価する。

### B. effort を固定値や魔法語で代用している

- 兆候: `ultrathink` / `think hard` / `step by step` を reasoning 設定の代替にしている。すべて最高 effort に固定している。
- 対応: caller / registry 側で effort を設定し、prompt は intent と acceptance criteria を明確にする。既定値と escalation 条件は reference に従う。

### C. 廃止または非対応 API parameter が残っている

- 兆候: sampling parameter や固定 thinking budget を推奨している。
- 対応: 削除し、provider の現行 thinking / effort 制御に寄せる。

### D. 手順固定と強制進捗 scaffolding

- 兆候: N tool call ごとの進捗報告、毎ターン plan / reflection 強制、product 要件ではない長い step-by-step。
- 対応: outcome、success criteria、constraints、allowed side effects、evidence rules、output shape を中心にし、手順固定は必要な箇所だけ残す。

### E. instruction priority と停止条件が曖昧

- 兆候: 新旧指示の優先順位、override scope、完了条件、blocked の扱いが不明。
- 対応: instruction priority、completion rule、missing context gate、verification loop を短く追加する。

### F. tool use 指示が古い

- 兆候: tool を必ず多用させる、tool 必須タスクなのに条件が曖昧、tool 固有の手順が system prompt に肥大化。
- 対応: tool を使う条件と evidence rule を明示し、tool 固有の説明は tool description へ寄せる。過剰な固定回数指定は削る。

### G. review harness の recall を落としている

- 兆候: finding prompt に「high severity のみ」「be conservative」などの曖昧なフィルタがある。
- 対応: finding phase は coverage-first にし、confidence / severity を付けて downstream の ranking / dedupe / verification へ渡す。

### H. long context / compaction 後に再開不能

- 兆候: 会話中の合意だけが正本、artifact path や failure report がない。
- 対応: prompt、summary、expected artifacts、blocked state を `.context/` や runner artifact に保存する。

### I. verbosity と reasoning を混同している

- 兆候: 「よく考えさせるために長く答えさせる」「簡潔化のため reasoning を下げる」。
- 対応: 最終回答長は output contract または provider の verbosity 制御、推論量は effort で別々に調整する。

### J. structured output と prompt caching の前提が古い

- 兆候: parse-sensitive な schema を自然言語 prompt に長く埋め込む。static instructions の前に日付や動的 context を挿入する。
- 対応: provider の structured output 機能を標準にし、static first / dynamic last に並べ替え、不要な日付注入を削る。

### K. vision / computer use の旧前提

- 兆候: 旧解像度上限、旧 image detail 既定、座標変換前提が残っている。
- 対応: reference の現行値に更新する。未検証なら旧値を残し「要確認」と記す。

### L. skill description が弱い

- 兆候: 起動条件、除外条件、対象粒度が description から読めない。
- 対応: literal に解釈できる description へ更新する。変更前後で誤発火と不発火を確認する。

## プロンプト書き換え最小例

旧:

> temperature=0、ultrathink で慎重に考え、3 tool call ごとに進捗を報告し、重要な問題だけ指摘してください。今日は 2026-05-02 です。

新:

> Intent: <目的>
> Constraints: <制約>
> Allowed side effects: <none / draft only / write files / external action with approval>
> Evidence rules: <provided context only / retrieved sources with citations / codebase inspection required>
> Output shape: <short prose / table / structured output name>
> Completion rule: 要求項目をすべて扱うか `[blocked]` と不足入力を明記するまで終了しない。
> Finding phase では重要度や確信度で落とさず、見つけた問題をすべて列挙し、各 finding に confidence と severity を付ける。ranking は後続 step で行う。

effort と thinking は呼び出し側または registry で設定する。既定値は対象モデルの reference に従う。

## ユーザーへの確認が必須なケース

- 中央 model registry の書き換え。
- `AGENTS.md` / `CLAUDE.md` の構造的書き換え。
- 既存 skill の `description` 変更。
- API クライアントコード、tool handler、provider adapter の編集。
- irreversible side effect を持つ tool policy の変更。

## 完了条件

- 対象ファイルに旧世代専用の tuning 方針が残っていない、または残置理由が artifact / ADR / 作業結果で説明されている。
- effort、thinking、sampling parameter、tool guidance、review harness、long-context / compaction、structured output、caching の扱いが公式ドキュメントと矛盾しない。確認できない項目は未検証として列挙されている。
- API コード変更と文書 / prompt tuning の責務が分離されている。
- 中央 SoT と AI 別ファイル / skill / docs が矛盾していない。
- 変更根拠、検証結果、残置理由が `.context/<task>/` または作業結果に残っている。
