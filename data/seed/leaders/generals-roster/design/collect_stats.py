#!/usr/bin/env python3
"""人物事實分層設計（ARCHITECTURE §20）的佐證統計；唯讀，只寫本目錄的 stats.json／stats.md。
2026-11-12 21:40 改版（主迴圈 21:29 結束後重跑）：min-check 改為以 ../bios/check_min.check() 對**現行 research.json 重算**，
不再讀批次目錄的 min-check.json——該檔是第 1 輪（retry 前）結果，retry 後的結果在 min-check.round2.json；
直接讀 min-check.json 會把 retry 後已達標的人算成未達標（21:29 時 22 人：S 3、A 19）。
同時輸出 rows（358 列）與 unique（扣掉已知重複鍵 chesternimitz、小泽治三郎；合併後兩者自然消失）。
09:20 版快照保存在 stats-20261112-0920.md／.json（§20 引用的是該快照）。
用法（repo 根目錄）：python3 -I data/seed/leaders/generals-roster/design/collect_stats.py
來源：generals-roster/bios/{S,A}/batch*/research.json、min-check.json、selection.json；
      b3-trial/**/research.json（B3，無國籍欄，只做整體網域統計）；.dev/cc-generals-*.json（total_cost_usd）。
"""
import json, glob, collections, re, datetime, sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(".")
BIOS = ROOT / "data/seed/leaders/generals-roster/bios"
OUT = ROOT / "data/seed/leaders/generals-roster/design"
sys.path.insert(0, str(BIOS))
from check_min import check as check_min  # noqa: E402
# 已知重複（主管 06:32 Nimitz、10:20 小澤；patch_merge_duplicates.py 於主迴圈後合併，保留左側）
DUP_OF = {("S", "chesternimitz"): "chesterwnimitz", ("A", "小泽治三郎"): "jisaburoozawa"}
GROUP = {"德國": "德國", "日本": "日本", "英國": "英國", "美國": "美國", "法國": "法國", "義大利": "義大利",
         "蘇聯": "蘇俄", "俄羅斯帝國": "蘇俄", "中華民國-國民政府": "中國", "中國共產黨": "中國",
         "澳洲": "大英國協", "紐西蘭": "大英國協", "加拿大": "大英國協", "南非": "大英國協"}

def host(u):
    h = (urlparse(u).hostname or "").lower() if u else ""
    return h[4:] if h.startswith("www.") else h

def load(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None

def cits_of(p):
    for kind, arr in (("paragraph", p.get("paragraphs")), ("position", p.get("positions")), ("role", p.get("roleCandidates"))):
        for x in arr or []:
            for c in x.get("citations") or []:
                yield kind, c

sel = load(BIOS / "selection.json")
country = {}
for t in ("S", "A"):
    for b in sel[t]:
        for q in b["people"]:
            country[q["key"]] = q["country"]

# ---- b. 網域命中 ----
dom = collections.defaultdict(lambda: collections.defaultdict(lambda: {"cit": 0, "A": 0, "B": 0, "C": 0, "people": set()}))
people_per_group = collections.defaultdict(set)
src_count = collections.Counter()
person_rows = []
import subprocess
def committed(f):
    """只收已 commit 的批次（主迴圈 commit 前 research.json 已在寫；2026-11-12 09:20 快照因此多算 A/batch016 的 5 人）。"""
    if not (Path(f).parent / "min-check.json").exists():
        return False
    return subprocess.run(["git", "ls-files", "--error-unmatch", str(f)], capture_output=True).returncode == 0
batches = sorted(f for f in glob.glob(str(BIOS / "*/batch*/research.json")) if committed(f))
for f in batches:
    d = load(f)
    if not d:
        continue
    tier = Path(f).parent.parent.name
    srcs = d.get("sources") or {}
    for p in d.get("people") or []:
        k = p.get("key")
        g = GROUP.get(country.get(k, "?"), "其他")
        people_per_group[g].add((tier, k))
        hosts = collections.Counter()
        for kind, c in cits_of(p):
            s = srcs.get(c.get("sourceKey")) or {}
            h = host(s.get("url")) or "(無網址)"
            gr = c.get("grade") or s.get("grade") or "?"
            e = dom[g][h]
            e["cit"] += 1
            if gr in ("A", "B", "C"):
                e[gr] += 1
            e["people"].add((tier, k))
            hosts[h] += 1
        person_rows.append({"tier": tier, "key": k, "country": country.get(k), "group": g,
                            "batch": Path(f).parent.name, "domains": dict(hosts)})

dom_out = {}
for g, m in dom.items():
    n = len(people_per_group[g])
    rows = []
    for h, e in m.items():
        rows.append({"domain": h, "citations": e["cit"], "A": e["A"], "B": e["B"], "C": e["C"],
                     "people": len(e["people"]), "coverage": round(len(e["people"]) / n, 3) if n else 0})
    rows.sort(key=lambda r: (-r["people"], -r["citations"]))
    dom_out[g] = {"people": n, "domains": rows}

# ---- c. min-check ----
mc = {"S": [], "A": []}
stale = []
for f in batches:
    tier = Path(f).parent.parent.name
    d = load(f)
    old = {r["key"]: r for r in ((load(Path(f).parent / "min-check.json") or {}).get("people") or [])}
    for p in (d or {}).get("people") or []:
        r = check_min(p); r["batch"] = Path(f).parent.name
        r["duplicateOf"] = DUP_OF.get((tier, r["key"]))
        mc[tier].append(r)
        o = old.get(r["key"])
        if o is not None and o.get("meetsMinimum") != r["meetsMinimum"]:
            stale.append({"tier": tier, "batch": r["batch"], "key": r["key"], "minCheckJson": o.get("meetsMinimum"), "recomputed": r["meetsMinimum"]})

def reasons(r):
    out = []
    if r["paragraphs"] < 3: out.append("段落<3")
    if r["zhChars"] < 300: out.append("字數<300")
    if r["termsMissing"] or r["termsFlagged"]: out.append("職位缺起訖")
    if not r["hasCommand"]: out.append("無指揮職")
    if not r["hasBattle"]: out.append("無戰役")
    return out

mc_out = {}
fails_all = []
for t, rows in mc.items():
    keys = collections.Counter(r["key"] for r in rows)
    fail = [r for r in rows if not r["meetsMinimum"]]
    rc = collections.Counter()
    only = collections.Counter()
    for r in fail:
        rs = reasons(r)
        for x in rs: rc[x] += 1
        only["+".join(rs) or "(無)"] += 1
        fails_all.append({"tier": t, "key": r["key"], "name": r["name"], "batch": r["batch"], "reasons": rs,
                          "group": GROUP.get(country.get(r["key"], "?"), "其他"),
                          "sourceInsufficient": r["sourceInsufficient"], "duplicateOf": r["duplicateOf"],
                          **{k: r[k] for k in ("paragraphs", "zhChars", "terms", "termsFull", "termsFlagged", "termsMissing", "hasCommand", "hasBattle")}})
    uq = [r for r in rows if not r["duplicateOf"]]
    mc_out[t] = {"rows": len(rows), "uniqueKeys": len(keys), "duplicateKeys": [k for k, v in keys.items() if v > 1],
                 "knownDuplicatesPresent": [r["key"] for r in rows if r["duplicateOf"]],
                 "uniquePeople": len(uq), "uniqueMeets": sum(r["meetsMinimum"] for r in uq), "uniqueFail": sum(not r["meetsMinimum"] for r in uq),
                 "meets": sum(r["meetsMinimum"] for r in rows), "fail": len(fail),
                 "failMarkedInsufficient": sum(r["sourceInsufficient"] for r in fail),
                 "failNotMarked": sum(not r["sourceInsufficient"] for r in fail),
                 "termsFull": sum(r["termsFull"] for r in rows), "termsFlagged": sum(r["termsFlagged"] for r in rows),
                 "termsMissing": sum(r["termsMissing"] for r in rows), "terms": sum(r["terms"] for r in rows),
                 "noBattle": sum(not r["hasBattle"] for r in rows), "noCommand": sum(not r["hasCommand"] for r in rows),
                 "failReasonCount": dict(rc), "failReasonCombo": dict(only.most_common()),
                 "paragraphsDist": dict(collections.Counter(r["paragraphs"] for r in rows)),
                 "zhCharsMin": min((r["zhChars"] for r in rows), default=0), "zhCharsMax": max((r["zhChars"] for r in rows), default=0)}
mc_out["selectionCounts"] = sel["counts"]
mc_out["staleMinCheckJson"] = stale
s_sel = {q["key"] for b in sel["S"] for q in b["people"]}
s_done = {r["key"] for r in mc["S"]}
mc_out["S_missingFromMinCheck"] = sorted(s_sel - s_done)

# ---- d. 費用 ----
cost = collections.defaultdict(lambda: {"files": 0, "usd": 0.0})
total = 0.0
for f in sorted(glob.glob(".dev/cc-generals-*.json")) + [".dev/cc-person-facts-design.json", ".dev/cc-person-facts-estimate.json"]:
    d = load(f)
    if not isinstance(d, dict) or "total_cost_usd" not in d:
        continue
    name = Path(f).name
    m = re.match(r"cc-generals-(?:bios-)?(insuff-)?([SA])-b\d+-(sonnet|retry|opus)", name)
    cat = (("insuff-" if m.group(1) else "") + m.group(2) + "-" + m.group(3)) if m else "other:" + name
    cost[cat]["files"] += 1; cost[cat]["usd"] += d["total_cost_usd"]; total += d["total_cost_usd"]
people_done = {t: mc_out[t]["uniqueKeys"] for t in ("S", "A")}
cost_out = {"byCategory": {k: {"files": v["files"], "usd": round(v["usd"], 4)} for k, v in sorted(cost.items())},
            "totalUsd": round(total, 4), "peopleWithMinCheck": people_done}
for t in ("S", "A"):
    usd = sum(v["usd"] for k, v in cost.items() if re.fullmatch(rf"{t}-(sonnet|retry|opus)", k))
    cost_out[f"{t}_usdPerPerson"] = round(usd / people_done[t], 4) if people_done[t] else None
    cost_out[f"{t}_retryUsd"] = round(cost.get(f"{t}-retry", {"usd": 0})["usd"], 4)
    cost_out[f"{t}_retryFiles"] = cost.get(f"{t}-retry", {"files": 0})["files"]
ins = [v for k, v in cost.items() if k.startswith("insuff-")]
cost_out["insuff_usd"] = round(sum(v["usd"] for v in ins), 4)

# ---- B3 ----
b3 = collections.defaultdict(lambda: {"cit": 0, "A": 0, "B": 0, "C": 0, "people": set()})
b3people = set()
for f in sorted(glob.glob("data/seed/leaders/b3-trial/**/research.json", recursive=True)):
    d = load(f)
    if not d: continue
    srcs = d.get("sources") or {}
    for p in d.get("people") or []:
        b3people.add(p.get("key"))
        for kind, c in cits_of(p):
            s = srcs.get(c.get("sourceKey")) or {}
            h = host(s.get("url")) or "(無網址)"
            e = b3[h]; e["cit"] += 1
            gr = c.get("grade") or s.get("grade")
            if gr in ("A", "B", "C"): e[gr] += 1
            e["people"].add(p.get("key"))
b3_out = {"files": len(glob.glob("data/seed/leaders/b3-trial/**/research.json", recursive=True)), "uniquePeople": len(b3people),
          "domains": sorted([{"domain": h, "citations": e["cit"], "A": e["A"], "B": e["B"], "C": e["C"], "people": len(e["people"])}
                             for h, e in b3.items()], key=lambda r: (-r["people"], -r["citations"]))[:40]}

out = {"generatedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
       "note": "快照；主迴圈已於 2026-11-12 21:29 結束（commit 52fd188）。min-check 以 check_min.check() 對現行 research.json 重算（不讀 retry 前的 min-check.json）。網域以引文（paragraph／position／roleCandidate citations）計，people＝至少一筆引文用到該網域的人數。費用含 .dev/cc-generals-*.json＋cc-person-facts-design.json＋cc-person-facts-estimate.json（若已存在）。",
       "researchFiles": len(batches), "domainsByGroup": dom_out, "minCheck": mc_out, "failing": fails_all,
       "cost": cost_out, "b3": b3_out, "persons": person_rows}
(OUT / "stats.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

L = [f"# 人物事實分層：佐證統計（{out['generatedAt']}）", "", out["note"], "",
     f"research.json 檔數：{len(batches)}", ""]
L += ["## min-check", ""]
for t in ("S", "A"):
    m = mc_out[t]
    L.append(f"- {t}：{m['uniqueKeys']} 人（列 {m['rows']}；重複鍵 {m['duplicateKeys']}），達標 {m['meets']}，未達標 {m['fail']}（已標來源不足 {m['failMarkedInsufficient']}，未標 {m['failNotMarked']}）；"
             f"任期完整 {m['termsFull']}/{m['terms']}（缺迄待查 {m['termsFlagged']}、缺起或迄 {m['termsMissing']}）；無戰役 {m['noBattle']}；無指揮職 {m['noCommand']}")
    L.append(f"  - 扣已知重複（{m['knownDuplicatesPresent']}）：{m['uniquePeople']} 人，達標 {m['uniqueMeets']}，未達標 {m['uniqueFail']}")
    L.append(f"  - 未達標原因（可重複）：{m['failReasonCount']}")
    L.append(f"  - 原因組合：{m['failReasonCombo']}")
L.append(f"- S 名單中沒有 min-check 的人：{mc_out['S_missingFromMinCheck']}")
L.append(f"- min-check.json（retry 前）與重算結果不同：{len(stale)} 人（{collections.Counter(x['tier'] for x in stale)}）：{[x['tier']+'/'+x['batch']+' '+x['key'] for x in stale]}")
L += ["", "## 費用", "", f"- 合計 USD {cost_out['totalUsd']}", f"- 分類：{cost_out['byCategory']}",
      f"- 每人平均（主迴圈 sonnet＋retry）：S {cost_out['S_usdPerPerson']}、A {cost_out['A_usdPerPerson']}", ""]
L += ["## 各國籍網域命中（前 12，依人數）", ""]
for g in sorted(dom_out, key=lambda g: -dom_out[g]["people"]):
    L += [f"### {g}（{dom_out[g]['people']} 人）", "", "| 網域 | 引文 | A | B | C | 人數 | 覆蓋率 |", "|---|---|---|---|---|---|---|"]
    for r in dom_out[g]["domains"][:12]:
        L.append(f"| {r['domain']} | {r['citations']} | {r['A']} | {r['B']} | {r['C']} | {r['people']} | {r['coverage']:.0%} |")
    L.append("")
L += [f"## B3（b3-trial，{b3_out['files']} 檔、{b3_out['uniquePeople']} 個不同 key，無國籍欄）前 15", "",
      "| 網域 | 引文 | A | B | C | 人數 |", "|---|---|---|---|---|---|"]
for r in b3_out["domains"][:15]:
    L.append(f"| {r['domain']} | {r['citations']} | {r['A']} | {r['B']} | {r['C']} | {r['people']} |")
(OUT / "stats.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L[:20]))
