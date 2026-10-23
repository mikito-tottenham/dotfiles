---
title: "Deploy, Retire, and Sync Distributed Skills Through chezmoi apply"
date: 2026-10-23
worked_at: 2026-10-23 JST
agent_model: "Claude Fable 5.1 (claude-fable-5-1)"
status: proposed
related_adr: ["0045", "0058", "0069", "0072"]
---

# ADR 0073: 配布 skill の配備・撤去・Codex 同期を `chezmoi apply` で完了させる

## Context

first-party skill（`skills/`）と公開 third-party skill の配備は、`docs/skills-install-manifest.md` の
`gh skill install` 一覧を人が（または Agent がその場で書いた script が）実行する docs-only 運用だった。
AGENTS.md は「新しいマシン向けの復元情報は当面 script 化せず manifest を正本」とし、自動化はクラウドの
ephemeral 環境（`scripts/bootstrap-web`、ADR-0045・ADR-0058）に限っていた。

この運用で次の問題が繰り返し出た。

1. **配備漏れと stale。** 2026-10-03（ADR-0069）と 2026-10-23（ADR-0072）の Skill 棚卸しで、撤去済み skill が
   3 配備先（`~/.claude/skills`・`~/.agents/skills`・`~/.codex/skills`）に残り、`gh skill install -f` が正本から消えた
   ファイルを配備先に残すため `first_party_sync` が stale を報告した。2026-10-23 は再 install 後に 4 skill を
   `rm -rf` してやり直し、`metadata.local-path` が別 worktree を指す配備コピーも 2 本見つかった。
2. **ローカルだけ手動。** クラウドは `bootstrap-web` が `chezmoi apply` に続けて skill を復元するのに、
   ローカルは `chezmoi apply` を実行しても skill が揃わず、「apply は済んだが skill は古い」状態が起きた。
3. **同期箇所が 3 つ。** 期待リストが `bootstrap-web` の配列、`verify-cloud-parity` の `THIRD_PARTY_SKILLS`、
   manifest の install 行に分かれ、増減のたびに 3 箇所を手で合わせていた。

一方で、chezmoi には `run_onchange_` script があり、include した内容の hash が変わったときだけ再実行される
（前例: `run_onchange_after_bootstrap-repo-sync.sh.tmpl`）。配備機構そのものは `gh skill install --from-local`
のまま使える。

## Decision

1. **期待リストの正本を `scripts/skill-lists.sh` に一本化する。** `claude_skills` / `codex_skills`（配列名は従来どおり）と
   third-party の pin `third_party_pins`（`owner/repo|commit sha|path|name`）だけを定義する sourced ファイルとし、
   `scripts/bootstrap-web`・`scripts/verify-cloud-parity`・`scripts/deploy-skills` が source する。
   `bootstrap-web` の他の挙動（`cp -a` による first-party 配置、third-party の best-effort 取得、status.json）は変えない。
2. **ローカルの標準配備は `chezmoi apply` とする。** root の `run_onchange_after_deploy-skills.sh.tmpl` が
   `scripts/deploy-skills` を `exec` する。再実行トリガは 3 つの hash（`scripts/skill-lists.sh`、`scripts/deploy-skills`、
   `git ls-files -s skills` の出力）で、skill のリスト・配備 script・`skills/` ツリーの内容のどれかが変わったときだけ走る。
   `git ls-files -s` は index の blob hash を列挙するので commit / stage 済みの変更で発火し、未 stage の作業ツリー変更は
   拾わない。作業ツリー全体を毎 apply 走査する案（`find` + `sha256sum`）は数百ファイルの読み込みが常時乗るため採らず、
   未 stage の確認は `scripts/deploy-skills` の直接実行で行う。
3. **`scripts/deploy-skills` は冪等で、次を 1 回で行う。**
   - preflight: `gh` の有無（無ければ導入手順を出して exit 1）と、manifest の install 行集合（first-party 2 agent 分と
     third-party の `--pin` 行）が `skill-lists.sh` と一致すること。不一致なら差分を出して配備せず exit 1 する
     （**manifest 一致ゲート**。skill-manager の doctor は manifest の install 行を期待値に使うため、両者がずれたまま
     配備すると doctor が誤報する）。
   - 撤去: 3 配備先の first-party 由来ディレクトリ（`SKILL.md` の `metadata.local-path` が source root の `skills/` 配下、
     または manifest の「撤去済み」見出し・撤去表に載る名前）のうち現在の一覧に無いものを
     `~/.local/share/skill-retired/<YYYY-MM-DD>/{claude-skills,agents-skills,codex-skills}/` へ `mv` する。削除はしない
     （ADR-0069 決定 1）。`local-path` が無い skill（third-party、Codex 同梱の `.system` / `hatch-pet` 等）と、
     `local-path` が source 外を指す skill（別 publisher 由来）は触らず、後者はログに残す。
   - first-party: 配備先の既存ディレクトリを `rm -rf` してから、source root を cwd にして
     `gh skill install . <skill> --from-local --agent <agent> --scope user -f` を実行する。Codex は `~/.agents/skills` に
     入るので `rsync -a --delete` で `~/.codex/skills` へ同期する。agent ごとに 1 件、配備コピーの `metadata.local-path`
     が source root 配下を指すことを確認する。
   - third-party: `third_party_pins` どおり `gh skill install <owner/repo> <path> --pin <sha> --agent <agent> --scope user -f`
     を実行する。配備コピーの `metadata.github-pinned` が同じ SHA なら skip する（ネットワークも使わない）。
     当初案の「commit SHA で取得して `--from-local`」は、配備コピーに `local-path` が注入されて doctor の
     `source_drift` / `retired_skills` が `SOURCE_PATH_STALE` / `FIRST_PARTY_NOT_IN_SOURCE` を報告するため採らない。
     公開 repo の `--pin` 取得は GitHub 認証無しで動くことを実測した（2026-10-23、`GH_CONFIG_DIR` を空にして確認）。
   - 完了時に installed / retired / skipped / failed の件数を出し、失敗があれば exit 1 する。最後に
     `skills/skill-manager/scripts/executable_doctor.sh` の実行を案内する（実行はしない）。
   - 進捗はすべて stdout にログする（開始・対象数・各 skill・退避・完了・失敗。secret は含まない）。
4. **素の `gh` を呼ぶ例外。** 共通ルールは `gh` を `ghrun gh` 経由にするが、`deploy-skills` が使う `gh skill install` は
   `--from-local` も公開 repo の `--pin` 取得も GitHub 認証を要求しない。1Password がロックされていても
   `chezmoi apply` を止めないため、`bootstrap-web` と同じく素の `gh` を呼ぶ。`gh` の remote 操作をこの script に
   足すときはこの例外を見直す。
5. **二重実行防止。** `bootstrap-web` は `chezmoi apply` に `DOTFILES_SKIP_SKILL_DEPLOY=1` を付け、run_onchange 側は
   `CLAUDE_CODE_REMOTE=true` または `DOTFILES_SKIP_SKILL_DEPLOY=1` なら skip（exit 0）する。クラウドの skill 配備は
   引き続き `bootstrap-web` が担う。
6. **`gh` 不在時は exit 1。** run_onchange script は `gh` が無ければ WARN ではなく exit 1 で `chezmoi apply` を失敗させる。
   chezmoi は run_onchange の実行済み状態を script が成功したときだけ記録するので、exit 0 で抜けると `gh` 導入後も
   次の apply で再実行されず「apply は通ったが skill は未配備」が固定化する。exit 1 なら `gh` 導入後の apply で
   自動的に再試行される。新しいマシンの手順は `brew bundle`（Brewfile に `gh`）を `chezmoi apply` より先に実行する
   順へ README を改める。
7. **文書。** AGENTS.md の「当面 script 化せず」を撤回し、ローカルの標準配備を `chezmoi apply`、手動を
   `scripts/deploy-skills`、増減時の同期箇所を `scripts/skill-lists.sh` と manifest（install 行と撤去表）の 2 箇所に改める。
   manifest の install 行は手動復旧用の写しとして残す。

## Consequences

- **初回 apply の順序。** 新しいマシンでは `gh` が無いと `chezmoi apply` が deploy-skills で失敗する。README の
  手順を `brew bundle` → `chezmoi apply` の順に改めた。既存マシンでマージ直後に `chezmoi apply` すると、
  run_onchange が初回実行され、first-party 40 件（Claude 20 / Codex 20）を再 install する。
- **`chezmoi apply` の実行時間。** 配備が走る回は `gh skill install` 40 回と rsync 20 回で数秒〜十数秒増える。
  hash が変わらない回は run_onchange が走らないので増えない。
- **部分 apply との関係。** repo の CLAUDE.md は Agent に「対象 target を明示した apply」を求めている。target を
  明示した apply では run_onchange は走らないため、Agent が skill だけを配備するときは `chezmoi apply --include=scripts`
  か `scripts/deploy-skills` を使う。
- **対話プロンプトの既知事項。** `chezmoi status` が `MM` を示す target（2026-10-23 時点で `.gemini/settings.json`・
  `.qwen/settings.json`・`.ssh/config`。アプリ側が書き換えた設定）があると、引数なしの `chezmoi apply` は上書き確認の
  対話プロンプトになる。run_onchange はファイル適用の後に走るので、プロンプトを中断すると skill 配備まで届かない。
  `scripts/chezmoi-drift` で差分を解消してから apply するか、`--include=scripts` で script だけ走らせる。
- **third-party はネットワーク前提。** pin が一致していれば skip するが、pin を上げた直後の apply は github.com への
  匿名取得が必要で、オフラインでは失敗して exit 1 になる（再実行で回復する）。
- **lock ファイルは触らない。** 撤去済み third-party の `~/.agents/.skill-lock.json` エントリ整理は従来どおり手動
  （manifest の退避手順）。`--from-local` の install は lock に記録されないため、first-party には影響が無い。
- **`git ls-files -s` への依存。** source dir が git 管理外（clone でない配置）だと template の `output` が失敗して
  apply が止まる。chezmoi の source は git clone が前提（README）で、この repo では該当しない。

## Verification

- `bash -n` と `shellcheck -x`: `scripts/skill-lists.sh`・`scripts/deploy-skills`・`scripts/bootstrap-web`・
  `scripts/verify-cloud-parity`、および `chezmoi execute-template` で展開した run_onchange script
- `DEPLOY_SKILLS_SOURCE=<worktree> scripts/deploy-skills --dry-run`: preflight 一致、first-party 40 件の install 計画、
  third-party 4 件（2 skill × 2 agent）の pin 一致 skip、失敗 0
- `HOME` を一時ディレクトリに向けた dry-run: `local-path` が source 配下の未掲載 skill と撤去表の skill は退避対象、
  `local-path` の無い同梱 skill と現行 third-party は対象外になることを確認
- `chezmoi execute-template --source <worktree>`: 3 つの hash と `exec` 行が展開され、`chezmoistate.boltdb` の更新時刻は
  変わらない。`chezmoi managed --include=scripts` に `deploy-skills.sh` が出る（`.chezmoiignore` の `scripts` は
  `scripts/` ディレクトリの話で root の run_onchange には掛からない）。`chezmoi apply --dry-run --include=scripts` で
  実行対象として表示される
- `scripts/verify-cloud-parity --quiet` が `skill-lists.sh` から配列を読み、ローカル実環境で MISSING 0
- `scripts/adr-number-check`、`scripts/docs-link-check`
- マージ後にローカルで `chezmoi apply`（または `--include=scripts`）を実行し、deploy-skills のサマリが failed 0、
  `skills/skill-manager/scripts/executable_doctor.sh` で `first_party_sync` / `retired_skills` / `source_drift` が pass
  であることを確認する（本 ADR 作成時点では dry-run のみ。実機配備は未実施）
