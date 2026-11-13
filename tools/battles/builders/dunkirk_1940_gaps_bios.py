"""dunkirk_1940：r7-missing-people 的 22 位指揮官尚無生平主檔，依主管 2026-11-13 20:44（Tai 20:43 同意寫庫）「不補，只標 gap」寫入 gaps.json。
只追加、以 target 去重；不改 r7 檔、不建生平。
用法：python3 -I tools/battles/builders/dunkirk_1940_gaps_bios.py dunkirk_1940
"""
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
if len(sys.argv) < 2 or sys.argv[1] != "dunkirk_1940":
    raise SystemExit("用法：python3 -I tools/battles/builders/dunkirk_1940_gaps_bios.py dunkirk_1940")
D = REPO / "data/seed/battles/dunkirk_1940"
people = json.loads((D / "r7-missing-people.json").read_text())["people"]
gp = D / "gaps.json"; g = json.loads(gp.read_text()); have = {x["target"] for x in g["gaps"]}
n = 0
for p in people:
    t = f"r7-missing-people.json:{p['name']}"
    if t in have: continue
    g["gaps"].append({"target": t, "kind": "commander_missing_bio",
        "note": f"{p['name']}（{p.get('nameZh') or '—'}，{p.get('unitKey') or '—'}）尚無 leader_bios 生平主檔；依主管 2026-11-13 20:44 不補，只標待查證缺口",
        "checkedOn": "2026-11-13"}); n += 1
gp.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n"); print("added", n, "total", len(g["gaps"]))
