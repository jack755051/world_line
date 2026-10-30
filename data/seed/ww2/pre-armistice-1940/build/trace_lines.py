"""從 USMA WWII Europe Map 13、14 原圖自動擷取戰線與 Maginot 帶的像素中心線，寫入 trace/lines-map13.json、lines-map14.json。

方法（不手畫）：在指定視窗內以顏色門檻取出圖上的藍色線條 → 形態學 closing／opening 去掉文字與細線 →
取視窗內最大的連通區塊 → 骨架化 → 取骨架上最長的路徑當中心線（每 3 px 取一點）。
原圖：/workspace/world-line-ww2/trace/WWIIEurope13.jpg、WWIIEurope14.jpg（5100×3300，USMA S3 下載）。
用法（box）：~/.venvs/gis/bin/python trace_lines.py
"""
import json, os, numpy as np, networkx as nx
from PIL import Image
from scipy import ndimage as ndi
from skimage.morphology import disk, binary_opening, binary_closing, skeletonize

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = '/workspace/world-line-ww2/trace/WWIIEurope{}.jpg'

def longest_path(mask):
    sk = skeletonize(mask); ys, xs = np.nonzero(sk)
    idx = {(y, x): i for i, (y, x) in enumerate(zip(ys, xs))}
    G = nx.Graph()
    for (y, x), i in idx.items():
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (dy or dx) and (y + dy, x + dx) in idx:
                    G.add_edge(i, idx[(y + dy, x + dx)], weight=float(np.hypot(dy, dx)))
    H = G.subgraph(max(nx.connected_components(G), key=len))
    a = next(iter(H.nodes)); d = nx.single_source_dijkstra_path_length(H, a); b = max(d, key=d.get)
    d2, paths = nx.single_source_dijkstra(H, b); c = max(d2, key=d2.get)
    return [(float(xs[i]), float(ys[i])) for i in paths[c]]

def trace(n, window, thr, close_r, open_r, start_near):
    im = np.array(Image.open(IMG.format(n)).convert('RGB')).astype(int)
    x0, y0, x1, y1 = window
    R, G, B = (im[y0:y1, x0:x1, k] for k in range(3))
    m = (R < thr[0]) & (G < thr[1]) & (B > thr[2])
    if close_r: m = binary_closing(m, disk(close_r))
    m = binary_opening(m, disk(open_r))
    lab, k = ndi.label(m); sizes = ndi.sum(m, lab, range(1, k + 1))
    p = longest_path(lab == int(np.argmax(sizes)) + 1)
    p = [(x + x0, y + y0) for x, y in p]
    if np.hypot(p[0][0] - start_near[0], p[0][1] - start_near[1]) > np.hypot(p[-1][0] - start_near[0], p[-1][1] - start_near[1]):
        p = p[::-1]
    return [[round(x, 1), round(y, 1)] for x, y in p[::3]]

if __name__ == '__main__':
    out13 = {
        'map': 'USMA WWII Europe Map 13',
        'front_e2w': trace(13, (900, 1600, 3300, 2600), (70, 115, 190), 0, 4, (3192, 2464)),
        'band_e2w': trace(13, (3186, 2380, 4368, 3000), (90, 140, 190), 4, 5, (4354, 2869)),
    }
    out14 = {
        'map': 'USMA WWII Europe Map 14',
        'west_e2w': trace(14, (1780, 1980, 3040, 2460), (70, 115, 190), 0, 2, (3015, 2397)),
        'east_s2n': trace(14, (3040, 2040, 3300, 2420), (70, 115, 190), 0, 2, (3065, 2379)),
        'band_s2n': trace(14, (3200, 2000, 4100, 3000), (90, 140, 190), 4, 5, (3864, 2924)),
    }
    for name, o in (('lines-map13.json', out13), ('lines-map14.json', out14)):
        old = json.load(open(os.path.join(HERE, 'trace', name)))
        o['note'] = old.get('note', '')
        json.dump(o, open(os.path.join(HERE, 'trace', name), 'w'), ensure_ascii=False)
        print(name, {k: (len(v), v[0], v[-1]) for k, v in o.items() if isinstance(v, list)})
