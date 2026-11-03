"""OHM admin_level=2 關係（拉丁美洲 1908-01-01～1945-09-30） → 組多邊形 → 拉美框裁切 → Natural Earth 10m 陸地裁切 → GeoJSON＋釘選清單。
比照 data/seed/interwar/batch-a/build/build.py（同一套組圈、補缺口、簡化、精度與授權判讀）。
輸入：raw/r<id>.json（Overpass `relation(id);out meta geom;way(r);out tags;`）＋ raw/r<id>.json.fetched。"""
import json, glob, collections, re, os
import shapefile
from shapely.geometry import LineString, Polygon, MultiPolygon, box, shape, mapping
from shapely.ops import polygonize, unary_union
from shapely.validation import make_valid
from shapely import set_precision
os.chdir(os.path.dirname(os.path.abspath(__file__)))
FRAME = box(-120, -60, -30, 35)
SIMPLIFY, PRECISION = 0.0005, 1e-4
sf = shapefile.Reader('/workspace/wl/ohm/ne/ne_10m_land.shp')
land = unary_union([make_valid(shape(s.__geo_interface__)).intersection(FRAME) for s in sf.shapes() if box(*s.bbox).intersects(FRAME)])

def attribution_key(t):
    lic = (t.get('license') or t.get('source:license') or '').strip()
    if not lic: return None
    if lic.upper().replace('CCO', 'CC0').startswith('CC0'): return 'cc0'   # 線段標「CCO 4.0」（字母 O）視為 CC0 筆誤，記在清單
    src = (t.get('source', '') + ' ' + t.get('source:geometry', '') + ' ' + t.get('source:url', '')).lower()
    if 'humdata.org' in src: return 'hdx'
    return 'cc_by_unknown'
ATTR = {'hdx': 'OCHA／HDX COD-AB（data.humdata.org，OHM 線段標示 CC BY 4.0）', 'cc_by_unknown': 'OHM 線段標示 CC BY 4.0、未註明原始來源（待查）'}
def osm_derived(t):
    s = (t.get('source', '') + ' ' + t.get('note', '')).lower()
    return 'openstreetmap' in s or 'osm contributor' in s or re.search(r'\bosm\b', s) is not None
def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    if isinstance(g, MultiPolygon): return list(g.geoms)
    return [p for x in getattr(g, 'geoms', []) for p in polys(x)]

out, man = [], []
for fn in sorted(glob.glob('raw/r*.json')):
    d = json.load(open(fn)); fetched = open(fn + '.fetched').read().strip()
    rel = [x for x in d['elements'] if x['type'] == 'relation'][0]
    waytags = {x['id']: x.get('tags', {}) for x in d['elements'] if x['type'] == 'way'}
    outer, inner = [], []
    for m in rel['members']:
        if m['type'] != 'way' or 'geometry' not in m: continue
        coords = [(p['lon'], p['lat']) for p in m['geometry'] if p]
        if len(coords) < 2: continue
        (inner if m['role'] == 'inner' else outer if m['role'] in ('outer', '') else []).append(LineString(coords))
    repair = None
    if outer and not list(polygonize(unary_union(outer))):
        ends = collections.Counter()
        for l in outer:
            for c in (l.coords[0], l.coords[-1]): ends[(round(c[0], 7), round(c[1], 7))] += 1
        odd = [e for e, c in ends.items() if c % 2]
        if len(odd) == 2 and LineString(odd).length < 0.02:
            outer.append(LineString(odd)); repair = f'外框缺口 {LineString(odd).length:.4f}° 以直線接合：{odd[0]} – {odd[1]}'
    o = unary_union(list(polygonize(unary_union(outer)))) if outer else Polygon()
    i = unary_union(list(polygonize(unary_union(inner)))) if inner else Polygon()
    g = make_valid(o.difference(i)) if not o.is_empty else o
    raw_area = g.area
    g = make_valid(g.intersection(FRAME).intersection(land))
    g = make_valid(g.simplify(SIMPLIFY, preserve_topology=True))
    g = make_valid(set_precision(g, PRECISION))
    ps = [p for p in polys(g) if p.area > 1e-6]
    t = rel['tags']
    keys = collections.Counter(attribution_key(wt) for wt in waytags.values())
    by_keys = sorted(k for k in keys if k and k != 'cc0')
    rec = dict(ohm_relation_id=rel['id'], ohm_version=rel['version'], ohm_timestamp=rel['timestamp'], ohm_changeset=rel.get('changeset'),
        fetched_at=fetched, osm_base=d['osm3s']['timestamp_osm_base'], name=t.get('name'), official_name=t.get('official_name'), name_en=t.get('name:en'),
        start_date=t.get('start_date'), end_date=t.get('end_date'), admin_level=t.get('admin_level'), wikidata=t.get('wikidata'),
        relation_license=t.get('license'), relation_source=t.get('source') or t.get('source:url'), fixme=t.get('fixme'),
        date_sources={k: v for k, v in t.items() if k.startswith(('start_date:', 'end_date:'))},
        member_way_count=len(waytags), member_way_license=dict((k or 'untagged(OHM CC0)', v) for k, v in keys.items()),
        osm_derived_way_count=sum(1 for wt in waytags.values() if osm_derived(wt)),
        geometry_license='cc_by' if by_keys else 'cc0', attribution='; '.join(ATTR[k] for k in by_keys) or None,
        cco_typo_ways=sum(1 for wt in waytags.values() if (wt.get('license') or '').upper().startswith('CCO')), polygons=len(ps), raw_area_deg2=round(raw_area, 4),
        clipped_area_deg2=round(sum(p.area for p in ps), 4), repair=repair)
    man.append(rec)
    if ps:
        out.append({'type': 'Feature', 'id': rel['id'], 'properties': {k: rec[k] for k in ('ohm_relation_id', 'ohm_version', 'name', 'start_date', 'end_date')}, 'geometry': mapping(MultiPolygon(ps))})
json.dump({'type': 'FeatureCollection', 'features': out}, open('borders-ohm-latam.geojson', 'w'), separators=(',', ':'))
json.dump(man, open('ohm-manifest.json', 'w'), ensure_ascii=False, indent=1)
print('features', len(out), 'relations', len(man))
for r in man:
    if r['polygons'] == 0 or r['repair'] or r['geometry_license'] != 'cc0' or r['osm_derived_way_count'] or (r['raw_area_deg2'] and r['clipped_area_deg2'] < 0.5 * r['raw_area_deg2']):
        print('CHECK', r['ohm_relation_id'], r['name'], 'polys', r['polygons'], 'raw', r['raw_area_deg2'], 'clip', r['clipped_area_deg2'], r['repair'], r['geometry_license'], 'osm', r['osm_derived_way_count'])
