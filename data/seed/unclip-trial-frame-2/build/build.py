"""補回被「歐洲、北非、近東試驗框」box(-20,15,60,72) 切掉的幾何（撤回再新增；做法同 ww2/unclip-su-tr）。
對象：丹麥王國（1908-01-01～1944-06-17，8 筆）、冰島王國、冰島共和國、法屬茅利塔尼亞（2 筆）、鄂圖曼帝國（1908-01-01～1918-10-30，6 筆）。
做法：同一固定版本 OHM 關係（版本號逐筆核對），用全球框重組＋Natural Earth 10m 陸地裁切，只取「試驗框外的部分」併回既有幾何；
框內幾何原封不動。框外部分簡化到約 2 公里（0.02 度）、略去小於 1e-3 平方度的小島。與同期其他政權的既有紀錄重疊處扣除（保留既有紀錄）；
丹麥在 1918-12-01 冰島成為獨立王國之後，框外部分另扣掉冰島。
用法：python build.py <targets.jsonl> <others.jsonl> <OHM raw 目錄> <ne_10m_land.geojson>
  targets／others 是唯讀 SQL 匯出（見 README）；raw 檔是 overpass「out meta geom」的回應（r<關係編號>.json）。
輸出：../unclip-trial-frame-2-derived.geojson、records.json。不連資料庫。
"""
import json, os, sys, collections
from shapely.geometry import LineString, Polygon, MultiPolygon, box, shape, mapping
from shapely.ops import polygonize, unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
TARGETS, OTHERS, RAW, NE = sys.argv[1:5]
FRAME = box(-20, 15, 60, 72); WORLD = box(-180, -60, 180, 85)
ICELAND_REL = 2801981; ICELAND_FROM = '1918-12-01'
def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    if isinstance(g, MultiPolygon): return list(g.geoms)
    return [p for x in getattr(g, 'geoms', []) for p in polys(x)]
def mp(g, minarea=1e-6): return MultiPolygon([p for p in polys(make_valid(g)) if p.area > minarea])
land = unary_union([make_valid(shape(f['geometry'])) for f in json.load(open(NE))['features']])
def load(rid):
    x = json.load(open(f'{RAW}/r{rid}.json')); rel = [e for e in x['elements'] if e['type'] == 'relation'][0]
    fetched = open(f'{RAW}/r{rid}.json.fetched').read().strip()
    return x, rel, fetched
def full(x, rel):
    outer, inner = [], []
    for m in rel['members']:
        if m['type'] != 'way' or 'geometry' not in m: continue
        c = [(p['lon'], p['lat']) for p in m['geometry'] if p]
        if len(c) < 2: continue
        (inner if m['role'] == 'inner' else outer if m['role'] in ('outer', '') else []).append(LineString(c))
    o = unary_union(list(polygonize(unary_union(outer)))) if outer else Polygon()
    i = unary_union(list(polygonize(unary_union(inner)))) if inner else Polygon()
    g = make_valid(make_valid(o.difference(i)).intersection(WORLD).intersection(land))
    return mp(set_precision(make_valid(g.simplify(0.0005, preserve_topology=True)), 1e-4))
def out_way_license(x, rel):
    tags = {e['id']: e.get('tags', {}) for e in x['elements'] if e['type'] == 'way'}; c = collections.Counter()
    for m in rel['members']:
        if m['type'] != 'way' or 'geometry' not in m: continue
        c_ = [(p['lon'], p['lat']) for p in m['geometry'] if p]
        if len(c_) < 2 or FRAME.contains(LineString(c_)): continue
        t = tags.get(m['ref'], {}); lic = (t.get('license') or t.get('source:license') or '').strip()
        c[lic or 'untagged(OHM CC0)'] += 1
    return dict(c)
rows = [json.loads(l) for l in open(TARGETS)]
others = [(o['slug'], o['lo'], o['hi'] or '9999-12-31', make_valid(shape(o['geom']))) for o in map(json.loads, open(OTHERS)) if o.get('geom')]
built, lic, vers = {}, {}, {}
for rid in sorted({r['ohm_relation_id'] for r in rows} | {ICELAND_REL}):
    x, rel, fetched = load(rid); built[rid] = full(x, rel); lic[rid] = out_way_license(x, rel); vers[rid] = (rel['version'], fetched)
    print(rid, 'v', rel['version'], 'outside-ways', lic[rid], flush=True)
iceland = built[ICELAND_REL]
res, bad = [], 0
for r in rows:
    rid = r['ohm_relation_id']
    if vers[rid][0] != r['ohm_version']: sys.exit(f"{r['slug']} {r['lo']}：raw 檔是 v{vers[rid][0]}，紀錄是 v{r['ohm_version']}，版本不同，不處理")
    old = make_valid(shape(r['geom'])); a, b = r['lo'], r['hi'] or '9999-12-31'
    outside = mp(mp(built[rid].simplify(0.02, preserve_topology=True), 1e-3).difference(FRAME), 1e-6)
    cut = []
    if r['slug'] == 'kingdom-of-denmark' and a >= ICELAND_FROM:
        x = outside.intersection(iceland.buffer(0.02)).area
        if x > 1e-6: cut.append({'slug': 'kingdom-of-iceland／republic-of-iceland', 'area_deg2': round(x, 4)}); outside = mp(outside.difference(iceland.buffer(0.02)))
    for slug, s, e, og in others:
        if s < b and a < e:
            x = outside.intersection(og).area
            if x > 1e-6: cut.append({'slug': slug, 'area_deg2': round(x, 4)}); outside = mp(outside.difference(og))
    for slug, s, e, og in others:
        if s < b and a < e and outside.intersection(og).area > 1e-4: print('OVERLAP', r['slug'], a, b, slug); bad += 1
    new = mp(set_precision(make_valid(unary_union([old, outside])), 1e-4), 1e-7)
    inside_diff = new.intersection(FRAME).symmetric_difference(old.intersection(FRAME)).area
    res.append({'row': {k: v for k, v in r.items() if k != 'geom'}, 'outside_area': round(outside.area, 3), 'old_area': round(old.area, 3), 'new_area': round(new.area, 3),
                'inside_change': round(inside_diff, 6), 'bounds': [round(v, 2) for v in new.bounds], 'geom': mapping(new), 'cut': cut, 'outside_license': lic[rid], 'raw_fetched': vers[rid][1]})
    print(r['slug'], a, r['hi'], 'rel', rid, 'old', round(old.area, 2), '+out', round(outside.area, 2), 'inside_change', round(inside_diff, 6), [round(v, 2) for v in new.bounds],
          'cut', [(c['slug'][:24], c['area_deg2']) for c in cut if c['area_deg2'] >= 0.001])
print('overlaps', bad)
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': 'U_' + x['row']['id'], 'properties': {}, 'geometry': x['geom']} for x in res]},
          open(os.path.join(ROOT, 'unclip-trial-frame-2-derived.geojson'), 'w'), separators=(',', ':'))
json.dump([{k: v for k, v in x.items() if k != 'geom'} for x in res], open(os.path.join(HERE, 'records.json'), 'w'), ensure_ascii=False, indent=1, default=str)
