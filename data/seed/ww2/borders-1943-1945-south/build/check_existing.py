"""本批紀錄 vs 開發庫既有有效紀錄（扣掉本批要撤回的）在各分段日是否重疊。輸入 /tmp/exist.txt（唯讀 SQL 匯出）。"""
import json, sys, os
from shapely.geometry import shape
from shapely.validation import make_valid
HERE = os.path.dirname(os.path.abspath(__file__))
ret = {json.load(open(f))['_post'].split('/')[4] for f in __import__('glob').glob(os.path.join(HERE, '..', 'requests', '04-retract-*.json'))}
ex = []
for line in open(sys.argv[1]):
    p = line.rstrip('\n').split('|', 4)
    if len(p) < 5 or len(p[4]) < 20 or p[0] in ret: continue
    ex.append((p[1], p[2], p[3], make_valid(shape(json.loads(p[4])))))
geo = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(HERE, '..', 'borders-1943-1945-south-derived.geojson')))['features']}
R = json.load(open(os.path.join(HERE, 'records.json')))
days = sorted({r['start'] for r in R} | {e[1] for e in ex if '1941' <= e[1] < '1945-05-09'})
bad = 0
for d in days:
    for r in R:
        if not (r['start'] <= d < r['end']): continue
        for slug, a, b, gg in ex:
            if a <= d < b:
                x = geo[r['geom']].intersection(gg).area
                if x > 0.02: print(d, r['ph'], slug, round(x, 3)); bad += 1
print('overlaps', bad)
