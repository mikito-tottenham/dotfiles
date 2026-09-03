---
title: "1Password 認証経路の適用範囲（oprun のスコープと SSH agent）"
date: 2026-09-03
agent_model: "Claude Opus 5 (claude-opus-5)"
status: accepted
---

# ADR 0055: 1Password 認証経路の適用範囲（oprun のスコープと SSH agent）

## Context

ADR-0036 で「secret 実値は 1Password に置き、`oprun`(= `op run --env-file`) 経由で
プロセス寿命だけ注入する」方針を採用した。その後 2 つの穴が観測された。

1. **oprun のスコープが広すぎた。** 対話 zsh が `alias git='oprun git'` を持っており、
   `git status` / `git log` / `git diff` / `git commit` のようにネットワークも secret も
   要らないローカル操作まで 1Password の認可待ちになっていた。1Password がロック中、
   または非対話セッション（Agent の Bash など）では git 操作が全滅する。
2. **SSH の受け皿が無かった。** `AGENTS-common.md` は「1Password 管理外の SSH 秘密鍵は
   代替経路としても不可」「SSH が要る場合は 1Password の SSH agent を使う」と定めているが、
   管理下の `~/.ssh/config` は存在しない `~/.ssh/id_ed25519` を `IdentitiesOnly yes` 付きで
   指しており、agent を使う設定がどこにも無かった。2026-09-03 時点の当該マシンでは
   `agent.sock` も未生成（1Password アプリ側の SSH agent が無効）だった。

## Decision

- **1Password 依存は「認証が必要な操作」に限定する。** `git` そのものを `oprun` で包まない。
  GitHub への通信に要る `GH_TOKEN` は `~/.gitconfig` の credential helper
  (`!oprun gh auth git-credential`) が必要になった時点だけ取りに行く。
  `gh` は全サブコマンドが GitHub API を叩くため `alias gh='oprun gh'` を維持する。
- **SSH は 1Password の SSH agent を唯一の経路とする。** 管理下 `~/.ssh/config` で
  `Host *` に `IdentityAgent` を指定し、ディスク上の秘密鍵を指す `IdentityFile` と
  `IdentitiesOnly yes` は撤去する（`IdentitiesOnly yes` は agent 側の鍵を弾くため）。
  クライアント固有の鍵は従来どおり管理外の `~/.ssh/config.local` に置く。

## Consequences

- 1Password がロック中でもローカル git 操作と Agent セッションは継続できる。認可が要るのは
  push / fetch / `gh` 実行時だけになる。
- 新しいマシンでは chezmoi 適用に加えて **1Password アプリ側の 2 つのトグルが必要**で、
  これは dotfiles では再現できないマシン固有の手作業として残る。
  - 設定 → 開発者 → 「1Password CLI と統合する」（`op` の認証。無いと `op whoami` が
    `account is not signed in`）
  - 設定 → 開発者 → 「SSH エージェントを使用する」（`agent.sock` の生成）
- 検証は `op whoami --account my.1password.com`、`ssh -G github.com | grep identityagent`、
  `ssh-add -l`（1Password 内の SSH 鍵が並ぶこと）、`ssh -T git@github.com` で行う。
- 認証エラーの一次切り分けは 1Password 側であり、`gh auth login` や平文 token file へ
  実値を落とす回避策は採用しない（ADR-0036 / AGENTS-common.md）。
