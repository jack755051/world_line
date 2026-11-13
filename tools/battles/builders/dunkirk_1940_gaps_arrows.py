"""dunkirk_1940：前端靜態 JSON 的進攻箭頭沒有通過驗證的 A/B 引文，依主管 2026-11-13 20:54「不寫庫，記成 gap」寫入 gaps.json。
只追加、以 target 去重；不改靜態 JSON、不寫資料庫。
用法：python3 -I tools/battles/builders/dunkirk_1940_gaps_arrows.py dunkirk_1940
"""
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
if len(sys.argv) < 2 or sys.argv[1] != "dunkirk_1940":
    raise SystemExit("用法：python3 -I tools/battles/builders/dunkirk_1940_gaps_arrows.py dunkirk_1940")
D = REPO / "data/seed/battles/dunkirk_1940"
static = json.loads((REPO / "frontend/public/campaigns/dunkirk_1940.json").read_text())
gp = D / "gaps.json"; g = json.loads(gp.read_text()); have = {x["target"] for x in g["gaps"]}
n = 0
for a in static["layers"]["arrows"]["features"]:
    p = a["properties"]; t = f"frontend/public/campaigns/dunkirk_1940.json:arrows:{p['id']}"
    if t in have: continue
    g["gaps"].append({"target": t, "kind": "arrow_missing_ab_citation",
        "note": f"P{p.get('phase')} 進攻箭頭 {p.get('from')} → {p.get('to')}（{p.get('unit') or '—'}）沒有通過驗證的 A/B 引文；依主管 2026-11-13 20:54 不寫入資料庫，只標待查證缺口",
        "checkedOn": "2026-11-13"}); n += 1
gp.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n"); print("added", n, "total", len(g["gaps"]))
