---
title: "日本語の文章 skill として natural-japanese と japanese-business-writing を third-party で導入し、使い分けを共通ルールに固定する"
date: 2026-09-23
agent_model: "Claude Opus 5.5 (claude-opus-5-5)"
status: accepted
---

# ADR 0066: 日本語の文章 skill として natural-japanese と japanese-business-writing を third-party で導入し、使い分けを共通ルールに固定する

## Context

2026-09-23、ユーザーから [coji/natural-japanese](https://github.com/coji/natural-japanese) の評価と、「外部に送る日本語」に使える skill があれば導入してほしいという依頼があった。対象は顧客・取引先・投資家向けのメール、社外チャット、提案書、報告書、スライドである。

その後の検討で、ユーザーは社内向けの文章にも同じ使い分けを適用する方針とした。

2026-09-15 以降、third-party external skill は全て撤去済みで（ADR-0062）、`scripts/bootstrap-web` の third-party 取得対象も空だった。external skill は vendoring せず `gh skill` で管理する方針（ADR-0020）は維持する。

評価の要点:

- natural-japanese（MIT、★1100 超）: 提案書・報告書・スライドの構成、読みやすさ、AI 臭と翻訳調の除去については、国内の公開 skill で設計の質が最も高い。書き換えすぎと捏造の歯止めも明文化されている。一方、メールの型と敬語は扱わず、挨拶やクッション言葉を削る方向に働く
- 代替の調査では、natural-japanese を置き換えられる候補は無かった。nwiizo/suiko は同じ設計の再実装で、skill 自身が `cargo install` を実行する。iKora128/stop-ai-slop-jp はブログ向けで、`gh skill install` で入らない。yamadashy/skills は LICENSE が無い
- RobTar97/japanese-writing-skills の `japanese-business-writing`（MIT）は敬語、内/外の切り替え、丁寧さの 3 段階、メール・チャットの作法、事実と約束を捏造しない規律を持つ。scripts も外部依存も無い。★0 の新しい repo のため、pin した SHA で SKILL.md と references を全文レビューし、不審な指示が無いことを確認した

## Decision

- `natural-japanese` と `japanese-business-writing` を third-party external skill として、Claude Code / Codex の user scope へ `gh skill install --pin <commit SHA>` で導入する。タグは付け替えできるため、commit SHA で固定する
- installed copy は改変しない。発火範囲の絞り込みや `semantic.py` の除去は、`gh skill` の provenance と update 導線を崩すため今回は行わない
- 役割の分担: 構成・読みやすさは `natural-japanese`、敬語・宛名・メール作法・送信前の事実確認は `japanese-business-writing` が担う
- 使い分けは `.chezmoitemplates/agents-common.md` の「日本語の文章スキル」節に 3 行で固定する。対象は人に読ませる日本語の文章（社内外）で、Agent 自身の返答・コミットメッセージ・ADR・`.context/` の作業メモは対象外とする。`natural-japanese` はクイックモードを既定とし、フルモードはユーザーが明示した場合だけ使う（SKILL.md の「対外文書はフル」規定より優先）。敬語表現で 2 skill の指摘が食い違う場合は `japanese-business-writing` を優先する
- 2 skill を統合した first-party skill（仮称 `japanese-writing`）への内製は見送る。3 行の使い分けで主な摩擦（自動フル昇格、担当の重なり）は解消でき、内製で上乗せされる効果に対して作成と upstream 追従の手間が見合わないため。自分の文体や社内用語を覚えさせたくなった場合、または Taskell のメンバーへ配布したくなった場合に再検討する
- 記録先は `docs/skills-install-manifest.md` の Third-party 節とする。web セッションの再現は `scripts/bootstrap-web` の `install_third_party()`（best-effort、SHA fetch）で行い、`scripts/verify-cloud-parity` の `THIRD_PARTY_SKILLS` とも揃える

## Consequences

- 人に読ませる日本語の文章（社内外）を書くとき、Claude Code / Codex がこの 2 skill を自動で読み込めるようになる
- natural-japanese の description は範囲が広い。そのため、社内向けの日本語レポートや既存の `external-report` skill の担当範囲でも読み込まれる可能性がある。対象外の文書は agents-common の使い分けで明示したが、誤発火が続く場合は installed copy の改変（明示呼び出し専用化）か内製を再検討する
- 2026-09-23 の計測（サブエージェント、各条件 2 回、架空の社内 Slack・社外メール・提案書）では、スキルなしが 10〜28 秒、クイックモードが 22〜76 秒、フルモードが社外メールで 3〜3.5 分、提案書で約 5.7 分だった。トークンはスキルなし約 7.3 万に対し、クイックモードが約 8〜9 万、フルモードがレビュー役 3 本を含めて約 43〜45 万だった。敬語の誤りや AI 的な言い回しはスキルなしでも直り、日付・金額も全条件で保たれた。原文に無い約束の書き足しや確信度の格上げを拾えたのはフルモードだけだった。このため、短文はクイックモードで足り、フルモードは重要な文書で明示的に使う運用とした（計測記録はセッション内の `.context/` に置き、git 管理しない）
- 2 skill は「提案書・報告・メール」で発火範囲が重なる。「いかがでしょうか」などの敬語表現について、natural-japanese は削る方向、business-writing は保つ方向に働くため、agents-common で business-writing を優先すると決めた
- natural-japanese の lint は `uv run`（`sudachipy` を初回に PyPI から取得）が前提である。導入時点のローカル Mac には `uv` が無いため、skill の規定どおり手動チェックリストで代替される。`uv` を Brewfile に加えるかは別途判断する
- natural-japanese の一時ファイル指示（scratchpad / `mktemp -d` に置き、完了時に削除）は、共通ルールの `.context/` 利用と artifact 保持が下限として優先される
- pin の更新は、manifest・`bootstrap-web`・（skill を増減するときは）`verify-cloud-parity` を同時に更新し、更新前に upstream の差分をレビューする
