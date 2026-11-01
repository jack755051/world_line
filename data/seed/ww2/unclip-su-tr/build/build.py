"""蘇聯、土耳其國界補完整（撤回再新增）：既有紀錄是歐陸試驗框（西經 12～東經 42、北緯 34～72）裁切後的幾何，
東經 42 度以東（蘇聯亞洲部分、高加索東部、西伯利亞、中亞；土耳其安納托利亞東部）被切掉。
做法：同一固定版本 OHM 關係（raw 檔即當時抓取的那一版，版本號逐筆核對），用全球框重組＋ Natural Earth 10m 陸地裁切，
取「框外部分」併回既有幾何（框內部分原封不動，含已扣掉的佔領區）。
輸入：/tmp/sutr.txt（唯讀 SQL 匯出既有紀錄）、/tmp/others.txt（其他政權框外部分，用於重疊檢查）、OHM raw 檔。
"""
import json, glob, os, sys, collections, re
import shapefile
from shapely.geometry import LineString, Polygon, MultiPolygon, box, shape, mapping
from shapely.ops import polygonize, unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
EU = box(-12, 34, 42, 72)
WORLD = box(-180, -60, 180, 85)
RAWDIRS = ['/workspace/wl/ohm', '/workspace/wl/ohm1942', '/workspace/wl/ohm1942b', '/workspace/wl/ohm4145', '/workspace/wl/ohm4345s']
sf = shapefile.Reader('/workspace/wl/ohmasia/ne/ne_10m_land.shp')
land = None
def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    if isinstance(g, MultiPolygon): return list(g.geoms)
    return [p for x in getattr(g, 'geoms', []) for p in polys(x)]
def mp(g, minarea=1e-6): return MultiPolygon([p for p in polys(make_valid(g)) if p.area > minarea])
def raw(rid, ver):
    for d in RAWDIRS:
        fn = f'{d}/raw/r{rid}.json'
        if os.path.exists(fn):
            x = json.load(open(fn)); rel = [e for e in x['elements'] if e['type'] == 'relation'][0]
            if rel['version'] == ver: return x, rel, fn
    raise SystemExit(f'找不到 relation/{rid} v{ver} 的 raw 檔')
def full(x, rel, land):
    outer, inner = [], []
    for m in rel['members']:
        if m['type'] != 'way' or 'geometry' not in m: continue
        c = [(p['lon'], p['lat']) for p in m['geometry'] if p]
        if len(c) < 2: continue
        (inner if m['role'] == 'inner' else outer if m['role'] in ('outer', '') else []).append(LineString(c))
    o = unary_union(list(polygonize(unary_union(outer)))) if outer else Polygon()
    i = unary_union(list(polygonize(unary_union(inner)))) if inner else Polygon()
    g = make_valid(o.difference(i))
    g = make_valid(g.intersection(WORLD).intersection(land))
    g = make_valid(g.simplify(0.0005, preserve_topology=True))
    return mp(set_precision(g, 1e-4))
def out_way_license(x, rel):
    tags = {e['id']: e.get('tags', {}) for e in x['elements'] if e['type'] == 'way'}
    c = collections.Counter()
    for m in rel['members']:
        if m['type'] != 'way' or 'geometry' not in m: continue
        c_ = [(p['lon'], p['lat']) for p in m['geometry'] if p]
        if len(c_) < 2 or EU.contains(LineString(c_)): continue
        t = tags.get(m['ref'], {}); lic = (t.get('license') or t.get('source:license') or '').strip()
        c[lic or 'untagged(OHM CC0)'] += 1
    return dict(c)

rows = []
for line in open('/tmp/sutr.txt'):
    p = line.rstrip('\n').split('|', 1)
    if len(p) < 2 or not p[0].startswith('{'): continue
    rows.append((json.loads(p[0]), make_valid(shape(json.loads(p[1])))))
need = {(r['ohm_relation_id'], r['ohm_version']) for r, _ in rows}
bb = box(-180, -60, 180, 85)
land = unary_union([make_valid(shape(s.__geo_interface__)).intersection(bb) for s in sf.shapes() if box(*s.bbox).intersects(bb)])
built, lic = {}, {}
for rid, ver in sorted(need):
    x, rel, fn = raw(rid, ver)
    built[rid] = full(x, rel, land); lic[rid] = out_way_license(x, rel)
    print(rid, ver, fn, 'outside-ways', lic[rid], flush=True)
# 其他政權的框外部分（重疊檢查）
others = []
if os.path.exists('/tmp/others.txt'):
    for line in open('/tmp/others.txt'):
        p = line.rstrip('\n').split('|', 4)
        if len(p) < 5 or len(p[4]) < 20: continue
        others.append((p[1], p[2], p[3], make_valid(shape(json.loads(p[4])))))
res, bad = [], 0
for r, g in rows:
    # 框外部分只用於世界縮放：先簡化到約 2 km（0.02 度）、去掉小於 1e-3 平方度的小島，再沿東經 42 度等框線切開（接縫為直線，不留縫）
    outside = mp(mp(built[r['ohm_relation_id']].simplify(0.02, preserve_topology=True), 1e-3).difference(EU), 1e-6)
    a, b = r['valid_period'][1:11], r['valid_period'][12:22]
    # 與其他政權（亞洲第一批）同期重疊的邊界小島（OHM 兩關係不一致，如黑龍江、烏蘇里江江中島）：扣掉，保留既有紀錄
    cut = []
    for slug, s, e, og in others:
        if s < b and a < e and outside.intersection(og).area > 1e-6:
            cut.append({'slug': slug, 'area_deg2': round(outside.intersection(og).area, 4)}); outside = mp(outside.difference(og))
    for slug, s, e, og in others:
        if s < b and a < e:
            x = outside.intersection(og).area
            if x > 1e-4: print('OVERLAP', r['id'], a, b, slug, s, e, round(x, 4)); bad += 1
    new = mp(set_precision(make_valid(unary_union([g, outside])), 1e-4), 1e-7)
    inside_diff = new.intersection(EU).symmetric_difference(g).area
    res.append({'row': r, 'outside_area': round(outside.area, 3), 'old_area': round(g.area, 3), 'new_area': round(new.area, 3), 'inside_change': round(inside_diff, 6),
                'bounds': [round(v, 2) for v in new.bounds], 'geom': mapping(new), 'cut': cut, 'outside_license': lic[r['ohm_relation_id']]})
    print(r['id'], a, b, r['ohm_relation_id'], 'old', round(g.area, 2), '+out', round(outside.area, 2), 'inside_change', round(inside_diff, 6), [round(v, 2) for v in new.bounds])
print('overlaps', bad)
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': 'U_' + x['row']['id'], 'properties': {}, 'geometry': x['geom']} for x in res]},
          open(os.path.join(ROOT, 'unclip-su-tr-derived.geojson'), 'w'), separators=(',', ':'))
json.dump([{k: v for k, v in x.items() if k != 'geom'} for x in res], open(os.path.join(HERE, 'records.json'), 'w'), ensure_ascii=False, indent=1, default=str)
