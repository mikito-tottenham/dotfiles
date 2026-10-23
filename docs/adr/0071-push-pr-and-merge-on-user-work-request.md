---
title: "作業指示を承認として扱い、push・PR 作成・マージまで確認なしで進める"
date: 2026-10-19
worked_at: 2026-10-19 JST
agent_model: "Claude Opus 5.5 (claude-opus-5-5)"
status: accepted
related_adr: ["0057", "0062", "0063", "0064", "0065"]
superseded_in_part_by: "ADR 0073"
updated_at: 2026-10-23
updated_by_agent_model: "Claude Opus 5.5 (claude-opus-5-5)"
---

# ADR 0071: 作業指示を承認として扱い、push・PR 作成・マージまで確認なしで進める

## Context

ADR-0065 で `git commit` は確認なしになったが、`git push`・PR 作成・マージは 2026-09-09 の指示のまま
「操作ごと・セッションごとの明示承認」制だった。Agent は作業を終えても push・PR 作成・マージのたびに
止まり、ユーザーの「push して」「マージして」を待っていた。

2026-10-19、ユーザーから「もう自動的に GH をマージできるようにしたい」と依頼があった。確認した結果は次のとおり。

- 範囲は push・PR 作成・マージの一括。force push・タグ・リモートブランチ削除は承認制のまま残す。
- マージ条件は、チェックがすべて成功し `mergeStateStatus` が `CLEAN`（CI の無いリポはコンフリクト無し）。
- 除外するリポや PR は設けない。「私がやってと言ったらできるようになっていればいい」。きっかけはユーザーの作業指示とする。

技術面では次の 2 点が実行を妨げうる。

- `permissions.allow` の `Bash(gh pr merge *)`（ADR-0057 / ADR-0062）は前方一致なので、ADR-0063 で
  Agent の呼び出しを `ghrun gh ...` に変えてからは `ghrun gh pr merge` に一致しない。単独で実行しても
  判断は auto mode の classifier に回る。
- classifier は push・PR 作成を共有状態の変更として扱う。チャットに「push して」が無いと、作業指示だけでは
  止められることがある。

## Decision

1. `.chezmoitemplates/agents-common.md` の「push 以降は操作ごとに承認」の行を次の 2 行に置き換える。
   - ユーザーがチャットで作業を指示した場合、その作業で作ったブランチの push・PR 作成・マージは指示に含まれる
     承認として扱い、commit から続けて確認なしで実行する。マージは実行中のチェックの完了を待ち、すべて成功して
     `CLEAN` のときだけ行う。そうでなければマージせず報告する。ユーザーが「PR まで」などと範囲を限った場合や、
     対象リポの指示ファイルが PR・マージを制限している場合はそちらに従う。
   - force push・タグ・リモートブランチ削除・保護を外すマージ（`--admin` など）と、作業指示の範囲外の PR
     （他人の PR など）は、引き続き操作ごとの明示指示を要する。
2. GitHub の auto-merge（`gh pr merge --auto`）は使わない。各リポで「Allow auto-merge」の設定変更が要るうえ、
   セッション終了後にマージが起きて結果を報告できない。Agent がチェック完了を確かめてから直接マージする。
3. `dot_claude/settings.json` を次のように変える。
   - `permissions.allow` に `Bash(ghrun gh pr merge *)` を足し、ADR-0057 の「単独で実行したマージは決定的に
     通る」状態を `ghrun` 形でも戻す。前方一致なので `--admin` なども通る点は既存の `gh pr merge *` と同じで、
     使わないことは agents-common のルールで担保する。
   - `autoMode.allow` に、作業指示があるときの通常 push・`ghrun gh pr create`・単独マージを許す規則を足す。
     force push・タグ・`--mirror`/`--all`・リモートブランチ削除・既定ブランチへの直接 push・`--admin`/`--auto`/
     `--delete-branch`・作業と無関係なブランチは対象外と明記し、判断は classifier に残す（ADR-0064 と同じ方式）。
4. push・PR を承認待ちとしていた Skill を合わせる。`deliverable-closeout` は push・PR 作成・マージを確認なしで
   進め、Drive 保存だけを 1 回承認する手順にする。`meeting-minutes-ingest` と `client-proposal-pack` の
   「push と PR は承認を待つ」も改める。`git-branch-review` の一括整理（他人のブランチや既存 PR の削除・
   クローズ・マージ）は作業指示の範囲外なので変えない。

## Consequences

- 「やって」の後、Agent は commit → push → PR 作成 → チェック待ち → マージ → 報告まで止まらずに進む。
- 公開リポ（dotfiles など）でも push は確認なしになる。commit 前の機密情報の混入確認（ADR-0065）が、
  外へ出る前の最後の確認になる。
- マージ後に取り消すには revert PR が要る。チェック成功と `CLEAN` を条件にして、壊れた変更が入る範囲を絞る。
- 既存のリポ別制限（例: fukuyama-san-confidential の「Claude に PR を作らせたりマージさせたりしない」）は
  リポ側の指示ファイルが優先するので、そのまま効く。
- `~/.claude/settings.json` への反映は Claude 自身の設定変更になり、auto mode では Agent が適用できない
  （ADR-0062 決定 7）。`chezmoi apply ~/.claude/settings.json` はユーザーが実行する。

## Verification

- このリポ自身の変更を、作業指示だけで push → PR 作成 → マージまで実行できたこと（PR は本 ADR の PR）。
- `chezmoi diff ~/.codex/AGENTS-common.md` が apply 後に空であること。
- ユーザーが `chezmoi apply ~/.claude/settings.json` を実行した後、`ghrun gh pr merge` を単独で実行して
  classifier に止められないこと。
