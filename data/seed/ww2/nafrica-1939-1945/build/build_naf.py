#!/usr/bin/env python3
"""北非、近東與冰島 1939-01-01～1945-09-03（二戰）：接續 B 批暫迄 1939-01-01 的 14 個政權（先撤後增延長），
加上義屬利比亞戰役、埃及西部被佔、火炬行動、突尼西亞戰役、敘利亞—黎巴嫩（維琪／自由法國）、伊拉克 1941 政變與英軍介入、
英美駐軍冰島、英蘇佔領伊朗（在 60°E 框內的部分）。
手繪範圍（佔領區、戰線）都是粗略近似（待查證）。產生 ../requests/N{1,2,3}/*.json、../nafrica-derived.geojson、../qa.json。
輸入：../exp_39.json（開發庫唯讀匯出：1938-06 後的主權紀錄，框 -25～65°E 裁切）、../rows14.json（14 筆紀錄欄位）、../raw/r2694890.json（OHM 伊朗）。
"""
import json, os, re, math, datetime, glob
import shapefile
from shapely.geometry import shape, mapping, MultiPolygon, Polygon, Point, LineString, box
from shapely.ops import unary_union, polygonize
from shapely.validation import make_valid
from shapely import set_precision, affinity
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
END = '1945-09-03'; START = '1939-01-01'
TRIAL = '北非、近東與冰島批 1939-01-01～1945-09-02'
def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x, 'geoms', []) for p in polys(y)]
def clean(x, m=1e-5):
    x = make_valid(set_precision(make_valid(x), 1e-6)); ps = [p for p in polys(x) if p.area > m]
    return MultiPolygon(ps) if ps else None
def circ(x, y, r): return affinity.scale(Point(x, y).buffer(r, 32), xfact=1 / math.cos(math.radians(y)), yfact=1)
nd = lambda s: (datetime.date.fromisoformat(s) + datetime.timedelta(days=1)).isoformat()
fmt = lambda pts: ' · '.join(f'{x},{y}' for x, y in pts)
# ── 既有資料 ──
F = json.load(open(os.path.join(ROOT, 'exp_39.json')))['features']
R = [dict(id=f['id'], slug=f['properties']['slug'], rid=f['properties']['regime_id'], lo=f['properties']['lo'], hi=f['properties']['hi'] or '9999-12-31',
          g=make_valid(shape(f['geometry']))) for f in F if f['geometry']]
ROWS = {r['slug']: r for r in json.loads(open(os.path.join(ROOT, 'rows14.json')).readline())}
G14 = {s: next(x['g'] for x in R if x['id'] == ROWS[s]['id']) for s in ROWS}
ID14 = {s: ROWS[s]['id'] for s in ROWS}
def others_over(lo, hi, excl_ids, g):
    gs = [r['g'] for r in R if r['lo'] < hi and r['hi'] > lo and r['id'] not in excl_ids and r['g'].intersects(g)]
    return unary_union(gs) if gs else Polygon()
# ── 既有 id ──
RG = dict(UK='01a18e71-cba5-7726-90e3-9b90ab344afd', IT='01a18e71-cc66-7f28-9763-3316d99f425d', DE='01a18e71-c9ba-719c-bc51-3086edef89bc',
          VICHY='01a18e71-cb9b-790b-8f4b-671d0e7359bc', US='01a191b4-36ac-792e-9113-9a46cc51fc9b', SU='01a18e71-cc2e-7f80-8d62-81879da43d7b',
          ES='01a18e71-ccbd-7a45-84f8-b9b537d8b769', CFLN='01a191a0-45aa-7cfc-9c24-39116f0d8f3d', GPRF='01a191a0-45a3-7187-ab39-3c324a023dd2',
          FR3='01a18e71-cb8c-761f-83c5-944ad7c6a879', TR='01a18e71-ccaa-7e5f-8e69-06921e5214cc')
for s in ROWS: RG[s] = ROWS[s]['regimeId']
EV_TORCH = '01a19112-056a-79a5-b1f7-e975f7580ec2'; EV_IS_REP_X = '01a191a0-a011-75a4-accd-fa15bc1b8ba9'; EV_VICHY_ARM = '01a18e71-cf6d-7e60-adb3-1813e221262f'
SRC = dict(FRUS1940V2='01a18fda-f981-7c7f-a327-8608abbd2ded', FRUS1940V3='01a18e71-c99a-7793-b034-59044869fb48', FRUS1941V2='01a19041-0935-77d1-b5a2-60f211b91d2a',
           NE='01a18e71-c977-7a2c-afe3-cb56ea3ec9fa')
REQ = []
def add(sub, cat, name, ph, post, body, meta=None, geom=None, readd=None):
    REQ.append(dict(sub=sub, cat=cat, name=name, ph=ph, post=post, body=body, meta=meta, geom=geom, readd=readd))
# ── 來源 ──
ir_raw = json.load(open(os.path.join(ROOT, 'raw', 'r2694890.json'))); OSM_BASE = ir_raw['osm3s']['timestamp_osm_base']
add('N1', '01-source', 'src_ohm_naf', 'SRC_OHM_NAF', '/api/v1/sources', {'sourceKind': 'dataset',
    'title': 'OpenHistoricalMap — boundary=administrative 關係（伊朗 1935～1959，北非、近東與冰島 1939～1945 批）', 'publisher': 'OpenHistoricalMap contributors',
    'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright', 'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
    'publishedText': f'Overpass osm_base {OSM_BASE}；relation/2694890；其餘地區沿用兩次大戰之間 B 批的 OHM 幾何', 'note': 'OHM 整體以 CC0 1.0 釋出。'})
GPO = 'United States Department of State; United States Government Printing Office, Washington'
add('N1', '01-source', 'src_frus_1941v3', 'SRC_FRUS_1941V3', '/api/v1/sources', {'sourceKind': 'official_record',
    'title': 'Foreign Relations of the United States, Diplomatic Papers, 1941, The British Commonwealth; The Near East and Africa, Volume III', 'publisher': GPO,
    'licenseCode': 'us_federal_pd', 'licenseEvidenceUrl': 'https://www.state.gov/copyright-information', 'url': 'https://history.state.gov/historicaldocuments/frus1941v03', 'publishedText': '1959 年出版'})
add('N1', '01-source', 'src_frus_1943v4', 'SRC_FRUS_1943V4', '/api/v1/sources', {'sourceKind': 'official_record',
    'title': 'Foreign Relations of the United States, Diplomatic Papers, 1943, The Near East and Africa, Volume IV', 'publisher': GPO,
    'licenseCode': 'us_federal_pd', 'licenseEvidenceUrl': 'https://www.state.gov/copyright-information', 'url': 'https://history.state.gov/historicaldocuments/frus1943v04', 'publishedText': '1964 年出版'})
# ── 政權 ──
NEWREG = [
 ('REGIME_FREE_FR', 'free-france', 'France libre', 'fr', '自由法國', 'Free France', '戴高樂領導的流亡抵抗政府（1941-09 起為法蘭西民族委員會）；1943-06-03 起併入法蘭西民族解放委員會。'),
 ('REGIME_IS_REP', 'republic-of-iceland', 'Lýðveldið Ísland', 'is', '冰島共和國', 'Republic of Iceland', None),
 ('REGIME_IR', 'imperial-state-of-iran', 'کشور شاهنشاهی ایران', 'fa', '伊朗帝國', 'Imperial State of Iran', None),
 ('REGIME_IR_SU', 'soviet-occupied-iran-1941', 'Soviet-occupied northern Iran', 'en', '蘇聯佔領下的伊朗北部', 'Soviet-occupied northern Iran', None),
 ('REGIME_IR_UK', 'british-occupied-iran-1941', 'British-occupied southern Iran', 'en', '英國佔領下的伊朗南部', 'British-occupied southern Iran', None),
 ('REGIME_EG_IT40', 'italian-occupied-egypt-1940', 'Italian-occupied western Egypt (Sidi Barrani)', 'en', '義大利佔領下的埃及西部（西迪巴拉尼）', 'Italian-occupied western Egypt (Sidi Barrani)', None),
 ('REGIME_EG_AX42', 'axis-occupied-egypt-1942', 'Axis-occupied western Egypt', 'en', '軸心國佔領下的埃及西部（阿拉曼以西）', 'Axis-occupied western Egypt (west of El Alamein)', None),
 ('REGIME_CYR_UK', 'british-occupied-cyrenaica-1941', 'British-occupied Cyrenaica', 'en', '英軍佔領下的昔蘭尼加（1941～1942）', 'British-occupied Cyrenaica (1941–1942)', None),
 ('REGIME_KUFRA_FF', 'free-french-occupied-kufra', 'Free French-occupied Kufra', 'en', '自由法國佔領的庫夫拉', 'Free French-occupied Kufra', None),
 ('REGIME_BMA_LY', 'british-military-administration-libya', 'British Military Administration of Tripolitania and Cyrenaica', 'en', '英國軍政府（的黎波里塔尼亞、昔蘭尼加）', 'British Military Administration (Tripolitania and Cyrenaica)', None),
 ('REGIME_FEZ_FR', 'french-military-territory-fezzan', 'Territoire militaire du Fezzan', 'fr', '法國軍管費贊', 'French military territory of Fezzan', None),
 ('REGIME_TN_AX', 'axis-occupied-tunisia', 'Axis-occupied Tunisia', 'en', '軸心國佔領下的突尼西亞', 'Axis-occupied Tunisia', None),
]
for i, (ph, slug, orig, lang, zh, en, _) in enumerate(NEWREG, 1):
    add('N1', '02-regime', slug, ph, '/api/v1/regimes', {'slug': slug, 'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]}, meta={'priorPlaceholder': False})
for ph, slug, *_ in NEWREG: RG[ph] = '{{%s}}' % ph
# ── 事件 ──
EV = {}
def ev(ph, date, kind, zh, en, parts, cites=None, note_zh=None, note_en=None, end=None, prec='day'):
    EV[ph] = date
    b = {'eventKind': kind, 'occurred': {'start': date, 'end': end or nd(date)}, 'datePrecision': prec, 'summary': {'zh-Hant': zh, 'en': en},
         'participants': [{'regimeId': RG[r], 'role': role} for r, role in parts], 'citations': cites or []}
    tz = note_zh or ''; te = note_en or ''
    if not cites: tz = ('未找到正式出處（待查證）。' + tz).strip(); te = ('No formal source located yet (pending). ' + te).strip()
    if tz: b['timeNote'] = {'zh-Hant': tz, 'en': te or tz}
    add('N1', '03-event', ph.lower(), ph, '/api/v1/events', b, meta={'verification': 'verified' if cites else 'pending（待查證）'})
def cite(src, loc, note): return {'sourceId': SRC.get(src, '{{%s}}' % src), 'locator': loc, 'evidenceNote': note}
B, S, O = 'belligerent', 'signatory', 'other'
ev('EV_IS_UK_OCC', '1940-05-10', 'campaign', '英軍登陸冰島（叉子行動），開始駐軍', 'British forces land in Iceland (Operation Fork)', [('UK', B), ('kingdom-of-iceland', O)],
   [cite('FRUS1940V2', 'Doc. 794', '美國國務卿 1940-05-15 覆英國大使：確認收到 5/10 照會，英國政府於 5 月 10 日上午派兵登陸冰島。')])
ev('EV_UK_DE_WAR', '1939-09-03', 'war', '英國對德國宣戰，英德進入戰爭狀態', 'Britain declares war on Germany', [('UK', B), ('DE', B)], note_zh='英國最後通牒 9/3 上午 11 時到期。', note_en='British ultimatum expired 11:00 on 3 Sep.')
ev('EV_IT_UK_WAR', '1940-06-10', 'war', '義大利向英國宣戰（6/11 起進入戰爭狀態），北非戰事開始', 'Italy declares war on Britain (state of war from 11 June); war in North Africa begins', [('IT', B), ('UK', B)],
   [cite('FRUS1940V2', 'Doc. 835, pp. 716–717', '義大利大使照會：齊亞諾 6/10 以同樣措辭通知英國大使，義大利自 6/11 起與英國處於戰爭狀態。')])
ev('EV_TANGIER_ES', '1940-06-14', 'campaign', '西班牙軍隊（西屬摩洛哥哈里發部隊）進駐丹吉爾國際共管區', 'Spanish (Khalifan) troops occupy the Tangier International Zone', [('ES', B), ('tangier-international-zone', O)],
   [cite('FRUS1940V3', 'Doc. 712, pp. 783–784', '駐西班牙大使 1940-06-14 電：西班牙外長照會，部隊奉命當天上午進入丹吉爾區，稱為臨時性質。')],
   '西班牙 1940-11-03 宣布將丹吉爾併入西屬摩洛哥行政（本表仍記為佔領，未改主權）；1945-10-11 撤出。')
ev('EV_SIDI_BARRANI', '1940-09-16', 'campaign', '義軍攻入埃及，佔領西迪巴拉尼', 'Italian army advances into Egypt and occupies Sidi Barrani', [('IT', B), ('UK', B), ('kingdom-of-egypt', O)], note_zh='義軍 9/13 越境。', note_en='Italian forces crossed the frontier on 13 Sep.')
ev('EV_SIDI_RECAP', '1940-12-10', 'battle', '英軍羅盤行動收復西迪巴拉尼', 'Operation Compass: British recapture Sidi Barrani', [('UK', B), ('IT', B)], note_zh='行動 12/9 開始；索倫一帶 12 月中旬才肅清（未分）。', note_en='Sollum area cleared mid-December (not split).')
ev('EV_TOBRUK_UK1', '1941-01-22', 'battle', '英軍攻佔托布魯克', 'British capture Tobruk', [('UK', B), ('IT', B)], note_zh='巴爾迪亞 1/5 已陷落（未分）。', note_en='Bardia fell on 5 Jan (not split).')
ev('EV_BEDA_FOMM', '1941-02-07', 'battle', '貝達富姆之戰：義大利第十軍團投降，英軍控制昔蘭尼加', 'Beda Fomm: Italian Tenth Army surrenders; British control Cyrenaica', [('UK', B), ('IT', B)], note_zh='班加西 2/6 已陷落。', note_en='Benghazi fell on 6 Feb.')
ev('EV_DAK', '1941-02-14', 'campaign', '德國非洲軍團先頭部隊抵達的黎波里', 'Advance units of the German Afrika Korps reach Tripoli', [('DE', B), ('UK', B)])
ev('EV_KUFRA', '1941-03-01', 'battle', '自由法國勒克萊爾部隊攻佔庫夫拉', 'Free French forces under Leclerc capture Kufra', [('REGIME_FREE_FR', B), ('IT', B)])
ev('EV_IQ_COUP', '1941-04-01', 'political', '伊拉克拉希德·阿里政變，親軸心政府上台', 'Rashid Ali coup in Iraq installs a pro-Axis government', [('kingdom-of-iraq', O)],
   [cite('SRC_FRUS_1941V3', 'Doc. 500', '英國大使館 1941-04-05 備忘錄：拉希德·阿里 4/3 接掌政府機關，英國不承認新政權；攝政已離開巴格達。')],
   '政變 4/1 夜起事（通行說法）；FRUS 記 4/3 接掌政府機關。', 'Coup began on the night of 1 Apr; FRUS records control of government offices on 3 Apr.', end='1941-04-04')
ev('EV_BENGHAZI_AX1', '1941-04-04', 'battle', '軸心軍反攻收復班加西，英軍退出昔蘭尼加', 'Axis counter-offensive retakes Benghazi; British withdraw from Cyrenaica', [('DE', B), ('IT', B), ('UK', B)])
ev('EV_TOBRUK_SIEGE', '1941-04-11', 'campaign', '托布魯克被圍（英聯邦守軍堅守至 12 月）', 'Siege of Tobruk begins', [('DE', B), ('IT', B), ('UK', B)])
ev('EV_IQ_WAR', '1941-05-02', 'war', '英伊戰爭：伊軍圍攻哈巴尼亞空軍基地，英軍開火', 'Anglo-Iraqi War begins at RAF Habbaniya', [('UK', B), ('kingdom-of-iraq', B)],
   [cite('SRC_FRUS_1941V3', 'Doc. 524', '駐伊拉克公使 1941-05-04 電：英國轟炸機在巴格達、拉希德營上空作戰；4/30 起各國僑民避入使館。')], '開戰日 5/2 為通行說法；FRUS 只證明 5/4 時戰事已在進行。', 'Start date per common accounts; FRUS shows fighting by 4 May.')
ev('EV_IQ_ARMISTICE', '1941-05-31', 'armistice', '英伊停戰，拉希德·阿里出走，英軍此後駐留伊拉克', 'Anglo-Iraqi armistice; British forces remain in Iraq', [('UK', S), ('kingdom-of-iraq', S)],
   [cite('SRC_FRUS_1941V3', 'Doc. 530', '駐伊拉克公使 1941-05-31 電：停戰協定當天下午簽字。')])
ev('EV_SY_INV', '1941-06-08', 'campaign', '英軍與自由法國進攻敘利亞、黎巴嫩（出口行動）', 'British and Free French invade Syria and Lebanon (Operation Exporter)', [('UK', B), ('REGIME_FREE_FR', B), ('VICHY', B)],
   [cite('SRC_FRUS_1941V3', 'Doc. 768, pp. 725–726', '邱吉爾 1941-06-07 致羅斯福：「明天早上」以相當兵力進入敘利亞，戴高樂的自由法國部隊參與。')])
ev('EV_US_ICELAND', '1941-07-07', 'campaign', '美軍抵達冰島，接替英軍防務', 'United States forces arrive in Iceland to take over its defence', [('US', O), ('kingdom-of-iceland', S), ('UK', O)],
   [cite('FRUS1941V2', 'Doc. 782, pp. 790–791, note 47', '1941-07-01 美英冰三方確認換文內容（美軍「補充並終將接替」英軍）；註 47：美軍 1941-07-07 抵達冰島。')], '英軍未立即撤出（1942 年起陸續縮減），本表 07-07 起記為美國駐軍、標共同駐軍。', 'British troops remained for some time (marked as co-occupation).')
ev('EV_ACRE', '1941-07-14', 'armistice', '阿克停戰協定：維琪法軍在敘利亞、黎巴嫩停火，兩地由英軍與自由法國控制', 'Armistice of Saint-Jean-d\'Acre: Vichy forces in the Levant cease fire', [('UK', S), ('REGIME_FREE_FR', O), ('VICHY', S)],
   [cite('SRC_FRUS_1941V3', 'Doc. 831', '駐埃及公使 1941-07-14 電：修正後的停戰條款已達成協議並正式簽字。'), cite('SRC_FRUS_1941V3', 'Doc. 830', '7/13 電：停戰條款 7/12 夜由威爾遜與德·韋爾迪拉克草簽。')])
ev('EV_IR_INV', '1941-08-25', 'war', '英蘇聯軍入侵伊朗', 'Anglo-Soviet invasion of Iran', [('UK', B), ('SU', B), ('REGIME_IR', B)],
   [cite('SRC_FRUS_1941V3', 'Doc. 400', '駐伊朗公使 1941-08-25 電：伊朗外交部請美國總統斡旋，促英蘇立即停止敵對行動。')])
ev('EV_IR_CEASE', '1941-08-30', 'armistice', '伊朗停止抵抗，英蘇軍在加茲溫一帶會師', 'Iran ceases resistance; British and Soviet forces meet', [('UK', S), ('SU', S), ('REGIME_IR', S)], note_zh='伊朗 8/29 前後下令停火（日期待查證）；9/17 英蘇軍進入德黑蘭、禮薩汗退位（未分）。', note_en='Exact ceasefire date pending; Allied entry into Tehran on 17 Sep not split.')
ev('EV_SY_INDEP', '1941-09-27', 'political', '自由法國卡特魯宣布敘利亞獨立（委任統治法律上未終止）', 'Catroux proclaims Syrian independence (mandate not legally terminated)', [('REGIME_FREE_FR', S), ('syrian-republic-mandate', O)])
ev('EV_LB_INDEP', '1941-11-26', 'political', '自由法國卡特魯宣布黎巴嫩獨立（委任統治法律上未終止）', 'Catroux proclaims Lebanese independence (mandate not legally terminated)', [('REGIME_FREE_FR', S), ('lebanese-republic-mandate', O)])
ev('EV_TOBRUK_RELIEF', '1941-12-10', 'battle', '十字軍行動：托布魯克解圍', 'Operation Crusader: siege of Tobruk lifted', [('UK', B), ('DE', B), ('IT', B)], note_zh='11/27 已與守軍會合，12/10 圍城部隊撤走。', note_en='Link-up on 27 Nov; besiegers withdrew 10 Dec.')
ev('EV_BENGHAZI_UK2', '1941-12-24', 'battle', '英軍再度攻佔班加西', 'British retake Benghazi', [('UK', B), ('DE', B), ('IT', B)])
ev('EV_BENGHAZI_AX2', '1942-01-29', 'battle', '軸心軍再度收復班加西，英軍退至加查拉防線', 'Axis retakes Benghazi; British fall back to the Gazala line', [('DE', B), ('IT', B), ('UK', B)])
ev('EV_TOBRUK_FALL', '1942-06-21', 'battle', '托布魯克陷落', 'Tobruk falls to the Axis', [('DE', B), ('IT', B), ('UK', B)])
ev('EV_AXIS_EGYPT', '1942-06-23', 'campaign', '軸心軍越過邊境攻入埃及，7 月初在阿拉曼受阻', 'Axis forces cross into Egypt, halted at El Alamein in early July', [('DE', B), ('IT', B), ('UK', B), ('kingdom-of-egypt', O)], note_zh='馬特魯港 6/29 陷落；阿拉曼以西範圍為手繪近似。', note_en='Mersa Matruh fell on 29 Jun; extent hand-drawn.')
ev('EV_ALAMEIN2', '1942-10-23', 'battle', '第二次阿拉曼戰役開始', 'Second Battle of El Alamein begins', [('UK', B), ('DE', B), ('IT', B)])
ev('EV_TUNIS_LAND', '1942-11-09', 'campaign', '德軍空運部隊在突尼斯登陸，軸心國進佔突尼西亞', 'German forces land at Tunis; Axis occupation of Tunisia begins', [('DE', B), ('IT', B), ('french-protectorate-tunisia', O)], note_zh='11 月底前控制突尼斯、比塞大與東部沿海（範圍為手繪近似）。', note_en='Extent by late November, hand-drawn.')
ev('EV_TORCH_CEASE', '1942-11-11', 'armistice', '法屬北非停火（達爾朗 11/10 下令，卡薩布蘭加 11/11 停火）', 'Ceasefire in French North Africa (Darlan order 10 Nov; Casablanca 11 Nov)', [('VICHY', S), ('US', S), ('UK', O)])
ev('EV_HALFAYA', '1942-11-11', 'battle', '英軍收復哈勒法亞隘口與索倫，軸心軍退出埃及', 'British retake Halfaya Pass and Sollum; Axis forces leave Egypt', [('UK', B), ('DE', B), ('IT', B)])
ev('EV_TOBRUK_UK3', '1942-11-13', 'battle', '英軍收復托布魯克', 'British retake Tobruk', [('UK', B), ('DE', B), ('IT', B)])
ev('EV_BENGHAZI_UK3', '1942-11-20', 'battle', '英軍第三度攻佔班加西，昔蘭尼加改由英國軍政府管理', 'British retake Benghazi for the third time; British military administration of Cyrenaica', [('UK', B), ('DE', B), ('IT', B)])
ev('EV_FEZZAN', '1943-01-13', 'campaign', '勒克萊爾部隊完成征服費贊（塞卜哈 1/12、邁爾祖格 1/13）', 'Leclerc completes the conquest of the Fezzan', [('REGIME_FREE_FR', B), ('IT', B)], note_zh='另有記載塞卜哈 1/8 已被佔、邁爾祖格守軍 1/10 投降。', note_en='Other accounts give Sebha 8 Jan and Murzuk surrender 10 Jan.')
ev('EV_TRIPOLI', '1943-01-23', 'battle', '英軍第八軍團攻佔的黎波里', 'British Eighth Army takes Tripoli', [('UK', B), ('DE', B), ('IT', B)], note_zh='利比亞西端至突尼西亞邊境 2 月中旬才肅清（未分）。', note_en='Westernmost Tripolitania cleared by mid-February (not split).')
ev('EV_SFAX', '1943-04-10', 'battle', '英軍攻佔斯法克斯，軸心軍退守突尼西亞東北角', 'British take Sfax; Axis forces fall back to north-eastern Tunisia', [('UK', B), ('DE', B), ('IT', B)])
ev('EV_TUNIS_SURR', '1943-05-13', 'surrender', '突尼西亞軸心軍投降，北非戰事結束', 'Axis forces in Tunisia surrender; end of the North African campaign', [('DE', S), ('IT', S), ('UK', S), ('US', S)], note_zh='突尼斯、比塞大 5/7 陷落。', note_en='Tunis and Bizerte fell on 7 May.')
ev('EV_LB_1943', '1943-11-22', 'political', '法國撤銷 11/11 法令、釋放黎巴嫩總統與部長（黎巴嫩獨立日）', 'French revoke the 11 Nov decrees and release the Lebanese President and ministers (Lebanese Independence Day)', [('CFLN', S), ('lebanese-republic-mandate', S)],
   [cite('SRC_FRUS_1943V4', 'Doc. 1097', '駐貝魯特外交代表 1943-11-23 電：11/22 晚夏塔紐簽署法令，撤銷 11/11 第 464 號（除第一條）與第 465 號法令。'), cite('SRC_FRUS_1943V4', 'Doc. 1098', '11/24 電：總統接見時已有獲釋的總理與部長在旁。')],
   '委任統治法律上未在此時終止（本表黎巴嫩仍記非主權；外國軍隊 1946 年撤出）。', 'The mandate was not legally terminated at this point.')
EVID = dict(EV_IT_ARM='01a191a0-45bd-788e-b2c7-e6e0604c1fc7', EV_DE_SURR='01a1913b-8fe1-7fd1-b8c5-4566cc7afc45', EV_TORCH=EV_TORCH, EV_IS_REP_X=EV_IS_REP_X, EV_VICHY_ARM=EV_VICHY_ARM)
def E(ph):
    if ph is None: return None
    return EVID.get(ph) or '{{%s}}' % ph
# ── 手繪範圍 ──
LY, EG, TN = G14['italian-libya'], G14['kingdom-of-egypt'], G14['french-protectorate-tunisia']
HAND = '手繪近似線（nafrica build/build_naf.py）'
PTS = {
 'CYR_FULL': [(19.2, 33.5), (25.5, 33.5), (25.5, 29.0), (19.2, 29.0)],
 'CYR_EAST': [(23.05, 33.5), (25.5, 33.5), (25.5, 30.0), (23.48, 30.0), (23.48, 31.6), (23.05, 32.2)],
 'FEZ': [(9.3, 29.6), (17.5, 29.6), (17.5, 21.5), (9.3, 21.5)],
 'EG40': [(24.6, 31.9), (26.05, 31.9), (26.05, 31.2), (24.6, 31.2)],
 'EG42': [(24.6, 31.9), (28.95, 31.9), (28.95, 29.0), (24.6, 29.0)],
 'TN1': [(9.2, 37.6), (9.4, 36.7), (9.3, 36.3), (9.6, 35.8), (9.3, 35.0), (9.0, 34.6), (9.4, 34.0), (10.0, 33.3), (10.6, 33.0), (11.6, 33.0), (11.6, 37.6)],
 'TN2': [(9.4, 37.6), (9.65, 36.9), (9.8, 36.6), (10.2, 36.3), (10.45, 36.1), (11.2, 36.1), (11.2, 37.6)],
 'IR_SU': [(43.5, 40.0), (61.0, 40.0), (61.0, 35.0), (59.0, 35.3), (57.0, 35.8), (55.0, 36.2), (53.4, 35.9), (52.5, 35.95), (51.0, 36.0), (49.9, 36.3), (48.5, 36.4), (47.2, 36.5), (46.2, 36.9), (45.6, 36.95), (44.0, 36.9), (43.5, 36.9)],
 'IR_UK': [(43.5, 24.0), (61.0, 24.0), (61.0, 31.0), (57.5, 31.8), (55.0, 32.8), (52.5, 33.8), (51.0, 34.4), (49.5, 34.6), (48.0, 35.0), (46.5, 35.2), (45.0, 35.6), (43.5, 35.6)],
}
CIRC = {'TOBRUK': (23.96, 32.0, 0.2), 'KUFRA': (23.3, 24.2, 0.6)}
RAW = {k: Polygon(v) for k, v in PTS.items()}; RAW.update({k: circ(*v) for k, v in CIRC.items()})
def handdesc(k):
    return f'{k}：' + (fmt(PTS[k]) if k in PTS else 'circle(%s,%s,r=%s°)' % CIRC[k])
# ── 伊朗（OHM 2694890）──
FRAME = box(-20, 15, 60, 72)
sf = shapefile.Reader('/workspace/wl/ohm/ne/ne_10m_land.shp')
land = unary_union([make_valid(shape(s.__geo_interface__)).intersection(FRAME) for s in sf.shapes() if box(*s.bbox).intersects(box(40, 20, 65, 45))])
rel = [x for x in ir_raw['elements'] if x['type'] == 'relation'][0]
outer, inner = [], []
for m in rel['members']:
    if m['type'] != 'way' or 'geometry' not in m: continue
    cs = [(p['lon'], p['lat']) for p in m['geometry'] if p]
    if len(cs) >= 2: (inner if m['role'] == 'inner' else outer).append(LineString(cs))
IRg = unary_union(list(polygonize(unary_union(outer))))
if inner: IRg = IRg.difference(unary_union(list(polygonize(unary_union(inner)))))
IRg = make_valid(make_valid(IRg).intersection(FRAME).intersection(land)); IRg = make_valid(IRg.simplify(0.0005, preserve_topology=True))
ir_raw_area = IRg.area
IRg = clean(IRg.difference(others_over(START, END, set(), IRg)).difference(unary_union(list(G14.values()))))
waytags = [x.get('tags', {}) for x in ir_raw['elements'] if x['type'] == 'way']
IR_LIC = {}
for t in waytags:
    k = 'untagged(OHM CC0)' if not (t.get('license') or t.get('source:license')) else (t.get('license') or t.get('source:license'))
    IR_LIC[k] = IR_LIC.get(k, 0) + 1
ZG = {'IR_SU': clean(IRg.intersection(RAW['IR_SU'])), 'IR_UK': clean(IRg.intersection(RAW['IR_UK']))}
# ── 各政權分段（基底 − 同期有效的佔領區）──
# zone: (key, regime_ph, raw_key, base_slug_or_IR, lo, hi, start_ev, end_ev)
ZONES = [
 ('EG40', 'REGIME_EG_IT40', 'EG40', 'kingdom-of-egypt', '1940-09-16', '1940-12-10', 'EV_SIDI_BARRANI', 'EV_SIDI_RECAP'),
 ('EG42', 'REGIME_EG_AX42', 'EG42', 'kingdom-of-egypt', '1942-06-23', '1942-11-11', 'EV_AXIS_EGYPT', 'EV_HALFAYA'),
 ('CYR0', 'REGIME_CYR_UK', 'CYR_EAST', 'italian-libya', '1941-01-22', '1941-02-07', 'EV_TOBRUK_UK1', 'EV_BEDA_FOMM'),
 ('CYR1', 'REGIME_CYR_UK', 'CYR_FULL', 'italian-libya', '1941-02-07', '1941-04-04', 'EV_BEDA_FOMM', 'EV_BENGHAZI_AX1'),
 ('CYR2', 'REGIME_CYR_UK', 'CYR_EAST', 'italian-libya', '1941-04-04', '1941-04-11', 'EV_BENGHAZI_AX1', 'EV_TOBRUK_SIEGE'),
 ('CYR3', 'REGIME_CYR_UK', 'TOBRUK', 'italian-libya', '1941-04-11', '1941-12-10', 'EV_TOBRUK_SIEGE', 'EV_TOBRUK_RELIEF'),
 ('CYR4', 'REGIME_CYR_UK', 'CYR_EAST', 'italian-libya', '1941-12-10', '1941-12-24', 'EV_TOBRUK_RELIEF', 'EV_BENGHAZI_UK2'),
 ('CYR5', 'REGIME_CYR_UK', 'CYR_FULL', 'italian-libya', '1941-12-24', '1942-01-29', 'EV_BENGHAZI_UK2', 'EV_BENGHAZI_AX2'),
 ('CYR6', 'REGIME_CYR_UK', 'CYR_EAST', 'italian-libya', '1942-01-29', '1942-06-21', 'EV_BENGHAZI_AX2', 'EV_TOBRUK_FALL'),
 ('KUF', 'REGIME_KUFRA_FF', 'KUFRA', 'italian-libya', '1941-03-01', '1943-01-23', 'EV_KUFRA', 'EV_TRIPOLI'),
 ('BMA1', 'REGIME_BMA_LY', 'CYR_EAST', 'italian-libya', '1942-11-13', '1942-11-20', 'EV_TOBRUK_UK3', 'EV_BENGHAZI_UK3'),
 ('BMA2', 'REGIME_BMA_LY', 'CYR_FULL', 'italian-libya', '1942-11-20', '1943-01-23', 'EV_BENGHAZI_UK3', 'EV_TRIPOLI'),
 ('BMA3', 'REGIME_BMA_LY', '-FEZ', 'italian-libya', '1943-01-23', END, 'EV_TRIPOLI', None),
 ('FEZ', 'REGIME_FEZ_FR', 'FEZ', 'italian-libya', '1943-01-13', END, 'EV_FEZZAN', None),
 ('TN1', 'REGIME_TN_AX', 'TN1', 'french-protectorate-tunisia', '1942-11-09', '1943-04-10', 'EV_TUNIS_LAND', 'EV_SFAX'),
 ('TN2', 'REGIME_TN_AX', 'TN2', 'french-protectorate-tunisia', '1943-04-10', '1943-05-13', 'EV_SFAX', 'EV_TUNIS_SURR'),
 ('IRSU', 'REGIME_IR_SU', 'IR_SU', 'IR', '1941-08-25', END, 'EV_IR_INV', None),
 ('IRUK', 'REGIME_IR_UK', 'IR_UK', 'IR', '1941-08-25', END, 'EV_IR_INV', None),
]
def base_geom(b): return IRg if b == 'IR' else G14[b]
def zone_raw(k):
    if k == '-FEZ': return box(5, 15, 30, 40).difference(RAW['FEZ'])
    return RAW[k]
QA = {'iran': {'ohm_clipped_area': round(ir_raw_area, 3), 'after_subtract': round(IRg.area, 3), 'zones': {k: round(v.area, 3) for k, v in ZG.items()}}, 'segments': [], 'overlaps': []}
DER = {}
NOTE_RM = [r'到 1938-12-31（本批試驗期間終點，無迄事件）。?', r'Until 31 Dec 1938 \(end of this batch\)\.?', r'暫迄 1939-01-01[^。]*。?']
def ext_note(slug, zh, en):
    old = ROWS[slug].get('note') or {}
    z = old.get('zh-Hant') or ''; e = old.get('en') or ''
    for p in NOTE_RM: z = re.sub(p, '', z); e = re.sub(p, '', e)
    return {'zh-Hant': (z.strip() + ' ' + zh).strip(), 'en': (e.strip() + ' ' + en).strip()}
SEGN = [0]
def segments(base, base_lo, base_start_ev, final_end, final_end_ev):
    zs = [z for z in ZONES if z[3] == base]
    pts = sorted({base_lo, final_end} | {z[4] for z in zs} | {z[5] for z in zs if z[5] < final_end})
    out = []
    for lo, hi in zip(pts, pts[1:]):
        act = [z for z in zs if z[4] <= lo < z[5]]
        sev = base_start_ev if lo == base_lo else next((z[6] for z in zs if z[4] == lo), None) or next((z[7] for z in zs if z[5] == lo), None)
        eev = final_end_ev if hi == final_end else next((z[7] for z in zs if z[5] == hi), None) or next((z[6] for z in zs if z[4] == hi), None)
        sub = unary_union([zone_raw(z[2]) for z in act]) if act else None
        out.append((lo, hi, sev, eev, act, sub))
    return out
BASE_END = {  # 政權: (最終迄日, 迄事件, 註記中文, 英文)
 'italian-libya': (END, None, '1939～1943 依戰事扣掉英軍佔領昔蘭尼加、托布魯克、庫夫拉、英國軍政府與法國軍管費贊（範圍為手繪近似，待查證）；1943-01-23 的黎波里陷落後全境由英法軍管，本主權紀錄止於該日（義大利在 1947 年和約前名義上仍保有主權，見佔領區紀錄）。', 'Occupied zones carved out 1940–45 (hand-drawn). Italy remained de jure sovereign until the 1947 peace treaty.'),
 'kingdom-of-egypt': (END, None, '1940-09～12、1942-06～11 扣掉義軍／軸心軍佔領的西部（手繪近似）。到 1945-09-02（本批試驗終點）。', 'Western Egypt occupied by Italian/Axis forces in 1940 and 1942 carved out (hand-drawn).'),
 'french-protectorate-tunisia': (END, None, '1942-11-09～1943-05-13 扣掉軸心國佔領區（手繪近似）。1940-07 起受維琪政府管轄（未另列）。到 1945-09-02（本批試驗終點）。', 'Axis-occupied area carved out Nov 1942–May 1943 (hand-drawn).'),
}
for base, (fend, fev, nzh, nen) in BASE_END.items():
    row = ROWS[base]
    segs = segments(base, row['lo'], row['startEventId'], fend, fev)
    add('N2', '04-retract', 'retract_' + base, 'RETRACTED_SOV_' + base.upper().replace('-', '_'), f"/api/v1/sovereignty-records/{row['id']}/retraction", {'reason': f'{TRIAL}：B 批暫迄 1939-01-01（試驗終點），依 1939～1945 戰事分段延長後重送'}, meta={'fix': True})
    i = 0
    for (lo, hi, sev, eev, act, sub) in segs:
        bg = G14[base]; g = clean(bg.difference(sub)) if sub is not None else bg
        if g is None: QA['segments'].append([base, lo, hi, 0, [z[0] for z in act], '全境被佔，不建主權段']); continue
        i += 1
        ph = f"SOV_{base.upper().replace('-', '_')}_N{i}"
        note = ext_note(base, nzh + (f' 本段扣掉：{"、".join(z[0] for z in act)}。' if act else ''), nen)
        ov = {'validPeriod': {'start': lo, 'end': hi}, 'startEventId': sev if (sev is None or re.match(r'^[0-9a-f-]{36}$', str(sev))) else E(sev), 'endEventId': E(eev), 'note': note}
        prov = dict(row['provenance'] or {}); prov['trialWindow'] = TRIAL
        if act: prov['handDrawnSubtract'] = '；'.join(handdesc(z[2]) if z[2] != '-FEZ' else '利比亞減費贊（' + handdesc('FEZ') + '）' for z in act)
        ov['provenance'] = prov
        if act: ov['geometryLocator'] = row['geometryLocator'] + ' − ' + '、'.join(z[0] for z in act) + f'（{HAND}）'
        add('N2', '05-sovereignty', ph.lower(), ph, '/api/v1/sovereignty-records', ov, meta={'fix': True}, readd={'base': row['id'], 'geomFrom': row['id'], 'union': None, 'subtract': mapping(sub) if sub is not None else None, 'noteAppend': None})
        QA['segments'].append([base, lo, hi, round(g.area, 3), [z[0] for z in act]]); DER[ph] = g
# 延長（不分段）
SIMPLE = {
 'french-protectorate-morocco': ('1942-11-08 起盟軍（美軍為主）進駐，另列佔領歸屬（同阿爾及利亞處理）；1940-07 起受維琪政府管轄（未另列）。', 'Allied (mainly US) presence from 8 Nov 1942 recorded as an occupation attribution.'),
 'spanish-protectorate-morocco': ('二戰期間西班牙中立，範圍不變。', 'Unchanged (Spain neutral).'),
 'mauritania-french-1912': ('法屬西非一部分，1940～1942 受維琪政府管轄（未另列）。', 'Part of French West Africa, under Vichy 1940–42 (not split).'),
 'mandatory-palestine': ('二戰期間範圍不變。', 'Unchanged during the war.'),
 'emirate-of-transjordan': ('二戰期間範圍不變（1946-05-25 獨立在試驗範圍外）。', 'Unchanged; independence in 1946 is outside the trial window.'),
 'cyprus-crown-colony': ('二戰期間範圍不變。', 'Unchanged during the war.'),
 'tangier-international-zone': ('1940-06-14～1945-10-11 西班牙軍隊佔領（另列佔領歸屬）。', 'Spanish occupation 1940-06-14 to 1945-10-11 recorded as an occupation attribution.'),
 'syrian-republic-mandate': ('1940-06-25～1941-07-14 由維琪政府管轄，1941-07-14 起由自由法國（英軍共同駐軍）管轄（另列佔領歸屬）；1941-09-27 卡特魯宣布獨立，但委任統治法律上要到戰後才結束（待查證），本表仍記非主權。', 'Vichy administration until 14 Jul 1941, then Free French with British forces (occupation attributions); independence proclaimed 27 Sep 1941 but the mandate continued legally.'),
 'lebanese-republic-mandate': ('1940-06-25～1941-07-14 由維琪政府管轄，1941-07-14 起由自由法國（英軍共同駐軍）管轄（另列佔領歸屬）；1941-11-26 宣布獨立、1943-11-22 法國撤銷停憲法令，但委任統治法律上要到戰後才結束（待查證），本表仍記非主權。', 'Vichy until 14 Jul 1941, then Free French; independence proclaimed 1941 and 1943 crisis resolved 22 Nov 1943, mandate continued legally.'),
 'kingdom-of-iraq': ('1941-04 拉希德·阿里政變、5 月英伊戰爭；1941-05-31 停戰後英軍駐留（另列佔領歸屬，伊拉克政府照常運作）。', 'Rashid Ali coup and Anglo-Iraqi War in 1941; British forces stationed thereafter (occupation attribution).'),
}
for base, (nzh, nen) in SIMPLE.items():
    row = ROWS[base]
    add('N2', '04-retract', 'retract_' + base, 'RETRACTED_SOV_' + base.upper().replace('-', '_'), f"/api/v1/sovereignty-records/{row['id']}/retraction", {'reason': f'{TRIAL}：B 批暫迄 1939-01-01（試驗終點），延長迄日後重送'}, meta={'fix': True})
    ph = f"SOV_{base.upper().replace('-', '_')}_N1"
    prov = dict(row['provenance'] or {}); prov['trialWindow'] = TRIAL
    add('N2', '05-sovereignty', ph.lower(), ph, '/api/v1/sovereignty-records', {'validPeriod': {'start': row['lo'], 'end': END}, 'endEventId': None, 'provenance': prov,
        'note': ext_note(base, nzh + ' 到 1945-09-02（本批試驗終點）。', nen + ' Until 2 Sep 1945 (end of this batch).')}, meta={'fix': True}, readd={'base': row['id'], 'geomFrom': row['id'], 'union': None, 'subtract': None, 'noteAppend': None})
    DER[ph] = G14[base]; QA['segments'].append([base, row['lo'], END, round(G14[base].area, 3), []])
# 西班牙國：既有二戰紀錄 01a193fc-0144…（F1 補撒哈拉後重送的版本）已含西屬摩洛哥北區，與延長後的保護國重疊 → 先撤後增，1939-04-01～1945-09-03 段扣掉保護國，之後原樣
ES_REC = '01a193fc-0144-7e79-ba20-490e7afe9fd0'; SPM = ROWS['spanish-protectorate-morocco']
add('N2', '04-retract', 'retract_spanish-state-1939', 'RETRACTED_SOV_ES_1939', f'/api/v1/sovereignty-records/{ES_REC}/retraction', {'reason': f'{TRIAL}：此紀錄含西屬摩洛哥保護國北區，與延長到 1945-09-03 的保護國紀錄重疊；拆成兩段，戰時段扣掉保護國範圍後重送'}, meta={'fix': True})
add('N2', '05-sovereignty', 'sov_es_1939_a', 'SOV_ES_1939_A', '/api/v1/sovereignty-records', {'validPeriod': {'start': '1939-04-01', 'end': END}, 'endEventId': None,
    'geometryLocator': '@locator − 西屬摩洛哥保護國（%s）' % SPM['geometryLocator']}, meta={'fix': True},
    readd={'base': ES_REC, 'geomFrom': ES_REC, 'union': None, 'subtract': mapping(G14['spanish-protectorate-morocco']),
           'noteAppend': {'zh-Hant': '1939-04-01～1945-09-02 扣掉西屬摩洛哥保護國（另有保護國紀錄）。', 'en': 'Spanish Protectorate of Morocco carved out 1939–45 (separate record).'}})
add('N2', '05-sovereignty', 'sov_es_1939_b', 'SOV_ES_1939_B', '/api/v1/sovereignty-records', {'validPeriod': {'start': END, 'end': '1956-04-07'}, 'startEventId': None}, meta={'fix': True},
    readd={'base': ES_REC, 'geomFrom': ES_REC, 'union': None, 'subtract': None,
           'noteAppend': {'zh-Hant': '1945-09-03 起為本批試驗期間外，範圍原樣（含保護國北區，待後續批次處理）。', 'en': 'After the trial window: unchanged (includes the northern protectorate; later batch).'}})
ESg = next(r['g'] for r in R if r['id'] == ES_REC)
DER['SOV_ES_1939_A'] = clean(ESg.difference(G14['spanish-protectorate-morocco'])); R = [r for r in R if r['id'] != ES_REC]
# 冰島：王國延長到 1944-06-17，之後冰島共和國（同範圍）
row = ROWS['kingdom-of-iceland']; prov = dict(row['provenance'] or {}); prov['trialWindow'] = TRIAL
add('N2', '04-retract', 'retract_kingdom-of-iceland', 'RETRACTED_SOV_KINGDOM_OF_ICELAND', f"/api/v1/sovereignty-records/{row['id']}/retraction", {'reason': f'{TRIAL}：B 批暫迄 1939-01-01（試驗終點），延長到 1944-06-17 冰島共和國成立後重送'}, meta={'fix': True})
add('N2', '05-sovereignty', 'sov_kingdom_of_iceland_n1', 'SOV_KINGDOM_OF_ICELAND_N1', '/api/v1/sovereignty-records', {'validPeriod': {'start': row['lo'], 'end': '1944-06-17'}, 'endEventId': EV_IS_REP_X, 'provenance': prov,
    'note': ext_note('kingdom-of-iceland', '1940-05-10 起英軍、1941-07-07 起美軍駐守（另列佔領歸屬；冰島政府照常運作）。', 'British (from 10 May 1940) and US (from 7 Jul 1941) garrisons recorded as occupation attributions.')}, meta={'fix': True},
    readd={'base': row['id'], 'geomFrom': row['id'], 'union': None, 'subtract': None, 'noteAppend': None})
add('N2', '05-sovereignty', 'sov_is_rep', 'SOV_IS_REP', '/api/v1/sovereignty-records', {'regimeId': '{{REGIME_IS_REP}}', 'validPeriod': {'start': '1944-06-17', 'end': END}, 'startEventId': EV_IS_REP_X, 'endEventId': None, 'provenance': prov,
    'note': {'zh-Hant': '冰島共和國，範圍同冰島王國（沿用 OHM %s）。美軍持續駐守（另列佔領歸屬）。到 1945-09-02（本批試驗終點）。' % row['geometryLocator'], 'en': 'Same extent as the Kingdom of Iceland; US garrison continued.'}}, meta={'fix': True},
    readd={'base': row['id'], 'geomFrom': row['id'], 'union': None, 'subtract': None, 'noteAppend': None})
DER['SOV_KINGDOM_OF_ICELAND_N1'] = DER['SOV_IS_REP'] = G14['kingdom-of-iceland']
QA['segments'].append(['kingdom-of-iceland', row['lo'], '1944-06-17', round(G14['kingdom-of-iceland'].area, 3), []])
# 伊朗（新紀錄）
ir_prov = {'memberWayLicense': IR_LIC, 'osmDerivedWayCount': 0, 'ohmFixme': rel['tags'].get('fixme'), 'ohmRelationSource': rel['tags'].get('source'), 'ohmAdminLevel': '2',
           'ohmChangeset': rel.get('changeset'), 'ohmTimestamp': rel['timestamp'], 'coastline': SRC['NE'], 'licenseReview': None, 'trialWindow': TRIAL, 'frameClip': '框東界 60°E 以東裁掉；扣掉開發庫同期既有紀錄（土耳其、蘇聯、伊拉克等）'}
ir_fetched = open(os.path.join(ROOT, 'raw', 'r2694890.json.fetched')).read().strip()
lic_by = any(k != 'untagged(OHM CC0)' and 'CC0' not in k.upper() for k in IR_LIC)
def ir_body(ph, regime, lo, hi, sev, eev, status, g, loc_extra, note_zh, note_en):
    DER[ph] = g
    return {'regimeId': regime, 'geometry': None, 'validPeriod': {'start': lo, 'end': hi}, 'layerStatus': status, 'geometrySourceId': '{{SRC_OHM_NAF}}',
            'geometryLocator': f'relation/2694890 v{rel["version"]}' + loc_extra, 'geometryLicense': 'cc_by' if lic_by else 'cc0', 'attribution': ('OHM 線段標示 CC BY 4.0（待查）' if lic_by else None),
            'startEventId': E(sev), 'endEventId': E(eev), 'ohmRelationId': 2694890, 'ohmVersion': rel['version'], 'ohmFetchedAt': ir_fetched,
            'ohmStartRaw': rel['tags'].get('start_date'), 'ohmEndRaw': rel['tags'].get('end_date'), 'provenance': ir_prov, 'note': {'zh-Hant': note_zh, 'en': note_en}}
irsegs = segments('IR', START, None, END, None)
for i, (lo, hi, sev, eev, act, sub) in enumerate(irsegs, 1):
    g = clean(IRg.difference(sub)) if sub is not None else IRg
    ph = f'SOV_IR_N{i}'
    add('N2', '05-sovereignty', ph.lower(), ph, '/api/v1/sovereignty-records', ir_body(ph, '{{REGIME_IR}}', lo, hi, sev, eev, 'de_jure', g, (' − 英蘇佔領區（%s）' % HAND) if act else '',
        '伊朗（1935 年由波斯改稱）。1939-01-01 為本批起點，不是政權起日。' + ('本段扣掉英蘇佔領區（手繪近似，待查證）。' if act else '') + '框東界 60°E 以東未畫。到 1945-09-02（本批試驗終點）。',
        'Iran; 1939-01-01 is the start of this batch.' + (' Anglo-Soviet zones carved out (hand-drawn).' if act else '')), geom=ph)
    QA['segments'].append(['imperial-state-of-iran', lo, hi, round(g.area, 3), [z[0] for z in act]])
# 佔領區紀錄
for z in ZONES:
    k, reg, rk, base, lo, hi, sev, eev = z
    if base == 'IR':
        g = ZG['IR_SU' if k == 'IRSU' else 'IR_UK']; ph = f'SOV_{k}'
        add('N2', '05-sovereignty', ph.lower(), ph, '/api/v1/sovereignty-records', ir_body(ph, '{{%s}}' % reg, lo, hi, sev, eev, 'not_sovereign', g, f' ∩ {k}（{HAND}）',
            ('非主權：英蘇聯軍入侵後的%s佔領區（範圍為手繪近似，待查證；1942-01-29 英蘇伊同盟條約確認駐軍）。德黑蘭一帶未列入兩區。到 1945-09-02（本批試驗終點；實際 1946 年撤軍）。' % ('蘇聯' if k == 'IRSU' else '英國')),
            'Not sovereign: %s occupation zone after the Anglo-Soviet invasion (hand-drawn).' % ('Soviet' if k == 'IRSU' else 'British')), geom=ph)
        QA['segments'].append([reg, lo, hi, round(g.area, 3), ['zone']]); continue
    row = ROWS[base]; bg = G14[base]
    g = clean(bg.intersection(zone_raw(rk)))
    ph = f'SOV_{k}'
    prov = dict(row['provenance'] or {}); prov['trialWindow'] = TRIAL; prov['handDrawn'] = handdesc(rk) if rk != '-FEZ' else '利比亞減費贊（' + handdesc('FEZ') + '）'
    body = {'regimeId': '{{%s}}' % reg, 'geometry': None, 'validPeriod': {'start': lo, 'end': hi}, 'layerStatus': 'not_sovereign', 'geometrySourceId': row['geometrySourceId'],
            'geometryLocator': row['geometryLocator'] + (f' ∩ {rk}' if rk != '-FEZ' else ' − FEZ') + f'（{HAND}）', 'geometryLicense': row['geometryLicense'], 'attribution': row['attribution'],
            'startEventId': E(sev), 'endEventId': E(eev), 'ohmRelationId': row['ohmRelationId'], 'ohmVersion': row['ohmVersion'], 'ohmFetchedAt': row['ohmFetchedAt'],
            'ohmStartRaw': row['ohmStartRaw'], 'ohmEndRaw': row['ohmEndRaw'], 'provenance': prov,
            'note': {'zh-Hant': f'非主權佔領區，範圍為手繪近似（待查證），與 OHM {row["geometryLocator"]} 相交。' + ('到 1945-09-02（本批試驗終點）。' if hi == END else ''), 'en': 'Occupied zone; hand-drawn approximation intersected with the OHM boundary.'}}
    add('N2', '05-sovereignty', ph.lower(), ph, '/api/v1/sovereignty-records', body, geom=ph); DER[ph] = g
    QA['segments'].append([reg, lo, hi, round(g.area, 3), ['zone']])
# ── 佔領歸屬 ──
def occ(ph, occd, occr, kind, lo, hi, co, zh, en, basis=None):
    add('N3', '06-occupation', ph.lower(), ph, '/api/v1/occupation-attributions', {'occupiedRegimeId': RG[occd] if occd in RG else '{{%s}}' % occd, 'occupierRegimeId': RG[occr],
        'controlKind': kind, 'validPeriod': {'start': lo, 'end': hi}, 'basisEventId': E(basis), 'coOccupied': co, 'note': {'zh-Hant': zh, 'en': en}})
MA, CA = 'military_administration', 'civil_administration'
occ('OCC_EG40', 'REGIME_EG_IT40', 'IT', MA, '1940-09-16', '1940-12-10', False, '義軍佔領西迪巴拉尼一帶。', 'Italian occupation around Sidi Barrani.', 'EV_SIDI_BARRANI')
occ('OCC_EG42', 'REGIME_EG_AX42', 'DE', MA, '1942-06-23', '1942-11-11', True, '德義聯軍（隆美爾裝甲軍團）佔領；列德國並標共同佔領（義大利）。', 'German-Italian occupation; listed under Germany as co-occupied.', 'EV_AXIS_EGYPT')
occ('OCC_CYR', 'REGIME_CYR_UK', 'UK', MA, '1941-01-22', '1942-06-21', False, '英聯邦軍佔領（範圍隨戰線變動，分段見主權紀錄）。', 'British Commonwealth occupation (extent varies, see sovereignty records).', 'EV_TOBRUK_UK1')
occ('OCC_KUF', 'REGIME_KUFRA_FF', 'REGIME_FREE_FR', MA, '1941-03-01', '1943-01-23', False, '自由法國佔領庫夫拉綠洲（範圍為圓形近似）。', 'Free French occupation of the Kufra oasis.', 'EV_KUFRA')
occ('OCC_BMA', 'REGIME_BMA_LY', 'UK', MA, '1942-11-13', END, False, '英國軍政府（1943 年起管轄的黎波里塔尼亞與昔蘭尼加，至 1951 年）。', 'British Military Administration (until 1951).', 'EV_TOBRUK_UK3')
occ('OCC_FEZ_1', 'REGIME_FEZ_FR', 'REGIME_FREE_FR', MA, '1943-01-13', '1943-06-03', False, '自由法國（戰鬥法國）軍管費贊。', 'Fighting French military administration of the Fezzan.', 'EV_FEZZAN')
occ('OCC_FEZ_2', 'REGIME_FEZ_FR', 'CFLN', MA, '1943-06-03', '1944-08-09', False, '法蘭西民族解放委員會軍管費贊。', 'French Committee of National Liberation.')
occ('OCC_FEZ_3', 'REGIME_FEZ_FR', 'GPRF', MA, '1944-08-09', END, False, '法蘭西共和國臨時政府軍管費贊（至 1951 年）。', 'Provisional Government of the French Republic.')
occ('OCC_TN_AX', 'REGIME_TN_AX', 'DE', MA, '1942-11-09', '1943-05-13', True, '德義聯軍佔領；列德國並標共同佔領（義大利）。突尼斯貝伊與維琪法國總督名義上照常。', 'German-Italian occupation; listed under Germany.', 'EV_TUNIS_LAND')
occ('OCC_IR_SU', 'REGIME_IR_SU', 'SU', MA, '1941-08-25', END, False, '蘇聯佔領伊朗北部（至 1946 年）。', 'Soviet occupation of northern Iran (until 1946).', 'EV_IR_INV')
occ('OCC_IR_UK', 'REGIME_IR_UK', 'UK', MA, '1941-08-25', END, False, '英國佔領伊朗南部（至 1946 年）。', 'British occupation of southern Iran (until 1946).', 'EV_IR_INV')
occ('OCC_IS_UK', 'kingdom-of-iceland', 'UK', MA, '1940-05-10', '1941-07-07', False, '英軍駐守（冰島抗議但未抵抗，政府照常運作；以軍事管理淺色表示外國駐軍）。', 'British garrison; Icelandic government continued.', 'EV_IS_UK_OCC')
occ('OCC_IS_US_1', 'kingdom-of-iceland', 'US', MA, '1941-07-07', '1944-06-17', True, '應冰島政府邀請由美軍駐守、英軍共同駐守（冰島政府照常運作）。', 'US garrison at Iceland\'s invitation, with British forces.', 'EV_US_ICELAND')
occ('OCC_IS_US_2', 'REGIME_IS_REP', 'US', MA, '1944-06-17', END, False, '美軍持續駐守（至 1947 年）。', 'US garrison continued (until 1947).')
occ('OCC_IQ_UK', 'kingdom-of-iraq', 'UK', MA, '1941-05-31', END, False, '英伊停戰後英軍駐留（伊拉克政府照常運作；至 1947 年）。', 'British forces in Iraq after the armistice (until 1947).', 'EV_IQ_ARMISTICE')
for lv in ('syrian-republic-mandate', 'lebanese-republic-mandate'):
    t = 'SY' if lv.startswith('syr') else 'LB'
    occ(f'OCC_{t}_FR3', lv, 'FR3', CA, START, '1940-06-25', False, '法國委任統治（第三共和）。1939-01-01 為本批起點。', 'French mandate (Third Republic).')
    occ(f'OCC_{t}_VICHY', lv, 'VICHY', CA, '1940-06-25', '1941-07-14', False, '維琪政府高級專員管轄（停戰協定 1940-06-25 生效起）。', 'Vichy High Commissioner.', 'EV_VICHY_ARM')
    occ(f'OCC_{t}_FF', lv, 'REGIME_FREE_FR', CA, '1941-07-14', '1943-06-03', True, '自由法國（法蘭西民族委員會）管轄，英軍共同駐守。', 'Free French administration with British forces.', 'EV_ACRE')
    occ(f'OCC_{t}_CFLN', lv, 'CFLN', CA, '1943-06-03', '1944-08-09', True, '法蘭西民族解放委員會管轄，英軍共同駐守。', 'CFLN administration with British forces.')
    occ(f'OCC_{t}_GPRF', lv, 'GPRF', CA, '1944-08-09', END, True, '法蘭西共和國臨時政府管轄，英軍共同駐守（至 1946 年撤軍）。', 'GPRF administration with British forces (until 1946).')
occ('OCC_TANGIER_ES', 'tangier-international-zone', 'ES', MA, '1940-06-14', '1945-10-11', False, '西班牙軍隊佔領（1940-11-03 宣布併入西屬摩洛哥行政，未改主權）。', 'Spanish occupation.', 'EV_TANGIER_ES')
occ('OCC_MA_US', 'french-protectorate-morocco', 'US', MA, '1942-11-08', '1943-06-03', True, '火炬行動後盟軍（美軍為主）進駐，法國保護國行政照常；比照開發庫既有阿爾及利亞處理，至 1943-06-03 法蘭西民族解放委員會成立。', 'Allied (mainly US) presence after Torch, as for Algeria.', 'EV_TORCH')
# ── 衝突 ──
def cf(ph, a, b, sev, eev, pt, how):
    add('N3', '07-conflict', ph.lower(), ph, '/api/v1/conflict-records', {'regimeAId': RG[a] if a in RG else '{{%s}}' % a, 'regimeBId': RG[b] if b in RG else '{{%s}}' % b,
        'startEventId': E(sev), 'endEventId': E(eev), 'location': {'type': 'Point', 'coordinates': list(pt)}, 'locationMethod': how})
cf('CF_UK_IT_NA', 'UK', 'IT', 'EV_IT_UK_WAR', 'EV_IT_ARM', (25.15, 31.57), '索倫（埃及—利比亞邊境；英義主要陸上戰場在北非，固定點）')
cf('CF_UK_DE_NA', 'UK', 'DE', 'EV_UK_DE_WAR', 'EV_DE_SURR', (2.0, 51.0), '多佛海峽（英德隔海相對，兩國不相鄰；英國宣戰到德國投降，固定點）')
cf('CF_UK_IQ', 'UK', 'kingdom-of-iraq', 'EV_IQ_WAR', 'EV_IQ_ARMISTICE', (43.57, 33.37), '哈巴尼亞空軍基地（固定點）')
cf('CF_UK_VICHY_SY', 'UK', 'VICHY', 'EV_SY_INV', 'EV_ACRE', (35.6, 33.3), '黎巴嫩南部前線（利塔尼河—馬傑尤恩，固定點）')
cf('CF_FF_VICHY_SY', 'REGIME_FREE_FR', 'VICHY', 'EV_SY_INV', 'EV_ACRE', (36.24, 33.36), '基斯韋（大馬士革南，自由法國進攻方向，固定點）')
cf('CF_US_VICHY_TORCH', 'US', 'VICHY', 'EV_TORCH', 'EV_TORCH_CEASE', (-7.6, 33.6), '卡薩布蘭加（火炬行動西路，固定點）')
cf('CF_UK_VICHY_TORCH', 'UK', 'VICHY', 'EV_TORCH', 'EV_TORCH_CEASE', (3.06, 36.75), '阿爾及爾（火炬行動東路，固定點）')
cf('CF_UK_IR', 'UK', 'REGIME_IR', 'EV_IR_INV', 'EV_IR_CEASE', (48.3, 30.35), '阿巴丹（英軍進攻方向，固定點）')
cf('CF_SU_IR', 'SU', 'REGIME_IR', 'EV_IR_INV', 'EV_IR_CEASE', (46.29, 38.08), '大不里士（蘇軍進攻方向，固定點）')
# ── QA：每個切點日的重疊（本批新幾何彼此、與開發庫其他紀錄）──
NEWG = []  # (ph, lo, hi, g, regime)
for r in REQ:
    if r['cat'] == '05-sovereignty' and r['ph'] in DER:
        b = r['body']; NEWG.append((r['ph'], b['validPeriod']['start'], b['validPeriod']['end'], DER[r['ph']]))
retracted = {ROWS[s]['id'] for s in ROWS} | {ES_REC}
dates = sorted({x[1] for x in NEWG} | {x[2] for x in NEWG} | {START} | {r['lo'] for r in R if START <= r['lo'] < END} | {r['hi'] for r in R if START <= r['hi'] < END})
for d in dates:
    if d >= END: continue
    act = [x for x in NEWG if x[1] <= d < x[2]]
    for i in range(len(act)):
        for j in range(i + 1, len(act)):
            a_ = act[i][3].intersection(act[j][3]).area
            if a_ > 1e-4: QA['overlaps'].append([d, act[i][0], act[j][0], round(a_, 4)])
    oth = [r for r in R if r['lo'] <= d < r['hi'] and r['id'] not in retracted]
    for x in act:
        for r in oth:
            if r['g'].intersects(x[3]):
                a_ = r['g'].intersection(x[3]).area
                if a_ > 1e-3: QA['overlaps'].append([d, x[0], r['slug'], round(a_, 4)])
# ── 輸出 ──
REQD = os.path.join(ROOT, 'requests')
for sub in ('N1', 'N2', 'N3'):
    os.makedirs(os.path.join(REQD, sub), exist_ok=True)
    for f in glob.glob(os.path.join(REQD, sub, '*.json')): os.remove(f)
cnt = {}
for r in REQ:
    k = (r['sub'], r['cat']); cnt[k] = cnt.get(k, 0) + 1
    fn = os.path.join(REQD, r['sub'], f"{r['cat']}-{cnt[k]:02d}-{r['name']}.json")
    o = {'_placeholder': r['ph'], '_post': r['post']}
    if r['geom']: o['_geometryFrom'] = r['geom']
    if r['meta']: o['_meta'] = r['meta']
    if r['readd']: o['_readd'] = r['readd']
    o['body'] = r['body']
    json.dump(o, open(fn, 'w'), ensure_ascii=False, indent=1)
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in DER.items() if any(r['geom'] == k for r in REQ)]},
          open(os.path.join(ROOT, 'nafrica-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(QA, open(os.path.join(ROOT, 'qa.json'), 'w'), ensure_ascii=False, indent=1)
from collections import Counter
print(Counter((r['sub'], r['cat']) for r in REQ)); print('iran', QA['iran']); print('overlaps', len(QA['overlaps']))
for o in QA['overlaps'][:40]: print('  ', o)
print('events pending', sum(1 for r in REQ if r['cat'] == '03-event' and r['meta']['verification'].startswith('pending')), 'of', sum(1 for r in REQ if r['cat'] == '03-event'))
