# Claude Opus 5.5 差分メモ

対象: Claude Opus 5.5（API model ID `claude-opus-5-5`、Opus 5 の後継）。本ファイルは SKILL.md の共通手順に対するモデル固有の差分だけを持つ。API コードの移行手順そのものは `claude-api` skill の model migration（Migrating to Claude Opus 5.5）を正とし、ここには運用文書・プロンプト・ハーネス監査で使う差分だけを置く。

## 確認済みの事実

出典: `claude-api` skill（Claude Code 同梱版、モデル表 cached 2026-09-25）の Current Models / Thinking & Effort と `shared/model-migration.md` の「Migrating to Claude Opus 5.5」。2026-10-03 に確認。

| 項目 | Opus 5.5 | Opus 5 との差 |
|---|---|---|
| effort の既定値 | `medium` | Opus 5 以前は `high`。省略すると 1 段低く動く |
| effort の段階 | `low` / `medium` / `high` / `xhigh` / `max` | 同じ名前でも思考量は 1 対 1 に対応しない。同じ段階では Opus 5 より多く考える傾向（特に `xhigh` / `max`） |
| thinking の無効化 | 不可。`{type: "disabled"}` と `budget_tokens` はどの effort でも 400 | Opus 5 は `high` 以下なら disabled を受け付けた |
| sampling（temperature 等） | 指定すると 400 | 変わらず |
| 強制 tool use（`tool_choice` の `any` / `tool`） | 400。`auto` + `strict: true` + プロンプトでの誘導、または structured outputs | Opus 5 では使えた |
| thinking ブロック | 生成したモデルと会話に結び付く（preserved thinking）。履歴の編集で無効になる | 新規 |
| tool 呼び出しの合間のテキスト | `thinking` ブロックとして返る（既定は空。`display: "updates"` で要約が返る） | 新規 |
| 安全分類器 | `cyber` に加え `bio` と `reasoning_extraction` で拒否しうる | `bio` / `reasoning_extraction` が新規 |
| prefill | 不可（4.6 以降と同じ） | 変わらず |
| per-message effort / 会話途中の system message / compaction / task budget / fast mode | 利用可（fast mode は Claude API のみ） | 変わらず |

## 監査時に確認する項目

`claude-fable-5-1.md` の表に加え、Opus 5.5 では次を確認する。

| 兆候 | パターン | 監査時の扱い |
|---|---|---|
| effort を書かず「Opus なので既定 high」を前提にした文書・registry | B | 既定は `medium`。caller / registry 側で effort を明示する提案として報告する |
| Opus 5 で決めた effort 値をそのまま引き継いでいる | A / B | 同じ値でも turn が長くなりうる。`low` / `medium` を含めて再評価する前提で「要再測定」と報告する |
| 「thinking を切って速くする」「考えずに答えて」型の指示 | C | thinking は切れない。effort を下げる方向へ寄せ、「考えるな」系の指示は削除候補にする |
| 推論過程を本文に書かせる指示 | C | `reasoning_extraction` で拒否されうる。削除し、必要なら thinking の要約表示（`display: "summarized"`）を使う |
| 特定 tool の呼び出しを強制する前提のハーネス | F | 強制指定は 400。tool を使う条件をプロンプトに書き、呼ばれたかを検査する形へ |
| 履歴を書き換える・途中のメッセージを消すハーネス | H | preserved thinking と衝突しうる。追記のみ（append-only）の形か確認する |
| Opus 5 向けの冗長さ・過剰検証・スコープ抑制の指示 | A | 起点としては残し、効いているかを再評価する。即削除はしない |
| 画像・図表入力用の補助手順（切り抜き前処理など） | K | 読み取り精度が上がっているため不要になっている可能性がある。「要再テスト」として報告する |
| フロントエンドで「AI っぽくしない」等の抽象的な指示 | L に準ずる | 避けたい具体的なパターンを列挙する形が効く |
| 長い turn を前提にしないタイムアウト設定 | H | `xhigh` / `max` では turn が長くなる。タイムアウト・進捗表示を確認する |

## この環境での位置付け

- `skills/agent-orchestrator/rules/model_registry.yaml` の Claude 列 A は alias `opus` で解決し、`references/model-profiles.md` は列 A を Opus 5 と記載している。alias `opus` が Opus 5.5 を指すかは Claude Code 側の alias 定義に依存し、本ファイル作成時点で未確認。registry / profiles の記述更新は本 skill の対象外（SKILL.md「ユーザーへの確認が必須なケース」）。
- 文書・skill 本文にモデル名や effort 値を直書きせず、registry の role / alias を参照させる方針は変わらない。

## 未検証のまま残す項目

- Claude Code / Codex の CLI 上での effort 既定値（API 既定 `medium` と同じかどうか）。
- alias `opus` の解決先。
- 日本語の対外文書・長文の書き味に関する Opus 5 との差。公式資料は英語の文章・報告の明瞭さ向上に触れているが、日本語での確認はしていない。
