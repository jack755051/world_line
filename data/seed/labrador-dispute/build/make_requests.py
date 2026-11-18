#!/usr/bin/env python3
"""產生 requests/*.json：出處、裁決事件、五筆紀錄的撤回與重寫、加拿大三筆的引文、主權爭議。只寫開發庫（5052）。"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'requests')
R = json.load(open(os.path.join(HERE, 'records.json')))
ZH = {'canada': '加拿大', 'dominion-of-newfoundland': '紐芬蘭自治領'}
def write(name, req):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f: json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')
regime = {x['row']['slug']: x['row']['regime_id'] for x in R}
Q1 = '「The long-standing controversy between the Dominion of Canada and Newfoundland with regard to their boundary in the Labrador Peninsula was, by consent of both parties, referred to the Judicial Committee of the British, Privy Council for decision. On March 1, 1927, this decision, awarding practically the whole territory in dispute to Newfoundland, was announced.」'
Q2 = '「As a consequence an area of 112,400 square miles previously included in the province of Quebec and in the Dominion of Canada by the official geographers is transferred to Newfoundland」'
write('01-source-cyb-1926.json', {'_placeholder': 'SRC_CYB_1926', '_post': '/api/v1/sources', 'body': {
    'sourceKind': 'official_record', 'title': 'The Canada Year Book 1926', 'publisher': "Dominion Bureau of Statistics, Canada; King's Printer, Ottawa, 1927",
    'licenseCode': 'pd_expired', 'licenseEvidenceUrl': 'https://www66.statcan.gc.ca/eng/1926/192610781036_p.%201036.pdf', 'url': 'https://www66.statcan.gc.ca/eng/1926/192610781036_p.%201036.pdf',
    'family': 'canada-year-book', 'grade': 'A',
    'gradeBasis': '加拿大自治領統計局編的官方年鑑（國家機構編纂的官方出版品）。對加拿大自己的主張是己方出處；對紐芬蘭的主張是對手方出處，不能單獨成立。',
    'note': '2026-11-14 取自加拿大統計局網站的掃描 PDF（p. 1036），SHA-256 640c8c96a91f02326a250e7c829cf645747629c9d1f6c97411ef7aa6029d35b1；引文逐字核對過 PDF 文字層。1927 年出版，已屬公有領域。'}})
write('02-event-jcpc-1927.json', {'_placeholder': 'EV_LABRADOR_AWARD_1927', '_post': '/api/v1/events', 'body': {
    'eventKind': 'political', 'occurred': {'start': '1927-03-01', 'end': '1927-03-02'}, 'datePrecision': 'day',
    'summary': {'zh-Hant': '樞密院司法委員會裁決拉布拉多邊界：爭議地區幾乎全歸紐芬蘭', 'en': 'Judicial Committee of the Privy Council decides the Labrador boundary, awarding practically the whole disputed territory to Newfoundland'},
    'participants': [{'regimeId': regime['canada'], 'role': 'other'}, {'regimeId': regime['dominion-of-newfoundland'], 'role': 'other'}],
    'citations': [{'sourceId': '{{SRC_CYB_1926}}', 'locator': 'p. 1036, Appendix, 3. The Labrador Boundary Award', 'evidenceNote': Q1, 'grade': 'A',
                   'gradeBasis': '加拿大官方年鑑記載裁決結果（對加拿大不利的一方自己的官方記載）。裁決本文尚未取得。'}],
    'timeNote': {'zh-Hant': '裁決 1927-03-01 宣布。資料庫裡加拿大、紐芬蘭的疆界紀錄照資料集在 1927-03-11 換段，和裁決日差十天，原因還沒查，所以這個事件沒有接成那些紀錄的起訖事件。',
                 'en': 'Decision announced 1 March 1927. The border records switch on 1927-03-11 (dataset date); the ten-day difference is unexplained, so this event is not linked as their start or end event.'}}})
for n, x in enumerate(R, 1):
    r = x['row']; tag = ('CA' if r['slug'] == 'canada' else 'NF') + f'_{n:02d}'
    write(f'03-{n:02d}a-retract-{tag.lower()}.json', {'_placeholder': f'RETRACTED_{tag}', '_post': f"/api/v1/sovereignty-records/{r['id']}/retraction", '_meta': {'fix': True},
          'body': {'reason': f"{ZH[r['slug']]} {r['lo']}～{r['hi']}：匯入時把拉布拉多內陸（與對方主張重疊的約 {x['zone_km2'] // 10000} 萬平方公里）從兩邊都扣掉留白。Tai 2026-11-14 決定照憲法 R6 記成兩方主張並存，"
                             f"本筆加回爭議範圍後重新新增（labrador-dispute）。"}})
    prov = dict(r['provenance'] or {})
    prov['dispute'] = {'batch': 'labrador-dispute', 'replaces': r['id'], 'zoneKm2': x['zone_km2'],
                       'method': '原紀錄幾何＋爭議範圍。爭議範圍＝紐芬蘭 OHM 關係的完整範圍扣掉資料庫裡紐芬蘭原有的部分（即匯入時 subtractedOverlaps 扣掉的那一塊）',
                       'note': '這筆紀錄是主張範圍，不是當時實際管轄的範圍；兩方主張重疊處由 sovereignty_disputes 標記'}
    prov['subtractedOverlaps'] = [s for s in (prov.get('subtractedOverlaps') or []) if 'newfoundland' not in s and 'canada' not in s] or None
    other = '紐芬蘭' if r['slug'] == 'canada' else '加拿大'
    note = dict(r['note'] or {})
    note = {'zh-Hant': ((note.get('zh-Hant') or '') + f'含拉布拉多內陸的主張範圍。這一帶在 1927-03-01 樞密院裁決以前由加拿大與紐芬蘭雙方主張；{other}的紀錄也畫了同一塊，兩筆重疊的部分就是爭議範圍。').strip(),
            'en': ((note.get('en') or '') + ' Includes the claimed Labrador interior, disputed between Canada and Newfoundland until the Privy Council decision of 1 March 1927; the overlap with the other claimant is the disputed zone.').strip()}
    write(f'03-{n:02d}b-sovereignty-{tag.lower()}.json', {'_placeholder': f'CLAIM_{tag}', '_post': '/api/v1/sovereignty-records', '_geometryFrom': 'L_' + r['id'],
          '_meta': {'replaces': r['id'], 'slug': r['slug'], 'old_km2': x['old_km2'], 'new_km2': x['new_km2']},
          'body': {'regimeId': r['regime_id'], 'geometry': None, 'validPeriod': {'start': r['lo'], 'end': r['hi']}, 'layerStatus': r['layer_status'],
                   'geometrySourceId': r['geometry_source_id'], 'geometryLocator': r['geometry_locator'] + '（含拉布拉多內陸的主張範圍）', 'geometryLicense': r['geometry_license'], 'attribution': r['attribution'],
                   'startEventId': r['start_event_id'], 'endEventId': r['end_event_id'], 'ohmRelationId': r['ohm_relation_id'], 'ohmVersion': r['ohm_version'],
                   'ohmFetchedAt': r['ohm_fetched_at'], 'ohmStartRaw': r['ohm_start_raw'], 'ohmEndRaw': r['ohm_end_raw'], 'provenance': prov, 'note': note}})
    # 引文只附在加拿大第一筆（1908 年那筆另有兩套地圖集可證明其餘輪廓）；後兩筆不附：這筆引文只證明內陸這一塊，附了會讓整筆變成已查證
    if r['slug'] == 'canada' and n == 1:
        write(f'04-{n:02d}-citation-{tag.lower()}.json', {'_placeholder': f'CITE_{tag}', '_post': '/api/v1/sovereignty-records/{{CLAIM_%s}}/citations' % tag, 'body': {
            'sourceId': '{{SRC_CYB_1926}}', 'locator': 'p. 1036, Appendix, 3. The Labrador Boundary Award',
            'evidenceNote': Q2 + ' 證明 1927 年裁決以前，加拿大官方把拉布拉多內陸算在魁北克省與自治領之內（年鑑的數字是 112,400 平方英里，約 29 萬平方公里；本紀錄加上的爭議範圍約 20 萬平方公里，範圍取自資料集，兩者不完全相同）。只證明這一塊的主張，本紀錄其餘輪廓不靠這筆引文。',
            'grade': 'A', 'gradeBasis': '加拿大官方年鑑對本國領土範圍的記載（己方出處）。逐字核對過 PDF 文字層，2026-11-14。'}})
pos = {'canada': {'zh-Hant': '主張拉布拉多內陸屬加拿大（魁北克省），紐芬蘭只有沿岸。出處：加拿大年鑑 1926 p. 1036（己方官方記載，A 級）。',
                  'en': 'Claimed the Labrador interior as part of Canada (Quebec), leaving Newfoundland only the coast. Source: Canada Year Book 1926, p. 1036 (own official record, grade A).'},
       'dominion-of-newfoundland': {'zh-Hant': '主張拉布拉多內陸屬紐芬蘭。目前只有對手方（加拿大年鑑）的記載提到這項主張，紐芬蘭自己的出處與裁決本文都還沒取得，所以這一方的範圍取自資料集，是待查證。',
                                    'en': 'Claimed the Labrador interior. So far attested only by the opposing side (Canada Year Book); no Newfoundland source or text of the decision has been obtained, so this extent comes from the dataset and is pending verification.'}}
write('05-dispute-labrador.json', {'_placeholder': 'DISPUTE_LABRADOR', '_post': '/api/v1/sovereignty-disputes', 'body': {
    'slug': 'labrador-boundary-before-1927',
    'summary': {'zh-Hant': '拉布拉多半島內陸的歸屬：加拿大與紐芬蘭長期爭執，雙方同意交樞密院司法委員會裁決；1927-03-01 裁決把爭議地區幾乎全判給紐芬蘭。裁決以前兩方的主張並存，本系統不裁判當時誰有理。',
                'en': 'Ownership of the interior of the Labrador Peninsula: long disputed between Canada and Newfoundland and referred by consent to the Judicial Committee of the Privy Council, which on 1 March 1927 awarded practically the whole disputed territory to Newfoundland. Before the decision both claims stood side by side.'},
    'claims': [{'claimantRegimeId': x['row']['regime_id'], 'recordId': '{{CLAIM_%s}}' % (('CA' if x['row']['slug'] == 'canada' else 'NF') + f'_{n:02d}'), 'position': pos[x['row']['slug']], 'effective': None}
               for n, x in enumerate(R, 1)]}})
print('ok', len(os.listdir(OUT)))
