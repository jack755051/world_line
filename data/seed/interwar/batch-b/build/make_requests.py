#!/usr/bin/env python3
"""兩次大戰之間 B 批：1924-01-01 → 1938（DRAFT，待 Tai 檢查）。
把 A 批迄於 1924-01-01（試驗終點）的 34 筆紀錄先撤後增、延長迄日，接上開發庫既有的 1938 年前後（二戰）資料，接點不留空隙、不重疊。
子批（依紀錄起日）：B1 [~, 1929-01-01)、B2 [1929-01-01, 1936-01-01)、B3 [1936-01-01, ~)。
另外先撤後增開發庫既有的「西班牙共和國」紀錄（原起日 1931-01-01，改 1931-04-14 宣布共和起，並扣掉內戰期間國民軍控制區）。
沒有後續資料的地區（北非、近東、北歐部分國家）暫迄 1939-01-01（本批試驗終點，無迄事件）。

輸入：
- ../borders-ohm-interwar-b.geojson＋../ohm-manifest.json（build/fetch.py＋build/build.py，固定版本 OHM 關係）
- A 批（環境變數 IWA；在 Mac 上是 data/seed/interwar/batch-a）的 requests、borders-ohm、ohm-manifest
- ../db-export/db_rows.json：開發庫唯讀匯出（1918-11～1939-07 間未撤回的主權紀錄；只做扣除與 QA，不進版控）
- ../db-export/es_rep.json：開發庫既有西班牙共和國紀錄（照抄幾何與 OHM 欄位，不進版控）
- ../db-export/ids-a.json：A 批送出的 id（找要撤回的紀錄，不進版控）
輸出：../interwar-b-derived.geojson（key＝placeholder）、../qa.json、../requests/B{1,2,3}/*.json
"""
import json, os, copy, datetime, sys, re, math
from shapely.geometry import shape, mapping, MultiPolygon, Polygon, Point
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import set_precision, STRtree, affinity

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
IWA = os.environ.get('IWA') or next(p for p in (os.path.join(ROOT, '..', 'batch-a'), os.path.join(ROOT, '..', 'a')) if os.path.isdir(p))
START, END = '1924-01-01', '1939-01-01'
SUBS = [('B1', '1900-01-01', '1929-01-01'), ('B2', '1929-01-01', '1936-01-01'), ('B3', '1936-01-01', '9999-12-31')]
MAN = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(IWA, 'ohm-manifest.json')))}
OWN_A = set(MAN)
MAN.update({r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))})
OWN = {r['ohm_relation_id'] for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))}
ohm = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(IWA, 'borders-ohm-interwar-a.geojson')))['features']}
ohm.update({f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-interwar-b.geojson')))['features']})
DBX = os.path.join(ROOT, 'db-export')
ROWS = json.load(open(os.path.join(DBX, 'db_rows.json')))['features']
ESR = json.load(open(os.path.join(DBX, 'es_rep.json')))
IDS_A = json.load(open(os.path.join(DBX, 'ids-a.json')))
AR = {}
for sub in sorted(os.listdir(os.path.join(IWA, 'requests'))):
    for fn in sorted(os.listdir(os.path.join(IWA, 'requests', sub))):
        r = json.load(open(os.path.join(IWA, 'requests', sub, fn), encoding='utf-8')); AR[r['_placeholder']] = r

def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x, 'geoms', []) for p in polys(y)]
def clean(x):
    x = make_valid(set_precision(make_valid(x), 1e-4))
    return MultiPolygon([p for p in polys(x) if p.area > 1e-5])
O = lambda i: ohm[i]
U = lambda *a: unary_union(list(a))
OL = lambda rid: f'relation/{rid} v{MAN[rid]["ohm_version"]}'
def nxt(s): return (datetime.date.fromisoformat(s) + datetime.timedelta(days=1)).isoformat()
fmt = lambda pts: ' · '.join(f'{x},{y}' for x, y in pts)
HAND = '手繪近似線（build/make_requests.py）'
def circ(x, y, r): return affinity.scale(Point(x, y).buffer(r, 32), xfact=1 / math.cos(math.radians(y)), yfact=1)

ES_GEOM = make_valid(shape(next(f['geometry'] for f in ROWS if f['id'] == ESR['id'])))   # 幾何取自 db_rows.json
# ── 手繪近似範圍（全部標「近似／待查證」）──
# 萊茵蘭佔領三區：萊茵河左岸，以手繪分界線分區，加三個右岸橋頭堡（半徑約 30 公里的圓）與凱爾小橋頭堡
RHINE = [(8.2, 48.97), (8.35, 49.2), (8.45, 49.45), (8.45, 49.7), (8.35, 49.9), (8.27, 50.0), (8.0, 49.98), (7.9, 49.97), (7.75, 50.1), (7.6, 50.36), (7.4, 50.5),
         (7.2, 50.65), (7.1, 50.73), (6.96, 50.94), (6.85, 51.1), (6.77, 51.23), (6.75, 51.43), (6.62, 51.66), (6.25, 51.83), (6.1, 51.9)]
WEST = Polygon([(5.0, 48.97)] + RHINE + [(6.1, 52.2), (5.0, 52.2)])
Z1_PTS = [(5.0, 50.55), (6.5, 50.5), (7.3, 50.58), (7.3, 52.2), (5.0, 52.2)]
Z2_PTS = [(5.0, 49.65), (6.9, 49.6), (7.5, 49.8), (7.95, 49.97), (8.0, 50.58), (7.3, 50.58), (6.5, 50.5), (5.0, 50.55)]
Z3_PTS = [(5.0, 48.9), (8.5, 48.9), (8.5, 49.99), (7.95, 49.97), (7.5, 49.8), (6.9, 49.6), (5.0, 49.65)]
HEADS = {'Z1': [(6.96, 50.94, 0.27)], 'Z2': [(7.6, 50.36, 0.27)], 'Z3': [(8.27, 50.0, 0.27), (7.81, 48.57, 0.08)]}
DE24 = O(2696515)
def zone(k, pts): return DE24.intersection(U(WEST.intersection(Polygon(pts)), *[circ(*h) for h in HEADS[k]]))
Z1 = zone('Z1', Z1_PTS); Z2 = zone('Z2', Z2_PTS).difference(Z1); Z3 = zone('Z3', Z3_PTS).difference(U(Z1, Z2))
RHINE_HAND = ('萊茵河左岸（萊茵河線 %s）以手繪分界線分區：科隆區 %s；科布倫茨區 %s；美因茲區 %s；右岸橋頭堡為圓（中心,半徑°）%s'
              % (fmt(RHINE), fmt(Z1_PTS), fmt(Z2_PTS), fmt(Z3_PTS), '；'.join(f'{k}: ' + ', '.join(f'({x},{y},{r})' for x, y, r in v) for k, v in HEADS.items())))
RUHR_PTS = [(6.55, 51.25), (6.6, 51.65), (7.0, 51.75), (7.6, 51.7), (7.95, 51.55), (7.8, 51.3), (7.3, 51.2), (6.9, 51.18)]   # 同 A 批
# 西班牙內戰國民軍控制區（各階段手繪，與西班牙共和國範圍相交）
MALLORCA = [(2.2, 39.2), (3.6, 39.2), (3.6, 40.0), (2.2, 40.0)]
IBIZA = [(1.1, 38.6), (1.7, 38.6), (1.7, 39.15), (1.1, 39.15)]
CANARIAS = [(-18.5, 27.5), (-13.2, 27.5), (-13.2, 29.5), (-18.5, 29.5)]
SAHARA = [(-17.5, 20.5), (-8.5, 20.5), (-8.5, 29.6), (-17.5, 29.6)]   # 西屬撒哈拉與伊夫尼（1936-07 起即歸國民軍）
ISLES = [MALLORCA, IBIZA, CANARIAS, SAHARA]
N36 = [(-9.8, 44.2), (-7.05, 44.2), (-7.05, 43.05), (-6.0, 42.95), (-4.8, 43.05), (-3.8, 42.95), (-3.2, 42.95), (-2.6, 42.9)]
PYR = [(-1.75, 43.45), (-0.7, 43.05), (0.0, 42.8), (-0.2, 42.2), (-0.3, 41.7), (-0.6, 41.2), (-0.9, 40.6), (-1.0, 40.3), (-1.6, 40.3), (-2.6, 40.9)]
SOUTH_M = [(-3.6, 40.9), (-3.85, 40.5), (-3.8, 40.3), (-3.9, 39.9), (-4.5, 39.5), (-5.0, 39.0), (-5.2, 38.6), (-4.95, 38.1), (-4.6, 37.8), (-4.4, 37.35), (-3.4, 37.35), (-3.4, 37.0)]
TAIL_M = [(-3.9, 36.9), (-4.6, 37.0), (-5.2, 36.6), (-5.35, 36.1), (-6.5, 35.9), (-7.6, 36.8), (-9.8, 37.0)]
TAIL_M2 = [(-3.55, 36.7), (-6.5, 35.9), (-7.6, 36.8), (-9.8, 37.0)]
ES_PH = {
 1: ([N36 + [(-2.0, 42.95)] + PYR + [(-4.0, 40.85), (-4.7, 40.5), (-5.5, 40.2), (-5.6, 39.5), (-6.2, 39.2), (-7.6, 39.4), (-9.8, 39.4)],
      [(-7.6, 37.6), (-6.0, 37.9), (-5.0, 37.95), (-4.7, 37.95), (-4.8, 37.5), (-5.2, 37.0), (-5.35, 36.5), (-5.45, 36.0), (-6.6, 36.5), (-7.6, 37.1)],
      [(-3.9, 37.35), (-3.4, 37.35), (-3.4, 37.0), (-3.9, 37.0)]] + ISLES),
 2: ([N36 + [(-2.45, 43.1), (-2.45, 43.6)] + PYR + SOUTH_M + TAIL_M] + ISLES),
 3: ([N36 + [(-2.45, 43.1), (-2.45, 43.6)] + PYR + SOUTH_M + TAIL_M2] + ISLES),
 4: ([N36[:6] + [(-3.45, 43.1), (-3.45, 43.6)] + PYR + SOUTH_M + TAIL_M2] + ISLES),
 5: ([N36[:5] + [(-4.55, 43.6)] + PYR + SOUTH_M + TAIL_M2] + ISLES),
 6: ([[(-9.8, 44.5), (-1.75, 44.5)] + PYR + SOUTH_M + TAIL_M2] + ISLES),
 7: ([[(-9.8, 44.5), (0.75, 44.5), (0.75, 42.4), (0.8, 41.95), (0.68, 41.6), (0.45, 41.3), (0.5, 40.95), (0.85, 40.7), (1.3, 40.6), (1.0, 40.2), (0.25, 40.25),
       (-0.3, 40.2), (-0.8, 40.05), (-1.6, 40.2), (-2.6, 40.9)] + SOUTH_M + TAIL_M2] + ISLES),
}
ES_R8 = [(-3.6, 40.95), (-2.6, 40.95), (-1.6, 40.25), (-0.8, 40.0), (-0.4, 39.85), (0.2, 39.75), (0.5, 38.5), (-0.5, 37.5), (-2.0, 36.5), (-3.55, 36.6)] + SOUTH_M[::-1][:-1]
def es_zone(n):
    if n == 8: return ES_GEOM.difference(Polygon(ES_R8))
    return ES_GEOM.intersection(U(*[Polygon(p) for p in ES_PH[n]]))
# 開發庫既有西班牙共和國幾何缺西屬撒哈拉、伊夫尼與部分加那利島嶼；重送時補上 OHM 2862762（1926 年版西班牙）多出的部分，避免 1931-04-14 接點留空
ES_GEOM = make_valid(unary_union([ES_GEOM, O(2862762)]).difference(U(O(2860422), O(2848366))))   # 西屬摩洛哥與丹吉爾另列
G = {'RUHR': DE24.intersection(Polygon(RUHR_PTS)), 'RHZ1': Z1, 'RHZ2': Z2, 'RHZ3': Z3, 'ES': ES_GEOM}
G.update({f'ESN{n}': es_zone(n) for n in range(1, 9)})
G = {k: clean(v) for k, v in G.items()}
def g_of(k):
    if isinstance(k, int): return clean(O(k))
    return G[k]

REQ = []
def add(cat, name, ph, post, body, meta=None, geom=None, sub=None):
    REQ.append(dict(cat=cat, name=name, ph=ph, post=post, body=body, meta=meta, geom=geom, sub=sub))

# ── 來源 ──
add('01-source', 'src_ohm_iwb', 'SRC_OHM_IWB', '/api/v1/sources', {'sourceKind': 'dataset',
    'title': 'OpenHistoricalMap — boundary=administrative 關係（歐洲、北非、近東，1924～1938 兩次大戰之間 B 批試驗）',
    'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
    'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
    'publishedText': 'Overpass osm_base %s；逐筆見 interwar/batch-b/ohm-manifest.json' % MAN[2694638]['osm_base'],
    'note': 'OHM 整體以 CC0 1.0 釋出；部分成員線段帶 license=CC BY 4.0 標籤，部分線段註明來自 OpenStreetMap（ODbL），逐筆在主權紀錄標示。'})
GPO = 'United States Department of State; United States Government Printing Office, Washington'
FRUS = [('SRC_FRUS_1925V1', 'frus1925v01', 'Papers Relating to the Foreign Relations of the United States, 1925, Volume I', '1940'),
        ('SRC_FRUS_1931V2', 'frus1931v02', 'Papers Relating to the Foreign Relations of the United States, 1931, Volume II', '1946'),
        ('SRC_FRUS_1936V1', 'frus1936v01', 'Foreign Relations of the United States: Diplomatic Papers, 1936, General, The British Commonwealth, Volume I', '1953'),
        ('SRC_FRUS_1936V2', 'frus1936v02', 'Foreign Relations of the United States: Diplomatic Papers, 1936, Europe, Volume II', '1954')]
for ph, vol, t, yr in FRUS:
    add('01-source', ph.lower(), ph, '/api/v1/sources', {'sourceKind': 'official_record', 'title': t, 'publisher': GPO, 'licenseCode': 'us_federal_pd',
        'licenseEvidenceUrl': 'https://www.state.gov/copyright-information', 'url': 'https://history.state.gov/historicaldocuments/' + vol, 'publishedText': f'{yr} 年出版'})
add('01-source', 'src_lnts_54', 'SRC_LNTS_54', '/api/v1/sources', {'sourceKind': 'treaty', 'title': 'League of Nations Treaty Series, Vol. 54（國際聯盟條約彙編第 54 卷）',
    'publisher': 'League of Nations（Geneva）', 'licenseCode': 'pd_expired',
    'licenseEvidenceUrl': 'https://treaties.un.org/Pages/Content.aspx?path=DB%2FLoNOnline%2FpageIntro_Table_en.xml',
    'url': 'https://treaties.un.org/doc/Publication/UNTS/LON/Volume%2054/v54.pdf', 'publishedText': '1926–1927 年出版（聯合國條約資料庫公開掃描本）',
    'note': '1930 年以前出版，美國著作權已過期；條約原文與英、法譯本。'})

# ── 政權（新）──
REGIMES = [
 ('REGIME_RHZ1', 'allied-rhineland-cologne-zone', 'Cologne Zone (Inter-Allied Rhineland occupation)', 'en', '協約國萊茵蘭佔領區：科隆區', 'Rhineland occupation: Cologne zone', '本表自訂的說明性名稱（非政權正式名稱）'),
 ('REGIME_RHZ2', 'allied-rhineland-koblenz-zone', 'Koblenz Zone (Inter-Allied Rhineland occupation)', 'en', '協約國萊茵蘭佔領區：科布倫茨區', 'Rhineland occupation: Koblenz zone', '本表自訂的說明性名稱（非政權正式名稱）'),
 ('REGIME_RHZ3', 'allied-rhineland-mainz-zone', 'Mainz Zone (Inter-Allied Rhineland occupation)', 'en', '協約國萊茵蘭佔領區：美因茲區', 'Rhineland occupation: Mainz zone', '本表自訂的說明性名稱（非政權正式名稱）'),
 ('REGIME_GR_REP', 'second-hellenic-republic', 'Ελληνική Δημοκρατία', 'el', '希臘第二共和國', 'Second Hellenic Republic', 'OHM relation/2801340 涵蓋 1924–1936 的希臘；名稱為通行稱呼'),
 ('REGIME_AL_REP', 'albanian-republic-1925', 'Republika Shqiptare', 'sq', '阿爾巴尼亞共和國', 'Albanian Republic', 'OHM relation/2885839、2800555（name=Albanian Republic）'),
 ('REGIME_SY_STATE', 'state-of-syria-mandate', 'État de Syrie', 'fr', '敘利亞國（法國委任統治）', 'State of Syria (French mandate)', 'OHM relation/2863991；原文名為通行稱呼'),
 ('REGIME_SY_REP', 'syrian-republic-mandate', 'République syrienne', 'fr', '敘利亞共和國（法國委任統治）', 'Syrian Republic (French mandate)', 'OHM relation/2863990、2863989、2863988；原文名為通行稱呼'),
 ('REGIME_ALAWITE', 'alawite-state', 'État des Alaouites', 'fr', '阿拉維國（法國委任統治）', 'Alawite State (French mandate)', 'OHM relation/2863987；原文名為通行稱呼（1930 起稱拉塔基亞政府，未分）'),
 ('REGIME_LB_REP', 'lebanese-republic-mandate', 'République libanaise', 'fr', '黎巴嫩共和國（法國委任統治）', 'Lebanese Republic (French mandate)', 'OHM relation/2831358；原文名為通行稱呼'),
 ('REGIME_IQ_K', 'kingdom-of-iraq', 'المملكة العراقية', 'ar', '伊拉克王國', 'Kingdom of Iraq', 'OHM relation/2839466（Hashemite Kingdom of Iraq）；原文名為通行稱呼'),
 ('REGIME_LY_IT', 'italian-libya', 'Libia italiana', 'it', '義屬利比亞', 'Italian Libya', 'OHM relation/2803189'),
 ('REGIME_CY_COL', 'cyprus-crown-colony', 'Crown Colony of Cyprus', 'en', '英屬賽普勒斯（直轄殖民地）', 'Crown Colony of Cyprus', 'OHM relation/2801349（British Cyprus）；名稱為通行稱呼'),
 ('REGIME_TANGIER', 'tangier-international-zone', 'Zone internationale de Tanger', 'fr', '丹吉爾國際共管區', 'Tangier International Zone', 'OHM relation/2848366；1923 年巴黎公約用語'),
 ('REGIME_HATAY', 'hatay-state', 'Hatay Devleti', 'tr', '哈塔伊國', 'Hatay State', 'OHM relation/2864001'),
 ('REGIME_ES_NAT', 'spanish-nationalist-zone', 'Zona nacional', 'es', '西班牙內戰國民軍控制區', 'Spanish Nationalist zone', '本表自訂的說明性名稱（1936-10-01 起佛朗哥自稱「西班牙國」，見開發庫既有 spanish-state）'),
]
for ph, slug, orig, lang, zh, en, ns in REGIMES:
    add('02-regime', slug, ph, '/api/v1/regimes', {'slug': slug, 'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang,
        'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]}, {'priorPlaceholder': False, 'nameSource': ns})

# ── 事件 ──
B, S_ = 'belligerent', 'signatory'
EVD = {}
def ev(ph, kind, start, zh, en, parts, cites, tn=None):
    body = {'eventKind': kind, 'occurred': {'start': start, 'end': nxt(start)}, 'datePrecision': 'day', 'summary': {'zh-Hant': zh, 'en': en},
            'participants': [{'regimeId': '{{%s}}' % r, 'role': role} for r, role in parts],
            'citations': [{'sourceId': '{{%s}}' % s, 'locator': l, 'evidenceNote': n} for s, l, n in cites]}
    if tn: body['timeNote'] = {'zh-Hant': tn[0], 'en': tn[1]}
    EVD[ph] = start
    add('03-event', ph.lower(), ph, '/api/v1/events', body, {'verification': 'verified' if cites else 'pending（待查證）'})
NOSRC = ('未找到正式出處（待查證）；日期為通行說法。', 'No formal source located yet (pending); date per common accounts.')
def nos(zh, en): return ('未找到正式出處（待查證）；' + zh, 'No formal source located yet (pending); ' + en)
P = None
ev('EV_ROME_1924', 'treaty', '1924-01-27', '義大利與塞爾維亞人、克羅埃西亞人和斯洛維尼亞人王國簽羅馬條約：阜姆歸義大利、蘇沙克歸南方', 'Treaty of Rome between Italy and the Kingdom of SCS: Fiume to Italy, Sušak to the Kingdom',
   [('REGIME_IT', S_), ('REGIME_KSCS', S_)], [], NOSRC)
ev('EV_FIUME_ANNEX', 'political', '1924-02-22', '阜姆正式併入義大利', 'Fiume is formally annexed to Italy', [('REGIME_IT', S_), ('REGIME_FIUME_FS', S_)], [],
   nos('2-22 為 OHM 義大利換版日（王國法令日，通行說法 1924-02-22 生效；3-16 舉行併入典禮）。', 'Date per the OHM Italy version (decree in force 22 Feb 1924 per common accounts).'))
ev('EV_JAVORINA', 'political', '1924-03-12', '波蘭與捷克斯洛伐克在亞沃日納（塔特拉山區）的邊界依國際聯盟／大使會議裁定調整', 'The Polish–Czechoslovak border at Javorina (Tatras) is adjusted following the League / Ambassadors decision',
   [('REGIME_PL', S_), ('REGIME_CS', S_)], [], nos('3-12 為 OHM 兩國換版日。', 'Date per the OHM versions of both countries.'))
ev('EV_GR_REP', 'political', '1924-03-25', '希臘國民議會廢除君主制，宣布成立共和國', 'The Greek National Assembly abolishes the monarchy and proclaims a republic', [('REGIME_GR', S_), ('REGIME_GR_REP', S_)], [],
   nos('4-13 公民投票確認。', 'Confirmed by the plebiscite of 13 Apr.'))
ev('EV_LAUSANNE_INFORCE', 'treaty', '1924-08-06', '洛桑條約生效：英、義、日交存批准書', 'The Treaty of Lausanne enters into force: Britain, Italy and Japan deposit ratifications',
   [('REGIME_TR', S_), ('REGIME_GR', S_), ('REGIME_UK', S_), ('REGIME_FR3', S_), ('REGIME_IT', S_)],
   [('SRC_LNTS_28', 'No. 701, p. 13, note (1)', '註 1：希臘 1924-02-11、土耳其 1924-03-31、英帝國、義大利與日本 1924-08-06 交存批准書。')])
ev('EV_SU_UZ_TM', 'political', '1924-10-27', '中亞民族劃界：成立烏茲別克與土庫曼蘇維埃社會主義共和國', 'National delimitation in Central Asia: the Uzbek and Turkmen SSRs are formed', [('REGIME_SU', S_)], [],
   nos('本表地圖框（東經 60° 以西）只含極小部分，蘇聯內部各加盟共和國未分。', 'Barely inside the map frame; Union republics are not split.'))
ev('EV_SU_1925', 'treaty', '1925-01-20', '蘇日基本條約（北京）：日本撤出北庫頁島', 'Soviet–Japanese Basic Convention (Peking): Japan withdraws from northern Sakhalin', [('REGIME_SU', S_), ('REGIME_JP', S_)], [],
   nos('1-20 為 OHM 蘇聯換版日；變動在地圖框外。', 'Date per the OHM Soviet Union version; the change is outside the map frame.'))
ev('EV_AL_REP', 'political', '1925-01-21', '阿爾巴尼亞制憲議會宣布成立共和國', 'The Albanian Constituent Assembly proclaims a republic', [('REGIME_AL_PR', S_), ('REGIME_AL_REP', S_)],
   [('SRC_FRUS_1925V1', 'Doc. 329, p. 491', '駐阿爾巴尼亞代辦電：國民議會 1925-01-21 宣布阿爾巴尼亞為共和國，索古為總統。')],
   ('OHM 2885839 起日為 1925-01-31（索古就任總統），本表依 FRUS 從 01-21 起。', 'OHM starts 31 Jan 1925 (Zogu installed as president); this table starts 21 Jan per FRUS.'))
ev('EV_CY_COLONY', 'political', '1925-05-01', '賽普勒斯成為英國直轄殖民地', 'Cyprus becomes a British Crown colony', [('REGIME_UK', S_), ('REGIME_CY_COL', S_)], [], NOSRC)
ev('EV_TANGIER', 'treaty', '1925-06-01', '丹吉爾國際共管區規約生效', 'The Statute of the Tangier International Zone comes into force', [('REGIME_FR3', S_), ('REGIME_UK', S_), ('REGIME_ES_K', S_)],
   [('SRC_LNTS_28', 'No. 729, p. 541', '英、法、西三國 1923-12-18 巴黎簽字的丹吉爾區組織公約（含兩項敕令議定書）。')],
   ('公約 1923-12-18 簽字；1925-06-01 生效為通行說法（本卷未載生效日）。', 'Signed 18 Dec 1923; in force 1 Jun 1925 per common accounts (not stated in this volume).'))
ev('EV_SVALBARD', 'treaty', '1925-08-14', '斯匹茨卑爾根條約生效：挪威正式接管斯瓦巴', 'The Spitsbergen Treaty takes effect: Norway formally takes over Svalbard', [('REGIME_NO', S_)],
   [('SRC_LNTS_2', 'No. 41, p. 7', '1920-02-09 巴黎簽字的斯匹茨卑爾根條約，承認挪威對斯瓦巴群島的主權。')],
   ('條約 1920-02-09 簽字；1925-08-14 挪威正式接管為通行說法（開發庫既有挪威紀錄起日）。', 'Signed 9 Feb 1920; Norwegian takeover on 14 Aug 1925 per common accounts (start of the existing Norway record).'))
ev('EV_RUHR_END', 'political', '1925-08-25', '法比軍撤出魯爾區（道威斯計畫後）', 'French and Belgian troops complete the evacuation of the Ruhr (after the Dawes Plan)', [('REGIME_FR3', B), ('REGIME_BE', B), ('REGIME_DE', B)], [],
   nos('8-25 撤離完成為通行說法（杜塞道夫、杜伊斯堡等地同日撤出）。', 'Evacuation completed 25 Aug per common accounts.'))
ev('EV_LOCARNO', 'treaty', '1925-10-16', '洛迦諾公約簽字：德、法、比、英、義萊茵保證公約', 'The Locarno Treaties are signed: the Rhineland Pact between Germany, France, Belgium, Britain and Italy',
   [('REGIME_DE', S_), ('REGIME_FR3', S_), ('REGIME_BE', S_), ('REGIME_UK', S_), ('REGIME_IT', S_)],
   [('SRC_LNTS_54', 'No. 1292, p. 289', '1925-10-16 洛迦諾萊茵相互保證條約、會議最後議定書與致德國集體照會；1926-09-14 生效並登記。')],
   ('1925-10-16 草簽、12-01 倫敦正式簽字、1926-09-14 生效（德國加入國際聯盟）。', 'Initialled 16 Oct 1925, signed in London 1 Dec, in force 14 Sep 1926.'))
ev('EV_COLOGNE_EVAC', 'political', '1926-01-31', '協約國撤出萊茵蘭科隆區', 'The Allies evacuate the Cologne zone of the Rhineland', [('REGIME_UK', B), ('REGIME_DE', B)], [],
   nos('1926-01-31 撤離完成為通行說法。', 'Completed 31 Jan 1926 per common accounts.'))
ev('EV_LB_REP', 'political', '1926-05-23', '大黎巴嫩頒布憲法，改稱黎巴嫩共和國（仍為法國委任統治）', 'Greater Lebanon adopts a constitution and becomes the Lebanese Republic (still under French mandate)',
   [('REGIME_LEBANON', S_), ('REGIME_LB_REP', S_)], [], NOSRC)
ev('EV_RIF_END', 'war', '1926-05-27', '阿卜杜勒—克里姆向法軍投降，里夫戰爭結束', 'Abd el-Krim surrenders to the French; end of the Rif War', [('REGIME_RIF', B), ('REGIME_FR3', B), ('REGIME_ES_K', B)], [], NOSRC)
ev('EV_AL_YU_1926', 'political', '1926-07-26', '阿爾巴尼亞與南斯拉夫邊界依大使會議裁定調整（聖瑙姆等地）', 'The Albanian–Yugoslav border is adjusted per the Ambassadors decision (Sveti Naum etc.)',
   [('REGIME_AL_REP', S_), ('REGIME_KSCS', S_)], [], nos('7-26 為 OHM 兩國換版日。', 'Date per the OHM versions of both countries.'))
ev('EV_AL_KINGDOM', 'political', '1928-09-01', '阿爾巴尼亞改制王國，索古稱國王索古一世', 'Albania becomes a kingdom; Zogu is proclaimed King Zog I', [('REGIME_AL_REP', S_), ('REGIME_AL', S_)], [],
   nos('開發庫既有阿爾巴尼亞王國紀錄起日。', 'Start of the existing Albanian Kingdom record.'))
ev('EV_LATERAN', 'treaty', '1929-06-07', '拉特朗條約批准書交換生效，梵蒂岡城國成立', 'Ratifications of the Lateran Treaty exchanged; Vatican City State established', [('REGIME_IT', S_)], [],
   nos('條約 1929-02-11 簽字；6-07 為 OHM 義大利換版日。', 'Signed 11 Feb 1929; 7 Jun is the OHM Italy version date.'))
ev('EV_YU', 'political', '1929-10-03', '塞爾維亞人、克羅埃西亞人和斯洛維尼亞人王國改稱南斯拉夫王國', 'The Kingdom of Serbs, Croats and Slovenes is renamed the Kingdom of Yugoslavia', [('REGIME_KSCS', S_), ('REGIME_YU', S_)], [], NOSRC)
ev('EV_SU_TJ', 'political', '1929-10-16', '塔吉克升格為加盟共和國', 'Tajikistan becomes a Union republic', [('REGIME_SU', S_)], [], nos('在地圖框外。', 'Outside the map frame.'))
ev('EV_KOBLENZ_EVAC', 'political', '1929-11-30', '協約國撤出萊茵蘭科布倫茨區（海牙會議後）', 'The Allies evacuate the Koblenz zone of the Rhineland (after the Hague Conference)', [('REGIME_FR3', B), ('REGIME_DE', B)], [], NOSRC)
ev('EV_SY_REP', 'political', '1930-05-14', '法國高級專員頒布敘利亞憲法，敘利亞國改稱敘利亞共和國', 'The French High Commissioner promulgates a constitution; the State of Syria becomes the Syrian Republic',
   [('REGIME_SY_STATE', S_), ('REGIME_SY_REP', S_)], [], NOSRC)
ev('EV_MAINZ_EVAC', 'political', '1930-06-30', '法軍撤出萊茵蘭美因茲區，協約國萊茵蘭佔領結束', 'French troops evacuate the Mainz zone; end of the Allied occupation of the Rhineland', [('REGIME_FR3', B), ('REGIME_DE', B)], [], NOSRC)
ev('EV_ES_REPUBLIC', 'political', '1931-04-14', '西班牙宣布成立共和國，國王阿方索十三世離境', 'Spain proclaims the Republic; King Alfonso XIII leaves the country', [('REGIME_ES_K', S_), ('REGIME_ES_REP', S_)],
   [('SRC_FRUS_1931V2', 'Doc. 1056, p. 985', '駐西班牙大使 1931-04-14 電：共和國已宣布成立，國王離開馬德里。')])
ev('EV_IQ_INDEP', 'political', '1932-10-03', '伊拉克加入國際聯盟，委任統治結束', 'Iraq is admitted to the League of Nations; end of the mandate', [('REGIME_IRAQ', S_), ('REGIME_IQ_K', S_), ('REGIME_UK', S_)], [], NOSRC)
ev('EV_LY_UNIFY', 'political', '1934-01-01', '的黎波里塔尼亞與昔蘭尼加合為義屬利比亞', 'Tripolitania and Cyrenaica are united as Italian Libya', [('REGIME_IT', S_), ('REGIME_LY_IT', S_)], [],
   nos('OHM 2803189 起日只到年（1934）。', 'OHM start only gives the year (1934).'))
ev('EV_SAAR_PLEB', 'political', '1935-01-13', '薩爾公民投票：九成選民贊成回歸德國', 'Saar plebiscite: some 90 % vote for return to Germany', [('REGIME_SAAR', S_), ('REGIME_DE', S_)],
   [('SRC_FRUS_PPC13', '凡爾賽和約 Part III, Section IV, Annex, Chapter III, §§34–35', '和約規定 15 年期滿由居民投票決定薩爾歸屬，國際聯盟依投票結果決定主權。')],
   ('投票日為通行說法；FRUS 只證明和約規定。', 'Voting day per common accounts; FRUS only documents the treaty provision.'))
ev('EV_SAAR_RETURN', 'political', '1935-03-01', '薩爾回歸德國', 'The Saar is returned to Germany', [('REGIME_SAAR', S_), ('REGIME_DE', S_)], [],
   nos('3-01 為 OHM 德國換版日。', 'Date per the OHM German Reich version.'))
ev('EV_GR_MONARCHY', 'political', '1935-11-03', '希臘公民投票恢復君主制（喬治二世復位）', 'A Greek plebiscite restores the monarchy (George II returns)', [('REGIME_GR_REP', S_), ('REGIME_GR', S_)], [],
   nos('10-10 康迪利斯政變宣布恢復王制，11-03 公民投票。', 'Monarchy declared after the Kondylis coup of 10 Oct; plebiscite 3 Nov.'))
ev('EV_RHINE_REMIL', 'campaign', '1936-03-07', '德軍開進萊茵非軍事區，德國宣布廢止洛迦諾公約', 'German troops enter the demilitarized Rhineland; Germany denounces Locarno',
   [('REGIME_DE', B), ('REGIME_FR3', B), ('REGIME_BE', B)],
   [('SRC_FRUS_1936V1', 'Doc. 183, pp. 214–216', '駐德大使 Dodd 1936-03-08 報告：希特勒 3 月 7 日國會演說、德軍開入萊茵蘭與廢止洛迦諾公約。'),
    ('SRC_FRUS_1936V1', 'Doc. 182', '同日相關電報。')])
ev('EV_ES_COUP', 'war', '1936-07-17', '摩洛哥西班牙駐軍起事，西班牙內戰開始', 'The Spanish army in Morocco revolts; the Spanish Civil War begins', [('REGIME_ES_REP', B), ('REGIME_ES_NAT', B)],
   [('SRC_FRUS_1936V2', 'Doc. 357, p. 440', '駐丹吉爾代表 1936-07-18 電：西屬摩洛哥駐軍起事。')],
   ('7-17 摩洛哥起事、7-18 本土各地響應。', 'Revolt in Morocco on 17 Jul, spreading to the mainland on 18 Jul.'))
ev('EV_SY_1936', 'treaty', '1936-09-09', '法敘條約簽字：德魯茲山與拉塔基亞併入敘利亞', 'The Franco-Syrian Treaty is signed: Jabal Druze and Latakia are joined to Syria', [('REGIME_FR3', S_), ('REGIME_SY_REP', S_)], [],
   nos('條約未經法國批准；兩地併入依 OHM 換版日。', 'Never ratified by France; the merger date follows the OHM versions.'))
ev('EV_ES_MADRID', 'campaign', '1936-11-07', '國民軍兵臨馬德里，馬德里保衛戰開始', 'Nationalist forces reach Madrid; the defence of Madrid begins', [('REGIME_ES_REP', B), ('REGIME_ES_NAT', B)], [], NOSRC)
ev('EV_SU_1936', 'political', '1936-12-05', '蘇聯新憲法：外高加索聯邦解散，哈薩克、吉爾吉斯升格加盟共和國', 'New Soviet constitution: the Transcaucasian SFSR is dissolved; Kazakh and Kirghiz SSRs created',
   [('REGIME_SU', S_)], [], nos('蘇聯內部各加盟共和國本表未分。', 'Union republics are not split in this table.'))
ev('EV_MALAGA', 'campaign', '1937-02-08', '國民軍攻佔馬拉加', 'Nationalist forces take Málaga', [('REGIME_ES_REP', B), ('REGIME_ES_NAT', B)], [], NOSRC)
ev('EV_BILBAO', 'campaign', '1937-06-19', '國民軍攻佔畢爾包', 'Nationalist forces take Bilbao', [('REGIME_ES_REP', B), ('REGIME_ES_NAT', B)], [], NOSRC)
ev('EV_SANTANDER', 'campaign', '1937-08-26', '國民軍攻佔桑坦德', 'Nationalist forces take Santander', [('REGIME_ES_REP', B), ('REGIME_ES_NAT', B)], [], NOSRC)
ev('EV_GIJON', 'campaign', '1937-10-21', '國民軍攻佔希洪，北方戰線結束', 'Nationalist forces take Gijón; end of the northern front', [('REGIME_ES_REP', B), ('REGIME_ES_NAT', B)], [], NOSRC)
ev('EV_VINAROS', 'campaign', '1938-04-15', '國民軍抵達比納羅斯地中海岸，共和國控制區被切成兩半', 'Nationalist forces reach the sea at Vinaròs, cutting the Republic in two', [('REGIME_ES_REP', B), ('REGIME_ES_NAT', B)], [], NOSRC)
ev('EV_IE_CONST', 'political', '1937-12-29', '愛爾蘭新憲法生效，愛爾蘭自由邦改稱愛爾（Éire）', 'The new Irish constitution takes effect; the Irish Free State becomes Éire', [('REGIME_IFS', S_), ('REGIME_IE', S_)], [],
   nos('開發庫既有愛爾紀錄起日。', 'Start of the existing Éire record.'))
ev('EV_HATAY_STATE', 'political', '1938-09-02', '亞歷山大勒塔桑賈克議會宣布成立哈塔伊國（法土共管下）', 'The Sanjak of Alexandretta assembly proclaims the Hatay State (under joint Franco-Turkish supervision)',
   [('REGIME_HATAY', S_), ('REGIME_FR3', S_), ('REGIME_TR', S_)], [], nos('1939-06-29 併入土耳其（開發庫既有土耳其紀錄換版日）。', 'Annexed by Turkey on 29 Jun 1939 (existing Turkey record).'))
ev('EV_CATALONIA', 'campaign', '1939-02-10', '國民軍抵達法國邊境，加泰隆尼亞戰役結束（梅諾卡島 2-09 投降）', 'Nationalist forces reach the French border; end of the Catalonia offensive (Menorca surrendered 9 Feb)',
   [('REGIME_ES_REP', B), ('REGIME_ES_NAT', B)], [], NOSRC)
ev('EV_RIF_FR', 'war', '1925-04-12', '里夫軍進攻法屬摩洛哥沃爾加河谷，法國參戰', 'Rif forces attack the Ouergha valley in French Morocco; France enters the Rif War', [('REGIME_RIF', B), ('REGIME_FR3', B)], [], NOSRC)
ev('EV_SY_STATE', 'political', '1925-01-01', '大馬士革國與阿勒坡國合併為敘利亞國', 'The States of Damascus and Aleppo are merged into the State of Syria', [('REGIME_SYR_FED', S_), ('REGIME_SY_STATE', S_)], [],
   nos('OHM 2863991 起日 1925-01-01；1924-12 法國高級專員令。', 'OHM starts 1 Jan 1925; decree of Dec 1924.'))

# ── 主權紀錄定義 ──
TWN = '兩次大戰之間 B 批 1924-01-01～1938-12-31'
DEFS = []
def d(ph, regime, start, end, geom, rid, prio=0, sev=None, eev=None, layer='de_jure', derived=None, loc=None, zh='', en='', label=None, hand=None, base=None):
    DEFS.append(dict(ph=ph, regime=regime, start=start, end=end, geom=g_of(geom) if isinstance(geom, (int, str)) else geom, rid=rid, prio=prio, sev=sev, eev=eev,
                     layer=layer, derived=derived or [rid], loc=loc or (OL(rid) if rid in MAN else None), zh=zh, en=en, label=label or ph, hand=hand, base=base))
def strip_ph(s): return s[2:-2] if s else None
RETRACT = []   # (A placeholder, 新 def placeholder)
def X(aph, end, eev=None, prio=0, geom=None, zh='', en='', label=None, layer=None, hand=None, loc=None):
    """延長 A 批迄於 1924-01-01 的紀錄：先撤後增，起日、政權、起事件照 A 批。"""
    a = AR[aph]['body']; assert a['validPeriod']['end'] == START, aph
    rid = a['ohmRelationId']
    nz = '延長 A 批紀錄（原迄 1924-01-01 試驗終點，先撤後增）。' + zh
    ne = 'Extends the batch-A record (was cut at the 1 Jan 1924 trial end; withdrawn and re-added). ' + en
    d(aph + '_X', strip_ph(a['regimeId']), a['validPeriod']['start'], end, geom if geom is not None else rid, rid, prio=prio, sev=strip_ph(a['startEventId']), eev=eev,
      layer=layer or a['layerStatus'], zh=nz, en=ne, label=label or aph, hand=hand, loc=loc, base=a)
    RETRACT.append((aph, aph + '_X'))
MAND = '非主權：國際聯盟委任統治地。'; MANE = 'Not sovereign: League of Nations mandate.'
# 德國、薩爾、魯爾、萊茵蘭
X('SOV_DE_H_2', '1935-03-01', 'EV_SAAR_RETURN', prio=2, label='德國', zh='萊茵蘭三個佔領區 1924-01-01 起另列（1918-12～1923 未畫，待查證）。', en='The three Rhineland zones are separate records from 1 Jan 1924 (1918–1923 not drawn, pending).')
d('SOV_DE_I', 'REGIME_DE', '1935-03-01', '1936-07-03', 2694638, 2694638, prio=2, sev='EV_SAAR_RETURN', label='德國', zh='含薩爾。1936-07-03 起接開發庫既有紀錄。', en='Including the Saar; continues into the existing record from 3 Jul 1936.')
X('SOV_SAAR', '1935-03-01', 'EV_SAAR_RETURN', prio=5, label='薩爾', zh='1935-01-13 公民投票後 03-01 回歸德國。', en='Returned to Germany on 1 Mar 1935 after the plebiscite of 13 Jan.')
X('SOV_RUHR', '1925-08-25', 'EV_RUHR_END', prio=5, geom=G['RUHR'], label='魯爾佔領區', loc=f'{OL(2696515)} ∩ 魯爾區（{HAND}）', hand='RUHR_PTS：' + fmt(RUHR_PTS),
  zh='範圍同 A 批（粗略近似，待查證）。', en='Same extent as batch A (rough approximation, pending).')
RHN = '非主權：凡爾賽和約第 428–432 條協約國萊茵蘭佔領區（範圍為手繪粗略近似，待查證）。本表從 1924-01-01（B 批起點，不是佔領起日）起畫，1918-12～1923 未畫（待查證）。'
RHE = 'Not sovereign: Allied Rhineland occupation zone under Versailles arts. 428–432 (rough hand-drawn approximation, pending); drawn from 1 Jan 1924 (start of batch B), 1918–1923 not drawn (pending).'
for k, nm, end, eev in [('RHZ1', '科隆區', '1926-01-31', 'EV_COLOGNE_EVAC'), ('RHZ2', '科布倫茨區', '1929-11-30', 'EV_KOBLENZ_EVAC'), ('RHZ3', '美因茲區', '1930-06-30', 'EV_MAINZ_EVAC')]:
    d(f'SOV_{k}', f'REGIME_{k}', START, end, k, 2696515, prio=4.5, eev=eev, layer='not_sovereign', label=f'萊茵蘭{nm}', loc=f'{OL(2696515)} ∩ 萊茵蘭{nm}（{HAND}）', hand=RHINE_HAND, zh=RHN, en=RHE)
# 捷克斯洛伐克、波蘭、義大利、阜姆、南斯拉夫、阿爾巴尼亞、希臘、土耳其
X('SOV_CS_D_2', '1924-03-12', 'EV_JAVORINA', prio=3.5, label='捷克斯洛伐克')
d('SOV_CS_E', 'REGIME_CS', '1924-03-12', '1936-07-03', 2692233, 2692233, prio=3.5, sev='EV_JAVORINA', label='捷克斯洛伐克', zh='1936-07-03 起接開發庫既有紀錄。', en='Continues into the existing record from 3 Jul 1936.')
X('SOV_PL_B', '1924-03-12', 'EV_JAVORINA', prio=1, label='波蘭')
d('SOV_PL_C', 'REGIME_PL', '1924-03-12', '1924-06-22', 2747892, 2747892, prio=1, sev='EV_JAVORINA', label='波蘭', zh='1924-06-22 起接開發庫既有紀錄。', en='Continues into the existing record from 22 Jun 1924.')
X('SOV_IT_B', '1924-02-22', 'EV_FIUME_ANNEX', prio=1, label='義大利')
d('SOV_IT_C', 'REGIME_IT', '1924-02-22', '1929-06-07', 2747870, 2747870, prio=1, sev='EV_FIUME_ANNEX', eev='EV_LATERAN', label='義大利', zh='含阜姆。1929-06-07 起接開發庫既有紀錄（梵蒂岡城國另列）。', en='Including Fiume; continues into the existing record from 7 Jun 1929.')
X('SOV_FIUME_FS', '1924-02-22', 'EV_FIUME_ANNEX', prio=6, label='阜姆自由邦', zh='1924-01-27 羅馬條約後由義大利併入。', en='Annexed by Italy after the Treaty of Rome (27 Jan 1924).')
X('SOV_KSCS_B', '1924-01-27', 'EV_ROME_1924', prio=3, label='塞爾維亞人、克羅埃西亞人和斯洛維尼亞人王國')
d('SOV_KSCS_C', 'REGIME_KSCS', '1924-01-27', '1926-07-26', 2885838, 2885838, prio=3, sev='EV_ROME_1924', eev='EV_AL_YU_1926', label='塞爾維亞人、克羅埃西亞人和斯洛維尼亞人王國', zh='含蘇沙克。', en='Including Sušak.')
d('SOV_KSCS_D', 'REGIME_KSCS', '1926-07-26', '1929-10-03', 2693463, 2693463, prio=3, sev='EV_AL_YU_1926', eev='EV_YU', label='塞爾維亞人、克羅埃西亞人和斯洛維尼亞人王國', zh='1929-10-03 起接開發庫既有南斯拉夫王國紀錄。', en='Continues as the existing Kingdom of Yugoslavia record from 3 Oct 1929.')
X('SOV_AL_B', '1925-01-21', 'EV_AL_REP', prio=2, label='阿爾巴尼亞')
d('SOV_AL_REP_A', 'REGIME_AL_REP', '1925-01-21', '1926-07-26', 2885839, 2885839, prio=2, sev='EV_AL_REP', eev='EV_AL_YU_1926', label='阿爾巴尼亞', zh='OHM 起日 1925-01-31，本表依 FRUS 從 01-21 起。', en='OHM starts 31 Jan; this table starts 21 Jan per FRUS.')
d('SOV_AL_REP_B', 'REGIME_AL_REP', '1926-07-26', '1928-09-01', 2800555, 2800555, prio=2, sev='EV_AL_YU_1926', eev='EV_AL_KINGDOM', label='阿爾巴尼亞', zh='1928-09-01 起接開發庫既有阿爾巴尼亞王國紀錄。', en='Continues as the existing Albanian Kingdom record from 1 Sep 1928.')
X('SOV_GR_C', '1924-03-25', 'EV_GR_REP', prio=1, label='希臘')
d('SOV_GR_REP_A', 'REGIME_GR_REP', '1924-03-25', '1924-08-06', 2863749, 2863749, prio=1, sev='EV_GR_REP', eev='EV_LAUSANNE_INFORCE', label='希臘')
d('SOV_GR_REP_B', 'REGIME_GR_REP', '1924-08-06', '1935-11-03', 2801340, 2801340, prio=1, sev='EV_LAUSANNE_INFORCE', eev='EV_GR_MONARCHY', label='希臘', zh='1926 潘加洛斯獨裁等未分。', en='The Pangalos dictatorship (1926) etc. are not split.')
d('SOV_GR_D', 'REGIME_GR', '1935-11-03', '1936-09-17', 2801340, 2801340, prio=1, sev='EV_GR_MONARCHY', label='希臘', zh='1936-09-17 起接開發庫既有紀錄。', en='Continues into the existing record from 17 Sep 1936.')
X('SOV_TR_A', '1924-08-06', 'EV_LAUSANNE_INFORCE', prio=0, label='土耳其', zh='1924-08-06 起接開發庫既有紀錄。', en='Continues into the existing record from 6 Aug 1924.')
# 北歐、愛爾蘭、美國、蘇聯
X('SOV_DK_C', '1932-01-30', label='丹麥', zh='1932-01-30 起接開發庫既有紀錄。', en='Continues into the existing record from 30 Jan 1932.')
X('SOV_SE_IWA', '1932-01-30', label='瑞典', zh='1932-01-30 起接開發庫既有紀錄。', en='Continues into the existing record from 30 Jan 1932.')
X('SOV_NO_B', '1925-08-14', 'EV_SVALBARD', label='挪威', zh='1925-08-14 起接開發庫既有紀錄（含斯瓦巴）。', en='Continues into the existing record (with Svalbard) from 14 Aug 1925.')
X('SOV_IS', END, prio=1, label='冰島')
X('SOV_IFS', '1937-12-29', 'EV_IE_CONST', prio=1, label='愛爾蘭自由邦', zh='1937-12-29 起接開發庫既有「愛爾」紀錄。', en='Continues as the existing Éire record from 29 Dec 1937.')
X('SOV_SU', '1925-01-20', 'EV_SU_1925', prio=-1, label='蘇聯', zh='框外部分裁掉；蘇聯內部加盟共和國未分。', en='Clipped to the map frame; Union republics are not split.')
d('SOV_SU_B', 'REGIME_SU', '1925-01-20', '1926-01-01', 2851271, 2851271, prio=-1, sev='EV_SU_1925', label='蘇聯',
  zh='框外部分裁掉。1926-01-01 起接開發庫既有紀錄（該紀錄含亞洲部分；1926 年以前亞洲部分本表只到地圖框東界）。', en='Clipped to the map frame; continues into the existing record from 1 Jan 1926.')
# 西班牙、摩洛哥、丹吉爾、北非
X('SOV_ES_B_IWA', '1926-05-27', prio=0, label='西班牙', zh='1926-05-27 為 OHM 換版日（里夫戰爭結束）。', en='1926-05-27 is the OHM version date (end of the Rif War).')
d('SOV_ES_C', 'REGIME_ES_K', '1926-05-27', '1931-04-14', 2862762, 2862762, prio=0, eev='EV_ES_REPUBLIC', label='西班牙', zh='1923～1930 普里莫·德里維拉獨裁未分。', en='The Primo de Rivera dictatorship (1923–1930) is not split.')
ESLOC = ESR['geometry_locator']
d('SOV_ES_REP_B', 'REGIME_ES_REP', '1931-04-14', '1939-04-01', 'ES', ESR['ohm_relation_id'], prio=0, sev='EV_ES_REPUBLIC', eev='EV_SPAIN_1939', label='西班牙共和國', loc=f'{ESLOC} ∪ {OL(2862762)}', derived=[-2, 2862762],
  zh='先撤後增開發庫既有紀錄（原起日 1931-01-01 為 OHM 年份）：改從 1931-04-14 宣布共和起；幾何照抄並補上 OHM 2862762 有而原紀錄缺的西屬撒哈拉、伊夫尼與部分加那利島嶼。內戰期間扣掉國民軍控制區。',
  en='Withdraws and re-adds the existing record (OHM start 1931): now from the proclamation of 14 Apr 1931; geometry copied plus the Spanish Sahara, Ifni and Canary islands from OHM 2862762 that it lacked; minus the Nationalist zone during the Civil War.')
ESD = ['1936-07-17', '1936-11-07', '1937-02-08', '1937-06-19', '1937-08-26', '1937-10-21', '1938-04-15', '1939-02-10', '1939-04-01']
ESE = ['EV_ES_COUP', 'EV_ES_MADRID', 'EV_MALAGA', 'EV_BILBAO', 'EV_SANTANDER', 'EV_GIJON', 'EV_VINAROS', 'EV_CATALONIA', 'EV_SPAIN_1939']
ESNOTE = ['1936-07 起事後的控制區：西北、納瓦拉—亞拉岡、塞維亞—加的斯、格拉納達、馬約卡、伊維薩、加那利、西屬撒哈拉（伊維薩 8～9 月曾被共和軍奪回，未分）。',
          '推進到馬德里外圍，與南部連成一片。', '加上馬拉加。', '加上比斯開（畢爾包）。', '加上桑坦德。', '北方全失（阿斯圖里亞斯）。',
          '亞拉岡攻勢後抵達比納羅斯海岸（之後 6 月攻佔卡斯特利翁未分）。', '加泰隆尼亞、梅諾卡之後，只剩中南部共和國控制區（扣掉手繪範圍 ES_R8）。']
for i in range(8):
    n = i + 1
    hand = (f'ES_R8（共和國控制區）：{fmt(ES_R8)}' if n == 8 else f'ES_PH[{n}]：' + '；'.join(fmt(p) for p in ES_PH[n]))
    d(f'SOV_ESNAT_{n}', 'REGIME_ES_NAT', ESD[i], ESD[i + 1], f'ESN{n}', ESR['ohm_relation_id'], prio=5, sev=ESE[i], eev=ESE[i + 1], layer='not_sovereign', label='國民軍控制區',
      loc=f'{ESLOC} ∩ 國民軍控制區第 {n} 階段（{HAND}）' if n < 8 else f'{ESLOC} − 共和國控制區（{HAND}）', derived=[-2], hand=hand,
      zh='非主權：內戰中的國民軍控制區（各階段為手繪粗略近似，待查證）。' + ESNOTE[i] + ' 西屬撒哈拉、伊夫尼 1936-07 起歸國民軍（近似）；西屬摩洛哥另列，未改。',
      en='Not sovereign: Nationalist-held territory in the Civil War (rough hand-drawn approximation per phase, pending).')
X('SOV_MA_ES_B', '1926-05-27', 'EV_RIF_END', prio=1, label='西屬摩洛哥')
d('SOV_MA_ES_C', 'REGIME_MA_ES', '1926-05-27', END, 2860422, 2860422, prio=1, sev='EV_RIF_END', label='西屬摩洛哥', zh='1936-07 起為國民軍基地（未分）。', en='Nationalist base from Jul 1936 (not split).')
X('SOV_RIF', '1926-05-27', 'EV_RIF_END', prio=5, label='里夫共和國')
X('SOV_MA_FR_B_IWA', '1926-05-27', 'EV_RIF_END', prio=1, label='法屬摩洛哥')
d('SOV_MA_FR_C', 'REGIME_MA_FR', '1926-05-27', END, 2690949, 2690949, prio=1, sev='EV_RIF_END', label='法屬摩洛哥', zh='1934 年才完全平定南部（未分，待查證）。', en='Southern pacification completed 1934 (not split, pending).')
d('SOV_TANGIER', 'REGIME_TANGIER', '1925-06-01', END, 2848366, 2848366, prio=6, sev='EV_TANGIER', layer='not_sovereign', label='丹吉爾', zh='非主權：國際共管區（1923 年巴黎公約）。OHM 2848366 只畫到丹吉爾城附近（約 0.003 平方度，實際共管區約 370 平方公里，偏小，待查證）。', en='Not sovereign: international zone (Paris Convention 1923). The OHM extent covers only the town area (too small, pending).')
X('SOV_TN_IWA', END, prio=1, label='突尼西亞')
X('SOV_MR_IWA', END, label='茅利塔尼亞')
X('SOV_LY_TR_IWA', '1934-01-01', 'EV_LY_UNIFY', label='的黎波里塔尼亞', zh='1920 年代義大利「再征服」逐步擴大控制範圍（未分，待查證）。', en='The Italian reconquest of the 1920s is not split (pending).')
X('SOV_LY_CY_IWA', '1934-01-01', 'EV_LY_UNIFY', label='昔蘭尼加', zh='1931 年奧馬爾·穆赫塔爾被俘前的抵抗未分（待查證）。', en='Resistance until 1931 is not split (pending).')
d('SOV_LY_IT', 'REGIME_LY_IT', '1934-01-01', END, 2803189, 2803189, sev='EV_LY_UNIFY', label='義屬利比亞')
X('SOV_EG_K', END, label='埃及')
X('SOV_US_IWA', '1937-07-07', label='美國', geom=make_valid(shape(next(f['geometry'] for f in ROWS if f['id'] == IDS_A['SOV_US_IWA']))))
# 近東
X('SOV_CY_IWA', '1925-05-01', 'EV_CY_COLONY', prio=1, label='賽普勒斯')
d('SOV_CY_COL', 'REGIME_CY_COL', '1925-05-01', END, 2801349, 2801349, prio=1, sev='EV_CY_COLONY', label='賽普勒斯')
X('SOV_LEBANON', '1926-05-23', 'EV_LB_REP', prio=2, label='大黎巴嫩')
d('SOV_LB_REP', 'REGIME_LB_REP', '1926-05-23', END, 2831358, 2831358, prio=2, sev='EV_LB_REP', layer='not_sovereign', label='黎巴嫩', zh=MAND, en=MANE)
X('SOV_PALESTINE', END, prio=1, label='巴勒斯坦')
X('SOV_TRANSJORDAN', END, prio=1, label='外約旦')
X('SOV_IRAQ', '1932-10-03', 'EV_IQ_INDEP', prio=1, label='伊拉克')
d('SOV_IQ_K', 'REGIME_IQ_K', '1932-10-03', END, 2839466, 2839466, prio=1, sev='EV_IQ_INDEP', label='伊拉克')
X('SOV_SYR_FED', '1924-08-06', prio=1, label='敘利亞聯邦', zh='1924-08-06 為 OHM 換版日（洛桑條約生效）。', en='OHM version date (Lausanne in force).')
d('SOV_SYR_FED_B', 'REGIME_SYR_FED', '1924-08-06', '1925-01-01', 2864020, 2864020, prio=1, eev='EV_SY_STATE', layer='not_sovereign', label='敘利亞聯邦', zh=MAND + '1924-07 拉塔基亞（阿拉維）退出聯邦未分（待查證）。', en=MANE)
d('SOV_SY_STATE', 'REGIME_SY_STATE', '1925-01-01', '1930-05-14', 2863991, 2863991, prio=1, sev='EV_SY_STATE', eev='EV_SY_REP', layer='not_sovereign', label='敘利亞',
  zh=MAND + '1925～1927 敘利亞大起義未分（待查證）。', en=MANE)
for i, (s, e, rid, sev, eev) in enumerate([('1930-05-14', '1936-09-09', 2863990, 'EV_SY_REP', 'EV_SY_1936'), ('1936-09-09', '1938-09-07', 2863989, 'EV_SY_1936', None), ('1938-09-07', END, 2863988, None, None)]):
    d(f'SOV_SY_REP_{chr(65 + i)}', 'REGIME_SY_REP', s, e, rid, rid, prio=1, sev=sev, eev=eev, layer='not_sovereign', label='敘利亞', zh=MAND, en=MANE)
d('SOV_ALAWITE', 'REGIME_ALAWITE', '1925-01-01', '1936-09-09', 2863987, 2863987, prio=2, eev='EV_SY_1936', layer='not_sovereign', label='阿拉維國', zh=MAND + 'OHM 起日 1925-01-01；1924-07 起已退出敘利亞聯邦（未分）。', en=MANE)
X('SOV_DRUZE_B', '1927-06-01', prio=2, label='德魯茲山國', zh='1927-06-01 為 OHM 換版日。', en='OHM version date.')
d('SOV_DRUZE_C', 'REGIME_DRUZE', '1927-06-01', '1936-09-09', 2864005, 2864005, prio=2, eev='EV_SY_1936', layer='not_sovereign', label='德魯茲山國', zh=MAND, en=MANE)
d('SOV_HATAY', 'REGIME_HATAY', '1938-09-02', '1939-06-29', 2864001, 2864001, prio=6, sev='EV_HATAY_STATE', eev='EV_HATAY', layer='not_sovereign', label='哈塔伊國',
  zh='非主權：法國委任統治下的自治國，1938-07 起法、土軍共同駐守（未另列佔領）。1939-06-29 併入土耳其（接開發庫既有土耳其紀錄）。', en='Not sovereign: autonomous state under the French mandate with joint Franco-Turkish garrison; annexed by Turkey on 29 Jun 1939.')

# 開發庫既有紀錄（prio 9，不送出，只扣除與 QA）；排除本批撤回的紀錄
RETRACT_IDS = {IDS_A[a] for a, _ in RETRACT} | {ESR['id']}
LO = min(x['start'] for x in DEFS); HI = '1939-07-01'
FIXED = [dict(ph=f"DB:{f['properties']['slug']}", geom=make_valid(shape(f['geometry'])), start=f['properties']['start'], end=f['properties']['end'] or '9999-12-31', prio=9,
              label=f['properties']['slug'], sev=None, eev=None, derived=[], id=f['id'])
         for f in ROWS if f['id'] not in RETRACT_IDS and f['properties']['start'] < HI and (f['properties']['end'] or '9999') > LO]
assert len(RETRACT_IDS) == 35 and RETRACT_IDS <= {f['id'] for f in ROWS}, len(RETRACT_IDS)

# ── 引擎（同 A 批）──
SEGS = []
for x in DEFS:
    higher = [h for h in DEFS + FIXED if h['prio'] > x['prio'] and h['start'] < x['end'] and x['start'] < h['end'] and h['geom'].intersects(x['geom'])
              and h['geom'].intersection(x['geom']).area > 1e-3]
    cuts = sorted({c for h in higher for c in (h['start'], h['end']) if x['start'] < c < x['end']})
    bounds = [x['start']] + cuts + [x['end']]
    pieces = []
    for a, b in zip(bounds, bounds[1:]):
        act = [h for h in higher if h['start'] <= a < h['end']]
        g = clean(x['geom'].difference(unary_union([h['geom'] for h in act]))) if act else x['geom']
        if pieces and pieces[-1]['g'].symmetric_difference(g).area < 1e-3:
            pieces[-1]['b'] = b; continue
        pieces.append(dict(a=a, b=b, g=g, act=act))
    def cut_event(c):
        for h in higher:
            if h['start'] == c and h.get('sev'): return h['sev']
            if h['end'] == c and h.get('eev'): return h['eev']
        return None
    keep = [p for p in pieces if p['g'].area >= max(1e-4, 0.002 * x['geom'].area) or not p['act']]
    for i, p in enumerate(pieces):
        if p not in keep: continue
        sev = x['sev'] if p['a'] == x['start'] else cut_event(p['a'])
        eev = x['eev'] if p['b'] == x['end'] else cut_event(p['b'])
        ph = x['ph'] if len(pieces) == 1 else f"{x['ph']}_{i + 1}"
        SEGS.append(dict(x=x, ph=ph, start=p['a'], end=p['b'], g=p['g'], act=p['act'], sev=sev, eev=eev))
SEGS.sort(key=lambda s: (s['x']['regime'], s['start']))
for i, s in enumerate(SEGS):
    for t in SEGS[i + 1:]:
        if t['x']['regime'] == s['x']['regime'] and t['start'] < s['end'] and s['start'] < t['end']:
            raise SystemExit(f"同政權重疊：{s['ph']} {t['ph']}")

def lic(rids):
    rids = [r for r in rids if r in MAN]
    cc_by = any(MAN[r]['geometry_license'] == 'cc_by' for r in rids)
    attrs = sorted({a for r in rids for a in (MAN[r]['attribution'] or '').split('; ') if a})
    return ('cc_by' if cc_by else 'cc0'), ('; '.join(attrs) or None), sum(MAN[r]['osm_derived_way_count'] for r in rids)
GEOM = {}
def ref(e): return ('{{%s}}' % e) if e and not re.match(r'^[0-9a-f]{8}-', e) else e
def endnote(end):
    return ('到 1938-12-31（本批試驗期間終點，無迄事件）。', ' Until 31 Dec 1938 (end of this batch).') if end == END else ('', '')
ESPROV = {'memberWayLicense': ESR['provenance']['memberWayLicense'], 'osmDerivedWayCount': ESR['provenance']['osmDerivedWayCount'], 'ohmFixme': ESR['provenance']['ohmFixme'],
          'ohmRelationSource': ESR['provenance']['ohmRelationSource'], 'ohmAdminLevel': ESR['provenance']['ohmAdminLevel'], 'ohmChangeset': ESR['provenance']['ohmChangeset'],
          'ohmTimestamp': ESR['provenance']['ohmTimestamp'], 'copiedFrom': ESR['id']}

# 撤回（先撤後增）
for aph, xph in RETRACT:
    post = '/api/v1/sovereignty-records/{{%s}}/retraction' % aph
    add('04-retract', aph.lower(), 'RETRACTED_' + aph, post, {'reason': f'兩次大戰之間 B 批：A 批迄於 1924-01-01（試驗期間終點），延長迄日後重送（{xph}）'}, {'fix': True, 'readd': xph})
add('04-retract', 'sov_r2860484', 'RETRACTED_SOV_R2860484', '/api/v1/sovereignty-records/{{SOV_R2860484}}/retraction',
    {'reason': '兩次大戰之間 B 批：起日 1931-01-01（OHM 年份）改為 1931-04-14 宣布共和，並扣掉內戰國民軍控制區後重送（SOV_ES_REP_B）'}, {'fix': True, 'readd': 'SOV_ES_REP_B'})
add('04-retract', 'occ_ruhr', 'RETRACTED_OCC_RUHR', '/api/v1/occupation-attributions/{{OCC_RUHR}}/retraction',
    {'reason': '兩次大戰之間 B 批：A 批迄於 1924-01-01（試驗期間終點），延長到 1925-08-25 撤離後重送（OCC_RUHR_X）'}, {'fix': True, 'readd': 'OCC_RUHR_X'})

for s in SEGS:
    x = s['x']; GEOM[s['ph']] = s['g']; a = x['base']
    if x['ph'] == 'SOV_US_IWA_X':
        b = copy.deepcopy(a); b['validPeriod'] = {'start': s['start'], 'end': s['end']}
        b['provenance']['trialWindow'] = TWN
        b['note'] = {'zh-Hant': '延長 A 批紀錄（原迄 1924-01-01，先撤後增），接開發庫既有 1937-07-07 起的美國紀錄。幾何照抄該紀錄，1918～1937 年的差異未處理（待查證）；主要給事件參與者用。',
                     'en': 'Extends the batch-A record to the existing US record of 7 Jul 1937. Geometry copied from it; differences not handled (pending).'}
        add('05-sovereignty', s['ph'].lower(), s['ph'], '/api/v1/sovereignty-records', b, {'replaces': 'SOV_US_IWA'}, geom=s['ph']); continue
    derived = list(dict.fromkeys(x['derived'] + [r for h in s['act'] for r in h.get('derived', [])]))
    loc = (x['loc'] or '') + ''.join(f" − {lb}" for lb in dict.fromkeys(h['label'] for h in s['act']))
    gl, attr, osm = lic(derived)
    zh = x['zh'] + (('扣掉同期：' + '、'.join(dict.fromkeys(h['label'] for h in s['act'])) + '。') if s['act'] else '')
    en = x['en'] + ((' Minus: ' + ', '.join(dict.fromkeys(h['label'] if h['ph'].startswith('DB:') else h['ph'] for h in s['act'])) + '.') if s['act'] else '')
    ez, ee = endnote(s['end'])
    if x['rid'] in MAN:
        m = MAN[x['rid']]
        ohmf = {'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'], 'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date']}
        prov = {'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': osm, 'ohmFixme': m['fixme'], 'ohmRelationSource': m['relation_source'],
                'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'], 'ohmTimestamp': m['ohm_timestamp']}
        if m.get('repair'): prov['ohmRepair'] = m['repair']
        src = '{{SRC_OHM_IWB}}' if x['rid'] in OWN else '{{SRC_OHM_IWA}}'
        coast = '{{SRC_NE_LAND}}'
    else:   # 西班牙共和國幾何（開發庫既有紀錄）
        ohmf = {'ohmVersion': ESR['ohm_version'], 'ohmFetchedAt': ESR['ohm_fetched_at'], 'ohmStartRaw': ESR['ohm_start_raw'], 'ohmEndRaw': ESR['ohm_end_raw']}
        prov = dict(ESPROV); src = '{{SRC_OHM}}'; gl, attr = ESR['geometry_license'], ESR['attribution']; coast = '{{SRC_NE_LAND}}'   # 開發庫既有紀錄的來源 id 換回 borders-dev 的 placeholder
    b = {'regimeId': '{{%s}}' % x['regime'], 'geometry': None, 'validPeriod': {'start': s['start'], 'end': s['end']}, 'layerStatus': x['layer'],
         'geometrySourceId': src, 'geometryLocator': loc, 'geometryLicense': gl, 'attribution': attr, 'startEventId': ref(s['sev']), 'endEventId': ref(s['eev']),
         'ohmRelationId': x['rid'], **ohmf,
         'provenance': {**prov, 'coastline': coast, 'licenseReview': 'osm_derived_ways' if prov.get('osmDerivedWayCount') else None, 'trialWindow': TWN},
         'note': {'zh-Hant': (zh + ez).strip(), 'en': (en + ee).strip()} if (zh + ez).strip() else None}
    if a: b['provenance']['replaces'] = '{{%s}}' % x['ph'][:-2]
    if x['ph'] == 'SOV_ES_REP_B': b['provenance']['replaces'] = ESR['id']
    if len(derived) > 1 or x['hand']: b['provenance'].update({'derivedFrom': [OL(r) for r in derived if r in MAN] + ([ESLOC] if -2 in derived else []), 'derivation': loc})
    if x['hand']: b['provenance']['handDrawn'] = x['hand'] + '（近似，待查證）'
    add('05-sovereignty', s['ph'].lower(), s['ph'], '/api/v1/sovereignty-records', b, None, geom=s['ph'])

# ── 佔領歸屬 ──
def occ(ph, occd, occr, kind, start, end, basis, co, zh, en):
    add('06-occupation', ph.lower(), ph, '/api/v1/occupation-attributions', {'occupiedRegimeId': '{{%s}}' % occd, 'occupierRegimeId': '{{%s}}' % occr, 'controlKind': kind,
        'validPeriod': {'start': start, 'end': end}, 'basisEventId': ref(basis), 'coOccupied': co, 'note': {'zh-Hant': zh, 'en': en}})
occ('OCC_RUHR_X', 'REGIME_RUHR', 'REGIME_FR3', 'military_administration', '1923-01-11', '1925-08-25', 'EV_RUHR', True, '法比共同軍事佔領（列法國並標共同佔領）。延長 A 批紀錄（先撤後增）。', 'Joint Franco-Belgian military occupation (extends the batch-A record).')
occ('OCC_RHZ1', 'REGIME_RHZ1', 'REGIME_UK', 'military_administration', START, '1926-01-31', None, True, '英軍為主的協約國佔領（比利時軍亦駐；列英國並標共同佔領）。1924-01-01 為本批起點。', 'Allied occupation led by Britain (with Belgian troops).')
occ('OCC_RHZ2', 'REGIME_RHZ2', 'REGIME_FR3', 'military_administration', START, '1929-11-30', None, False, '法軍佔領（1923 年美軍撤出後）。1924-01-01 為本批起點。', 'French occupation (after the US withdrawal of 1923).')
occ('OCC_RHZ3', 'REGIME_RHZ3', 'REGIME_FR3', 'military_administration', START, '1930-06-30', None, False, '法軍佔領。1924-01-01 為本批起點。', 'French occupation.')

# ── 衝突（全部用固定點）──
CF = [('CF_ES_RIF', 'REGIME_ES_K', 'REGIME_RIF', 'EV_RIF', 'EV_RIF_END', ([-3.93, 35.2], '阿日迪爾—阿盧塞馬斯灣（里夫共和國首府，固定點）'), 'B1'),
      ('CF_FR_RIF', 'REGIME_FR3', 'REGIME_RIF', 'EV_RIF_FR', 'EV_RIF_END', ([-4.5, 34.6], '沃爾加河谷（1925 里夫軍進攻法屬摩洛哥處，固定點）'), 'B1'),
      ('CF_ES_CW', 'REGIME_ES_REP', 'REGIME_ES_NAT', 'EV_ES_COUP', 'EV_SPAIN_1939', ([-3.72, 40.45], '馬德里大學城前線（固定點）'), 'B3')]
cf_qa = {}
for ph, a_, b_, sev, eev, (pt, method), sub in CF:
    cf_qa[ph] = pt
    add('07-conflict', ph.lower(), ph, '/api/v1/conflict-records', {'regimeAId': '{{%s}}' % a_, 'regimeBId': '{{%s}}' % b_, 'startEventId': '{{%s}}' % sev,
        'endEventId': '{{%s}}' % eev, 'location': {'type': 'Point', 'coordinates': pt}, 'locationMethod': method}, sub=sub)

# ── 子批分配 ──
def sub_of(day):
    for n, a, b in SUBS:
        if a <= day < b: return n
order = [n for n, _, _ in SUBS]
for rq in REQ:
    b = rq['body']
    if rq['sub'] is None and rq['cat'] in ('05-sovereignty', '06-occupation'): rq['sub'] = sub_of(b['validPeriod']['start'])
    elif rq['sub'] is None and rq['cat'] == '03-event': rq['sub'] = sub_of(EVD[rq['ph']])
byph = {rq['ph']: rq for rq in REQ}
# 撤回放在重送紀錄最早的子批
for rq in REQ:
    if rq['cat'] == '04-retract':
        x = rq['meta']['readd']; subs = [r['sub'] for r in REQ if r['cat'] in ('05-sovereignty', '06-occupation') and (r['ph'] == x or r['ph'].startswith(x + '_'))]
        assert subs, x; rq['sub'] = min(subs, key=order.index)
changed = True
while changed:
    changed = False
    for rq in REQ:
        if rq['sub'] is None: continue
        for m in re.findall(r'\{\{(\w+)\}\}', json.dumps(rq['body'], ensure_ascii=False) + rq['post']):
            t = byph.get(m)
            if t is None or t['cat'] == '04-retract': continue
            if t['sub'] is None or order.index(t['sub']) > order.index(rq['sub']):
                t['sub'] = rq['sub']; changed = True
# 與前批 placeholder 撞名的本批項目改名（加 _IWB）
RESERVED = set(open(os.path.join(HERE, 'prior-placeholders.txt')).read().split())
REN = {rq['ph']: rq['ph'] + '_IWB' for rq in REQ if rq['ph'] in RESERVED and rq['cat'] != '04-retract'}
assert not (set(REN.values()) & RESERVED)
def _ren(t): return re.sub(r'\{\{(\w+)\}\}', lambda m: '{{%s}}' % REN.get(m.group(1), m.group(1)), t)
for rq in REQ:
    rq['ph'] = REN.get(rq['ph'], rq['ph'])
    if rq['cat'] != '04-retract': rq['post'] = _ren(rq['post'])
    rq['body'] = json.loads(_ren(json.dumps(rq['body'], ensure_ascii=False)))
    if rq['geom']: rq['geom'] = REN.get(rq['geom'], rq['geom'])
GEOM = {REN.get(k, k): v for k, v in GEOM.items()}
for s_ in SEGS: s_['ph'] = REN.get(s_['ph'], s_['ph'])
cf_qa = {REN.get(k, k): v for k, v in cf_qa.items()}
EVD = {REN.get(k, k): v for k, v in EVD.items()}
print('renamed', sorted(REN))
unused = [rq['ph'] for rq in REQ if rq['sub'] is None]
assert not unused, unused
# 所有 placeholder 都要能解析（本批或前批）
mine = {rq['ph'] for rq in REQ}
unres = sorted({m for rq in REQ for m in re.findall(r'\{\{(\w+)\}\}', json.dumps(rq['body'], ensure_ascii=False) + rq['post'])} - mine - RESERVED)
assert not unres, unres
for n in order:
    os.makedirs(os.path.join(ROOT, 'requests', n), exist_ok=True)
    for f in os.listdir(os.path.join(ROOT, 'requests', n)):
        if f.endswith('.json'): os.remove(os.path.join(ROOT, 'requests', n, f))
counter = {}
CATO = ['01-source', '02-regime', '03-event', '04-retract', '05-sovereignty', '06-occupation', '07-conflict']
for rq in sorted(REQ, key=lambda r: CATO.index(r['cat'])):
    k = (rq['sub'], rq['cat']); counter[k] = counter.get(k, 0) + 1
    req = {'_placeholder': rq['ph'], '_post': rq['post'], **({'_geometryFrom': rq['geom']} if rq['geom'] else {}), **({'_meta': rq['meta']} if rq['meta'] else {}), 'body': rq['body']}
    with open(os.path.join(ROOT, 'requests', rq['sub'], f"{rq['cat']}-{counter[k]:02d}-{rq['name']}.json"), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')

# ── QA：每個切點日互不重疊；接點不留空隙（每筆本批紀錄迄日當天，原範圍要被其他紀錄蓋住）──
items_all = [(s['ph'], s['g'], s['start'], s['end']) for s in SEGS if s['x']['ph'] != 'SOV_US_IWA_X'] + [(f['ph'], f['geom'], f['start'], f['end']) for f in FIXED]
DAYS = sorted({s['start'] for s in SEGS if START <= s['start'] < END} | {f['start'] for f in FIXED if START <= f['start'] < '1939-07-01'} | {START})
qa = {'overlaps': {}, 'coverage_deg2': {}, 'gaps': {}, 'conflictLocations': cf_qa, 'records': {}}
for day in DAYS:
    items = [(k, g) for k, g, s0, e0 in items_all if s0 <= day < e0]
    tree = STRtree([g for _, g in items]); worst = []
    for i_, (ni, gi) in enumerate(items):
        for j in tree.query(gi):
            if j <= i_: continue
            a_ = gi.intersection(items[j][1]).area
            if a_ > 1e-3: worst.append((ni, items[j][0], round(a_, 4)))
    qa['overlaps'][day] = [w for w in worst if not (w[0].startswith('DB:') and w[1].startswith('DB:'))]
    qa.setdefault('overlapsExistingOnly', {})[day] = [w for w in worst if w[0].startswith('DB:') and w[1].startswith('DB:')]
    qa['coverage_deg2'][day] = round(unary_union([g for _, g in items]).area, 2)
for s in SEGS:
    if s['x']['ph'] == 'SOV_US_IWA_X' or s['end'] >= END and s['end'] != '1939-04-01' and s['end'] != '1939-06-29': continue
    day = s['end']
    cover = unary_union([g for k, g, s0, e0 in items_all if s0 <= day < e0])
    miss = s['g'].difference(cover).area
    if miss > 0.01: qa['gaps'][s['ph']] = [day, round(miss, 3)]
for s in SEGS:
    qa['records'][s['ph']] = {'period': [s['start'], s['end']], 'area': round(s['g'].area, 3), 'sev': s['sev'], 'eev': s['eev'], 'minus': [h['ph'] for h in s['act']]}
qa['retracted'] = [a for a, _ in RETRACT] + ['SOV_R2860484', 'OCC_RUHR']
qa['renamed'] = REN
qa['requestCounts'] = {n: sum(1 for rq in REQ if rq['sub'] == n) for n in order}
qa['pendingEvents'] = [rq['ph'] for rq in REQ if rq['cat'] == '03-event' and not rq['body']['citations']]
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in GEOM.items()]},
          open(os.path.join(ROOT, 'interwar-b-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(qa, open(os.path.join(ROOT, 'qa.json'), 'w'), indent=1, ensure_ascii=False)
bad = [(day, w) for day in DAYS for w in qa['overlaps'][day]]
print('requests', qa['requestCounts'], 'segments', len(SEGS), 'events', sum(1 for r in REQ if r['cat'] == '03-event'), 'pending', len(qa['pendingEvents']))
for day, w in bad: print('OVERLAP', day, w)
for k, v in qa['gaps'].items(): print('GAP', k, v)
if '--strict' in sys.argv: assert not bad and not qa['gaps']
