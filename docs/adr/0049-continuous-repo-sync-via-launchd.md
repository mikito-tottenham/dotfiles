---
title: "Continuously Sync Push-Permitted Repositories via launchd repo-sync"
date: 2026-07-25
agent_model: "Claude Code (Claude Fable 5)"
updated_at: 2026-08-14
updated_by: "Codex (GPT-5)"
status: accepted
---

# ADR 0049: Continuously Sync Push-Permitted Repositories via launchd repo-sync

## Context

ローカルには複数ルート（`ghq root`、`~/Claude`）に
GitHub リポジトリの checkout が分散しており、リモートとの追従は手動だった。
ユーザー要求は「push 権限があり自分がコミット/push するリポジトリは、
当面継続的に最新版へ追従させ続けること」。

また複数 PC で運用しており、接続が断続的なサブ PC では毎時実行が
オフライン時間帯に空振りするため、「インターネットに接続された時点で
同期する」トリガーが必要になった。運用方針は「自動実行を土台に、
作業直前だけ手動 `repo-sync` を併用する」で合意している。

初期実装は `~/Claude` を `find -maxdepth 4` で走査していたが、
`~/Claude/ghq/github.com/<owner>/<repo>/.git` は深さ 5 となるため、
`ghq root` 配下の checkout を検出できなかった。その結果、同じ slug の repository を
既定の別 root へ二重 clone した。内容一致かつ clean な重複 checkout は解消し、
固有作業が残る checkout は自動操作の対象外として保持した。

## Decision

- 同期スクリプト `repo-sync`（`dot_local/bin/executable_repo-sync`）を chezmoi 管理で
  `~/.local/bin/repo-sync` に配備する
- launchd LaunchAgent `com.mikito.repo-sync`
  （`Library/LaunchAgents/com.mikito.repo-sync.plist.tmpl`）で
  1 時間ごと + ロード時 + ネットワーク構成変化時に実行する
  - ネットワーク変化は `WatchPaths`（`/etc/resolv.conf`、
    `/Library/Preferences/SystemConfiguration/NetworkInterfaces.plist`）で検知する。
    deprecated で不安定な `NetworkState` キーは使わない
  - スクリプトは実行冒頭で `nc -z -w 3 github.com 443` の到達性ゲートを通し、
    オフライン時は OFFLINE とログして正常終了する（エラー・通知にしない）
  - launchd からの起動には `--debounce` を付与し、前回成功から 300 秒以内は
    SKIP する（ネットワークイベントのバースト対策）。手動実行はデバウンスなしで
    常にフル実行され、「作業直前に確実に最新化する」安全弁として機能する
- 同期ポリシー:
  - 対象は origin が github.com で、`gh api repos/<slug>` の `.permissions.push` が
    true のリポジトリ（自分名義に限らず、権限付与された他組織リポジトリも含む）
  - clean（tracked 変更なし）かつ ahead=0 の場合のみ `merge --ff-only` で自動更新
  - ahead / diverged / dirty / upstream なしは自動操作せず ATTENTION として
    ログ + macOS 通知
  - ローカルに存在しない `mikito-tottenham` 名義のリポジトリ（archived 除く）は
    `ghq get` で `ghq root` に clone する（既存の `~/Claude` 配下の配置は移動しない）
- 走査 root は実行時の `ghq root` と `~/Claude` とする。
  `node_modules` と `.claude/worktrees` は探索から除外し、同じ origin slug が
  複数 path で見つかった場合は最初の checkout だけを同期して残りを明示的に SKIP する
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

- clean なリポジトリはリモート更新後 1 時間以内に自動追従する。
  断続接続のマシンでもネット接続時（DNS/インターフェース構成変化時）に
  即座に同期される
- 別マシンへの展開は `chezmoi update`（または `chezmoi apply`）だけで完結する。
  `run_onchange_after_bootstrap-repo-sync.sh.tmpl` が plist の内容ハッシュを
  埋め込んでおり、初回 apply および plist 変更時に launchd への
  bootout + bootstrap を自動実行する
  - 前提: `brew bundle`（gh / ghq は Brewfile 登録済み）と `gh auth login` が
    済んでいること。gh 未認証でもサービスは起動し、権限確認不可の SKIP として
    ログに現れるだけで壊れはしない
- 自動 pull 直後に作業セッションが古い前提で動くリスクは、clean + ff-only 限定で低減
- 停止する場合: `launchctl bootout gui/$UID/com.mikito.repo-sync`
- 再登録する場合: `launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.mikito.repo-sync.plist`
- 「当面」の運用が終わったら plist とスクリプトを chezmoi から削除して bootout する
