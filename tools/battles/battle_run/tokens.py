"""統計本工作（staging 目錄對應的 Claude 專案）的 token 用量。

用法：python3 -I tools/battles/battle_run/cli.py tokens --since 2026-11-18T08:00:00+08:00
五小時額度約 68.75M tokens。超過 --stop-tokens（預設 5M）就該停、回報，不要再開新 agent。
"""
from __future__ import annotations

import collections
import datetime
import glob
import json
import os
from pathlib import Path

LIMIT = 68.75e6
DEFAULT_STOP = 5_000_000


def parse_since(s):
    if s.endswith("Z"):
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return datetime.datetime.fromisoformat(s)


def collect(since: datetime.datetime, globs=None):
    """只讀 ~/.claude/projects 下與戰役 staging／本 skill 相關的 jsonl，不改檔。"""
    patterns = globs or [
        str(Path.home() / ".claude/projects/*wl-battle-staging*/**/*.jsonl"),
        str(Path.home() / ".claude/projects/*wl-battle-skill*/**/*.jsonl"),
        str(Path.home() / ".claude/projects/*battle-run*/**/*.jsonl"),
    ]
    seen = set()
    agg = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    ts = since.timestamp() if since.tzinfo is None else since.timestamp()
    for pat in patterns:
        for f in glob.glob(pat, recursive=True):
            if os.path.getmtime(f) < ts:
                continue
            proj = f.split("/projects/")[1].split("/")[0]
            for line in open(f, errors="ignore"):
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") != "assistant" or not d.get("timestamp"):
                    continue
                when = datetime.datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
                if when.tzinfo and since.tzinfo is None:
                    since_c = since.replace(tzinfo=datetime.timezone.utc)
                else:
                    since_c = since
                if when < since_c:
                    continue
                m = d.get("message") or {}
                u = m.get("usage")
                if not u:
                    continue
                k = (m.get("id"), d.get("requestId"))
                if k in seen:
                    continue
                seen.add(k)
                model = (m.get("model") or "?").replace("claude-", "")
                a = agg[(proj, os.path.basename(f)[:8], model)]
                a[0] += u.get("input_tokens", 0)
                a[1] += u.get("cache_creation_input_tokens", 0)
                a[2] += u.get("cache_read_input_tokens", 0)
                a[3] += u.get("output_tokens", 0)
                a[4] += 1
    return agg


def report(since, stop_tokens=DEFAULT_STOP, globs=None):
    agg = collect(since, globs)
    T = 0
    byp = collections.Counter()
    lines = []
    for (p, s, mo), a in sorted(agg.items()):
        t = sum(a[:4])
        T += t
        byp[p] += t
        lines.append(f"{p:24} {s} {mo:18} calls={a[4]:4} in={a[0]:>8,} cc={a[1]:>9,} cr={a[2]:>11,} out={a[3]:>7,} total={t:>11,}")
    for p, t in byp.items():
        lines.append(f"BYPROJ {p}: {t:,} ({t/LIMIT*100:.1f}%)")
    lines.append(f"TOTAL {T:,} tokens = {T/LIMIT*100:.1f}% of 5h limit; stop at {stop_tokens:,} ({'STOP' if T >= stop_tokens else 'ok'})")
    return {"total": T, "stopTokens": stop_tokens, "stop": T >= stop_tokens, "lines": lines, "limit": LIMIT}
