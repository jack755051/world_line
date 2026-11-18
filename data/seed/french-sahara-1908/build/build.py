#!/usr/bin/env python3
"""法屬西非 1908–1912 補上撒哈拉尚未設治的部分。只讀開發庫，不寫任何資料。
問題：資料集的法屬西非在 1910-06-22 以前不含尼日北部（約 89 萬平方公里），在 1912-01-01 以前不含茅利塔尼亞北部與馬利北部（約 51 萬），
      這些地方在那段期間沒有任何紀錄。1910 年前後的兩套地圖集都歸法國（一套畫成領地、一套畫成勢力範圍）。
Tai 2026-11-14：併進法屬西非既有的紀錄，註明未設治，標待查證。提貝斯提、博爾庫一帶不在這一批（另查出處）。
做法：兩筆法屬西非紀錄撤回重寫。
  ZONE_A（尼日北部）＝法屬西非 1910-06-22 那一筆的範圍，扣掉 1908-01-01～1910-06-22 之間任何有效紀錄已涵蓋的部分
  ZONE_B（茅利塔尼亞北部、馬利北部）＝1912 年法屬西非、上塞內加爾與尼日、茅利塔尼亞三者的範圍，扣掉 1908-01-01～1912-01-01 之間任何有效紀錄已涵蓋的部分
  1908-01-01～1910-06-22 那一筆加 A 與 B；1910-06-22～1912-01-01 那一筆加 B。小於 200 平方公里的碎片不要。
用法：python3 -I build/build.py
"""
import json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
REC1, REC2 = '01a1a27b-d37b-7569-b8bb-79f18b06ba8f', '01a1a27b-d394-7cba-b7fe-e49e06ac953e'   # 原始兩筆（已撤回）：範圍計算仍以它們為準
# 寫入後的檢查備忘：用 geography 面積量這兩筆與西班牙紀錄的交集會得到 109 平方公里，那是沿緯線的極細長碎片造成的計算假象；
# 平面座標下交集只有 1.9e-7 平方度（約 0.002 平方公里），實際上沒有重疊。
WRITTEN = ['01a1da33-da68-72b2-9661-0712183cdcc9', '01a1da33-dac7-79e0-bd81-f7ace3676ce5']   # 這一批寫入的兩筆；重跑時不算既有涵蓋
def q(sql):
    _r = subprocess.run(['docker', 'exec', 'worldline-borders-dev-db', 'psql', '-X', '-U', 'worldline', '-d', 'worldline_borders_dev', '-At', '-c', sql], capture_output=True, text=True)
    if _r.returncode: raise SystemExit(_r.stderr[-600:])
    return _r.stdout.strip()
# 兩筆目標紀錄即使已撤回也算「既有涵蓋」並可讀取：第一次送出時第一筆撤回後重寫因幾何無效失敗，要能原樣重建
def big(expr): return f"(select coalesce(st_union(d.geom), st_setsrid('MULTIPOLYGON EMPTY'::geometry, 4326)) from st_dump({expr}) d where st_area(d.geom::geography) > 2e8)"
ZA = big(f"""st_intersection(st_difference((select st_makevalid(geom) from sovereignty_records where id = '{REC2}'),
        (select st_union(st_makevalid(geom)) from sovereignty_records where ((retracted_at is null and id not in ('01a1da33-da68-72b2-9661-0712183cdcc9', '01a1da33-dac7-79e0-bd81-f7ace3676ce5')) or id in ('01a1a27b-d37b-7569-b8bb-79f18b06ba8f', '01a1a27b-d394-7cba-b7fe-e49e06ac953e')) and valid_period && daterange('1908-01-01','1910-06-22') and st_intersects(geom, st_makeenvelope(0,10,21,25,4326)))),
        st_makeenvelope(0,10,21,25,4326))""")
ZB = big(f"""st_intersection(st_difference((select st_union(st_makevalid(r.geom)) from sovereignty_records r join regimes g on g.id = r.regime_id where r.retracted_at is null and r.valid_period @> date '1912-06-01' and g.slug in ('french-west-africa','upper-senegal-and-niger','mauritania-french-1912')),
        (select st_union(st_makevalid(geom)) from sovereignty_records where ((retracted_at is null and id not in ('01a1da33-da68-72b2-9661-0712183cdcc9', '01a1da33-dac7-79e0-bd81-f7ace3676ce5')) or id in ('01a1a27b-d37b-7569-b8bb-79f18b06ba8f', '01a1a27b-d394-7cba-b7fe-e49e06ac953e')) and valid_period && daterange('1908-01-01','1912-01-01') and st_intersects(geom, st_makeenvelope(-19,13,-3,29,4326)))),
        st_makeenvelope(-19,13,-3,29,4326))""")
COLS = "regime_id, lower(valid_period) lo, upper(valid_period) hi, layer_status, start_event_id, end_event_id, geometry_source_id, geometry_locator, geometry_license, attribution, ohm_relation_id, ohm_version, ohm_fetched_at, ohm_start_raw, ohm_end_raw, provenance, note, round((st_area(geom::geography)/1e6)::numeric) old_km2"
feats = []
def write(name, obj): json.dump(obj, open(os.path.join(ROOT, 'requests', name), 'w'), ensure_ascii=False, indent=1)
for n, (rid, add, what, zones) in enumerate([(REC1, f"st_union({ZA}, {ZB})", '尼日北部、茅利塔尼亞北部與馬利北部', ['A', 'B']), (REC2, ZB, '茅利塔尼亞北部與馬利北部', ['B'])], 1):
    r = json.loads(q(f"""select row_to_json(t) from (select {COLS},
        round((st_area({add}::geography)/1e6)::numeric) add_km2, round((st_area(st_intersection(st_makevalid(geom), {add})::geography)/1e6)::numeric, 1) overlap_km2,
        st_asgeojson(st_multi(st_collectionextract(st_makevalid(st_reduceprecision(st_union(st_makevalid(geom), {add}), 0.000001)), 3)), 7)::json geom,
        st_isvalid(st_multi(st_collectionextract(st_makevalid(st_reduceprecision(st_union(st_makevalid(geom), {add}), 0.000001)), 3))) ok,
        round((st_area(st_union(st_makevalid(geom), {add})::geography)/1e6)::numeric) new_km2
        from sovereignty_records where id = '{rid}') t"""))
    assert r['ok'], '幾何無效'
    print(r['lo'], r['hi'], 'old', r['old_km2'], '+', r['add_km2'], '→', r['new_km2'], 'overlap', r['overlap_km2'])
    tag = f'FWA_{n:02d}'; feats.append({'type': 'Feature', 'id': tag, 'properties': {}, 'geometry': r['geom']})
    write(f'01-{n:02d}a-retract-{tag.lower()}.json', {'_placeholder': f'RETRACTED_{tag}', '_post': f'/api/v1/sovereignty-records/{rid}/retraction', '_meta': {'fix': True}, 'body': {
        'reason': f"法屬西非 {r['lo']}～{r['hi']}：資料集在這段期間不含{what}（約 {int(r['add_km2']) // 10000} 萬平方公里），那些地方因此沒有任何紀錄。Tai 2026-11-14 決定併進法屬西非並註明未設治。加上後重新新增（french-sahara-1908）。"}})
    prov = dict(r['provenance'] or {})
    prov['unorganised'] = {'batch': 'french-sahara-1908', 'replaces': rid, 'zones': zones, 'addedKm2': float(r['add_km2']),
                           'method': 'A＝法屬西非 1910-06-22 那一筆的範圍扣掉 1908-01-01～1910-06-22 既有紀錄；B＝1912 年法屬西非、上塞內加爾與尼日、茅利塔尼亞的範圍扣掉 1908-01-01～1912-01-01 既有紀錄；小於 200 平方公里的碎片略去',
                           'basis': 'Shepherd 1911 pp. 174–175 畫成法國勢力範圍（斜線）；劍橋 1924 年版 Map 130（Africa in 1910）畫成法國色。兩者性質不同，本紀錄沒有附引文，維持待查證。'}
    note = dict(r['note'] or {})
    note = {'zh-Hant': ((note.get('zh-Hant') or '') + f'含{what}：這些地方當時法國尚未設治（資料集的法屬西非要到稍後才畫進去），1910 年前後的地圖集一套畫成法國領地、一套畫成法國勢力範圍。加上去的範圍取自稍後的法屬西非紀錄，不是當時實際管轄的範圍。').strip(),
            'en': ((note.get('en') or '') + ' Includes Saharan areas not yet organised by France at the time; atlases of c. 1910 show them either as French territory or as a French sphere of influence. The added extent is taken from later French West Africa records, not from the area actually administered.').strip()}
    write(f'01-{n:02d}b-sovereignty-{tag.lower()}.json', {'_placeholder': tag, '_post': '/api/v1/sovereignty-records', '_geometryFrom': tag, '_meta': {'replaces': rid, 'old_km2': float(r['old_km2']), 'new_km2': float(r['new_km2'])}, 'body': {
        'regimeId': r['regime_id'], 'geometry': None, 'validPeriod': {'start': r['lo'], 'end': r['hi']}, 'layerStatus': r['layer_status'],
        'geometrySourceId': r['geometry_source_id'], 'geometryLocator': r['geometry_locator'] + '（含尚未設治的撒哈拉部分，取自稍後的紀錄）', 'geometryLicense': r['geometry_license'], 'attribution': r['attribution'],
        'startEventId': r['start_event_id'], 'endEventId': r['end_event_id'], 'ohmRelationId': r['ohm_relation_id'], 'ohmVersion': r['ohm_version'], 'ohmFetchedAt': r['ohm_fetched_at'],
        'ohmStartRaw': r['ohm_start_raw'], 'ohmEndRaw': r['ohm_end_raw'], 'provenance': prov, 'note': note}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(ROOT, 'french-sahara-1908-derived.geojson'), 'w'))
