"""R8 當年疆界參照清單（共用工具，由 dunkirk_1940/tools/build_r8_manifest.py 一般化）：只記主專案主權資料的參照，不複製、不改幾何、不手描。

做法：對開發 API 唯讀 GET /api/v1/sovereignty?date=D，D 從 window 起日逐日到止日；只看與戰區框相交的紀錄。
第一天記完整切片，之後只在「紀錄組合有變」的日期加切片。
設定：data/seed/battles/<battle>/battle.config.json 的 "r8"：{"box": [西,南,東,北], "window": [起,止], "focusRegimes": [...], "decision": "..."}
輸出 data/seed/battles/<battle>/r8-borders.manifest.json。
用法：python3 -I tools/battles/build_r8.py <battle> [--api http://127.0.0.1:5052]
"""
import datetime, json, sys, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
API = sys.argv[sys.argv.index("--api") + 1] if "--api" in sys.argv else "http://127.0.0.1:5052"
BOX = None
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
                     "geometryLicense": g.get("geometryLicense"), "sourceTitle": g.get("sourceTitle"), "focus": None})
    return sorted(rows, key=lambda r: r["regimeSlug"])


def main():
    global BOX
    battle = sys.argv[1]; D = REPO / "data" / "seed" / "battles" / battle
    C = json.loads((D / "battle.config.json").read_text())["r8"]
    BOX = tuple(C["box"]); FOCUS = set(C["focusRegimes"]); OUT = D / "r8-borders.manifest.json"
    d0, d1 = (datetime.date.fromisoformat(x) for x in C["window"])
    slices, prev, d = [], None, d0
    while d <= d1:
        rows = day(d.isoformat()); ids = {r["recordId"] for r in rows}
        if prev is None:
            slices.append({"date": d.isoformat(), "kind": "full", "records": rows})
        elif ids != prev[0]:
            slices.append({"date": d.isoformat(), "kind": "change", "added": [r for r in rows if r["recordId"] not in prev[0]],
                           "removed": [r for r in prev[1] if r["recordId"] not in ids]})
        prev = (ids, rows); d += datetime.timedelta(days=1)
    for s in slices:
        for r in s.get("records", []) + s.get("added", []) + s.get("removed", []): r["focus"] = r["regimeSlug"] in FOCUS
    focus_missing = sorted(FOCUS - {r["regimeSlug"] for r in slices[0]["records"]})
    OUT.write_text(json.dumps({"schema": f"{battle}-data/0.1 r8", "decision": C["decision"], "tool": "tools/battles/build_r8.py",
                               "fetchedFrom": f"{API}/api/v1/sovereignty（唯讀 GET，5442 開發庫）", "fetchedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                               "theatreBox": BOX, "window": [d0.isoformat(), d1.isoformat()], "focusRegimes": sorted(FOCUS), "focusMissingOnFirstDay": focus_missing,
                               "changeDates": [s["date"] for s in slices[1:]], "slices": slices}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("切片：", [(s["date"], s["kind"], len(s.get("records") or s.get("added") or []), len(s.get("removed") or [])) for s in slices], "缺：", focus_missing)


if __name__ == "__main__":
    main()
