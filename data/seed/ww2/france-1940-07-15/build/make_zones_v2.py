"""v2（Tai 2026-10-28 22:37 決定）：混合做法。
- 外框與各區塊單位：TRF-GIS 1940 年省界（Gay 2021，CC BY 4.0）
- 佔領區／自由區：照原圖描的分界線（Ain 資料集座標，已對照 Leconte CC0 原圖），不沿省界
- 北部兩省、亞爾薩斯-摩澤爾：1940 年省界組合
- 東北禁區：ligne du Nord-Est（Perseus112 圖向量化，CC BY-SA 4.0，auxiliary）
所有疊合運算在 1e-5° 網格上做，各區邊界完全共用（I3：面積重疊 = 0）。"""
import json, shapefile, shapely
from shapely.geometry import shape, mapping, Point, LineString, MultiPolygon, Polygon, box
from shapely.ops import transform, split
unary_union = lambda gs, grid_size=None: shapely.union_all(gs, grid_size=grid_size)
from pyproj import Transformer
T = '/workspace/world-line-ww2/trace/'
G = 1e-5
tr = Transformer.from_crs(2154, 4326, always_xy=True).transform

r = shapefile.Reader(T + 'trf-gis/DEPARTEMENTS_1940', encoding='utf-8')
dep = {}
for sr in r.iterShapeRecords():
    g = shapely.make_valid(transform(tr, shape(sr.shape.__geo_interface__)))
    dep[str(sr.record['dep_id'])] = (sr.record['dep_name'], shapely.set_precision(g, G))
france = unary_union([g for _, g in dep.values()], grid_size=G)

def polys(g): return list(g.geoms) if hasattr(g, 'geoms') else [g]
def mp(g):
    ps = [p for p in polys(g) if isinstance(p, Polygon) and p.area > 0]
    return MultiPolygon(ps)

def extend(coords, d=0.05):
    import math
    (x0, y0), (x1, y1) = coords[0], coords[1]; (xa, ya), (xb, yb) = coords[-2], coords[-1]
    n0 = math.hypot(x0 - x1, y0 - y1); n1 = math.hypot(xb - xa, yb - ya)
    return [(x0 + (x0 - x1) / n0 * d, y0 + (y0 - y1) / n0 * d)] + list(coords) + [(xb + (xb - xa) / n1 * d, yb + (yb - ya) / n1 * d)]

# 1) 分界線切出自由區（含 Vichy 的那塊＋地中海島嶼）
ain = json.load(open(T + 'ain-ligne-demarcation.geojson'))['features'][0]['geometry']
ain_line = LineString(extend(ain['coordinates'] if ain['type'] == 'LineString' else ain['coordinates'][0]))
free_parts = []
for p in polys(france):
    if p.intersects(ain_line):
        for q in polys(split(p, ain_line)):
            if q.contains(Point(3.43, 46.13)): free_parts.append(q)
    else:
        rp = p.representative_point()
        if rp.y < 43.8 and rp.x > 3.0: free_parts.append(p)   # 地中海島嶼（Corse、Hyères 等）
free_raw = shapely.set_precision(unary_union(free_parts), G)
occupied = shapely.difference(france, free_raw, grid_size=G)
free = shapely.intersection(france, free_raw, grid_size=G)

# 2) 省界組合
def union_deps(ids): return unary_union([dep[i][1] for i in ids], grid_size=G)
nord = shapely.intersection(union_deps(['59', '62']), occupied, grid_size=G)
am = shapely.intersection(union_deps(['57', '67', '68']), occupied, grid_size=G)
rest = shapely.difference(occupied, unary_union([nord, am], grid_size=G), grid_size=G)

# 3) ligne du Nord-Est 切出東北禁區（不含巴黎那塊、且位於東北象限的部分）
ne = json.load(open(T + 'build/nordest-line.geojson'))['features'][0]['geometry']['coordinates']
ne_line = LineString(extend(ne, 0.03))
pieces = []
for p in polys(rest):
    pieces += polys(split(p, ne_line)) if p.intersects(ne_line) else [p]
paris_piece = next(q for q in pieces if q.contains(Point(2.3488, 48.8534)))
zi_core = max((q for q in pieces if q is not paris_piece), key=lambda q: q.area)  # 東北禁區主體
zi_parts = [zi_core]
for q in pieces:
    if q is paris_piece or q is zi_core: continue
    # 小碎塊（線本身的迴圈、河口補點造成）：歸給共用邊界較長的一側；不相鄰的島嶼歸本體
    lz = q.boundary.intersection(zi_core.boundary).length
    lm = q.boundary.intersection(paris_piece.boundary).length
    if lz > lm: zi_parts.append(q)
zi_raw = shapely.set_precision(unary_union(zi_parts), G)
zi = shapely.intersection(rest, zi_raw, grid_size=G)
main = shapely.difference(rest, zi_raw, grid_size=G)

regions = {'main': main, 'nord': nord, 'am': am, 'zi': zi}
geod = __import__('pyproj').Geod(ellps='WGS84')
def km2(g): return abs(geod.geometry_area_perimeter(g)[0]) / 1e6
out = {}
for k, g in regions.items():
    g = mp(g); assert g.is_valid, k
    out[k] = g
    print(k, 'parts', len(g.geoms), 'vertices', shapely.get_num_coordinates(g), 'km2', round(km2(g)))
names = list(out)
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        ov = shapely.intersection(out[names[i]], out[names[j]], grid_size=G).area
        assert ov == 0, (names[i], names[j], ov)
print('france km2', round(km2(france)), 'occupied', round(km2(occupied)), 'free', round(km2(free)))
json.dump({k: mapping(v) for k, v in out.items()} | {'free_reference': mapping(mp(free))}, open(T + 'build/zones-v2.json', 'w'))
