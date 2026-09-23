---
title: "Use the ghq checkout as the chezmoi source of truth"
date: 2026-08-14
agent_model: "Codex (GPT-5)"
status: accepted
---

# ADR 0056: Use the ghq checkout as the chezmoi source of truth

## Context

dotfiles repository が `ghq root` 配下と chezmoi の旧既定 source
`~/.local/share/chezmoi` に重複して存在し、編集対象と適用元が分かれていた。
また、wrapper、Codex automation、bootstrap 文書が旧 source path を直接参照していたため、
旧 checkout を退避すると実行経路が壊れる状態だった。

## Decision

- `/Users/mikito/Claude/ghq/github.com/mikito-tottenham/dotfiles` を唯一の
  chezmoi source of truth とする
- machine-local な `~/.config/chezmoi/chezmoi.toml` に `sourceDir` を設定し、
  repository 管理対象には含めない
- source path を必要とする wrapper と automation は、固定 path ではなく
  `chezmoi source-path` または chezmoi template data の `.chezmoi.sourceDir` から解決する
- 新規 machine の bootstrap は ghq checkout の配置へ clone してから
  machine-local の `sourceDir` を設定する

## Consequences

- repository の編集場所と `chezmoi apply` の source が一致する
- machine ごとに source の絶対 path を設定する必要があるが、個別 path を
  repository の宣言的設定へ固定しない
- 旧 `~/.local/share/chezmoi` は、旧 path のハードコード解消を検証し、かつ同 checkout に
  残る未 push branch の扱いを完了した後にのみ退避または削除できる
- 本 ADR は旧 source の削除・移動を許可するものではなく、その操作は別途明示的な判断を要する
