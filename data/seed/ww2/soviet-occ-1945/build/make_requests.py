#!/usr/bin/env python3
"""soviet-occ-1945：新政權 soviet-occupied-karafuto-kurils（非主權），南樺太 08-25、千島（擇捉以北）08-31、國後／色丹／齒舞 09-05 起；
從 empire-of-japan 對應段扣出（Tai 2026-11-05 16:39 同意）。只讀資料庫；產生 requests/*.json、soviet-occ-1945-derived.geojson、qa.json。"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
END = '1945-10-01'; TAG = 'soviet-occ-1945'; REQ = os.path.join(HERE, 'requests')
def q(sql):
    p = subprocess.run(['docker', 'exec', '-i', 'worldline-borders-dev-db', 'psql', '-U', 'worldline', '-d', 'worldline_borders_dev', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1'], input=sql, capture_output=True, text=True)
    if p.returncode: sys.exit(p.stderr)
    return json.loads(p.stdout.strip() or 'null')
JP_A = '01a1aacc-b342-7718-a9e1-9f9c9e64e421'; JP_B = '01a1aacc-b373-7251-9893-09c343ac4727'
SU = '01a18e71-cc2e-7f80-8d62-81879da43d7b'; JAPAN = '01a191c9-07d8-7a6d-969f-c702cc8df64c'; FRUS6 = '01a191c9-07ce-7ff2-9c26-0a20ea97757f'
def sov(i):
    return q(f"""select row_to_json(x) from (select s.id, s.regime_id, lower(s.valid_period)::text lo, upper(s.valid_period)::text hi, s.layer_status, s.geometry_source_id, s.geometry_locator,
      s.geometry_license, s.attribution, s.start_event_id, s.end_event_id, s.ohm_relation_id, s.ohm_version, s.ohm_fetched_at, s.ohm_start_raw, s.ohm_end_raw, s.provenance, s.note
      from sovereignty_records s where s.id='{i}' and s.retracted_at is null) x;""")
A, B = sov(JP_A), sov(JP_B)
if not A or not B: sys.exit('日本紀錄已變動')
K = "st_y(st_centroid(d.geom))>45.8 and st_x(st_centroid(d.geom))<145"
N = "st_x(st_centroid(d.geom))>=146.5 and st_y(st_centroid(d.geom))>=44.3"
S = "st_x(st_centroid(d.geom)) between 145.85 and 146.95 and st_y(st_centroid(d.geom)) between 43.35 and 44.6 and st_area(d.geom::geography)<5e9"
def piece(rid, cond, keep):
    return q(f"select st_asgeojson(st_multi(st_collect(d.geom)),15)::json from sovereignty_records s, st_dump(s.geom) d where s.id='{rid}' and {'' if keep else 'not '}({cond})")
def area(cond, rid=JP_A):
    return q(f"select json_agg(json_build_array(round(st_x(st_centroid(d.geom))::numeric,3), round(st_y(st_centroid(d.geom))::numeric,3), round((st_area(d.geom::geography)/1e6)::numeric,2))) from sovereignty_records s, st_dump(s.geom) d where s.id='{rid}' and ({cond})")
DER = {
 'D_SOV_K': (piece(JP_A, K, True), '南樺太（含海馬島）：empire-of-japan 幾何中質心北緯 45.8 度以北、東經 145 度以西的多邊形'),
 'D_SOV_KN': (piece(JP_A, f"({K}) or ({N})", True), '南樺太＋千島（得撫以北至占守，及擇捉）：質心東經 146.5、北緯 44.3 以上的多邊形'),
 'D_SOV_KNS': (piece(JP_A, f"({K}) or ({N}) or ({S})", True), '南樺太＋全千島＋國後、色丹、齒舞群島（水晶、勇留、志發、多樂）'),
 'D_JP_0825': (piece(JP_A, K, False), f'empire-of-japan {JP_A} − D_SOV_K'),
 'D_JP_0831': (piece(JP_A, f"({K}) or ({N})", False), f'empire-of-japan {JP_A} − D_SOV_KN'),
 'D_JP_0905': (piece(JP_A, f"({K}) or ({N}) or ({S})", False), f'empire-of-japan {JP_A} − D_SOV_KNS'),
 'D_JP_0908': (piece(JP_B, f"({K}) or ({N}) or ({S})", False), f'empire-of-japan {JP_B} − D_SOV_KNS'),
}
os.makedirs(REQ, exist_ok=True)
for f in os.listdir(REQ): os.remove(os.path.join(REQ, f))
def w(n, o): json.dump(o, open(os.path.join(REQ, n), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
feats = [{'type': 'Feature', 'id': k, 'geometry': v[0], 'properties': {'derivation': v[1]}} for k, v in DER.items()]
feats.append({'type': 'Feature', 'id': 'COPY_' + JP_A, 'geometry': q(f"select st_asgeojson(st_multi(geom),15)::json from sovereignty_records where id='{JP_A}'"), 'properties': {}})
DATES = {
 'karafuto': '1945-08-25：蘇軍佔領樺太廳所在地豐原，南樺太作戰（08-11～08-25）結束；俄羅斯總統圖書館 prlib.ru/history/1172670；北海道大學 HUSCAP《北方人文研究》12 號（2019）Vishnevsky 報告（08-22 知取停戰協定、08-25 進入豐原、大泊登陸）。B 級',
 'kurils_n': '1945-08-31：「8月31日までに千島列島の南端である得撫島まで占領を完了」；擇捉 08-28 — 內閣府北方對策本部「歴史」（引外務省『われらの北方領土』）https://www8.cao.go.jp/hoppo/mondai/02.html。A 級（日本政府）',
 'kurils_s': '1945-09-05：「8月28日から遅くとも9月5日までの間に、北方四島を占領」— 外務省「北方領土問題の経緯（領土問題の発生まで）」https://www.mofa.go.jp/mofaj/area/hoppo/hoppo_keii.html；國後、色丹、齒舞 09-01～09-05（內閣府北方對策本部）。A 級（日本政府）',
}
nz = lambda n, zh, en: {**(n or {}), 'zh-Hant': ((n or {}).get('zh-Hant', '') + ' ' + zh).strip(), 'en': ((n or {}).get('en', '') + ' ' + en).strip()}
REASON = f'Tai 2026-11-05 16:39 同意新建蘇軍佔領南樺太、千島的非主權政權：empire-of-japan 對應段扣出該地區；先撤回、再重寫（{TAG}）'
w('00-01-source-mofa-hoppo-keii.json', {'_placeholder': 'SRC_MOFA_HOPPO', '_post': '/api/v1/sources', 'body': {'sourceKind': 'official_record', 'title': '北方領土問題の経緯（領土問題の発生まで）',
   'publisher': '外務省（日本国）', 'publishedText': '外務省ウェブサイト（2026-11-05 閲覧）', 'licenseCode': 'cc_by', 'licenseEvidenceUrl': 'https://www.mofa.go.jp/mofaj/annai/legalmatters/index.html',
   'url': 'https://www.mofa.go.jp/mofaj/area/hoppo/hoppo_keii.html', 'note': '公共データ利用規約（第1.0版）（PDL1.0）適用，與 CC BY 4.0 相容（外務省「法的事項」）。出典：外務省ウェブサイト。'}})
w('00-02-regime-soviet-occupied-karafuto-kurils.json', {'_placeholder': 'REGIME_SOVOCC_KK', '_post': '/api/v1/regimes', '_meta': {'priorPlaceholder': False, 'nameSource': 'FRUS 1945 VI Doc. 437（General Order No. 1 1(b) Karafuto）、Doc. 450（千島）'},
   'body': {'slug': 'soviet-occupied-karafuto-kurils', 'names': [{'nameKind': 'self', 'originalText': 'Soviet-occupied South Sakhalin (Karafuto) and Kuril Islands', 'originalLang': 'en',
     'display': {'zh-Hant': '蘇聯佔領下的南樺太與千島群島', 'en': 'Soviet-occupied South Sakhalin (Karafuto) and Kuril Islands'}, 'isPrimary': True}]}})
w('00-03-event-soviet-occupation-karafuto-kurils.json', {'_placeholder': 'EV_SOVOCC_KK', '_post': '/api/v1/events', '_meta': {'verification': 'verified'},
   'body': {'eventKind': 'campaign', 'occurred': {'start': '1945-08-25', 'end': '1945-09-06'}, 'datePrecision': 'day',
     'summary': {'zh-Hant': '蘇軍完成佔領南樺太（08-25）與千島群島（08-31 得撫以北及擇捉；09-05 國後、色丹、齒舞）', 'en': 'Soviet forces complete the occupation of South Sakhalin (25 Aug) and the Kuril Islands (by 31 Aug north of and incl. Etorofu; by 5 Sep Kunashiri, Shikotan, Habomai)'},
     'participants': [{'regimeId': SU, 'role': 'other'}, {'regimeId': JAPAN, 'role': 'other'}, {'regimeId': '{{REGIME_SOVOCC_KK}}', 'role': 'other'}],
     'citations': [
       {'sourceId': FRUS6, 'locator': 'Doc. 437, pp. 658–659（Enclosure A, General Order No. 1, 1 b）', 'evidenceNote': '一般命令第一號草案：滿洲、北緯 38 度以北朝鮮及樺太的日軍向蘇聯遠東軍總司令投降。'},
       {'sourceId': FRUS6, 'locator': 'Doc. 450, pp. 667–668', 'evidenceNote': '史達林 1945-08-16 致杜魯門：要求把全部千島群島列入向蘇軍投降的區域。'},
       {'sourceId': '{{SRC_MOFA_HOPPO}}', 'locator': '「ポツダム宣言（1945年8月受諾）」項', 'evidenceNote': 'ソ連は…8月28日から遅くとも9月5日までの間に、北方四島を占領しました（無血占領）。'}],
     'timeNote': {'zh-Hant': '南樺太 08-25 依俄羅斯總統圖書館與北海道大學 HUSCAP（08-22 知取停戰、08-24～25 進入豐原、08-25 大泊）；千島 08-18 占守登陸，08-31 前占領至得撫、08-28 擇捉，09-01～09-05 國後、色丹、齒舞（內閣府北方對策本部引外務省『われらの北方領土』）。分段日取各地區「佔領完成」日。',
                  'en': 'South Sakhalin 25 Aug (Presidential Library of Russia; HUSCAP); Kurils: landing on Shumshu 18 Aug, occupied to Urup by 31 Aug, Etorofu 28 Aug, Kunashiri/Shikotan/Habomai 1–5 Sep (Cabinet Office of Japan, MOFA). Segment dates are completion dates.'}}})
w('10-01a-retract-empire-of-japan-0824.json', {'_placeholder': f'RETRACTED_{JP_A}', '_post': f'/api/v1/sovereignty-records/{JP_A}/retraction', '_meta': {'fix': True, 'oldId': JP_A}, 'body': {'reason': REASON}})
w('10-02a-retract-empire-of-japan-0908.json', {'_placeholder': f'RETRACTED_{JP_B}', '_post': f'/api/v1/sovereignty-records/{JP_B}/retraction', '_meta': {'fix': True, 'oldId': JP_B}, 'body': {'reason': REASON}})
def body(base, lo, hi, gid, zh, en, ds, start_event, regime=None, layer=None):
    prov = dict(base['provenance'] or {}); prov.update({'batch': TAG, 'geometryFrom': base['id']})
    if regime: prov.pop('replaces', None); prov['derivedFromRecord'] = base['id']
    else: prov['replaces'] = base['id']
    if gid in DER: prov['derivation'] = DER[gid][1]
    if ds: prov['dateSource'] = ds
    return {'regimeId': regime or base['regime_id'], 'geometry': None, 'validPeriod': {'start': lo, 'end': hi}, 'layerStatus': layer or base['layer_status'],
            'geometrySourceId': base['geometry_source_id'], 'geometryLocator': base['geometry_locator'], 'geometryLicense': base['geometry_license'], 'attribution': base['attribution'],
            'startEventId': start_event, 'endEventId': None, 'ohmRelationId': base['ohm_relation_id'], 'ohmVersion': base['ohm_version'], 'ohmFetchedAt': base['ohm_fetched_at'],
            'ohmStartRaw': base['ohm_start_raw'], 'ohmEndRaw': base['ohm_end_raw'], 'provenance': prov, 'note': nz({} if regime else base['note'], f'【{TAG}】{zh}', f'[{TAG}] {en}')}
J = [('1945-08-24', '1945-08-25', 'COPY_' + JP_A, A, '08-24～08-25 幾何同前。', 'Unchanged 24–25 Aug.', None, A['start_event_id']),
     ('1945-08-25', '1945-08-31', 'D_JP_0825', A, '1945-08-25 起扣掉南樺太（蘇軍佔領，另立非主權政權）。', 'From 25 Aug excluding South Sakhalin (Soviet-occupied).', DATES['karafuto'], '{{EV_SOVOCC_KK}}'),
     ('1945-08-31', '1945-09-05', 'D_JP_0831', A, '1945-08-31 起再扣掉千島（得撫以北至占守，及擇捉）。', 'From 31 Aug also excluding the Kurils north of and incl. Etorofu.', DATES['kurils_n'], '{{EV_SOVOCC_KK}}'),
     ('1945-09-05', '1945-09-08', 'D_JP_0905', A, '1945-09-05 起再扣掉國後、色丹、齒舞群島。', 'From 5 Sep also excluding Kunashiri, Shikotan and the Habomai Islands.', DATES['kurils_s'], '{{EV_SOVOCC_KK}}'),
     ('1945-09-08', END, 'D_JP_0908', B, '1945-09-08 起扣掉北緯 38 度以南朝鮮（USAMGIK）與蘇軍佔領的南樺太、千島。', 'From 8 Sep excluding Korea south of 38°N (USAMGIK) and Soviet-occupied South Sakhalin and Kurils.', DATES['kurils_s'], B['start_event_id'])]
for i, (lo, hi, gid, base, zh, en, ds, ev) in enumerate(J, 3):
    w(f'10-{i:02d}b-sovereignty-empire-of-japan-{lo}.json', {'_placeholder': f'SOVP_SO_japan_{lo}', '_post': '/api/v1/sovereignty-records', '_geometryFrom': gid, 'body': body(base, lo, hi, gid, zh, en, ds, ev)})
SO = [('1945-08-25', '1945-08-31', 'D_SOV_K', '非主權：蘇軍佔領下的南樺太（08-25 佔領豐原、作戰結束）。法理上仍屬日本，1946-02-02 蘇聯才宣布併入。', 'Not sovereign: Soviet-occupied South Sakhalin.', DATES['karafuto']),
      ('1945-08-31', '1945-09-05', 'D_SOV_KN', '非主權：南樺太＋千島（08-31 前佔領至得撫，擇捉 08-28）。', 'Not sovereign: South Sakhalin and the Kurils north of and incl. Etorofu.', DATES['kurils_n']),
      ('1945-09-05', END, 'D_SOV_KNS', '非主權：南樺太＋全部千島，含國後、色丹、齒舞群島（遲至 09-05 佔領完畢）。', 'Not sovereign: South Sakhalin and all Kurils incl. Kunashiri, Shikotan, Habomai.', DATES['kurils_s'])]
for i, (lo, hi, gid, zh, en, ds) in enumerate(SO, 8):
    w(f'10-{i:02d}b-sovereignty-soviet-occupied-karafuto-kurils-{lo}.json', {'_placeholder': f'SOVP_SO_kk_{lo}', '_post': '/api/v1/sovereignty-records', '_geometryFrom': gid,
       'body': body(A, lo, hi, gid, zh, en, ds, '{{EV_SOVOCC_KK}}', regime='{{REGIME_SOVOCC_KK}}', layer='not_sovereign')})
w('20-01-occupation-soviet-occupied-karafuto-kurils.json', {'_placeholder': 'OCCP_SO_kk', '_post': '/api/v1/occupation-attributions', 'body': {'occupiedRegimeId': '{{REGIME_SOVOCC_KK}}', 'occupierRegimeId': SU,
   'controlKind': 'military_administration', 'validPeriod': {'start': '1945-08-25', 'end': END}, 'basisEventId': '{{EV_SOVOCC_KK}}', 'coOccupied': False,
   'note': {'zh-Hant': f'【{TAG}】蘇軍軍事佔領（09-17 起豐原設南樺太民政局；1946-02-02 宣布併入）。', 'en': f'[{TAG}] Soviet military occupation (civil administration at Toyohara from 17 Sep 1945; annexed 2 Feb 1946).'}}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(HERE, f'{TAG}-derived.geojson'), 'w'))
ar = lambda g: q(f"select round((st_area(st_geomfromgeojson('{json.dumps(g)}')::geography)/1e6)::numeric,1)")
qa = {'areasKm2': {k: ar(v[0]) for k, v in DER.items()}, 'piecesK': area(K), 'piecesN': area(N), 'piecesS': area(S), 'requests': len(os.listdir(REQ))}
json.dump(qa, open(os.path.join(HERE, 'qa.json'), 'w'), ensure_ascii=False, indent=1); print(json.dumps(qa, ensure_ascii=False))
