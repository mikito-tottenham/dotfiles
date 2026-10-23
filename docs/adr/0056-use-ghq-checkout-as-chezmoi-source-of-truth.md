---
title: "Use the ghq checkout as the chezmoi source of truth"
date: 2026-08-14
agent_model: "Codex (GPT-5)"
status: accepted
updated_at: 2026-10-23
updated_by: "Claude Opus 5.5 (claude-opus-5-5)"
---

# ADR 0056: Use the ghq checkout as the chezmoi source of truth

## Context

dotfiles repository が `ghq root` 配下と chezmoi の旧既定 source
`~/.local/share/chezmoi` に重複して存在し、編集対象と適用元が分かれていた。
また、wrapper、Codex automation、bootstrap 文書が旧 source path を直接参照していたため、
旧 checkout を退避すると実行経路が壊れる状態だった。

## Decision

- `ghq root` 配下の checkout（この環境では `~/Claude/ghq/github.com/mikito-tottenham/dotfiles`）を唯一の
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

## 追補（2026-10-23、ADR-0076）

- 本 ADR は 2026-08-14 に main checkout で作成されたまま commit されず、ADR-0058 / ADR-0062 が「ADR-0056」として
  参照する一方で repo には存在しなかった。2026-10-23 の WIP 仕分け（ADR-0076）で、番号が空いていたため同じ番号のまま取り込んだ。
- 取り込み時に、下書きにあった利用者のホームディレクトリの絶対 path を `ghq root` 基準の表記へ改めた。決定の内容は変えていない。
