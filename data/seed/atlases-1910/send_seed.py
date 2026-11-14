#!/usr/bin/env python3
"""依序送出 requests/*.json（1910 年前後的地圖集來源）。預設 dry-run；只寫入本機開發 API 127.0.0.1:5052，拒絕其他目標。
API key 從 --env 檔安靜讀取，不印出。已送過的（sent-ids.json 有紀錄）會略過。
用法：python3 send_seed.py [--send] --base http://127.0.0.1:5052 --env <開發用 env 檔>
"""
import argparse, glob, json, os, re, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--send', action='store_true'); ap.add_argument('--base', required=True); ap.add_argument('--env', required=True)
a = ap.parse_args()
if not re.search(r'://(127\.0\.0\.1|localhost):5052/?$', a.base): sys.exit('拒絕：這批只寫入開發 API 127.0.0.1:5052。')
IDS = os.path.join(HERE, 'sent-ids.json')
ids = json.load(open(IDS, encoding='utf-8')) if os.path.exists(IDS) else {}


def api_key():
    for line in open(os.path.expanduser(a.env), encoding='utf-8'):
        line = line.strip()
        if line.startswith('export '): line = line[7:]
        if line.startswith('WORLDLINE_API_KEY='): return line.split('=', 1)[1].strip().strip('"').strip("'")
    sys.exit('找不到 WORLDLINE_API_KEY')


key = api_key() if a.send else None
for path in sorted(glob.glob(os.path.join(HERE, 'requests', '*.json'))):
    req = json.load(open(path, encoding='utf-8')); ph = req['_placeholder']; name = os.path.basename(path)
    if ph in ids: print(f'SKIP {name}（已寫入）'); continue
    if not a.send: print(f'DRY  {name} → POST {req["_post"]}'); continue
    r = urllib.request.Request(a.base.rstrip('/') + req['_post'], data=json.dumps(req['body']).encode(), method='POST',
                               headers={'Content-Type': 'application/json', 'X-API-Key': key})
    try:
        with urllib.request.urlopen(r) as resp: ids[ph] = json.load(resp)['data']['id']; print(f'POST {name} → {ids[ph]}')
    except urllib.error.HTTPError as e:
        sys.exit(f'{name} 失敗：{e.code} {e.read().decode()[:300]}')
    json.dump(ids, open(IDS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
