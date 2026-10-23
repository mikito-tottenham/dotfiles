---
title: "fleet のリモート削除保護を、同じ GitHub repo の全 checkout と直近 24h の worktree に広げる"
date: 2026-10-23
worked_at: 2026-10-23 JST
agent_model: "Claude Opus 5.5 (claude-opus-5-5)"
status: accepted
related_adr: ["0063", "0069"]
---

# ADR 0074: fleet のリモート削除保護を、同じ GitHub repo の全 checkout と直近 24h の worktree に広げる

## Context

`git-branch-review` の fleet mode（ADR-0069）は、Claude Desktop セッションの worktree（`.claude/worktrees/`）で
checkout 中のブランチを削除対象から外す前提で作られていた。2026-10-23 の棚卸し
（`~/Claude/.context/2026-10-23-branch-fleet/`、46 checkout）で、リモート側の保護に 3 つの穴が見つかった。

1. **計画がリモート側で保護していない。** `fleet_plan.py` はローカルブランチだけを worktree で除外し、
   リモートのマージ済みブランチは worktree を見ずに `remote_delete_mine` へ入れていた（81 本のうち 26 本が
   セッション worktree で checkout 中）。除外は `fleet_verify_remote.py` だけが行い、それも plan の `path`
   （primary checkout）の worktree しか見ていなかった。同じ GitHub repo を 2 か所に checkout していると
   （`rmanzoku/taskell-management` と `taskell-ai/taskell-management`、後者は `duplicate_of`）、2 つ目の checkout の
   セッション worktree で checkout 中の `feat/training-cloudflare-setup` が再検証も通過した。
2. **転送された repo が 2 つに数えられる。** `mikito-tottenham/collab-hatakeyama` は `taskell-ai/collab-hatakeyama`
   へ転送済みで、旧配置の checkout の origin URL は旧 slug のままだった。scan は origin URL の文字列で重複を
   判定していたため別 repo として扱い、同じリモートブランチ 3 本が二重に計画へ載った。旧 slug 側の 3 本は
   新 slug 側のセッション worktree で checkout 中のブランチで、旧 slug 経由の push もリダイレクトで同じ repo に届く。
3. **直近 24h の作業が保護されていない。** `~/Claude/AGENTS.md` は直近 24h に動きのある worktree / 未マージ
   ブランチを整理対象外とするが、script はセッション外の worktree で checkout 中のブランチを
   「ローカルで checkout 中」と注記するだけで、削除コマンドに含めていた（例: 当日の作業中だった dotfiles の
   `claude/chezmoi-skill-deploy`）。

当日の提案（`03-proposal.md`）はこれらを手作業で除外して整合を取っていた。

## Decision

1. `fleet_scan.py` は origin URL の slug を `ghrun gh repo view --json nameWithOwner` で GitHub 上の現在の
   owner/name に解決し、それを `slug` として PR 取得と重複判定に使う。origin URL の値は `origin_slug` に残す。
   解決に失敗した checkout は `slug_error` を記録してログに出し、origin の slug のまま扱う（PR 取得失敗の
   `pr_error` と同じ扱い）。`--no-pr` では GitHub に問い合わせない。
2. `fleet_scan.py` はセッション外の worktree と main checkout ごとに `last_activity`（HEAD のコミット時刻、
   HEAD の reflog、未コミットのファイルの mtime のうち最新）を記録する。`git status` / `git fetch` はどれも動かさない。
3. `fleet_plan.py` は、同じ `slug` を持つ全 checkout（`--exclude` で外した checkout も含む）の worktree から、
   リモートのマージ済みブランチを B 区分の外に出す。
   - セッション worktree で checkout 中 → `kept_in_session_worktree`
   - セッション外の worktree / main checkout で checkout 中かつ直近 `RECENT_HOURS`（24h）に動きあり →
     `kept_recent_worktree`
   - B の各項目に、その repo の全 checkout の path を `checkouts` として載せる
4. `fleet_verify_remote.py` は `checkouts` の全 checkout の worktree を実行時に読み直し、上の 2 条件に当たる
   ブランチを skip する。`checkouts` の無い古い plan と、読めない checkout を含む repo はコマンドを出さずに
   skip する（primary checkout だけを見る旧挙動へ黙って戻さない）。

## Consequences

- 2026-10-23 の scan に新しい plan を適用すると `remote_delete_mine` は 81 本から 54 本になり、
  `feat/training-cloudflare-setup` を含む 26 本が `kept_in_session_worktree`、1 本が `kept_recent_worktree` に入る。
  新しい scan では転送前 slug の checkout が `duplicate_of` になり、二重計上の 3 本も消える。
  手作業の除外は `archive/*` のような意図的な退避ブランチだけになる
- scan は checkout ごとに `gh repo view` を 1 回（同じ origin slug は 1 回にまとめる）、セッション外の worktree ごとに
  git コマンドを数回多く呼ぶ
- 古い plan は verify で使えなくなる。fleet_plan.py を再実行すれば足りる（scan のやり直しは不要）
- `last_activity` の無い古い scan では worktree の最終コミット日で判定し、前日以降なら直近として扱う（保護を広く取る側）
- 24h の閾値は `fleet_common.RECENT_HOURS` の定数とし、CLI フラグは設けない

## Verification

- 2026-10-23 の `01-scan.json` に新しい `fleet_plan.py` を適用し、上記の件数を確認した
- 旧 plan の項目に両 checkout の `checkouts` を付けた合成 plan で `fleet_verify_remote.py --no-fetch` を実行し、
  `feat/training-cloudflare-setup` が taskell-ai 側のセッション worktree を理由に skip されることを確認した。
  dotfiles の `claude/chezmoi-skill-deploy` は 24h ルールで skip され、旧 `02-plan.json` は repo ごと拒否された
- 新しい scan（fetch なし）で `mikito-tottenham/collab-hatakeyama` の checkout が `taskell-ai/collab-hatakeyama` の
  `duplicate_of` になることを確認した
- いずれも削除は実行していない（verify は削除しない script で、`CMD` 行は実行していない）
