---
title: "コンテキスト長の常時可視化と単一読み込み上限の導入"
date: 2026-08-03
agent_model: "実測・分析 = Claude Fable 5 (claude-fable-5)、ルール策定・実装 = Claude Opus 5 (claude-opus-5)"
status: accepted
---

# ADR 0054: コンテキスト長の常時可視化と単一読み込み上限の導入

## Context

ADR-0051 は 2026-07-25 に 150k handoff / 10 回スクリプト化 / リサーチのファンアウト
を導入した。2026-07 全期間を `~/.claude/projects` の全ログ(202 セッション、
6,629 リクエスト)で再集計したところ、次の状態だった。

- cache_read 916M(Fable 5 = 692M、Opus 5 = 224M)、API 換算で合計 $1,731
- うちコンテキスト持ち回り(cache_read + cache_creation)が $1,574 = 全体の 91%。
  純粋な生成 output は Fable 5 で 4.1M トークン($204)にとどまる
- ピーク 150k 超のセッションは 202 中 58 で、持ち回りコストの 79% を占める
- 上位10セッションで持ち回りコストの 47%

問題は、ADR-0051 の導入後である 7/27・7/30 にも peak 392k〜621k のセッションが
発生し、150k 超のまま 129〜238 リクエスト継続していた点にある。150k ルールは
存在したが機能していなかった。原因は 2 つと判断した。

1. **観測不能**: 実行中に常駐コンテキスト長を確認する手段がなく、ADR-0051 自身が
   「直接観測できないときは代理指標」と書いていたとおり、閾値判定が主観だった
2. **条項の穴**: 生の材料を親へ蓄積しない規定は「複数観点または複数出典を要する
   調査・リサーチ依頼」に限定されており、単一ファイル・単一 Skill の 1 回読みは
   対象外だった。実例として、モデル単価の確認のために claude-api skill 全体
   32.5 万トークンを親で読み込み、cache write $6.5 に加えて以降のターンごとに
   約 $0.33 を支払う状態が発生した

加えて、150k 超過分のみを削った場合の圧縮幅は $234(持ち回りの 15%)にとどまる
と実測された。閾値運用だけでは不足で、ベースラインとなる常駐コンテキスト自体を
下げる必要がある。

## Decision

- Claude Code の statusline でコンテキスト長を常時表示する。実装は
  `dot_claude/executable_statusline.py`(transcript 末尾の直近 usage から
  `input + cache_read + cache_creation` を算出)、有効化は `dot_claude/settings.json`
  の `statusLine`。100k で黄、150k で赤 + `⚠ handoff` を表示する
- `agents-common.md` に単一読み込みの上限を追加する。1 回の読み込みが 50KB
  (概ね 2 万トークン)を超える見込みなら親で読まず委譲し、読み込み前に
  `ls -l` / `wc -c` でサイズを確認する。単一出典・単発読み込みはファンアウトの
  対象外だが、この上限は独立に適用する
- `agents-common.md` に Skill のファイル単位読み込みを追加する。Skill 全体の
  読み込みが避けられない場合は委譲先で行う
- ADR-0051 由来の 150k handoff 条項について、代理指標の記述を statusline 表示を
  一次情報とする形へ更新する
- 閾値の根拠: 50KB は読み込み前に機械的に判定できる点を優先した運用値であり、
  主観判断を排除することを目的とする。トークン換算は概算で、モデル窓や
  tokenizer に由来する値ではない。次期集計で見直す

## Consequences

- 親セッションの常駐コンテキストのベースライン低下を狙う。閾値超過後の分割
  (ADR-0051)と、超過に至る前の流入抑制(本 ADR)の二段構えになる
- statusline は宣言的設定のため chezmoi 管理とする(machine-local state ではない)
- 効果検証は ADR-0051 と同じく `scripts/ai-usage-aggregate.py` を 2026-09-01 を
  目安に再実行し、本 ADR の Context の実測値を baseline として比較する。特に
  peak>150k セッション数(baseline 58/202)と持ち回りコスト比率(baseline 91%)を見る
- 今回の集計は `.context/` 配下のアドホックスクリプトで実施したが、正本は
  `scripts/ai-usage-aggregate.py` である。次回検証は正本を使うこと

## 補遺(2026-08-10): モデル向け enforcement hook

statusline はユーザー向け可視化であり、モデルは statusline を見ないため、150k
ルールの自己執行はモデル側に伝わらない穴が残っていた。2026-07 の実測では、5MB
超セッション 9 本に対し handoff skill の使用は 2 回だった。

対策として UserPromptSubmit hook `dot_claude/hooks/executable_context_guard.py` を
追加する。transcript 末尾の直近 usage 合計が 150k 以上のとき、プレーン stdout で
モデルのコンテキストへ handoff 指示を注入する。閾値は環境変数
`CLAUDE_CTX_HANDOFF_THRESHOLD` で変更できる。判定は機械的閾値のみであり、
CLAUDE.md の「hook に意味理解を持たせない」制約に適合する。

transcript JSONL の形式は Claude Code の内部仕様で、バージョンにより変わりうる
ことが公式 docs に明記されている。これは statusline と同じ既知リスクであり、
破損時は無出力に倒れる(fail-open)。

- 作業日時: 2026-08-10
- 実装 Agent: Codex (GPT-5.6-sol)
