#!/usr/bin/env python3
"""tail-1945-09c：(c) 組 13 個政權＋USAMGIK、泰國、spanish-state、蘇丹（plan_1945tail_groupC.md 第 1～15 題；Tai 2026-11-05「照建議」）。
從開發庫 5442（docker worldline-borders-dev-db）讀既有紀錄（以 id 指定）與 PostGIS 算出的衍生幾何 →
requests/*.json、tail-1945-09c-derived.geojson、40-leaders.{dry,commit}.sql、sim.dry.sql（整批模擬＋QA，ROLLBACK）。
只讀資料庫；不連 API。用法：python3 build/make_requests.py
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
END = '1945-10-01'
TAG = 'tail-1945-09c'
REQ = os.path.join(HERE, 'requests')

def q(sql):
    p = subprocess.run(['docker', 'exec', '-i', 'worldline-borders-dev-db', 'psql', '-U', 'worldline', '-d', 'worldline_borders_dev',
                        '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1'], input=sql, capture_output=True, text=True)
    if p.returncode: sys.exit(p.stderr)
    return json.loads(p.stdout.strip() or 'null')

# ---- 既有紀錄 id ----
ID = dict(
 jomal43='01a1943f-c3b6-7f13-ab4d-8a7d5b219165', bmal37='01a1943f-c0d3-71ac-b09c-0d325b9e5f9f', ss37='01a1943f-bf5e-7b14-9e77-6feec7c6ff4b',
 jobor='01a1948d-ad3b-76a3-aaae-9b218b90597f', bnb37='01a1948d-a982-7fd6-a326-bde81d7844c2', sar37='01a1948d-a4aa-722c-ad5f-c6413f0fb78f',
 bru37='01a1948d-a62d-77d4-aecc-c7cb29addff2', jodei='01a1943f-da30-72bc-a07a-93f344fc6694', joic='01a1943f-d5ab-78aa-a7d4-e119e80510d8',
 jokcw='01a1948d-8049-744d-8a2e-6fee6ca01e8d', jonb='01a1948d-b38d-73df-a3c0-e516b6e2c896', tng42='01a1948d-b6c5-7dec-be84-d4f8e805290b',
 tng37='01a1948d-b525-7afa-851b-46927f771830', jotim='01a1948d-b060-7adc-b11b-4a1f1f3029bc', jowake='01a1943f-e8f5-713e-85e7-843c42e468d7',
 usa44='01a1aa96-9b03-788e-9495-9c41c6d6962e', jp45='01a191c9-0ad1-7d5c-af30-6706db83b998', su45='01a1942c-aed4-7ac2-ba6d-0c051586a544',
 th43='01a191c9-0f2a-7cbb-b019-5961b91deb00', th41='01a191c9-0eab-7514-af1f-9994fe206d98', bur45='01a1aa96-8f4a-7dec-abc2-4ca567e4d247',
 esp45='01a19410-2b70-7fe7-a52d-90b9e592322a', spm='01a19410-0c0a-78b6-876e-3407f764d23e', sud45='01a1a27b-cd91-7202-8314-150d490ae4d3',
 egy='01a1aa96-93f5-780d-ae3a-c352eff7932f')
OCC = dict(jomal='01a19440-2dce-7124-974b-b9cee50d4527', jobor='01a1948e-1270-78f1-bfc1-29371bae25e5', jodei='01a19440-2ddd-7ac4-9455-61731ddb77ae',
 joic='01a19440-2df4-7bf9-a8f2-11274620feca', jokcw='01a1948e-1288-7571-9c12-ac479af2e218', jonb='01a1948e-1280-76c4-86cf-512aa2a6fc86',
 jotim='01a1948e-1278-7de7-bb24-c34d79e014b0', jowake='01a19440-2e0a-7fca-89fd-cbe3abf2651d')
CAP = dict(tokyo='01a19ec0-f3e1-7e2a-9d17-04b0c96f897d', moscow='01a19ec0-f549-7215-bbcc-b656022f905f')
LEAD = ['01a19eb7-b387-7522-bab9-13a38211e879', '01a19ebb-17a7-7f6f-9bdf-99e8e43469a6', '01a19ebb-1787-7e9c-873c-5cf1b424ac0b']
EV_THAI = '01a1943f-2e66-712d-aca1-646d1a536e59'; EV_SURR = '01a191c9-0952-7baa-9c62-cbef88437dea'
USA = '01a191b4-36ac-792e-9113-9a46cc51fc9b'; JAPAN = '01a191c9-07d8-7a6d-969f-c702cc8df64c'
SRC_FRUS6 = '01a191c9-07ce-7ff2-9c26-0a20ea97757f'
HULL = "ST_SetSRID(ST_GeomFromText('POLYGON((123.5 32.8,128.5 32.8,128.5 33.2,129.15 34.9,129.6 35.4,131.6 35.4,131.6 38.9,123.5 38.9,123.5 32.8))'),4326)"

# ---- 日期出處（A 級，2026-11-05 查證） ----
DS = {
 'singapore': 'Instrument of Surrender (Singapore), signed 0341 GMT 12 Sep 1945 by Itagaki for Terauchi to Mountbatten — UK National Archives FO 371/46415; Avalon Project text (avalon.law.yale.edu/wwii/j3.asp)',
 'labuan': 'Australian War Memorial 115991／P01542.001／F07316：Labuan 1945-09-10, Lt Gen Masao Baba (37th Army, all Japanese forces in Borneo) surrendered to Maj Gen G. F. Wootten, 9th Australian Division',
 'rabaul': 'Australian War Memorial F07301／C51506：1945-09-06 Gen Imamura (8th Area Army) and V Adm Kusaka signed the Instrument of Surrender on HMS Glory off Rabaul to Lt Gen Sturdee',
 'wewak': 'Australian War Memorial 096232／P00554.003：Cape Wom (Wewak) 1945-09-13, Lt Gen Adachi (18th Army) surrendered to Maj Gen H. C. H. Robertson',
 'wake': 'Naval History and Heritage Command 80-G-490485／NH 96813：Wake surrendered 4 Sep 1945 on board USS Levy (DE-162), R Adm Sakaibara to Brig Gen Sanderson USMC',
 'korea': 'FRUS 1945 Vol. VI Doc. 776：Proclamation No. 1 by General MacArthur, Yokohama 7 Sep 1945 ("will today occupy the territory of Korea south of 38 degrees north latitude"; Art. I all powers of government exercised under his authority)',
 'thai': 'FRUS 1945 Vol. VI Doc. 949, Doc. 957 p. 1294（1945-08-16 泰國和平宣言；馬來四州與撣邦交還英國）',
}
def nz(n, zh, en):
    n = dict(n or {}); n['zh-Hant'] = (n.get('zh-Hant', '') + ' ' + zh).strip(); n['en'] = (n.get('en', '') + ' ' + en).strip(); return n

def sov(i):
    return q(f"""select row_to_json(x) from (select s.id, r.slug, s.regime_id, lower(s.valid_period)::text lo, upper(s.valid_period)::text hi, s.layer_status,
      s.geometry_source_id, s.geometry_locator, s.geometry_license, s.attribution, s.start_event_id, s.end_event_id, s.ohm_relation_id, s.ohm_version, s.ohm_fetched_at,
      s.ohm_start_raw, s.ohm_end_raw, s.provenance, s.note, st_asgeojson(st_multi(s.geom), 15)::json geom
      from sovereignty_records s join regimes r on r.id=s.regime_id where s.id='{i}' and s.retracted_at is null) x;""")
R = {k: sov(v) for k, v in ID.items()}
for k, v in R.items():
    if v is None: sys.exit(f'找不到有效紀錄 {k} {ID[k]}（可能已被撤回）')

def g(expr):
    return q(f"select st_asgeojson(st_multi(st_collectionextract(st_makevalid(({expr})),3)), 15)::json;")
G = lambda k: f"(select geom from sovereignty_records where id='{ID[k]}')"
THDIFF = f"(select (st_dump(st_collectionextract(st_makevalid(st_difference({G('th43')},{G('th41')})),3))).geom gg)"
DER = {
 'D_SK': (g(f"st_intersection({G('jp45')},{HULL})"), f"empire-of-japan {ID['jp45']} ∩ 朝鮮半島北緯 38 度以南框（排除對馬、壹岐、五島）"),
 'D_JP0908': (g(f"st_difference({G('jp45')},{HULL})"), f"empire-of-japan {ID['jp45']} − 同一框（= 原幾何 − USAMGIK）"),
 'D_MALAY4': (g(f"(select st_union(gg) from {THDIFF} t where st_y(st_centroid(gg))<10)"), 'kingdom-of-thailand 1943-10-18 段 − 1941-03-01 段，北緯 10 度以南（馬來四州）'),
 'D_SHAN2': (g(f"(select st_union(gg) from {THDIFF} t where st_y(st_centroid(gg))>19 and st_x(st_centroid(gg))<101)"), 'kingdom-of-thailand 1943-10-18 段 − 1941-03-01 段，北緯 19 度以北、東經 101 度以西（景棟、孟版）'),
}
DER['D_JOMAL0816'] = (g(f"st_union({G('jomal43')}, (select st_union(gg) from {THDIFF} t where st_y(st_centroid(gg))<10))"), f"japanese-occupied-malaya {ID['jomal43']} ∪ D_MALAY4")
DER['D_BUR0816'] = (g(f"st_union({G('bur45')}, (select st_union(gg) from {THDIFF} t where st_y(st_centroid(gg))>19 and st_x(st_centroid(gg))<101))"), f"british-burma {ID['bur45']} ∪ D_SHAN2")
DER['D_USA0904'] = (g(f"st_union({G('usa44')},{G('jowake')})"), f"united-states-of-america {ID['usa44']} ∪ japanese-occupied-wake {ID['jowake']}")
DER['D_ESP'] = (g(f"st_difference({G('esp45')},{G('spm')})"), f"spanish-state {ID['esp45']} − spanish-protectorate-morocco {ID['spm']}")
DER['D_SUD'] = (g(f"st_difference({G('sud45')},{G('egy')})"), f"anglo-egyptian-sudan {ID['sud45']} − kingdom-of-egypt {ID['egy']}")

os.makedirs(REQ, exist_ok=True)
for f in os.listdir(REQ): os.remove(os.path.join(REQ, f))
def w(name, obj): json.dump(obj, open(os.path.join(REQ, name), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
feats = [{'type': 'Feature', 'id': k, 'geometry': v[0], 'properties': {'derivation': v[1]}} for k, v in DER.items()]
seq = [0]
def nxt(prefix): seq[0] += 1; return f'{prefix}-{seq[0]:02d}'

RETRACTED = set()
def retract_sov(k, reason):
    RETRACTED.add(k); s = R[k]; w(f'{nxt("10")}a-retract-{s["slug"]}.json', {'_placeholder': f'RETRACTED_{s["id"]}', '_post': f'/api/v1/sovereignty-records/{s["id"]}/retraction',
        '_meta': {'fix': True, 'oldId': s['id']}, 'body': {'reason': reason}})
def new_sov(k, lo, hi, item, zh, en, geom=None, start_event='keep', end_event=None, regime=None, layer=None, ph=None, extra_prov=None):
    s = R[k]
    if geom is None:
        gid = f'COPY_{s["id"]}'
        if gid not in {f['id'] for f in feats}: feats.append({'type': 'Feature', 'id': gid, 'geometry': s['geom'], 'properties': {'slug': s['slug']}})
    else: gid = geom
    prov = dict(s['provenance'] or {}); prov.update({'geometryFrom': s['id'], 'batch': TAG, 'planItem': item})
    if regime is not None: prov.pop('replaces', None); prov.pop('extendedBy', None); prov['derivedFromRecord'] = s['id']
    elif k in RETRACTED: prov['replaces'] = s['id']
    else: prov.pop('replaces', None); prov.pop('extendedBy', None)
    if geom: prov['derivation'] = DER[geom][1]
    if extra_prov: prov.update(extra_prov)
    slug = s['slug'] if regime is None else 'usamgik'
    body = {'regimeId': regime or s['regime_id'], 'geometry': None, 'validPeriod': {'start': lo, 'end': hi}, 'layerStatus': layer or s['layer_status'],
            'geometrySourceId': s['geometry_source_id'], 'geometryLocator': s['geometry_locator'], 'geometryLicense': s['geometry_license'],
            'attribution': s['attribution'], 'startEventId': s['start_event_id'] if start_event == 'keep' else start_event, 'endEventId': end_event,
            'ohmRelationId': s['ohm_relation_id'], 'ohmVersion': s['ohm_version'], 'ohmFetchedAt': s['ohm_fetched_at'], 'ohmStartRaw': s['ohm_start_raw'],
            'ohmEndRaw': s['ohm_end_raw'], 'provenance': prov, 'note': nz(s['note'] if regime is None else {}, f'【{TAG}】{zh}', f'[{TAG}] {en}')}
    w(f'{nxt("10")}b-sovereignty-{slug}-{lo}.json', {'_placeholder': ph or f'SOVP_C_{slug}_{lo}', '_post': '/api/v1/sovereignty-records', '_geometryFrom': gid, 'body': body})

def occ(i):
    return q(f"""select row_to_json(x) from (select o.id, r.slug, o.occupied_regime_id, o.occupier_regime_id, o.control_kind, lower(o.valid_period)::text lo,
      upper(o.valid_period)::text hi, o.basis_event_id, o.co_occupied, o.note from occupation_attributions o join regimes r on r.id=o.occupied_regime_id where o.id='{i}' and o.retracted_at is null) x;""")
def occ_change(k, hi, reason, zh):
    o = occ(OCC[k]);
    if o is None: sys.exit(f'找不到佔領歸屬 {k}')
    n = nxt('20')
    w(f'{n}a-retract-occ-{o["slug"]}.json', {'_placeholder': f'RETRACTED_{o["id"]}', '_post': f'/api/v1/occupation-attributions/{o["id"]}/retraction', '_meta': {'fix': True, 'oldId': o['id']}, 'body': {'reason': reason}})
    w(f'{n}b-occupation-{o["slug"]}.json', {'_placeholder': f'OCCP_C_{o["slug"]}', '_post': '/api/v1/occupation-attributions', 'body': {'occupiedRegimeId': o['occupied_regime_id'],
       'occupierRegimeId': o['occupier_regime_id'], 'controlKind': o['control_kind'], 'validPeriod': {'start': o['lo'], 'end': hi}, 'basisEventId': o['basis_event_id'],
       'coOccupied': o['co_occupied'], 'note': nz(o['note'], f'【{TAG}】{zh}', f'[{TAG}] Period end {hi} (exclusive).')}})
    return o

RS = lambda item, why: f'(c) 組第 {item} 題（Tai 2026-11-05 照建議，plan_1945tail_groupC.md）：{why}；先撤回、再重寫（{TAG}）'

# ---- 00 新政權與事件（第 11 題） ----
w('00-01-regime-usamgik.json', {'_placeholder': 'REGIME_USAMGIK', '_post': '/api/v1/regimes', '_meta': {'priorPlaceholder': False, 'nameSource': DS['korea']},
   'body': {'slug': 'usamgik', 'wikidataQid': 'Q484104', 'names': [{'nameKind': 'self', 'originalText': 'United States Army Military Government in Korea', 'originalLang': 'en',
     'display': {'zh-Hant': '駐朝鮮美國陸軍軍政廳（北緯 38 度以南的朝鮮，美軍佔領）', 'en': 'United States Army Military Government in Korea (south of the 38th parallel)'}, 'isPrimary': True}]}})
w('00-02-event-usamgik.json', {'_placeholder': 'EV_USAMGIK', '_post': '/api/v1/events', '_meta': {'verification': 'verified'},
   'body': {'eventKind': 'political', 'occurred': {'start': '1945-09-08', 'end': '1945-09-09'}, 'datePrecision': 'day',
     'summary': {'zh-Hant': '美軍在仁川登陸，依麥克阿瑟第 1 號布告對北緯 38 度以南的朝鮮實施軍事管制（駐朝鮮美國陸軍軍政廳）', 'en': 'US forces land at Incheon and establish military control over Korea south of the 38th parallel under MacArthur Proclamation No. 1 (USAMGIK)'},
     'participants': [{'regimeId': USA, 'role': 'other'}, {'regimeId': JAPAN, 'role': 'other'}, {'regimeId': '{{REGIME_USAMGIK}}', 'role': 'other'}],
     'citations': [{'sourceId': SRC_FRUS6, 'locator': 'Doc. 776', 'evidenceNote': '麥克阿瑟第 1 號布告（1945-09-07 橫濱）：麾下部隊「今日」佔領北緯 38 度以南的朝鮮；第 1 條：該地區一切政府權力暫由其權力行使。'}],
     'timeNote': {'zh-Hant': '布告署 09-07；美軍第 24 軍 09-08 於仁川登陸，09-09 進入漢城並受降（駐韓美軍史 HUSA 第 1 卷第 4 章）。起日採 09-08（plan 第 11 題）。', 'en': 'Proclamation dated 7 Sep; XXIV Corps landed at Incheon 8 Sep and took the surrender in Seoul 9 Sep. Start date 8 Sep per plan item 11.'}}})

# ---- 10 主權紀錄 ----
# 第 2、13 題：馬來亞
retract_sov('jomal43', RS('2、13', '日佔馬來亞延到 1945-09-12 新加坡受降；1945-08-16 起併入泰國交出的馬來四州'))
new_sov('jomal43', '1943-10-18', '1945-08-16', '2/13', '分段：1945-08-16 泰國和平宣言前。', 'Split at the Thai peace proclamation (16 Aug 1945).')
new_sov('jomal43', '1945-08-16', '1945-09-12', '2/13', '1945-08-16 起含泰國交出的馬來四州（玻璃市、吉打、吉蘭丹、登嘉樓）；1945-09-12 新加坡受降止。英軍 09-03 登陸檳城、09-05 登陸新加坡。',
        'From 16 Aug 1945 incl. the four Malay states returned by Thailand; ends with the Singapore surrender of 12 Sep 1945.', geom='D_JOMAL0816', start_event=EV_THAI, extra_prov={'dateSource': [DS['thai'], DS['singapore']]})
new_sov('bmal37', '1945-09-12', END, '2', '1945-09-12 新加坡受降後恢復英屬馬來亞（幾何同 1937-07-07～1942-02-15 段）；英軍政府（BMA）只寫在備註。', 'Restored after the Singapore surrender (12 Sep 1945); geometry as 1937–42. British Military Administration noted only.', start_event=None, extra_prov={'dateSource': DS['singapore']})
new_sov('ss37', '1945-09-12', END, '2', '1945-09-12 新加坡受降後恢復海峽殖民地（幾何同 1937-07-07～1942-02-15 段，含納閩）；BMA 只寫在備註。', 'Restored after the Singapore surrender (12 Sep 1945); geometry as 1937–42 (incl. Labuan). BMA noted only.', start_event=None, extra_prov={'dateSource': DS['singapore']})
# 第 3 題：英屬婆羅洲
retract_sov('jobor', RS('3', '日佔英屬婆羅洲延到 1945-09-10 納閩受降'))
new_sov('jobor', '1942-02-15', '1945-09-10', '3', '1945-09-10 納閩受降（馬場正郎向澳軍第 9 師 Wootten 投降，涵蓋婆羅洲全部日軍）止。', 'Ends with the Labuan surrender of all Japanese forces in Borneo (10 Sep 1945).', extra_prov={'dateSource': DS['labuan']})
for k, nm in (('bnb37', '英屬北婆羅洲'), ('sar37', '砂拉越（布洛克王朝）'), ('bru37', '汶萊保護國')):
    new_sov(k, '1945-09-10', END, '3', f'1945-09-10 納閩受降後恢復{nm}（幾何同戰前段）；澳軍／英軍軍政只寫在備註。古晉日軍 09-11 另行受降。', 'Restored after the Labuan surrender (10 Sep 1945); pre-war geometry. Military administration noted only.', start_event=None, extra_prov={'dateSource': DS['labuan']})
# 第 4 題：荷屬東印度
retract_sov('jodei', RS('4', '日佔荷屬東印度原幾何延到 1945-10-01'))
new_sov('jodei', '1942-03-08', END, '4', '延長至 1945-09-30，幾何原樣。1945-08-17 印尼宣布獨立；英軍 1945-09-29 在雅加達登陸。印尼共和國留待第二階段（contested）。', 'Extended to 30 Sep 1945. Indonesia proclaimed independence 17 Aug 1945; British landed at Jakarta 29 Sep 1945. Republic of Indonesia deferred to phase 2.')
# 第 5 題：印度支那
retract_sov('joic', RS('5', '日佔印度支那原幾何延到 1945-10-01'))
new_sov('joic', '1945-03-09', END, '5', '延長至 1945-09-30，幾何原樣。09-02 越南民主共和國成立；北緯 16 度以北由中國軍隊進駐（09-09 進入河內），以南由英軍進駐（09-13 進入西貢）。越南帝國、高棉、寮國留待第二階段。', 'Extended to 30 Sep 1945. DRV proclaimed 2 Sep; Chinese forces north of 16°N (Hanoi 9 Sep), British south (Saigon 13 Sep). Deferred to phase 2.')
# 第 6 題：廣州灣（接收日出處未找到 → 備案）
retract_sov('jokcw', RS('6', '中國接收日出處未找到，依備案日佔段延到 1945-10-01'))
new_sov('jokcw', '1943-02-21', END, '6', '延長至 1945-09-30（備案）：1945-08-18 中法專約交還中國，但中國實際接收日尚無出處，暫不併入中華民國。', 'Extended to 30 Sep 1945 (fallback): returned to China by the Sino-French convention of 18 Aug 1945; takeover date not yet sourced.')
# 第 7 題：新不列顛、新幾內亞
retract_sov('jonb', RS('7', '日佔新不列顛延到 1945-09-06 拉包爾受降'))
new_sov('jonb', '1942-01-23', '1945-09-06', '7', '1945-09-06 拉包爾受降（今村均、草鹿任一於英艦光榮號向 Sturdee 投降）止。', 'Ends with the Rabaul surrender on HMS Glory (6 Sep 1945).', extra_prov={'dateSource': DS['rabaul']})
retract_sov('tng42', RS('7', '新幾內亞委任統治地「1942 起」段延到 1945-09-06，之後恢復 1937 年幾何'))
new_sov('tng42', '1942-01-23', '1945-09-06', '7', '延至 1945-09-06（拉包爾受降，新不列顛等島併回）。', 'Extended to 6 Sep 1945 (Rabaul surrender).', extra_prov={'dateSource': DS['rabaul']})
new_sov('tng37', '1945-09-06', END, '7', '1945-09-06 起恢復 1937 年全境幾何（含新不列顛）；本土日軍 09-13 於威瓦克（Cape Wom）受降，寫在備註。', 'From 6 Sep 1945 the 1937 geometry incl. New Britain; mainland Japanese forces surrendered at Cape Wom (Wewak) 13 Sep 1945.', start_event=None, extra_prov={'dateSource': [DS['rabaul'], DS['wewak']]})
# 第 8 題：葡屬帝汶（日期出處未找到 → 備案）
retract_sov('jotim', RS('8', '葡方恢復日出處未找到，依備案日佔段延到 1945-10-01'))
new_sov('jotim', '1942-02-20', END, '8', '延長至 1945-09-30（備案）：日軍向葡方移交、葡國恢復統治的日期尚無原始出處（上一輪寫的 09-11／09-27 待查證）。', 'Extended to 30 Sep 1945 (fallback): date of handover to Portugal not yet sourced.')
# 第 9 題：威克島
retract_sov('jowake', RS('9', '日佔威克島延到 1945-09-04 受降'))
new_sov('jowake', '1941-12-23', '1945-09-04', '9', '1945-09-04 於美艦 Levy 受降止。', 'Ends with the surrender on USS Levy (4 Sep 1945).', extra_prov={'dateSource': DS['wake']})
retract_sov('usa44', RS('9', '1945-09-04 起威克島併回美國'))
new_sov('usa44', '1944-08-10', '1945-09-04', '9', '分段：1945-09-04 威克島受降前。', 'Split at the Wake surrender (4 Sep 1945).')
new_sov('usa44', '1945-09-04', END, '9', '1945-09-04 起含威克島（約 4 km²）。', 'From 4 Sep 1945 incl. Wake Island.', geom='D_USA0904', start_event=None, extra_prov={'dateSource': DS['wake']})
# 第 10、11 題：日本、USAMGIK
retract_sov('jp45', RS('10、11', '日本 9 月仍為法理主權；1945-09-08 起扣掉北緯 38 度以南的朝鮮（USAMGIK）'))
new_sov('jp45', '1945-08-24', '1945-09-08', '10', '延至 1945-09-08，幾何原樣（9 月仍為法理主權，1952 年和約才變更）。', 'Extended to 8 Sep 1945; geometry unchanged (de jure sovereignty until 1952).')
new_sov('jp45', '1945-09-08', END, '10/11', '1945-09-08 起扣掉北緯 38 度以南的朝鮮（改由 USAMGIK 表示）。盟軍佔領見佔領歸屬；蘇軍佔領南樺太、千島未另表示。', 'From 8 Sep 1945 excluding Korea south of 38°N (USAMGIK).', geom='D_JP0908', start_event='{{EV_USAMGIK}}', extra_prov={'dateSource': DS['korea']})
new_sov('jp45', '1945-09-08', END, '11', '非主權：美軍佔領下的北緯 38 度以南朝鮮（駐朝鮮美國陸軍軍政廳）。法理上仍屬日本，之後另議。與 soviet-civil-administration-korea 對稱。', 'Not sovereign: US-occupied Korea south of the 38th parallel (USAMGIK); mirrors soviet-civil-administration-korea.',
        geom='D_SK', start_event='{{EV_USAMGIK}}', regime='{{REGIME_USAMGIK}}', layer='not_sovereign', ph='SOVP_C_usamgik', extra_prov={'dateSource': DS['korea']})
# 第 12 題：蘇聯
retract_sov('su45', RS('12', '蘇聯原幾何延到 1945-10-01'))
new_sov('su45', '1945-08-02', END, '12', '延長至 1945-09-30，幾何原樣（南樺太、千島 1946-02-02 才併入，不在第一階段）。', 'Extended to 30 Sep 1945; geometry unchanged.')
# 第 13 題：泰國、緬甸
retract_sov('th43', RS('13', '1945-08-16 和平宣言起扣回 1943 年併入的馬來四州與撣邦兩地'))
new_sov('th43', '1943-10-18', '1945-08-16', '13', '分段：1945-08-16 和平宣言前。', 'Split at the peace proclamation (16 Aug 1945).')
new_sov('th41', '1945-08-16', END, '13', '1945-08-16 和平宣言起，幾何用 1941-03-01～1943-08-18 段（保留 1941 年自法屬印度支那取得之地，1946-11 華盛頓協定才歸還）。', 'From 16 Aug 1945 the 1941–43 geometry (territories from French Indochina kept until Nov 1946).', start_event=EV_THAI, extra_prov={'dateSource': DS['thai'], 'replaces': ID['th43']})
retract_sov('bur45', RS('13', '1945-08-16 起併入泰國交出的撣邦兩地'))
new_sov('bur45', '1945-05-03', '1945-08-16', '13', '分段：1945-08-16 泰國和平宣言前。', 'Split at the Thai peace proclamation.')
new_sov('bur45', '1945-08-16', END, '13', '1945-08-16 起含泰國交出的撣邦兩地（景棟、孟版）。', 'From 16 Aug 1945 incl. Kengtung and Mongpan returned by Thailand.', geom='D_BUR0816', start_event=EV_THAI, extra_prov={'dateSource': DS['thai']})
# 第 14 題：西班牙、西屬摩洛哥
retract_sov('esp45', RS('14', '扣掉西屬摩洛哥，解決重疊'))
new_sov('esp45', '1945-09-03', R['esp45']['hi'], '14', '幾何扣掉 spanish-protectorate-morocco（原多 20,723 km²，得土安落在本國內），與 1939-04-01 段一致。', 'Geometry minus the Spanish protectorate in Morocco (overlap of 20,723 km² removed).', geom='D_ESP', end_event=R['esp45']['end_event_id'])
retract_sov('spm', RS('14', '西屬摩洛哥原幾何延到 1945-10-01'))
new_sov('spm', '1926-05-27', END, '14', '延長至 1945-09-30，幾何原樣。', 'Extended to 30 Sep 1945; geometry unchanged.')
# 第 15 題：蘇丹
retract_sov('sud45', RS('15', '扣掉 1934 年已劃給埃及的 18,949 km²，解決與埃及重疊'))
new_sov('sud45', '1945-09-03', END, '15', '幾何扣掉與 kingdom-of-egypt 重疊的 18,949 km²（1934 年已劃給埃及），與 1934-01-01 段一致。', 'Geometry minus the 18,949 km² overlapping Egypt (ceded 1934); matches the 1934 segment.', geom='D_SUD', end_event=R['sud45']['end_event_id'])

# ---- 20 佔領歸屬 ----
occ_change('jomal', '1945-09-12', RS('2', '佔領延到 1945-09-12'), '延至 1945-09-12 新加坡受降。')
occ_change('jobor', '1945-09-10', RS('3', '佔領延到 1945-09-10'), '延至 1945-09-10 納閩受降。')
occ_change('jodei', END, RS('4', '佔領延到 1945-10-01'), '延長至 1945-09-30。')
occ_change('joic', END, RS('5', '佔領延到 1945-10-01'), '延長至 1945-09-30。')
occ_change('jokcw', END, RS('6', '佔領延到 1945-10-01（備案）'), '延長至 1945-09-30（備案，接收日待查）。')
occ_change('jonb', '1945-09-06', RS('7', '佔領延到 1945-09-06'), '延至 1945-09-06 拉包爾受降。')
occ_change('jotim', END, RS('8', '佔領延到 1945-10-01（備案）'), '延長至 1945-09-30（備案，移交日待查）。')
occ_change('jowake', '1945-09-04', RS('9', '佔領延到 1945-09-04'), '延至 1945-09-04 受降。')
w(f'{nxt("20")}-occupation-empire-of-japan.json', {'_placeholder': 'OCCP_C_empire-of-japan', '_post': '/api/v1/occupation-attributions', 'body': {'occupiedRegimeId': JAPAN, 'occupierRegimeId': USA,
   'controlKind': 'military_administration', 'validPeriod': {'start': '1945-09-02', 'end': END}, 'basisEventId': EV_SURR, 'coOccupied': False,
   'note': {'zh-Hant': f'【{TAG}】盟軍（美國主導，盟軍最高司令官總司令部）佔領日本本土，1945-09-02 降伏文書起；日本政府存續、間接統治。南樺太、千島的蘇軍佔領與北緯 38 度以南朝鮮（USAMGIK）不在此歸屬內。（plan 第 10 題）',
            'en': f'[{TAG}] Allied (US-led, SCAP) occupation of the Japanese home islands from the Instrument of Surrender (2 Sep 1945); indirect rule. Soviet-occupied Karafuto/Kurils and Korea are not covered.'}}})
w(f'{nxt("20")}-occupation-usamgik.json', {'_placeholder': 'OCCP_C_usamgik', '_post': '/api/v1/occupation-attributions', 'body': {'occupiedRegimeId': '{{REGIME_USAMGIK}}', 'occupierRegimeId': USA,
   'controlKind': 'military_administration', 'validPeriod': {'start': '1945-09-08', 'end': END}, 'basisEventId': '{{EV_USAMGIK}}', 'coOccupied': False,
   'note': {'zh-Hant': f'【{TAG}】美軍佔領，軍政廳（與 soviet-civil-administration-korea 對稱）。', 'en': f'[{TAG}] US military occupation, military government.'}}})

# ---- 30 首都 ----
for k in ('tokyo', 'moscow'):
    c = q(f"""select row_to_json(x) from (select c.id, r.slug, c.regime_id, c.city_name, st_asgeojson(c.location)::json loc, lower(c.valid_period)::text lo, upper(c.valid_period)::text hi,
      c.source_ref, c.note from capital_records c join regimes r on r.id=c.regime_id where c.id='{CAP[k]}' and c.retracted_at is null) x;""")
    if c is None: sys.exit(f'找不到首都 {k}')
    n = nxt('30')
    w(f'{n}a-retract-cap-{c["slug"]}.json', {'_placeholder': f'RETRACTED_{c["id"]}', '_post': f'/api/v1/capital-records/{c["id"]}/retraction', '_meta': {'fix': True, 'oldId': c['id']},
       'body': {'reason': RS('10' if k == 'tokyo' else '12', '首都延到 1945-10-01')}})
    w(f'{n}b-capital-{c["slug"]}.json', {'_placeholder': f'CAP_C_{c["slug"]}', '_post': '/api/v1/capital-records', 'body': {'regimeId': c['regime_id'], 'cityName': c['city_name'], 'location': c['loc'],
       'validStart': c['lo'], 'validEnd': END, 'sourceRef': c['source_ref'], 'note': ((c['note'] or '') + f' 【{TAG}】延長至 1945-09-30（第一階段終點）。').strip()}})

json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(HERE, f'{TAG}-derived.geojson'), 'w'))

# ---- 40 領導人（API 無撤回端點，沿用 SQL 撤回＋同交易新增） ----
ids = "','".join(LEAD); REASON_L = RS('10、12', '領導人延到 1945-10-01')
body = f"""\\set ON_ERROR_STOP 1
BEGIN;
CREATE TEMP TABLE t_old ON COMMIT DROP AS SELECT * FROM leader_records WHERE id IN ('{ids}') AND retracted_at IS NULL;
UPDATE leader_records SET retracted_at=now(), retraction_reason='{REASON_L}' WHERE id IN (SELECT id FROM t_old);
INSERT INTO leader_records(id,regime_id,name,name_zh,role,title,valid_period,source,source_url,verified,person_id)
  SELECT uuidv7(),regime_id,name,name_zh,role,title,daterange(lower(valid_period),'{END}','[)'),source,source_url,verified,person_id FROM t_old;
SELECT 'LEADERS', (SELECT count(*) FROM t_old) retracted, (SELECT count(*) FROM leader_records WHERE retracted_at IS NULL AND upper(valid_period)='{END}' AND (regime_id,role,name) IN (SELECT regime_id,role,name FROM t_old)) active_extended;
"""
open(os.path.join(HERE, '40-leaders.dry.sql'), 'w').write(body + 'ROLLBACK;\n')
open(os.path.join(HERE, '40-leaders.commit.sql'), 'w').write(body + 'COMMIT;\n')
areas = {k: q(f"select round((st_area(st_geomfromgeojson('{json.dumps(v[0])}')::geography)/1e6)::numeric)") for k, v in DER.items() if k not in ('D_USA0904',)}
json.dump({'requests': len(os.listdir(REQ)), 'derivedAreasKm2': areas}, open(os.path.join(HERE, 'qa.json'), 'w'), ensure_ascii=False, indent=1)
print('requests', len(os.listdir(REQ)), 'derived', areas)
