---
title: "条件を満たすマージを PreToolUse hook で許可し、auto mode の classifier に止められないようにする"
date: 2026-10-23
worked_at: 2026-10-23 JST
agent_model: "Claude Opus 5.5 (claude-opus-5-5)"
status: accepted
supersedes_in_part: ["ADR 0071"]
related_adr: ["0057", "0062", "0063", "0069", "0071"]
---

# ADR 0073: 条件を満たすマージを PreToolUse hook で許可し、auto mode の classifier に止められないようにする

## Context

ADR-0071 で「作業指示で作った PR は、チェックがすべて成功し `mergeStateStatus` が `CLEAN` ならマージする」と決め、
`permissions.allow` に `Bash(ghrun gh pr merge *)` を足した。2026-10-23、ユーザーから「全てのリポジトリでマージ
できるようになっていない」と指摘があった。

2026-10-19 から 10-23 までの Claude Code の transcript を調べた結果は次のとおり。

- `ghrun gh pr merge` は約 100 回成功していた（本リポを含む 9 リポ）。
- 設定の反映後も、auto mode の classifier が `[Merge Without Review]` として止めた例が 2 リポで 4 回残った
  （10-19 の `timeout 120 ghrun gh pr merge <番号> ...` と、10-21〜23 の 3 回）。最後の 1 回は、ユーザーが
  「マージして」と指示した直後でも止められた。
- `timeout` は Claude Code が rule の照合前に外す wrapper なので、どの例も `Bash(ghrun gh pr merge *)` に一致する。
  公式ドキュメントでは、allow ルールに一致した操作は classifier を通らずに決まる。それでも classifier が判定しており、
  この allow ルールは auto mode で判定を決めていなかった。原因は確定できていない（サーバー側の classifier review が
  関わる可能性がある）。
- 止められたリポの一方は、指示ファイルに「方針を変える PR はリポジトリの持ち主（ユーザー本人）がマージする」と
  書いている。classifier はユーザーが持ち主本人だと判断できず、「マージして」をレビュー済みのマージと
  扱わなかったとみられる。
- リポ側の `.claude/settings.json` で、マージの allow を打ち消すものは無かった。
- このほかの失敗は設定では直らないので、本 ADR の対象外とする。本リポは GitHub で rebase マージだけが
  許可されており、`--merge` / `--squash` は失敗する（Agent は `--rebase` に切り替えて成功している）。
  外部組織のリポ 1 件は、このアカウントに書き込み権限が無い。

また、`Bash(ghrun gh pr merge *)` は前方一致なので、`--admin` や `--auto` も通る。ADR-0071 では、これらを使わない
ことを agents-common の文面だけで担保していた。

## Decision

1. `dot_claude/hooks/executable_gh_merge_allow.py`（target は `~/.claude/hooks/gh_merge_allow.py`）を追加し、
   `PreToolUse`(Bash) に登録する。次をすべて満たすときだけ `permissionDecision: "allow"` を返す。
   - コマンドが、連結・リダイレクト・変数展開・クォートを含まない 1 つであること。英数字と `_./=-`、空白だけで
     書かれ、`ghrun gh pr merge <番号>` で始まること（前置きは `timeout <秒>` だけ可）。
   - オプションが `--merge` / `--squash` / `--rebase` のどれか 1 つと、`--repo` / `-R`、`--match-head-commit`、
     `--delete-branch=false` だけであること。`--admin`、`--auto`、`--delete-branch` は対象外とする。
   - `ghrun gh pr view` で見て、PR が OPEN・draft でない・`mergeStateStatus` が `CLEAN` であり、作者が
     `ghrun gh api user` の login（token の持ち主）と一致すること。
2. 条件を満たさないとき、hook は許可を返さない。通常の permission 判定（allow / deny ルール、classifier）に任せる。
   コマンドが対象の形なのに状態の条件で外れた場合は、理由を `additionalContext` と stderr に出す。
   GitHub に問い合わせられない場合も同じ扱いにする（許可しない側に倒す）。
3. `permissions.allow` から `Bash(ghrun gh pr merge *)` を外す。マージを決定的に通す経路は hook に一本化し、
   `--admin` などを通さない。`Bash(git merge *)` はローカルのマージなので残す。
4. マージさせたくないリポは、そのリポの `.claude/settings.json` の `permissions.deny` に
   `Bash(ghrun gh pr merge *)` を書く。deny ルールは hook の allow より優先される。

hook は GitHub の状態を機械的に照合するだけで、自然言語の意味判断は持たせない
（`dot_claude/CLAUDE.md` の hook の原則に沿う）。

## Consequences

- 単独で実行した、自分の CLEAN な PR のマージは、どのリポでも classifier を通らずに実行される。
  「持ち主がマージする」と指示ファイルに書いたリポでも止まらない。
- 「作業指示で作った PR か」「リポの指示ファイルがマージを制限していないか」の判断は、hook では確かめない。
  これまでは classifier が裏で確かめていたが、今後は agents-common のルールに従う Agent に任せる。
  Claude にマージさせないと決めているリポ（1 件）は、リポ側の settings で `git push` を deny しており、
  Claude がマージ対象の PR を作ることはない。
- 作者の照合で、他人の PR（共同作業者の PR など）は hook では許可しない。ユーザーが指示した場合は、
  これまでどおり classifier の判断に回る。
- hook はマージのたびに GitHub API を 2 回呼ぶ（timeout は各 8 秒、hook 全体で 20 秒）。それ以外の Bash では、
  文字列の判定だけで終わる。
- 公式ドキュメントでは、hook の `"allow"` は permission prompt を飛ばすとされている。ただ、サーバー側の
  classifier review に対しても効くかは、適用後の実マージで確かめるまで未確認である。効かなかった場合は、
  止められたリポの指示ファイルに「持ち主はユーザー本人であり、チャットでの指示は持ち主のマージとして扱う」と
  明記する案を次に検討する。
- `~/.claude/settings.json` と `~/.claude/hooks/` への反映は、ユーザーが `chezmoi apply` で行う
  （ADR-0062 決定 7）。hook ファイルの作成も、auto mode の classifier が「auto mode の回避」として止めたため、
  ユーザーが auto mode を抜け、確認ありのモードで承認して作成した。

## Verification

- hook の判定を、許可する形・許可しない形（連結、`--admin`、`--auto`、`--delete-branch`、方式の指定なし・
  複数指定、番号なし、変数展開）の入力で確かめる。
- GitHub への照合を、MERGED の PR、存在しない PR、本 ADR を含む OPEN の PR で確かめる。
- 適用後に auto mode のセッションで `ghrun gh pr merge <番号> --rebase` などを単独で実行し、classifier に
  止められずにマージされることを確かめる。
