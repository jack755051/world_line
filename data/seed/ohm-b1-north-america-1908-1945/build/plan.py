"""第 1 步：OHM 釘選清單＋幾何 → 候選片段 cands.csv（還沒做跨政權疊合檢查）。
規則（Tai 2026-11-04 00:40／00:53／00:55）：政權用 OHM 名＋wikidata；已有政權優先掛既有記錄；採信 OHM 起訖日；
期間裁到 [1908-01-01, 1945-10-01)；只寫該政權目前沒有有效紀錄的時段（不延長、不撤回既有紀錄）。
同政權同批多條 relation 期間重疊時，依 config.ORDER（沒有就依起日）先到先得，後者只補空檔，並列入 conflicts。
用法：plan.py <批次目錄>（讀 config.py、ohm-manifest.json、borders.geojson、../regsov.csv）"""
import csv, collections, importlib.util, json, os, re, sys
B = os.path.abspath(sys.argv[1]); HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('cfg', os.path.join(B, 'config.py')); C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
LO, HI = '1908-01-01', '1945-10-01'
man = {r['ohm_relation_id']: r for r in json.load(open(f'{B}/ohm-manifest.json'))}
geo = {f['properties']['ohm_relation_id']: f['geometry'] for f in json.load(open(f'{B}/borders.geojson'))['features']}
ex = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(HERE, '../regsov.csv'))):
    if r['s']: ex[r['slug']].append((r['s'], r['e'] or '9999-12-31'))
def norm(d, is_end):
    if d is None: return (HI if is_end else LO), 'open'
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d): return d, 'day'
    if re.fullmatch(r'\d{4}-\d{2}', d): return d + '-01', 'month'
    if re.fullmatch(r'\d{4}', d): return d + '-01-01', 'year'
    sys.exit(f'無法解析日期 {d}')
def minus(iv, taken):
    out = [iv]
    for s, e in taken:
        nxt = []
        for a, b in out:
            if e <= a or s >= b: nxt.append((a, b)); continue
            if a < s: nxt.append((a, s))
            if e < b: nxt.append((e, b))
        out = nxt
    return out
cands, skipped, conflicts, low = [], [], [], []
taken = collections.defaultdict(list)
order = getattr(C, 'ORDER', None) or sorted(man, key=lambda r: (man[r]['start_date'] or ''))
for rid in order:
    m = man[rid]
    if rid in C.DROP: skipped.append(dict(rid=rid, name=m['name'], reason=C.DROP[rid])); continue
    slug = C.MAP[m['name']]
    s, sp = norm(m['start_date'], False); e, ep = norm(m['end_date'], True)
    lo, hi = getattr(C, 'CLAMP', {}).get(slug, (LO, HI))
    a, b = max(s, lo), min(e, hi)
    if a >= b: skipped.append(dict(rid=rid, name=m['name'], reason='期間不在 1908-01-01～1945-09-30')); continue
    if rid not in geo: skipped.append(dict(rid=rid, name=m['name'], reason='裁切後沒有陸地多邊形')); continue
    prec = {k: v for k, v, d in (('start', sp, s), ('end', ep, e)) if v in ('year', 'month') and LO < d < HI}
    if prec: low.append(dict(rid=rid, name=m['name'], start_raw=m['start_date'], end_raw=m['end_date'], used=[a, b], precision=prec))
    after_ex = minus((a, b), ex[slug])
    if not after_ex: skipped.append(dict(rid=rid, name=m['name'], reason=f'整段已有既有 {slug} 有效紀錄', window=[a, b]))
    elif after_ex != [(a, b)]: skipped.append(dict(rid=rid, name=m['name'], reason=f'與既有 {slug} 有效紀錄重疊的時段不寫（只補空檔）', window=[a, b], kept=after_ex))
    pieces = [p for q in after_ex for p in minus(q, taken[slug])]
    if pieces != after_ex:
        conflicts.append(dict(rid=rid, name=m['name'], window=[a, b], kept=pieces, reason='同政權同批另一條 relation 已佔用部分期間（OHM 內部重疊）'))
    taken[slug].append((a, b))
    for k, (x, y) in enumerate(pieces):
        cands.append(dict(cid=f'{rid}_{k}', rid=rid, slug=slug, s=x, e=y, prec=prec))
with open(f'{B}/cands.csv', 'w', newline='') as f:
    w = csv.writer(f)
    for c in cands: w.writerow([c['cid'], c['slug'], c['s'], c['e'], json.dumps(geo[c['rid']], separators=(',', ':'))])
json.dump(dict(cands=cands, skipped=skipped, conflicts=conflicts, low=low), open(f'{B}/plan.json', 'w'), ensure_ascii=False, indent=1)
for c in cands: print('CAND', c['cid'], c['slug'], c['s'], c['e'])
for x in skipped: print('SKIP', x)
for x in conflicts: print('CONFLICT', x)
