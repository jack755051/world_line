"""法、英政權與 1940 控制區（feature/ww2-fr-uk-regimes）：產生幾何與 requests/*.json。

幾何：
- 維希自由區：TRF-GIS 1940 外框，用 Ain 分界線切出南側（與 france-1940-07-15 v2 同一套算法），
  再扣掉與義大利接壤的 5 省（04、05、06、73、74）。義大利佔領區沒有合格來源（docs/research §4.3），
  扣掉的部分留「控制資料缺」（R9），不把義大利佔領的市鎮誤標為維希。
- 英國本土：Natural Earth 10m admin-0「United Kingdom」（GBR，公有領域），只當 auxiliary_geometry。
所有運算在 1e-5° 網格；檢查與法國那批既有控制區的交集面積 = 0。
用法（box）：~/.venvs/gis/bin/python make_fruk.py
"""
import json, os, shapefile, shapely
from shapely.geometry import shape, mapping, Point, LineString, MultiPolygon, Polygon
from shapely.ops import split
from shapely.ops import transform  # 與 make_zones_v2.py 相同（shapely 2.2 有 DeprecationWarning）
from pyproj import Transformer, Geod

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.dirname(HERE)
FR = os.path.join(SEED, '..', 'france-1940-07-15')
T = '/workspace/world-line-ww2/trace/'
G = 1e-5
union = lambda gs: shapely.union_all(gs, grid_size=G)
tr = Transformer.from_crs(2154, 4326, always_xy=True).transform
geod = Geod(ellps='WGS84')
km2 = lambda g: abs(geod.geometry_area_perimeter(g)[0]) / 1e6
polys = lambda g: list(g.geoms) if hasattr(g, 'geoms') else [g]
def mp(g):
    ps = [p for p in polys(g) if isinstance(p, Polygon) and p.area > 0]
    out = MultiPolygon(ps); assert out.is_valid; return out
def extend(coords, d=0.05):
    import math
    (x0, y0), (x1, y1) = coords[0], coords[1]; (xa, ya), (xb, yb) = coords[-2], coords[-1]
    n0 = math.hypot(x0 - x1, y0 - y1); n1 = math.hypot(xb - xa, yb - ya)
    return [(x0 + (x0 - x1) / n0 * d, y0 + (y0 - y1) / n0 * d)] + list(coords) + [(xb + (xb - xa) / n1 * d, yb + (yb - ya) / n1 * d)]

# 1) 自由區（同 make_zones_v2.py 第 1 步）
r = shapefile.Reader(T + 'trf-gis/DEPARTEMENTS_1940', encoding='utf-8')
dep = {}
for sr in r.iterShapeRecords():
    g = shapely.make_valid(transform(tr, shape(sr.shape.__geo_interface__)))
    dep[str(sr.record['dep_id'])] = (sr.record['dep_name'], shapely.set_precision(g, G))
france = union([g for _, g in dep.values()])
ain = json.load(open(T + 'ain-ligne-demarcation.geojson'))['features'][0]['geometry']
ain_line = LineString(extend(ain['coordinates'] if ain['type'] == 'LineString' else ain['coordinates'][0]))
free_parts = []
for p in polys(france):
    if p.intersects(ain_line):
        for q in polys(split(p, ain_line)):
            if q.contains(Point(3.43, 46.13)): free_parts.append(q)
    else:
        rp = p.representative_point()
        if rp.y < 43.8 and rp.x > 3.0: free_parts.append(p)   # Corse 等地中海島嶼
free = shapely.intersection(france, shapely.set_precision(union(free_parts), G), grid_size=G)

ALPINE = ['4', '5', '6', '73', '74']   # TRF dep_id 為整數字串
print('扣除省份：', [(i, dep[i][0]) for i in ALPINE])
alpine = union([dep[i][1] for i in ALPINE])
vichy = mp(shapely.difference(free, alpine, grid_size=G))
gap = mp(shapely.intersection(free, alpine, grid_size=G))

# 2) 與法國那批既有控制區（含待決的東北禁區）不重疊：先扣掉它們的幾何（請求檔座標四捨五入到 1e-5，邊界可能有 m² 級微小交集）
existing = []
for f in sorted(os.listdir(os.path.join(FR, 'requests'))):
    if '-control-' in f:
        existing.append((f, shape(json.load(open(os.path.join(FR, 'requests', f)))['body']['geometry'])))
before = km2(vichy)
vichy = mp(shapely.difference(vichy, union([g for _, g in existing]), grid_size=G))
print(f'  扣掉既有控制區後面積差 {before - km2(vichy):.4f} km2')

# 3) 英國本土（Natural Earth GBR）
ne = json.load(open(T + 'ne_10m_admin_0_countries.geojson'))
gbr = next(f for f in ne['features'] if f['properties']['ADM0_A3'] == 'GBR')
uk_all = mp(shapely.set_precision(shapely.make_valid(shape(gbr['geometry'])), G))
# Rockall（約 13.7°W）1955 年才由英國宣布併入（1972 Island of Rockall Act），1940 年不屬英國，排除
rockall = [p for p in uk_all.geoms if p.bounds[2] < -10]
print('排除 Rockall 等 10°W 以西的部分：', [tuple(round(b, 2) for b in p.bounds) for p in rockall])
uk = mp(MultiPolygon([p for p in uk_all.geoms if p.bounds[2] >= -10]))
minx, miny, maxx, maxy = uk.bounds
assert -9 < minx and maxx < 2.1 and 49.8 < miny and maxy < 61, uk.bounds   # 只含不列顛與北愛爾蘭，沒有海外領地
print('vichy parts', len(vichy.geoms), 'vertices', shapely.get_num_coordinates(vichy), 'km2', round(km2(vichy)))
print('gap(5 省) km2', round(km2(gap)), '；free 全部 km2', round(km2(free)))
print('uk parts', len(uk.geoms), 'vertices', shapely.get_num_coordinates(uk), 'km2', round(km2(uk)), 'bounds', [round(b, 2) for b in uk.bounds])

def rnd(g):
    return json.loads(json.dumps(mapping(g)), parse_float=lambda s: round(float(s), 5))
geo = {'vichy': rnd(vichy), 'uk': rnd(uk)}
# 四捨五入後再扣一次既有控制區（全部座標都在 1e-5 網格上）
geo['vichy'] = rnd(mp(shapely.difference(shape(geo['vichy']), union([shapely.set_precision(shapely.make_valid(g), G) for _, g in existing]), grid_size=G)))
# 用請求檔實際送出的（四捨五入後）座標再驗一次：有效、且與既有控制區交集面積 = 0
for k in ('vichy', 'uk'):
    assert shape(geo[k]).is_valid, k
for f, g in existing:
    ov = shapely.intersection(shape(geo['vichy']), shapely.make_valid(g), grid_size=G).area
    print(f'  與 {f} 交集面積 {ov}'); assert ov == 0, f
# 缺口（GAP_ALPINE，2026-10-31 起送成涵蓋備註）：四捨五入後扣掉維琪自由區與既有控制區，交集面積必須為 0（R9：缺口不與控制紀錄重疊）
others = [shape(geo['vichy'])] + [shapely.set_precision(shapely.make_valid(g), G) for _, g in existing]
# 與控制區之間留約 2 m 退縮（大於 1e-5 網格捨入量），避免 PostGIS 不設網格比對時出現浮點細縫
geo['gap'] = rnd(mp(shapely.difference(shapely.set_precision(shape(rnd(gap)), G), union(others).buffer(2e-5), grid_size=G)))
assert shape(geo['gap']).is_valid
for g in others:
    assert shape(geo['gap']).intersection(g).area == 0   # 不設網格的浮點交集
print('GAP_ALPINE km2', round(km2(shape(geo['gap']))))
json.dump({'type': 'FeatureCollection', 'features': [
    {'type': 'Feature', 'properties': {'id': 'CR_VICHY_FREE', 'controller': 'État français', 'km2': round(km2(vichy)),
        'boundarySource': '分界線：Ain 座標（對照 Leconte）；外框與扣除的 5 省：TRF-GIS 1940'}, 'geometry': geo['vichy']},
    {'type': 'Feature', 'properties': {'id': 'GAP_ALPINE', 'note': '義大利佔領區沒有合格來源：04、05、06、73、74 五省不畫（控制資料缺）', 'km2': round(km2(shape(geo['gap'])))}, 'geometry': geo['gap']},
    {'type': 'Feature', 'properties': {'id': 'CR_UK_HOME', 'controller': 'United Kingdom', 'km2': round(km2(uk)),
        'boundarySource': 'Natural Earth 10m admin-0 GBR（公有領域）'}, 'geometry': geo['uk']},
]}, open(os.path.join(SEED, 'zones-fr-uk-1940.geojson'), 'w'))
print('ok')
