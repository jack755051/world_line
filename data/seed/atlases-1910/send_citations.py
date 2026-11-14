#!/usr/bin/env python3
"""把 citations.json（國界本身的引文）送進開發 API。預設 dry-run；只寫 127.0.0.1:5052。
每筆以「政權代號＋日期」找到當天有效的主權紀錄（GET /sovereignty?date=），來源代號對到 sent-ids.json（先跑 send_seed.py）。
已存在的引文（同來源、同引用位置）API 回 409，視為已送過。API key 從 --env 檔安靜讀取，不印出。
用法：python3 send_citations.py [--send] --base http://127.0.0.1:5052 --env <開發用 env 檔>
"""
import argparse, json, os, re, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--send', action='store_true'); ap.add_argument('--base', required=True); ap.add_argument('--env', required=True)
a = ap.parse_args()
if not re.search(r'://(127\.0\.0\.1|localhost):5052/?$', a.base): sys.exit('拒絕：這批只寫入開發 API 127.0.0.1:5052。')
base = a.base.rstrip('/')
ids = json.load(open(os.path.join(HERE, 'sent-ids.json'), encoding='utf-8'))
cites = json.load(open(os.path.join(HERE, 'citations.json'), encoding='utf-8'))


def api_key():
    for line in open(os.path.expanduser(a.env), encoding='utf-8'):
        line = line.strip()
        if line.startswith('export '): line = line[7:]
        if line.startswith('WORLDLINE_API_KEY='): return line.split('=', 1)[1].strip().strip('"').strip("'")
    sys.exit('找不到 WORLDLINE_API_KEY')


by_date = {}
def record_id(slug, day):
    if day not in by_date:
        with urllib.request.urlopen(f'{base}/api/v1/sovereignty?date={day}') as r:
            fs = json.load(r)['data']['featureCollection']['features']
        m = {}
        for f in fs: m.setdefault(f['properties']['regimeSlug'], []).append(f['properties']['recordId'])
        by_date[day] = m
    got = by_date[day].get(slug, [])
    if len(got) != 1: sys.exit(f'{slug} 在 {day} 有 {len(got)} 筆主權紀錄，無法唯一對應')
    return got[0]


key = api_key() if a.send else None; n = {'POST': 0, 'SKIP': 0, 'DRY': 0}
for c in cites:
    rid = record_id(c['regimeSlug'], c['onDate'])
    body = {'sourceId': ids[c['source']], 'locator': c['locator'], 'evidenceNote': c['evidenceNote'], 'grade': c['grade'], 'gradeBasis': c['gradeBasis']}
    if not a.send: n['DRY'] += 1; print(f"DRY  {c['regimeSlug']} → {rid}"); continue
    req = urllib.request.Request(f'{base}/api/v1/sovereignty-records/{rid}/citations', data=json.dumps(body).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'X-API-Key': key})
    try:
        with urllib.request.urlopen(req): n['POST'] += 1; print(f"POST {c['regimeSlug']}")
    except urllib.error.HTTPError as e:
        if e.code == 409: n['SKIP'] += 1; print(f"SKIP {c['regimeSlug']}（已存在）")
        else: sys.exit(f"{c['regimeSlug']} 失敗：{e.code} {e.read().decode()[:300]}")
print(n)
