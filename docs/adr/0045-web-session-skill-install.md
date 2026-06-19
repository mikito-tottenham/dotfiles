---
title: "Install Skills At SessionStart For Claude Code On The Web"
date: 2026-06-19
agent_model: "Claude Code"
status: proposed
---

# ADR 0045: Install Skills At SessionStart For Claude Code On The Web

## Context

`docs/skills-install-manifest.md` と AGENTS.md「スキル管理」は、新しいマシンでの skill 復元方法を次のように定めている: docs-only manifest を正本とし、`gh skill install`（first-party publisher skill は `skills/` から `--from-local`、external skill は upstream から直接）を標準経路とし、復元を script 化せず、external skill を repo に vendoring しない。

Claude Code on the web は各セッションを ephemeral コンテナで実行し、以下の制約がある。

- 毎回まっさらな clone から開始し、`gh skill install --scope user` で構築したローカルの `~/.claude/skills/` を引き継がない。
- `gh`（および `gh skill` 拡張）が入っていないため、manifest の標準 `gh skill install` 経路をそのまま実行できない。
- skill の auto-load 元は repo の `.claude/skills/` と `~/.claude/skills/` のみで、publisher `skills/` ディレクトリは対象外。

このため、first-party skill（`opus-4-8-tuning`、`handoff` 等）や external の `grill-me` は、このリポジトリを scope に入れても web セッションで利用できない。manifest の仕組みはローカル / 新規 Mac の復元フロー向けであり、gh 非搭載の web コンテナを想定していない。

## Decision

repo-local の `SessionStart` フック（`.claude/hooks/session-start.sh`、`.claude/settings.json` に登録）を追加する。web コンテナ（`CLAUDE_CODE_REMOTE=true`）でのみ動作し、`~/.claude/skills/` を populate してそのセッションで skill を使えるようにする。

- First-party publisher skill: 各 `skills/*` を `~/.claude/skills/` へ copy する。ただし `claude-cli-runner`（manifest 上 Codex 専用）と `onepassword-secret-materialize`（repo-local `.claude/skills/` で既に供給）は除外する。正本は引き続き repo の `skills/`。
- External `grill-me`（+ 依存の `grilling`）: `mattpocock/skills` upstream から runtime 取得して `~/.claude/skills/` へ置く。repo へは vendoring しない。upstream は publisher layout（`skills/<category>/<skill>`）へ再編済みのため、フックは固定パスではなく `find` で skill を探す。grill-me 本体は `/grilling` を呼ぶだけなので grilling も併せて入れる。
- best-effort かつ冪等: 個々の install 失敗は stderr へログするが、セッション起動は止めない（常に `exit 0`）。

本フックは gh 非搭載の web コンテナに限定する。ローカルマシンでは no-op とし、`gh skill` + chezmoi を標準経路として維持する。

`empirical-prompt-tuning` と `gws-*` は当面対象外とする。前者は manifest 記載の upstream URL が現在 404 を返し、後者は web コンテナに無い `googleworkspace-cli`（Brewfile）を必要とするため。

## Status / ownership

Claude Code が branch `claude/eloquent-davinci-ckezix` で起案（proposed）。リポジトリの管理責任は Codex が持つ（AGENTS.md）。Codex は本例外を承認し、AGENTS.md「スキル管理」と `docs/skills-install-manifest.md` に web SessionStart 経路を反映する（または却下する）こと。承認までは、本フックを governance レビュー待ちの実装として扱う。

なお `docs/skills-install-manifest.md` の grill-me 項は upstream の旧 flat layout を前提にしており、現在の publisher layout（`skills/productivity/grill-me`）および grill-me が `/grilling` に依存する変更が未反映で stale。Codex は manifest の grill-me 項（layout 前提・grilling 依存の追記）も併せて更新すること。

## Consequences

- このリポジトリを scope に入れた web セッションで、first-party skill と `grill-me` が `gh` 無しで利用可能になる。
- 「復元を script 化しない / `gh skill` を標準」ルールに web 限定の例外が文書化される。ローカル復元フローは不変。
- フックは manifest の curation（skip 対象）を shell で持つため、manifest と drift し得る。緩和策として first-party 一覧は `skills/` ディレクトリから導出し、skip 集合を最小に保つ。
- external `grill-me` は session 開始時の upstream 可用性とネットワークポリシーに依存する。失敗時は graceful degradation（その session で skill が無いだけ）。
- 将来 web コンテナで `gh` が使えるようになった場合は、フックを manifest の `gh skill install` 経路へ移行することを優先する。
