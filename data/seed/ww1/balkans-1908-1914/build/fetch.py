import json, time, urllib.request, urllib.parse, datetime, os, sys
IDS = [2866014,2807008,2739874,2692361,2746402,2797729,2692586,2801185,2848136,2869935,2866012,2866016,2866017,2690947,2692425,2692855,2828270,2693293,
 2803190,2830316,2690837,2696424,2828299,2692556,2692585,2739656,2958264,2959467,2692219,2693260,2692716,2746681,2883430,2746467,2748545,2693418,2692537,
 2746682,2849728,2807009,2855613,2692715,2917211,2849760,2851294,2853735,2860486,2860487,2692524,2798802,2742283,2746680,2828388,2692703,2696520,2860428,2860424,2964463,2696816,2848135]
os.makedirs('raw', exist_ok=True)
for rid in IDS:
    fn = f'raw/r{rid}.json'
    if not os.path.exists(fn):
        q = f'[out:json][timeout:600];relation({rid});out meta geom;way(r);out tags;'
        for attempt in range(3):
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
    print(rid, rel['version'], rel['tags'].get('name:en', rel['tags'].get('name')), rel['tags'].get('start_date'), rel['tags'].get('end_date'), flush=True)
