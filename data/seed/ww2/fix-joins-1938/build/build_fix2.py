"""接點修補第二段：蘇台德分區進駐紀錄（整塊簡化）與捷克斯洛伐克之間 1938-10-01～10-10 約 0.11 平方度細縫。"""
import json, os
from load import *
from shapely.ops import unary_union
from shapely.geometry import mapping, MultiPolygon, Polygon
from shapely.validation import make_valid
from shapely import set_precision
def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x,'geoms',[]) for p in polys(y)]
OUT='requests/F2'; os.makedirs(OUT, exist_ok=True)
CS36='01a18e71-d1c8-742d-854c-8a577f35110e'; CS30='01a18e71-d210-7981-8724-854dc836c51c'
SUD=[r for r in R if r['slug']=='sudeten-german-occupation-1938'][0]
others=[r for r in R if r['lo']<'1938-10-10' and r['hi']>'1938-10-01' and r['id'] not in (CS36,CS30,SUD['id'])]
P=BYID[CS36]['g'].difference(BYID[CS30]['g']).difference(SUD['g'])
P=P.difference(unary_union([r['g'] for r in others if r['g'].intersects(P)]))
P=make_valid(set_precision(make_valid(P),1e-6)); P=MultiPolygon([p for p in polys(P) if p.area>1e-6])
print('fill', round(P.area,4), len(P.geoms))
json.dump(dict(_placeholder='RETRACTED_SUDETEN_OCC',_post=f"/api/v1/sovereignty-records/{SUD['id']}/retraction",_meta={'fix':True},
  body={'reason':'接點修補 2026-11-01：蘇台德分區進駐紀錄是整塊簡化幾何，與捷克斯洛伐克（10-01 起）之間有約 0.11 平方度細縫；補上後重送'}),open(f'{OUT}/001-retracted_sudeten_occ.json','w'),ensure_ascii=False,indent=1)
json.dump(dict(_placeholder='SOV_SUDETEN_OCC_B',_post='/api/v1/sovereignty-records',_meta={'fix':True},
  _readd={'base':SUD['id'],'geomFrom':SUD['id'],'union':mapping(P),'noteAppend':{'zh-Hant':'補上與捷克斯洛伐克 1938-09-30 版（OHM 2747874）之間的細縫（約 0.11 平方度），即 1938-10-01 前捷克斯洛伐克範圍扣掉 10-01 後範圍的其餘部分。','en':'Filled ~0.11 deg² sliver against the Czechoslovakia record from 1938-10-01.'}},body={}),
  open(f'{OUT}/002-sov_sudeten_occ_b.json','w'),ensure_ascii=False,indent=1)
