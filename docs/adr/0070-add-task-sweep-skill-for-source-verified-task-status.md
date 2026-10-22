---
title: "Taskell のタスク完了をソースの証拠で判定する first-party skill task-sweep を追加し、台帳を持たない"
date: 2026-10-03
agent_model: "Claude Opus 5.5 (claude-opus-5-5)"
status: accepted
---

# ADR 0070: Taskell のタスク完了をソースの証拠で判定する first-party skill task-sweep を追加し、台帳を持たない

## Context

2026-10-03、ユーザーから、バックオフィス担当へ事務作業を渡す前に、自分のタスクが本当に終わっているかを繋がっている全ソースから判定する仕組みがほしいという依頼があった。口頭やメモ上の「済み」「未着手」と、メール・Slack・Chatwork・Drive・カレンダー・git 上の実態がずれることがあり、渡す対象を誤ると二重作業や抜けが起きる。

仕様は taskell-management の作業 artifact（`.context/` 配下、git 管理外）で固め、次の 4 点はユーザーが決定した。

- 置き場所: グローバル Skill（本リポジトリの publisher layout `skills/`）
- 台帳: 持たない。毎回ソースから拾い直す
- 実行: 手動のみ。定期実行は作らない
- 対象: Taskell だけ

## Decision

- first-party skill `skills/task-sweep/` を追加する。`SKILL.md` に前提・手順・5 区分の判定ルール・機密の扱いを置き、ソース経路と読み取り専用の操作範囲は `references/sources-taskell.md`、artifact と報告の書式は `references/output-format.md` に分ける
- ソースは Taskell Slack（`oprun slack-account taskell`）、Chatwork MCP、Gmail / Calendar / Drive（`gws-account taskell`）、taskell-management の `origin/main` とする。claude.ai の Slack / Gmail コネクタは別アカウントのため使わない。疎通に失敗したソースは別経路へ fallback せず `判定不能（ソース不通）` の根拠として記録する
- 読み取り専用を Skill 本文と references で定める。`slack-account api` は allowlist を持たず `taskell` プロファイルの token は書込 scope を持つため（ADR-0061）、使ってよい Slack method を列挙して、それ以外を呼ばないことにする。Chatwork は既読状態を変える `read_room_messages` / `unread_room_message` も使わない操作に含める
- 状態は `完了` / `進行中` / `未着手` / `不要になった` / `判定不能` の 5 区分とし、`完了` は一次証拠がある場合だけ付ける。証拠が食い違う場合は `判定不能` として両方の出典を書く。メモ・auto memory・議事録は補助証拠とする
- 手順は `01-preflight` → `02-candidates-<source>` → `03-resolution` → `04-report` の 4 Phase とし、各 Phase の artifact を作業リポジトリの `.context/task-sweep/<YYYY-MM-DD>/` に保存してから次へ進む（共通ルールの artifact gate）
- Claude Code / Codex の両方へ first-party として配備対象にし、`docs/skills-install-manifest.md` と `scripts/bootstrap-web` の配列に追加する。`scripts/verify-cloud-parity` は配列を `bootstrap-web` から読むため変更しない
- 作らないもの: 定期実行（scheduler・cron・hook）、Taskell 以外の会社向けプロファイル枠、台帳ファイル、書き込み系の操作

## Consequences

- 渡す前の確認を、メモの記述ではなくソースの証拠で行えるようになる。根拠の出典が報告に残るため、受け取る側も確認できる
- 台帳を持たないため、前回との差分や「前回は見つけたが今回は見落とした」タスクを機械的に検出できない。取りこぼしを後から検証しにくいことは意識的に受け入れる。その代わりに、報告の末尾へ「ソース不通」「探したが見つからなかった範囲」「新規候補」を必ず書かせ、探索範囲の記録を検証の手がかりにする
- 毎回全ソースを読み直すため、実行時間と API 呼び出しは台帳方式より多い。手動実行に限るので許容する
- Chatwork のメッセージ取得は 1 ルーム最新 100 件までのため、発言の多いルームでは期間内でも古い発言を確認できない。その範囲は報告に明記させる
- 書き込み禁止は Skill の指示による運用ガードであり、CLI 側の強制ではない。Chatwork は taskell-management の `.claude/settings.json` で書込ツールが `ask` になっているが、Slack と gws には同等の機械的な歯止めが無い
- クラウドの ephemeral 環境では Taskell の認証経路が揃わないことが多い。その場合も skill は配備されるが、実行すると多くのソースが `判定不能（ソース不通）` になる
- 対象を他社へ広げる場合や定期実行が必要になった場合は、本 ADR を更新してから Skill を変更する

## 追補（2026-10-23、ADR-0072）

- 本 ADR の skill は worktree ブランチのまま配備され、main に未マージだった。2026-10-23 の再棚卸しで、SKILL.md と
  references に会社固有値（gws / Slack の profile 名、対象 repo 名）が直書きされており公開 repo の規則（ADR-0069 決定 3）
  と衝突することが分かった
- 決定: repo ローカル skill へ移す案は採らず、会社固有値を repo 側 profile（雛形は `references/sources-profile-template.md`）に
  分離して main へ取り込む。skill 本文はソース種別（Slack / Chatwork / Gmail / Calendar / Drive / git）と判定ルールだけを持つ。
  対象を 1 社に限る・台帳を持たない・手動のみの決定は変えない
- 配備コピーが未マージ worktree を指す状態を検出するため、`skill-manager` doctor に `source_branch` を追加する（ADR-0072 決定 5）
