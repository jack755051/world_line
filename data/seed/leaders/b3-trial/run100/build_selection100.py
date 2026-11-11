#!/usr/bin/env python3
"""B3 100 人名單（只準備，不研究；Tai 2026-11-11 12:12 第 1 項）。

不連任何資料庫，只讀 repo 內離線資料：
  - data/seed/leaders/gap-830/existing_bios.tsv   候選池（bioId、姓名、中文名、生卒年；與 5442 bioId 一致，試跑 50 人全在內）
  - data/seed/leaders/gap-830/b*/sent.5052.json   gap-830 people key → bioId（只用 bioId 出現在 tsv 者）
  - data/seed/leaders/gap-830/b*/research.json    groupKeys、各欄位出處數（厚薄代理指標）
  - data/seed/leaders/gap-830/b*/worklist.json    regimes（政權 slug）、firstTermStart（年代）
  - data/seed/leaders/b3-trial/selection.json     排除已做 50 人
  - data/seed/leaders/b3-sample/research.json     排除 b3-sample 5 人（含邱吉爾）
輸出：run100/selection100.json（固定種子、無時間戳；連跑兩次逐位元相同）。
用法：python3 -I data/seed/leaders/b3-trial/run100/build_selection100.py
"""
import csv
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEADERS = HERE.parent.parent
GAP = LEADERS / "gap-830"
OUT = HERE / "selection100.json"
SEED = "b3-run100-20261111"
TOTAL, BATCH_SIZE = 100, 5
# 刻意加重薄人物（試跑 50 人中薄 11 人＝22%；本輪 35%，見 PLAN.md）
TIER_QUOTA = {"薄": 35, "中": 40, "厚": 25}
TIER_ORDER = ["薄", "中", "厚"]
EXCLUDE_NAME_HINTS = ["churchill", "adolf hitler", "getúlio", "jadambaa", "東條"]

# 政權 slug → 次區域（依 slug 字樣；順序即優先序）
SUBREGION_RULES = [
    (("british-raj", "nepal", "bhutan"), "南亞"),
    (("dutch-east-indies",), "東南亞"),
    (("afghanistan",), "中亞"),
    (("mongolian",), "內亞"),
    (("japan", "korean", "china"), "東亞"),
    (("ottoman", "grand-national-assembly", "iraq", "saudi", "yemen", "muscat", "iran", "persia"), "西亞"),
    (("georgia", "armenia", "azerbaijan", "transcaucasian"), "高加索"),
    (("egypt",), "北非"),
    (("australia",), "澳洲"),
    (("costa-rica", "el-salvador", "guatemala", "honduras", "nicaragua", "panama"), "中美"),
    (("cuba", "dominican", "haiti"), "加勒比海"),
    (("bolivia", "ecuador", "paraguay", "peru"), "南美"),
    (("russian", "ukrainian", "byelorussian", "romania", "bulgaria"), "東歐"),
    (("austria", "czechoslovak", "bohemia", "slovak", "hungar", "danzig", "polish"), "中歐"),
    (("sweden", "norway", "denmark", "iceland", "finland", "estonia", "latvia", "lithuania"), "北歐"),
    (("spain", "spanish", "portug", "vatican", "greece", "hellenic", "albania", "albanian",
      "montenegro", "serbia", "serbs", "yugoslavia", "croatia"), "南歐"),
    (("belgium", "netherlands", "luxembourg", "swiss", "monaco", "liechtenstein", "andorra",
      "ireland", "irish"), "西歐"),
]
CONTINENT = {"南亞": "亞洲", "東南亞": "亞洲", "中亞": "亞洲", "內亞": "亞洲", "東亞": "亞洲", "西亞": "亞洲",
             "高加索": "歐洲", "東歐": "歐洲", "中歐": "歐洲", "北歐": "歐洲", "南歐": "歐洲", "西歐": "歐洲",
             "北非": "非洲", "澳洲": "大洋洲", "中美": "美洲", "加勒比海": "美洲", "南美": "美洲"}
DOMINION = {"commonwealth-of-australia", "irish-free-state"}


def subregion_of(slug):
    for keys, sub in SUBREGION_RULES:
        if any(k in slug for k in keys):
            return sub
    return None


def regime_type_of(slug):
    if slug in DOMINION:
        return "自治領"
    if any(k in slug for k in ("protectorate", "under-italy", "independent-state-of-croatia", "slovak-state",
                               "dutch-east-indies", "british-raj")):
        return "殖民／保護國／傀儡"
    if any(k in slug for k in ("provisional", "government-of-the")):
        return "臨時政府"
    if any(k in slug for k in ("ssr", "sfsr", "peoples-republic", "mongolian")):
        return "蘇維埃／人民共和"
    if any(k in slug for k in ("kingdom", "empire", "tsardom", "principality", "grand-duchy", "sultanate",
                               "emirate", "imperial-state", "sublime-state")):
        return "君主制"
    return "共和制"


def era_band(year):
    if year is None:
        return "不明"
    if year < 1919:
        return "1908–1918"
    if year < 1930:
        return "1919–1929"
    if year < 1940:
        return "1930–1939"
    return "1940–1945"


def count_urls(node, acc):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "sources" and isinstance(v, list):
                for s in v:
                    if isinstance(s, dict) and s.get("url"):
                        acc.add(s["url"])
            else:
                count_urls(v, acc)
    elif isinstance(node, list):
        for v in node:
            count_urls(v, acc)
    return acc


def to_int(s):
    s = (s or "").strip()
    return int(s) if s.lstrip("-").isdigit() else None


def load():
    tsv = {}
    with open(GAP / "existing_bios.tsv", encoding="utf-8", newline="") as f:
        for row in csv.reader(f, delimiter="\t"):
            if not row or not row[0].strip():
                continue
            row += [""] * (5 - len(row))
            tsv[row[0]] = {"bioId": row[0], "name": row[1], "nameZh": row[2],
                           "birthYear": to_int(row[3]), "deathYear": to_int(row[4])}
    # gap-830：bioId → 政權、年代、出處數
    info = {}
    for bdir in sorted(p for p in GAP.glob("b[0-9]*") if p.is_dir()):
        sent, res, wl = bdir / "sent.5052.json", bdir / "research.json", bdir / "worklist.json"
        if not (sent.exists() and res.exists() and wl.exists()):
            continue
        key2bio = json.loads(sent.read_text(encoding="utf-8")).get("bios", {})
        groups = {g["key"]: g for g in json.loads(wl.read_text(encoding="utf-8"))["groups"]}
        for p in json.loads(res.read_text(encoding="utf-8"))["people"]:
            bio = key2bio.get(p["key"])
            if bio not in tsv or bio in info:
                continue
            gs = sorted((groups[k] for k in p.get("groupKeys", []) if k in groups),
                        key=lambda g: (g.get("firstTermStart") or "9999", g["key"]))
            slugs = [s for g in gs for s in g.get("regimes", [])]
            start = next((g["firstTermStart"] for g in gs if g.get("firstTermStart")), None)
            info[bio] = {"gapKey": p["key"], "gapBatch": bdir.name, "regimes": slugs,
                         "firstTermStart": start, "sourceUrls": len(count_urls(p, set()))}
    sel = json.loads((LEADERS / "b3-trial" / "selection.json").read_text(encoding="utf-8"))["people"]
    smp = json.loads((LEADERS / "b3-sample" / "research.json").read_text(encoding="utf-8"))["people"]
    excluded = {p["bioId"] for p in sel} | {p["bioId"] for p in smp}
    return tsv, info, excluded


def profile(rec, inf):
    flags = []
    if inf and inf["regimes"]:
        slug = inf["regimes"][0]
        sub = subregion_of(slug)
        if sub is None:
            flags.append("regionUnmapped")
        rtype = regime_type_of(slug)
        year = to_int((inf["firstTermStart"] or "")[:4])
        if year is None:
            flags.append("eraUncertain")
        n = inf["sourceUrls"]
        tier = "厚" if n >= 3 else ("中" if n == 2 else "薄")
        basis = f"gap-830 {inf['gapBatch']} 研究檔不同出處網址 {n} 個（≥3 厚、2 中、≤1 薄）"
    else:
        slug, sub, rtype = None, None, "不明"
        flags += ["regionUncertain", "regimeUncertain"]
        by = rec["birthYear"]
        year = None if by is None else min(max(by + 50, 1908), 1945)
        flags.append("eraUncertain")
        tier = "薄" if by is None and rec["deathYear"] is None else "中"
        flags.append("thicknessUncertain")
        basis = "不在 gap-830 研究檔；依 tsv 生卒年：皆缺→薄，否則→中（不確定）"
    return {"regimeSlug": slug, "subregion": sub or "不明", "continent": CONTINENT.get(sub, "不明"),
            "regimeType": rtype, "eraYear": year, "eraBand": era_band(year),
            "eraBasis": "worklist firstTermStart" if inf and inf.get("firstTermStart") else
                        ("tsv 生年＋50（推估，夾在 1908–1945）" if year is not None else "無"),
            "thickness": tier, "thicknessBasis": basis, "flags": flags}


def largest_remainder(counts, total):
    s = sum(counts.values())
    if s == 0:
        return {k: 0 for k in counts}
    raw = {k: total * v / s for k, v in counts.items()}
    alloc = {k: int(raw[k]) for k in counts}
    for k in sorted(counts, key=lambda k: (-(raw[k] - alloc[k]), k))[: total - sum(alloc.values())]:
        alloc[k] += 1
    # 每個有候選的洲至少 1 人（從配額最多者挪）
    for k in sorted(counts):
        if counts[k] and alloc[k] == 0 and total >= len(counts):
            donor = max(sorted(alloc), key=lambda d: alloc[d])
            alloc[donor] -= 1
            alloc[k] += 1
    return {k: min(alloc[k], counts[k]) for k in counts}


def pick(cands, n, rng_key):
    """固定種子洗牌後，依年代區段、政權類型輪流取，分散年代與政權。"""
    pool = sorted(cands, key=lambda c: c["bioId"])
    random.Random(f"{SEED}|{rng_key}").shuffle(pool)
    buckets = {}
    for c in pool:
        buckets.setdefault((c["eraBand"], c["regimeType"]), []).append(c)
    order = sorted(buckets)
    out = []
    while len(out) < n and any(buckets.values()):
        for k in order:
            if buckets[k] and len(out) < n:
                out.append(buckets[k].pop(0))
    return out


def main():
    tsv, info, excluded = load()
    cands = []
    for bio in sorted(tsv):
        rec = tsv[bio]
        if bio in excluded or any(h in f"{rec['name']} {rec['nameZh']}".lower() for h in EXCLUDE_NAME_HINTS):
            continue
        cands.append({**rec, **profile(rec, info.get(bio)), "gapKey": (info.get(bio) or {}).get("gapKey")})

    selected, shortfall = [], 0
    for tier in TIER_ORDER:
        tc = [c for c in cands if c["thickness"] == tier]
        quota = TIER_QUOTA[tier] + shortfall
        conts = {}
        for c in tc:
            conts[c["continent"]] = conts.get(c["continent"], 0) + 1
        alloc = largest_remainder(conts, min(quota, len(tc)))
        got = []
        for cont in sorted(alloc):
            got += pick([c for c in tc if c["continent"] == cont], alloc[cont], f"{tier}|{cont}")
        if len(got) < min(quota, len(tc)):  # 某洲不足 → 同層補
            rest = [c for c in tc if c not in got]
            got += pick(rest, min(quota, len(tc)) - len(got), f"{tier}|fill")
        shortfall = quota - len(got)
        selected += got
    if len(selected) < TOTAL:  # 最後一層（厚）候選不足 → 依 中、薄 順序補足
        for tier in ("中", "薄"):
            rest = [c for c in cands if c["thickness"] == tier and c not in selected]
            selected += pick(rest, TOTAL - len(selected), f"{tier}|backfill")
    assert len(selected) == TOTAL, len(selected)

    # 分 20 批×5：依（厚薄、洲、年代）排序後蛇形發牌，讓每批混合厚薄與地區
    selected.sort(key=lambda c: (TIER_ORDER.index(c["thickness"]), c["continent"], c["subregion"],
                                 c["eraBand"], c["bioId"]))
    nb = TOTAL // BATCH_SIZE
    for i, c in enumerate(selected):
        r, k = divmod(i, nb)
        c["batch"] = f"{(k if r % 2 == 0 else nb - 1 - k) + 1:02d}"
    selected.sort(key=lambda c: (c["batch"], TIER_ORDER.index(c["thickness"]), c["bioId"]))

    people = []
    for c in selected:
        why = (f"{c['subregion']}｜{c['regimeType']}｜{c['eraBand']}｜預估{c['thickness']}；"
               f"分層（{c['thickness']}×{c['continent']}）固定種子抽樣，年代×政權類型輪取")
        if c["flags"]:
            why += "；不確定：" + "、".join(c["flags"])
        people.append({"batch": c["batch"], "bioId": c["bioId"], "name": c["name"], "nameZh": c["nameZh"],
                       "birthYear": c["birthYear"], "deathYear": c["deathYear"],
                       "continent": c["continent"], "subregion": c["subregion"],
                       "regimeSlug": c["regimeSlug"], "regimeType": c["regimeType"],
                       "eraYear": c["eraYear"], "eraBand": c["eraBand"], "eraBasis": c["eraBasis"],
                       "thickness": c["thickness"], "thicknessBasis": c["thicknessBasis"],
                       "flags": c["flags"], "gapKey": c["gapKey"], "reason": why})

    def tally(field, rows):
        t = {}
        for r in rows:
            t[r[field]] = t.get(r[field], 0) + 1
        return dict(sorted(t.items()))

    out = {
        "run": "b3-run100",
        "decision": "Tai 2026-11-11 12:12 第 1 項（先調提示再跑 100 人，不寫庫）；本檔只是名單，未啟動研究",
        "seed": SEED,
        "offlineOnly": True,
        "sources": ["gap-830/existing_bios.tsv", "gap-830/b*/sent.5052.json", "gap-830/b*/research.json",
                    "gap-830/b*/worklist.json", "b3-trial/selection.json", "b3-sample/research.json"],
        "excluded": {"trial50": 50, "b3sample": 5, "note": "b3-sample 含邱吉爾；另以姓名字樣防重"},
        "tierQuota": TIER_QUOTA,
        "thicknessNote": "厚／中／薄是離線代理指標（gap-830 研究檔出處網址數），非實際 A／B 來源深度；研究時以實查為準",
        "pool": {"size": len(cands), "byThickness": tally("thickness", cands), "byContinent": tally("continent", cands)},
        "stats": {k: tally(k, people) for k in ("thickness", "continent", "subregion", "regimeType", "eraBand")},
        "flagged": sum(1 for p in people if p["flags"]),
        "batchSize": BATCH_SIZE,
        "people": people,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"pool": out["pool"], "stats": out["stats"], "flagged": out["flagged"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
