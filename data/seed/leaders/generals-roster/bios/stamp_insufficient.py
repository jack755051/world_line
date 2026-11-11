#!/usr/bin/env python3
"""After one retry, stamp remaining failing people with 來源不足. Does not invent biography text."""
import json, sys, pathlib
src, report, out = sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv)>3 else sys.argv[1]
d = json.load(open(src, encoding="utf-8"))
rep = json.load(open(report, encoding="utf-8"))
fail = set(rep.get("failingKeys") or [])
n = 0
for p in d.get("people") or []:
    if p.get("key") not in fail:
        continue
    row = next((r for r in rep["people"] if r["key"]==p["key"]), {})
    note = (f"來源不足：重跑後仍未達 v3 最低標準（目前 {row.get('paragraphs')} 段／{row.get('zhChars')} 字；"
            f"任期齊全 {row.get('termsFull')}/{row.get('terms')}；指揮={row.get('hasCommand')} 戰役={row.get('hasBattle')}）。不硬湊。")
    p["sourceInsufficient"] = True
    gaps = p.setdefault("gaps", [])
    if not any((g.get("note") or "").startswith("來源不足") for g in gaps):
        gaps.append({"target": "paragraph:length", "gapKind": "not_found", "note": note})
    n += 1
pathlib.Path(out).write_text(json.dumps(d, ensure_ascii=False, indent=1)+"\n", encoding="utf-8")
print(f"stamped {n}")
