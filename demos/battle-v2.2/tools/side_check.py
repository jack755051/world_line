"""檢查每個地面部隊在關鍵日是否位於己方控制區（schema v2：用 fronts[].control.axis 的 MultiPolygon，含包圍圈）。
另檢查：被包圍（encircled）的盟軍單位應在某個口袋裡。只出警告。"""
import json
from shapely.geometry import shape, Point, Polygon
d=json.load(open('data/dunkirk-1940.example.json'))
side={u['id']:(u['side'],u['domain']) for u in d['units']}
ctrl={f['date']:shape(f['control']['axis']) for f in d['fronts']}
pk={f['date']:[Polygon(p['ring']) for p in f.get('pockets',[])] for f in d['fronts']}
w=[]
for p in d['positions']:
    s,dm=side[p['unit_id']]
    if dm!='ground' or p['state'] in ('surrendered',): continue
    pt=Point(p['lng'],p['lat'])
    if p['state']=='encircled' and s=='allied':
        if pk[p['date']] and not any(g.contains(pt) for g in pk[p['date']]): w.append(f"{p['date']} {p['unit_id']} encircled but not in a pocket")
        continue
    inside=ctrl[p['date']].contains(pt)
    if (s=='axis')!=inside: w.append(f"{p['date']} {p['unit_id']} ({p['lng']},{p['lat']}) on wrong side")
print(len(w),'warnings'); print('\n'.join(w))
json.dump(w,open('data/side-check.json','w'),ensure_ascii=False,indent=1)
