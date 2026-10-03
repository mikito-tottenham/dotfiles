---
title: Fleet cleanup — repo 横断のブランチ / PR / worktree 棚卸しと削除
updated_at: 2026-10-03
source: ~/Claude/.context/2026-09-26-branch-pr-cleanup の scan.py / plan.py / delete_local.py / verify_remote.py を汎用化
---

# Fleet cleanup

複数 repo のブランチ・PR・worktree を棚卸しし、計画 → 承認 → 実行の順で整理する手順。script はすべて `scripts/` にあり、標準ライブラリと `git`、`ghrun gh` だけを使う。

## 守ること

- `.claude/worktrees/` 配下は Claude Desktop セッションの作業場所。その worktree と、そこで checkout 中のブランチは消さない（片付けはセッションのアーカイブで行う）。script も計画・削除・リモート削除のすべてで除外する
- squash マージ済みは祖先判定では検出できない。マージ済み PR の head SHA との一致（scan 時に `merged_pr_heads` として記録）か、merge しても tree が変わらないことで判定する
- 削除・クローズ・マージ・push はユーザーの明示承認を区分ごとに取ってから実行する。承認範囲外の区分（他者のブランチ、未マージの残骸、古い PR のクローズなど）は提案に留める
- 削除系コマンドは `&&`・`;`・パイプで連結せず、1 コマンドずつ単独で実行する（連結すると permission の allow が効かず auto mode classifier に止められる）。classifier に拒否された操作を別の道具で迂回しない
- gh は `ghrun gh` で呼ぶ。401 や token 欠落のときは Agent から再生成せず、ユーザーに通常のターミナルで `ghrun --refresh` を依頼する
- 古い PR をマージする前に、ADR など連番ファイルの番号が default 側と重ならないか確認する（計画の D 区分）

## 手順

成果物は作業 worktree の `.context/<YYYY-MM-DD>-branch-fleet/` に置く（以下 `$D`）。各 Step の JSON / Markdown が次 Step へ進む条件になる。

1. 棚卸し（読み取り専用）

   ```bash
   python3 <skill>/scripts/fleet_scan.py --root "$(ghq root)" --root ~/ghq --out "$D/01-scan.json" [--prune]
   ```

   - `--root` は repo 1 つ、ghq root（host/owner/repo の 3 階層）、`~/Claude/repos` のような symlink 置き場のいずれでもよい。`~/Claude/ghq` と旧配置の `~/ghq` を両方渡すと、後に出た同じ GitHub repo の checkout は `duplicate_of` になり、リモート側の集計は 1 回だけになる
   - 既定では fetch しない。最新化するなら `--fetch`、`upstream gone` を正確に出すなら `--prune`（remote-tracking ref の掃除だけでブランチは消さない）
   - 他社・チームの外部 repo は `--exclude <slug>` で外す
2. 計画（読み取り専用）

   ```bash
   python3 <skill>/scripts/fleet_plan.py --scan "$D/01-scan.json" --out-dir "$D" [--me <自分の author email の一部>]
   ```

   `02-plan.md` の区分: A ローカルのマージ済み / B リモートのマージ済み（自分・他者）/ C open PR / D 連番衝突 / E PR 無しの未マージリモート / F PR クローズ済みの未マージ / G 未 push のローカル / H dirty な作業ツリー / I 消えた worktree の登録 / J 保護対象 / K スキャン失敗
3. 承認を取る: `02-plan.md` の区分ごとの件数と代表例を示し、「どの区分を実行するか」をまとめて 1 回で聞く。承認された区分だけを次へ進める
4. ローカルブランチ削除（区分 A）

   ```bash
   python3 <skill>/scripts/fleet_delete_local.py --plan "$D/02-plan.json" --out "$D/03-local-delete.json"            # dry-run
   python3 <skill>/scripts/fleet_delete_local.py --plan "$D/02-plan.json" --out "$D/03-local-delete.json" --execute  # 承認後
   ```

   削除直前に tip 不変・どの worktree でも checkout されていない・default に取り込み済みを再検証し、外れたものは skip する。`03-local-delete.json` に full SHA が残るので `git -C <path> branch <branch> <full_tip>` で復元できる。`--repo` で承認された repo に絞れる
5. リモートブランチ削除（区分 B、承認がある repo だけ）

   ```bash
   python3 <skill>/scripts/fleet_verify_remote.py --plan "$D/02-plan.json" --out "$D/05-remote-verified.json"
   ```

   この script は削除しない。出力の `CMD` 行（repo ごとの `git -C <path> push origin --delete ...`）をユーザーに示し、承認後に 1 行ずつ単独で実行する。実行後に open PR 数を確認し、巻き添えのクローズが無いことを確かめる
6. worktree の登録掃除（区分 I）は `git -C <repo> worktree prune --dry-run` で確認してから、承認後に repo ごとに単独実行する
7. 結果を `$D/04-result.md` にまとめる: 承認範囲、実施件数、skip 理由、見送り項目、復元方法

## PR のマージ・クローズ

- マージはユーザーが PR を指定して指示した場合だけ、`ghrun gh pr merge <n> -R <slug> --match-head-commit <sha> --<merge|squash|rebase>` を 1 件ずつ単独で実行する。方式は repo の設定と既存運用に合わせる
- auto mode classifier が `Merge Without Review` などで拒否したら再試行も迂回もせず、拒否された PR を列挙してユーザーに渡す
- クローズは提案に留め、明示承認があった PR だけを単独コマンドで閉じる

## repo の取り込みと日常同期

- 新しい repo の clone と置き場所は `ghq-repo-placement` skill に従う（`ghq root` が `~/Claude/ghq` を返すことを確認してから `ghq get`、その後 `~/Claude/repos/` に symlink を 1 本追加）
- push 権限のある repo の定期的な fast-forward 追従は dotfiles 管理の `repo-sync`（`~/.local/bin/repo-sync`、LaunchAgent で毎時実行）が担う。clean かつ fast-forward 可能なものだけ pull し、dirty / ahead / diverged は ATTENTION として報告するので、その一覧を棚卸しの入力にしてよい
