#!/usr/bin/env python3
"""產生 1942 後期（1942-07-01～1942-12-31）德國、蘇聯主權國界與東方佔領行政區的 requests/*.json（DRAFT，待 Tai 檢查）。

- 幾何：固定版本 OHM（ohm-manifest.json；Overpass osm_base 2026-10-31T02:32:24Z），衍生規則見 build/derive.py。
- 紀錄期間一律 [1942-07-01, 1943-01-01)（本批只補 1942 後期；之前之後不追溯）。
- 引用只用已核對原文的 FRUS（history.state.gov pg_N 核頁）與 Nazi Conspiracy and Aggression（美國政府印刷局 1946，紙本頁碼）。
- 找不到正式出處的事件不附引用 → API 回 pending（「待查證」），不補造。
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); OUT = os.path.join(ROOT, 'requests')
MAN = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))}
PERIOD = {'start': '1942-07-01', 'end': '1943-01-01'}

def write(name, ph, post, body, meta=None, geom=None):
    req = {'_placeholder': ph, '_post': post, **({'_geometryFrom': geom} if geom else {}), **({'_meta': meta} if meta else {}), 'body': body}
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')

GPO = 'United States Department of State; United States Government Printing Office, Washington'
SOURCES = [
    ('SRC_OHM_1942', {'sourceKind': 'dataset',
        'title': 'OpenHistoricalMap — boundary=administrative, admin_level=2／3 關係（德國、蘇聯與東方佔領行政區，1942 後期試驗）',
        'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
        'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
        'publishedText': 'Overpass osm_base 2026-10-31T02:32:24Z；逐筆關係版本見 borders-1942-late/ohm-manifest.json',
        'note': 'OHM 整體以 CC0 1.0 釋出；部分成員線段帶 license=CC BY 4.0 標籤（逐筆在主權紀錄的 geometryLicense／attribution 標示）。本批 8 筆關係都沒有 OSM 匯入線段。'}),
    ('SRC_FRUS_1941_I', {'sourceKind': 'official_record',
        'title': 'Foreign Relations of the United States, Diplomatic Papers, 1941, General, The Soviet Union, Volume I',
        'publisher': GPO, 'licenseCode': 'us_federal_pd', 'licenseEvidenceUrl': 'https://www.state.gov/copyright-information',
        'url': 'https://history.state.gov/historicaldocuments/frus1941v01'}),
    ('SRC_FRUS_1942_III', {'sourceKind': 'official_record',
        'title': 'Foreign Relations of the United States, Diplomatic Papers, 1942, Europe, Volume III',
        'publisher': GPO, 'licenseCode': 'us_federal_pd', 'licenseEvidenceUrl': 'https://www.state.gov/copyright-information',
        'url': 'https://history.state.gov/historicaldocuments/frus1942v03'}),
    ('SRC_NCA_III', {'sourceKind': 'official_record',
        'title': 'Nazi Conspiracy and Aggression, Volume III（Office of United States Chief of Counsel for Prosecution of Axis Criminality）',
        'publisher': 'United States Government Printing Office, Washington', 'licenseCode': 'us_federal_pd',
        'licenseEvidenceUrl': 'https://www.loc.gov/item/2011525363_NT_Nazi_Vol-III/', 'url': 'https://www.loc.gov/item/2011525363_NT_Nazi_Vol-III/',
        'publishedText': '1946', 'note': '美國政府著作（17 U.S.C. §105）；頁碼依紙本（國會圖書館 Military Legal Resources 掃描）。'}),
    ('SRC_NCA_IV', {'sourceKind': 'official_record',
        'title': 'Nazi Conspiracy and Aggression, Volume IV（Office of United States Chief of Counsel for Prosecution of Axis Criminality）',
        'publisher': 'United States Government Printing Office, Washington', 'licenseCode': 'us_federal_pd',
        'licenseEvidenceUrl': 'https://www.loc.gov/item/2011525363_NT_Nazi_Vol-IV/', 'url': 'https://www.loc.gov/item/2011525363_NT_Nazi_Vol-IV/',
        'publishedText': '1946', 'note': '美國政府著作（17 U.S.C. §105）；頁碼依紙本（國會圖書館 Military Legal Resources 掃描）。'}),
]
for i, (ph, body) in enumerate(SOURCES, 1):
    write(f'01-source-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sources', body, {'priorPlaceholder': False})

REGIMES = [
    ('REGIME_RK_OSTLAND', 'reichskommissariat-ostland', 'Reichskommissariat Ostland', '東方總督轄區', 'Reichskommissariat Ostland',
     'SRC_FRUS_1942_III Doc. 350, pp. 406–407（the Reichskommissar for “Ostland”）'),
    ('REGIME_RK_UKRAINE', 'reichskommissariat-ukraine', 'Reichskommissariat Ukraine', '烏克蘭總督轄區', 'Reichskommissariat Ukraine',
     'SRC_NCA_III Doc. 197-PS, p. 210（Reich Commissariat Ukraine）'),
]
for i, (ph, slug, orig, zh, en, src) in enumerate(REGIMES, 1):
    write(f'02-regime-{i:02d}-{slug}.json', ph, '/api/v1/regimes', {'slug': slug, 'names': [
        {'nameKind': 'self', 'originalText': orig, 'originalLang': 'de', 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]},
        {'priorPlaceholder': False, 'nameSource': src})

# (placeholder, kind, start, end, zh, en, participants, citations[(src, locator, note)], timeNote)
EVENTS = [
    ('EV_BARBAROSSA', 'war', '1941-06-22', '1941-06-23', '德國進攻蘇聯（蘇聯西部隨後遭德國佔領）', 'Germany attacks the Soviet Union (western Soviet territory subsequently occupied)',
     [('REGIME_DE', 'belligerent'), ('REGIME_SU', 'belligerent')],
     [('SRC_FRUS_1941_I', 'Doc. 620, p. 625', '駐蘇大使 6/22 電：莫洛托夫廣播宣布德國於當日 4 時進攻蘇聯領土。'),
      ('SRC_FRUS_1941_I', 'Doc. 157, pp. 152–153', '駐德代辦 6/22 電：希特勒當日上午發布公告並致蘇聯政府照會。')], None),
    ('EV_OST_DECREE', 'political', '1941-07-17', '1941-07-18', '希特勒〈新佔東方領土行政命令〉：設東方佔領區部，民政區劃為總督轄區；東方總督轄區（總督 Lohse，駐里加）',
     'Hitler decree on the administration of the newly occupied Eastern territories: Reich Commissariats under the Reich Minister for the Occupied Eastern Territories; Reichskommissariat Ostland (Lohse, Riga)',
     [('REGIME_DE', 'other')],
     [('SRC_NCA_IV', 'Doc. 1997-PS, pp. 634–635', '1941-07-17 元首命令第 1、2、5、6 條：軍事行動結束的地區移交民政，歸東方佔領區部長，劃分為總督轄區（Reich Commissariats），各設總督。'),
      ('SRC_FRUS_1942_III', 'Doc. 350, pp. 406–407', '駐芬蘭公使 1942-01-09 電：東方總督為 Lohse，駐里加，下轄波羅的海三國總專員（考納斯、里加、塔林），上屬羅森堡。')],
     ('東方總督轄區各區移交民政的日期分批進行，本批未取得逐區日期；OHM 只記 1941 年。', 'Civil administration was introduced in stages; the per-district dates are not yet sourced (OHM records only “1941”).')),
    ('EV_RKU_CIVIL', 'political', '1941-09-01', '1941-09-02', '烏克蘭總督轄區移交民政（總督 Koch）', 'Reichskommissariat Ukraine transferred to civil administration (Reichskommissar Koch)',
     [('REGIME_DE', 'other')],
     [('SRC_NCA_III', 'Doc. 197-PS, p. 210', '1941-08-27 會議紀錄：說明 1941-09-01 起烏克蘭總督轄區的邊界與移交民政；比薩拉比亞、布科維納由羅馬尼亞設民政。')], None),
    ('EV_GALICIA_BIALYSTOK', 'political', '1941-08-01', '1941-08-02', '東加利西亞併入總督府（加利西亞區）、比亞韋斯托克區歸德國民政（OHM 德國國界變動日 1941-08-01）',
     'Eastern Galicia joined to the Generalgouvernement (District of Galicia) and Bezirk Bialystok under German civil administration (OHM border change 1941-08-01)',
     [('REGIME_DE', 'other')], [], ('尚未取得正式出處；日期依 OHM relation/2692712、2693084 的 start_date。', 'No formal source yet; date from OHM start_date.')),
]
for i, (ph, kind, s, e, zh, en, parts, cites, tn) in enumerate(EVENTS, 1):
    body = {'eventKind': kind, 'occurred': {'start': s, 'end': e}, 'datePrecision': 'day', 'summary': {'zh-Hant': zh, 'en': en},
            'participants': [{'regimeId': '{{%s}}' % r, 'role': role} for r, role in parts],
            'citations': [{'sourceId': '{{%s}}' % src, 'locator': loc, 'evidenceNote': note} for src, loc, note in cites]}
    if tn: body['timeNote'] = {'zh-Hant': tn[0], 'en': tn[1]}
    write(f'03-event-{i:02d}-{ph.lower()}.json', ph, '/api/v1/events', body, {'verification': 'verified' if cites else 'pending（待查證）'})

def lic(rels):
    rs = [MAN[r] for r in rels]
    attr = sorted({a for r in rs if r['attribution'] for a in r['attribution'].split('; ')})
    return ('cc_by' if any(r['geometry_license'] == 'cc_by' for r in rs) else 'cc0'), ('; '.join(attr) or None)

# (placeholder, regime, fix id, main relation, derived-from relations, locator, layer, start event, note)
RECORDS = [
    ('SOV1942_DE', 'REGIME_DE', 'FIX1942_DE', 2692712, [2692712], 'relation/2692712 v266', 'de_jure', 'EV_GALICIA_BIALYSTOK',
     ('1942 後期德意志國事實國界（OHM 原樣）：含總督府（含加利西亞區）、比亞韋斯托克區、波希米亞—摩拉維亞保護國（沿用 Tai 決定 1「事實國界」）。',
      'German Reich, late 1942, as drawn by OHM (includes the Generalgouvernement, Bezirk Bialystok and the Protectorate).')),
    ('SOV1942_RKO', 'REGIME_RK_OSTLAND', 'FIX1942_RKO', 2692529, [2692529, 2692712], 'relation/2692529 v46 − relation/2692712 v266', 'not_sovereign', 'EV_OST_DECREE',
     ('非主權：德國佔領行政區（東方總督轄區），法理上仍屬蘇聯所併的波羅的海三國與白俄羅斯西部。', 'Not sovereign: German occupation administration.')),
    ('SOV1942_RKU', 'REGIME_RK_UKRAINE', 'FIX1942_RKU', 2693267, [2693267, 2692712, 2692529], 'relation/2693267 v68 − relation/2692712 v266 − relation/2692529 v46', 'not_sovereign', 'EV_RKU_CIVIL',
     ('非主權：德國佔領行政區（烏克蘭總督轄區）。', 'Not sovereign: German occupation administration.')),
    ('SOV1942_SU', 'REGIME_SU', 'FIX1942_SU', 2851156, [2851156, 2692712, 2692529, 2693267, 2693255],
     'relation/2851156 v94 − relation/2692712 v266 − relation/2692529 v46 − relation/2693267 v68 − relation/2693255 v79', 'de_jure', 'EV_BARBAROSSA',
     ('1941 年蘇聯國界扣除德國事實併入區、兩個總督轄區與羅馬尼亞 1941-08-19 起的範圍（比薩拉比亞、北布科維納、外涅斯特里亞；羅馬尼亞不在本批，該處留白）。其餘德軍佔領而未設總督轄區的地區（軍政區）仍畫為蘇聯。',
      'Soviet 1941 border minus German de facto annexations, the two Reich Commissariats and the Romanian-held area from 19 Aug 1941 (Romania itself is not in this batch). Areas under German military rule outside the Reich Commissariats remain Soviet.')),
]
for i, (ph, reg, fix, rel, rels, loc, layer, ev, note) in enumerate(RECORDS, 1):
    m = MAN[rel]; gl, attr = lic(rels)
    body = {'regimeId': '{{%s}}' % reg, 'geometry': None, 'validPeriod': PERIOD, 'layerStatus': layer, 'geometrySourceId': '{{SRC_OHM_1942}}',
            'geometryLocator': loc, 'geometryLicense': gl, 'attribution': attr, 'startEventId': '{{%s}}' % ev, 'endEventId': None,
            'ohmRelationId': rel, 'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'], 'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date'],
            'provenance': {'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': sum(MAN[r]['osm_derived_way_count'] for r in rels),
                           'ohmFixme': m['fixme'], 'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'], 'ohmTimestamp': m['ohm_timestamp'],
                           'coastline': '{{SRC_NE_LAND}}', 'derivedFrom': [f'relation/{r} v{MAN[r]["ohm_version"]}' for r in rels], 'derivation': loc,
                           'trialWindow': '1942-07-01～1942-12-31（期間外不追溯）'},
            'note': {'zh-Hant': note[0], 'en': note[1]}}
    write(f'04-sovereignty-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sovereignty-records', body, {'ohmName': m['name']}, geom=fix)
print('ok', len(SOURCES), 'sources', len(REGIMES), 'regimes', len(EVENTS), 'events', len(RECORDS), 'records')
