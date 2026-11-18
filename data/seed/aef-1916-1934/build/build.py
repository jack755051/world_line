#!/usr/bin/env python3
"""產生 aef-1916-1934 的幾何與請求檔。不連資料庫（輸入是唯讀匯出檔）。
問題：法屬赤道非洲 1916-07-20～1934-06-30 那一筆只有加彭與中剛果（約 60 萬平方公里），查德與烏班基沙立約 175 萬平方公里在這 18 年沒有任何紀錄。
      原因是匯入當時 OHM relation/2839999 v12 的範圍不含這兩地；OHM 在 2026-11-05 改成 v13，已含整個法屬赤道非洲，並另立 relation/2969589（1931～1934-06-30，多了提貝斯提）。
做法：撤回原紀錄，用新版本重建成兩筆（1916-07-20～1931-01-01、1931-01-01～1934-06-30）。與同期其他政權既有紀錄重疊處扣除，保留既有紀錄。
用法：python build.py <old.json> <others.jsonl> <OHM raw 目錄> <ne_10m_land.geojson>   （需要 shapely）
  old.json：原紀錄的欄位；others.jsonl：同期鄰近的其他主權紀錄（唯讀 SQL 匯出）；raw：overpass「relation(ID);out meta geom;way(r);out tags;」的回應。
"""
import json, os, sys, math, collections
from shapely.geometry import LineString, Polygon, MultiPolygon, box, shape, mapping
from shapely.ops import polygonize, unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
OLD, OTHERS, RAW, NE = sys.argv[1:5]
PARTS = [('FEA_1916', 2839999, '1916-07-20', '1931-01-01'), ('FEA_1931', 2969589, '1931-01-01', '1934-06-30')]
def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    if isinstance(g, MultiPolygon): return list(g.geoms)
    return [p for x in getattr(g, 'geoms', []) for p in polys(x)]
def mp(g, minarea=1e-6): return MultiPolygon([p for p in polys(make_valid(g)) if p.area > minarea])
def km2(g): return sum(p.area * 12392 * math.cos(math.radians(p.centroid.y)) for p in polys(g))
land = unary_union([make_valid(shape(f['geometry'])) for f in json.load(open(NE))['features']]).intersection(box(0, -15, 40, 35))
def load(rid):
    x = json.load(open(f'{RAW}/r{rid}.json')); rel = [e for e in x['elements'] if e['type'] == 'relation'][0]
    tags = {e['id']: e.get('tags', {}) for e in x['elements'] if e['type'] == 'way'}; outer, inner, lic = [], [], collections.Counter()
    for m in rel['members']:
        if m['type'] != 'way' or 'geometry' not in m: continue
        c = [(p['lon'], p['lat']) for p in m['geometry'] if p]
        if len(c) < 2: continue
        (inner if m['role'] == 'inner' else outer if m['role'] in ('outer', '') else []).append(LineString(c))
        t = tags.get(m['ref'], {}); lic[(t.get('license') or t.get('source:license') or '').strip() or 'untagged(OHM CC0)'] += 1
    o = unary_union(list(polygonize(unary_union(outer)))) if outer else Polygon()
    i = unary_union(list(polygonize(unary_union(inner)))) if inner else Polygon()
    g = make_valid(make_valid(o.difference(i)).intersection(land))
    return rel, mp(set_precision(make_valid(g.simplify(0.0005, preserve_topology=True)), 1e-4)), dict(lic), open(f'{RAW}/r{rid}.json.fetched').read().strip()
old = json.load(open(OLD)); others = [json.loads(l) for l in open(OTHERS)]; others = [o for o in others if o['id'] != old['id']]
feats = []
def write(name, obj): json.dump(obj, open(os.path.join(ROOT, 'requests', name), 'w'), ensure_ascii=False, indent=1)
write('01-retract.json', {'_placeholder': 'RETRACTED_FEA_1916_1934', '_post': f"/api/v1/sovereignty-records/{old['id']}/retraction", '_meta': {'fix': True}, 'body': {
    'reason': '法屬赤道非洲 1916-07-20～1934-06-30：只有加彭與中剛果（約 60 萬平方公里），查德與烏班基沙立在這 18 年沒有任何紀錄。匯入時的 OHM relation/2839999 v12 不含這兩地，OHM 已於 2026-11-05 更正。'
              '改用新版本重建成兩筆（aef-1916-1934：撤回後重新新增）。'}})
for n, (ph, rid, a, b) in enumerate(PARTS, 2):
    rel, g, lic, fetched = load(rid); t = rel['tags']; cut = []
    for o in others:
        if o['lo'] < b and a < (o['hi'] or '9999'):
            og = make_valid(shape(o['geom'])); x = km2(g.intersection(og))
            if x > 0.5: cut.append({'slug': o['slug'], 'period': [o['lo'], o['hi']], 'km2': round(x, 1)}); g = mp(g.difference(og))
    g = mp(set_precision(make_valid(g), 1e-4), 1e-5)
    assert all(c['km2'] < 3000 for c in cut), cut
    assert set(lic) == {'untagged(OHM CC0)'}, lic
    feats.append({'type': 'Feature', 'id': ph, 'properties': {}, 'geometry': mapping(g)})
    print(ph, rid, 'v', rel['version'], a, b, 'km2', round(km2(g)), 'cut', [(c['slug'], c['km2']) for c in cut], lic)
    write(f'{n:02d}-sovereignty-{ph.lower()}.json', {'_placeholder': ph, '_post': '/api/v1/sovereignty-records', '_geometryFrom': ph, '_meta': {'replaces': old['id'], 'km2': round(km2(g))}, 'body': {
        'regimeId': old['regime_id'], 'geometry': None, 'validPeriod': {'start': a, 'end': b}, 'layerStatus': 'de_jure',
        'geometrySourceId': old['geometry_source_id'], 'geometryLocator': f"relation/{rid} v{rel['version']}", 'geometryLicense': 'cc0', 'attribution': None,
        'startEventId': None, 'endEventId': None, 'ohmRelationId': rid, 'ohmVersion': rel['version'], 'ohmFetchedAt': fetched, 'ohmStartRaw': t.get('start_date'), 'ohmEndRaw': t.get('end_date'),
        'provenance': {'decision': (old['provenance'] or {}).get('decision'), 'coastline': (old['provenance'] or {}).get('coastline'), 'ohmChangeset': rel.get('changeset'), 'ohmTimestamp': rel.get('timestamp'),
                       'ohmAdminLevel': t.get('admin_level'), 'memberWayLicense': lic, 'writtenKm2': round(km2(g), 1), 'subtractedOverlaps': cut,
                       'datePrecision': {'end' if b == '1931-01-01' else 'start': 'year'},
                       'fix': {'batch': 'aef-1916-1934', 'replaces': old['id'], 'replacedLocator': old['geometry_locator'], 'reason': 'OHM 於 2026-11-05 更正範圍（原版本不含查德與烏班基沙立）'}},
        'note': {'zh-Hant': '法屬赤道非洲（含加彭、中剛果、烏班基沙立、查德）。' + ('OHM 的結束日只寫「1931」，記為 1931-01-01；' if b == '1931-01-01' else 'OHM 的起始日只寫「1931」，記為 1931-01-01；這一筆比前一筆多了提貝斯提，') + '1931 年那次變動的確切日期與出處還沒有查。',
                 'en': 'French Equatorial Africa including Gabon, Middle Congo, Ubangi-Shari and Chad. The 1931 boundary change is dated only to the year in OHM.'}}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(ROOT, 'aef-1916-1934-derived.geojson'), 'w'))
