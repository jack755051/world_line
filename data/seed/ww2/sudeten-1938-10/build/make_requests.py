#!/usr/bin/env python3
"""蘇台德 1938-10-01～10-10：依慕尼黑協定分區進駐期間的空白（DRAFT，待 Tai 檢查）。
- 協定第 4 條（DGFP D/II No. 675, pp. 1014–1015，原文已核頁）：10-01 起分階段佔領，I 區 10-01／02、II 區 10-02／03、III 區 10-03～05、IV 區 10-06／07，
  其餘以德意志人為主的地區由國際委員會劃定、10-10 前佔領；FRUS 1938 I Doc. 682（pp. 702–703）、Doc. 700（pp. 721–722，第五區）、Doc. 710（pp. 734–735，10-10 大致完成）佐證。
- OHM 沒有分區幾何：把整塊蘇台德（德國 1938-10-10 紀錄 − 1938-03-13 紀錄；即 OHM 2704711 v199 ∩ 2692764 v97 的部分，與既有紀錄幾何完全一致）
  自 10-01 起畫為「德軍分區進駐中的蘇台德」（非主權斜線）至 10-10，註記說明簡化。面積 < 0.01 平方度的碎片（佩特爾扎爾卡／Engerau 一小片與邊界細縫）不納入。
- 德國 1938-10-10～11-21 紀錄的註記寫著「10-01～10-10 維持空白」，已不符：撤回後以同一幾何、更新後的註記重新新增。
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); OUT = os.path.join(ROOT, 'requests')
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT): os.remove(os.path.join(OUT, f)) if f.endswith('.json') else None
def write(name, ph, post, body, meta=None, geom=None):
    req = {'_placeholder': ph, '_post': post, **({'_geometryFrom': geom} if geom else {}), **({'_meta': meta} if meta else {}), 'body': body}
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')
sud = json.load(open(os.path.join(HERE, 'sudeten.json')))
de = json.load(open(os.path.join(HERE, 'de_1010.json')))
json.dump({'type': 'FeatureCollection', 'features': [
    {'type': 'Feature', 'id': 'SUD_1001', 'properties': {}, 'geometry': sud},
    {'type': 'Feature', 'id': 'DE_1010', 'properties': {}, 'geometry': de}]},
    open(os.path.join(ROOT, 'sudeten-1938-10-derived.geojson'), 'w'), separators=(',', ':'))

write('01-source-01-src_dgfp_d2.json', 'SRC_DGFP_D2', '/api/v1/sources', {
    'sourceKind': 'official_record',
    'title': 'Documents on German Foreign Policy 1918–1945, Series D (1937–1945), Volume II: Germany and Czechoslovakia, 1937–1938（美國國務院版）',
    'publisher': 'U.S. Department of State／United States Government Printing Office, Washington', 'licenseCode': 'us_federal_pd',
    'licenseEvidenceUrl': 'https://www.state.gov/copyright-information',
    'url': 'https://archive.org/details/documents-on-german-foreign-policy-series-d-vol.-ii-germany-and-czechoslovakia-1937...1938',
    'publishedText': '1949（GPO）；英國 HMSO 版 1950',
    'note': '美、英、法聯合編纂。頁碼依 archive.org 的 HMSO 1950 版掃描核對（No. 675 在 pp. 1014–1015），與 FRUS 1938 I Doc. 682 註腳所引「German Documents, ser. D, vol. ii, doc. No. 675, p. 1014」一致；授權以美國政府版（17 U.S.C. §105）登錄。'},
    {'priorPlaceholder': False})
write('02-regime-01-sudeten-german-occupation-1938.json', 'REGIME_SUDETEN_OCC', '/api/v1/regimes', {'slug': 'sudeten-german-occupation-1938', 'names': [
    {'nameKind': 'self', 'originalText': 'Sudetendeutsche Gebiete', 'originalLang': 'de',
     'display': {'zh-Hant': '蘇台德地區（德軍依慕尼黑協定分區進駐中）', 'en': 'Sudeten German territory (German occupation by zones under the Munich Agreement)'}, 'isPrimary': True}]},
    {'priorPlaceholder': False, 'nameSource': 'DGFP D/II No. 675, p. 1014（協定英文本：the Sudeten German territory）；德文名稱為通行稱呼，原文出處待查證'})
# 事件：沿用既有 EV_SUDETEN_OCCUPATION（FRUS 引用），補一條 DGFP 協定本文出處的事件不另建：改在紀錄註記與新來源中引用。
# 協定第 4 條的分區日期以新事件記錄（引用 DGFP 本文）。
write('03-event-01-ev_munich_zones.json', 'EV_MUNICH_ZONES', '/api/v1/events', {
    'eventKind': 'political', 'occurred': {'start': '1938-10-01', 'end': '1938-10-11'}, 'datePrecision': 'day',
    'summary': {'zh-Hant': '慕尼黑協定第 4 條：德軍分區進駐蘇台德（I 區 10-01／02、II 區 10-02／03、III 區 10-03～05、IV 區 10-06／07；其餘由國際委員會劃定，10-10 前佔領）',
                'en': 'Munich Agreement art. 4: German troops occupy the Sudeten territory by zones (I: 1–2 Oct; II: 2–3 Oct; III: 3–5 Oct; IV: 6–7 Oct; the rest, fixed by the international commission, by 10 Oct)'},
    'participants': [{'regimeId': '{{REGIME_DE}}', 'role': 'other'}, {'regimeId': '{{REGIME_CS}}', 'role': 'other'}],
    'citations': [
        {'sourceId': '{{SRC_DGFP_D2}}', 'locator': 'No. 675, pp. 1014–1015', 'evidenceNote': '協定本文第 1、2、4 條：撤離 10-01 開始、10-10 完成；四個標示區依 10-01／02、10-02／03、10-03～05、10-06／07 順序由德軍佔領，其餘地區由國際委員會劃定並於 10-10 前佔領。'},
        {'sourceId': '{{SRC_FRUS_1938_I}}', 'locator': 'Doc. 682, pp. 702–703', 'evidenceNote': 'Carr 1938-09-30 電：協定規定德國自翌日起逐步佔領，10 月 10 日完成。'},
        {'sourceId': '{{SRC_FRUS_1938_I}}', 'locator': 'Doc. 700, pp. 721–722', 'evidenceNote': 'Carr 1938-10-07 電：國際委員會定出第五佔領區。'}],
    'timeNote': {'zh-Hant': '期間依協定（10-01～10-10）；各區實際進駐日未逐區核對。', 'en': 'Period per the agreement (1–10 Oct); actual entry dates per zone not checked.'}},
    {'verification': 'verified'})
PROV = {'ohmFixme': 'needs source for boundary lines', 'coastline': '{{SRC_NE_LAND}}', 'ohmChangeset': 272226, 'ohmTimestamp': '2026-09-22T01:48:40Z',
        'licenseReview': 'osm_derived_ways', 'ohmAdminLevel': '2', 'memberWayLicense': {'gurs': 25, 'untagged(OHM CC0)': 1774}, 'ohmRelationSource': None, 'osmDerivedWayCount': 464}
base = {'geometry': None, 'geometrySourceId': '{{SRC_OHM}}', 'geometryLicense': 'cc_by', 'attribution': '© Geodetska uprava Republike Slovenije（GURS），CC BY 4.0',
        'ohmRelationId': 2704712, 'ohmVersion': 208, 'ohmFetchedAt': '2026-10-30T19:27:35Z', 'ohmStartRaw': '1938-03-13', 'ohmEndRaw': '1938-11-21'}
write('04-sovereignty-01-sov_sudeten_occ.json', 'SOV_SUDETEN_OCC', '/api/v1/sovereignty-records', {**base,
    'regimeId': '{{REGIME_SUDETEN_OCC}}', 'validPeriod': {'start': '1938-10-01', 'end': '1938-10-10'}, 'layerStatus': 'not_sovereign',
    'geometryLocator': '((relation/2704711 v199 ∩ relation/2692764 v97) − 1938-10-15 其他紀錄)，即德國 1938-10-10 紀錄 − 1938-03-13 紀錄（< 0.01 平方度碎片不納入）',
    'startEventId': '{{EV_MUNICH_ZONES}}', 'endEventId': '{{EV_SUDETEN_OCCUPATION}}',
    'provenance': {**PROV, 'derivedFrom': ['relation/2704712 v208', 'relation/2704711 v199', 'relation/2692764 v97'],
                   'derivation': '德國 1938-10-10 紀錄幾何 − 德國 1938-03-13 紀錄幾何；去掉 < 0.01 平方度碎片', 'simplification': 'whole_area_from_first_day'},
    'note': {'zh-Hant': '非主權：慕尼黑協定（DGFP D/II No. 675）規定 10-01 起德軍分四區進駐、其餘地區由國際委員會劃定並於 10-10 前佔領。OHM 沒有分區幾何，這裡簡化為整塊蘇台德自 10-01 起標為德軍分區進駐中，至 10-10 佔領大致完成、劃入德國（FRUS 1938 I Doc. 710）。實際上 10-01 時多數地區尚未進駐；佩特爾扎爾卡一小片不在此範圍（OHM 自 10-10 劃入德國）。',
             'en': 'Not sovereign: under the Munich Agreement (DGFP D/II No. 675) German troops occupied four zones from 1 Oct and the rest, fixed by the international commission, by 10 Oct. OHM has no zone geometry, so the whole Sudeten area is shown as under German occupation from 1 Oct (simplification) until it is drawn as German from 10 Oct (FRUS 1938 I Doc. 710).'}},
    {'ohmName': 'German Reich（2704711 ∩ 2692764 部分）'}, geom='SUD_1001')
DE_ID = '01a18e93-755c-7ada-8deb-2da962c08d7c'
write('05-retract-01-de_1938_10_10.json', 'RETRACTED_DE_1938_10_10', f'/api/v1/sovereignty-records/{DE_ID}/retraction',
      {'reason': '註記寫「10-01～10-10 分區佔領無分區幾何，維持空白」已不符：該期間改以 sudeten-german-occupation-1938 非主權紀錄補上（DGFP D/II No. 675）。同一幾何、更新註記後重新新增。'}, {'fix': True})
write('06-sovereignty-01-sov_de_1938_10_10.json', 'SOV_DE_1938_10_10', '/api/v1/sovereignty-records', {**base,
    'regimeId': '{{REGIME_DE}}', 'validPeriod': {'start': '1938-10-10', 'end': '1938-11-21'}, 'layerStatus': 'de_jure',
    'geometryLocator': 'relation/2704712 v208 ∪ (relation/2704711 v199 ∩ relation/2692764 v97 − 1938-10-15 其他紀錄)',
    'startEventId': '{{EV_SUDETEN_OCCUPATION}}', 'endEventId': '01a18e71-cea1-7ef6-804a-62920348589a',
    'provenance': {**PROV, 'derivation': '2704712 ∪ ((2704711 ∩ 2692764) − 1938-10-15 其他有效紀錄)', 'derivedFrom': ['relation/2704712 v208', 'relation/2704711 v199', 'relation/2692764 v97'],
                   'replaces': DE_ID},
    'note': {'zh-Hant': '蘇台德：OHM 捷克斯洛伐克 09-30 縮小、德國 11-21 才擴大。依 FRUS 1938 I Doc. 710（佔領 10-10 大致完成、實際移轉）自 10-10 起畫入德國；邊界取 OHM 2704711（11-21 版）。10-01～10-10 依慕尼黑協定分區進駐，另以非主權紀錄（整塊簡化）呈現。',
             'en': 'Sudetenland drawn as German from 10 Oct (occupation substantially complete, FRUS 1938 I Doc. 710); line from OHM 2704711. 1–10 Oct is shown as a separate not-sovereign record (zones simplified to the whole area).'}},
    {'ohmName': 'German Reich', 'fix': True}, geom='DE_1010')
print('ok')
