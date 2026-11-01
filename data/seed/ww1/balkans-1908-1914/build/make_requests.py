#!/usr/bin/env python3
"""WW1 第一批：1908-10-06 波士尼亞併吞 → 1914-07-28 奧匈對塞爾維亞宣戰（DRAFT，待 Tai 檢查）。
輸入：
- ../borders-ohm-ww1-1.geojson＋../ohm-manifest.json：固定版本 OHM 關係（build/fetch.py 抓、build/build.py 組多邊形，歐洲—北非—近東框 -20,15,60,72 裁切＋Natural Earth 陸地）
- ../db-export/ww1_rows.json：開發庫（5442）唯讀匯出，1908-10-05～1914-07-28 期間已有的主權紀錄（安道爾、瑞士、荷蘭、葡萄牙共和國等；QA 與葡萄牙修正用，不進版控）
輸出：../ww1-1908-1914-derived.geojson（所有新紀錄的幾何，key＝placeholder）、../qa.json、../requests/*.json
期間：半開區間，迄 1914-07-29（含 7-28 奧匈宣戰日）＝本批試驗期間終點，無迄事件。
"""
import json, os, copy, datetime
from shapely.geometry import shape, mapping, MultiPolygon, Polygon, LineString, MultiLineString, Point
from shapely.ops import unary_union, linemerge
from shapely.validation import make_valid
from shapely import set_precision, STRtree
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); OUT = os.path.join(ROOT, 'requests')
START, END = '1908-10-06', '1914-07-29'
MAN = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))}
ohm = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-ww1-1.geojson')))['features']}
ROWS = json.load(open(os.path.join(ROOT, 'db-export', 'ww1_rows.json')))
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

# ── 幾何組合 ──
AEG, CRETE, CY, ALB1, ALB2 = O(2830316), O(2692586), O(2848136), O(2807008), O(2855613)
LIBYA = U(O(2690837), O(2803190))
OT08, OT13 = O(2746682), O(2849728)
SULT = U(O(2866014), O(2866017)).difference(O(2860487))
CEDED = OT08.difference(OT13).difference(AEG).difference(ALB1).difference(CRETE)
G = {
 'OT_A': U(OT08, LIBYA), 'OT_B': U(OT08.difference(AEG), LIBYA), 'OT_C': OT08.difference(AEG), 'OT_D': OT08.difference(AEG).difference(ALB1),
 'OT_E': OT13.difference(CY).difference(AEG).difference(U(ALB1, ALB2)),
 'LONDON': CEDED.difference(U(O(2692716), O(2692556), O(2742283), O(2739656), O(2692219))),
 'MA_SULT': SULT, 'MA_FR_A': U(O(2866016), SULT), 'MA_FR_B': U(O(2866016), SULT).difference(O(2860424)).difference(O(2860486)),
 'ES_B': O(2860486).difference(O(2860424)),
}
for rid in [2692361, 2692425, 2849760, 2696424, 2866012, 2828388, 2797729, 2869935, 2692537, 2692524, 2696520, 2690947, 2917211, 2848136, 2692586,
            2830316, 2690837, 2803190, 2692556, 2692585, 2692716, 2746681, 2692715, 2958264, 2739656, 2742283, 2746680, 2692219, 2693260,
            2807008, 2855613, 2860487, 2860424, 2959467]:
    G[str(rid)] = O(rid)
PT = [r for r in ROWS if r['slug'] == 'portuguese-republic'][0]
G['COPY_PT'] = shape(PT['geometry'])
G = {k: (v if k == 'COPY_PT' else clean(v)) for k, v in G.items()}

for f in os.listdir(OUT): os.remove(os.path.join(OUT, f)) if f.endswith('.json') else None
def write(name, ph, post, body, meta=None, geom=None):
    req = {'_placeholder': ph, '_post': post, **({'_geometryFrom': geom} if geom else {}), **({'_meta': meta} if meta else {}), 'body': body}
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')

# ── 來源 ──
write('01-source-01-src_ohm_ww1.json', 'SRC_OHM_WW1', '/api/v1/sources', {'sourceKind': 'dataset',
    'title': 'OpenHistoricalMap — boundary=administrative, admin_level=2 關係（歐洲、北非、近東，1908～1914 WW1 第一批試驗）',
    'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
    'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
    'publishedText': 'Overpass osm_base %s；逐筆見 ww1/balkans-1908-1914/ohm-manifest.json' % MAN[2692361]['osm_base'],
    'note': 'OHM 整體以 CC0 1.0 釋出；部分成員線段帶 license=CC BY 4.0 標籤，部分線段註明來自 OpenStreetMap（ODbL），逐筆在主權紀錄標示。'})
GPO = 'United States Department of State; United States Government Printing Office, Washington'
FRUS = [('SRC_FRUS_1908', 'frus1908', 'December 8, 1908'), ('SRC_FRUS_1910', 'frus1910', 'December 6, 1910'), ('SRC_FRUS_1911', 'frus1911', 'December 7, 1911'),
        ('SRC_FRUS_1912', 'frus1912', 'December 3, 1912')]
i = 2
for ph, vol, d in FRUS:
    write(f'01-source-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sources', {'sourceKind': 'official_record',
          'title': f'Papers Relating to the Foreign Relations of the United States, With the Annual Message of the President Transmitted to Congress {d}',
          'publisher': GPO, 'licenseCode': 'us_federal_pd', 'licenseEvidenceUrl': 'https://www.state.gov/copyright-information', 'url': 'https://history.state.gov/historicaldocuments/' + vol}); i += 1
write(f'01-source-{i:02d}-src_frus_1913.json', 'SRC_FRUS_1913', '/api/v1/sources', {'sourceKind': 'official_record',
      'title': 'Papers Relating to the Foreign Relations of the United States, With the Address of the President to Congress December 2, 1913',
      'publisher': GPO, 'licenseCode': 'us_federal_pd', 'licenseEvidenceUrl': 'https://www.state.gov/copyright-information', 'url': 'https://history.state.gov/historicaldocuments/frus1913'}); i += 1
AJIL = [  # (ph, kind, 英文篇名, 卷, 頁, 年, jstor id)
 ('SRC_AJIL_AH_TR_1909', 'treaty', 'Protocol between Austria-Hungary and Turkey', '3', '286–289', '1909', '2212637'),
 ('SRC_AJIL_FEZ_1912', 'treaty', 'Protectorate Treaty Between France and Morocco', '6', '207–209', '1912', '2212598'),
 ('SRC_AJIL_OUCHY_1912', 'treaty', 'Treaty of Peace Between Italy and Turkey', '7', '58–62', '1913', '2212446'),
 ('SRC_AJIL_FR_ES_1912', 'treaty', 'Treaty Between France and Spain Regarding Morocco', '7', '81–99', '1913', '2212275'),
 ('SRC_AJIL_LONDON_1913', 'treaty', 'Treaty of Peace Between Turkey and the Balkan Allies', '8', '12–13', '1914', '2212402'),
 ('SRC_AJIL_BUCHAREST_1913', 'treaty', 'Treaty of Peace Between Bulgaria and Roumania, Greece, Monte-Negro and Servia', '8', '13–27', '1914', '2212403'),
 ('SRC_AJIL_CONSTANTINOPLE_1913', 'treaty', 'Treaty of Peace Between Bulgaria and Turkey', '8', '27–45', '1914', '2212404'),
 ('SRC_AJIL_ATHENS_1913', 'treaty', 'The Treaty of Peace Between Turkey and Greece', '8', '46–55', '1914', '2212405'),
 ('SRC_AJIL_YELLOW_BOOK_1914', 'official_record', 'French Yellow Book, Chapter IV: From the Rupture of Diplomatic Relations (July 25, 1914), to the Declaration of War by Austria on Servia (July 28, 1914)', '9', '191–232', '1915', '2212040'),
]
for ph, kind, t, vol, pp, yr, jid in AJIL:
    write(f'01-source-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sources', {'sourceKind': kind,
          'title': f'{t}（The American Journal of International Law, Supplement: Official Documents, Vol. {vol}, {yr}, pp. {pp}）',
          'publisher': 'American Society of International Law', 'licenseCode': 'pd_expired',
          'licenseEvidenceUrl': f'https://archive.org/details/jstor-{jid}', 'url': f'https://www.jstor.org/stable/{jid}',
          'publishedText': f'{yr} 年美國出版（JSTOR Early Journal Content，archive.org 公開全文）',
          'note': '1927 年以前在美國出版，著作權已過期；條約與官方文件的英譯本文。'}); i += 1

# ── 政權 ──
REGIMES = [
 ('REGIME_AH', 'austria-hungary', 'Österreichisch-Ungarische Monarchie', 'de', '奧匈帝國', 'Austria-Hungary', '原文名為通行稱呼；OHM relation/2692361'),
 ('REGIME_DE_EMP', 'german-empire', 'Deutsches Reich', 'de', '德意志帝國', 'German Empire', 'OHM relation/2692425（name=Deutsches Reich）'),
 ('REGIME_RU_EMP', 'russian-empire', 'Российская империя', 'ru', '俄羅斯帝國', 'Russian Empire', '原文名為通行稱呼；OHM relation/2849760'),
 ('REGIME_OT', 'ottoman-empire', 'دولت عليه عثمانيه', 'ota', '鄂圖曼帝國', 'Ottoman Empire', '原文名為通行稱呼（Devlet-i Âliyye-i Osmâniyye，待查證）；OHM relation/2746682'),
 ('REGIME_RS', 'kingdom-of-serbia', 'Краљевина Србија', 'sr', '塞爾維亞王國', 'Kingdom of Serbia', 'OHM relation/2692716；原文名為通行稱呼'),
 ('REGIME_MN_P', 'principality-of-montenegro', 'Књажевина Црна Гора', 'sr', '蒙特內哥羅親王國', 'Principality of Montenegro', 'OHM relation/2692715；原文名為通行稱呼'),
 ('REGIME_MN_K', 'kingdom-of-montenegro', 'Краљевина Црна Гора', 'sr', '蒙特內哥羅王國', 'Kingdom of Montenegro', 'OHM relation/2958264；原文名為通行稱呼'),
 ('REGIME_AL_PROV', 'albania-provisional-government-1912', 'Qeveria e Përkohshme e Vlorës', 'sq', '阿爾巴尼亞臨時政府（發羅拉）', 'Provisional Government of Albania (Vlorë)', '名稱為通行稱呼（待查證）；OHM relation/2807008'),
 ('REGIME_AL_PR', 'principality-of-albania', 'Principata e Shqipërisë', 'sq', '阿爾巴尼亞親王國', 'Principality of Albania', '名稱為通行稱呼（待查證）；OHM relation/2855613'),
 ('REGIME_CRETE', 'cretan-state', 'Κρητική Πολιτεία', 'el', '克里特國', 'Cretan State', 'OHM relation/2692586；原文名為通行稱呼'),
 ('REGIME_CY_BR', 'cyprus-british-administration', 'Cyprus (under British administration)', 'en', '英國管理下的賽普勒斯', 'Cyprus (British-administered)', '名稱為通行稱呼；OHM relation/2848136（Cyprus Protectorate）'),
 ('REGIME_LONDON', 'ottoman-territories-ceded-1913', 'Territories ceded by the Ottoman Empire under the Treaty of London (1913)', 'en', '倫敦條約割讓、待巴爾幹同盟分配的原鄂圖曼領土', 'Territories ceded under the Treaty of London (1913), pending partition', '本表自訂的說明性名稱（非政權正式名稱）；AJIL Supp. 8 pp. 12–13 第 2 條'),
 ('REGIME_MA_SULT', 'sultanate-of-morocco', 'السلطنة الشريفة', 'ar', '摩洛哥蘇丹國', 'Sultanate of Morocco', '原文名為通行稱呼（待查證）；OHM relation/2866014（Alawi Sultanate）'),
 ('REGIME_MA_FR', 'french-protectorate-morocco', 'Protectorat français au Maroc', 'fr', '法屬摩洛哥保護國', 'French protectorate in Morocco', 'OHM relation/2866016；AJIL Supp. 6 pp. 207–209'),
 ('REGIME_MA_ES', 'spanish-protectorate-morocco', 'Protectorado español de Marruecos', 'es', '西屬摩洛哥保護國', 'Spanish protectorate in Morocco', 'OHM relation/2860424；原文名為通行稱呼'),
 ('REGIME_TN', 'french-protectorate-tunisia', 'Protectorat français de Tunisie', 'fr', '法屬突尼西亞保護國', 'French protectorate of Tunisia', 'OHM relation/2690947；原文名為通行稱呼'),
 ('REGIME_LY_TR', 'italian-tripolitania', 'Tripolitania italiana', 'it', '義屬的黎波里塔尼亞', 'Italian Tripolitania', 'OHM relation/2690837'),
 ('REGIME_LY_CY', 'italian-cyrenaica', 'Cirenaica italiana', 'it', '義屬昔蘭尼加', 'Italian Cyrenaica', 'OHM relation/2803190'),
 ('REGIME_UK_GBI', 'united-kingdom-of-great-britain-and-ireland', 'United Kingdom of Great Britain and Ireland', 'en', '大不列顛及愛爾蘭聯合王國', 'United Kingdom of Great Britain and Ireland', 'OHM relation/2828388'),
 ('REGIME_ES_K', 'kingdom-of-spain', 'Reino de España', 'es', '西班牙王國', 'Kingdom of Spain', 'OHM relation/2860487；原文名為通行稱呼'),
 ('REGIME_PT_K', 'kingdom-of-portugal', 'Reino de Portugal', 'pt', '葡萄牙王國', 'Kingdom of Portugal', 'OHM relation/2959467'),
 ('REGIME_MR', 'mauritania-french-1912', 'Mauritanie', 'fr', '法屬茅利塔尼亞', 'French Mauritania', '名稱為通行稱呼（OHM 名 Protectorate of Mauritania，待查證）；OHM relation/2917211'),
 ('REGIME_MORESNET', 'neutral-moresnet', 'Neutral-Moresnet', 'de', '中立莫雷斯內', 'Neutral Moresnet', 'OHM relation/2696520'),
]
for j, (ph, slug, orig, lang, zh, en, ns) in enumerate(REGIMES, 1):
    write(f'02-regime-{j:02d}-{slug}.json', ph, '/api/v1/regimes', {'slug': slug, 'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang,
          'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]}, {'priorPlaceholder': False, 'nameSource': ns})
# 沿用既有政權（前置表 .dev/sent-ids.borders-dev.json）：REGIME_IT、REGIME_RO、REGIME_GR、REGIME_BE、REGIME_DK、REGIME_NO、REGIME_SE、REGIME_BG、REGIME_FR3、REGIME_IT_AEGEAN、REGIME_PT

# ── 事件 ──
def nxt(s): return (datetime.date.fromisoformat(s) + datetime.timedelta(days=1)).isoformat()
EVN = [0]
def ev(ph, kind, start, zh, en, parts, cites, tn=None):
    EVN[0] += 1
    body = {'eventKind': kind, 'occurred': {'start': start, 'end': nxt(start)}, 'datePrecision': 'day', 'summary': {'zh-Hant': zh, 'en': en},
            'participants': [{'regimeId': '{{%s}}' % r, 'role': role} for r, role in parts],
            'citations': [{'sourceId': '{{%s}}' % s, 'locator': l, 'evidenceNote': n} for s, l, n in cites]}
    if tn: body['timeNote'] = {'zh-Hant': tn[0], 'en': tn[1]}
    write(f'03-event-{EVN[0]:02d}-{ph.lower()}.json', ph, '/api/v1/events', body, {'verification': 'verified' if cites else 'pending（待查證）'})
B, S_ = 'belligerent', 'signatory'
ev('EV_BG_INDEP', 'political', '1908-10-05', '保加利亞宣布獨立（斐迪南稱沙皇）', 'Bulgaria proclaims its independence', [('REGIME_BG', S_)],
   [('SRC_FRUS_1908', 'Doc. 44, p. 56', '駐布加勒斯特公使 1908-10-05 電：「Bulgaria proclaimed her independence to-day.」')])
ev('EV_BOSNIA', 'political', '1908-10-06', '奧匈帝國宣布併吞波士尼亞與赫塞哥維納，自新帕扎爾桑賈克撤軍', 'Austria-Hungary proclaims the annexation of Bosnia and Herzegovina and evacuates the Sanjak of Novi Pazar',
   [('REGIME_AH', S_)],
   [('SRC_FRUS_1908', 'Doc. 30, pp. 36–38', '駐維也納代辦 1908-10-07 函：附《維也納日報》所載皇帝致奧、匈總理信，宣布將主權延伸至波士尼亞與赫塞哥維納，並自新帕扎爾桑賈克撤軍。'),
    ('SRC_AJIL_AH_TR_1909', 'pp. 286–289', '1909-02-26 奧匈—鄂圖曼議定書：鄂圖曼承認新局（奧匈放棄新帕扎爾桑賈克權利、給付補償）。')],
   ('皇帝詔書日期為 10 月 5 日、10 月 6–7 日公布（待查證）；OHM 奧匈 2692361 起日 1908-10-06，本表取 10 月 6 日。', 'The rescript is dated 5 Oct and was published 6–7 Oct (pending); OHM starts 6 Oct 1908.'))
ev('EV_MN_KINGDOM', 'political', '1910-08-28', '蒙特內哥羅親王尼古拉一世稱王，親王國改為王國', 'Prince Nicholas I proclaims Montenegro a kingdom', [('REGIME_MN_K', S_)], [],
   ('未找到正式出處（待查證）；日期依 OHM 2692715／2958264 起訖。', 'No formal source located yet (pending); date per OHM.'))
ev('EV_PT_REPUBLIC', 'political', '1910-10-05', '葡萄牙革命：君主制廢除、共和國成立', 'Portuguese revolution: the monarchy is abolished and the Republic proclaimed', [('REGIME_PT', S_)],
   [('SRC_FRUS_1910', 'Doc. 905, pp. 825–826', '葡萄牙臨時總統 1910-10-05 電國務卿：人民與軍隊剛廢除君主制、宣布共和，臨時政府已成立。'),
    ('SRC_FRUS_1910', 'Doc. 904, p. 825', '駐里斯本公使 1910-10-05 電：徹夜巷戰後許多保王派士兵投降，多數公共建築與堡壘升起共和旗。')])
ev('EV_IT_TR_WAR', 'war', '1911-09-29', '義大利對鄂圖曼帝國宣戰（義土戰爭，爭奪的黎波里塔尼亞與昔蘭尼加）', 'Italy declares war on the Ottoman Empire (Italo-Turkish War over Tripolitania and Cyrenaica)',
   [('REGIME_IT', B), ('REGIME_OT', B)],
   [('SRC_FRUS_1911', 'Doc. 402', '義大利駐美代辦 1911-09-30 照會：說明的黎波里塔尼亞與昔蘭尼加問題，宣布義大利與鄂圖曼帝國進入戰爭狀態。')],
   ('宣戰為 9 月 29 日（通行說法，FRUS 照會日期為 9 月 30 日，待查證）。', 'War was declared on 29 Sep (common account; the FRUS note is dated 30 Sep, pending).'))
ev('EV_DODECANESE', 'campaign', '1912-04-27', '義大利佔領多德卡尼斯群島（4 月底起，5 月 4 日登陸羅德島）', 'Italy occupies the Dodecanese (from late April; Rhodes landing 4 May)',
   [('REGIME_IT', B), ('REGIME_OT', B)],
   [('SRC_AJIL_OUCHY_1912', 'Art. 2, pp. 58–59', '烏契和約第 2 條：義大利政府自「義大利佔領的愛琴海島嶼」撤回軍官、部隊與文職人員（證明佔領存在；日期本條約未載）。')],
   ('起日依 OHM 義屬愛琴海群島 2830316（1912-04-27），確切日期待查證。', 'Start date per OHM relation/2830316 (pending).'))
ev('EV_FEZ', 'treaty', '1912-03-30', '菲斯條約：摩洛哥成為法國保護國', 'Treaty of Fez: Morocco becomes a French protectorate', [('REGIME_FR3', S_), ('REGIME_MA_SULT', S_)],
   [('SRC_AJIL_FEZ_1912', 'pp. 207–209', '1912-03-30 法國—摩洛哥保護國條約全文（英譯）。')])
ev('EV_MN_WAR', 'war', '1912-10-08', '蒙特內哥羅對鄂圖曼帝國宣戰（第一次巴爾幹戰爭開始）', 'Montenegro declares war on the Ottoman Empire (start of the First Balkan War)',
   [('REGIME_MN_K', B), ('REGIME_OT', B)],
   [('SRC_FRUS_1912', 'Doc. 1792', '駐君士坦丁堡大使 1912-10-08 電：蒙特內哥羅代辦今日向土耳其政府遞交宣戰書。')])
ev('EV_BALKAN_WAR', 'war', '1912-10-18', '塞爾維亞、保加利亞、希臘對鄂圖曼帝國宣戰（第一次巴爾幹戰爭）', 'Serbia, Bulgaria and Greece declare war on the Ottoman Empire (First Balkan War)',
   [('REGIME_RS', B), ('REGIME_BG', B), ('REGIME_GR', B), ('REGIME_OT', B)],
   [('SRC_FRUS_1912', 'Doc. 1795', '駐羅馬尼亞公使 1912-10-18 電：塞爾維亞今日對土耳其宣戰。'),
    ('SRC_FRUS_1912', 'Doc. 1796', '同日電：保加利亞對土耳其宣戰。'),
    ('SRC_FRUS_1912', 'Doc. 1797', '駐君士坦丁堡大使 1912-10-18 電：希臘今日對土耳其宣戰。')],
   ('鄂圖曼對塞、保宣戰為 10 月 17 日（通行說法，待查證）；FRUS 三電均為 10 月 18 日，本表取 10 月 18 日。', 'The Ottoman declaration against Serbia and Bulgaria is usually dated 17 Oct (pending); FRUS telegrams are dated 18 Oct.'))
ev('EV_OUCHY', 'treaty', '1912-10-18', '烏契（洛桑）和約：義土戰爭結束，鄂圖曼自的黎波里塔尼亞、昔蘭尼加撤出', 'Treaty of Ouchy (Lausanne) ends the Italo-Turkish War; Ottoman withdrawal from Tripolitania and Cyrenaica',
   [('REGIME_IT', S_), ('REGIME_OT', S_)],
   [('SRC_AJIL_OUCHY_1912', 'pp. 58–62', '1912-10-18 義土和約全文（英譯），第 2 條雙方撤軍。'),
    ('SRC_FRUS_1912', 'Doc. 785', '義大利駐美代辦 1912-10-18 照會：義土戰爭狀態因當日在洛桑簽訂的和約而終止。')])
ev('EV_ES_MOROCCO', 'treaty', '1912-11-27', '法西摩洛哥條約：劃定西班牙在摩洛哥北部的保護區', 'Franco-Spanish treaty on Morocco defines the Spanish zone in northern Morocco',
   [('REGIME_FR3', S_), ('REGIME_ES_K', S_)],
   [('SRC_AJIL_FR_ES_1912', 'pp. 81–99', '1912-11-27 法國—西班牙關於摩洛哥的條約全文（英譯），含西班牙區界線。')])
ev('EV_AL_INDEP', 'political', '1912-11-28', '阿爾巴尼亞在發羅拉宣布獨立，成立臨時政府', 'Albania proclaims independence at Vlorë and forms a provisional government', [('REGIME_AL_PROV', S_)], [],
   ('未找到正式出處（待查證）；日期依 OHM 2807008 起日。', 'No formal source located yet (pending); date per OHM.'))
ev('EV_LONDON', 'treaty', '1913-05-30', '倫敦和約：鄂圖曼割讓伊諾斯—米迪亞線以西領土與克里特，第一次巴爾幹戰爭結束', 'Treaty of London: the Ottoman Empire cedes territory west of the Enos–Midia line and Crete, ending the First Balkan War',
   [('REGIME_OT', S_), ('REGIME_BG', S_), ('REGIME_GR', S_), ('REGIME_MN_K', S_), ('REGIME_RS', S_)],
   [('SRC_AJIL_LONDON_1913', 'pp. 12–13', '1913-05-30 倫敦和約全文（英譯），第 2 條伊諾斯—米迪亞線、第 4 條克里特。'),
    ('SRC_FRUS_1913', 'Doc. 1655', '希臘駐美代辦 1913-06-08 照會：保、希、蒙、塞與鄂圖曼代表於 5 月 30 日在倫敦簽訂和約。')])
ev('EV_BALKAN2', 'war', '1913-06-29', '保加利亞攻擊塞爾維亞、希臘陣地（第二次巴爾幹戰爭）', 'Bulgaria attacks Serbian and Greek positions (Second Balkan War)',
   [('REGIME_BG', B), ('REGIME_RS', B), ('REGIME_GR', B)],
   [('SRC_FRUS_1913', 'Doc. 76, pp. 78–81', '駐希臘公使 1913-07-10 報告：巴爾幹同盟國之間已爆發戰爭，戰事始於烏斯庫普一帶，並分析馬其頓、色雷斯的爭議。')],
   ('6 月 29–30 日夜保軍攻擊為通行說法；FRUS 報告只記至 7 月 10 日已開戰（待查證）。', 'The Bulgarian night attack of 29–30 June is the common account; FRUS only confirms war by 10 July (pending).'))
ev('EV_RO_WAR', 'war', '1913-07-10', '羅馬尼亞對保加利亞宣戰', 'Romania declares war on Bulgaria', [('REGIME_RO', B), ('REGIME_BG', B)], [],
   ('未找到正式出處（待查證）；日期為通行說法。', 'No formal source located yet (pending).'))
ev('EV_OT_BG2', 'war', '1913-07-12', '鄂圖曼軍越過伊諾斯—米迪亞線進攻保加利亞（7 月 22 日收復埃迪爾內）', 'Ottoman forces cross the Enos–Midia line against Bulgaria (Edirne retaken on 22 July)',
   [('REGIME_OT', B), ('REGIME_BG', B)], [], ('未找到正式出處（待查證）；日期為通行說法。', 'No formal source located yet (pending).'))
ev('EV_BUCHAREST', 'treaty', '1913-08-10', '布加勒斯特和約：第二次巴爾幹戰爭結束，劃分馬其頓與南多布羅加', 'Treaty of Bucharest ends the Second Balkan War; partition of Macedonia and Southern Dobruja',
   [('REGIME_BG', S_), ('REGIME_RO', S_), ('REGIME_GR', S_), ('REGIME_MN_K', S_), ('REGIME_RS', S_)],
   [('SRC_AJIL_BUCHAREST_1913', 'pp. 13–27', '1913-07-28／08-10 布加勒斯特和約全文（英譯），各國新界線。')],
   ('約文署新舊曆並列（7 月 28 日／8 月 10 日），本表用格里曆 8 月 10 日；OHM 羅馬尼亞新界 2693260 起日為 8 月 30 日，本表取和約日。', 'Dated 28 July / 10 August (Julian/Gregorian); OHM Romania 2693260 starts 30 Aug, here the treaty date.'))
ev('EV_CONSTANTINOPLE', 'treaty', '1913-09-29', '君士坦丁堡和約：保加利亞與鄂圖曼議和，埃迪爾內歸鄂圖曼', 'Treaty of Constantinople between Bulgaria and the Ottoman Empire; Edirne remains Ottoman',
   [('REGIME_BG', S_), ('REGIME_OT', S_)],
   [('SRC_AJIL_CONSTANTINOPLE_1913', 'pp. 27–45', '1913-09-16／29 保加利亞—鄂圖曼和約全文（英譯），第 1 條新界。')])
ev('EV_ATHENS', 'treaty', '1913-11-14', '雅典和約：希臘與鄂圖曼議和', 'Treaty of Athens between Greece and the Ottoman Empire', [('REGIME_GR', S_), ('REGIME_OT', S_)],
   [('SRC_AJIL_ATHENS_1913', 'pp. 46–55', '1913-11-01／14 希臘—鄂圖曼和約全文（英譯）。'),
    ('SRC_FRUS_1913', 'Doc. 1658', '駐雅典代辦 1913-11-14 電：「Turkish-Greek treaty signed today.」')])
ev('EV_AL_PRINCIPALITY', 'political', '1914-02-21', '維德親王威廉接受阿爾巴尼亞王位，阿爾巴尼亞親王國成立', 'Prince Wilhelm of Wied accepts the Albanian throne; Principality of Albania', [('REGIME_AL_PR', S_)], [],
   ('未找到正式出處（待查證）；日期依 OHM 2855613 起日（3 月 7 日抵都拉斯）。', 'No formal source located yet (pending); date per OHM.'))
ev('EV_SARAJEVO', 'political', '1914-06-28', '奧匈皇儲法蘭茲·斐迪南大公在塞拉耶佛遇刺', 'Assassination of Archduke Franz Ferdinand at Sarajevo', [],
   [('SRC_AJIL_YELLOW_BOOK_1914', 'pp. 222–223', '奧匈致各國附件（法國黃皮書轉載）：「the profoundly regrettable outrage of the 28th June」，並述普林西普、格拉貝茲與民族自衛會的關係。')])
ev('EV_AH_RS_WAR', 'war', '1914-07-28', '奧匈帝國對塞爾維亞宣戰', 'Austria-Hungary declares war on Serbia', [('REGIME_AH', B), ('REGIME_RS', B)],
   [('SRC_AJIL_YELLOW_BOOK_1914', 'No. 80, pp. 229–230', '法國駐倫敦大使康邦 1914-07-28 電：「Austria has just officially declared war against Servia」。'),
    ('SRC_AJIL_YELLOW_BOOK_1914', 'No. 75 (2)', '維也納 1914-07-28 新聞局公報：奧匈駐貝爾格勒公使已返回，塞爾維亞覆文不被接受。')])

# ── 主權紀錄 ──
def lic(rids):
    cc_by = any(MAN[r]['geometry_license'] == 'cc_by' for r in rids)
    attrs = sorted({a for r in rids for a in (MAN[r]['attribution'] or '').split('; ') if a})
    osm = sum(MAN[r]['osm_derived_way_count'] for r in rids)
    return ('cc_by' if cc_by else 'cc0'), ('; '.join(attrs) or None), osm
REC = []  # (ph, regime, start, end, geomkey, layer, sev, eev, main rid, derived rids, locator, zh, en)
def rec(ph, regime, start, end, gk, rid, sev=None, eev=None, layer='de_jure', derived=None, loc=None, zh='', en=''):
    REC.append((ph, regime, start, end, gk, layer, sev, eev, rid, derived or [rid], loc or OL(rid), zh, en))
TW = ('本批試驗期間 1908-10-06～1914-07-28（起訖為試驗邊界，不是政權起訖）。', 'Trial window 6 Oct 1908 – 28 Jul 1914.')
rec('SOV_AH', 'REGIME_AH', START, END, '2692361', 2692361, sev='{{EV_BOSNIA}}', zh='含 1908-10-06 併吞的波士尼亞與赫塞哥維納（OHM 2692361 已含，未另立波赫紀錄）。', en='Includes Bosnia and Herzegovina annexed on 6 Oct 1908.')
rec('SOV_DE_EMP', 'REGIME_DE_EMP', START, END, '2692425', 2692425)
rec('SOV_RU_EMP', 'REGIME_RU_EMP', START, END, '2849760', 2849760, zh='含芬蘭大公國（OHM 2849760 已含，未另立）。OHM 在 1914-04-17 換版（2851294），框內範圍相同，未分段。', en='Includes the Grand Duchy of Finland; OHM relation 2851294 from 17 Apr 1914 has the same extent in frame.')
rec('SOV_IT', 'REGIME_IT', START, END, '2696424', 2696424)
rec('SOV_FR3', 'REGIME_FR3', START, END, '2866012', 2866012, zh='含阿爾及利亞（OHM 2866012 已含）。', en='Includes Algeria.')
rec('SOV_UK_GBI', 'REGIME_UK_GBI', START, END, '2828388', 2828388)
rec('SOV_BE', 'REGIME_BE', START, END, '2797729', 2797729)
rec('SOV_DK', 'REGIME_DK', START, END, '2869935', 2869935, zh='OHM 2869935 不含冰島與法羅群島（冰島留白，待查證）。', en='Iceland and the Faroes are not in this relation (pending).')
rec('SOV_NO', 'REGIME_NO', START, END, '2692537', 2692537)
rec('SOV_SE', 'REGIME_SE', START, END, '2692524', 2692524)
rec('SOV_MORESNET', 'REGIME_MORESNET', START, END, '2696520', 2696520, zh='普魯士（德國）與比利時共管的中立地帶。', en='Neutral territory under joint Prussian (German) and Belgian administration.')
rec('SOV_TN', 'REGIME_TN', START, END, '2690947', 2690947, zh='法國保護國（1881 巴爾杜條約），貝伊名義主權。', en='French protectorate (Bardo, 1881).')
rec('SOV_MR', 'REGIME_MR', '1912-01-01', END, '2917211', 2917211, zh='OHM 起日只到年（1912），1912-01-01 起；之前留白（法屬西非一部分，待查證）。', en='OHM gives only the year 1912; blank before (pending).')
rec('SOV_CY', 'REGIME_CY_BR', START, END, '2848136', 2848136, layer='not_sovereign', zh='非主權：1878 年英鄂協定後由英國管理，法理上仍屬鄂圖曼（1914-11-05 英國併吞，不在本批）。', en='Not sovereign: British-administered under the 1878 convention, Ottoman de jure.')
rec('SOV_CRETE', 'REGIME_CRETE', START, '1913-08-10', '2692586', 2692586, eev='{{EV_BUCHAREST}}', layer='not_sovereign',
    zh='非主權：鄂圖曼宗主權下的自治國（1908-10 宣布與希臘合併未獲列強承認）。倫敦和約第 4 條割讓；OHM 只到年（1913），本表到 8 月 10 日起改畫入希臘 2692585（正式合併 1913-12-01，待查證）。',
    en='Not sovereign: autonomous under Ottoman suzerainty; ceded at London (art. 4); drawn into Greece from 10 Aug 1913 per OHM 2692585 (formal union 1 Dec 1913, pending).')
# 鄂圖曼
LYL = f'{OL(2690837)} ∪ {OL(2803190)}'
rec('SOV_OT_A', 'REGIME_OT', START, '1912-04-27', 'OT_A', 2746682, eev='{{EV_DODECANESE}}', derived=[2746682, 2690837, 2803190], loc=f'{OL(2746682)} ∪ 利比亞（{LYL}）',
    zh='OHM 2746682 不含利比亞；本表把 OHM 義屬的黎波里塔尼亞／昔蘭尼加範圍畫回鄂圖曼，到烏契和約（近似，待查證）。不含克里特（克里特國另段）、賽普勒斯（英國管理另段）、埃及（OHM 無，留白）。',
    en='Libya (from the Italian relations) is drawn as Ottoman until Ouchy (approximation, pending). Crete, Cyprus and Egypt are not included.')
rec('SOV_OT_B', 'REGIME_OT', '1912-04-27', '1912-10-18', 'OT_B', 2746682, sev='{{EV_DODECANESE}}', eev='{{EV_OUCHY}}', derived=[2746682, 2690837, 2803190, 2830316], loc=f'({OL(2746682)} − {OL(2830316)}) ∪ 利比亞（{LYL}）',
    zh='扣掉義大利佔領的多德卡尼斯（另段）；利比亞同前段（義軍 1911-10 起佔領沿岸，未分）。第一次巴爾幹戰爭佔領區法理上仍屬鄂圖曼。', en='Minus the Italian-occupied Dodecanese; Libya as before.')
rec('SOV_OT_C', 'REGIME_OT', '1912-10-18', '1912-11-28', 'OT_C', 2746682, sev='{{EV_OUCHY}}', eev='{{EV_AL_INDEP}}', derived=[2746682, 2830316], loc=f'{OL(2746682)} − {OL(2830316)}',
    zh='烏契和約後不含利比亞與多德卡尼斯。巴爾幹同盟佔領區法理上仍屬鄂圖曼，到倫敦和約。', en='After Ouchy: without Libya and the Dodecanese; areas occupied by the Balkan League remain Ottoman de jure until London.')
rec('SOV_OT_D', 'REGIME_OT', '1912-11-28', '1913-05-30', 'OT_D', 2746682, sev='{{EV_AL_INDEP}}', eev='{{EV_LONDON}}', derived=[2746682, 2830316, 2807008], loc=f'{OL(2746682)} − {OL(2830316)} − {OL(2807008)}',
    zh='再扣掉 1912-11-28 宣布獨立的阿爾巴尼亞（臨時政府另段；當時大部分被塞、希、蒙軍佔領，未分）。', en='Minus Albania from its declaration of independence.')
rec('SOV_OT_E', 'REGIME_OT', '1913-05-30', END, 'OT_E', 2849728, sev='{{EV_LONDON}}', derived=[2849728, 2848136, 2830316, 2807008, 2855613], loc=f'{OL(2849728)} − {OL(2848136)} − {OL(2830316)} − 阿爾巴尼亞',
    zh='倫敦和約後：OHM 2849728（含埃迪爾內與東色雷斯；埃迪爾內 1913-05～07-22 實際由保軍控制，君士坦丁堡和約才確定歸屬，依 OHM 不分，待查證）。扣掉賽普勒斯、多德卡尼斯、阿爾巴尼亞。',
    en='After London per OHM 2849728 (includes Edirne; Bulgarian-held until 22 Jul 1913, pending). Minus Cyprus, the Dodecanese and Albania.')
rec('SOV_LONDON', 'REGIME_LONDON', '1913-05-30', '1913-08-10', 'LONDON', 2746682, sev='{{EV_LONDON}}', eev='{{EV_BUCHAREST}}', layer='not_sovereign',
    derived=[2746682, 2849728, 2830316, 2807008, 2692586, 2692716, 2692556, 2742283, 2739656, 2692219],
    loc=f'{OL(2746682)} − {OL(2849728)} − 多德卡尼斯 − 阿爾巴尼亞 − 克里特 − 塞、希、保、蒙、羅當期範圍',
    zh='非主權：倫敦和約第 2 條割讓給巴爾幹同盟、到布加勒斯特和約才分配的馬其頓、西色雷斯與北愛琴海島嶼（實際分由塞、希、保軍佔領，未分區，待查證）。', en='Not sovereign: territories ceded to the Balkan allies at London, partitioned only at Bucharest (occupation zones not drawn, pending).')
# 巴爾幹各國
rec('SOV_GR_A', 'REGIME_GR', START, '1913-08-10', '2692556', 2692556, eev='{{EV_BUCHAREST}}')
rec('SOV_GR_B', 'REGIME_GR', '1913-08-10', END, '2692585', 2692585, sev='{{EV_BUCHAREST}}', zh='含南馬其頓、伊庇魯斯南部、克里特、北愛琴海島嶼（雅典和約 1913-11-14 才確認對鄂圖曼的和平，界線依 OHM）。', en='Includes southern Macedonia, Crete and the northern Aegean islands.')
rec('SOV_RS_A', 'REGIME_RS', START, '1913-08-10', '2692716', 2692716, eev='{{EV_BUCHAREST}}')
rec('SOV_RS_B', 'REGIME_RS', '1913-08-10', END, '2746681', 2746681, sev='{{EV_BUCHAREST}}', zh='含科索沃、北馬其頓與新帕扎爾桑賈克東半。', en='Includes Kosovo, Vardar Macedonia and the eastern Sanjak.')
rec('SOV_MN_P', 'REGIME_MN_P', START, '1910-08-28', '2692715', 2692715, eev='{{EV_MN_KINGDOM}}')
rec('SOV_MN_K_A', 'REGIME_MN_K', '1910-08-28', '1913-05-30', '2958264', 2958264, sev='{{EV_MN_KINGDOM}}', eev='{{EV_LONDON}}', zh='第一次巴爾幹戰爭佔領區（斯庫台 1913-04 投降後 5 月交列強）法理上仍屬鄂圖曼，到倫敦和約。', en='Areas occupied in the First Balkan War remain Ottoman de jure until London.')
rec('SOV_MN_K_B', 'REGIME_MN_K', '1913-05-30', END, '2739656', 2739656, sev='{{EV_LONDON}}', zh='OHM 起日為倫敦和約日；蒙、塞分新帕扎爾桑賈克的界線 1913-11 才定（待查證）。', en='OHM starts at the Treaty of London; the Montenegro–Serbia line in the Sanjak was fixed in Nov 1913 (pending).')
rec('SOV_BG_A', 'REGIME_BG', '1908-10-05', '1913-08-10', '2742283', 2742283, sev='{{EV_BG_INDEP}}', eev='{{EV_BUCHAREST}}', zh='自 1908-10-05 獨立起（含東魯米利亞）。', en='From independence on 5 Oct 1908 (including Eastern Rumelia).')
rec('SOV_BG_B', 'REGIME_BG', '1913-08-10', END, '2746680', 2746680, sev='{{EV_BUCHAREST}}', zh='布加勒斯特和約後：失去南多布羅加，得皮林馬其頓與西色雷斯（OHM 2746680）。', en='After Bucharest: minus Southern Dobruja, plus Pirin Macedonia and Western Thrace.')
rec('SOV_RO_A', 'REGIME_RO', START, '1913-08-10', '2692219', 2692219, eev='{{EV_BUCHAREST}}')
rec('SOV_RO_B', 'REGIME_RO', '1913-08-10', END, '2693260', 2693260, sev='{{EV_BUCHAREST}}', zh='含南多布羅加。OHM 起日 1913-08-30，本表取布加勒斯特和約日 8 月 10 日。', en='Includes Southern Dobruja; OHM starts 30 Aug 1913, here the treaty date.')
rec('SOV_AL_PROV', 'REGIME_AL_PROV', '1912-11-28', '1914-02-21', '2807008', 2807008, sev='{{EV_AL_INDEP}}', eev='{{EV_AL_PRINCIPALITY}}', layer='not_sovereign',
    zh='非主權：發羅拉臨時政府宣布獨立；大部分地區被塞、希、蒙軍佔領。列強 1913-07-29 倫敦大使會議決定阿爾巴尼亞為自治親王國（待查證）。範圍依 OHM（1913 年界線）。',
    en='Not sovereign: provisional government; much of the area under Serbian, Greek and Montenegrin occupation; recognized by the Powers on 29 Jul 1913 (pending).')
rec('SOV_AL_PR', 'REGIME_AL_PR', '1914-02-21', END, '2855613', 2855613, sev='{{EV_AL_PRINCIPALITY}}')
# 義屬
rec('SOV_IT_AEGEAN', 'REGIME_IT_AEGEAN', '1912-04-27', END, '2830316', 2830316, sev='{{EV_DODECANESE}}', layer='not_sovereign',
    zh='非主權：義大利佔領的多德卡尼斯群島；烏契和約第 2 條約定撤出但未實行，法理上仍屬鄂圖曼（待查證）。', en='Not sovereign: Italian-occupied Dodecanese; Ottoman de jure (withdrawal under Ouchy art. 2 not carried out).')
rec('SOV_LY_TR', 'REGIME_LY_TR', '1912-10-18', END, '2690837', 2690837, sev='{{EV_OUCHY}}', zh='烏契和約後（義大利 1911-11-05 宣布併吞；鄂圖曼以蘇丹詔書給予自治，未明文割讓，待查證）。內陸實際未控制。', en='From Ouchy (Italian annexation decree 5 Nov 1911); interior not controlled (pending).')
rec('SOV_LY_CY', 'REGIME_LY_CY', '1912-10-18', END, '2803190', 2803190, sev='{{EV_OUCHY}}', zh='同的黎波里塔尼亞。', en='As Tripolitania.')
# 伊比利、摩洛哥
rec('SOV_ES_A', 'REGIME_ES_K', START, '1912-11-27', '2860487', 2860487, eev='{{EV_ES_MOROCCO}}', zh='OHM 2860487 含休達、梅利利亞、伊夫尼與薩基亞阿姆拉（西屬撒哈拉北部；實際 1934 年後才進駐，待查證）。', en='Includes Ceuta, Melilla, Ifni and Saguia el-Hamra (effective occupation only from 1934, pending).')
rec('SOV_ES_B', 'REGIME_ES_K', '1912-11-27', END, 'ES_B', 2860486, sev='{{EV_ES_MOROCCO}}', derived=[2860486, 2860424], loc=f'{OL(2860486)} − {OL(2860424)}', zh='扣掉西屬摩洛哥保護區（另段）。', en='Minus the Spanish protectorate zone.')
rec('SOV_MA_ES', 'REGIME_MA_ES', '1912-11-27', END, '2860424', 2860424, sev='{{EV_ES_MOROCCO}}')
rec('SOV_MA_SULT', 'REGIME_MA_SULT', START, '1912-03-30', 'MA_SULT', 2866014, eev='{{EV_FEZ}}', derived=[2866014, 2866017, 2860487], loc=f'({OL(2866014)} ∪ {OL(2866017)}) − {OL(2860487)}',
    zh='含 1907 年起法軍佔領的舍維亞與烏季達一帶（OHM 2866017，法理上仍屬蘇丹，未另分，待查證）。', en='Includes the French-occupied Chaouia and Oujda areas (from 1907; not split, pending).')
rec('SOV_MA_FR_A', 'REGIME_MA_FR', '1912-03-30', '1912-11-27', 'MA_FR_A', 2866016, sev='{{EV_FEZ}}', eev='{{EV_ES_MOROCCO}}', derived=[2866016, 2866014, 2866017, 2860487], loc=f'{OL(2866016)} ∪ 前段蘇丹國範圍',
    zh='菲斯條約後整個謝里夫帝國為法國保護國，到法西條約劃出西班牙區。OHM 2866016 未含中南部約 12 平方度（阿特拉斯以南），依條約併入（待查證）。', en='The whole Sherifian Empire under French protection until the Spanish zone is defined; includes the southern areas missing in OHM 2866016 (pending).')
rec('SOV_MA_FR_B', 'REGIME_MA_FR', '1912-11-27', END, 'MA_FR_B', 2866016, sev='{{EV_ES_MOROCCO}}', derived=[2866016, 2866014, 2866017, 2860424, 2860486], loc=f'({OL(2866016)} ∪ 蘇丹國範圍) − {OL(2860424)} − {OL(2860486)}',
    zh='扣掉西屬摩洛哥保護區；丹吉爾國際共管 1923 年才成立，不分。', en='Minus the Spanish zone; Tangier not split.')
rec('SOV_PT_K', 'REGIME_PT_K', START, '1910-10-05', '2959467', 2959467, eev='{{EV_PT_REPUBLIC}}', zh='OHM 迄日只到年（1910），本表到 1910-10-05 革命。', en='OHM gives only the year 1910; ends with the revolution of 5 Oct 1910.')

def write_sov(n, ph, regime, start, end, gk, layer, sev, eev, rid, derived, loc, zh, en):
    m = MAN[rid]; gl, attr, osm = lic(derived)
    b = {'regimeId': '{{%s}}' % regime, 'geometry': None, 'validPeriod': {'start': start, 'end': end}, 'layerStatus': layer,
         'geometrySourceId': '{{SRC_OHM_WW1}}', 'geometryLocator': loc, 'geometryLicense': gl, 'attribution': attr, 'startEventId': sev, 'endEventId': eev,
         'ohmRelationId': rid, 'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'], 'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date'],
         'provenance': {'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': osm, 'ohmFixme': m['fixme'], 'ohmRelationSource': m['relation_source'],
                        'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'], 'ohmTimestamp': m['ohm_timestamp'], 'coastline': '{{SRC_NE_LAND}}',
                        'licenseReview': 'osm_derived_ways' if osm else None, 'trialWindow': 'WW1 第一批 1908-10-06～1914-07-28'},
         'note': {'zh-Hant': (zh + ('' if end != END else '到 1914-07-28（本批試驗期間終點，無迄事件）。')).strip(), 'en': (en + ('' if end != END else ' Until 28 Jul 1914 (end of this batch).')).strip()}}
    if len(derived) > 1: b['provenance'].update({'derivedFrom': [OL(r) for r in derived], 'derivation': loc})
    if start == START and sev is None: b['note']['zh-Hant'] = '起於 1908-10-06（本批試驗期間起點，不是政權起日）。' + b['note']['zh-Hant']; b['note']['en'] = 'From 6 Oct 1908 (start of this batch). ' + b['note']['en']
    if not b['note']['zh-Hant']: b['note'] = None
    write(f'05-sovereignty-{n:02d}-{ph.lower()}.json', ph, '/api/v1/sovereignty-records', b, None, geom=gk)
for n, r in enumerate(REC, 1): write_sov(n, *r)

# 葡萄牙共和國：既有紀錄起日 1910-01-01（OHM 只到年）→ 撤回，改由 1910-10-05 革命起重送（I5：先撤後增）
write('04-retract-01-portuguese-republic.json', f'RETRACTED_{PT["id"]}', f'/api/v1/sovereignty-records/{PT["id"]}/retraction',
      {'reason': 'WW1 第一批：起日由 1910-01-01（OHM 只到年）改為 1910-10-05 葡萄牙革命（FRUS 1910 Doc. 905），補起事件後重送'}, {'fix': True, 'oldId': PT['id']})
b = {'regimeId': PT['regimeId'], 'geometry': None, 'validPeriod': {'start': '1910-10-05', 'end': PT['end']}, 'layerStatus': PT['layer'], 'geometrySourceId': PT['geometrySourceId'],
     'geometryLocator': PT['geometryLocator'], 'geometryLicense': PT['geometryLicense'], 'attribution': PT['attribution'], 'startEventId': '{{EV_PT_REPUBLIC}}', 'endEventId': PT['endEventId'],
     'ohmRelationId': PT['ohmRelationId'], 'ohmVersion': PT['ohmVersion'], 'ohmFetchedAt': PT['ohmFetchedAt'], 'ohmStartRaw': PT['ohmStartRaw'], 'ohmEndRaw': PT['ohmEndRaw'],
     'provenance': {**copy.deepcopy(PT['provenance']), 'coastline': PT['provenance'].get('coastline'), 'replaces': PT['id']},
     'note': {'zh-Hant': '起於 1910-10-05 革命（OHM 起日只到年 1910）。', 'en': 'From the revolution of 5 Oct 1910 (OHM gives only the year 1910).'}}
write(f'05-sovereignty-{len(REC)+1:02d}-sov_pt_republic.json', 'SOV_PT_REPUBLIC', '/api/v1/sovereignty-records', b, None, geom='COPY_PT')

# ── 佔領歸屬 ──
write('06-occupation-01-occ_it_aegean.json', 'OCC_IT_AEGEAN', '/api/v1/occupation-attributions', {'occupiedRegimeId': '{{REGIME_IT_AEGEAN}}', 'occupierRegimeId': '{{REGIME_IT}}',
      'controlKind': 'military_administration', 'validPeriod': {'start': '1912-04-27', 'end': END}, 'basisEventId': '{{EV_DODECANESE}}', 'coOccupied': False,
      'note': {'zh-Hant': '義大利軍事佔領多德卡尼斯（起日依 OHM，待查證）。', 'en': 'Italian military occupation of the Dodecanese (start per OHM, pending).'}})

# ── 衝突 ──
def at(regime, d):
    gs = [G[r[4]] for r in REC if r[1] == regime and r[2] <= d < r[3]]
    return unary_union(gs) if gs else None
def border_mid(a, b):
    line = a.boundary.intersection(b.buffer(0.02))
    parts = [g for g in getattr(line, 'geoms', [line]) if isinstance(g, (LineString, MultiLineString)) and not g.is_empty]
    if not parts: return None
    u = unary_union(parts); m = linemerge(u) if isinstance(u, MultiLineString) else u; segs = list(getattr(m, 'geoms', [m]))
    best = max(segs, key=lambda s: s.length)
    if best.length < 0.05: return None
    p = best.interpolate(0.5, normalized=True); return [round(p.x, 4), round(p.y, 4)]
CF = [('CF_IT_OT', 'REGIME_IT', 'REGIME_OT', 'EV_IT_TR_WAR', 'EV_OUCHY', '1911-09-29', [13.1913, 32.8872], '的黎波里（義軍 1911-10 登陸地，雙方不相鄰，取主要戰區）'),
      ('CF_MN_OT', 'REGIME_MN_K', 'REGIME_OT', 'EV_MN_WAR', 'EV_LONDON', '1912-10-08', None, None),
      ('CF_BG_OT', 'REGIME_BG', 'REGIME_OT', 'EV_BALKAN_WAR', 'EV_LONDON', '1912-10-18', None, None),
      ('CF_RS_OT', 'REGIME_RS', 'REGIME_OT', 'EV_BALKAN_WAR', 'EV_LONDON', '1912-10-18', None, None),
      ('CF_GR_OT', 'REGIME_GR', 'REGIME_OT', 'EV_BALKAN_WAR', 'EV_LONDON', '1912-10-18', None, None),
      ('CF_BG_RS', 'REGIME_BG', 'REGIME_RS', 'EV_BALKAN2', 'EV_BUCHAREST', '1913-06-29', None, None),
      ('CF_BG_GR', 'REGIME_BG', 'REGIME_GR', 'EV_BALKAN2', 'EV_BUCHAREST', '1913-06-29', [22.65, 41.05], '馬其頓戰線（保、希在 1913-06 不相鄰，雙方隔倫敦割讓區；取保軍攻擊方向的蓋夫蓋利亞一帶，待查證）'),
      ('CF_RO_BG', 'REGIME_RO', 'REGIME_BG', 'EV_RO_WAR', 'EV_BUCHAREST', '1913-07-10', None, None),
      ('CF_OT_BG2', 'REGIME_OT', 'REGIME_BG', 'EV_OT_BG2', 'EV_CONSTANTINOPLE', '1913-07-12', [26.5555, 41.6771], '埃迪爾內（鄂圖曼 1913-07-22 收復；倫敦和約後雙方界線依 OHM 不相鄰，取主要目標）'),
      ('CF_AH_RS', 'REGIME_AH', 'REGIME_RS', 'EV_AH_RS_WAR', None, '1914-07-28', None, None)]
cf_qa = {}
for n, (ph, a, b_, sev, eev, d, fb, fbm) in enumerate(CF, 1):
    pt = border_mid(at(a, d), at(b_, d))
    if pt and not fb: method = f'本批主權紀錄在開戰日 {d} 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid）'
    else: pt, method = fb, fbm
    assert pt, ph
    cf_qa[ph] = pt
    write(f'07-conflict-{n:02d}-{ph.lower()}.json', ph, '/api/v1/conflict-records', {'regimeAId': '{{%s}}' % a, 'regimeBId': '{{%s}}' % b_, 'startEventId': '{{%s}}' % sev,
          'endEventId': ('{{%s}}' % eev) if eev else None, 'location': {'type': 'Point', 'coordinates': pt}, 'locationMethod': method})

# ── QA：抽樣日互不重疊（新紀錄＋未動的既有紀錄）──
base = [(r['slug'], make_valid(shape(r['geometry'])), r['start'], r['end'] or '9999-12-31') for r in ROWS if r['slug'] != 'portuguese-republic']
new = [(r[0], G[r[4]], r[2], r[3]) for r in REC] + [('SOV_PT_REPUBLIC', G['COPY_PT'], '1910-10-05', PT['end'])]
DAYS = ['1908-10-06', '1908-10-07', '1910-09-01', '1911-01-01', '1912-06-01', '1912-11-01', '1913-01-01', '1913-07-01', '1913-09-01', '1914-03-01', '1914-07-28']
qa = {'area_deg2': {k: round(v.area, 3) for k, v in G.items()}, 'overlaps': {}, 'conflictLocations': cf_qa}
for d in DAYS:
    items = [(k, g) for k, g, s, e in new + base if s <= d < e]
    tree = STRtree([g for _, g in items]); worst = []
    for i_, (ni, gi) in enumerate(items):
        for j in tree.query(gi):
            if j <= i_: continue
            a = gi.intersection(items[j][1]).area
            if a > 1e-3: worst.append((ni, items[j][0], round(a, 4)))
    qa['overlaps'][d] = worst
os.makedirs(ROOT, exist_ok=True)
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in G.items()]},
          open(os.path.join(ROOT, 'ww1-1908-1914-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(qa, open(os.path.join(ROOT, 'qa.json'), 'w'), indent=1, ensure_ascii=False)
print(json.dumps(qa['overlaps'], ensure_ascii=False)); print(cf_qa)
bad = [w for d in DAYS for w in qa['overlaps'][d]]
assert not bad, bad
