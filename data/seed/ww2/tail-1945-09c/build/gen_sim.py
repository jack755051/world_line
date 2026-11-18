#!/usr/bin/env python3
"""把 requests/*.json 原樣轉成 SQL，在單一交易中模擬整批寫入＋QA，最後 ROLLBACK（不改資料）。輸出 sim.dry.sql。"""
import glob, json, os, re, uuid
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
geoms = {f['id']: f['geometry'] for f in json.load(open(os.path.join(HERE, 'tail-1945-09c-derived.geojson')))['features']}
L = lambda s: "NULL" if s is None else "'" + str(s).replace("'", "''") + "'"
J = lambda o: "NULL" if o is None else L(json.dumps(o, ensure_ascii=False)) + "::jsonb"
ph = {}
out = ["\\set ON_ERROR_STOP 1", "BEGIN;"]
QA = open(os.path.join(HERE, 'build', 'qa.sql')).read()
out.append(QA.replace('@@', 'BEFORE'))
for p in sorted(glob.glob(os.path.join(HERE, 'requests', '*.json'))):
    r = json.load(open(p, encoding='utf-8')); post = r['_post']; b = r['body']
    raw = json.dumps(b, ensure_ascii=False)
    for m in set(re.findall(r'\{\{(\w+)\}\}', raw)): raw = raw.replace('{{%s}}' % m, ph[m])
    b = json.loads(raw); name = os.path.basename(p)
    m = re.match(r'/api/v1/([a-z-]+)/([0-9a-f-]+)/retraction$', post)
    if m:
        tbl = {'sovereignty-records': 'sovereignty_records', 'occupation-attributions': 'occupation_attributions', 'capital-records': 'capital_records'}[m.group(1)]
        out.append(f"DO $$ BEGIN UPDATE {tbl} SET retracted_at=now(), retraction_reason={L(b['reason'])} WHERE id='{m.group(2)}' AND retracted_at IS NULL; IF NOT FOUND THEN RAISE EXCEPTION 'retract miss {name}'; END IF; END $$;")
        continue
    nid = str(uuid.uuid4()); ph[r['_placeholder']] = nid
    if post == '/api/v1/regimes':
        out.append(f"INSERT INTO regimes(id,slug,wikidata_qid) VALUES ('{nid}',{L(b['slug'])},{L(b.get('wikidataQid'))});")
        for n in b['names']:
            out.append(f"INSERT INTO regime_names(regime_id,name_kind,original_text,original_lang,display,is_primary) VALUES ('{nid}',{L(n['nameKind'])},{L(n['originalText'])},{L(n['originalLang'])},{J(n['display'])},{str(n['isPrimary']).lower()});")
    elif post == '/api/v1/events':
        o = b['occurred']; out.append(f"INSERT INTO historical_events(id,event_kind,summary,occurred,date_precision,time_note) VALUES ('{nid}',{L(b['eventKind'])},{J(b['summary'])},daterange('{o['start']}','{o['end']}','[)'),{L(b['datePrecision'])},{J(b.get('timeNote'))});")
    elif post == '/api/v1/sovereignty-records':
        g = json.dumps(geoms[r['_geometryFrom']]); v = b['validPeriod']
        out.append(f"""INSERT INTO sovereignty_records(id,regime_id,geom,valid_period,layer_status,start_event_id,end_event_id,geometry_source_id,geometry_locator,geometry_license,attribution,ohm_relation_id,ohm_version,ohm_fetched_at,ohm_start_raw,ohm_end_raw,provenance,note)
 VALUES ('{nid}','{b['regimeId']}',ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON('{g}'),4326)),daterange('{v['start']}','{v['end']}','[)'),{L(b['layerStatus'])},{L(b['startEventId'])},{L(b['endEventId'])},{L(b['geometrySourceId'])},{L(b['geometryLocator'])},{L(b['geometryLicense'])},{L(b['attribution'])},{b['ohmRelationId'] if b['ohmRelationId'] is not None else 'NULL'},{b['ohmVersion'] if b['ohmVersion'] is not None else 'NULL'},{L(b['ohmFetchedAt'])},{L(b['ohmStartRaw'])},{L(b['ohmEndRaw'])},{J(b['provenance'])},{J(b['note'])});""")
    elif post == '/api/v1/occupation-attributions':
        v = b['validPeriod']
        out.append(f"INSERT INTO occupation_attributions(id,occupied_regime_id,occupier_regime_id,control_kind,valid_period,basis_event_id,co_occupied,note) VALUES ('{nid}','{b['occupiedRegimeId']}','{b['occupierRegimeId']}',{L(b['controlKind'])},daterange('{v['start']}','{v['end']}','[)'),{L(b['basisEventId'])},{str(b['coOccupied']).lower()},{J(b['note'])});")
    elif post == '/api/v1/capital-records':
        out.append(f"INSERT INTO capital_records(id,regime_id,city_name,location,valid_period,source_ref,note) VALUES ('{nid}','{b['regimeId']}',{J(b['cityName'])},ST_SetSRID(ST_GeomFromGeoJSON('{json.dumps(b['location'])}'),4326),daterange('{b['validStart']}','{b['validEnd']}','[)'),{L(b['sourceRef'])},{L(b['note'])});")
    else: raise SystemExit('unknown ' + post)
lead = open(os.path.join(HERE, '40-leaders.dry.sql')).read().replace('\\set ON_ERROR_STOP 1\n', '').replace('BEGIN;\n', '').replace('ROLLBACK;\n', '').replace('ON COMMIT DROP', '')
out.append(lead)
out.append(QA.replace('@@', 'AFTER'))
out.append('ROLLBACK;')
open(os.path.join(HERE, 'sim.dry.sql'), 'w').write('\n'.join(out) + '\n')
print('sim.dry.sql', sum(len(x) for x in out))
