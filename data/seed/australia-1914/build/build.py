#!/usr/bin/env python3
"""產生 australia-1914 的請求檔。只讀開發庫，不寫任何資料。
問題：澳洲聯邦第一筆紀錄到 1914-01-01 結束（OHM 的結束日只寫「1914」），下一筆 1914-07-01 才開始，中間六個月整個澳洲沒有紀錄。
      兩筆的形狀只差諾福克島（41 平方公里，下一筆才有）。
做法：撤回第一筆，用同一幾何重寫，結束日改為 1914-07-01（下一筆的起始日）。
用法：python3 -I build/build.py
"""
import json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
OLD = '01a1a282-3b67-70f5-81c1-52dbcd97fe9f'
def q(sql):
    return subprocess.run(['docker', 'exec', 'worldline-borders-dev-db', 'psql', '-U', 'worldline', '-d', 'worldline_borders_dev', '-At', '-c', sql], check=True, capture_output=True, text=True).stdout.strip()
o = json.loads(q(f"select row_to_json(t) from (select regime_id, geometry_source_id, geometry_locator, geometry_license, attribution, ohm_relation_id, ohm_version, ohm_fetched_at, ohm_start_raw, ohm_end_raw, provenance, note, st_asgeojson(geom, 7)::json geom from sovereignty_records where id = '{OLD}' and retracted_at is null) t"))
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': 'AUSTRALIA_1908', 'properties': {}, 'geometry': o['geom']}]}, open(os.path.join(ROOT, 'australia-1914-derived.geojson'), 'w'))
def write(name, obj): json.dump(obj, open(os.path.join(ROOT, 'requests', name), 'w'), ensure_ascii=False, indent=1)
write('01a-retract.json', {'_placeholder': 'RETRACTED_AUSTRALIA_1908', '_post': f'/api/v1/sovereignty-records/{OLD}/retraction', '_meta': {'fix': True}, 'body': {
    'reason': '澳洲聯邦 1908-01-01～1914-01-01：結束日取自 OHM 只寫年份的「1914」，下一筆 1914-07-01 才開始，中間六個月整個澳洲沒有紀錄。同一幾何重寫，結束日改為 1914-07-01（australia-1914）。'}})
write('01b-sovereignty.json', {'_placeholder': 'AUSTRALIA_1908', '_post': '/api/v1/sovereignty-records', '_geometryFrom': 'AUSTRALIA_1908', '_meta': {'replaces': OLD}, 'body': {
    'regimeId': o['regime_id'], 'geometry': None, 'validPeriod': {'start': '1908-01-01', 'end': '1914-07-01'}, 'layerStatus': 'de_jure',
    'geometrySourceId': o['geometry_source_id'], 'geometryLocator': o['geometry_locator'], 'geometryLicense': o['geometry_license'], 'attribution': o['attribution'],
    'startEventId': None, 'endEventId': None, 'ohmRelationId': o['ohm_relation_id'], 'ohmVersion': o['ohm_version'], 'ohmFetchedAt': o['ohm_fetched_at'], 'ohmStartRaw': o['ohm_start_raw'], 'ohmEndRaw': o['ohm_end_raw'],
    'provenance': {**(o['provenance'] or {}), 'fix': {'batch': 'australia-1914', 'replaces': OLD, 'endChanged': '1914-01-01 → 1914-07-01', 'reason': 'OHM 結束日只有年份；接到下一筆的起始日，補上六個月的空白'}},
    'note': {'zh-Hant': '結束日 1914-07-01 是下一筆紀錄的起始日（下一筆多了諾福克島）。OHM 對這個形狀的結束日只寫「1914」。諾福克島移交的日期與出處還沒有另外查證。',
             'en': 'End date set to 1914-07-01, the start of the next record (which adds Norfolk Island); OHM gives only the year 1914.'}}})
print('ok')
