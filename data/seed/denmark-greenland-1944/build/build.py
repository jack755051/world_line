#!/usr/bin/env python3
"""丹麥 1944-06-17 之後補回格陵蘭與法羅群島。只讀開發庫，不寫任何資料。
問題：冰島 1944-06-17 獨立後，丹麥的兩筆紀錄（1944-06-17～1945-05-05、1945-05-05～1945-10-01）所用的資料集關係只有丹麥本土，
      格陵蘭（約 215 萬平方公里）與法羅群島在這段期間沒有任何紀錄。丹麥對格陵蘭的主權並沒有中斷。
做法：兩筆撤回重寫；幾何＝原幾何＋前一筆丹麥紀錄（1940-04-09～1944-06-17）在西經 5 度以西的部分（格陵蘭與法羅群島；那一筆已不含冰島）。其他欄位照舊。
用法：python3 -I build/build.py
"""
import json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
PREV = '01a1d843-fff4-7e2c-8565-a3b4b6792bf9'
TARGETS = ['01a191a0-a593-7b55-8930-e6f2880e1b99', '01a1aa96-93d2-7629-bd0e-f3aa8f58257b']
FRUS1941, FRUS1945 = '01a19041-0935-77d1-b5a2-60f211b91d2a', '01a191a0-4556-70c2-af32-2210b8605bbd'
def q(sql):
    return subprocess.run(['docker', 'exec', 'worldline-borders-dev-db', 'psql', '-X', '-U', 'worldline', '-d', 'worldline_borders_dev', '-At', '-c', sql], check=True, capture_output=True, text=True).stdout.strip()
WEST = f"(select st_intersection(st_makevalid(geom), st_makeenvelope(-80, 55, -5, 85, 4326)) from sovereignty_records where id = '{PREV}')"
feats = []
def write(name, obj): json.dump(obj, open(os.path.join(ROOT, 'requests', name), 'w'), ensure_ascii=False, indent=1)
prev_loc = q(f"select geometry_locator from sovereignty_records where id = '{PREV}'")
for n, tid in enumerate(TARGETS, 1):
    r = json.loads(q(f"""select row_to_json(t) from (select regime_id, lower(valid_period) lo, upper(valid_period) hi, layer_status, start_event_id, end_event_id, geometry_source_id, geometry_locator, geometry_license, attribution,
        ohm_relation_id, ohm_version, ohm_fetched_at, ohm_start_raw, ohm_end_raw, provenance, note, round((st_area(geom::geography)/1e6)::numeric) old_km2,
        round((st_area(st_union(st_makevalid(geom), {WEST})::geography)/1e6)::numeric) new_km2,
        round((st_area(st_intersection(st_makevalid(geom), {WEST})::geography)/1e6)::numeric, 2) overlap_km2,
        st_asgeojson(st_multi(st_collectionextract(st_union(st_makevalid(geom), {WEST}), 3)), 7)::json geom
        from sovereignty_records where id = '{tid}' and retracted_at is null) t"""))
    print(r['lo'], r['hi'], 'old', r['old_km2'], '→', r['new_km2'], 'overlap', r['overlap_km2'])
    tag = f'DK_{n:02d}'; feats.append({'type': 'Feature', 'id': tag, 'properties': {}, 'geometry': r['geom']})
    write(f'01-{n:02d}a-retract-{tag.lower()}.json', {'_placeholder': f'RETRACTED_{tag}', '_post': f'/api/v1/sovereignty-records/{tid}/retraction', '_meta': {'fix': True}, 'body': {
        'reason': f"丹麥王國 {r['lo']}～{r['hi']}：所用的資料集關係只有丹麥本土，格陵蘭與法羅群島在 1944-06-17 之後沒有任何紀錄；丹麥對格陵蘭的主權沒有中斷。補回後重新新增（denmark-greenland-1944）。"}})
    prov = dict(r['provenance'] or {})
    prov['restore'] = {'batch': 'denmark-greenland-1944', 'replaces': tid, 'addedFromRecord': PREV, 'addedLocator': prev_loc,
                       'method': '原幾何＋前一筆丹麥紀錄（1940-04-09～1944-06-17）在西經 5 度以西的部分（格陵蘭與法羅群島）', 'addedKm2': float(r['new_km2']) - float(r['old_km2'])}
    note = dict(r['note'] or {})
    note = {'zh-Hant': ((note.get('zh-Hant') or '') + '（2026-11-14 修正：補回格陵蘭與法羅群島。這段期間丹麥本土被德國佔領到 1945-05-05，格陵蘭由美國依 1941 年協議協防，法羅群島由英國佔領；主權仍屬丹麥。法羅群島這一段沒有另外的出處，只是沿用前一筆的形狀。）').strip(),
            'en': ((note.get('en') or '') + ' (Fixed 2026-11-14: Greenland and the Faroe Islands restored. Denmark proper was under German occupation until 5 May 1945, Greenland under US protection (agreement of 1941) and the Faroes under British occupation; sovereignty remained Danish.)').strip()}
    write(f'01-{n:02d}b-sovereignty-{tag.lower()}.json', {'_placeholder': tag, '_post': '/api/v1/sovereignty-records', '_geometryFrom': tag, '_meta': {'replaces': tid, 'old_km2': float(r['old_km2']), 'new_km2': float(r['new_km2'])}, 'body': {
        'regimeId': r['regime_id'], 'geometry': None, 'validPeriod': {'start': r['lo'], 'end': r['hi']}, 'layerStatus': r['layer_status'],
        'geometrySourceId': r['geometry_source_id'], 'geometryLocator': r['geometry_locator'] + ' ＋ ' + prev_loc.split('（')[0] + ' 的格陵蘭與法羅群島', 'geometryLicense': r['geometry_license'], 'attribution': r['attribution'],
        'startEventId': r['start_event_id'], 'endEventId': r['end_event_id'], 'ohmRelationId': r['ohm_relation_id'], 'ohmVersion': r['ohm_version'], 'ohmFetchedAt': r['ohm_fetched_at'],
        'ohmStartRaw': r['ohm_start_raw'], 'ohmEndRaw': r['ohm_end_raw'], 'provenance': prov, 'note': note}})
    write(f'02-{n:02d}a-citation-{tag.lower()}-1941.json', {'_placeholder': f'CITE_{tag}_1941', '_post': '/api/v1/sovereignty-records/{{%s}}/citations' % tag, 'body': {
        'sourceId': FRUS1941, 'locator': 'Doc. 40（丹麥公使 Kauffmann 1941-04-13 致國務卿函，引 1941-04-09 格陵蘭防衛協定前言第 4 點）',
        'evidenceNote': '協定前言：「Although the sovereignty of Denmark over Greenland is fully recognized, the present circumstances for the time being prevent the Government in Denmark from exercising its powers in respect of Greenland」。證明美國與丹麥公使簽的協定承認格陵蘭主權屬丹麥，只是丹麥政府暫時無法行使；只證明格陵蘭的歸屬，不證明本紀錄其餘範圍。',
        'grade': 'A', 'gradeBasis': '協定本文（簽署人在正式照會中逐字引述；美國國務院外交文件彙編所收）。逐字核對過 history.state.gov 的頁面文字，2026-11-14。'}})
    write(f'02-{n:02d}b-citation-{tag.lower()}-1945.json', {'_placeholder': f'CITE_{tag}_1945', '_post': '/api/v1/sovereignty-records/{{%s}}/citations' % tag, 'body': {
        'sourceId': FRUS1945, 'locator': 'Doc. 569（丹麥公使 Kauffmann 1945-05-25 致代理國務卿函）',
        'evidenceNote': '「His Majesty the King of Denmark in a Council of State held on the 23rd of May has formally approved the Greenland Agreement of April 9th, 1941.」證明丹麥解放後由國王正式核准 1941 年協定（協定承認格陵蘭主權屬丹麥），格陵蘭在 1945 年仍由丹麥行使主權；只證明格陵蘭的歸屬。',
        'grade': 'A', 'gradeBasis': '丹麥政府的正式照會（美國國務院外交文件彙編所收）。逐字核對過 history.state.gov 的頁面文字，2026-11-14；引文略去原文中的註腳編號。'}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(ROOT, 'denmark-greenland-1944-derived.geojson'), 'w'))
