#!/usr/bin/env python3
"""每筆既有紀錄先撤回、再以同欄位新增補完整幾何的紀錄（幾何見 build.py）。只寫開發庫（5052）。"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'requests')
ZH = {'french-third-republic': '法蘭西第三共和', 'french-state-vichy': '維琪法國', 'french-north-africa-allied-occupation': '盟軍佔領下的法屬北非',
      'french-committee-of-national-liberation': '法蘭西民族解放委員會', 'provisional-government-french-republic': '法蘭西共和國臨時政府'}
def write(name, req):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f: json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')
for n, x in enumerate(json.load(open(os.path.join(HERE, 'records.json'))), 1):
    r = x['row']; tag = f'FR_{n:02d}'
    write(f'01-{n:02d}a-retract-{tag.lower()}.json', {'_placeholder': f'RETRACTED_UNCLIP_{tag}', '_post': f"/api/v1/sovereignty-records/{r['id']}/retraction", '_meta': {'fix': True},
          'body': {'reason': f"{ZH[r['slug']]} {r['lo']}～{r['hi']}：原紀錄幾何被最早的歐陸試驗框（西經 12～東經 42、北緯 34～72）裁切，阿爾及利亞北緯 34 度以南約 {x['outside_km2'] // 10000} 萬平方公里缺漏；"
                             f"unclip-eu-frame-france 補回後重新新增。"}})
    prov = dict(r['provenance'] or {})
    prov['unclip'] = {'batch': 'unclip-eu-frame-france', 'replaces': r['id'], 'frameRemoved': 'box(-12,34,42,72)',
                      'method': '框內幾何沿用原紀錄；框外部分（阿爾及利亞北緯 34 度以南）取自同一 OHM 關係，Natural Earth 10m 陸地裁切、簡化到 0.02 度後併入',
                      'outsideFromVersion': x['rawVersion'], 'outsideVersionTimestamp': x['rawTimestamp'], 'rawRefetched': x['rawFetched'],
                      'versionNote': f"紀錄記的是 v{r['ohm_version']}，原始下載檔不在本機；OHM 於 2026-11-13 改過這個關係，2026-11-14 取回的是 v{x['rawVersion']}，舊版本取不回來。"
                                     f"框外部分用 v{x['rawVersion']}。新版本與原紀錄在阿爾及利亞北部（框內）相差約 {x['northAlgeriaDiffVsNewVersion_km2']} 平方公里。",
                      'outsideMemberWayLicense': x['outside_license'], 'cutAgainstExisting': x['cut'], 'cutNote': '與同期其他政權既有紀錄重疊處扣除，保留既有紀錄'}
    note = dict(r['note'] or {})
    note = {'zh-Hant': (note.get('zh-Hant') or '') + '（2026-11-14 修正：補回試驗框外的幾何——阿爾及利亞北緯 34 度以南。南界是資料集的線，沒有另外查證。）',
            'en': ((note.get('en') or '') + ' (Fixed 2026-11-14: geometry outside the trial frame restored — Algeria south of 34°N.)').strip()}
    write(f'01-{n:02d}b-sovereignty-{tag.lower()}.json', {'_placeholder': f'UNCLIP_{tag}', '_post': '/api/v1/sovereignty-records', '_geometryFrom': 'U_' + r['id'],
          '_meta': {'replaces': r['id'], 'slug': r['slug'], 'old_km2': x['old_km2'], 'new_km2': x['new_km2'], 'inside_change_km2': x['inside_change_km2']},
          'body': {'regimeId': r['regime_id'], 'geometry': None, 'validPeriod': {'start': r['lo'], 'end': r['hi']}, 'layerStatus': r['layer_status'],
                   'geometrySourceId': r['geometry_source_id'], 'geometryLocator': r['geometry_locator'] + f"（框外阿爾及利亞南部取自 v{x['rawVersion']}）", 'geometryLicense': r['geometry_license'], 'attribution': r['attribution'],
                   'startEventId': r['start_event_id'], 'endEventId': r['end_event_id'], 'ohmRelationId': r['ohm_relation_id'], 'ohmVersion': r['ohm_version'],
                   'ohmFetchedAt': r['ohm_fetched_at'], 'ohmStartRaw': r['ohm_start_raw'], 'ohmEndRaw': r['ohm_end_raw'], 'provenance': prov, 'note': note}})
print('ok', n)
