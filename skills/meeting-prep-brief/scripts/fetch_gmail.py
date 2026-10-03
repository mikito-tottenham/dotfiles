#!/usr/bin/env python3
"""Gmail のメッセージ一覧とヘッダ（metadata）を gws-account 経由で取得し JSON に落とす。読み取り専用。

usage: fetch_gmail.py --profile <gws-profile> --after YYYY/MM/DD --out .context/<dir> [--query '-category:promotions']
出力: <out>/gmail_meta.json（id, threadId, date, from, to, subject, snippet, labels）
進捗は標準出力に出す（100 通あたり約 70 秒が目安）。

取り込み元: 業務 repo の定例会議 Skill（scripts/fetch_gmail.py）。
プロファイルの既定値は持たない。どのプロファイルを使うかは作業ルートの AGENTS.md のアカウント境界で決める。
"""
import argparse
import json
import subprocess
import time
from pathlib import Path


def gws(profile: str, *args: str):
    r = subprocess.run(['gws-account', profile, *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        print('ERR', args[:4], f'rc={r.returncode}', r.stderr.strip().splitlines()[-1:] or '', flush=True)
        return None
    return json.loads(r.stdout)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--profile', required=True, help='gws-account のプロファイル')
    ap.add_argument('--after', required=True, help='YYYY/MM/DD（この日を含まない。前回会議の前日を指定）')
    ap.add_argument('--out', required=True, help='出力ディレクトリ（.context/<task>）')
    ap.add_argument('--query', default='-category:promotions', help='追加の Gmail 検索条件')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    q = f'after:{a.after} {a.query}'.strip()
    print(f'start profile={a.profile} q={q}', flush=True)
    msgs, tok = [], None
    while True:
        p = {'userId': 'me', 'q': q, 'maxResults': 100}
        if tok:
            p['pageToken'] = tok
        res = gws(a.profile, 'gmail', 'users', 'messages', 'list', '--params', json.dumps(p))
        if not res:
            break
        msgs += res.get('messages', [])
        tok = res.get('nextPageToken')
        print(f'list: total={len(msgs)} next={bool(tok)} elapsed={time.time() - t0:.0f}s', flush=True)
        if not tok:
            break

    rows = []
    for i, m in enumerate(msgs):
        r = gws(a.profile, 'gmail', 'users', 'messages', 'get', '--params', json.dumps(
            {'userId': 'me', 'id': m['id'], 'format': 'metadata', 'metadataHeaders': ['Subject', 'From', 'To', 'Date']}))
        if not r:
            continue
        h = {x['name']: x['value'] for x in r['payload'].get('headers', [])}
        rows.append({'id': m['id'], 'threadId': m['threadId'], 'date': h.get('Date'), 'from': h.get('From'),
                     'to': h.get('To'), 'subject': h.get('Subject'), 'snippet': r.get('snippet'), 'labels': r.get('labelIds')})
        if i % 10 == 0:
            print(f'get {i + 1}/{len(msgs)} elapsed={time.time() - t0:.0f}s', flush=True)
    (out / 'gmail_meta.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'done {len(rows)}/{len(msgs)} {time.time() - t0:.0f}s -> {out / "gmail_meta.json"}', flush=True)


if __name__ == '__main__':
    main()
