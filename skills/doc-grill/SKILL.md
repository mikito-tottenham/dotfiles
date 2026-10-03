---
name: doc-grill
description: "Run an adversarial review loop on a document: a different model grills the draft, the parent adjudicates every finding in a table, fixes the source, has a consistency review check the fixes, and repeats until a stated convergence condition holds; documents leaving the organization then pass a pre-send gate for Japanese fonts, client-unfit wording, leaked internal notes or confidential data, and file format. For proposals, business plans, scheme documents, training material, and client decks. Not grill-me, which interviews the user about their plan; this skill reviews a written document. Use when asked to Grill して, 叩いて, 敵対レビュー, 壁打ちレビュー, 批判的にレビュー, 別モデルでレビュー, 相互レビュー, 徹底的にレビューして, 外部に出せるように, or 送付前チェック."
---

# Doc Grill

書いた文書を別モデルに徹底的に批判させ、親が全指摘を裁定して直し、直した結果を整合レビューで確かめる。これを収束条件まで繰り返し、対外文書なら最後に送付前検品を通す。

`grill-me`（ユーザーに質問を重ねて計画を詰める skill）とは用途が違う。こちらは書かれた文書を相手にする。

## 役割と委譲先

モデル名は書かない。役割は agent-orchestrator の `rules/model_registry.yaml` で解決する。registry に `skills.doc-grill.roles.*` があればそれを優先する。

| 役割 | 解決のしかた | 実行経路 |
|---|---|---|
| 親（執筆・裁定・反映） | `orchestrator` | 親自身 |
| Grill レビュアー | 文書の性質で `reviewer_biz`（提案・事業・契約条件）か `reviewer_tech`（技術・製品・データ）を選び、その tier で解決する。ただし provider は**下書きを書いた側と別の provider** にする。失敗コストが高い文書は tier を S へ上げてよい | 親が Claude Code なら codex-cli-runner、親が Codex なら claude-cli-runner。使い方は各 runner skill に従う |
| 整合レビュアー | `reviewer_tech`（文書の突合が中心のため）。事業条件の整合が中心なら `reviewer_biz` | registry のとおり（同 provider の subagent） |

- ユーザーが複数のモデルでの Grill を指定した場合は、Grill を並列で回し、裁定表で指摘をまとめる
- レビュアーには読み取り専用・成果物 1 ファイル・再委譲なしを依頼文で指定する

## 置き場

```
.context/<task>/
  00-scope.md                 対象・目的・読者・関連文書・収束条件・ラウンド上限
  grill-r1/prompt.md          Grill 依頼文（references/grill-prompt.md を埋めたもの）
  grill-r1/result.md          Grill 結果（レビュアーが書く）
  10-grill-r1-response.md     裁定表（親が書く）
  grill-r1/consistency.md     整合レビュー結果
  grill-r2/ ...               再 Grill する場合
  90-preflight.md             送付前検品（対外文書のみ）
```

各 artifact の Front Matter に `task` / `phase_or_step` / `created_at` を入れる。repo が grill の置き場を別に決めている場合（例: 資料ディレクトリの `process/` に残す）は、repo の規約に従う。

## 手順

### 0. 範囲を決める

`00-scope.md` に次を書いてから始める。

- 対象: 文言の正本（Markdown など）の path。pptx / pdf は正本から作る派生物として扱い、Grill は正本に対して行う
- 目的と読者: 誰に、何を判断させる文書か。対外か社内か
- 関連文書: 相手から受け取った文書、送付済みの文書、後続の合意、差分表・対応表、社内の既存見解、文言ルール、機密の境界、経緯
- 収束条件とラウンド上限（既定は下の「収束」）

### 1. Grill

[references/grill-prompt.md](references/grill-prompt.md) を埋めて `grill-rN/prompt.md` に保存し、レビュアーに渡す。

- 観点: 相手の視点、自社の事業・契約の視点、事実・技術の正確性、構成と論理、差分表・対応表の誤り、数値の検算
- 深刻度は Critical / Major / Minor の 3 段階
- 数値は、レビュアーにも親にも暗算させない。script で再計算した検算表を付けさせる
- 確信が持てない事実は「要確認」とし、断定させない

### 2. 裁定

Grill 結果の**全件**について、[references/adjudication.md](references/adjudication.md) の裁定表を `NN-grill-rN-response.md` に書く。表に載らない指摘を残さない。

既定の裁定:

- 事実誤認・技術的な誤り・計算の誤り → 採用して直す
- 相手に伝えた条件・提供範囲・成果物を超える約束 → 伝えた範囲を既定として保留し、ユーザーの裁定待ちにする。親が条件を独断で変えない
- 好みの範囲の Minor → 理由を書いて却下してよい
- 文書側では決められない論点 → 「ユーザー裁定」として一覧にし、ユーザーへ確認する

### 3. 反映

- 採用した指摘を正本に反映する
- 差分表・対応表など、正本と連動する表も同じターンで更新する（表の更新漏れは次の Grill で陳腐化として指摘される）
- 保留にした項目を、本文で確約の表現にしない
- 反映後に本文を読み直し、日本語の読みやすさは `natural-japanese` のクイックモードで整える。対外のメール・送付文は `japanese-business-writing` も使う

### 4. 整合レビュー

[references/consistency-prompt.md](references/consistency-prompt.md) を埋めて整合レビュアーに渡す。必ず次を観点に入れる。

- 裁定で「採用」とした指摘が本当に反映されているか
- 「保留」の項目が確約の表現になっていないか
- 同時に送る文書、送付済み文書、相手の文書、確定事実（日時・期限・過去の発言）との整合

整合レビューの指摘も、裁定表に追記して同じ規則で裁定・反映する。

### 5. 収束の判定

親が次の両方を満たすと判定した時点で収束とし、判定理由を裁定表の末尾に書く。

- 未解決の Critical が 0 件
- 残る Major（保留・却下）が、文書の読み手の意思決定を変えない

ラウンドの進め方:

- 既定は R1 と、修正後の再 Grill 1 回まで（計 2 ラウンド）
- R2 で新しい Critical が出た場合、または採用した Major が文書の主張を大きく変えた場合だけ R3 を回す
- R3 でも収束しない場合は、残りの指摘と論点をまとめてユーザーに判断を仰ぐ。それ以上は自動で回さない

### 6. 送付前検品（対外文書のみ）

社外に出す文書は、収束後に [references/preflight-checklist.md](references/preflight-checklist.md) を通し、結果を `90-preflight.md` に書く。1 項目でも不合格なら「送付可」としない。

- 日本語フォント（埋め込み、文字化け、代替フォント、はみ出し）
- 顧客に出せない文言（内輪の表現、過剰な約束、保証表現、保留中の論点の確約）
- 機密・内部メモの混入（コメント、発表者ノート、`要確認` タグ、他案件の名称、内部 path、AI の作業メモ）
- ファイル形式（指定どおりの形式、最新の正本からの生成、ファイル名の規約、開けること）

送付、アップロード、共有設定の変更は、この skill では行わない。ユーザーの明示指示を受けて別の作業として行う。

## 最終報告

- 対象と、回したラウンド数
- 深刻度別の指摘件数と、採用・保留・却下の件数
- 収束の判定と理由
- ユーザーの裁定が必要な論点
- 送付前検品の結果（対外文書の場合）
- artifact の path

## Validation

When updating this skill, run:

```bash
scripts/skill-quick-validate skills/doc-grill
```
