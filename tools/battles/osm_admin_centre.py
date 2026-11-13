"""OSM 行政區 relation 的 admin_centre／label 成員節點查詢（唯讀 GET OSM API 0.6，每次間隔 1.2 秒）。
用途：Nominatim 對城市只回行政區 relation 時，取該 relation 標為 admin_centre 或 label 的 place 節點當城鎮中心（不用行政區形心）。
用法：python3 -I tools/battles/osm_admin_centre.py <battle> 名稱=relationId [...]
寫  data/seed/battles/<battle>/osm-places.json 的 adminCentre{名稱:{relation, role, node:{id, lat, lon, place, name}}}（已查者不重查）
"""
import json, sys, time, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UA = {"User-Agent": "WorldLine-research/0.1"}


def get(url):
    time.sleep(1.2)
    return ET.fromstring(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read())


def main():
    battle = sys.argv[1]
    p = REPO / "data/seed/battles" / battle / "osm-places.json"
    d = json.loads(p.read_text())
    ac = d.setdefault("adminCentre", {})
    for a in sys.argv[2:]:
        k, rid = a.split("=", 1)
        if k in ac:
            continue
        rel = get(f"https://api.openstreetmap.org/api/0.6/relation/{rid}")
        mem = [(m.get("role"), m.get("ref")) for m in rel.iter("member") if m.get("type") == "node" and m.get("role") in ("admin_centre", "label")]
        rec = {"relation": int(rid), "role": None, "node": None}
        for role in ("admin_centre", "label"):
            hit = [ref for r, ref in mem if r == role]
            if hit:
                n = get(f"https://api.openstreetmap.org/api/0.6/node/{hit[0]}").find("node")
                tags = {t.get("k"): t.get("v") for t in n.iter("tag")}
                rec.update(role=role, node={"id": int(hit[0]), "lat": float(n.get("lat")), "lon": float(n.get("lon")), "place": tags.get("place"), "name": tags.get("name")})
                break
        ac[k] = rec
        print(k, rec)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
