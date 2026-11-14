#!/usr/bin/env python3
"""產生 italian-somaliland-1908 的幾何與請求檔。只讀開發庫（5442 的容器），不寫任何資料。
問題：義屬索馬利蘭 1908-01-01～1920-01-01 只有貝納迪爾沿岸 10,697 平方公里；1920 年起那一筆有 172,815 平方公里。
      兩者相差的內陸約 16 萬平方公里，在 1908–1920 年沒有任何紀錄涵蓋。兩套 1910 年前後的地圖集都把這一帶畫成義屬索馬利蘭。
做法：撤回 1908–1920 那一筆，改用資料庫裡 1920-01-01 起那一筆的形狀重寫，不重新取回 OHM。
用法：python3 -I build/build.py
"""
import json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
def q(sql):
    return subprocess.run(['docker', 'exec', 'worldline-borders-dev-db', 'psql', '-U', 'worldline', '-d', 'worldline_borders_dev', '-At', '-c', sql],
                          check=True, capture_output=True, text=True).stdout.strip()
COLS = "id, regime_id, lower(valid_period) lo, upper(valid_period) hi, geometry_source_id, geometry_locator, geometry_license, attribution, ohm_relation_id, ohm_version, ohm_fetched_at, ohm_start_raw, ohm_end_raw, provenance, round((st_area(geom::geography)/1e6)::numeric,1) km2"
old, new = (json.loads(q(f"select row_to_json(t) from (select {COLS} from sovereignty_records where retracted_at is null and ohm_relation_id = {r}) t")) for r in (2923095, 2923094))
geom = json.loads(q(f"select st_asgeojson(geom, 7) from sovereignty_records where id = '{new['id']}'"))
over = q(f"""select coalesce(string_agg(g.slug || ' ' || round((st_area(st_intersection(st_makevalid(r.geom), st_makevalid(n.geom))::geography)/1e6)::numeric, 1), '、'), '無')
  from sovereignty_records r join regimes g on g.id = r.regime_id, sovereignty_records n
  where n.id = '{new['id']}' and r.retracted_at is null and r.id not in ('{old['id']}', '{new['id']}') and r.valid_period && daterange('1908-01-01', '1920-01-01')
    and st_intersects(r.geom, n.geom) and st_area(st_intersection(st_makevalid(r.geom), st_makevalid(n.geom))::geography) > 1e5""")
print('與 1908–1920 其他紀錄重疊（平方公里）：', over)
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': 'IT_SOMALILAND_1908', 'properties': {}, 'geometry': geom}]},
          open(os.path.join(ROOT, 'italian-somaliland-1908-derived.geojson'), 'w'), ensure_ascii=False)
def write(name, obj): json.dump(obj, open(os.path.join(ROOT, 'requests', name), 'w'), ensure_ascii=False, indent=1)
write('01a-retract.json', {'_placeholder': 'RETRACTED_IT_SOMALILAND_1908', '_post': f"/api/v1/sovereignty-records/{old['id']}/retraction", '_meta': {'fix': True}, 'body': {
    'reason': '義屬索馬利蘭 1908-01-01～1920-01-01：只有貝納迪爾沿岸約 1 萬平方公里，內陸約 16 萬平方公里在這段期間沒有任何紀錄涵蓋；兩套 1910 年前後的地圖集都把內陸畫成義屬索馬利蘭。'
              '改用 1920-01-01 起那一筆的形狀（italian-somaliland-1908：撤回後重新新增）。'}})
write('01b-sovereignty.json', {'_placeholder': 'IT_SOMALILAND_1908', '_post': '/api/v1/sovereignty-records', '_geometryFrom': 'IT_SOMALILAND_1908', '_meta': {'replaces': old['id'], 'oldKm2': float(old['km2']), 'newKm2': float(new['km2'])}, 'body': {
    'regimeId': old['regime_id'], 'geometry': None, 'validPeriod': {'start': old['lo'], 'end': old['hi']}, 'layerStatus': 'de_jure',
    'geometrySourceId': new['geometry_source_id'], 'geometryLocator': f"relation/{new['ohm_relation_id']} v{new['ohm_version']}（沿用 1920-01-01 起那一筆的形狀）",
    'geometryLicense': new['geometry_license'], 'attribution': new['attribution'], 'startEventId': None, 'endEventId': None,
    'ohmRelationId': new['ohm_relation_id'], 'ohmVersion': new['ohm_version'], 'ohmFetchedAt': new['ohm_fetched_at'], 'ohmStartRaw': new['ohm_start_raw'], 'ohmEndRaw': new['ohm_end_raw'],
    'provenance': {**(new['provenance'] or {}), 'fix': {'batch': 'italian-somaliland-1908', 'replaces': old['id'], 'replacedLocator': old['geometry_locator'], 'shapeFromRecord': new['id'],
                   'reason': 'OHM 把含內陸的形狀起日記為 1920；1908–1920 年內陸沒有紀錄涵蓋'}},
    'note': {'zh-Hant': '含內陸的義屬索馬利蘭（南部，貝納迪爾及其腹地）。幾何沿用 1920-01-01 起那一筆。內陸與衣索比亞的界線依 1908-05-16 義衣協定，但協定原文還沒取得，'
                        '而且那條線一直沒有實地勘定；1908-05-16 以前的界線（1897 年的約定）也沒有另外處理。所以內陸界線只是大致位置。',
             'en': 'Italian Somaliland (southern part) including the hinterland. Geometry copied from the record starting 1920-01-01. The inland line toward Ethiopia (convention of 16 May 1908, never demarcated) is approximate; the text of the convention has not been obtained.'}}})
def cite(n, ph, src, locator, note, basis):
    write(f'{n}-citation-{ph.lower()}.json', {'_placeholder': ph, '_post': '/api/v1/sovereignty-records/{{IT_SOMALILAND_1908}}/citations',
          'body': {'sourceId': '{{%s}}' % src, 'locator': locator, 'evidenceNote': note, 'grade': 'B', 'gradeBasis': basis}})
cite('02', 'CITE_ITSOM_SHEPHERD', 'SRC_SHEPHERD_1911', 'pp. 174–175, The Partition of Africa（archive.org 掃描頁 n166–n167）',
     '圖版畫出：義屬索馬利蘭從朱巴河口沿岸一路到瓜達富伊角，並深入內陸，貝納迪爾一帶另有標示。本紀錄是其中南部（朱巴河以東到霍比亞蘇丹國以南）含腹地的部分，改用含內陸的形狀之後與圖相符。比例尺 1:40,000,000，只能確認到輪廓與歸屬，內陸界線的位置無法確認。',
     '具名學者編著的歷史地圖集圖版（學術地圖集為 B）。Claude 目視比對，2026-11-14，待考證複核。')
cite('03', 'CITE_ITSOM_CMHA', 'SRC_CMHA_1924', 'Map 130, Africa in 1910（archive.org 掃描頁 n589–n590）',
     '圖版畫出：義屬索馬利蘭以義大利色著色，從朱巴河到瓜達富伊角、深入內陸的一整塊。本紀錄是其中南部含腹地的部分，改用含內陸的形狀之後與圖相符。只能確認到輪廓與歸屬，內陸界線的位置無法確認。',
     '學術機構出版的歷史地圖集圖版（學術地圖集為 B）。Claude 目視比對，2026-11-14，待考證複核。')
print('old', old['km2'], '→ new', new['km2'])
