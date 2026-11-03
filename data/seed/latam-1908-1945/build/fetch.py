"""OHM Overpass：逐筆抓 relation（out meta geom＋成員線段 tags），每筆間隔 2 秒，已抓過的跳過。"""
import json, time, urllib.request, urllib.parse, datetime, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
for rid in [int(x) for x in open('ids.txt').read().split()]:
    fn = f'raw/r{rid}.json'
    if os.path.exists(fn): continue
    q = f'[out:json][timeout:600];relation({rid});out meta geom;way(r);out tags;'
    for attempt in range(4):
        try:
            data = urllib.request.urlopen(urllib.request.Request('https://overpass-api.openhistoricalmap.org/api/interpreter',
                data=('data=' + urllib.parse.quote(q)).encode(), headers={'User-Agent': 'world-line-research/0.1 (latam borders trial; low volume)', 'Content-Type': 'application/x-www-form-urlencoded'}), timeout=700).read()
            json.loads(data); break
        except Exception as e:
            print('retry', rid, e, flush=True); time.sleep(20)
    else:
        print('FAIL', rid, flush=True); continue
    open(fn, 'wb').write(data)
    open(fn + '.fetched', 'w').write(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    print(rid, len(data), flush=True)
    time.sleep(2)
print('done')
