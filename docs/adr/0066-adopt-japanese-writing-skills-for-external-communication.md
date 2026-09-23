---
title: "対外日本語の skill として natural-japanese と japanese-business-writing を third-party で導入する"
date: 2026-09-23
agent_model: "Claude Opus 5.5 (claude-opus-5-5)"
status: accepted
---

# ADR 0066: 対外日本語の skill として natural-japanese と japanese-business-writing を third-party で導入する

## Context

2026-09-23、ユーザーから [coji/natural-japanese](https://github.com/coji/natural-japanese) の評価と、「外部に送る日本語」に使える skill があれば導入してほしいという依頼があった。対象は顧客・取引先・投資家向けのメール、社外チャット、提案書、報告書、スライドである。

2026-09-15 以降、third-party external skill は全て撤去済みで（ADR-0062）、`scripts/bootstrap-web` の third-party 取得対象も空だった。external skill は vendoring せず `gh skill` で管理する方針（ADR-0020）は維持する。

評価の要点:

- natural-japanese（MIT、★1100 超）: 提案書・報告書・スライドの構成、読みやすさ、AI 臭と翻訳調の除去については、国内の公開 skill で設計の質が最も高い。書き換えすぎと捏造の歯止めも明文化されている。一方、メールの型と敬語は扱わず、挨拶やクッション言葉を削る方向に働く
- 代替の調査では、natural-japanese を置き換えられる候補は無かった。nwiizo/suiko は同じ設計の再実装で、skill 自身が `cargo install` を実行する。iKora128/stop-ai-slop-jp はブログ向けで、`gh skill install` で入らない。yamadashy/skills は LICENSE が無い
- RobTar97/japanese-writing-skills の `japanese-business-writing`（MIT）は敬語、内/外の切り替え、丁寧さの 3 段階、メール・チャットの作法、事実と約束を捏造しない規律を持つ。scripts も外部依存も無い。★0 の新しい repo のため、pin した SHA で SKILL.md と references を全文レビューし、不審な指示が無いことを確認した

## Decision

- `natural-japanese` と `japanese-business-writing` を third-party external skill として、Claude Code / Codex の user scope へ `gh skill install --pin <commit SHA>` で導入する。タグは付け替えできるため、commit SHA で固定する
- installed copy は改変しない。発火範囲の絞り込みや `semantic.py` の除去は、`gh skill` の provenance と update 導線を崩すため今回は行わない
- 役割の分担: 構成・読みやすさは `natural-japanese`、敬語・宛名・メール作法・送信前の事実確認は `japanese-business-writing` が担う
- 記録先は `docs/skills-install-manifest.md` の Third-party 節とする。web セッションの再現は `scripts/bootstrap-web` の `install_third_party()`（best-effort、SHA fetch）で行い、`scripts/verify-cloud-parity` の `THIRD_PARTY_SKILLS` とも揃える

## Consequences

- 対外文書を書くとき、Claude Code / Codex がこの 2 skill を自動で読み込めるようになる
- natural-japanese の description は範囲が広い。そのため、社内向けの日本語レポートや既存の `external-report` skill の担当範囲でも読み込まれる可能性がある。また、対外文書は skill の規定で「フルモード」（並列サブエージェント、短文でも数分）に昇格する。誤発火や所要時間が問題になったら、installed copy の改変（明示呼び出し専用化）か first-party wrapper を別途判断する
- 2 skill は「提案書・報告・メール」で発火範囲が重なる。「いかがでしょうか」などの敬語表現について、natural-japanese は削る方向、business-writing は保つ方向に働く。優先順位は指示ファイルに固定せず、実運用で衝突が問題になった時点で決める
- natural-japanese の lint は `uv run`（`sudachipy` を初回に PyPI から取得）が前提である。導入時点のローカル Mac には `uv` が無いため、skill の規定どおり手動チェックリストで代替される。`uv` を Brewfile に加えるかは別途判断する
- natural-japanese の一時ファイル指示（scratchpad / `mktemp -d` に置き、完了時に削除）は、共通ルールの `.context/` 利用と artifact 保持が下限として優先される
- pin の更新は、manifest・`bootstrap-web`・（skill を増減するときは）`verify-cloud-parity` を同時に更新し、更新前に upstream の差分をレビューする
