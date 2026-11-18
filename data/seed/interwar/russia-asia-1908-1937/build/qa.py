import sys, pickle, collections
sys.path.insert(0,'/workspace/ru')
from load import load
import shapely
from shapely.validation import make_valid
from shapely.ops import unary_union
EX=load(); done=pickle.load(open('/workspace/ru/batch/build/done.pkl','rb'))
RET={d['old']['id'] for d in done if d.get('old')}
print('retract',len(RET),'new',len(done))
P0=[r for r in EX if r['id'] not in RET]
for r in P0:
    if not r['g'].is_valid: r['g']=make_valid(r['g'])
recs=[(r['slug'],r['lo'],r['hi'],r['g'],r.get('layer_status'),'P0') for r in P0]+[(d['slug'],d['lo'],d['hi'],d['g'],d['layer'],'N') for d in done]
RU=('russian-empire','russian-provisional-government-1917','russian-sfsr-1917','soviet-union')
dates=['1908-10-05','1910-01-01','1912-06-01','1914-08-01','1916-01-01','1917-06-01','1918-06-01','1919-06-01','1920-03-01','1920-06-01','1921-06-01','1922-06-01','1923-06-01','1924-09-01','1924-12-01','1925-06-01','1927-01-01','1930-01-01','1933-01-01','1936-01-01','1937-07-06','1939-06-01','1942-01-01']
for D in dates:
    act=[x for x in recs if x[1]<=D<x[2]]
    tr=shapely.STRtree([x[3] for x in act]); bad=[]
    for i,x in enumerate(act):
        for j in tr.query(x[3]):
            if j<=i: continue
            y=act[j]
            if 'N' not in (x[5],y[5]): continue
            a=x[3].intersection(y[3]).area
            if a>1e-3: bad.append((x[0],y[0],round(a,4)))
    ru=sum(x[3].area for x in act if x[0] in RU)
    print(D,'active',len(act),'RU area',round(ru,1),'overlaps>1e-3:',bad)
# seams vs existing next records
print('--- seams')
for d in done:
    nxt=[r for r in P0 if r['lo']==d['hi'] and r['slug']==d['slug']]
    for r in nxt:
        print('seam',d['slug'],d['hi'],'symdiff',round(d['g'].symmetric_difference(r['g']).area,3),'areas',round(d['g'].area,1),round(r['g'].area,1))
# also prev
for d in done:
    prv=[r for r in P0 if r['hi']==d['lo'] and r['slug']==d['slug']]
    for r in prv: print('seam-prev',d['slug'],d['lo'],'symdiff',round(d['g'].symmetric_difference(r['g']).area,3))
# gaps at 1937-07-06 vs union of 1937-07-07 records in Asia box
from shapely.geometry import box
B=box(40,15,180,80)
a=unary_union([x[3] for x in recs if x[1]<='1937-07-06'<x[2]]).intersection(B)
b=unary_union([x[3] for x in recs if x[1]<='1937-07-07'<x[2]]).intersection(B)
print('coverage 1937-07-06',round(a.area,1),'1937-07-07',round(b.area,1),'b-a',round(b.difference(a).area,2),'a-b',round(a.difference(b).area,2))
c=unary_union([x[3] for x in recs if x[1]<='1908-10-05'<x[2]]).intersection(B)
print('coverage 1908-10-05',round(c.area,1),'missing vs 1937-07-07',round(b.difference(c).area,2))
m=b.difference(c)
for p in sorted(getattr(m,'geoms',[m]),key=lambda p:-p.area)[:8]: print('  miss',round(p.area,2),p.representative_point())
