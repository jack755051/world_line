#!/usr/bin/env python3
"""蘇聯、土耳其國界補完整：每筆既有紀錄先撤回、再以同欄位（同政權、期間、起訖事件、來源、OHM 固定版本）新增補完整幾何的紀錄。
幾何由 build/build.py 產生（unclip-su-tr-derived.geojson）。只寫開發庫（5052）。"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'requests')
R = json.load(open(os.path.join(HERE, 'records.json')))
SLUG = {'01a18e71-ccaa-7e5f-8e69-06921e5214cc': 'republic-of-turkey'}
def write(name, req):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f: json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')
for i, x in enumerate(R, 1):
    r = x['row']; tr = r['ohm_relation_id'] in (2801012, 2864004); tag = ('TR' if tr else 'SU') + f'_{i:02d}'
    who = '土耳其共和國' if tr else '蘇聯'
    lost = '安納托利亞東部（卡爾斯、埃爾祖魯姆、凡湖一帶）' if tr else '亞洲部分（高加索東部、中亞、西伯利亞、遠東）與東經 42 度以東的歐俄'
    write(f'01-{i:02d}a-retract-{tag.lower()}.json', {'_placeholder': f'RETRACTED_UNCLIP_{tag}', '_post': f"/api/v1/sovereignty-records/{r['id']}/retraction", '_meta': {'fix': True},
          'body': {'reason': f"{who}：原紀錄幾何被歐陸試驗框（西經 12～東經 42、北緯 34～72）裁切，{lost}缺漏；改以 unclip-su-tr 用同一固定版本 OHM（relation/{r['ohm_relation_id']} v{r['ohm_version']}）補完整幾何，撤回後重新新增。"}})
    cuts = [c for c in x['cut'] if c['area_deg2'] >= 0.001]
    prov = dict(r['provenance'] or {})
    prov['unclip'] = {'batch': 'unclip-su-tr', 'replaces': r['id'], 'frameRemoved': 'box(-12,34,42,72)',
                      'method': '框內幾何沿用原紀錄；框外部分取同一 OHM 版本全球重組（Natural Earth 10m 陸地裁切）後併入',
                      'outsideMemberWayLicense': x['outside_license'],
                      'cutAgainstExisting': cuts, 'cutNote': '與同期其他政權共有邊界上的細碎重疊（<0.001 平方度）亦一併扣除'}
    note = dict(r['note'] or {})
    add_zh = '（2026-10-31 修正：補回歐陸試驗框外的幾何' + ('；黑龍江／烏蘇里江江中島與滿洲國重疊處依既有滿洲國紀錄扣除' if any(c['slug'] == 'manchukuo' for c in cuts) else '') + '。）'
    add_en = '(Fixed 2026-10-31: geometry outside the European trial frame restored.)'
    note = {'zh-Hant': (note.get('zh-Hant') or '') + add_zh, 'en': ((note.get('en') or '') + ' ' + add_en).strip()}
    lo, hi = r['valid_period'][1:11], r['valid_period'][12:22]
    loc = r['geometry_locator'] + '（完整，不受歐陸框裁切）'
    write(f'01-{i:02d}b-sovereignty-{tag.lower()}.json', {'_placeholder': f'UNCLIP_{tag}', '_post': '/api/v1/sovereignty-records', '_geometryFrom': 'U_' + r['id'],
          '_meta': {'replaces': r['id'], 'old_area': x['old_area'], 'new_area': x['new_area'], 'inside_change': x['inside_change']},
          'body': {'regimeId': r['regime_id'], 'geometry': None, 'validPeriod': {'start': lo, 'end': hi}, 'layerStatus': r['layer_status'],
                   'geometrySourceId': r['geometry_source_id'], 'geometryLocator': loc, 'geometryLicense': r['geometry_license'], 'attribution': r['attribution'],
                   'startEventId': r['start_event_id'], 'endEventId': r['end_event_id'], 'ohmRelationId': r['ohm_relation_id'], 'ohmVersion': r['ohm_version'],
                   'ohmFetchedAt': r['ohm_fetched_at'], 'ohmStartRaw': r['ohm_start_raw'], 'ohmEndRaw': r['ohm_end_raw'], 'provenance': prov, 'note': note}})
print('ok', len(R))
