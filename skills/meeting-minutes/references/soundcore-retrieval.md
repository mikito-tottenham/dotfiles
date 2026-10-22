---
title: Soundcore Work / Soundcore AI からの文字起こし取得
updated_at: 2026-10-23
source: 2026-10-23 の Skill 統合で、旧 Soundcore 取得 skill の Workflow / Extraction Notes を移設
---

# Soundcore からの取得

Soundcore AI の Web UI（`https://ai.soundcore.com/home`）には公開 API が無い。認証済みブラウザセッションで UI を操作し、見えている内容だけを一次情報にする。見えないフィールドを作らない。

## ブラウザの選び方

- 既存のログインセッション、Cookie、パスワードマネージャ、MFA の状態が要るなら Chrome（Claude in Chrome）を使う
- ユーザーが Codex App Browser を指定した、そこで既にログイン済み、またはアプリ内ブラウザで進めたい場合はそちらを使う
- どちらも未認証なら `https://ai.soundcore.com/home` を開き、ユーザーがログインを終えるまで待ってから続ける
- Soundcore の認証情報をユーザーに求めない。認証はユーザー本人がブラウザで行う

## 手順

1. 選んだブラウザで `https://ai.soundcore.com/home` を開く
2. 認証済みで録音一覧（または同等のホーム画面）が出ていることを確かめる
3. ユーザーの条件（タイトル、日付、時刻、長さ、参加者、案件名、最新の録音）から対象の録音を特定する。複数が該当する場合は候補を列挙し、機密内容を抽出する前にユーザーに選んでもらう
4. 対象の録音を開き、文字起こしと要約のペインの読み込み完了を待つ
5. 見えているメタデータ、要約、アクション、トピック、話者、文字起こし本文を取得する
6. UI がページング・遅延読み込み・折りたたみ・仮想化している場合は、文字起こし領域を最後までスクロールして全セグメントを集める
7. 回答には出典として録音の識別子（表示タイトル + 日時、URL または `note_id`）を含める。要約と文字起こしの両方があるときは、文字起こしで要約を検証・補強する

ブラウザツールで仮想化された文字起こしを安定して読めないときは、サイトの表示・コピー・ダウンロード機能を使う。ダウンロードを起こす前にユーザーに確認する。

## 観測メモ（Soundcore Online Hub × Claude in Chrome、2026-09-18）

UI やブラウザツールが変わったら再確認する。

- 録音一覧の各行は `YYYY-MM-DD HH:MM:SS | <duration>` の形。日時で対象を特定し、会議名ラベルは Soundcore の表示どおりに使う
- 文字起こしの無い録音には「生成」ボタンが出る。生成はユーザーの文字起こし枠（分）を消費するため、明示の指示なしに押さない
- 録音を開くと AI 要約だけが出る。右上アイコン列の右端（tooltip「文字起こしを表示／非表示」）を押すと、右ペインに話者ラベル付きの文字起こしが開く。ページを再読み込みすると閉じる
- 文字起こしペインは仮想化されていない。34 分の録音で 186 セグメントが全部 DOM にあった。1 セグメントのブロックは、`/^speaker\s?\d+$/` に一致する葉要素から親へ上がり、`innerText` が 3 行以上（話者、`HH:MM:SS`、本文）になった要素
- `javascript_tool` の戻り値は約 1,000 文字で `[TRUNCATED]` される。URL やクエリ文字列を含む値（`outerHTML` など）は `[BLOCKED: Cookie/query string data]` になる。async IIFE を直接返すと `{}` になるので、top-level `await` を使うか、結果を `window` 変数に入れて別の呼び出しで読む
- 全文を 1 回で読むには、整形したセグメントを一時的な `<article>`（セグメントごとに `<p>`）として `document.body` の先頭に挿入し、`get_page_text` で読み（約 16,000 文字が切り詰めなしで返った）、読み終えたら要素を外す
- `navigator.clipboard.writeText` や `document.execCommand('copy')` でローカル側へ渡さない。ユーザー操作なしでは書き込みが失敗し、クリップボードは変わらない
- file artifact（話者・時刻・本文の TSV など）で逐語の保証が要るときは、保存したファイルからセグメントごとに UTF-16 code unit 数と code unit の総和 mod 9973 を計算し、その checksum 一覧を実行する JS に埋め込んで DOM と比較し、不一致の index だけを返す（結果が短くなり切り詰められない）。観測した回では 186/186 が一致した

## 一括取得（2026-10-08 観測、99 件を約 70 秒で取得）

- 多数の録音は、録音を 1 件ずつ開かず、ページ内から Web アプリ自身の API を呼ぶ。アプリは `https://anka-api-*.soundcore.com` へ `POST` XHR を送る: `/app/audio/note/list`（body `{page, page_size, sort_by, order, is_recycled}`。`page_size: 200` で 99 件全部が返った）、`/app/audio/note/query_summary` と `/app/audio/note/query_trans`（body `{note_id}`）。文字起こしセグメントは `speaker_label`、ミリ秒の `start_time` / `end_time`、`content` を持つ
- auth header は、`XMLHttpRequest.prototype.setRequestHeader` をラップしてページ変数に保持したまま録音を 1 件クリックして再利用する。その値を `javascript_tool` から返したりファイルに書いたりしない。終わったらタブを閉じる
- 一覧の `app_note_id` は録音開始の epoch 秒（UI の `YYYY-MM-DD HH:MM:SS` と一致する）、`created_at` はアップロード時刻、`audio_duration` はミリ秒。録音は `https://ai.soundcore.com/file/<note_id>` で開く。後の実行で重複を検出できるよう、この URL か `note_id` を出典に書く
- 結果をローカル側へ移すには、ページ内で 1 つの JSON Blob を作ってダウンロードする。ファイル名・出典・サイズを示してユーザーに確認し、ダウンロード後すぐに作業 repo の `.context/` へ移す
- レコーダーの時計が狂っていることがあり、2025-01-01 のような日付の録音がある。実際の日付は文字起こしと既存の議事録で確かめる
