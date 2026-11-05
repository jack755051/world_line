"""同批不同政權候選之間的幾何疊合（期間重疊者）：列出 > 1000 km² 的組合（以 shapely＋粗估面積）。"""
import csv, json, sys, math
from shapely.geometry import shape
csv.field_size_limit(1 << 30)
B = sys.argv[1]
rows = [(r[0], r[1], r[2], r[3], shape(json.loads(r[4]))) for r in csv.reader(open(f'{B}/cands.csv'))]
def km2(g):
    if g.is_empty: return 0
    lat = g.centroid.y; return g.area * 111.32 ** 2 * math.cos(math.radians(lat))
out = []
for i, x in enumerate(rows):
    for y in rows[i+1:]:
        if x[1] == y[1] or not (x[2] < y[3] and y[2] < x[3]) or not x[4].intersects(y[4]): continue
        a = km2(x[4].intersection(y[4]))
        if a > 1000: out.append(dict(a=x[0], a_slug=x[1], b=y[0], b_slug=y[1], period=[max(x[2], y[2]), min(x[3], y[3])], km2=round(a)))
json.dump(out, open(f'{B}/intra-overlaps.json', 'w'), ensure_ascii=False, indent=1)
for o in out: print(o)
print('pairs >1000km²:', len(out))
