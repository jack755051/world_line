"""第 5 批：1908-01-01～1908-10-05／06 全球缺口（Tai 2026-11-04 00:55／01:21）。
- 27 個政權：第一筆既有紀錄所用的 OHM relation 起日早於 1908-01-01 → 直接沿用該筆幾何（同一 relation、同一版本、同一來源），補 [1908-01-01, 第一筆起日)。
- 鄂圖曼：1908-10-06 前的 relation 2692584 多了波士尼亞與保加利亞；沿用第一筆幾何，再加上 2692584 在巴爾幹（13–30°E, 39–46°N）多出的部分，扣掉保加利亞（保加利亞 1908 前待 Tai 決定，留白）。
- 奧匈：用 1908-10-06 前的 relation 2746402（不含波士尼亞）。
- 保加利亞（tsardom-of-bulgaria，1908-10-05 獨立）不補，待決。
用法：make5.py cands → cands.csv；make5.py requests → requests/*.json（讀 pieces.csv）"""
import csv, json, os, sys
from shapely.geometry import shape, mapping, box, MultiPolygon
from shapely.validation import make_valid
csv.field_size_limit(1 << 30); os.chdir(os.path.dirname(os.path.abspath(__file__)))
LO = '1908-01-01'
cols = 'slug id regime_id start layer src locator lic attr ohm_rid ohm_ver ohm_fetched ohm_s ohm_e gj'.split()
F = {r[0]: dict(zip(cols, r)) for r in csv.reader(open('first.csv'))}
man = {m['ohm_relation_id']: m for m in json.load(open('ohm-manifest.json'))}
G = {f['properties']['ohm_relation_id']: shape(f['geometry']) for f in json.load(open('borders.geojson'))['features']}
def mp(g):
    g = make_valid(g); ps = [p for p in getattr(g, 'geoms', [g]) if p.geom_type == 'Polygon'] + [q for p in getattr(g, 'geoms', [g]) if p.geom_type == 'MultiPolygon' for q in p.geoms]
    return MultiPolygon(ps)
SKIP = {'tsardom-of-bulgaria': '1908-10-05 前的保加利亞公國在 OHM 併在鄂圖曼 relation 2692584 內，沒有獨立疆界 → 待 Tai 決定，留白'}
cands = []
for slug, f in sorted(F.items()):
    if slug in SKIP: continue
    g = shape(json.loads(f['gj'])); kind = 'copy'
    if slug == 'ottoman-empire':
        extra = G[2692584].difference(g).intersection(box(13, 39, 30, 46)).difference(shape(json.loads(F['tsardom-of-bulgaria']['gj'])))
        g = mp(g.union(extra)); kind = 'ottoman'
    elif slug == 'austria-hungary':
        g = mp(G[2746402]); kind = 'ah'
    cands.append(dict(cid=f'b5_{slug}', slug=slug, s=LO, e=f['start'], layer=f['layer'], kind=kind, g=g))
if sys.argv[1] == 'cands':
    with open('cands.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        for c in cands: w.writerow([c['cid'], c['slug'], c['s'], c['e'], json.dumps(mapping(c['g'])), c['layer']])
    json.dump(dict(skipped=SKIP), open('plan.json', 'w'), ensure_ascii=False)
    for c in cands: print(c['cid'], c['s'], c['e'], c['kind'], round(c['g'].area, 2))
    sys.exit()
# requests
import datetime
def iso(t):  # psql 輸出 '2026-10-31 16:57:28.123+00' → ISO 8601
    return datetime.datetime.fromisoformat(t.replace(' ', 'T')).astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') if t else None
P = {}
for cid, a, b, others, ckm, rkm, gj in csv.reader(open('pieces.csv')):
    P.setdefault(cid, []).append(dict(a=a, b=b, others=others.split(), ckm=float(ckm), rkm=float(rkm), g=shape(json.loads(gj))))
for cid, ps in P.items():   # 相鄰子期間只差邊界細條（< 5 km²）就合併，幾何取交集
    ps.sort(key=lambda p: p['a']); out = [ps[0]]
    for p in ps[1:]:
        q = out[-1]
        if q['b'] == p['a'] and abs(q['rkm'] - p['rkm']) < 5:
            q['b'] = p['b']; q['g'] = mp(q['g'].intersection(p['g'])); q['others'] = sorted(set(q['others']) | set(p['others'])); q['rkm'] = min(q['rkm'], p['rkm'])
        else: out.append(p)
    P[cid] = out
os.makedirs('requests', exist_ok=True)
for x in os.listdir('requests'): os.remove('requests/' + x)
def w(name, obj): json.dump(obj, open(f'requests/{name}.json', 'w'), ensure_ascii=False, indent=1)
w('01-source-01-src_ohm_b5', {'_placeholder': 'SRC_OHM_B5', '_post': '/api/v1/sources', 'body': {
    'sourceKind': 'dataset', 'title': 'OpenHistoricalMap — boundary=administrative, admin_level=2 關係（1908-10-06 前的鄂圖曼帝國 relation 2692584、奧匈帝國 relation 2746402；1908-01-01～1908-10-05 缺口）',
    'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright', 'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
    'publishedText': 'Overpass osm_base ' + max(m['osm_base'] for m in man.values()) + '；逐筆見 data/seed/ohm-b5-gap-1908/ohm-manifest.json',
    'note': 'OHM 整體以 CC0 1.0 釋出；奧匈 relation 2746402 有線段標示 CC BY 4.0，該筆標 cc_by 並附 attribution。'}})
derived, report, j = [], [], 0
for c in cands:
    f = F[c['slug']]
    for p in sorted(P[c['cid']], key=lambda p: p['a']):
        if p['g'].is_empty or p['rkm'] < 1: report.append(dict(cid=c['cid'], period=[p['a'], p['b']], reason='扣除後沒有剩餘')); continue
        j += 1; ph = f'SOV_{c["cid"]}_{p["a"]}'
        if p['ckm'] - p['rkm'] > 1000: report.append(dict(cid=c['cid'], period=[p['a'], p['b']], removed_km2=round(p['ckm'] - p['rkm']), against=p['others']))
        derived.append({'type': 'Feature', 'id': ph, 'properties': {'slug': c['slug'], 'start': p['a'], 'end': p['b']}, 'geometry': mapping(p['g'])})
        if c['kind'] == 'copy':
            src, loc, lic, attr = f['src'], f['locator'], f['lic'], f['attr'] or None
            rid, ver, fetched, sraw, eraw = int(f['ohm_rid']), int(f['ohm_ver']), iso(f['ohm_fetched']), f['ohm_s'] or None, f['ohm_e'] or None
            zh = f'1908-01-01～{c["e"]} 缺口：沿用第一筆既有紀錄（{f["id"]}）同一 OHM relation、同一版本的幾何（該 relation 起日 {sraw}，早於 1908-01-01）。'
        else:
            m = man[2692584 if c['kind'] == 'ottoman' else 2746402]
            src, rid, ver, fetched, sraw, eraw = '{{SRC_OHM_B5}}', m['ohm_relation_id'], m['ohm_version'], m['fetched_at'], m['start_date'], m['end_date']
            if c['kind'] == 'ottoman':
                loc, lic, attr = f'relation/2692584 v{ver}（巴爾幹部分，扣保加利亞）∪ {f["locator"]}', f['lic'], f['attr'] or None
                zh = '1908-01-01～1908-10-06：沿用第一筆既有紀錄幾何，加上 1908-10-06 前 relation 2692584 在巴爾幹多出的波士尼亞—赫塞哥維納等地；保加利亞（OHM 併在鄂圖曼內）扣除留白，待 Tai 決定。'
            else:
                loc, lic, attr = f'relation/2746402 v{ver}', m['geometry_license'], m['attribution']
                zh = '1908-01-01～1908-10-06：1908-10-06 合併波士尼亞前的奧匈帝國疆界（relation 2746402）。'
        if p['ckm'] - p['rkm'] > 1000: zh += f'與既有疆界重疊的 {p["ckm"] - p["rkm"]:.0f} km² 已扣除不覆蓋。'
        w(f'05-sovereignty-{j:02d}-sov_{c["slug"]}_{p["a"]}', {'_placeholder': ph, '_post': '/api/v1/sovereignty-records', '_geometryFrom': ph, 'body': {
            'regimeId': f['regime_id'], 'geometry': None, 'validPeriod': {'start': p['a'], 'end': p['b']}, 'layerStatus': f['layer'],
            'geometrySourceId': src, 'geometryLocator': loc, 'geometryLicense': lic, 'attribution': attr, 'startEventId': None, 'endEventId': None,
            'ohmRelationId': rid, 'ohmVersion': ver, 'ohmFetchedAt': fetched, 'ohmStartRaw': sraw, 'ohmEndRaw': eraw,
            'provenance': {'copiedFromRecord': f['id'] if c['kind'] == 'copy' else None, 'baseRecord': f['id'], 'subtractedOverlaps': sorted(p['others']) or None, 'writtenKm2': p['rkm'],
                'coastline': '01a18e71-c977-7a2c-afe3-cb56ea3ec9fa', 'decision': 'Tai 2026-11-04 00:55／01:21：補 1908-06～10 全球缺口；採信 OHM；與既有疆界重疊處不覆蓋', 'trialWindow': '1908-01-01～1908-10-05'},
            'note': {'zh-Hant': zh, 'en': f'Fills the 1908-01-01 to {c["e"]} gap using the same OHM relation as the following record.' if c['kind'] == 'copy' else 'Pre-1908-10-06 OHM boundary for the 1908 gap.'}}})
json.dump({'type': 'FeatureCollection', 'features': derived}, open('derived.geojson', 'w'), separators=(',', ':'))
json.dump(dict(report=report, skipped=SKIP), open('report.json', 'w'), ensure_ascii=False, indent=1)
print('sovereignty', j); [print(r) for r in report]
