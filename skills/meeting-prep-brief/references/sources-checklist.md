---
title: 情報源チェックリストと取得レシピ
updated: "2026-10-03"
source: 業務 repo の定例会議 Skill（references/sources.md）を一般化
---

# 情報源チェックリスト

すべて読み取りで済ませる。経路（gws プロファイル、slack-account プロファイル、MCP コネクタ）は Phase 0 で決めたものだけを使う。`<profile>` は作業ルートの `AGENTS.md` のアカウント境界から決め、ここには書かない。

| # | 情報源 | 主な経路 | 収集期間・対象 |
|---|---|---|---|
| 1 | カレンダー | `gws-account <profile> calendar events list` / Calendar コネクタ | 当日の開催時刻・出席者・添付。前回開催日 |
| 2 | 過去議事録 | repo の議事録ディレクトリ → 未マージブランチ → 会議メモの Doc → メールで届いた会議メモ → 録音（`soundcore-minutes`） | 前回分（必要なら前々回） |
| 3 | Slack | `oprun slack-account <profile> api search.messages ...` / Slack コネクタ | 前回開催日の前日以降 |
| 4 | Gmail | 同梱 `scripts/fetch_gmail.py` → `scripts/fetch_threads.py` / Gmail コネクタ | 同上 |
| 5 | Chatwork | Chatwork MCP の room 一覧 → メッセージ読み取り | 同上（相手先とのルームがあるとき） |

作業 repo にタスク台帳や共有アジェンダ Doc がある場合は 2 の後に読む。

## 1. カレンダー

```bash
gws-account <profile> calendar events list --params '{"calendarId":"primary","timeMin":"<date>T00:00:00+09:00","timeMax":"<date>T23:59:59+09:00","singleEvents":true,"orderBy":"startTime"}'
```

- 定例は振替（祝日・出張）がある。前提日付は必ずカレンダーで確かめる。
- 前回開催日は同じ summary のイベントを過去方向に検索して決める。

## 2. 過去議事録

1. repo の議事録ディレクトリ（`meetings/`、`docs/mtg/` など。repo の README / 索引で確認）。
2. `git fetch origin` の後、議事録を含む未マージブランチを探す: `git log --oneline main..origin/<branch>`、`git diff --stat main origin/<branch> -- <議事録 dir>`。取り出しは `git show origin/<branch>:<path>`。
3. 会議メモの Doc（カレンダー添付や自動生成メモ）。`drive files get` が 404 でも `drive files export`（`text/plain`）は通ることがある。
4. メールで届いた会議メモ（会議ツールの自動要約など）。
5. 録音サービス（`soundcore-minutes`）。同日に複数録音があることがある。

決定事項と宿題（アクションアイテム）を優先して読む。50KB を超える議事録は親で読まず、サブエージェントに要約させる。

## 3. Slack

- slack-account の場合: `oprun slack-account <profile> api search.messages --params '{"query":"in:#<channel> after:<YYYY-MM-DD>","sort":"timestamp","count":100}'`。複数ページは `page` を進める。`oprun` は 1Password の承認を求めることがある。`search.messages` は user token が必要で、bot token のプロファイル（`auth status` の `token_type` で確認）では `conversations.history` / `conversations.replies` を使う。
- コネクタの場合: 検索ツールに `in:#<channel> after:<YYYY-MM-DD>` を渡し、cursor で全件取る。ツール名の接頭辞は接続ごとに違うので ToolSearch で解決する。
- チャンネルの一覧読み取りは、oldest より前に立った親スレッドへの新しい返信を返さないことがある。古いスレッドはキーワード検索で親を見つけてからスレッドを読む。
- 「未回答」と判断する前に、ユーザー本人の発言を期間で検索する。

## 4. Gmail

```bash
python3 <skill-dir>/scripts/fetch_gmail.py --profile <profile> --after <YYYY/MM/DD> --out .context/<task>
# gmail_meta.json から関係するスレッドを選び、threadId を ids.txt に並べる
python3 <skill-dir>/scripts/fetch_threads.py --profile <profile> --ids .context/<task>/ids.txt --out .context/<task>
```

- `--after` は前回開催日の前日。既定で `-category:promotions` を付ける。
- 選別の目安: 会議の相手先、税理士・会計・銀行・決済・電子契約・契約書・請求書・会議ツールの自動要約。SaaS の通知や広告は除く。
- 件数が多い本文の読み込みはサブエージェントに渡す。

## 5. Chatwork

- Chatwork MCP の自分の情報（`get_me`）で接続先を確かめてから、room 一覧 → 対象 room のメッセージを読む。
- 既読化を伴うツールは使わない。メッセージ送信・タスク作成は禁止。

## 情報源ごとの記録

`01-sources.md` に次の表を残す。

| 情報源 | 状態 | 経路 | 期間 | 件数 | 出力ファイル | 備考 |
|---|---|---|---|---|---|---|
| カレンダー | 確認済み／対象外／未確認 | | | | | 未確認なら理由（接続先不一致、認証断など） |
