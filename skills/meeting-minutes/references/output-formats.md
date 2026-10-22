# Output Formats

Use Japanese by default. Keep the output factual and traceable to the transcript or the visible Soundcore content.

## Standard Minutes

```markdown
# 議事録

- ソース: <Soundcore recording title, date/time, or URL>
- 日時: <visible meeting date/time or 未確認>
- 参加者: <visible participants or 未確認>

## 要約

<3-6 bullets summarizing the meeting>

## 決定事項

- <decision>

## アクションアイテム

| 担当 | 期限 | 内容 |
| --- | --- | --- |
| 未確認 | 未確認 | <action item> |

## 論点・議論メモ

- <topic and key discussion>

## 未解決事項

- <open question or blocker>

## 抽出メモ

- <missing transcript ranges, missing speakers, partial loading, or other caveats>
```

## Transcript Plus Minutes

When the user asks for both transcript and minutes, put minutes first, then include the transcript under `# 書き起こし`.

Preserve speaker labels and timestamps exactly as Soundcore exposes them. If the transcript has no speakers, use plain paragraphs or bullets rather than inventing names.

## Quality Rules

- 欠けている項目の扱い（`未確認`）、記憶で補わないこと、要約と文字起こしの食い違い、アクションの統合は SKILL.md の「共通の規則」と手順 4 に従う。ここでは再掲しない
