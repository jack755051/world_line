#!/usr/bin/env python3
"""tiles 模式的 overlay（ARCHITECTURE.md §9 遷移步驟 5）：換日期不向 API 要資料。

從第 1 層 API（開發庫 5442 後面的 5052）依變動區間各取一次，輸出：
- out/overlay-control.geojsonseq、out/overlay-gaps.geojsonseq：控制區、控制資料缺的幾何（每個 versionId／gapId 一筆），
  由 build-overlay.sh 用 tippecanoe 做成 overlay-v{hash}.pmtiles（圖層 control、gaps）。
- out/overlay-v{hash}.json：各區間的中繼資料（屬性、戰區狀態、涵蓋備註；每筆只留最大多邊形與全幾何外框，
  讓 controlLabels／點選聚焦跟 geojson 模式算出一樣的結果），out/overlay.json 連到它。
區間外（範圍以外的日期）前端退回 API。

用法：python3 tools/tiles/build-overlay.py [API_BASE] [--sections=control,conflicts,capitals,leaders]
"""
import hashlib, json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
args = [a for a in sys.argv[1:] if not a.startswith('--')]
API = (args[0] if args else os.environ.get('WL_API', 'http://127.0.0.1:5052/api/v1')).rstrip('/')
SECTIONS = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--sections=')), 'control,conflicts,capitals,leaders').split(',')
START, END = '1908-10-05', '1945-12-31'  # 時間軸範圍（含）；之外退回 API


def get(path):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(API + path, timeout=120) as r:
                return json.loads(r.read())['data']
        except Exception:
            if attempt == 3:
                raise
            time.sleep(1 + attempt)


def ring_area(r):
    a = 0.0
    for i in range(len(r) - 1):
        a += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1]
    return abs(a) / 2


def polys_of(g):
    if not g:
        return []
    return [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates'] if g['type'] == 'MultiPolygon' else []


def slim(g):
    """只留最大多邊形（與前端 controlLabels 同一個選法：外環面積最大，同面積取先出現的）＋全幾何外框。"""
    ps = polys_of(g)
    if not ps:
        return g, None
    big = ps[0]
    for p in ps[1:]:
        if ring_area(p[0]) > ring_area(big[0]):
            big = p
    xs = [c[0] for p in ps for c in p[0]]
    ys = [c[1] for p in ps for c in p[0]]
    return {'type': 'Polygon', 'coordinates': big}, [min(xs), min(ys), max(xs), max(ys)]


def canon(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def in_range(points):
    return sorted(set(p for p in points if START <= p <= END) | {START})


def days(a, b):
    d, e = date.fromisoformat(a), date.fromisoformat(b)
    while d <= e:
        yield d.isoformat()
        d += timedelta(days=1)


def pmap(fn, items, n=8):
    with ThreadPoolExecutor(n) as ex:
        return list(ex.map(fn, items))


cp = get('/timeline/change-points')
overlay = {'range': [START, END]}
seq = {}


def hkey(o):
    """內容雜湊（同一筆紀錄在不同區間屬性可能不同，例如陣營換了一段）：區間只記雜湊，內容只存一份。"""
    return hashlib.sha256(canon(o).encode()).hexdigest()[:16]


def build_control():
    pts = in_range(cp['controlPoints'] or [])
    feats, shapes, notes, note_shapes, geoms, gaps, intervals = {}, {}, {}, {}, {}, {}, []
    for p, dto in zip(pts, pmap(lambda p: get(f'/control?date={p}'), pts)):
        ids = []
        for f in dto['featureCollection']['features']:
            vid = f['properties']['versionId']
            g = canon(f['geometry'])
            if vid in geoms and geoms[vid][0] != g:
                raise SystemExit(f'versionId {vid} 在不同區間幾何不同（{p}）')
            if vid not in geoms:
                big, bbox = slim(f['geometry'])
                shapes[vid] = {'largest': big, 'bbox': bbox}
            geoms[vid] = (g, f['geometry'])
            rest = {k: v for k, v in f.items() if k != 'geometry'}
            k = hkey(rest)
            feats[k] = rest
            ids.append(k)
        nids = []
        for n in dto.get('coverageNotes') or []:
            g = canon(n.get('geometry'))
            if n['id'] in gaps and gaps[n['id']][0] != g:
                raise SystemExit(f'coverage note {n["id"]} 幾何不同（{p}）')
            if n['id'] not in gaps:
                big, bbox = slim(n.get('geometry'))
                note_shapes[n['id']] = {'largest': big, 'bbox': bbox}
            gaps[n['id']] = (g, n.get('geometry'))
            rest = {k: v for k, v in n.items() if k != 'geometry'}
            k = hkey(rest)
            notes[k] = rest
            nids.append(k)
        intervals.append({'start': p, 'features': ids, 'theaters': dto.get('theaters') or [], 'notes': nids})
    overlay['control'] = {'points': pts, 'intervals': intervals, 'features': feats, 'shapes': shapes, 'notes': notes, 'noteShapes': note_shapes}
    seq['control'] = [{'type': 'Feature', 'geometry': g, 'properties': {'versionId': k}} for k, (_, g) in sorted(geoms.items())]
    seq['gaps'] = [{'type': 'Feature', 'geometry': g, 'properties': {'gapId': k}} for k, (_, g) in sorted(gaps.items()) if g]
    print(f'control：{len(pts)} 區間，{len(geoms)} 個 version（{len(feats)} 種屬性），{len(gaps)} 個涵蓋備註', file=sys.stderr)


def build_points(kind, pts_src, list_of, path):
    pts = in_range(pts_src)
    recs, intervals = {}, []
    for p, dto in zip(pts, pmap(lambda p: get(path(p)), pts)):
        ids = []
        for f in list_of(dto):
            k = hkey(f)
            recs[k] = f
            ids.append(k)
        intervals.append({'start': p, 'ids': ids})
    overlay[kind] = {'points': pts, 'intervals': intervals, 'records': recs}
    print(f'{kind}：{len(pts)} 區間，{len(recs)} 筆', file=sys.stderr)


def build_daily(kind):
    """首都／領導人：API 依日期回傳，沒有變動點 → 逐日掃一遍，相同內容的連續日期併成區間。"""
    ds = list(days(START, END))
    recs, intervals, prev = {}, [], None
    for d, dto in zip(ds, pmap(lambda d: get(f'/{kind}?date={d}'), ds, 12)):
        ids = []
        for f in dto['features']:
            k = hkey(f)
            recs[k] = f
            ids.append(k)
        if ids != prev:
            intervals.append({'start': d, 'ids': ids})
            prev = ids
    overlay[kind] = {'points': [i['start'] for i in intervals], 'intervals': intervals, 'records': recs}
    print(f'{kind}：{len(ds)} 天 → {len(intervals)} 區間，{len(recs)} 筆', file=sys.stderr)


t0 = time.time()
for s in SECTIONS:
    if s == 'control':
        build_control()
    elif s == 'conflicts':
        build_points('conflicts', cp['points'], lambda d: d['featureCollection']['features'], lambda p: f'/conflicts?date={p}')
    else:
        build_daily(s)
os.makedirs(OUT, exist_ok=True)
for name, feats in seq.items():
    with open(os.path.join(OUT, f'overlay-{name}.geojsonseq'), 'w') as fh:
        for f in feats:
            fh.write(json.dumps(f, separators=(',', ':')) + '\n')
h = hashlib.sha256(canon(overlay).encode()).hexdigest()[:12]
overlay['version'] = h
fn = f'overlay-v{h}.json'
with open(os.path.join(OUT, fn), 'w') as fh:
    fh.write(canon(overlay))
link = os.path.join(OUT, 'overlay.json')
if os.path.lexists(link):
    os.remove(link)
os.symlink(fn, link)
print(json.dumps({'file': fn, 'bytes': os.path.getsize(os.path.join(OUT, fn)), 'seconds': round(time.time() - t0)}))
