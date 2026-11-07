#!/usr/bin/env python3
"""審查用精簡輸出：python3 review.py bNN —— 每人一段：群組（政權／首任）、欄位值、每欄來源 URL＋原文摘錄（截短）；staging 與 unverified/conflicts。
另標旗：來源網域為 wikipedia/wikidata/baidu、群組未被任何人或 staging 覆蓋、群組重複分派。"""
import json, sys
from urllib.parse import urlparse
b = sys.argv[1]
wl = {g["key"]: g for g in json.load(open(f"{b}/worklist.json", encoding="utf-8"))["groups"]}
r = json.load(open(f"{b}/research.json", encoding="utf-8"))
used = []
def cut(s, n=110): s = str(s or "").replace("\n", " "); return s if len(s) <= n else s[:n] + "…"
for p in r.get("people", []):
    used += p.get("groupKeys", [])
    gs = "; ".join(f"{k}[{','.join(wl[k]['regimes']) if k in wl else '??'} {wl.get(k, {}).get('firstTermStart', '')}]" for k in p.get("groupKeys", []))
    print(f"\n## {p.get('key')}  {(p.get('name') or {}).get('value','')} / {(p.get('nameZh') or {}).get('value','')}  Q={p.get('wikidataQid')}  groups: {gs}")
    if p.get("existingBioId"): print("  LINK existing", p["existingBioId"], "|", cut(p.get("linkEvidence"), 200)); continue
    for f in ("birthDate", "deathDate", "birthPlace", "party", "summary"):
        v = p.get(f)
        if not isinstance(v, dict): continue
        print(f"  {f}: {cut(json.dumps(v.get('value'), ensure_ascii=False), 200)} {v.get('precision') or ''}")
        for s in v.get("sources") or []:
            u = s.get("url", "")
            flag = " ⚠WIKI" if any(w in urlparse(u).netloc for w in ("wikipedia", "wikidata", "baidu")) else ""
            print(f"     · {u}{flag} | {cut(s.get('locator'),30)} | “{cut(s.get('evidence'), 75)}”")
    for k in ("unverified", "conflicts"):
        if p.get(k): print(f"  {k}: {cut('; '.join(f"{x.get('field')}: {x.get('why') or x.get('note') or ''}" for x in p[k]), 260)}")
    if p.get("portrait"): print("  portrait:", cut(json.dumps(p["portrait"], ensure_ascii=False), 200))
for s in r.get("staging", []):
    used += s.get("groupKeys", [])
    print(f"\n## STAGING {s.get('groupKeys')} {s.get('names')} | why: {cut(s.get('why'), 220)} | clues: {cut(s.get('clues'), 160)}")
dup = {k for k in used if used.count(k) > 1}; miss = set(wl) - set(used); extra = set(used) - set(wl)
print(f"\n覆蓋：worklist {len(wl)}、未覆蓋 {sorted(miss)}、重複 {sorted(dup)}、不在 worklist {sorted(extra)}")
