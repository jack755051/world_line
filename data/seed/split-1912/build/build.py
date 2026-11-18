#!/usr/bin/env python3
"""把「只靠 1910 年前後的地圖集就標成已查證、期間卻延續到 1912 年以後」的主權紀錄在 1912-01-01 切成兩段。只讀開發庫。
依據：憲法 I1「一段出處不該撐起整段未經核實的期間」；Tai 2026-11-14 決定切段，切點 1912-01-01（兩套地圖集畫的是 1910 年，最晚一套 1911 年出版）。
對象：未撤回、可信程度的依據是 record_citation_two_b_families、引文全部來自地圖集（Shepherd 1911、劍橋近代史地圖集）、而且結束日晚於 1912-01-01 的紀錄。
      另有 A 級文件出處或已查證起始事件的紀錄不在此列（條約、裁決等確立的是一段期間的狀態，不是某一年的快照）。
每一筆：撤回 → 新增前段 [起, 1912-01-01)（欄位照舊，引文接到這一段）→ 新增後段 [1912-01-01, 迄)（形狀相同，沒有引文）。
後段的來歷由 apply_links.py 寫成 beyond_source：形狀沿用前段，但不沿用前段的已查證。
用法：python3 -I build/build.py   （輸出 requests/*.json、split-1912-derived.geojson（不進版本庫，可由此腳本重建）、build/records.json）
"""
import json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
CUT = '1912-01-01'
def q(sql):
    r = subprocess.run(['docker', 'exec', 'worldline-borders-dev-db', 'psql', '-X', '-U', 'worldline', '-d', 'worldline_borders_dev', '-At', '-c', sql], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr[-800:])
    return r.stdout.strip()
LIST = os.path.join(HERE, 'records.json')
if os.path.exists(LIST):   # 已選定的對象（第一次執行時由下面的查詢選出並存檔；之後重建以存檔為準，因為原紀錄已撤回）
    targets = [x['id'] for x in json.load(open(LIST))]
else:
    targets = q(f"""
      with atlas as (select id from sources where title = 'Historical Atlas' or title ~ 'Cambridge Modern History Atlas'),
           rc as (select record_id, count(*) n, count(*) filter (where source_id in (select id from atlas)) n_atlas from sovereignty_record_citations where retracted_at is null group by 1)
      select r.id from sovereignty_records r join rc on rc.record_id = r.id join v_record_confidence c on c.record_kind = 'sovereignty' and c.record_id = r.id
      where r.retracted_at is null and c.basis = 'record_citation_two_b_families' and rc.n = rc.n_atlas and lower(r.valid_period) < date '{CUT}'
        and (upper(r.valid_period) > date '{CUT}' or upper(r.valid_period) is null)
      order by r.id""").split()
recs, feats = [], []
def write(name, obj): json.dump(obj, open(os.path.join(ROOT, 'requests', name), 'w'), ensure_ascii=False, indent=1)
for old in os.listdir(os.path.join(ROOT, 'requests')): os.remove(os.path.join(ROOT, 'requests', old))
for n, rid in enumerate(targets, 1):
    r = json.loads(q(f"""select row_to_json(t) from (select g.slug, r.regime_id, lower(r.valid_period) lo, upper(r.valid_period) hi, r.layer_status, r.start_event_id, r.end_event_id, r.geometry_source_id, r.geometry_locator,
        r.geometry_license, r.attribution, r.ohm_relation_id, r.ohm_version, r.ohm_fetched_at, r.ohm_start_raw, r.ohm_end_raw, r.provenance, r.note, st_asgeojson(r.geom, 9)::json geom,
        (select json_agg(json_build_object('sourceId', c.source_id, 'locator', c.locator, 'evidenceNote', c.evidence_note, 'grade', c.grade, 'gradeBasis', c.grade_basis) order by c.created_at, c.id)
           from sovereignty_record_citations c where c.record_id = r.id and c.retracted_at is null) cites,
        (select json_agg(json_build_object('kind', l.kind, 'startEventId', l.start_event_id, 'precision', l.start_date_precision)) from sovereignty_record_links l where l.record_id = r.id and l.retracted_at is null) links
        from sovereignty_records r join regimes g on g.id = r.regime_id where r.id = '{rid}') t"""))
    assert r['start_event_id'] is None and not any(l['startEventId'] or l['precision'] for l in (r['links'] or [])), (r['slug'], '有起始事件或日期精度，需另外處理')
    tag = f'{n:02d}'; gid = 'S_' + rid; feats.append({'type': 'Feature', 'id': gid, 'properties': {}, 'geometry': r['geom']})
    recs.append({'id': rid, 'slug': r['slug'], 'lo': r['lo'], 'hi': r['hi'], 'citations': len(r['cites'] or []), 'endEvent': r['end_event_id']})
    write(f'{tag}a-retract.json', {'_placeholder': f'RETRACTED_{tag}', '_post': f'/api/v1/sovereignty-records/{rid}/retraction', '_meta': {'fix': True, 'slug': r['slug']}, 'body': {
        'reason': f"{r['slug']} {r['lo']}～{r['hi']}：出處是 1910 年前後的地圖集，只能證明那幾年；在 {CUT} 切成兩段，後段不沿用前段的已查證（憲法 I1；split-1912）。"}})
    def body(a, b, start_ev, end_ev, zh, en, part):
        prov = dict(r['provenance'] or {}); prov['split'] = {'batch': 'split-1912', 'replaces': rid, 'cut': CUT, 'part': part}
        note = dict(r['note'] or {})
        note = {'zh-Hant': ((note.get('zh-Hant') or '') + zh).strip(), 'en': ((note.get('en') or '') + ' ' + en).strip()}
        return {'regimeId': r['regime_id'], 'geometry': None, 'validPeriod': {'start': a, 'end': b}, 'layerStatus': r['layer_status'], 'geometrySourceId': r['geometry_source_id'],
                'geometryLocator': r['geometry_locator'], 'geometryLicense': r['geometry_license'], 'attribution': r['attribution'], 'startEventId': start_ev, 'endEventId': end_ev,
                'ohmRelationId': r['ohm_relation_id'], 'ohmVersion': r['ohm_version'], 'ohmFetchedAt': r['ohm_fetched_at'], 'ohmStartRaw': r['ohm_start_raw'], 'ohmEndRaw': r['ohm_end_raw'], 'provenance': prov, 'note': note}
    write(f'{tag}b-sovereignty-early.json', {'_placeholder': f'EARLY_{tag}', '_post': '/api/v1/sovereignty-records', '_geometryFrom': gid, '_meta': {'replaces': rid, 'slug': r['slug']},
          'body': body(r['lo'], CUT, None, None, f'（{CUT} 是資料分段日，不是疆界變動：這一段有 1910 年前後地圖集的出處，之後那一段還沒有。）', f'(Split at {CUT} for sourcing only, not a border change: this part is supported by atlases of about 1910.)', 'early')})
    write(f'{tag}c-sovereignty-late.json', {'_placeholder': f'LATE_{tag}', '_post': '/api/v1/sovereignty-records', '_geometryFrom': gid, '_meta': {'replaces': rid, 'slug': r['slug']},
          'body': body(CUT, r['hi'], None, r['end_event_id'], f'（{CUT} 是資料分段日，不是疆界變動：形狀沿用前一段；前一段的出處是 1910 年前後的地圖集，證明不到這一段，這一段待查證。）', f'(Split at {CUT} for sourcing only, not a border change: same shape as the preceding part, whose atlas sources of about 1910 do not reach this period.)', 'late')})
    for k, c in enumerate(r['cites'] or [], 1):
        write(f'{tag}d-citation-{k}.json', {'_placeholder': f'CITE_{tag}_{k}', '_post': '/api/v1/sovereignty-records/{{EARLY_%s}}/citations' % tag, 'body': c})
if not os.path.exists(LIST): json.dump(recs, open(LIST, 'w'), ensure_ascii=False, indent=1)
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(ROOT, 'split-1912-derived.geojson'), 'w'), separators=(',', ':'))
print(len(recs), 'records;', len(os.listdir(os.path.join(ROOT, 'requests'))), 'requests;', sum(x['citations'] for x in recs), 'citations')
