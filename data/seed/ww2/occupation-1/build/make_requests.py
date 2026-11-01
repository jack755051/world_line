#!/usr/bin/env python3
"""佔領區依佔領國上色（2026-10-31 Tai）：資料部分（DRAFT，待 Tai 檢查；只寫開發庫 5052）。
A. 既有非主權政權（帝國專員轄區、軍政府、佔領區…）補「佔領歸屬」（佔領方＋控制程度＋依據事件；依據事件沒有引用＝待查證）。
B. 大德意志國紀錄原本把保護國、總督府、併入區都算在德國（法理）內：自 1939-03-16 起逐段撤回，改為
   德國本土（法理）＋保護國、總督府（民政，中等）＋併入的波蘭地區、奧伊彭—馬爾梅迪、亞爾薩斯—摩澤爾、盧森堡、斯洛維尼亞北部（事實併入，最深），
   後者皆為非主權（無國際承認的割讓）。幾何：同一 OHM 版本的德國紀錄 ∩ 戰前國家紀錄（開發庫既有、OHM 固定版本），總督府用 OHM relation/2693083、2693084。
輸入：build/input/*.txt（唯讀 SQL 匯出）。
"""
import json, os, sys, itertools
from shapely.geometry import shape, mapping, MultiPolygon, Polygon, box
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); IN = os.path.join(HERE, 'input'); OUT = os.path.join(ROOT, 'requests')
sys.argv = sys.argv[:1]
exec(open('/workspace/data/seed/ww2/unclip-su-tr/build/build.py').read().split('rows = []')[0])  # polys/mp/full/raw helpers
def clean(g): return mp(set_precision(make_valid(g), 1e-4), 1e-4)
def write(name, req):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f: json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')
REGIME = {l.split('|')[0]: l.split('|')[1].strip() for l in open(os.path.join(IN, 'occupiers.txt')) if '|' in l and not l.startswith('slug')}
DE = REGIME['deutsches-reich']
# ── 戰前國家幾何（開發庫既有） ──
pre = {}
for l in open(os.path.join(IN, 'prewar.txt')):
    p = l.rstrip('\n').split('|', 2)
    if len(p) == 3 and p[2].startswith('{'): pre[p[1]] = make_valid(shape(json.loads(p[2])))
CS2, PL39, FR39, LUX, BE, YU = (pre[k] for k in ('czechoslovak-republic', 'polish-republic', 'french-third-republic', 'grand-duchy-of-luxembourg', 'kingdom-of-belgium', 'kingdom-of-yugoslavia'))
PRE_LOC = {'czechoslovak-republic': 'relation/2857482 v25', 'polish-republic': 'relation/2741574 v118', 'french-third-republic': 'relation/2696299 v155',
           'grand-duchy-of-luxembourg': 'relation/2748545 v31', 'kingdom-of-belgium': 'relation/2800293 v50', 'kingdom-of-yugoslavia': 'relation/2747831 v50'}
# ── 總督府（OHM 固定版本 raw） ──
land_bb = box(-12, 34, 42, 72)
land = unary_union([make_valid(shape(s.__geo_interface__)).intersection(land_bb) for s in sf.shapes() if box(*s.bbox).intersects(land_bb)])
GG = {}
for rid, ver in ((2693083, 72), (2693084, 96)):
    fn = f'/workspace/wl/ohmocc/raw/r{rid}.json'; x = json.load(open(fn)); rel = [e for e in x['elements'] if e['type'] == 'relation'][0]
    assert rel['version'] == ver, (rid, rel['version'])
    GG[rid] = (full(x, rel, land), rel, open(fn + '.fetched').read().strip())
# ── 德國紀錄 ──
rows = []
for l in open(os.path.join(IN, 'reich.txt')):
    p = l.rstrip('\n').split('|', 1)
    if len(p) == 2 and p[0].startswith('{'): rows.append((json.loads(p[0]), make_valid(shape(json.loads(p[1])))))
EV = {'PROT': '01a18e71-cec4-76b5-8377-684b0ab0a984', 'PL': '01a18e71-cf25-7f93-89d2-c586ccb608ad', 'GG': '01a18e96-f155-7988-84ae-5c2075dd8759',
      'EUPEN': '01a18e71-cf56-7d64-b3c6-e939fdefdb53', 'WEST': '01a18e71-cfdc-78aa-9f78-3a7c39d456d7', 'SLO': '01a19134-d0ad-76c8-abfd-2b6400aaa8fe',
      'GG_END': '01a1913b-8fd7-7b1f-884a-bd320e0b9451', 'GALICIA': '01a18ff5-a2a7-7247-992d-2125e63f5ead'}
AREAS = [  # key, regime placeholder, slug, 原文名, lang, 中文, 英文, 控制程度, 起日, 依據事件, 推導說明
 ('PROT', 'REGIME_PROTECTORATE_BM', 'protectorate-bohemia-moravia', 'Protektorat Böhmen und Mähren', 'de', '波希米亞—摩拉維亞保護國（德國）', 'Protectorate of Bohemia and Moravia (German)', 'civil_administration', '1939-03-16', 'PROT', 'czechoslovak-republic'),
 ('GG', 'REGIME_GENERALGOUVERNEMENT', 'generalgouvernement', 'Generalgouvernement', 'de', '總督府（德佔波蘭）', 'General Government (German-occupied Poland)', 'civil_administration', '1939-10-26', 'GG', None),
 ('PL', 'REGIME_DE_ANNEX_PL', 'german-annexed-polish-territories', 'Eingegliederte Ostgebiete', 'de', '德國併入的波蘭西部與北部地區', 'Polish territories annexed by Germany', 'annexed', '1939-10-26', 'PL', 'polish-republic'),
 ('EUPEN', 'REGIME_DE_ANNEX_EUPEN', 'eupen-malmedy-german-annexation', 'Eupen-Malmedy', 'de', '奧伊彭—馬爾梅迪（德國併入）', 'Eupen-Malmedy (annexed by Germany)', 'annexed', '1940-05-18', 'EUPEN', 'kingdom-of-belgium'),
 ('AM', 'REGIME_DE_ANNEX_ALSACE_MOSELLE', 'alsace-moselle-german-annexation', 'CdZ-Gebiete Elsass und Lothringen', 'de', '亞爾薩斯—摩澤爾（德國事實併入）', 'Alsace-Moselle (de facto annexed by Germany)', 'annexed', '1940-08-02', 'WEST', 'french-third-republic'),
 ('LUX', 'REGIME_DE_ANNEX_LUX', 'luxembourg-german-annexation', 'CdZ-Gebiet Luxemburg', 'de', '盧森堡（德國事實併入）', 'Luxembourg (de facto annexed by Germany)', 'annexed', '1940-08-02', 'WEST', 'grand-duchy-of-luxembourg'),
 ('SLO', 'REGIME_DE_ANNEX_SLO', 'northern-slovenia-german-annexation', 'Untersteiermark und Oberkrain', 'de', '斯洛維尼亞北部（德國事實併入：下施蒂利亞、上卡尼奧拉）', 'Northern Slovenia (de facto annexed by Germany)', 'annexed', '1941-04-14', 'SLO', 'kingdom-of-yugoslavia'),
]
PREG = {'czechoslovak-republic': CS2, 'polish-republic': PL39, 'french-third-republic': FR39, 'grand-duchy-of-luxembourg': LUX, 'kingdom-of-belgium': BE, 'kingdom-of-yugoslavia': YU}
pieces = []  # (row, {area: geom}, reich_geom)
for r, g in rows:
    a, b = r['valid_period'][1:11], r['valid_period'][12:22]
    got, used = {}, []
    if a >= '1939-10-26' and a < '1945-01-17':
        rid = 2693083 if a < '1941-08-01' else 2693084
        got['GG'] = clean(g.intersection(GG[rid][0]))
    for key, _, _, _, _, _, _, _, start, _, prewar in AREAS:
        if key == 'GG' or a < start: continue
        x = g.intersection(PREG[prewar])
        if key == 'PL': x = x.difference(unary_union([got.get('GG', Polygon()), CS2]))
        got[key] = clean(x)
    got = {k: v for k, v in got.items() if v.area > 0.01}
    reich = clean(g.difference(unary_union(list(got.values())))) if got else g
    pieces.append((r, got, reich, a, b))
    print(a, b, 'reich', round(g.area, 2), '→', round(reich.area, 2), {k: round(v.area, 2) for k, v in got.items()})
# 批內不重疊
for r, got, reich, a, b in pieces:
    for (k1, g1), (k2, g2) in itertools.combinations(list(got.items()) + [('REICH', reich)], 2):
        assert g1.intersection(g2).area < 1e-3, (a, k1, k2, g1.intersection(g2).area)

derived, n = {}, 0
# 1) regimes
for i, (key, ph, slug, orig, lang, zh, en, kind, start, evk, prewar) in enumerate(AREAS, 1):
    write(f'01-regime-{i:02d}-{slug}.json', {'_placeholder': ph, '_post': '/api/v1/regimes', '_meta': {'priorPlaceholder': False, 'nameSource': 'OHM relation name（德文行政名稱）或通行的德文官方稱呼；中文為描述性譯名'},
          'body': {'slug': slug, 'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]}})
# 2) 撤回德國紀錄＋新增：德國本土＋各區（同一區連續段幾何相同就合併）
segs = {k[0]: [] for k in AREAS}
for r, got, reich, a, b in pieces:
    for k, geom in got.items():
        s = segs[k]
        if s and s[-1]['end'] == a and s[-1]['geom'].symmetric_difference(geom).area < 1e-3: s[-1]['end'] = b; s[-1]['end_event'] = r['end_event_id']; s[-1]['rows'].append(r)
        else: s.append({'start': a, 'end': b, 'geom': geom, 'start_event': r['start_event_id'], 'end_event': r['end_event_id'], 'rows': [r]})
def loc_of(r): return r['geometry_locator']
for i, (r, got, reich, a, b) in enumerate(pieces, 1):
    if not got: continue
    write(f'02-{i:02d}a-retract-reich-{a}.json', {'_placeholder': f'RETRACTED_OCC_REICH_{a}', '_post': f"/api/v1/sovereignty-records/{r['id']}/retraction", '_meta': {'fix': True},
          'body': {'reason': '德意志國：原紀錄把保護國、總督府與事實併入區都算在德國法理國土內，地圖看不出佔領；改以 occupation-1 拆成德國本土（法理）與各佔領／併入區（非主權），撤回後重新新增。'}})
    gid = f'R_{a}'; derived[gid] = reich
    prov = dict(r['provenance'] or {}); prov['occupationSplit'] = {'batch': 'occupation-1', 'replaces': r['id'], 'removed': sorted(got)}
    note = dict(r['note'] or {})
    note = {'zh-Hant': (note.get('zh-Hant') or '') + '（2026-10-31：保護國、總督府與事實併入區另列為非主權佔領／併入區。）',
            'en': ((note.get('en') or '') + ' (2026-10-31: protectorate, General Government and de facto annexed areas listed separately as non-sovereign.)').strip()}
    write(f'02-{i:02d}b-sovereignty-reich-{a}.json', {'_placeholder': f'OCC_REICH_{a}', '_post': '/api/v1/sovereignty-records', '_geometryFrom': gid,
          'body': {'regimeId': r['regime_id'], 'geometry': None, 'validPeriod': {'start': a, 'end': b}, 'layerStatus': 'de_jure',
                   'geometrySourceId': r['geometry_source_id'], 'geometryLocator': loc_of(r) + ' − 保護國、總督府與事實併入區', 'geometryLicense': r['geometry_license'], 'attribution': r['attribution'],
                   'startEventId': r['start_event_id'], 'endEventId': r['end_event_id'], 'ohmRelationId': r['ohm_relation_id'], 'ohmVersion': r['ohm_version'],
                   'ohmFetchedAt': r['ohm_fetched_at'], 'ohmStartRaw': r['ohm_start_raw'], 'ohmEndRaw': r['ohm_end_raw'], 'provenance': prov, 'note': note}})
AREA = {x[0]: x for x in AREAS}
j = 0
for key, ss in segs.items():
    _, ph, slug, orig, lang, zh, en, kind, start, evk, prewar = AREA[key]
    for s in ss:
        j += 1; r0 = s['rows'][0]; gid = f'A_{key}_{s["start"]}'; derived[gid] = s['geom']
        if key == 'GG':
            rid = 2693083 if s['start'] < '1941-08-01' else 2693084; _, rel, fetched = GG[rid]
            ohm = {'ohmRelationId': rid, 'ohmVersion': rel['version'], 'ohmFetchedAt': fetched, 'ohmStartRaw': rel['tags'].get('start_date'), 'ohmEndRaw': rel['tags'].get('end_date')}
            loc = f"relation/{rid} v{rel['version']} ∩ ({' / '.join(sorted({loc_of(x) for x in s['rows']}))})"
            lic, attr = 'cc0', None
        else:
            ohm = {'ohmRelationId': r0['ohm_relation_id'], 'ohmVersion': r0['ohm_version'], 'ohmFetchedAt': r0['ohm_fetched_at'], 'ohmStartRaw': r0['ohm_start_raw'], 'ohmEndRaw': r0['ohm_end_raw']}
            loc = f"({' / '.join(sorted({loc_of(x) for x in s['rows']}))}) ∩ {PRE_LOC[prewar]}" + ('（扣總督府、保護國）' if key == 'PL' else '')
            lic, attr = r0['geometry_license'], r0['attribution']
        sev = EV[evk] if s['start'] == start else s['start_event']
        eev = EV['GG_END'] if key == 'GG' and s['end'] == '1945-01-17' else s['end_event']
        write(f'03-{j:02d}-sovereignty-{key.lower()}-{s["start"]}.json', {'_placeholder': f'OCC_{key}_{s["start"]}', '_post': '/api/v1/sovereignty-records', '_geometryFrom': gid,
              'body': {'regimeId': '{{%s}}' % ph, 'geometry': None, 'validPeriod': {'start': s['start'], 'end': s['end']}, 'layerStatus': 'not_sovereign',
                       'geometrySourceId': r0['geometry_source_id'], 'geometryLocator': loc, 'geometryLicense': lic, 'attribution': attr,
                       'startEventId': sev, 'endEventId': eev, **ohm,
                       'provenance': {'batch': 'occupation-1', 'derivedFrom': [x['id'] for x in s['rows']], 'coastline': (r0['provenance'] or {}).get('coastline')},
                       'note': {'zh-Hant': f'非主權：{zh}。幾何為同期德國 OHM 紀錄與戰前國界的交集' + ('，扣除總督府與保護國' if key == 'PL' else '') + '；國際上未承認割讓。' + ('總督府內部各區（克拉科夫、華沙、拉多姆、盧布林、加利西亞）OHM 資料不全，未分；保留總督府與德國本土、併入區之間的界線。' if key == 'GG' else '') + ('1944-45 盟軍收復（如 1944-11 斯特拉斯堡）尚未分段，仍畫到德國紀錄結束（待查證）。' if key in ('AM', 'LUX', 'EUPEN') else ''),
                                'en': f'Not sovereign: {en}. Geometry = German OHM record ∩ pre-war state boundary.'}}})
# 3) 佔領歸屬
NS = {}
for l in open(os.path.join(IN, 'ns.txt')):
    p = l.rstrip('\n').split('|')
    if len(p) >= 6 and p[0] != 'slug': NS[p[0]] = dict(id=p[1], start=p[2], end=p[3], sev=p[4] or None, eev=p[5] or None)
O = lambda s: REGIME[s]
ATT = [  # 被佔領政權, 佔領方, 控制程度, 起, 迄, 依據事件, 共同佔領, 註記
 ('sudeten-german-occupation-1938', 'deutsches-reich', 'military_administration', None, None, None, False, '慕尼黑協定下德軍分區進駐。'),
 ('german-military-administration-poland', 'deutsches-reich', 'military_administration', None, None, None, False, ''),
 ('kingdom-of-denmark', 'deutsches-reich', 'military_administration', None, None, None, False, '「保護佔領」：丹麥政府名義存續至 1943-08-29，德國全權代表監督；歸入軍事管理（最淺），待拍板。'),
 ('reichskommissariat-norwegen', 'deutsches-reich', 'civil_administration', None, None, None, False, '帝國專員轄區。'),
 ('reichskommissariat-niederlande', 'deutsches-reich', 'civil_administration', None, None, None, False, '帝國專員轄區。'),
 ('mil-admin-belgium-northern-france', 'deutsches-reich', 'military_administration', None, None, None, False, '軍政府。'),
 ('military-commander-serbia', 'deutsches-reich', 'military_administration', None, None, None, False, '軍事指揮官轄區（內迪奇傀儡政府）。'),
 ('occupied-greece-hellenic-state', 'kingdom-of-italy', 'military_administration', None, '1943-09-08', None, True, '德、義、保共同佔領；缺分區幾何，主要佔領方暫記義大利（佔大部分地區，待查證）。'),
 ('occupied-greece-hellenic-state', 'deutsches-reich', 'military_administration', '1943-09-08', None, '01a191a0-45bd-788e-b2c7-e6e0604c1fc7', True, '義大利停戰後德軍接管義大利佔領區；保加利亞佔領區另計。'),
 ('reichskommissariat-ostland', 'deutsches-reich', 'civil_administration', None, None, None, False, '帝國專員轄區。'),
 ('transnistria-governorate', 'kingdom-of-romania', 'civil_administration', None, None, None, False, '羅馬尼亞總督轄區（不主張領土）。'),
 ('reichskommissariat-ukraine', 'deutsches-reich', 'civil_administration', None, None, None, False, '帝國專員轄區。'),
 ('italian-governorate-montenegro', 'kingdom-of-italy', 'military_administration', None, None, None, False, '義大利軍事總督轄區。'),
 ('french-north-africa-allied-occupation', 'united-states-of-america', 'military_administration', None, None, None, True, '英美共同軍事佔領；主要佔領方暫記美國（登陸主力，待查證）。'),
 ('french-state-vichy', 'deutsches-reich', 'military_administration', None, None, None, False, '1942-11-11 起德國全面佔領法國本土（義大利佔領區另列）。'),
 ('italian-occupation-zone-france', 'kingdom-of-italy', 'military_administration', None, None, None, False, ''),
 ('german-occupation-albania', 'deutsches-reich', 'military_administration', None, None, None, False, ''),
 ('german-occupation-italy-operational-zones', 'deutsches-reich', 'civil_administration', None, None, None, False, '作戰區（阿爾卑斯山麓、亞得里亞海沿岸）由大區長官兼最高專員治理，歸入民政（中等）。'),
 ('german-occupation-dodecanese', 'deutsches-reich', 'military_administration', None, None, None, False, ''),
 ('german-occupation-montenegro', 'deutsches-reich', 'military_administration', None, None, None, False, ''),
 ('amgot-italy', 'united-states-of-america', 'military_administration', None, None, None, True, '盟軍（英美）軍政府；主要佔領方暫記美國（待查證）。'),
 ('italian-social-republic', 'deutsches-reich', 'military_administration', None, None, None, False, '德國扶植的傀儡政權名義治理，德軍佔領。'),
 ('kingdom-of-hungary', 'deutsches-reich', 'military_administration', None, None, None, False, '1944-03-19 德軍佔領匈牙利。'),
 ('reichskommissariat-belgien-nordfrankreich', 'deutsches-reich', 'civil_administration', None, None, None, False, '帝國專員公署。'),
 ('soviet-civil-administration-korea', 'soviet-union', 'military_administration', None, None, None, False, '蘇軍佔領，民政署。'),
]
k = 0
for occ, by, kind, s0, e0, ev, co, nzh in ATT:
    x = NS[occ]; k += 1
    s, e = s0 or x['start'], e0 or x['end']
    write(f'04-{k:02d}-occupation-{occ}-{s}.json', {'_placeholder': f'OCCA_{occ}_{s}', '_post': '/api/v1/occupation-attributions',
          'body': {'occupiedRegimeId': x['id'], 'occupierRegimeId': O(by), 'controlKind': kind, 'validPeriod': {'start': s, 'end': None if e.startswith('9999') else e},
                   'basisEventId': ev or x['sev'], 'coOccupied': co, 'note': {'zh-Hant': nzh or '依據事件為此佔領區主權紀錄的起始事件。', 'en': ''}}})
for key, ph, slug, orig, lang, zh, en, kind, start, evk, prewar in AREAS:
    k += 1; ss = segs[key]
    write(f'04-{k:02d}-occupation-{slug}.json', {'_placeholder': f'OCCA_{key}', '_post': '/api/v1/occupation-attributions',
          'body': {'occupiedRegimeId': '{{%s}}' % ph, 'occupierRegimeId': DE, 'controlKind': kind, 'validPeriod': {'start': ss[0]['start'], 'end': ss[-1]['end']},
                   'basisEventId': EV[evk], 'coOccupied': False, 'note': {'zh-Hant': {'annexed': '事實併入（德國以命令併入，國際未承認割讓）。', 'civil_administration': '德國民政管理（保護國／總督府）。'}[kind], 'en': ''}}})
# en 留空不合法 → 補英文
for f in os.listdir(OUT):
    if f.startswith('04-'):
        p = os.path.join(OUT, f); d = json.load(open(p))
        if not d['body']['note']['en']: d['body']['note']['en'] = 'Occupation attribution (see zh-Hant note).'
        write(f, d)
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k_, 'properties': {}, 'geometry': mapping(v)} for k_, v in derived.items()]},
          open(os.path.join(ROOT, 'occupation-1-derived.geojson'), 'w'), separators=(',', ':'))
print('ok', len(os.listdir(OUT)), 'requests;', {k_: [(s['start'], s['end']) for s in v] for k_, v in segs.items()})
