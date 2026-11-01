import json, time, urllib.request, urllib.parse, datetime, os
IDS = [2848216, 2961654, 2961652, 2848313, 2848182, 2893390, 2906073, 2822863, 2961649, 2965458, 2920522, 2922714, 2905965, 2960814, 2848223, 2848485, 2905974, 2848320, 2848319, 2848318, 2848364, 2849400, 2849421, 2961066, 2961074, 2848286, 2848295, 2848294, 2848293, 2848292, 2864414, 2885873, 2801211, 2801212, 2831242, 2848197, 2694462, 2889933]
for rid in IDS:
    fn = f'raw/r{rid}.json'
    if not os.path.exists(fn):
        q = f'[out:json][timeout:600];relation({rid});out meta geom;way(r);out tags;'
        data = urllib.request.urlopen(urllib.request.Request('https://overpass-api.openhistoricalmap.org/api/interpreter', data=('data='+urllib.parse.quote(q)).encode(), headers={'User-Agent':'world-line-research/0.1 (borders trial)','Content-Type':'application/x-www-form-urlencoded'}), timeout=700).read()
        open(fn, 'wb').write(data)
        open(fn + '.fetched', 'w').write(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        time.sleep(1)
    d = json.load(open(fn))
    rel = [x for x in d['elements'] if x['type'] == 'relation'][0]
    print(rid, rel['version'], rel['tags'].get('name:en', rel['tags'].get('name')), len(rel['members']), d['osm3s']['timestamp_osm_base'], rel['tags'].get('start_date'), rel['tags'].get('end_date'), rel['tags'].get('fixme'), rel['tags'].get('source','')[:60], flush=True)
