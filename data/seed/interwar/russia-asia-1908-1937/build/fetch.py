import json, time, urllib.request, urllib.parse, datetime, os, sys
IDS = [int(x) for x in sys.argv[1:]]
for rid in IDS:
    fn = f'raw/r{rid}.json'
    if not os.path.exists(fn):
        q = f'[out:json][timeout:600];relation({rid});out meta geom;way(r);out tags;'
        for attempt in range(4):
            try:
                data = urllib.request.urlopen(urllib.request.Request('https://overpass-api.openhistoricalmap.org/api/interpreter', data=('data='+urllib.parse.quote(q)).encode(), headers={'User-Agent':'world-line-research/0.1 (borders trial)','Content-Type':'application/x-www-form-urlencoded'}), timeout=700).read()
                json.loads(data); break
            except Exception as e:
                print('retry', rid, e, flush=True); time.sleep(10)
        open(fn, 'wb').write(data)
        open(fn + '.fetched', 'w').write(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        time.sleep(1.5)
    d = json.load(open(fn))
    rel = [x for x in d['elements'] if x['type'] == 'relation'][0]
    t=rel['tags']
    print(rid, 'v%d'%rel['version'], t.get('name:en', t.get('name')), t.get('start_date'), t.get('end_date'), t.get('admin_level'), len(rel['members']), flush=True)
