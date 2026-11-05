#!/usr/bin/env python3
"""產生 requests/R1（來源、政權、事件）與 requests/R2（撤回＋新增主權紀錄）、derived geojson。
輸入：build_ru.py 產生的 done.pkl。只寫開發庫（5052）。"""
import sys, os, json, pickle, glob
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, '/workspace/ru')
from defs import *
from shapely.geometry import mapping
G = pickle.load(open('/workspace/ru/geoms.pkl', 'rb'))
done = pickle.load(open(os.path.join(HERE, 'done.pkl'), 'rb'))
OUT = os.path.join(HERE, '..', 'requests'); R1, R2 = os.path.join(OUT, 'R1'), os.path.join(OUT, 'R2')
for d in (R1, R2):
    os.makedirs(d, exist_ok=True)
    for f in glob.glob(os.path.join(d, '*.json')): os.remove(f)
def write(d, name, req):
    with open(os.path.join(d, name), 'w', encoding='utf-8') as f: json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')
RU_ZH = {'russian-empire': '俄羅斯帝國', 'russian-provisional-government-1917': '俄羅斯臨時政府（俄羅斯共和國）', 'russian-sfsr-1917': '俄羅斯蘇維埃聯邦社會主義共和國', 'soviet-union': '蘇聯',
         'imperial-state-of-iran': '伊朗', 'soviet-occupied-iran-1941': '蘇聯佔領下的伊朗北部', 'british-occupied-iran-1941': '英國佔領下的伊朗南部'}
WINDOW = '俄國與亞洲鄰國 1908-10-05～1937-07-07（russia-asia-1908-1937）'
# ---------- R1 ----------
for i, (ph, body) in enumerate(SOURCES, 1):
    write(R1, f'01-source-{i:02d}-{ph.lower()}.json', {'_placeholder': ph, '_post': '/api/v1/sources', 'body': body})
for i, (ph, slug, orig, lang, zh, en) in enumerate(REGIMES, 1):
    write(R1, f'02-regime-{i:02d}-{slug}.json', {'_placeholder': ph, '_post': '/api/v1/regimes', '_meta': {'nameSource': 'OHM name 標籤（原文）'},
          'body': {'slug': slug, 'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]}})
for i, (ph, date, kind, zh, en, parts, cits, tn, ok) in enumerate(sorted(EVENTS, key=lambda e: e[1]), 1):
    import datetime
    nd = (datetime.date.fromisoformat(date) + datetime.timedelta(days=1)).isoformat()
    body = {'eventKind': kind, 'occurred': {'start': date, 'end': nd}, 'datePrecision': 'day', 'summary': {'zh-Hant': zh, 'en': en},
            'participants': [{'regimeId': RG[s], 'role': r} for s, r in parts], 'citations': cits}
    if tn: body['timeNote'] = {'zh-Hant': tn[0], 'en': tn[1]}
    write(R1, f'03-event-{i:02d}-{ph.lower()}.json', {'_placeholder': ph, '_post': '/api/v1/events', '_meta': {'verification': 'verified' if ok else 'pending（待查證）'}, 'body': body})
# ---------- R2 ----------
feats = []
def rnd(o):
    if isinstance(o, dict): return {k: rnd(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        if o and isinstance(o[0], float): return [round(x, 4) for x in o]
        return [rnd(x) for x in o]
    return o
def geom_meta(rid):
    m = G[rid][1]
    return m
def prov_common(d, m):
    return {'memberWayLicense': m['memberWayLicense'], 'osmDerivedWayCount': 0, 'ohmFixme': m.get('fixme'), 'ohmRelationSource': m.get('relationSource'),
            'ohmAdminLevel': m.get('admin_level'), 'ohmChangeset': m.get('changeset'), 'ohmTimestamp': m.get('timestamp'), 'ohmOverpassBase': m.get('osm_base'),
            'coastline': SRC_NE, 'licenseReview': None, 'trialWindow': WINDOW,
            'boundaryBasis': [BASIS[k] for k in d.get('basis', [])],
            'cutAgainst': {'higherPriority': d['cut_big'], 'sliversRemoved': d['cut_small']}}
by_old = {}
for d in done:
    if d.get('old'): by_old.setdefault(d['old']['id'], []).append(d)
n = 0; stats = {'retract': 0, 'new_replacement': 0, 'new_asia': 0}
def sov_req(d, ph, body_extra):
    global n
    n += 1
    feats.append({'type': 'Feature', 'id': ph, 'properties': {'slug': d['slug'], 'start': d['lo'], 'end': d['hi'], 'area_deg2': round(d['g'].area, 4)}, 'geometry': rnd(mapping(d['g']))})
    return {'_placeholder': ph, '_post': '/api/v1/sovereignty-records', '_geometryFrom': ph,
            '_meta': {'segOf': d['seg_of'], 'area_deg2': round(d['g'].area, 4)}, 'body': body_extra}
seq = 0
# 俄國與伊朗：每筆舊紀錄先撤回，再新增補完整的段
for oid, segs in sorted(by_old.items(), key=lambda kv: (kv[1][0]['slug'] not in RU_ZH or kv[1][0]['slug'].startswith('i'), kv[1][0]['lo'])):
    r = segs[0]['old']; seq += 1; iran = r['slug'] in IR_SLUGS
    who = RU_ZH[r['slug']]
    reason = (f"{who} {r['lo']}～{r['hi']}：原紀錄幾何被試驗框 box(-20,15,60,72) 裁在東經 60 度，" +
              ('伊朗東部（呼羅珊、錫斯坦—俾路支）缺漏' if iran else '中亞、西伯利亞、遠東全部缺漏') +
              '；改以同一或依指示更換的 OHM 固定版本補完整幾何，撤回後重新新增（russia-asia-1908-1937）。')
    write(R2, f'{seq:03d}a-retract-{r["slug"]}-{r["lo"]}.json', {'_placeholder': f'RETRACTED_RA_{oid.replace('-', '')[-12:]}', '_post': f'/api/v1/sovereignty-records/{oid}/retraction', '_meta': {'fix': True}, 'body': {'reason': reason}})
    stats['retract'] += 1
    for j, d in enumerate(sorted(segs, key=lambda x: x['lo'])):
        m = G[d['rid']][1]; same = d['rid'] == r['ohm_relation_id']
        prov = dict(r['provenance'] or {})
        prov.update({'replaces': oid, 'unclip': {'batch': 'russia-asia-1908-1937', 'frameRemoved': 'box(-20,15,60,72)',
                     'method': '框內幾何沿用原紀錄（換版段：新版框內幾何扣除原紀錄已扣掉的部分）；框外取同一 OHM 版本全球重組（Natural Earth 10m 陸地裁切；海岸簡化 0.02°，與鄰國陸界 0.05° 內用 0.0005° 原幾何）',
                     'ohmVersionChange': None if same else {'from': f"relation/{r['ohm_relation_id']} v{r['ohm_version']}", 'to': f"relation/{d['rid']} v{m['version']}"},
                     'arcticIslandsPatch': ('新地島、新西伯利亞群島取自 OHM relation/2851158 v122（此版漏列）' if d.get('arctic_patch') else None),
                     'boundaryBasis': [BASIS[k] for k in d.get('basis', [])],
                     'cutAgainst': {'higherPriority': d['cut_big'], 'sliversRemoved': d['cut_small']}}})
        if not same:
            prov.update({'memberWayLicense': m['memberWayLicense'], 'ohmChangeset': m.get('changeset'), 'ohmTimestamp': m.get('timestamp'), 'ohmFixme': m.get('fixme'), 'ohmAdminLevel': m.get('admin_level')})
        prov['trialWindow'] = WINDOW if not iran else prov.get('trialWindow')
        old_note = r['note'] or {}
        zh_add = f"（2026-11-01 修正：補回東經 60 度以東的幾何" + ('' if same else f"；本段依指示改用 OHM relation/{d['rid']} v{m['version']}") + ('；新地島、新西伯利亞群島依 2851158 補上' if d.get('arctic_patch') else '') + '。）'
        en_add = '(Fixed 2026-11-01: geometry east of 60°E restored' + ('' if same else f"; OHM relation/{d['rid']} v{m['version']} used for this segment") + '.)'
        if r['slug'] == 'russian-empire' and d['lo'] == '1908-10-05':
            note = {'zh-Hant': '起於 1908-10-05（本批起點，不是政權起日）。含芬蘭大公國（OHM 已含，未另立）；布哈拉、希瓦為俄國保護國，另列（非主權）。' + zh_add,
                    'en': 'From 5 Oct 1908 (start of this batch). Includes the Grand Duchy of Finland; Bukhara and Khiva are recorded separately as protectorates. ' + en_add}
        elif same:
            note = {'zh-Hant': (old_note.get('zh-Hant') or '') + zh_add, 'en': ((old_note.get('en') or '') + ' ' + en_add).strip()}
        else:
            note = {'zh-Hant': f"{who}，OHM relation/{d['rid']}（{m['start']}～{m['end']}）。" + zh_add, 'en': f"{m.get('name_en') or who}, OHM relation/{d['rid']}. " + en_add}
        ph = f"SOV_RA_RU_{d['lo'].replace('-', '')}" if not iran else f"SOV_RA_IR_{oid.replace('-', '')[-12:]}"
        body = {'regimeId': r['regime_id'], 'geometry': None, 'validPeriod': {'start': d['lo'], 'end': d['hi']}, 'layerStatus': r['layer_status'],
                'geometrySourceId': r['geometry_source_id'] if same else '{{SRC_OHM_RUASIA}}',
                'geometryLocator': (r['geometry_locator'] if same else f"relation/{d['rid']} v{m['version']}") + '（完整，不受東經 60 度框裁切）' + ('＋北極島嶼取自 relation/2851158 v122' if d.get('arctic_patch') else ''),
                'geometryLicense': r['geometry_license'], 'attribution': r['attribution'],
                'startEventId': E(d['sev']) if d['sev'] else None, 'endEventId': E(d['eev']) if d['eev'] else None,
                'ohmRelationId': d['rid'], 'ohmVersion': m['version'] if not same else r['ohm_version'],
                'ohmFetchedAt': (r['ohm_fetched_at'] if same else m['fetched']).replace('+00:00', 'Z'), 'ohmStartRaw': r['ohm_start_raw'] if same else m['start'], 'ohmEndRaw': r['ohm_end_raw'] if same else m['end'],
                'provenance': prov, 'note': note}
        write(R2, f'{seq:03d}b{j}-sovereignty-{r["slug"]}-{d["lo"]}.json', sov_req(d, ph, body)); stats['new_replacement'] += 1
# 亞洲鄰國新紀錄
for d in sorted([d for d in done if not d.get('old')], key=lambda x: (x['lo'], x['slug'])):
    seq += 1
    nsakh = d['slug'] == 'japanese-occupied-northern-sakhalin'
    m = G[d['rid']][1]
    prov = prov_common(d, m)
    if nsakh:
        m2 = G[2889779][1]; prov['derivation'] = f"relation/2851273 v{m['version']} − relation/2889779 v{m2['version']}（北緯 48～55、東經 140～146 範圍內）"
    loc = f"relation/{d['rid']} v{m['version']}" + (f" − relation/2889779 v{G[2889779][1]['version']}" if nsakh else '')
    nx = next(x for x in NEW if x[0] == d['seg_of'])
    nz, ne = nx[10] or '', nx[11] or ''
    if d['seg_of'] != d['key'] or (d['lo'], d['hi']) != next((x[2], x[3]) for x in NEW if x[0] == d['seg_of']):
        nz += f"（本段 {d['lo']}～{d['hi']}，依同期高優先紀錄切段）"
    body = {'regimeId': RG[d['slug']], 'geometry': None, 'validPeriod': {'start': d['lo'], 'end': d['hi']}, 'layerStatus': d['layer'],
            'geometrySourceId': '{{SRC_OHM_RUASIA}}', 'geometryLocator': loc, 'geometryLicense': 'cc0', 'attribution': None,
            'startEventId': E(d['sev']) if d['sev'] else None, 'endEventId': E(d['eev']) if d['eev'] else None,
            'ohmRelationId': d['rid'], 'ohmVersion': m['version'], 'ohmFetchedAt': m['fetched'], 'ohmStartRaw': m['start'], 'ohmEndRaw': m['end'],
            'provenance': prov, 'note': {'zh-Hant': nz.strip(), 'en': ne.strip()}}
    assert all(v == {'untagged(OHM CC0)'} or True for v in [set(m['memberWayLicense'])])
    assert set(m['memberWayLicense']) <= {'untagged(OHM CC0)', 'CC0'}, (d['slug'], m['memberWayLicense'])
    ph = f"SOV_RA_{d['seg_of']}_{d['lo'].replace('-', '')}"
    write(R2, f'{seq:03d}-sovereignty-{d["slug"]}-{d["lo"]}.json', sov_req(d, ph, body)); stats['new_asia'] += 1
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(HERE, '..', 'russia-asia-derived.geojson'), 'w'), ensure_ascii=False, separators=(',', ':'))
print(stats, 'files R1', len(os.listdir(R1)), 'R2', len(os.listdir(R2)))
