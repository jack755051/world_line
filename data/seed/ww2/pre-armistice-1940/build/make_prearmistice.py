"""停戰前快照（1940-06-04、1940-06-12）幾何：由 USMA WWII Europe Map 13、14 的描圖產生。

追溯方式（每一步都可從地圖重做）：
1. trace/gcp-map13.json、gcp-map14.json：控制點＝圖上城市圓點的像素座標（原圖 5100×3300）↔ 該城市的經緯度。
   像素座標先目讀、再用圓環樣板在 ±35px 內自動對準；以三次多項式（EPSG:3035 平面）擬合，
   殘差 > 3 km 的點視為讀錯剔除（Map 13 保留 50 點、Map 14 保留 37 點）。
2. trace/lines-map13.json、lines-map14.json：圖上的戰線（粗藍實線）與 Maginot 網格帶中心線的像素座標，
   由 trace_lines.py 以顏色門檻＋形態學＋骨架化自動擷取（不手畫）。
3. 本檔把像素轉成經緯度，用「戰線＋Maginot 帶」切開 1940 年法國（TRF-GIS 1940 省界）與比、盧、荷（Natural Earth），
   戰線右側（南／西）＝法國控制，左側（北／東）＝德國控制。
4. 地圖畫不清楚的地方不推測，改為「控制資料缺」（coverage note，R9）：
   - 圖框以外（地圖沒畫到）
   - Maginot 帶與國界之間（圖上只畫要塞帶，沒有標示誰控制帶外的狹長地帶）
   - Map 13 敦克爾克防線內（圖註：5/28 建立防線、6/4 夜撤離完成；6/4 當日狀態不明）
   - Map 14 Pays de Caux（圖上 12 June 線西端以西、8 June 點線以西；St-Valery 守軍 6/12 投降、Le Havre 未標）
   - Map 14 兩段 12 June 線之間的不連續處（Châlons 東南，約 10 km）
6. 英國本土（Tai 2026-10-31 選 B：每張快照只寫當天、只寫圖上看得到的範圍）：
   - Map 13（6/4）圖框內英國的位置畫成海面與標題框，沒有畫英國陸地 → 6/4 不寫。
   - Map 14（6/12）畫出英格蘭東南（標「ENGLAND」，與德軍區不同色），圖框左上被標題框蓋住。
     看得到的範圍＝圖框 − 標題框（像素 752,257–1570,636），用英格蘭與海峽兩岸 21 個控制點（trace/gcp-map14-uk.json，
     其中 Norwich、Coventry、Southampton、Portland 4 點為本次新增）做一次（仿射）配準；再把邊界往內縮
     leave-one-out 最大誤差（UK_INSET_KM），確保紀錄只落在圖上確實畫到的地方。陸地外框用 Natural Earth GBR。
     其餘英國領土（圖框外、標題框下、內縮帶）列控制資料缺，不推測。
5. 已寫入的 CR_NORD（Nord＋Pas-de-Calais，[1940-06-04, 1944-07-16)，德國）先扣掉，避免同一控制方重疊（I3）。
用法（box）：~/.venvs/gis/bin/python make_prearmistice.py
"""
import json, os, math, shapefile, shapely, numpy as np
from shapely.geometry import shape, mapping, Point, LineString, Polygon, MultiPolygon
from shapely.ops import transform
from pyproj import Transformer, Geod

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.dirname(HERE)
FR = os.path.join(SEED, '..', 'france-1940-07-15')
TRACE = os.path.join(HERE, 'trace')
T = '/workspace/world-line-ww2/trace/'
G = 1e-5
MARGIN = 2e-5
geod = Geod(ellps='WGS84')
km2 = lambda g: abs(geod.geometry_area_perimeter(g)[0]) / 1e6
polys = lambda g: list(g.geoms) if hasattr(g, 'geoms') else [g]
union = lambda gs: P(shapely.union_all([g for g in gs if g is not None and not g.is_empty], grid_size=G))
def mp(g, min_km2=0.5):
    g = P(g)
    ps = [p for p in polys(g) if isinstance(p, Polygon) and p.area > 0 and km2(p) >= min_km2]
    out = MultiPolygon(ps); assert out.is_valid; return out
def rnd(g): return P(shapely.set_precision(g, G))
def P(g):
    """只留面（集合運算可能夾帶線、點）。"""
    ps = [p for p in polys(g) if isinstance(p, Polygon) and not p.is_empty]
    if hasattr(g, 'geoms'):
        ps = [q for x in g.geoms for q in (polys(x) if hasattr(x, 'geoms') else [x]) if isinstance(q, Polygon) and not q.is_empty]
    return MultiPolygon(ps) if len(ps) != 1 else ps[0]
_I, _D = shapely.intersection, shapely.difference
def inter(a, b): return P(_I(a, b, grid_size=G))
def diff(a, b): return P(_D(a, b, grid_size=G))

# ── 地理底圖 ──
TR3035 = Transformer.from_crs('EPSG:4326', 'EPSG:3035', always_xy=True)
INV3035 = Transformer.from_crs('EPSG:3035', 'EPSG:4326', always_xy=True)
tr2154 = Transformer.from_crs(2154, 4326, always_xy=True).transform
r = shapefile.Reader(T + 'trf-gis/DEPARTEMENTS_1940', encoding='utf-8')
france = union([P(shapely.make_valid(transform(tr2154, shape(s.__geo_interface__)))) for s in r.shapes()])
ne = json.load(open(T + 'ne_10m_admin_0_countries.geojson'))
cty = {f['properties']['ADM0_A3']: shapely.make_valid(shape(f['geometry'])) for f in ne['features'] if f['properties']['ADM0_A3'] in ('BEL', 'LUX', 'NLD')}
benelux = {k: rnd(v) for k, v in cty.items()}
land = union([france] + list(benelux.values()))
nord = shape(json.load(open(os.path.join(FR, 'requests', '05-control-2-nord-pas-de-calais.json')))['body']['geometry'])
nord = rnd(nord)

# ── 像素 → 經緯度（三次多項式，EPSG:3035） ──
def fit(gcps):
    P = np.array([[g[1], g[2]] for g in gcps], float)
    X = np.array([TR3035.transform(g[3], g[4]) for g in gcps])
    pm, ps, xm, xs = P.mean(0), P.std(0), X.mean(0), X.std(0)
    def des(u, v): return np.stack([np.ones_like(u), u, v, u*u, u*v, v*v, u**3, u*u*v, u*v*v, v**3], 1)
    A = des(*((P - pm) / ps).T); c, *_ = np.linalg.lstsq(A, (X - xm) / xs, rcond=None)
    res = np.hypot(*((A @ c * xs + xm) - X).T)
    def p2ll(pts):
        pts = np.asarray(pts, float); xy = des(*((pts - pm) / ps).T) @ c * xs + xm
        return list(zip(*INV3035.transform(xy[:, 0], xy[:, 1])))
    return p2ll, float(np.sqrt((res ** 2).mean())), float(res.max()), len(gcps)

def extend(coords, d):
    (x0, y0), (x1, y1) = coords[0], coords[3]; (xa, ya), (xb, yb) = coords[-4], coords[-1]
    n0 = math.hypot(x0 - x1, y0 - y1); n1 = math.hypot(xb - xa, yb - ya)
    return [(x0 + (x0 - x1) / n0 * d, y0 + (y0 - y1) / n0 * d)] + list(coords) + [(xb + (xb - xa) / n1 * d, yb + (yb - ya) / n1 * d)]

def frame(p2ll):
    x0, y0, x1, y1 = 752, 257, 4364, 3026
    edge = [(x, y0) for x in np.linspace(x0, x1, 60)] + [(x1, y) for y in np.linspace(y0, y1, 60)] + \
           [(x, y1) for x in np.linspace(x1, x0, 60)] + [(x0, y) for y in np.linspace(y1, y0, 60)]
    return rnd(Polygon(p2ll(edge)))

def right_side(line_ll):
    """有向線（西→東）右側＝南／西：用線＋外圈閉合成多邊形。"""
    c = list(line_ll.coords)
    # 外圈閉合只走海上／底圖以外（英國不在底圖內）：西端 → 經度 -0.05 的英吉利海峽 → 北緯 51.2 → 西、南、東繞回東端。
    ring = c + [(c[-1][0] + 0.5, 30.0), (-30.0, 30.0), (-30.0, 51.2), (-0.05, 51.2), (-0.05, c[0][1]), c[0]]
    poly = P(shapely.make_valid(Polygon(ring)))
    return poly

def build(name, gcp_file, line_px, junction_px, gaps_px, as_of):
    p2ll, rms, mx, n = fit(json.load(open(os.path.join(TRACE, gcp_file))))
    fr = frame(p2ll)
    line = LineString(extend(p2ll(line_px), 0.15))
    assert line.is_simple, f'{name}: 戰線自交'
    south = right_side(line)
    inside = inter(land, fr)
    S = inter(inside, south)
    N = diff(inside, south)
    jx = p2ll([junction_px])[0][0]
    east = Polygon([(jx, 40), (20, 40), (20, 60), (jx, 60)])
    gap_maginot = inter(inter(N, france), east)
    gap_frame = diff(land, fr)
    named_gaps = {k: inter(rnd(Polygon(p2ll(v))), inside) for k, v in gaps_px.items()}
    allgaps = union([gap_maginot] + list(named_gaps.values()))
    de = diff(diff(diff(N, gap_maginot), allgaps), nord)
    fr3 = diff(inter(S, france), allgaps)
    # 網格運算會在共用邊界留下 m² 級的浮點細縫；PostGIS 不設網格比對（I3、R9 檢查），所以與既有紀錄（CR_NORD）
    # 及同日控制區之間留 MARGIN（約 2 m，大於 1e-5 網格的捨入量）的退縮，確保送出的座標彼此交集面積為 0。
    de = diff(de, nord.buffer(MARGIN))
    taken = union([de, fr3, nord]).buffer(MARGIN)
    out = {
        'DE': mp(de), 'FR3': mp(fr3),
        'GAP_FRAME': mp(diff(gap_frame, taken)),
        'GAP_MAGINOT': mp(diff(diff(gap_maginot, union(named_gaps.values())), taken)),
    }
    for k, g in named_gaps.items():
        out[k] = mp(diff(g, taken), min_km2=0.05)
    out = {k: mp(rnd(v), min_km2=0.05) for k, v in out.items()}
    # 檢查（不設網格的浮點交集，同 PostGIS）：彼此不重疊、與 CR_NORD 不重疊
    keys = list(out)
    for i, a in enumerate(keys):
        assert out[a].intersection(nord).area == 0, (a, 'nord')
        for b in keys[i + 1:]:
            if {a, b} == {'DE', 'FR3'}: continue   # 不同控制方，I3 不適用（相鄰邊界允許浮點細縫）
            if a.startswith('GAP') and b.startswith('GAP'): continue   # 缺口彼此重疊無妨（同為控制資料缺）
            ov = out[a].intersection(out[b]).area
            assert ov == 0, (name, a, b, ov)
    print(f'== {name}（{as_of}）GCP {n} 點，擬合殘差 RMS {rms/1000:.2f} km、最大 {mx/1000:.2f} km')
    for k, g in out.items(): print(f'   {k:14s} {km2(g):>10,.0f} km²  {len(g.geoms)} 塊')
    return out, {'gcp': n, 'rms_km': round(rms / 1000, 2), 'max_km': round(mx / 1000, 2)}

L13 = json.load(open(os.path.join(TRACE, 'lines-map13.json')))
L14 = json.load(open(os.path.join(TRACE, 'lines-map14.json')))
def join(*parts, near=12):
    """依序接起各段；下一段開頭距上一段終點 near px 內的點捨去（戰線與 Maginot 帶在交會處重疊，避免折返自交）。"""
    out = list(parts[0])
    for p in parts[1:]:
        p = list(p)
        while p and math.hypot(p[0][0] - out[-1][0], p[0][1] - out[-1][1]) < near: p.pop(0)
        out += p
    return out
line13 = join(L13['front_e2w'][::-1], L13['band_e2w'][::-1])
line14 = join(L14['west_e2w'][::-1], L14['east_s2n'], L14['band_s2n'][::-1])
DUNKIRK = [(1300, 960), (1340, 1010), (1350, 1033), (1380, 1045), (1455, 1055), (1510, 1050), (1550, 1042), (1570, 1010),
           (1590, 980), (1620, 960), (1645, 938), (1660, 900), (1400, 880)]
CAUX = [(2102, 1790), (2102, 1820), (2102, 1945), (2080, 1965), (2010, 1985), (1950, 1990), (1920, 2010), (1910, 2030),
        (1918, 2062), (1880, 2092), (1844, 2086), (1760, 2085), (1650, 2075), (1650, 1790)]
a, b = L14['west_e2w'][0], L14['east_s2n'][0]        # 兩段 12 June 線的斷點（像素）
mx_, my_ = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2; rad = max(30, math.hypot(a[0] - b[0], a[1] - b[1]) / 2 + 15)
BREAK = [(mx_ + rad * math.cos(t), my_ + rad * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 24)]

z13, m13 = build('Map 13', 'gcp-map13.json', line13, L13['band_e2w'][-1], {'GAP_DUNKIRK': DUNKIRK}, '1940-06-04')
z14, m14 = build('Map 14', 'gcp-map14.json', line14, L14['band_s2n'][-1], {'GAP_CAUX': CAUX, 'GAP_LINEBREAK': BREAK}, '1940-06-12')

# ── 英國本土（Map 14，1940-06-12） ──
UK_TITLE_PX = (752, 257, 1570, 636)      # 標題框（含 5 px 邊距）
def fit_affine(gcps):
    Pp = np.array([[g[1], g[2]] for g in gcps], float)
    X = np.array([TR3035.transform(g[3], g[4]) for g in gcps])
    A = np.c_[np.ones(len(Pp)), Pp]; c, *_ = np.linalg.lstsq(A, X, rcond=None)
    return (lambda pts: np.c_[np.ones(len(pts)), np.asarray(pts, float)] @ c), np.hypot(*((A @ c) - X).T)
UKG = json.load(open(os.path.join(TRACE, 'gcp-map14-uk.json')))
uk_f, uk_res = fit_affine(UKG)
uk_loo = []
for i in range(len(UKG)):
    fi, _ = fit_affine(UKG[:i] + UKG[i + 1:])
    uk_loo.append(float(np.hypot(*(fi([UKG[i][1:3]])[0] - np.array(TR3035.transform(UKG[i][3], UKG[i][4]))))))
UK_INSET_KM = math.ceil(max(uk_loo) / 1000)
x0, y0, x1, y1 = 752, 257, 4364, 3026; tx0, ty0, tx1, ty1 = UK_TITLE_PX
def edge(pts):
    out = []
    for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
        out += [(ax + (bx - ax) * t, ay + (by - ay) * t) for t in np.linspace(0, 1, 40, endpoint=False)]
    return out
# 圖框 − 標題框（L 形，像素座標，順時針）
vis_px = [(tx1, y0), (x1, y0), (x1, y1), (x0, y1), (x0, ty1), (tx1, ty1)]
vis3035 = Polygon(uk_f(edge(vis_px))).buffer(-UK_INSET_KM * 1000)
vis_ll = rnd(Polygon(list(zip(*INV3035.transform(*np.array(vis3035.exterior.coords).T)))))
gbr = rnd(P(shapely.make_valid(shape([f for f in ne['features'] if f['properties']['ADM0_A3'] == 'GBR'][0]['geometry']))))
uk_vis = mp(rnd(inter(gbr, vis_ll)), min_km2=0.5)
uk_gap = mp(rnd(diff(gbr, uk_vis.buffer(MARGIN))), min_km2=0.5)
assert uk_vis.intersection(uk_gap).area == 0
for k, g in z14.items(): assert uk_vis.intersection(g).area == 0 and uk_gap.intersection(g).area == 0, k
z14['UK'] = uk_vis; z14['GAP_UK'] = uk_gap
m_uk = {'gcp': len(UKG), 'rms_km': round(float(np.sqrt((uk_res ** 2).mean())) / 1000, 2), 'max_km': round(float(uk_res.max()) / 1000, 2),
        'loo_max_km': round(max(uk_loo) / 1000, 2), 'inset_km': UK_INSET_KM}
print(f'== 英國本土（1940-06-12）控制點 {m_uk["gcp"]}，仿射殘差 RMS {m_uk["rms_km"]} km、最大 {m_uk["max_km"]} km，LOO 最大 {m_uk["loo_max_km"]} km → 內縮 {UK_INSET_KM} km')
print(f'   UK {km2(uk_vis):,.0f} km²　GAP_UK {km2(uk_gap):,.0f} km²')

feats = []
for as_of, z, meta, src in [('1940-06-04', z13, m13, 'USMA WWII Europe Map 13'), ('1940-06-12', z14, m14, 'USMA WWII Europe Map 14')]:
    for k, g in z.items():
        mm = m_uk if k in ('UK', 'GAP_UK') else meta
        feats.append({'type': 'Feature', 'properties': {'snapshot': as_of, 'zone': k, 'km2': round(km2(g)), 'source': src, **mm},
                      'geometry': mapping(shapely.set_precision(g, G))})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(SEED, 'zones-pre-armistice-1940.geojson'), 'w'))
print('寫出 zones-pre-armistice-1940.geojson')
