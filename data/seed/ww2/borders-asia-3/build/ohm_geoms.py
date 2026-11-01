"""OHM admin_level=2／3 關係（亞洲第三批，1937–1945） → 組多邊形 → 世界框裁切 → Natural Earth 10m 陸地裁切 → GeoJSON＋釘選清單＋QA。
輸入：raw/r<id>.json（Overpass `relation(id);out meta geom;way(r);out tags;`）＋ raw/r<id>.json.fetched（UTC 抓取時間）。
"""
import json, glob, collections, re, datetime, sys
import shapefile
from shapely.geometry import LineString, Polygon, MultiPolygon, box, shape, mapping
from shapely.ops import polygonize, unary_union
from shapely.validation import make_valid
from shapely import set_precision
FRAME = box(30, -50, 180, 75)   # 亞洲第三批：南亞、阿拉伯半島、婆羅洲、帝汶、新幾內亞與澳洲（整片，不在 15°S 切開）
SIMPLIFY = 0.0005              # 約 50 m
PRECISION = 1e-4               # 約 10 m
sf = shapefile.Reader('ne/ne_10m_land.shp')
land = unary_union([make_valid(shape(s.__geo_interface__)).intersection(FRAME) for s in sf.shapes() if box(*s.bbox).intersects(FRAME)])

def attribution_key(t):
    lic = (t.get('license') or t.get('source:license') or '').strip()
    src = (t.get('source', '') + ' ' + t.get('source:geometry', '') + ' ' + t.get('source:url', '')).lower()
    if not lic: return None
    if lic.upper().startswith('CC0'): return 'cc0'
    if 'cnig' in src: return 'cnig'
    if 'eprostor.gov.si' in src or 'slovenia' in src: return 'gurs'
    if 'kartverket' in src or 'geonorge' in src: return 'kartverket'
    if 'humdata.org' in src: return 'hdx_ukr'
    return 'cc_by_unknown'
ATTR = {
    'cnig': '© Instituto Geográfico Nacional de España（CNIG，Líneas límite municipales），CC BY 4.0',
    'gurs': '© Geodetska uprava Republike Slovenije（GURS），CC BY 4.0',
    'kartverket': '© Kartverket（挪威測繪局，Administrative enheter），CC BY 4.0',
    'hdx_ukr': 'OCHA／HDX COD-AB Ukraine（OHM 線段標示 CC BY 4.0）',
    'cc_by_unknown': 'OHM 線段標示 CC BY 4.0、未註明原始來源（待查）',
}
def osm_derived(t):
    s = (t.get('source', '') + ' ' + t.get('note', '')).lower()
    return 'openstreetmap' in s or 'osm contributor' in s or re.search(r'\bosm\b', s) is not None or 'cadastre-dgi-fr' in s

def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    if isinstance(g, MultiPolygon): return list(g.geoms)
    return [p for x in getattr(g, 'geoms', []) for p in polys(x)]

out, man, geoms = [], [], {}
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
    o = unary_union(list(polygonize(unary_union(outer)))) if outer else Polygon()
    i = unary_union(list(polygonize(unary_union(inner)))) if inner else Polygon()
    g = make_valid(o.difference(i)) if not o.is_empty else o
    g = make_valid(g.intersection(FRAME).intersection(land))
    g = make_valid(g.simplify(SIMPLIFY, preserve_topology=True))
    g = make_valid(set_precision(g, PRECISION))
    ps = [p for p in polys(g) if p.area > 1e-6]
    t = rel['tags']
    keys = collections.Counter(attribution_key(wt) for wt in waytags.values())
    by_keys = sorted(k for k in keys if k and k != 'cc0')
    osm = sum(1 for wt in waytags.values() if osm_derived(wt))
    rec = dict(ohm_relation_id=rel['id'], ohm_version=rel['version'], ohm_timestamp=rel['timestamp'], ohm_changeset=rel.get('changeset'),
        fetched_at=fetched, osm_base=d['osm3s']['timestamp_osm_base'],
        name=t.get('name'), name_en=t.get('name:en'), start_date=t.get('start_date'), end_date=t.get('end_date'),
        admin_level=t.get('admin_level'), wikidata=t.get('wikidata'),
        relation_license=t.get('license'), relation_source=t.get('source'), fixme=t.get('fixme') or t.get('fixme:s'),
        member_way_count=len(waytags),
        member_way_license=dict((k or 'untagged(OHM CC0)', v) for k, v in keys.items()),
        osm_derived_way_count=osm,
        geometry_license='cc_by' if by_keys else 'cc0',
        attribution='; '.join(ATTR[k] for k in by_keys) or None,
        polygons=len(ps), clipped_area_deg2=round(sum(p.area for p in ps), 4))
    man.append(rec)
    if ps:
        mp = MultiPolygon(ps); geoms[rel['id']] = mp
        out.append({'type': 'Feature', 'id': rel['id'], 'properties': {k: rec[k] for k in ('ohm_relation_id', 'ohm_version', 'name', 'name_en', 'start_date', 'end_date')},
                    'geometry': mapping(mp)})
json.dump({'type': 'FeatureCollection', 'features': out}, open('ohm-asia3.geojson', 'w'), separators=(',', ':'))
json.dump(man, open('ohm-manifest3.json', 'w'), ensure_ascii=False, indent=1)
print('features', len(out))
