#!/usr/bin/env python3
"""依序送出本目錄 requests/*.json（OHM admin_level=2 國界補缺批次；Tai 2026-11-04 00:40／00:53／00:55 決定政權用 OHM 名＋wikidata、採信 OHM 起訖日、與既有疆界重疊處不覆蓋）。
預設只做 dry-run：列出要送的請求並檢查前置 id、期間、幾何，不連 API。
**只寫入本機開發資料庫**（worldline-borders-dev，API 127.0.0.1:5052）；拒絕 5051（正式 appdb_ww2）。
`_geometryFrom`：送出時才從 derived.geojson（key＝placeholder）讀入幾何。API key 從 --env 檔安靜讀取，不印出。
用法：python3 send_seed.py [--send] --base http://127.0.0.1:5052 --env <開發用 env 檔> --ids <本批 id 表>
"""
import argparse, glob, json, os, re, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--send', action='store_true', help='真的送出（預設 dry-run）')
ap.add_argument('--base', required=True)
ap.add_argument('--env', default=os.path.join(HERE, '../../../.env'))
ap.add_argument('--ids', default=os.path.join(HERE, 'sent-ids.json'))
a = ap.parse_args()
if not re.search(r'://(127\.0\.0\.1|localhost):5052/?$', a.base):
    sys.exit('拒絕：這批只寫入開發 API 127.0.0.1:5052。')

def api_key():
    for line in open(a.env, encoding='utf-8'):
        if line.startswith('WORLDLINE_API_KEY='):
            return line.split('=', 1)[1].strip()
    sys.exit('找不到 WORLDLINE_API_KEY')

mine = json.load(open(a.ids, encoding='utf-8')) if os.path.exists(a.ids) else {}
ids, key = dict(mine), (api_key() if a.send else None)
geoms = {f['id']: f['geometry'] for f in json.load(open(os.path.join(HERE, 'derived.geojson')))['features']}
n = {'POST': 0, 'SKIP': 0}
for path in sorted(glob.glob(os.path.join(HERE, 'requests', '*.json'))):
    req = json.load(open(path, encoding='utf-8'))
    name, ph = os.path.basename(path), req['_placeholder']
    if ph in mine:
        n['SKIP'] += 1; print(f'SKIP {name}（已寫入：{ph}）'); continue
    body = req['body']
    if req.get('_geometryFrom'):
        g = geoms.get(req['_geometryFrom'])
        if not g or not g.get('coordinates'): sys.exit(f'{name} 沒有幾何')
        body['geometry'] = g
        vp = body['validPeriod']
        if not (vp['start'] < vp['end']): sys.exit(f'{name} 期間無效 {vp}')
    raw, post = json.dumps(body, ensure_ascii=False), req['_post']
    missing = sorted(set(m for m in re.findall(r'\{\{(\w+)\}\}', raw + post) if m not in ids))
    if a.send and missing: sys.exit(f'{name} 缺少前置 id：{missing}')
    for k, v in ids.items():
        if v: raw = raw.replace('{{%s}}' % k, v); post = post.replace('{{%s}}' % k, v)
    n['POST'] += 1
    print(f"POST {post}  ← {name}  （→ {ph}）" + (f"  前置（本批先送）：{missing}" if missing and not a.send else ''))
    if not a.send: continue
    r = urllib.request.Request(a.base.rstrip('/') + post, data=raw.encode(), method='POST', headers={'Content-Type': 'application/json', 'X-API-Key': key})
    try:
        data = json.load(urllib.request.urlopen(r, timeout=300))['data']
    except urllib.error.HTTPError as e:
        sys.exit(f'失敗 {e.code}：{e.read().decode()[:800]}')
    mine[ph] = ids[ph] = data.get('id') if isinstance(data, dict) else None
    json.dump(mine, open(a.ids, 'w'), indent=2)
    print('   id =', ids[ph])
print(f"\n{'送出' if a.send else 'dry-run（未送出）'}：POST {n['POST']}，SKIP {n['SKIP']}")
