"""OSM Nominatim 地名查詢（由 .dev/battle/poland/build/osm.py 一般化）。
用法：python3 -I tools/battles/osm_lookup.py <battle> [名稱=查詢字串 ...]
讀寫 data/seed/battles/<battle>/osm-places.json：queries 為待查清單；results 已查過的不重查（保留舊結果）；
命令列可追加新地名。每次請求間隔 1.2 秒，帶 User-Agent。results 每筆含 type/id/lat/lon。
"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main():
    battle = sys.argv[1]
    p = REPO / "data/seed/battles" / battle / "osm-places.json"
    d = json.loads(p.read_text()) if p.exists() else {"queries": {}, "results": {}, "pick": {}}
    for a in sys.argv[2:]:
        k, q = a.split("=", 1); d["queries"][k] = q
    new = 0
    for k, q in d["queries"].items():
        if k in d["results"]:
            continue
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"format": "json", "limit": 3, "q": q})
        r = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "WorldLine-research/0.1"}), timeout=30).read())
        d["results"][k] = [{"type": x["osm_type"], "id": int(x["osm_id"]), "lat": float(x["lat"]), "lon": float(x["lon"]),
                            "name": x["display_name"][:80], "class": x.get("class"), "t": x.get("type")} for x in r]
        new += 1; time.sleep(1.2)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
    print(f"新查 {new} 筆；共 {len(d['results'])} 筆")


if __name__ == "__main__":
    main()
