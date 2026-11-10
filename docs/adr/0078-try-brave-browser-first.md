---
title: "Try the User's Brave Browser First for Browser Operations"
date: 2026-11-10
agent_model: "Claude Code (Claude Opus 5.5)"
status: accepted
---

# ADR 0078: Try the User's Brave Browser First for Browser Operations

## Context

ユーザーが普段使い、ログイン状態・Cookie・1Password 拡張を持っているブラウザは Brave Browser
で、Claude in Chrome 拡張の接続先も Brave である（`~/Claude/AGENTS.md` に 2026-09-09 の実測あり）。

一方で Agent は、ハーネスの既定や Skill の記述に引きずられて、Brave を試す前に次のような
ブラウザを開くことがあった。

- Claude Desktop のアプリ内ブラウザ（browser pane）や Codex App Browser
- `open -a "Google Chrome"` や AppleScript の `tell application "Google Chrome"`。この Mac では
  Google Chrome がプロセスだけ残ってウィンドウ 0 のことがあり、操作が空振りする

ユーザーから見ると「知らないブラウザを勝手に開く」ことになり、ログインのやり直しや
認証情報の扱いの手間が増える。2026-11-10 にユーザーから、Brave を最初に試すルールを
dotfiles 全体で決めるよう指示があった。

## Decision

共通ルール（`.chezmoitemplates/agents-common.md`）に「ブラウザ操作」の節を追加し、Claude Code と
Codex の両方に次を適用する。

1. ユーザーが別のブラウザを指定した場合を除き、最初に Brave Browser を試す。Claude Code では
   Claude in Chrome を使い、複数のブラウザが接続されているときは `list_connected_browsers` で
   Brave を選ぶ。
2. Brave を試す前に、アプリ内ブラウザや Google Chrome・Safari などを開かない。`open -a` や
   AppleScript も `Brave Browser` を対象にする。
3. 別のブラウザへの切り替えは、Brave を操作するツールが無い、再試行しても接続できない、
   Brave では開けないページ、のいずれかに限る。切り替える前に理由を 1 行でユーザーに伝える。
4. 作業中プロジェクトの dev server をハーネスのプレビュー機能（`preview_start` など）で起動して
   確認する場合は例外とし、そのプレビュー画面を使ってよい。

あわせて meeting-minutes skill の `references/soundcore-retrieval.md` の「ブラウザの選び方」を
このルールに揃えた。

## Alternatives Considered

- **`~/Claude/AGENTS.md` だけに書く**: ~/Claude 配下の作業にしか効かず、他の作業ディレクトリや
  Codex では効かない。ユーザーの指示は dotfiles 全体のルールなので採らない。
- **dev server のプレビューも Brave に限る**: Claude Desktop ではハーネスの指示で dev server を
  Bash から起動できず、`preview_start` がサーバー起動とプレビュー画面を兼ねる。これを禁じると
  dev server の確認手段が無くなるため、例外として残す。

## Consequences

- Brave 側のログイン状態と 1Password 拡張をそのまま使えるため、ログインのやり直しが減る。
- Codex には Brave を直接操作する経路が無いことが多い。その場合はルール 3 に当たり、
  理由を伝えてから Codex App Browser などを使う。
- 2026-11-10 の追補で Brewfile に `cask "brave-browser"` を追加し、新しいマシンでは `brew bundle` で
  Brave が入るようにした。既に手動で入れた `/Applications/Brave Browser.app` がある Mac では
  `brew bundle` が既存アプリとの衝突で失敗するため、`brew install --cask --adopt brave-browser` で
  Homebrew の管理下に移す。
