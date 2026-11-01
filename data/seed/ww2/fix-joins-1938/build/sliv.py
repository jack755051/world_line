from load import *
from shapely.ops import unary_union
cases={'SU':'01a193e1-c433-71fc-a129-3d9c52cca03e','TR':'01a193e1-c4f5-7162-8c47-e82f44cc4779','AL':'01a193e1-b794-7d5d-9c5c-bbdd0ea03146'}
for k,i in cases.items():
    e=BYID[i]; d=e['hi']
    cov=unary_union([r['g'] for r in active(d) if r['g'].intersects(e['g'])])
    P=e['g'].difference(cov)
    print(k,e['slug'],e['lo'],d,'sliver',round(P.area,4))
    # same-regime successors chain
    succ=sorted([r for r in R if r['rid']==e['rid'] and r['lo']>=d],key=lambda r:r['lo'])
    for s in succ[:8]:
        # at s start date, is P covered by active records excluding s? and how much of P is inside s
        others=unary_union([r['g'] for r in active(s['lo']) if r['id']!=s['id'] and r['g'].intersects(P)]) if True else None
        print('   succ',s['lo'],s['hi'],'P∩s',round(P.intersection(s['g']).area,4),'P∩others',round(P.intersection(others).area,4) if not others.is_empty else 0)
    # predecessor
    pred=[r for r in R if r['rid']==e['rid'] and r['hi']==e['lo']]
    for p in pred: print('   pred',p['lo'],p['hi'],'P∩pred',round(P.intersection(p['g']).area,4))
