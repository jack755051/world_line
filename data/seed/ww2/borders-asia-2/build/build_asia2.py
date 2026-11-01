#!/usr/bin/env python3
"""東南亞殖民地、日本佔領與蘇聯進攻滿洲 1937-07-07～1945-09-02（亞洲第二批）。
新政權：英屬香港、海峽殖民地、英屬馬來亞、英屬緬甸、荷屬東印度、法屬印度支那，與日本佔領區（香港、馬來亞、緬甸、荷屬東印度、1945 印度支那、
菲律賓、關島、威克島、阿留申群島）、扶植政權（緬甸國、菲律賓第二共和國）、蘇聯佔領下的滿洲；泰國相關事件與日泰同盟；日英開戰弧線端點改落英屬馬來亞。
輸入：../exp_asia.json（開發庫唯讀匯出，框 55～185°E）、../ohm-asia2.geojson＋../ohm-manifest2.json（build/ohm_geoms.py 由 ../raw 產生）。
輸出：../requests/A{1,2,3}/*.json、../asia2-derived.geojson、../qa.json。
"""
import json, os, re, datetime, glob
from collections import Counter
from shapely.geometry import shape, mapping, MultiPolygon, Polygon, Point, box
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
START, END = '1937-07-07', '1945-09-02'
TRIAL = '亞洲第二批（東南亞殖民地與日本佔領）1937-07-07～1945-09-02'
def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x, 'geoms', []) for p in polys(y)]
def clean(x, m=1e-6):
    x = make_valid(set_precision(make_valid(x), 1e-6)); ps = [p for p in polys(x) if p.area > m]
    return MultiPolygon(ps) if ps else None
nd = lambda s: (datetime.date.fromisoformat(s) + datetime.timedelta(days=1)).isoformat()
# ── 既有資料 ──
F = json.load(open(os.path.join(ROOT, 'exp_asia.json')))['features']
R = [dict(id=f['id'], slug=f['properties']['slug'], rid=f['properties']['regime_id'], lo=f['properties']['lo'], hi=f['properties']['hi'] or '9999-12-31',
          g=make_valid(shape(f['geometry']))) for f in F if f['geometry']]
BYID = {r['id']: r for r in R}
OHM = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'ohm-asia2.geojson')))['features']}
MAN = {m['ohm_relation_id']: m for m in json.load(open(os.path.join(ROOT, 'ohm-manifest2.json')))}
def existing_over(lo, hi, g, excl=()):
    gs = [r['g'] for r in R if r['lo'] < hi and r['hi'] > lo and r['id'] not in excl and r['g'].intersects(g)]
    return unary_union(gs) if gs else Polygon()
RG = dict(JP='01a191c9-07d8-7a6d-969f-c702cc8df64c', MAN='01a191c9-07ff-7fd1-a279-449ef9d2591e', TH='01a191c9-0821-71a8-89a5-9a3f0b7aba3d',
          PH='01a191b4-36d6-73a7-9161-3e4f9bd241e0', CN='01a191c9-07f8-76a7-8497-ce49a6de97fa', US='01a191b4-36ac-792e-9113-9a46cc51fc9b',
          UK='01a18e71-cba5-7726-90e3-9b90ab344afd', SU='01a18e71-cc2e-7f80-8d62-81879da43d7b')
SRC = dict(FRUS1940V4='01a191c9-07c3-7653-9d3b-4a16982be20d', FRUS1945V6='01a191c9-07ce-7ff2-9c26-0a20ea97757f', FRUS1945V7='01a191c9-07d3-74a6-a4ae-55883ad3a3a9',
           NE='01a18e71-c977-7a2c-afe3-cb56ea3ec9fa')
EVID = dict(EV_PARACEL='01a191c9-08d1-7a42-96dc-11e59c3645c6', EV_SPRATLY='01a191c9-08de-75d0-a275-a8bdf1813f80', EV_TH_IC='01a191c9-08f6-71b6-883a-23995c900dcb',
            EV_JP_UK='01a19294-4aaa-7d7c-a10e-c11c3233cc2f', EV_GUAM='01a191b4-37d9-75ba-ad7f-410b6e3af31c', EV_WAKE='01a191b4-37e3-7dfe-9e5c-60411a2b3a25',
            EV_MANILA='01a191b4-3813-7738-be54-ead83991817a', EV_ALEUT='01a191b4-37ed-7de9-9e87-8fcb3d3983ff', EV_ATTU='01a191b4-37f6-72cf-bf0f-038f7a18a295',
            EV_KISKA='01a191b4-3800-7498-8155-327c2fe382f0', EV_SHAN='01a191c9-0900-7b1e-9e77-ed5d0430ea00', EV_MALAY4='01a191c9-0909-779b-9da0-2bc3c027b46e',
            EV_GUAM_RE='01a191b4-380a-7018-8042-6359430a15c1', EV_SU_WAR='01a191c9-092e-7f27-a6cd-d0410ab7f6ef', EV_MAN_END='01a191c9-0940-744b-941c-28ca92252052',
            EV_JP_SURR='01a191c9-0952-7baa-9c62-cbef88437dea')
REC = dict(PH='01a191b4-4107-7369-971b-c61ae65d327a', MAN='01a191c9-0d65-7f56-ae03-d6c6fbb0d8d8',
           US_A='01a191b4-394e-7eb3-95f5-9d6d9d72cbb2', US_B='01a191b4-3a93-75d7-9bcb-2e2b6f0c3fb6', US_C='01a191b4-3bc9-7f44-b89a-c5b0252516cb',
           US_D='01a191b4-3cfc-747a-9f2e-c74339fac462', US_E='01a191b4-3e2d-7902-b598-9ce933c3c117', US_F='01a191b4-3f64-7b0b-88de-34d7d88fba6d')
CF_JP_UK = '01a19294-4d12-7fe4-bd9c-5337ffb3d612'
REQ = []
def add(sub, cat, name, ph, post, body, meta=None, geom=None, readd=None):
    REQ.append(dict(sub=sub, cat=cat, name=name, ph=ph, post=post, body=body, meta=meta, geom=geom, readd=readd))
# ── 來源 ──
OSM_BASE = json.load(open(os.path.join(ROOT, 'raw', 'r2848458.json')))['osm3s']['timestamp_osm_base']
add('A1', '01-source', 'src_ohm_asia2', 'SRC_OHM_ASIA2', '/api/v1/sources', {'sourceKind': 'dataset',
    'title': 'OpenHistoricalMap — boundary=administrative 關係（亞洲第二批：香港、海峽殖民地、馬來諸邦、緬甸、荷屬東印度、法屬印度支那、菲律賓，1937～1945）', 'publisher': 'OpenHistoricalMap contributors',
    'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright', 'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
    'publishedText': f'Overpass osm_base {OSM_BASE}；relation/' + '、'.join(str(k) for k in sorted(MAN)), 'note': 'OHM 整體以 CC0 1.0 釋出；本批 27 個關係的成員線段都未另標授權。'})
GPO = 'United States Department of State; United States Government Printing Office, Washington'
add('A1', '01-source', 'src_frus_1942v1', 'SRC_FRUS_1942V1', '/api/v1/sources', {'sourceKind': 'official_record',
    'title': 'Foreign Relations of the United States, Diplomatic Papers, 1942, General; the British Commonwealth; the Far East, Volume I', 'publisher': GPO,
    'licenseCode': 'us_federal_pd', 'licenseEvidenceUrl': 'https://www.state.gov/copyright-information', 'url': 'https://history.state.gov/historicaldocuments/frus1942v01', 'publishedText': '1960 年出版'})
add('A1', '01-source', 'src_frus_1943v3', 'SRC_FRUS_1943V3', '/api/v1/sources', {'sourceKind': 'official_record',
    'title': 'Foreign Relations of the United States, Diplomatic Papers, 1943, The British Commonwealth, Eastern Europe, the Far East, Volume III', 'publisher': GPO,
    'licenseCode': 'us_federal_pd', 'licenseEvidenceUrl': 'https://www.state.gov/copyright-information', 'url': 'https://history.state.gov/historicaldocuments/frus1943v03', 'publishedText': '1963 年出版'})
# ── 政權 ──
NEWREG = [
 ('REGIME_HK', 'british-hong-kong', 'British Hong Kong', 'en', '英屬香港', 'British Hong Kong'),
 ('REGIME_SS', 'straits-settlements', 'Straits Settlements', 'en', '海峽殖民地', 'Straits Settlements'),
 ('REGIME_MY', 'british-malaya', 'British Malaya', 'en', '英屬馬來亞（馬來聯邦與馬來屬邦）', 'British Malaya (Federated and Unfederated Malay States)'),
 ('REGIME_BU', 'british-burma', 'British Burma', 'en', '英屬緬甸', 'British Burma'),
 ('REGIME_DEI', 'dutch-east-indies', 'Nederlands-Indië', 'nl', '荷屬東印度', 'Dutch East Indies'),
 ('REGIME_IC', 'french-indochina', 'Indochine française', 'fr', '法屬印度支那', 'French Indochina'),
 ('REGIME_HK_JP', 'japanese-occupied-hong-kong', '香港占領地', 'ja', '日本佔領下的香港', 'Japanese-occupied Hong Kong'),
 ('REGIME_MY_JP', 'japanese-occupied-malaya', 'マライ（馬来）軍政', 'ja', '日本佔領下的馬來亞（含新加坡「昭南」）', 'Japanese-occupied Malaya (incl. Singapore/Syonan)'),
 ('REGIME_BU_JP', 'japanese-occupied-burma', 'Japanese-occupied Burma', 'en', '日本佔領下的緬甸', 'Japanese-occupied Burma'),
 ('REGIME_BU_ST', 'state-of-burma', 'ဗမာနိုင်ငံတော်', 'my', '緬甸國（日本扶植）', 'State of Burma (Japanese puppet state)'),
 ('REGIME_DEI_JP', 'japanese-occupied-dutch-east-indies', 'Japanese-occupied Dutch East Indies', 'en', '日本佔領下的荷屬東印度', 'Japanese-occupied Dutch East Indies'),
 ('REGIME_IC_JP', 'japanese-occupied-indochina', 'Japanese-occupied Indochina', 'en', '日本佔領下的印度支那（1945）', 'Japanese-occupied Indochina (1945)'),
 ('REGIME_PH_JP', 'japanese-occupied-philippines', 'Japanese-occupied Philippines (Philippine Executive Commission)', 'en', '日本佔領下的菲律賓（菲律賓行政委員會）', 'Japanese-occupied Philippines (Philippine Executive Commission)'),
 ('REGIME_PH_REP2', 'second-philippine-republic', 'Republika ng Pilipinas', 'tl', '菲律賓第二共和國（日本扶植）', 'Second Philippine Republic (Japanese puppet state)'),
 ('REGIME_GU_JP', 'japanese-occupied-guam', '大宮島', 'ja', '日本佔領下的關島（大宮島）', 'Japanese-occupied Guam (Ōmiya-jima)'),
 ('REGIME_WK_JP', 'japanese-occupied-wake', '大鳥島', 'ja', '日本佔領下的威克島（大鳥島）', 'Japanese-occupied Wake Island (Ōtori-shima)'),
 ('REGIME_AL_JP', 'japanese-occupied-aleutians', '熱田島・鳴神島', 'ja', '日本佔領下的阿留申群島（阿圖島、基斯卡島）', 'Japanese-occupied Aleutians (Attu and Kiska)'),
 ('REGIME_MAN_SU', 'soviet-occupied-manchuria', 'Soviet-occupied Manchuria', 'en', '蘇聯佔領下的滿洲', 'Soviet-occupied Manchuria'),
]
for ph, slug, orig, lang, zh, en in NEWREG:
    add('A1', '02-regime', slug, ph, '/api/v1/regimes', {'slug': slug, 'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]}, meta={'priorPlaceholder': False})
    RG[ph] = '{{%s}}' % ph
# ── 事件 ──
EV = {}
def cite(src, loc, note): return {'sourceId': SRC.get(src, '{{%s}}' % src), 'locator': loc, 'evidenceNote': note}
def ev(ph, date, kind, zh, en, parts, cites=None, note_zh=None, note_en=None, end=None):
    EV[ph] = date
    b = {'eventKind': kind, 'occurred': {'start': date, 'end': end or nd(date)}, 'datePrecision': 'day', 'summary': {'zh-Hant': zh, 'en': en},
         'participants': [{'regimeId': RG[r], 'role': role} for r, role in parts], 'citations': cites or []}
    tz = note_zh or ''; te = note_en or ''
    if not cites: tz = ('未找到正式出處（待查證）。' + tz).strip(); te = ('No formal source located yet (pending). ' + te).strip()
    if tz: b['timeNote'] = {'zh-Hant': tz, 'en': te or tz}
    add('A1', '03-event', ph.lower(), ph, '/api/v1/events', b, meta={'verification': 'verified' if cites else 'pending（待查證）'})
B, S, O = 'belligerent', 'signatory', 'other'
ev('EV_IC_N', '1940-09-22', 'campaign', '日法河內協定簽字，日軍進駐法屬印度支那北部（同日起華南日軍越境進攻諒山）', 'Hanoi accord signed; Japanese forces enter northern French Indochina',
   [('JP', B), ('REGIME_IC', B)],
   [cite('FRUS1940V4', 'Doc. 169, pp. 141–142', '駐河內領事 1940-09-22 電：當天下午 3 時馬丹將軍與西原少將簽署協定。'),
    cite('FRUS1940V4', 'Doc. 183, p. 153', '9/25 電：依 9/22（星期日）簽署的協定，同意日軍次日在海防登陸。')],
   '日軍原以 9/22 晚 10 時為最後期限（Doc. 159）。', 'Japan had set 10 p.m. on 22 Sep as its deadline (Doc. 159).')
ev('EV_LANGSON', '1940-09-25', 'battle', '諒山法軍向日軍投降，北部越境衝突結束', 'French garrison at Lang Son surrenders to Japanese forces',
   [('JP', B), ('REGIME_IC', B)], [cite('FRUS1940V4', 'Doc. 186', '電文轉述：被優勢日軍包圍的諒山法軍分隊於 9/25 下午 6 時投降；日軍並強行在塗山以南登陸。')])
ev('EV_IC_S', '1941-07-28', 'campaign', '日軍進駐法屬印度支那南部（7/29 日法共同防衛議定書）', 'Japanese forces move into southern French Indochina (Franco-Japanese joint defence protocol, 29 Jul)',
   [('JP', O), ('REGIME_IC', O)], note_zh='FRUS 1941 IV 只見 7/24 羅斯福關於印度支那的提議（Doc. 266, p. 378）；進駐日期依通行說法。', note_en='FRUS 1941 IV Doc. 266 only mentions the 24 Jul proposal; date per common accounts.')
ev('EV_TH_PASSAGE', '1941-12-08', 'treaty', '泰國與日本簽訂協定，允許日軍過境（日軍同日登陸泰國南部，短暫交火後停火）', 'Thailand signs an agreement allowing Japanese troops passage',
   [('TH', S), ('JP', S)], [cite('SRC_FRUS_1942V1', 'Doc. 808, p. 919', '國務院 1942 年泰國情勢摘要：12/8 中午 12 時泰國與日本簽訂協定，允許日軍通過泰國攻擊英國。')])
ev('EV_TH_ALLIANCE', '1941-12-21', 'treaty', '泰日同盟條約簽字', 'Thai–Japanese treaty of alliance signed',
   [('TH', S), ('JP', S)], [cite('SRC_FRUS_1942V1', 'Doc. 808, p. 919', '同上：泰日攻守同盟 1941-12-21 締結。'),
                           cite('SRC_FRUS_1942V1', 'Doc. 803, p. 913', '國務院 1941-12 備忘錄：英國認為泰日締結同盟條約通常足以構成對泰宣戰理由。')])
ev('EV_HK_SURR', '1941-12-25', 'surrender', '香港總督楊慕琦向日軍投降（黑色聖誕）', 'Governor Mark Young surrenders Hong Kong to Japan', [('UK', S), ('JP', S), ('REGIME_HK', O)])
ev('EV_JP_DEI', '1942-01-11', 'campaign', '日軍登陸荷屬婆羅洲打拉根，進攻荷屬東印度', 'Japanese forces land at Tarakan, beginning the invasion of the Dutch East Indies',
   [('JP', B), ('REGIME_DEI', B)], note_zh='荷蘭流亡政府 1941-12-08 已對日宣戰（未另列）。', note_en='The Netherlands had declared war on Japan on 8 Dec 1941.')
ev('EV_TH_WAR', '1942-01-25', 'war', '泰國對英國、美國宣戰（中午起生效；美國不對泰宣戰）', 'Thailand declares war on Britain and the United States (the US does not reciprocate)',
   [('TH', B), ('UK', B), ('US', O)],
   [cite('SRC_FRUS_1942V1', 'Doc. 806', '駐瑞士代辦 1942-02-02 電：瑞士駐曼谷領事轉報，泰國外交部 1/25 函告「奉王命自 1/25 中午起對英美宣戰」。'),
    cite('SRC_FRUS_1942V1', 'Doc. 807', '美國照會：目前無意對泰國宣戰。'), cite('SRC_FRUS_1942V1', 'Doc. 808, p. 919', '泰國 1942-01-25 中午起對美英宣戰。')])
ev('EV_SINGAPORE', '1942-02-15', 'surrender', '新加坡英軍投降，馬來亞全境由日軍佔領', 'British forces in Singapore surrender; all Malaya under Japanese occupation',
   [('UK', S), ('JP', S), ('REGIME_SS', O), ('REGIME_MY', O)], note_zh='日軍 1941-12-08 登陸哥打巴魯後逐步南下（檳城 12/19、吉隆坡 1942-01-11 等，未分段）。', note_en='Progressive invasion from 8 Dec 1941 not split.')
ev('EV_DEI_CAPIT', '1942-03-08', 'surrender', '荷屬東印度軍在卡里查提（萬隆）投降', 'Dutch East Indies forces capitulate at Kalijati',
   [('REGIME_DEI', S), ('JP', S)], note_zh='3/8 宣布投降、3/9 正式簽字（通行說法）；蘇門答臘、婆羅洲等地先後陷落未分段。', note_en='Announced 8 Mar, signed 9 Mar; other islands not split.')
ev('EV_BURMA_FALL', '1942-05-01', 'battle', '日軍攻佔曼德勒，英軍撤出緬甸（OHM 記 1942-05）', 'Japanese take Mandalay; British withdraw from Burma',
   [('JP', B), ('UK', B), ('REGIME_BU', O)], note_zh='仰光 3/8 陷落、密支那 5/8、英緬軍 5 月中下旬撤入印度（未分段）。', note_en='Rangoon fell 8 Mar; withdrawal to India completed in late May (not split).')
ev('EV_BURMA_ST', '1943-08-01', 'political', '日本扶植的緬甸國宣布「獨立」（巴莫），並對英美宣戰', 'Japanese-sponsored State of Burma proclaims "independence" under Ba Maw',
   [('JP', O), ('REGIME_BU_ST', O)])
ev('EV_PH_REP', '1943-10-14', 'political', '日本扶植的菲律賓共和國成立（勞威爾），日菲同盟', 'Japanese-sponsored Philippine Republic established; alliance with Japan',
   [('JP', O), ('REGIME_PH_REP2', O)], [cite('SRC_FRUS_1943V3', 'Doc. 981, pp. 1105–1106', '國務卿 1943-10-18 通電：日本 10/14 在菲律賓成立傀儡政府，並宣布與該「新政權」締結政治、經濟、軍事同盟。')])
ev('EV_PH_RESTORE', '1945-02-27', 'political', '麥克阿瑟在馬尼拉將菲律賓民政交還自由邦總統奧斯梅納', 'MacArthur restores civil government of the Philippines to President Osmeña',
   [('US', O), ('PH', O)], [cite('FRUS1945V6', 'Doc. 880, pp. 1195–1196 (n.)', '駐馬尼拉總領事 1945-03-21 報告與註：麥克阿瑟將菲律賓民政交還奧斯梅納總統。')],
   'FRUS 註記為 2 月 28 日；本表依馬拉坎南宮典禮的通行日期 2 月 27 日（差一天，待查證）。日軍在呂宋等地抵抗到 8 月（未分段）。', 'FRUS footnote gives 28 Feb; ceremony date commonly 27 Feb (pending). Japanese resistance continued (not split).')
ev('EV_IC_COUP', '1945-03-09', 'campaign', '日軍在法屬印度支那發動政變（明號作戰），解除法國行政並繳械法軍', 'Japanese coup in French Indochina ousts the French administration',
   [('JP', B), ('REGIME_IC', B)], [cite('FRUS1945V6', 'Doc. 173, pp. 297–298', '法國大使 1945-03-12 照會：3/9 夜同盟社廣播日軍高司令部公報，印度支那日本佔領軍驅逐法國行政並繳械部分法軍。')],
   '日本隨後扶植越南帝國、柬埔寨、寮國宣布「獨立」（未另列政權）。', 'Japanese-sponsored Vietnam, Cambodia and Laos then proclaimed "independence" (not listed separately).')
ev('EV_RANGOON', '1945-05-03', 'battle', '英軍收復仰光（緬甸國政府已於 4 月撤離）', 'British forces retake Rangoon', [('UK', B), ('JP', B), ('REGIME_BU_ST', O)],
   note_zh='日軍在丹那沙林與東部山區抵抗到 8 月（未分段）。', note_en='Japanese forces held Tenasserim and the east until August (not split).')
ev('EV_SU_MANCH', '1945-08-09', 'campaign', '蘇軍進攻滿洲（八月風暴作戰）', 'Soviet invasion of Manchuria (Operation August Storm)', [('SU', B), ('MAN', B), ('JP', B)],
   [cite('FRUS1945V6', 'Doc. 409', '駐蘇大使哈里曼 1945-08-11 電：莫洛托夫表示蘇軍繼續向滿洲推進，當時（午夜後）已是蘇聯作戰的第三天。')],
   '蘇聯 8/8 宣戰（另列事件），8/9 零時起進攻；關東軍 8/19 起投降（未分段）。', 'War declared 8 Aug; offensive from 9 Aug; Kwantung Army surrendered from 19 Aug.')
ev('EV_TH_PEACE', '1945-08-16', 'political', '泰國和平宣言：宣布對英美宣戰無效，廢除與日本的同盟及協定', 'Thai peace proclamation disavows the declaration of war and repudiates agreements with Japan',
   [('TH', S), ('UK', O), ('US', O)],
   [cite('FRUS1945V6', 'Doc. 949', '1945-08-16 談話備忘錄：泰國公使轉報曼谷外長電，泰國已宣布對美英宣戰無效，並廢除鑾披汶政府與日本所訂協定。'),
    cite('FRUS1945V6', 'Doc. 957, p. 1294', '提及「1945-08-16 泰國和平宣言」表示馬來四州與撣邦將交還英國。')])
ev('EV_HK_REOCC', '1945-08-30', 'campaign', '英國海軍夏慤少將艦隊抵港，英國恢復管治香港', 'Royal Navy under Rear Admiral Harcourt reoccupies Hong Kong',
   [('UK', B), ('JP', O), ('REGIME_HK_JP', O)],
   [cite('FRUS1945V7', 'Doc. 357, p. 500', '英國政府通知蔣介石：派兵重佔香港並恢復行政。'), cite('FRUS1945V7', 'Doc. 371, p. 512', '英國大使告知：英國指派夏慤少將在香港接受日軍投降。')],
   'FRUS 只證明英方重佔安排，8/30 抵港日期依通行說法（待查證）；正式受降 9/16。', 'FRUS documents the arrangements; arrival date per common accounts; formal surrender 16 Sep.')
def E(ph):
    if ph is None: return None
    if re.match(r'^[0-9a-f-]{36}$', ph): return ph
    return EVID.get(ph) or '{{%s}}' % ph
# ── 幾何 ──
def ohm(*ids): return make_valid(unary_union([OHM[i] for i in ids]))
GEO = {}
GEO['HK_A'] = ohm(2694575); GEO['HK_JP'] = ohm(2694574); GEO['HK_B'] = ohm(2694460)
GEO['SS'] = ohm(2848277)
MY_IDS = (2848458, 2848476, 2848477, 2848478, 2848479, 2848480)
GEO['MY'] = make_valid(ohm(*MY_IDS).difference(GEO['SS']))
GEO['MY_JP1'] = ohm(2801989); GEO['MY_JP2'] = ohm(2961557)
GEO['BU_A'] = ohm(2848255); GEO['BU_JP'] = ohm(2848254); GEO['BU_ST1'] = ohm(2848254); GEO['BU_ST2'] = ohm(2961562); GEO['BU_B'] = ohm(2801016)
GEO['DEI'] = ohm(2864434); GEO['DEI_JP'] = ohm(2864434)
GEO['IC1'] = ohm(2745674); GEO['IC2'] = ohm(2948947); GEO['IC3'] = ohm(2948946); GEO['IC4'] = ohm(2745895); GEO['IC_JP'] = ohm(2745895)
# 分段：(key, regime, relIds, lo, hi, sev, eev, status, priority, note_zh, note_en)
OCCN = '非主權：日本佔領區（軍事管理，另列佔領歸屬）。'
SEG = [
 ('HK_A', 'REGIME_HK', (2694575,), START, '1941-12-25', None, 'EV_HK_SURR', 'de_jure', 1, '英國直轄殖民地（香港島、九龍、新界租借地）。', 'British crown colony incl. the New Territories lease.'),
 ('HK_JP', 'REGIME_HK_JP', (2694574,), '1941-12-25', '1945-08-30', 'EV_HK_SURR', 'EV_HK_REOCC', 'not_sovereign', 1, OCCN + '香港佔領地總督部。', 'Japanese occupation (Governor-General of Occupied Hong Kong).'),
 ('HK_B', 'REGIME_HK', (2694460,), '1945-08-30', END, 'EV_HK_REOCC', None, 'de_jure', 1, '英國恢復管治（先由英國軍政府管理）。', 'British rule restored (military administration at first).'),
 ('SS', 'REGIME_SS', (2848277,), START, '1942-02-15', None, 'EV_SINGAPORE', 'de_jure', 2, '英國直轄殖民地（新加坡、檳城、馬六甲、納閩等；聖誕島、科科斯群島在框內）。日軍 1941-12 起逐步佔領，本表到新加坡投降日一次切換（未分段）。', 'Crown colony; progressive invasion from Dec 1941 not split.'),
 ('MY', 'REGIME_MY', MY_IDS, START, '1942-02-15', None, 'EV_SINGAPORE', 'de_jure', 3, '英國保護下的馬來聯邦與五個馬來屬邦（柔佛、吉打、吉蘭丹、登嘉樓、玻璃市）合為一筆，扣掉海峽殖民地。各邦為英國保護國（本表記英屬，各邦蘇丹名義主權未分）。日軍 1941-12-08 登陸起逐步南下，本表到新加坡投降日一次切換（未分段）。', 'Federated and Unfederated Malay States combined; progressive invasion not split.'),
 ('MY_JP1', 'REGIME_MY_JP', (2801989,), '1942-02-15', '1943-10-18', 'EV_SINGAPORE', 'EV_MALAY4', 'not_sovereign', 3, OCCN + '馬來亞與新加坡（昭南）軍政。', 'Japanese military administration of Malaya and Singapore.'),
 ('MY_JP2', 'REGIME_MY_JP', (2961557,), '1943-10-18', END, 'EV_MALAY4', None, 'not_sovereign', 3, OCCN + '1943-10-18 北部四州交泰國後（泰國紀錄另列）。日軍 1945-09-12 在新加坡向東南亞司令部投降（本表止於 9/2）。', 'After the four northern states were transferred to Thailand.'),
 ('BU_A', 'REGIME_BU', (2848255,), START, '1942-05-01', None, 'EV_BURMA_FALL', 'de_jure', 4, '英國殖民地緬甸（1937-04-01 起與印度分治）。', 'British colony of Burma (separated from India 1 Apr 1937).'),
 ('BU_JP', 'REGIME_BU_JP', (2848254,), '1942-05-01', '1943-08-01', 'EV_BURMA_FALL', 'EV_BURMA_ST', 'not_sovereign', 4, OCCN + '仰光 1942-03-08 已陷落，本表以 5/1 曼德勒陷落一次切換（待查證）。', 'Japanese military administration; switch date pending.'),
 ('BU_ST1', 'REGIME_BU_ST', (2848254,), '1943-08-01', '1943-08-18', 'EV_BURMA_ST', 'EV_SHAN', 'not_sovereign', 4, '非主權：日本扶植的緬甸國（巴莫），日軍實際控制；撣邦兩地 8/18 交泰國前（幾何沿用日本佔領緬甸版本）。', 'Japanese puppet State of Burma, before the Shan states went to Thailand.'),
 ('BU_ST2', 'REGIME_BU_ST', (2961562,), '1943-08-18', '1945-05-03', 'EV_SHAN', 'EV_RANGOON', 'not_sovereign', 4, '非主權：日本扶植的緬甸國（巴莫），日軍實際控制。', 'Japanese puppet State of Burma.'),
 ('BU_B', 'REGIME_BU', (2801016,), '1945-05-03', END, 'EV_RANGOON', None, 'de_jure', 4, '英軍收復仰光後恢復英屬（英國軍政府）；日軍在東部、丹那沙林抵抗到 8 月（未分段，待查證）。撣邦兩地仍由泰國紀錄涵蓋。', 'British rule after the recapture of Rangoon; Japanese pockets not split.'),
 ('IC1', 'REGIME_IC', (2745674,), START, '1938-07-03', None, 'EV_PARACEL', 'de_jure', 5, '法國殖民地與保護國（交趾支那、安南、東京、柬埔寨、寮國，含廣州灣以外）。', 'French colony and protectorates.'),
 ('IC2', 'REGIME_IC', (2948947,), '1938-07-03', '1939-04-09', 'EV_PARACEL', 'EV_SPRATLY', 'de_jure', 5, '法屬印度支那（OHM 南海島礁版本交替）。', 'French Indochina (OHM version change: South China Sea islands).'),
 ('IC3', 'REGIME_IC', (2948946,), '1939-04-09', '1941-03-01', 'EV_SPRATLY', 'EV_TH_IC', 'de_jure', 5, '法屬印度支那。1940-09-22 起日軍駐北部（另列佔領歸屬，法國行政照常）。', 'Japanese troops in the north from 22 Sep 1940 (occupation attribution).'),
 ('IC4', 'REGIME_IC', (2745895,), '1941-03-01', '1945-03-09', 'EV_TH_IC', 'EV_IC_COUP', 'de_jure', 5, '泰法戰爭後割讓寮國湄公河右岸與柬埔寨西北部給泰國（泰國紀錄另列）。1941-07-28 起日軍駐全境（另列佔領歸屬，維琪法國行政照常）。', 'After cessions to Thailand; Japanese garrison throughout from Jul 1941.'),
 ('IC_JP', 'REGIME_IC_JP', (2745895,), '1945-03-09', END, 'EV_IC_COUP', None, 'not_sovereign', 5, OCCN + '日軍政變後直接控制（越南帝國、柬埔寨、寮國名義「獨立」未另列）。依一般命令第一號，北緯 16 度以北向中國、以南向東南亞司令部投降（FRUS 1945 VI Doc. 418, p. 636）。', 'Direct Japanese control after the coup; General Order No. 1 split at 16°N.'),
 ('DEI', 'REGIME_DEI', (2864434,), START, '1942-03-08', None, 'EV_DEI_CAPIT', 'de_jure', 6, '荷蘭殖民地（含荷屬新幾內亞）。日軍 1942-01 起逐島進攻，本表到爪哇投降日一次切換（未分段）。', 'Dutch colony incl. Netherlands New Guinea; progressive invasion not split.'),
 ('DEI_JP', 'REGIME_DEI_JP', (2864434,), '1942-03-08', END, 'EV_DEI_CAPIT', None, 'not_sovereign', 6, OCCN + '陸軍（爪哇、蘇門答臘）與海軍（婆羅洲、東部群島）分區軍政未分；荷屬新幾內亞部分地區未被佔領（未分，待查證）。1945-08-17 蘇卡諾宣布印尼獨立（FRUS 1945 VI Doc. 852 記為 8/19，未另列政權）。', 'Army/Navy zones not split; parts of New Guinea never occupied; Indonesian proclamation not listed.'),
]
PRIO = {}
DER = {}; QA = {'segments': [], 'overlaps': [], 'gaps': [], 'islands': {}}
for k, reg, ids, lo, hi, sev, eev, st, pr, nz, ne in SEG:
    g = GEO[k]
    ex = existing_over(lo, hi, g)
    higher = [DER[x[0]] for x in SEG if x[8] < pr and x[0] in DER and x[3] < hi and x[4] > lo]
    sub = unary_union([ex] + higher) if higher else ex
    g2 = clean(g.difference(sub))
    DER[k] = g2
    QA['segments'].append([k, lo, hi, round(g.area, 4), round(g2.area, 4)])
def ohm_body(k, reg, ids, lo, hi, sev, eev, st, nz, ne):
    m0 = MAN[ids[0]]
    prov = {'trialWindow': TRIAL, 'coastline': SRC['NE'], 'frameClip': '框 60～180°E、15°S～75°N，Natural Earth 10m 陸地裁切，簡化 0.0005°、精度 1e-4°；扣掉開發庫同期既有紀錄與本批優先序較高的新紀錄（香港＞海峽殖民地＞馬來亞＞緬甸＞印度支那＞荷屬東印度）',
            'ohmRelations': [{'id': i, 'version': MAN[i]['ohm_version'], 'name': MAN[i]['name_en'] or MAN[i]['name'], 'start': MAN[i]['start_date'], 'end': MAN[i]['end_date'],
                              'timestamp': MAN[i]['ohm_timestamp'], 'changeset': MAN[i]['ohm_changeset'], 'memberWayLicense': MAN[i]['member_way_license'], 'fixme': MAN[i]['fixme']} for i in ids],
            'osmDerivedWayCount': sum(MAN[i]['osm_derived_way_count'] for i in ids), 'licenseReview': None}
    loc = ' ∪ '.join(f'relation/{i} v{MAN[i]["ohm_version"]}' for i in ids)
    if k == 'MY': loc += ' − relation/2848277（海峽殖民地）'
    tail = '1937-07-07 為本批起點，不是政權起日。' if lo == START else ''
    tail += '到 1945-09-02（本批試驗終點）。' if hi == END else ''
    return {'regimeId': RG[reg], 'geometry': None, 'validPeriod': {'start': lo, 'end': hi}, 'layerStatus': st, 'geometrySourceId': '{{SRC_OHM_ASIA2}}',
            'geometryLocator': loc, 'geometryLicense': 'cc0', 'attribution': None, 'startEventId': E(sev), 'endEventId': E(eev),
            'ohmRelationId': ids[0], 'ohmVersion': m0['ohm_version'], 'ohmFetchedAt': m0['fetched_at'], 'ohmStartRaw': m0['start_date'], 'ohmEndRaw': m0['end_date'],
            'provenance': prov, 'note': {'zh-Hant': (nz + tail).strip(), 'en': ne}}
for k, reg, ids, lo, hi, sev, eev, st, pr, nz, ne in SEG:
    if DER[k] is None: QA['segments'].append([k, 'EMPTY']); continue
    ph = f'SOV_{k}'
    add('A2', '05-sovereignty', ph.lower(), ph, '/api/v1/sovereignty-records', ohm_body(k, reg, ids, lo, hi, sev, eev, st, nz, ne), geom=ph)
    DER[ph] = DER[k]
# 菲律賓：沿用既有自由邦紀錄幾何（先例：接縫一致）
PHG = BYID[REC['PH']]['g']
for ph, reg, lo, hi, sev, eev, st, nz, ne in [
 ('SOV_PH_JP', 'REGIME_PH_JP', '1942-01-03', '1943-10-14', 'EV_MANILA', 'EV_PH_REP', 'not_sovereign', OCCN + '日軍 1942-01-02 進入馬尼拉，1-23 成立菲律賓行政委員會；巴丹 4/9、科雷吉多 5/6 才陷落，本表以 1-03 一次切換（未分段）。自由邦政府流亡華盛頓。', 'Japanese occupation (Philippine Executive Commission); Bataan and Corregidor held out until Apr/May 1942 (not split).'),
 ('SOV_PH_REP2', 'REGIME_PH_REP2', '1943-10-14', '1945-02-27', 'EV_PH_REP', 'EV_PH_RESTORE', 'not_sovereign', '非主權：日本扶植的菲律賓共和國（勞威爾），日軍實際控制。美軍 1944-10-20 登陸雷伊泰後逐步收復（未分段）。', 'Japanese puppet republic; progressive US reconquest from Oct 1944 not split.'),
 ('SOV_PH_CW', 'PH', '1945-02-27', END, 'EV_PH_RESTORE', None, 'de_jure', '麥克阿瑟交還民政後恢復自由邦管治（美國主權下）；日軍殘部抵抗到 8 月（未分段）。到 1945-09-02（本批試驗終點）。', 'Commonwealth government restored; Japanese holdouts not split.')]:
    add('A2', '05-sovereignty', ph.lower(), ph, '/api/v1/sovereignty-records', {'regimeId': RG[reg], 'validPeriod': {'start': lo, 'end': hi}, 'layerStatus': st,
        'startEventId': E(sev), 'endEventId': E(eev), 'geometryLocator': '@locator（沿用自由邦紀錄 %s 的幾何）' % REC['PH'],
        'note': {'zh-Hant': nz, 'en': ne}},
        meta={'readdFrom': 'commonwealth-of-the-philippines 1937-07-07～1942-01-03'}, readd={'base': REC['PH'], 'geomFrom': REC['PH'], 'union': None, 'subtract': None, 'noteAppend': None})
    DER[ph] = PHG
# 島嶼：前後兩筆美國紀錄的差（框內）
WORLD = box(-540, -90, 540, 90)
def isl(a, b, bx):
    g = clean(BYID[REC[a]]['g'].difference(BYID[REC[b]]['g']).intersection(box(*bx)), 1e-7)
    return g
ISL = {'GU': isl('US_A', 'US_B', (144, 13, 146, 14)), 'WK': isl('US_B', 'US_C', (166, 19, 167, 20)),
       'AK': isl('US_C', 'US_D', (172, 51, 178.5, 53.5))}
ISL['KI'] = clean(BYID[REC['US_F']]['g'].difference(BYID[REC['US_E']]['g']).intersection(box(172, 51, 178.5, 53.5)), 1e-7)
QA['islands'] = {k: (round(v.area, 5) if v else None) for k, v in ISL.items()}
for ph, reg, k, lo, hi, sev, eev, base, nz, ne, locx in [
 ('SOV_GU_JP', 'REGIME_GU_JP', 'GU', '1941-12-10', '1944-08-10', 'EV_GUAM', 'EV_GUAM_RE', 'US_A', OCCN + '日軍改名大宮島；美軍 1944-07-21 登陸，8/10 宣布有組織抵抗結束。', 'Japanese occupation of Guam.', '關島'),
 ('SOV_WK_JP', 'REGIME_WK_JP', 'WK', '1941-12-23', END, 'EV_WAKE', None, 'US_B', OCCN + '日軍改名大鳥島；守軍 1945-09-04 才投降（本表止於 9/2）。', 'Japanese occupation of Wake (surrendered 4 Sep 1945).', '威克島'),
 ('SOV_AL_JP1', 'REGIME_AL_JP', 'AK', '1942-06-07', '1943-05-30', 'EV_ALEUT', 'EV_ATTU', 'US_C', OCCN + '阿圖島（熱田島）與基斯卡島（鳴神島）。', 'Attu and Kiska.', '阿圖島＋基斯卡島'),
 ('SOV_AL_JP2', 'REGIME_AL_JP', 'KI', '1943-05-30', '1943-07-29', 'EV_ATTU', 'EV_KISKA', 'US_F', OCCN + '美軍收復阿圖島後，只剩基斯卡島。', 'Kiska only after the recapture of Attu.', '基斯卡島')]:
    g = ISL[k]
    sub = WORLD.difference(g.buffer(1e-6))
    add('A2', '05-sovereignty', ph.lower(), ph, '/api/v1/sovereignty-records', {'regimeId': RG[reg], 'validPeriod': {'start': lo, 'end': hi}, 'layerStatus': 'not_sovereign',
        'startEventId': E(sev), 'endEventId': E(eev), 'geometryLocator': f'@locator ∩ {locx}（前後兩筆美國紀錄的差）',
        'note': {'zh-Hant': nz + ('到 1945-09-02（本批試驗終點）。' if hi == END else ''), 'en': ne}},
        meta={'readdFrom': base}, readd={'base': REC[base], 'geomFrom': REC[base], 'union': None, 'subtract': mapping(sub), 'noteAppend': None})
    DER[ph] = g
# 滿洲：蘇聯佔領（沿用滿洲國紀錄幾何）
add('A2', '05-sovereignty', 'sov_man_su', 'SOV_MAN_SU', '/api/v1/sovereignty-records', {'regimeId': RG['REGIME_MAN_SU'], 'validPeriod': {'start': '1945-08-17', 'end': END},
    'layerStatus': 'not_sovereign', 'startEventId': E('EV_MAN_END'), 'endEventId': None, 'geometryLocator': '@locator（沿用滿洲國紀錄 %s 的幾何）' % REC['MAN'],
    'note': {'zh-Hant': '非主權：滿洲國解體後由蘇軍佔領（軍事管理，另列佔領歸屬）。依一般命令第一號，滿洲日軍向蘇軍投降（FRUS 1945 VI Doc. 418, p. 636；Doc. 450, pp. 667–668 史達林回覆）。8/9～8/17 蘇軍推進範圍未分段。中國主權與 1946 年撤軍在試驗範圍外。到 1945-09-02（本批試驗終點）。',
             'en': 'Soviet occupation after the dissolution of Manchukuo; Japanese forces in Manchuria surrendered to the Soviets under General Order No. 1.'}},
    readd={'base': REC['MAN'], 'geomFrom': REC['MAN'], 'union': None, 'subtract': None, 'noteAppend': None})
DER['SOV_MAN_SU'] = BYID[REC['MAN']]['g']
# ── 佔領歸屬 ──
def occ(ph, occd, occr, kind, lo, hi, co, zh, en, basis=None):
    add('A3', '06-occupation', ph.lower(), ph, '/api/v1/occupation-attributions', {'occupiedRegimeId': RG[occd], 'occupierRegimeId': RG[occr],
        'controlKind': kind, 'validPeriod': {'start': lo, 'end': hi}, 'basisEventId': E(basis), 'coOccupied': co, 'note': {'zh-Hant': zh, 'en': en}})
MA = 'military_administration'
occ('OCC_HK_JP', 'REGIME_HK_JP', 'JP', MA, '1941-12-25', '1945-08-30', False, '日本軍政（香港佔領地總督部）。', 'Japanese military administration.', 'EV_HK_SURR')
occ('OCC_MY_JP', 'REGIME_MY_JP', 'JP', MA, '1942-02-15', END, False, '日本第 25 軍軍政（馬來亞、昭南）。', 'Japanese military administration of Malaya.', 'EV_SINGAPORE')
occ('OCC_BU_JP', 'REGIME_BU_JP', 'JP', MA, '1942-05-01', '1943-08-01', False, '日本軍政（緬甸國成立前）。', 'Japanese military administration before the State of Burma.', 'EV_BURMA_FALL')
occ('OCC_DEI_JP', 'REGIME_DEI_JP', 'JP', MA, '1942-03-08', END, False, '日本陸海軍分區軍政（未分區）。', 'Japanese Army and Navy military administrations (zones not split).', 'EV_DEI_CAPIT')
occ('OCC_IC_N', 'REGIME_IC', 'JP', MA, '1940-09-22', '1941-07-28', False, '日軍依 1940-09-22 河內協定駐紮北部（東京），維琪法國行政照常；歸屬以全境表示（北部駐軍範圍未另畫）。', 'Japanese garrison in northern Indochina; French administration continued.', 'EV_IC_N')
occ('OCC_IC_S', 'REGIME_IC', 'JP', MA, '1941-07-28', '1945-03-09', False, '日軍進駐南部後駐紮全境，維琪法國行政照常（日法共管）。', 'Japanese garrison throughout Indochina; French administration continued.', 'EV_IC_S')
occ('OCC_IC_JP', 'REGIME_IC_JP', 'JP', MA, '1945-03-09', END, False, '政變後日軍直接控制。', 'Direct Japanese control after the coup.', 'EV_IC_COUP')
occ('OCC_PH_JP', 'REGIME_PH_JP', 'JP', MA, '1942-01-03', '1943-10-14', False, '日本第 14 軍軍政（菲律賓行政委員會在軍政下運作）。', 'Japanese military administration.', 'EV_MANILA')
occ('OCC_GU_JP', 'REGIME_GU_JP', 'JP', MA, '1941-12-10', '1944-08-10', False, '日本海軍軍政。', 'Japanese naval administration.', 'EV_GUAM')
occ('OCC_WK_JP', 'REGIME_WK_JP', 'JP', MA, '1941-12-23', END, False, '日本海軍駐守。', 'Japanese naval garrison.', 'EV_WAKE')
occ('OCC_AL_JP', 'REGIME_AL_JP', 'JP', MA, '1942-06-07', '1943-07-29', False, '日軍駐守阿圖島、基斯卡島。', 'Japanese garrisons on Attu and Kiska.', 'EV_ALEUT')
occ('OCC_MAN_SU', 'REGIME_MAN_SU', 'SU', MA, '1945-08-17', END, False, '蘇軍軍事佔領（至 1946 年撤軍）。', 'Soviet military occupation (until 1946).', 'EV_SU_MANCH')
# ── 持續關係 ──
def rel(ph, a, b, t, lo, hi, zh, en):
    add('A3', '08-relation', ph.lower(), ph, '/api/v1/regime-relations', {'regimeAId': RG[a], 'regimeBId': RG[b], 'relationType': t, 'validPeriod': {'start': lo, 'end': hi}, 'note': {'zh-Hant': zh, 'en': en}})
rel('REL_JP_TH', 'JP', 'TH', 'alliance', '1941-12-21', '1945-08-16', '泰日攻守同盟（1941-12-21 締結，FRUS 1942 I Doc. 808, p. 919）；1945-08-16 泰國和平宣言廢除（FRUS 1945 VI Doc. 949）。', 'Thai–Japanese alliance, repudiated 16 Aug 1945.')
rel('REL_JP_MAN', 'JP', 'MAN', 'patron_puppet', START, '1945-08-17', '日本扶植滿洲國（1937-07-07 為本批起點）。', 'Japanese puppet state (from the start of this batch).')
rel('REL_JP_BU', 'JP', 'REGIME_BU_ST', 'patron_puppet', '1943-08-01', '1945-05-03', '日本扶植緬甸國（巴莫政府 1945-04 撤離仰光；終點以英軍收復仰光為準，待查證）。', 'Japanese puppet State of Burma.')
rel('REL_JP_PH', 'JP', 'REGIME_PH_REP2', 'patron_puppet', '1943-10-14', '1945-02-27', '日本扶植菲律賓共和國並宣布同盟（FRUS 1943 III Doc. 981）；終點以麥克阿瑟交還民政為準（共和國 1945-08-17 才正式解散）。', 'Japanese puppet Philippine Republic.')
# ── 衝突 ──
def cf(ph, a, b, sev, eev, pt, how, note=None):
    body = {'regimeAId': RG[a], 'regimeBId': RG[b], 'startEventId': E(sev), 'endEventId': E(eev), 'location': {'type': 'Point', 'coordinates': list(pt)}, 'locationMethod': how}
    if note: body['note'] = note
    add('A3', '07-conflict', ph.lower(), ph, '/api/v1/conflict-records', body)
cf('CF_JP_IC', 'JP', 'REGIME_IC', 'EV_IC_N', 'EV_LANGSON', (106.76, 21.85), '開戰地點：諒山（華南日軍越過中越邊境）')
cf('CF_JP_DEI', 'JP', 'REGIME_DEI', 'EV_JP_DEI', 'EV_DEI_CAPIT', (117.58, 3.32), '開戰地點：打拉根（日軍首次登陸荷屬東印度）')
cf('CF_TH_UK', 'TH', 'UK', 'EV_TH_WAR', 'EV_TH_PEACE', (99.88, 20.43), '泰緬邊境美塞（泰軍 1942-05 攻入撣邦的方向；兩國本土不相鄰，固定點）')
cf('CF_SU_MAN', 'SU', 'MAN', 'EV_SU_MANCH', 'EV_MAN_END', (129.6, 44.58), '牡丹江（蘇軍第一遠東方面軍主攻方向，固定點）')
# 日英開戰弧線：先撤後增，地點改為英屬馬來亞（吉蘭丹）內的哥打巴魯
MYg = DER['MY']; kb = Point(102.24, 6.13)
if not MYg.contains(kb):
    from shapely.ops import nearest_points
    kb2 = nearest_points(MYg.buffer(-0.01), kb)[0]; kb = Point(round(kb2.x, 4), round(kb2.y, 4))
QA['kota_bharu'] = [kb.x, kb.y, MYg.contains(kb)]
add('A3', '05-retract', 'retract_cf_jp_uk', 'RETRACTED_CF_JP_UK', f'/api/v1/conflict-records/{CF_JP_UK}/retraction',
    {'reason': f'{TRIAL}：英屬馬來亞已建立，開戰地點改為英屬馬來亞（吉蘭丹）範圍內的哥打巴魯，弧線英方端點落在英屬馬來亞'}, meta={'fix': True})
cf('CF_JP_UK2', 'JP', 'UK', 'EV_JP_UK', 'EV_JP_SURR', (kb.x, kb.y), '開戰地點：哥打巴魯（英屬馬來亞吉蘭丹；日軍登陸點，日英本土不相鄰）',
   {'zh-Hant': '交戰期間由起訖事件日期推得；結束取 1945-09-02 降伏文書簽字。開戰地點 2026-11-01 改落英屬馬來亞範圍內（重送前地點 102.24, 6.13）。',
    'en': 'Period derived from the start event and the surrender of 2 Sep 1945. Location moved inside British Malaya on 2026-11-01.'})
# ── QA ──
NEWG = []
for r in REQ:
    if r['cat'] == '05-sovereignty' and r['ph'] in DER and DER[r['ph']] is not None:
        b = r['body']; NEWG.append((r['ph'], b['validPeriod']['start'], b['validPeriod']['end'], DER[r['ph']]))
dates = sorted({x[1] for x in NEWG} | {r['lo'] for r in R if START <= r['lo'] < END})
REGIONS = {'HK': (113.8, 22.1, 114.5, 22.6), 'MY': (99.5, 1.1, 104.6, 6.8), 'BU': (92, 9.5, 101.5, 28.6), 'IC': (102, 8.4, 109.6, 23.5), 'DEI': (95, -11, 141.1, 6), 'PH': (116.9, 4.5, 127, 21.2)}
for d in dates:
    if d >= END: continue
    act = [x for x in NEWG if x[1] <= d < x[2]]
    oth = [r for r in R if r['lo'] <= d < r['hi']]
    for i in range(len(act)):
        for j in range(i + 1, len(act)):
            a_ = act[i][3].intersection(act[j][3]).area
            if a_ > 1e-4: QA['overlaps'].append([d, act[i][0], act[j][0], round(a_, 4)])
        for r in oth:
            if r['g'].intersects(act[i][3]):
                a_ = r['g'].intersection(act[i][3]).area
                if a_ > 1e-3: QA['overlaps'].append([d, act[i][0], r['slug'], round(a_, 4)])
for d in ['1938-01-01', '1941-12-08', '1942-06-01', '1943-08-10', '1943-12-01', '1944-10-01', '1945-03-15', '1945-05-10', '1945-08-15', '1945-08-20']:
    act = unary_union([x[3] for x in NEWG if x[1] <= d < x[2]] + [r['g'] for r in R if r['lo'] <= d < r['hi']])
    for nm, bx in REGIONS.items():
        ref = unary_union([GEO[k] for k in GEO if k.startswith(nm)] or [Polygon()]) if nm != 'PH' else PHG
        gap = ref.intersection(box(*bx)).difference(act).area
        if gap > 1e-3: QA['gaps'].append([d, nm, round(gap, 4)])
# ── 輸出 ──
REQD = os.path.join(ROOT, 'requests')
for sub in ('A1', 'A2', 'A3'):
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
          open(os.path.join(ROOT, 'asia2-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(QA, open(os.path.join(ROOT, 'qa.json'), 'w'), ensure_ascii=False, indent=1)
print(Counter((r['sub'], r['cat']) for r in REQ))
for s in QA['segments']: print('  seg', s)
print('islands', QA['islands'], 'kota_bharu', QA['kota_bharu'])
print('overlaps', len(QA['overlaps']));  [print('  ', o) for o in QA['overlaps'][:40]]
print('gaps', QA['gaps'])
print('events pending', sum(1 for r in REQ if r['cat'] == '03-event' and r['meta']['verification'].startswith('pending')), 'of', sum(1 for r in REQ if r['cat'] == '03-event'))
