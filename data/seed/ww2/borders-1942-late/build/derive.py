"""1942 後期（1942-07-01～1942-12-31）主權圖層的衍生幾何。
輸入：borders-ohm-1942.geojson（build.py 產生；feature id＝OHM 關係 id，已裁歐陸框與 Natural Earth 陸地）。
規則（沿用 Tai 2026-10-31 決定 1「事實國界」與 1938–1940 批次做法：同一天不重疊）：
- 德意志國＝relation/2692712（OHM 已含總督府、比亞韋斯托克區、波希米亞—摩拉維亞保護國）。
- 東方總督轄區＝relation/2692529、烏克蘭總督轄區＝relation/2693267，皆為非主權（佔領行政區，斜線）。
- 蘇聯＝relation/2851156（1941 年國界）− 德意志國 − 兩個總督轄區 − 羅馬尼亞 1941-08-19 起的範圍（relation/2693255：
  比薩拉比亞、北布科維納、外涅斯特里亞；羅馬尼亞本身不在本批，該處留白）。
"""
import json, os
from shapely.geometry import shape, mapping, MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
g = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-1942.geojson')))['features']}
def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x, 'geoms', []) for p in polys(y)]
def clean(x):
    x = make_valid(set_precision(make_valid(x), 1e-4))
    return MultiPolygon([p for p in polys(x) if p.area > 1e-5])
DE, SU, RKO, RKU, RO = 2692712, 2851156, 2692529, 2693267, 2693255
out = {
    'FIX1942_DE': clean(g[DE]),
    'FIX1942_RKO': clean(g[RKO].difference(g[DE])),
    'FIX1942_RKU': clean(g[RKU].difference(g[DE]).difference(g[RKO])),
    'FIX1942_SU': clean(g[SU].difference(unary_union([g[DE], g[RKO], g[RKU], g[RO]]))),
}
ids = list(out)
for i in ids:
    for j in ids:
        if i < j:
            a = out[i].intersection(out[j]).area
            assert a < 1e-3, (i, j, a)
qa = {k: {'area_deg2': round(v.area, 3), 'polygons': len(v.geoms), 'bounds': [round(b, 2) for b in v.bounds]} for k, v in out.items()}
qa['removed_from_su'] = {'by_de': round(g[SU].intersection(g[DE]).area, 3), 'by_rk': round(g[SU].intersection(unary_union([g[RKO], g[RKU]])).area, 3),
                         'by_romania_1941': round(g[SU].difference(unary_union([g[DE], g[RKO], g[RKU]])).intersection(g[RO]).area, 3)}
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in out.items()]},
          open(os.path.join(ROOT, 'borders-1942-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(qa, open(os.path.join(ROOT, 'qa.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(qa, ensure_ascii=False))
