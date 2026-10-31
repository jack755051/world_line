#!/usr/bin/env python3
"""亞洲太平洋第一批（1937-07-07～1945-09-02；DRAFT，待 Tai 檢查）：日本（含朝鮮、臺灣、樺太、關東州、南洋廳委任統治地）、中華民國、
滿洲國（非主權）、蒙古人民共和國、唐努烏梁海、西藏、泰國，1945-08-24 起北韓的蘇聯民政署（非主權）；華北、華中的傀儡政權只建政權與事件。
幾何：固定版本 OHM（ohm-manifest.json；Overpass osm_base 2026-10-31T11:30:12Z），東亞框＋ Natural Earth 10m 陸地裁切。
OHM 沒有日本佔領中國地區、臨時政府／維新政府／蒙疆／汪政權的邊界：不畫，於註記與回報列為空白（待查證），不補造。
只寫開發庫（5052）。
"""
import json, os, datetime, itertools
from shapely.geometry import shape, mapping, MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); OUT = os.path.join(ROOT, 'requests')
MAN = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))}
g = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-asia1.geojson')))['features']}
def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x, 'geoms', []) for p in polys(y)]
def clean(x):
    x = make_valid(set_precision(make_valid(x), 1e-4))
    return MultiPolygon([p for p in polys(x) if p.area > 1e-5])
def D(a, *bs): return clean(g[a].difference(unary_union([g[b] for b in bs]))) if bs else clean(g[a])
JP37, JP39, CN37, CN38, CN39, MK, MN, TUVA, TIBET, KR_SU = 2889894, 2948948, 2694471, 2948950, 2948949, 2885965, 2942671, 2849759, 2828810, 2801070
TH = [2874871, 2801980, 2874870, 2961563, 2848473]
geo = {'A_JP_A': D(JP37), 'A_JP_B': D(JP39), 'A_JP_C': D(JP39, KR_SU), 'A_KR_SU': D(KR_SU),
       'A_CN_A': D(CN37, MK), 'A_CN_B': D(CN38, MK), 'A_CN_C': D(CN39, MK), 'A_MK': D(MK), 'A_MN': D(MN), 'A_TUVA': D(TUVA), 'A_TIBET': D(TIBET),
       **{f'A_TH_{i}': D(r) for i, r in enumerate(TH, 1)}}

def write(name, ph, post, body, meta=None, geom=None):
    req = {'_placeholder': ph, '_post': post, **({'_geometryFrom': geom} if geom else {}), **({'_meta': meta} if meta else {}), 'body': body}
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')
GPO = 'United States Department of State; United States Government Printing Office, Washington'
SRC = [('SRC_OHM_ASIA1', None),
       ('SRC_FRUS_1937_III', ('Foreign Relations of the United States, Diplomatic Papers, 1937, The Far East, Volume III', 'frus1937v03')),
       ('SRC_FRUS_1940_IV', ('Foreign Relations of the United States, Diplomatic Papers, 1940, The Far East, Volume IV', 'frus1940v04')),
       ('SRC_FRUS_JP_1931_41_II', ('Papers Relating to the Foreign Relations of the United States, Japan, 1931–1941, Volume II', 'frus1931-41v02')),
       ('SRC_FRUS_1945_VI', ('Foreign Relations of the United States: Diplomatic Papers, 1945, The British Commonwealth, The Far East, Volume VI', 'frus1945v06')),
       ('SRC_FRUS_1945_VII', ('Foreign Relations of the United States: Diplomatic Papers, 1945, The Far East, China, Volume VII', 'frus1945v07'))]
for i, (ph, t) in enumerate(SRC, 1):
    b = ({'sourceKind': 'dataset', 'title': 'OpenHistoricalMap — boundary=administrative 關係（東亞第一批：日本、中國、滿洲國、蒙古、唐努烏梁海、西藏、泰國，1937～1945）',
          'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
          'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
          'publishedText': 'Overpass osm_base 2026-10-31T11:30:12Z；逐筆見 borders-asia-1/ohm-manifest.json', 'note': 'OHM 整體以 CC0 1.0 釋出；本批成員線段皆未帶 CC BY 標籤。'}
         if t is None else {'sourceKind': 'official_record', 'title': t[0], 'publisher': GPO, 'licenseCode': 'us_federal_pd',
                            'licenseEvidenceUrl': 'https://www.state.gov/copyright-information', 'url': 'https://history.state.gov/historicaldocuments/' + t[1]})
    write(f'01-source-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sources', b, {'priorPlaceholder': False})

REG = [
 ('REGIME_JP', 'empire-of-japan', '大日本帝國', 'ja', '大日本帝國', 'Empire of Japan', 'FRUS 1931–41 II Doc. 422（the Japanese Empire）；日文名為通行稱呼'),
 ('REGIME_CN', 'republic-of-china-nationalist', '中華民國', 'zh', '中華民國（國民政府）', 'Republic of China (Nationalist Government)', 'FRUS 1931–41 II Doc. 75（National Government of the Republic of China）'),
 ('REGIME_MANCHUKUO', 'manchukuo', '滿洲國', 'zh', '滿洲國（日本扶植）', 'Manchukuo (Japanese puppet state)', 'FRUS 1937 III Doc. 674（Manchukuo）；OHM relation/2885965'),
 ('REGIME_MN', 'mongolian-peoples-republic', 'Бүгд Найрамдах Монгол Ард Улс', 'mn', '蒙古人民共和國', "Mongolian People's Republic", 'FRUS 1945 VII Doc. 120（Mongolian People’s Republic）；蒙文名為通行稱呼'),
 ('REGIME_TUVA', 'tuvan-peoples-republic', 'Тыва Арат Республика', 'tyv', '唐努烏梁海（圖瓦人民共和國）', "Tuvan People's Republic", "OHM relation/2849759 name；圖瓦文名為通行稱呼，待查證"),
 ('REGIME_TIBET', 'tibet-ganden-phodrang', 'བོད་', 'bo', '西藏（噶廈政府）', 'Tibet (Ganden Phodrang government)', 'OHM relation/2828810 name；藏文名為通行稱呼，待查證'),
 ('REGIME_TH', 'kingdom-of-thailand', 'ราชอาณาจักรไทย', 'th', '泰國（暹羅）', 'Thailand (Siam)', 'FRUS 1940 IV Doc. 182（Thailand）；泰文名為通行稱呼；1939-06-24 前國名暹羅'),
 ('REGIME_SU_KOREA', 'soviet-civil-administration-korea', 'Soviet Civil Administration in Korea', 'en', '蘇聯民政署（北緯 38 度以北的朝鮮，蘇軍佔領）', 'Soviet Civil Administration (Korea north of the 38th parallel)', 'OHM relation/2801070 name；FRUS 1945 VI Doc. 771（38th parallel）'),
 ('REGIME_CN_PROV', 'provisional-government-republic-of-china-1937', '中華民國臨時政府', 'zh', '中華民國臨時政府（北平，日本扶植）', 'Provisional Government of the Republic of China (Peiping, Japanese-sponsored)', 'FRUS 1937 III Doc. 897（“Provisional Government of the Republic of China”）'),
 ('REGIME_CN_REFORMED', 'reformed-government-republic-of-china-1938', '中華民國維新政府', 'zh', '中華民國維新政府（南京，日本扶植）', 'Reformed Government of the Republic of China (Nanking, Japanese-sponsored)', 'FRUS 1931–41 II Doc. 73（the Reformed Government of the Republic of China）'),
 ('REGIME_MENGJIANG', 'mengjiang', '蒙疆', 'zh', '蒙疆（日本扶植）', 'Mengjiang (Japanese-sponsored)', 'FRUS 1939 III Doc. 405（Mengchiang）；正式名稱與成立日待查證'),
 ('REGIME_CN_WANG', 'reorganized-national-government-nanjing', '中華民國國民政府（南京）', 'zh', '汪精衛政權（南京國民政府，日本扶植）', 'Wang Jingwei regime (Reorganized National Government, Nanking; Japanese-sponsored)', 'FRUS 1940 IV Doc. 350（“National Government of the Republic of China” at Nanking）'),
]
for i, (ph, slug, orig, lang, zh, en, src) in enumerate(REG, 1):
    write(f'02-regime-{i:02d}-{slug}.json', ph, '/api/v1/regimes', {'slug': slug, 'names': [
        {'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]},
        {'priorPlaceholder': False, 'nameSource': src})

def ev(i, ph, kind, start, zh, en, parts, cites, tn=None, precision='day'):
    d0 = datetime.date.fromisoformat(start + ('-01' if precision == 'month' else ''))
    e = ((d0.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) if precision == 'month' else d0 + datetime.timedelta(days=1)).isoformat()
    body = {'eventKind': kind, 'occurred': {'start': d0.isoformat(), 'end': e}, 'datePrecision': precision, 'summary': {'zh-Hant': zh, 'en': en},
            'participants': [{'regimeId': '{{%s}}' % r, 'role': role} for r, role in parts],
            'citations': [{'sourceId': '{{%s}}' % s, 'locator': l, 'evidenceNote': n} for s, l, n in cites]}
    if tn: body['timeNote'] = {'zh-Hant': tn[0], 'en': tn[1]}
    write(f'03-event-{i:02d}-{ph.lower()}.json', ph, '/api/v1/events', body, {'verification': 'verified' if cites and not (tn and '待查證' in tn[0]) else 'pending（待查證）'})
B = lambda *rs: [(r, 'belligerent') for r in rs]
O = lambda *rs: [(r, 'other') for r in rs]
NOSRC = lambda w: ('尚未取得正式出處（待查證）；日期依 ' + w + '。', 'No formal source yet (pending); date from ' + w + '.')
E = [
 ('EV_MARCO_POLO', 'war', '1937-07-07', '盧溝橋事變：中日兩軍在北平近郊盧溝橋衝突，全面戰爭開始', 'Marco Polo Bridge Incident: Chinese and Japanese troops clash near Peiping; full-scale war begins', B('REGIME_JP', 'REGIME_CN'),
  [('SRC_FRUS_1937_III', 'Doc. 107, pp. 129–130', '駐華大使館 1937-07-08 電：日軍要求中國軍隊撤出盧溝橋（Marco Polo Bridge）與宛平。'),
   ('SRC_FRUS_1937_III', 'Doc. 109, pp. 130–131', '1937-07-09 電：中日兩軍昨日凌晨在盧溝橋發生衝突。')],
  ('衝突發生於 7 日夜間至 8 日凌晨（當地時間），通行記為 7 月 7 日。', 'The clash took place on the night of 7–8 July (local time); conventionally dated 7 July.')),
 ('EV_CN_PROVISIONAL', 'political', '1937-12-14', '日本扶植的「中華民國臨時政府」在北平成立', 'Japanese-sponsored “Provisional Government of the Republic of China” set up in Peiping', O('REGIME_CN_PROV', 'REGIME_JP'),
  [('SRC_FRUS_1937_III', 'Doc. 897, p. 807', '駐北平使館 1937-12-14 電：新政府名為「中華民國臨時政府」，設行政、議政、司法三委員會。')]),
 ('EV_CN_REFORMED', 'political', '1938-03-28', '日本扶植的「中華民國維新政府」在南京成立', 'Japanese-sponsored “Reformed Government of the Republic of China” set up in Nanking', O('REGIME_CN_REFORMED', 'REGIME_JP'), [],
  ('尚未取得正式出處（待查證）；日期為通行說法。', 'No formal source yet (pending); commonly cited date.')),
 ('EV_MENGJIANG', 'political', '1939-09-01', '蒙古聯合自治政府（蒙疆）成立', 'Mongolian United Autonomous Government (Mengjiang) formed', O('REGIME_MENGJIANG', 'REGIME_JP'), [],
  ('尚未取得正式出處（待查證）；日期為通行說法。', 'No formal source yet (pending); commonly cited date.')),
 ('EV_CN_WANG', 'political', '1940-03-30', '汪精衛在南京成立「國民政府」（日本扶植）；重慶國民政府聲明不承認', 'Wang Jingwei sets up a “National Government” at Nanking (Japanese-sponsored); Chungking declares it void',
  O('REGIME_CN_WANG', 'REGIME_JP', 'REGIME_CN'),
  [('SRC_FRUS_1940_IV', 'Doc. 350, p. 308', '1940-03-31 電：中國外交部長 3 月 30 日備忘錄，稱日本軍閥在南京成立所謂「中華民國國民政府」，中國政府絕不承認。'),
   ('SRC_FRUS_JP_1931_41_II', 'Doc. 75, pp. 122–123', '駐華大使 1940-12-01 電轉中國外交部長 11 月 30 日聲明：汪精衛為國賊，南京偽組織為非法組織，其一切行為無效。')]),
 ('EV_PARACEL_1938', 'political', '1938-07-03', '中國國界變動（OHM 版本交替；南海島礁）', 'Change in the Chinese boundary (OHM version change; South China Sea islands)', O('REGIME_CN'), [], NOSRC('OHM relation/2694471 end_date')),
 ('EV_SPRATLY_1939', 'political', '1939-04-09', '日本將南海島礁（新南群島）劃入臺灣（OHM 版本交替）', 'Japan places the Spratly Islands under Taiwan (OHM version change)', O('REGIME_JP', 'REGIME_CN'), [], NOSRC('OHM relation/2889894／2948948')),
 ('EV_TH_RENAME', 'political', '1939-06-24', '暹羅改國名為泰國', 'Siam renamed Thailand', O('REGIME_TH'), [], NOSRC('OHM relation/2874871 end_date')),
 ('EV_TH_1941', 'treaty', '1941-03', '泰法戰爭停戰，泰國取得法屬印度支那部分領土（1941-05-09 東京條約）', 'Franco-Thai war settlement: Thailand gains parts of French Indochina (Tokyo treaty, 9 May 1941)', O('REGIME_TH', 'REGIME_JP'), [],
  ('尚未取得正式出處（待查證）；OHM relation/2801980 end_date 只標 1941-03，紀錄取 03-01。', 'No formal source; OHM gives only 1941-03.'), 'month'),
 ('EV_TH_SHAN', 'treaty', '1943-08-18', '日本將緬甸撣邦兩地交泰國（OHM 版本交替）', 'Japan transfers two Shan states to Thailand (OHM version change)', O('REGIME_TH', 'REGIME_JP'), [], NOSRC('OHM relation/2961563 start_date')),
 ('EV_TH_MALAY', 'treaty', '1943-10-18', '日本將馬來北部四州交泰國（OHM 版本交替）', 'Japan transfers four northern Malay states to Thailand (OHM version change)', O('REGIME_TH', 'REGIME_JP'), [], NOSRC('OHM relation/2848473 start_date')),
 ('EV_PEARL_HARBOR', 'war', '1941-12-07', '日本偷襲珍珠港；美國 12 月 8 日對日宣戰', 'Japanese attack on Pearl Harbor; the US declares war on Japan on 8 December', B('REGIME_JP', 'REGIME_US'),
  [('SRC_FRUS_JP_1931_41_II', 'Doc. 419, pp. 786–787（註）', '日軍攻擊珍珠港：華盛頓時間 12 月 7 日下午 1:20（檀香山 7:50），東京時間 12 月 8 日凌晨 3:20。'),
   ('SRC_FRUS_JP_1931_41_II', 'Doc. 422, pp. 793–794', '羅斯福 1941-12-08 致國會：請國會宣布自 12 月 7 日起美國與日本帝國處於戰爭狀態。')],
  ('夏威夷當地 12 月 7 日；東京時間 12 月 8 日。', 'Local date 7 Dec (Hawaii); 8 Dec in Tokyo.')),
 ('EV_WAR_JP_UK', 'war', '1941-12-08', '日軍進攻英屬馬來亞與香港，日英開戰', 'Japan attacks British Malaya and Hong Kong; war between Japan and the UK', B('REGIME_JP', 'REGIME_UK'), [],
  ('尚未取得正式出處（待查證）；日期為通行說法（當地 12 月 8 日）。', 'No formal source yet (pending); commonly cited date.')),
 ('EV_TUVA', 'political', '1944-10-11', '唐努烏梁海併入蘇聯', 'Tuvan People’s Republic annexed by the USSR', O('REGIME_TUVA', 'REGIME_SU'), [], NOSRC('OHM relation/2849759 end_date')),
 ('EV_SU_JP_WAR', 'war', '1945-08-08', '蘇聯對日宣戰（8 月 9 日起進攻滿洲、朝鮮北部、樺太）', 'The Soviet Union declares war on Japan (offensive into Manchuria, northern Korea and Karafuto from 9 Aug)', B('REGIME_SU', 'REGIME_JP'),
  [('SRC_FRUS_1945_VI', 'Doc. 402, p. 624', '1945-08-08 電：莫洛托夫將聲明蘇聯與日本處於戰爭狀態（8 月 8 日面交日本大使佐藤）。')]),
 ('EV_MN_JP_WAR', 'war', '1945-08-10', '蒙古人民共和國對日宣戰', "The Mongolian People's Republic declares war on Japan", B('REGIME_MN', 'REGIME_JP'),
  [('SRC_FRUS_1945_VII', 'Doc. 120, pp. 150–151', '駐蘇大使 1945-08-11 電：8 月 11 日報載烏蘭巴托塔斯社 8 月 10 日電，蒙古人民共和國小呼拉爾與部長會議當日上午聯席會議一致決定對日宣戰（附宣言）。'),
   ('SRC_FRUS_1945_VII', 'Doc. 122, p. 152', '駐蘇大使 1945-08-11 電：蒙古人民共和國對日宣戰，強調其「獨立」與「主權」主張。')],
  ('宣戰決定於 8 月 10 日上午（烏蘭巴托），FRUS 見於 8 月 11 日電報。', 'Decision taken on the morning of 10 Aug (Ulan Bator); reported in FRUS on 11 Aug.')),
 ('EV_MANCHUKUO_END', 'political', '1945-08-17', '滿洲國解體（溥儀退位）', 'Dissolution of Manchukuo (abdication of Puyi)', O('REGIME_MANCHUKUO'), [], NOSRC('OHM relation/2885965 end_date')),
 ('EV_SU_KOREA', 'political', '1945-08-24', '蘇軍在北緯 38 度以北的朝鮮設立民政署', 'Soviet civil administration set up in Korea north of the 38th parallel', O('REGIME_SU_KOREA', 'REGIME_SU', 'REGIME_JP'),
  [('SRC_FRUS_1945_VI', 'Doc. 771, pp. 1037–1039（註）', '一般命令第一號：朝鮮北緯 38 度以北的日軍向蘇軍投降，以南向美軍投降。')],
  ('民政署成立日依 OHM relation/2801070 start_date（待查證）；FRUS 只證明以 38 度線分區受降。', 'Date from OHM (pending); FRUS only shows the 38th-parallel surrender zones.')),
 ('EV_JP_SURRENDER', 'surrender', '1945-09-02', '日本簽署降伏文書', 'Japan signs the Instrument of Surrender', [('REGIME_JP', 'signatory'), ('REGIME_US', 'signatory'), ('REGIME_CN', 'signatory'), ('REGIME_UK', 'signatory'), ('REGIME_SU', 'signatory')],
  [('SRC_FRUS_1945_VI', 'Doc. 776, pp. 1043–1044（註）', '麥克阿瑟 1945-09-07 對朝鮮公告：依 9 月 2 日簽署的降伏文書。')]),
]
for i, e in enumerate(E, 1): ev(i, *e)

L = lambda *rs: ' − '.join(f'relation/{r} v{MAN[r]["ohm_version"]}' for r in rs)
def rec(i, ph, regime, fix, main, rels, layer, start, end, sev, eev, nzh, nen):
    m = MAN[main]
    body = {'regimeId': '{{%s}}' % regime, 'geometry': None, 'validPeriod': {'start': start, 'end': end}, 'layerStatus': layer,
            'geometrySourceId': '{{SRC_OHM_ASIA1}}', 'geometryLocator': L(*rels), 'geometryLicense': 'cc0', 'attribution': None,
            'startEventId': ('{{%s}}' % sev) if sev else None, 'endEventId': ('{{%s}}' % eev) if eev else None,
            'ohmRelationId': main, 'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'], 'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date'],
            'provenance': {'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': sum(MAN[r]['osm_derived_way_count'] for r in rels),
                           'ohmFixme': m['fixme'], 'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'], 'ohmTimestamp': m['ohm_timestamp'],
                           'coastline': '{{SRC_NE_LAND}}', 'derivedFrom': [f'relation/{r} v{MAN[r]["ohm_version"]}' for r in rels], 'derivation': L(*rels),
                           'trialWindow': '1937-07-07～1945-09-02（亞洲第一批）'},
            'note': {'zh-Hant': nzh, 'en': nen}}
    write(f'04-sovereignty-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sovereignty-records', body, {'ohmName': m['name']}, geom=fix)
JPN = '大日本帝國（OHM）：含朝鮮、臺灣與澎湖、樺太（南庫頁島）、千島，租借的關東州與委任統治的南洋群島。佔領地（中國、東南亞、太平洋島嶼）不在此紀錄，另批補上。'
JPE = 'Empire of Japan (OHM) incl. Korea, Taiwan, Karafuto, the Kurils, the Kwantung Leased Territory and the South Seas Mandate; occupied areas are separate.'
CNN = '中華民國（國民政府）：OHM 中國扣掉滿洲國。日本佔領區與華北、華中傀儡政權（臨時政府、維新政府、蒙疆、汪政權）OHM 沒有邊界，未分出（空白待查證），因此佔領區仍畫在中華民國內；西藏、外蒙古另畫（中華民國主張主權）。'
CNE = 'Republic of China: OHM China minus Manchukuo. Japanese-occupied areas and puppet regimes have no OHM boundaries and are not separated (pending); Tibet and Outer Mongolia drawn separately (claimed by the ROC).'
T = '1937-07-07'
R = [
 ('SOVA_JP_A', 'REGIME_JP', 'A_JP_A', JP37, [JP37], 'de_jure', T, '1939-04-09', None, 'EV_SPRATLY_1939', JPN + '起點為試驗期間起點（不追溯）。', JPE),
 ('SOVA_JP_B', 'REGIME_JP', 'A_JP_B', JP39, [JP39], 'de_jure', '1939-04-09', '1945-08-24', 'EV_SPRATLY_1939', 'EV_SU_KOREA', JPN + '1945-08 蘇軍佔領樺太、千島，OHM 未分，簡化。', JPE),
 ('SOVA_JP_C', 'REGIME_JP', 'A_JP_C', JP39, [JP39, KR_SU], 'de_jure', '1945-08-24', '1945-09-02', 'EV_SU_KOREA', 'EV_JP_SURRENDER', JPN + '扣掉北緯 38 度以北的朝鮮（蘇聯民政署）；樺太、千島的蘇軍佔領 OHM 未分，簡化。', JPE),
 ('SOVA_KR_SU', 'REGIME_SU_KOREA', 'A_KR_SU', KR_SU, [KR_SU], 'not_sovereign', '1945-08-24', '1945-09-02', 'EV_SU_KOREA', 'EV_JP_SURRENDER',
  '非主權：蘇軍佔領下的北緯 38 度以北朝鮮（OHM 蘇聯民政署）。法理上仍屬日本至降伏，之後另議。', 'Not sovereign: Soviet-occupied Korea north of the 38th parallel.'),
 ('SOVA_CN_A', 'REGIME_CN', 'A_CN_A', CN37, [CN37, MK], 'de_jure', T, '1938-07-03', 'EV_MARCO_POLO', 'EV_PARACEL_1938', CNN, CNE),
 ('SOVA_CN_B', 'REGIME_CN', 'A_CN_B', CN38, [CN38, MK], 'de_jure', '1938-07-03', '1939-04-09', 'EV_PARACEL_1938', 'EV_SPRATLY_1939', CNN, CNE),
 ('SOVA_CN_C', 'REGIME_CN', 'A_CN_C', CN39, [CN39, MK], 'de_jure', '1939-04-09', '1945-09-02', 'EV_SPRATLY_1939', 'EV_JP_SURRENDER',
  CNN + '1945-08-17 滿洲國解體後至 09-02，滿洲（蘇軍佔領）OHM 沒有幾何，留白。', CNE),
 ('SOVA_MK', 'REGIME_MANCHUKUO', 'A_MK', MK, [MK], 'not_sovereign', T, '1945-08-17', None, 'EV_MANCHUKUO_END',
  '非主權：日本扶植的滿洲國（OHM relation/2885965），法理上為中國領土（中華民國不承認）。', 'Not sovereign: Japanese puppet state of Manchukuo, de jure Chinese territory.'),
 ('SOVA_MN', 'REGIME_MN', 'A_MN', MN, [MN], 'de_jure', T, '1945-09-02', None, None,
  '蒙古人民共和國（OHM）。中華民國當時主張外蒙古主權（1945-08 中蘇條約後同意公投後承認獨立，FRUS 1945 VII Doc. 688），層級依 OHM 事實國界。', "Mongolian People's Republic (de facto, OHM); claimed by the ROC."),
 ('SOVA_TUVA', 'REGIME_TUVA', 'A_TUVA', TUVA, [TUVA], 'de_jure', T, '1944-10-11', None, 'EV_TUVA',
  '唐努烏梁海（圖瓦人民共和國，OHM）。1944-10-11 併入蘇聯；蘇聯亞洲部分目前未畫（歐洲紀錄只到東經 42 度），之後留白。', "Tuvan People's Republic (OHM) until annexation by the USSR."),
 ('SOVA_TIBET', 'REGIME_TIBET', 'A_TIBET', TIBET, [TIBET], 'de_jure', T, '1945-09-02', None, None,
  '西藏（噶廈政府，OHM 事實國界）。中華民國主張主權；層級依 OHM，待查證。', 'Tibet (de facto, OHM); claimed by the ROC (pending).'),
]
THN = [('暹羅（OHM）。', 'Siam (OHM).'), ('泰國（1939-06-24 改國名，OHM）。', 'Thailand (OHM).'),
       ('泰國，含泰法戰爭後取得的法屬印度支那部分領土（OHM；起始日只標 1941-03，取 03-01）。', 'Thailand incl. territory gained from French Indochina (OHM).'),
       ('泰國，加上日本交付的撣邦兩地（OHM）。', 'Thailand incl. two Shan states transferred by Japan (OHM).'),
       ('泰國，加上日本交付的馬來北部四州（OHM）。泰國 1942-01-25 對英美宣戰，屬軸心一方；陣營另議。', 'Thailand incl. four northern Malay states transferred by Japan (OHM).')]
TS = [(T, '1939-06-24', None, 'EV_TH_RENAME'), ('1939-06-24', '1941-03-01', 'EV_TH_RENAME', 'EV_TH_1941'), ('1941-03-01', '1943-08-18', 'EV_TH_1941', 'EV_TH_SHAN'),
      ('1943-08-18', '1943-10-18', 'EV_TH_SHAN', 'EV_TH_MALAY'), ('1943-10-18', '1945-09-02', 'EV_TH_MALAY', None)]
for i, (r, (s, e, sv, evv), (nz, ne)) in enumerate(zip(TH, TS, THN), 1):
    R.append((f'SOVA_TH_{i}', 'REGIME_TH', f'A_TH_{i}', r, [r], 'de_jure', s, e, sv, evv, nz + '英屬緬甸、馬來亞等鄰近殖民地另批補上。', ne))

# 同日不重疊（批內）
for d in sorted({r[6] for r in R}):
    act = [r for r in R if r[6] <= d < r[7]]
    for a, b in itertools.combinations(act, 2):
        x = geo[a[2]].intersection(geo[b[2]]).area
        assert x < 1e-3, (d, a[0], b[0], x)
for a, b in itertools.combinations(R, 2):
    if a[1] == b[1]: assert a[7] <= b[6] or b[7] <= a[6], (a[0], b[0])
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in geo.items()]},
          open(os.path.join(ROOT, 'borders-asia-1-derived.geojson'), 'w'), separators=(',', ':'))
json.dump({k: {'area_deg2': round(v.area, 3), 'polygons': len(v.geoms), 'bounds': [round(b, 2) for b in v.bounds]} for k, v in geo.items()}, open(os.path.join(ROOT, 'qa.json'), 'w'), indent=1)
json.dump([{'ph': r[0], 'regime': r[1], 'geom': r[2], 'start': r[6], 'end': r[7]} for r in R], open(os.path.join(HERE, 'records.json'), 'w'), indent=0)
for i, r in enumerate(R, 1): rec(i, *r)

CF = [('JP', 'CN', 'EV_MARCO_POLO', (116.2134, 39.8494), '開戰地點：盧溝橋（兩國當時不直接相鄰：中間隔滿洲國、關東州）'),
      ('JP', 'US', 'EV_PEARL_HARBOR', (-157.95, 21.36), '開戰地點：珍珠港（兩國不相鄰）'),
      ('JP', 'UK', 'EV_WAR_JP_UK', (102.24, 6.13), '開戰地點：哥打巴魯（馬來亞登陸，兩國不相鄰）'),
      ('SU', 'JP', 'EV_SU_JP_WAR', (142.6, 50.0), '樺太北緯 50 度的日蘇陸上邊界'),
      ('MN', 'JP', 'EV_MN_JP_WAR', (124.9078, 42.9605), '兩國不相鄰：烏蘭巴托與東京大圓連線的中點（滿洲）')]
for i, (a, b, s, pt, how) in enumerate(CF, 1):
    write(f'05-conflict-{i:02d}-{a.lower()}_{b.lower()}.json', f'CF_{a}_{b}', '/api/v1/conflict-records', {
        'regimeAId': '{{REGIME_%s}}' % a, 'regimeBId': '{{REGIME_%s}}' % b, 'startEventId': '{{%s}}' % s, 'endEventId': '{{EV_JP_SURRENDER}}',
        'location': {'type': 'Point', 'coordinates': list(pt)}, 'locationMethod': how,
        'note': {'zh-Hant': '交戰期間由起訖事件日期推得；結束取 1945-09-02 降伏文書簽字。', 'en': 'Period derived from the start event and the surrender of 2 Sep 1945.'}})
print('ok', len(R), 'records;', len(E), 'events;', len(REG), 'regimes;', len(CF), 'conflicts')
