#!/usr/bin/env python3
"""tail-1945-09：第一階段終點 1945-09-30（憲法 Decision 3）。把 (b) 組 64 個政權在 1945-09-02／03 截止的主權紀錄，
連同佔領歸屬、首都，用原幾何延到 1945-10-01（exclusive）：先撤後增（I5，不刪除）。
從開發庫 5442（docker worldline-borders-dev-db）讀現有紀錄 → requests/*.json、tail-1945-09-derived.geojson、10-leaders.{dry,commit}.sql。
只讀資料庫；不連 API。用法：python3 build/make_requests.py
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(HERE, 'scope.json'), encoding='utf-8'))
END = '1945-10-01'
TAILS = ('1945-09-02', '1945-09-03')
REASON = '第一階段終點改為 1945-09-30（憲法 Decision 3）：原紀錄以批次終點 1945-09-02／03 截止（無迄事件），以原幾何延長到 1945-10-01 後重送（tail-1945-09）'
NOTE_ZH = '【tail-1945-09】延長至 1945-09-30（第一階段終點，憲法 Decision 3），幾何原樣。'
NOTE_EN = '[tail-1945-09] Extended to 30 Sep 1945 (end of phase 1); geometry unchanged.'
def q(sql):
    p = subprocess.run(['docker', 'exec', '-i', 'worldline-borders-dev-db', 'psql', '-U', 'worldline', '-d', 'worldline_borders_dev',
                        '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1'], input=sql, capture_output=True, text=True)
    if p.returncode: sys.exit(p.stderr)
    return json.loads(p.stdout.strip() or 'null') or []
slugs = "','".join(S['groupB'])
sov = q(f"""select json_agg(x order by x.slug) from (select s.id, r.slug, s.regime_id, lower(s.valid_period)::text lo, upper(s.valid_period)::text hi, s.layer_status,
  s.geometry_source_id, s.geometry_locator, s.geometry_license, s.attribution, s.start_event_id, s.ohm_relation_id, s.ohm_version, s.ohm_fetched_at,
  s.ohm_start_raw, s.ohm_end_raw, s.provenance, s.note, st_asgeojson(st_multi(s.geom), 15)::json geom
  from sovereignty_records s join regimes r on r.id=s.regime_id where s.retracted_at is null and r.slug in ('{slugs}')
  and upper(s.valid_period) in ('1945-09-02','1945-09-03')) x;""")
occ = q(f"""select json_agg(x order by x.slug) from (select o.id, r.slug, o.occupied_regime_id, o.occupier_regime_id, o.control_kind, lower(o.valid_period)::text lo,
  upper(o.valid_period)::text hi, o.basis_event_id, o.co_occupied, o.note from occupation_attributions o join regimes r on r.id=o.occupied_regime_id
  where o.retracted_at is null and r.slug in ('{slugs}') and upper(o.valid_period) in ('1945-09-02','1945-09-03')) x;""")
cslugs = "','".join(S['capitalsExtend'])
cap = q(f"""select json_agg(x order by x.slug) from (select c.id, r.slug, c.regime_id, c.city_name, st_asgeojson(c.location)::json loc, lower(c.valid_period)::text lo,
  upper(c.valid_period)::text hi, c.source_ref, c.note from capital_records c join regimes r on r.id=c.regime_id
  where c.retracted_at is null and r.slug in ('{cslugs}') and upper(c.valid_period) in ('1945-09-02','1945-09-03')) x;""")
lead = q(f"""select json_agg(x order by x.slug, x.role) from (select l.id, r.slug, l.role, l.name, lower(l.valid_period)::text lo, upper(l.valid_period)::text hi
  from leader_records l join regimes r on r.id=l.regime_id where l.retracted_at is null and r.slug in ('{slugs}') and upper(l.valid_period) in ('1945-09-02','1945-09-03')) x;""")
assert len(sov) == 64, len(sov)
os.makedirs(os.path.join(HERE, 'requests'), exist_ok=True)
for f in os.listdir(os.path.join(HERE, 'requests')): os.remove(os.path.join(HERE, 'requests', f))
def w(name, obj): json.dump(obj, open(os.path.join(HERE, 'requests', name), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
feats = []
for i, s in enumerate(sov, 1):
    w(f'10-{i:02d}a-retract-{s["slug"]}.json', {'_placeholder': f'RETRACTED_{s["id"]}', '_post': f'/api/v1/sovereignty-records/{s["id"]}/retraction',
       '_meta': {'fix': True, 'oldId': s['id']}, 'body': {'reason': REASON}})
    note = dict(s['note'] or {}); note['zh-Hant'] = (note.get('zh-Hant', '') + ' ' + NOTE_ZH).strip(); note['en'] = (note.get('en', '') + ' ' + NOTE_EN).strip()
    prov = dict(s['provenance'] or {}); prov['replaces'] = s['id']; prov['extendedBy'] = 'tail-1945-09'
    feats.append({'type': 'Feature', 'id': f'COPY_{s["id"]}', 'geometry': s['geom'], 'properties': {'slug': s['slug']}})
    w(f'10-{i:02d}b-sovereignty-{s["slug"]}.json', {'_placeholder': f'SOVP_TAIL_{s["slug"]}', '_post': '/api/v1/sovereignty-records', '_geometryFrom': f'COPY_{s["id"]}',
       'body': {'regimeId': s['regime_id'], 'geometry': None, 'validPeriod': {'start': s['lo'], 'end': END}, 'layerStatus': s['layer_status'],
                'geometrySourceId': s['geometry_source_id'], 'geometryLocator': s['geometry_locator'], 'geometryLicense': s['geometry_license'],
                'attribution': s['attribution'], 'startEventId': s['start_event_id'], 'endEventId': None, 'ohmRelationId': s['ohm_relation_id'],
                'ohmVersion': s['ohm_version'], 'ohmFetchedAt': s['ohm_fetched_at'], 'ohmStartRaw': s['ohm_start_raw'], 'ohmEndRaw': s['ohm_end_raw'],
                'provenance': prov, 'note': note}})
for i, o in enumerate(occ, 1):
    w(f'20-{i:02d}a-retract-occ-{o["slug"]}.json', {'_placeholder': f'RETRACTED_{o["id"]}', '_post': f'/api/v1/occupation-attributions/{o["id"]}/retraction',
       '_meta': {'fix': True, 'oldId': o['id']}, 'body': {'reason': REASON}})
    note = dict(o['note'] or {}); note['zh-Hant'] = (note.get('zh-Hant', '') + ' ' + NOTE_ZH).strip()
    w(f'20-{i:02d}b-occupation-{o["slug"]}.json', {'_placeholder': f'OCCP_TAIL_{o["slug"]}', '_post': '/api/v1/occupation-attributions',
       'body': {'occupiedRegimeId': o['occupied_regime_id'], 'occupierRegimeId': o['occupier_regime_id'], 'controlKind': o['control_kind'],
                'validPeriod': {'start': o['lo'], 'end': END}, 'basisEventId': o['basis_event_id'], 'coOccupied': o['co_occupied'], 'note': note}})
for i, c in enumerate(cap, 1):
    w(f'30-{i:02d}a-retract-cap-{c["slug"]}.json', {'_placeholder': f'RETRACTED_{c["id"]}', '_post': f'/api/v1/capital-records/{c["id"]}/retraction',
       '_meta': {'fix': True, 'oldId': c['id']}, 'body': {'reason': REASON}})
    w(f'30-{i:02d}b-capital-{c["slug"]}.json', {'_placeholder': f'CAP_TAIL_{c["slug"]}', '_post': '/api/v1/capital-records',
       'body': {'regimeId': c['regime_id'], 'cityName': c['city_name'], 'location': c['loc'], 'validStart': c['lo'], 'validEnd': END,
                'sourceRef': c['source_ref'], 'note': ((c['note'] or '') + ' ' + NOTE_ZH).strip()}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(HERE, 'tail-1945-09-derived.geojson'), 'w'))
# 領導人：API 沒有撤回端點，沿用既有做法（SQL 撤回＋同交易新增，欄位原樣、只改迄日）
ids = "','".join(l['id'] for l in lead)
body = f"""\\set ON_ERROR_STOP 1
BEGIN;
CREATE TEMP TABLE t_old ON COMMIT DROP AS SELECT * FROM leader_records WHERE id IN ('{ids}') AND retracted_at IS NULL;
UPDATE leader_records SET retracted_at=now(), retraction_reason='{REASON}' WHERE id IN (SELECT id FROM t_old);
INSERT INTO leader_records(id,regime_id,name,name_zh,role,title,valid_period,source,source_url,verified,person_id)
  SELECT uuidv7(),regime_id,name,name_zh,role,title,daterange(lower(valid_period),'{END}','[)'),source,source_url,verified,person_id FROM t_old;
SELECT 'LEADERS', (SELECT count(*) FROM t_old) retracted, (SELECT count(*) FROM leader_records WHERE retracted_at IS NULL AND upper(valid_period)='{END}' AND (regime_id,role,name) IN (SELECT regime_id,role,name FROM t_old)) active_extended;
"""
open(os.path.join(HERE, '40-leaders.dry.sql'), 'w').write(body + 'ROLLBACK;\n')
open(os.path.join(HERE, '40-leaders.commit.sql'), 'w').write(body + 'COMMIT;\n')
json.dump({'sovereignty': len(sov), 'occupation': len(occ), 'capitals': len(cap), 'leaders': len(lead),
           'leaderList': [(l['slug'], l['role'], l['name'][:40]) for l in lead]}, open(os.path.join(HERE, 'qa.json'), 'w'), ensure_ascii=False, indent=1)
print('sov', len(sov), 'occ', len(occ), 'cap', len(cap), 'leaders', len(lead))
