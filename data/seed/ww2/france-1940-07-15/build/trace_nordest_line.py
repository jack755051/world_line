"""從 Perseus112 地圖（CC BY-SA 4.0，Commons）向量化「ligne du Nord-Est」（圖例 #5，深紅線核心色 ≈ (128,26,26)）。
輸出 build/nordest-line.geojson（WGS84），只當 auxiliary_geometry。"""
import json, numpy as np, networkx as nx
from PIL import Image
from skimage.morphology import skeletonize
T = '/workspace/world-line-ww2/trace/'
P = json.load(open(T + 'build/perseus_gcps.json'))['points']
px = np.array([[p[1], p[2]] for p in P], float); ll = np.array([[p[3], p[4]] for p in P], float)
f = lambda a: np.stack([np.ones(len(a)), a[:, 0], a[:, 1], a[:, 0] ** 2, a[:, 0] * a[:, 1], a[:, 1] ** 2], 1)
# 像素 → 經緯度（反向直接擬合）
ilon = np.linalg.lstsq(f(px), ll[:, 0], rcond=None)[0]; ilat = np.linalg.lstsq(f(px), ll[:, 1], rcond=None)[0]
flon = np.linalg.lstsq(f(ll), px[:, 0], rcond=None)[0]; flat = np.linalg.lstsq(f(ll), px[:, 1], rcond=None)[0]
to_px = lambda lo, la: (float((f(np.array([[lo, la]])) @ flon)[0]), float((f(np.array([[lo, la]])) @ flat)[0]))
res = np.hypot(f(px) @ ilon - ll[:, 0], (f(px) @ ilat - ll[:, 1]))
print('inverse rmse deg', round(float(np.sqrt((res ** 2).mean())), 5))

a = np.asarray(Image.open(T + 'perseus112/full.png').convert('RGB')).astype(int)
core = (abs(a[..., 0] - 128) < 30) & (abs(a[..., 1] - 26) < 25) & (abs(a[..., 2] - 26) < 25)
core[:, :2900] = False; core[3000:, :] = False; core[:, 5000:] = False
sk = skeletonize(core)
ys, xs = np.nonzero(sk)
G = nx.Graph()
pts = set(zip(xs.tolist(), ys.tolist()))
for x, y in pts:
    for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
        if (x + dx, y + dy) in pts: G.add_edge((x, y), (x + dx, y + dy), weight=float(np.hypot(dx, dy)))
# 補斷點：度數 1 的端點彼此 ≤ 25 px 相連（線被地名、河流蓋住處）
from scipy.spatial import cKDTree
ends = [n for n in G.nodes if G.degree(n) == 1]
tree = cKDTree(ends)
for i, j in tree.query_pairs(25):
    d = float(np.hypot(ends[i][0] - ends[j][0], ends[i][1] - ends[j][1]))
    if not nx.has_path(G, ends[i], ends[j]): G.add_edge(ends[i], ends[j], weight=d * 3)
nodes = np.array(list(G.nodes)); nt = cKDTree(nodes)
start = tuple(nodes[nt.query(to_px(1.834, 50.105))[1]])     # Abbeville
end = tuple(nodes[nt.query((4560, 2512))[1]])               # Dole 以南與分界線交會處
path = nx.shortest_path(G, start, end, weight='weight')
print('start', start, 'end', end, 'path px', len(path))
p = np.array(path, float)[::4]
lon = f(p) @ ilon; lat = f(p) @ ilat
coords = [[round(x, 5), round(y, 5)] for x, y in zip(lon, lat)]
# 向海延伸：Abbeville → Saint-Valery-sur-Somme → 索姆灣外海（沿 Somme 河口）
head = [[1.45, 50.25], [1.58, 50.215], [1.633, 50.187], [1.75, 50.14]]
line = head + coords
json.dump({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
    "name": "ligne du Nord-Est (Nordostlinie)", "source": "Perseus112, Carte régionale et zonale de la France occupée de 1940 à 1943, CC BY-SA 4.0",
    "method": "核心色像素骨架化＋最短路徑；Abbeville 以西沿索姆河口手動補 4 點；終點為 Dole 以南與分界線交會處"},
    "geometry": {"type": "LineString", "coordinates": line}}]}, open(T + 'build/nordest-line.geojson', 'w'))
from shapely.geometry import LineString
print('vertices', len(line), 'approx km', round(LineString(line).length * 85, 0), 'end', line[-1])
