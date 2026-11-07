#!/usr/bin/env python3
"""從 status.json 取「待查」群組，依未連結任期天數排序，切出一批寫成 bNN/worklist.json。
用法：python3 make_worklist.py bNN start count [slug前綴過濾...]（start 從 0 起，對排序後的「待查」清單）"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
st = json.load(open(os.path.join(HERE, "status.json"), encoding="utf-8"))
batch, start, count = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
pend = sorted([(k, g) for k, g in st["groups"].items() if g["status"] == "待查"], key=lambda kv: (-kv[1]["days"], kv[0]))
sel = pend[start:start + count]
os.makedirs(os.path.join(HERE, batch), exist_ok=True)
json.dump({"batch": batch, "groups": [{"key": k, "name": g["name"], "zh": g["zh"], "regimes": g["slugs"], "recordIds": g["recordIds"],
                                         "firstTermStart": g["first"]} for k, g in sel]},
          open(os.path.join(HERE, batch, "worklist.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(batch, len(sel), [g["name"][:30] for _, g in sel])
