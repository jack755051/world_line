#!/usr/bin/env python3
"""產生 1942 後期（1942-07-01～1942-12-31）義、匈、羅、保、克、塞、希、蒙、阿與 1942-11-11 後法國的 requests/*.json（DRAFT，待 Tai 檢查）。
- 幾何：固定版本 OHM（ohm-manifest.json；Overpass osm_base 2026-10-31T03:13:48Z），衍生規則見 build/derive.py。
- 引用只用已核對原文的 FRUS（history.state.gov pg_N 核頁）與 NCA（紙本頁碼）。找不到正式出處的事件不附引用 → 待查證，不補造。
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); OUT = os.path.join(ROOT, 'requests')
MAN = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))}
P_ALL = {'start': '1942-07-01', 'end': '1943-01-01'}; P_NOV = {'start': '1942-11-11', 'end': '1943-01-01'}
GPO = 'United States Department of State; United States Government Printing Office, Washington'

def write(name, ph, post, body, meta=None, geom=None):
    req = {'_placeholder': ph, '_post': post, **({'_geometryFrom': geom} if geom else {}), **({'_meta': meta} if meta else {}), 'body': body}
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')

SOURCES = [
    ('SRC_OHM_1942S', {'sourceKind': 'dataset',
        'title': 'OpenHistoricalMap — boundary=administrative, admin_level=2 關係（南歐、東南歐與法國，1942 後期試驗）',
        'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
        'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
        'publishedText': 'Overpass osm_base 2026-10-31T03:13:48Z；逐筆關係版本見 borders-1942-south/ohm-manifest.json',
        'note': 'OHM 整體以 CC0 1.0 釋出；部分成員線段帶 license=CC BY 4.0 標籤（逐筆在主權紀錄標示）。'}),
    ('SRC_FRUS_1941_II', {'sourceKind': 'official_record', 'title': 'Foreign Relations of the United States, Diplomatic Papers, 1941, Europe, Volume II',
        'publisher': GPO, 'licenseCode': 'us_federal_pd', 'licenseEvidenceUrl': 'https://www.state.gov/copyright-information',
        'url': 'https://history.state.gov/historicaldocuments/frus1941v02'}),
    ('SRC_FRUS_1942_II', {'sourceKind': 'official_record', 'title': 'Foreign Relations of the United States, Diplomatic Papers, 1942, Europe, Volume II',
        'publisher': GPO, 'licenseCode': 'us_federal_pd', 'licenseEvidenceUrl': 'https://www.state.gov/copyright-information',
        'url': 'https://history.state.gov/historicaldocuments/frus1942v02'}),
]
for i, (ph, body) in enumerate(SOURCES, 1):
    write(f'01-source-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sources', body, {'priorPlaceholder': False})

REGIMES = [
    ('REGIME_HR', 'independent-state-of-croatia', 'Nezavisna Država Hrvatska', 'hr', '克羅埃西亞獨立國', 'Independent State of Croatia', 'SRC_FRUS_1941_II Doc. 977, p. 979'),
    ('REGIME_RS_MILCMD', 'military-commander-serbia', 'Gebiet des Militärbefehlshabers in Serbien', 'de', '塞爾維亞軍事指揮官轄區（德國佔領）', 'Territory of the Military Commander in Serbia (German occupation)', 'OHM relation/2692357 name'),
    ('REGIME_ME_GOV', 'italian-governorate-montenegro', 'Governatorato del Montenegro', 'it', '蒙特內哥羅總督轄區（義大利佔領）', 'Governorate of Montenegro (Italian occupation)', 'OHM relation/2695479 name:en'),
    ('REGIME_GR_OCC', 'occupied-greece-hellenic-state', 'Ελληνική Πολιτεία', 'el', '軸心佔領下的希臘（希臘國）', 'Axis-occupied Greece (Hellenic State)', 'OHM relation/2920398; FRUS 1941 II Doc. 590（parts of Greece occupied by German troops）'),
    ('REGIME_TRANSNISTRIA', 'transnistria-governorate', 'Guvernământul Transnistriei', 'ro', '外涅斯特里亞（羅馬尼亞佔領）', 'Transnistria (Romanian occupation)', 'FRUS 1941 I Doc. 350（the territory between the Dniester and the Bug）；羅文名稱為通行稱呼，原文出處待查證'),
    ('REGIME_IT_OCC_FR', 'italian-occupation-zone-france', 'Zona di occupazione italiana in Francia', 'it', '義大利佔領的法國地區', 'Italian-occupied French territory', 'OHM relation/2747832 − 2747829'),
]
for i, (ph, slug, orig, lang, zh, en, src) in enumerate(REGIMES, 1):
    write(f'02-regime-{i:02d}-{slug}.json', ph, '/api/v1/regimes', {'slug': slug, 'names': [
        {'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]},
        {'priorPlaceholder': False, 'nameSource': src})

def tn(zh, en): return (zh, en)
OHMD = lambda d: tn(f'日期依 OHM 國界變動日 {d}；引用證明事件本身，未逐日載明 OHM 變動日。', f'Date from the OHM change date {d}; the citations attest the event, not that exact day.')
# (placeholder, kind, start, zh, en, participants, citations, timeNote)
EVENTS = [
    ('EV_ROME_AGREEMENTS', 'political', '1941-05-18', '羅馬協定：克羅埃西亞將南斯拉夫部分領土割予義大利；德、義瓜分並併入斯洛維尼亞（OHM 義大利國界變動日 1941-04-18）',
     'Rome agreements: parts of Yugoslav territory ceded to Italy; Slovenia partitioned and annexed by Germany and Italy (OHM change 18 Apr 1941)',
     [('REGIME_IT', 'signatory'), ('REGIME_HR', 'signatory')],
     [('SRC_FRUS_1941_II', 'Doc. 978, p. 980', '南斯拉夫公使 1941-05-24 照會：5 月 18 日在羅馬簽署協定，將南斯拉夫領土的完整部分割予義大利。'),
      ('SRC_FRUS_1941_II', 'Doc. 981, pp. 981–982', '國務卿 1941-09-25 覆照：德國與義大利瓜分並併入南斯拉夫的斯洛維尼亞各省。')], None),
    ('EV_HU_YU_1941', 'political', '1941-12-14', '匈牙利併入南斯拉夫北部領土（OHM 匈牙利國界變動日 1941-12-14）', 'Hungary annexes northern Yugoslav territories (OHM change 14 Dec 1941)',
     [('REGIME_HU', 'other')],
     [('SRC_FRUS_1942_III', 'Doc. 727, pp. 841–844', '南斯拉夫公使 1942-05-20 照會：德、義、匈瓜分南斯拉夫境內斯洛維尼亞各部並併入本國（只涵蓋斯洛維尼亞部分；巴奇卡、巴拉尼亞的併入日期仍待查）。')],
     tn('日期依 OHM；巴奇卡、巴拉尼亞併入的日期與文件尚未取得。', 'Date from OHM; the date/document for Bačka and Baranja is not yet sourced.')),
    ('EV_RO_REGAIN', 'political', '1941-08-19', '羅馬尼亞收回比薩拉比亞、北布科維納並設民政（OHM 羅馬尼亞國界變動日 1941-08-19）', 'Romania regains Bessarabia and northern Bukovina and sets up civil administration (OHM change 19 Aug 1941)',
     [('REGIME_RO', 'other')],
     [('SRC_NCA_III', 'Doc. 197-PS, p. 210', '1941-08-27 會議紀錄：比薩拉比亞與布科維納已由羅馬尼亞設立民政。'),
      ('SRC_FRUS_1941_I', 'Doc. 80, pp. 68–70', '國務卿 1941-09-17 談話紀錄：羅馬尼亞稱收回原羅馬尼亞領土、攻下敖德薩後即停止對蘇作戰。')], OHMD('1941-08-19')),
    ('EV_TRANSNISTRIA', 'political', '1941-08-19', '羅馬尼亞佔領德涅斯特河與布格河之間（外涅斯特里亞），不主張領土', 'Romanian occupation of the area between the Dniester and the Bug (Transnistria), no territorial claim',
     [('REGIME_RO', 'other')],
     [('SRC_FRUS_1941_I', 'Doc. 350, pp. 326–327', '1941-09-04 談話紀錄：羅馬尼亞稱越過收回領土後只作佔領軍，範圍限於德涅斯特河與布格河之間，未提出領土要求。')], OHMD('1941-08-19')),
    ('EV_BG_OCC', 'political', '1941-04-19', '保加利亞軍隊進入希臘色雷斯與希臘、南斯拉夫馬其頓（OHM 保加利亞國界變動日 1941-04-30）', 'Bulgarian troops move into Greek Thrace and Greek and Yugoslav Macedonia (OHM change 30 Apr 1941)',
     [('REGIME_BG', 'other')],
     [('SRC_FRUS_1941_II', 'Doc. 710, p. 720', '駐保加利亞公使 1941-04-19 電：官方公報將宣布保軍為治安與行政目的進入希臘色雷斯與希臘、南斯拉夫馬其頓。')], None),
    ('EV_NDH', 'political', '1941-04-10', '「克羅埃西亞獨立國」在佔領軍保護下宣布成立', 'The “Independent State of Croatia” proclaimed under the protection of the occupying army',
     [('REGIME_HR', 'other')],
     [('SRC_FRUS_1941_II', 'Doc. 977, p. 979', '南斯拉夫公使 1941-05-12 照會：帕韋利奇在佔領軍保護下宣布成立所謂「克羅埃西亞獨立國」。')],
     tn('日期依 OHM（1941-04-10）；出處未載明宣布日。', 'Date from OHM; the source does not state the day.')),
    ('EV_RS_OCC', 'political', '1941-04-22', '德國佔領塞爾維亞，設軍事指揮官轄區（內迪奇傀儡政府）', 'German occupation of Serbia under a military commander (Nedić puppet government)',
     [('REGIME_DE', 'other')],
     [('SRC_FRUS_1941_II', 'Doc. 590, pp. 630–631', '駐德代辦 1941-06-19 電：德方列出德軍佔領地區，含塞爾維亞與希臘的德佔部分。'),
      ('SRC_FRUS_1942_III', 'Doc. 703, pp. 810–813', '1942-09-09 電：貝爾格勒的內迪奇傀儡政府。')], OHMD('1941-04-22')),
    ('EV_GR_OCC', 'political', '1941-04-30', '軸心佔領希臘（OHM 變動日 1941-04-30）', 'Axis occupation of Greece (OHM change 30 Apr 1941)',
     [('REGIME_DE', 'other'), ('REGIME_IT', 'other'), ('REGIME_BG', 'other')],
     [('SRC_FRUS_1941_II', 'Doc. 590, pp. 630–631', '駐德代辦 1941-06-19 電：德方所列德軍佔領地區含「希臘的德佔部分」。')], OHMD('1941-04-30')),
    ('EV_ME_GOV', 'political', '1941-10-03', '義大利設蒙特內哥羅總督轄區（OHM 變動日 1941-10-03）', 'Italy establishes the Governorate of Montenegro (OHM change 3 Oct 1941)',
     [('REGIME_IT', 'other')], [], tn('尚未取得正式出處；日期依 OHM。', 'No formal source yet; date from OHM.')),
    ('EV_AL_1941', 'political', '1941-06-07', '科索沃等南斯拉夫領土併入義屬阿爾巴尼亞（OHM 變動日 1941-06-07）', 'Kosovo and other Yugoslav areas joined to Italian-ruled Albania (OHM change 7 Jun 1941)',
     [('REGIME_AL_IT', 'other')], [], tn('尚未取得正式出處；日期依 OHM。', 'No formal source yet; date from OHM.')),
    ('EV_ANTON', 'war', '1942-11-11', '德國全面佔領法國本土（原非佔領區）；美國不再承認在此運作的政權為主權獨立政府', 'Germany occupies all of metropolitan France (formerly unoccupied zone); the US no longer regards any regime there as sovereign',
     [('REGIME_DE', 'other'), ('REGIME_FR_STATE', 'other')],
     [('SRC_FRUS_1942_II', 'Doc. 207, pp. 203–204', '國務卿 1942-11-19 致各使館：鑑於德國全面佔領法國本土，不能視希特勒容許在該地運作的任何政權為主權獨立政府。'),
      ('SRC_FRUS_1942_II', 'Doc. 206, p. 203', '國務卿 1942-11-18 談話紀錄：德國佔領原非佔領區後，視維琪政府為已消滅。'),
      ('SRC_FRUS_1942_II', 'Doc. 641, p. 647', '國務卿 1942-11-12 電：德國即將全面佔領法國。')], OHMD('1942-11-11')),
    ('EV_IT_OCC_FR', 'war', '1942-11-11', '義大利佔領科西嘉與法國東南部（OHM 義大利國界變動日 1942-11-11）', 'Italy occupies Corsica and south-eastern France (OHM change 11 Nov 1942)',
     [('REGIME_IT', 'other'), ('REGIME_FR_STATE', 'other')], [], tn('尚未取得正式出處；日期依 OHM。', 'No formal source yet; date from OHM.')),
]
for i, (ph, kind, s, zh, en, parts, cites, t) in enumerate(EVENTS, 1):
    import datetime
    e = (datetime.date.fromisoformat(s) + datetime.timedelta(days=1)).isoformat()
    body = {'eventKind': kind, 'occurred': {'start': s, 'end': e}, 'datePrecision': 'day', 'summary': {'zh-Hant': zh, 'en': en},
            'participants': [{'regimeId': '{{%s}}' % r, 'role': role} for r, role in parts],
            'citations': [{'sourceId': '{{%s}}' % src, 'locator': loc, 'evidenceNote': note} for src, loc, note in cites]}
    if t: body['timeNote'] = {'zh-Hant': t[0], 'en': t[1]}
    write(f'03-event-{i:02d}-{ph.lower()}.json', ph, '/api/v1/events', body, {'verification': 'verified' if cites else 'pending（待查證）'})

def lic(rels):
    rs = [MAN[r] for r in rels]
    attr = sorted({a for r in rs if r['attribution'] for a in r['attribution'].split('; ')})
    return ('cc_by' if any(r['geometry_license'] == 'cc_by' for r in rs) else 'cc0'), ('; '.join(attr) or None)
L = lambda *rs: ' − '.join(f'relation/{r} v{MAN[r]["ohm_version"]}' for r in rs)
# (placeholder, regime, fix, main rel, rels, locator, layer, period, start event, note zh, note en)
RECORDS = [
    ('SOVS_IT', 'REGIME_IT', 'FIXS_IT', 2747829, [2747829], L(2747829), 'de_jure', P_ALL, 'EV_ROME_AGREEMENTS',
     '1942 後期義大利事實國界（含併入的盧布爾雅那、達爾馬提亞等）。1942-11-11 起 OHM 另含義軍佔領的法國地區，本批另畫為非主權。', 'Italy, late 1942 (de facto, OHM). Italian-occupied French territory from 11 Nov 1942 is drawn separately as not sovereign.'),
    ('SOVS_IT_OCC_FR', 'REGIME_IT_OCC_FR', 'FIXS_IT_OCC_FR', 2747832, [2747832, 2747829], L(2747832, 2747829), 'not_sovereign', P_NOV, 'EV_IT_OCC_FR',
     '非主權：義大利佔領的法國地區（科西嘉與東南部），依 OHM 1942-11-11 起的義大利國界扣除先前國界。', 'Not sovereign: Italian-occupied French territory (OHM Italy after 11 Nov 1942 minus before).'),
    ('SOVS_FR', 'REGIME_FR_STATE', 'FIXS_FR', 2747869, [2747869], L(2747869), 'not_sovereign', P_NOV, 'EV_ANTON',
     '非主權：1942-11-11 起德國全面佔領法國本土，維琪政權不再視為主權獨立政府（FRUS 1942 II Doc. 207）。OHM 沒有德國佔領區的分區幾何，整區畫為一個佔領下的區域。',
     'Not sovereign from 11 Nov 1942 (FRUS 1942 II Doc. 207). OHM has no separate German occupation-zone geometry.'),
    ('SOVS_HU', 'REGIME_HU', 'FIXS_HU', 2692359, [2692359], L(2692359), 'de_jure', P_ALL, 'EV_HU_YU_1941', '1942 後期匈牙利事實國界（OHM）。', 'Hungary, late 1942 (de facto, OHM).'),
    ('SOVS_RO', 'REGIME_RO', 'FIXS_RO', 2693255, [2693255, 2693259], L(2693255) + ' − 外涅斯特里亞', 'de_jure', P_ALL, 'EV_RO_REGAIN',
     '1942 後期羅馬尼亞事實國界（含收回的比薩拉比亞、北布科維納）；外涅斯特里亞另畫為非主權。', 'Romania, late 1942, incl. Bessarabia and northern Bukovina; Transnistria drawn separately as not sovereign.'),
    ('SOVS_TRANSNISTRIA', 'REGIME_TRANSNISTRIA', 'FIXS_TRANSNISTRIA', 2693255, [2693255, 2693259], f'{L(2693255)} − {L(2693259)}（德涅斯特河以東）', 'not_sovereign', P_ALL, 'EV_TRANSNISTRIA',
     '非主權：羅馬尼亞佔領的德涅斯特河—布格河之間（外涅斯特里亞），羅方未提出領土要求（FRUS 1941 I Doc. 350）。', 'Not sovereign: Romanian-occupied Transnistria (FRUS 1941 I Doc. 350).'),
    ('SOVS_BG', 'REGIME_BG', 'FIXS_BG', 2695478, [2695478], L(2695478), 'de_jure', P_ALL, 'EV_BG_OCC', '1942 後期保加利亞事實國界（OHM，含佔領併入的色雷斯、馬其頓）。', 'Bulgaria, late 1942 (de facto, OHM).'),
    ('SOVS_GR', 'REGIME_GR_OCC', 'FIXS_GR', 2920398, [2920398, 2695478], L(2920398, 2695478), 'not_sovereign', P_ALL, 'EV_GR_OCC',
     '非主權：軸心（德、義、保）佔領下的希臘；保加利亞佔領併入的部分已扣除。OHM 沒有德、義佔領區的分區幾何。', 'Not sovereign: Axis-occupied Greece; OHM has no zone-level geometry.'),
    ('SOVS_HR', 'REGIME_HR', 'FIXS_HR', 2692713, [2692713], L(2692713), 'de_jure', P_ALL, 'EV_NDH', '1942 後期克羅埃西亞獨立國（OHM；軸心扶植）。', 'Independent State of Croatia, late 1942 (OHM; Axis-sponsored).'),
    ('SOVS_RS', 'REGIME_RS_MILCMD', 'FIXS_RS', 2692357, [2692357], L(2692357), 'not_sovereign', P_ALL, 'EV_RS_OCC', '非主權：德國佔領下的塞爾維亞（軍事指揮官轄區）。', 'Not sovereign: German-occupied Serbia.'),
    ('SOVS_ME', 'REGIME_ME_GOV', 'FIXS_ME', 2695479, [2695479], L(2695479), 'not_sovereign', P_ALL, 'EV_ME_GOV', '非主權：義大利佔領下的蒙特內哥羅總督轄區。', 'Not sovereign: Italian Governorate of Montenegro.'),
    ('SOVS_AL', 'REGIME_AL_IT', 'FIXS_AL', 2695459, [2695459], L(2695459), 'de_jure', P_ALL, 'EV_AL_1941', '1942 後期義屬阿爾巴尼亞（OHM，含科索沃等），沿用 1939–1941 紀錄的處理。', 'Italian-ruled Albania, late 1942 (OHM), as in the 1939–1941 record.'),
]
# 修正：FIXS_FR 含阿爾及利亞北部（OHM 2747869），1942-11-08 起盟軍登陸北非，不該畫成德國佔領。撤回後改送只含法國本土的 FIXS_FR_EU。
write('05-retract-01-sovs_fr.json', 'RETRACTED_SOVS_FR', '/api/v1/sovereignty-records/{{SOVS_FR}}/retraction',
      {'reason': '法國 1942-11-11 起的非主權紀錄誤含阿爾及利亞北部（OHM 2747869 仍含）；1942-11-08 起盟軍登陸北非，改為只含法國本土（北緯 40 度以北），阿爾及利亞留白待查證'}, {'fix': True})
FR = RECORDS[2]
RECORDS_FIX = [('SOVS_FR_EU', FR[1], 'FIXS_FR_EU', FR[3], FR[4], FR[5] + ' ∩ 北緯 40 度以北（法國本土）', FR[6], FR[7], FR[8],
    FR[9] + '只含法國本土；阿爾及利亞北部 1942-11-08 起盟軍登陸，1942-11-11 起留白（待查證）。', FR[10] + ' Metropolitan France only; northern Algeria is left blank from 11 Nov 1942 (Allied landings from 8 Nov; pending).')]
for prefix, recs in (('04-sovereignty', RECORDS), ('06-sovereignty', RECORDS_FIX)):
  for i, (ph, reg, fix, rel, rels, loc, layer, period, ev, nzh, nen) in enumerate(recs, 1):
      m = MAN[rel]; gl, attr = lic(rels)
      body = {'regimeId': '{{%s}}' % reg, 'geometry': None, 'validPeriod': period, 'layerStatus': layer, 'geometrySourceId': '{{SRC_OHM_1942S}}',
              'geometryLocator': loc, 'geometryLicense': gl, 'attribution': attr, 'startEventId': '{{%s}}' % ev, 'endEventId': None,
              'ohmRelationId': rel, 'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'], 'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date'],
              'provenance': {'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': sum(MAN[r]['osm_derived_way_count'] for r in rels),
                             'ohmFixme': m['fixme'], 'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'], 'ohmTimestamp': m['ohm_timestamp'],
                             'coastline': '{{SRC_NE_LAND}}', 'derivedFrom': [f'relation/{r} v{MAN[r]["ohm_version"]}' for r in rels], 'derivation': loc,
                             'trialWindow': '1942-07-01～1942-12-31（期間外不追溯）', **({'licenseReview': 'osm_derived_ways'} if any(MAN[r]['osm_derived_way_count'] for r in rels) else {})},
              'note': {'zh-Hant': nzh, 'en': nen}}
      write(f'{prefix}-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sovereignty-records', body, {'ohmName': m['name'], **({'fix': True} if prefix.startswith('06') else {})}, geom=fix)
print('ok', len(SOURCES), 'sources', len(REGIMES), 'regimes', len(EVENTS), 'events', len(RECORDS), 'records')
