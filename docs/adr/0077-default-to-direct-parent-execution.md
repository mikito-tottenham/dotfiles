---
title: "Default to Direct Parent Execution and Delegate Only on Stated Conditions"
date: 2026-10-25
agent_model: "Claude Code (Claude Opus 5.5)"
status: accepted
---

# ADR 0077: Default to Direct Parent Execution and Delegate Only on Stated Conditions

## Context

ADR-0050 と ADR-0052 は、親エージェント（Claude Code / Codex）を「司令塔」とし、
親はオーケストレーション作業だけを行い、実装・調査・レビュー・秘書的整理・commit
などの具体タスクは role ごとに委譲する方針を採った。registry の Self-Elision も、
親と同じ provider / model に解決した role を「外部 CLI は使わないが、同じモデルの
subagent へ委譲する」と定めていた。ADR-0072 の統合後も、この方針は
`agents-common` の司令塔条項と `agent-orchestrator` の `orchestration-invariants.md`
に引き継がれていた。

2026-10-22、Anthropic が記事「Building agents: When to fold subagents into your
main agent loop」（https://claude.com/resources/articles/building-agents-when-to-fold-subagents-into-your-main-agent-loop）
を公開した。要点は次のとおり。

- 1 つのループでスキルやツールを必要なときだけ読み込む形の方が、役割ごとに
  サブエージェントへ分ける構成より、品質・コスト・レイテンシで勝つことが多い。
- サブエージェントを残すのは、(a) 文脈の膨張による劣化が測定で見える、
  (b) 並列に走らせて終われば捨てる文脈が要る、(c) ツール選択に迷う・指示が
  衝突する、のいずれかに当たる場合に限る。
- 組織図をそのままエージェント構成に写す分割は避け、測定しながら一度に一つずつ変える。

この観点で現行ルールを見直すと、次の問題があった。

- 既定が「委譲」で、例外が「親の直接実行」になっていた。役割で分ける設計は、
  記事が見直しを勧める組織図型の分割に当たる。
- committer role は Claude Code 親で tier A（opus）に固定されていた（2026-07-25
  ユーザー指示、ADR-0052 で維持）。当時の親は Fable で、安いモデルへ渡す意味が
  あった。親が Opus のセッションでは同じモデルへの委譲になり、コスト上の利点が
  なく、レイテンシと文脈の受け渡しだけが増える。
- 委譲した方が良かったかを確かめる仕組みがなく、原則だけで決まっていた。

2026-10-25、ユーザーは次の 2 点の実施を承認した。

1. 親と同じモデルへの委譲をやめる。
2. 既定を親の直接実行に反転し、委譲は条件付きにする。

## Decision

- 共通ルール正本 `.chezmoitemplates/agents-common.md` の司令塔条項を書き換え、
  既定は親の直接実行とする。委譲は次のいずれかに当たる場合に限る。
  1. 50KB 超の読み込みや長い反復など、親のコンテキストを膨らませる作業の切り離し
  2. 互いに独立した作業の並列化
  3. 親と異なるツール・権限・指示が必要で、同居させると選択を誤る・指示が衝突する作業
  4. 別の文脈や別モデルによる独立レビュー
  5. Codex など親と別の利用枠で実行した方がコスト上有利な、大きめで独立した作業
- 役割分担だけを理由に委譲しない。委譲先が親と同じモデルに解決される場合は、
  1〜4 に当たらなければ親が直接実行する。
- 条件 4 と 5 は記事の 3 条件に含まれないが、それぞれ自己確認の甘さを避ける
  独立性と、別の課金枠を使うコスト上の理由によるもので、記事の前提（同じ枠の中で
  委譲すると固定費が増える）が当てはまらないため残す。
- 「会話応答、軽微な単発編集、オーケストレーション作業は親が直接行ってよい」
  条項は新しい既定に含まれるため、「役割分担だけを理由に委譲しない」条項に置き換える。
- `skills/agent-orchestrator/rules/model_registry.yaml` を v5 とする。
  - `execution_modes.self` を既定の実行モードとし、委譲条件に当たらない具体タスクも含める。
  - `model_elision` を追加し、解決 model が親と同じ場合の委譲を上の 1〜4 に限る。
  - `orchestrator` / `worker` の `use_for` を新しい既定に合わせる。
  - `committer` role を削除する。commit は委譲条件のどれにも当たらないため親が行う。
    ADR-0052 の「committer の Claude 親 tier A pin は維持する」と 2026-07-25 の
    指示を置き換える。
- 依存する文書を同じ方針にそろえる。
  - `skills/agent-orchestrator/SKILL.md`、`references/model-profiles.md`
  - `skills/agent-orchestrator/references/orchestration-invariants.md` の不変条件 1・2。
    旧方針のまま残すと、次回の監査が新方針を違反として差し戻すため。独立レビューの
    役は、モデルが一致しても親が兼任しない点は維持する。
  - `dot_codex/AGENTS.md.tmpl` の「司令塔運用でも」を「委譲する場合も」に改める
  - `dot_gemini/GEMINI.md` と `dot_qwen/QWEN.md` の「積極的に使う」行。ADR-0052 は
    Gemini / Qwen の共通ルール drift を別件としたが、この行は新方針と正面から
    矛盾するため、条件を自己完結で書いた 1 行に置き換える。

## Consequences

- subagent の起動回数が減り、委譲の固定費・レイテンシ・要約による情報の欠落が減る。
- 親のコンテキストに作業の詳細が残るぶん、親の文脈は膨らみやすくなる。50KB の
  読み込み上限、反復のスクリプト化、150k での handoff は条件 1 の具体化として
  そのまま残し、膨張の歯止めとする。
- 親が Fable のセッションでも commit は Opus に渡さず親が行うため、commit 部分の
  トークン単価は上がる。作業量が小さく、委譲時の文脈の受け渡しも不要になるため
  受け入れる。
- Codex への委譲（条件 5）と独立レビュー（条件 4）は従来どおり使える。
- 委譲判断の基準が役割から条件に変わるため、secretary や `tech` / `biz` /
  `personal` などの役割別 role・custom agent は、条件に当たるときだけ使われる。

## Verification

- 記事の方針に合わせ、切り替え後に品質が落ちた作業種別があれば
  `skills/agent-orchestrator/references/model-profiles.md` の実測メモへ記録し、
  委譲条件の追加または一部の戻しを個別に判断する。一度に複数の条件を変えない。

## Unresolved

- 役割別 role（secretary など）と custom agent 自体の整理は今回の対象外とした。
- 共通ルールと repo 固有 `AGENTS.md` の重複整理（記事の「継ぎはぎのプロンプト」
  への対処）は別作業とする。
- Codex 親で committer が担っていた未 pin の扱い（ADR-0052 の Unresolved）は、
  role の削除により解消した。
