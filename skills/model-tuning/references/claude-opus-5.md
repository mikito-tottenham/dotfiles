# Claude Opus 5 差分メモ

対象: Claude Opus 5（model registry alias `opus`、Claude 列 A）。本ファイルは SKILL.md の共通手順に対するモデル固有の差分だけを持つ。

## この環境で確認済みの事実

- `skills/agent-orchestrator/rules/model_registry.yaml` の Claude 列 A tier が alias `opus` で解決する。committer role の pin 先（`skills/agent-orchestrator/references/model-profiles.md`）。
- 得意領域: MCP・ブラウザ等ハーネス前提の実行、日本語の対外文書、セッション文脈に近い作業、Codex 成果物のクロスチェック（同上）。
- 同世代に Sonnet 5（alias `sonnet`、列 B）があり、定型実装・整理・下書きは Sonnet 側へ落とす前提。

## 監査時に確認する項目

`claude-fable-5-1.md` と同じ表を適用する。Opus 5 固有に追加で確認する点:

| 項目 | 状態 | 監査時の扱い |
|---|---|---|
| Opus 5 と Fable 5.1 で effort / thinking の既定が異なるか | 未検証 | registry の tier ごとの設定を SoT にし、文書側でモデル名を直書きしない |
| Sonnet 5 との使い分け記述 | 確認済み（registry） | 「Opus でなければならない理由」が書かれていない委譲は tier 見直し候補として報告 |
| 旧 Opus 4.x 固有の記述（「Opus 4.7 では」「4.8 既定 high」等） | 該当あり得る | パターン A / C として報告。値の置換は公式確認後 |

## 参照する公式ソース

`claude-fable-5-1.md` と同じ入口（Models overview / What's new / Migration guide / Prompt engineering / Effort / Thinking / Prompt caching）。確認した URL と `verified_at` を artifact に残す。

## 旧世代からの差分候補

`legacy-opus-4-8.md` の 11 項目が Opus 5 で継続しているか未確認。監査で該当箇所を見つけたら「4.8 世代の値。5 系で要確認」と注記して報告し、公式確認前に書き換えない。
