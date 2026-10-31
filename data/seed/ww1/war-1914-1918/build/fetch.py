import json, time, urllib.request, urllib.parse, datetime, os, sys
IDS = [2692425,2692361,2851294,2851158,2869933,2852344,2850854,2957452,2959041,2959042,2696424,2866012,2828388,2797729,2869935,2692537,2692524,
 2849728,2920989,2848136,2848135,2803205,2692585,2746681,2692716,2739656,2746680,2693260,2692219,2855613,2830316,2690837,2803190,2860486,2860424,
 2866016,2866014,2866017,2860487,2690947,2917211,2696520,
 2695682,2695683,2695684,2696283,2744424,2744425,2744426,2869679,2869680,2694815,2957449,2696817,2959044,2959043,2957453,2957454,2957459,
 2698086,2698116,2698117,2891769,2694154,2747877,2747879,2884612,2951914,2951908,2945081,2945094,2945074,2945069,2945066,2945090,2696816]
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
