"""建 1940-07-15 德國在法國本土的軍事佔領區多邊形。
方法：Natural Earth 10m（PD）的法國本土外框，用 Ain 省分界線資料集（Licence Ouverte 2.0）切成兩半，
取含巴黎的一側＋大西洋／英吉利海峽沿岸島嶼。"""
import json, math
from shapely.geometry import shape, mapping, LineString, Point, MultiPolygon, Polygon, box
from shapely.ops import split, unary_union
from shapely.validation import explain_validity
from pyproj import Geod

T = '/workspace/world-line-ww2/trace/'
ne = json.load(open(T + 'ne_10m_admin_0_countries.geojson'))
fr = next(f for f in ne['features'] if f['properties']['ADM0_A3'] == 'FRA')
metro_box = box(-6, 41, 10, 52)
parts = [p for p in shape(fr['geometry']).geoms if p.intersects(metro_box)]
mainland = max(parts, key=lambda p: p.area)
islands = [p for p in parts if p is not mainland]

ain = json.load(open(T + 'ain-ligne-demarcation.geojson'))['features'][0]['geometry']['coordinates']
def extend(a, b, deg=0.05):
    dx, dy = b[0] - a[0], b[1] - a[1]; n = math.hypot(dx, dy)
    return (b[0] + dx / n * deg, b[1] + dy / n * deg)
coords = [extend(ain[1], ain[0])] + [tuple(c[:2]) for c in ain] + [extend(ain[-2], ain[-1])]
line = LineString(coords)

pieces = list(split(mainland, line).geoms)
# 以自由區內的維琪（3.43, 46.13）判定：含維琪的那塊是自由區，其餘（含巴黎一側、熱克斯地區小塊）為佔領區
vichy, paris = Point(3.43, 46.13), Point(2.35, 48.86)
free_main = [p for p in pieces if p.contains(vichy)]
assert len(free_main) == 1, len(pieces)
free_main = free_main[0]
occ_pieces = [p for p in pieces if p is not free_main]
assert any(p.contains(paris) for p in occ_pieces)
occ_main = unary_union(occ_pieces)

def occupied_island(p):
    c = p.representative_point()
    return not (c.y < 43.8 and c.x > 3.0)  # 地中海島嶼（科西嘉、耶爾群島等）屬自由區側
occ_islands = [p for p in islands if occupied_island(p)]
free_islands = [p for p in islands if not occupied_island(p)]

zone = unary_union([occ_main] + occ_islands)
zone = MultiPolygon([zone]) if isinstance(zone, Polygon) else zone
assert zone.is_valid, explain_validity(zone)
zone = MultiPolygon([Polygon([(round(x, 5), round(y, 5)) for x, y in g.exterior.coords],
                             [[(round(x, 5), round(y, 5)) for x, y in r.coords] for r in g.interiors]) for g in zone.geoms])
assert zone.is_valid, explain_validity(zone)

geod = Geod(ellps='WGS84')
area = abs(geod.geometry_area_perimeter(zone)[0]) / 1e6
farea = abs(geod.geometry_area_perimeter(unary_union(parts))[0]) / 1e6
print(f'pieces={len(pieces)} islands occ={len(occ_islands)} free={len(free_islands)}')
print(f'zone parts={len(zone.geoms)} vertices={sum(len(g.exterior.coords) for g in zone.geoms)} area={area:,.0f} km2 / metro France {farea:,.0f} km2 = {area/farea:.1%}')
print('bounds', zone.bounds)

props = {
  'name': {'zh-Hant': '德國在法國本土的軍事佔領區（1940-07-15）', 'en': 'German military occupation zone in metropolitan France (1940-07-15)'},
  'controller': 'deutsches-reich', 'controlType': 'military_occupation',
  'validPeriod': {'start': '1940-07-15', 'end': '1942-11-11'},
  'status': 'DRAFT — 待 Tai 檢查，未寫入資料庫',
  'method': 'Natural Earth 10m 法國本土外框（PD）以 Ain 省「Ligne de démarcation」線（Licence Ouverte 2.0，依停戰協定與 Michelin 1:200,000 建置）切割；取含巴黎一側＋大西洋／海峽島嶼；對照 Leconte 1:1,800,000 分界線圖（CC0，館藏號 2015.3.1.230）目視檢查。座標四捨五入至 1e-5 度。',
  'includes': ['北部兩省（Nord、Pas-de-Calais，歸駐布魯塞爾德軍軍事管理）', '亞爾薩斯-摩澤爾（1940-08 起實質併入）', '東北禁區（zone interdite）', '大西洋沿岸帶'],
  'excludes': ['自由區（維琪直接統治）', '義大利佔領區', '海峽群島（英國王室屬地，另立紀錄）'],
}
json.dump({'type': 'FeatureCollection', 'features': [
  {'type': 'Feature', 'properties': props, 'geometry': mapping(zone)},
]}, open(T + 'occupied-zone-1940-07-15.geojson', 'w'), ensure_ascii=False)
json.dump({'type': 'FeatureCollection', 'features': [
  {'type': 'Feature', 'properties': {'role': 'demarcation-line (Ain dataset, extended 0.05° at both ends to close against Natural Earth border)'}, 'geometry': mapping(line)},
  {'type': 'Feature', 'properties': {'role': 'free-zone side (reference only, not a record in this request)'}, 'geometry': mapping(unary_union([free_main] + free_islands))},
]}, open(T + 'build/reference-layers.geojson', 'w'))
