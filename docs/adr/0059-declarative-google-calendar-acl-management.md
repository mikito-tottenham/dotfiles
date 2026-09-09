---
title: "Manage Google Calendar Sharing ACLs Declaratively with calendar-acl"
date: 2026-09-09
agent_model: "Claude Code (Claude Opus 5)"
status: accepted
---

# ADR 0059: Manage Google Calendar Sharing ACLs Declaratively with calendar-acl

## Context

本人が使う 5 つの Google アカウント（taskell / yoake / twinplanet / amicitia /
個人 Gmail）のカレンダー共有権限が Web UI 経由の手作業で積み上がり、相互権限が
不統一になっていた。棚卸しの結果、20 通りの組合せのうち 6 件が未共有、5 件が
`freeBusyReader`（予定の詳細が見えない）で、個人 Gmail からは業務カレンダーが
1 件も見えていなかった。

権限の実体は Calendar API の ACL であり、Web UI で 5 アカウント分を突き合わせる
運用では、どのカレンダーに誰が何の権限を持つかを一覧できず、再現性もない。

## Decision

desired state を宣言ファイルに置き、差分適用するツール `calendar-acl` を導入する。

- スクリプト `dot_local/bin/executable_calendar-acl`（→ `~/.local/bin/calendar-acl`）
  - `calendar-acl plan` で差分表示、`calendar-acl apply` で適用。冪等
  - `accounts` に列挙した本人アカウント間は `self_role` を相互に自動付与する
  - `grants` は作成・修正、`revoke` は削除の対象
  - ポリシーに現れない ACL は UNMANAGED として報告するのみで削除しない
- ポリシー実値 `~/.config/calendar-acl/policy.yaml`
  - 第三者のメールアドレスを含み、dotfiles は public のため git 管理しない
  - 1Password の "Secrets Manifest" に登録し `opmaterialize restore` で復元する
  - プレースホルダのみの `dot_config/calendar-acl/policy.example.yaml` を repo に置く

本人 5 アカウント相互は `writer` に統一した。全て本人の資産で情報漏えいのリスクが
なく、どのアカウントでログインしても全予定を一元管理できるため。

## Calendar API の制約（2026-09-09 実測）

- `domain` scope に指定できるのは Workspace のプライマリドメインのみ。ログインに
  使うエイリアスドメインを渡すと `Not Found` になる（`twinplanet.co.jp` は
  エイリアスで、プライマリは `twinplanet.jp`）
- 操作に使っている profile 自身のアクセスレベルは変更できない
  （`Cannot change your own access level.`）。降格するには対象カレンダーの
  データオーナー本人でログインして Web UI から行う
- `writer` は ACL の読み取りが可能で、書き込みのみ `owner` を要する。よって
  owner から降格しても差分検出は継続できる

## Consequences

適用時に事故が 1 件発生した。`domain twinplanet.co.jp` の付与が `Not Found` で
失敗した一方、置き換え対象の `domain twinplanet.jp` の削除だけが成功し、社内への
カレンダー共有が一時的に失われた。同一カレンダーで付与が失敗した場合は以降の削除を
中止するガードを実装し、`plan` で確認してから復旧した。

置き換えを「付与 → 削除」の順に固定するだけでは不十分で、付与の成否を削除の
前提条件として扱う必要がある。同種の破壊的置き換えを行うツールでは同じ順序制約を
設けること。
