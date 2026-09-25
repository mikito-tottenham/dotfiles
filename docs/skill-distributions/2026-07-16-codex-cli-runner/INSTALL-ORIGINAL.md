---
title: codex-cli-runner
description: Codex CLI を観測可能なサブプロセスとして実行する Agent Skill の配布パッケージ
---

# codex-cli-runner

Codex CLI（`codex exec`）をサブプロセスとして実行し、JSONL イベントログ・タイムアウト・失敗 artifact を残すための Agent Skill です。Claude Code / Codex などのオーケストレーター Agent から、長時間の調査・レビュー・生成・ファイル作業を Codex に委譲するときに使います。

詳細な使い方・成功/失敗判定・検証手順は [SKILL.md](SKILL.md) を参照してください。

## 構成

- `SKILL.md` — Skill 本体（ルール、コマンド形、成功/失敗基準、検証手順）
- `scripts/run_codex_cli.py` — `codex exec` のラッパー（Python 3、標準ライブラリのみ）
- `agents/openai.yaml` — Codex 向けの Skill インターフェース定義

## 前提

- Codex CLI がインストール・認証済みであること
- Python 3

## インストール

このディレクトリごと、利用する Agent の skills ディレクトリへコピーしてください。

```bash
# Claude Code（ユーザーグローバル）
cp -R codex-cli-runner ~/.claude/skills/

# Codex（ユーザーグローバル）
cp -R codex-cli-runner ~/.codex/skills/

# リポジトリローカルに置く場合
cp -R codex-cli-runner <repo>/.claude/skills/
```

## 補足

- `SKILL.md` の Validation 節にある `scripts/skill-quick-validate` は、配布元 dotfiles リポジトリ固有の検証スクリプトでこのパッケージには含まれません。動作確認は `python3 scripts/run_codex_cli.py --help` と SKILL.md 記載の No-API Validation を使ってください。
- 実行 artifact は作業リポジトリ配下の `.context/<task>/` に生成されます。必要に応じて `.gitignore` に `.context/` を追加してください。
