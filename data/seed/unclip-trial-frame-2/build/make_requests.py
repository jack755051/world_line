#!/usr/bin/env python3
"""補回試驗框外的幾何：每筆既有紀錄先撤回、再以同欄位（同政權、期間、起訖事件、來源、OHM 固定版本）新增補完整幾何的紀錄。
幾何由 build.py 產生（unclip-trial-frame-2-derived.geojson）。框外沒有可補的部分（outside_area = 0）的紀錄不產生請求。只寫開發庫（5052）。"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'requests')
R = json.load(open(os.path.join(HERE, 'records.json')))
WHO = {'kingdom-of-norway': ('挪威王國', 'NO'), 'kingdom-of-portugal': ('葡萄牙王國', 'PT'), 'portuguese-republic': ('葡萄牙共和國', 'PT')}
def lost(r):
    return '斯瓦巴（北緯 72 度以北）' if r['slug'] == 'kingdom-of-norway' else '亞速群島（西經 20 度以西）'
def write(name, req):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f: json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')
n = 0
for x in R:
    r = x['row']
    if x['outside_area'] <= 0 or r['slug'] not in WHO: continue
    n += 1; who, code = WHO[r['slug']]; tag = f'{code}_{n:02d}'
    write(f'01-{n:02d}a-retract-{tag.lower()}.json', {'_placeholder': f'RETRACTED_UNCLIP_{tag}', '_post': f"/api/v1/sovereignty-records/{r['id']}/retraction", '_meta': {'fix': True},
          'body': {'reason': f"{who} {r['lo']}～{r['hi']}：原紀錄幾何被試驗框（西經 20～東經 60、北緯 15～72）裁切，{lost(r)}缺漏；改以 unclip-trial-frame-2 用同一固定版本 OHM（relation/{r['ohm_relation_id']} v{r['ohm_version']}）補完整幾何，撤回後重新新增。"}})
    cuts = [c for c in x['cut'] if c['area_deg2'] >= 0.001]
    prov = dict(r['provenance'] or {})
    prov['unclip'] = {'batch': 'unclip-trial-frame-2', 'replaces': r['id'], 'frameRemoved': 'box(-20,15,60,72)',
                      'method': '框內幾何沿用原紀錄；框外部分取同一 OHM 版本全球重組（Natural Earth 10m 陸地裁切、簡化到 0.02 度、略去小於 1e-3 平方度的小島）後併入',
                      'rawRefetched': x['raw_fetched'], 'rawNote': '原始下載檔不在本機，2026-11-14 以同一查詢重新取得；關係版本號與原紀錄相同',
                      'outsideMemberWayLicense': x['outside_license'], 'cutAgainstExisting': cuts, 'cutNote': '與同期其他政權既有紀錄重疊處扣除，保留既有紀錄'}
    note = dict(r['note'] or {})
    note = {'zh-Hant': (note.get('zh-Hant') or '') + f'（2026-11-14 修正：補回試驗框外的幾何——{lost(r)}。）',
            'en': ((note.get('en') or '') + ' (Fixed 2026-11-14: geometry outside the trial frame restored.)').strip()}
    write(f'01-{n:02d}b-sovereignty-{tag.lower()}.json', {'_placeholder': f'UNCLIP_{tag}', '_post': '/api/v1/sovereignty-records', '_geometryFrom': 'U_' + r['id'],
          '_meta': {'replaces': r['id'], 'slug': r['slug'], 'old_area': x['old_area'], 'new_area': x['new_area'], 'inside_change': x['inside_change']},
          'body': {'regimeId': r['regime_id'], 'geometry': None, 'validPeriod': {'start': r['lo'], 'end': r['hi']}, 'layerStatus': r['layer_status'],
                   'geometrySourceId': r['geometry_source_id'], 'geometryLocator': r['geometry_locator'] + '（完整，不受試驗框裁切）', 'geometryLicense': r['geometry_license'], 'attribution': r['attribution'],
                   'startEventId': r['start_event_id'], 'endEventId': r['end_event_id'], 'ohmRelationId': r['ohm_relation_id'], 'ohmVersion': r['ohm_version'],
                   'ohmFetchedAt': r['ohm_fetched_at'], 'ohmStartRaw': r['ohm_start_raw'], 'ohmEndRaw': r['ohm_end_raw'], 'provenance': prov, 'note': note}})
print('ok', n)
