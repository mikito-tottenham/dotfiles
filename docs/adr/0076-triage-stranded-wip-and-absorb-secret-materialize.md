---
title: "Triage the Stranded WIP, Resolve chezmoi Drift, and Absorb onepassword-secret-materialize into op-cli-runner"
date: 2026-10-23
worked_at: 2026-10-23 JST
agent_model: "Claude Opus 5.5 (claude-opus-5-5)"
status: proposed
related_adr: ["0006", "0016", "0047", "0048", "0049", "0055", "0056", "0063", "0069", "0072", "0073"]
---

# ADR 0076: 退避 WIP の仕分けと chezmoi のずれ解消、`onepassword-secret-materialize` の `op-cli-runner` への吸収

## Context

1. **main checkout に未レビューの変更が残っていた。** 2026-08-13〜10-03 に main checkout で作られ commit されなかった変更
   16 ファイルを、ADR-0073 の配備に main を追従させるため `wip/main-local-leftovers-2026-10-23`（04c071c、親 d72eebc）へ退避した。
   一部は target に適用済みで（`~/.local/bin/opmaterialize`・`~/.local/bin/repo-sync`・Codex automation の `cwds`）、
   `~/.codex/hooks.json` と `~/.codex/hooks/context_guard.py` は source に無いまま chezmoi 管理外の実ファイルとして動いていた。
   ADR-0058 / ADR-0062 が参照する「ADR-0056」（ghq checkout を chezmoi source にする決定）も、この WIP にしか無かった。
2. **`chezmoi status` に 7 target のずれがあった。** 2026-10-23 時点で次のとおりだった。
   - ` M`: `.codex/AGENTS.md`（target が 2026-09-28 の commit 5012cf2 時点の描画と完全一致。ADR-0071 / ADR-0072 の更新が未適用なだけで target 固有の内容は無い）、
     `.codex/automations/daily-ai-brew-upgrade/automation.toml`・`.local/bin/opmaterialize`・`.local/bin/repo-sync`（target が WIP 版）
   - `MM`: `.gemini/settings.json`（target は `mcpServers` が空で末尾改行なし）、`.qwen/settings.json`（末尾改行の有無だけ）、
     `.ssh/config`（target の末尾に同じ `IdentityAgent` を持つ `Host *` が重複して追記されている）
   - chezmoi の挙動を一時 source で実測した。`MM` の target は `--no-tty` の対象指定 apply が上書き確認で EOF になり exit 1 で止まる。
     source と target が同じ bytes なら apply 前から status に出ない。
3. **`onepassword-secret-materialize` の吸収を見送っていた。** ADR-0072 決定 1 は、別セッションがラッパーを編集中であることを理由に
   吸収を次回へ回した。そのラッパー編集は 1 の WIP に入っていた。`op-cli-runner` は既に `opmaterialize` の実行と Restore Pattern を持ち、
   復元方針だけを `$onepassword-secret-materialize` に委ねていた。repo ローカルの `.claude/skills/onepassword-secret-materialize` は
   publisher 版の旧版で、本文は publisher 版の部分集合、固有なのは description の trigger 語だけだった。

## Decision

1. **WIP は 3 つに仕分ける。** 「取り込む」は現行 main と矛盾せず target に適用済みか価値があるもの、「捨てる」は main の決定と矛盾するか
   置き換え済みのもの、「ユーザー判断」は target 側の事情や意図が読めないもの。

   | WIP のファイル | 分類 | 理由 |
   |---|---|---|
   | `dot_codex/automations/daily-ai-brew-upgrade/automation.toml.tmpl` | 取り込む | `cwds` を `.chezmoi.sourceDir` にする。ADR-0056 / ADR-0073 の source 解決と一致し、target と同じ描画になる |
   | `dot_local/bin/executable_opmaterialize` | 取り込む | `chezmoi source-path` による source 解決。決定 3 で `op-cli-runner` の path に改めた |
   | `dot_local/bin/executable_repo-sync` | 取り込む | 走査 root を `ghq root` + `~/Claude` にし、`node_modules` / `.claude/worktrees` を除外、重複 slug を SKIP する。target と同一で、2026-10-23 の実行が error 0 |
   | `dot_codex/create_private_config.toml.tmpl` | 取り込む | `[features].hooks`（codex-cli 0.163.0 の `codex features list` で `hooks` が stable、`codex_hooks` は無い）と、未導入の Pencil MCP の削除。`create_` のため既存 target は変わらない |
   | `dot_gemini/settings.json.tmpl` | 取り込む（一部） | Pencil MCP の削除だけ取り込み、target と同じ `"mcpServers": {}` にする。認証方式の変更は下記のユーザー判断 |
   | `README.md` | 取り込む | 新しいマシンの手順を ghq checkout への clone と machine-local の `sourceDir` 設定に改める。ADR-0073 の `brew bundle` → `chezmoi apply` の順と統合した |
   | `docs/adr/0047-*` / `docs/adr/0049-*` | 取り込む | 上記 2 件（Pencil MCP、repo-sync の走査 root）の記録 |
   | `docs/adr/0056-*` | 取り込む（同じ番号） | main に 0056 は無く、ADR-0058 / ADR-0062 が既にこの番号で参照している。利用者のホームディレクトリの絶対 path を `ghq root` 基準の表記に改め、追補を付けた |
   | `.agents/skills/chezmoi-knowledge` と sync json | 取り込む | AGENTS.md が dotfile 変更前に読むよう求める repo ローカル skill を、Codex からも読めるようにする |
   | `.agents/skills/onepassword-secret-materialize` | 捨てる | 決定 3 で repo ローカル版を削除するため |
   | `docs/adr/0055-import-claude-setup-into-codex.md` | 捨てる | 番号が main の ADR-0055（1Password 認証経路）と重なる。Codex のグローバル hook に artifact gate の互換 shim を置く決定は ADR-0016 / ADR-0069 決定 9 と矛盾する。残す価値のある `[features].hooks` と `.agents/skills` の symlink 運用は本 ADR に記録した |
   | `dot_codex/hooks.json.tmpl` | 捨てる | PreToolUse で repo の `phase_artifact_hook.py` を呼ぶ（ADR-0069 決定 9 に反する）。SUPERSET 通知 5 本は ADR-0072 決定 4 で Claude 側から外したものと同じで、通知先が無い |
   | `dot_codex/hooks/executable_context_guard.py` | 捨てる | 上記 hooks.json からしか呼ばれない。Codex transcript の形式は安定 API ではない |
   | `docs/adr/0006-*` と Gemini の `selectedType = gemini-api-key` | ユーザー判断 | WIP は 2026-08-12 に `oauth-personal` が拒否されたと記すが、target は今も `oauth-personal` で、`~/.gemini/oauth_creds.json` は 08-14 に更新されている |

2. **ずれは source を正しくして解消し、`--force` は使わない。**
   - `.codex/AGENTS.md` と `.local/bin/opmaterialize` は対象指定の `chezmoi apply` で直す（どちらも ` M` で確認は出ない）。
   - automation.toml と repo-sync は取り込みで source と target が一致し、マージ後は apply せずに status から消える。
   - Gemini CLI と Qwen Code は settings.json を末尾改行なしで書き戻す。source を同じ bytes（末尾改行なし）にして、内容が同じなのに
     `MM` になり対話確認で止まる状態をなくす。
   - `.ssh/config` の重複 `Host *` は source に取り込まない。`MM` のため Agent は上書きできず（repo の CLAUDE.md が `--force` を禁じる）、
     ユーザーが自分の terminal で `chezmoi apply ~/.ssh/config` を実行して上書きを選ぶか、残すかを決める。
3. **`onepassword-secret-materialize` を `op-cli-runner` に吸収する。** first-party は 21 本 → 20 本（Claude Code / Codex 各 19 本）。
   - `SKILL.md` 本文を `skills/op-cli-runner/references/materialize.md`、`scripts/opmaterialize` を `skills/op-cli-runner/scripts/` へ
     `git mv` する。`op-cli-runner` の `SKILL.md` には Secret-Backed Files 節を 1 つ足し、description は 500 字以内で
     「opmaterializeで復元」「secret-backed file を登録」などの trigger 語を保つ。
   - `~/.local/bin/opmaterialize` は `~/.codex/skills/op-cli-runner`、`~/.claude/skills/op-cli-runner`、`chezmoi source-path` 配下の
     `skills/op-cli-runner` の順に script を探す。旧 skill の path へはフォールバックしない。見つからなければ exit 127 で配備方法を出す。
   - repo ローカルの `.claude/skills/onepassword-secret-materialize` は削除する。固有だった trigger 語は `materialize.md` の冒頭に入れ、
     dotfiles 固有の検証手順は同ファイルの「Changing The Tool」節に残した。global に置けない repo 固有手順は無かった。
   - 撤去は ADR-0069 決定 1 / ADR-0073 決定 3 のとおり、`docs/skills-install-manifest.md` の撤去表に載せ、`scripts/deploy-skills` が
     3 配備先のコピーを `~/.local/share/skill-retired/<date>/` へ退避する。
4. **ADR-0055 の下書きから残すもの。** Codex の create-only seed は `[features].hooks = true` とする（repo ローカルの
   `.codex/hooks.json` を動かすため。ADR-0016 の repo enforcement の置き場は変えない）。repo ローカル skill は `.claude/skills/` を正本とし、
   Codex には `.agents/skills/` の symlink で見せる（コピーを置かない）。

## Consequences

- **マージ後の適用順。** 正本 checkout を main に追従させてから、`chezmoi apply ~/.codex/AGENTS.md ~/.local/bin/opmaterialize`、
  続けて `chezmoi apply --include=scripts`（`deploy-skills` が 38 件を install し、旧 skill の 3 配備先コピーを退避する）、最後に
  `skill-manager` の doctor を実行する。ラッパーを先に入れても、配備前は `chezmoi source-path` 配下の script を使うので動く。
- **管理外の `~/.codex/hooks.json` は残る。** source に入れないので chezmoi は触らない。実機では今も artifact gate の互換 shim と
  SUPERSET 通知が動いており、ADR-0069 決定 9 と食い違う。消すか、context guard と SessionStart の `opmaterialize restore` だけ残すかは
  ユーザーが決める。
- **Gemini の認証方式は未決。** API key 方式へ移るなら `dot_gemini/settings.json.tmpl` と ADR-0006 を WIP のとおり直す。
  `oauth-personal` を続けるなら変更は要らない。
- **アプリが書き戻すと再びずれる。** Gemini / Qwen が設定を書き換えれば `MM` に戻る。末尾改行を合わせたのは改行だけのずれを
  なくすためで、内容の変更は従来どおり `scripts/chezmoi-drift` で取り込むか戻すかを決める。
- **範囲外で見つけたもの。** `dot_gemini/settings.json.tmpl` の SUPERSET hook は `~/.superset/hooks/` が無いまま 3 event に残っている
  （ADR-0072 決定 4 は Claude 側だけを外した）。README と `docs/web-session-runner-setup.md` は「`opmaterialize add` は field 方式の
  manifest を拒否する」と書くが、ADR-0048（field 方式対応）以降の script は field 方式でも登録する。どちらも今回は直していない。
- **再検討条件:** secret-backed file の運用が `op` 以外のバックエンドを持つなど、`op-cli-runner` から分ける必要が出た場合。

## Verification

- `scripts/skill-quick-validate skills/*`: 20 本 valid、WARN 0（`op-cli-runner` の description 496 字）
- `bash -n` / `sh -n` と `shellcheck`: `dot_local/bin/executable_opmaterialize`、`dot_local/bin/executable_repo-sync`、
  `skills/op-cli-runner/scripts/opmaterialize`
- `DEPLOY_SKILLS_SOURCE=<worktree> scripts/deploy-skills --dry-run`: preflight 一致、installed 38 / retired 3（旧 skill を 3 配備先から）/
  skipped 4 / failed 0
- ラッパーの解決（`HOME` を `.context/` の一時ディレクトリに向けて `--help` を実行。1Password には触れない）: Claude の配備先にある
  script、`chezmoi source-path` 配下の script はどちらも usage を出して exit 0。旧 skill の path にだけ script がある場合は exit 127
- `chezmoi --source <worktree> status`: Gemini / Qwen / repo-sync が消え、`.codex/AGENTS.md`・`opmaterialize`・`.ssh/config`・
  `deploy-skills.sh` と、worktree path で描画される automation.toml だけが残る
- `grep -rn onepassword-secret-materialize --exclude-dir=.git --exclude-dir=adr --exclude-dir=worktrees .` が manifest の撤去記録だけ
- `scripts/adr-number-check`、`scripts/docs-link-check`、`scripts/verify-cloud-parity --quiet`
- 機密 grep: 変更ファイルに `op://` の実値、メールアドレス、ホスト名、IP、利用者のホームディレクトリの絶対 path が無いこと
