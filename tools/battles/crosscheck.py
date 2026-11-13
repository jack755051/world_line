"""戰役資料多來源比對與可信度（共用工具）。規則見 docs/source-rules.md（Tai 2026-11-13 核准 D1–D6）。

來源等級、獨立來源、可信程度分開判定，互不換算：
  verified     一筆 A，或兩個獨立家族的 A/B；引文逐字自檢通過
  needs-check  有 A/B 出處但不到上列門檻；或只有 C 級
  estimate     沒有出處，或本來就是推估（地圖數位化位置、前線、疆界）
- 來源等級不因來源數目更動：effectiveGrade＝最佳 grade（欄位名沿用；已取消「單一來源降一級」）。
- 對手方的 A 不能單獨成立：講單一陣營的資料（R1 部隊、R3 位置、R7 指揮官）若 A/B 出處全來自對手方，一律 needs-check（opposingOnly=true）。
  來源立場寫在 battle.config.json 的 sourceFamilies.sides（家族 → 陣營代號，或 "third"）；單一 A 的家族沒登記立場時不升 verified。
- 「獨立來源」＝不同來源家族：battle.config.json 的 sourceFamilies.map 把 sourceKey 對到家族；沒列的 sourceKey 自成一族。引文 quoteCheck 未通過者不算。
- 可當戰役事實（可寫入資料庫）：最佳 grade 屬 battleFactGrades（預設 A/B）。只有一個來源不影響能不能寫入。
  否則 confidence.battleFact=false，只留作候選並記入 gaps（kind=below_fact_grade）。
注意：主專案檔目前每筆只存一個值，本工具不判 conflict（衝突仍記在 gaps.json）。

用法：python3 -I tools/battles/crosscheck.py <battle> [--apply]
寫  data/seed/battles/<battle>/checks/crosscheck.json（逐筆）與 checks/CROSSCHECK.md（總表）
    --apply：另把 confidence 欄寫回各筆資料
"""
import collections, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COLLECTIONS = [  # (檔名, 陣列欄位, 鍵產生方式, 種類)
    ("r1-units.json", "units", lambda r, i: r["unitKey"], "R1 部隊"),
    ("r3-unit-positions.json", "positions", lambda r, i: f'{r["unitKey"]}@{r["date"]}#{i}', "R3 部隊位置（文字）"),
    ("r4-leadin-fronts.json", "fronts", lambda r, i: f'{r["date"]}#{i}', "R4 前段前線（文字）"),
    ("r4-fronts.json", "fronts", lambda r, i: r["lineKey"], "R4 主期前線（地圖）"),
    ("r5-engagements.json", "engagements", lambda r, i: r["key"], "R5 交戰"),
    ("r6-site-control.json", "sites", lambda r, i: f'{r["placeAsInSource"]}@{r["date"]}#{i}', "R6 據點易手"),
    ("r7-commanders.json", "commanders", lambda r, i: f'{r["unitKey"]}:{r.get("personKey") or r.get("name")}#{i}', "R7 指揮官"),
    ("r7-missing-people.json", "people", lambda r, i: r.get("key") or r.get("name") or str(i), "R7 待補人物"),
    ("phase-leadin.json", "phases", lambda r, i: r["key"], "前段階段"),
]
GRADES = ["A", "B", "C"]
OK_QC = ("verbatim", "verbatim-pdf-hyphen")
ZH = {"verified": "已查證", "needs-check": "待查證", "estimate": "推估"}


FAM = {}
SIDES = {}      # 家族 → 陣營代號或 "third"
UNIT_SIDE = {}  # unitKey → 陣營代號
SIDED = ("r1-units.json", "r3-unit-positions.json", "r7-commanders.json")


def fam(c):
    k = c.get("sourceKey") or c.get("url")
    return FAM.get(k, k)


def judge(rec, fact_grades=("A", "B"), rec_side=None):
    cits = [c for c in rec.get("citations", []) or [] if isinstance(c, dict)]
    # 主管裁示可指定某筆紀錄的關鍵欄位（如日期）只由特定來源家族支持：只以這些家族的引文判定等級（其餘引文保留但不計）
    rul = rec.get("confidenceRuling") or {}
    if rul.get("basisFamilies"):
        cits = [c for c in cits if fam(c) in rul["basisFamilies"]]
    good = [c for c in cits if c.get("grade") in GRADES and (c.get("quoteCheck") or {}).get("status", "verbatim") in OK_QC]
    ab = [c for c in good if c["grade"] in ("A", "B")]
    srcs = sorted({fam(c) for c in good})
    ab_srcs = sorted({fam(c) for c in ab})
    best = min((c["grade"] for c in good), key=GRADES.index, default=None)
    estimate_kind = rec.get("estimate") == "推估" or rec.get("basis") in ("map-digitized",)
    opposing = False
    if not good:
        lv, why = "estimate", "沒有出處" if not estimate_kind else "推估（地圖數位化／依文字推定頂點）"
    elif ab:
        a_fams = sorted({fam(c) for c in ab if c["grade"] == "A"})
        if len(ab_srcs) >= 2:
            lv, why = "verified", f"{len(ab_srcs)} 個獨立 A/B 來源家族（{'、'.join(ab_srcs)}）"
        elif a_fams and (not rec_side or SIDES.get(a_fams[0])):
            lv, why = "verified", f"一筆 A 級出處（{a_fams[0]}）"
        elif a_fams:
            lv, why = "needs-check", f"一筆 A 級出處（{a_fams[0]}），但來源立場未登記"
        else:
            lv, why = "needs-check", "只有一個獨立 B 級來源家族（" + ab_srcs[0] + "）"
        if rec_side and all(SIDES.get(f) not in (None, "third", rec_side) for f in ab_srcs):
            opposing = True
            lv, why = "needs-check", f"只有對手方的說法（{'、'.join(ab_srcs)}）：對手方出處不能單獨成立"
    else:
        lv, why = "needs-check", "只有 C 級出處"
    if estimate_kind and lv == "verified":
        lv, why = "needs-check", why + "；位置／線形為推估"
    if rul.get("basisFamilies"):
        why = f"{why}；依裁示只計 {'、'.join(rul['basisFamilies'])}（{rul.get('why', '')}）"
    single = len(srcs) == 1
    eff = best
    return {"level": lv, "levelZh": ZH[lv], "why": why, "independentSources": srcs, "singleSource": single, "opposingOnly": opposing,
            "bestGrade": best, "effectiveGrade": eff, "battleFact": bool(eff in fact_grades) if good else False,
            "sourceKeys": sorted({c.get("sourceKey") or c.get("url") for c in good})}


def main():
    battle = sys.argv[1]; apply = "--apply" in sys.argv
    D = REPO / "data" / "seed" / "battles" / battle
    cfg = json.loads((D / "battle.config.json").read_text()) if (D / "battle.config.json").exists() else {}
    FAM.clear(); FAM.update((cfg.get("sourceFamilies") or {}).get("map", {}))
    SIDES.clear(); SIDES.update((cfg.get("sourceFamilies") or {}).get("sides", {}))
    UNIT_SIDE.clear()
    if (D / "r1-units.json").exists():
        UNIT_SIDE.update({u["unitKey"]: u.get("side") for u in json.loads((D / "r1-units.json").read_text()).get("units", [])})
    fact_grades = tuple(cfg.get("battleFactGrades", ["A", "B"]))
    items, per = {}, collections.defaultdict(collections.Counter)
    below = []
    docs = {}
    for fn, arr, keyf, kind in COLLECTIONS:
        p = D / fn
        if not p.exists(): continue
        d = json.loads(p.read_text()); docs[p] = d
        for i, r in enumerate(d.get(arr, [])):
            j = judge(r, fact_grades, (r.get("side") or UNIT_SIDE.get(r.get("unitKey"))) if fn in SIDED else None); k = f"{fn}:{keyf(r, i)}"
            if j["bestGrade"] and not j["battleFact"]:
                below.append((k, j))
            items[k] = {"kind": kind, **j}
            per[kind][j["level"]] += 1; per[kind]["single"] += j["singleSource"]
            per[kind]["opp"] += j["opposingOnly"]; per[kind]["nofact"] += bool(j["bestGrade"] and not j["battleFact"])
            if apply:
                r["confidence"] = {"level": j["level"], "why": j["why"], "singleSource": j["singleSource"], "opposingOnly": j["opposingOnly"], "sourceFamilies": j["independentSources"],
                                   "effectiveGrade": j["effectiveGrade"], "battleFact": j["battleFact"], "tool": "tools/battles/crosscheck.py"}
                if j["bestGrade"] and not j["battleFact"]:
                    r["confidence"]["battleFactNote"] = f"最佳出處為 {j['bestGrade']} 級，戰役只收 {'/'.join(fact_grades)}：保留作候選，不當戰役事實"
        if apply:
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    summ = {lv: sum(c[lv] for c in per.values()) for lv in ("verified", "needs-check", "estimate")}
    summ["singleSource"] = sum(c["single"] for c in per.values()); summ["opposingOnly"] = sum(c["opp"] for c in per.values())
    summ["notBattleFact"] = len(below)
    if apply:
        G = D / "gaps.json"; g = json.loads(G.read_text()); today = __import__("datetime").date.today().isoformat()
        g["gaps"] = [x for x in g["gaps"] if x.get("kind") not in ("single_source_below_fact_grade", "below_fact_grade")]
        for k, j in below:
            g["gaps"].append({"target": k, "kind": "below_fact_grade",
                              "note": f"出處 {'、'.join(j['sourceKeys'])} 最佳為 {j['bestGrade']} 級；戰役只收 {'/'.join(fact_grades)}，保留為候選、不當戰役事實，待補 A/B 來源",
                              "checkedOn": today, "tool": "tools/battles/crosscheck.py"})
        G.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (D / "checks").mkdir(exist_ok=True)
    (D / "checks" / "crosscheck.json").write_text(json.dumps({"meta": {"generated_by": "tools/battles/crosscheck.py", "battle": battle},
                                                              "summary": summ, "items": items}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md = [f"# 多來源比對：{battle}", "", "由 `tools/battles/crosscheck.py` 產生，不要手改。規則見 `docs/source-rules.md`：已查證＝一筆 A 或兩個獨立家族的 A/B；來源等級不因來源數目更動；對手方出處不能單獨成立。", "",
          "來源家族（battle.config.json）：" + "；".join(f"{k}→{v}" for k, v in FAM.items()), "",
          "來源立場：" + ("；".join(f"{k}＝{v}" for k, v in SIDES.items()) or "未登記"), "",
          "| 種類 | 已查證 | 待查證 | 推估 | 單一來源 | 只有對手方說法 | 不到 A/B（不寫入） |", "|---|---|---|---|---|---|---|"]
    for kind, c in per.items():
        md.append(f"| {kind} | {c['verified']} | {c['needs-check']} | {c['estimate']} | {c['single']} | {c['opp']} | {c['nofact']} |")
    md.append(f"| **合計** | {summ['verified']} | {summ['needs-check']} | {summ['estimate']} | {summ['singleSource']} | {summ['opposingOnly']} | {summ['notBattleFact']} |")
    (D / "checks" / "CROSSCHECK.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summ, ensure_ascii=False))
    for kind, c in per.items(): print(kind, dict(c))


if __name__ == "__main__":
    main()
