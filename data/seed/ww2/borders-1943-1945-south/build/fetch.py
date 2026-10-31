import json, time, urllib.request, urllib.parse, datetime, os, sys
IDS = [2794960, 2956707, 2956734, 2794959, 2795081, 2794958, 2794957, 2961564, 2800536, 2920370, 2800553, 2878108, 2855621, 2747830, 2923084, 2920399, 2920397, 2848877, 2878067, 2877966, 2696300, 2696301, 2748552, 2692857, 2851793, 2855285, 2692766, 2956943, 2692839]
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
