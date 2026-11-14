#!/usr/bin/env python3
"""補回被最早的歐陸試驗框 box(-12, 34, 42, 72) 切掉的法國紀錄：阿爾及利亞在北緯 34 度以南的部分。不連資料庫。
對象：法蘭西第三共和（1918-11-22～1940-06-22）、維琪法國、盟軍佔領下的法屬北非、法蘭西民族解放委員會（2 筆）、法蘭西共和國臨時政府（3 筆），共 8 筆。
做法同 unclip-trial-frame：框內幾何原封不動；框外部分取自 OHM 同一關係，Natural Earth 10m 陸地裁切、簡化到 0.02 度，與同期其他政權既有紀錄重疊處扣除，再併回。
**與先前批次不同的地方**：這四個關係在 2026-11-13 被 OHM 改過，線上版本比紀錄記的新兩版，舊版本取不回來。框外部分用的是新版本，並逐筆比對新版本在框內與原紀錄的差異（列在 records.json）。
用法：python build.py <targets.jsonl> <others.jsonl> <OHM raw 目錄> <ne_10m_land.geojson>   （需要 shapely）
"""
import json, os, sys, math, collections
from shapely.geometry import LineString, Polygon, MultiPolygon, box, shape, mapping
from shapely.ops import polygonize, unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
TARGETS, OTHERS, RAW, NE = sys.argv[1:5]
FRAME = box(-12, 34, 42, 72); AFRICA = box(-12, 15, 14, 34)   # 框外只取阿爾及利亞一帶，不碰其他地方
def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    if isinstance(g, MultiPolygon): return list(g.geoms)
    return [p for x in getattr(g, 'geoms', []) for p in polys(x)]
def mp(g, minarea=1e-6): return MultiPolygon([p for p in polys(make_valid(g)) if p.area > minarea])
def km2(g): return sum(p.area * 12392 * math.cos(math.radians(p.centroid.y)) for p in polys(g))
land = unary_union([make_valid(shape(f['geometry'])) for f in json.load(open(NE))['features']]).intersection(box(-20, 10, 45, 75))
built = {}
def load(rid):
    if rid in built: return built[rid]
    x = json.load(open(f'{RAW}/r{rid}.json')); rel = [e for e in x['elements'] if e['type'] == 'relation'][0]
    tags = {e['id']: e.get('tags', {}) for e in x['elements'] if e['type'] == 'way'}; outer, inner, lic = [], [], collections.Counter()
    for m in rel['members']:
        if m['type'] != 'way' or 'geometry' not in m: continue
        c = [(p['lon'], p['lat']) for p in m['geometry'] if p]
        if len(c) < 2: continue
        (inner if m['role'] == 'inner' else outer if m['role'] in ('outer', '') else []).append(LineString(c))
        if not FRAME.contains(LineString(c)) and AFRICA.intersects(LineString(c)):
            t = tags.get(m['ref'], {}); lic[(t.get('license') or t.get('source:license') or '').strip() or 'untagged(OHM CC0)'] += 1
    o = unary_union(list(polygonize(unary_union(outer)))) if outer else Polygon()
    i = unary_union(list(polygonize(unary_union(inner)))) if inner else Polygon()
    g = mp(set_precision(make_valid(make_valid(make_valid(o.difference(i)).intersection(land)).simplify(0.0005, preserve_topology=True)), 1e-4))
    built[rid] = (rel, g, dict(lic), open(f'{RAW}/r{rid}.json.fetched').read().strip()); return built[rid]
rows = [json.loads(l) for l in open(TARGETS)]; others = [json.loads(l) for l in open(OTHERS)]
for o in others: o['g'] = make_valid(shape(o['geom']))
res = []
for r in rows:
    rel, full, lic, fetched = load(r['ohm_relation_id']); old = make_valid(shape(r['geom'])); a, b = r['lo'], r['hi']
    outside = mp(mp(full.simplify(0.02, preserve_topology=True), 1e-3).intersection(AFRICA).difference(FRAME), 1e-6); cut = []
    for o in others:
        if o['lo'] < b and a < (o['hi'] or '9999'):
            x = km2(outside.intersection(o['g']))
            if x > 1: cut.append({'slug': o['slug'], 'period': [o['lo'], o['hi']], 'km2': round(x)}); outside = mp(outside.difference(o['g']))
    new = mp(set_precision(make_valid(unary_union([old, outside])), 1e-4), 1e-7)
    inside_change = km2(new.intersection(FRAME).symmetric_difference(old.intersection(FRAME)))
    algeria_n = box(-3, 34, 9, 38)   # 新舊版本在框內的差異只看阿爾及利亞北部（本土部分各筆扣過佔領區，不能直接比）
    ver_diff = km2(full.intersection(algeria_n).symmetric_difference(old.intersection(algeria_n)))
    res.append({'row': {k: v for k, v in r.items() if k != 'geom'}, 'rawVersion': rel['version'], 'rawTimestamp': rel['timestamp'], 'rawFetched': fetched,
                'old_km2': round(km2(old)), 'outside_km2': round(km2(outside)), 'new_km2': round(km2(new)), 'inside_change_km2': round(inside_change, 2),
                'northAlgeriaDiffVsNewVersion_km2': round(ver_diff, 1), 'cut': cut, 'outside_license': lic, 'geom': mapping(new)})
    print(r['slug'], a, b, f"rel {r['ohm_relation_id']} v{r['ohm_version']}→v{rel['version']}", 'old', round(km2(old)), '+out', round(km2(outside)), 'inside_change', round(inside_change, 2),
          'N-Algeria diff', round(ver_diff, 1), 'cut', [(c['slug'], c['km2']) for c in cut], lic)
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': 'U_' + x['row']['id'], 'properties': {}, 'geometry': x['geom']} for x in res]},
          open(os.path.join(ROOT, 'unclip-eu-frame-france-derived.geojson'), 'w'), separators=(',', ':'))
json.dump([{k: v for k, v in x.items() if k != 'geom'} for x in res], open(os.path.join(HERE, 'records.json'), 'w'), ensure_ascii=False, indent=1, default=str)
