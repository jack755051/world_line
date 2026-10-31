#!/usr/bin/env python3
"""兩次大戰之間 A 批：1918-11-12 → 1924-01-01（DRAFT，待 Tai 檢查）。
子批（依紀錄起日）：A1 [1918-11-12, 1920-01-10)、A2 [1920-01-10, 1921-03-18)、A3 [1921-03-18, 1924-01-01)。
唯一的修正（先撤後增）：WW1 第二批的德意志帝國紀錄 SOV_DE_EMP_R [1908-10-06, 1918-11-12) 改迄於 1918-11-09（德國革命），
1918-11-09～11-12 改由「德意志國」（REGIME_DE，開發庫既有政權）以同一幾何接上。其他第二批紀錄（迄於 1918-11-12）不動，本批從 11-12 接續。

輸入：
- ../borders-ohm-interwar-a.geojson＋../ohm-manifest.json（build/fetch.py＋build/build.py，固定版本 OHM 關係）
- WW1 第二批（環境變數 WW1B2；在 Mac 上是 seeds/ww1/war-1914-1918）的 requests、derived geojson、ohm-manifest：德意志帝國先撤後增、庫爾蘭／利沃尼亞與鄂圖曼的第二批幾何
- ../db-export/iwa_rows.json：開發庫唯讀匯出，本期間已有的主權紀錄（只做 QA 與扣除，不進版控）
- 第二批 db-export/us_1937.json：開發庫美國最早一筆紀錄（照抄幾何，不進版控）
輸出：../interwar-a-derived.geojson（key＝placeholder）、../qa.json、../requests/A{1,2,3}/*.json
幾何規則同 WW1 第二批的優先序引擎：低優先紀錄扣掉同期較高優先的紀錄（開發庫既有紀錄 prio 9），在較高優先紀錄起訖日切段。
"""
import json, os, copy, datetime, sys, re
from shapely.geometry import shape, mapping, MultiPolygon, Polygon, LineString, MultiLineString, box
from shapely.ops import unary_union, linemerge
from shapely.validation import make_valid
from shapely import set_precision, STRtree

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
B2 = os.environ.get('WW1B2', os.path.join(ROOT, '..', '..', 'ww1', 'war-1914-1918'))
START, END = '1918-11-12', '1924-01-01'
SUBS = [('A1', START, '1920-01-10'), ('A2', '1920-01-10', '1921-03-18'), ('A3', '1921-03-18', END)]
MAN = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(B2, 'ohm-manifest.json')))}
MAN.update({r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))})
OWN = {r['ohm_relation_id'] for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))}
ohm = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(B2, 'borders-ohm-ww1-2.geojson')))['features']}
ohm.update({f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-interwar-a.geojson')))['features']})
ROWS = json.load(open(os.path.join(ROOT, 'db-export', 'iwa_rows.json')))
US = json.load(open(os.path.join(B2, 'db-export', 'us_1937.json')))
B2G = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(B2, 'ww1-1914-1918-derived.geojson')))['features']}
B2R = {}
for sub in sorted(os.listdir(os.path.join(B2, 'requests'))):
    for fn in sorted(os.listdir(os.path.join(B2, 'requests', sub))):
        r = json.load(open(os.path.join(B2, 'requests', sub, fn), encoding='utf-8')); B2R[r['_placeholder']] = r

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

# ── 手繪近似範圍（全部標「近似／待查證」）──
ZUNR_PTS = [(22.6, 49.05), (22.7, 49.55), (22.95, 50.05), (23.5, 50.42), (24.1, 50.6), (25.0, 50.35), (25.75, 49.95), (26.25, 49.55), (26.4, 48.7),
            (25.2, 47.9), (24.6, 47.95), (23.5, 48.55), (22.9, 48.9)]
CLT_PTS = [(24.75, 54.1), (24.9, 54.9), (25.6, 55.25), (26.6, 55.65), (26.85, 55.3), (26.7, 54.8), (26.2, 54.4), (25.8, 54.2), (25.5, 54.05), (24.9, 53.95)]
RUHR_PTS = [(6.55, 51.25), (6.6, 51.65), (7.0, 51.75), (7.6, 51.7), (7.95, 51.55), (7.8, 51.3), (7.3, 51.2), (6.9, 51.18)]
P1922 = O(2855672)
GRDIFF = O(2863750).difference(O(2863749))
def is_thrace(p):
    c = p.representative_point(); return c.y >= 40.45 or (c.y >= 39.95 and c.x < 26.9)
G = {
 'ZUNR': P1922.intersection(Polygon(ZUNR_PTS)),
 'CLT': P1922.intersection(Polygon(CLT_PTS)),
 'RUHR': O(2696515).intersection(Polygon(RUHR_PTS)),
 'IT_JULIAN': O(2696325).difference(O(2696424)),
 'ETHRACE': unary_union([p for p in polys(GRDIFF) if is_thrace(p)]),
 'SMYRNA': unary_union([p for p in polys(GRDIFF) if not is_thrace(p)]),
 'RO_A': U(O(2693260), B2G['SOV_RO_BESS'] if 'SOV_RO_BESS' in B2G else O(2694154)),
 'RS_MN': U(O(2746681), O(2739656)),
}
G = {k: clean(v) for k, v in G.items()}
def g_of(k):
    if isinstance(k, int): return clean(O(k))
    if k in G: return G[k]
    return clean(B2G[k])

REQ = []
def add(cat, name, ph, post, body, meta=None, geom=None, sub=None):
    REQ.append(dict(cat=cat, name=name, ph=ph, post=post, body=body, meta=meta, geom=geom, sub=sub))

# ── 來源 ──
add('01-source', 'src_ohm_iwa', 'SRC_OHM_IWA', '/api/v1/sources', {'sourceKind': 'dataset',
    'title': 'OpenHistoricalMap — boundary=administrative 關係（歐洲、北非、近東，1918～1923 兩次大戰之間 A 批試驗）',
    'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
    'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
    'publishedText': 'Overpass osm_base %s；逐筆見 interwar/batch-a/ohm-manifest.json' % MAN[2696519]['osm_base'],
    'note': 'OHM 整體以 CC0 1.0 釋出；部分成員線段帶 license=CC BY 4.0 標籤，部分線段註明來自 OpenStreetMap（ODbL），逐筆在主權紀錄標示。'})
GPO = 'United States Department of State; United States Government Printing Office, Washington'
FRUS = [('SRC_FRUS_PPC2', 'frus1919Parisv02', 'Papers Relating to the Foreign Relations of the United States, The Paris Peace Conference, 1919, Volume II', '1942'),
        ('SRC_FRUS_PPC12', 'frus1919Parisv12', 'Papers Relating to the Foreign Relations of the United States, The Paris Peace Conference, 1919, Volume XII', '1947'),
        ('SRC_FRUS_PPC13', 'frus1919Parisv13', 'Papers Relating to the Foreign Relations of the United States, The Paris Peace Conference, 1919, Volume XIII（凡爾賽和約全文附註解；各和約生效狀態）', '1947'),
        ('SRC_FRUS_1922V2', 'frus1922v02', 'Papers Relating to the Foreign Relations of the United States, 1922, Volume II', '1938'),
        ('SRC_FRUS_1923V2', 'frus1923v02', 'Papers Relating to the Foreign Relations of the United States, 1923, Volume II', '1938')]
for ph, vol, t, yr in FRUS:
    add('01-source', ph.lower(), ph, '/api/v1/sources', {'sourceKind': 'official_record', 'title': t, 'publisher': GPO, 'licenseCode': 'us_federal_pd',
        'licenseEvidenceUrl': 'https://www.state.gov/copyright-information', 'url': 'https://history.state.gov/historicaldocuments/' + vol, 'publishedText': f'{yr} 年出版'})
LNTS = [('SRC_LNTS_2', 2, '1920–1921'), ('SRC_LNTS_3', 3, '1921'), ('SRC_LNTS_6', 6, '1921'), ('SRC_LNTS_11', 11, '1922'), ('SRC_LNTS_18', 18, '1923'), ('SRC_LNTS_28', 28, '1924')]
for ph, v, yr in LNTS:
    add('01-source', ph.lower(), ph, '/api/v1/sources', {'sourceKind': 'treaty', 'title': f'League of Nations Treaty Series, Vol. {v}（國際聯盟條約彙編第 {v} 卷）',
        'publisher': 'League of Nations（Geneva）', 'licenseCode': 'pd_expired',
        'licenseEvidenceUrl': 'https://treaties.un.org/Pages/Content.aspx?path=DB%2FLoNOnline%2FpageIntro_Table_en.xml',
        'url': f'https://treaties.un.org/doc/Publication/UNTS/LON/Volume%20{v}/v{v}.pdf', 'publishedText': f'{yr} 年出版（聯合國條約資料庫公開掃描本）',
        'note': '1930 年以前出版，美國著作權已過期；條約原文與英、法譯本。'})

# ── 新政權 ──
DESC = '本表自訂的說明性名稱（非政權正式名稱）'
REGIMES = [
 ('REGIME_AT_R1', 'republic-of-austria-1918', 'Republik Österreich', 'de', '奧地利共和國（第一共和，1918–1922）', 'Republic of Austria (First Republic, 1918–1922)', '1918-11-12 稱 Republik Deutschösterreich，1919-10-21 依聖日耳曼條約改稱 Republik Österreich（改名日期待查證）；FRUS PPC II Doc. 117'),
 ('REGIME_HU_PR', 'hungarian-peoples-republic-1918', 'Magyar Népköztársaság', 'hu', '匈牙利人民共和國（1918–1919）', "Hungarian People's Republic (1918–1919)", '原文名為通行稱呼；FRUS PPC II Doc. 136 稱「Hungarian Republic」。1919-08 起的過渡政府也歸在此政權（待查證）'),
 ('REGIME_HU_SR', 'hungarian-soviet-republic', 'Magyarországi Tanácsköztársaság', 'hu', '匈牙利蘇維埃共和國', 'Hungarian Soviet Republic', '原文名為通行稱呼；FRUS PPC XII Doc. 157'),
 ('REGIME_KSCS', 'kingdom-of-serbs-croats-and-slovenes', 'Краљевство Срба, Хрвата и Словенаца', 'sr', '塞爾維亞人、克羅埃西亞人和斯洛維尼亞人王國', 'Kingdom of Serbs, Croats and Slovenes', '1929 年改稱南斯拉夫王國（開發庫既有政權 kingdom-of-yugoslavia）；OHM relation/2747828'),
 ('REGIME_IS', 'kingdom-of-iceland', 'Konungsríkið Ísland', 'is', '冰島王國', 'Kingdom of Iceland', 'OHM relation/2801981；原文名為通行稱呼'),
 ('REGIME_IFS', 'irish-free-state', 'Saorstát Éireann', 'ga', '愛爾蘭自由邦', 'Irish Free State', 'OHM relation/2697727；1937 年起為開發庫既有政權 ireland-eire'),
 ('REGIME_EG_K', 'kingdom-of-egypt', 'المملكة المصرية', 'ar', '埃及王國', 'Kingdom of Egypt', 'OHM relation/2803204；原文名為通行稱呼'),
 ('REGIME_SAAR', 'territory-of-the-saar-basin', 'Saarbeckengebiet', 'de', '薩爾盆地地區（國際聯盟託管）', 'Territory of the Saar Basin (League of Nations)', 'OHM relation/2690373；凡爾賽和約第 45–50 條'),
 ('REGIME_MEMEL', 'klaipeda-region-allied-administration', 'Memelgebiet', 'de', '梅梅爾地區（協約國管理，1920–1923）', 'Memel Territory (Allied administration, 1920–1923)', 'OHM relation/2691476；凡爾賽和約第 99 條'),
 ('REGIME_DANZIG_ALLIED', 'danzig-allied-administration-1920', 'Danzig under Allied administration (1920)', 'en', '協約國管理下的但澤（1920）', 'Danzig under Allied administration (1920)', f'{DESC}；凡爾賽和約第 100–108 條'),
 ('REGIME_RUHR', 'franco-belgian-occupied-ruhr', 'Franco-Belgian-occupied Ruhr (1923–1925)', 'en', '法比佔領下的魯爾區', 'Franco-Belgian-occupied Ruhr', DESC),
 ('REGIME_IT_JULIAN', 'italian-occupied-former-austrian-lands-1918', 'Italian-occupied former Austro-Hungarian territory (1918–1920)', 'en', '義大利佔領的原奧匈領土（1918–1920）', 'Italian-occupied former Austro-Hungarian territory (1918–1920)', f'{DESC}；範圍＝OHM 2696325 − 2696424（聖日耳曼條約後義大利所得）'),
 ('REGIME_FIUME_IA', 'fiume-inter-allied-occupation', 'Fiume under inter-Allied occupation (1918–1919)', 'en', '協約國佔領下的阜姆（1918–1919）', 'Fiume under inter-Allied occupation (1918–1919)', DESC),
 ('REGIME_CARNARO', 'italian-regency-of-carnaro', 'Reggenza Italiana del Carnaro', 'it', '卡爾納羅義大利攝政國（鄧南遮）', "Italian Regency of Carnaro (D'Annunzio)", '原文名為通行稱呼（1920-09-08 宣布；1919-09-12 起鄧南遮佔領阜姆，待查證）'),
 ('REGIME_FIUME_FS', 'free-state-of-fiume', 'Stato libero di Fiume', 'it', '阜姆自由邦', 'Free State of Fiume', 'OHM relation/2696321；拉帕洛條約第 4 條'),
 ('REGIME_CIESZYN', 'cieszyn-silesia-disputed-1918', 'Cieszyn Silesia (disputed, 1918–1920)', 'en', '切申西里西亞（爭議區，1918–1920）', 'Cieszyn Silesia (disputed, 1918–1920)', f'{DESC}；OHM relation/2747891'),
 ('REGIME_ZUNR', 'west-ukrainian-peoples-republic', 'Західноукраїнська Народна Республіка', 'uk', '西烏克蘭人民共和國', "West Ukrainian People's Republic", '原文名為通行稱呼'),
 ('REGIME_CLT', 'republic-of-central-lithuania', 'Litwa Środkowa', 'pl', '中立陶宛共和國', 'Republic of Central Lithuania', '原文名為通行稱呼'),
 ('REGIME_UA_SSR', 'ukrainian-ssr-1919', 'Українська Соціалістична Радянська Республіка', 'uk', '烏克蘭蘇維埃社會主義共和國（1919–1922）', 'Ukrainian Socialist Soviet Republic (1919–1922)', 'OHM relation/2848214；原文名為通行稱呼（1922-12-30 起加入蘇聯）'),
 ('REGIME_BY_SSR', 'byelorussian-ssr-1919', 'Беларуская Савецкая Сацыялістычная Рэспубліка', 'be', '白俄羅斯蘇維埃社會主義共和國（1919–1922）', 'Byelorussian Soviet Socialist Republic (1919–1922)', 'OHM relation/2848186；原文名為通行稱呼（1919 年立陶宛—白俄羅斯蘇維埃共和國未分，待查證）'),
 ('REGIME_SOUTH_RUSSIA', 'government-of-south-russia-1920', 'Правительство Юга России', 'ru', '南俄政府（弗蘭格爾）', 'Government of South Russia (Wrangel)', 'OHM relation/2854270；原文名為通行稱呼'),
 ('REGIME_GE_SSR', 'georgian-ssr-1921', 'Социалистическая Советская Республика Грузия', 'ru', '喬治亞蘇維埃社會主義共和國（1921–1922）', 'Georgian Socialist Soviet Republic (1921–1922)', 'OHM relation/2957462 等；原文名為通行稱呼（待查證）'),
 ('REGIME_ABKHAZ_SSR', 'abkhaz-ssr-1921', 'Социалистическая Советская Республика Абхазия', 'ru', '阿布哈茲蘇維埃社會主義共和國（1921）', 'Socialist Soviet Republic of Abkhazia (1921)', 'OHM relation/2957464；原文名為通行稱呼（待查證）'),
 ('REGIME_AZ_SSR', 'azerbaijan-ssr-1920', 'Азербайджанская Социалистическая Советская Республика', 'ru', '亞塞拜然蘇維埃社會主義共和國（1920–1922）', 'Azerbaijan Socialist Soviet Republic (1920–1922)', 'OHM relation/2697987；原文名為通行稱呼'),
 ('REGIME_AM_SSR', 'armenian-ssr-1920', 'Социалистическая Советская Республика Армения', 'ru', '亞美尼亞蘇維埃社會主義共和國（1920–1922）', 'Socialist Soviet Republic of Armenia (1920–1922)', 'OHM relation/2698022；原文名為通行稱呼'),
 ('REGIME_TSFSR', 'transcaucasian-sfsr-1922', 'Федеративный Союз Социалистических Советских Республик Закавказья', 'ru', '外高加索社會主義蘇維埃共和國聯盟（1922）', 'Federative Union of Socialist Soviet Republics of Transcaucasia (1922)', 'OHM relation/2698093；原文名為通行稱呼（1922-12-13 改組，12-30 加入蘇聯）'),
 ('REGIME_BATUMI', 'british-occupied-batumi-1918', 'British-occupied Batumi (1918–1920)', 'en', '英軍佔領的巴統（1918–1920）', 'British-occupied Batumi (1918–1920)', f'{DESC}；OHM relation/2698257'),
 ('REGIME_SMYRNA', 'greek-occupied-smyrna-zone', 'Ζώνη Σμύρνης', 'el', '希臘佔領的士麥那區', 'Smyrna Zone (Greek occupation)', '原文名為通行稱呼；範圍＝OHM 2863750 − 2863749 的安納托利亞部分（近似，待查證）'),
 ('REGIME_ETHRACE', 'greek-occupied-eastern-thrace', 'Greek-occupied Eastern Thrace (1920–1922)', 'en', '希臘佔領的東色雷斯（1920–1922）', 'Greek-occupied Eastern Thrace (1920–1922)', f'{DESC}；範圍＝OHM 2863750 − 2863749 的歐洲部分（近似，待查證）'),
 ('REGIME_GNA', 'government-of-the-grand-national-assembly', 'Türkiye Büyük Millet Meclisi Hükûmeti', 'tr', '土耳其大國民議會政府（安卡拉）', 'Government of the Grand National Assembly (Ankara)', '原文名為通行稱呼；OHM relation/2958039（State of Turkey）'),
 ('REGIME_LEVANT', 'french-mandate-levant-1920', 'French Mandate for Syria and the Lebanon (1920)', 'en', '法國敘利亞—黎巴嫩委任統治地（1920）', 'French Mandate for Syria and the Lebanon (1920)', f'{DESC}；OHM relation/2863754（Levant States）'),
 ('REGIME_LEBANON', 'state-of-greater-lebanon', 'État du Grand Liban', 'fr', '大黎巴嫩國（法國委任統治）', 'State of Greater Lebanon (French mandate)', 'OHM relation/2831357；原文名為通行稱呼'),
 ('REGIME_DAMASCUS', 'state-of-damascus', 'État de Damas', 'fr', '大馬士革國（法國委任統治）', 'State of Damascus (French mandate)', 'OHM relation/2863995；原文名為通行稱呼'),
 ('REGIME_ALEPPO', 'state-of-aleppo', "État d'Alep", 'fr', '阿勒坡國（法國委任統治）', 'State of Aleppo (French mandate)', 'OHM relation/2864000；原文名為通行稱呼'),
 ('REGIME_DRUZE', 'jabal-druze-state', 'État du Djebel Druze', 'fr', '德魯茲山國（法國委任統治）', 'Jabal Druze State (French mandate)', 'OHM relation/2864007、2864006（Souaida）；原文名為通行稱呼'),
 ('REGIME_SYR_FED', 'syrian-federation-1922', 'Fédération syrienne', 'fr', '敘利亞聯邦（法國委任統治）', 'Syrian Federation (French mandate)', 'OHM relation/2863992；原文名為通行稱呼'),
 ('REGIME_PALESTINE', 'mandatory-palestine', 'Mandatory Palestine', 'en', '英屬巴勒斯坦委任統治地', 'Mandatory Palestine', 'OHM relation/2848316；名稱為通行稱呼'),
 ('REGIME_TRANSJORDAN', 'emirate-of-transjordan', 'إمارة شرق الأردن', 'ar', '外約旦酋長國（英國委任統治）', 'Emirate of Transjordan (British mandate)', 'OHM relation/2848317；原文名為通行稱呼'),
 ('REGIME_IRAQ', 'mandatory-iraq', 'Mandatory Iraq', 'en', '英屬伊拉克委任統治地', 'Mandatory Iraq', 'OHM relation/2839465；名稱為通行稱呼（1921-08-23 起為伊拉克王國，未分，待查證）'),
 ('REGIME_RIF', 'republic-of-the-rif', 'Republic of the Rif', 'en', '里夫共和國', 'Republic of the Rif', 'OHM relation/2860425；名稱為通行稱呼'),
 ('REGIME_LAJTA', 'lajtabansag', 'Lajtabánság', 'hu', '萊塔班國', 'Banate of Leitha', 'OHM relation/2747802；原文名為通行稱呼'),
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
F18, P2, P12, P13, F22, F23 = 'SRC_FRUS_1918S1', 'SRC_FRUS_PPC2', 'SRC_FRUS_PPC12', 'SRC_FRUS_PPC13', 'SRC_FRUS_1922V2', 'SRC_FRUS_1923V2'
def VERS(part, arts, note): return (P13, f'凡爾賽和約 {part}，{arts}', note)
# 1918–1919
ev('EV_DE_REV', 'political', '1918-11-09', '德國十一月革命：德皇退位、宣布共和，艾伯特出任總理', 'German November Revolution: the Kaiser abdicates, a republic is proclaimed and Ebert becomes chancellor',
   [('REGIME_DE_EMP', S_), ('REGIME_DE', S_)], [(F18, 'Doc. 418, pp. 492–493', '駐海牙公使 1918-11-11 電：轉述艾伯特談話與德國新政府組成，並記德意志奧地利國民議會的表決。')],
   ('11 月 9 日宣布共和為通行說法；FRUS 電報日為 11 月 11 日。', 'Republic proclaimed on 9 Nov per common accounts; the FRUS telegram is of 11 Nov.'))
ev('EV_DEAT', 'political', '1918-11-12', '德意志奧地利臨時國民議會宣布成立民主共和國', 'The Provisional National Assembly of German Austria proclaims a democratic republic', [('REGIME_AT_R1', S_)],
   [(P2, 'Doc. 117, pp. 189–190', '瑞典公使 1918-11-16 照會：德意志奧地利臨時國民議會 1918-11-12 決議國家為民主共和國。')])
ev('EV_ZUNR', 'political', '1918-11-13', '西烏克蘭人民共和國在利沃夫定名（11-01 起與波蘭爭奪東加利西亞）', "The West Ukrainian People's Republic is named in Lviv (fighting with Poland over Eastern Galicia since 1 Nov)",
   [('REGIME_ZUNR', S_), ('REGIME_PL', B)], [], nos('11-01 利沃夫起事、11-13 臨時基本法定名為通行說法。', 'Lviv rising 1 Nov, name adopted 13 Nov per common accounts.'))
ev('EV_HU_PR', 'political', '1918-11-16', '匈牙利宣布成立共和國（卡羅伊政府）', 'Hungary proclaims a republic (Károlyi government)', [('REGIME_HU_PR', S_)],
   [(P2, 'Doc. 136, pp. 204–205', '瑞典使館備忘錄：轉達「the Government of the Hungarian Republic」向協約國與美國的請求。')],
   ('11 月 16 日宣布為通行說法；FRUS 文件只證明共和政府已存在。11-12～11-16 匈牙利本表也歸此政權。', 'Proclaimed 16 Nov per common accounts; FRUS shows the republican government in existence.'))
ev('EV_FIUME_OCC', 'campaign', '1918-11-17', '義大利軍進入阜姆，協約國共同佔領', 'Italian troops enter Fiume; inter-Allied occupation', [('REGIME_IT', B), ('REGIME_SCS', B)], [], NOSRC)
ev('EV_LV', 'political', '1918-11-18', '拉脫維亞宣布獨立', 'Latvia declares independence', [('REGIME_LV', S_)], [], NOSRC)
ev('EV_SCS_SERBIA', 'political', '1918-11-24', '斯洛維尼亞人、克羅埃西亞人和塞爾維亞人國決議與塞爾維亞合併', 'The SCS State resolves to unite with Serbia', [('REGIME_SCS', S_), ('REGIME_RS', S_)], [], NOSRC)
ev('EV_PODGORICA', 'political', '1918-11-26', '波德戈里察議會廢黜蒙特內哥羅國王、決議與塞爾維亞合併', 'The Podgorica Assembly deposes the King of Montenegro and votes for union with Serbia',
   [('REGIME_MN_K', S_), ('REGIME_RS', S_)], [(P2, 'Doc. 274, pp. 349–350', '蒙特內哥羅方面照會：抗議波德戈里察議會（11 月 13／26 日）廢黜尼古拉國王、與塞爾維亞合併的決議。')],
   ('11 月 26 日（儒略曆 13 日）。', '26 Nov (13 Nov O.S.).'))
ev('EV_EE_WAR', 'war', '1918-11-28', '紅軍進攻納爾瓦，愛沙尼亞獨立戰爭開始', 'The Red Army attacks Narva; the Estonian War of Independence begins', [('REGIME_RSFSR', B), ('REGIME_EE', B)], [], NOSRC)
ev('EV_KSCS', 'political', '1918-12-01', '塞爾維亞人、克羅埃西亞人和斯洛維尼亞人王國在貝爾格勒宣布成立', 'The Kingdom of Serbs, Croats and Slovenes is proclaimed in Belgrade', [('REGIME_KSCS', S_), ('REGIME_RS', S_), ('REGIME_SCS', S_)],
   [(P2, 'Doc. 276, pp. 351–354', '塞爾維亞方面通知：攝政亞歷山大 1918-12-01 接受國民議會代表團的合併宣言，宣布成立統一王國。')])
ev('EV_ALBA_IULIA', 'political', '1918-12-01', '阿爾巴尤利亞國民大會決議外西凡尼亞等地與羅馬尼亞合併', 'The Alba Iulia National Assembly votes for the union of Transylvania with Romania', [('REGIME_RO', S_)],
   [(P2, 'Doc. 326, pp. 395–396', '羅馬尼亞方面通知：1918-12-01 阿爾巴尤利亞大會的合併決議。')])
ev('EV_IS', 'political', '1918-12-01', '丹冰聯合法生效，冰島成為與丹麥共主的主權王國', 'The Danish–Icelandic Act of Union takes effect; Iceland becomes a sovereign kingdom in personal union with Denmark', [('REGIME_IS', S_), ('REGIME_DK', S_)], [], NOSRC)
ev('EV_LV_WAR', 'war', '1918-12-01', '紅軍進入拉脫維亞，拉脫維亞獨立戰爭（1919-01-03 里加失守）', 'The Red Army invades Latvia; Latvian War of Independence (Riga falls on 3 Jan 1919)', [('REGIME_RSFSR', B), ('REGIME_LV', B)], [],
   nos('紅軍 1918-12 初進入拉脫維亞，日期只到月；本表取 12-01。', 'Red Army entered Latvia in early Dec 1918; only the month is certain (1 Dec used).'))
ev('EV_LT_WAR', 'war', '1918-12-15', '紅軍進入立陶宛，立陶宛—蘇維埃戰爭開始', 'The Red Army advances into Lithuania; the Lithuanian–Soviet War begins', [('REGIME_RSFSR', B), ('REGIME_LT', B)], [],
   nos('1918-12 中旬，日期只到月；本表取 12-15。', 'Mid-December 1918; only the month is certain (15 Dec used).'))
ev('EV_BY_SSR', 'political', '1919-01-01', '白俄羅斯蘇維埃社會主義共和國宣布成立', 'The Byelorussian Soviet Socialist Republic is proclaimed', [('REGIME_BY_SSR', S_), ('REGIME_BY_PR', S_)], [], NOSRC)
ev('EV_PL_SOV_WAR', 'war', '1919-02-14', '波蘭與蘇俄軍在別廖扎首次交火，波蘇戰爭開始', 'First clash of Polish and Soviet troops at Bereza Kartuska; the Polish–Soviet War begins', [('REGIME_PL', B), ('REGIME_RSFSR', B)], [], NOSRC)
ev('EV_UA_SSR', 'political', '1919-03-10', '烏克蘭蘇維埃社會主義共和國第一部憲法通過（OHM 起日）', 'The first constitution of the Ukrainian SSR is adopted (OHM start date)', [('REGIME_UA_SSR', S_), ('REGIME_UA_PR', S_)], [],
   nos('紅軍 1919-02-05 進入基輔；本表依 OHM 2848214 起日 3-10 切換。', 'Red Army in Kyiv from 5 Feb 1919; the OHM start date 10 Mar is used.'))
ev('EV_HU_SR', 'political', '1919-03-21', '匈牙利蘇維埃共和國成立（庫恩·貝拉）', 'The Hungarian Soviet Republic is proclaimed (Béla Kun)', [('REGIME_HU_SR', S_), ('REGIME_HU_PR', S_)],
   [(P12, 'Doc. 157, pp. 424–427', '布朗教授 1919-03-30 自布達佩斯致柯立芝：與「the new Soviet Republic in Hungary」教育人民委員昆菲的談話。')],
   ('3 月 21 日成立為通行說法；FRUS 報告日為 3 月 30 日。', 'Proclaimed 21 Mar per common accounts; FRUS report of 30 Mar.'))
ev('EV_HU_WAR', 'war', '1919-04-16', '羅馬尼亞軍（及 4 月底起捷克斯洛伐克軍）進攻匈牙利蘇維埃共和國', 'Romanian (and from late April Czechoslovak) forces attack the Hungarian Soviet Republic',
   [('REGIME_RO', B), ('REGIME_CS', B), ('REGIME_HU_SR', B)], [], NOSRC)
ev('EV_SMYRNA', 'campaign', '1919-05-15', '希臘軍在士麥那登陸', 'Greek troops land at Smyrna', [('REGIME_GR', B), ('REGIME_OT', B)], [], NOSRC)
ev('EV_VERSAILLES_SIGN', 'treaty', '1919-06-28', '凡爾賽和約簽字', 'The Treaty of Versailles is signed', [('REGIME_DE', S_), ('REGIME_FR3', S_), ('REGIME_UK_GBI', S_), ('REGIME_IT', S_), ('REGIME_US', S_), ('REGIME_PL', S_), ('REGIME_CS', S_), ('REGIME_BE', S_)],
   [(P13, 'Treaty of Peace with Germany（全文與註解）', '1919-06-28 於凡爾賽簽字的對德和約全文。')])
ev('EV_ZUNR_END', 'campaign', '1919-07-17', '西烏克蘭軍撤過茲布魯奇河，東加利西亞全歸波蘭軍控制', 'West Ukrainian forces withdraw across the Zbruch; Eastern Galicia under Polish control', [('REGIME_PL', B), ('REGIME_ZUNR', B)], [], NOSRC)
ev('EV_HU_SR_END', 'political', '1919-08-01', '匈牙利蘇維埃共和國垮台，羅馬尼亞軍逼近布達佩斯', 'The Hungarian Soviet Republic collapses as Romanian troops approach Budapest', [('REGIME_HU_SR', S_), ('REGIME_HU_PR', S_), ('REGIME_RO', B)], [],
   nos('羅馬尼亞軍 8 月 4 日進入布達佩斯、1919-11 至 1920-03 撤出（未畫）。', 'Romanian troops entered Budapest on 4 Aug and left by Mar 1920 (not drawn).'))
ev('EV_SAINT_GERMAIN_SIGN', 'treaty', '1919-09-10', '聖日耳曼條約簽字', 'The Treaty of Saint-Germain is signed', [('REGIME_AT_R1', S_), ('REGIME_FR3', S_), ('REGIME_UK_GBI', S_), ('REGIME_IT', S_), ('REGIME_US', S_)],
   [(P13, 'Status of the Treaties：Treaty of Saint-Germain-en-Laye, p. 30', '對奧和約 1919-09-10 簽字、1920-07-16 生效。')])
ev('EV_DANNUNZIO', 'campaign', '1919-09-12', '鄧南遮率志願軍佔領阜姆', "D'Annunzio's volunteers seize Fiume", [('REGIME_CARNARO', S_), ('REGIME_FIUME_IA', S_)], [], NOSRC)
# 1920
ev('EV_VERSAILLES', 'treaty', '1920-01-10', '凡爾賽和約生效：德國割讓領土，薩爾、但澤、梅梅爾交國際管理，什列斯威、上西里西亞等地待公投', 'The Treaty of Versailles enters into force: German cessions; the Saar, Danzig and Memel under international administration; plebiscites to come',
   [('REGIME_DE', S_), ('REGIME_FR3', S_), ('REGIME_UK_GBI', S_), ('REGIME_IT', S_), ('REGIME_PL', S_), ('REGIME_CS', S_), ('REGIME_BE', S_)],
   [(P13, 'Status of the Treaties, p. 29', '對德和約 1920-01-10 下午 4 時 15 分在巴黎交存批准書後生效。'),
    VERS('Part III, Section I', 'Arts. 27–30', '德國邊界。'), VERS('Part III, Section IV', 'Arts. 45–50', '薩爾盆地交國際聯盟託管。'), VERS('Part III, Section V', 'Art. 51', '亞爾薩斯—洛林自 1918-11-11 停戰日起歸還法國。'),
    VERS('Part III, Section VIII', 'Arts. 87–93', '承認波蘭獨立與德波邊界、上西里西亞公投（第 88 條）。'), VERS('Part III, Section X', 'Art. 99', '梅梅爾地區交協約國主要國處置。'),
    VERS('Part III, Section XI', 'Arts. 100–108', '但澤自由市。'), VERS('Part III, Section XII', 'Arts. 109–114', '什列斯威公投。')])
ev('EV_TARTU_EE', 'treaty', '1920-02-02', '塔爾圖和約：蘇俄承認愛沙尼亞獨立', 'Treaty of Tartu: Soviet Russia recognizes the independence of Estonia', [('REGIME_EE', S_), ('REGIME_RSFSR', S_)],
   [('SRC_LNTS_11', 'No. 289, p. 3', '愛沙尼亞與蘇俄和約，1920-02-02 於塔爾圖簽字（第 2 條承認獨立、第 3 條邊界）。')])
ev('EV_SCHLESWIG_1', 'political', '1920-02-10', '北什列斯威（第一區）公投，多數贊成歸丹麥', 'Plebiscite in North Schleswig (Zone I): majority for Denmark', [('REGIME_DK', S_), ('REGIME_DE', S_)],
   [VERS('Part III, Section XII', 'Arts. 109–110', '什列斯威分區公投的規定。')], ('日期與結果為通行說法（待查證）；條約只規定公投辦法。', 'Date and result per common accounts (pending); the treaty sets the procedure only.'))
ev('EV_HU_KINGDOM', 'political', '1920-03-01', '匈牙利國會選霍爾蒂為攝政，恢復王國', 'The Hungarian parliament elects Horthy regent; the kingdom is restored', [('REGIME_HU', S_), ('REGIME_HU_PR', S_)], [], NOSRC)
ev('EV_SCHLESWIG_2', 'political', '1920-03-14', '中什列斯威（第二區）公投，多數贊成留在德國', 'Plebiscite in Central Schleswig (Zone II): majority for Germany', [('REGIME_DK', S_), ('REGIME_DE', S_)],
   [VERS('Part III, Section XII', 'Arts. 109–110', '什列斯威分區公投的規定。')], ('日期與結果為通行說法（待查證）。', 'Date and result per common accounts (pending).'))
ev('EV_GNA', 'political', '1920-04-23', '土耳其大國民議會在安卡拉開議', 'The Grand National Assembly of Turkey opens in Ankara', [('REGIME_GNA', S_), ('REGIME_OT', S_)], [], NOSRC)
ev('EV_AZ_SSR', 'political', '1920-04-28', '紅軍進入巴庫，亞塞拜然蘇維埃社會主義共和國成立', 'The Red Army enters Baku; the Azerbaijan SSR is proclaimed', [('REGIME_AZ_SSR', S_), ('REGIME_AZ', S_), ('REGIME_RSFSR', B)], [], NOSRC)
ev('EV_SCHLESWIG_TRANSFER', 'political', '1920-06-15', '北什列斯威正式移交丹麥', 'North Schleswig is formally transferred to Denmark', [('REGIME_DK', S_), ('REGIME_DE', S_)],
   [VERS('Part III, Section XII', 'Arts. 110–111', '依公投結果劃定德丹新界。')], ('移交日為通行說法、也是 OHM 換版日（待查證）。', 'Transfer date per common accounts and OHM (pending).'))
ev('EV_BATUMI_END', 'campaign', '1920-07-07', '英軍撤出巴統，移交喬治亞', 'British troops leave Batumi and hand it over to Georgia', [('REGIME_UK_GBI', S_), ('REGIME_GE', S_)], [], NOSRC)
ev('EV_MOSCOW_LT', 'treaty', '1920-07-12', '莫斯科和約：蘇俄承認立陶宛獨立', 'Treaty of Moscow: Soviet Russia recognizes the independence of Lithuania', [('REGIME_LT', S_), ('REGIME_RSFSR', S_)],
   [('SRC_LNTS_3', 'No. 94, p. 105', '立陶宛與蘇俄和約及議定書，1920-07-12 於莫斯科簽字。')])
ev('EV_SAINT_GERMAIN', 'treaty', '1920-07-16', '聖日耳曼條約生效：奧地利承認繼承國，南提洛、的里雅斯特、伊斯特里亞歸義大利', 'The Treaty of Saint-Germain enters into force: Austria recognizes the successor states; South Tyrol, Trieste and Istria go to Italy',
   [('REGIME_AT_R1', S_), ('REGIME_IT', S_), ('REGIME_CS', S_), ('REGIME_KSCS', S_), ('REGIME_FR3', S_), ('REGIME_UK_GBI', S_)],
   [(P13, 'Status of the Treaties：Treaty of Saint-Germain-en-Laye, p. 30', '對奧和約 1920-07-16 生效。')])
ev('EV_SPA', 'political', '1920-07-28', '協約國大使會議裁定切申西里西亞分割（捷克斯洛伐克、波蘭）', 'The Conference of Ambassadors divides Cieszyn Silesia between Czechoslovakia and Poland', [('REGIME_CS', S_), ('REGIME_PL', S_)], [],
   nos('7-28 大使會議裁定為通行說法；OHM 爭議區迄日 8-28。', 'Decision of 28 Jul per common accounts; the OHM disputed area ends 28 Aug.'))
ev('EV_NEUILLY', 'treaty', '1920-08-09', '納伊條約生效：保加利亞割讓西色雷斯等地', 'The Treaty of Neuilly enters into force: Bulgaria cedes Western Thrace and other areas', [('REGIME_BG', S_), ('REGIME_GR', S_), ('REGIME_KSCS', S_)],
   [(P13, 'Status of the Treaties：Treaty of Neuilly-sur-Seine, p. 33', '對保和約 1919-11-27 簽字、1920-08-09 生效。')])
ev('EV_SEVRES', 'treaty', '1920-08-10', '色佛爾條約簽字（從未生效）；同日起委任統治地依 OHM 劃分', 'The Treaty of Sèvres is signed (never in force); mandate extents per OHM from the same day',
   [('REGIME_OT', S_), ('REGIME_GR', S_), ('REGIME_FR3', S_), ('REGIME_UK_GBI', S_), ('REGIME_IT', S_), ('REGIME_AM', S_)],
   [(P13, 'Status of the Treaties, p. 35', '對土和約（色佛爾）未生效。')], ('委任統治地起日依 OHM（1920-08-10），實際分配在 1920-04 聖雷莫會議（待查證）。', 'Mandate start dates per OHM; the allocation was made at San Remo in April 1920 (pending).'))
ev('EV_RIGA_LV', 'treaty', '1920-08-11', '里加和約：蘇俄承認拉脫維亞獨立', 'Treaty of Riga: Soviet Russia recognizes the independence of Latvia', [('REGIME_LV', S_), ('REGIME_RSFSR', S_)],
   [('SRC_LNTS_2', 'No. 67, p. 195', '拉脫維亞與蘇俄和約，莫斯科議定、1920-08-11 於里加簽字。')])
ev('EV_AM_TR_WAR', 'war', '1920-09-24', '土耳其（安卡拉）軍進攻亞美尼亞', 'Turkish (Ankara) forces attack Armenia', [('REGIME_GNA', B), ('REGIME_AM', B)], [], NOSRC)
ev('EV_CARINTHIA', 'political', '1920-10-10', '克恩頓公投：A 區多數贊成留在奧地利', 'Carinthian plebiscite: Zone A votes to remain in Austria', [('REGIME_AT_R1', S_), ('REGIME_KSCS', S_)], [],
   nos('聖日耳曼條約第 49–50 條規定公投（本批未查到條約原文頁）。', 'Arts. 49–50 of Saint-Germain provide for the plebiscite (treaty text page not located).'))
ev('EV_CLT', 'political', '1920-10-12', '熱利戈夫斯基佔領維爾紐斯，宣布中立陶宛共和國', 'Żeligowski seizes Vilnius and proclaims the Republic of Central Lithuania', [('REGIME_CLT', S_), ('REGIME_LT', B), ('REGIME_PL', S_)], [],
   nos('10-09 佔領、10-12 宣布為通行說法。', 'Vilnius taken 9 Oct, proclamation 12 Oct per common accounts.'))
ev('EV_TARTU_FI', 'treaty', '1920-10-14', '塔爾圖（多爾帕特）和約：芬蘭與蘇俄劃界，佩琴加歸芬蘭', 'Treaty of Tartu (Dorpat): Finland–Soviet border; Petsamo to Finland', [('REGIME_FI', S_), ('REGIME_RSFSR', S_)],
   [('SRC_LNTS_3', 'No. 91, p. 5', '芬蘭與蘇俄和約，1920-10-14 於多爾帕特簽字（第 4 條佩琴加）。')], ('生效日（1920-12-31）待查證；開發庫既有芬蘭紀錄從簽字日起。', 'Entry into force (31 Dec 1920) pending; the existing Finland record starts on signature.'))
ev('EV_RAPALLO', 'treaty', '1920-11-12', '拉帕洛條約：義大利與塞爾維亞人克羅埃西亞人和斯洛維尼亞人王國劃界，阜姆成為自由邦', 'Treaty of Rapallo: Italy–Kingdom SCS border; Fiume becomes a free state', [('REGIME_IT', S_), ('REGIME_KSCS', S_)],
   [('SRC_LNTS_18', 'No. 477, p. 387', '義大利與塞爾維亞人克羅埃西亞人和斯洛維尼亞人王國條約，1920-11-12 於拉帕洛簽字（邊界、薩拉、阜姆自由邦）。')])
ev('EV_DANZIG', 'political', '1920-11-15', '但澤自由市成立', 'The Free City of Danzig is constituted', [('REGIME_DANZIG', S_)],
   [VERS('Part III, Section XI', 'Arts. 100–102', '但澤自由市與國際聯盟保護的規定。')], ('成立日 11-15 為通行說法、也是 OHM 起日（待查證）。', 'Date per common accounts and OHM (pending).'))
ev('EV_CRIMEA', 'campaign', '1920-11-17', '弗蘭格爾軍撤出克里米亞，南俄政府結束', "Wrangel's army evacuates the Crimea; end of the Government of South Russia", [('REGIME_RSFSR', B), ('REGIME_SOUTH_RUSSIA', B)], [], NOSRC)
ev('EV_ALEXANDROPOL', 'treaty', '1920-12-02', '亞歷山德羅波爾條約；同日亞美尼亞蘇維埃化', 'Treaty of Alexandropol; Armenia is Sovietized the same day', [('REGIME_AM', S_), ('REGIME_GNA', S_), ('REGIME_AM_SSR', S_)], [], NOSRC)
ev('EV_FIUME_FS', 'political', '1920-12-30', '義軍驅逐鄧南遮（「血腥聖誕」），阜姆自由邦依拉帕洛條約成立', "Italian troops expel D'Annunzio ('Bloody Christmas'); the Free State of Fiume is set up under the Treaty of Rapallo",
   [('REGIME_FIUME_FS', S_), ('REGIME_CARNARO', S_), ('REGIME_IT', B)], [('SRC_LNTS_18', 'No. 477, p. 387（第 4 條）', '拉帕洛條約第 4 條承認阜姆自由邦。')],
   ('鄧南遮 12-29 至 31 投降為通行說法；起日依 OHM（12-30）。', "D'Annunzio surrendered on 29–31 Dec per common accounts; the OHM start is 30 Dec."))
ev('EV_GE_INV', 'war', '1921-02-12', '紅軍進攻喬治亞', 'The Red Army invades Georgia', [('REGIME_RSFSR', B), ('REGIME_GE', B)], [], NOSRC)
ev('EV_GE_SSR', 'political', '1921-02-25', '紅軍佔領提比里斯，喬治亞蘇維埃社會主義共和國成立', 'The Red Army takes Tbilisi; the Georgian SSR is proclaimed', [('REGIME_GE_SSR', S_), ('REGIME_GE', S_), ('REGIME_RSFSR', B)], [], NOSRC)
ev('EV_MOSCOW_TR', 'treaty', '1921-03-16', '莫斯科條約（蘇俄與安卡拉政府）', 'Treaty of Moscow (Soviet Russia and the Ankara government)', [('REGIME_RSFSR', S_), ('REGIME_GNA', S_)], [], NOSRC)
# 1921–1923
ev('EV_RIGA', 'treaty', '1921-03-18', '里加和約：波蘭與蘇俄、蘇烏克蘭劃界，波蘇戰爭結束', 'Peace of Riga: border between Poland and Soviet Russia and Ukraine; end of the Polish–Soviet War', [('REGIME_PL', S_), ('REGIME_RSFSR', S_), ('REGIME_UA_SSR', S_)],
   [('SRC_LNTS_6', 'No. 149, p. 51', '波蘭與蘇俄、蘇烏克蘭和約，1921-03-18 於里加簽字（第 2 條邊界）。')])
ev('EV_USIL_PLEB', 'political', '1921-03-20', '上西里西亞公投', 'Upper Silesia plebiscite', [('REGIME_DE', S_), ('REGIME_PL', S_)],
   [VERS('Part III, Section VIII', 'Art. 88 與附件', '上西里西亞公投的規定。')], ('日期為通行說法（待查證）。', 'Date per common accounts (pending).'))
ev('EV_TRIANON', 'treaty', '1921-07-26', '特里阿農條約生效：匈牙利承認新邊界', 'The Treaty of Trianon enters into force: Hungary accepts its new borders', [('REGIME_HU', S_), ('REGIME_RO', S_), ('REGIME_CS', S_), ('REGIME_KSCS', S_), ('REGIME_AT_R1', S_)],
   [(P13, 'Status of the Treaties：Treaty of Trianon, p. 34', '對匈和約 1920-06-04 簽字、1921-07-26 生效。'), ('SRC_LNTS_6', 'No. 152, p. 187', '和約全文。')])
ev('EV_RIF', 'political', '1921-09-18', '里夫共和國宣布成立', 'The Republic of the Rif is proclaimed', [('REGIME_RIF', S_), ('REGIME_ES_K', B)], [], ('未找到正式出處（待查證）；日期依 OHM 起日。', 'No formal source (pending); date per OHM.'))
ev('EV_LAJTA', 'political', '1921-10-04', '布爾根蘭的匈牙利非正規軍宣布萊塔班國', 'Hungarian irregulars in the Burgenland proclaim the Banate of Leitha', [('REGIME_LAJTA', S_)], [], NOSRC)
ev('EV_KARS', 'treaty', '1921-10-13', '卡爾斯條約：安卡拉政府與外高加索三蘇維埃共和國劃界', 'Treaty of Kars: border between the Ankara government and the three Transcaucasian Soviet republics',
   [('REGIME_GNA', S_), ('REGIME_GE_SSR', S_), ('REGIME_AM_SSR', S_), ('REGIME_AZ_SSR', S_), ('REGIME_RSFSR', S_)], [], NOSRC)
ev('EV_ANKARA', 'treaty', '1921-10-20', '安卡拉協定：法國與安卡拉政府停戰，法軍撤出奇里乞亞', 'Treaty of Ankara: France makes peace with the Ankara government and leaves Cilicia', [('REGIME_FR3', S_), ('REGIME_GNA', S_)], [], NOSRC)
ev('EV_USIL_DIV', 'political', '1921-10-20', '國際聯盟建議、大使會議決定分割上西里西亞', 'Upper Silesia is divided on the recommendation of the League of Nations', [('REGIME_DE', S_), ('REGIME_PL', S_)], [], NOSRC)
ev('EV_BURGENLAND', 'political', '1921-11-10', '布爾根蘭移交奧地利（萊塔班國結束）', 'The Burgenland is handed over to Austria (end of the Banate of Leitha)', [('REGIME_AT_R1', S_), ('REGIME_HU', S_), ('REGIME_LAJTA', S_)], [],
   nos('依 OHM 換版日；索普朗 12 月公投未分（待查證）。', 'OHM version date; the Sopron plebiscite in December not modeled (pending).'))
ev('EV_EG_K', 'political', '1922-02-28', '英國單方面宣布埃及獨立（3-15 福阿德一世稱王）', 'Britain unilaterally declares Egyptian independence (Fuad I king from 15 Mar)', [('REGIME_EG_K', S_), ('REGIME_UK_GBI', S_)], [], NOSRC)
ev('EV_TSFSR', 'political', '1922-03-12', '外高加索社會主義蘇維埃共和國聯盟成立', 'The Federative Union of Transcaucasian Soviet Republics is formed', [('REGIME_TSFSR', S_), ('REGIME_GE_SSR', S_), ('REGIME_AM_SSR', S_), ('REGIME_AZ_SSR', S_)], [], NOSRC)
ev('EV_CLT_ANNEX', 'political', '1922-04-18', '中立陶宛併入波蘭（依 OHM 換版日）', 'Central Lithuania is incorporated into Poland (OHM version date)', [('REGIME_CLT', S_), ('REGIME_PL', S_)], [],
   nos('維爾紐斯議會 1922-02-20 決議、波蘭國會 03-24 通過為通行說法；本表依 OHM 換版日 04-18。', 'Vilnius assembly 20 Feb, Polish Sejm 24 Mar per common accounts; OHM version date used.'))
ev('EV_USIL_TRANSFER', 'political', '1922-06-20', '上西里西亞東部移交波蘭', 'Eastern Upper Silesia is handed over to Poland', [('REGIME_DE', S_), ('REGIME_PL', S_)], [], ('未找到正式出處（待查證）；日期依 OHM 換版日。', 'No formal source (pending); OHM version date.'))
ev('EV_SMYRNA_FALL', 'campaign', '1922-09-09', '土耳其軍進入士麥那，希臘佔領結束', 'Turkish forces enter Smyrna; end of the Greek occupation', [('REGIME_GNA', B), ('REGIME_GR', B)],
   [(F22, 'Doc. 328', '駐士麥那總領事 1922-09-08 晚 10 時電：土耳其軍預計明晚或後天早上抵達。'), (F22, 'Doc. 330', '駐君士坦丁堡高級專員 1922-09-09 電：希臘總部撤到切什梅，美國驅逐艦已在士麥那。')])
ev('EV_MUDANYA', 'armistice', '1922-10-11', '穆達尼亞停戰協定：希臘撤出東色雷斯', 'Armistice of Mudanya: Greece evacuates Eastern Thrace', [('REGIME_GNA', S_), ('REGIME_GR', S_), ('REGIME_UK_GBI', S_), ('REGIME_FR3', S_), ('REGIME_IT', S_)], [], NOSRC)
ev('EV_SULTANATE_END', 'political', '1922-11-01', '大國民議會廢除蘇丹制，鄂圖曼帝國結束', 'The Grand National Assembly abolishes the sultanate; end of the Ottoman Empire', [('REGIME_GNA', S_), ('REGIME_OT', S_)], [], NOSRC)
ev('EV_IFS', 'political', '1922-12-06', '愛爾蘭自由邦成立', 'The Irish Free State is established', [('REGIME_IFS', S_), ('REGIME_UK_GBI', S_)], [], NOSRC)
ev('EV_USSR', 'political', '1922-12-30', '蘇聯成立：俄、烏、白俄、外高加索組成蘇維埃社會主義共和國聯盟', 'Creation of the USSR', [('REGIME_SU', S_), ('REGIME_RSFSR', S_), ('REGIME_UA_SSR', S_), ('REGIME_BY_SSR', S_), ('REGIME_TSFSR', S_)], [], NOSRC)
ev('EV_RUHR', 'campaign', '1923-01-11', '法、比軍佔領魯爾區', 'French and Belgian troops occupy the Ruhr', [('REGIME_FR3', B), ('REGIME_BE', B), ('REGIME_DE', B)],
   [(F23, 'Doc. 32', '駐巴黎大使 1923-01-10 下午 5 時電：法軍「明日」進入魯爾，由德古特將軍指揮、駐紮埃森一帶。'), (F23, 'Doc. 34', '德國大使 1923-01-11 新聞聲明：法比軍隊最遲明日佔領埃森與魯爾部分地區。')])
ev('EV_MEMEL', 'campaign', '1923-01-15', '梅梅爾起事，立陶宛控制梅梅爾地區', 'Klaipėda Revolt: Lithuania takes control of the Memel Territory', [('REGIME_LT', B), ('REGIME_MEMEL', B)], [],
   nos('1923-01-10 起事、01-15 法軍撤出為通行說法；開發庫既有立陶宛紀錄從 01-19 起，梅梅爾紀錄截在 01-19。大使會議 1923-02-16 承認（待查證）。', 'Revolt from 10 Jan, French withdrawal 15 Jan per common accounts; the existing Lithuania record starts 19 Jan.'))
ev('EV_LAUSANNE', 'treaty', '1923-07-24', '洛桑條約簽字：土耳其新邊界（取代色佛爾條約）', 'The Treaty of Lausanne is signed: the new borders of Turkey (replacing Sèvres)', [('REGIME_GNA', S_), ('REGIME_GR', S_), ('REGIME_UK', S_), ('REGIME_FR3', S_), ('REGIME_IT', S_)],
   [('SRC_LNTS_28', 'No. 701, p. 11', '英、法、義、日、希等國與土耳其和約，1923-07-24 於洛桑簽字。')], ('1924-08-06 生效（開發庫既有土耳其紀錄起日）。', 'In force 6 Aug 1924 (start of the existing Turkey record).'))
ev('EV_TR_REPUBLIC', 'political', '1923-10-29', '土耳其共和國宣布成立', 'The Republic of Turkey is proclaimed', [('REGIME_TR', S_), ('REGIME_GNA', S_)], [], NOSRC)

# ── 主權紀錄定義（優先序引擎）──
TWN = '兩次大戰之間 A 批 1918-11-12～1923-12-31'
DEFS = []
def d(ph, regime, start, end, geom, rid, prio=0, sev=None, eev=None, layer='de_jure', derived=None, loc=None, zh='', en='', label=None, hand=None):
    DEFS.append(dict(ph=ph, regime=regime, start=start, end=end, geom=g_of(geom) if isinstance(geom, (int, str)) else geom, rid=rid, prio=prio, sev=sev, eev=eev,
                     layer=layer, derived=derived or [rid], loc=loc or OL(rid), zh=zh, en=en, label=label or ph, hand=hand))
# 德國
NDE = '依 OHM 德國各版本（凡爾賽和約各條款逐步生效）。萊茵蘭協約國佔領（停戰協定與凡爾賽和約第 428–432 條）未另畫（待查證）。'
d('SOV_DE_A', 'REGIME_DE', '1918-11-09', START, 'SOV_DE_EMP_R', 2692425, prio=2, sev='EV_DE_REV', label='德國', loc=B2R['SOV_DE_EMP_R']['body']['geometryLocator'],
  zh='1918-11-09 宣布共和後的德國；幾何照抄 WW1 第二批德意志帝國紀錄（OHM 2692425）。', en='Germany after the proclamation of the republic; geometry copied from the WW1 batch-2 German Empire record.')
for i, (s, e, rid, sev, eev) in enumerate([(START, '1920-01-10', 2696519, None, 'EV_VERSAILLES'), ('1920-01-10', '1920-02-04', 2692483, 'EV_VERSAILLES', None),
        ('1920-02-04', '1920-06-15', 2696518, None, 'EV_SCHLESWIG_TRANSFER'), ('1920-06-15', '1920-08-15', 2696517, 'EV_SCHLESWIG_TRANSFER', None),
        ('1920-08-15', '1920-12-24', 2741459, None, None), ('1920-12-24', '1922-06-20', 2696516, None, 'EV_USIL_TRANSFER'), ('1922-06-20', END, 2696515, 'EV_USIL_TRANSFER', None)]):
    d(f'SOV_DE_{chr(66 + i)}', 'REGIME_DE', s, e, rid, rid, prio=2, sev=sev, eev=eev, label='德國', zh=NDE, en='Per OHM German Reich versions; the Allied Rhineland occupation is not drawn (pending).')
d('SOV_SAAR', 'REGIME_SAAR', '1920-01-10', END, 2690373, 2690373, prio=5, sev='EV_VERSAILLES', layer='not_sovereign', label='薩爾', zh='非主權：凡爾賽和約第 45–50 條，國際聯盟委員會治理 15 年。', en='Not sovereign: League of Nations governing commission (Versailles arts. 45–50).')
d('SOV_MEMEL', 'REGIME_MEMEL', '1920-01-10', '1923-01-19', 2691476, 2691476, prio=5, sev='EV_VERSAILLES', eev='EV_MEMEL', layer='not_sovereign', label='梅梅爾',
  zh='非主權：凡爾賽和約第 99 條，德國放棄給協約國主要國；1920-02 起法國代管。1923-01 立陶宛接管（迄日接開發庫既有立陶宛紀錄 01-19）。', en='Not sovereign: renounced by Germany to the Principal Allied Powers (art. 99); French administration from Feb 1920.')
d('SOV_DANZIG_ALLIED', 'REGIME_DANZIG_ALLIED', '1920-01-10', '1920-11-15', 2696571, 2696571, prio=5, sev='EV_VERSAILLES', eev='EV_DANZIG', layer='not_sovereign', label='但澤',
  zh='非主權：凡爾賽和約第 100 條德國放棄後、自由市成立前由協約國管理。範圍沿用 OHM 自由市 2696571。', en='Not sovereign: Allied administration between Versailles and the constitution of the Free City.')
d('SOV_DANZIG_A', 'REGIME_DANZIG', '1920-11-15', '1920-12-24', 2696571, 2696571, prio=5, sev='EV_DANZIG', label='但澤', zh='但澤自由市（1920-12-24 起接開發庫既有紀錄）。', en='Free City of Danzig (continues into the existing record from 24 Dec 1920).')
d('SOV_RUHR', 'REGIME_RUHR', '1923-01-11', END, 'RUHR', 2696515, prio=5, sev='EV_RUHR', layer='not_sovereign', label='魯爾佔領區', loc=f'{OL(2696515)} ∩ 魯爾區（{HAND}）', hand='RUHR_PTS：' + fmt(RUHR_PTS),
  zh='非主權：法比軍佔領的魯爾區（範圍為粗略近似，待查證）。1921-03 起已佔領的杜塞道夫、杜伊斯堡、魯爾奧特未另分。', en='Not sovereign: Franco-Belgian-occupied Ruhr (rough approximation, pending).')
d('SOV_MORESNET', 'REGIME_MORESNET', START, '1920-01-10', 2696520, 2696520, prio=5, eev='EV_VERSAILLES', label='中立莫雷斯內', zh='凡爾賽和約第 32 條歸比利時。', en='To Belgium under Versailles art. 32.')
# 西歐、北歐、北非
d('SOV_FR3_A', 'REGIME_FR3', START, '1918-11-22', 2866012, 2866012, label='法國', zh='1918-11-22 起接開發庫既有紀錄（含亞爾薩斯—洛林）；11-12～11-22 亞爾薩斯—洛林未畫（待查證）。',
  en='Continues into the existing record from 22 Nov 1918; Alsace-Lorraine 12–22 Nov not drawn (pending).')
d('SOV_BE_A', 'REGIME_BE', START, '1920-01-10', 2797729, 2797729, prio=1, eev='EV_VERSAILLES', label='比利時', zh='1920-01-10 起接開發庫既有紀錄（含奧伊彭—馬爾梅迪）。', en='Continues into the existing record from 10 Jan 1920.')
d('SOV_DK_A', 'REGIME_DK', START, '1920-06-15', 2869935, 2869935, label='丹麥', eev='EV_SCHLESWIG_TRANSFER', zh='OHM 2869935 迄日只到年（1920），本表截在北什列斯威移交日。', en='OHM end only gives the year; cut at the Schleswig transfer.')
d('SOV_DK_B', 'REGIME_DK', '1920-06-15', '1921-05-21', 2692238, 2692238, label='丹麥', sev='EV_SCHLESWIG_TRANSFER')
d('SOV_DK_C', 'REGIME_DK', '1921-05-21', END, 2850547, 2850547, label='丹麥')
d('SOV_IS', 'REGIME_IS', '1918-12-01', END, 2801981, 2801981, prio=1, sev='EV_IS', label='冰島', zh='OHM 起日只到年（1918）。', en='OHM start only gives the year.')
d('SOV_NO_A', 'REGIME_NO', START, '1921-01-01', 2692537, 2692537, label='挪威', zh='OHM 換版日只到年（1921）。', en='OHM version date only gives the year.')
d('SOV_NO_B', 'REGIME_NO', '1921-01-01', END, 2851797, 2851797, label='挪威')
d('SOV_SE', 'REGIME_SE', START, END, 2692524, 2692524, label='瑞典')
d('SOV_UK_GBI', 'REGIME_UK_GBI', START, '1922-12-06', 2828388, 2828388, label='英國', eev='EV_IFS',
  zh='1922-12-05 起開發庫既有「聯合王國」紀錄（不含南愛爾蘭）接手，12-05 這一天只剩南愛爾蘭。1919～1921 愛爾蘭獨立戰爭、1922 臨時政府未分（待查證）。', en='From 5 Dec 1922 the existing UK record takes over; the Irish War of Independence and Provisional Government are not split (pending).')
d('SOV_IFS', 'REGIME_IFS', '1922-12-06', END, 2697727, 2697727, prio=1, sev='EV_IFS', label='愛爾蘭自由邦')
d('SOV_ES_A', 'REGIME_ES_K', START, '1921-06-01', 2860486, 2860486, label='西班牙', zh='OHM 換版日只到月（1921-06）。', en='OHM version date only gives the month.')
d('SOV_ES_B', 'REGIME_ES_K', '1921-06-01', END, 2860485, 2860485, label='西班牙')
d('SOV_MA_ES_A', 'REGIME_MA_ES', START, '1921-06-01', 2860424, 2860424, prio=1, label='西屬摩洛哥')
d('SOV_MA_ES_B', 'REGIME_MA_ES', '1921-06-01', END, 2860423, 2860423, prio=1, label='西屬摩洛哥', zh='1921-07 阿努瓦勒戰役後西班牙失去里夫大部（見里夫共和國）。', en='After Annual (Jul 1921) Spain lost most of the Rif.')
d('SOV_RIF', 'REGIME_RIF', '1921-09-18', END, 2860425, 2860425, prio=5, sev='EV_RIF', layer='not_sovereign', label='里夫共和國', zh='非主權：未獲國際承認。', en='Not sovereign: unrecognized.')
d('SOV_MA_FR_A', 'REGIME_MA_FR', START, '1921-01-01', 2866016, 2866016, prio=1, label='法屬摩洛哥', zh='OHM 換版日只到年（1921）。', en='OHM version date only gives the year.')
d('SOV_MA_FR_B', 'REGIME_MA_FR', '1921-01-01', END, 2866015, 2866015, prio=1, label='法屬摩洛哥')
d('SOV_TN', 'REGIME_TN', START, END, 2690947, 2690947, prio=1, label='突尼西亞')
d('SOV_MR', 'REGIME_MR', START, END, 2917211, 2917211, label='茅利塔尼亞', zh='OHM 迄日 1920-12-04（改為殖民地），本表未分（待查證）。', en='OHM ends 4 Dec 1920 (colony); not split (pending).')
d('SOV_LY_TR', 'REGIME_LY_TR', START, END, 2690837, 2690837, label='的黎波里塔尼亞', zh='義大利實際控制僅限沿岸（待查證）。', en='Italian control limited to the coast (pending).')
d('SOV_LY_CY', 'REGIME_LY_CY', START, END, 2803190, 2803190, label='昔蘭尼加', zh='義大利實際控制僅限沿岸（待查證）。', en='Italian control limited to the coast (pending).')
d('SOV_EG_A', 'REGIME_EG', START, '1922-02-28', 2803205, 2803205, label='埃及', eev='EV_EG_K')
d('SOV_EG_K', 'REGIME_EG_K', '1922-02-28', END, 2803204, 2803204, sev='EV_EG_K', label='埃及', zh='英國保留國防、蘇伊士運河、蘇丹等事項（待查證）。', en='Britain reserved defence, the Suez Canal and the Sudan (pending).')
d('SOV_CY', 'REGIME_CY_ANNEX', START, END, 2848135, 2848135, prio=1, label='賽普勒斯')
d('SOV_US', 'REGIME_US', START, END, make_valid(shape(US['geometry'])), US['ohmRelationId'], label='美國', loc=US['geometryLocator'], derived=[-1])
# 義大利、阜姆、奧地利、匈牙利、捷克斯洛伐克
d('SOV_IT_A', 'REGIME_IT', START, '1920-07-16', 2696424, 2696424, prio=1, eev='EV_SAINT_GERMAIN', label='義大利')
d('SOV_IT_B', 'REGIME_IT', '1920-07-16', END, 2696325, 2696325, prio=1, sev='EV_SAINT_GERMAIN', label='義大利', zh='薩拉（扎達爾）依拉帕洛條約（1920-11-12）歸義大利，本表未另分（待查證）。', en='Zara per Rapallo (12 Nov 1920), not split (pending).')
d('SOV_IT_JULIAN', 'REGIME_IT_JULIAN', START, '1920-07-16', 'IT_JULIAN', 2696325, prio=5, eev='EV_SAINT_GERMAIN', layer='not_sovereign', label='義大利佔領的原奧匈領土',
  derived=[2696325, 2696424], loc=f'{OL(2696325)} − {OL(2696424)}', zh='非主權：依朱斯蒂別墅停戰協定佔領、聖日耳曼條約生效後併入義大利的南提洛、的里雅斯特、伊斯特里亞等地。達爾馬提亞佔領區未畫（待查證）。',
  en='Not sovereign: areas occupied under the Villa Giusti armistice and annexed after Saint-Germain; the Dalmatian zone is not drawn (pending).')
d('SOV_IT_AEGEAN', 'REGIME_IT_AEGEAN', START, '1921-01-01', 2830316, 2830316, prio=5, layer='not_sovereign', label='多德卡尼斯', zh='非主權：義大利軍事佔領（1921 起接開發庫既有紀錄；OHM 換版日只到年）。', en='Not sovereign: Italian military occupation; continues into the existing record from 1921.')
d('SOV_FIUME_IA', 'REGIME_FIUME_IA', '1918-11-17', '1919-09-12', 2696321, 2696321, prio=6, sev='EV_FIUME_OCC', eev='EV_DANNUNZIO', layer='not_sovereign', label='阜姆',
  zh='非主權：義、英、法、美共同佔領（義軍為主）。範圍沿用 OHM 阜姆自由邦 2696321（近似）。', en='Not sovereign: inter-Allied (mainly Italian) occupation; extent of the later Free State (approximate).')
d('SOV_CARNARO', 'REGIME_CARNARO', '1919-09-12', '1920-12-30', 2696321, 2696321, prio=6, sev='EV_DANNUNZIO', eev='EV_FIUME_FS', layer='not_sovereign', label='阜姆',
  zh='非主權：鄧南遮佔領（1920-09-08 宣布卡爾納羅攝政國），未獲承認。範圍近似。', en='Not sovereign: unrecognized; approximate extent.')
d('SOV_FIUME_FS', 'REGIME_FIUME_FS', '1920-12-30', END, 2696321, 2696321, prio=6, sev='EV_FIUME_FS', label='阜姆自由邦', zh='1922-03 法西斯政變後義軍進駐（未分，待查證）；1924-02-22 併入義大利（不在本批）。', en='The Fascist coup and Italian troops from March 1922 are not split (pending).')
d('SOV_AT_R1_A', 'REGIME_AT_R1', START, '1921-11-10', 2692711, 2692711, prio=1, sev='EV_DEAT', eev='EV_BURGENLAND', label='奧地利',
  zh='範圍依 OHM 2692711（聖日耳曼條約邊界，起日 1920-07-16，本表前推到 1918-11-12）；德意志奧地利主張的蘇台德等地未畫，克恩頓南部 1918-11～1920-10 南斯拉夫軍佔領未分（待查證）。',
  en='Extent per OHM 2692711 (Saint-Germain borders), extended back to 12 Nov 1918; claimed areas and the Yugoslav occupation of southern Carinthia are not drawn (pending).')
d('SOV_AT_R1_B', 'REGIME_AT_R1', '1921-11-10', '1922-10-01', 2695634, 2695634, prio=1, sev='EV_BURGENLAND', label='奧地利', zh='含布爾根蘭。1922-10-01 起接開發庫既有紀錄。', en='Including the Burgenland; continues into the existing record from 1 Oct 1922.')
d('SOV_LAJTA', 'REGIME_LAJTA', '1921-10-04', '1921-11-10', 2747802, 2747802, prio=6, sev='EV_LAJTA', eev='EV_BURGENLAND', layer='not_sovereign', label='萊塔班國', zh='非主權：未獲承認。', en='Not sovereign: unrecognized.')
HUN = '範圍一律用特里阿農邊界（OHM 2693462，起日 1921-07-26，本表前推）；1918～1920 實際控制範圍（羅馬尼亞、捷克斯洛伐克、塞爾維亞軍佔領線，斯洛伐克蘇維埃共和國、巴拉尼亞）未畫（待查證）。'
HUE = 'Trianon extent (OHM 2693462) used throughout; actual lines of control 1918–1920 are not drawn (pending).'
d('SOV_HU_PR_A', 'REGIME_HU_PR', START, '1919-03-21', 2693462, 2693462, prio=2, eev='EV_HU_SR', label='匈牙利', zh=HUN, en=HUE)
d('SOV_HU_SR', 'REGIME_HU_SR', '1919-03-21', '1919-08-01', 2693462, 2693462, prio=2, sev='EV_HU_SR', eev='EV_HU_SR_END', label='匈牙利', zh=HUN, en=HUE)
d('SOV_HU_PR_B', 'REGIME_HU_PR', '1919-08-01', '1920-03-01', 2693462, 2693462, prio=2, sev='EV_HU_SR_END', eev='EV_HU_KINGDOM', label='匈牙利', zh='1919-08 以後的過渡政府歸在此政權（待查證）。' + HUN, en=HUE)
d('SOV_HU_A', 'REGIME_HU', '1920-03-01', '1921-11-10', 2693462, 2693462, prio=2, sev='EV_HU_KINGDOM', label='匈牙利', zh='1921-11-10 起接開發庫既有紀錄。', en='Continues into the existing record from 10 Nov 1921.')
CSN = '範圍依 OHM 捷克斯洛伐克各版本；斯洛伐克南部 1919 年控制線變化未畫（待查證）。'
d('SOV_CS_A', 'REGIME_CS', START, '1920-02-04', 2747877, 2747877, prio=3.5, label='捷克斯洛伐克', zh=CSN, en='Per OHM versions.')
d('SOV_CS_B', 'REGIME_CS', '1920-02-04', '1920-05-19', 2747876, 2747876, prio=3.5, label='捷克斯洛伐克', zh=CSN, en='Per OHM versions.')
d('SOV_CS_C', 'REGIME_CS', '1920-05-19', '1920-08-10', 2693465, 2693465, prio=3.5, label='捷克斯洛伐克', zh=CSN, en='Per OHM versions.')
d('SOV_CS_D', 'REGIME_CS', '1920-08-10', END, 2747893, 2747893, prio=3.5, label='捷克斯洛伐克', zh=CSN, en='Per OHM versions.')
d('SOV_CIESZYN', 'REGIME_CIESZYN', START, '1920-08-28', 2747891, 2747891, prio=6, layer='not_sovereign', label='切申爭議區',
  zh='非主權：捷克斯洛伐克與波蘭爭議區（1918-11 地方協議分治、1919-01 七日戰爭，未分）。迄日依 OHM（大使會議 7-28 裁定，待查證）。', en='Not sovereign: disputed between Czechoslovakia and Poland; end date per OHM (pending).')
# 巴爾幹
d('SOV_SCS_A', 'REGIME_SCS', START, '1918-11-24', 2747879, 2747879, prio=3, eev='EV_SCS_SERBIA', layer='not_sovereign', label='斯洛維尼亞人、克羅埃西亞人和塞爾維亞人國')
d('SOV_SCS_B', 'REGIME_SCS', '1918-11-24', '1918-12-01', 2747878, 2747878, prio=3, sev='EV_SCS_SERBIA', eev='EV_KSCS', layer='not_sovereign', label='斯洛維尼亞人、克羅埃西亞人和塞爾維亞人國')
d('SOV_RS_A', 'REGIME_RS', START, '1918-11-26', 2746681, 2746681, prio=3, eev='EV_PODGORICA', label='塞爾維亞', zh='伏伊伏丁那（11-25 決議併入塞爾維亞）未畫（待查證）。', en='Vojvodina not drawn (pending).')
d('SOV_RS_B', 'REGIME_RS', '1918-11-26', '1918-12-01', 'RS_MN', 2746681, prio=3, sev='EV_PODGORICA', eev='EV_KSCS', label='塞爾維亞', derived=[2746681, 2739656], loc=f'{OL(2746681)} ∪ {OL(2739656)}',
  zh='波德戈里察議會決議後含蒙特內哥羅。', en='Including Montenegro after the Podgorica Assembly.')
d('SOV_MN', 'REGIME_MN_K', START, '1918-11-26', 2739656, 2739656, prio=4, eev='EV_PODGORICA', label='蒙特內哥羅')
d('SOV_KSCS_A', 'REGIME_KSCS', '1918-12-01', '1922-10-01', 2747828, 2747828, prio=3, sev='EV_KSCS', label='塞爾維亞人、克羅埃西亞人和斯洛維尼亞人王國',
  zh='範圍依 OHM 2747828（起日 1920-11-12 拉帕洛條約，本表前推到 1918-12-01）；1918～1920 的佔領線（義大利達爾馬提亞區、克恩頓、巴拉尼亞）未分（待查證）。', en='Extent per OHM 2747828 (from Rapallo), extended back to 1 Dec 1918; occupation lines are not drawn (pending).')
d('SOV_KSCS_B', 'REGIME_KSCS', '1922-10-01', END, 2858752, 2858752, prio=3, label='塞爾維亞人、克羅埃西亞人和斯洛維尼亞人王國')
d('SOV_AL_A', 'REGIME_AL_PR', START, '1918-11-24', 2855613, 2855613, prio=2, label='阿爾巴尼亞')
d('SOV_AL_B', 'REGIME_AL_PR', '1918-11-24', END, 2800556, 2800556, prio=2, label='阿爾巴尼亞', zh='1918～1920 義大利（發羅拉，至 1920-08）、法國（科爾察，至 1920-06）佔領與 1920-01 盧什涅大會後的政府未分（待查證）。', en='Italian and French occupations and the Lushnjë government are not split (pending).')
d('SOV_RO_A', 'REGIME_RO', START, '1918-12-01', 'RO_A', 2693260, prio=3, eev='EV_ALBA_IULIA', label='羅馬尼亞', derived=[2693260, 2694154], loc=f'{OL(2693260)} ∪ 比薩拉比亞（WW1 第二批 SOV_RO_BESS 幾何）',
  zh='含 1918-04 合併的比薩拉比亞與南多布羅加；布科維納（11-28 合併）與外西凡尼亞（12-01）合併前未畫（待查證）。', en='Including Bessarabia and Southern Dobruja; Bukovina and Transylvania before their unions are not drawn (pending).')
d('SOV_RO_B', 'REGIME_RO', '1918-12-01', '1921-01-01', 2693464, 2693464, prio=3, sev='EV_ALBA_IULIA', label='羅馬尼亞', zh='OHM 2693464 起日只到年（1919），本表從阿爾巴尤利亞大會起。1921-01-01 起接開發庫既有紀錄。', en='OHM start only gives 1919; from Alba Iulia. Continues into the existing record from 1921.')
d('SOV_BG_A', 'REGIME_BG', START, '1919-11-27', 2746680, 2746680, prio=4, label='保加利亞', zh='西色雷斯 1919-10 移交協約國管理（未分，待查證）。1919-11-27 起接開發庫既有紀錄。', en='Western Thrace under Allied administration from Oct 1919 not split (pending).')
d('SOV_GR_A', 'REGIME_GR', START, '1920-08-10', 2863749, 2863749, prio=1, eev='EV_SEVRES', label='希臘', zh='OHM 2863749 起日只到年（1919，含西色雷斯）；西色雷斯在 1919-11-27 前由保加利亞紀錄覆蓋，1919-11～1920-05 協約國管理未分（待查證）。',
  en='OHM start only gives 1919; Western Thrace covered by Bulgaria until 27 Nov 1919; the inter-Allied administration is not split (pending).')
d('SOV_GR_B', 'REGIME_GR', '1920-08-10', '1922-10-11', 2863750, 2863750, prio=1, sev='EV_SEVRES', eev='EV_MUDANYA', label='希臘',
  zh='OHM 2863750 是色佛爾條約範圍（未生效），本表扣掉士麥那區與東色雷斯（另列希臘佔領區）。', en='OHM 2863750 reflects Sèvres (never in force); the Smyrna zone and Eastern Thrace are separate Greek-occupied records.')
d('SOV_GR_C', 'REGIME_GR', '1922-10-11', END, 2863749, 2863749, prio=1, sev='EV_MUDANYA', label='希臘')
d('SOV_SMYRNA', 'REGIME_SMYRNA', '1919-05-15', '1922-09-09', 'SMYRNA', 2863750, prio=5, sev='EV_SMYRNA', eev='EV_SMYRNA_FALL', layer='not_sovereign', label='士麥那區',
  derived=[2863750, 2863749], loc=f'({OL(2863750)} − {OL(2863749)}) 的安納托利亞部分', hand='依代表點分歐亞兩部分：y ≥ 40.45 或（y ≥ 39.95 且 x < 26.9）算色雷斯',
  zh='非主權：希臘軍佔領（色佛爾條約規定的士麥那區範圍，近似；1921 年希軍推進到薩卡里亞河一帶未畫，待查證）。', en='Not sovereign: Greek occupation (Sèvres zone, approximate); the 1921 advance is not drawn (pending).')
d('SOV_ETHRACE', 'REGIME_ETHRACE', '1920-08-10', '1922-10-11', 'ETHRACE', 2863750, prio=5, sev='EV_SEVRES', eev='EV_MUDANYA', layer='not_sovereign', label='東色雷斯',
  derived=[2863750, 2863749], loc=f'({OL(2863750)} − {OL(2863749)}) 的歐洲部分', hand='同士麥那區',
  zh='非主權：希臘軍佔領（1920-07 進入阿德里安堡；本表從色佛爾條約簽字起，近似，待查證）。', en='Not sovereign: Greek occupation (from Sèvres; approximate, pending).')
# 波羅的海、波蘭、蘇俄
d('SOV_BALTIC_A', 'REGIME_BALTIC_OCC', START, '1918-11-18', 'SOV_BALTIC', 2744426, prio=1, eev='EV_LV', layer='not_sovereign', label='庫爾蘭與利沃尼亞', loc=B2R['SOV_BALTIC']['body']['geometryLocator'], derived=[2744426, 2869679],
  zh='非主權：停戰後德軍仍駐（幾何照抄 WW1 第二批）。', en='Not sovereign: German troops still present after the armistice (geometry from WW1 batch 2).')
d('SOV_FI_D', 'REGIME_FI', START, '1920-10-14', 2959043, 2959043, prio=2, eev='EV_TARTU_FI', label='芬蘭', zh='1920-10-14 起接開發庫既有紀錄（含佩琴加）。', en='Continues into the existing record from 14 Oct 1920.')
d('SOV_LV_A', 'REGIME_LV', '1918-11-18', '1920-01-01', 2704702, 2704702, prio=2, sev='EV_LV', label='拉脫維亞',
  zh='範圍依 OHM 2704702（起日 1920-01-01，本表前推）；1919 年紅軍、德國志願軍與白軍的佔領未畫（待查證）。1920-01-01 起接開發庫既有紀錄。', en='Extent per OHM, extended back; 1919 occupations not drawn (pending).')
d('SOV_LT_A', 'REGIME_LT', START, '1923-01-19', 2693086, 2693086, prio=2, label='立陶宛',
  zh='範圍依 OHM 2693086（起日只到年 1920，本表前推）；1919～1920 維爾紐斯先後由紅軍、波蘭、立陶宛控制未畫（待查證）。1923-01-19 起接開發庫既有紀錄。', en='Extent per OHM, extended back; the changing control of Vilnius is not drawn (pending).')
d('SOV_CLT', 'REGIME_CLT', '1920-10-12', '1922-04-18', 'CLT', 2855672, prio=6, sev='EV_CLT', eev='EV_CLT_ANNEX', layer='not_sovereign', label='中立陶宛', loc=f'{OL(2855672)} ∩ 維爾紐斯地區（{HAND}）', hand='CLT_PTS：' + fmt(CLT_PTS),
  zh='非主權：波蘭軍扶植，未獲承認（範圍為粗略近似，待查證）。', en='Not sovereign: Polish-backed, unrecognized (rough approximation, pending).')
d('SOV_ZUNR', 'REGIME_ZUNR', '1918-11-13', '1919-07-17', 'ZUNR', 2855672, prio=6, sev='EV_ZUNR', eev='EV_ZUNR_END', layer='not_sovereign', label='西烏克蘭', loc=f'{OL(2855672)} ∩ 東加利西亞（{HAND}）', hand='ZUNR_PTS：' + fmt(ZUNR_PTS),
  zh='非主權：未獲承認。範圍取東加利西亞（粗略近似；實際控制線隨波烏戰爭變動，利沃夫 1918-11-22 起由波蘭控制，北布科維納未含，待查證）。', en='Not sovereign: unrecognized; Eastern Galicia roughly (pending).')
PLN = '東界在里加條約前未定，暫用 1922 年里加線近似（OHM 2855672，待查證）。OHM 1920～1921 年各版波蘭關係（2855675、2855669、2855670、2855671）外框缺東界、組不成多邊形，未用。'
PLE = 'Eastern border undefined before Riga; approximated by the 1922 Riga line (OHM 2855672, pending). The OHM 1920–21 Poland relations are open rings and were not used.'
d('SOV_PL_A', 'REGIME_PL', START, '1922-06-20', 2855672, 2855672, prio=1, label='波蘭', eev='EV_USIL_TRANSFER', zh=PLN, en=PLE)
d('SOV_PL_B', 'REGIME_PL', '1922-06-20', END, 2741472, 2741472, prio=1, sev='EV_USIL_TRANSFER', label='波蘭', zh='含上西里西亞東部。1924-06-22 起開發庫既有紀錄，之間由 B 批補上。', en='Including eastern Upper Silesia.')
d('SOV_UA_PR', 'REGIME_UA_PR', START, '1919-03-10', 2694815, 2694815, prio=2.5, eev='EV_UA_SSR', label='烏克蘭',
  zh='範圍依 OHM 2694815（迄日 1919-01-22，本表延到 3-10）；1918-12 起督政府、1919-01 起與紅軍內戰未分（待查證）。', en='Extent per OHM 2694815, extended to 10 Mar 1919; the Directorate and the civil war are not split (pending).')
d('SOV_UA_SSR', 'REGIME_UA_SSR', '1919-03-10', '1922-12-30', 2848214, 2848214, prio=1, sev='EV_UA_SSR', eev='EV_USSR', label='烏克蘭',
  zh='範圍依 OHM 2848214；1919～1920 鄧尼金、波蘭軍與烏克蘭人民共和國的控制區未畫（待查證）。', en='Extent per OHM; White, Polish and UPR control in 1919–20 not drawn (pending).')
d('SOV_BY_PR', 'REGIME_BY_PR', START, '1919-01-01', 2957449, 2957449, prio=2, eev='EV_BY_SSR', layer='not_sovereign', label='白俄羅斯', zh='非主權：未獲承認。', en='Not sovereign: unrecognized.')
d('SOV_BY_SSR', 'REGIME_BY_SSR', '1919-01-01', '1922-12-30', 2848186, 2848186, prio=0, sev='EV_BY_SSR', eev='EV_USSR', label='白俄羅斯',
  zh='範圍依 OHM 2848186（起日 1920-07-31，本表前推），扣掉波蘭；1919～1920 波蘭軍佔領明斯克等地未畫（待查證）。', en='Extent per OHM, extended back; Polish occupation of Minsk 1919–20 not drawn (pending).')
RSN = '依 OHM 俄羅斯蘇維埃共和國各版本（框外部分裁掉）；內戰期間白軍控制區只畫南俄政府（1920），其餘未畫（待查證）。'
for i, (s, e, rid) in enumerate([(START, '1919-03-10', 2959042), ('1919-03-10', '1920-04-06', 2957450), ('1920-04-06', '1920-04-28', 2958036), ('1920-04-28', '1920-10-14', 2957458),
                                  ('1920-10-14', '1921-08-14', 2959040), ('1921-08-14', '1922-03-12', 2957470), ('1922-03-12', '1922-11-15', 2957457), ('1922-11-15', '1922-12-30', 2958035)]):
    d(f'SOV_RSFSR_{chr(71 + i)}', 'REGIME_RSFSR', s, e, rid, rid, prio=-1, eev='EV_USSR' if e == '1922-12-30' else None, label='蘇俄', zh=RSN, en='Per OHM RSFSR versions; White-held areas other than South Russia (1920) not drawn (pending).')
d('SOV_SU', 'REGIME_SU', '1922-12-30', END, 2800978, 2800978, prio=-1, sev='EV_USSR', label='蘇聯', zh='1924 年以後由 B 批接續。', en='Continues in batch B.')
d('SOV_SOUTH_RUSSIA', 'REGIME_SOUTH_RUSSIA', '1920-04-04', '1920-11-17', 2854270, 2854270, prio=5, eev='EV_CRIMEA', layer='not_sovereign', label='南俄政府', zh='非主權：未獲承認的白軍政府（克里米亞）。', en='Not sovereign: unrecognized White government (Crimea).')
# 外高加索
d('SOV_MRNC', 'REGIME_MRNC', START, '1919-09-01', 2891769, 2891769, prio=2, label='北高加索山地共和國', zh='OHM 迄日只到月（1919-09，鄧尼金軍佔領）。', en='OHM end only gives the month.')
d('SOV_GE_A', 'REGIME_GE', START, '1921-02-25', 2698086, 2698086, prio=2, eev='EV_GE_SSR', label='喬治亞')
d('SOV_GE_SSR_A', 'REGIME_GE_SSR', '1921-02-25', '1921-03-31', 2698086, 2698086, prio=2, sev='EV_GE_SSR', label='喬治亞')
d('SOV_GE_SSR_B', 'REGIME_GE_SSR', '1921-03-31', '1921-10-13', 2957462, 2957462, prio=2, label='喬治亞')
d('SOV_GE_SSR_C', 'REGIME_GE_SSR', '1921-10-13', '1921-12-16', 2957465, 2957465, prio=2, sev='EV_KARS', label='喬治亞')
d('SOV_GE_SSR_D', 'REGIME_GE_SSR', '1921-12-16', '1922-03-12', 2957461, 2957461, prio=2, eev='EV_TSFSR', label='喬治亞')
d('SOV_ABKHAZ', 'REGIME_ABKHAZ_SSR', '1921-03-31', '1921-12-16', 2957464, 2957464, prio=5, layer='not_sovereign', label='阿布哈茲', zh='非主權：名義上獨立的蘇維埃共和國，1921-12-16 以條約加入喬治亞（待查證）。', en='Not sovereign: nominally separate Soviet republic (pending).')
d('SOV_BATUMI', 'REGIME_BATUMI', '1918-12-01', '1920-07-07', 2698257, 2698257, prio=5, eev='EV_BATUMI_END', layer='not_sovereign', label='巴統', zh='非主權：英軍佔領。OHM 起日只到月（1918-12）；迄日依英軍撤出（OHM 迄日 1921-03-18，待查證）。', en='Not sovereign: British occupation; dates approximate (pending).')
d('SOV_AZ_A', 'REGIME_AZ', START, '1920-04-28', 2698117, 2698117, prio=2, eev='EV_AZ_SSR', label='亞塞拜然')
d('SOV_AZ_SSR_A', 'REGIME_AZ_SSR', '1920-04-28', '1921-10-13', 2697987, 2697987, prio=2, sev='EV_AZ_SSR', eev='EV_KARS', label='亞塞拜然')
d('SOV_AZ_SSR_B', 'REGIME_AZ_SSR', '1921-10-13', '1922-03-12', 2697988, 2697988, prio=2, sev='EV_KARS', eev='EV_TSFSR', label='亞塞拜然')
d('SOV_AM_A', 'REGIME_AM', START, '1920-12-02', 2698116, 2698116, prio=3, eev='EV_ALEXANDROPOL', label='亞美尼亞', zh='範圍依 OHM 2698116（巴統條約後的範圍）；1919～1920 控制卡爾斯一帶未畫（待查證）。OHM 2863796（色佛爾／威爾遜邊界）未用。', en='Per OHM 2698116; Kars 1919–20 not drawn (pending); the Sèvres/Wilsonian version is not used.')
d('SOV_AM_SSR', 'REGIME_AM_SSR', '1920-12-02', '1922-03-12', 2698022, 2698022, prio=3, sev='EV_ALEXANDROPOL', eev='EV_TSFSR', label='亞美尼亞', zh='範圍依 OHM 2698022（卡爾斯條約後，起日 1921-10-13，本表前推）。', en='Per OHM 2698022 (post-Kars), extended back.')
d('SOV_TSFSR', 'REGIME_TSFSR', '1922-03-12', '1922-12-30', 2698093, 2698093, prio=2, sev='EV_TSFSR', eev='EV_USSR', label='外高加索')
# 鄂圖曼、土耳其、委任統治地
d('SOV_OT_G', 'REGIME_OT', START, '1920-08-10', 'SOV_OT_F', 2920989, prio=0, eev='EV_SEVRES', label='鄂圖曼帝國', loc=B2R['SOV_OT_F']['body']['geometryLocator'], derived=[2920989, 2848136, 2830316, 2855613],
  zh='幾何照抄 WW1 第二批（穆德羅斯停戰後）。1918～1920 協約國佔領的伊斯坦堡、敘利亞、伊拉克、巴勒斯坦（OETA）與 1920-04 起安卡拉政府的實際控制未分（待查證）。',
  en='Geometry from WW1 batch 2; Allied occupations (OETA) and the Ankara government are not split (pending).')
d('SOV_OT_H', 'REGIME_OT', '1920-08-10', '1922-11-01', 2958040, 2958040, prio=0, sev='EV_SEVRES', eev='EV_SULTANATE_END', label='鄂圖曼帝國',
  zh='範圍依 OHM 2958040（安納托利亞與東色雷斯；色佛爾條約版 2863740 因條約未生效未用）。安卡拉大國民議會政府實際控制大部分安納托利亞，未另分（待查證）。', en='Per OHM 2958040 (the Sèvres version 2863740 is not used); the Ankara government is not split (pending).')
d('SOV_GNA', 'REGIME_GNA', '1922-11-01', '1923-10-29', 2958039, 2958039, prio=0, sev='EV_SULTANATE_END', eev='EV_TR_REPUBLIC', label='土耳其')
d('SOV_TR_A', 'REGIME_TR', '1923-10-29', END, 2958039, 2958039, prio=0, sev='EV_TR_REPUBLIC', label='土耳其', zh='1924-08-06 起開發庫既有紀錄；之間由 B 批補上。', en='The existing record starts 6 Aug 1924; batch B fills the gap.')
MAND = '非主權：國際聯盟委任統治地（委任統治書 1922～1923 年才生效，起日依 OHM，待查證）。'
MANE = 'Not sovereign: League of Nations mandate (start per OHM; mandates in force 1922–23, pending).'
d('SOV_LEVANT', 'REGIME_LEVANT', '1920-08-10', '1920-09-01', 2863754, 2863754, prio=1, sev='EV_SEVRES', layer='not_sovereign', label='法屬敘利亞黎巴嫩', zh=MAND, en=MANE)
d('SOV_LEBANON', 'REGIME_LEBANON', '1920-09-01', END, 2831357, 2831357, prio=2, layer='not_sovereign', label='大黎巴嫩', zh=MAND, en=MANE)
d('SOV_DAMASCUS_A', 'REGIME_DAMASCUS', '1920-09-01', '1921-05-01', 2863995, 2863995, prio=1, layer='not_sovereign', label='大馬士革國', zh=MAND, en=MANE)
d('SOV_DAMASCUS_B', 'REGIME_DAMASCUS', '1921-05-01', '1922-06-28', 2863994, 2863994, prio=1, layer='not_sovereign', label='大馬士革國', zh=MAND, en=MANE)
d('SOV_ALEPPO', 'REGIME_ALEPPO', '1920-09-01', '1922-06-28', 2864000, 2864000, prio=1, layer='not_sovereign', label='阿勒坡國', zh=MAND + '阿拉維國（1920-09 起）OHM 無範圍，未畫。', en=MANE)
d('SOV_DRUZE_A', 'REGIME_DRUZE', '1921-05-01', '1922-03-04', 2864007, 2864007, prio=2, layer='not_sovereign', label='德魯茲山國', zh=MAND, en=MANE)
d('SOV_DRUZE_B', 'REGIME_DRUZE', '1922-03-04', END, 2864006, 2864006, prio=2, layer='not_sovereign', label='德魯茲山國', zh=MAND, en=MANE)
d('SOV_SYR_FED', 'REGIME_SYR_FED', '1922-06-28', END, 2863992, 2863992, prio=1, layer='not_sovereign', label='敘利亞聯邦', zh=MAND, en=MANE)
d('SOV_PALESTINE', 'REGIME_PALESTINE', '1920-08-10', END, 2848316, 2848316, prio=1, sev='EV_SEVRES', layer='not_sovereign', label='巴勒斯坦', zh=MAND, en=MANE)
d('SOV_TRANSJORDAN', 'REGIME_TRANSJORDAN', '1920-08-10', END, 2848317, 2848317, prio=1, sev='EV_SEVRES', layer='not_sovereign', label='外約旦', zh=MAND + '1921-04 才成立酋長國（待查證）。', en=MANE)
d('SOV_IRAQ', 'REGIME_IRAQ', '1920-08-10', END, 2839465, 2839465, prio=1, sev='EV_SEVRES', layer='not_sovereign', label='伊拉克', zh=MAND, en=MANE)

# 開發庫既有紀錄（prio 9，不送出，只扣除與 QA）
FIXED = [dict(ph=f"DB:{r['slug']}", geom=make_valid(shape(r['geometry'])), start=r['start'], end=r['end'] or '9999-12-31', prio=9, label=r['slug'], sev=None, eev=None, derived=[])
         for r in ROWS if r['start'] < END and (r['end'] or '9999') > START]

# ── 引擎（同 WW1 第二批）──
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
for i, s in enumerate(SEGS):   # 同一政權同期只能有一筆主權紀錄
    for t in SEGS[i + 1:]:
        if t['x']['regime'] == s['x']['regime'] and t['start'] < s['end'] and s['start'] < t['end']:
            raise SystemExit(f"同政權重疊：{s['ph']} {t['ph']}")

def lic(rids):
    rids = [r for r in rids if r in MAN]
    cc_by = any(MAN[r]['geometry_license'] == 'cc_by' for r in rids)
    attrs = sorted({a for r in rids for a in (MAN[r]['attribution'] or '').split('; ') if a})
    return ('cc_by' if cc_by else 'cc0'), ('; '.join(attrs) or None), sum(MAN[r]['osm_derived_way_count'] for r in rids)
# OHM 清單裡沒有的關係（WW1 第一、二批幾何）：從第二批請求本文抄 OHM 欄位
FALLBACK = {2692425: B2R['SOV_DE_EMP_R']['body'], 2744426: B2R['SOV_BALTIC']['body']}
GEOM = {}
def ref(e): return ('{{%s}}' % e) if e else None
def endnote(end):
    return ('到 1923-12-31（本批試驗期間終點，無迄事件）。', ' Until 31 Dec 1923 (end of this batch).') if end == END else ('', '')

# 唯一修正：德意志帝國迄日改 1918-11-09（先撤後增）
r = copy.deepcopy(B2R['SOV_DE_EMP_R']); b = r['body']
b['validPeriod']['end'] = '1918-11-09'; b['endEventId'] = '{{EV_DE_REV}}'
b['note'] = {'zh-Hant': '起於 1908-10-06（WW1 第一批試驗期間起點，不是政權起日）。1918-11-09 德國革命、宣布共和，之後改為「德意志國」（兩次大戰之間 A 批）。',
             'en': 'From 6 Oct 1908 (start of WW1 batch 1, not of the regime). Ends with the German revolution of 9 Nov 1918; continued as the German Reich (interwar batch A).'}
b['provenance']['trialWindow'] = 'WW1 第一、二批 1908-10-06～1918-11-11；兩次大戰之間 A 批改迄日'; b['provenance']['replaces'] = '{{SOV_DE_EMP_R}}'
add('04-retract', 'sov_de_emp_r', 'RETRACTED_SOV_DE_EMP_R', '/api/v1/sovereignty-records/{{SOV_DE_EMP_R}}/retraction',
    {'reason': '兩次大戰之間 A 批：WW1 第二批截在 1918-11-12（試驗期間終點），改迄於 1918-11-09 德國革命（EV_DE_REV）後重送；11-09 起由德意志國接續'}, {'fix': True}, sub='A1')
add('05-sovereignty', 'sov_de_emp_r2', 'SOV_DE_EMP_R2', '/api/v1/sovereignty-records', b, {'replaces': 'SOV_DE_EMP_R'}, geom='SOV_DE_EMP_R2', sub='A1')
GEOM['SOV_DE_EMP_R2'] = B2G['SOV_DE_EMP_R']

for s in SEGS:
    x = s['x']; GEOM[s['ph']] = s['g']
    if x['ph'] == 'SOV_US':
        b = {'regimeId': '{{REGIME_US}}', 'geometry': None, 'validPeriod': {'start': s['start'], 'end': s['end']}, 'layerStatus': 'de_jure', 'geometrySourceId': '{{SRC_OHM_US}}',
             'geometryLocator': US['geometryLocator'], 'geometryLicense': US['geometryLicense'], 'attribution': US['attribution'], 'startEventId': None, 'endEventId': None,
             'ohmRelationId': US['ohmRelationId'], 'ohmVersion': US['ohmVersion'], 'ohmFetchedAt': US['ohmFetchedAt'], 'ohmStartRaw': US['ohmStartRaw'], 'ohmEndRaw': US['ohmEndRaw'],
             'provenance': {**copy.deepcopy(US['provenance']), 'trialWindow': TWN, 'copiedFrom': US['id']},
             'note': {'zh-Hant': '接 WW1 第二批（迄於 1918-11-12）。幾何照抄開發庫 1937 年起的美國紀錄，1918～1923 年的差異未處理（待查證）；主要給事件參與者用。' + endnote(s['end'])[0],
                      'en': 'Continues WW1 batch 2. Geometry copied from the 1937 US record; differences not handled (pending).' + endnote(s['end'])[1]}}
        add('05-sovereignty', 'sov_us', 'SOV_US', '/api/v1/sovereignty-records', b, None, geom='SOV_US'); continue
    derived = list(dict.fromkeys(x['derived'] + [r for h in s['act'] for r in h.get('derived', [])]))
    loc = x['loc'] + ''.join(f" − {lb}" for lb in dict.fromkeys(h['label'] for h in s['act']))
    gl, attr, osm = lic(derived)
    zh = x['zh'] + (('扣掉同期：' + '、'.join(dict.fromkeys(h['label'] for h in s['act'])) + '。') if s['act'] else '')
    en = x['en'] + ((' Minus: ' + ', '.join(dict.fromkeys(h['label'] if h['ph'].startswith('DB:') else h['ph'] for h in s['act'])) + '.') if s['act'] else '')
    if s['start'] == START and not s['sev']: zh = '接 WW1 第二批（迄於 1918-11-12）。' + zh; en = 'Continues WW1 batch 2 (ends 12 Nov 1918). ' + en
    ez, ee = endnote(s['end'])
    if x['rid'] in MAN:
        m = MAN[x['rid']]
        ohmf = {'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'], 'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date']}
        prov = {'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': osm, 'ohmFixme': m['fixme'], 'ohmRelationSource': m['relation_source'],
                'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'], 'ohmTimestamp': m['ohm_timestamp']}
        src = '{{SRC_OHM_IWA}}' if x['rid'] in OWN else '{{SRC_OHM_WW1B}}'
        if m.get('repair'): prov['ohmRepair'] = m['repair']
    else:
        fb = FALLBACK[x['rid']]
        ohmf = {k: fb[k] for k in ('ohmVersion', 'ohmFetchedAt', 'ohmStartRaw', 'ohmEndRaw')}
        prov = {k: v for k, v in fb['provenance'].items() if k not in ('trialWindow', 'replaces', 'coastline', 'derivedFrom', 'derivation')}
        src = fb['geometrySourceId']; gl, attr = fb['geometryLicense'], fb['attribution']
    b = {'regimeId': '{{%s}}' % x['regime'], 'geometry': None, 'validPeriod': {'start': s['start'], 'end': s['end']}, 'layerStatus': x['layer'],
         'geometrySourceId': src, 'geometryLocator': loc, 'geometryLicense': gl, 'attribution': attr, 'startEventId': ref(s['sev']), 'endEventId': ref(s['eev']),
         'ohmRelationId': x['rid'], **ohmf,
         'provenance': {**prov, 'coastline': '{{SRC_NE_LAND}}', 'licenseReview': 'osm_derived_ways' if prov.get('osmDerivedWayCount') else None, 'trialWindow': TWN},
         'note': {'zh-Hant': (zh + ez).strip(), 'en': (en + ee).strip()} if (zh + ez).strip() else None}
    if len(derived) > 1 or x['hand']: b['provenance'].update({'derivedFrom': [OL(r) for r in derived if r in MAN], 'derivation': loc})
    if x['hand']: b['provenance']['handDrawn'] = x['hand'] + '（近似，待查證）'
    add('05-sovereignty', s['ph'].lower(), s['ph'], '/api/v1/sovereignty-records', b, None, geom=s['ph'])

# ── 佔領歸屬 ──
def occ(ph, occd, occr, kind, start, end, basis, co, zh, en):
    add('06-occupation', ph.lower(), ph, '/api/v1/occupation-attributions', {'occupiedRegimeId': '{{%s}}' % occd, 'occupierRegimeId': '{{%s}}' % occr, 'controlKind': kind,
        'validPeriod': {'start': start, 'end': end}, 'basisEventId': ref(basis), 'coOccupied': co, 'note': {'zh-Hant': zh, 'en': en}})
occ('OCC_IT_AEGEAN_2', 'REGIME_IT_AEGEAN', 'REGIME_IT', 'military_administration', START, '1921-01-01', None, False, '義大利軍事佔領多德卡尼斯（接 WW1 第二批；1921 起開發庫既有紀錄）。', 'Italian military occupation of the Dodecanese (continues WW1 batch 2).')
occ('OCC_IT_JULIAN', 'REGIME_IT_JULIAN', 'REGIME_IT', 'military_administration', START, '1920-07-16', None, False, '依朱斯蒂別墅停戰協定的義大利軍事佔領，聖日耳曼條約生效後併入。', 'Italian military occupation under the Villa Giusti armistice until Saint-Germain.')
occ('OCC_FIUME_IA', 'REGIME_FIUME_IA', 'REGIME_IT', 'military_administration', '1918-11-17', '1919-09-12', 'EV_FIUME_OCC', True, '協約國共同佔領，義軍為主（一個政權只能有一筆同期歸屬，列義大利並標共同佔領）。', 'Inter-Allied occupation led by Italy.')
occ('OCC_MEMEL', 'REGIME_MEMEL', 'REGIME_FR3', 'civil_administration', '1920-01-10', '1923-01-19', 'EV_VERSAILLES', False, '協約國主要國委託法國代管（法國高級專員 1920-02 到任，待查證）。', 'Administered by France on behalf of the Principal Allied Powers.')
occ('OCC_DANZIG_ALLIED', 'REGIME_DANZIG_ALLIED', 'REGIME_UK_GBI', 'civil_administration', '1920-01-10', '1920-11-15', 'EV_VERSAILLES', True, '協約國管理，由英國代表主持（待查證）。', 'Allied administration under a British administrator (pending).')
occ('OCC_RUHR', 'REGIME_RUHR', 'REGIME_FR3', 'military_administration', '1923-01-11', END, 'EV_RUHR', True, '法比共同軍事佔領（列法國並標共同佔領）。' + endnote(END)[0], 'Joint Franco-Belgian military occupation.')
occ('OCC_SMYRNA', 'REGIME_SMYRNA', 'REGIME_GR', 'military_administration', '1919-05-15', '1922-09-09', 'EV_SMYRNA', False, '希臘軍事佔領（待查證）。', 'Greek military occupation.')
occ('OCC_ETHRACE', 'REGIME_ETHRACE', 'REGIME_GR', 'military_administration', '1920-08-10', '1922-10-11', 'EV_SEVRES', False, '希臘軍事佔領。', 'Greek military occupation.')
occ('OCC_BATUMI', 'REGIME_BATUMI', 'REGIME_UK_GBI', 'military_administration', '1918-12-01', '1920-07-07', None, False, '英軍佔領（停戰後進駐，日期近似）。', 'British military occupation (approximate dates).')
occ('OCC_CLT', 'REGIME_CLT', 'REGIME_PL', 'military_administration', '1920-10-12', '1922-04-18', 'EV_CLT', False, '波蘭軍控制下的政府（待查證）。', 'Under Polish military control (pending).')

# ── 衝突（全部用固定點）──
CF = [('CF_EE_RSFSR', 'REGIME_EE', 'REGIME_RSFSR', 'EV_EE_WAR', 'EV_TARTU_EE', ([28.2, 59.37], '納爾瓦（1918-11-28 紅軍進攻處，固定點）')),
      ('CF_LV_RSFSR', 'REGIME_LV', 'REGIME_RSFSR', 'EV_LV_WAR', 'EV_RIGA_LV', ([24.1, 56.95], '里加（1919-01 失守、1919-05 收復，固定點）')),
      ('CF_LT_RSFSR', 'REGIME_LT', 'REGIME_RSFSR', 'EV_LT_WAR', 'EV_MOSCOW_LT', ([25.28, 54.69], '維爾紐斯（固定點）')),
      ('CF_PL_ZUNR', 'REGIME_PL', 'REGIME_ZUNR', 'EV_ZUNR', 'EV_ZUNR_END', ([24.03, 49.84], '利沃夫（1918-11 巷戰處，固定點）')),
      ('CF_PL_RSFSR', 'REGIME_PL', 'REGIME_RSFSR', 'EV_PL_SOV_WAR', 'EV_RIGA', ([21.0, 52.25], '華沙（1920-08 華沙戰役，固定點）')),
      ('CF_RO_HUSR', 'REGIME_RO', 'REGIME_HU_SR', 'EV_HU_WAR', 'EV_HU_SR_END', ([20.2, 46.25], '提薩河（羅、匈前線，固定點）')),
      ('CF_CS_HUSR', 'REGIME_CS', 'REGIME_HU_SR', 'EV_HU_WAR', 'EV_HU_SR_END', ([20.8, 48.3], '米什科爾茨—斯洛伐克南部（固定點）')),
      ('CF_GR_GNA', 'REGIME_GR', 'REGIME_GNA', 'EV_SMYRNA', 'EV_MUDANYA', ([30.5, 39.6], '薩卡里亞河—埃斯基謝希爾（希土戰爭主戰場，固定點）')),
      ('CF_FR_GNA', 'REGIME_FR3', 'REGIME_GNA', 'EV_GNA', 'EV_ANKARA', ([36.93, 37.58], '馬拉什—奇里乞亞（法土戰爭，固定點）')),
      ('CF_AM_GNA', 'REGIME_AM', 'REGIME_GNA', 'EV_AM_TR_WAR', 'EV_ALEXANDROPOL', ([43.1, 40.6], '卡爾斯（固定點）')),
      ('CF_RSFSR_GE', 'REGIME_RSFSR', 'REGIME_GE', 'EV_GE_INV', 'EV_GE_SSR', ([44.8, 41.7], '提比里斯（固定點）'))]
cf_qa = {}
for ph, a, b_, sev, eev, (pt, method) in CF:
    cf_qa[ph] = pt
    add('07-conflict', ph.lower(), ph, '/api/v1/conflict-records', {'regimeAId': '{{%s}}' % a, 'regimeBId': '{{%s}}' % b_, 'startEventId': '{{%s}}' % sev,
        'endEventId': '{{%s}}' % eev, 'location': {'type': 'Point', 'coordinates': pt}, 'locationMethod': method})

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
while changed:
    changed = False
    for rq in REQ:
        if rq['sub'] is None: continue
        for m in re.findall(r'\{\{(\w+)\}\}', json.dumps(rq['body'], ensure_ascii=False) + rq['post']):
            t = byph.get(m)
            if t is None or t['cat'] == '04-retract': continue
            if t['sub'] is None or order.index(t['sub']) > order.index(rq['sub']):
                t['sub'] = rq['sub']; changed = True
# ── 與前批 placeholder 撞名的本批項目改名（加 _IWA），避免送出時誤用前批 id（build/prior-placeholders.txt：Mac .dev/sent-ids.*.json 的鍵名，只有名稱）──
RESERVED = set(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prior-placeholders.txt')).read().split())
REN = {rq['ph']: rq['ph'] + '_IWA' for rq in REQ if rq['ph'] in RESERVED and rq['cat'] != '04-retract'}
assert not (set(REN.values()) & RESERVED)
def _ren(t):
    return re.sub(r'\{\{(\w+)\}\}', lambda m: '{{%s}}' % REN.get(m.group(1), m.group(1)), t)
for rq in REQ:
    rq['ph'] = REN.get(rq['ph'], rq['ph']); rq['post'] = _ren(rq['post'])
    rq['body'] = json.loads(_ren(json.dumps(rq['body'], ensure_ascii=False)))
    if rq['geom']: rq['geom'] = REN.get(rq['geom'], rq['geom'])
GEOM = {REN.get(k, k): v for k, v in GEOM.items()}
for s_ in SEGS: s_['ph'] = REN.get(s_['ph'], s_['ph'])
cf_qa = {REN.get(k, k): v for k, v in cf_qa.items()}
EVD = {REN.get(k, k): v for k, v in EVD.items()}
print('renamed', sorted(REN))
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

# ── QA：每個切點日互不重疊（本批紀錄＋開發庫既有紀錄）、涵蓋面積 ──
items_all = [(s['ph'], s['g'], s['start'], s['end']) for s in SEGS if s['ph'] != 'SOV_US'] + [(f['ph'], f['geom'], f['start'], f['end']) for f in FIXED]
DAYS = sorted({s['start'] for s in SEGS if START <= s['start'] < END} | {f['start'] for f in FIXED if START <= f['start'] < END} | {START})
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
qa['retracted'] = ['SOV_DE_EMP_R']
qa['renamed'] = REN
qa['requestCounts'] = {n: sum(1 for rq in REQ if rq['sub'] == n) for n in order}
qa['pendingEvents'] = [rq['ph'] for rq in REQ if rq['cat'] == '03-event' and not rq['body']['citations']]
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in GEOM.items()]},
          open(os.path.join(ROOT, 'interwar-a-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(qa, open(os.path.join(ROOT, 'qa.json'), 'w'), indent=1, ensure_ascii=False)
bad = [(day, w) for day in DAYS for w in qa['overlaps'][day]]
print('requests', qa['requestCounts'], 'segments', len(SEGS), 'events', sum(1 for r in REQ if r['cat'] == '03-event'), 'pending', len(qa['pendingEvents']))
for day, w in bad: print('OVERLAP', day, w)
if '--strict' in sys.argv: assert not bad
