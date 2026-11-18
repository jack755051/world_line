#!/usr/bin/env python3
"""產生 siam-1909 的幾何與請求檔。只讀開發庫（5442 的容器），不寫任何資料。
做的事：暹羅 1908-01-01～1937-07-07 那一筆（1909 年之後的形狀）拆成兩段：
  SIAM_PRE1909   1908-01-01～1909-07-09：原形狀＋吉打、吉蘭丹、登嘉樓、玻璃市四筆紀錄的形狀（聯集）
  SIAM_POST1909  1909-07-09～1937-07-07：原形狀不動，起始事件接英暹條約互換批准書
用法：python3 -I build/build.py   （輸出 ../siam-1909-derived.geojson 與 ../requests/*.json）
"""
import json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
SIAM = '01a1a282-3f3b-7171-936a-dd65e175e8b2'
FOUR = {'kedah-protectorate': '01a1a282-3ece-7888-b45c-e0a925f73000', 'kelantan-protectorate': '01a1a282-3ede-7a31-8206-b03af2194bd7',
        'perlis-protectorate': '01a1a282-3f7e-726b-82cb-ed9c505c98da', 'trengganu-protectorate': '01a1a282-401e-7cc6-9b34-07dae78b7c49'}
EVENT = '01a1d79b-34b7-7b6b-a14c-59b455e15806'   # 英暹條約互換批准書 1909-07-09（data/seed/border-events）
def q(sql):
    return subprocess.run(['docker', 'exec', 'worldline-borders-dev-db', 'psql', '-U', 'worldline', '-d', 'worldline_borders_dev', '-At', '-c', sql],
                          check=True, capture_output=True, text=True).stdout.strip()
ids = "','".join([SIAM, *FOUR.values()])
row = json.loads(q(f"""select json_build_object(
  'retracted', (select count(*) from sovereignty_records where id in ('{ids}') and retracted_at is not null),
  'post', (select st_asgeojson(geom, 7)::json from sovereignty_records where id = '{SIAM}'),
  'pre', (select st_asgeojson(st_multi(st_collectionextract(st_union(st_makevalid(geom)), 3)), 7)::json from sovereignty_records where id in ('{ids}')),
  'post_km2', (select st_area(geom::geography) / 1e6 from sovereignty_records where id = '{SIAM}'),
  'pre_km2', (select st_area(st_union(st_makevalid(geom))::geography) / 1e6 from sovereignty_records where id in ('{ids}')),
  'rec', (select row_to_json(t) from (select regime_id, geometry_source_id, ohm_relation_id, ohm_version, ohm_fetched_at, ohm_start_raw, ohm_end_raw, provenance
                                      from sovereignty_records where id = '{SIAM}') t),
  'four', (select json_agg(json_build_object('id', id, 'locator', geometry_locator, 'km2', round((st_area(geom::geography) / 1e6)::numeric, 1)) order by geometry_locator)
           from sovereignty_records where id in ('{"','".join(FOUR.values())}')))"""))
assert row['retracted'] == 0, '來源紀錄已有被撤回的，請先確認（這批可能已經寫入過）'
rec = row['rec']
json.dump({'type': 'FeatureCollection', 'features': [
    {'type': 'Feature', 'id': 'SIAM_PRE1909', 'properties': {'km2': round(row['pre_km2'], 1)}, 'geometry': row['pre']},
    {'type': 'Feature', 'id': 'SIAM_POST1909', 'properties': {'km2': round(row['post_km2'], 1)}, 'geometry': row['post']}]},
    open(os.path.join(ROOT, 'siam-1909-derived.geojson'), 'w'), ensure_ascii=False)
fix = {'batch': 'siam-1909', 'replaces': SIAM, 'event': EVENT}
def write(name, obj): json.dump(obj, open(os.path.join(ROOT, 'requests', name), 'w'), ensure_ascii=False, indent=1)
write('01-retract-siam.json', {'_placeholder': 'RETRACTED_SIAM_1908_1937', '_post': f'/api/v1/sovereignty-records/{SIAM}/retraction', '_meta': {'fix': True}, 'body': {
    'reason': '暹羅 1908-01-01～1937-07-07：整段用同一個形狀（1909 年之後的暹羅），但吉打、吉蘭丹、登嘉樓、玻璃市到 1909-07-09 英暹條約生效才移交英國。'
              '改成兩段（siam-1909）：1909-07-09 以前含四邦，之後沿用原形狀並接上條約事件。撤回後重新新增。'}})
base = {'regimeId': rec['regime_id'], 'geometry': None, 'layerStatus': 'de_jure', 'geometrySourceId': rec['geometry_source_id'], 'geometryLicense': 'cc0', 'attribution': None}
write('02-sovereignty-siam-pre1909.json', {'_placeholder': 'SIAM_PRE1909', '_post': '/api/v1/sovereignty-records', '_geometryFrom': 'SIAM_PRE1909',
    '_meta': {'replaces': SIAM, 'km2': round(row['pre_km2'], 1)}, 'body': {**base,
    'validPeriod': {'start': '1908-01-01', 'end': '1909-07-09'},
    'geometryLocator': f"relation/{rec['ohm_relation_id']} v{rec['ohm_version']} ＋ " + '、'.join(f['locator'] for f in row['four']) + '（聯集）',
    'startEventId': None, 'endEventId': EVENT,
    'ohmRelationId': None, 'ohmVersion': None, 'ohmFetchedAt': None, 'ohmStartRaw': None, 'ohmEndRaw': None,
    'provenance': {**fix, 'derived': True,
        'method': '原暹羅紀錄的幾何，與資料庫裡吉打、吉蘭丹、登嘉樓、玻璃市四筆保護國紀錄（1909-07-09 起）的幾何做聯集；沒有重新取回 OHM。',
        'parts': [{'record': SIAM, 'locator': f"relation/{rec['ohm_relation_id']} v{rec['ohm_version']}", 'km2': round(row['post_km2'], 1)}, *[{'record': f['id'], 'locator': f['locator'], 'km2': float(f['km2'])} for f in row['four']]],
        'memberWayLicense': 'all untagged (OHM CC0)', 'writtenKm2': round(row['pre_km2'], 1),
        'shapeIsEstimate': '四邦的範圍用的是 1909 年之後各邦的界線，不是 1909 年以前暹羅屬地的實際界線。'},
    'note': {'zh-Hant': '1909-07-09 英暹條約生效以前的暹羅：含吉打、吉蘭丹、登嘉樓、玻璃市。依據是條約第 1 條（暹羅把對這四邦的宗主、保護、行政與管轄權移交英國）。'
                        '形狀是推估：四邦用的是移交之後的邦界。條約同時重劃了邊界，移交前暹羅屬地與霹靂之間的界線和這裡畫的可能不同，尚未查證。',
             'en': 'Siam before the Anglo-Siamese Treaty took effect on 9 July 1909, including Kedah, Kelantan, Trengganu and Perlis (Article 1). The shape is an estimate: the four states use their post-transfer boundaries; the pre-1909 line toward Perak is unverified.'}}})
write('03-sovereignty-siam-post1909.json', {'_placeholder': 'SIAM_POST1909', '_post': '/api/v1/sovereignty-records', '_geometryFrom': 'SIAM_POST1909',
    '_meta': {'replaces': SIAM, 'km2': round(row['post_km2'], 1)}, 'body': {**base,
    'validPeriod': {'start': '1909-07-09', 'end': '1937-07-07'},
    'geometryLocator': f"relation/{rec['ohm_relation_id']} v{rec['ohm_version']}",
    'startEventId': EVENT, 'endEventId': None,
    'ohmRelationId': rec['ohm_relation_id'], 'ohmVersion': rec['ohm_version'], 'ohmFetchedAt': rec['ohm_fetched_at'], 'ohmStartRaw': rec['ohm_start_raw'], 'ohmEndRaw': rec['ohm_end_raw'],
    'provenance': {**(rec['provenance'] or {}), 'fix': {**fix, 'note': '幾何與原紀錄相同，只改起始日並接上起始事件'}},
    'note': {'zh-Hant': '1909-07-09 英暹條約生效之後的暹羅。幾何沿用原紀錄（同一 OHM 關係、同一版本）。OHM 把這個形狀的起日記為 1907-03-23，但四邦到 1909-07-09 才移交，所以起始日改為 1909-07-09。',
             'en': 'Siam after the Anglo-Siamese Treaty took effect on 9 July 1909. Geometry unchanged from the retracted record; start date moved from 1908-01-01 to 1909-07-09.'}}})
print('pre km2', round(row['pre_km2'], 1), 'post km2', round(row['post_km2'], 1), 'diff', round(row['pre_km2'] - row['post_km2'], 1), 'four', sum(float(f['km2']) for f in row['four']))
