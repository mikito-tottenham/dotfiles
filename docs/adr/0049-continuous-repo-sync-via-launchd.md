---
title: "Continuously Sync Push-Permitted Repositories via launchd repo-sync"
date: 2026-07-25
agent_model: "Claude Code (Claude Fable 5)"
status: accepted
---

# ADR 0049: Continuously Sync Push-Permitted Repositories via launchd repo-sync

## Context

ローカルには複数ルート（`~/ghq`、`~/Claude`、`~/.local/share/chezmoi`）に
GitHub リポジトリの checkout が分散しており、リモートとの追従は手動だった。
ユーザー要求は「push 権限があり自分がコミット/push するリポジトリは、
当面継続的に最新版へ追従させ続けること」。

## Decision

- 同期スクリプト `repo-sync`（`dot_local/bin/executable_repo-sync`）を chezmoi 管理で
  `~/.local/bin/repo-sync` に配備する
- launchd LaunchAgent `com.mikito.repo-sync`
  （`Library/LaunchAgents/com.mikito.repo-sync.plist.tmpl`）で
  1 時間ごと + ロード時に実行する
- 同期ポリシー:
  - 対象は origin が github.com で、`gh api repos/<slug>` の `.permissions.push` が
    true のリポジトリ（自分名義に限らず、権限付与された他組織リポジトリも含む）
  - clean（tracked 変更なし）かつ ahead=0 の場合のみ `merge --ff-only` で自動更新
  - ahead / diverged / dirty / upstream なしは自動操作せず ATTENTION として
    ログ + macOS 通知
  - ローカルに存在しない `mikito-tottenham` 名義のリポジトリ（archived 除く）は
    `ghq get` で `~/ghq` に clone する（既存の `~/Claude` 配下の配置は移動しない）
- ログは `~/.local/state/repo-sync/` に出力し、lock・ログ・state は
  machine-local として dotfiles 管理外とする（既存の automation state 方針と同じ）

## Alternatives Considered

- **Claude/Codex Desktop automation**: 決定的処理に LLM を介する必要がなく、
  コストと確実性の面で launchd + シェルスクリプトを採用
- **fetch + 報告のみ（read-only）**: 「最新版に同期し続ける」要求を満たさないため不採用。
  ただし自動操作は ff-only に限定し、分岐・作業中状態には触れない
- **マニフェストファイルによる対象管理**: 実態とズレるため不採用。
  既知ルートの走査 + origin URL 判定で対象を動的に決定する

## Consequences

- clean なリポジトリはリモート更新後 1 時間以内に自動追従する
- 自動 pull 直後に作業セッションが古い前提で動くリスクは、clean + ff-only 限定で低減
- 停止する場合: `launchctl bootout gui/$UID/com.mikito.repo-sync`
- 再登録する場合: `launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.mikito.repo-sync.plist`
- 「当面」の運用が終わったら plist とスクリプトを chezmoi から削除して bootout する
