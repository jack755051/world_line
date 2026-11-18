"""R8 當年疆界：只記主專案主權資料的參照（不複製、不改幾何、不手描）。

做法：對 5052 開發 API 唯讀 GET /api/v1/sovereignty?date=D，D 從 1940-05-10 逐日到 1940-06-04；
只看與戰區框（西經 6°～東經 10°、北緯 47°～56°）相交的紀錄。第一天記完整切片，之後只在「紀錄組合有變」的日期加切片
（主管 2026-11-13 11:38 Q7：前段疆界只取 5/10，另加資料實際有變的日期）。
輸出 r8-borders.manifest.json。用法：python3 -I build_r8_manifest.py [--api http://127.0.0.1:5052]
"""
import datetime, json, sys, urllib.request
from pathlib import Path

API = sys.argv[sys.argv.index("--api") + 1] if "--api" in sys.argv else "http://127.0.0.1:5052"
BOX = (-6.0, 47.0, 10.0, 56.0)
OUT = Path(__file__).resolve().parent.parent / "r8-borders.manifest.json"
FOCUS = {"french-third-republic", "kingdom-of-belgium", "kingdom-of-the-netherlands", "grand-duchy-of-luxembourg", "deutsches-reich", "united-kingdom"}


def bbox(g):
    xs, ys = [], []
    def walk(c):
        if isinstance(c[0], (int, float)): xs.append(c[0]); ys.append(c[1])
        else:
            for k in c: walk(k)
    walk(g["coordinates"]); return min(xs), min(ys), max(xs), max(ys)


def hit(b):
    return not (b[2] < BOX[0] or b[0] > BOX[2] or b[3] < BOX[1] or b[1] > BOX[3])


def day(d):
    j = json.load(urllib.request.urlopen(f"{API}/api/v1/sovereignty?date={d}", timeout=60))["data"]["featureCollection"]["features"]
    rows = []
    for f in j:
        if not f.get("geometry") or not hit(bbox(f["geometry"])): continue
        p = f["properties"]; g = p.get("geometry") or {}
        rows.append({"regimeSlug": p["regimeSlug"], "recordId": p["recordId"], "layerStatus": p["layerStatus"], "validPeriod": p["validPeriod"],
                     "ohmRelationId": g.get("ohmRelationId"), "ohmVersion": g.get("ohmVersion"), "locator": g.get("locator"),
                     "geometryLicense": g.get("geometryLicense"), "sourceTitle": g.get("sourceTitle"), "focus": p["regimeSlug"] in FOCUS})
    return sorted(rows, key=lambda r: r["regimeSlug"])


def main():
    d0, d1 = datetime.date(1940, 5, 10), datetime.date(1940, 6, 4)
    slices, prev, d = [], None, d0
    while d <= d1:
        rows = day(d.isoformat()); ids = {r["recordId"] for r in rows}
        if prev is None:
            slices.append({"date": d.isoformat(), "kind": "full", "records": rows})
        elif ids != prev[0]:
            slices.append({"date": d.isoformat(), "kind": "change", "added": [r for r in rows if r["recordId"] not in prev[0]],
                           "removed": [r for r in prev[1] if r["recordId"] not in ids]})
        prev = (ids, rows); d += datetime.timedelta(days=1)
    focus_missing = sorted(FOCUS - {r["regimeSlug"] for r in slices[0]["records"]})
    OUT.write_text(json.dumps({"schema": "dunkirk-data/0.1 r8", "decision": "主管 2026-11-13 11:38 Q7；R8 只用主專案主權資料（OpenHistoricalMap 來源），不手描",
                               "fetchedFrom": f"{API}/api/v1/sovereignty（唯讀 GET，5442 開發庫）", "fetchedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                               "theatreBox": BOX, "window": [d0.isoformat(), d1.isoformat()], "focusRegimes": sorted(FOCUS), "focusMissingOn0510": focus_missing,
                               "changeDates": [s["date"] for s in slices[1:]], "slices": slices}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("切片：", [(s["date"], s["kind"], len(s.get("records") or s.get("added") or []), len(s.get("removed") or [])) for s in slices], "缺：", focus_missing)


if __name__ == "__main__":
    main()
