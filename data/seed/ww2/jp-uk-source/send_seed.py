#!/usr/bin/env python3
"""依序送出 requests/*.json（日英開戰事件補正式出處；DRAFT，待 Tai 檢查）。

預設只做 dry-run：列出要送的請求，不連 API。
**這批只寫入本機開發／測試資料庫**（worldline-borders-dev，API 127.0.0.1:5052），不要送到 appdb_ww2（5051）。
前置 id（REGIME_JP、REGIME_UK、EV_JP_SURRENDER）用 --prior 帶入 borders-dev／borders-asia-1 的 id 表。
API key 從 --env 指定的檔案（WORLDLINE_API_KEY）安靜讀取，不會印出。
用法：python3 send_seed.py [--send] --base http://127.0.0.1:5052 --env <開發用 env 檔> --prior <id 表> --ids <本批 id 表>
"""
import argparse, glob, json, os, re, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--send', action='store_true', help='真的送出（預設 dry-run）')
ap.add_argument('--base', required=True)
ap.add_argument('--env', default=os.path.join(HERE, '../../../../.env'))
ap.add_argument('--prior', action='append', default=[])
ap.add_argument('--ids', default=os.path.join(HERE, 'sent-ids.json'))
a = ap.parse_args()
if a.send and a.base.rstrip('/').endswith(':5051'):
    sys.exit('拒絕：5051 是正式 appdb_ww2 的 API；這批只寫入開發／測試資料庫。')

def api_key():
    for line in open(a.env, encoding='utf-8'):
        if line.startswith('WORLDLINE_API_KEY='):
            return line.split('=', 1)[1].strip()
    sys.exit('找不到 WORLDLINE_API_KEY')

prior = {}
for p in a.prior:
    if os.path.exists(p): prior.update(json.load(open(p, encoding='utf-8')))
mine = json.load(open(a.ids, encoding='utf-8')) if os.path.exists(a.ids) else {}
ids, key = {**prior, **mine}, (api_key() if a.send else None)
for path in sorted(glob.glob(os.path.join(HERE, 'requests', '*.json'))):
    req = json.load(open(path, encoding='utf-8'))
    name, ph, meta = os.path.basename(path), req['_placeholder'], req.get('_meta', {})
    if ph in mine:
        print(f'SKIP {name}（已寫入：{ph}）'); continue
    if meta.get('priorPlaceholder') and ph in prior:
        print(f'SKIP {name}（前置表已有：{ph}）'); continue
    raw, post = json.dumps(req['body'], ensure_ascii=False), req['_post']
    missing = [m for m in re.findall(r'\{\{(\w+)\}\}', raw + post) if m not in ids]
    if missing: print(f'   （缺少前置 id：{missing}）')
    if a.send and missing: sys.exit(f'{name} 缺少前置 id：{missing}')
    for k, v in ids.items():
        if v is None: continue
        raw = raw.replace('{{%s}}' % k, v); post = post.replace('{{%s}}' % k, v)
    print(f"POST {post}  ← {name}  （→ {ph}）")
    if not a.send: continue
    r = urllib.request.Request(a.base + post, data=raw.encode(), method='POST',
                               headers={'Content-Type': 'application/json', 'X-API-Key': key})
    try:
        data = json.load(urllib.request.urlopen(r))['data']
    except urllib.error.HTTPError as e:
        sys.exit(f'失敗 {e.code}：{e.read().decode()[:500]}')
    mine[ph] = ids[ph] = data.get('id') if isinstance(data, dict) else None
    json.dump(mine, open(a.ids, 'w'), indent=2)
    print('   id =', ids[ph])
if not a.send:
    print('\n（dry-run，未送出。）')
