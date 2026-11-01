#!/usr/bin/env python3
"""美國（本土與屬地）與菲律賓自治邦國界、美國對德義羅保匈的交戰（DRAFT，待 Tai 檢查）。只寫開發庫（5052）。
幾何：固定版本 OHM（ohm-manifest.json；Overpass osm_base 2026-10-31T10:59:07Z），世界框（北緯 75 度以南）＋ Natural Earth 10m 陸地裁切。
OHM「United States」relation/2874803（1935-03-26～1946-07-03）已含阿拉斯加、夏威夷、波多黎各、關島、美屬薩摩亞、維京群島、巴拿馬運河區與菲律賓；
菲律賓另畫為菲律賓自治邦（relation/2889834），日軍佔領的關島、威克島、阿圖島、基斯卡島依分段扣除（佔領方紀錄留待亞洲批次）。
試驗期間 1937-07-07～1945-09-02；沒有正式出處的分段日標待查證，不補造。
"""
import json, os, datetime
from shapely.geometry import shape, mapping, MultiPolygon, Polygon, box
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); OUT = os.path.join(ROOT, 'requests')
MAN = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))}
g = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-us.geojson')))['features']}
def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x, 'geoms', []) for p in polys(y)]
def clean(x):
    x = make_valid(set_precision(make_valid(x), 1e-4))
    return MultiPolygon([p for p in polys(x) if p.area > 1e-5])
US, PH, GUAM = 2874803, 2889834, 2854023
WAKE = clean(g[US].intersection(box(166.4, 19.1, 166.8, 19.5)))
ATTU = clean(g[US].intersection(box(172.3, 52.6, 173.4, 53.1)))
KISKA = clean(g[US].intersection(box(177.2, 51.8, 177.75, 52.2)))
def usm(*xs): return clean(g[US].difference(unary_union([g[PH]] + [g[x] if isinstance(x, int) else x for x in xs])))
geo = {'U_A': usm(), 'U_B': usm(GUAM), 'U_C': usm(GUAM, WAKE), 'U_D': usm(GUAM, WAKE, ATTU, KISKA), 'U_E': usm(GUAM, WAKE, KISKA),
       'U_F': usm(GUAM, WAKE), 'U_G': usm(WAKE), 'PH_A': clean(g[PH])}
for k in ['U_B', 'U_C', 'U_D', 'U_E', 'U_F', 'U_G']: assert geo[k].area < geo['U_A'].area
assert geo['U_A'].intersection(geo['PH_A']).area < 1e-6
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in geo.items()]},
          open(os.path.join(ROOT, 'borders-us-derived.geojson'), 'w'), separators=(',', ':'))
json.dump({k: {'area_deg2': round(v.area, 3), 'polygons': len(v.geoms), 'bounds': [round(b, 2) for b in v.bounds]} for k, v in geo.items()}, open(os.path.join(ROOT, 'qa.json'), 'w'), indent=1)

def write(name, ph, post, body, meta=None, geom=None):
    req = {'_placeholder': ph, '_post': post, **({'_geometryFrom': geom} if geom else {}), **({'_meta': meta} if meta else {}), 'body': body}
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')

write('01-source-01-src_ohm_us.json', 'SRC_OHM_US', '/api/v1/sources', {'sourceKind': 'dataset',
    'title': 'OpenHistoricalMap — boundary=administrative 關係（美國與屬地、菲律賓自治邦，1937～1945）',
    'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
    'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
    'publishedText': 'Overpass osm_base 2026-10-31T10:59:07Z；逐筆見 borders-us/ohm-manifest.json',
    'note': 'OHM 整體以 CC0 1.0 釋出；本批成員線段皆未帶 CC BY 標籤。'}, {'priorPlaceholder': False})

write('02-regime-01-united-states.json', 'REGIME_US', '/api/v1/regimes', {'slug': 'united-states-of-america', 'names': [
    {'nameKind': 'self', 'originalText': 'United States of America', 'originalLang': 'en', 'display': {'zh-Hant': '美利堅合眾國', 'en': 'United States of America'}, 'isPrimary': True}]},
    {'priorPlaceholder': False, 'nameSource': 'FRUS 1941 I Doc. 587（the Government and the people of the United States of America）'})
write('02-regime-02-commonwealth-of-the-philippines.json', 'REGIME_PH_CW', '/api/v1/regimes', {'slug': 'commonwealth-of-the-philippines', 'names': [
    {'nameKind': 'self', 'originalText': 'Commonwealth of the Philippines', 'originalLang': 'en', 'display': {'zh-Hant': '菲律賓自治邦（美國屬地）', 'en': 'Commonwealth of the Philippines (US)'}, 'isPrimary': True}]},
    {'priorPlaceholder': False, 'nameSource': 'OHM relation/2889834 name'})

def ev(i, ph, kind, start, zh, en, parts, cites, tn=None):
    e = (datetime.date.fromisoformat(start) + datetime.timedelta(days=1)).isoformat()
    body = {'eventKind': kind, 'occurred': {'start': start, 'end': e}, 'datePrecision': 'day', 'summary': {'zh-Hant': zh, 'en': en},
            'participants': [{'regimeId': '{{%s}}' % r, 'role': role} for r, role in parts],
            'citations': [{'sourceId': '{{%s}}' % s, 'locator': l, 'evidenceNote': n} for s, l, n in cites]}
    if tn: body['timeNote'] = {'zh-Hant': tn[0], 'en': tn[1]}
    write(f'03-event-{i:02d}-{ph.lower()}.json', ph, '/api/v1/events', body, {'verification': 'verified' if cites and not (tn and '待查證' in tn[0]) else 'pending（待查證）'})
JP = ('日本政權尚未建立（亞洲批次補上參與方與佔領紀錄）。', 'Japan is not yet in the regime table (Asia batch).')
NOSRC = lambda what: ('尚未取得正式出處（待查證）；日期為通行說法。' + what, 'No formal source yet (pending); commonly cited date. ' + what)
E = [
 ('EV_WAR_DE_US', 'war', '1941-12-11', '德國對美國宣戰；美國國會同日決議與德國處於戰爭狀態', 'Germany declares war on the United States; Congress resolves that a state of war exists',
  [('REGIME_DE', 'belligerent'), ('REGIME_US', 'belligerent')],
  [('SRC_FRUS_1941_I', 'Doc. 586, p. 590', '羅斯福 1941-12-11 致國會：當日上午德國政府對美國宣戰，義大利亦然。'),
   ('SRC_FRUS_1941_I', 'Doc. 587, pp. 590–591', '1941-12-11 兩院聯合決議：美國與德國政府之間的戰爭狀態（下午 3:05 批准）。')]),
 ('EV_WAR_IT_US', 'war', '1941-12-11', '義大利對美國宣戰；美國國會同日決議與義大利處於戰爭狀態', 'Italy declares war on the United States; Congress resolves that a state of war exists',
  [('REGIME_IT', 'belligerent'), ('REGIME_US', 'belligerent')],
  [('SRC_FRUS_1941_I', 'Doc. 585, pp. 589–590', '駐義代辦 1941-12-11 電：齊亞諾正式告知「義大利自今日起認為與美國處於戰爭狀態」。'),
   ('SRC_FRUS_1941_I', 'Doc. 587, pp. 590–591', '同一聯合決議對義大利者 1941-12-11 下午 3:06 批准。')]),
 ('EV_WAR_RO_US', 'war', '1941-12-12', '羅馬尼亞宣布與美國處於戰爭狀態（美國 1942-06-05 宣戰）', 'Romania declares itself at war with the United States (US declaration 5 Jun 1942)',
  [('REGIME_RO', 'belligerent'), ('REGIME_US', 'belligerent')],
  [('SRC_FRUS_1941_I', 'Doc. 589, p. 591', '駐羅代辦 1941-12-12 電：羅外交部遞交照會，依三國同盟條約，羅馬尼亞與美國處於戰爭狀態。'),
   ('SRC_FRUS_1941_I', 'Doc. 587, pp. 590–591（註）', '美國對保加利亞、匈牙利、羅馬尼亞的宣戰決議 1942-06-05 批准。')]),
 ('EV_WAR_BG_US', 'war', '1941-12-13', '保加利亞宣布與美國處於戰爭狀態（美國 1942-06-05 宣戰）', 'Bulgaria declares itself at war with the United States (US declaration 5 Jun 1942)',
  [('REGIME_BG', 'belligerent'), ('REGIME_US', 'belligerent')],
  [('SRC_FRUS_1941_I', 'Doc. 590, p. 592', '保加利亞外交部致美國公使館照會（1941-12-13 下午面交）：德、義宣布與美國處於戰爭狀態後，保加利亞政府……'),
   ('SRC_FRUS_1941_I', 'Doc. 587, pp. 590–591（註）', '美國對保加利亞的宣戰決議 1942-06-05 批准。')]),
 ('EV_WAR_HU_US', 'war', '1941-12-13', '匈牙利宣布與美國處於戰爭狀態（美國 1942-06-05 宣戰）', 'Hungary declares war to exist with the United States (US declaration 5 Jun 1942)',
  [('REGIME_HU', 'belligerent'), ('REGIME_US', 'belligerent')],
  [('SRC_FRUS_1941_I', 'Doc. 591, p. 592', '駐匈公使 1941-12-13 電：匈總理告知，匈牙利認為與美國之間存在戰爭狀態。'),
   ('SRC_FRUS_1941_I', 'Doc. 587, pp. 590–591（註）', '美國對匈牙利的宣戰決議 1942-06-05 批准。')]),
 ('EV_RO_ARMISTICE', 'armistice', '1944-09-12', '羅馬尼亞與盟國在莫斯科簽訂停戰協定（9 月 13 日凌晨簽字，日期記 9 月 12 日）', 'Romanian armistice signed in Moscow (signed early 13 Sep, dated 12 Sep 1944)',
  [('REGIME_RO', 'signatory'), ('REGIME_SU', 'signatory'), ('REGIME_US', 'other'), ('REGIME_UK', 'other')],
  [('SRC_FRUS_1944_IV', 'Doc. 245, pp. 231–232（編者註）', '對羅馬尼亞停戰協定 9 月 13 日上午 5 時在莫斯科簽字，日期記為 9 月 12 日。'),
   ('SRC_FRUS_1944_IV', 'Doc. 297, pp. 283–286', '1944-12-18 電：停戰協定議定書由哈里曼、卡爾—克爾與維辛斯基簽署。')],
  ('蘇聯元帥代表盟國簽字；美、英參與談判並簽議定書，角色記為 other。', 'Signed by the Soviet commander on behalf of the Allies; US and UK recorded as other.')),
 ('EV_BG_ARMISTICE', 'armistice', '1944-10-28', '保加利亞與盟國在莫斯科簽訂停戰協定', 'Bulgarian armistice signed in Moscow',
  [('REGIME_BG', 'signatory'), ('REGIME_SU', 'signatory'), ('REGIME_US', 'other'), ('REGIME_UK', 'other')],
  [('SRC_FRUS_1944_III', 'Doc. 416, pp. 480–481（編者註）', '對保加利亞停戰協定 10 月 28 日下午 3 時在莫斯科簽字，議定書同日晚間簽字。')]),
 ('EV_GUAM_FALL', 'war', '1941-12-10', '日軍佔領關島', 'Japanese forces occupy Guam', [('REGIME_US', 'belligerent')], [], NOSRC(JP[0])),
 ('EV_WAKE_FALL', 'war', '1941-12-23', '日軍佔領威克島', 'Japanese forces take Wake Island', [('REGIME_US', 'belligerent')], [], NOSRC(JP[0])),
 ('EV_ALEUTIANS_OCC', 'war', '1942-06-07', '日軍佔領阿留申群島的基斯卡島（6 月 6 日）與阿圖島（6 月 7 日）', 'Japanese forces occupy Kiska (6 Jun) and Attu (7 Jun) in the Aleutians', [('REGIME_US', 'belligerent')],
  [('SRC_FRUS_1942_III', 'Doc. 488, p. 597（註）', '1942-06-19 文件的編者註：日軍已在阿留申群島的基斯卡、阿圖島。')],
  ('日期待查證（FRUS 僅載 6 月 19 日前已在島上）；紀錄兩島同取 06-07，簡化。' + JP[0], 'Date pending (FRUS only shows occupation by 19 Jun); both islands taken as 7 Jun (simplified). ' + JP[1])),
 ('EV_ATTU', 'war', '1943-05-30', '美軍收復阿圖島', 'US forces retake Attu', [('REGIME_US', 'belligerent')], [], NOSRC(JP[0])),
 ('EV_KISKA', 'war', '1943-07-29', '日軍撤離基斯卡島（美加聯軍 8 月 15 日登陸）', 'Japanese forces evacuate Kiska (Allied landing on 15 Aug)', [('REGIME_US', 'belligerent')], [], NOSRC(JP[0])),
 ('EV_GUAM_LIB', 'war', '1944-08-10', '美軍收復關島（宣布有組織抵抗結束）', 'US forces retake Guam (organized resistance declared ended)', [('REGIME_US', 'belligerent')], [], NOSRC(JP[0])),
 ('EV_PH_MANILA', 'war', '1942-01-02', '日軍進入馬尼拉（菲律賓行政委員會隨後成立）', 'Japanese forces enter Manila (Philippine Executive Commission formed soon after)', [('REGIME_PH_CW', 'belligerent'), ('REGIME_US', 'belligerent')], [],
  ('尚未取得正式出處（待查證）；自治邦紀錄止於 OHM 菲律賓行政委員會起始日 1942-01-03。' + JP[0], 'No formal source yet; the Commonwealth record ends on the OHM start of the Executive Commission (3 Jan 1942). ' + JP[1])),
]
for i, e in enumerate(E, 1): ev(i, *e)

L = lambda *rs: ' − '.join(f'relation/{r} v{MAN[r]["ohm_version"]}' for r in rs)
def rec(i, ph, regime, fix, main, rels, locator, start, end, sev, eev, nzh, nen):
    m = MAN[main]
    body = {'regimeId': '{{%s}}' % regime, 'geometry': None, 'validPeriod': {'start': start, 'end': end}, 'layerStatus': 'de_jure',
            'geometrySourceId': '{{SRC_OHM_US}}', 'geometryLocator': locator, 'geometryLicense': 'cc0', 'attribution': None,
            'startEventId': ('{{%s}}' % sev) if sev else None, 'endEventId': ('{{%s}}' % eev) if eev else None,
            'ohmRelationId': main, 'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'], 'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date'],
            'provenance': {'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': sum(MAN[r]['osm_derived_way_count'] for r in rels),
                           'ohmFixme': m['fixme'], 'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'], 'ohmTimestamp': m['ohm_timestamp'],
                           'coastline': '{{SRC_NE_LAND}}', 'derivedFrom': [f'relation/{r} v{MAN[r]["ohm_version"]}' for r in rels], 'derivation': locator,
                           'trialWindow': '1937-07-07～1945-09-02（美國）'},
            'note': {'zh-Hant': nzh, 'en': nen}}
    write(f'04-sovereignty-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sovereignty-records', body, {'ohmName': m['name']}, geom=fix)
USN = '美國本土與屬地（OHM relation/2874803：含阿拉斯加、夏威夷兩個建制領地，波多黎各、關島、美屬薩摩亞、維京群島，及美國管轄的巴拿馬運河區），菲律賓自治邦另畫。'
USE = 'United States incl. Alaska, Hawaii, Puerto Rico, Guam, American Samoa, the Virgin Islands and the Panama Canal Zone (OHM); the Philippine Commonwealth drawn separately.'
BASE = L(US, PH)
R = [
 ('SOVU_A', 'REGIME_US', 'U_A', US, [US, PH], BASE, '1937-07-07', '1941-12-10', None, 'EV_GUAM_FALL', USN + '起點為試驗期間起點 1937-07-07（不追溯）。', USE),
 ('SOVU_B', 'REGIME_US', 'U_B', US, [US, PH, GUAM], BASE + ' − 關島', '1941-12-10', '1941-12-23', 'EV_GUAM_FALL', 'EV_WAKE_FALL', USN + '關島 1941-12-10 起由日軍佔領，扣除（日期待查證）。', USE + ' Guam excluded (Japanese occupation).'),
 ('SOVU_C', 'REGIME_US', 'U_C', US, [US, PH, GUAM], BASE + ' − 關島 − 威克島', '1941-12-23', '1942-06-07', 'EV_WAKE_FALL', 'EV_ALEUTIANS_OCC', USN + '關島、威克島日軍佔領中，扣除。', USE + ' Guam and Wake excluded.'),
 ('SOVU_D', 'REGIME_US', 'U_D', US, [US, PH, GUAM], BASE + ' − 關島 − 威克島 − 阿圖島 − 基斯卡島', '1942-06-07', '1943-05-30', 'EV_ALEUTIANS_OCC', 'EV_ATTU', USN + '關島、威克島與阿留申的阿圖、基斯卡島日軍佔領中，扣除。', USE + ' Guam, Wake, Attu and Kiska excluded.'),
 ('SOVU_E', 'REGIME_US', 'U_E', US, [US, PH, GUAM], BASE + ' − 關島 − 威克島 − 基斯卡島', '1943-05-30', '1943-07-29', 'EV_ATTU', 'EV_KISKA', USN + '阿圖島 1943-05-30 收復；關島、威克島、基斯卡島仍扣除。', USE + ' Attu retaken; Guam, Wake and Kiska excluded.'),
 ('SOVU_F', 'REGIME_US', 'U_F', US, [US, PH, GUAM], BASE + ' − 關島 − 威克島', '1943-07-29', '1944-08-10', 'EV_KISKA', 'EV_GUAM_LIB', USN + '基斯卡島日軍 1943-07-29 撤離（盟軍 08-15 登陸，簡化取撤離次日）；關島、威克島仍扣除。', USE + ' Kiska evacuated; Guam and Wake excluded.'),
 ('SOVU_G', 'REGIME_US', 'U_G', US, [US, PH], BASE + ' − 威克島', '1944-08-10', '1945-09-02', 'EV_GUAM_LIB', None, USN + '關島 1944-08-10 收復；威克島日軍到 1945-09-04 才投降，至試驗期間終點仍扣除。', USE + ' Guam retaken; Wake excluded until the end of the trial window.'),
 ('SOVU_PH', 'REGIME_PH_CW', 'PH_A', PH, [PH], L(PH), '1937-07-07', '1942-01-03', None, 'EV_PH_MANILA',
  '菲律賓自治邦（1935-11-15 起，美國主權下的自治政府；OHM relation/2889834）。日軍 1941-12-08 起登陸，1942-01-02 進入馬尼拉；OHM 自治邦結束日為 1942-02-20、菲律賓行政委員會 1942-01-03 起，兩者重疊，本表自治邦先止於 01-03，之後的日軍佔領與未佔領地區留待亞洲批次（待查證）。',
  'Commonwealth of the Philippines (under US sovereignty) until 3 Jan 1942; the Japanese occupation is left to the Asia batch.'),
]
for i, r in enumerate(R, 1): rec(i, *r)

CF = [('DE', 'EV_WAR_DE_US', 'EV_DE_SURRENDER', (-38.8493, 55.3024), '柏林'), ('IT', 'EV_WAR_IT_US', 'EV_IT_ARMISTICE', (-33.5385, 50.1575), '羅馬'),
      ('RO', 'EV_WAR_RO_US', 'EV_RO_ARMISTICE', (-28.5666, 55.0242), '布加勒斯特'), ('BG', 'EV_WAR_BG_US', 'EV_BG_ARMISTICE', (-28.8241, 53.41), '索非亞'),
      ('HU', 'EV_WAR_HU_US', 'EV_HU_ARMISTICE', (-33.4878, 54.463), '布達佩斯')]
for i, (r, s, e, pt, cap) in enumerate(CF, 1):
    write(f'05-conflict-{i:02d}-{r.lower()}_us.json', f'CF_{r}_US', '/api/v1/conflict-records', {
        'regimeAId': '{{REGIME_%s}}' % r, 'regimeBId': '{{REGIME_US}}', 'startEventId': '{{%s}}' % s, 'endEventId': '{{%s}}' % e,
        'location': {'type': 'Point', 'coordinates': list(pt)},
        'locationMethod': f'兩國沒有共同邊界：圖示放在華盛頓與{cap}兩首都大圓連線的中點（大西洋上）。',
        'note': {'zh-Hant': '交戰期間由起訖事件日期推得。', 'en': 'Period derived from the start and end events.'}})
print('ok', len(R), 'records;', len(E), 'events;', len(CF), 'conflicts')
