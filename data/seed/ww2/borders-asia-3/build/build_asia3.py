#!/usr/bin/env python3
"""亞洲第三批：南亞、阿拉伯半島、英屬婆羅洲、帝汶、新幾內亞與澳洲、澳門與廣州灣 1937-07-07～1945-09-02（填補亞洲與太平洋空白）。
新政權：英屬印度（含土邦，OHM 未分）、錫蘭、馬爾地夫、尼泊爾、不丹、阿富汗、法屬印度、葡屬印度、沙烏地阿拉伯、葉門、亞丁殖民地與保護地、
馬斯喀特與阿曼（含瓜達爾）、特魯西爾諸國、卡達、巴林、科威特、砂拉越、汶萊、北婆羅洲、葡屬帝汶、澳大利亞、巴布亞、新幾內亞、英屬索羅門群島、
葡屬澳門、廣州灣，與日本佔領區（安達曼與尼科巴、英屬婆羅洲、葡屬帝汶、新不列顛與新愛爾蘭、廣州灣）。
既有中華民國三筆紀錄先撤後增扣掉廣州灣；泰英交戰先撤後增，改用開戰地點（泰緬邊境美塞）。
輸入：../exp_asia3.json（開發庫唯讀匯出，框 30～185°E、20°S～45°N）、../ohm-asia3.geojson＋../ohm-manifest3.json（build/ohm_geoms.py 由 ../raw 產生）。
輸出：../requests/B{1,2,3}/*.json、../asia3-derived.geojson、../qa.json。
"""
import json, os, re, datetime, glob
from collections import Counter
from shapely.geometry import shape, mapping, MultiPolygon, Polygon, box
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
START, END = '1937-07-07', '1945-09-02'
TRIAL = '亞洲第三批（南亞、阿拉伯半島、婆羅洲、帝汶、新幾內亞、澳門與廣州灣）1937-07-07～1945-09-02'
def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x, 'geoms', []) for p in polys(y)]
def clean(x, m=1e-6):
    x = make_valid(set_precision(make_valid(x), 1e-6)); ps = [p for p in polys(x) if p.area > m]
    return MultiPolygon(ps) if ps else None
nd = lambda s: (datetime.date.fromisoformat(s) + datetime.timedelta(days=1)).isoformat()
F = json.load(open(os.path.join(ROOT, 'exp_asia3.json')))['features']
R = [dict(id=f['id'], slug=f['properties']['slug'], rid=f['properties']['regime_id'], lo=f['properties']['lo'], hi=f['properties']['hi'] or '9999-12-31',
          g=make_valid(shape(f['geometry']))) for f in F if f['geometry']]
OHM = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'ohm-asia3.geojson')))['features']}
MAN = {m['ohm_relation_id']: m for m in json.load(open(os.path.join(ROOT, 'ohm-manifest3.json')))}
def existing_over(lo, hi, g, excl=()):
    gs = [r['g'] for r in R if r['lo'] < hi and r['hi'] > lo and r['id'] not in excl and r['g'].intersects(g)]
    return unary_union(gs) if gs else Polygon()
RG = dict(JP='01a191c9-07d8-7a6d-969f-c702cc8df64c', TH='01a191c9-0821-71a8-89a5-9a3f0b7aba3d', UK='01a18e71-cba5-7726-90e3-9b90ab344afd')
SRC = dict(NE='01a18e71-c977-7a2c-afe3-cb56ea3ec9fa')
EVID = dict(EV_TH_WAR='01a1943f-2ded-7f33-b24e-6456fa9a3217', EV_TH_PEACE='01a1943f-2e66-712d-aca1-646d1a536e59')
CF_TH_UK = '01a19440-2e31-7734-9f09-01c604551712'
ROC = [('01a191c9-0bab-744a-9021-afa4c24e17f6', '1937-07-07', '1938-07-03'), ('01a191c9-0c64-736f-94c9-585e047576ca', '1938-07-03', '1939-04-09'),
       ('01a191c9-0d21-7fca-8164-1a8c7861569b', '1939-04-09', '1945-09-02')]
REQ = []
def add(sub, cat, name, ph, post, body, meta=None, geom=None, readd=None):
    REQ.append(dict(sub=sub, cat=cat, name=name, ph=ph, post=post, body=body, meta=meta, geom=geom, readd=readd))
OSM_BASE = sorted({m['osm_base'] for m in MAN.values()})[-1]
add('B1', '01-source', 'src_ohm_asia3', 'SRC_OHM_ASIA3', '/api/v1/sources', {'sourceKind': 'dataset',
    'title': 'OpenHistoricalMap — boundary=administrative 關係（亞洲第三批：英屬印度、錫蘭、阿拉伯半島、英屬婆羅洲、帝汶、新幾內亞、澳洲、澳門、廣州灣等，1937～1945）', 'publisher': 'OpenHistoricalMap contributors',
    'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright', 'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
    'publishedText': f'Overpass osm_base {OSM_BASE}；relation/' + '、'.join(str(k) for k in sorted(MAN)),
    'note': 'OHM 整體以 CC0 1.0 釋出；本批關係的成員線段都未另標授權。部分關係的 source 標籤指向 Natural Earth、CIA World Data Bank、維基百科，僅作繪製參考。'})
NEWREG = [
 ('REGIME_RAJ', 'british-raj', 'British Raj', 'en', '英屬印度（含土邦）', 'British India (incl. the princely states)'),
 ('REGIME_CEY', 'british-ceylon', 'British Ceylon', 'en', '英屬錫蘭', 'British Ceylon'),
 ('REGIME_MDV', 'maldives-protectorate', 'Maldive Islands', 'en', '馬爾地夫（英國保護國）', 'Maldive Islands (British protectorate)'),
 ('REGIME_NPL', 'kingdom-of-nepal', 'नेपाल अधिराज्य', 'ne', '尼泊爾王國', 'Kingdom of Nepal'),
 ('REGIME_BTN', 'kingdom-of-bhutan', 'འབྲུག་རྒྱལ་ཁབ་', 'dz', '不丹王國', 'Kingdom of Bhutan'),
 ('REGIME_AFG', 'kingdom-of-afghanistan', 'پادشاهی افغانستان', 'fa', '阿富汗王國', 'Kingdom of Afghanistan'),
 ('REGIME_FRI', 'french-india', "Établissements français dans l'Inde", 'fr', '法屬印度', 'French India'),
 ('REGIME_PTI', 'portuguese-india', 'Estado da Índia', 'pt', '葡屬印度', 'Portuguese India'),
 ('REGIME_AND_JP', 'japanese-occupied-andaman-nicobar', 'Japanese-occupied Andaman and Nicobar Islands', 'en', '日本佔領下的安達曼與尼科巴群島', 'Japanese-occupied Andaman and Nicobar Islands'),
 ('REGIME_SAU', 'kingdom-of-saudi-arabia', 'المملكة العربية السعودية', 'ar', '沙烏地阿拉伯王國', 'Kingdom of Saudi Arabia'),
 ('REGIME_YEM', 'mutawakkilite-kingdom-of-yemen', 'المملكة المتوكلية اليمنية', 'ar', '葉門穆塔瓦基利亞王國', 'Mutawakkilite Kingdom of Yemen'),
 ('REGIME_ADC', 'aden-colony', 'Aden Colony', 'en', '亞丁殖民地', 'Aden Colony'),
 ('REGIME_ADP', 'aden-protectorate', 'Aden Protectorate', 'en', '亞丁保護地', 'Aden Protectorate'),
 ('REGIME_OMN', 'sultanate-of-muscat-and-oman', 'سلطنة مسقط وعمان', 'ar', '馬斯喀特與阿曼蘇丹國', 'Sultanate of Muscat and Oman'),
 ('REGIME_TRU', 'trucial-states', 'Trucial States', 'en', '特魯西爾諸國（英國保護）', 'Trucial States (British protection)'),
 ('REGIME_QAT', 'qatar-protectorate', 'قطر', 'ar', '卡達（英國保護國）', 'Qatar (British protectorate)'),
 ('REGIME_BHR', 'bahrain-protectorate', 'البحرين', 'ar', '巴林（英國保護國）', 'Bahrain (British protectorate)'),
 ('REGIME_KWT', 'kuwait-protectorate', 'الكويت', 'ar', '科威特（英國保護國）', 'Kuwait (British protectorate)'),
 ('REGIME_SWK', 'raj-of-sarawak', 'Raj of Sarawak', 'en', '砂拉越（布魯克王朝，英國保護國）', 'Raj of Sarawak (British protected state)'),
 ('REGIME_BRN', 'brunei-protectorate', 'Brunei', 'en', '汶萊（英國保護國）', 'Brunei (British protectorate)'),
 ('REGIME_NBO', 'british-north-borneo', 'British North Borneo', 'en', '英屬北婆羅洲（渣打公司）', 'British North Borneo (chartered company)'),
 ('REGIME_BOR_JP', 'japanese-occupied-british-borneo', '北ボルネオ軍政', 'ja', '日本佔領下的英屬婆羅洲', 'Japanese-occupied British Borneo'),
 ('REGIME_TLS', 'portuguese-timor', 'Timor Português', 'pt', '葡屬帝汶', 'Portuguese Timor'),
 ('REGIME_TLS_JP', 'japanese-occupied-portuguese-timor', 'Japanese-occupied Portuguese Timor', 'en', '日本佔領下的葡屬帝汶', 'Japanese-occupied Portuguese Timor'),
 ('REGIME_AUS', 'commonwealth-of-australia', 'Commonwealth of Australia', 'en', '澳大利亞聯邦', 'Commonwealth of Australia'),
 ('REGIME_PAP', 'territory-of-papua', 'Territory of Papua', 'en', '巴布亞領地（澳洲）', 'Territory of Papua (Australia)'),
 ('REGIME_TNG', 'territory-of-new-guinea', 'Territory of New Guinea', 'en', '新幾內亞委任統治地（澳洲管理）', 'Territory of New Guinea (Australian mandate)'),
 ('REGIME_NBR_JP', 'japanese-occupied-new-britain', 'Japanese-occupied New Britain and New Ireland', 'en', '日本佔領下的新不列顛與新愛爾蘭（拉包爾）', 'Japanese-occupied New Britain and New Ireland (Rabaul)'),
 ('REGIME_SLB', 'british-solomon-islands', 'British Solomon Islands Protectorate', 'en', '英屬索羅門群島保護國', 'British Solomon Islands Protectorate'),
 ('REGIME_MAC', 'portuguese-macau', 'Macau', 'pt', '葡屬澳門', 'Portuguese Macau'),
 ('REGIME_KCW', 'kwangchowan', 'Territoire de Kouang-Tchéou-Wan', 'fr', '廣州灣（法國租借地）', 'Kwangchowan (French leased territory)'),
 ('REGIME_KCW_JP', 'japanese-occupied-kwangchowan', 'Japanese-occupied Kwangchowan', 'en', '日本佔領下的廣州灣', 'Japanese-occupied Kwangchowan'),
]
for ph, slug, orig, lang, zh, en in NEWREG:
    add('B1', '02-regime', slug, ph, '/api/v1/regimes', {'slug': slug, 'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]}, meta={'priorPlaceholder': False})
    RG[ph] = '{{%s}}' % ph
EV = {}
def ev(ph, date, kind, zh, en, parts, cites=None, note_zh=None, note_en=None):
    EV[ph] = date
    b = {'eventKind': kind, 'occurred': {'start': date, 'end': nd(date)}, 'datePrecision': 'day', 'summary': {'zh-Hant': zh, 'en': en},
         'participants': [{'regimeId': RG[r], 'role': role} for r, role in parts], 'citations': cites or []}
    tz = note_zh or ''; te = note_en or ''
    if not cites: tz = ('未找到正式出處（待查證）。' + tz).strip(); te = ('No formal source located yet (pending). ' + te).strip()
    b['timeNote'] = {'zh-Hant': tz, 'en': te or tz}
    add('B1', '03-event', ph.lower(), ph, '/api/v1/events', b, meta={'verification': 'verified' if cites else 'pending（待查證）'})
B, O = 'belligerent', 'other'
ev('EV_BORNEO_JP', '1941-12-16', 'campaign', '日軍登陸砂拉越美里與汶萊詩里亞，進攻英屬婆羅洲', 'Japanese forces land at Miri (Sarawak) and Seria (Brunei)',
   [('JP', B), ('UK', B), ('REGIME_SWK', O), ('REGIME_BRN', O)], note_zh='日期依 OHM 與通行說法；古晉 12/24 陷落（未分段）。', note_en='Date per OHM and common accounts; Kuching fell 24 Dec (not split).')
ev('EV_NBO_JP', '1942-01-02', 'campaign', '日軍佔領納閩並進入英屬北婆羅洲', 'Japanese forces take Labuan and enter British North Borneo',
   [('JP', B), ('UK', B), ('REGIME_NBO', O)], note_zh='依 OHM 切換日（1942-01-02）；納閩 1/1、亞庇（傑斯頓）1/8、山打根 1/19 陷落（未分段）。', note_en='OHM switch date; Labuan 1 Jan, Jesselton 8 Jan, Sandakan 19 Jan (not split).')
ev('EV_RABAUL', '1942-01-23', 'battle', '日軍攻佔新不列顛島拉包爾', 'Japanese forces capture Rabaul (New Britain)',
   [('JP', B), ('REGIME_AUS', B), ('REGIME_TNG', O)], note_zh='新愛爾蘭卡維恩同日陷落；新幾內亞本島北岸（萊城、薩拉毛亞 1942-03-08 等）與布干維爾的佔領未分段。', note_en='Kavieng fell the same day; mainland and Bougainville occupations not split.')
ev('EV_TIMOR_JP', '1942-02-20', 'campaign', '日軍登陸葡屬帝汶帝力', 'Japanese forces land at Dili, Portuguese Timor',
   [('JP', B), ('REGIME_TLS', O)], note_zh='荷澳聯軍 1941-12-17 已進駐帝力（未另列）；葡萄牙中立，總督府在日軍佔領下名義存續。OHM 記日本佔領起於 1943-02-10，本表依登陸日（待查證）。', note_en='Allied troops had landed on 17 Dec 1941 (not listed); OHM gives 1943-02-10 for the occupation; landing date used here (pending).')
ev('EV_ANDAMAN', '1942-03-23', 'campaign', '日軍佔領安達曼群島布萊爾港', 'Japanese forces occupy Port Blair, Andaman Islands',
   [('JP', B), ('UK', B), ('REGIME_RAJ', O)], note_zh='尼科巴群島隨後被佔；1943-12-29 名義移交自由印度臨時政府（未另列）。', note_en='Nicobars occupied subsequently; nominal transfer to Azad Hind on 29 Dec 1943 not listed.')
ev('EV_KCW_JP', '1943-02-21', 'campaign', '日軍進駐廣州灣（維琪法國當局同意）', 'Japanese forces occupy Kwangchowan with Vichy French consent',
   [('JP', O), ('REGIME_KCW', O)], note_zh='1945-08-18 中法簽約交還中國（日軍到 9 月才撤，未分段）。', note_en='Franco-Chinese convention of 18 Aug 1945 returned it to China (not split).')
def E(ph):
    if ph is None: return None
    if re.match(r'^[0-9a-f-]{36}$', ph): return ph
    return EVID.get(ph) or '{{%s}}' % ph
def ohm(*ids): return make_valid(unary_union([OHM[i] for i in ids]))
NBR_BOX = box(148.0, -6.6, 153.8, -2.3)   # 新不列顛＋新愛爾蘭（不含海軍部群島 146–148°E）
GEO = {
 'RAJ_A': ohm(2848216), 'RAJ_B': ohm(2961654), 'AND_JP': ohm(2961652), 'CEY': ohm(2848313), 'MDV': ohm(2848182), 'NPL': ohm(2893390), 'BTN': ohm(2906073),
 'AFG': ohm(2822863), 'FRI': ohm(2961649), 'PTI': ohm(2965458),
 'SAU': ohm(2905965), 'YEM': ohm(2960814), 'ADC': ohm(2848223), 'ADP': ohm(2848485), 'OMN': ohm(2905974, 2920522), 'TRU': ohm(2848320), 'QAT': ohm(2848319),
 'BHR': ohm(2848318), 'KWT': ohm(2848364),
 'SWK': ohm(2961074), 'BRN': ohm(2961066), 'NBO': ohm(2848286), 'BOR_JP1': ohm(2848295), 'BOR_JP2A': ohm(2848294, 2848293, 2848292), 'BOR_JP2B': ohm(2848294, 2848293, 2848292),
 'TLS': ohm(2864414), 'TLS_JP': ohm(2885873),
 'AUS': make_valid(ohm(2848197).difference(ohm(2801211, 2801212))), 'PAP': ohm(2801211), 'TNG_A': ohm(2801212),
 'NBR_JP': make_valid(ohm(2801212).intersection(NBR_BOX)), 'TNG_B': make_valid(ohm(2801212).difference(NBR_BOX)), 'SLB': ohm(2831242),
 'MAC': ohm(2694462), 'KCW': ohm(2889933), 'KCW_JP': ohm(2889933),
}
RELS = {'RAJ_A': (2848216,), 'RAJ_B': (2961654,), 'AND_JP': (2961652,), 'CEY': (2848313,), 'MDV': (2848182,), 'NPL': (2893390,), 'BTN': (2906073,), 'AFG': (2822863,),
        'FRI': (2961649,), 'PTI': (2965458,), 'SAU': (2905965,), 'YEM': (2960814,), 'ADC': (2848223,), 'ADP': (2848485,), 'OMN': (2905974, 2920522), 'TRU': (2848320,),
        'QAT': (2848319,), 'BHR': (2848318,), 'KWT': (2848364,), 'SWK': (2961074,), 'BRN': (2961066,), 'NBO': (2848286,), 'BOR_JP1': (2848295,),
        'BOR_JP2A': (2848294, 2848293, 2848292), 'BOR_JP2B': (2848294, 2848293, 2848292), 'TLS': (2864414,), 'TLS_JP': (2885873,), 'AUS': (2848197,), 'PAP': (2801211,), 'TNG_A': (2801212,), 'NBR_JP': (2801212,),
        'TNG_B': (2801212,), 'SLB': (2831242,), 'MAC': (2694462,), 'KCW': (2889933,), 'KCW_JP': (2889933,)}
LOCX = {'OMN': '（含瓜達爾）', 'AUS': ' − relation/2801211、2801212（巴布亞、新幾內亞另列）', 'NBR_JP': ' ∩ 框 148–153.8°E、6.6–2.3°S（新不列顛、新愛爾蘭；方法近似）',
        'TNG_B': ' − 框 148–153.8°E、6.6–2.3°S（新不列顛、新愛爾蘭另列日本佔領）', 'BOR_JP2A': '（三個版本合併；扣掉開發庫既有荷屬東印度、海峽殖民地納閩等）', 'BOR_JP2B': '（三個版本合併；扣掉開發庫既有荷屬東印度等）'}
OCCN = '非主權：日本佔領區（軍事管理，另列佔領歸屬）。'
UKP = '英國保護國（對外關係由英國掌理）。'
SEG = [
 ('MAC', 'REGIME_MAC', START, END, None, None, 'de_jure', 1, '葡萄牙殖民地；戰時中立，日本未佔領。', 'Portuguese colony; neutral, never occupied by Japan.'),
 ('KCW', 'REGIME_KCW', START, '1943-02-21', None, 'EV_KCW_JP', 'not_sovereign', 1, '非主權：法國租借地（1898 年租借 99 年，中國保留主權；1940 起維琪法國管理）。原由開發庫中華民國紀錄涵蓋，本批扣出。', 'French leased territory (Chinese sovereignty retained); Vichy administration from 1940.'),
 ('KCW_JP', 'REGIME_KCW_JP', '1943-02-21', END, 'EV_KCW_JP', None, 'not_sovereign', 1, OCCN + '1945-08-18 中法簽約交還中國，日軍到 9 月才撤（未分段，待查證）。', 'Japanese occupation; returned to China by the convention of 18 Aug 1945 (not split).'),
 ('FRI', 'REGIME_FRI', START, END, None, None, 'de_jure', 1, '法國在印度的五個商館（朋迪治里、加里加爾、亞南、馬埃、昌德納哥）；1940-09 起歸附自由法國（未分段）。', 'Five French settlements; rallied to Free France in Sep 1940 (not split).'),
 ('PTI', 'REGIME_PTI', START, END, None, None, 'de_jure', 1, '葡萄牙殖民地（果阿、達曼、第烏）；戰時中立。', 'Portuguese colony (Goa, Daman, Diu); neutral.'),
 ('CEY', 'REGIME_CEY', START, END, None, None, 'de_jure', 1, '英國直轄殖民地。日軍 1942-04 空襲可倫坡與亭可馬里，未登陸。', 'British crown colony; raided by Japanese aircraft in Apr 1942, never occupied.'),
 ('MDV', 'REGIME_MDV', START, END, None, None, 'de_jure', 1, UKP, 'British protectorate.'),
 ('AND_JP', 'REGIME_AND_JP', '1942-03-23', END, 'EV_ANDAMAN', None, 'not_sovereign', 1, OCCN + '日軍守備到 1945-10 才投降（本表止於 9/2）。', 'Japanese occupation (surrendered Oct 1945).'),
 ('RAJ_A', 'REGIME_RAJ', START, '1942-03-23', None, 'EV_ANDAMAN', 'de_jure', 2, '英屬印度各省與土邦合為一筆（OHM 未分；錫金、海得拉巴、喀什米爾等土邦名義上由各自王公統治，對外由英國掌理）。含安達曼與尼科巴群島。', 'British India provinces and princely states combined (OHM does not separate them); incl. the Andaman and Nicobar Islands.'),
 ('RAJ_B', 'REGIME_RAJ', '1942-03-23', END, 'EV_ANDAMAN', None, 'de_jure', 2, '英屬印度（含土邦），扣掉日本佔領的安達曼與尼科巴群島。1944 年日軍攻入曼尼普爾、那加丘陵（英帕爾、科希馬戰役）未分段。', 'British India excluding the occupied Andamans; the 1944 Imphal–Kohima incursion is not split.'),
 ('NPL', 'REGIME_NPL', START, END, None, None, 'de_jure', 3, '獨立王國（拉納家族掌權）。', 'Independent kingdom (Rana regime).'),
 ('BTN', 'REGIME_BTN', START, END, None, None, 'de_jure', 3, '獨立王國（1910 年條約由英國指導外交）。', 'Kingdom; foreign relations guided by Britain under the 1910 treaty.'),
 ('AFG', 'REGIME_AFG', START, END, None, None, 'de_jure', 3, '獨立王國，戰時中立。', 'Independent kingdom; neutral.'),
 ('ADC', 'REGIME_ADC', START, END, None, None, 'de_jure', 1, '英國直轄殖民地（1937-04-01 自英屬印度分出）。', 'British crown colony (separated from British India 1 Apr 1937).'),
 ('ADP', 'REGIME_ADP', START, END, None, None, 'de_jure', 2, '英國保護地（東西亞丁保護地各酋長國合為一筆）。', 'British protectorate (Eastern and Western Aden Protectorates combined).'),
 ('KWT', 'REGIME_KWT', START, END, None, None, 'de_jure', 1, UKP + '含沙科中立區（OHM 科威特關係已涵蓋）。', 'British protectorate; incl. the Saudi–Kuwaiti neutral zone as drawn in OHM.'),
 ('BHR', 'REGIME_BHR', START, END, None, None, 'de_jure', 1, UKP + '1940-10-19 義大利空襲煉油廠（未另列）。', 'British protectorate; bombed by Italy on 19 Oct 1940 (not listed).'),
 ('QAT', 'REGIME_QAT', START, END, None, None, 'de_jure', 1, UKP, 'British protectorate.'),
 ('TRU', 'REGIME_TRU', START, END, None, None, 'de_jure', 2, '英國保護下的休戰諸酋長國合為一筆。', 'Trucial sheikhdoms under British protection, combined.'),
 ('OMN', 'REGIME_OMN', START, END, None, None, 'de_jure', 3, '獨立蘇丹國（與英國有條約關係），含俾路支海岸的瓜達爾飛地。與特魯西爾諸國的界線（布賴米一帶）未定，重疊處歸特魯西爾諸國。', 'Independent sultanate incl. the Gwadar exclave; the Buraimi area overlap is given to the Trucial States.'),
 ('YEM', 'REGIME_YEM', START, END, None, None, 'de_jure', 3, '獨立王國（伊瑪目葉海亞）。', 'Independent kingdom (Imam Yahya).'),
 ('SAU', 'REGIME_SAU', START, END, None, None, 'de_jure', 4, '獨立王國，戰時中立到 1945-03-01 對德日宣戰（未另列）。沙伊中立區由開發庫伊拉克紀錄涵蓋（既有）。', 'Independent kingdom; declared war on Germany and Japan on 1 Mar 1945 (not listed). The Saudi–Iraqi neutral zone remains in the existing Iraq record.'),
 ('SWK', 'REGIME_SWK', START, '1941-12-16', None, 'EV_BORNEO_JP', 'de_jure', 1, '布魯克家族統治的英國保護國。', 'Brooke Raj under British protection.'),
 ('BRN', 'REGIME_BRN', START, '1941-12-16', None, 'EV_BORNEO_JP', 'de_jure', 1, UKP, 'British protectorate.'),
 ('BOR_JP1', 'REGIME_BOR_JP', '1941-12-16', '1942-01-02', 'EV_BORNEO_JP', 'EV_NBO_JP', 'not_sovereign', 1, OCCN + '砂拉越、汶萊（依 OHM 版本）。', 'Japanese occupation of Sarawak and Brunei (per OHM).'),
 ('NBO', 'REGIME_NBO', START, '1942-01-02', None, 'EV_NBO_JP', 'de_jure', 2, '英國保護下由北婆羅洲渣打公司管理。', 'British protectorate administered by the North Borneo Chartered Company.'),
 ('BOR_JP2A', 'REGIME_BOR_JP', '1942-01-02', '1942-02-15', 'EV_NBO_JP', None, 'not_sovereign', 2, OCCN + '英屬婆羅洲全境（砂拉越、汶萊、北婆羅洲）。澳軍 1945-06 起收復汶萊灣等地（未分段）；納閩到 1942-02-15 仍由開發庫海峽殖民地紀錄涵蓋。', 'All of British Borneo; Australian landings from Jun 1945 not split.'),
 ('BOR_JP2B', 'REGIME_BOR_JP', '1942-02-15', END, None, None, 'not_sovereign', 2, OCCN + '英屬婆羅洲全境（砂拉越、汶萊、北婆羅洲，含納閩；日方改稱前田島）。澳軍 1945-06 起收復汶萊灣等地（未分段）；日軍 9/10 投降。', 'All of British Borneo; Australian landings from Jun 1945 not split.'),
 ('TLS', 'REGIME_TLS', START, '1942-02-20', None, 'EV_TIMOR_JP', 'de_jure', 1, '葡萄牙殖民地；荷澳聯軍 1941-12-17 起駐帝力（未分段）。', 'Portuguese colony; Allied troops at Dili from 17 Dec 1941 (not split).'),
 ('TLS_JP', 'REGIME_TLS_JP', '1942-02-20', END, 'EV_TIMOR_JP', None, 'not_sovereign', 1, OCCN + '葡萄牙總督府名義存續；澳軍游擊隊抵抗到 1943-02（未分段）。日軍 9/11 投降。', 'Japanese occupation; Portuguese administration nominally continued; Australian guerrillas until Feb 1943 (not split).'),
 ('PAP', 'REGIME_PAP', START, END, None, None, 'de_jure', 1, '澳洲領地。日軍 1942-07 登陸布納、戈納並沿可可達小徑南下（未分段，待查證）。', 'Australian territory; the Japanese Buna–Gona landings of Jul 1942 are not split.'),
 ('NBR_JP', 'REGIME_NBR_JP', '1942-01-23', END, 'EV_RABAUL', None, 'not_sovereign', 1, OCCN + '新不列顛與新愛爾蘭（以經緯框從新幾內亞委任統治地取出，方法近似）；拉包爾日軍守到戰爭結束（9/6 投降）。', 'New Britain and New Ireland (bounding box taken from the mandate geometry, approximate).'),
 ('TNG_A', 'REGIME_TNG', START, '1942-01-23', None, 'EV_RABAUL', 'not_sovereign', 2, '非主權：國際聯盟丙類委任統治地，澳洲管理。', 'League of Nations C mandate administered by Australia.'),
 ('TNG_B', 'REGIME_TNG', '1942-01-23', END, 'EV_RABAUL', None, 'not_sovereign', 2, '非主權：澳洲管理的委任統治地，扣掉新不列顛與新愛爾蘭。新幾內亞本島北岸（萊城、馬當、韋瓦克等）、海軍部群島、布干維爾的日本佔領未分段（待查證）。', 'Australian mandate excl. New Britain/New Ireland; mainland, Admiralties and Bougainville occupations not split.'),
 ('SLB', 'REGIME_SLB', START, END, None, None, 'de_jure', 1, '英國保護國。日軍 1942-05 佔圖拉吉、瓜達康納爾等地，1942-08 起美軍反攻（未分段，待查證）。', 'British protectorate; Japanese occupation of Tulagi/Guadalcanal from May 1942 and the Allied counteroffensive are not split.'),
 ('AUS', 'REGIME_AUS', START, END, None, None, 'de_jure', 3, '澳洲聯邦全境（不在 15°S 切開）。', 'All of Australia (not clipped at 15°S).'),
]
DER = {}; QA = {'segments': [], 'overlaps': [], 'gaps': []}
for k, reg, lo, hi, sev, eev, st, pr, nz, ne in SEG:
    g = GEO[k]
    ex = existing_over(lo, hi, g, excl=[x[0] for x in ROC] if k.startswith('KCW') else ())
    higher = [DER[x[0]] for x in SEG if x[7] < pr and DER.get(x[0]) is not None and x[2] < hi and x[3] > lo]
    sub = unary_union([ex] + higher) if higher else ex
    g2 = clean(g.difference(sub))
    DER[k] = g2
    QA['segments'].append([k, lo, hi, round(g.area, 4), round(g2.area, 4) if g2 else 0])
def ohm_body(k, reg, lo, hi, sev, eev, st, nz, ne):
    ids = RELS[k]; m0 = MAN[ids[0]]
    prov = {'trialWindow': TRIAL, 'coastline': SRC['NE'], 'frameClip': '框 30～180°E、50°S～75°N，Natural Earth 10m 陸地裁切，簡化 0.0005°、精度 1e-4°；扣掉開發庫同期既有紀錄與本批優先序較高的新紀錄',
            'ohmRelations': [{'id': i, 'version': MAN[i]['ohm_version'], 'name': MAN[i]['name_en'] or MAN[i]['name'], 'start': MAN[i]['start_date'], 'end': MAN[i]['end_date'],
                              'timestamp': MAN[i]['ohm_timestamp'], 'changeset': MAN[i]['ohm_changeset'], 'memberWayLicense': MAN[i]['member_way_license'], 'fixme': MAN[i]['fixme'],
                              'relationSource': MAN[i]['relation_source']} for i in ids],
            'osmDerivedWayCount': sum(MAN[i]['osm_derived_way_count'] for i in ids), 'licenseReview': None}
    loc = ' ∪ '.join(f'relation/{i} v{MAN[i]["ohm_version"]}' for i in ids) + LOCX.get(k, '')
    tail = '1937-07-07 為本批起點，不是政權起日。' if lo == START else ''
    tail += '到 1945-09-02（本批試驗終點）。' if hi == END else ''
    return {'regimeId': RG[reg], 'geometry': None, 'validPeriod': {'start': lo, 'end': hi}, 'layerStatus': st, 'geometrySourceId': '{{SRC_OHM_ASIA3}}',
            'geometryLocator': loc, 'geometryLicense': 'cc0', 'attribution': None, 'startEventId': E(sev), 'endEventId': E(eev),
            'ohmRelationId': ids[0], 'ohmVersion': m0['ohm_version'], 'ohmFetchedAt': m0['fetched_at'], 'ohmStartRaw': m0['start_date'], 'ohmEndRaw': m0['end_date'],
            'provenance': prov, 'note': {'zh-Hant': (nz + tail).strip(), 'en': ne}}
# ── 中華民國三筆：先撤後增扣掉廣州灣（放在 B2 最前面，避免與新廣州灣紀錄重疊）──
KCWg = GEO['KCW']
for i, (rid, lo, hi) in enumerate(ROC, 1):
    add('B2', '04-retract', f'retract_roc_{i}', f'RETRACTED_ROC_{i}', f'/api/v1/sovereignty-records/{rid}/retraction',
        {'reason': f'{TRIAL}：廣州灣（法國租借地，後由日軍佔領）另列政權，中華民國紀錄扣掉廣州灣後重送'}, meta={'fix': True})
for i, (rid, lo, hi) in enumerate(ROC, 1):
    add('B2', '05-sovereignty', f'sov_roc_{i}', f'SOV_ROC_{i}', '/api/v1/sovereignty-records',
        {'geometryLocator': '@locator − relation/2889933（廣州灣另列）'}, meta={'readdFrom': rid},
        readd={'base': rid, 'geomFrom': rid, 'union': None, 'subtract': mapping(KCWg.buffer(1e-6)), 'noteAppend': None})
for k, reg, lo, hi, sev, eev, st, pr, nz, ne in SEG:
    if DER[k] is None: QA['segments'].append([k, 'EMPTY']); continue
    ph = f'SOV_{k}'
    add('B2', '05-sovereignty', ph.lower(), ph, '/api/v1/sovereignty-records', ohm_body(k, reg, lo, hi, sev, eev, st, nz, ne), geom=ph)
    DER[ph] = DER[k]
def occ(ph, occd, occr, kind, lo, hi, zh, en, basis=None):
    add('B3', '06-occupation', ph.lower(), ph, '/api/v1/occupation-attributions', {'occupiedRegimeId': RG[occd], 'occupierRegimeId': RG[occr],
        'controlKind': kind, 'validPeriod': {'start': lo, 'end': hi}, 'basisEventId': E(basis), 'coOccupied': False, 'note': {'zh-Hant': zh, 'en': en}})
MA = 'military_administration'
occ('OCC_AND_JP', 'REGIME_AND_JP', 'JP', MA, '1942-03-23', END, '日本海軍駐守（1943-12 名義移交自由印度臨時政府，未另列）。', 'Japanese naval occupation.', 'EV_ANDAMAN')
occ('OCC_BOR_JP', 'REGIME_BOR_JP', 'JP', MA, '1941-12-16', END, '日本陸軍北婆羅洲軍政。', 'Japanese army military administration of North Borneo.', 'EV_BORNEO_JP')
occ('OCC_TLS_JP', 'REGIME_TLS_JP', 'JP', MA, '1942-02-20', END, '日軍佔領（葡萄牙總督府名義存續）。', 'Japanese occupation (Portuguese administration nominally continued).', 'EV_TIMOR_JP')
occ('OCC_NBR_JP', 'REGIME_NBR_JP', 'JP', MA, '1942-01-23', END, '日本海軍與第 8 方面軍（拉包爾）。', 'Japanese navy and Eighth Area Army (Rabaul).', 'EV_RABAUL')
occ('OCC_KCW_JP', 'REGIME_KCW_JP', 'JP', MA, '1943-02-21', END, '日軍佔領。', 'Japanese occupation.', 'EV_KCW_JP')
add('B3', '07-retract', 'retract_cf_th_uk', 'RETRACTED_CF_TH_UK', f'/api/v1/conflict-records/{CF_TH_UK}/retraction',
    {'reason': f'{TRIAL}：地點方法改為開戰地點（泰緬邊境美塞），英國改由英屬印度等屬地計算最近端點，弧線不再接到英國本土'}, meta={'fix': True})
add('B3', '08-conflict', 'cf_th_uk2', 'CF_TH_UK2', '/api/v1/conflict-records', {'regimeAId': RG['TH'], 'regimeBId': RG['UK'], 'startEventId': E('EV_TH_WAR'), 'endEventId': E('EV_TH_PEACE'),
    'location': {'type': 'Point', 'coordinates': [99.88, 20.43]},
    'locationMethod': '開戰地點：泰緬邊境美塞（1942-01-25 泰國對英宣戰；泰軍 1942-05 由此攻入撣邦）',
    'note': {'zh-Hant': '交戰期間由起訖事件日期推得（1942-01-25 宣戰～1945-08-16 和平宣言）。2026-11-01 重送：地點方法改為開戰地點。',
             'en': 'Period from the declaration (25 Jan 1942) to the peace proclamation (16 Aug 1945). Re-sent on 2026-11-01 with the location as the opening point.'}})
NEWG = [(r['ph'], r['body']['validPeriod']['start'], r['body']['validPeriod']['end'], DER[r['ph']]) for r in REQ if r['cat'] == '05-sovereignty' and r['ph'] in DER and DER[r['ph']] is not None]
dates = sorted({x[1] for x in NEWG} | {r['lo'] for r in R if START <= r['lo'] < END})
for d in dates:
    if d >= END: continue
    act = [x for x in NEWG if x[1] <= d < x[2]]
    oth = [r for r in R if r['lo'] <= d < r['hi'] and r['id'] not in {x[0] for x in ROC}]
    for i in range(len(act)):
        for j in range(i + 1, len(act)):
            a_ = act[i][3].intersection(act[j][3]).area
            if a_ > 1e-4: QA['overlaps'].append([d, act[i][0], act[j][0], round(a_, 4)])
        for r in oth:
            if r['g'].intersects(act[i][3]):
                a_ = r['g'].intersection(act[i][3]).area
                if a_ > 1e-3: QA['overlaps'].append([d, act[i][0], r['slug'], round(a_, 4)])
REGIONS = {'IN': (60, 5, 98, 37.5), 'AR': (34, 12, 60, 30.5), 'BO': (108.5, 0.8, 119.5, 7.5), 'TL': (124, -9.6, 127.5, -8), 'NG': (140.9, -12, 162, -1), 'AU': (112, -45, 154, -10), 'MC': (110, 20.9, 113.7, 22.3)}
REF = unary_union(list(GEO.values()))
for d in ['1938-01-01', '1941-12-20', '1942-01-10', '1942-03-01', '1942-06-01', '1943-06-01', '1944-06-01', '1945-08-20']:
    act = unary_union([x[3] for x in NEWG if x[1] <= d < x[2]] + [r['g'] for r in R if r['lo'] <= d < r['hi']])
    for nm, bx in REGIONS.items():
        gap = REF.intersection(box(*bx)).difference(act).area
        if gap > 1e-3: QA['gaps'].append([d, nm, round(gap, 4)])
REQD = os.path.join(ROOT, 'requests')
for sub in ('B1', 'B2', 'B3'):
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
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': r['geom'], 'properties': {}, 'geometry': mapping(DER[r['geom']])} for r in REQ if r['geom']]},
          open(os.path.join(ROOT, 'asia3-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(QA, open(os.path.join(ROOT, 'qa.json'), 'w'), ensure_ascii=False, indent=1)
print(Counter((r['sub'], r['cat']) for r in REQ), len(REQ))
for s in QA['segments']: print('  seg', s)
print('overlaps', len(QA['overlaps']));  [print('  ', o) for o in QA['overlaps'][:40]]
print('gaps', QA['gaps'])
print('events pending', sum(1 for r in REQ if r['cat'] == '03-event' and r['meta']['verification'].startswith('pending')), 'of', sum(1 for r in REQ if r['cat'] == '03-event'))
