from load import *
from shapely.ops import unary_union
import sys
cases={'SU':'01a193e1-c433-71fc-a129-3d9c52cca03e','TR':'01a193e1-c4f5-7162-8c47-e82f44cc4779','AL':'01a193e1-b794-7d5d-9c5c-bbdd0ea03146'}
for k,i in cases.items():
    e=BYID[i]; d=e['hi']
    P=e['g'].difference(unary_union([r['g'] for r in active(d) if r['g'].intersects(e['g'])]))
    dates=sorted({r['lo'] for r in R if r['lo']>=d and r['g'].intersects(P)}|{r['hi'] for r in R if d<=r['hi']<'1946' and r['g'].intersects(P)})
    print(k)
    for dd in dates:
        a=[r for r in active(dd) if r['g'].intersects(P)]
        cov=sum(P.intersection(r['g']).area for r in a)
        print('  ',dd,round(cov,4),sorted({r['slug'] for r in a if P.intersection(r['g']).area>1e-5}))
