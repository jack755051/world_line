#!/usr/bin/env python3
"""QA：在每個疆界變動日與截圖日，檢查不同紀錄之間的重疊（同一地方兩個主權）與 1938-01-01 範圍內的空白。輸出 qa.json。"""
import json, os, sys, importlib.util
from shapely.geometry import shape
from shapely.ops import unary_union
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location('mr', os.path.join(HERE, 'make_requests.py'))
man = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json'), encoding='utf-8'))}
src = open(os.path.join(HERE, 'make_requests.py'), encoding='utf-8').read()
ns = {}; exec(src.split("def ohm_date")[0].split("HERE = ")[0] + "\n" + "REL_REGIME=None", ns)  # 只取 import
exec('REL_REGIME = ' + src.split('REL_REGIME = ')[1].split('\n}\n')[0] + '\n}', ns)
REL_REGIME = ns['REL_REGIME']
feats = {f['id']: shape(f['geometry']) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-1938-1940.geojson')))['features']}
def d(s):
    if s is None: return '9999-12-31'
    return s if len(s) == 10 else (s + '-01-01' if len(s) == 4 else s + '-01')
def active(day):
    return [rid for rid, r in man.items() if rid in feats and d(r['start_date']) <= day < d(r['end_date'])]
days = sorted({d(r[k]) for r in man.values() for k in ('start_date', 'end_date') if r[k] and '1938-01-01' <= d(r[k]) <= '1940-12-31'}
              | {'1938-01-01', '1938-10-15', '1939-04-15', '1939-10-15', '1940-09-15'})
base = unary_union([feats[r] for r in active('1938-01-01')])
out = []
for day in days:
    ids = active(day); issues = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if feats[a].intersects(feats[b]):
                ar = feats[a].intersection(feats[b]).area
                if ar > 0.005: issues.append({'type': 'overlap', 'a': [a, man[a]['name_en'] or man[a]['name']], 'b': [b, man[b]['name_en'] or man[b]['name']], 'area_deg2': round(ar, 3)})
    cov = unary_union([feats[r] for r in ids])
    gap = base.difference(cov)
    big = sorted([g for g in getattr(gap, 'geoms', [gap]) if g.area > 0.05], key=lambda g: -g.area)[:5]
    for g in big:
        c = g.representative_point()
        issues.append({'type': 'gap', 'area_deg2': round(g.area, 3), 'at': [round(c.x, 2), round(c.y, 2)]})
    out.append({'date': day, 'records': len(ids), 'issues': issues})
json.dump(out, open(os.path.join(ROOT, 'qa.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for o in out:
    if o['issues']: print(o['date'], o['records'], json.dumps(o['issues'], ensure_ascii=False))
