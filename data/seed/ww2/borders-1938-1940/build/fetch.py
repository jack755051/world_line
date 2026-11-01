import json, time, urllib.request, urllib.parse, datetime, os, sys
sel = json.load(open('sel.json'))
EXCLUDE_NAMES = {'Emirate of Transjordan','Hashemite Kingdom of Iraq','Hatay State','Iran','Italian Libya','Lebanese Republic',
 'Palestine Mandate','Syrian Republic','French protectorate in Morocco','French protectorate of Tunisia','Tangier International Zone',
 'British Cyprus','German Occupation','Boundary  Finland-USSR 1917-1940, 1944','Граница СССР-Финляндия'}
os.makedirs('raw', exist_ok=True)
man = []
for e in sel:
    t = e['tags']; name = t.get('name:en', t.get('name'))
    if name in EXCLUDE_NAMES: continue
    rid = e['id']
    fn = f'raw/r{rid}.json'
    if not os.path.exists(fn):
        q = f'[out:json][timeout:600];relation({rid});out meta geom;way(r);out tags;'
        for attempt in range(3):
            try:
                data = urllib.request.urlopen(urllib.request.Request('https://overpass-api.openhistoricalmap.org/api/interpreter', data=('data='+urllib.parse.quote(q)).encode(), headers={'User-Agent':'world-line-research/0.1 (borders trial)','Content-Type':'application/x-www-form-urlencoded'}), timeout=700).read()
                break
            except Exception as ex:
                print('retry', rid, ex, file=sys.stderr); time.sleep(5)
        open(fn, 'wb').write(data)
        fetched = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        open(fn + '.fetched', 'w').write(fetched)
    d = json.load(open(fn))
    rel = [x for x in d['elements'] if x['type'] == 'relation'][0]
    print(rid, rel['version'], name, len(rel['members']), d['osm3s']['timestamp_osm_base'], flush=True)
