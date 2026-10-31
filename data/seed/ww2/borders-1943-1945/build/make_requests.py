#!/usr/bin/env python3
"""補德國、蘇聯與兩者之間佔領區的空白時段，第二段：1943-01-01～1945-05-09（DRAFT，待 Tai 檢查）。
幾何：固定版本 OHM（ohm-manifest.json），依有出處的事件分段（沒有出處的分段日依 OHM，事件標待查證），同一天互不重疊。
- 德意志國＝2692712（含總督府、比亞韋斯托克區、保護國），1945-01-17 華沙收復起扣掉總督府，1945-05-08 投降止。
- 東方總督轄區＝2692529；1944-07-13 維爾紐斯收復起只剩愛沙尼亞（2693111）、拉脫維亞（2693110）兩個總區，
  1944-09-17 蘇軍攻入愛沙尼亞起只剩拉脫維亞，1944-10-13（OHM，待查證）止。
- 烏克蘭總督轄區＝2693267；1944-01-05 蘇軍越過戰前波蘭國界起只剩沃里尼亞—波多里亞（2693261）、尼古拉耶夫（2693264）兩個總區，
  1944-04-02 蘇軍越過普魯特河止。
- 蘇聯＝OHM 蘇聯（2851156；1944-09-19 起 2852346；1944-10-11 起 2957472）− 德國 − 當時的總督轄區 − 羅馬尼亞（2693255，至 1944-04-02）。
- 波蘭臨時政府（蘇軍控制下）＝總督府 2693084 − 蘇聯，1945-01-17 起，非主權。
"""
import json, os, datetime
from shapely.geometry import shape, mapping, MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); OUT = os.path.join(ROOT, 'requests')
MAN = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))}
g = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-1943-1945.geojson')))['features']}
def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x, 'geoms', []) for p in polys(y)]
def clean(x):
    x = make_valid(set_precision(make_valid(x), 1e-4))
    return MultiPolygon([p for p in polys(x) if p.area > 1e-5])
U = lambda *xs: unary_union([g[x] if isinstance(x, int) else x for x in xs])
DE, GG, RKO, EST, LV, RKU, WP, NIK, SU, SU44A, SU44B, RO = 2692712, 2693084, 2692529, 2693111, 2693110, 2693267, 2693261, 2693264, 2851156, 2852346, 2957472, 2693255
DE45 = clean(g[DE].difference(g[GG]))
geo = {
    'F45_DE_A': clean(g[DE]), 'F45_DE_B': DE45,
    'F45_PL': clean(g[GG].difference(g[SU44B])),
    'F45_RKO_A': clean(g[RKO].difference(g[DE])), 'F45_RKO_B': clean(U(EST, LV).difference(g[DE])), 'F45_RKO_C': clean(g[LV]),
    'F45_RKU_A': clean(g[RKU].difference(U(DE, RKO))), 'F45_RKU_B': clean(U(WP, NIK).difference(U(DE, RKO))),
    'F45_SU_1': clean(g[SU].difference(U(DE, RKO, RKU, RO))),
    'F45_SU_2': clean(g[SU].difference(U(DE, RKO, WP, NIK, RO))),
    'F45_SU_3': clean(g[SU].difference(U(DE, RKO))),
    'F45_SU_4': clean(g[SU].difference(U(DE, EST, LV))),
    'F45_SU_5': clean(g[SU].difference(U(DE, LV))),
    'F45_SU_6': clean(g[SU44A].difference(U(DE, LV))),
    'F45_SU_7': clean(g[SU44B].difference(U(DE, LV))),
    'F45_SU_8': clean(g[SU44B].difference(g[DE])),
    'F45_SU_9': clean(g[SU44B].difference(DE45)),
}
DAYS = {'1943-07-01': ['F45_DE_A', 'F45_RKO_A', 'F45_RKU_A', 'F45_SU_1'], '1944-02-01': ['F45_DE_A', 'F45_RKO_A', 'F45_RKU_B', 'F45_SU_2'],
        '1944-05-01': ['F45_DE_A', 'F45_RKO_A', 'F45_SU_3'], '1944-08-01': ['F45_DE_A', 'F45_RKO_B', 'F45_SU_4'], '1944-09-18': ['F45_DE_A', 'F45_RKO_C', 'F45_SU_5'],
        '1944-10-01': ['F45_DE_A', 'F45_RKO_C', 'F45_SU_6'], '1944-10-12': ['F45_DE_A', 'F45_RKO_C', 'F45_SU_7'], '1944-12-01': ['F45_DE_A', 'F45_SU_8'],
        '1945-03-01': ['F45_DE_B', 'F45_PL', 'F45_SU_9']}
for d, ks in DAYS.items():
    for i in ks:
        for j in ks:
            if i < j:
                a = geo[i].intersection(geo[j]).area
                assert a < 1e-3, (d, i, j, a)
qa = {k: {'area_deg2': round(v.area, 3), 'polygons': len(v.geoms), 'bounds': [round(b, 2) for b in v.bounds]} for k, v in geo.items()}
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in geo.items()]},
          open(os.path.join(ROOT, 'borders-1943-1945-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(qa, open(os.path.join(ROOT, 'qa.json'), 'w'), indent=1)

def write(name, ph, post, body, meta=None, geom=None):
    req = {'_placeholder': ph, '_post': post, **({'_geometryFrom': geom} if geom else {}), **({'_meta': meta} if meta else {}), 'body': body}
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')

GPO = 'United States Department of State; United States Government Printing Office, Washington'
SOURCES = [
    ('SRC_OHM_4345', {'sourceKind': 'dataset',
        'title': 'OpenHistoricalMap — boundary=administrative, admin_level=2／3／4 關係（德國、蘇聯與東方佔領區，1943～1945-05 試驗）',
        'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
        'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
        'publishedText': '新抓的關係 Overpass osm_base 2026-10-31T08:42:13Z；其餘沿用 borders-1942-late 的固定版本；逐筆見 borders-1943-1945/ohm-manifest.json',
        'note': 'OHM 整體以 CC0 1.0 釋出；部分成員線段帶 license=CC BY 4.0 標籤（逐筆在主權紀錄標示）。'}),
    ('SRC_FRUS_1944_III', {'title': 'Foreign Relations of the United States, Diplomatic Papers, 1944, The British Commonwealth and Europe, Volume III', 'url': 'frus1944v03'}),
    ('SRC_FRUS_1944_IV', {'title': 'Foreign Relations of the United States, Diplomatic Papers, 1944, Europe, Volume IV', 'url': 'frus1944v04'}),
    ('SRC_FRUS_1945_III', {'title': 'Foreign Relations of the United States, Diplomatic Papers, 1945, European Advisory Commission, Austria, Germany, Volume III', 'url': 'frus1945v03'}),
    ('SRC_FRUS_1945_V', {'title': 'Foreign Relations of the United States, Diplomatic Papers, 1945, Europe, Volume V', 'url': 'frus1945v05'}),
]
for i, (ph, b) in enumerate(SOURCES, 1):
    if ph.startswith('SRC_FRUS'):
        b = {'sourceKind': 'official_record', 'title': b['title'], 'publisher': GPO, 'licenseCode': 'us_federal_pd',
             'licenseEvidenceUrl': 'https://www.state.gov/copyright-information', 'url': 'https://history.state.gov/historicaldocuments/' + b['url']}
    write(f'01-source-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sources', b, {'priorPlaceholder': False})

write('02-regime-01-polish-provisional-government.json', 'REGIME_PL_PROV', '/api/v1/regimes', {'slug': 'polish-provisional-government-1945', 'names': [
    {'nameKind': 'self', 'originalText': 'Rząd Tymczasowy Rzeczypospolitej Polskiej', 'originalLang': 'pl',
     'display': {'zh-Hant': '波蘭臨時政府（蘇軍控制下）', 'en': 'Polish Provisional Government (under Soviet control)'}, 'isPrimary': True}]},
    {'priorPlaceholder': False, 'nameSource': 'FRUS 1945 V Doc. 113 註（the Polish Provisional Government moved from Lublin to Warsaw）；波蘭文名為通行稱呼'})

def ev(i, ph, kind, start, zh, en, parts, cites, tn=None):
    e = (datetime.date.fromisoformat(start) + datetime.timedelta(days=1)).isoformat()
    body = {'eventKind': kind, 'occurred': {'start': start, 'end': e}, 'datePrecision': 'day', 'summary': {'zh-Hant': zh, 'en': en},
            'participants': [{'regimeId': '{{%s}}' % r, 'role': role} for r, role in parts],
            'citations': [{'sourceId': '{{%s}}' % s, 'locator': l, 'evidenceNote': n} for s, l, n in cites]}
    if tn: body['timeNote'] = {'zh-Hant': tn[0], 'en': tn[1]}
    write(f'03-event-{i:02d}-{ph.lower()}.json', ph, '/api/v1/events', body, {'verification': 'verified' if cites else 'pending（待查證）'})
W = [('REGIME_SU', 'belligerent'), ('REGIME_DE', 'belligerent')]
ev(1, 'EV_SU_PL_FRONTIER', 'war', '1944-01-05', '蘇軍越過戰前波蘭國界（烏克蘭總督轄區東部已收復）', 'Soviet forces cross the pre-war Polish frontier (eastern Reichskommissariat Ukraine retaken)', W,
   [('SRC_FRUS_1944_III', 'Doc. 1139, pp. 1216–1217', '駐波蘭流亡政府代辦 1944-01-05 電：波蘭政府將發表聲明，稱據報蘇軍已越過波蘭國界。')],
   ('日期取電報日；實際越界日未載。基輔等地 1943 年秋冬已收復，本表在此日之前仍畫整個總督轄區，是簡化。', 'Date of the telegram; Kiev etc. were retaken in autumn 1943, so drawing the whole Reichskommissariat until this date is a simplification.'))
ev(2, 'EV_PRUT', 'war', '1944-04-02', '蘇軍越過普魯特河進入羅馬尼亞（烏克蘭總督轄區與外涅斯特里亞已收復）', 'Soviet forces cross the Prut into Romania', [('REGIME_SU', 'belligerent'), ('REGIME_DE', 'belligerent'), ('REGIME_RO', 'belligerent')],
   [('SRC_FRUS_1944_IV', 'Doc. 173, pp. 165–166', '蘇聯大使館 1944-04-02 照會：紅軍追擊德軍及羅馬尼亞軍，已在數處越過普魯特河進入羅馬尼亞領土；蘇方不謀取羅馬尼亞任何領土。')],
   ('OHM 羅馬尼亞國界變動日為 1944-04-01；比薩拉比亞南部實際到 1944 年 8 月才全部收復（待查證），本表自此日起畫入蘇聯是簡化。', 'OHM changes Romania on 1 Apr 1944; southern Bessarabia was only fully retaken in Aug 1944 (pending).'))
ev(3, 'EV_VILNA', 'war', '1944-07-13', '蘇軍收復維爾紐斯（白俄羅斯、立陶宛總區已收復）', 'Soviet forces take Vilnius (White Ruthenia and Lithuania retaken)', W,
   [('SRC_FRUS_1944_III', 'Doc. 1191, pp. 1296–1298', '歐洲司長 1944-07-20 備忘錄（編者註）：蘇軍 7 月初攻勢，7 月 13 日攻下維爾紐斯，7 月 23 日攻下盧布林。'),
    ('SRC_FRUS_1944_III', 'Doc. 1301, pp. 1427–1428', '駐蘇大使 1944-07-26 電：蘇聯 7 月 25 日聲明，紅軍已抵達蘇波國界並進入波蘭。')],
   ('OHM 白俄羅斯、立陶宛總區結束日為 1944-08-01；本表取維爾紐斯收復日。', 'OHM ends the White Ruthenia and Lithuania districts on 1 Aug 1944; this table uses the date Vilnius was taken.'))
ev(4, 'EV_EST_1944', 'war', '1944-09-17', '蘇軍攻入愛沙尼亞（9 月 22 日進入塔林）', 'Soviet offensive into Estonia (Tallinn entered on 22 Sep)', W,
   [('SRC_FRUS_1944_IV', 'Doc. 832, pp. 919–920', '駐蘇大使 1944-09-28 電（編者註）：蘇軍 9 月 17 日攻入愛沙尼亞，9 月 22 日進入塔林，9 月 26 日作戰大致結束。')])
ev(5, 'EV_FI_ARMISTICE', 'political', '1944-09-19', '芬蘭與蘇聯在莫斯科簽訂停戰協定（佩察莫歸還蘇聯）', 'Finnish–Soviet armistice signed in Moscow (Petsamo returned to the USSR)', [('REGIME_SU', 'signatory'), ('REGIME_FI', 'signatory')],
   [('SRC_FRUS_1944_III', 'Doc. 560, p. 622', '駐蘇大使 1944-09-19 電：維辛斯基告知芬蘭停戰協定當日中午在莫斯科簽字。'),
    ('SRC_FRUS_1944_III', 'Doc. 526, pp. 585–587', '蘇聯大使館 1944-04-01 照會：蘇方停戰條件含佩察莫地區歸還蘇聯。')])
ev(6, 'EV_RIGA', 'war', '1944-10-13', '蘇軍收復里加（拉脫維亞總區結束；庫爾蘭仍由德軍據守）', 'Soviet forces take Riga (Courland still held by German forces)', W, [],
   ('尚未取得正式出處；日期依 OHM relation/2693110 的 end_date。', 'No formal source yet; date from OHM.'))
ev(7, 'EV_WARSAW', 'war', '1945-01-17', '蘇軍攻下華沙，波蘭臨時政府由盧布林遷往華沙（總督府結束）', 'Red Army takes Warsaw; Polish Provisional Government moves from Lublin to Warsaw', W,
   [('SRC_FRUS_1945_V', 'Doc. 113, pp. 123–125', '駐蘇大使 1945-02-24 電（編者註）：紅軍 1945-01-17 攻下華沙後，波蘭臨時政府由盧布林遷往華沙。')],
   ('OHM 總督府結束日為 1945-01-19；本表取華沙攻下日。', 'OHM ends the Generalgouvernement on 19 Jan 1945; this table uses the date Warsaw was taken.'))
ev(8, 'EV_DE_SURRENDER', 'surrender', '1945-05-08', '德國無條件投降（5 月 7 日蘭斯簽字，5 月 8 日柏林批准）', 'Unconditional surrender of Germany (signed at Reims 7 May, ratified in Berlin 8 May)',
   [('REGIME_DE', 'signatory'), ('REGIME_SU', 'signatory'), ('REGIME_UK', 'signatory')],
   [('SRC_FRUS_1945_III', 'Doc. 222, p. 280', '編者註：1945-05-07 德軍最高統帥部在蘭斯向盟軍最高統帥與蘇聯統帥部無條件投降；5 月 8 日在柏林批准。'),
    ('SRC_FRUS_1945_III', 'Doc. 229, pp. 284–285', '駐德政治顧問 1945-05-10 電：提及 5 月 8 日在柏林簽署軍事投降書。')],
   ('美國是主要簽字方之一，但政權表尚無美國。', 'The US was a principal signatory but is not yet in the regime table.'))

def lic(rels):
    rs = [MAN[r] for r in rels]
    attr = sorted({a for r in rs if r['attribution'] for a in r['attribution'].split('; ')})
    return ('cc_by' if any(r['geometry_license'] == 'cc_by' for r in rs) else 'cc0'), ('; '.join(attr) or None)
L = lambda *rs: ' − '.join(f'relation/{r} v{MAN[r]["ohm_version"]}' for r in rs)
def rec(i, ph, regime, fix, main, rels, locator, layer, start, end, sev, eev, nzh, nen):
    m = MAN[main]; gl, attr = lic(rels)
    body = {'regimeId': '{{%s}}' % regime, 'geometry': None, 'validPeriod': {'start': start, 'end': end}, 'layerStatus': layer,
            'geometrySourceId': '{{SRC_OHM_4345}}', 'geometryLocator': locator, 'geometryLicense': gl, 'attribution': attr,
            'startEventId': ('{{%s}}' % sev) if sev else None, 'endEventId': ('{{%s}}' % eev) if eev else None,
            'ohmRelationId': main, 'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'], 'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date'],
            'provenance': {'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': sum(MAN[r]['osm_derived_way_count'] for r in rels),
                           'ohmFixme': m['fixme'], 'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'], 'ohmTimestamp': m['ohm_timestamp'],
                           'coastline': '{{SRC_NE_LAND}}', 'derivedFrom': [f'relation/{r} v{MAN[r]["ohm_version"]}' for r in rels], 'derivation': locator,
                           'trialWindow': '1943-01-01～1945-05-09（補空白）'},
            'note': {'zh-Hant': nzh, 'en': nen}}
    write(f'04-sovereignty-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sovereignty-records', body, {'ohmName': m['name']}, geom=fix)

SUN = ('蘇聯事實國界（OHM）扣掉德國、當時仍在的總督轄區與羅馬尼亞控制區；德軍在總督轄區以東佔領或據守的地區 OHM 沒有幾何，仍畫入蘇聯。',
       'Soviet Union (OHM) minus Germany, the remaining Reichskommissariat areas and Romanian-held territory; other German-held areas have no OHM geometry.')
RKO_N = '非主權：德國佔領行政區（東方總督轄區），法理上仍屬蘇聯所併的波羅的海三國與白俄羅斯西部。'
RKU_N = '非主權：德國佔領行政區（烏克蘭總督轄區）。'
R = [
    ('SOV45_DE_A', 'REGIME_DE', 'F45_DE_A', DE, [DE], L(DE), 'de_jure', '1943-01-01', '1945-01-17', None, 'EV_WARSAW',
     '德意志國事實國界（OHM 原樣：含總督府、比亞韋斯托克區、保護國）。OHM 沒有 1944 年蘇軍進入總督府東部（盧布林 7/23、利沃夫 7/27）的幾何，華沙攻下前仍畫入德國。',
     'German Reich (OHM as is, incl. the Generalgouvernement). OHM has no geometry for the Soviet advance into the eastern GG in July 1944.'),
    ('SOV45_DE_B', 'REGIME_DE', 'F45_DE_B', DE, [DE, GG], L(DE, GG), 'de_jure', '1945-01-17', '1945-05-08', 'EV_WARSAW', 'EV_DE_SURRENDER',
     '1945-01-17 起德意志國扣掉總督府；東普魯士、西里西亞等 1945 年春失守的地區 OHM 沒有幾何，投降前仍畫入德國。', 'German Reich minus the Generalgouvernement from 17 Jan 1945 until the surrender.'),
    ('SOV45_PL', 'REGIME_PL_PROV', 'F45_PL', GG, [GG, SU44B], L(GG, SU44B), 'not_sovereign', '1945-01-17', '1945-05-09', 'EV_WARSAW', None,
     '非主權：原總督府（不含劃入蘇聯的加利西亞）在蘇軍控制下，由波蘭臨時政府管轄；美英當時尚未承認（雅爾達會議後另議改組，FRUS 1945 V Doc. 113）。',
     'Not sovereign: the former Generalgouvernement under Soviet control, administered by the Polish Provisional Government, not yet recognized by the US and UK.'),
    ('SOV45_RKO_A', 'REGIME_RK_OSTLAND', 'F45_RKO_A', RKO, [RKO, DE], L(RKO, DE), 'not_sovereign', '1943-01-01', '1944-07-13', None, 'EV_VILNA', RKO_N, 'Not sovereign: Reichskommissariat Ostland.'),
    ('SOV45_RKO_B', 'REGIME_RK_OSTLAND', 'F45_RKO_B', EST, [EST, LV], f'{L(EST)} ∪ {L(LV)}', 'not_sovereign', '1944-07-13', '1944-09-17', 'EV_VILNA', 'EV_EST_1944',
     RKO_N + '維爾紐斯收復後只剩愛沙尼亞、拉脫維亞兩個總區。', 'Only the Estonia and Latvia districts after Vilnius was taken.'),
    ('SOV45_RKO_C', 'REGIME_RK_OSTLAND', 'F45_RKO_C', LV, [LV], L(LV), 'not_sovereign', '1944-09-17', '1944-10-13', 'EV_EST_1944', 'EV_RIGA',
     RKO_N + '只剩拉脫維亞總區；里加收復後的庫爾蘭據點 OHM 沒有幾何，未畫。', 'Only the Latvia district; the Courland pocket after Riga has no OHM geometry.'),
    ('SOV45_RKU_A', 'REGIME_RK_UKRAINE', 'F45_RKU_A', RKU, [RKU, DE, RKO], L(RKU, DE, RKO), 'not_sovereign', '1943-01-01', '1944-01-05', None, 'EV_SU_PL_FRONTIER',
     RKU_N + 'OHM 不記逐區收復；基輔等地 1943 年秋冬已收復，本段仍畫整個總督轄區是簡化。', 'Not sovereign: Reichskommissariat Ukraine (whole OHM extent; a simplification for late 1943).'),
    ('SOV45_RKU_B', 'REGIME_RK_UKRAINE', 'F45_RKU_B', WP, [WP, NIK], f'{L(WP)} ∪ {L(NIK)}', 'not_sovereign', '1944-01-05', '1944-04-02', 'EV_SU_PL_FRONTIER', 'EV_PRUT',
     RKU_N + '蘇軍越過戰前波蘭國界後只剩沃里尼亞—波多里亞、尼古拉耶夫兩個總區（實際逐步收復，這是簡化）。', 'Only the Volhynia-Podolia and Nikolaev districts (a simplification).'),
    ('SOV45_SU_1', 'REGIME_SU', 'F45_SU_1', SU, [SU, DE, RKO, RKU, RO], L(SU, DE, RKO, RKU, RO), 'de_jure', '1943-01-01', '1944-01-05', None, 'EV_SU_PL_FRONTIER', *SUN),
    ('SOV45_SU_2', 'REGIME_SU', 'F45_SU_2', SU, [SU, DE, RKO, WP, NIK, RO], L(SU, DE, RKO, WP, NIK, RO), 'de_jure', '1944-01-05', '1944-04-02', 'EV_SU_PL_FRONTIER', 'EV_PRUT', *SUN),
    ('SOV45_SU_3', 'REGIME_SU', 'F45_SU_3', SU, [SU, DE, RKO], L(SU, DE, RKO), 'de_jure', '1944-04-02', '1944-07-13', 'EV_PRUT', 'EV_VILNA', *SUN),
    ('SOV45_SU_4', 'REGIME_SU', 'F45_SU_4', SU, [SU, DE, EST, LV], L(SU, DE, EST, LV), 'de_jure', '1944-07-13', '1944-09-17', 'EV_VILNA', 'EV_EST_1944', *SUN),
    ('SOV45_SU_5', 'REGIME_SU', 'F45_SU_5', SU, [SU, DE, LV], L(SU, DE, LV), 'de_jure', '1944-09-17', '1944-09-19', 'EV_EST_1944', 'EV_FI_ARMISTICE', *SUN),
    ('SOV45_SU_6', 'REGIME_SU', 'F45_SU_6', SU44A, [SU44A, DE, LV], L(SU44A, DE, LV), 'de_jure', '1944-09-19', '1944-10-11', 'EV_FI_ARMISTICE', None,
     SUN[0] + '1944-09-19 起含佩察莫。', SUN[1]),
    ('SOV45_SU_7', 'REGIME_SU', 'F45_SU_7', SU44B, [SU44B, DE, LV], L(SU44B, DE, LV), 'de_jure', '1944-10-11', '1944-10-13', None, 'EV_RIGA',
     SUN[0] + 'OHM 1944-10-11 的變動（圖瓦併入）在歐陸框外，框內幾何不變。', SUN[1]),
    ('SOV45_SU_8', 'REGIME_SU', 'F45_SU_8', SU44B, [SU44B, DE], L(SU44B, DE), 'de_jure', '1944-10-13', '1945-01-17', 'EV_RIGA', 'EV_WARSAW', *SUN),
    ('SOV45_SU_9', 'REGIME_SU', 'F45_SU_9', SU44B, [SU44B, DE, GG], L(SU44B) + ' − (' + L(DE, GG) + ')', 'de_jure', '1945-01-17', '1945-05-09', 'EV_WARSAW', None,
     SUN[0] + '本段到 1945-05-09（試驗期間終點，不追溯）。', SUN[1]),
]
for i, r in enumerate(R, 1): rec(i, *r)
print('ok', json.dumps(qa))
