---
name: pdf-extract
description: Extract structured content (tables, body text, handwritten notes, margin annotations) from a PDF into a reproducible Markdown artifact with YAML frontmatter and a cache key. Codex CLI is the primary backend, resolved through the agent-orchestrator model registry and run via codex-cli-runner; an explicitly declared Claude path covers environments without Codex. Repo-specific prompt templates stay in the repository. Use when asked to PDFを構造化して抽出, PDFから表を抜き出す, 見積書・請求書・図面・FAXを読み取る, 手書きメモも含めて書き起こす, OCRして artifact に残す, or pdf-extract.
---

# pdf-extract

PDF から書誌・主表・手書き注記などを抜き出し、後段で再利用できる Markdown artifact を 1 PDF につき 1 ファイル作る。入口（PDF パスとプロンプト）と出口（artifact のパス・frontmatter・本文構成）は backend に依存しない。

## 使わない場面

- 本文テキストだけが欲しい: `pdftotext` や pdfplumber を直接使う
- 一度内容を確認するだけで artifact が不要: その場で PDF を開いて読む
- PDF の結合・分割・フォーム入力など PDF 自体の加工: 汎用の PDF 用 skill を使う

## 入口

| 引数 | 必須 | 内容 |
|---|---|---|
| `--pdf <path>` | 必須 | 対象 PDF。repo ルート配下にあること |
| `--prompt-id <id>` | `--prompt-text` と択一 | プロンプトテンプレート名（拡張子なし）。探索順は下記 |
| `--prompt-text <text>` | `--prompt-id` と択一 | テンプレートを使わない一回限りの指示。cache key 上の ID は `inline` |
| `--out <path>` | 任意 | 出力先。省略時はミラーパス |
| `--tier <S\|A\|B\|C>` | 任意 | model registry の tier。既定 `B` |
| `--model` / `--effort` | 任意 | registry を使わず明示指定するときだけ渡す |
| `--repo-root <dir>` | 任意 | 省略時は cwd の git top-level。git 管理外なら cwd |
| `--prompts-dir <dir>` | 任意 | repo 側テンプレートの置き場を明示する |
| `--service-tier <fast\|priority>` | 任意 | 渡したときだけ Codex に `service_tier` を設定する |
| `--force` | 任意 | cache hit を無視して再生成 |

プロンプトテンプレートの探索順（最初に見つかったものを使い、使った path をログに出す）:

1. `--prompts-dir`
2. `<repo>/.claude/skills/pdf-extract/prompts/`（移行前の repo ローカル配置）
3. `<repo>/.agents/skills/pdf-extract/prompts/`
4. この skill の `prompts/`（汎用テンプレート `generic_document` のみ同梱）

業種・案件に固有のテンプレート（例: 製造業の見積書、機械図面）は repo 側に置き、この skill には持ち込まない。

## 出口

- 既定パス: `<repo>/.context/pdf-extract/<PDF の repo 相対パス>` の拡張子を `.ocr.md` に置換したもの
- 形式: [references/output-format.md](references/output-format.md)（frontmatter のキーと型、本文セクション、cache key）
- stdout: 結果サマリ JSON（`status`、`extraction_backend`、`artifact_path`、`cache_key`、`cache_hit`）
- Codex の実行記録: `<repo>/.context/pdf-extract/runs/<PDF 名>-<sha8>/`（codex-cli-runner の `summary.json`・events・stderr）

## モデルの解決

モデル名はこの skill に書かない。`scripts/extract_pdf.py` は兄弟 skill の `agent-orchestrator/rules/model_registry.yaml` を読み、`tiers.<tier>.codex` の model と effort を使う。

- 既定 tier は `B`（手順が自明で多少の判断を伴う抽出）。手書きの判読が難しい、表の構造推定が重いなど判断が多い PDF は親が `--tier A` を選ぶ
- registry が見つからない、または tier を解決できないときは exit 2 で止まる。別のモデルへ黙って切り替えない
- `--model` を明示した場合はその値をそのまま使い、frontmatter に記録する

## 実行手順

1. 親が対象 PDF とプロンプトを決める。repo にテンプレートが無ければ `--prompt-id generic_document` か `--prompt-text` を使う
2. スクリプトを実行する

   ```bash
   python3 <skill-dir>/scripts/extract_pdf.py \
     --pdf ".context/<task>/data/<file>.pdf" \
     --prompt-id generic_document
   ```

3. 終了コードで分岐する

   | exit | 意味 | 次の行動 |
   |---|---|---|
   | 0 | 成功（cache hit を含む） | artifact を読み、`## 認識上の注意` を確認する |
   | 1 | Codex 実行の失敗 | run dir の `summary.json` と `failure.md` を読み、原因を報告する。Claude 経路へ自動で切り替えない |
   | 2 | 入力・registry・runner の不備 | メッセージに従って入力を直す |
   | 127 | `codex` が PATH に無い | 下記の Claude 経路を使うか、ユーザーに確認する |

4. artifact の数値・固有名詞のうち後段で使うものは、原本 PDF と突き合わせてから使う

## Claude 経路（Codex 不在時の代替経路）

Codex CLI が無い環境のための代替経路。発動条件・手順・記録方法は [references/claude-path.md](references/claude-path.md) に従う。

- 発動条件は exit 127、またはユーザーが Claude 経路を明示したときに限る。exit 1（Codex は在るが失敗）では使わない
- frontmatter の `extraction_backend: claude` で経路を記録し、Codex 経路と同じ出口契約を守る
- 契約書など誤読の影響が大きい文書では、Claude 経路の結果を確定値として扱わずユーザーの目視確認を求める

## Codex 親の場合

親が Codex のときは `scripts/extract_pdf.py` を使わない。この script は codex-cli-runner で Codex CLI を subprocess として起動する経路で、`agent-orchestrator/rules/model_registry.yaml` の `providers.codex.self_elision`（親が Codex なら cli_runner を使わず agent_tool へ委譲する）に反する。Codex の配備一覧（`docs/skills-install-manifest.md` の Codex 節）にも codex-cli-runner は入っていない。

- 経路: Codex の custom agent（agent_tool）へ抽出を委譲する。spawn 時に `tiers.<tier>.codex` の model と effort を明示する（既定 tier は `B`。registry の `harness_notes.codex_custom_agents` のとおり、省略すると tier が適用されない）
- 手順: [references/claude-path.md](references/claude-path.md) の手順 1〜8 と同じ入口・出口契約で artifact を作る。違いは frontmatter を `extraction_backend: codex`、`backend_model` / `backend_effort` / `backend_tier` を spawn で指定した値にすることと、cache key の backend 部分を `codex` にすることだけ
- 記録: run dir（`.context/pdf-extract/runs/`）は作られない。最終報告に「Codex 親の agent_tool で抽出した」と書く
- 誤って script を実行した場合は exit 2（codex-cli-runner が無い）で止まる。この停止を Claude 経路への切り替え条件として扱わず、この節の経路へ移る

## 依存

- `codex-cli-runner`（兄弟 skill）: Codex の起動・停止検知・失敗 artifact。`<skill-dir>/../codex-cli-runner/scripts/run_codex_cli.py`
- `agent-orchestrator`（兄弟 skill）: `rules/model_registry.yaml`

どちらかが同じ skills ディレクトリに無いときは exit 2 で止まる。親が Codex の場合は上記「Codex 親の場合」に従い、script 自体を使わない。

## 検証

- skill 変更後: `scripts/skill-quick-validate skills/pdf-extract` と `python3 scripts/extract_pdf.py --help`
- 抽出品質の回帰は repo 側で行う。repo に fixture（期待する主表・書誌値）があれば、その repo の手順に従って再処理し構造一致を確認する
- 同条件で再実行して cache hit になることを確認する
