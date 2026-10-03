#!/usr/bin/env python3
"""Gmail スレッド本文を gws-account 経由で取得し Markdown に落とす。読み取り専用。
引用部（> 行）は除き、1 通あたり 6000 文字で切る。

usage: fetch_threads.py --profile <gws-profile> --ids ids.txt --out .context/<dir>
ids.txt: threadId を空白か改行区切りで列挙
出力: <out>/threads/<threadId>.md

取り込み元: 業務 repo の定例会議 Skill（scripts/fetch_threads.py）。
"""
import argparse
import base64
import html
import json
import re
import subprocess
import time
from pathlib import Path


def gws(profile: str, *args: str):
    r = subprocess.run(['gws-account', profile, *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        print('ERR', args[:4], f'rc={r.returncode}', r.stderr.strip().splitlines()[-1:] or '', flush=True)
        return None
    return json.loads(r.stdout)


def walk(p, acc):
    mt = p.get('mimeType', '')
    b = p.get('body', {}).get('data')
    if b and mt in ('text/plain', 'text/html'):
        t = base64.urlsafe_b64decode(b + '==').decode('utf-8', 'replace')
        if mt == 'text/html':
            t = re.sub(r'<style.*?</style>', '', t, flags=re.S)
            t = re.sub(r'<[^>]+>', ' ', t)
            t = html.unescape(t)
            t = re.sub(r'[ \t]+', ' ', t)
            t = re.sub(r'\n\s*\n+', '\n', t)
        acc.append((mt, t))
    for c in p.get('parts', []):
        walk(c, acc)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--profile', required=True, help='gws-account のプロファイル')
    ap.add_argument('--ids', required=True, help='threadId 一覧ファイル')
    ap.add_argument('--out', required=True, help='出力ディレクトリ')
    a = ap.parse_args()
    ids = Path(a.ids).read_text(encoding='utf-8').split()
    out = Path(a.out) / 'threads'
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print(f'start profile={a.profile} threads={len(ids)} -> {out}', flush=True)
    ok = 0
    for i, tid in enumerate(ids):
        r = gws(a.profile, 'gmail', 'users', 'threads', 'get', '--params', json.dumps({'userId': 'me', 'id': tid, 'format': 'full'}))
        if not r:
            continue
        parts = []
        for m in r['messages']:
            h = {x['name']: x['value'] for x in m['payload'].get('headers', [])}
            acc = []
            walk(m['payload'], acc)
            body = next((t for mt, t in acc if mt == 'text/plain'), None) or (acc[0][1] if acc else '(no body)')
            body = re.sub(r'\n>.*', '', body)
            parts.append(f"### {h.get('Date')} | From: {h.get('From')} | To: {h.get('To')}\nSubject: {h.get('Subject')}\n{body.strip()[:6000]}\n")
        (out / f'{tid}.md').write_text('\n'.join(parts), encoding='utf-8')
        ok += 1
        print(f"{i + 1}/{len(ids)} {tid} msgs={len(r['messages'])} {time.time() - t0:.0f}s", flush=True)
    print(f'done {ok}/{len(ids)} {time.time() - t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
