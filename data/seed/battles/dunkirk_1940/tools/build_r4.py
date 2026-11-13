"""R4 前線建置：讀 Ellis 態勢圖 <mapKey>.json（georef_ellis.py 輸出），只收 threshold.passes 為 true 的圖，產出 r4-fronts.json。
用法：python3 -I tools/build_r4.py（從 dunkirk_1940 目錄或任意處皆可；可重跑）
門檻：留一 95 百分位 ≤ 2 km（主管 2026-11-13 12:05）。usma-13-4jun 未通過，列入 excludedMaps。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIG = ROOT / "digitized"
MAPS = ["ellis-sm-26may", "ellis-sm-27may", "ellis-sm-withdrawal", "ellis-sm-28may", "ellis-sm-29may", "ellis-sm-30may", "ellis-sm-1jun", "usma-13-4jun"]
LON, LAT = (1.5, 3.6), (50.4, 51.4)
# 主期 5/26–6/4；沒有可用前線的日期在 gapsByDate 說明
MAIN_DATES = ["1940-05-26", "1940-05-27", "1940-05-28", "1940-05-29", "1940-05-30", "1940-05-31", "1940-06-01", "1940-06-02", "1940-06-03", "1940-06-04"]


def main():
    fronts, excluded, noLine = [], [], []
    for mk in MAPS:
        p = DIG / f"{mk}.json"
        if not p.exists():
            continue
        m = json.loads(p.read_text())
        th = m["threshold"]
        if not th["passes"]:
            excluded.append({"mapKey": mk, "loo_p95_km": th["loo_p95_km"], "reason": "留一 95 百分位超過 2 km 門檻，僅供參考，不取前線頂點"})
            continue
        rd = json.loads((DIG / f"{mk}.readings.json").read_text())
        src = m["source"]
        if not m.get("lines"):
            noLine.append({"mapKey": mk, "mapDate": m["mapDate"], "reason": rd.get("linesNote", "圖上無前線可讀")})
            continue
        if all(l["lineKind"] == "boundary" for l in m["lines"]):  # 只有界線、沒有前線
            noLine.append({"mapKey": mk, "mapDate": m["mapDate"], "reason": m["lines"][0].get("readNote", "")})
        g = m["georef"]
        for ln in m["lines"]:
            date = ln.get("date", m["mapDate"])
            fronts.append({
                "date": date,
                "dateNote": rd.get("dateNote", ""),
                "lineKey": ln["lineKey"], "lineKind": ln["lineKind"], "side": ln["side"], "label": ln["label"],
                "vertices": [{"lonlat": v["lonlat"], "px": v["px"], "nearPlace": v.get("nearPlace")} for v in ln["vertices"]],
                "basis": "map-digitized", "estimate": "推估",
                "mapRef": {"mapKey": mk, "citation": src["citation"], "mapDate": m["mapDate"], "url": src["url"], "grade": src["grade"]},
                "method": "georef_ellis.py 二次多項式",
                "georef": {"control_points": g["control_points"], "loo_median_km": g["loo_median_km"], "loo_p95_km": g["loo_p95_km"]},
                "precision_m": m["precision_m"],
                "precisionNote": m["precisionNote"] + "；前線頂點為目視讀圖（約 ±3–6 px，約 1.5–3 km），未含線寬",
                "readNote": ln.get("readNote", ""),
            })
    have = {f["date"] for f in fronts if f["lineKind"] != "boundary"}
    gaps = []
    for d in MAIN_DATES:
        if d in have:
            continue
        nl = [n for n in noLine if n["mapDate"] == d]
        if nl:
            why = "有通過門檻的圖，但圖上未畫出前線／周界：" + nl[0]["reason"]
        elif d in ("1940-05-31",):
            why = "Ellis 7 張態勢圖無 31 May 一張"
        else:
            why = "沒有通過門檻的態勢圖（usma-13-4jun 未通過，僅供參考）"
        gaps.append({"date": d, "reason": why})
    out = {"schema": "dunkirk-data/0.1 r4", "rule": "只取留一 95 百分位 ≤ 2 km 的圖（主管 2026-11-13 12:05）",
           "fronts": fronts, "excludedMaps": excluded, "gapsByDate": gaps}
    (ROOT / "r4-fronts.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    bad = 0
    for f in fronts:
        n = len(f["vertices"])
        oob = [v for v in f["vertices"] if not (LON[0] <= v["lonlat"][0] <= LON[1] and LAT[0] <= v["lonlat"][1] <= LAT[1])]
        if n < 3 or oob:
            bad += 1
            print("CHECK 失敗", f["lineKey"], n, oob)
    per = {}
    for f in fronts:
        k = f["mapRef"]["mapKey"]; a = per.setdefault(k, [0, 0]); a[0] += 1; a[1] += len(f["vertices"])
    print(f"fronts {len(fronts)} 條；各圖（線,頂點）{per}；排除 {[e['mapKey'] for e in excluded]}；缺口 {[g['date'] for g in gaps]}；自檢失敗 {bad}")


if __name__ == "__main__":
    main()
