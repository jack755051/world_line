import json, time, urllib.request, urllib.parse, datetime, os, sys
IDS = [2704717, 2692712, 2851156, 2692529, 2693267, 2693255, 2693259, 2692359]  # 2692712、2851156、2692529、2693267、2693084 沿用 borders-1942-late 的抓取；2693255、2693259、2692359 沿用 borders-1942-south
for rid in IDS:
    fn = f'raw/r{rid}.json'
    if not os.path.exists(fn):
        q = f'[out:json][timeout:600];relation({rid});out meta geom;way(r);out tags;'
        data = urllib.request.urlopen(urllib.request.Request('https://overpass-api.openhistoricalmap.org/api/interpreter', data=('data='+urllib.parse.quote(q)).encode(), headers={'User-Agent':'world-line-research/0.1 (borders trial)','Content-Type':'application/x-www-form-urlencoded'}), timeout=700).read()
        open(fn, 'wb').write(data)
        open(fn + '.fetched', 'w').write(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        time.sleep(2)
    d = json.load(open(fn))
    rel = [x for x in d['elements'] if x['type'] == 'relation'][0]
    print(rid, rel['version'], rel['tags'].get('name:en', rel['tags'].get('name')), len(rel['members']), d['osm3s']['timestamp_osm_base'], rel['tags'].get('start_date'), rel['tags'].get('end_date'), flush=True)
