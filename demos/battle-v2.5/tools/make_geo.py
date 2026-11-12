"""把 Natural Earth 1:10m（公有領域）裁成某一場戰役的底圖小檔。取代舊的 clip_geo.py＋make_sea.py。
用法（在 demo 根目錄）：python tools/make_geo.py <battle-id> /path/to/ne_dir
讀 battles/<id>/theatre.json：
  bbox          [西, 南, 東, 北]            戰區範圍（也是地圖可拖曳的邊界）
  land_classes  {"allied": [國名...], ...}  陸地底色分類（Natural Earth 的 ADMIN 名稱）；沒列到的是 other
                也可寫成 {"countries": [...], "within": {"國名": 多邊形}, "clip": 多邊形}；有 control.border 時會自動扣掉當年國界內的範圍
  sea_mask_bbox [西, 南, 東, 北]            海面遮罩範圍（控制區會伸進海裡的地方）；省略＝整個 bbox
  river_rank    9                           河流 scalerank 上限
輸出 battles/<id>/geo/{land,landc,countries,borders,rivers,sea,graticule}.geojson
注意：國界是 Natural Earth 的現代國界，不是當年的國界。
"""
import json, os, sys, math
from shapely.geometry import shape, box, mapping, LineString, MultiLineString, Polygon
from shapely.ops import unary_union

bid, src = sys.argv[1], sys.argv[2]
cfg = json.load(open(f'battles/{bid}/theatre.json'))
W, S, E, N = cfg['bbox']
BB = box(W, S, E, N)
OUT = f'battles/{bid}/geo/'
os.makedirs(OUT, exist_ok=True)

def load(n): return json.load(open(f'{src}/{n}.geojson'))['features']
def rnd(g, nd=4): return json.loads(json.dumps(mapping(g)), parse_float=lambda x: round(float(x), nd))
def dump(name, feats): json.dump({'type': 'FeatureCollection', 'features': feats}, open(OUT + name, 'w'), separators=(',', ':'), ensure_ascii=False)
def feat(g, props=None): return {'type': 'Feature', 'properties': props or {}, 'geometry': rnd(g)}

land = unary_union([shape(f['geometry']).buffer(0).intersection(BB) for f in load('ne_10m_land') if shape(f['geometry']).intersects(BB)])
land = land.simplify(0.004, preserve_topology=True).buffer(0)
dump('land.geojson', [feat(land)])

countries = {}
feats = []
for f in load('ne_10m_admin_0_countries'):
    g = shape(f['geometry']).buffer(0)
    if g.intersects(BB):
        g = g.intersection(BB).simplify(0.004, preserve_topology=True).buffer(0)
        countries[f['properties']['ADMIN']] = g
        feats.append(feat(g, {'name': f['properties']['ADMIN'], 'iso': f['properties']['ISO_A3']}))
dump('countries.geojson', feats)

feats = []
for f in load('ne_10m_admin_0_boundary_lines_land'):
    g = shape(f['geometry'])
    if g.intersects(BB): feats.append(feat(g.intersection(BB).simplify(0.003)))
dump('borders.geojson', feats)

feats = []
for f in load('ne_10m_rivers_lake_centerlines'):
    g, p = shape(f['geometry']), f['properties']
    if g.intersects(BB) and (p.get('scalerank') or 10) <= cfg.get('river_rank', 9) and (p.get('featurecla') or '').startswith('River'):
        feats.append(feat(g.intersection(BB).simplify(0.003), {'name': p.get('name'), 'sr': p.get('scalerank')}))
dump('rivers.geojson', feats)
print('rivers:', sorted({f['properties']['name'] for f in feats if f['properties']['name']}))

rest, classed = land, []
hb = cfg.get('control', {}).get('border')
hist = Polygon([p[:2] for p in hb]).buffer(0) if hb else None
for k, spec in cfg.get('land_classes', {}).items():
    if isinstance(spec, list): spec = {'countries': spec}
    names = spec['countries']
    missing = [n for n in names if n not in countries]
    if missing: print('警告：bbox 內找不到', missing)
    g = unary_union([countries[n] for n in names if n in countries]).buffer(0).intersection(land)
    for n, poly in spec.get('within', {}).items():   # 某國只取多邊形內的部分（例：俄羅斯只取加里寧格勒）
        if n in countries: g = g.difference(countries[n].difference(Polygon(poly)))
    if spec.get('clip'): g = g.intersection(Polygon(spec['clip']))
    if hist is not None: g = g.difference(hist)   # 當年國界內的範圍由控制區圖層上色，底色不重複塗
    classed.append((k, g)); rest = rest.difference(g.buffer(0.0005))
dump('landc.geojson', [feat(g.simplify(0.002), {'k': k}) for k, g in [('other', rest)] + classed if not g.is_empty])

dump('sea.geojson', [feat(box(*cfg.get('sea_mask_bbox', cfg['bbox'])).intersection(BB).difference(land))])
sea_all = BB.difference(land)
ny, nx = int(round((N - S) * 10)) + 1, int(round((E - W) * 10)) + 1
lines = [LineString([(lon, S + i * 0.1) for i in range(ny)]) for lon in range(math.ceil(W), math.floor(E) + 1)] \
      + [LineString([(W + i * 0.1, lat) for i in range(nx)]) for lat in range(math.ceil(S), math.floor(N) + 1)]
dump('graticule.geojson', [feat(MultiLineString(lines).intersection(sea_all))])
print('ok', bid, {n: os.path.getsize(OUT + n) for n in sorted(os.listdir(OUT))})
