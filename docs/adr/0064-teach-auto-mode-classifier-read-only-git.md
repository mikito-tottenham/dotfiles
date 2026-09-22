---
title: "auto mode の classifier に読み取り専用の git 確認を許可として教える"
date: 2026-09-22
agent_model: "Claude Opus 5 (claude-opus-5)"
status: accepted
---

# ADR 0064: auto mode の classifier に読み取り専用の git 確認を許可として教える

## Context

2026-09-21、ADR-0063 のコミット直後の確認で、読み取りしかしない `git log` / `git status`
（`git -C <path> status -sb` など）を auto mode の classifier が 2 回拒否した。理由は
`Modify Shared Resources` と `Git Destructive` で、どちらも誤判定である。Claude が作業結果を
自分で確認できなくなるため、ユーザーから「全体のルールとして設定して」と指示があった（2026-09-22）。

`permissions.allow` の前方一致ルール（`Bash(git status *)` など）だけでは足りない。

- `git -C <path> status` の形は `git status` で始まらないので一致しない。
- `Bash(git -C * status *)` のように途中に `*` を置くと、`git -C /x -c core.fsmonitor=<cmd> status` の
  ように設定を差し込む形まで一致してしまい、任意のコマンド実行を無確認で通す穴になる。
- `git diff` / `git log` / `git show` は `--output=<file>` でファイルを書けるので、前方一致の allow は
  classifier の判断を飛ばしてファイル書き込みまで通してしまう。

## Decision

- ユーザー設定（`~/.claude/settings.json`。source は `dot_claude/settings.json`）の `autoMode.allow` に、
  `$defaults`（既定ルールの継承）と、読み取り専用の git 確認を許可する規則を 1 つ追加する。
  対象は `git status` / `git log` / `git diff` / `git show` / `git branch --show-current` /
  `git rev-parse` / `git ls-files`。`git -C <path>` の形と、`head` / `grep` / `sed -n` / `wc` / `cut`
  へのパイプも含める。
- 同じ規則の中で、除外するものを明示する。その場で設定や環境変数を差し込むもの（`-c`、`--config-env`、
  `GIT_*=`）、ファイルを書くもの（`--output`）、外部プログラムを実行するもの（`--ext-diff`）、
  状態を変えるサブコマンドは許可しない。
- `permissions.allow` には追加しない。classifier の判断を飛ばさず、判断材料を与える方式にする。
- 適用はユーザーが実行するスクリプトで行う（`.context/2026-09-21-op-touchid/apply-automode-allow.py`）。
  ADR-0062 決定 7 のとおり classifier は Claude 自身の設定の編集を「自己変更」として拒否し、今回は
  source の編集とコピーでの試験も拒否された。live には `chezmoi apply` を使わず `autoMode` だけを差し込む。
  live の `~/.claude/settings.json` には ADR-0062（e76e12b）で source から外した pencil MCP の許可と
  oasys の plugin / marketplace が未配備のまま残っており、`chezmoi apply` はその配備まで巻き込むためである。

## Consequences

- 読み取り専用の git 確認が誤判定で止まりにくくなる。判断は classifier のままなので、除外した形や
  状態を変える git 操作は引き続き止められる。
- commit / push などの状態変更は、agents-common の「操作ごとにユーザー承認」ルールのまま変えない。
- Codex には auto mode の classifier が無いため対応項目なし。
- ADR-0062 の未配備分（上記の pencil / oasys）は今回の範囲外として残る。`chezmoi apply ~/.claude/settings.json`
  を実行すれば、今回の `autoMode` を保ったまま ADR-0062 の削除も反映される。

## Verification

2026-09-22、ユーザーがスクリプトを実行した後に確認した。

- 前回拒否された `git -C <repo> status -sb` と `git -C <repo> log -2 --stat` が、classifier に止められず実行できた。
- `git diff -- dot_claude/settings.json` は `autoMode` の追加だけで、他の行の整形は変わっていない。
