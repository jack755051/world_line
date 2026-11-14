#!/usr/bin/env python3
"""拉布拉多內陸（1927 年樞密院裁決以前）：加拿大與紐芬蘭兩方主張並存。產生幾何與請求檔；不連資料庫。
背景：匯入時（ohm-b1-north-america-1908-1945）兩國的 OHM 範圍在拉布拉多內陸重疊約 20 萬平方公里，當時兩邊都扣掉留白，待 Tai 決定。
      Tai 2026-11-14 決定：有爭議的照憲法 R6 記多筆主張並標爭議。
做法：爭議範圍＝紐芬蘭 OHM 關係的完整範圍扣掉資料庫裡紐芬蘭已有的部分（就是當初被扣掉的那一塊）。
      加拿大 3 筆、紐芬蘭 2 筆（1908-01-01～1927-03-11）各自加上爭議範圍後撤回重寫，其他欄位照舊；再用一筆主權爭議把兩方串起來。
用法：python build.py <targets.jsonl> <OHM raw 目錄> <ne_10m_land.geojson>   （需要 shapely；targets 是五筆紀錄的唯讀匯出）
"""
import json, os, sys, math
from shapely.geometry import LineString, Polygon, MultiPolygon, box, shape, mapping
from shapely.ops import polygonize, unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
TARGETS, RAW, NE = sys.argv[1:4]
def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    if isinstance(g, MultiPolygon): return list(g.geoms)
    return [p for x in getattr(g, 'geoms', []) for p in polys(x)]
def mp(g, minarea=1e-6): return MultiPolygon([p for p in polys(make_valid(g)) if p.area > minarea])
def km2(g): return sum(p.area * 12392 * math.cos(math.radians(p.centroid.y)) for p in polys(g))
land = unary_union([make_valid(shape(f['geometry'])) for f in json.load(open(NE))['features']]).intersection(box(-75, 44, -50, 64))
def full(rid, version):
    x = json.load(open(f'{RAW}/r{rid}.json')); rel = [e for e in x['elements'] if e['type'] == 'relation'][0]
    assert rel['version'] == version, f'relation/{rid} 線上是 v{rel["version"]}，紀錄是 v{version}'
    outer, inner = [], []
    for m in rel['members']:
        if m['type'] != 'way' or 'geometry' not in m: continue
        c = [(p['lon'], p['lat']) for p in m['geometry'] if p]
        if len(c) < 2: continue
        (inner if m['role'] == 'inner' else outer if m['role'] in ('outer', '') else []).append(LineString(c))
    o = unary_union(list(polygonize(unary_union(outer)))) if outer else Polygon()
    i = unary_union(list(polygonize(unary_union(inner)))) if inner else Polygon()
    return mp(set_precision(make_valid(make_valid(make_valid(o.difference(i)).intersection(land)).simplify(0.0005, preserve_topology=True)), 1e-4))
rows = [json.loads(l) for l in open(TARGETS)]
nf = [r for r in rows if r['slug'] == 'dominion-of-newfoundland']; ca = [r for r in rows if r['slug'] == 'canada']
assert len(nf) == 2 and len(ca) == 3
zones = {}
for r in nf:   # 每一筆紐芬蘭紀錄的期間各有一個爭議範圍
    z = mp(full(r['ohm_relation_id'], r['ohm_version']).difference(make_valid(shape(r['geom'])).buffer(0.0002)), 1e-4)
    zones[(r['lo'], r['hi'])] = z; print('zone', r['lo'], r['hi'], 'km2', round(km2(z)), [round(v, 2) for v in z.bounds], 'parts', len(z.geoms))
def zone_for(r):
    zs = [z for (a, b), z in zones.items() if a < r['hi'] and r['lo'] < b]
    assert len(zs) == 1, (r['slug'], r['lo'], r['hi'], len(zs)); return zs[0]
feats, out = [], []
for r in rows:
    old = make_valid(shape(r['geom'])); z = zone_for(r)
    overlap = km2(old.intersection(z))
    new = mp(set_precision(make_valid(unary_union([old, z])), 1e-4), 1e-7)
    feats.append({'type': 'Feature', 'id': 'L_' + r['id'], 'properties': {}, 'geometry': mapping(new)})
    out.append({'row': {k: v for k, v in r.items() if k != 'geom'}, 'old_km2': round(km2(old)), 'zone_km2': round(km2(z)), 'new_km2': round(km2(new)), 'zoneAlreadyInside_km2': round(overlap, 1)})
    print(r['slug'], r['lo'], r['hi'], 'old', round(km2(old)), '+zone', round(km2(z)), '→', round(km2(new)), 'zone already inside', round(overlap, 1))
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(ROOT, 'labrador-dispute-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(out, open(os.path.join(HERE, 'records.json'), 'w'), ensure_ascii=False, indent=1, default=str)
