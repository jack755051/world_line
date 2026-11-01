import json, pickle, collections
from shapely.geometry import box, MultiPolygon, Polygon, LineString
from shapely.ops import unary_union, polygonize
from shapely.validation import make_valid
from shapely import set_precision
import geoms as GM
FRAME = box(-20, 15, 60, 72)
landF = pickle.load(open('/workspace/ru/landF.pkl', 'rb'))
def ww1proc(rid):
    """與 WW1／兩次大戰之間各批 build.py 相同：框 box(-20,15,60,72) → 陸地 → 簡化 0.0005 → 精度 1e-4。"""
    fn = GM.find(rid); x = json.load(open(fn)); rel = [e for e in x['elements'] if e['type'] == 'relation'][0]
    outer, inner = [], []
    for m in rel['members']:
        if m['type'] != 'way' or 'geometry' not in m: continue
        c = [(p['lon'], p['lat']) for p in m['geometry'] if p]
        if len(c) < 2: continue
        (inner if m['role'] == 'inner' else outer if m['role'] in ('outer', '') else []).append(LineString(c))
    o = unary_union(list(polygonize(unary_union(outer)))) if outer else Polygon()
    i = unary_union(list(polygonize(unary_union(inner)))) if inner else Polygon()
    g = make_valid(o.difference(i)) if not o.is_empty else o
    g = make_valid(g.intersection(FRAME).intersection(landF))
    g = make_valid(g.simplify(0.0005, preserve_topology=True))
    g = make_valid(set_precision(g, 1e-4))
    return MultiPolygon([p for p in GM.polys(g) if p.area > 1e-6])
