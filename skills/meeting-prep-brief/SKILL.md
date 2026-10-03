---
name: meeting-prep-brief
description: Prepare a pre-meeting brief for a recurring or one-off meeting by collecting the calendar event, past minutes, Slack, Gmail, and Chatwork through a fixed checklist with an account-boundary preflight, then drafting discussion points, carried-over action items, and questions per counterpart with sources and an explicit list of sources that could not be read. Use when asked to 定例の準備, 今日の定例の確認事項, MTG で準備するべきもの, 会議の論点整理, 質問リストを作って, 前回の宿題を確認, 話さないといけないトピック, or アジェンダを作って.
---

# Meeting Prep Brief

会議・定例の前に、決まった順番で情報源を集め、論点・前回の宿題・確認事項を出典付きでまとめる。「Slack もメールも見ていない」という参照漏れを防ぐため、集めた情報源と読めなかった情報源を必ず出力に残す。

## repo ローカル Skill との関係

- 作業 repo に会議専用の Skill（例: 定例会議専用の repo ローカル Skill）があれば、そちらを優先する。この Skill はその一般形で、会議ごとの Doc ID・チャンネル・出席者・書き込み先は持たない。
- 会議固有の情報（議事録の置き場、アジェンダの正本、見るチャンネル、相手先の呼び方）は作業 repo の README / AGENTS.md / 議事録索引から読む。見つからなければユーザーに聞く。
- 議事録の作成（会議後）は対象外。文字起こしの取得は `soundcore-minutes` を使う。

## Phase と artifact

各 Phase の artifact を `.context/<YYYY-MM-DD>-<meeting-slug>/` に保存してから次へ進む。Front Matter に `task` / `phase_or_step` / `created_at` を入れる。

### Phase 0 preflight → `00-preflight.md`

1. 会議の主体（どの会社・どの相手との会議か）を決める。曖昧ならユーザーに聞く。
2. 作業ルートの `AGENTS.md`「アカウント境界」節で、主体ごとの経路を引く。カレンダー・Gmail・Drive は `gws-account <profile>` か MCP コネクタ、Slack は `oprun slack-account <profile>` か MCP コネクタ、Chatwork は MCP。プロファイル名の対応は `gws-cli-runner` の `references/account-profiles.md` を正本とする。
3. `auth-preflight` Skill の script を `--only gws` などで実行し、使う経路の状態を確かめる。MCP コネクタは同 Skill の「MCP コネクタの確認」で接続先の組織を確かめる。コネクタの接続先が目的の組織と違う場合、そのコネクタの結果は使わない。
4. 情報源ごとに「使う経路／接続先の確認結果／使えない理由」を `00-preflight.md` に書く。

### Phase 1 収集 → `01-sources.md`

[references/sources-checklist.md](references/sources-checklist.md) の順に 5 つ全部を確認する。

1. カレンダー: 開催日時・出席者・添付資料。前回の開催日（収集期間の起点）もここで決める。
2. 過去議事録: 前回の決定事項と宿題。repo の議事録、未マージのブランチ、会議メモの Doc、録音サービスの順に探す。
3. Slack: 前回会議の前日以降。
4. Gmail: 同期間。件数が多いときは同梱 script で metadata を落としてから選ぶ。
5. Chatwork: 同期間。相手先とのやり取りがある場合。

使わない情報源も「対象外（理由）」と書く。量が多い情報源（Slack・Gmail・長い議事録）はサブエージェントに並列で委譲し、親は要約ファイルと裏取り対象の原文だけを読む。委譲のひな形は [references/subagent-brief.md](references/subagent-brief.md)。委譲先は agent-orchestrator の `rules/model_registry.yaml` の `secretary` role で解決する。

### Phase 2 起案 → `02-brief.md`

[references/output-template.md](references/output-template.md) の形でまとめる。判断ルール:

- ベースラインは前回会議の宿題と論点だけにする。それより前の項目は、ユーザーが求めない限り復活させない。
- 前回の各宿題は「進展あり（内容・日付・発言者）」「動きなし」「完了」のどれかを書く。
- 前回以降に出た依頼・期限・承認待ち・未回答を追加し、誰のボールかを書く。
- 金額・期限・人名・承認は出典のある値だけを書く。サブエージェントの分類は誤ることがあるので、金額・承認・期限に関わる項目は親が原文で裏取りする。
- 「未回答」と書く前に、本人が別スレッドや別チャネルで答えていないか検索する。
- メールアドレス・口座番号・パスワード・token は書かない。

### Phase 3 報告

`02-brief.md` の要約、ユーザー自身のボールの件、読めなかった情報源とその理由、裏取りできなかった項目を報告する。アジェンダの正本（共有 Doc など）へ書き込む場合は、書き込み先と内容をユーザーに確認してから行う。

## 禁止

- Slack・Gmail・Chatwork への送信、リアクション、既読化、下書き作成をしない（収集は読み取りのみ）。
- 接続先が違うコネクタの空振りを「該当なし」と扱わない。「未確認（接続先不一致）」と書く。
- 失敗した経路の代わりに別アカウントの結果を使わない。

## 完了チェック

- [ ] `00-preflight.md` に情報源ごとの経路と接続先の確認結果がある
- [ ] 5 つの情報源すべてに「確認済み／対象外（理由）／未確認（理由）」がある
- [ ] 前回の宿題すべてに判定がある
- [ ] 金額・承認・期限の項目を親が裏取りした
- [ ] 出力にメールアドレスや secret が入っていない
