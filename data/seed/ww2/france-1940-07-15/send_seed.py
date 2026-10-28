#!/usr/bin/env python3
"""依序送出 requests/*.json（M0 第一批真實資料：1940 法國，v2）。

預設只做 dry-run：列出要送的請求，不連 API。Tai 檢查通過後才加 --send。
_meta.requiresDecision = true 的請求（東北禁區兩筆）預設跳過，Tai 拍板後再加 --include-pending。
API key 從 worktree 的 .env（WORLDLINE_API_KEY）安靜讀取，不會印出。
用法：python3 send_seed.py [--send] [--include-pending] [--base http://127.0.0.1:5050] [--env ../../../../.env]
"""
import argparse, glob, json, os, re, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--send', action='store_true', help='真的送出（預設 dry-run）')
ap.add_argument('--include-pending', action='store_true', help='連同 requiresDecision 的請求一起送')
ap.add_argument('--base', default='http://127.0.0.1:5050')
ap.add_argument('--env', default=os.path.join(HERE, '../../../../.env'))
a = ap.parse_args()

def api_key():
    for line in open(a.env, encoding='utf-8'):
        if line.startswith('WORLDLINE_API_KEY='):
            return line.split('=', 1)[1].strip()
    sys.exit('找不到 WORLDLINE_API_KEY')

ids, key = {}, (api_key() if a.send else None)
for path in sorted(glob.glob(os.path.join(HERE, 'requests', '*.json'))):
    req = json.load(open(path, encoding='utf-8'))
    meta, name = req.get('_meta', {}), os.path.basename(path)
    if meta.get('requiresDecision') and not a.include_pending:
        print(f"SKIP {name}（待決：{meta.get('reason', '')}）"); continue
    raw = json.dumps(req['body'], ensure_ascii=False)
    missing = [m for m in re.findall(r'\{\{(\w+)\}\}', raw) if m not in ids]
    if a.send and missing: sys.exit(f'{name} 缺少前置 id：{missing}')
    for k, v in ids.items(): raw = raw.replace('{{%s}}' % k, v)
    print(f"POST {req['_post']}  ← {name}  （→ {req['_placeholder']}）")
    if not a.send: continue
    r = urllib.request.Request(a.base + req['_post'], data=raw.encode(), method='POST',
                               headers={'Content-Type': 'application/json', 'X-API-Key': key})
    try:
        body = json.load(urllib.request.urlopen(r))
    except urllib.error.HTTPError as e:
        sys.exit(f'失敗 {e.code}：{e.read().decode()[:500]}')
    data = body['data']
    ids[req['_placeholder']] = data.get('id') or data.get('controlRecordId')
    print('   id =', ids[req['_placeholder']])
if a.send:
    json.dump(ids, open(os.path.join(HERE, 'sent-ids.json'), 'w'), indent=2)
else:
    print('\n（dry-run，未送出。確認後加 --send。）')
