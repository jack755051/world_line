#!/usr/bin/env python3
"""修正兩個舊資料問題（DRAFT，待 Tai 檢查）：
(1) 維琪法國 [1940-06-25, 1942-11-11) 含阿爾及利亞北部 → 拆在 1942-11-08（盟軍登陸法屬北非）：
    之前照舊含阿爾及利亞（當時是法國本土的省份，依事實國界）；11-08 起阿爾及利亞改為「盟軍佔領下的法屬北非」非主權。
(2) 荷蘭、挪威、丹麥的舊紀錄跨過整個戰爭都是主權 → 自各自被佔領日起改為非主權。
規則：舊紀錄只撤回不刪除；幾何沿用舊紀錄（old-records.json 是撤回前從開發庫匯出的快照，含已裁切的幾何）；
引用只用已核頁的 FRUS（history.state.gov pg_N）與 NCA（紙本頁碼）；找不到出處的事件不附引用 → 待查證。
"""
import json, os, datetime
from shapely.geometry import shape, mapping, box, MultiPolygon, Polygon
from shapely.validation import make_valid
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); OUT = os.path.join(ROOT, 'requests')
OLD = {r['slug']: r for r in json.load(open(os.path.join(ROOT, 'old-records.json')))}

def write(name, ph, post, body, meta=None, geom=None):
    req = {'_placeholder': ph, '_post': post, **({'_geometryFrom': geom} if geom else {}), **({'_meta': meta} if meta else {}), 'body': body}
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')

def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x, 'geoms', []) for p in polys(y)]
def mp(x): return MultiPolygon([p for p in polys(make_valid(x)) if p.area > 1e-5])

# ---- 幾何 ----
vichy = OLD['french-state-vichy']; g_vichy = make_valid(shape(vichy['geometry']))
SOUTH = box(-12, 34, 42, 40)  # 北緯 40 度以南＝阿爾及利亞北部（框架南界 34°N；科西嘉南端 41.3°N 不受影響）
geoms = {
    'FIX_VICHY_FULL': mp(g_vichy),
    'FIX_VICHY_EU': mp(g_vichy.difference(SOUTH)),
    'FIX_ALGERIA': mp(g_vichy.intersection(SOUTH)),
    'FIX_NL': mp(shape(OLD['kingdom-of-the-netherlands']['geometry'])),
    'FIX_NO': mp(shape(OLD['kingdom-of-norway']['geometry'])),
    'FIX_DK': mp(shape(OLD['kingdom-of-denmark']['geometry'])),
}
assert geoms['FIX_VICHY_EU'].intersection(geoms['FIX_ALGERIA']).area < 1e-6
assert abs(geoms['FIX_VICHY_EU'].area + geoms['FIX_ALGERIA'].area - geoms['FIX_VICHY_FULL'].area) < 1e-3
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in geoms.items()]},
          open(os.path.join(ROOT, 'borders-1942-fix-derived.geojson'), 'w'), separators=(',', ':'))
qa = {k: {'area_deg2': round(v.area, 3), 'bounds': [round(b, 2) for b in v.bounds]} for k, v in geoms.items()}
json.dump(qa, open(os.path.join(ROOT, 'qa.json'), 'w'), indent=1)

# ---- 來源 ----
write('01-source-01-src_nca_viii.json', 'SRC_NCA_VIII', '/api/v1/sources', {
    'sourceKind': 'official_record',
    'title': 'Nazi Conspiracy and Aggression, Volume VIII（Office of United States Chief of Counsel for Prosecution of Axis Criminality）',
    'publisher': 'United States Government Printing Office, Washington', 'licenseCode': 'us_federal_pd',
    'licenseEvidenceUrl': 'https://www.loc.gov/item/2011525363_NT_Nazi_Vol-VIII/', 'url': 'https://www.loc.gov/item/2011525363_NT_Nazi_Vol-VIII/',
    'publishedText': '1946–1947（國會圖書館著錄為 1947）',
    'note': '美國政府著作（17 U.S.C. §105）；頁碼依紙本（國會圖書館 Military Legal Resources 掃描）。'}, {'priorPlaceholder': False})

# ---- 政權 ----
REGIMES = [
    ('REGIME_FNA_ALLIED', 'french-north-africa-allied-occupation', 'French North Africa (Allied military occupation)', 'en',
     '盟軍佔領下的法屬北非（達爾朗高級專員）', 'French North Africa under Allied occupation (High Commissioner Darlan)',
     'FRUS 1942 II Doc. 453（military occupation of territories in … North Africa）、Doc. 469（the High Commissioner for French North Africa）'),
    ('REGIME_RK_NL', 'reichskommissariat-niederlande', 'Reichskommissariat Niederlande', 'de',
     '德國佔領下的荷蘭（帝國專員轄區）', 'German-occupied Netherlands (Reichskommissariat)',
     'NCA III Doc. 1183-PS, p. 829（The Reich Commissioner for the occupied Dutch territories）；德文名為通行稱呼'),
    ('REGIME_RK_NO', 'reichskommissariat-norwegen', 'Reichskommissariat Norwegen', 'de',
     '德國佔領下的挪威（帝國專員轄區）', 'German-occupied Norway (Reichskommissariat)',
     'NCA III Doc. 1183-PS, p. 829（The Reich Commissioner for the occupied Norwegian territories）；德文名為通行稱呼'),
]
for i, (ph, slug, orig, lang, zh, en, src) in enumerate(REGIMES, 1):
    write(f'02-regime-{i:02d}-{slug}.json', ph, '/api/v1/regimes', {'slug': slug, 'names': [
        {'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]},
        {'priorPlaceholder': False, 'nameSource': src})

# ---- 事件 ----
def ev(i, ph, kind, start, zh, en, parts, cites, tn=None):
    e = (datetime.date.fromisoformat(start) + datetime.timedelta(days=1)).isoformat()
    body = {'eventKind': kind, 'occurred': {'start': start, 'end': e}, 'datePrecision': 'day', 'summary': {'zh-Hant': zh, 'en': en},
            'participants': [{'regimeId': '{{%s}}' % r, 'role': role} for r, role in parts],
            'citations': [{'sourceId': '{{%s}}' % s, 'locator': l, 'evidenceNote': n} for s, l, n in cites]}
    if tn: body['timeNote'] = {'zh-Hant': tn[0], 'en': tn[1]}
    write(f'03-event-{i:02d}-{ph.lower()}.json', ph, '/api/v1/events', body, {'verification': 'verified' if cites else 'pending（待查證）'})

ev(1, 'EV_TORCH', 'war', '1942-11-08', '盟軍登陸法屬北非；阿爾及利亞改由盟軍軍事佔領，達爾朗任法屬北非高級專員', 'Allied landings in French North Africa; Algeria under Allied military occupation, Darlan as High Commissioner',
   [('REGIME_UK', 'belligerent'), ('REGIME_FR_STATE', 'belligerent')],
   [('SRC_FRUS_1942_II', 'Doc. 427, p. 430', '駐丹吉爾代辦 1942-11-08 電：當日凌晨傳來美軍登陸法屬北非的消息。'),
    ('SRC_FRUS_1942_II', 'Doc. 203, pp. 201–202', '駐維琪代辦 1942-11-08 電：賴伐爾告知，美軍登陸法屬北非，維琪政府因此與美國斷交。'),
    ('SRC_FRUS_1942_II', 'Doc. 453, pp. 451–452', '國務卿 1942-11-21 電：北非等「重新佔領地區」的民政安排；聯合國軍隊對歐洲與北非領土的軍事佔領。'),
    ('SRC_FRUS_1942_II', 'Doc. 454, pp. 453–457', '1942-11-22 克拉克—達爾朗協定（阿爾及爾）：盟軍總司令與在當地行使民政、軍事職能的北非委員會之間的協定。'),
    ('SRC_FRUS_1942_II', 'Doc. 469, p. 471', '1942-12-03 談話紀錄：達爾朗為法屬北非高級專員；艾森豪表示，除為軍事行動成立的臨時組織外，不承認法屬非洲的任何政府。')],
   ('美國是登陸的主要一方，但政權表尚無美國，參與方暫列英國與維琪法國。', 'The US was the main landing power but is not yet in the regime table; participants list the UK and Vichy France.'))
ev(2, 'EV_INV_NO', 'war', '1940-04-09', '德國入侵並佔領挪威', 'Germany invades and occupies Norway',
   [('REGIME_DE', 'belligerent'), ('REGIME_NO', 'belligerent')],
   [('SRC_NCA_VIII', 'Doc. TC-55, pp. 409–413', '德國 1940-04-09 致挪威、丹麥政府備忘錄（最後通牒），並聲明無意侵犯挪威領土完整與政治獨立。'),
    ('SRC_NCA_IV', 'Doc. 1546-PS, pp. 103–105', '雷德爾備忘錄：1940-04-09 佔領挪威；元首把登陸日定在 4 月 9 日，並決定同時佔領丹麥。')],
   ('挪威本土戰事延續到 1940-06-10；本表把全境自 04-09 起畫為佔領，是簡化。', 'Fighting in Norway lasted until 10 June 1940; drawing the whole country as occupied from 9 April is a simplification.'))
ev(3, 'EV_DK_DURESS', 'political', '1941-04-14', '美國認定在丹麥的政府在德軍佔領下受脅迫行事，仍承認丹麥主權與駐美公使', 'The US holds that the government in Denmark acts under duress of German occupation, while recognizing Danish sovereignty and the Danish Minister',
   [('REGIME_DK', 'other')],
   [('SRC_FRUS_1941_II', 'Doc. 43, p. 51', '國務卿 1941-04-14 致丹麥公使：美國認為在丹麥的政府此舉是受脅迫，繼續承認考夫曼為丹麥公使，並盼丹麥早日解放。'),
    ('SRC_FRUS_1941_II', 'Doc. 63, pp. 68–69', '國務卿 1941-10-25 照會：因德軍佔領，丹麥政府目前無法自由行事；美國仍承認丹麥對格陵蘭的主權。'),
    ('SRC_FRUS_1941_II', 'Doc. 64, pp. 70–72', '丹麥外交部 1941-12-12 照會（丹方立場）：丹麥雖在德軍佔領下，合法政府仍在運作。')])
ev(4, 'EV_LIB_NL', 'surrender', '1945-05-05', '荷蘭境內德軍投降，荷蘭恢復主權', 'German forces in the Netherlands surrender; Dutch sovereignty restored',
   [('REGIME_DE', 'other'), ('REGIME_NL', 'other')], [], ('尚未取得正式出處；日期待查證。', 'No formal source yet; date pending.'))
ev(5, 'EV_LIB_NO', 'surrender', '1945-05-08', '挪威境內德軍投降，挪威恢復主權', 'German forces in Norway surrender; Norwegian sovereignty restored',
   [('REGIME_DE', 'other'), ('REGIME_NO', 'other')], [], ('尚未取得正式出處；日期待查證。', 'No formal source yet; date pending.'))

# ---- 撤回舊紀錄 ----
RETRACT = [
    ('french-state-vichy', '維琪法國紀錄拆在 1942-11-08：盟軍登陸法屬北非後阿爾及利亞北部不再由維琪控制'),
    ('kingdom-of-the-netherlands', '荷蘭自 1940-05-15 起為德國佔領下的帝國專員轄區（非主權），舊紀錄跨過佔領期'),
    ('kingdom-of-norway', '挪威自 1940-04-09 起為德國佔領（非主權），舊紀錄跨過佔領期'),
    ('kingdom-of-denmark', '丹麥自 1940-04-09 起在德軍佔領下，政府受脅迫行事（非主權），舊紀錄跨過佔領期'),
]
for i, (slug, reason) in enumerate(RETRACT, 1):
    write(f'04-retract-{i:02d}-{slug}.json', f'RETRACTED_{slug.upper().replace("-", "_")}', f'/api/v1/sovereignty-records/{OLD[slug]["id"]}/retraction',
          {'reason': reason}, {'fix': True, 'oldId': OLD[slug]['id']})

# ---- 新紀錄 ----
def rec(i, ph, slug, regime, fix, period, layer, start_ev, end_ev, nzh, nen, locator_suffix=''):
    o = OLD[slug]
    body = {'regimeId': regime, 'geometry': None, 'validPeriod': period, 'layerStatus': layer,
            'geometrySourceId': o['geometrySourceId'], 'geometryLocator': o['geometryLocator'] + locator_suffix,
            'geometryLicense': o['geometryLicense'], 'attribution': o['attribution'], 'startEventId': start_ev, 'endEventId': end_ev,
            'ohmRelationId': o['ohmRelationId'], 'ohmVersion': o['ohmVersion'], 'ohmFetchedAt': o['ohmFetchedAt'],
            'ohmStartRaw': o['ohmStartRaw'], 'ohmEndRaw': o['ohmEndRaw'],
            'provenance': {**o['provenance'], 'supersedes': o['id'], 'fixBatch': 'borders-1942-fix'},
            'note': {'zh-Hant': nzh, 'en': nen}}
    write(f'05-sovereignty-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sovereignty-records', body, {'fix': True}, geom=fix)

V = OLD['french-state-vichy']; NLr = OLD['kingdom-of-the-netherlands']; NOr = OLD['kingdom-of-norway']; DKr = OLD['kingdom-of-denmark']
ALG_NOTE = '阿爾及利亞北部（阿爾及爾、奧蘭、君士坦丁三省）當時屬法國本土的省份，依 OHM 事實國界與法國本土同一紀錄。'
rec(1, 'SOVF_VICHY_A', 'french-state-vichy', '{{REGIME_FR_STATE}}', 'FIX_VICHY_FULL', {'start': V['lower'], 'end': '1942-11-08'}, 'de_jure', V['startEventId'], '{{EV_TORCH}}',
    ALG_NOTE + '1942-11-08 盟軍登陸法屬北非後另分段。', 'Northern Algeria (then French départements) is drawn with metropolitan France per OHM, until the Allied landings of 8 Nov 1942.')
rec(2, 'SOVF_VICHY_B', 'french-state-vichy', '{{REGIME_FR_STATE}}', 'FIX_VICHY_EU', {'start': '1942-11-08', 'end': '1942-11-11'}, 'de_jure', '{{EV_TORCH}}', '{{EV_ANTON}}',
    '1942-11-08 盟軍登陸後，阿爾及利亞北部不再由維琪控制，本段只含法國本土（北緯 40 度以北）。', 'From 8 Nov 1942 metropolitan France only (north of 40°N).', ' ∩ 北緯 40 度以北（法國本土）')
rec(3, 'SOVF_ALGERIA', 'french-state-vichy', '{{REGIME_FNA_ALLIED}}', 'FIX_ALGERIA', {'start': '1942-11-08', 'end': '1943-01-01'}, 'not_sovereign', '{{EV_TORCH}}', None,
    '非主權：1942-11-08 盟軍登陸後的阿爾及利亞北部，由盟軍軍事佔領，達爾朗以法屬北非高級專員行使民政；美方表示不承認當地任何政府（FRUS 1942 II Doc. 469）。登陸後數日仍有戰鬥，日期取登陸日。突尼西亞、摩洛哥不在既有資料範圍內，未畫。',
    'Not sovereign: northern Algeria under Allied military occupation from 8 Nov 1942, with Darlan as High Commissioner; the US recognized no government there (FRUS 1942 II Doc. 469).', ' ∩ 北緯 40 度以南（阿爾及利亞北部）')
rec(4, 'SOVF_NL_A', 'kingdom-of-the-netherlands', '{{REGIME_NL}}', 'FIX_NL', {'start': NLr['lower'], 'end': '1940-05-15'}, 'de_jure', NLr['startEventId'], '{{EV_SURR_NL}}',
    '荷蘭王國，至 1940-05-14 荷軍奉命停止戰鬥為止。', 'Kingdom of the Netherlands until the capitulation of 14 May 1940.')
rec(5, 'SOVF_RK_NL', 'kingdom-of-the-netherlands', '{{REGIME_RK_NL}}', 'FIX_NL', {'start': '1940-05-15', 'end': '1945-05-05'}, 'not_sovereign', '{{EV_SURR_NL}}', '{{EV_LIB_NL}}',
    '非主權：德國佔領下的荷蘭。依 1940-05-18 元首命令（在荷蘭行使政府權力，RGBl. I, p. 778）設帝國專員（NCA IV Doc. 2111-PS, p. 734；NCA III Doc. 1183-PS, p. 829 所列 1942 年的帝國專員）。05-15～05-18 間為軍事管理，未另分段。1945-05-05 結束日待查證。',
    'Not sovereign: German-occupied Netherlands under a Reich Commissioner (Führer decree of 18 May 1940; NCA IV Doc. 2111-PS, p. 734). End date pending.')
rec(6, 'SOVF_NL_B', 'kingdom-of-the-netherlands', '{{REGIME_NL}}', 'FIX_NL', {'start': '1945-05-05', 'end': NLr['upper']}, 'de_jure', '{{EV_LIB_NL}}', NLr['endEventId'],
    '荷蘭王國恢復主權後（起始日待查證），沿用舊紀錄幾何與結束日。', 'Kingdom of the Netherlands after liberation (start date pending); geometry and end as in the old record.')
rec(7, 'SOVF_NO_A', 'kingdom-of-norway', '{{REGIME_NO}}', 'FIX_NO', {'start': NOr['lower'], 'end': '1940-04-09'}, 'de_jure', NOr['startEventId'], '{{EV_INV_NO}}',
    '挪威王國，至 1940-04-09 德國入侵為止。', 'Kingdom of Norway until the German invasion of 9 April 1940.')
rec(8, 'SOVF_RK_NO', 'kingdom-of-norway', '{{REGIME_RK_NO}}', 'FIX_NO', {'start': '1940-04-09', 'end': '1945-05-08'}, 'not_sovereign', '{{EV_INV_NO}}', '{{EV_LIB_NO}}',
    '非主權：德國佔領下的挪威（1942 年由帝國專員管轄，NCA III Doc. 1183-PS, p. 829）。04-09～06-10 戰事期間全境畫為佔領是簡化；帝國專員設立日未另分段。1945-05-08 結束日待查證。',
    'Not sovereign: German-occupied Norway (Reich Commissioner in 1942, NCA III Doc. 1183-PS, p. 829). End date pending.')
rec(9, 'SOVF_NO_B', 'kingdom-of-norway', '{{REGIME_NO}}', 'FIX_NO', {'start': '1945-05-08', 'end': NOr['upper']}, 'de_jure', '{{EV_LIB_NO}}', NOr['endEventId'],
    '挪威王國恢復主權後（起始日待查證），沿用舊紀錄幾何與結束日。', 'Kingdom of Norway after liberation (start date pending); geometry and end as in the old record.')
rec(10, 'SOVF_DK_A', 'kingdom-of-denmark', '{{REGIME_DK}}', 'FIX_DK', {'start': DKr['lower'], 'end': '1940-04-09'}, 'de_jure', DKr['startEventId'], '{{EV_WAR_DE_DK}}',
    '丹麥王國，至 1940-04-09 德軍進入為止。', 'Kingdom of Denmark until German forces entered on 9 April 1940.')
rec(11, 'SOVF_DK_OCC', 'kingdom-of-denmark', '{{REGIME_DK}}', 'FIX_DK', {'start': '1940-04-09', 'end': DKr['upper']}, 'not_sovereign', '{{EV_WAR_DE_DK}}', DKr['endEventId'],
    '非主權（特殊情況）：丹麥自 1940-04-09 起在德軍佔領下，國王、政府、議會仍在，德方只派全權代表，沒有設帝國專員，所以政權仍記為丹麥王國，不另立佔領行政區。美國認定在丹麥的政府受脅迫、無法自由行事，但仍承認丹麥主權（FRUS 1941 II Doc. 43、63）。1943-08-29 丹麥政府停止運作，未另分段（待查證）。法羅群島 1940 年起由英國佔領，含在本紀錄裡，未另畫（待查證）。',
    'Not sovereign (special case): Denmark under German occupation from 9 April 1940 with its King, government and parliament in place; the US held that the government acted under duress while still recognizing Danish sovereignty (FRUS 1941 II Docs. 43, 63). The 29 Aug 1943 change and the British-occupied Faroes are not split (pending).')
print('ok', json.dumps(qa))
