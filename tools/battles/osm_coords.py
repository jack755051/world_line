"""以 OSM 物件 id 補座標（Nominatim /lookup，批次 ≤ 50，間隔 1.2 秒，帶 User-Agent；不用 curl -k）。
用法：python3 -I tools/battles/osm_coords.py <battle>
掃描 data/seed/battles/<battle>/ 下 r3/r5/r6 與 r4-text-vertices 的 place.osm／vertices[].osm，
把缺座標的 (type,id) 查回，寫入 osm-places.json 的 coords {"R123": {"lon","lat","name"}}（只新增，不覆蓋舊值）。
"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
P = {"relation": "R", "way": "W", "node": "N"}


def walk(o, out):
    if isinstance(o, dict):
        osm = o.get("osm")
        if isinstance(osm, dict) and osm.get("type") in P and osm.get("id"):
            out.add(P[osm["type"]] + str(osm["id"]))
        for v in o.values(): walk(v, out)
    elif isinstance(o, list):
        for v in o: walk(v, out)


def main():
    battle = sys.argv[1]
    D = REPO / "data/seed/battles" / battle
    op = D / "osm-places.json"; d = json.loads(op.read_text()) if op.exists() else {"note": "tools/battles/osm_coords.py 建立：OSM id → 座標", "coords": {}}
    coords = d.setdefault("coords", {})
    for k, v in d.get("withCoords", {}).items():
        coords.setdefault(P[v["type"]] + str(v["id"]), {"lon": v["lon"], "lat": v["lat"], "name": v.get("name", k)[:80]})
    want = set()
    for f in ["r3-unit-positions.json", "r5-engagements.json", "r6-site-control.json", "r4-text-vertices.json"]:
        if (D / f).exists(): walk(json.loads((D / f).read_text()), want)
    todo = sorted(want - set(coords))
    for i in range(0, len(todo), 50):
        url = "https://nominatim.openstreetmap.org/lookup?" + urllib.parse.urlencode({"format": "json", "osm_ids": ",".join(todo[i:i + 50])})
        r = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "WorldLine-research/0.1"}), timeout=60).read())
        for x in r:
            coords[P[x["osm_type"]] + str(x["osm_id"])] = {"lon": float(x["lon"]), "lat": float(x["lat"]), "name": x["display_name"][:80]}
        time.sleep(1.2)
    op.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
    print("want", len(want), "new", len(todo), "missing", sorted(want - set(coords)))


if __name__ == "__main__":
    main()
