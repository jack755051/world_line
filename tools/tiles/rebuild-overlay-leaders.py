#!/usr/bin/env python3
"""只重建 overlay 的「領導人」段（人物分頁卡片的資料），其他段（控制區、衝突、首都、樣式、政權）原樣沿用。

生平、照片補齊後，卡片要看到新生平與照片，overlay.json 的 leaders 段必須跟著更新；整份 build-overlay.py 要重掃全部圖層，
這支只逐日掃 GET /leaders（與 build-overlay.py 的 build_daily 同一演算法），寫成新的 overlay-v{hash}.json 再把 overlay.json 指過去。
舊檔不刪（可直接把連結指回去還原）。

用法：python3 tools/tiles/rebuild-overlay-leaders.py [API_BASE]（預設 http://127.0.0.1:5052/api/v1；拒絕 5051）
"""
import hashlib, json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
API = (sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:5052/api/v1').rstrip('/')
if ':5051' in API:
    sys.exit('拒絕 5051')


def get(path):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(API + path, timeout=120) as r:
                return json.loads(r.read())['data']
        except Exception:
            if attempt == 3:
                raise
            time.sleep(1 + attempt)


def canon(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def hkey(o):
    return hashlib.sha256(canon(o).encode()).hexdigest()[:16]


t0 = time.time()
link = os.path.join(OUT, 'overlay.json')
old_name = os.readlink(link)
overlay = json.load(open(link, encoding='utf-8'))
start, end = overlay['range']
d, e, ds = date.fromisoformat(start), date.fromisoformat(end), []
while d <= e:
    ds.append(d.isoformat())
    d += timedelta(days=1)
with ThreadPoolExecutor(12) as ex:
    dtos = list(ex.map(lambda x: get(f'/leaders?date={x}'), ds))
recs, intervals, prev = {}, [], None
for day, dto in zip(ds, dtos):
    ids = []
    for f in dto['features']:
        k = hkey(f)
        recs[k] = f
        ids.append(k)
    if ids != prev:
        intervals.append({'start': day, 'ids': ids})
        prev = ids
before = len(overlay['leaders']['records'])
overlay['leaders'] = {'points': [i['start'] for i in intervals], 'intervals': intervals, 'records': recs}
overlay.pop('version', None)
h = hashlib.sha256(canon(overlay).encode()).hexdigest()[:12]
overlay['version'] = h
fn = f'overlay-v{h}.json'
with open(os.path.join(OUT, fn), 'w', encoding='utf-8') as fh:
    fh.write(canon(overlay))
os.remove(link)
os.symlink(fn, link)
print(json.dumps({'old': old_name, 'file': fn, 'leaderRecordsBefore': before, 'leaderRecordsAfter': len(recs),
                  'intervals': len(intervals), 'seconds': round(time.time() - t0)}, ensure_ascii=False))
