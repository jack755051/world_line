"""接點修補（1924～1945）：產生 requests/F1/*.json。幾何運算在 box 上算出小塊（補縫多邊形），送出時才在開發庫以 PostGIS 與既有幾何合併（避免把整個蘇聯幾何寫進版控）。"""
import json, os
from load import *
from shapely.ops import unary_union
from shapely.geometry import mapping, MultiPolygon, Polygon
from shapely.validation import make_valid
from shapely import set_precision
OUT='requests/F1'; os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT): os.remove(os.path.join(OUT,f))
def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x,'geoms',[]) for p in polys(y)]
def clean(x, minarea=1e-6):
    x = make_valid(set_precision(make_valid(x), 1e-6))
    ps=[p for p in polys(x) if p.area>minarea]
    return MultiPolygon(ps) if ps else None
def others_over(lo,hi,excl,g):
    gs=[r['g'] for r in R if r['lo']<hi and r['hi']>lo and r['id'] not in excl and r['g'].intersects(g)]
    return unary_union(gs) if gs else Polygon()
N=[0]; QA=[]
def emit(ph, post, d):
    N[0]+=1; fn=f'{OUT}/{N[0]:03d}-{ph.lower()}.json'
    json.dump(dict(_placeholder=ph,_post=post,**d), open(fn,'w'), ensure_ascii=False, indent=1)
def retract(ph_key, rid, reason):
    emit('RETRACTED_'+ph_key, f'/api/v1/sovereignty-records/{rid}/retraction', dict(_meta={'fix':True}, body={'reason':reason}))
def readd(ph, base, override, union=None, note_zh=None, note_en=None, geomFrom=None):
    d=dict(_meta={'fix':True}, _readd={'base':base,'geomFrom':geomFrom or base,'union':mapping(union) if union is not None else None,
           'noteAppend':{'zh-Hant':note_zh,'en':note_en} if note_zh else None}, body=override)
    emit(ph,'/api/v1/sovereignty-records',d)
ANSCHLUSS_DE36='01a18e71-d2b0-742c-8579-30af75ea0474'
SUDETEN_EV='01a18e93-72ad-7bf8-aa97-a2374b09a19f'
TAG='接點修補 2026-11-01'
# 1. 德國 1935-03-01～1938-03-13 合併（1936-07-03 只是 OHM 換版，無歷史事件）
DEI='01a193e2-1479-7c0d-9b8e-c733308d4248'
retract('DE_I', DEI, f'{TAG}：1936-07-03 只是 OHM 換版（兩版幾何差約 0.0004 平方度），無歷史事件、缺迄事件；與既有 1936-07-03 起紀錄合併為 1935-03-01～1938-03-13（SOV_DE_J）')
retract('DE_1936', ANSCHLUSS_DE36, f'{TAG}：與 1935-03-01 起紀錄合併為 1935-03-01～1938-03-13（SOV_DE_J）；1936-07-03 只是 OHM 換版')
readd('SOV_DE_J', ANSCHLUSS_DE36, {'validPeriod':{'start':'1935-03-01','end':'1938-03-13'},'startEventId':'@'+DEI+'.startEventId'},
      note_zh='合併：1935-03-01（薩爾回歸）起的 OHM 2694638 v245 與 1936-07-03 起的 OHM 2693085 v290 兩筆；兩版幾何差約 0.0004 平方度，1936-07-03 只是 OHM 換版、無歷史事件，幾何取後者。',
      note_en='Merged the 1935-03-01 (Saar) and 1936-07-03 records; 1936-07-03 is only an OHM version change (no historical event).')
# 2. 捷克斯洛伐克：1924-03-12～1938-10-01 合併；1938-10-01 起（蘇台德分區進駐）
CSE='01a193e1-b88e-7425-bb48-6fa5d1ec1863'; CS36='01a18e71-d1c8-742d-854c-8a577f35110e'; CS30='01a18e71-d210-7981-8724-854dc836c51c'
retract('CS_E', CSE, f'{TAG}：1936-07-03 只是 OHM 換版、無迄事件；與既有 1936-07-03 起紀錄合併（SOV_CS_J）')
retract('CS_1936', CS36, f'{TAG}：迄日 1938-09-30 改 1938-10-01（德軍 10-01 才依慕尼黑協定進駐蘇台德，原本 09-30 當天蘇台德留白）；並與 1924-03-12 起紀錄合併（SOV_CS_J）')
retract('CS_1938_09_30', CS30, f'{TAG}：起日 1938-09-30 改 1938-10-01（蘇台德 10-01 起另列德軍分區進駐），避免 09-30 留白（SOV_CS_K）')
readd('SOV_CS_J', CS36, {'validPeriod':{'start':'1924-03-12','end':'1938-10-01'},'startEventId':'@'+CSE+'.startEventId','endEventId':SUDETEN_EV},
      note_zh='合併：1924-03-12（亞沃日納）起的 OHM 2692233 v107 與 1936-07-03 起的 OHM 2692764 v97；兩版幾何差約 0.0001 平方度，1936-07-03 只是 OHM 換版，幾何取後者。迄日 1938-10-01：慕尼黑協定 09-30 簽字，德軍 10-01 起分區進駐蘇台德。',
      note_en='Merged 1924-03-12 and 1936-07-03 records; ends 1938-10-01 when German troops began occupying the Sudetenland.')
readd('SOV_CS_K', CS30, {'validPeriod':{'start':'1938-10-01','end':'1938-11-02'},'startEventId':SUDETEN_EV},
      note_zh='起日由 1938-09-30（OHM）改 1938-10-01，接蘇台德德軍分區進駐紀錄。', note_en='Start moved to 1938-10-01 to meet the Sudeten occupation record.')
# 3. 梅梅爾：德國改 1939-03-23 起含梅梅爾（立陶宛既有紀錄到 03-23）
D16='01a1920c-f877-75d1-85ba-6eac4589b677'; D22='01a1920c-f948-77fb-a3ab-b65ffb782931'
retract('DE_1939_03_16', D16, f'{TAG}：迄日 1939-03-22 改 1939-03-23（梅梅爾 03-23 才移交；原本 03-22 一天與立陶宛重疊）')
retract('DE_1939_03_22', D22, f'{TAG}：起日 1939-03-22 改 1939-03-23（立陶宛 03-23 交出梅梅爾，避免與立陶宛重疊一天）')
readd('SOV_DE_1939_03_16B', D16, {'validPeriod':{'start':'1939-03-16','end':'1939-03-23'}},
      note_zh='迄日由 03-22 改 03-23：梅梅爾條約 03-22 在柏林簽字，立陶宛 03-23 交出、德軍進駐。', note_en='End moved to 23 Mar 1939 (Memel handed over on 23 Mar).')
readd('SOV_DE_1939_03_23', D22, {'validPeriod':{'start':'1939-03-23','end':'1939-09-01'}},
      note_zh='起日由 03-22 改 03-23，接立陶宛既有紀錄（03-23 交出梅梅爾），避免重疊。', note_en='Start moved to 23 Mar 1939 to meet the Lithuania record.')
# 4. 西班牙國：補西屬撒哈拉、伊夫尼、加那利缺塊
ES='01a18e71-d632-7698-97ca-44b90e4d4c1b'; esr=BYID[ES]
prev=[r for r in R if r['hi']=='1939-04-01' and r['slug'] in ('spanish-nationalist-zone','spanish-republic')]
cont=[r for r in R if r['hi']=='1939-01-01' and r['slug'] in ('spanish-protectorate-morocco','tangier-international-zone','french-protectorate-morocco','mauritania-french-1912')]
add=unary_union([r['g'] for r in prev]).difference(esr['g'])
oth=unary_union([others_over('1939-04-01','1956-04-07',{ES}|{r['id'] for r in prev},add)]+[r['g'] for r in cont])
add=clean(add.difference(oth), 1e-5)
QA.append(('ES add', round(add.area,4), len(add.geoms)))
retract('ES_STATE', ES, f'{TAG}：既有幾何缺西屬撒哈拉、伊夫尼與部分加那利島嶼，1939-04-01 接點留白；補上後重送（SOV_ES_STATE_B）')
readd('SOV_ES_STATE_B', ES, {}, union=add,
      note_zh='補上西屬撒哈拉、伊夫尼與加那利群島缺塊（取自 1939-04-01 前的國民軍／共和國紀錄幾何，即 OHM 2862762 v19；扣除同期其他紀錄）。',
      note_en='Added Spanish Sahara, Ifni and missing Canary Islands (from OHM 2862762 v19 via the 1939-03 records).')
# 5. 阿爾巴尼亞共和國 1925-01-21：補細縫
ALA='01a193e1-b7b1-744a-a151-ab48bd621e73'; ALP='01a193e1-b794-7d5d-9c5c-bbdd0ea03146'
P=BYID[ALP]['g'].difference(unary_union([r['g'] for r in active('1925-01-21')]))
P=clean(P.difference(others_over('1925-01-21','1926-07-26',{ALA,ALP},P)),1e-5); QA.append(('AL sliver',round(P.area,4)))
retract('AL_REP_A', ALA, f'{TAG}：1925-01-21 接點與前一筆阿爾巴尼亞公國紀錄有約 0.024 平方度細縫（OHM 版本差），補上後重送（SOV_AL_REP_A2）')
readd('SOV_AL_REP_A2', ALA, {}, union=P, note_zh='補上與前一筆（OHM 2800556）之間的細縫（約 0.024 平方度，OHM 版本差）。', note_en='Filled a 0.024 deg² sliver against the previous record.')
# 6. 土耳其 1924-08-06：補細縫（分段：1926-01-01 起有一部分在蘇聯紀錄內）
TRA='01a193e1-c4f5-7162-8c47-e82f44cc4779'; TR24='01a191da-1e2d-7b1a-9056-b2b01358dddc'
TR39=[r for r in R if r['slug']=='republic-of-turkey' and r['lo']=='1939-06-29'][0]['id']
P=BYID[TRA]['g'].difference(unary_union([r['g'] for r in active('1924-08-06')]))
Pa=clean(P.difference(others_over('1924-08-06','1926-01-01',{TRA,TR24,TR39},P)),1e-6)
Pb=clean(P.difference(others_over('1926-01-01','1939-06-29',{TRA,TR24,TR39},P)),1e-6)
Pc=clean(P.difference(others_over('1939-06-29','1964-05-15',{TRA,TR24,TR39},P)).difference(BYID[TR39]['g']),1e-6)
QA.append(('TR sliver',round(P.area,4),round(Pa.area,4),round(Pb.area,4) if Pb else 0,round(Pc.area,4) if Pc else 0))
retract('TR_1924', TR24, f'{TAG}：1924-08-06 接點與土耳其 1923-10-29 紀錄有約 0.036 平方度細縫（土伊邊界，OHM 版本差）；補上後分兩段重送（1926-01-01 起其中一部分已在蘇聯紀錄內）')
readd('SOV_TR_1924A', TR24, {'validPeriod':{'start':'1924-08-06','end':'1926-01-01'},'endEventId':None}, union=Pa,
      note_zh='補上與 1923-10-29 起紀錄之間的細縫（約 0.036 平方度，OHM 版本差）。1926-01-01 分段只因其中約 0.013 平方度從那天起在蘇聯紀錄內，不是歷史事件。', note_en='Sliver filled; split at 1926-01-01 only because part of it lies in the Soviet record from then.')
readd('SOV_TR_1924B', TR24, {'validPeriod':{'start':'1926-01-01','end':'1939-06-29'},'startEventId':None}, union=Pb,
      note_zh='補上細縫中不與蘇聯紀錄重疊的部分。1926-01-01 分段不是歷史事件。', note_en='Sliver part not overlapping the Soviet record; 1926-01-01 split is not a historical event.')
if Pc is not None:
    retract('TR_1939', TR39, f'{TAG}：補上 1924-08-06 起紀錄同一塊細縫（不與蘇聯重疊部分），避免 1939-06-29 再出現細縫')
    readd('SOV_TR_1939B', TR39, {}, union=Pc, note_zh='補上土伊邊界細縫（與 1924～1939 紀錄一致）。', note_en='Same Turkey–Iran border sliver as 1924–1939.')
# 7. 蘇聯 1926-01-01 起各筆：補海岸與北極島嶼細縫
SUB='01a193e1-c433-71fc-a129-3d9c52cca03e'
P=BYID[SUB]['g'].difference(unary_union([r['g'] for r in active('1926-01-01') if r['g'].intersects(BYID[SUB]['g'])]))
P=clean(P,1e-6); QA.append(('SU sliver',round(P.area,4),len(P.geoms)))
sus=sorted([r for r in R if r['slug']=='soviet-union' and r['lo']>='1926-01-01' and r['lo']<'1945-09-03'], key=lambda r:r['lo'])
for r in sus:
    o=others_over(r['lo'],r['hi'],{x['id'] for x in sus},P)
    Pr=clean(P.difference(o).difference(r['g']),1e-6)
    if Pr is None: continue
    k=r['lo'].replace('-','_')
    retract(f'SU_{k}', r['id'], f'{TAG}：補上 1926-01-01 接點出現的海岸與北極島嶼細縫（合計約 0.44 平方度，前一筆 OHM 2851271 有、這批紀錄沒有）')
    readd(f'SOV_SU_{k}_B', r['id'], {}, union=Pr, note_zh='補上海岸與北極島嶼細縫（約 0.44 平方度，取自 1925 年紀錄 OHM 2851271；扣除同期其他紀錄）。', note_en='Filled coastal/Arctic slivers (~0.44 deg²) from OHM 2851271.')
    QA.append(('SU rec',r['lo'],r['hi'],round(Pr.area,4)))
json.dump(QA, open('qa-fix.json','w'), ensure_ascii=False, indent=1)
for q in QA: print(q)
print('requests', N[0])
