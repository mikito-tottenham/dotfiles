---
title: "Keep Account Email Addresses Out Of The Repository"
date: 2026-09-09
agent_model: "Claude Code (Claude Fable 5.1)"
status: accepted
---

# ADR 0060: Keep Account Email Addresses Out Of The Repository

## Context

この dotfiles リポジトリは public であり、かつ `rmanzoku/dotfiles` の fork として fork network を
共有している。共通ルール正本 `.chezmoitemplates/agents-common.md` の gws 節には、プロファイルと
アカウントの対応として業務アカウント 4 件・個人アカウント 1 件・他環境アカウント 1 件の実メール
アドレスが書かれており、うち 3 件は 2026-07-25 以降、1 件は 2026-08-19 以降 `origin/main` で公開
されていた（残り 2 件は未 push commit にのみ存在）。

要件は「メールアドレスを公開しない」であり、リポジトリ全体の private 化ではない。private 化は
fork のため単体では不可能で、README / cloud setup script の無認証 clone 経路も壊す。

一方、実アドレスは文書に持たなくても実行時に取得できる。`gws-account <profile> auth status` の
`user` フィールドに認証済みアカウントのアドレスが載ることを実測した（`token_valid` と併せて確認
可能）。`gws-cli-runner` skill も account mapping を machine-local state として扱うと規定している。

## Decision

1. git 管理下の文書・コミットメッセージに gws アカウントの実メールアドレスを書かない。
   プロファイルと組織ドメインの対応のみを文書に残し、実アドレスが必要な場面では
   `gws-account <profile> auth status` の `user` を実行時に参照する。このルールを
   `agents-common.md` の gws 節に追加した。
2. 未 push の commit に含まれていた未公開アドレス 2 件は、その commit を作り直して push 履歴に
   載せない。
3. 2026-07-25〜08-19 から公開済みの 4 件（業務用 3 件 + 他環境 1 件）については履歴書き換え
   （`git filter-repo` + 全ブランチ force push）を行わない。fork network 共有のため force push
   だけでは by-SHA 到達性が消えず GitHub Support への purge 依頼が別途必要になること、
   36 commit 以上の SHA 変更が全 clone と cloud setup キャッシュに波及すること、既に数週間
   公開済みであることから、HEAD からの削除（GitHub code search と通常閲覧からの除外）に留める。
4. 一方、本 ADR の作業中に並行セッションが未 push commit を `git pull --rebase` で再生して push
   したため、未公開だった個人アドレス 1 件と業務アドレス 1 件が `origin/main` に入った
   （2026-09-09T04:52Z、PR 参照なし、GitHub code search 未インデックス）。この直近 2 commit に
   限り、メールアドレスを除いた形で作り直して `--force-with-lease` で main を置き換え、到達不能
   になった旧 commit の purge を GitHub Support へ依頼する。書き換え範囲が 2 commit・同一マシンの
   clone に限られ、公開から数分であることが 3 との判断の分かれ目である。

## Consequences

- agent が実アドレスを必要とする場面（再認証依頼で選ぶべきアカウントの明示など）では、
  `auth status` を 1 回実行する手間が増える。
- 組織ドメイン名は文書に残るため、所属組織は引き続き読み取れる。これは本 ADR の対象外。
- 公開済み 4 件を含む過去 commit の by-SHA 閲覧は残る。将来 purge を行う場合は別 ADR で
  履歴書き換えと GitHub Support 依頼を扱う。
- 直近 2 commit の作り直しにより main の SHA が 2 件変わる。同一マシンの main checkout は
  `git reset --keep origin/main` で追従させる。旧 commit は refs から到達不能になるが by-SHA では
  残るため、GitHub Support への purge 依頼を行う。

## 検証

- `git grep -nE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}'` で `noreply` 以外の一致が 0 件
- `gws-account amicitia auth status` の出力に `user` キーがあり、`token_valid` が `true`
