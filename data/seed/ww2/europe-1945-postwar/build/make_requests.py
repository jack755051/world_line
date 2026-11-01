#!/usr/bin/env python3
"""歐洲 1945-05-08～1945-09-02（DRAFT，待 Tai 檢查）。
輸入：
- ../db-export/eu45_rows.json：開發庫（5442）唯讀匯出的既有紀錄（要延伸或要沿用幾何的紀錄，含原幾何與出處欄位）
- ../db-export/eu45_active0508.json：1945-05-08 有效紀錄（不含 05-09 截止者）的聯集，用來算德國投降後的空白
- ../db-export/eu45_active0901.json：1945-09-01 既有有效紀錄（QA 用）
- ../borders-ohm-1945-postwar.geojson＋../ohm-manifest.json：新抓的固定版本 OHM（奧地利 2692360、波蘭 1945-08 2692206、蘇聯 1945-08-01 2851943）
輸出：../europe-1945-postwar-derived.geojson（P45_*）、../qa.json、../requests/*.json
"""
import json, os, copy
from shapely.geometry import shape, mapping, MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import set_precision, STRtree
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); OUT = os.path.join(ROOT, 'requests'); DB = os.path.join(ROOT, 'db-export')
END = '1945-09-03'  # 半開區間：含 1945-09-02（日本降伏文書簽字日，試驗期間終點）
MAN = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))}
ohm = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-1945-postwar.geojson')))['features']}
ROWS = {r['slug'] + '|' + r['start']: r for r in json.load(open(os.path.join(DB, 'eu45_rows.json')))}
def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x, 'geoms', []) for p in polys(y)]
def clean(x):
    x = make_valid(set_precision(make_valid(x), 1e-4))
    return MultiPolygon([p for p in polys(x) if p.area > 1e-5])
G = lambda k: make_valid(shape(ROWS[k]['geometry']))
R = lambda k: ROWS[k]
ext_keys = [k for k, r in ROWS.items() if r['end'] == '1945-05-09']
act = unary_union([make_valid(shape(json.load(open(os.path.join(DB, 'eu45_active0508.json')))))] + [G(k) for k in ext_keys])
AT_R, PL_R, SU_R = 2692360, 2692206, 2851943
reich, pla, lux, dod = G('deutsches-reich|1945-01-17'), G('german-annexed-polish-territories|1941-08-01'), G('luxembourg-german-annexation|1940-08-02'), G('german-occupation-dodecanese|1943-09-11')
plp, su_old, ndh, dfy = G('polish-provisional-government-1945|1945-01-17'), G('soviet-union|1945-01-17'), G('independent-state-of-croatia|1943-09-10'), G('democratic-federal-yugoslavia|1945-05-08')
cs = G('czechoslovak-republic|1945-05-08')
gap = reich.difference(act)
AT = clean(ohm[AT_R].intersection(gap))
DE_A = clean(gap.difference(AT))
PL_A = clean(unary_union([plp, pla.difference(act)]))
gain = clean(ohm[SU_R].intersection(unary_union([DE_A, PL_A])).difference(su_old))
SU_B = clean(unary_union([su_old, gain]))
PL_B = clean(unary_union([ohm[PL_R], PL_A]).difference(SU_B).difference(cs).difference(AT))
DE_B = clean(DE_A.difference(PL_B).difference(SU_B))
geo = {'P45_AT': AT, 'P45_DE_A': DE_A, 'P45_DE_B': DE_B, 'P45_PL_A': PL_A, 'P45_PL_B': PL_B, 'P45_SU_B': SU_B,
       'P45_LU': clean(lux.difference(act)), 'P45_DOD': clean(dod.difference(act)), 'P45_YU_B': clean(unary_union([dfy, ndh]))}
for k in ext_keys: geo['COPY_' + R(k)['id']] = shape(ROWS[k]['geometry'])  # 延伸紀錄沿用原幾何（資料庫原樣匯出，不重新簡化）

# QA：抽樣日互不重疊（新紀錄＋未動的既有紀錄）
base0901 = [(x['slug'], make_valid(shape(x['geometry']))) for x in json.load(open(os.path.join(DB, 'eu45_active0901.json')))]
touched = {R(k)['slug'] for k in ext_keys} | {'soviet-union'}
base = [(s, g) for s, g in base0901 if s not in touched]
COPY = lambda slug_start: 'COPY_' + R(slug_start)['id']
EXT = [k for k in ext_keys if not k.startswith(('soviet-union', 'polish-provisional', 'independent-state-of-croatia', 'democratic-federal-yugoslavia'))]
DAYS = {
    '1945-05-08': ['P45_AT', 'P45_DE_A', 'P45_PL_A', 'P45_LU', 'P45_DOD', COPY('soviet-union|1945-01-17'), COPY('independent-state-of-croatia|1943-09-10'), COPY('democratic-federal-yugoslavia|1945-05-08')] + [COPY(k) for k in EXT],
    '1945-06-01': ['P45_AT', 'P45_DE_A', 'P45_PL_A', 'P45_LU', 'P45_DOD', COPY('soviet-union|1945-01-17'), 'P45_YU_B'] + [COPY(k) for k in EXT],
    '1945-09-01': ['P45_AT', 'P45_DE_B', 'P45_PL_B', 'P45_LU', 'P45_DOD', COPY('soviet-union|1945-01-17'), 'QA_SU_GAIN', 'P45_YU_B'] + [COPY(k) for k in EXT],
}
QA_ONLY = {'QA_SU_GAIN': gain}  # 蘇聯 8/2 段＝原幾何（既有）＋新增部分；只檢查新增部分
qa = {'area_deg2': {k: round(v.area, 3) for k, v in geo.items() if not k.startswith('COPY_')}, 'gap_after_surrender_deg2': round(gap.area, 3), 'overlaps': {}}
for d, ks in DAYS.items():
    items = [(k, geo.get(k, QA_ONLY.get(k))) for k in ks] + base
    tree = STRtree([g for _, g in items]); worst = []
    for i, (ni, gi) in enumerate(items):
        for j in tree.query(gi):
            if j <= i: continue
            a = gi.intersection(items[j][1]).area
            if a > 1e-3: worst.append((ni, items[j][0], round(a, 4)))
    qa['overlaps'][d] = worst
    assert not [w for w in worst if w[0].startswith(('P45', 'QA_')) or w[1].startswith(('P45', 'QA_'))], (d, worst)  # COPY＝原樣重送，既有的小重疊照記在 qa.json
# 留白檢查：9/1 德奧波一帶剩下的空白
qa['blank_0901_central_europe_deg2'] = round(reich.union(pla).difference(unary_union([geo.get(k, QA_ONLY.get(k)) for k in DAYS['1945-09-01']])).area, 4)
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in geo.items()]},
          open(os.path.join(ROOT, 'europe-1945-postwar-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(qa, open(os.path.join(ROOT, 'qa.json'), 'w'), indent=1, ensure_ascii=False)

for f in os.listdir(OUT): os.remove(os.path.join(OUT, f)) if f.endswith('.json') else None
def write(name, ph, post, body, meta=None, geom=None):
    req = {'_placeholder': ph, '_post': post, **({'_geometryFrom': geom} if geom else {}), **({'_meta': meta} if meta else {}), 'body': body}
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')

GPO = 'United States Department of State; United States Government Printing Office, Washington'
write('01-source-01-src_ohm_45pw.json', 'SRC_OHM_45PW', '/api/v1/sources', {'sourceKind': 'dataset',
    'title': 'OpenHistoricalMap — boundary=administrative, admin_level=2 關係（奧地利 1945、波蘭 1945-08、蘇聯 1945-08，歐洲 1945-05～09 試驗）',
    'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
    'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
    'publishedText': 'Overpass osm_base %s；逐筆見 europe-1945-postwar/ohm-manifest.json' % MAN[AT_R]['osm_base'],
    'note': 'OHM 整體以 CC0 1.0 釋出；部分成員線段帶 license=CC BY 4.0 標籤（逐筆在主權紀錄標示）。'}, {'priorPlaceholder': False})
for i, (ph, title, url) in enumerate([('SRC_FRUS_1945_BERLIN_I', 'Foreign Relations of the United States: Diplomatic Papers, The Conference of Berlin (The Potsdam Conference), 1945, Volume I', 'frus1945Berlinv01'),
                                      ('SRC_FRUS_1945_BERLIN_II', 'Foreign Relations of the United States: Diplomatic Papers, The Conference of Berlin (The Potsdam Conference), 1945, Volume II', 'frus1945Berlinv02')], 2):
    write(f'01-source-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sources', {'sourceKind': 'official_record', 'title': title, 'publisher': GPO, 'licenseCode': 'us_federal_pd',
          'licenseEvidenceUrl': 'https://www.state.gov/copyright-information', 'url': 'https://history.state.gov/historicaldocuments/' + url}, {'priorPlaceholder': False})

REGIMES = [
    ('REGIME_AOG', 'allied-occupied-germany', 'Allied-occupied Germany', 'en', '盟軍佔領下的德國', 'Allied-occupied Germany', 'FRUS 1945 III Doc. 275（四國 1945-06-05 宣布接管對德國的最高權力）；名稱為通行稱呼'),
    ('REGIME_AT45', 'republic-of-austria-1945', 'Republik Österreich', 'de', '奧地利共和國（盟軍佔領下）', 'Republic of Austria (under Allied occupation)', '原文名為通行稱呼（待查證）；OHM relation/2692360'),
    ('REGIME_PL_TRJN', 'polish-provisional-government-national-unity', 'Tymczasowy Rząd Jedności Narodowej', 'pl', '波蘭全國統一臨時政府', 'Polish Provisional Government of National Unity', 'FRUS 1945 Berlin I Doc. 501（Polish Provisional Government of National Unity）；波蘭文名為通行稱呼'),
    ('REGIME_DOD_BMA', 'british-military-administration-dodecanese', 'British Military Administration of the Dodecanese', 'en', '英軍管理的多德卡尼斯群島', 'British-administered Dodecanese', '名稱為通行稱呼（待查證）'),
]
for i, (ph, slug, orig, lang, zh, en, ns) in enumerate(REGIMES, 1):
    write(f'02-regime-{i:02d}-{slug}.json', ph, '/api/v1/regimes', {'slug': slug, 'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang,
          'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]}, {'priorPlaceholder': False, 'nameSource': ns})

def ev(i, ph, kind, start, zh, en, parts, cites, tn=None, end=None):
    d = datetime_next(start) if end is None else end
    body = {'eventKind': kind, 'occurred': {'start': start, 'end': d}, 'datePrecision': 'day', 'summary': {'zh-Hant': zh, 'en': en},
            'participants': [{'regimeId': '{{%s}}' % r, 'role': role} for r, role in parts],
            'citations': [{'sourceId': '{{%s}}' % s, 'locator': l, 'evidenceNote': n} for s, l, n in cites]}
    if tn: body['timeNote'] = {'zh-Hant': tn[0], 'en': tn[1]}
    write(f'03-event-{i:02d}-{ph.lower()}.json', ph, '/api/v1/events', body, {'verification': 'verified' if cites else 'pending（待查證）'})
import datetime
def datetime_next(s): return (datetime.date.fromisoformat(s) + datetime.timedelta(days=1)).isoformat()
ev(1, 'EV_NDH_END', 'war', '1945-05-08', '南斯拉夫游擊隊進入薩格勒布，克羅埃西亞獨立國瓦解', 'Yugoslav Partisans enter Zagreb; the Independent State of Croatia collapses',
   [('REGIME_DFY', 'belligerent'), ('REGIME_HR', 'belligerent')],
   [('SRC_FRUS_1945_V', 'Doc. 984, pp. 1230–1232', '駐法大使 1945-05 電（訪談馬切克）：其一行 5 月 6 日離開薩格勒布經策列、克拉根福投向美軍；德軍自克羅埃西亞撤退倉促失序。')],
   ('FRUS 只載 5 月 6 日離開薩格勒布與德軍撤退；游擊隊 5 月 8 日進城為通行說法（待查證）。克羅埃西亞獨立國殘部到 5 月 15 日在布萊堡投降，OHM 結束日亦為 1945-05-15，本表取 5 月 8 日。',
    'FRUS records only the departure from Zagreb on 6 May and the German withdrawal; the Partisan entry on 8 May is the common account (pending). Remnants surrendered at Bleiburg on 15 May.'))
ev(2, 'EV_BERLIN_DECL', 'political', '1945-06-05', '柏林宣言：美、蘇、英、法四國宣布接管對德國的最高權力', 'Berlin Declaration: the US, USSR, UK and France assume supreme authority with respect to Germany',
   [('REGIME_US', 'signatory'), ('REGIME_SU', 'signatory'), ('REGIME_UK', 'signatory'), ('REGIME_FR_PROV', 'signatory')],
   [('SRC_FRUS_1945_III', 'Doc. 275, pp. 326–327', '編者註：1945-06-05 在柏林由四國軍事代表簽署「關於德國戰敗並接管最高權力的宣言」，並發表佔領區、管制機構聲明（TIAS 1520）。')])
ev(3, 'EV_PL_RECOG', 'political', '1945-07-05', '美國承認波蘭全國統一臨時政府（6 月 28 日成立）', 'The US recognizes the Polish Provisional Government of National Unity (formed 28 June)',
   [('REGIME_US', 'signatory'), ('REGIME_PL_TRJN', 'signatory')],
   [('SRC_FRUS_1945_BERLIN_I', 'Doc. 501, p. 735', '白宮 1945-07-05 新聞稿：美國自當日 7 p.m.（東部戰時）起與華沙的波蘭全國統一臨時政府建交。'),
    ('SRC_FRUS_1945_BERLIN_I', 'Doc. 496, pp. 731–732', '代理國務卿 1945-07-02 備忘錄附件：波蘭全國統一臨時政府於 1945-06-28 依克里米亞決定成立。')],
   ('英國同日承認為通行說法，此兩件未記載，未列為參與方（待查證）。', 'UK recognition on the same day is the common account but not in these documents (pending).'))
ev(4, 'EV_POTSDAM', 'treaty', '1945-08-02', '波茨坦會議議定書：奧得—尼斯河以東德國領土交波蘭管理、柯尼斯堡及鄰近地區交蘇聯', 'Potsdam Protocol: German territories east of the Oder–Neisse under Polish administration; Königsberg area to the USSR',
   [('REGIME_US', 'signatory'), ('REGIME_UK', 'signatory'), ('REGIME_SU', 'signatory')],
   [('SRC_FRUS_1945_BERLIN_II', 'Doc. 1383, p. 1489', '議定書第 vi 節：會議原則同意蘇聯關於柯尼斯堡市及鄰近地區最終移交蘇聯的提議。'),
    ('SRC_FRUS_1945_BERLIN_II', 'Doc. 1383, p. 1491', '議定書第 ix 節：波蘭西界最終劃定待和約；斯維內明德以西沿奧得河、西尼斯河以東的前德國領土（含東普魯士未交蘇聯部分）由波蘭國家管理，不視為蘇聯佔領區。')],
   ('議定書文件日期為 8 月 1 日，實際在 8 月 2 日凌晨簽字（Doc. 1383 註 1d）；本表取 8 月 2 日。', 'Dated 1 August but signed just after midnight on 2 August (Doc. 1383 n. 1d).'))

# 撤回（I5：修正＝先撤後增）
ret = []
for k in ext_keys:
    r = R(k); ret.append((k, r['id']))
for i, (k, rid) in enumerate(ret, 1):
    write(f'04-retract-{i:02d}-{R(k)["slug"]}.json', f'RETRACTED_{rid}', f'/api/v1/sovereignty-records/{rid}/retraction',
          {'reason': '歐洲 1945-05-08～09-02 延伸：原紀錄以試驗期間終點 1945-05-09 截止（無迄事件），改為延伸或分段後重送'}, {'fix': True, 'oldId': rid})

def copy_body(k, start=None, end=None, sev='keep', eev='keep', note_add=None, geom_from=None, regime=None, layer=None):
    r = R(k)
    b = {'regimeId': regime or r['regimeId'], 'geometry': None, 'validPeriod': {'start': start or r['start'], 'end': end},
         'layerStatus': layer or r['layer'], 'geometrySourceId': r['geometrySourceId'], 'geometryLocator': r['geometryLocator'], 'geometryLicense': r['geometryLicense'],
         'attribution': r['attribution'], 'startEventId': r['startEventId'] if sev == 'keep' else sev, 'endEventId': r['endEventId'] if eev == 'keep' else eev,
         'ohmRelationId': r['ohmRelationId'], 'ohmVersion': r['ohmVersion'], 'ohmFetchedAt': r['ohmFetchedAt'], 'ohmStartRaw': r['ohmStartRaw'], 'ohmEndRaw': r['ohmEndRaw'],
         'provenance': copy.deepcopy(r['provenance']) or {}, 'note': copy.deepcopy(r['note']) or {'zh-Hant': '', 'en': ''}}
    b['provenance']['trialWindow'] = '延伸至 1945-09-02（europe-1945-postwar）'
    if k in ext_keys and (start or r['start']) == r['start']: b['provenance']['replaces'] = r['id']  # 撤回後重送
    else: b['provenance']['geometryBasedOnRecord'] = r['id']  # 新紀錄，幾何由既有紀錄推得（該紀錄不撤回或另有重送）
    if note_add:
        b['note']['zh-Hant'] = (b['note'].get('zh-Hant') or '').replace('本段到 1945-05-09（試驗期間終點，不追溯）。', '') + note_add[0]
        b['note']['en'] = (b['note'].get('en') or '') + ' ' + note_add[1]
    return b, (geom_from or COPY(k))

def lic_of(*items):
    """items：('row', key) 或 ('ohm', relation id)。"""
    cc_by, attrs = False, set()
    for kind, x in items:
        if kind == 'row':
            cc_by |= R(x)['geometryLicense'] == 'cc_by'; attrs |= set((R(x)['attribution'] or '').split('; ')) - {''}
        else:
            cc_by |= MAN[x]['geometry_license'] == 'cc_by'; attrs |= set((MAN[x]['attribution'] or '').split('; ')) - {''}
    return ('cc_by' if cc_by else 'cc0'), ('; '.join(sorted(attrs)) or None)
OL = lambda rid: f'relation/{rid} v{MAN[rid]["ohm_version"]}'
def ohm_fields(b, rid):
    m = MAN[rid]
    b.update({'ohmRelationId': rid, 'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'], 'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date']})
    b['provenance'].update({'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': m['osm_derived_way_count'], 'ohmFixme': m['fixme'],
                            'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'], 'ohmTimestamp': m['ohm_timestamp'], 'coastline': '{{SRC_NE_LAND}}'})

EVDE = '01a1913b-8fe1-7fd1-b8c5-4566cc7afc45'  # EV_DE_SURRENDER（borders-1943-1945）
S = []  # (ph, body, geom)
EXTN = ('延伸至 1945-09-02（試驗期間終點，無迄事件）。', 'Extended to 2 Sep 1945 (end of trial window).')
for k in EXT:
    b, g = copy_body(k, end=END, eev=None, note_add=EXTN); S.append(('SOVP_' + R(k)['slug'].upper().replace('-', '_'), b, g))
# 克羅埃西亞獨立國：同期間重送，補迄事件
k = 'independent-state-of-croatia|1943-09-10'
b, g = copy_body(k, end='1945-05-09', eev='{{EV_NDH_END}}', note_add=('迄於 1945-05-08 游擊隊進入薩格勒布（EV_NDH_END）。', 'Ends with the Partisan entry into Zagreb on 8 May 1945.')); S.append(('SOVP_HR', b, g))
k = 'democratic-federal-yugoslavia|1945-05-08'
b, g = copy_body(k, end='1945-05-09', eev='{{EV_NDH_END}}'); S.append(('SOVP_YU_A', b, g))
b, g = copy_body(k, start='1945-05-09', end=END, sev='{{EV_NDH_END}}', eev=None, geom_from='P45_YU_B',
                 note_add=('1945-05-09 起併入克羅埃西亞獨立國原有範圍（OHM 2747830）。的里雅斯特—威尼斯朱利亞 5–6 月南軍佔領與 6 月 9 日貝爾格勒協定的摩根線未分，簡化（待查證）。延伸至 1945-09-02。',
                           'From 9 May 1945 includes the former NDH area; Trieste/Venezia Giulia and the Morgan Line are not split (pending).'))
nd = R('independent-state-of-croatia|1943-09-10')
b['geometryLocator'] = f"{b['geometryLocator']} ∪ {nd['geometryLocator']}"; b['geometryLicense'], b['attribution'] = lic_of(('row', k), ('row', 'independent-state-of-croatia|1943-09-10'))
b['provenance']['derivedFrom'] = [R(k)['geometryLocator'], nd['geometryLocator']]; b['provenance']['alsoGeometrySourceId'] = nd['geometrySourceId']; b['provenance']['derivation'] = b['geometryLocator']
S.append(('SOVP_YU_B', b, g))
# 蘇聯：同起點重送到波茨坦；之後加柯尼斯堡等地
k = 'soviet-union|1945-01-17'
b, g = copy_body(k, end='1945-08-02', eev='{{EV_POTSDAM}}', note_add=('延伸至 1945-08-02 波茨坦議定書。', 'Extended to the Potsdam Protocol (2 Aug 1945).')); S.append(('SOVP_SU_A', b, g))
b, g = copy_body(k, start='1945-08-02', end=END, sev='{{EV_POTSDAM}}', eev=None, geom_from='P45_SU_B',
                 note_add=('1945-08-02 起加上 OHM 蘇聯 1945-08-01 版（2851943）中原屬德國與德併波蘭地區的部分：柯尼斯堡及鄰近地區（波茨坦議定書第 vi 節）、梅梅爾，以及比亞韋斯托克以東的格羅德諾一帶。1945-08-16 蘇波邊界條約未分段（待查證）。延伸至 1945-09-02。',
                           'From 2 Aug 1945 adds the Königsberg area (Potsdam Protocol sec. vi), Memel and the Grodno area per OHM relation/2851943; the 16 Aug Soviet–Polish border treaty is not split (pending).'))
b['geometrySourceId'] = '{{SRC_OHM_45PW}}'; b['geometryLocator'] = f"{R(k)['geometryLocator']} ∪ ({OL(SU_R)} ∩ 盟軍佔領德國／波蘭臨時政府範圍)"
b['geometryLicense'], b['attribution'] = lic_of(('row', k), ('ohm', SU_R)); b['provenance']['alsoGeometrySourceId'] = R(k)['geometrySourceId']
b['provenance']['derivedFrom'] = [R(k)['geometryLocator'], OL(SU_R)]; b['provenance']['derivation'] = b['geometryLocator']; S.append(('SOVP_SU_B', b, g))
# 波蘭
k = 'polish-provisional-government-1945|1945-01-17'
b, g = copy_body(k, end='1945-05-08', eev=EVDE, note_add=('迄於德國投降（1945-05-08）；其後併入德併波蘭地區另段。', 'Ends at the German surrender; continued with the formerly annexed areas.')); S.append(('SOVP_PL_PROV_A', b, g))
pl_note = ('非主權：原總督府加上德國投降後的德併波蘭西部、北部地區（波茲南、但澤—西普魯士、上西里西亞東部、齊赫瑙），在蘇軍控制下由波蘭臨時政府管轄；美英尚未承認。',
           'Not sovereign: the former Generalgouvernement plus the formerly German-annexed Polish territories after the surrender, under Soviet control; not yet recognized by the US and UK.')
b, g = copy_body(k, start='1945-05-08', end='1945-07-05', sev=EVDE, eev='{{EV_PL_RECOG}}', geom_from='P45_PL_A'); b['note'] = {'zh-Hant': pl_note[0], 'en': pl_note[1]}
pa = R('german-annexed-polish-territories|1941-08-01')
b['geometryLocator'] = f"{R(k)['geometryLocator']} ∪ ({pa['geometryLocator']} − 1945-05-08 其他有效紀錄)"; b['geometryLicense'], b['attribution'] = lic_of(('row', k), ('row', 'german-annexed-polish-territories|1941-08-01'))
b['provenance'].update({'derivedFrom': [R(k)['geometryLocator'], pa['geometryLocator']], 'derivation': b['geometryLocator'], 'alsoGeometrySourceId': pa['geometrySourceId']}); S.append(('SOVP_PL_PROV_B', b, g))
b2 = copy.deepcopy(b); b2.update({'regimeId': '{{REGIME_PL_TRJN}}', 'layerStatus': 'de_jure', 'validPeriod': {'start': '1945-07-05', 'end': '1945-08-02'}, 'startEventId': '{{EV_PL_RECOG}}', 'endEventId': '{{EV_POTSDAM}}',
           'note': {'zh-Hant': '波蘭全國統一臨時政府（1945-06-28 成立，07-05 美英承認，FRUS 1945 Berlin I Doc. 501）；範圍同前段（原總督府＋德併波蘭地區）。',
                    'en': 'Polish Provisional Government of National Unity (formed 28 June, recognized 5 July 1945); same extent as the previous segment.'}})
S.append(('SOVP_PL_TRJN_A', b2, 'P45_PL_A'))
b3 = copy.deepcopy(b2); b3.update({'validPeriod': {'start': '1945-08-02', 'end': END}, 'startEventId': '{{EV_POTSDAM}}', 'endEventId': None, 'geometrySourceId': '{{SRC_OHM_45PW}}',
           'geometryLocator': f'({OL(PL_R)} ∪ 前段範圍) − 蘇聯 − 捷克斯洛伐克 − 奧地利',
           'note': {'zh-Hant': '波蘭全國統一臨時政府；1945-08-02 起含波茨坦議定書第 ix 節交波蘭管理的奧得—尼斯河以東前德國領土（OHM 波蘭 1945-08 版 2692206）。法理上待和約，層級暫列國界（待查證）。延伸至 1945-09-02。',
                    'en': 'Includes the former German territories east of the Oder–Neisse placed under Polish administration (Potsdam Protocol sec. ix), pending the peace settlement.'}})
ohm_fields(b3, PL_R); b3['geometryLicense'], b3['attribution'] = lic_of(('ohm', PL_R), ('row', k), ('row', 'german-annexed-polish-territories|1941-08-01'))
b3['provenance'].update({'derivedFrom': [OL(PL_R), R(k)['geometryLocator'], pa['geometryLocator']], 'derivation': b3['geometryLocator']}); S.append(('SOVP_PL_TRJN_B', b3, 'P45_PL_B'))
# 盟軍佔領下的德國
k = 'deutsches-reich|1945-01-17'
de_note = ('非主權：德國投降後由美、蘇、英、法分區佔領（1945-06-05 柏林宣言四國接管最高權力）。OHM 沒有蘇、法佔領區幾何，未分區（待查證）。',
           'Not sovereign: Germany after the surrender under four-power occupation; zone geometry is not drawn (OHM lacks the Soviet and French zones).')
b, g = copy_body(k, start='1945-05-08', end='1945-08-02', sev=EVDE, eev='{{EV_POTSDAM}}', geom_from='P45_DE_A', regime='{{REGIME_AOG}}', layer='not_sovereign')
b['note'] = {'zh-Hant': de_note[0] + '範圍為投降前德意志國扣掉奧地利（OHM 2692360）與 1945-05-08 已有的其他紀錄（蘇台德、亞爾薩斯—洛林、歐本—馬爾梅迪等已回歸）。', 'en': de_note[1]}
b['geometryLocator'] = f"{R(k)['geometryLocator']} − {OL(AT_R)} − 1945-05-08 其他有效紀錄"; b['geometryLicense'], b['attribution'] = lic_of(('row', k), ('ohm', AT_R))
b['provenance'].update({'derivedFrom': [R(k)['geometryLocator'], OL(AT_R)], 'derivation': b['geometryLocator'], 'alsoGeometrySourceId': '{{SRC_OHM_45PW}}'}); S.append(('SOVP_AOG_A', b, g))
b2 = copy.deepcopy(b); b2.update({'validPeriod': {'start': '1945-08-02', 'end': END}, 'startEventId': '{{EV_POTSDAM}}', 'endEventId': None,
           'geometryLocator': b['geometryLocator'] + f' − 波蘭管理區（{OL(PL_R)}） − 蘇聯（{OL(SU_R)}）',
           'note': {'zh-Hant': de_note[0] + '1945-08-02 起扣掉波茨坦議定書交波蘭管理的奧得—尼斯河以東地區與交蘇聯的柯尼斯堡一帶。延伸至 1945-09-02。', 'en': de_note[1] + ' From 2 Aug 1945 minus the areas east of the Oder–Neisse and Königsberg.'}})
b2['geometryLicense'], b2['attribution'] = lic_of(('row', k), ('ohm', AT_R), ('ohm', PL_R), ('ohm', SU_R)); b2['provenance']['derivedFrom'] += [OL(PL_R), OL(SU_R)]; b2['provenance']['derivation'] = b2['geometryLocator']
S.append(('SOVP_AOG_B', b2, 'P45_DE_B'))
# 奧地利
b = {'regimeId': '{{REGIME_AT45}}', 'geometry': None, 'validPeriod': {'start': '1945-05-08', 'end': END}, 'layerStatus': 'not_sovereign', 'geometrySourceId': '{{SRC_OHM_45PW}}',
     'geometryLocator': f'{OL(AT_R)} ∩ 投降前德意志國範圍', 'startEventId': EVDE, 'endEventId': None, 'provenance': {'derivedFrom': [OL(AT_R), R(k)['geometryLocator']], 'trialWindow': '1945-05-08～09-02'},
     'note': {'zh-Hant': '非主權：奧地利共和國（1945-04-27 倫納臨時政府宣布恢復，OHM 起日；西方盟國到 1945-10 才承認，待查證），在美、蘇、英、法四國佔領下。1945-04-27～05-08 仍畫入德國紀錄，本段自德國投降起。',
              'en': 'Not sovereign: Republic of Austria (provisional government of 27 Apr 1945) under four-power occupation; drawn from the German surrender.'}}
ohm_fields(b, AT_R); b['provenance']['derivation'] = b['geometryLocator']; b['geometryLicense'], b['attribution'] = lic_of(('ohm', AT_R)); S.append(('SOVP_AT45', b, 'P45_AT'))
# 盧森堡、多德卡尼斯
k = 'luxembourg-german-annexation|1940-08-02'
b, g = copy_body(k, start='1945-05-08', end=END, sev=EVDE, eev=None, geom_from='P45_LU', regime='{{REGIME_LU}}', layer='de_jure')
b['note'] = {'zh-Hant': '盧森堡大公國（德國事實併入結束）。實際 1944-09 已大致由盟軍解放，本表併入紀錄畫到德國投降（沿用既有簡化，待查證）。延伸至 1945-09-02。', 'en': 'Grand Duchy of Luxembourg after the end of the German annexation (liberated Sep 1944; earlier records keep the annexation until the surrender, pending).'}
S.append(('SOVP_LU', b, g))
k = 'german-occupation-dodecanese|1943-09-11'
b, g = copy_body(k, start='1945-05-08', end=END, sev=EVDE, eev=None, geom_from='P45_DOD', regime='{{REGIME_DOD_BMA}}', layer='not_sovereign')
b['note'] = {'zh-Hant': '非主權：德軍投降後由英軍管理的多德卡尼斯群島（法理上仍屬義大利，1947 年和約割讓希臘）。德軍在羅德島投降的確切日期與英軍政府成立日待查證，本段自德國投降起。',
             'en': 'Not sovereign: the Dodecanese under British military administration after the German surrender (still Italian de jure); exact dates pending.'}
S.append(('SOVP_DOD', b, g))

for i, (ph, body, g) in enumerate(S, 1):
    write(f'05-sovereignty-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sovereignty-records', body, None, geom=g)

OCC = [
    ('OCCP_AOG', 'REGIME_AOG', 'REGIME_SU', '1945-05-08', EVDE, True, '美、蘇、英、法分區共同佔領（法國 1945-06-05 柏林宣言起正式參與）；缺分區幾何，主要佔領方暫記蘇聯（投降時控制面積最大，待查證）。'),
    ('OCCP_AT45', 'REGIME_AT45', 'REGIME_SU', '1945-05-08', EVDE, True, '美、蘇、英、法分區共同佔領（1945-07-04 管制機構協定、07-09 維也納分區協定，FRUS 1945 III 索引，待查證）；缺分區幾何，主要佔領方暫記蘇聯（維也納與東部）。'),
    ('OCCP_DOD', 'REGIME_DOD_BMA', 'REGIME_UK', '1945-05-08', EVDE, False, '英軍軍政管理（待查證確切起日）。'),
]
for i, (ph, a, b_, start, basis, co, note) in enumerate(OCC, 1):
    write(f'06-occupation-{i:02d}-{ph.lower()}.json', ph, '/api/v1/occupation-attributions', {'occupiedRegimeId': '{{%s}}' % a, 'occupierRegimeId': '{{%s}}' % b_,
          'controlKind': 'military_administration', 'validPeriod': {'start': start, 'end': END}, 'basisEventId': basis if '-' in basis else '{{%s}}' % basis, 'coOccupied': co,
          'note': {'zh-Hant': note, 'en': 'Occupation attribution (see zh-Hant note).'}})
print(json.dumps(qa, ensure_ascii=False)[:3000])
