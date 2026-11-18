"""第 3 步：pieces.csv（Mac 上 PostGIS 疊合檢查結果）→ requests/*.json＋derived.geojson＋報告。
合併：同一候選相鄰子期間若剩餘面積差 < 5 km²（只差邊界細條）就合併，幾何取各段交集（保證不蓋到任何一段的既有紀錄）。
扣除 > 1000 km² 的疊合列入 overlaps.json 待 Tai 決定；剩不到 1 km² 的片段不寫。
用法：make.py <批次目錄> <批次代號，例 B1> <seed 目錄名>"""
import csv, collections, importlib.util, json, os, sys
from shapely.geometry import shape, mapping, MultiPolygon
from shapely.validation import make_valid
csv.field_size_limit(1 << 30)
B, TAG, SEED = os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3]; HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('cfg', os.path.join(B, 'config.py')); C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
HI = '1945-10-01'; NE_LAND = '01a18e71-c977-7a2c-afe3-cb56ea3ec9fa'
man = {r['ohm_relation_id']: r for r in json.load(open(f'{B}/ohm-manifest.json'))}
plan = json.load(open(f'{B}/plan.json')); cands = {c['cid']: c for c in plan['cands']}
reg = {r[0]: (r[1], r[2]) for r in csv.reader(open(os.path.join(HERE, '../regimes.csv')))}
qids = {q: s for s, (i, q) in reg.items() if q}
for slug, v in C.NEW.items():
    if slug in reg: sys.exit(f'{slug} 已存在，應掛既有政權')
    if v[5] in qids: sys.exit(f'{slug} 的 wikidata {v[5]} 已屬既有政權 {qids[v[5]]}')
def poly(g):
    g = make_valid(g)
    ps = [p for p in getattr(g, 'geoms', [g]) if p.geom_type == 'Polygon'] + [q for p in getattr(g, 'geoms', []) if p.geom_type == 'MultiPolygon' for q in p.geoms]
    if g.geom_type == 'MultiPolygon': ps = list(g.geoms)
    return MultiPolygon(ps) if ps else MultiPolygon()
rows = collections.defaultdict(list)
for cid, a, b, others, ckm, rkm, gj in csv.reader(open(f'{B}/pieces.csv')):
    rows[cid].append(dict(a=a, b=b, others=others.split(), ckm=float(ckm), rkm=float(rkm), g=shape(json.loads(gj))))
recs, overlaps, dropped = [], [], []
for cid, ps in rows.items():
    ps.sort(key=lambda p: p['a']); cur = None
    for p in ps:
        for o in p['others']:
            pass
        if cur and cur['b'] == p['a'] and abs(cur['rkm'] - p['rkm']) < 5:
            cur['b'] = p['b']; cur['g'] = poly(cur['g'].intersection(p['g'])); cur['others'] |= set(p['others']); cur['rkm'] = min(cur['rkm'], p['rkm']); continue
        cur and recs.append(cur)
        cur = dict(cid=cid, a=p['a'], b=p['b'], g=p['g'], others=set(p['others']), ckm=p['ckm'], rkm=p['rkm'])
        if p['ckm'] - p['rkm'] > 1000:
            overlaps.append(dict(cid=cid, slug=cands[cid]['slug'], period=[p['a'], p['b']], cand_km2=p['ckm'], written_km2=p['rkm'], removed_km2=round(p['ckm'] - p['rkm'], 1), against=p['others']))
    recs.append(cur)
keep = []
for r in recs:
    if r['g'].is_empty or r['rkm'] < 1: dropped.append(dict(cid=r['cid'], period=[r['a'], r['b']], reason='扣除疊合後幾乎沒有剩餘陸地')); continue
    keep.append(r)
os.makedirs(f'{B}/requests', exist_ok=True)
for f in os.listdir(f'{B}/requests'): os.remove(f'{B}/requests/{f}')
def w(name, obj): json.dump(obj, open(f'{B}/requests/{name}.json', 'w'), ensure_ascii=False, indent=1)
osm_base = max(m['osm_base'] for m in man.values()); SRC = f'SRC_OHM_{TAG}'
w(f'01-source-01-{SRC.lower()}', {'_placeholder': SRC, '_post': '/api/v1/sources', 'body': {
    'sourceKind': 'dataset', 'title': C.SOURCE_TITLE, 'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0',
    'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright', 'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
    'publishedText': f'Overpass osm_base {osm_base}；逐筆見 data/seed/{SEED}/ohm-manifest.json',
    'note': 'OHM 整體以 CC0 1.0 釋出；逐筆成員線段授權見 provenance。政權名稱與起訖日依 Tai 2026-11-04 00:40／00:53 決定採信 OHM；與既有疆界重疊處不覆蓋（扣除）。'}})
rid_of = {}
used = sorted({cands[r['cid']]['slug'] for r in keep})
for i, slug in enumerate([s for s in used if s in C.NEW], 1):
    orig, lang, zh, en, layer, qid = C.NEW[slug]; ph = 'REGIME_' + slug.upper().replace('-', '_')
    rels = sorted({cands[r['cid']]['rid'] for r in keep if cands[r['cid']]['slug'] == slug})
    rid_of[slug] = '{{%s}}' % ph
    w(f'02-regime-{i:02d}-{slug}', {'_placeholder': ph, '_post': '/api/v1/regimes', '_meta': {'nameSource': f'OHM relation {", ".join(map(str, rels))} 的 official_name／name；wikidata 取自 OHM（{qid}）'},
       'body': {'slug': slug, 'wikidataQid': qid, 'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]}})
for slug in used:
    if slug not in C.NEW:
        if slug not in reg: sys.exit(f'{slug} 不在 NEW 也不在既有政權')
        rid_of[slug] = reg[slug][0]
layer_of = {s: v[4] for s, v in C.NEW.items()}; layer_of.update(getattr(C, 'LAYER', {}))
derived = []
for j, r in enumerate(sorted(keep, key=lambda r: (cands[r['cid']]['slug'], r['a'])), 1):
    c = cands[r['cid']]; m = man[c['rid']]; slug = c['slug']; ph = f'SOV_{r["cid"]}_{r["a"]}'
    derived.append({'type': 'Feature', 'id': ph, 'properties': {'slug': slug, 'start': r['a'], 'end': r['b'], 'ohm': c['rid']}, 'geometry': mapping(r['g'])})
    zh, en = [], []
    if c['prec']:
        zh.append('OHM 日期缺日精度：' + '、'.join(f'{"起" if k == "start" else "迄"}日只有{"年" if v == "year" else "年月"}（{m["start_date"] if k == "start" else m["end_date"]}），補為該{"年" if v == "year" else "月"}第一天' for k, v in c['prec'].items()) + '。')
        en.append('OHM date lacks day precision; first day of the ' + '/'.join(c['prec'].values()) + ' used.')
    big = [o for o in overlaps if o['cid'] == r['cid'] and r['a'] <= o['period'][0] < r['b']]
    if big:
        zh.append('與既有／同批疆界重疊的部分已扣除不覆蓋（' + '；'.join(f"{o['period'][0]}～{o['period'][1]} 扣 {o['removed_km2']:.0f} km²" for o in big) + '），待 Tai 決定。')
        en.append('Parts overlapping existing or same-batch boundaries were subtracted, pending decision.')
    if r['b'] == HI and (m['end_date'] is None or m['end_date'] >= HI): zh.append('到 1945-09-30（第一階段終點）。'); en.append('Until 30 Sep 1945 (end of stage 1).')
    layer = layer_of.get(slug, 'de_jure')
    w(f'05-sovereignty-{j:02d}-sov_{slug}_{r["a"]}', {'_placeholder': ph, '_post': '/api/v1/sovereignty-records', '_geometryFrom': ph, 'body': {
        'regimeId': rid_of[slug], 'geometry': None, 'validPeriod': {'start': r['a'], 'end': r['b']}, 'layerStatus': layer,
        'geometrySourceId': '{{%s}}' % SRC, 'geometryLocator': f'relation/{c["rid"]} v{m["ohm_version"]}', 'geometryLicense': m['geometry_license'], 'attribution': m['attribution'],
        'startEventId': None, 'endEventId': None, 'ohmRelationId': c['rid'], 'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'],
        'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date'],
        'provenance': {'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': m['osm_derived_way_count'], 'ohmFixme': m['fixme'],
            'ohmRelationSource': m['relation_source'], 'ohmDateSources': m['date_sources'] or None, 'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'],
            'ohmTimestamp': m['ohm_timestamp'], 'coastline': NE_LAND,
            'licenseReview': (f"{m['cco_typo_ways']} 條成員線段標 license=CCO 4.0（字母 O），視為 CC0" if m['cco_typo_ways'] else None), 'datePrecision': c['prec'] or None,
            'subtractedOverlaps': sorted(r['others']) or None, 'writtenKm2': r['rkm'],
            'decision': 'Tai 2026-11-04 00:40／00:53／00:55：政權用 OHM 名＋wikidata、採信 OHM 起訖日；已有政權掛既有記錄；與既有疆界重疊處不覆蓋', 'trialWindow': C.TRIAL},
        'note': ({'zh-Hant': ''.join(zh), 'en': ' '.join(en)} if zh else None)}})
json.dump({'type': 'FeatureCollection', 'features': derived}, open(f'{B}/derived.geojson', 'w'), separators=(',', ':'))
json.dump(dict(overlaps=overlaps, dropped=dropped, skipped=plan['skipped'], conflicts=plan['conflicts'], low=plan['low']), open(f'{B}/report.json', 'w'), ensure_ascii=False, indent=1)
print('new regimes', len([s for s in used if s in C.NEW]), 'sovereignty', len(keep), 'overlaps>1000km²', len(overlaps), 'dropped', len(dropped))
for r in sorted(keep, key=lambda r: (cands[r['cid']]['slug'], r['a'])): print(' ', cands[r['cid']]['slug'], r['a'], r['b'], round(r['rkm']), sorted(r['others'])[:3])
