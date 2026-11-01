#!/usr/bin/env python3
"""WW1 第二批：1914-07-29 → 1918-11-11 停戰（DRAFT，待 Tai 檢查）。
分三個子批（依紀錄起日）：sub1 [1914-07-29, 1916-01-01)、sub2 [1916-01-01, 1918-01-01)、sub3 [1918-01-01, 1918-11-12)。
每筆紀錄都用真實起訖（迄日若超過本批終點才截在 1918-11-12），所以子批之間不需要先撤後增；後面子批還沒送時只會出現空白、不會重疊。
來源、政權、事件放在第一個引用它們的子批。

輸入：
- ../borders-ohm-ww1-2.geojson＋../ohm-manifest.json（build/fetch.py＋build/build.py，固定版本 OHM 關係）
- ../../balkans-1908-1914/（WW1 第一批的 requests 與 derived geojson：迄於 1914-07-29 的紀錄要先撤後增、延長）
- ../db-export/ww1c_rows.json：開發庫唯讀匯出，本期間已有的主權紀錄（愛沙尼亞、盧森堡、荷蘭、瑞士等；只做 QA 與扣除，不進版控）
- ../db-export/us_1937.json：開發庫美國最早一筆紀錄（1937-07-07 起；本批照抄幾何，給衝突弧線用，不進版控）
輸出：../ww1-1914-1918-derived.geojson（key＝placeholder）、../qa.json、../requests/sub{1,2,3}/*.json

幾何規則（優先序引擎）：底層國家（prio 0）扣掉同期較高優先的紀錄（佔領區、新國家 prio 1～2；開發庫既有紀錄 prio 9），
在較高優先紀錄的起訖日切段，切點事件＝該紀錄的起／迄事件。相鄰兩段幾何相同就合併。
"""
import json, os, copy, datetime, sys, re
from shapely.geometry import shape, mapping, MultiPolygon, Polygon, LineString, MultiLineString, box
from shapely.ops import unary_union, linemerge
from shapely.validation import make_valid
from shapely import set_precision, STRtree

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); B1 = os.path.join(ROOT, '..', 'balkans-1908-1914')
START, END = '1914-07-29', '1918-11-12'
SUBS = [('sub1', START, '1916-01-01'), ('sub2', '1916-01-01', '1918-01-01'), ('sub3', '1918-01-01', END)]
MAN = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))}
ohm = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-ww1-2.geojson')))['features']}
ROWS = json.load(open(os.path.join(ROOT, 'db-export', 'ww1c_rows.json')))
US = json.load(open(os.path.join(ROOT, 'db-export', 'us_1937.json')))
B1G = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(B1, 'ww1-1908-1914-derived.geojson')))['features']}
B1R = {}
for fn in sorted(os.listdir(os.path.join(B1, 'requests'))):
    r = json.load(open(os.path.join(B1, 'requests', fn), encoding='utf-8')); B1R[r['_placeholder']] = r

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

# ── 手繪近似線（全部標「近似／待查證」）──
FRONT_1914 = [(2.75, 51.13), (2.87, 51.03), (2.95, 50.85), (2.88, 50.69), (2.80, 50.55), (2.75, 50.43), (2.82, 50.29), (2.65, 50.14), (2.72, 50.0), (2.79, 49.70),
              (2.84, 49.58), (2.93, 49.51), (3.33, 49.40), (3.79, 49.44), (3.90, 49.40), (4.05, 49.30), (4.30, 49.20), (4.60, 49.18), (4.75, 49.18), (4.88, 49.20),
              (5.03, 49.22), (5.20, 49.21), (5.40, 49.22), (5.60, 49.07), (5.55, 48.89), (5.64, 48.86), (6.05, 48.90), (6.30, 48.85)]
ARMISTICE_1918 = [(3.8, 51.2), (3.72, 51.05), (3.88, 50.77), (3.78, 50.63), (3.95, 50.45), (3.97, 50.28), (4.08, 49.92), (4.72, 49.77), (4.94, 49.70), (5.19, 49.49),
                  (5.40, 49.34), (5.75, 49.0), (6.05, 48.90)]
P_FRONT = make_valid(Polygon(FRONT_1914 + [(8, 48.85), (8, 52.5), (2.6, 52.5), (2.6, 51.2)]))
P_ARM = make_valid(Polygon(ARMISTICE_1918 + [(8, 48.9), (8, 52.5), (3.8, 52.5)]))
P_BGZONE = U(box(19, 40, 23.5, 42.35), box(21.5, 42.35, 23.5, 43.9))
P_NDOB = Polygon([(27.27, 43.5), (27.27, 44.12), (28.03, 44.34), (27.95, 44.68), (28.13, 45.25), (28.46, 45.27), (28.7, 45.22), (28.84, 45.35), (29.29, 45.42),
                  (29.6, 45.40), (30.5, 45.40), (30.5, 43.5)])
P_MOLD = Polygon([(25.5, 46.15), (26.5, 46.15), (26.9, 45.9), (27.2, 45.72), (27.6, 45.55), (28.2, 45.4), (28.25, 45.47), (28.25, 49), (25.5, 49)])
fmt = lambda pts: ' · '.join(f'{x},{y}' for x, y in pts)

RS, RO, RO81, BE, FR = O(2746681), O(2693260), O(2692219), O(2797729), O(2866012)
SDOB = RO.difference(RO81)                       # 南多布羅加（1913 布加勒斯特和約所得）
NDOB = RO81.intersection(P_NDOB)
DOB = U(SDOB, NDOB)                               # 整個多布羅加
PROV6 = U(*[O(r) for r in (2884612, 2951914, 2951908, 2945081, 2945094, 2945074)])
G = {
 'GG_BE_A': BE.intersection(PROV6), 'GG_BE_B': BE.intersection(P_FRONT), 'GG_BE_C': BE.intersection(P_ARM),
 'NFR_A': FR.intersection(P_FRONT), 'NFR_B': FR.intersection(P_ARM),
 'SERBIA_BG': RS.intersection(P_BGZONE), 'MGG_SERBIA': RS.difference(P_BGZONE),
 'DOB': DOB, 'NDOB': NDOB, 'RO_WAL': RO.difference(P_MOLD).difference(DOB),
 'BG_C': U(O(2746680), SDOB), 'RO_C': RO.difference(SDOB),
 'OT_F': O(2920989).difference(O(2848136)).difference(O(2830316)).difference(O(2855613)),
 'BALTIC': U(O(2744426), O(2869679)),
}
G = {k: clean(v) for k, v in G.items()}
def g_of(k):
    if isinstance(k, int): return clean(O(k))
    return G[k]

REQ = []
def add(cat, name, ph, post, body, meta=None, geom=None, sub=None):
    REQ.append(dict(cat=cat, name=name, ph=ph, post=post, body=body, meta=meta, geom=geom, sub=sub))

# ── 來源 ──
add('01-source', 'src_ohm_ww1b', 'SRC_OHM_WW1B', '/api/v1/sources', {'sourceKind': 'dataset',
    'title': 'OpenHistoricalMap — boundary=administrative 關係（歐洲、北非、近東，1914～1918 WW1 第二批試驗）',
    'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
    'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
    'publishedText': 'Overpass osm_base %s；逐筆見 ww1/war-1914-1918/ohm-manifest.json' % MAN[2695684]['osm_base'],
    'note': 'OHM 整體以 CC0 1.0 釋出；部分成員線段帶 license=CC BY 4.0 標籤，部分線段註明來自 OpenStreetMap（ODbL），逐筆在主權紀錄標示。'})
GPO = 'United States Department of State; United States Government Printing Office, Washington'
FRUS = [('SRC_FRUS_1914S', 'frus1914Supp', 'Papers Relating to the Foreign Relations of the United States, 1914, Supplement, The World War', '1928'),
        ('SRC_FRUS_1915S', 'frus1915Supp', 'Papers Relating to the Foreign Relations of the United States, 1915, Supplement, The World War', '1928'),
        ('SRC_FRUS_1916S', 'frus1916Supp', 'Papers Relating to the Foreign Relations of the United States, 1916, Supplement, The World War', '1929'),
        ('SRC_FRUS_1917', 'frus1917', 'Papers Relating to the Foreign Relations of the United States, With the Address of the President to Congress December 4, 1917', '1926'),
        ('SRC_FRUS_1917S1', 'frus1917Supp01v01', 'Papers Relating to the Foreign Relations of the United States, 1917, Supplement 1, The World War', '1931'),
        ('SRC_FRUS_1917S2', 'frus1917Supp02v01', 'Papers Relating to the Foreign Relations of the United States, 1917, Supplement 2, The World War, Volume I', '1932'),
        ('SRC_FRUS_1918R1', 'frus1918Russiav01', 'Papers Relating to the Foreign Relations of the United States, 1918, Russia, Volume I', '1931'),
        ('SRC_FRUS_1918R2', 'frus1918Russiav02', 'Papers Relating to the Foreign Relations of the United States, 1918, Russia, Volume II', '1932'),
        ('SRC_FRUS_1918S1', 'frus1918Supp01v01', 'Papers Relating to the Foreign Relations of the United States, 1918, Supplement 1, The World War, Volume I', '1933')]
for ph, vol, t, yr in FRUS:
    add('01-source', ph.lower(), ph, '/api/v1/sources', {'sourceKind': 'official_record', 'title': t, 'publisher': GPO, 'licenseCode': 'us_federal_pd',
        'licenseEvidenceUrl': 'https://www.state.gov/copyright-information', 'url': 'https://history.state.gov/historicaldocuments/' + vol, 'publishedText': f'{yr} 年出版'})

# ── 新政權 ──
DESC = '本表自訂的說明性名稱（非政權正式名稱）'
REGIMES = [
 ('REGIME_CY_ANNEX', 'cyprus-british-annexation-1914', 'Cyprus (annexed by the United Kingdom)', 'en', '英國併吞的賽普勒斯', 'Cyprus (annexed by the United Kingdom, 1914)', f'{DESC}；OHM relation/2848135（British Occupation of Cyprus）'),
 ('REGIME_EG', 'sultanate-of-egypt', 'السلطنة المصرية', 'ar', '埃及蘇丹國（英國保護國）', 'Sultanate of Egypt (British protectorate)', 'OHM relation/2803205；原文名為通行稱呼'),
 ('REGIME_GG_BE', 'german-general-government-belgium-1914', 'Kaiserlich Deutsches Generalgouvernement in Belgien', 'de', '德國比利時總督府（1914–1918）', 'German General Government of Belgium (1914–1918)', '名稱為通行稱呼（待查證）'),
 ('REGIME_NFR_OCC', 'german-occupied-northern-france-1914', 'German-occupied northern France (1914–1918)', 'en', '德國佔領下的法國北部（1914–1918）', 'German-occupied northern France (1914–1918)', DESC),
 ('REGIME_GG_WARSAW', 'german-general-government-warsaw', 'Kaiserlich Deutsches Generalgouvernement Warschau', 'de', '德國華沙總督府', 'German General Government of Warsaw', 'OHM relation/2695682；名稱為通行稱呼'),
 ('REGIME_GG_LUBLIN', 'austro-hungarian-military-government-lublin', 'k.u.k. Militärgeneralgouvernement Lublin', 'de', '奧匈盧布林軍事總督府', 'Austro-Hungarian Military General Government of Lublin', 'OHM relation/2695683；名稱為通行稱呼'),
 ('REGIME_PL_REGENCY', 'regency-kingdom-of-poland', 'Królestwo Polskie', 'pl', '波蘭攝政王國', 'Regency Kingdom of Poland', 'OHM relation/2695684；FRUS 1916 Supp. Doc. 1035'),
 ('REGIME_OBER_OST', 'ober-ost', 'Gebiet des Oberbefehlshabers Ost', 'de', '東方總司令轄區（Ober Ost）', 'Ober Ost', 'OHM relation/2696283；原文名為通行稱呼'),
 ('REGIME_LT_1918', 'state-of-lithuania-1918', 'Lietuvos valstybė', 'lt', '立陶宛國（1918，德國佔領下）', 'State of Lithuania (1918, under German occupation)', '名稱為通行稱呼（待查證）；OHM relation/2744425（Verwaltungsbezirk Litauen）'),
 ('REGIME_BALTIC_OCC', 'german-occupied-courland-livonia-1918', 'German-occupied Courland and Livonia (1918)', 'en', '德國佔領下的庫爾蘭與利沃尼亞（1918）', 'German-occupied Courland and Livonia (1918)', f'{DESC}；OHM relation/2744426 ∪ relation/2869679'),
 ('REGIME_BY_PR', 'belarusian-peoples-republic', 'Беларуская Народная Рэспубліка', 'be', '白俄羅斯人民共和國', "Belarusian People's Republic", 'OHM relation/2957449；原文名為通行稱呼'),
 ('REGIME_UA_PR', 'ukrainian-peoples-republic', 'Українська Народна Республіка', 'uk', '烏克蘭人民共和國', "Ukrainian People's Republic", 'OHM relation/2694815；原文名為通行稱呼'),
 ('REGIME_RU_PROV', 'russian-provisional-government-1917', 'Временное правительство России', 'ru', '俄國臨時政府（俄羅斯共和國）', 'Russian Provisional Government (Russian Republic)', '原文名為通行稱呼；OHM relation/2869933（Russian Republic）'),
 ('REGIME_RSFSR', 'russian-sfsr-1917', 'Российская Социалистическая Федеративная Советская Республика', 'ru', '俄羅斯蘇維埃聯邦社會主義共和國', 'Russian Socialist Federative Soviet Republic', 'OHM relation/2852344 等；原文名為通行稱呼（1918-07 憲法定名，之前稱呼不一，待查證）'),
 ('REGIME_TC_COMM', 'transcaucasian-commissariat', 'Закавказский комиссариат', 'ru', '外高加索委員會', 'Transcaucasian Commissariat', 'OHM relation/2957453'),
 ('REGIME_TDFR', 'transcaucasian-democratic-federative-republic', 'Закавказская демократическая федеративная республика', 'ru', '外高加索民主聯邦共和國', 'Transcaucasian Democratic Federative Republic', 'OHM relation/2957454；原文名為通行稱呼'),
 ('REGIME_GE', 'democratic-republic-of-georgia', 'საქართველოს დემოკრატიული რესპუბლიკა', 'ka', '喬治亞民主共和國', 'Democratic Republic of Georgia', 'OHM relation/2698086；原文名為通行稱呼'),
 ('REGIME_AM', 'first-republic-of-armenia', 'Հայաստանի Հանրապետություն', 'hy', '亞美尼亞第一共和國', 'First Republic of Armenia', 'OHM relation/2698116；原文名為通行稱呼'),
 ('REGIME_AZ', 'azerbaijan-democratic-republic', 'Azərbaycan Xalq Cümhuriyyəti', 'az', '亞塞拜然民主共和國', 'Azerbaijan Democratic Republic', 'OHM relation/2698117；原文名為通行稱呼'),
 ('REGIME_MRNC', 'mountainous-republic-northern-caucasus', 'Республика Союза горцев Северного Кавказа', 'ru', '北高加索山地共和國', 'Mountainous Republic of the Northern Caucasus', 'OHM relation/2891769；原文名為通行稱呼（待查證）'),
 ('REGIME_SCS', 'state-of-slovenes-croats-and-serbs', 'Država Slovenaca, Hrvata i Srba', 'sh', '斯洛維尼亞人、克羅埃西亞人和塞爾維亞人國', 'State of Slovenes, Croats and Serbs', 'OHM relation/2747879；原文名為通行稱呼'),
 ('REGIME_SERBIA_BG', 'bulgarian-occupied-serbia-1915', 'Bulgarian-occupied Serbia (1915–1918)', 'en', '保加利亞佔領（併入）的塞爾維亞領土', 'Bulgarian-occupied Serbia (1915–1918)', DESC),
 ('REGIME_MGG_SERBIA', 'austro-hungarian-military-government-serbia', 'k.u.k. Militärgeneralgouvernement Serbien', 'de', '奧匈塞爾維亞軍事總督府', 'Austro-Hungarian Military General Government of Serbia', '名稱為通行稱呼'),
 ('REGIME_MGG_MN', 'austro-hungarian-military-government-montenegro', 'k.u.k. Militärgeneralgouvernement Montenegro', 'de', '奧匈蒙特內哥羅軍事總督府', 'Austro-Hungarian Military General Government of Montenegro', '名稱為通行稱呼'),
 ('REGIME_RO_MILVERW', 'military-administration-romania-1916', 'Militärverwaltung in Rumänien', 'de', '德軍羅馬尼亞軍政府', 'Military Administration in Romania', '名稱為通行稱呼'),
 ('REGIME_DOBRUJA', 'occupied-dobruja-1916', 'Central Powers–occupied Dobruja (1916–1918)', 'en', '同盟國佔領的多布羅加', 'Central Powers–occupied Dobruja (1916–1918)', DESC),
]
for ph, slug, orig, lang, zh, en, ns in REGIMES:
    add('02-regime', slug, ph, '/api/v1/regimes', {'slug': slug, 'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang,
        'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]}, {'priorPlaceholder': False, 'nameSource': ns})
# 沿用：第一批 REGIME_AH、REGIME_DE_EMP、REGIME_RU_EMP、REGIME_OT、REGIME_RS、REGIME_MN_K、REGIME_UK_GBI、REGIME_CY_BR 等；
# 前置表 REGIME_IT、REGIME_RO、REGIME_GR、REGIME_BE、REGIME_BG、REGIME_FR3、REGIME_PT、REGIME_LU、REGIME_EE、REGIME_FI、REGIME_CS、REGIME_PL；美國表 REGIME_US、SRC_OHM_US

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
F14, F15, F16, F17, F17A, F17B, R1, R2, F18 = 'SRC_FRUS_1914S', 'SRC_FRUS_1915S', 'SRC_FRUS_1916S', 'SRC_FRUS_1917', 'SRC_FRUS_1917S1', 'SRC_FRUS_1917S2', 'SRC_FRUS_1918R1', 'SRC_FRUS_1918R2', 'SRC_FRUS_1918S1'
# 1914
ev('EV_DE_RU_WAR', 'war', '1914-08-01', '德國對俄國宣戰', 'Germany declares war on Russia', [('REGIME_DE_EMP', B), ('REGIME_RU_EMP', B)],
   [(F14, 'Doc. 58, pp. 28–29', '駐聖彼得堡代辦 1914-08-01 電：約下午 6 時德國大使向俄外交部遞交對俄宣戰書。'), (F14, 'Doc. 70, p. 33', '同日相關電報：德國對俄宣戰。')])
ev('EV_LUX_OCC', 'campaign', '1914-08-02', '德軍進入並佔領盧森堡', 'German troops enter and occupy Luxembourg', [('REGIME_DE_EMP', B), ('REGIME_LU', B)], [], NOSRC)
ev('EV_DE_FR_WAR', 'war', '1914-08-03', '德國對法國宣戰', 'Germany declares war on France', [('REGIME_DE_EMP', B), ('REGIME_FR3', B)],
   [(F14, 'Doc. 88, p. 40', '德國代辦 1914-08-03 電國務卿：法國自 8 月 1 日起多次攻擊德國領土，德國因此與法國進入戰爭狀態。'), (F14, 'Doc. 209, pp. 112–113', '相關照會：德法開戰經過。')])
ev('EV_DE_BE_INV', 'war', '1914-08-04', '德軍入侵比利時', 'Germany invades Belgium', [('REGIME_DE_EMP', B), ('REGIME_BE', B)],
   [(F14, 'Doc. 98, p. 45', '國務院 1914-08-05 備忘錄：比利時政府通知德軍已進入比利時領土、中立被破壞，比利時將以武力抵抗。'),
    (F14, 'Doc. 157, pp. 71–72', '比利時公使 1914-08-20 照會：依 1839 年條約，德國破壞比利時中立。')])
ev('EV_UK_DE_WAR', 'war', '1914-08-04', '英國對德國宣戰', 'Great Britain declares war on Germany', [('REGIME_UK_GBI', B), ('REGIME_DE_EMP', B)],
   [(F14, 'Doc. 96, p. 44', '駐倫敦大使 1914-08-05 電：收到英外交部 8 月 4 日照會，英德之間存在戰爭狀態。')])
ev('EV_AH_RU_WAR', 'war', '1914-08-06', '奧匈帝國對俄國宣戰', 'Austria-Hungary declares war on Russia', [('REGIME_AH', B), ('REGIME_RU_EMP', B)],
   [(F14, 'Doc. 107, p. 47', '俄國大使電（1914-08-06 收到）：奧匈已對俄宣戰。'), (F14, 'Doc. 110, pp. 48–49', '相關電報：奧匈對俄宣戰。')])
ev('EV_AH_MN_WAR', 'war', '1914-08-09', '奧匈帝國與蒙特內哥羅開戰', 'War between Austria-Hungary and Montenegro', [('REGIME_AH', B), ('REGIME_MN_K', B)],
   [(F14, 'Doc. 120, p. 52', '駐維也納大使 1914-08-10 電：「Austria-Hungary declared war against Montenegro 9th instant.」')],
   ('蒙特內哥羅 8 月 5 日對奧匈宣戰為通行說法（待查證）；本表取 FRUS 所記奧匈宣戰日 8 月 9 日。', 'Montenegro is usually said to have declared war on 5 Aug (pending); FRUS records the Austro-Hungarian declaration of 9 Aug.'))
ev('EV_FR_AH_WAR', 'war', '1914-08-12', '法國對奧匈帝國宣戰', 'France declares war on Austria-Hungary', [('REGIME_FR3', B), ('REGIME_AH', B)],
   [(F14, 'Doc. 143, pp. 64–65', '法國代辦 1914-08-13 照會：法國政府「昨日」向奧匈政府遞交宣戰聲明。')])
ev('EV_UK_AH_WAR', 'war', '1914-08-12', '英國對奧匈帝國宣戰', 'Great Britain declares war on Austria-Hungary', [('REGIME_UK_GBI', B), ('REGIME_AH', B)],
   [(F14, 'Doc. 128, p. 56', '駐開羅副總領事 1914-08-13 電：英國代辦告知英國已對奧地利宣戰。')], ('8 月 12 日為通行說法；FRUS 電報日為 8 月 13 日。', 'Usually dated 12 Aug; the FRUS telegram is of 13 Aug.'))
ev('EV_BRUSSELS', 'campaign', '1914-08-20', '德軍進入布魯塞爾，比利時大部被佔領', 'German troops enter Brussels; most of Belgium occupied', [('REGIME_DE_EMP', B), ('REGIME_BE', B)],
   [(F14, 'Doc. 159, pp. 73–74', '駐布魯塞爾公使 1914-08-24 電：電報須由專人穿越德軍防線送到安特衛普發出（布魯塞爾已在德軍控制下）。')],
   ('8 月 20 日德軍入城為通行說法；FRUS 只證明 8 月 24 日前已被佔領。', 'Entry on 20 Aug per common accounts; FRUS confirms occupation by 24 Aug.'))
ev('EV_ANTWERP', 'campaign', '1914-10-10', '安特衛普陷落，比利時軍退守伊瑟河', 'Fall of Antwerp; the Belgian army withdraws to the Yser', [('REGIME_DE_EMP', B), ('REGIME_BE', B)],
   [(F14, 'Doc. 229, pp. 122–123', '駐海牙公使 1914-10-14 報告：安特衛普陷落是上週的主要事件，大量比利時難民湧入荷蘭。')],
   ('10 月 10 日投降為通行說法；FRUS 報告日為 10 月 14 日。', 'Surrender on 10 Oct per common accounts; FRUS report of 14 Oct.'))
ev('EV_NFR_FRONT', 'campaign', '1914-10-13', '德軍佔領里爾，法國北部佔領區大致成形（西線轉入壕溝戰）', 'German troops take Lille; the occupied zone in northern France takes shape (trench warfare)',
   [('REGIME_DE_EMP', B), ('REGIME_FR3', B)], [], ('未找到正式出處（待查證）；里爾 10 月 12–13 日陷落為通行說法。FRUS 1914 Supp. Doc. 1282（魯貝領事報告）只記 10 月初兩軍出現在里爾一帶。', 'No formal source (pending); Lille fell on 12–13 Oct per common accounts.'))
ev('EV_OT_ENTRY', 'war', '1914-10-29', '鄂圖曼艦隊砲擊俄國黑海港口，鄂圖曼帝國參戰', 'Ottoman fleet bombards Russian Black Sea ports; the Ottoman Empire enters the war', [('REGIME_OT', B), ('REGIME_RU_EMP', B)],
   [(F14, 'Doc. 239, p. 127', '駐君士坦丁堡大使 1914-10-30 電：內政大臣告知塞瓦斯托波爾已遭砲擊，俄國大使索取護照。'), (F14, 'Doc. 238, p. 127', '同日相關電報。')],
   ('10 月 29 日砲擊為通行說法；俄國 11 月 2 日正式宣戰（待查證）。', 'Bombardment on 29 Oct per common accounts; Russia declared war on 2 Nov (pending).'))
ev('EV_ENTENTE_OT_WAR', 'war', '1914-11-05', '英、法對鄂圖曼帝國宣戰', 'Britain and France declare war on the Ottoman Empire', [('REGIME_UK_GBI', B), ('REGIME_FR3', B), ('REGIME_OT', B)],
   [(F14, 'Doc. 243, p. 129', '駐倫敦大使 1914-11-05 電：格雷爵士告知英國與土耳其之間存在戰爭狀態，土耳其大使館今晨撤離。')],
   ('FRUS 只記英國；法國同日宣戰為通行說法（待查證）。', 'FRUS records Britain only; France on the same day per common accounts (pending).'))
ev('EV_CY_ANNEX', 'political', '1914-11-05', '英國併吞賽普勒斯', 'Britain annexes Cyprus', [('REGIME_UK_GBI', S_), ('REGIME_CY_BR', S_)], [],
   ('未找到正式出處（待查證）；11 月 5 日樞密院令為通行說法；OHM 2848135 起日只到年（1914）。', 'No formal source (pending); Order in Council of 5 Nov 1914 per common accounts.'))
ev('EV_EGYPT', 'political', '1914-12-18', '英國宣布埃及為保護國，終止鄂圖曼宗主權', 'Britain proclaims a protectorate over Egypt, ending Ottoman suzerainty', [('REGIME_UK_GBI', S_), ('REGIME_EG', S_)],
   [(F14, 'Doc. 274, pp. 152–153', '英國大使 1914-12-18 照會：英國政府認為土耳其對埃及的宗主權已終止，埃及成為英國保護國。'),
    (F14, 'Doc. 275, p. 153', '駐開羅外交代表電（12 月 20 日收到）：侯賽因親王「今日」被英王宣布為埃及蘇丹。')],
   ('保護國宣言 12 月 18 日；侯賽因稱蘇丹 12 月 19 日（OHM 2803205 起日）。', 'Protectorate proclaimed 18 Dec; Hussein Kamel proclaimed Sultan 19 Dec (OHM start).'))
# 1915
ev('EV_IT_AH_WAR', 'war', '1915-05-23', '義大利對奧匈帝國宣戰（5 月 24 日起進入戰爭狀態）', 'Italy declares war on Austria-Hungary (state of war from 24 May)', [('REGIME_IT', B), ('REGIME_AH', B)],
   [(F15, 'Doc. 53, pp. 35–36', '駐羅馬大使 1915-05-23 電：義大利外交部通知，義大利「自明日起」與奧匈處於戰爭狀態。')])
ev('EV_WARSAW', 'campaign', '1915-08-05', '德軍佔領華沙，俄屬波蘭失守', 'German troops take Warsaw; Russian Poland lost', [('REGIME_DE_EMP', B), ('REGIME_AH', B), ('REGIME_RU_EMP', B)],
   [(F15, 'Doc. 79, pp. 59–61', '駐彼得格勒大使 1915-08-31 報告：「the evacuation of Warsaw and the withdrawal of the Russians from the fortress of Kovno」。')],
   ('8 月 5 日德軍入城為通行說法；華沙、盧布林總督府 8 月底至 10 月才正式設立（OHM 起日 9-01／10-18），本表從華沙陷落起算。', 'Warsaw entered on 5 Aug per common accounts; the general governments were set up Aug–Oct (OHM starts 1 Sep / 18 Oct).'))
ev('EV_IT_OT_WAR', 'war', '1915-08-21', '義大利對鄂圖曼帝國宣戰', 'Italy declares war on the Ottoman Empire', [('REGIME_IT', B), ('REGIME_OT', B)], [], NOSRC)
ev('EV_VILNA', 'campaign', '1915-09-19', '德軍佔領維爾紐斯，東方總司令轄區（Ober Ost）成形', 'German troops take Vilnius; the Ober Ost territory takes shape', [('REGIME_DE_EMP', B), ('REGIME_RU_EMP', B)], [],
   ('未找到正式出處（待查證）；維爾紐斯 9 月 18–19 日陷落為通行說法。OHM 2696283 起日只到月（1914-11，指司令部設立）。', 'No formal source (pending); Vilnius fell on 18–19 Sep per common accounts.'))
ev('EV_BG_RS_WAR', 'war', '1915-10-14', '保加利亞進攻塞爾維亞，保加利亞參戰', 'Bulgaria attacks Serbia and enters the war', [('REGIME_BG', B), ('REGIME_RS', B)],
   [(F15, 'Doc. 88, p. 65', '駐羅馬大使 1915-10-15 電：塞爾維亞使館接報保加利亞未經宣戰從背後攻擊塞爾維亞。')],
   ('保、塞 10 月 14 日互相宣戰為通行說法（待查證）。', 'Mutual declarations of 14 Oct per common accounts (pending).'))
ev('EV_ENTENTE_BG_WAR', 'war', '1915-10-15', '協約國對保加利亞宣戰（英 10-15、法 10-16、義 10-19）', 'The Entente declares war on Bulgaria (UK 15 Oct, France 16 Oct, Italy 19 Oct)',
   [('REGIME_UK_GBI', B), ('REGIME_FR3', B), ('REGIME_IT', B), ('REGIME_RU_EMP', B), ('REGIME_BG', B)],
   [(F15, 'Doc. 89, p. 65', '駐倫敦大使 1915-10-16 電：格雷爵士告知 10 月 15 日起英保之間存在戰爭狀態。'),
    (F15, 'Doc. 90, p. 65', '駐巴黎大使 1915-10-18 電：《官報》載法國自 1915-10-16 上午 6 時起與保加利亞處於戰爭狀態。'),
    (F15, 'Doc. 91, p. 65', '1915-10-19 國務院紀錄：義大利使館參事告知義保之間存在戰爭狀態。')],
   ('俄國約 10 月 18–19 日宣戰（待查證）。', 'Russia declared war around 18–19 Oct (pending).'))
ev('EV_SERBIA_FALL', 'campaign', '1915-11-28', '塞爾維亞全境被同盟國佔領，塞軍經阿爾巴尼亞撤退', 'Serbia overrun by the Central Powers; the Serbian army retreats through Albania',
   [('REGIME_AH', B), ('REGIME_DE_EMP', B), ('REGIME_BG', B), ('REGIME_RS', B)], [],
   ('未找到正式出處（待查證）；11 月下旬戰役結束為通行說法（奧匈塞爾維亞軍事總督府 1916-01-01 成立）。', 'No formal source (pending); campaign over in late November per common accounts.'))
# 1916
ev('EV_MN_OCC', 'campaign', '1916-01-13', '奧匈軍佔領采蒂涅，蒙特內哥羅被佔領', 'Austro-Hungarian troops take Cetinje; Montenegro occupied', [('REGIME_AH', B), ('REGIME_MN_K', B)], [],
   ('未找到正式出處（待查證）；采蒂涅 1 月 13 日陷落、1 月 25 日投降為通行說法。', 'No formal source (pending); Cetinje fell 13 Jan, capitulation 25 Jan per common accounts.'))
ev('EV_DE_PT_WAR', 'war', '1916-03-09', '德國對葡萄牙宣戰', 'Germany declares war on Portugal', [('REGIME_DE_EMP', B), ('REGIME_PT', B)],
   [(F16, 'Doc. 12, p. 18', '駐里斯本公使 1916-03-09 電：德國公使奉命向葡外交部聲明德國認為與葡萄牙處於戰爭狀態。')])
ev('EV_RO_ENTRY', 'war', '1916-08-27', '羅馬尼亞對奧匈帝國宣戰', 'Romania declares war on Austria-Hungary', [('REGIME_RO', B), ('REGIME_AH', B)],
   [(F16, 'Doc. 62, p. 48', '駐布加勒斯特公使 1916-08-28 電：羅馬尼亞自 27 日晚 9 時起認為與奧匈處於戰爭狀態。'), (F16, 'Doc. 60', '相關電報：羅馬尼亞參戰。')])
ev('EV_CP_RO_WAR', 'war', '1916-08-28', '德國、鄂圖曼、保加利亞對羅馬尼亞宣戰', 'Germany, the Ottoman Empire and Bulgaria declare war on Romania',
   [('REGIME_DE_EMP', B), ('REGIME_OT', B), ('REGIME_BG', B), ('REGIME_RO', B)],
   [(F16, 'Doc. 65, p. 49', '駐君士坦丁堡代辦 1916-08-30 電：鄂圖曼內閣「昨日」決議，與德國、保加利亞共同對羅馬尼亞宣戰。')],
   ('德國 8 月 28 日、鄂圖曼 8 月 29–30 日、保加利亞 9 月 1 日為通行說法（待查證）；本表取德國宣戰日。', 'Germany 28 Aug, Ottomans 29–30 Aug, Bulgaria 1 Sep per common accounts (pending).'))
ev('EV_IT_DE_WAR', 'war', '1916-08-28', '義大利對德國宣戰', 'Italy declares war on Germany', [('REGIME_IT', B), ('REGIME_DE_EMP', B)],
   [(F16, 'Doc. 63, pp. 48–49', '義大利大使 1916-08-28 照會：列舉德國的敵對行為，宣布義大利與德國處於戰爭狀態。')])
ev('EV_DOBRUJA_OCC', 'campaign', '1916-10-22', '同盟國軍攻佔康斯坦察，多布羅加被佔領', 'Central Powers take Constanța; Dobruja occupied', [('REGIME_BG', B), ('REGIME_DE_EMP', B), ('REGIME_RO', B)], [],
   ('未找到正式出處（待查證）；康斯坦察 10 月 22 日陷落為通行說法，北多布羅加三角洲到 1917-01 才全部佔領。', 'No formal source (pending); Constanța fell on 22 Oct per common accounts.'))
ev('EV_PL_KINGDOM', 'political', '1916-11-05', '德、奧兩皇宣布成立波蘭王國（攝政王國）', 'The German and Austrian Emperors proclaim a Kingdom of Poland', [('REGIME_DE_EMP', S_), ('REGIME_AH', S_), ('REGIME_PL_REGENCY', S_)],
   [(F16, 'Doc. 1035, p. 796', '駐柏林代辦 1916-11-05 電：德、奧匈兩皇今日宣言宣布波蘭為世襲君主立憲的獨立國家，邊界日後決定。'), (F16, 'Doc. 1036, pp. 796–797', '宣言全文。')])
ev('EV_BUCHAREST_FALL', 'campaign', '1916-12-06', '同盟國軍攻佔布加勒斯特，瓦拉幾亞被佔領', 'Central Powers take Bucharest; Wallachia occupied', [('REGIME_DE_EMP', B), ('REGIME_AH', B), ('REGIME_RO', B)],
   [(F16, 'Doc. 109, pp. 81–82', '駐柏林代辦 1916-12-07 電：「The taking of Bucharest has made a very strong impression in Berlin.」')])
# 1917
ev('EV_FEB_REV', 'political', '1917-03-15', '俄國二月革命：尼古拉二世退位，臨時政府成立', 'February Revolution: Nicholas II abdicates; the Provisional Government is formed', [('REGIME_RU_EMP', S_), ('REGIME_RU_PROV', S_)],
   [(F17, 'Doc. 1449, p. 1205', '駐彼得格勒大使 1917-03-17 電：12 日起彼得格勒革命，部隊倒戈，臨時政府成立。'), (F17, 'Doc. 1450, pp. 1205–1206', '同日電：皇帝為自己及皇子退位的詔書已正式公布。')],
   ('退位為 3 月 15 日（儒略曆 3 月 2 日）。', 'Abdication on 15 March (2 March O.S.).'))
ev('EV_US_DE_WAR', 'war', '1917-04-06', '美國對德國宣戰', 'The United States declares war on Germany', [('REGIME_US', B), ('REGIME_DE_EMP', B)],
   [(F17A, 'Doc. 240, pp. 207–208', '1917-04-06 總統宣告：美德之間存在戰爭狀態。')])
ev('EV_GR_WAR', 'war', '1917-07-02', '希臘（統一政府）對德國、保加利亞處於戰爭狀態', 'Greece (reunited government) at war with Germany and Bulgaria', [('REGIME_GR', B), ('REGIME_DE_EMP', B), ('REGIME_BG', B)],
   [(F17B, 'Doc. 165, p. 117', '駐雅典公使 1917-07-02 電：外交大臣告知希臘與德國、保加利亞處於戰爭狀態，與其他同盟國斷交。'),
    (F17B, 'Doc. 159, p. 113', '同使 6 月 30 日電：統一後的希臘承擔原臨時政府（已對德、保宣戰）的政策。')],
   ('韋尼澤洛斯的國防臨時政府 1916-11 已對德、保宣戰（不在本表）；本表取 FRUS 所記希臘政府宣告日。', 'The Venizelist provisional government had declared war in Nov 1916 (not modeled).'))
ev('EV_RU_REPUBLIC', 'political', '1917-09-14', '俄國臨時政府宣布俄國為共和國', 'The Provisional Government proclaims Russia a republic', [('REGIME_RU_PROV', S_)],
   [(R1, 'Doc. 154, pp. 191–192', '駐彼得格勒大使 1917-09-16 電：蘇維埃機關報宣布臨時政府已宣布共和。')], ('9 月 14 日（儒略曆 9 月 1 日）宣布。', 'Proclaimed 14 Sep (1 Sep O.S.).'))
ev('EV_OCT_REV', 'political', '1917-11-07', '俄國十月革命：布爾什維克奪取政權', 'October Revolution: the Bolsheviks seize power', [('REGIME_RU_PROV', S_), ('REGIME_RSFSR', S_)],
   [(R1, 'Doc. 198, p. 224', '駐彼得格勒大使 1917-11-07 電：克倫斯基匆忙離城去迎部隊。'), (R1, 'Doc. 199, pp. 224–225', '同日電：「Bolsheviki appear to have control of everything here.」')],
   ('11 月 7 日（儒略曆 10 月 25 日）。', '7 Nov (25 Oct O.S.).'))
ev('EV_TC', 'political', '1917-11-15', '外高加索委員會在梯弗里斯成立', 'The Transcaucasian Commissariat is formed in Tiflis', [('REGIME_TC_COMM', S_)], [], NOSRC)
ev('EV_FI_INDEP', 'political', '1917-12-06', '芬蘭宣布獨立', 'Finland declares independence', [('REGIME_FI', S_)],
   [(R2, 'Doc. 864, p. 734', '駐斯德哥爾摩公使 1917-12-06 電：芬蘭參議院繼議會之後宣布芬蘭完全獨立。')])
ev('EV_US_AH_WAR', 'war', '1917-12-07', '美國對奧匈帝國宣戰', 'The United States declares war on Austria-Hungary', [('REGIME_US', B), ('REGIME_AH', B)],
   [(F17B, 'Doc. 381, p. 459', '國務卿 1917-12-07 通電：國會今日通過、總統簽署對奧匈宣戰的聯合決議。')])
# 1918
ev('EV_BREST_UA', 'treaty', '1918-02-09', '布列斯特—立陶夫斯克（烏克蘭）和約：同盟國承認烏克蘭人民共和國', "Treaty of Brest-Litovsk with Ukraine: the Central Powers recognize the Ukrainian People's Republic",
   [('REGIME_UA_PR', S_), ('REGIME_DE_EMP', S_), ('REGIME_AH', S_), ('REGIME_OT', S_), ('REGIME_BG', S_)],
   [(R2, 'Doc. 785, pp. 665–666', '駐莫斯科總領事 1918-04-27 電：烏克蘭與同盟國和約條文（含邊界條款）。'), (F18, 'Doc. 746, p. 757', '駐羅馬尼亞公使 1918-02-09 電：同盟國與烏克蘭剛簽訂和約。')])
ev('EV_EE_OCC', 'campaign', '1918-02-24', '德軍進入愛沙尼亞與利沃尼亞（愛沙尼亞同日宣布獨立）', 'German troops advance into Estonia and Livonia (Estonia declares independence the same day)',
   [('REGIME_DE_EMP', B), ('REGIME_RSFSR', B), ('REGIME_EE', S_)],
   [(F18, 'Doc. 84, pp. 135–138', '駐海牙公使 1918-02-25 電轉述赫特林國會演說：德軍在利沃尼亞、愛沙尼亞的軍事行動「成功遠超原定目標」，稱無意長期佔領。')],
   ('德軍 2 月 25 日進入塔林為通行說法；開發庫既有愛沙尼亞紀錄起日 1918-02-24（未設起事件，不在本批修改）。', 'German troops entered Tallinn on 25 Feb per common accounts; the existing Estonia record starts 24 Feb.'))
ev('EV_BREST', 'treaty', '1918-03-03', '布列斯特—立陶夫斯克和約：俄國退出戰爭，放棄波蘭、立陶宛、庫爾蘭、利沃尼亞、愛沙尼亞、芬蘭、烏克蘭', 'Treaty of Brest-Litovsk: Russia leaves the war and gives up Poland, Lithuania, Courland, Livonia, Estonia, Finland and Ukraine',
   [('REGIME_RSFSR', S_), ('REGIME_DE_EMP', S_), ('REGIME_AH', S_), ('REGIME_OT', S_), ('REGIME_BG', S_)],
   [(R1, 'Doc. 443, pp. 442–471', '駐莫斯科總領事 1918-03-30／04-02 電：布列斯特—立陶夫斯克和約全文（第 3 條西部界線、第 4 條卡爾斯／阿爾達漢／巴統、第 6 條芬蘭與烏克蘭）。'),
    (R1, 'Doc. 434, p. 434', '駐斯德哥爾摩公使 1918-03-04 電：對俄和約於星期日 5 時簽字。')])
ev('EV_BY_PR', 'political', '1918-03-25', '白俄羅斯人民共和國宣布獨立', "The Belarusian People's Republic declares independence", [('REGIME_BY_PR', S_)], [], NOSRC)
ev('EV_BESSARABIA', 'political', '1918-04-09', '比薩拉比亞（摩爾達維亞民主共和國）議會表決與羅馬尼亞合併', 'The Bessarabian assembly votes for union with Romania', [('REGIME_RO', S_)], [],
   ('未找到正式出處（待查證）；4 月 9 日（儒略曆 3 月 27 日）表決為通行說法。FRUS 1918 Russia II Doc. 848（4 月 9 日協約國公使聯電）只說合併「在即」。', 'No formal source (pending); FRUS only says the union "appears imminent" on 9 April.'))
ev('EV_TDFR', 'political', '1918-04-22', '外高加索民主聯邦共和國宣布獨立', 'The Transcaucasian Democratic Federative Republic declares independence', [('REGIME_TDFR', S_)], [], NOSRC)
ev('EV_BUCH18', 'treaty', '1918-05-07', '布加勒斯特和約（1918）：羅馬尼亞割讓南多布羅加給保加利亞，北多布羅加歸同盟國共管', 'Treaty of Bucharest (1918): Romania cedes Southern Dobruja to Bulgaria; Northern Dobruja under Central Powers condominium',
   [('REGIME_RO', S_), ('REGIME_DE_EMP', S_), ('REGIME_AH', S_), ('REGIME_BG', S_), ('REGIME_OT', S_)],
   [(F18, 'Doc. 768, pp. 771–777', '駐雅西公使 1918-05-14／20 電：報載羅馬尼亞與同盟國和約全文（第 10 條多布羅加）。')],
   ('羅馬尼亞國王未批准，1918-11 停戰後失效（德國停戰協定第 15 條）。', 'Never ratified by the King of Romania; annulled by the armistice of 11 Nov 1918 (art. 15).'))
ev('EV_MRNC', 'political', '1918-05-11', '北高加索山地共和國宣布獨立', 'The Mountainous Republic of the Northern Caucasus declares independence', [('REGIME_MRNC', S_)], [], NOSRC)
ev('EV_GE', 'political', '1918-05-26', '喬治亞宣布獨立，外高加索聯邦解體', 'Georgia declares independence; the Transcaucasian federation dissolves', [('REGIME_GE', S_), ('REGIME_TDFR', S_)], [], NOSRC)
ev('EV_AM_AZ', 'political', '1918-05-28', '亞美尼亞、亞塞拜然宣布獨立', 'Armenia and Azerbaijan declare independence', [('REGIME_AM', S_), ('REGIME_AZ', S_)], [], NOSRC)
ev('EV_BG_ARMISTICE', 'armistice', '1918-09-29', '薩洛尼卡停戰協定：保加利亞退出戰爭', 'Armistice of Salonika: Bulgaria leaves the war', [('REGIME_BG', S_), ('REGIME_FR3', S_), ('REGIME_UK_GBI', S_), ('REGIME_RS', S_), ('REGIME_GR', S_), ('REGIME_IT', S_)],
   [(F18, 'Doc. 273, p. 331', '駐薩洛尼卡總領事 1918-09-30 電：午夜協約國聯軍總司令與保加利亞代表簽訂軍事協定，對保戰事結束。'), (F18, 'Doc. 275, p. 334', '停戰條件。')],
   ('9 月 29 日夜簽字、30 日中午生效。', 'Signed on the night of 29 Sep, effective noon 30 Sep.'))
ev('EV_CS', 'political', '1918-10-28', '捷克斯洛伐克在布拉格宣布獨立', 'Czechoslovakia proclaims independence in Prague', [('REGIME_CS', S_)], [], NOSRC)
ev('EV_SCS', 'political', '1918-10-29', '薩格勒布議會宣布脫離奧匈，成立斯洛維尼亞人、克羅埃西亞人和塞爾維亞人國', 'The Zagreb Sabor breaks with Austria-Hungary; State of Slovenes, Croats and Serbs', [('REGIME_SCS', S_)], [],
   ('未找到正式出處（待查證）；日期為通行說法。FRUS 1918 Supp. 1 I Doc. 372（11-02）列出奧匈境內已成立的各政府機關。', 'No formal source for the date (pending); FRUS Doc. 372 (2 Nov) lists the new governmental organs.'))
ev('EV_MUDROS', 'armistice', '1918-10-30', '穆德羅斯停戰協定：鄂圖曼帝國退出戰爭', 'Armistice of Mudros: the Ottoman Empire leaves the war', [('REGIME_OT', S_), ('REGIME_UK_GBI', S_)],
   [(F18, 'Doc. 368, pp. 441–443', '1918-10-30 於利姆諾斯島穆德羅斯港英艦阿伽門農號簽訂，10 月 31 日中午生效；停戰條件全文。')])
ev('EV_VILLA_GIUSTI', 'armistice', '1918-11-03', '朱斯蒂別墅停戰協定：奧匈帝國退出戰爭', 'Armistice of Villa Giusti: Austria-Hungary leaves the war', [('REGIME_AH', S_), ('REGIME_IT', S_)],
   [(F18, 'Doc. 373, p. 447', '豪斯 1918-11-03 電：「Austrian armistice signed.」'), (F18, 'Doc. 360, pp. 430–431', '豪斯 10-31 電：最高戰爭委員會在凡爾賽正式通過對奧停戰條件。')],
   ('11 月 3 日簽字、4 日 15 時生效。', 'Signed 3 Nov, effective 4 Nov 15:00.'))
ev('EV_COMPIEGNE', 'armistice', '1918-11-11', '貢比涅停戰協定：德國停戰，西線戰事結束', 'Armistice of Compiègne: Germany signs the armistice; fighting ends on the Western Front', [('REGIME_DE_EMP', S_), ('REGIME_FR3', S_), ('REGIME_UK_GBI', S_)],
   [(F18, 'Doc. 417, p. 492', '豪斯 1918-11-11 電：停戰協定今晨 5 時簽字，上午 11 時停火。'), (F18, 'Doc. 384, pp. 463–468', '對德停戰條件全文（第 2 條撤出比、法、盧、亞爾薩斯—洛林；第 15 條廢除布加勒斯特與布列斯特和約）。'),
    (F18, 'Doc. 420, pp. 494–498', '簽字版最後修改。')])
ev('EV_PL_INDEP', 'political', '1918-11-11', '攝政會議把軍權交給畢蘇斯基，波蘭獨立', 'The Regency Council hands military command to Piłsudski; Polish independence', [('REGIME_PL', S_), ('REGIME_PL_REGENCY', S_)], [], NOSRC)

# ── 主權紀錄定義（優先序引擎）──
TWN = 'WW1 第二批 1914-07-29～1918-11-11'
HAND = '手繪近似線（build/make_requests.py）'
DEFS = []
def d(ph, regime, start, end, geom, rid, prio=0, sev=None, eev=None, layer='de_jure', derived=None, loc=None, zh='', en='', readd=None, label=None, hand=None):
    DEFS.append(dict(ph=ph, regime=regime, start=start, end=end, geom=(g_of(geom) if isinstance(geom, (int, str)) else geom), rid=rid, prio=prio, sev=sev, eev=eev,
                     layer=layer, derived=derived or [rid], loc=loc or OL(rid), zh=zh, en=en, readd=readd, label=label or ph, hand=hand))
def readd(b1ph, end=END, eev=None, zh='', en=''):
    r = B1R[b1ph]; b = r['body']
    d(b1ph + '_R', b['regimeId'][2:-2], b['validPeriod']['start'], end, B1G[r['_geometryFrom']], b['ohmRelationId'], sev=(b['startEventId'] or '')[2:-2] or None,
      eev=eev, layer=b['layerStatus'], readd=b1ph, loc=b['geometryLocator'], zh=zh, en=en)
# 第一批迄於 1914-07-29 的紀錄：先撤後增（延長）；之後的切段由引擎產生新紀錄
NOTES = {
 'SOV_AH': dict(zh='1918-10 起奧匈帝國瓦解中：捷克斯洛伐克（10-28）、斯洛維尼亞人克羅埃西亞人和塞爾維亞人國（10-29）另段；德意志奧地利（10-30／11-12）、匈牙利（10-31／11-16）、西烏克蘭（11-01）與波蘭在加利西亞的接管未分（待查證）。',
                en='Austria-Hungary dissolving from Oct 1918: Czechoslovakia and the SCS State are split; German-Austria, Hungary, West Ukraine and Polish Galicia are not (pending).'),
 'SOV_DE_EMP': dict(zh='1918-11-09 德國革命、宣布共和，本批未改政權（待查證）。', en='The German revolution and proclamation of the republic on 9 Nov 1918 are not modeled (pending).'),
 'SOV_AL_PR': dict(zh='1914-09 維德親王離開後阿爾巴尼亞陷入無政府，1915～1918 年由義、奧匈、法、希、塞、蒙軍分區佔領，未畫（待查證）。', en='Multiple occupations of Albania (1915–1918) are not drawn (pending).'),
 'SOV_MORESNET': dict(zh='1915 年起實際由德國管理（待查證），未改。', en='Administered by Germany from 1915 (pending), not modeled.'),
 'SOV_GR_B': dict(zh='1916-08～1917-06 韋尼澤洛斯國防臨時政府（薩洛尼卡）與雅典政府分裂、協約國佔領未畫（待查證）。', en='The 1916–17 National Schism and Allied occupation are not drawn (pending).'),
}
for p in ['SOV_AH', 'SOV_DE_EMP', 'SOV_IT', 'SOV_FR3', 'SOV_UK_GBI', 'SOV_BE', 'SOV_DK', 'SOV_NO', 'SOV_SE', 'SOV_MORESNET', 'SOV_TN', 'SOV_MR', 'SOV_GR_B', 'SOV_RS_B',
          'SOV_MN_K_B', 'SOV_AL_PR', 'SOV_IT_AEGEAN', 'SOV_LY_TR', 'SOV_LY_CY', 'SOV_ES_B', 'SOV_MA_ES', 'SOV_MA_FR_B']:
    readd(p, **NOTES.get(p, {}))
readd('SOV_RU_EMP', '1917-03-15', 'EV_FEB_REV')
readd('SOV_CY', '1914-11-05', 'EV_CY_ANNEX')
readd('SOV_OT_E', '1918-10-30', 'EV_MUDROS')
readd('SOV_BG_B', '1918-05-07', 'EV_BUCH18')
readd('SOV_RO_B', '1918-05-07', 'EV_BUCH18')
d('SOV_OT_F', 'REGIME_OT', '1918-10-30', END, 'OT_F', 2920989, sev='EV_MUDROS', derived=[2920989, 2848136, 2830316, 2855613], loc=f'{OL(2920989)} − {OL(2848136)} − {OL(2830316)} − {OL(2855613)}',
  zh='穆德羅斯停戰後依 OHM 2920989（協約國佔領伊斯坦堡等不分）。1915～1918 年在阿拉伯半島、美索不達米亞、巴勒斯坦的失地未畫（待查證）。', en='After Mudros per OHM 2920989; wartime losses in Arabia, Mesopotamia and Palestine are not drawn (pending).')
d('SOV_BG_C', 'REGIME_BG', '1918-05-07', END, 'BG_C', 2746680, sev='EV_BUCH18', derived=[2746680, 2693260, 2692219], loc=f'{OL(2746680)} ∪ 南多布羅加（{OL(2693260)} − {OL(2692219)}）',
  zh='布加勒斯特和約（1918）第 10 條得南多布羅加。羅馬尼亞國王未批准；德國停戰協定第 15 條廢除該和約，實際歸還在 1918-11 以後（待查證）。', en='Southern Dobruja gained under the Treaty of Bucharest (1918), art. 10; the treaty was annulled by the armistice (art. 15).')
d('SOV_RO_C', 'REGIME_RO', '1918-05-07', END, 'RO_C', 2693260, sev='EV_BUCH18', derived=[2693260, 2692219], loc=f'{OL(2693260)} − 南多布羅加',
  zh='布加勒斯特和約（1918）後不含南多布羅加；喀爾巴阡山口一帶割給奧匈的邊界調整未畫（待查證）。', en='Without Southern Dobruja; the Carpathian border rectifications in favour of Austria-Hungary are not drawn (pending).')
d('SOV_RU_PROV_A', 'REGIME_RU_PROV', '1917-03-15', '1917-09-14', 2849760, 2849760, sev='EV_FEB_REV', eev='EV_RU_REPUBLIC', zh='沿用帝俄範圍（OHM 2849760），扣掉同期佔領區。', en='Russian Empire extent, minus occupied areas.')
d('SOV_RU_PROV_B', 'REGIME_RU_PROV', '1917-09-14', '1917-11-07', 2869933, 2869933, sev='EV_RU_REPUBLIC', eev='EV_OCT_REV', zh='9 月 14 日宣布共和後依 OHM 2869933（Russian Republic）。', en='Per OHM 2869933 after the proclamation of the republic.')
RSN = '依 OHM 俄羅斯蘇維埃共和國各版本；OHM 2852344 起日 1917-12-06，十月革命到 12-06 之間沿用帝俄範圍（OHM 2849760）。實際控制範圍遠小於此（內戰，待查證）。'
d('SOV_RSFSR_A', 'REGIME_RSFSR', '1917-11-07', '1917-12-06', 2849760, 2849760, sev='EV_OCT_REV', zh=RSN, en='Russian Empire extent until OHM 2852344 starts (6 Dec 1917); actual control far smaller.')
d('SOV_RSFSR_B', 'REGIME_RSFSR', '1917-12-06', '1918-01-24', 2852344, 2852344, zh=RSN, en='Per OHM versions.')
d('SOV_RSFSR_C', 'REGIME_RSFSR', '1918-01-24', '1918-04-22', 2850854, 2850854, zh=RSN, en='Per OHM versions.')
d('SOV_RSFSR_D', 'REGIME_RSFSR', '1918-04-22', '1918-08-31', 2957452, 2957452, zh=RSN, en='Per OHM versions.')
d('SOV_RSFSR_E', 'REGIME_RSFSR', '1918-08-31', '1918-09-12', 2959041, 2959041, zh=RSN, en='Per OHM versions.')
d('SOV_RSFSR_F', 'REGIME_RSFSR', '1918-09-12', END, 2959042, 2959042, zh=RSN, en='Per OHM versions.')
d('SOV_US', 'REGIME_US', START, END, make_valid(shape(US['geometry'])), US['ohmRelationId'], label='美國', loc=US['geometryLocator'], derived=[-1])
# 新國家、併吞（prio 1～2）
d('SOV_CY_ANNEX', 'REGIME_CY_ANNEX', '1914-11-05', END, 2848135, 2848135, prio=1, sev='EV_CY_ANNEX', label='英國併吞的賽普勒斯', zh='OHM 2848135 起日只到年（1914）；本表取 11 月 5 日。1925 年改為直轄殖民地（不在本批）。', en='OHM gives only the year 1914.')
d('SOV_EG', 'REGIME_EG', '1914-12-18', END, 2803205, 2803205, prio=1, sev='EV_EGYPT', label='埃及', zh='英國保護國（1914-12-18 宣言）。OHM 起日 12-19（侯賽因稱蘇丹）。之前埃及在 OHM 無範圍，留白。', en='British protectorate; blank before (no OHM extent).')
d('SOV_FI_A', 'REGIME_FI', '1917-12-06', '1918-08-31', 2696817, 2696817, prio=1, sev='EV_FI_INDEP', label='芬蘭', zh='沿用開發庫既有政權「芬蘭共和國」（1918 年曾選國王，正式共和 1919，待查證）。1918-01～05 芬蘭內戰未分。', en='Uses the existing Republic of Finland regime; the civil war of 1918 is not split.')
d('SOV_FI_B', 'REGIME_FI', '1918-08-31', '1918-09-12', 2959044, 2959044, prio=1, label='芬蘭', zh='OHM 換版。', en='OHM version change.')
d('SOV_FI_C', 'REGIME_FI', '1918-09-12', END, 2959043, 2959043, prio=1, label='芬蘭', zh='OHM 換版。', en='OHM version change.')
d('SOV_UA', 'REGIME_UA_PR', '1918-02-09', END, 2694815, 2694815, prio=2, sev='EV_BREST_UA', label='烏克蘭',
  zh='同盟國依和約承認；1918-03 起德、奧匈軍隊進駐（未設佔領歸屬，待查證），4 月 29 日起為斯科羅帕茨基的烏克蘭國（未分政權，待查證）。', en='Recognized by the Central Powers; German and Austro-Hungarian troops from March 1918 (no occupation attribution, pending); Hetmanate from 29 Apr (not split, pending).')
d('SOV_BY', 'REGIME_BY_PR', '1918-03-25', END, 2957449, 2957449, prio=1, sev='EV_BY_PR', layer='not_sovereign', label='白俄羅斯人民共和國', zh='非主權：德國佔領下宣布獨立，未獲承認。', en='Not sovereign: declared under German occupation, unrecognized.')
d('SOV_LT', 'REGIME_LT_1918', '1918-03-03', END, 2744425, 2744425, prio=1, sev='EV_BREST', layer='not_sovereign', label='立陶宛',
  zh='非主權：德國佔領下。立陶宛理事會 1918-02-16 宣布獨立（待查證），德國 3 月 23 日承認；本表從布列斯特和約起。範圍沿用 OHM 立陶宛行政區（Verwaltungsbezirk Litauen，OHM 迄日 1918-02-16）。', en='Not sovereign: under German occupation; drawn from Brest-Litovsk with the Verwaltungsbezirk Litauen extent.')
d('SOV_BALTIC', 'REGIME_BALTIC_OCC', '1918-03-03', END, 'BALTIC', 2744426, prio=1, sev='EV_BREST', layer='not_sovereign', derived=[2744426, 2869679], loc=f'{OL(2744426)} ∪ {OL(2869679)}', label='庫爾蘭與利沃尼亞',
  zh='非主權：布列斯特和約後德國佔領的庫爾蘭與利沃尼亞（扣掉愛沙尼亞既有紀錄）。波羅的海公國（1918-11-05）與拉脫維亞宣布獨立（11-18）不在本批。', en='Not sovereign: German-occupied Courland and Livonia after Brest-Litovsk (minus the existing Estonia record).')
d('SOV_RO_BESS', 'REGIME_RO', '1918-04-09', END, 2694154, 2694154, prio=3, sev='EV_BESSARABIA', label='比薩拉比亞',
  zh='比薩拉比亞與羅馬尼亞合併（範圍沿用 OHM 比薩拉比亞省 2694154）。合併前的摩爾達維亞民主共和國（1917-12～1918-04）未畫（待查證）。', en='Bessarabia united with Romania (extent of OHM 2694154); the Moldavian Democratic Republic before it is not drawn (pending).')
d('SOV_TC', 'REGIME_TC_COMM', '1917-11-15', '1918-04-22', 2957453, 2957453, prio=1, sev='EV_TC', eev='EV_TDFR', layer='not_sovereign', label='外高加索', zh='非主權：未宣布獨立的地區政府。', en='Not sovereign: regional government without a declaration of independence.')
d('SOV_TDFR_A', 'REGIME_TDFR', '1918-04-22', '1918-05-26', 2957454, 2957454, prio=1, sev='EV_TDFR', eev='EV_GE', label='外高加索')
d('SOV_TDFR_B', 'REGIME_TDFR', '1918-05-26', '1918-05-28', 2957459, 2957459, prio=1, sev='EV_GE', eev='EV_AM_AZ', label='外高加索', zh='喬治亞退出後的殘餘（OHM 2957459）。', en='Rump after Georgia left.')
d('SOV_GE', 'REGIME_GE', '1918-05-26', END, 2698086, 2698086, prio=2, sev='EV_GE', label='喬治亞', zh='1918-06 起德軍進駐（未設佔領歸屬，待查證）。', en='German troops from June 1918 (no attribution, pending).')
d('SOV_AM', 'REGIME_AM', '1918-05-28', END, 2698116, 2698116, prio=1, sev='EV_AM_AZ', label='亞美尼亞', zh='巴統條約（1918-06-04）割地給鄂圖曼未畫（待查證）。', en='Cessions to the Ottomans under the Treaty of Batum are not drawn (pending).')
d('SOV_AZ', 'REGIME_AZ', '1918-05-28', END, 2698117, 2698117, prio=1, sev='EV_AM_AZ', label='亞塞拜然')
d('SOV_MRNC', 'REGIME_MRNC', '1918-05-11', END, 2891769, 2891769, prio=1, sev='EV_MRNC', label='北高加索山地共和國', zh='範圍依 OHM；實際控制有限（待查證）。', en='Extent per OHM; actual control limited (pending).')
d('SOV_CS', 'REGIME_CS', '1918-10-28', END, 2747877, 2747877, prio=1, sev='EV_CS', label='捷克斯洛伐克',
  zh='沿用開發庫既有政權。範圍依 OHM 2747877（起日 11-05）；斯洛伐克到 1919-01 才由捷軍控制（待查證）。', en='Uses the existing regime; extent per OHM 2747877; Slovakia controlled only from Jan 1919 (pending).')
d('SOV_SCS', 'REGIME_SCS', '1918-10-29', END, 2747879, 2747879, prio=1, sev='EV_SCS', layer='not_sovereign', label='斯洛維尼亞人、克羅埃西亞人和塞爾維亞人國',
  zh='非主權：未獲國際承認；11 月起義大利依停戰協定佔領達爾馬提亞等地（未畫，待查證）。12-01 併入塞爾維亞人、克羅埃西亞人和斯洛維尼亞人王國（不在本批）。', en='Not sovereign: unrecognized; Italian occupation under the armistice not drawn (pending).')
d('SOV_PL', 'REGIME_PL', '1918-11-11', END, 2695684, 2695684, prio=3, sev='EV_PL_INDEP', label='波蘭', zh='沿用開發庫既有政權「波蘭共和國」；範圍暫用攝政王國（OHM 2695684），西加利西亞等未畫（待查證）。', en='Uses the existing Polish Republic regime; Regency Kingdom extent for now (pending).')
# 佔領區（prio 1～2）
d('SOV_GG_BE_A', 'REGIME_GG_BE', '1914-08-20', '1914-10-10', 'GG_BE_A', 2797729, prio=1, sev='EV_BRUSSELS', eev='EV_ANTWERP', layer='not_sovereign', label='比利時佔領區',
  derived=[2797729, 2884612, 2951914, 2951908, 2945081, 2945094, 2945074], loc=f'{OL(2797729)} ∩ 列日、那慕爾、盧森堡、布拉班、林堡、埃諾六省（OHM 各省 relation）',
  zh='非主權：德軍佔領的比利時東部、中部六省（近似：以省界代替 8～10 月的運動戰線，待查證）。法蘭德斯兩省與安特衛普省到安特衛普陷落前仍由比軍控制。', en='Not sovereign: six provinces under German occupation (approximation by provincial boundaries, pending).')
d('SOV_GG_BE_B', 'REGIME_GG_BE', '1914-10-10', '1918-11-11', 'GG_BE_B', 2797729, prio=1, sev='EV_ANTWERP', eev='EV_COMPIEGNE', layer='not_sovereign', label='比利時佔領區',
  loc=f'{OL(2797729)} ∩ 伊瑟河—伊珀爾前線以東（{HAND}）', hand='FRONT_1914：' + fmt(FRONT_1914[:4]) + ' …',
  zh='非主權：伊瑟河—伊珀爾前線以東的比利時（近似線，待查證；1914-10 伊瑟河戰役後到 1918-09 大致不變）。法蘭德斯為軍方的作戰／兵站區，此處統一列為德國總督府。', en='Not sovereign: Belgium east of the Yser–Ypres front (approximate line, pending).')
d('SOV_GG_BE_C', 'REGIME_GG_BE', '1918-11-11', END, 'GG_BE_C', 2797729, prio=1, sev='EV_COMPIEGNE', layer='not_sovereign', label='比利時佔領區',
  loc=f'{OL(2797729)} ∩ 停戰線以東（{HAND}）', hand='ARMISTICE_1918：' + fmt(ARMISTICE_1918),
  zh='非主權：停戰當日德軍仍在的比利時（停戰線近似，待查證）；依停戰協定第 2 條 15 日內撤出。', en='Not sovereign: Belgium still held by Germany on armistice day (approximate line, pending).')
d('SOV_NFR_A', 'REGIME_NFR_OCC', '1914-10-13', '1918-11-11', 'NFR_A', 2866012, prio=1, sev='EV_NFR_FRONT', eev='EV_COMPIEGNE', layer='not_sovereign', label='法國北部佔領區',
  loc=f'{OL(2866012)} ∩ 1914 年底西線以北／以東（{HAND}）', hand='FRONT_1914：' + fmt(FRONT_1914),
  zh='非主權：德軍佔領的法國北部（近似：1914 年底穩定下來的西線，待查證）。1917-03 撤到興登堡防線、1918 年春季攻勢與百日攻勢的前線變化未畫。', en='Not sovereign: German-occupied northern France along the stabilized front of late 1914 (approximate, pending); later front changes are not drawn.')
d('SOV_NFR_B', 'REGIME_NFR_OCC', '1918-11-11', END, 'NFR_B', 2866012, prio=1, sev='EV_COMPIEGNE', layer='not_sovereign', label='法國北部佔領區',
  loc=f'{OL(2866012)} ∩ 停戰線以東（{HAND}）', hand='ARMISTICE_1918：' + fmt(ARMISTICE_1918), zh='非主權：停戰當日德軍仍在的法國領土（停戰線近似，待查證）。', en='Not sovereign: French territory still held on armistice day (approximate, pending).')
d('SOV_GG_WARSAW', 'REGIME_GG_WARSAW', '1915-08-05', '1916-11-05', 2695682, 2695682, prio=1, sev='EV_WARSAW', eev='EV_PL_KINGDOM', layer='not_sovereign', label='華沙總督府',
  zh='非主權：德國佔領的俄屬波蘭北部。OHM 起日 1915-10-18（總督府設立），本表從華沙陷落起。', en='Not sovereign: German-occupied northern Russian Poland.')
d('SOV_GG_LUBLIN', 'REGIME_GG_LUBLIN', '1915-08-05', '1916-11-05', 2695683, 2695683, prio=1, sev='EV_WARSAW', eev='EV_PL_KINGDOM', layer='not_sovereign', label='盧布林軍事總督府',
  zh='非主權：奧匈佔領的俄屬波蘭南部。OHM 起日 1915-09-01，本表從華沙陷落起。OHM 外框有約 600 m 缺口，build.py 以直線接合（見 ohm-manifest repair）。', en='Not sovereign: Austro-Hungarian-occupied southern Russian Poland.')
d('SOV_PL_REGENCY', 'REGIME_PL_REGENCY', '1916-11-05', '1918-11-11', 2695684, 2695684, prio=3, sev='EV_PL_KINGDOM', eev='EV_PL_INDEP', layer='not_sovereign', label='波蘭攝政王國',
  zh='非主權：德、奧兩皇宣布的波蘭王國，仍分由德國華沙、奧匈盧布林兩總督府軍事管理（OHM 外框缺口同盧布林）。', en='Not sovereign: proclaimed by the two Emperors, still administered by the two general governments.')
d('SOV_OBER_OST_A', 'REGIME_OBER_OST', '1915-09-19', '1918-03-03', 2696283, 2696283, prio=1, sev='EV_VILNA', eev='EV_BREST', layer='not_sovereign', label='Ober Ost',
  zh='非主權：德軍東方總司令轄區（庫爾蘭、立陶宛、比亞維斯托克—格羅德諾）。1917-09 佔領里加、1918-02 推進到愛沙尼亞與白俄羅斯未畫（待查證）。', en='Not sovereign: Ober Ost (Courland, Lithuania, Białystok–Grodno); later advances are not drawn (pending).')
d('SOV_OBER_OST_B', 'REGIME_OBER_OST', '1918-03-03', END, 2744424, 2744424, prio=1, sev='EV_BREST', layer='not_sovereign', label='Ober Ost',
  zh='布列斯特和約後剩下的比亞維斯托克—格羅德諾行政區（OHM 2744424，迄日 1918-02-16，本表延用）。', en='Remaining Białystok–Grodno district after Brest-Litovsk.')
d('SOV_SERBIA_BG', 'REGIME_SERBIA_BG', '1915-11-28', '1918-09-29', 'SERBIA_BG', 2746681, prio=1, sev='EV_SERBIA_FALL', eev='EV_BG_ARMISTICE', layer='not_sovereign', label='保加利亞佔領的塞爾維亞',
  loc=f'{OL(2746681)} ∩ 北緯 42.35° 以南（馬其頓）＋東經 21.5° 以東、北緯 43.9° 以南（摩拉瓦）（{HAND}）', hand='box(19,40,23.5,42.35) ∪ box(21.5,42.35,23.5,43.9)',
  zh='非主權：保加利亞佔領並併入（馬其頓軍事督察區、摩拉瓦軍事督察區）的塞爾維亞領土；分界為粗略近似（待查證）。', en='Not sovereign: Serbian territory occupied and annexed by Bulgaria; boundary roughly approximated (pending).')
d('SOV_MGG_SERBIA', 'REGIME_MGG_SERBIA', '1915-11-28', '1918-11-03', 'MGG_SERBIA', 2746681, prio=1, sev='EV_SERBIA_FALL', eev='EV_VILLA_GIUSTI', layer='not_sovereign', label='奧匈佔領的塞爾維亞',
  loc=f'{OL(2746681)} − 保加利亞佔領區（{HAND}）', hand='同保加利亞佔領區',
  zh='非主權：奧匈塞爾維亞軍事總督府（1916-01-01 設立）。1918-09～11 塞軍反攻、11-01 收復貝爾格勒的逐步解放未畫（待查證）。', en='Not sovereign: Austro-Hungarian Military General Government of Serbia; the gradual liberation in autumn 1918 is not drawn (pending).')
d('SOV_MGG_MN', 'REGIME_MGG_MN', '1916-01-13', '1918-11-03', 2739656, 2739656, prio=1, sev='EV_MN_OCC', eev='EV_VILLA_GIUSTI', layer='not_sovereign', label='奧匈佔領的蒙特內哥羅',
  zh='非主權：奧匈蒙特內哥羅軍事總督府（整個蒙特內哥羅）。', en='Not sovereign: Austro-Hungarian Military General Government of Montenegro.')
d('SOV_DOB_A', 'REGIME_DOBRUJA', '1916-10-22', '1918-05-07', 'DOB', 2693260, prio=1, sev='EV_DOBRUJA_OCC', eev='EV_BUCH18', layer='not_sovereign', label='多布羅加佔領區',
  derived=[2693260, 2692219], loc=f'南多布羅加（{OL(2693260)} − {OL(2692219)}）∪ 北多布羅加（{OL(2692219)} ∩ 多瑙河以東，{HAND}）', hand='P_NDOB：' + fmt(list(P_NDOB.exterior.coords)[:-1]),
  zh='非主權：保、德（及鄂圖曼）軍佔領的多布羅加；北部三角洲 1917-01 才全部佔領（未分，待查證）。', en='Not sovereign: Dobruja occupied by Bulgarian, German (and Ottoman) troops.')
d('SOV_DOB_B', 'REGIME_DOBRUJA', '1918-05-07', END, 'NDOB', 2692219, prio=1, sev='EV_BUCH18', layer='not_sovereign', label='多布羅加佔領區',
  loc=f'{OL(2692219)} ∩ 多瑙河以東（{HAND}）', hand='P_NDOB', zh='非主權：布加勒斯特和約（1918）第 10 條，北多布羅加歸同盟國共管。', en='Not sovereign: Northern Dobruja under Central Powers condominium (Bucharest 1918, art. 10).')
d('SOV_RO_WAL', 'REGIME_RO_MILVERW', '1916-12-06', END, 'RO_WAL', 2693260, prio=1, sev='EV_BUCHAREST_FALL', layer='not_sovereign', label='羅馬尼亞佔領區',
  loc=f'{OL(2693260)} − 未佔領的摩爾達維亞（{HAND}）− 多布羅加', hand='P_MOLD：' + fmt(list(P_MOLD.exterior.coords)[:-1]),
  zh='非主權：德軍羅馬尼亞軍政府（瓦拉幾亞與摩爾達維亞南部；1917 年初穩定於錫雷特河—奧伊圖茲一線，近似，待查證）。1918-11 德軍撤出前一直佔領。', en='Not sovereign: German military administration in Romania (Wallachia and southern Moldavia; approximate line, pending).')

# 開發庫既有紀錄（prio 9，不送出，只扣除與 QA）
FIXED = [dict(ph=f"DB:{r['slug']}", geom=make_valid(shape(r['geometry'])), start=r['start'], end=r['end'] or '9999-12-31', prio=9, label=r['slug'], sev=None, eev=None, derived=[])
         for r in ROWS if r['start'] < END and (r['end'] or '9999') > START]

# ── 引擎 ──
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
    def cut_event(c, which):
        # 切點：某較高優先紀錄在 c 開始（用其起事件）或結束（用其迄事件）
        for h in higher:
            if h['start'] == c and h.get('sev'): return h['sev']
            if h['end'] == c and h.get('eev'): return h['eev']
        return None
    keep = [p for p in pieces if p['g'].area >= max(1e-4, 0.002 * x['geom'].area) or not p['act']]
    for i, p in enumerate(pieces):
        if p not in keep: continue
        sev = x['sev'] if p['a'] == x['start'] else cut_event(p['a'], 'start')
        eev = x['eev'] if p['b'] == x['end'] else cut_event(p['b'], 'end')
        base = x['ph'][:-2] if x['readd'] else x['ph']   # 重送段 SOV_AH_R；之後的切段 SOV_AH_2、SOV_AH_3…
        ph = x['ph'] if len(pieces) == 1 or (i == 0 and x['readd']) else f"{base}_{i + 1}"
        SEGS.append(dict(x=x, ph=ph, start=p['a'], end=p['b'], g=p['g'], act=p['act'], sev=sev, eev=eev, readd=(x['readd'] if i == 0 and not p['act'] else None)))
        if i == 0 and x['readd']: assert not p['act'], x['ph']

# 同一政權同期只能有一筆主權紀錄（API 409 CONFLICTING_OFFICIAL_VERSION）：比薩拉比亞（prio 3，用來扣掉烏克蘭）併入同期羅馬尼亞各段
def fold(extra_ph):
    ex = [s for s in SEGS if s['ph'] == extra_ph]; assert len(ex) == 1, extra_ph; e = ex[0]; SEGS.remove(e)
    reg = e['x']['regime']
    for s in sorted([s for s in SEGS if s['x']['regime'] == reg and s['start'] < e['end'] and e['start'] < s['end']], key=lambda s: s['start']):
        assert not s['readd'], s['ph']
        if s['start'] < e['start']:          # 前段保留原狀，截在合併起日；後段另起一筆
            tail = dict(s, start=e['start'], sev=e['sev'], ph=None); s['end'] = e['start']; s['eev'] = e['sev']; s = tail
            base = s['x']['ph'][:-2] if s['x']['readd'] else s['x']['ph']; n = 2
            while any(t['ph'] == f'{base}_{n}' for t in SEGS): n += 1
            s['ph'] = f'{base}_{n}'; SEGS.append(s)
        assert s['end'] <= e['end'], s['ph']
        s['g'] = clean(unary_union([s['g'], e['g']])); s['extra'] = s.get('extra', []) + [e['x']]
fold('SOV_RO_BESS')
SEGS.sort(key=lambda s: (s['x']['regime'], s['start']))

def lic(rids):
    rids = [r for r in rids if r in MAN]
    cc_by = any(MAN[r]['geometry_license'] == 'cc_by' for r in rids)
    attrs = sorted({a for r in rids for a in (MAN[r]['attribution'] or '').split('; ') if a})
    return ('cc_by' if cc_by else 'cc0'), ('; '.join(attrs) or None), sum(MAN[r]['osm_derived_way_count'] for r in rids)
GEOM = {}
def ref(e): return ('{{%s}}' % e) if e else None
def endnote(end):
    return ('到 1918-11-11（本批試驗期間終點，無迄事件）。', ' Until 11 Nov 1918 (end of this batch).') if end == END else ('', '')
retracted = []
for s in SEGS:
    x = s['x']; GEOM[s['ph']] = s['g']
    if s['readd']:
        r = copy.deepcopy(B1R[s['readd']]); b = r['body']
        b['validPeriod']['end'] = s['end']; b['endEventId'] = ref(s['eev'])
        zh, en = (b['note']['zh-Hant'], b['note']['en']) if b['note'] else ('', '')
        zh = zh.replace('到 1914-07-28（本批試驗期間終點，無迄事件）。', '') + x['zh']; en = (en.replace(' Until 28 Jul 1914 (end of this batch).', '') + ' ' + x['en']).strip()
        ez, ee = endnote(s['end'])
        b['note'] = {'zh-Hant': (zh + ez).strip(), 'en': (en + ee).strip()} if (zh + ez).strip() else None
        b['provenance']['trialWindow'] = 'WW1 第一、二批 1908-10-06～1918-11-11'; b['provenance']['replaces'] = '{{%s}}' % s['readd']
        add('04-retract', s['readd'].lower(), f"RETRACTED_{s['readd']}", '/api/v1/sovereignty-records/{{%s}}/retraction' % s['readd'],
            {'reason': f"WW1 第二批：第一批截在 1914-07-29（試驗期間終點），延長到 {s['end']}（{s['eev'] or '本批終點'}）後重送"}, {'fix': True}, sub='sub1')
        add('05-sovereignty', s['ph'].lower(), s['ph'], '/api/v1/sovereignty-records', b, {'replaces': s['readd']}, geom=s['ph'], sub='sub1')
        retracted.append(s['readd']); continue
    if x['ph'] == 'SOV_US':
        b = {'regimeId': '{{REGIME_US}}', 'geometry': None, 'validPeriod': {'start': s['start'], 'end': s['end']}, 'layerStatus': 'de_jure', 'geometrySourceId': '{{SRC_OHM_US}}',
             'geometryLocator': US['geometryLocator'], 'geometryLicense': US['geometryLicense'], 'attribution': US['attribution'], 'startEventId': None, 'endEventId': None,
             'ohmRelationId': US['ohmRelationId'], 'ohmVersion': US['ohmVersion'], 'ohmFetchedAt': US['ohmFetchedAt'], 'ohmStartRaw': US['ohmStartRaw'], 'ohmEndRaw': US['ohmEndRaw'],
             'provenance': {**copy.deepcopy(US['provenance']), 'trialWindow': TWN, 'copiedFrom': US['id']},
             'note': {'zh-Hant': '起於 1914-07-29（本批試驗期間起點）。幾何照抄開發庫 1937 年起的美國紀錄（OHM 2874803 v33 − 2889834），1914～1918 年的差異（如 1917-03-31 購入維京群島）未處理（待查證）；主要給衝突弧線用。' + endnote(s['end'])[0],
                      'en': 'From 29 Jul 1914 (start of this batch). Geometry copied from the 1937 US record; 1914–1918 differences not handled (pending).' + endnote(s['end'])[1]}}
        add('05-sovereignty', 'sov_us', 'SOV_US', '/api/v1/sovereignty-records', b, None, geom='SOV_US'); continue
    EX = s.get('extra', [])
    derived = list(dict.fromkeys(x['derived'] + [r for h in s['act'] for r in h.get('derived', [])] + [r for e in EX for r in e['derived']]))
    loc = x['loc'] + ''.join(f" − {lb}" for lb in dict.fromkeys(h['label'] for h in s['act'])) + ''.join(f" ∪ {e['label']}（{e['loc']}）" for e in EX)
    gl, attr, osm = lic(derived); m = MAN[x['rid']]
    zh = x['zh'] + (('扣掉同期：' + '、'.join(dict.fromkeys(h['label'] for h in s['act'])) + '。') if s['act'] else '')
    en = x['en'] + ((' Minus: ' + ', '.join(dict.fromkeys(h['label'] if h['ph'].startswith('DB:') else h['ph'] for h in s['act'])) + '.') if s['act'] else '')
    for e in EX: zh += e['zh']; en = (en + ' ' + e['en']).strip()
    if s['start'] == START and not s['sev']: zh = '起於 1914-07-29（本批試驗期間起點）。' + zh; en = 'From 29 Jul 1914 (start of this batch). ' + en
    ez, ee = endnote(s['end'])
    b = {'regimeId': '{{%s}}' % x['regime'], 'geometry': None, 'validPeriod': {'start': s['start'], 'end': s['end']}, 'layerStatus': x['layer'],
         'geometrySourceId': '{{SRC_OHM_WW1B}}', 'geometryLocator': loc, 'geometryLicense': gl, 'attribution': attr, 'startEventId': ref(s['sev']), 'endEventId': ref(s['eev']),
         'ohmRelationId': x['rid'], 'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'], 'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date'],
         'provenance': {'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': osm, 'ohmFixme': m['fixme'], 'ohmRelationSource': m['relation_source'],
                        'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'], 'ohmTimestamp': m['ohm_timestamp'], 'coastline': '{{SRC_NE_LAND}}',
                        'licenseReview': 'osm_derived_ways' if osm else None, 'trialWindow': TWN},
         'note': {'zh-Hant': (zh + ez).strip(), 'en': (en + ee).strip()} if (zh + ez).strip() else None}
    if len(derived) > 1 or x['hand']: b['provenance'].update({'derivedFrom': [OL(r) for r in derived if r in MAN], 'derivation': loc})
    if x['hand']: b['provenance']['handDrawn'] = x['hand'] + '（近似，待查證）'
    if m.get('repair'): b['provenance']['ohmRepair'] = m['repair']
    add('05-sovereignty', s['ph'].lower(), s['ph'], '/api/v1/sovereignty-records', b, None, geom=s['ph'])

# ── 佔領歸屬 ──
def occ(ph, occd, occr, kind, start, end, basis, co, zh, en):
    add('06-occupation', ph.lower(), ph, '/api/v1/occupation-attributions', {'occupiedRegimeId': '{{%s}}' % occd, 'occupierRegimeId': '{{%s}}' % occr, 'controlKind': kind,
        'validPeriod': {'start': start, 'end': end}, 'basisEventId': ref(basis), 'coOccupied': co, 'note': {'zh-Hant': zh, 'en': en}})
r = copy.deepcopy(B1R['OCC_IT_AEGEAN']); r['body']['validPeriod']['end'] = END
r['body']['note'] = {'zh-Hant': '義大利軍事佔領多德卡尼斯（起日依 OHM，待查證）。到 1918-11-11（本批試驗期間終點）。', 'en': 'Italian military occupation of the Dodecanese (start per OHM, pending). Until 11 Nov 1918 (end of this batch).'}
add('04-retract', 'occ_it_aegean', 'RETRACTED_OCC_IT_AEGEAN', '/api/v1/occupation-attributions/{{OCC_IT_AEGEAN}}/retraction', {'reason': 'WW1 第二批：第一批截在 1914-07-29，延長到 1918-11-12 後重送'}, {'fix': True}, sub='sub1')
add('06-occupation', 'occ_it_aegean_r', 'OCC_IT_AEGEAN_R', '/api/v1/occupation-attributions', r['body'], {'replaces': 'OCC_IT_AEGEAN'}, sub='sub1')
TE = '到 1918-11-11（本批試驗期間終點）。'
occ('OCC_LU', 'REGIME_LU', 'REGIME_DE_EMP', 'military_administration', '1914-08-02', END, 'EV_LUX_OCC', False, '德軍佔領盧森堡（大公國政府照常運作，近似列為軍事管理，待查證）。' + TE, 'German military occupation of Luxembourg (the grand-ducal government continued; pending).')
occ('OCC_GG_BE', 'REGIME_GG_BE', 'REGIME_DE_EMP', 'civil_administration', '1914-08-20', END, 'EV_BRUSSELS', False, '德國比利時總督府（1914-08-26 設立；法蘭德斯作戰／兵站區由軍方管理，未分）。' + TE, 'German General Government of Belgium (military zones in Flanders not split).')
occ('OCC_NFR', 'REGIME_NFR_OCC', 'REGIME_DE_EMP', 'military_administration', '1914-10-13', END, 'EV_NFR_FRONT', False, '德軍兵站區軍事管理。' + TE, 'German military (Etappen) administration.')
occ('OCC_GG_WARSAW', 'REGIME_GG_WARSAW', 'REGIME_DE_EMP', 'civil_administration', '1915-08-05', '1916-11-05', 'EV_WARSAW', False, '德國華沙總督府。', 'German General Government of Warsaw.')
occ('OCC_GG_LUBLIN', 'REGIME_GG_LUBLIN', 'REGIME_AH', 'military_administration', '1915-08-05', '1916-11-05', 'EV_WARSAW', False, '奧匈盧布林軍事總督府。', 'Austro-Hungarian Military General Government of Lublin.')
occ('OCC_PL_REGENCY', 'REGIME_PL_REGENCY', 'REGIME_DE_EMP', 'civil_administration', '1916-11-05', '1918-11-11', 'EV_PL_KINGDOM', True, '德、奧匈共同佔領：北部德國華沙總督府、南部奧匈盧布林軍事總督府（一個政權只能有一筆同期歸屬，列德國為佔領方並標共同佔領）。', 'Joint German and Austro-Hungarian occupation (Warsaw and Lublin general governments).')
occ('OCC_OBER_OST', 'REGIME_OBER_OST', 'REGIME_DE_EMP', 'military_administration', '1915-09-19', END, 'EV_VILNA', False, '德軍東方總司令部軍事管理。' + TE, 'German military administration (Ober Ost).')
occ('OCC_LT_1918', 'REGIME_LT_1918', 'REGIME_DE_EMP', 'military_administration', '1918-03-03', END, 'EV_BREST', False, '布列斯特和約後仍由德軍管理。' + TE, 'Still under German military administration after Brest-Litovsk.')
occ('OCC_BALTIC', 'REGIME_BALTIC_OCC', 'REGIME_DE_EMP', 'military_administration', '1918-03-03', END, 'EV_BREST', False, '德軍軍事管理。' + TE, 'German military administration.')
occ('OCC_EE', 'REGIME_EE', 'REGIME_DE_EMP', 'military_administration', '1918-02-24', END, 'EV_EE_OCC', False, '德軍佔領愛沙尼亞（1918-11-19 移交臨時政府，不在本批）。' + TE, 'German occupation of Estonia (handover on 19 Nov 1918 not in this batch).')
occ('OCC_BY', 'REGIME_BY_PR', 'REGIME_DE_EMP', 'military_administration', '1918-03-25', END, 'EV_BY_PR', False, '德軍佔領下（明斯克 1918-02-21 起，待查證）。' + TE, 'Under German occupation (pending).')
occ('OCC_SERBIA_BG', 'REGIME_SERBIA_BG', 'REGIME_BG', 'annexed', '1915-11-28', '1918-09-29', 'EV_SERBIA_FALL', False, '保加利亞事實上併入（馬其頓、摩拉瓦軍事督察區）。', 'De facto annexed by Bulgaria.')
occ('OCC_MGG_SERBIA', 'REGIME_MGG_SERBIA', 'REGIME_AH', 'military_administration', '1915-11-28', '1918-11-03', 'EV_SERBIA_FALL', False, '奧匈塞爾維亞軍事總督府（1916-01-01 設立）。', 'Austro-Hungarian Military General Government of Serbia.')
occ('OCC_MGG_MN', 'REGIME_MGG_MN', 'REGIME_AH', 'military_administration', '1916-01-13', '1918-11-03', 'EV_MN_OCC', False, '奧匈蒙特內哥羅軍事總督府。', 'Austro-Hungarian Military General Government of Montenegro.')
occ('OCC_DOBRUJA', 'REGIME_DOBRUJA', 'REGIME_BG', 'military_administration', '1916-10-22', END, 'EV_DOBRUJA_OCC', True, '保加利亞與德國（及鄂圖曼）共同佔領；1918-05-07 起北多布羅加為同盟國共管。' + TE, 'Joint Bulgarian–German (and Ottoman) occupation; condominium in Northern Dobruja from 7 May 1918.')
occ('OCC_RO_WAL', 'REGIME_RO_MILVERW', 'REGIME_DE_EMP', 'military_administration', '1916-12-06', END, 'EV_BUCHAREST_FALL', True, '德軍軍政府，奧匈、保加利亞、鄂圖曼部隊參與（共同佔領）。' + TE, 'German military administration with Austro-Hungarian, Bulgarian and Ottoman participation.')

# ── 衝突 ──
def at(regime, day):
    gs = [GEOM[s['ph']] for s in SEGS if s['x']['regime'] == regime and s['start'] <= day < s['end']]
    return unary_union(gs) if gs else None
def border_mid(a, b):
    if a is None or b is None: return None
    line = a.boundary.intersection(b.buffer(0.02))
    parts = [g for g in getattr(line, 'geoms', [line]) if isinstance(g, (LineString, MultiLineString)) and not g.is_empty]
    if not parts: return None
    u = unary_union(parts); m = linemerge(u) if isinstance(u, MultiLineString) else u; segs = list(getattr(m, 'geoms', [m]))
    best = max(segs, key=lambda s: s.length)
    if best.length < 0.05: return None
    p = best.interpolate(0.5, normalized=True); return [round(p.x, 4), round(p.y, 4)]
YPRES = ([2.885, 50.85], '伊珀爾（英軍西線主要戰區，固定點）')
GALLI = ([26.4, 40.2], '加里波利（協約國登陸地，固定點；巴勒斯坦、美索不達米亞戰線未另立）')
SALON = ([22.5, 41.1], '薩洛尼卡戰線（馬其頓前線，固定點）')
TRIPOLI = ([13.19, 32.89], '的黎波里（義軍在利比亞與賽努西部落及鄂圖曼作戰，固定點）')
CAPOR = ([13.55, 46.25], '卡波雷托（1917-10 德奧聯軍突破處，固定點）')
LYS = ([2.75, 50.62], '利斯河（1918-04 葡萄牙軍在此作戰，固定點）')
WFRONT = ([5.7, 48.9], '聖米耶勒（1918-09 美軍首次獨立攻勢，固定點）')
VV = ([12.3, 45.98], '維托里奧威尼托（1918-10 美軍第 332 團參戰，固定點）')
DOBR = ([28.3, 44.2], '多布羅加（1916 年戰區，固定點）')
OTRANTO = ([18.5, 40.2], '奧特朗托海峽（協約國封鎖亞得里亞海，固定點）')
ARGES = ([25.6, 44.6], '阿爾傑什河（1916-12 布加勒斯特戰役，固定點）')
RIGA = ([24.0, 56.8], '里加—德維納河前線（固定點）')
FOCSANI = ([27.2, 45.7], '福克沙尼—錫雷特河前線（俄、羅軍與同盟國，固定點）')
def sh(p, dx, dy): return ([round(p[0][0] + dx, 4), round(p[0][1] + dy, 4)], p[1])
CF = [('CF_DE_RU', 'REGIME_DE_EMP', 'REGIME_RU_EMP', 'EV_DE_RU_WAR', 'EV_FEB_REV', None),
      ('CF_DE_FR', 'REGIME_DE_EMP', 'REGIME_FR3', 'EV_DE_FR_WAR', 'EV_COMPIEGNE', None),
      ('CF_DE_BE', 'REGIME_DE_EMP', 'REGIME_BE', 'EV_DE_BE_INV', 'EV_COMPIEGNE', None),
      ('CF_UK_DE', 'REGIME_UK_GBI', 'REGIME_DE_EMP', 'EV_UK_DE_WAR', 'EV_COMPIEGNE', YPRES),
      ('CF_AH_RU', 'REGIME_AH', 'REGIME_RU_EMP', 'EV_AH_RU_WAR', 'EV_FEB_REV', None),
      ('CF_AH_MN', 'REGIME_AH', 'REGIME_MN_K', 'EV_AH_MN_WAR', 'EV_VILLA_GIUSTI', None),
      ('CF_FR_AH', 'REGIME_FR3', 'REGIME_AH', 'EV_FR_AH_WAR', 'EV_VILLA_GIUSTI', OTRANTO),
      ('CF_UK_AH', 'REGIME_UK_GBI', 'REGIME_AH', 'EV_UK_AH_WAR', 'EV_VILLA_GIUSTI', sh(OTRANTO, 0.15, -0.15)),
      ('CF_OT_RU', 'REGIME_OT', 'REGIME_RU_EMP', 'EV_OT_ENTRY', 'EV_FEB_REV', None),
      ('CF_UK_OT', 'REGIME_UK_GBI', 'REGIME_OT', 'EV_ENTENTE_OT_WAR', 'EV_MUDROS', GALLI),
      ('CF_FR_OT', 'REGIME_FR3', 'REGIME_OT', 'EV_ENTENTE_OT_WAR', 'EV_MUDROS', sh(GALLI, -0.1, -0.1)),
      ('CF_IT_AH', 'REGIME_IT', 'REGIME_AH', 'EV_IT_AH_WAR', 'EV_VILLA_GIUSTI', None),
      ('CF_IT_OT', 'REGIME_IT', 'REGIME_OT', 'EV_IT_OT_WAR', 'EV_MUDROS', TRIPOLI),
      ('CF_BG_RS', 'REGIME_BG', 'REGIME_RS', 'EV_BG_RS_WAR', 'EV_BG_ARMISTICE', None),
      ('CF_UK_BG', 'REGIME_UK_GBI', 'REGIME_BG', 'EV_ENTENTE_BG_WAR', 'EV_BG_ARMISTICE', SALON),
      ('CF_FR_BG', 'REGIME_FR3', 'REGIME_BG', 'EV_ENTENTE_BG_WAR', 'EV_BG_ARMISTICE', sh(SALON, -0.3, 0.05)),
      ('CF_IT_BG', 'REGIME_IT', 'REGIME_BG', 'EV_ENTENTE_BG_WAR', 'EV_BG_ARMISTICE', sh(SALON, -0.9, -0.05)),
      ('CF_RU_BG', 'REGIME_RU_EMP', 'REGIME_BG', 'EV_ENTENTE_BG_WAR', 'EV_FEB_REV', DOBR),
      ('CF_DE_PT', 'REGIME_DE_EMP', 'REGIME_PT', 'EV_DE_PT_WAR', 'EV_COMPIEGNE', LYS),
      ('CF_RO_AH', 'REGIME_RO', 'REGIME_AH', 'EV_RO_ENTRY', 'EV_BUCH18', None),
      ('CF_RO_DE', 'REGIME_RO', 'REGIME_DE_EMP', 'EV_CP_RO_WAR', 'EV_BUCH18', ARGES),
      ('CF_RO_BG', 'REGIME_RO', 'REGIME_BG', 'EV_CP_RO_WAR', 'EV_BUCH18', None),
      ('CF_RO_OT', 'REGIME_RO', 'REGIME_OT', 'EV_CP_RO_WAR', 'EV_BUCH18', sh(DOBR, 0.15, 0.15)),
      ('CF_IT_DE', 'REGIME_IT', 'REGIME_DE_EMP', 'EV_IT_DE_WAR', 'EV_COMPIEGNE', CAPOR),
      ('CF_US_DE', 'REGIME_US', 'REGIME_DE_EMP', 'EV_US_DE_WAR', 'EV_COMPIEGNE', WFRONT),
      ('CF_GR_BG', 'REGIME_GR', 'REGIME_BG', 'EV_GR_WAR', 'EV_BG_ARMISTICE', None),
      ('CF_GR_DE', 'REGIME_GR', 'REGIME_DE_EMP', 'EV_GR_WAR', 'EV_COMPIEGNE', sh(SALON, 0.3, -0.05)),
      ('CF_US_AH', 'REGIME_US', 'REGIME_AH', 'EV_US_AH_WAR', 'EV_VILLA_GIUSTI', VV),
      ('CF_RUP_DE', 'REGIME_RU_PROV', 'REGIME_DE_EMP', 'EV_FEB_REV', 'EV_OCT_REV', RIGA),
      ('CF_RUP_AH', 'REGIME_RU_PROV', 'REGIME_AH', 'EV_FEB_REV', 'EV_OCT_REV', None),
      ('CF_RUP_OT', 'REGIME_RU_PROV', 'REGIME_OT', 'EV_FEB_REV', 'EV_OCT_REV', None),
      ('CF_RUP_BG', 'REGIME_RU_PROV', 'REGIME_BG', 'EV_FEB_REV', 'EV_OCT_REV', FOCSANI),
      ('CF_RSFSR_DE', 'REGIME_RSFSR', 'REGIME_DE_EMP', 'EV_OCT_REV', 'EV_BREST', sh(RIGA, 0.3, 0.1)),
      ('CF_RSFSR_AH', 'REGIME_RSFSR', 'REGIME_AH', 'EV_OCT_REV', 'EV_BREST', None),
      ('CF_RSFSR_OT', 'REGIME_RSFSR', 'REGIME_OT', 'EV_OCT_REV', 'EV_BREST', None),
      ('CF_RSFSR_BG', 'REGIME_RSFSR', 'REGIME_BG', 'EV_OCT_REV', 'EV_BREST', sh(FOCSANI, 0.15, 0.1))]
FALLBACK_AUTO = {'CF_RUP_AH': ([25.6, 49.55], '塔爾諾波爾—加利西亞前線（兩國當日無共同邊界，固定點）'), 'CF_RSFSR_AH': ([25.75, 49.45], '塔爾諾波爾—加利西亞前線（固定點）'),
                 'CF_RUP_OT': ([41.3, 39.9], '埃爾祖魯姆—高加索前線（固定點）'), 'CF_RSFSR_OT': ([41.45, 39.8], '埃爾祖魯姆—高加索前線（固定點）'),
                 'CF_AH_MN': ([18.75, 42.75], '赫塞哥維納—蒙特內哥羅邊界（固定點）'), 'CF_RO_BG': ([27.0, 44.0], '多瑙河—南多布羅加（圖爾圖卡亞，固定點）')}
cf_qa = {}
for ph, a, b_, sev, eev, fb in CF:
    day = EVD[sev]
    pt = None if fb else border_mid(at(a, day), at(b_, day))
    if pt: method = f'本批主權紀錄在開戰日 {day} 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid）'
    else:
        fb = fb or FALLBACK_AUTO.get(ph)
        assert fb, f'{ph}: 無共同邊界也沒有固定點'
        pt, method = fb
    cf_qa[ph] = pt
    add('07-conflict', ph.lower(), ph, '/api/v1/conflict-records', {'regimeAId': '{{%s}}' % a, 'regimeBId': '{{%s}}' % b_, 'startEventId': '{{%s}}' % sev,
        'endEventId': '{{%s}}' % eev, 'location': {'type': 'Point', 'coordinates': pt}, 'locationMethod': method})
r = copy.deepcopy(B1R['CF_AH_RS']); r['body']['endEventId'] = '{{EV_VILLA_GIUSTI}}'
add('04-retract', 'cf_ah_rs', 'RETRACTED_CF_AH_RS', '/api/v1/conflict-records/{{CF_AH_RS}}/retraction', {'reason': 'WW1 第二批：補迄事件（朱斯蒂別墅停戰）後重送'}, {'fix': True}, sub='sub1')
add('07-conflict', 'cf_ah_rs_r', 'CF_AH_RS_R', '/api/v1/conflict-records', r['body'], {'replaces': 'CF_AH_RS'}, sub='sub1')

# ── 子批分配：紀錄依起日；定義（來源、政權、事件）放在第一個引用它的子批 ──
def sub_of(day):
    for n, a, b in SUBS:
        if a <= day < b: return n
    return SUBS[0][0] if day < START else SUBS[-1][0]
order = [n for n, _, _ in SUBS]
for rq in REQ:
    b = rq['body']
    if rq['sub'] is None and rq['cat'] in ('05-sovereignty', '06-occupation'): rq['sub'] = sub_of(b['validPeriod']['start'])
    elif rq['sub'] is None and rq['cat'] == '07-conflict': rq['sub'] = sub_of(EVD[b['startEventId'][2:-2]])
    elif rq['sub'] is None and rq['cat'] == '03-event': rq['sub'] = sub_of(EVD[rq['ph']])
byph = {rq['ph']: rq for rq in REQ}
changed = True
while changed:  # 引用者在較早子批 → 被引用的定義提前
    changed = False
    for rq in REQ:
        if rq['sub'] is None: continue
        for m in re.findall(r'\{\{(\w+)\}\}', json.dumps(rq['body'], ensure_ascii=False) + rq['post']):
            t = byph.get(m)
            if t is None or t['cat'] == '04-retract': continue
            if t['sub'] is None or order.index(t['sub']) > order.index(rq['sub']):
                t['sub'] = rq['sub']; changed = True
unused = [rq['ph'] for rq in REQ if rq['sub'] is None]
assert not unused, unused
for n in order:
    os.makedirs(os.path.join(ROOT, 'requests', n), exist_ok=True)
    for f in os.listdir(os.path.join(ROOT, 'requests', n)):
        if f.endswith('.json'): os.remove(os.path.join(ROOT, 'requests', n, f))
counter = {}
for rq in REQ:
    k = (rq['sub'], rq['cat']); counter[k] = counter.get(k, 0) + 1
    req = {'_placeholder': rq['ph'], '_post': rq['post'], **({'_geometryFrom': rq['geom']} if rq['geom'] else {}), **({'_meta': rq['meta']} if rq['meta'] else {}), 'body': rq['body']}
    with open(os.path.join(ROOT, 'requests', rq['sub'], f"{rq['cat']}-{counter[k]:02d}-{rq['name']}.json"), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')

# ── QA：抽樣日互不重疊（本批紀錄＋開發庫既有紀錄）、涵蓋面積 ──
items_all = [(s['ph'], s['g'], s['start'], s['end']) for s in SEGS if s['ph'] != 'SOV_US'] + [(f['ph'], f['geom'], f['start'], f['end']) for f in FIXED]
DAYS = ['1914-07-29', '1914-08-21', '1914-10-11', '1914-10-14', '1914-11-06', '1914-12-19', '1915-06-01', '1915-08-06', '1915-09-20', '1915-11-29', '1916-01-14',
        '1916-10-23', '1916-11-06', '1916-12-01', '1916-12-07', '1917-03-16', '1917-09-15', '1917-11-08', '1917-11-16', '1917-12-07', '1918-01-25', '1918-02-10',
        '1918-02-25', '1918-03-04', '1918-03-26', '1918-04-10', '1918-04-23', '1918-05-08', '1918-05-12', '1918-05-27', '1918-05-29', '1918-09-01', '1918-09-13',
        '1918-09-30', '1918-10-29', '1918-10-30', '1918-10-31', '1918-11-04', '1918-11-11']
qa = {'overlaps': {}, 'coverage_deg2': {}, 'conflictLocations': cf_qa, 'records': {}}
for day in DAYS:
    items = [(k, g) for k, g, s0, e0 in items_all if s0 <= day < e0]
    tree = STRtree([g for _, g in items]); worst = []
    for i_, (ni, gi) in enumerate(items):
        for j in tree.query(gi):
            if j <= i_: continue
            a = gi.intersection(items[j][1]).area
            if a > 1e-3: worst.append((ni, items[j][0], round(a, 4)))
    qa['overlaps'][day] = worst
    qa['coverage_deg2'][day] = round(unary_union([g for _, g in items]).area, 2)
for s in SEGS:
    qa['records'][s['ph']] = {'period': [s['start'], s['end']], 'area': round(s['g'].area, 3), 'sev': s['sev'], 'eev': s['eev'], 'minus': [h['ph'] for h in s['act']]}
qa['retractedFromBatch1'] = retracted + ['OCC_IT_AEGEAN', 'CF_AH_RS']
qa['requestCounts'] = {n: sum(1 for rq in REQ if rq['sub'] == n) for n in order}
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in GEOM.items()]},
          open(os.path.join(ROOT, 'ww1-1914-1918-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(qa, open(os.path.join(ROOT, 'qa.json'), 'w'), indent=1, ensure_ascii=False)
bad = [(day, w) for day in DAYS for w in qa['overlaps'][day]]
print('requests', qa['requestCounts'], 'segments', len(SEGS))
print('coverage', qa['coverage_deg2'])
for day, w in bad: print('OVERLAP', day, w)
if '--strict' in sys.argv: assert not bad
