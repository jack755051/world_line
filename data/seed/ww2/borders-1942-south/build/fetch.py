import json, time, urllib.request, urllib.parse, datetime, os, sys
IDS = [2747829, 2747832, 2692359, 2693255, 2693259, 2695478, 2692713, 2692357, 2920398, 2695479, 2695459, 2747869]  # 2693259（羅馬尼亞 1921–1940-06-28）只用來切出外涅斯特里亞；r2693259 沿用 1938–1940 批次的抓取
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
