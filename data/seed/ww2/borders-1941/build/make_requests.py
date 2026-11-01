#!/usr/bin/env python3
"""補德國、蘇聯與兩者之間佔領區的空白時段，第一段：既有 1940–1941 紀錄結束後至 1942-06-30（DRAFT，待 Tai 檢查）。
幾何：固定版本 OHM（ohm-manifest.json），依各 OHM 關係的變動日與有出處的事件分段，同一天互不重疊。
- 德意志國：relation/2704717（1941-04-14～08-01）、relation/2692712（1941-08-01 起；含總督府、比亞韋斯托克區、保護國）。
- 東方總督轄區＝2692529（自 1941-07-17 元首命令起）；烏克蘭總督轄區＝2693267（自 1941-09-01 移交民政起）。皆非主權。
  OHM 只有最大範圍；各區實際移交民政是分批進行，移交前是軍事管理（同樣是德國佔領），這裡一律畫為總督轄區，是簡化。
- 蘇聯＝relation/2851156（1941-07-17 起）− 德國 − 兩個總督轄區 − 羅馬尼亞（1941-08-19 起的 2693255）。
- 羅馬尼亞（含比薩拉比亞、北布科維納）＝2693255 − 外涅斯特里亞；外涅斯特里亞＝2693255 − 2693259，只取德涅斯特河以東；匈牙利＝2692359（1941-12-14 起）。
  這三筆與 borders-1942-south 同一套規則，只是往前補到各自的起始日，避免蘇聯扣掉之後留白。
- 1941-06-22～07-17 沿用既有的蘇聯 1940-08-06 紀錄：OHM 沒有巴巴羅薩後德軍佔領線的幾何，依事實國界不另畫。
"""
import json, os, datetime
from shapely.geometry import shape, mapping, MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); OUT = os.path.join(ROOT, 'requests')
MAN = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))}
g = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-1941.geojson')))['features']}
def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x, 'geoms', []) for p in polys(y)]
def clean(x, keep=lambda p: True):
    x = make_valid(set_precision(make_valid(x), 1e-4))
    return MultiPolygon([p for p in polys(x) if p.area > 1e-5 and keep(p)])
U = lambda *xs: unary_union(list(xs))
DE41, DE42, SU, RKO, RKU, RO, RO40, HU = 2704717, 2692712, 2851156, 2692529, 2693267, 2693255, 2693259, 2692359
TR = clean(g[RO].difference(g[RO40]), keep=lambda p: p.centroid.x > 28.5 and p.area > 0.01)
geo = {
    'F41_DE_A': clean(g[DE41]),
    'F41_DE_B': clean(g[DE42]),
    'F41_RKO': clean(g[RKO].difference(g[DE42])),
    'F41_RKU': clean(g[RKU].difference(U(g[DE42], g[RKO]))),
    'F41_SU_A': clean(g[SU].difference(U(g[DE41], g[RKO]))),
    'F41_SU_B': clean(g[SU].difference(U(g[DE42], g[RKO]))),
    'F41_SU_C': clean(g[SU].difference(U(g[DE42], g[RKO], g[RO]))),
    'F41_SU_D': clean(g[SU].difference(U(g[DE42], g[RKO], g[RKU], g[RO]))),
    'F41_RO': clean(g[RO].difference(TR)),
    'F41_TR': TR,
    'F41_HU': clean(g[HU]),
}
# 同一天的組合互不重疊
DAYS = {'1941-07-20': ['F41_DE_A', 'F41_RKO', 'F41_SU_A'], '1941-08-10': ['F41_DE_B', 'F41_RKO', 'F41_SU_B'],
        '1941-08-25': ['F41_DE_B', 'F41_RKO', 'F41_SU_C', 'F41_RO', 'F41_TR'],
        '1942-01-01': ['F41_DE_B', 'F41_RKO', 'F41_RKU', 'F41_SU_D', 'F41_RO', 'F41_TR', 'F41_HU']}
for d, ks in DAYS.items():
    for i in ks:
        for j in ks:
            if i < j:
                a = geo[i].intersection(geo[j]).area
                assert a < 1e-3, (d, i, j, a)
qa = {k: {'area_deg2': round(v.area, 3), 'polygons': len(v.geoms), 'bounds': [round(b, 2) for b in v.bounds]} for k, v in geo.items()}
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in geo.items()]},
          open(os.path.join(ROOT, 'borders-1941-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(qa, open(os.path.join(ROOT, 'qa.json'), 'w'), indent=1)

def write(name, ph, post, body, meta=None, geom=None):
    req = {'_placeholder': ph, '_post': post, **({'_geometryFrom': geom} if geom else {}), **({'_meta': meta} if meta else {}), 'body': body}
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')

write('01-source-01-src_ohm_1941.json', 'SRC_OHM_1941', '/api/v1/sources', {'sourceKind': 'dataset',
    'title': 'OpenHistoricalMap — boundary=administrative, admin_level=2／3 關係（德國、蘇聯與東方佔領區，1941-04～1942-06 試驗）',
    'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
    'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
    'publishedText': 'relation/2704717 抓取於 Overpass osm_base 2026-10-31T08:42:13Z；其餘沿用 borders-1942-late、borders-1942-south 的固定版本；逐筆見 borders-1941/ohm-manifest.json',
    'note': 'OHM 整體以 CC0 1.0 釋出；部分成員線段帶 license=CC BY 4.0 標籤（逐筆在主權紀錄標示）。'}, {'priorPlaceholder': False})

def ev(i, ph, kind, start, zh, en, parts, cites, tn=None):
    e = (datetime.date.fromisoformat(start) + datetime.timedelta(days=1)).isoformat()
    body = {'eventKind': kind, 'occurred': {'start': start, 'end': e}, 'datePrecision': 'day', 'summary': {'zh-Hant': zh, 'en': en},
            'participants': [{'regimeId': '{{%s}}' % r, 'role': role} for r, role in parts],
            'citations': [{'sourceId': '{{%s}}' % s, 'locator': l, 'evidenceNote': n} for s, l, n in cites]}
    if tn: body['timeNote'] = {'zh-Hant': tn[0], 'en': tn[1]}
    write(f'02-event-{i:02d}-{ph.lower()}.json', ph, '/api/v1/events', body, {'verification': 'verified' if cites else 'pending（待查證）'})
ev(1, 'EV_DE_SLOVENIA', 'political', '1941-04-14', '德國併入斯洛維尼亞北部（下施蒂利亞、上卡尼奧拉；OHM 德國國界變動日 1941-04-14）',
   'Germany annexes northern Slovenia (Lower Styria, Upper Carniola; OHM change 14 Apr 1941)', [('REGIME_DE', 'other')],
   [('SRC_FRUS_1941_II', 'Doc. 981, pp. 981–982', '國務卿 1941-09-25 覆照：德國與義大利瓜分並併入南斯拉夫的斯洛維尼亞各省。')],
   ('日期依 OHM relation/2704717 的 start_date；引用證明併入本身，未載明日期。', 'Date from OHM; the citation attests the annexation, not the day.'))

def lic(rels):
    rs = [MAN[r] for r in rels]
    attr = sorted({a for r in rs if r['attribution'] for a in r['attribution'].split('; ')})
    return ('cc_by' if any(r['geometry_license'] == 'cc_by' for r in rs) else 'cc0'), ('; '.join(attr) or None)
L = lambda *rs: ' − '.join(f'relation/{r} v{MAN[r]["ohm_version"]}' for r in rs)
def rec(i, ph, regime, fix, main, rels, locator, layer, start, end, sev, eev, nzh, nen):
    m = MAN[main]; gl, attr = lic(rels)
    body = {'regimeId': '{{%s}}' % regime, 'geometry': None, 'validPeriod': {'start': start, 'end': end}, 'layerStatus': layer,
            'geometrySourceId': '{{SRC_OHM_1941}}', 'geometryLocator': locator, 'geometryLicense': gl, 'attribution': attr,
            'startEventId': ('{{%s}}' % sev) if sev else None, 'endEventId': ('{{%s}}' % eev) if eev else None,
            'ohmRelationId': main, 'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'], 'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date'],
            'provenance': {'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': sum(MAN[r]['osm_derived_way_count'] for r in rels),
                           'ohmFixme': m['fixme'], 'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'], 'ohmTimestamp': m['ohm_timestamp'],
                           'coastline': '{{SRC_NE_LAND}}', 'derivedFrom': [f'relation/{r} v{MAN[r]["ohm_version"]}' for r in rels], 'derivation': locator,
                           'trialWindow': '1941-04-14～1942-06-30（補空白）'},
            'note': {'zh-Hant': nzh, 'en': nen}}
    write(f'03-sovereignty-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sovereignty-records', body, {'ohmName': m['name']}, geom=fix)

SU_NOTE = ('蘇聯事實國界（OHM 1941 年國界）扣掉德國、已設的總督轄區與羅馬尼亞收回的領土；總督轄區以東的德佔地區（軍事管理區）OHM 沒有幾何，仍畫入蘇聯。',
           'Soviet Union (OHM 1941 borders) minus Germany, the Reichskommissariats and Romanian-held territory; German-held military areas further east have no OHM geometry and stay in the USSR.')
R = [
    ('SOV41_DE_A', 'REGIME_DE', 'F41_DE_A', DE41, [DE41], L(DE41), 'de_jure', '1941-04-14', '1941-08-01', 'EV_DE_SLOVENIA', 'EV_GALICIA_BIALYSTOK',
     '1941-04-14～08-01 德意志國事實國界（OHM 原樣，含總督府、保護國與併入的斯洛維尼亞北部）。', 'German Reich, 14 Apr–1 Aug 1941 (OHM as is).'),
    ('SOV41_DE_B', 'REGIME_DE', 'F41_DE_B', DE42, [DE42], L(DE42), 'de_jure', '1941-08-01', '1942-07-01', 'EV_GALICIA_BIALYSTOK', None,
     '1941-08-01～1942-06-30 德意志國事實國界（OHM 原樣：含總督府〔含加利西亞區〕、比亞韋斯托克區、保護國），與 1942 後期紀錄相同幾何。', 'German Reich from 1 Aug 1941 (OHM as is), same geometry as the late-1942 record.'),
    ('SOV41_RKO', 'REGIME_RK_OSTLAND', 'F41_RKO', RKO, [RKO, DE42], L(RKO, DE42), 'not_sovereign', '1941-07-17', '1942-07-01', 'EV_OST_DECREE', None,
     '非主權：德國佔領行政區（東方總督轄區），法理上仍屬蘇聯所併的波羅的海三國與白俄羅斯西部。OHM 只有最大範圍；各區分批移交民政（如愛沙尼亞總區 OHM 記 1941-12-05），移交前為軍事管理，一律畫為總督轄區是簡化。',
     'Not sovereign: Reichskommissariat Ostland (maximum OHM extent; areas were transferred to civil administration in stages).'),
    ('SOV41_RKU', 'REGIME_RK_UKRAINE', 'F41_RKU', RKU, [RKU, DE42, RKO], L(RKU, DE42, RKO), 'not_sovereign', '1941-09-01', '1942-07-01', 'EV_RKU_CIVIL', None,
     '非主權：德國佔領行政區（烏克蘭總督轄區）。OHM 只有最大範圍；1941-09-01 後各區分批擴大，一律畫為總督轄區是簡化。', 'Not sovereign: Reichskommissariat Ukraine (maximum OHM extent).'),
    ('SOV41_SU_A', 'REGIME_SU', 'F41_SU_A', SU, [SU, DE41, RKO], L(SU, DE41, RKO), 'de_jure', '1941-07-17', '1941-08-01', 'EV_OST_DECREE', 'EV_GALICIA_BIALYSTOK', SU_NOTE[0], SU_NOTE[1]),
    ('SOV41_SU_B', 'REGIME_SU', 'F41_SU_B', SU, [SU, DE42, RKO], L(SU, DE42, RKO), 'de_jure', '1941-08-01', '1941-08-19', 'EV_GALICIA_BIALYSTOK', 'EV_RO_REGAIN', SU_NOTE[0], SU_NOTE[1]),
    ('SOV41_SU_C', 'REGIME_SU', 'F41_SU_C', SU, [SU, DE42, RKO, RO], L(SU, DE42, RKO, RO), 'de_jure', '1941-08-19', '1941-09-01', 'EV_RO_REGAIN', 'EV_RKU_CIVIL', SU_NOTE[0], SU_NOTE[1]),
    ('SOV41_SU_D', 'REGIME_SU', 'F41_SU_D', SU, [SU, DE42, RKO, RKU, RO], L(SU, DE42, RKO, RKU, RO), 'de_jure', '1941-09-01', '1942-07-01', 'EV_RKU_CIVIL', None, SU_NOTE[0], SU_NOTE[1]),
    ('SOV41_RO', 'REGIME_RO', 'F41_RO', RO, [RO, RO40], L(RO) + ' − 外涅斯特里亞', 'de_jure', '1941-08-19', '1942-07-01', 'EV_RO_REGAIN', None,
     '羅馬尼亞事實國界（含收回的比薩拉比亞、北布科維納）；外涅斯特里亞另畫為非主權。與 1942 後期紀錄同一規則。', 'Romania incl. Bessarabia and northern Bukovina; Transnistria drawn separately.'),
    ('SOV41_TR', 'REGIME_TRANSNISTRIA', 'F41_TR', RO, [RO, RO40], f'{L(RO)} − {L(RO40)}（德涅斯特河以東）', 'not_sovereign', '1941-08-19', '1942-07-01', 'EV_TRANSNISTRIA', None,
     '非主權：羅馬尼亞佔領的德涅斯特河—布格河之間（外涅斯特里亞），羅方未提出領土要求（FRUS 1941 I Doc. 350）。', 'Not sovereign: Romanian-occupied Transnistria.'),
    ('SOV41_HU', 'REGIME_HU', 'F41_HU', HU, [HU], L(HU), 'de_jure', '1941-12-14', '1942-07-01', 'EV_HU_YU_1941', None,
     '匈牙利事實國界（OHM 1941-12-14 起），與 1942 後期紀錄相同幾何。', 'Hungary from 14 Dec 1941 (OHM), same geometry as the late-1942 record.'),
]
for i, r in enumerate(R, 1): rec(i, *r)
print('ok', json.dumps(qa))
