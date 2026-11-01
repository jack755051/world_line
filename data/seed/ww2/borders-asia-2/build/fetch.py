import json, time, urllib.request, urllib.parse, datetime, os
IDS = [2694575, 2694574, 2694460, 2848277, 2848458, 2848476, 2848479, 2848477, 2848480, 2848478, 2801989, 2961557, 2848255, 2848254, 2961562, 2801016, 2864434,
       2745674, 2948947, 2948946, 2961509, 2745895, 2889834, 2889833, 2889832, 2889831, 2889933]
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
