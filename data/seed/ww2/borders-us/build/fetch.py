import json, time, urllib.request, urllib.parse, datetime, os
IDS = [2874803, 2693746, 2693751, 2696414, 2854023, 2854024, 2873302, 2943772, 2889834]
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
