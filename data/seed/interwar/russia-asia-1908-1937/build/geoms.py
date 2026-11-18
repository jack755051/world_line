"""OHM 固定版本關係 → 全球框重組 → Natural Earth 10m 陸地裁切 → 簡化 0.0005°、精度 1e-4°（與既有各批相同）。輸出 geoms.pkl。"""
import json, os, glob, pickle, collections, sys
import shapefile
from shapely.geometry import LineString, Polygon, MultiPolygon, box, shape
from shapely.ops import polygonize, unary_union
from shapely.validation import make_valid
from shapely import set_precision
WORLD = box(-180, -60, 180, 85)
DIRS = ['/workspace/ru/raw', '/workspace/wl/ww1c/raw', '/workspace/wl/ww1/raw', '/workspace/wl/interwar/a/raw', '/workspace/wl/interwar/b/raw',
        '/workspace/wl/ohm/raw', '/workspace/wl/ohmasia/raw', '/workspace/wl/asia3/raw', '/workspace/wl/nafrica/raw']
def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    if isinstance(g, MultiPolygon): return list(g.geoms)
    return [p for x in getattr(g, 'geoms', []) for p in polys(x)]
def mp(g, minarea=1e-6): return MultiPolygon([p for p in polys(make_valid(g)) if p.area > minarea])
def find(rid):
    for d in DIRS:
        fn = f'{d}/r{rid}.json'
        if os.path.exists(fn): return fn
    raise SystemExit(f'no raw {rid}')
_land = None
def land():
    global _land
    if _land is None:
        sf = shapefile.Reader('/workspace/wl/ohm/ne/ne_10m_land.shp')
        _land = unary_union([make_valid(shape(s.__geo_interface__)).intersection(WORLD) for s in sf.shapes() if box(*s.bbox).intersects(WORLD)])
    return _land
def build(rid):
    fn = find(rid); x = json.load(open(fn)); rel = [e for e in x['elements'] if e['type'] == 'relation'][0]
    outer, inner = [], []
    for m in rel['members']:
        if m['type'] != 'way' or 'geometry' not in m: continue
        c = [(p['lon'], p['lat']) for p in m['geometry'] if p]
        if len(c) < 2: continue
        (inner if m['role'] == 'inner' else outer if m['role'] in ('outer', '') else []).append(LineString(c))
    repair = None
    if outer and not list(polygonize(unary_union(outer))):
        ends = collections.Counter()
        for l in outer:
            for c in (l.coords[0], l.coords[-1]): ends[(round(c[0], 7), round(c[1], 7))] += 1
        odd = [e for e, c in ends.items() if c % 2]
        if len(odd) == 2 and LineString(odd).length < 0.02:
            outer.append(LineString(odd)); repair = f'gap {LineString(odd).length:.4f}'
    o = unary_union(list(polygonize(unary_union(outer)))) if outer else Polygon()
    i = unary_union(list(polygonize(unary_union(inner)))) if inner else Polygon()
    g = make_valid(o.difference(i))
    g = make_valid(g.intersection(WORLD).intersection(land()))
    g = make_valid(g.simplify(0.0005, preserve_topology=True))
    g = mp(set_precision(g, 1e-4))
    wt = {e['id']: e.get('tags', {}) for e in x['elements'] if e['type'] == 'way'}
    lic = collections.Counter()
    for t in wt.values():
        l = (t.get('license') or t.get('source:license') or '').strip(); lic[l or 'untagged(OHM CC0)'] += 1
    t = rel['tags']
    fetched = open(fn + '.fetched').read().strip() if os.path.exists(fn + '.fetched') else None
    meta = dict(id=rid, version=rel['version'], timestamp=rel['timestamp'], changeset=rel.get('changeset'), name=t.get('name'), name_en=t.get('name:en'),
                start=t.get('start_date'), end=t.get('end_date'), admin_level=t.get('admin_level'), wikidata=t.get('wikidata'), fetched=fetched,
                osm_base=x['osm3s']['timestamp_osm_base'], file=fn, memberWayLicense=dict(lic), relationSource=t.get('source'), fixme=t.get('fixme'), repair=repair)
    return g, meta
if __name__ == '__main__':
    out = pickle.load(open('geoms.pkl', 'rb')) if os.path.exists('geoms.pkl') else {}
    for rid in map(int, sys.argv[1:]):
        if rid in out: continue
        g, m = build(rid); out[rid] = (g, m)
        print(rid, 'v%d' % m['version'], m['name_en'] or m['name'], m['start'], m['end'], 'area', round(g.area, 2), [round(v, 1) for v in g.bounds], m['repair'], flush=True)
        pickle.dump(out, open('geoms.pkl', 'wb'))
