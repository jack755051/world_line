#!/usr/bin/env python3
"""從 ~/.claude/projects/<repo>/<session>.jsonl 算每個 agent 的實際 token（以 message.id 去重）。

    python3 -I tools/b3v3/session_cost.py --journal ~/wl-b3v3-runs/pilot/journal.jsonl
    python3 -I tools/b3v3/session_cost.py --session <uuid> [--session <uuid>]
"""
import argparse
import json
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"


def find_session(session_id):
    for path in PROJECTS.glob(f"*/{session_id}.jsonl"):
        return path
    return None


def session_usage(path):
    seen = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "assistant":
            continue
        message = obj.get("message") or {}
        usage = message.get("usage") or {}
        key = message.get("id") or obj.get("uuid")
        seen[key] = (message.get("model"), usage)
    rows = {"calls": 0, "input": 0, "cacheCreate": 0, "cacheRead": 0, "output": 0, "maxContext": 0, "models": {}}
    for model, usage in seen.values():
        if model == "<synthetic>":
            continue
        rows["calls"] += 1
        rows["input"] += usage.get("input_tokens") or 0
        rows["cacheCreate"] += usage.get("cache_creation_input_tokens") or 0
        rows["cacheRead"] += usage.get("cache_read_input_tokens") or 0
        rows["output"] += usage.get("output_tokens") or 0
        context = sum(usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        rows["maxContext"] = max(rows["maxContext"], context)
        rows["models"][model] = rows["models"].get(model, 0) + 1
    rows["total"] = rows["input"] + rows["cacheCreate"] + rows["cacheRead"] + rows["output"]
    rows["cacheReadShare"] = round(rows["cacheRead"] / rows["total"], 3) if rows["total"] else 0
    return rows


def from_journal(path):
    out = []
    for line in Path(path).expanduser().read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec.get("event") == "agent_end" and rec.get("session"):
            out.append((rec["id"], rec["session"], rec.get("numTurns"), rec.get("outcome")))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal")
    parser.add_argument("--session", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    items = from_journal(args.journal) if args.journal else []
    items += [(sid, sid, None, None) for sid in args.session]
    report = []
    for agent_id, sid, turns, outcome in items:
        path = find_session(sid)
        row = session_usage(path) if path else {"missing": True}
        row.update({"id": agent_id, "session": sid, "numTurns": turns, "outcome": outcome})
        report.append(row)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 0
    for row in report:
        if row.get("missing"):
            print(f"{row['id']} 找不到 transcript {row['session']}")
            continue
        print(f"{row['id']}  calls={row['calls']} turns={row['numTurns']} in={row['input']:,} cc={row['cacheCreate']:,} "
              f"cr={row['cacheRead']:,} out={row['output']:,} total={row['total']:,} crShare={row['cacheReadShare']} "
              f"maxCtx={row['maxContext']:,} models={row['models']} outcome={row['outcome']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
