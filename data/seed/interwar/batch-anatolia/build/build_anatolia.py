#!/usr/bin/env python3
"""安納托利亞 1920-04-23～1922-11-01：安卡拉大國民議會政府自有領土（先撤後增）。
既有鄂圖曼帝國 5 筆主權紀錄（開發庫）撤回後重送：
- 1919-05-15～1920-08-10 那筆在 1920-04-23 切成兩段（前段幾何不變）；
- 1920-04-23 起鄂圖曼只留伊斯坦堡與海峽區（協約國佔領下）、東色雷斯與其他原有範圍；
- 安卡拉政府＝原鄂圖曼紀錄 ∩ 安納托利亞（Natural Earth 1:10m Admin-1 v5.1.1 土耳其各省，扣掉伊斯坦堡、科賈埃利、亞洛瓦、恰納卡萊與色雷斯三省）。
希臘士麥那區、東色雷斯、法屬敘利亞（阿勒坡國）、亞美尼亞等既有紀錄不動（原鄂圖曼紀錄本來就已扣掉）。
幾何由 send_seed2 的 _readd 在資料庫內計算：鄂圖曼＝base − ANKARA_AREA；安卡拉＝base − (BOX − ANKARA_AREA)。
輸入：../exp_anatolia.json（開發庫唯讀匯出）、../ne/ne_10m_admin_1_states_provinces.shp。輸出：../requests/A/*.json、../qa.json。
"""
import json, os, glob
import shapefile
from shapely.geometry import shape, mapping, box
from shapely.ops import unary_union
from shapely.validation import make_valid
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
STRAITS = {'Istanbul', 'Kocaeli', 'Yalova', 'Çanakkale'}
THRACE = {'Edirne', 'Kirklareli', 'Tekirdag'}
r = shapefile.Reader(os.path.join(ROOT, 'ne', 'ne_10m_admin_1_states_provinces.shp'), encoding='utf-8')
fl = [f[0] for f in r.fields[1:]]; ia, inn = fl.index('adm0_a3'), fl.index('name')
prov = {rec[inn]: make_valid(shape(sh.__geo_interface__)) for sh, rec in zip(r.shapes(), r.records()) if rec[ia] == 'TUR'}
assert STRAITS | THRACE <= set(prov), set(prov)
OTHER = make_valid(unary_union([g for n, g in prov.items() if n not in STRAITS | THRACE]).buffer(0))
STR = make_valid(unary_union([prov[n] for n in STRAITS]))
NW = make_valid(unary_union([prov[n] for n in STRAITS | THRACE]))
BOX = box(-30, -10, 90, 70)   # 要大於原紀錄範圍（1920-08 前含阿拉伯半島）
# 現代省界與 OHM 1920 年海岸、邊界不完全一致：各往外擴 0.05°（約 5 km）吸收沿岸碎片。
KEEP = make_valid(NW.buffer(0.05).difference(OTHER))                 # 留給鄂圖曼的西北區（海峽區＋色雷斯）
ANK1 = make_valid(OTHER.buffer(0.05).difference(KEEP))               # 1920-04-23～08-10：原紀錄含阿拉伯地區，只取安納托利亞
ANK2 = make_valid(BOX.difference(KEEP))                              # 1920-08-10 起：原紀錄只剩安納托利亞與東色雷斯
ANK = ANK1
def J(g): return mapping(g.simplify(0.0005))
SUB_OTT = [J(ANK1)] + [J(ANK2)] * 4                                  # 鄂圖曼重送時扣掉的範圍
SUB_ANK = [J(BOX.difference(ANK1))] + [J(KEEP)] * 4                  # 安卡拉＝原紀錄扣掉這些
F = {f['id']: f for f in json.load(open(os.path.join(ROOT, 'exp_anatolia.json')))['features']}
GNA = '01a193a2-bef1-7786-9b0f-2339f992c043'
EV_GNA = '01a193a3-2528-70e6-afbe-b302867abdfc'
OTT = ['01a193a2-ccbe-75d8-b7e8-9cb362527216', '01a193a3-2cfd-754b-9813-4b6f0f80a5d1', '01a193a3-2d32-7860-b1c2-727aafa8477d',
       '01a193a3-2d65-7197-af62-e24fe7706762', '01a193a3-59c4-7539-a67c-008379400ed3']
for o in OTT: assert F[o]['properties']['slug'] == 'ottoman-empire', o
NE_LOC = 'Natural Earth 1:10m Admin-1 v5.1.1（公有領域）土耳其各省'
ANK_LOC = f' ∩ 安納托利亞（{NE_LOC}，扣掉伊斯坦堡、科賈埃利、亞洛瓦、恰納卡萊與埃迪爾內、克爾克拉雷利、泰基爾達；方法近似）'
OTT_LOC = f' − 安卡拉政府控制區（{NE_LOC}；伊斯坦堡、科賈埃利、亞洛瓦、恰納卡萊留鄂圖曼；方法近似）'
TRIAL = '安納托利亞 1920-04-23～1922-11-01：安卡拉大國民議會政府另列領土'
OTT_NOTE = {'zh-Hant': '鄂圖曼帝國（伊斯坦堡政府）：1920-04-23 起只留伊斯坦堡與海峽區（1920-03-16 起協約國正式佔領伊斯坦堡）、東色雷斯（1920-08 起由希臘佔領，另列）與原紀錄其他範圍；'
            '安納托利亞另列安卡拉大國民議會政府。海峽區以現代省界（伊斯坦堡、科賈埃利、亞洛瓦、恰納卡萊）近似，未依協約國實際駐軍線劃（待查證）；'
            '伊茲密特 1921-06 由安卡拉軍收復未分段（待查證）。',
            'en': 'Ottoman (Istanbul) government: from 23 Apr 1920 only Istanbul and the Straits (Allied occupation from 16 Mar 1920), Eastern Thrace and the rest of the original record; '
                  'Anatolia is drawn as the Ankara Grand National Assembly government. The Straits zone is approximated by modern provinces (pending); İzmit (retaken Jun 1921) not split.'}
ANK_NOTE = {'zh-Hant': '非主權：安卡拉大國民議會政府（1920-04-23 開議）實際控制的安納托利亞；洛桑條約前未獲國際承認為主權政府，伊斯坦堡的鄂圖曼政府名義上仍存在。'
            '範圍＝原鄂圖曼紀錄 ∩ 現代土耳其安納托利亞各省（扣掉海峽區），方法近似（待查證）。希臘士麥那區、法國佔領的奇里乞亞（未另列，1920-08 前落在本區，待查證）、'
            '義大利安塔利亞駐軍（未另列）、亞美尼亞等不另扣。',
            'en': 'Not sovereign: Anatolia under the de facto control of the Ankara Grand National Assembly government (opened 23 Apr 1920); not recognised as sovereign before Lausanne. '
                  'Extent = original Ottoman record ∩ modern Anatolian provinces (excluding the Straits), approximate (pending). French Cilicia and the Italian Antalya presence are not drawn separately.'}
REQ = []
def add(cat, name, ph, post, body, readd=None, meta=None):
    REQ.append(dict(cat=cat, name=name, ph=ph, post=post, body=body, readd=readd, meta=meta))
for i, o in enumerate(OTT, 1):
    add('04-retract', f'retract_ott_{i}', f'RETRACTED_OTT_{i}', f'/api/v1/sovereignty-records/{o}/retraction',
        {'reason': f'{TRIAL}：鄂圖曼紀錄扣掉安卡拉政府控制的安納托利亞後重送（1919-05-15 那筆在 1920-04-23 切段）'}, meta={'fix': True})
o1 = F[OTT[0]]['properties']
add('05-sovereignty', 'sov_ott_1a', 'SOV_OTT_1A', '/api/v1/sovereignty-records',
    {'validPeriod': {'start': o1['lo'], 'end': '1920-04-23'}, 'endEventId': EV_GNA, 'geometryLocator': '@locator（1920-04-23 切段，幾何不變）'},
    readd={'base': OTT[0], 'geomFrom': OTT[0], 'union': None, 'subtract': None, 'noteAppend': None}, meta={'readdFrom': OTT[0]})
for i, o in enumerate(OTT, 1):
    p = F[o]['properties']; lo = max(p['lo'], '1920-04-23')
    b = {'validPeriod': {'start': lo, 'end': p['hi']}, 'geometryLocator': '@locator' + OTT_LOC, 'note': OTT_NOTE}
    if i == 1: b['startEventId'] = EV_GNA
    add('05-sovereignty', f'sov_ott_{i}' + ('b' if i == 1 else ''), f'SOV_OTT_{i}' + ('B' if i == 1 else ''), '/api/v1/sovereignty-records', b,
        readd={'base': o, 'geomFrom': o, 'union': None, 'subtract': SUB_OTT[i - 1], 'noteAppend': None}, meta={'readdFrom': o})
for i, o in enumerate(OTT, 1):
    p = F[o]['properties']; lo = max(p['lo'], '1920-04-23')
    b = {'regimeId': GNA, 'validPeriod': {'start': lo, 'end': p['hi']}, 'layerStatus': 'not_sovereign', 'geometryLocator': '@locator' + ANK_LOC, 'note': ANK_NOTE}
    if i == 1: b['startEventId'] = EV_GNA
    add('06-sovereignty', f'sov_gna_{i}', f'SOV_GNA_{i}', '/api/v1/sovereignty-records', b,
        readd={'base': o, 'geomFrom': o, 'union': None, 'subtract': SUB_ANK[i - 1], 'noteAppend': None}, meta={'readdFrom': o})
# QA（本地近似；正式幾何由資料庫計算）
QA = []
for o in OTT:
    p = F[o]['properties']; g = make_valid(shape(F[o]['geometry'])); k = OTT.index(o)
    A = ANK1 if k == 0 else ANK2
    a_ank = g.intersection(A).area; a_ott = g.difference(A).area; a_str = g.intersection(STR).area
    ottg = g.difference(A); parts = sorted([round(x.area, 4) for x in getattr(ottg, 'geoms', [ottg])], reverse=True)
    others = [(f['properties']['slug'], round(make_valid(shape(f['geometry'])).intersection(g.intersection(A)).area, 4)) for f in F.values()
              if f['id'] != o and f['properties']['lo'] < p['hi'] and f['properties']['hi'] > max(p['lo'], '1920-04-23')
              and f['properties']['slug'] != 'ottoman-empire' and shape(f['geometry']).intersects(g)]
    QA.append({'record': o, 'period': [p['lo'], p['hi']], 'area': round(g.area, 3), 'ankara': round(a_ank, 3), 'ottoman_left': round(a_ott, 3), 'straits': round(a_str, 3), 'ottoman_parts': parts[:8], 'n_parts': len(parts),
               'overlap_with_others_in_ankara': [x for x in others if x[1] > 0.002]})
D = os.path.join(ROOT, 'requests', 'A'); os.makedirs(D, exist_ok=True)
for f in glob.glob(os.path.join(D, '*.json')): os.remove(f)
cnt = {}
for q in REQ:
    cnt[q['cat']] = cnt.get(q['cat'], 0) + 1
    o = {'_placeholder': q['ph'], '_post': q['post']}
    if q['meta']: o['_meta'] = q['meta']
    if q['readd']: o['_readd'] = q['readd']
    o['body'] = q['body']
    json.dump(o, open(os.path.join(D, f"{q['cat']}-{cnt[q['cat']]:02d}-{q['name']}.json"), 'w'), ensure_ascii=False, indent=1)
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': 'ANKARA_AREA_1920A', 'properties': {}, 'geometry': J(ANK1)}, {'type': 'Feature', 'id': 'OTTOMAN_KEEP', 'properties': {}, 'geometry': J(KEEP)},
                                                     {'type': 'Feature', 'id': 'STRAITS', 'properties': {}, 'geometry': mapping(STR.simplify(0.0005))}]},
          open(os.path.join(ROOT, 'anatolia-areas.geojson'), 'w'), separators=(',', ':'))
json.dump(QA, open(os.path.join(ROOT, 'qa.json'), 'w'), ensure_ascii=False, indent=1)
print(len(REQ), cnt); [print(q) for q in QA]
