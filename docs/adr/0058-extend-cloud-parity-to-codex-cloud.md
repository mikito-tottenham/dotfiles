---
title: "Extend Cloud Parity To Codex Cloud And Verify It"
date: 2026-09-01
agent_model: "Claude Code (Claude Opus 5)"
status: accepted
---

# ADR 0058: Extend Cloud Parity To Codex Cloud And Verify It

## Context

ADR-0045 は Claude Code on the web の ephemeral 環境について、`scripts/bootstrap-web` による
再現を定めた。しかし以下が未解決だった。

1. **Codex cloud が対象外**。`bootstrap-web` の `REPO_DIR` は `CLAUDE_PROJECT_DIR` を優先して
   解決するため、Claude 以外のクラウドから source を固定する手段が無かった。
2. **再現差分を確認する手段が無い**。`status.json` は bootstrap 自身の実行結果しか持たず、
   「ローカルにあってクラウドに無いもの」を突き合わせる経路が無かった。個々の項目は
   セッションごとに手で `command -v` して確かめるしかなかった。
3. **`jq` が導入対象に無い**。`onepassword-secret-materialize` の field 方式は `jq` を必須依存に
   しており（ADR-0046）、未導入だと restore が field 方式分だけ静かに欠ける。
4. **MCP が再現対象外**。ローカルの MCP のうち `mfc_ca` は URL のみの HTTP サーバーで headless
   再現が可能だが、`~/.claude.json` は machine-local state として `.chezmoiignore` 対象のため、
   `chezmoi apply` では復元されない。

また Codex cloud は Claude Code on the web と **env / secret の注入タイミングが逆**である
（[Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment.md)）。

| 項目 | Claude Code on the web | Codex cloud |
| :-- | :-- | :-- |
| env var の注入先 | agent phase のみ | setup script + agent phase |
| secret 専用枠 | なし | あり（setup のみ・agent phase 開始前に削除） |
| agent phase の network | 管理 proxy 経由 | 既定 off（allowlist で許可） |
| キャッシュ無効化 | Setup script / allowed hosts の変更 | 12h 経過、setup / maintenance / env / secret の変更 |

そのため ADR-0045 の「Setup script では restore しない」という判断を、Codex 側へそのまま
転写できるかどうかが自明でなかった。

## Decision

再現対象を「Claude Code on the web」から「クラウドの ephemeral セッション全般」へ広げ、
再現結果を検証可能にする。

- **`bootstrap-web` をプラットフォーム非依存にする。** `REPO_DIR` を
  `BOOTSTRAP_REPO_DIR` > `CLAUDE_PROJECT_DIR` > スクリプト位置 の順で解決する。
  Codex cloud には `CLAUDE_PROJECT_DIR` が無いため、Setup script は `BOOTSTRAP_REPO_DIR` で
  source を `/opt/dotfiles` に固定する。スクリプト名は既存参照（ADR-0045・AGENTS.md・
  `.claude/hooks/session-start.sh`）を壊さないため変更しない。
- **`jq` と `rg` を導入対象に加える。** `jq` は field 方式 secret の必須依存であり、導入できない
  場合は「field 方式の secret-backed file は復元できない」と warn を出す（静かな部分失敗を作らない）。
  `rg` は AGENTS.md の検索運用ルールが前提にする CLI。いずれも best-effort。
- **headless 再現できる MCP を user scope へ best-effort 登録する。** 対象は
  `mcp_servers` 配列（現在 `mfc_ca` のみ）。`~/.claude.json` を直接編集せず `claude mcp add
  --scope user` を使い、登録済みなら何もしない（冪等）。ローカルアプリ依存（`pencil`）と
  対話 OAuth 必須（`slack-twin` / claude.ai コネクタ）は headless 経路が無いため対象外とし、
  この区別を配列のコメントに残す。
- **Codex cloud では `OP_SERVICE_ACCOUNT_TOKEN` を secret 枠ではなく environment variables 枠に
  置く。** secret 枠は setup script でしか読めず agent phase 開始前に削除されるため、
  セッション内 on-demand restore ができない。env var 枠なら agent phase で restore が通り、
  ADR-0045 の「Setup script では restore せずスナップショットに焼き込まない」という判断を
  Codex 側でも維持できる。Setup script は Claude と同じく `BOOTSTRAP_WEB_SKIP_OP=true` で呼ぶ。
- **`scripts/verify-cloud-parity` を追加する。** 実環境を検査し、期待リストと突き合わせて
  `OK` / `MISSING` / `N/A` を出す。`MISSING` が 1 件でもあれば exit 1。期待リスト
  （`claude_skills` / `codex_skills` / `mcp_servers`）は `bootstrap-web` から抽出して使い、
  検証側で再定義しない（二重管理を増やさない）。third-party skill と CLI 一覧だけは
  `bootstrap-web` が関数内にハードコードしているため検証側が持ち、同期対象としてコメントに明示する。
  secret は実値を出さず有無だけを見る。
- Codex cloud の agent phase は network が既定 off のため、restore と runner 実行に必要な
  ドメイン（1Password 配布元・API、GitHub、npm、Go proxy）を allowlist に登録する運用とし、
  手順書に列挙する。

## Consequences

- Codex cloud でも Claude Code on the web と同じ `bootstrap-web` 一本で再現できる。実ロジックの
  二重管理は発生しない。差分は environment UI 側の設定（env / network / setup script）に閉じる。
- 再現の欠落が `verify-cloud-parity` の 1 コマンドで観測できるようになる。セッションごとの
  手作業確認と、`command -v` の結果を目視で突き合わせる運用が不要になる。
- 期待リストの正本が `bootstrap-web` に集約される一方、third-party skill と CLI 一覧は
  検証側にも複製が残る。skill / CLI を増減したときは `docs/skills-install-manifest.md`・
  `bootstrap-web`・`verify-cloud-parity` の 3 箇所を同期する必要がある（ADR-0045 で受容した
  二重管理が 3 重になる）。将来 `bootstrap-web` の CLI 導入を配列駆動へ寄せれば解消できる。
- MCP 登録は `claude` CLI に依存するため Codex cloud では skip される。Codex 側で MCP が要る
  場合は `~/.codex/config.toml` の `mcp_servers` を chezmoi 管理下に置く必要があり、本 ADR の
  範囲外とする。
- Codex cloud で secret 枠を使わない判断により、agent phase の network allowlist 設定が
  必須になる。allowlist を絞りすぎると restore と runner 導入が静かに失敗するため、
  手順書のドメイン一覧を運用契約として扱う。
- ローカル（macOS）で `verify-cloud-parity` を実行すると、クラウド専用項目は `N/A` に分類される。
  ローカル実行は「期待リスト自体が壊れていないか」の回帰確認として使える。

## 検証

2026-09-01 にローカル（macOS）で実測。

- `bash -n` / `shellcheck -S warning`: `bootstrap-web`・`verify-cloud-parity` とも警告なし
- `verify-cloud-parity`: OK=91 / MISSING=1 / N/A=3（total 95）、exit 1
- `--json`: 妥当な JSON として parse 可能
- 検出された唯一の `MISSING` は `claude-code-metrics-plugin@oasys-dev-marketplace`。
  marketplace `oasysgames/claude-code-dev-marketplace` が解決できずローカルでも未インストール
  （`installed_plugins.json` に無い）。クラウド固有の欠落ではなく既存の設定不整合であり、
  対処は本 ADR の範囲外（`dot_claude/settings.json` は Codex の管理対象）。
- クラウド実測（Claude Code on the web / Codex cloud での `verify-cloud-parity` 実行）は未実施。
