"""依 build/ids.txt 從 OHM Overpass 抓關係（out meta geom＋成員線段 tags），存 raw/（已有的沿用 WW1 第二批的抓取）。"""
import json, time, urllib.request, urllib.parse, datetime, os
IDS = [int(x) for x in open(os.path.join(os.path.dirname(__file__), 'ids.txt')).read().split()]
for rid in IDS:
    fn = f'raw/r{rid}.json'
    if not os.path.exists(fn):
        q = f'[out:json][timeout:600];relation({rid});out meta geom;way(r);out tags;'
        for attempt in range(4):
            try:
                data = urllib.request.urlopen(urllib.request.Request('https://overpass-api.openhistoricalmap.org/api/interpreter', data=('data='+urllib.parse.quote(q)).encode(), headers={'User-Agent':'world-line-research/0.1 (borders trial)','Content-Type':'application/x-www-form-urlencoded'}), timeout=700).read()
                json.loads(data); break
            except Exception as e:
                print('retry', rid, e, flush=True); time.sleep(15)
        open(fn, 'wb').write(data)
        open(fn + '.fetched', 'w').write(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        time.sleep(1.5)
    d = json.load(open(fn))
    rel = [x for x in d['elements'] if x['type'] == 'relation'][0]
    print(rid, rel['version'], rel['tags'].get('name:en', rel['tags'].get('name')), rel['tags'].get('start_date'), rel['tags'].get('end_date'), flush=True)
