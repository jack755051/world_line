#!/usr/bin/env python3
"""加總一個 Claude Code session transcript 的 token 用量（含其 subagents），依 message id 去重。
用法：python3 usage_tally.py <session_id> [since ISO 時間，例 2026-11-07T08:10]
只讀 ~/.claude/projects/<專案>/<session_id>.jsonl 與同名資料夾下 subagents/*.jsonl；不印內容。USD 不估（牌價未入檔 → 標「缺」）。"""
import glob, json, os, sys
sid = sys.argv[1]; since = sys.argv[2] if len(sys.argv) > 2 else ""
d = os.path.expanduser("~/.claude/projects/-Users-jack755051-01-Projects-world-line")
files = [os.path.join(d, sid + ".jsonl")] + glob.glob(os.path.join(d, sid, "**", "*.jsonl"), recursive=True)
seen, tot, t0, t1 = set(), dict(input=0, output=0, cache_creation=0, cache_read=0), None, None
for fn in files:
    for line in open(fn, encoding="utf-8"):
        try: r = json.loads(line)
        except ValueError: continue
        m = r.get("message") or {}; u = m.get("usage"); ts = r.get("timestamp", "")
        if not u or (since and ts < since): continue
        k = (m.get("id"), r.get("requestId"))
        if k in seen: continue
        seen.add(k); t0 = min(t0 or ts, ts); t1 = max(t1 or ts, ts)
        tot["input"] += u.get("input_tokens", 0); tot["output"] += u.get("output_tokens", 0)
        tot["cache_creation"] += u.get("cache_creation_input_tokens", 0); tot["cache_read"] += u.get("cache_read_input_tokens", 0)
print(f"| {sid} | {t0} | {t1} | {tot['input']} | {tot['output']} | {tot['cache_creation']} | {tot['cache_read']} | 缺 |")
