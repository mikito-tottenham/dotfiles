#!/usr/bin/env python3
"""free_slots.py — 複数アカウントのカレンダーを横断して共通の空き枠を出す（読み取りのみ）。

各 --source の profile で `gws-account <profile> calendar freebusy query` を実行し、
すべての busy を OR で重ねて、受付時間帯の中で全員が空いている枠を数える。
カレンダーごとに「実際に参照できたか」を表で出す。1 つでも参照できなかったカレンダーが
あれば、表の後に警告を出して exit 3 で終わる（枠そのものは出力する）。

使い方:
  free_slots.py --source <profile>[:<calendarId>] [--source ...] \
      [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--start-hour 10] [--end-hour 18] \
      [--slot-min 30] [--buffer-min 0] [--days mon,tue,wed,thu,fri] [--tz Asia/Tokyo]

  --source <profile>             その profile の calendarList に載っている全カレンダー（祝日を除く）
  --source <profile>:primary     その profile の主カレンダーだけ
  --source <profile>:<id>        その profile の権限で読める特定のカレンダー（freeBusyReader 共有を含む）

出力:
  stdout: Markdown（参照状況の表、日ごとの共通空き枠）
  stderr: 進捗ログ
  exit:   0 全カレンダー参照済み / 1 gws 実行失敗 / 2 引数不備 / 3 参照できないカレンダーあり

カレンダー ID は出力時にローカル部を伏せる（`***@domain`）。アドレスをソースや出力に残さない。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_JA = ["月", "火", "水", "木", "金", "土", "日"]
FREEBUSY_CHUNK = 50  # freeBusy の 1 リクエストあたりの上限
STARTED = time.monotonic()


def log(msg: str) -> None:
    print(f"[free-slots +{time.monotonic() - STARTED:5.1f}s] {msg}", file=sys.stderr, flush=True)


def mask(cal_id: str) -> str:
    if cal_id == "primary":
        return cal_id
    if "@" not in cal_id:
        return "***"
    return "***@" + cal_id.split("@", 1)[1]


def gws(profile: str, args: list[str], body: dict | None = None) -> dict:
    cmd = ["gws-account", profile, "calendar"] + args + ["--format", "json"]
    if body is not None:
        cmd += ["--json", json.dumps(body, ensure_ascii=False)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        log(f"gws failed (profile={profile}, exit={proc.returncode}): {detail[-1] if detail else ''}")
        log("auth errors: follow gws-cli-runner's recovery runbook for the same profile; do not switch accounts")
        sys.exit(1)
    return json.loads(proc.stdout or "{}")


def parse_sources(raw: list[str]) -> dict[str, list[str] | None]:
    """profile -> calendar id list（None は calendarList 全体）。"""
    out: dict[str, list[str] | None] = {}
    for item in raw:
        profile, _, cal = item.partition(":")
        if not profile:
            log(f"invalid --source: {item}")
            sys.exit(2)
        if not cal:
            out[profile] = None
        elif out.get(profile, []) is not None:
            out.setdefault(profile, []).append(cal)
    return out


def resolve_calendars(profile: str, ids: list[str] | None) -> list[tuple[str, str]]:
    """(calendar id, accessRole) の一覧。"""
    if ids is not None:
        return [(i, "explicit") for i in ids]
    items = gws(profile, ["calendarList", "list"]).get("items", [])
    cals = [(i["id"], i.get("accessRole", "?")) for i in items if "#holiday@" not in i["id"]]
    log(f"profile={profile}: {len(cals)} calendars from calendarList (holidays excluded)")
    return cals


def merge(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    merged: list[tuple[datetime, datetime]] = []
    for s, e in sorted(intervals):
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def free_windows(ws, we, busy, min_len):
    free, cur = [], ws
    for s, e in busy:
        if e <= ws or s >= we:
            continue
        if s > cur:
            free.append((cur, min(s, we)))
        cur = max(cur, e)
        if cur >= we:
            break
    if cur < we:
        free.append((cur, we))
    return [(s, e) for s, e in free if e - s >= min_len]


def count_slots(windows, slot_min: int) -> int:
    n = 0
    step = timedelta(minutes=slot_min)
    for s, e in windows:
        t = s.replace(second=0, microsecond=0)
        if t.minute % slot_min:
            t += timedelta(minutes=slot_min - t.minute % slot_min)
        while t + step <= e:
            n += 1
            t += step
    return n


def main() -> int:
    p = argparse.ArgumentParser(description="Common free slots across gws-account profiles (read-only)")
    p.add_argument("--source", action="append", required=True)
    p.add_argument("--from", dest="start")
    p.add_argument("--to", dest="end")
    p.add_argument("--start-hour", type=int, default=10)
    p.add_argument("--end-hour", type=int, default=18)
    p.add_argument("--slot-min", type=int, default=30)
    p.add_argument("--buffer-min", type=int, default=0, help="busy の前後に足す余白（分）")
    p.add_argument("--days", default="mon,tue,wed,thu,fri")
    p.add_argument("--tz", default="Asia/Tokyo")
    a = p.parse_args()

    tz = ZoneInfo(a.tz)
    today = datetime.now(tz).date()
    d_from = datetime.fromisoformat(a.start or str(today + timedelta(days=1))).replace(tzinfo=tz)
    d_to = datetime.fromisoformat(a.end or str(today + timedelta(days=15))).replace(tzinfo=tz)
    days = {DAY_KEYS.index(d.strip()) for d in a.days.split(",") if d.strip() in DAY_KEYS}
    if d_to <= d_from or not days or not (0 <= a.start_hour < a.end_hour <= 24):
        log("invalid range, days, or hours")
        return 2
    buffer = timedelta(minutes=a.buffer_min)
    log(f"start: {d_from:%Y-%m-%d} .. {d_to:%Y-%m-%d} {a.start_hour}:00-{a.end_hour}:00 {a.slot_min}min tz={a.tz}")

    status_rows = []
    busy_all: list[tuple[datetime, datetime]] = []
    unreadable = 0
    for profile, ids in parse_sources(a.source).items():
        cals = resolve_calendars(profile, ids)
        for i in range(0, len(cals), FREEBUSY_CHUNK):
            chunk = cals[i:i + FREEBUSY_CHUNK]
            log(f"profile={profile}: freebusy for {len(chunk)} calendars")
            res = gws(profile, ["freebusy", "query"], {
                "timeMin": d_from.isoformat(), "timeMax": d_to.isoformat(), "timeZone": a.tz,
                "items": [{"id": cid} for cid, _ in chunk],
            }).get("calendars", {})
            for cid, role in chunk:
                cal = res.get(cid)
                if cal is None or cal.get("errors"):
                    reason = ",".join(e.get("reason", "?") for e in (cal or {}).get("errors", [])) or "no_response"
                    status_rows.append((profile, mask(cid), role, f"参照できず（{reason}）", "-"))
                    unreadable += 1
                    continue
                blocks = cal.get("busy", [])
                status_rows.append((profile, mask(cid), role, "参照済み", str(len(blocks))))
                for b in blocks:
                    s = datetime.fromisoformat(b["start"].replace("Z", "+00:00")).astimezone(tz) - buffer
                    e = datetime.fromisoformat(b["end"].replace("Z", "+00:00")).astimezone(tz) + buffer
                    busy_all.append((s, e))
    busy = merge(busy_all)
    log(f"merged busy blocks: {len(busy)}")

    print(f"# 共通空き枠（{d_from:%Y-%m-%d} 〜 {d_to:%Y-%m-%d}）\n")
    print(f"条件: {','.join(DAY_KEYS[d] for d in sorted(days))} {a.start_hour}:00-{a.end_hour}:00 {a.tz} / "
          f"{a.slot_min} 分枠 / 前後余白 {a.buffer_min} 分\n")
    print("## 参照したカレンダー\n")
    print("| profile | カレンダー | 権限 | 状態 | busy 件数 |")
    print("|---|---|---|---|---|")
    for row in status_rows:
        print("| " + " | ".join(row) + " |")
    if unreadable:
        print(f"\n> 警告: {unreadable} 件のカレンダーを参照できていない。該当者の予定はこの枠に反映されていないため、確定した空き枠として提示しないこと。")

    print("\n## 日ごとの共通空き\n")
    print("| 日付 | 共通空き | 枠数 |")
    print("|---|---|---|")
    total, d = 0, d_from.date()
    min_len = timedelta(minutes=a.slot_min)
    while d < d_to.date():
        if d.weekday() in days:
            ws = datetime.combine(d, dtime(a.start_hour, 0), tz)
            we = datetime.combine(d, dtime(0, 0), tz) + timedelta(hours=a.end_hour)
            w = free_windows(ws, we, busy, min_len)
            n = count_slots(w, a.slot_min)
            total += n
            label = " / ".join(f"{s:%H:%M}-{e:%H:%M}" for s, e in w) or "—"
            print(f"| {d:%m/%d}({DAY_JA[d.weekday()]}) | {label} | {n} |")
        d += timedelta(days=1)
    print(f"\n合計 {total} 枠")
    log(f"done: {total} slots, unreadable calendars: {unreadable}")
    return 3 if unreadable else 0


if __name__ == "__main__":
    sys.exit(main())
