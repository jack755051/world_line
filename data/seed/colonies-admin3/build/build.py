#!/usr/bin/env python3
"""補三個整段期間沒有紀錄的殖民地：蘇利南、庫拉索及屬地、西屬幾內亞。產生幾何與請求檔；不連資料庫。
原因：匯入只取 OHM admin_level=2 的關係；這三個殖民地在 OHM 是 admin_level=3（掛在荷蘭、西班牙底下），本國的紀錄又只畫歐洲本土，所以整段期間沒有紀錄。
Tai 2026-11-14：照新規則（憲法 R10）有出處的不留白；另立殖民地政權，和資料庫裡其他殖民地的做法一致。
用法：python build.py <others.jsonl> <OHM raw 目錄> <ne_10m_land.geojson>   （需要 shapely；others 是鄰近既有紀錄的唯讀匯出）
"""
import json, os, sys, math, collections
from shapely.geometry import LineString, Polygon, MultiPolygon, box, shape, mapping
from shapely.ops import polygonize, unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
OTHERS, RAW, NE = sys.argv[1:4]
END = '1945-10-01'
SH_SA, CM_SA = 'pp. 214–215, South America（archive.org 掃描頁 n198）', 'Map 135, South America in 1910（archive.org 掃描頁 n603–n604）'
SH_WI, CM_WI = 'p. 213, Mexico, Central America and the West Indies（archive.org 掃描頁 n196）', 'Map 134, The West Indies and Central America in 1910（archive.org 掃描頁 n600）'
SH_AF, CM_AF = 'pp. 174–175, The Partition of Africa（archive.org 掃描頁 n166–n167）', 'Map 130, Africa in 1910（archive.org 掃描頁 n589–n590）'
COLONIES = [
 {'ph': 'SURINAME', 'slug': 'colony-of-suriname', 'orig': 'Kolonie Suriname', 'lang': 'nl', 'zh': '蘇利南（荷屬圭亞那）', 'en': 'Suriname (Dutch Guiana)', 'qid': 'Q7646305', 'bbox': (-60, 0, -52, 8),
  'parts': [(2884613, '1908-01-01', '1922-12-13'), (2884614, '1922-12-13', END)],
  'cites': [('SRC_SHEPHERD_1911', SH_SA, '圖版畫出：圭亞那三塊之中的荷屬圭亞那（標「Dutch」「Surinam」與帕拉馬里博），以荷蘭色著色，西鄰英屬圭亞那、東鄰法屬圭亞那。'),
            ('SRC_CMHA_1924', CM_SA, '圖版畫出：「Dutch Guiana」，以荷蘭色著色，介於英屬與法屬圭亞那之間，標出帕拉馬里博。')]},
 {'ph': 'CURACAO', 'slug': 'curacao-and-dependencies', 'orig': 'Curaçao en Onderhorigheden', 'lang': 'nl', 'zh': '庫拉索及屬地（荷屬安地列斯）', 'en': 'Curaçao and Dependencies', 'qid': 'Q1953333', 'bbox': (-71, 11, -62, 19),
  'parts': [(2877150, '1908-01-01', '1922-12-13'), (2877118, '1922-12-13', END)],
  'cites': [('SRC_SHEPHERD_1911', SH_WI, '圖版畫出：阿魯巴、庫拉索（標「Dutch」）、波奈以荷蘭色底線標示；背風群島的聖馬丁、聖佑達修斯也以同色標示。'),
            ('SRC_CMHA_1924', CM_WI, '圖版畫出：Oruba、Curaçoa、Buen Ayre 三島以荷蘭色底線標示；聖佑達修斯一帶同色。')]},
 {'ph': 'SPGUINEA', 'slug': 'spanish-guinea', 'orig': 'Territorios Españoles del Golfo de Guinea', 'lang': 'es', 'zh': '西屬幾內亞', 'en': 'Spanish Guinea', 'qid': 'Q1232509', 'bbox': (4, -3, 13, 5),
  'parts': [(2860389, '1908-01-01', END)],
  'cites': [('SRC_SHEPHERD_1911', SH_AF, '圖版畫出：木尼河區（Rio Muni）與費爾南多波島、安諾本島，標為西班牙屬地。'),
            ('SRC_CMHA_1924', CM_AF, '圖版畫出：「RIO MUNI」以西班牙色著色，費爾南多波島標名。')]},
]
def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    if isinstance(g, MultiPolygon): return list(g.geoms)
    return [p for x in getattr(g, 'geoms', []) for p in polys(x)]
def mp(g, minarea=1e-7): return MultiPolygon([p for p in polys(make_valid(g)) if p.area > minarea])
def km2(g): return sum(p.area * 12392 * math.cos(math.radians(p.centroid.y)) for p in polys(g))
ALL_LAND = [make_valid(shape(f['geometry'])) for f in json.load(open(NE))['features']]
def load(rid, bbox):
    land = unary_union([g.intersection(box(*bbox)) for g in ALL_LAND if g.intersects(box(*bbox))])
    x = json.load(open(f'{RAW}/r{rid}.json')); rel = [e for e in x['elements'] if e['type'] == 'relation'][0]
    tags = {e['id']: e.get('tags', {}) for e in x['elements'] if e['type'] == 'way'}; outer, inner, lic = [], [], collections.Counter()
    for m in rel['members']:
        if m['type'] != 'way' or 'geometry' not in m: continue
        c = [(p['lon'], p['lat']) for p in m['geometry'] if p]
        if len(c) < 2: continue
        (inner if m['role'] == 'inner' else outer if m['role'] in ('outer', '') else []).append(LineString(c))
        t = tags.get(m['ref'], {}); lic[(t.get('license') or t.get('source:license') or '').strip() or 'untagged(OHM CC0)'] += 1
    o = unary_union(list(polygonize(unary_union(outer)))) if outer else Polygon()
    i = unary_union(list(polygonize(unary_union(inner)))) if inner else Polygon()
    g = mp(set_precision(make_valid(make_valid(make_valid(o.difference(i)).intersection(land)).simplify(0.0005, preserve_topology=True)), 1e-4))
    return rel, g, dict(lic), open(f'{RAW}/r{rid}.json.fetched').read().strip()
others = [json.loads(l) for l in open(OTHERS)]
for o in others: o['g'] = make_valid(shape(o['geom']))
def write(name, obj): json.dump(obj, open(os.path.join(ROOT, 'requests', name), 'w'), ensure_ascii=False, indent=1)
write('01-source-ohm-admin3.json', {'_placeholder': 'SRC_OHM_ADMIN3_COLONIES', '_post': '/api/v1/sources', 'body': {
    'sourceKind': 'dataset', 'title': 'OpenHistoricalMap — boundary=administrative, admin_level=3 關係（蘇利南 2884613／2884614、庫拉索及屬地 2877150／2877118、西屬幾內亞 2860389；1908～1945）',
    'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
    'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter', 'publishedText': '2026-11-14 以 Overpass 逐筆取回；版本與取回時間記在每筆主權紀錄上',
    'note': 'OHM 整體以 CC0 1.0 釋出；這五個關係的成員線段都沒有另外標示授權。'}})
feats, n = [], 1
B = {'SRC_SHEPHERD_1911': '具名學者編著的歷史地圖集圖版（學術地圖集為 B）。Claude 目視比對，2026-11-14，待考證複核。', 'SRC_CMHA_1924': '學術機構出版的歷史地圖集圖版（學術地圖集為 B）。Claude 目視比對，2026-11-14，待考證複核。'}
for c in COLONIES:
    n += 1
    write(f'{n:02d}-regime-{c["slug"]}.json', {'_placeholder': 'REGIME_' + c['ph'], '_post': '/api/v1/regimes', '_meta': {'nameSource': 'OHM 關係的 name／name:nl／name:es；wikidata 取自 OHM'},
          'body': {'slug': c['slug'], 'wikidataQid': c['qid'], 'names': [{'nameKind': 'self', 'originalText': c['orig'], 'originalLang': c['lang'], 'display': {'zh-Hant': c['zh'], 'en': c['en']}, 'isPrimary': True}]}})
    for k, (rid, a, b) in enumerate(c['parts']):
        rel, g, lic, fetched = load(rid, c['bbox']); t = rel['tags']; cut = []
        for o in others:
            if o['lo'] < b and a < (o['hi'] or '9999'):
                x = km2(g.intersection(o['g']))
                if x > 0.05: cut.append({'slug': o['slug'], 'period': [o['lo'], o['hi']], 'km2': round(x, 2)}); g = mp(g.difference(o['g']))
        g = mp(set_precision(make_valid(g), 1e-4), 1e-7)
        assert set(lic) == {'untagged(OHM CC0)'}, lic
        assert sum(x['km2'] for x in cut) < 0.02 * km2(g) + 50, (c['slug'], cut)
        ph = f'SOV_{c["ph"]}_{a[:4]}'; feats.append({'type': 'Feature', 'id': ph, 'properties': {}, 'geometry': mapping(g)})
        print(c['slug'], rid, 'v', rel['version'], a, b, 'km2', round(km2(g), 1), 'parts', len(g.geoms), 'cut', [(x['slug'], x['km2']) for x in cut])
        n += 1
        write(f'{n:02d}-sovereignty-{ph.lower()}.json', {'_placeholder': ph, '_post': '/api/v1/sovereignty-records', '_geometryFrom': ph, '_meta': {'km2': round(km2(g), 1)}, 'body': {
            'regimeId': '{{REGIME_%s}}' % c['ph'], 'geometry': None, 'validPeriod': {'start': a, 'end': b}, 'layerStatus': 'de_jure',
            'geometrySourceId': '{{SRC_OHM_ADMIN3_COLONIES}}', 'geometryLocator': f"relation/{rid} v{rel['version']}", 'geometryLicense': 'cc0', 'attribution': None,
            'startEventId': None, 'endEventId': None, 'ohmRelationId': rid, 'ohmVersion': rel['version'], 'ohmFetchedAt': fetched, 'ohmStartRaw': t.get('start_date'), 'ohmEndRaw': t.get('end_date'),
            'provenance': {'decision': 'Tai 2026-11-14：有出處的不留白（憲法 R10）；另立殖民地政權', 'batch': 'colonies-admin3', 'ohmChangeset': rel.get('changeset'), 'ohmTimestamp': rel.get('timestamp'),
                           'ohmAdminLevel': t.get('admin_level'), 'memberWayLicense': lic, 'writtenKm2': round(km2(g), 1), 'subtractedOverlaps': cut or None,
                           'trialWindow': '1908-01-01～1945-09-30', 'coastline': 'Natural Earth 1:10m land'},
            'note': {'zh-Hant': f"{c['zh']}：{'荷蘭' if c['lang'] == 'nl' else '西班牙'}殖民地。資料集把它記為本國底下的次一級單位；資料庫裡本國的紀錄只畫歐洲本土，所以另立殖民地政權。" + ('1922-12-13 是資料集的分段日（荷蘭修憲把殖民地改稱領地），形狀沒有變。' if len(c['parts']) > 1 else ''),
                     'en': f"{c['en']}: a {'Dutch' if c['lang'] == 'nl' else 'Spanish'} colony, recorded as a separate regime because the metropolitan record covers only Europe."}}})
        if k == 0:
            for src, loc, note in c['cites']:
                n += 1
                write(f'{n:02d}-citation-{ph.lower()}-{src[4:8].lower()}.json', {'_placeholder': f'CITE_{c["ph"]}_{src[4:8]}', '_post': '/api/v1/sovereignty-records/{{%s}}/citations' % ph, 'body': {
                    'sourceId': '{{%s}}' % src, 'locator': loc, 'evidenceNote': note + '與本紀錄 1908 年的範圍與歸屬相符；1908 到 1911 年間沒有影響這個判斷的變動。圖版比例尺很小，只能確認到輪廓與歸屬，不能確認邊界細節。', 'grade': 'B', 'gradeBasis': B[src]}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(ROOT, 'colonies-admin3-derived.geojson'), 'w'), separators=(',', ':'))
