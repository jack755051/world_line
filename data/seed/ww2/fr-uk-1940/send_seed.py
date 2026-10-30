#!/usr/bin/env python3
"""依序送出 requests/*.json（法、英政權與 1940 控制區；DRAFT，待 Tai 檢查）。

預設只做 dry-run：列出要送的請求，不連 API。Tai 同意寫入 appdb_ww2 後才加 --send。
_meta.requiresDecision = true 的請求（英國本土控制區、英法同盟候選）預設跳過，Tai 拍板後再加 --include-pending。
前置 id（SNAP_0715、SRC_LECONTE、SRC_AIN、SRC_TRF、SRC_USMA15）從 ../france-1940-07-15/sent-ids.json 讀取。
API key 從 repo 根目錄的 .env（WORLDLINE_API_KEY）安靜讀取，不會印出。
用法：python3 send_seed.py [--send] [--include-pending] [--base http://127.0.0.1:5051] [--env ../../../../.env]
"""
import argparse, glob, json, os, re, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--send', action='store_true', help='真的送出（預設 dry-run）')
ap.add_argument('--include-pending', action='store_true', help='連同 requiresDecision 的請求一起送')
ap.add_argument('--base', default='http://127.0.0.1:5051')
ap.add_argument('--env', default=os.path.join(HERE, '../../../../.env'))
ap.add_argument('--prior', action='append', help='前置 id 對照表（可重複）',
                default=None)
a = ap.parse_args()
priors = a.prior or [os.path.join(HERE, '../france-1940-07-15/sent-ids.json'), os.path.join(HERE, '../alignments/sent-ids.json')]

def api_key():
    for line in open(a.env, encoding='utf-8'):
        if line.startswith('WORLDLINE_API_KEY='):
            return line.split('=', 1)[1].strip()
    sys.exit('找不到 WORLDLINE_API_KEY')

prior = {}
for p in priors:
    if os.path.exists(p): prior.update(json.load(open(p, encoding='utf-8')))
mine_path = os.path.join(HERE, 'sent-ids.json')
mine = json.load(open(mine_path, encoding='utf-8')) if os.path.exists(mine_path) else {}
ids, key = {**prior, **mine}, (api_key() if a.send else None)
for path in sorted(glob.glob(os.path.join(HERE, 'requests', '*.json'))):
    req = json.load(open(path, encoding='utf-8'))
    name, ph, meta = os.path.basename(path), req['_placeholder'], req.get('_meta', {})
    if ph in mine:
        print(f'SKIP {name}（已寫入：{ph}）'); continue
    if meta.get('requiresDecision') and not a.include_pending:
        print(f"SKIP {name}（待決：{meta.get('reason', '')}）"); continue
    raw = json.dumps(req['body'], ensure_ascii=False)
    post = req['_post']
    missing = [m for m in re.findall(r'\{\{(\w+)\}\}', raw + post) if m not in ids]
    if a.send and missing: sys.exit(f'{name} 缺少前置 id：{missing}')
    for k, v in ids.items():
        raw = raw.replace('{{%s}}' % k, v); post = post.replace('{{%s}}' % k, v)
    print(f"POST {post}  ← {name}  （→ {ph}）")
    if not a.send: continue
    r = urllib.request.Request(a.base + post, data=raw.encode(), method='POST',
                               headers={'Content-Type': 'application/json', 'X-API-Key': key})
    try:
        body = json.load(urllib.request.urlopen(r))
    except urllib.error.HTTPError as e:
        sys.exit(f'失敗 {e.code}：{e.read().decode()[:500]}')
    data = body['data']
    mine[ph] = ids[ph] = data.get('id') or data.get('controlRecordId')
    json.dump(mine, open(mine_path, 'w'), indent=2)  # 每筆成功就記，補寫時不重複
    print('   id =', ids[ph])
if not a.send:
    print('\n（dry-run，未送出。Tai 同意後加 --send。）')
