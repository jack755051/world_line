#!/usr/bin/env python3
"""依序送出 requests/<子批>/*.json 到開發 API（預設 dry-run，不連 API）。
- 一般請求：body 原樣（{{PLACEHOLDER}} 以前置 id 表與本批 id 表代換；"_geometryFrom" 從 derived geojson 讀幾何）。
- "_readd"：先撤後增的重送。送出（或 dry-run）時在開發庫唯讀查詢 base 紀錄的欄位，幾何取 geomFrom 紀錄，
  有 "union" 就用 PostGIS ST_Union 合併補縫多邊形；body 內的欄位覆蓋 base；"@<id>.startEventId" 取該紀錄的事件 id；
  noteAppend 加在原註記後。dry-run 也會做同樣查詢並檢查與其他政權同期紀錄的重疊（扣掉本子批要撤回的紀錄）。
- 拒絕 5051（正式 appdb_ww2）；API key 從 --env 安靜讀取，不印出。每筆成功即寫入 --ids，重跑會跳過已送的。
"""
import argparse, glob, json, os, re, subprocess, sys, urllib.request, urllib.error
ap = argparse.ArgumentParser()
ap.add_argument('--dir', required=True); ap.add_argument('--send', action='store_true')
ap.add_argument('--base', required=True); ap.add_argument('--env', required=True)
ap.add_argument('--prior', action='append', default=[]); ap.add_argument('--ids', required=True)
ap.add_argument('--derived', default=None)
a = ap.parse_args()
if a.base.rstrip('/').endswith(':5051'): sys.exit('拒絕：5051 是正式 appdb_ww2 的 API。')
DB = ['docker', 'exec', '-i', 'worldline-borders-dev-db', 'psql', '-U', 'worldline', '-d', 'worldline_borders_dev', '-At', '-v', 'ON_ERROR_STOP=1']
def sql(q):
    r = subprocess.run(DB, input=q, capture_output=True, text=True)
    if r.returncode: sys.exit('SQL 失敗：' + r.stderr[:800])
    return r.stdout.strip()
def lit(s): return "'" + s.replace("'", "''") + "'"
def api_key():
    for line in open(a.env, encoding='utf-8'):
        if line.startswith('WORLDLINE_API_KEY='): return line.split('=', 1)[1].strip()
    sys.exit('找不到 WORLDLINE_API_KEY')
prior = {}
for p in a.prior:
    if os.path.exists(p): prior.update(json.load(open(p, encoding='utf-8')))
mine = json.load(open(a.ids, encoding='utf-8')) if os.path.exists(a.ids) else {}
ids, key = {**prior, **mine}, (api_key() if a.send else None)
geoms = {f['id']: f['geometry'] for f in json.load(open(a.derived))['features']} if a.derived else {}
files = sorted(glob.glob(os.path.join(a.dir, '*.json')))
retracting = []
for p in files:
    r = json.load(open(p, encoding='utf-8'))
    m = re.search(r'/sovereignty-records/([0-9a-f-]{36})/retraction', r['_post'])
    if m: retracting.append(m.group(1))
def subst(s):
    for k, v in ids.items():
        if v: s = s.replace('{{%s}}' % k, v)
    return s
def readd_body(rd, override):
    u = rd.get('union'); sb = rd.get('subtract')
    ug = f"ST_SetSRID(ST_GeomFromGeoJSON({lit(json.dumps(u))}),4326)" if u else None
    sg = f"ST_SetSRID(ST_GeomFromGeoJSON({lit(json.dumps(sb))}),4326)" if sb else None
    gexpr = "g.geom"
    if ug: gexpr = f"ST_Union({gexpr}, {ug})"
    if sg: gexpr = f"ST_Difference({gexpr}, {sg})"
    if ug or sg: gexpr = f"ST_Multi(ST_CollectionExtract(ST_MakeValid({gexpr}),3))"
    q = f"""select json_build_object('regimeId',s.regime_id,'geometry',ST_AsGeoJSON({gexpr})::json,
      'validPeriod',json_build_object('start',lower(s.valid_period),'end',upper(s.valid_period)),'layerStatus',s.layer_status,
      'geometrySourceId',s.geometry_source_id,'geometryLocator',s.geometry_locator,'geometryLicense',s.geometry_license,'attribution',s.attribution,
      'startEventId',s.start_event_id,'endEventId',s.end_event_id,'ohmRelationId',s.ohm_relation_id,'ohmVersion',s.ohm_version,
      'ohmFetchedAt',to_char(s.ohm_fetched_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS"Z"'),'ohmStartRaw',s.ohm_start_raw,'ohmEndRaw',s.ohm_end_raw,
      'provenance',s.provenance,'note',s.note,'_oldArea',ST_Area(s.geom),'_newArea',ST_Area({gexpr}),'_retracted',s.retracted_at is not null)
      from sovereignty_records s, sovereignty_records g where s.id={lit(rd['base'])}::uuid and g.id={lit(rd['geomFrom'])}::uuid"""
    b = json.loads(sql(q))
    for k, v in override.items():
        if k == 'geometryLocator' and isinstance(v, str) and v.startswith('@locator'):
            b[k] = b[k] + v[len('@locator'):]; continue
        if isinstance(v, str) and v.startswith('@'):
            rid, fld = v[1:].split('.')
            col = {'startEventId': 'start_event_id', 'endEventId': 'end_event_id'}[fld]
            v = sql(f"select {col} from sovereignty_records where id={lit(rid)}::uuid") or None
        b[k] = v
    na = rd.get('noteAppend')
    if na:
        old = b.get('note') or {}
        b['note'] = {lang: ((old.get(lang) or '') + ('　' if old.get(lang) else '') + '【接點修補 2026-11-01】' + na[lang]).strip() for lang in ('zh-Hant', 'en')}
    return b
def overlap_check(body):
    g = lit(json.dumps(body['geometry']))
    vp = body['validPeriod']; hi = vp['end'] or 'infinity'
    ex = ','.join(lit(x) + '::uuid' for x in retracting) or 'null'
    q = f"""select coalesce(string_agg(r.slug||'['||lower(s.valid_period)||']:'||round(ST_Area(ST_Intersection(s.geom,x.g))::numeric,4),', '),'') from
      (select ST_SetSRID(ST_GeomFromGeoJSON({g}),4326) g) x, sovereignty_records s join regimes r on r.id=s.regime_id
      where s.retracted_at is null and s.id not in ({ex}) and s.regime_id<>{lit(body['regimeId'])}::uuid and s.valid_period && daterange({lit(vp['start'])},{lit(hi)})
      and ST_Intersects(s.geom,x.g) and ST_Area(ST_Intersection(s.geom,x.g))>0.002"""
    return sql(q)
for path in files:
    req = json.load(open(path, encoding='utf-8')); name, ph = os.path.basename(path), req['_placeholder']
    if ph in mine: print(f'SKIP {name}（已寫入：{ph}）'); continue
    post = subst(req['_post']); body = req.get('body', {})
    if req.get('_readd'):
        ob = json.loads(subst(json.dumps(body, ensure_ascii=False)))
        miss = sorted(set(re.findall(r'\{\{(\w+)\}\}', json.dumps(ob))))
        if miss:
            if a.send: sys.exit(f'{name} 缺少前置 id：{miss}')
            print(f'   （dry-run）尚無前置 id：{miss}'); print(f'POST {post}  ← {name}（→ {ph}）（重送；前置 id 未齊，略過幾何查詢）'); continue
        body = readd_body(req['_readd'], ob)
        info = f"面積 {body.pop('_oldArea'):.4f}→{body.pop('_newArea'):.4f}；base 已撤回={body.pop('_retracted')}"
        ov = overlap_check(body)
        print(f"POST {post}  ← {name}（→ {ph}）{body['validPeriod']}  {info}" + (f"  ⚠重疊：{ov}" if ov else ''))
    else:
        if 'geometry' in body and req.get('_geometryFrom'): body['geometry'] = geoms[req['_geometryFrom']]
        raw = subst(json.dumps(body, ensure_ascii=False)); body = json.loads(raw)
        missing = sorted(set(re.findall(r'\{\{(\w+)\}\}', raw + post)))
        if missing:
            if a.send: sys.exit(f'{name} 缺少前置 id：{missing}')
            print(f'   （dry-run）尚無前置 id：{missing}')
        extra = ''
        if body.get('geometry') and body.get('regimeId') and body.get('validPeriod') and not missing:
            ov = overlap_check(body); extra = f"  ⚠重疊：{ov}" if ov else ''
        print(f"POST {post}  ← {name}（→ {ph}）{extra}")
    if not a.send: continue
    rq = urllib.request.Request(a.base + post, data=json.dumps(body, ensure_ascii=False).encode(), method='POST',
                                headers={'Content-Type': 'application/json', 'X-API-Key': key})
    try:
        data = json.load(urllib.request.urlopen(rq))['data']
    except urllib.error.HTTPError as e:
        sys.exit(f'失敗 {e.code}：{e.read().decode()[:800]}')
    m = re.search(r'/([0-9a-f-]{36})/retraction', post)
    mine[ph] = ids[ph] = (data.get('id') if isinstance(data, dict) and data.get('id') else (m.group(1) if m else None))
    json.dump(mine, open(a.ids, 'w'), indent=2)
    print('   id =', ids[ph])
if not a.send: print('\n（dry-run，未送出。）')
