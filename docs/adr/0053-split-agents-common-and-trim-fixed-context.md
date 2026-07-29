---
title: "AGENTS.md の共通/Codex 固有分割と固定コンテキストの削減"
status: accepted
date: 2026-07-29
agent_model: "Claude Fable 5 (claude-fable-5)"
---

# 0053: AGENTS.md の共通/Codex 固有分割と固定コンテキストの削減

## 背景

Claude Code の毎セッション固定コンテキストを実測したところ、指示ファイルと Skill description だけで約 12〜15k トークンを消費していた。特に以下の無駄が確認された。

- `~/.claude/CLAUDE.md` が `~/.codex/AGENTS.md` 全体(19.4KB)を import しており、うち `# Codex 固有ルール` 5.1KB は「適用しない」と宣言した上で毎回読み込まれていた
- ローカル Skill 26 個の description 合計が 13.2KB(500B 超が 12 個)。SKILL.md 本文は呼び出し時のみ読まれるが、description は全数が毎セッション載る
- `opus-4-7-tuning` は `opus-4-8-tuning` に実質置き換えられており、配備し続ける必要がなかった

## 決定

1. **共通ルールの単一ソース化と二重レンダリング**: `.chezmoitemplates/agents-common.md` を正本とし、chezmoi template include で
   - `dot_codex/AGENTS.md.tmpl` → `~/.codex/AGENTS.md`(共通 + Codex 固有ルール、Codex 用フル版)
   - `dot_codex/AGENTS-common.md.tmpl` → `~/.codex/AGENTS-common.md`(共通のみ、Claude 用)
   を生成する。`dot_claude/CLAUDE.md` の import は `@~/.codex/AGENTS-common.md` へ変更し、「Codex 固有ルール以降は適用しない」の打ち消しルールを廃止
2. **Skill description の圧縮**: 500B 前後を超える 14 skill の description を、トリガーキーワードと否定スコープを維持したまま約半分に圧縮(合計 −3.5KB)。正本は repo `skills/`、`gh skill install --from-local` で claude-code / codex 両方へ再配備
3. **opus-4-7-tuning の退役**: `docs/skills-install-manifest.md` と `scripts/bootstrap-web` から除外し、ローカル配備(`~/.claude/skills/`, `~/.codex/skills/`)を削除。repo `skills/opus-4-7-tuning/` は履歴として残す
4. **共通ルール本文の重複統合**: 意味を変えずに近接する重複バレット(保存先ルール 7→3、スクリプトログ 3→1、恒久対策レビュー 2→1、artifact gate 3→1、ADR 2→1)を統合(−543B)。規範的な語句は削っていない

## 削減効果(実測)

- Claude セッション: Codex 固有部 5.1KB + description 3.5KB + 共通部 0.5KB ≒ 9.1KB(約 2.5〜3k トークン/セッション)
- Codex セッション: description 圧縮 + 共通部統合分

## 検証

- 分割直後の `chezmoi cat ~/.codex/AGENTS.md` は分割前の配備ファイルとバイト一致を確認(純粋な構造変更)
- 全 SKILL.md front matter を yaml.safe_load でパース検証
- 再配備 27 install 全成功、`~/.claude/skills` の description 合計 13,162B → 9,663B

## 注意

- 共通ルールを編集するときは `.chezmoitemplates/agents-common.md` を編集する。`~/.codex/AGENTS.md` / `~/.codex/AGENTS-common.md` は生成物
- スキルを追加・削除したときの manifest / bootstrap-web 同期ルールは従来どおり
