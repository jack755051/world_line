from load import *
from shapely.ops import unary_union
def others_over(lo,hi,excl,g):
    return unary_union([r['g'] for r in R if r['lo']<hi and r['hi']>lo and r['id'] not in excl and r['g'].intersects(g)])
DEI=BYID['01a193e2-1479-7c0d-9b8e-c733308d4248']; DE36=BYID['01a18e71-d2b0-742c-8579-30af75ea0474']
CSE=BYID['01a193e1-b88e-7425-bb48-6fa5d1ec1863']; CS36=BYID['01a18e71-d1c8-742d-854c-8a577f35110e']
print('DE symdiff',round(DEI['g'].symmetric_difference(DE36['g']).area,4),'CS symdiff',round(CSE['g'].symmetric_difference(CS36['g']).area,4))
ex={DEI['id'],DE36['id'],CSE['id'],CS36['id']}
for name,g,lo,hi in [('DEI',DEI['g'],'1935-03-01','1938-03-13'),('DE36',DE36['g'],'1935-03-01','1938-03-13'),('CSE',CSE['g'],'1924-03-12','1938-10-01'),('CS36',CS36['g'],'1924-03-12','1938-10-01')]:
    o=others_over(lo,hi,ex,g)
    print(name,'overlap others over merged period',round(g.intersection(o).area,4))
# overlap between DE and CS candidates
for a,b in [('DEI','CSE'),('DE36','CS36'),('DEI','CS36'),('DE36','CSE')]:
    print(a,b,round(locals()[a]['g'].intersection(locals()[b]['g']).area if False else 0,4))
print('DE36∩CS36',round(DE36['g'].intersection(CS36['g']).area,5),'DEI∩CSE',round(DEI['g'].intersection(CSE['g']).area,5),'DE36∩CSE',round(DE36['g'].intersection(CSE['g']).area,5),'DEI∩CS36',round(DEI['g'].intersection(CS36['g']).area,5))
# which others overlap
for name,g,lo,hi in [('DE36',DE36['g'],'1935-03-01','1938-03-13'),('CS36',CS36['g'],'1924-03-12','1938-10-01'),('DEI',DEI['g'],'1935-03-01','1938-03-13'),('CSE',CSE['g'],'1924-03-12','1938-10-01')]:
    for r in R:
        if r['lo']<hi and r['hi']>lo and r['id'] not in ex and r['g'].intersects(g):
            a=r['g'].intersection(g).area
            if a>1e-4: print('  ',name,r['slug'],r['lo'],r['hi'],round(a,4))
