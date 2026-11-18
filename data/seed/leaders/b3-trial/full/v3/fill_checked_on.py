#!/usr/bin/env python3
"""補缺口的 checkedOn（寫庫腳本必填，研究 agent 偶爾漏寫）。取值順序：同一人其他缺口最常見的日期 → 同批缺口 → 同批引文 accessedOn。
只補缺的欄位，不動其他內容。用法：python3 -I fill_checked_on.py <research.json> [...]
"""
import collections, json, re, sys

for f in sys.argv[1:]:
    s = open(f, encoding="utf-8").read(); d = json.loads(s)
    batch = collections.Counter(g["checkedOn"] for p in d["people"] for g in p.get("gaps", []) if g.get("checkedOn"))
    acc = collections.Counter(re.findall(r'"accessed(?:On|_on)": "(\d{4}-\d\d-\d\d)"', s))
    n = 0
    for p in d["people"]:
        own = collections.Counter(g["checkedOn"] for g in p.get("gaps", []) if g.get("checkedOn"))
        pick = (own or batch or acc).most_common(1)
        for g in p.get("gaps", []):
            if not g.get("checkedOn"):
                if not pick:
                    sys.exit(f"{f}: {p['key']} 找不到可用日期")
                g["checkedOn"] = pick[0][0]; n += 1
    if n:
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1); fh.write("\n")
    print(f, "filled", n)
