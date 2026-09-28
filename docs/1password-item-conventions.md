---
title: 1Password の項目の型（CLI・AI から使う秘密）
created_at: 2026-09-28
updated_at: 2026-09-28
author: Claude Opus 5.5 (claude-opus-5-5)
related_adr: 0036
---

# 1Password の項目の型（CLI・AI から使う秘密）

CLI や AI（Claude Code / Codex）が `op run` / `op read` で使う秘密を 1Password に保存するときの型。
保存のたびに保管庫・種類・名前・フィールド名がばらばらになり、参照（`op://…`）が英数字の ID になったり、同じ秘密が二重に保存されたりするのを防ぐ。
AI が保存方法を案内するときも、この型をそのまま使う。

## 1. 置き場所（保管庫）

| 用途 | 保管庫 |
|---|---|
| CLI・AI が `op run` / `op read` / `opmaterialize` で使う秘密 | `Dotfiles Secrets`（`opmaterialize` の既定と同じ） |
| ブラウザでのログインだけに使うもの | 今ある保管庫のままでよい（この型の対象外） |

## 2. 項目の種類

| 秘密の種類 | 1Password の種類 | 値を入れる欄 |
|---|---|---|
| API トークン・API キー | API 認証情報（API Credential） | 組み込みの `credential` |
| SSH 鍵 | SSH 鍵（SSH Key） | 1Password のアプリの中で生成する。秘密鍵は 1Password の外に出さない |
| ファイル（VPN 設定など） | ドキュメント | `opmaterialize add <file>` で登録する（手で作らない） |

## 3. 名前の付け方

参照に使える文字は、英数字と `-` `_` `.` と空白だけ（[公式](https://www.1password.dev/cli/secret-reference-syntax)）。これ以外の文字（日本語、`/`、括弧など）を名前に入れると、参照を英数字の ID でしか書けなくなる。

- **タイトル**: `<サービス> <組織> <用途>` を英語で書く。単語の先頭は大文字
  - 組織は `Taskell` / `Yoake` / `TwinPlanet` / `Amicitia` / `Personal` のどれか
  - 例: `Cloudflare Amicitia Workers Deploy`、`Slack Taskell Bot`、`Gemini Personal API`
- **重複させない**: 同じ保管庫に同じタイトルを作らない。作る前に保管庫を検索する。重複していると参照がどちらを指すか決まらず、エラーになる
- **秘密の値**: 組み込みの `credential` に入れる。`token` や `key` などの欄を別に作らない
- **秘密でない識別子**: 追加のテキスト欄に、小文字のスネークケースの名前で入れる（`account_id`、`zone_id`、`username`、`team_id`）
- **セクションは使わない**: 参照が長くなり、名前違いの原因になる
- **日本語はメモ欄だけ**に書く

## 4. 埋めておく情報

| 欄 | 書くこと |
|---|---|
| ウェブサイト | サービスの管理画面の URL |
| 有効期限 | トークンに期限がある場合はその日付 |
| タグ | `org/<組織>` と `svc/<サービス>`（小文字。例: `org/amicitia`、`svc/cloudflare`） |
| メモ（日本語可） | 用途、権限の範囲、使う場所（リポジトリのパスと env ファイル）、作成日、作り直し方 |

## 5. 参照の取り方と書き方

1. 1Password のアプリで項目を開き、フィールドのメニューから「シークレット参照をコピー」を選ぶ
2. 取れた参照が `op://Dotfiles Secrets/<タイトル>/credential` の形になっていることを確かめる。英数字の ID が混じっていたら、名前に使えない文字か重複がある。名前を直してから取り直す
3. env ファイルには、引用符で囲んで書く（保管庫の名前に空白があるため）

```dotenv
CLOUDFLARE_API_TOKEN="op://Dotfiles Secrets/Cloudflare Amicitia Workers Deploy/credential"
CLOUDFLARE_ACCOUNT_ID="op://Dotfiles Secrets/Cloudflare Amicitia Workers Deploy/account_id"
```

参照は秘密の値ではないので、AI に伝えてよい。ただし保管庫や項目の名前が分かるので、参照を書いた env ファイルは git に入れない（ADR-0036）。
型どおりに名前を付けていれば、参照はタイトルとフィールド名から書けるので、コピーせずに組み立ててもよい。

## 6. 確かめ方（値を表示しない）

```bash
op run --env-file=<env ファイル> -- sh -c 'test -n "$CLOUDFLARE_API_TOKEN" && echo ok'
```

`ok` が出れば、参照が解決できている。`op read` の結果を画面やログに出して確かめない。

## 7. してはいけないこと

- 秘密の値をチャット・ファイル・コミットに貼る
- 同じ秘密を別の項目に二重に保存する（作り直したときは古い項目を消すか、タイトルに `Old` を付けて区別する）
- ツール独自の保存場所（`gh auth login`、`wrangler login` など）に保存する（共通ルール）

## 8. 既存の項目

型に合わない既存の項目（値の欄が `token`、ID でしか参照できないものなど）は、一括では直さない。参照している env ファイルが壊れるため。
その項目を使う作業のついでに、参照と一緒に直す。
