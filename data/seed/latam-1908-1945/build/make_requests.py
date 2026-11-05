"""ohm-manifest.json＋borders-ohm-latam.geojson → requests/L1/*.json（來源 1、政權、主權紀錄）＋latam-derived.geojson（key＝placeholder）。
規則（Tai 2026-11-04 00:40）：政權用 OHM 國名（official_name，沒有就 name）＋OHM wikidata 建立；起訖日採信 OHM start_date／end_date。
期間裁到 [1908-01-01, 1945-10-01)（第一階段 1908-01-01～1945-09-30）；end_date 視為變動當日（不含），與既有批次相同。
缺日精度（只有年或年月）的日期補成該年／月第一天，記在 provenance.datePrecision 與 note，並列在 low-precision.json。"""
import json, os, re, collections, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regimes import R
os.chdir(os.path.dirname(os.path.abspath(__file__)))
LO, HI = '1908-01-01', '1945-10-01'
NE_LAND = '01a18e71-c977-7a2c-afe3-cb56ea3ec9fa'   # Natural Earth 10m Land（既有來源，直接用 id）
man = {r['ohm_relation_id']: r for r in json.load(open('ohm-manifest.json'))}
geo = {f['id']: f['geometry'] for f in json.load(open('borders-ohm-latam.geojson'))['features']}
osm_base = max(r['osm_base'] for r in man.values())

def norm(d, is_end):
    if d is None: return (HI if is_end else None), 'open'
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d): return d, 'day'
    if re.fullmatch(r'\d{4}-\d{2}', d): return d + '-01', 'month'
    if re.fullmatch(r'\d{4}', d): return d + '-01-01', 'year'
    raise SystemExit(f'無法解析日期 {d}')

recs, low, skipped = [], [], []
for rid, m in sorted(man.items(), key=lambda kv: (kv[1]['name'], kv[1]['start_date'] or '')):
    slug, _orig, lang, zh, en, layer = R[m['name']]
    s, sp = norm(m['start_date'], False); e, ep = norm(m['end_date'], True)
    a, b = max(s, LO), min(e, HI)
    if a >= b: skipped.append((rid, m['name'], 'outside window')); continue
    if rid not in geo: skipped.append((rid, m['name'], 'no polygon after clip')); continue
    prec = {}
    if sp in ('year', 'month') and s > LO: prec['start'] = sp
    if ep in ('year', 'month') and e < HI: prec['end'] = ep
    if prec: low.append(dict(ohm_relation_id=rid, name=m['name'], start_raw=m['start_date'], end_raw=m['end_date'], used=[a, b], precision=prec))
    recs.append(dict(rid=rid, slug=slug, lang=lang, zh=zh, en=en, layer=layer, start=a, end=b, prec=prec, m=m))

# 同政權期間不得重疊（ex_sovereignty_records_no_overlap）
by = collections.defaultdict(list)
for r in recs: by[r['slug']].append(r)
for slug, rs in by.items():
    rs.sort(key=lambda r: r['start'])
    for x, y in zip(rs, rs[1:]):
        if y['start'] < x['end']: raise SystemExit(f'衝突：{slug} {x["rid"]} [{x["start"]},{x["end"]}) 與 {y["rid"]} [{y["start"]},{y["end"]}) 重疊')

os.makedirs('requests/L1', exist_ok=True)
for f in os.listdir('requests/L1'): os.remove(os.path.join('requests/L1', f))
def w(name, obj): json.dump(obj, open(f'requests/L1/{name}.json', 'w'), ensure_ascii=False, indent=1)
w('01-source-01-src_ohm_latam', {'_placeholder': 'SRC_OHM_LATAM', '_post': '/api/v1/sources', 'body': {
    'sourceKind': 'dataset',
    'title': 'OpenHistoricalMap — boundary=administrative, admin_level=2 關係（拉丁美洲：墨西哥、中美洲、加勒比、南美，1908～1945）',
    'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
    'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
    'publishedText': f'Overpass osm_base {osm_base}；逐筆見 data/seed/latam-1908-1945/ohm-manifest.json',
    'note': 'OHM 整體以 CC0 1.0 釋出；本批成員線段沒有 CC BY 標籤、沒有標示來自 OpenStreetMap 的線段（逐筆見 provenance）。政權名稱與起訖日依 Tai 2026-11-04 00:40 決定採信 OHM。'}})
seen = {}
for i, slug in enumerate(sorted(by), 1):
    rs = by[slug]; m0 = max(rs, key=lambda r: r['end'])['m']
    names = collections.Counter((r['m']['official_name'] or r['m']['name']) for r in rs)
    orig = names.most_common(1)[0][0]
    qids = collections.Counter(r['m']['wikidata'] for r in rs if r['m']['wikidata'])
    qid = (m0['wikidata'] or (qids.most_common(1)[0][0] if qids else None))
    r0 = rs[0]
    ph = 'REGIME_' + slug.upper().replace('-', '_')
    seen[slug] = ph
    w(f'02-regime-{i:02d}-{slug}', {'_placeholder': ph, '_post': '/api/v1/regimes', '_meta': {
        'nameSource': f'OHM relation {", ".join(str(r["rid"]) for r in rs)} 的 official_name／name；wikidata 取自 OHM（{qid or "OHM 未標"}）'},
        'body': {'slug': slug, 'wikidataQid': qid, 'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': r0['lang'],
            'display': {'zh-Hant': r0['zh'], 'en': r0['en']}, 'isPrimary': True}]}})
derived = []
for j, r in enumerate(sorted(recs, key=lambda r: (r['slug'], r['start'])), 1):
    m = r['m']; ph = f'SOV_{r["rid"]}'
    derived.append({'type': 'Feature', 'id': ph, 'properties': {'slug': r['slug'], 'start': r['start'], 'end': r['end'], 'ohm': r['rid']}, 'geometry': geo[r['rid']]})
    notes_zh, notes_en = [], []
    if r['prec']:
        notes_zh.append('OHM 日期缺日精度：' + '、'.join(f'{"起" if k == "start" else "迄"}日只有{"年" if v == "year" else "年月"}（{m["start_date"] if k == "start" else m["end_date"]}），補為該{"年" if v == "year" else "月"}第一天' for k, v in r['prec'].items()))
        notes_en.append('OHM date lacks day precision; first day of the ' + '/'.join(r['prec'].values()) + ' used.')
    if r['start'] == LO and (m['start_date'] or '0') < LO: pass
    if r['end'] == HI and (m['end_date'] is None or m['end_date'] >= HI):
        notes_zh.append('到 1945-09-30（第一階段終點）。'); notes_en.append('Until 30 Sep 1945 (end of stage 1).')
    w(f'05-sovereignty-{j:02d}-sov_{r["slug"]}_{r["rid"]}', {'_placeholder': ph, '_post': '/api/v1/sovereignty-records', '_geometryFrom': ph, 'body': {
        'regimeId': '{{%s}}' % seen[r['slug']], 'geometry': None, 'validPeriod': {'start': r['start'], 'end': r['end']},
        'layerStatus': r['layer'], 'geometrySourceId': '{{SRC_OHM_LATAM}}', 'geometryLocator': f'relation/{r["rid"]} v{m["ohm_version"]}',
        'geometryLicense': m['geometry_license'], 'attribution': m['attribution'], 'startEventId': None, 'endEventId': None,
        'ohmRelationId': r['rid'], 'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'], 'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date'],
        'provenance': {'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': m['osm_derived_way_count'], 'ohmFixme': m['fixme'],
            'ohmRelationSource': m['relation_source'], 'ohmDateSources': m['date_sources'] or None, 'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'],
            'ohmTimestamp': m['ohm_timestamp'], 'coastline': NE_LAND, 'licenseReview': (f"{m['cco_typo_ways']} 條成員線段標 license=CCO 4.0（字母 O），視為 CC0" if m['cco_typo_ways'] else None), 'datePrecision': r['prec'] or None,
            'decision': 'Tai 2026-11-04 00:40：政權用 OHM 國名＋wikidata，採信 OHM 起訖日', 'trialWindow': '拉丁美洲 1908-01-01～1945-09-30'},
        'note': ({'zh-Hant': ' '.join(notes_zh), 'en': ' '.join(notes_en)} if notes_zh else None)}})
json.dump({'type': 'FeatureCollection', 'features': derived}, open('latam-derived.geojson', 'w'), separators=(',', ':'))
json.dump(low, open('low-precision.json', 'w'), ensure_ascii=False, indent=1)
json.dump(skipped, open('skipped.json', 'w'), ensure_ascii=False, indent=1)
print('regimes', len(by), 'sovereignty', len(recs), 'low-precision', len(low), 'skipped', skipped)
