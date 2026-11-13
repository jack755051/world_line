"""R4 前線建置（共用版，由 dunkirk_1940/tools/build_r4.py 一般化）。
用法：python3 -I tools/battles/build_r4.py <battle>     例：python3 -I tools/battles/build_r4.py poland_1939
設定：data/seed/battles/<battle>/battle.config.json 的 "r4"：
  {"maps": [mapKey...], "box": [lonMin, latMin, lonMax, latMax], "dates": [YYYY-MM-DD...],
   "dateGapNotes": {"YYYY-MM-DD": "說明"}, "defaultGapNote": "說明"}
輸入：digitized/<mapKey>.json（tools/battles/georef.py 輸出）＋ <mapKey>.readings.json；只收 threshold.passes 為 true 的圖。
     選用：r4-text-vertices.json（{"fronts":[...]}，文字出處推得的頂點，basis "text"，原樣併入並計入日期覆蓋）。
輸出：r4-fronts.json（可重跑）。
"""
import json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main():
    battle = sys.argv[1]
    root = REPO / "data/seed/battles" / battle
    cfg = json.loads((root / "battle.config.json").read_text())["r4"]
    dig = root / "digitized"
    lon0, lat0, lon1, lat1 = cfg["box"]
    fronts, excluded, noLine = [], [], []
    for mk in cfg["maps"]:
        p = dig / f"{mk}.json"
        if not p.exists():
            excluded.append({"mapKey": mk, "reason": "尚未配準（無 georef 輸出）"})
            continue
        m = json.loads(p.read_text())
        th = m["threshold"]
        if not th["passes"]:
            excluded.append({"mapKey": mk, "loo_p95_km": th["loo_p95_km"], "reason": f"留一 95 百分位超過 {th.get('limit_km', 2)} km 門檻，僅供參考，不取前線頂點"})
            continue
        rd = json.loads((dig / f"{mk}.readings.json").read_text())
        src = m["source"]
        if not m.get("lines"):
            noLine.append({"mapKey": mk, "mapDate": m["mapDate"], "reason": rd.get("linesNote", "圖上無前線可讀")})
            continue
        if all(l["lineKind"] == "boundary" for l in m["lines"]):
            noLine.append({"mapKey": mk, "mapDate": m["mapDate"], "reason": m["lines"][0].get("readNote", "")})
        g = m["georef"]
        for ln in m["lines"]:
            fronts.append({
                "date": ln.get("date", m["mapDate"]), "dateNote": rd.get("dateNote", ""),
                "lineKey": ln["lineKey"], "lineKind": ln["lineKind"], "side": ln["side"], "label": ln["label"],
                "vertices": [{"lonlat": v["lonlat"], "px": v["px"], "nearPlace": v.get("nearPlace")} for v in ln["vertices"]],
                "basis": "map-digitized", "estimate": "推估",
                "mapRef": {"mapKey": mk, "citation": src["citation"], "mapDate": m["mapDate"], "url": src["url"], "grade": src["grade"]},
                "method": "tools/battles/georef.py 二次多項式",
                "georef": {"control_points": g["control_points"], "loo_median_km": g["loo_median_km"], "loo_p95_km": g["loo_p95_km"]},
                "precision_m": m["precision_m"],
                "precisionNote": m["precisionNote"] + "；前線頂點為目視讀圖（約 ±3–6 px），未含線寬",
                "readNote": ln.get("readNote", ""),
            })
    tv = root / "r4-text-vertices.json"
    if tv.exists():
        fronts += json.loads(tv.read_text())["fronts"]
    have = {f["date"] for f in fronts if f["lineKind"] != "boundary"}
    gaps = []
    for d in cfg["dates"]:
        if d in have:
            continue
        nl = [n for n in noLine if n["mapDate"] == d]
        why = ("有通過門檻的圖，但圖上未畫出前線：" + nl[0]["reason"]) if nl else cfg.get("dateGapNotes", {}).get(d, cfg.get("defaultGapNote", "沒有通過門檻的態勢圖，也沒有文字頂點"))
        gaps.append({"date": d, "reason": why})
    out = {"schema": "battle-data/0.1 r4", "rule": "地圖頂點只取留一 95 百分位 ≤ 門檻的圖；文字頂點一律推估",
           "fronts": fronts, "excludedMaps": excluded, "gapsByDate": gaps}
    (root / "r4-fronts.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    bad = 0
    for f in fronts:
        oob = [v for v in f["vertices"] if not (lon0 <= v["lonlat"][0] <= lon1 and lat0 <= v["lonlat"][1] <= lat1)]
        if len(f["vertices"]) < 2 or oob:
            bad += 1
            print("CHECK 失敗", f["lineKey"], len(f["vertices"]), oob)
    per = {}
    for f in fronts:
        k = (f.get("mapRef") or {}).get("mapKey") or f.get("basis", "?"); a = per.setdefault(k, [0, 0]); a[0] += 1; a[1] += len(f["vertices"])
    print(f"fronts {len(fronts)} 條；各來源（線,頂點）{per}；排除 {[e['mapKey'] for e in excluded]}；缺口 {len(gaps)} 天；自檢失敗 {bad}")


if __name__ == "__main__":
    main()
