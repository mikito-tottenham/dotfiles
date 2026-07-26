#!/usr/bin/env python3
"""Aggregate Claude Code + Codex session logs for token-efficiency review.

ADR 0051 の効果検証用。
使い方: `python3 scripts/ai-usage-aggregate.py <出力先.json>`

進捗ログを標準出力へ出す。出力は JSON (集計のみ、secret なし)。
"""
import json, glob, os, sys, time
from collections import defaultdict

HOME = os.path.expanduser("~")
OUT = sys.argv[1]

def log(msg):
    print(f"[analyze] {msg}", flush=True)

# ---------- Claude Code ----------
claude_files = sorted(glob.glob(f"{HOME}/.claude/projects/*/*.jsonl"))
log(f"claude sessions: {len(claude_files)} files")

sessions = []
tool_counts = defaultdict(int)
tool_result_bytes = defaultdict(int)
model_usage = defaultdict(lambda: defaultdict(int))

for i, path in enumerate(claude_files):
    proj = os.path.basename(os.path.dirname(path))
    sid = os.path.basename(path)[:8]
    s = {
        "project": proj, "session": sid, "file_mb": round(os.path.getsize(path)/1e6, 2),
        "human_msgs": 0, "assistant_msgs": 0, "sidechain_msgs": 0,
        "output_tokens": 0, "cache_creation": 0, "cache_read": 0, "input_tokens": 0,
        "max_cache_read": 0, "models": defaultdict(int),
        "tools": defaultdict(int), "tool_errors": 0,
        "human_prompts": [], "first_ts": None, "last_ts": None,
        "entrypoint": None, "compact_events": 0,
    }
    # pending tool_use id -> name for result size attribution
    pending = {}
    with open(path) as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            ts = d.get("timestamp")
            if ts:
                if s["first_ts"] is None: s["first_ts"] = ts
                s["last_ts"] = ts
            t = d.get("type")
            if t == "user":
                if d.get("isSidechain"): s["sidechain_msgs"] += 1
                s["entrypoint"] = d.get("entrypoint") or s["entrypoint"]
                msg = d.get("message", {})
                content = msg.get("content")
                origin = (d.get("origin") or {}).get("kind")
                if isinstance(content, str):
                    if origin == "human" and not d.get("isSidechain"):
                        s["human_msgs"] += 1
                        s["human_prompts"].append(content[:200])
                elif isinstance(content, list):
                    is_tool_result = False
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "tool_result":
                            is_tool_result = True
                            name = pending.pop(c.get("tool_use_id"), "?")
                            blob = json.dumps(c.get("content"), ensure_ascii=False) if c.get("content") else ""
                            tool_result_bytes[name] += len(blob)
                            if c.get("is_error"): s["tool_errors"] += 1
                    if not is_tool_result and origin == "human" and not d.get("isSidechain"):
                        texts = [c.get("text","") for c in content if isinstance(c, dict) and c.get("type")=="text"]
                        if texts:
                            s["human_msgs"] += 1
                            s["human_prompts"].append(" ".join(texts)[:200])
            elif t == "assistant":
                if d.get("isSidechain"): s["sidechain_msgs"] += 1
                s["assistant_msgs"] += 1
                msg = d.get("message", {})
                model = msg.get("model", "?")
                s["models"][model] += 1
                u = msg.get("usage") or {}
                ot = u.get("output_tokens", 0); cc = u.get("cache_creation_input_tokens", 0)
                cr = u.get("cache_read_input_tokens", 0); it = u.get("input_tokens", 0)
                s["output_tokens"] += ot; s["cache_creation"] += cc
                s["cache_read"] += cr; s["input_tokens"] += it
                s["max_cache_read"] = max(s["max_cache_read"], cr + cc)
                mu = model_usage[model]
                mu["output"] += ot; mu["cache_creation"] += cc; mu["cache_read"] += cr; mu["input"] += it; mu["calls"] += 1
                for c in (msg.get("content") or []):
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        name = c.get("name","?")
                        s["tools"][name] += 1
                        tool_counts[name] += 1
                        pending[c.get("id")] = name
            elif t == "system":
                sub = d.get("subtype","")
                if "compact" in str(sub).lower(): s["compact_events"] += 1
            elif t == "summary":
                s["compact_events"] += 1
    s["models"] = dict(s["models"]); s["tools"] = dict(sorted(s["tools"].items(), key=lambda kv:-kv[1])[:15])
    s["human_prompts"] = s["human_prompts"][:30]
    sessions.append(s)
    log(f"  [{i+1}/{len(claude_files)}] {proj}/{sid} out={s['output_tokens']} cc={s['cache_creation']}")

# ---------- Codex ----------
codex_files = sorted(glob.glob(f"{HOME}/.codex/sessions/*/*/*/*.jsonl"))
log(f"codex sessions: {len(codex_files)} files")
codex_sessions = []
for i, path in enumerate(codex_files):
    s = {"file": os.path.basename(path)[:40], "date": path.split("/sessions/")[1][:10],
         "cwd": None, "source": None, "thread_source": None, "model": None,
         "total_tokens": 0, "input": 0, "cached_input": 0, "output": 0, "reasoning": 0,
         "user_msgs": 0, "func_calls": 0}
    last_total = None
    with open(path) as fh:
        for line in fh:
            try: d = json.loads(line)
            except Exception: continue
            t = d.get("type"); p = d.get("payload") or {}
            if t == "session_meta":
                s["cwd"] = p.get("cwd"); s["source"] = p.get("source")
                s["thread_source"] = p.get("thread_source")
            elif t == "turn_context":
                s["model"] = p.get("model") or s["model"]
            elif t == "event_msg":
                pt = p.get("type")
                if pt == "token_count":
                    info = p.get("info") or {}
                    tot = info.get("total_token_usage") or {}
                    if tot: last_total = tot
                elif pt == "user_message":
                    s["user_msgs"] += 1
            elif t == "response_item" and p.get("type") == "function_call":
                s["func_calls"] += 1
    if last_total:
        s["total_tokens"] = last_total.get("total_tokens", 0)
        s["input"] = last_total.get("input_tokens", 0)
        s["cached_input"] = last_total.get("cached_input_tokens", 0)
        s["output"] = last_total.get("output_tokens", 0)
        s["reasoning"] = last_total.get("reasoning_output_tokens", 0)
    codex_sessions.append(s)
log("codex done")

result = {
    "claude": {
        "sessions": sessions,
        "model_usage": {k: dict(v) for k, v in model_usage.items()},
        "tool_counts": dict(sorted(tool_counts.items(), key=lambda kv:-kv[1])),
        "tool_result_bytes_top": dict(sorted(tool_result_bytes.items(), key=lambda kv:-kv[1])[:20]),
    },
    "codex": {"sessions": codex_sessions},
}
with open(OUT, "w") as fh:
    json.dump(result, fh, ensure_ascii=False, indent=1, default=str)
log(f"wrote {OUT}")
