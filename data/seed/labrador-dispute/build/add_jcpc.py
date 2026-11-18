#!/usr/bin/env python3
"""補上 1927 年樞密院裁決本文（Tai 2026-11-14 提供下載的 PDF）。產生 requests/06～12；只寫開發庫（5052）。
先前（requests/01～05）只有加拿大年鑑一個出處，紐芬蘭一方的主張只有對手方的記載。裁決書逐字載明雙方主張與裁決結論。
引文是 Claude 看掃描圖逐字抄錄的（PDF 沒有文字層），頁碼是裁決書印的頁碼。
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'requests')
ids = json.load(open(os.path.join(HERE, '..', 'sent-ids.json')))
old_ev = json.load(open(os.path.join(OUT, '02-event-jcpc-1927.json')))['body']
old_dp = json.load(open(os.path.join(OUT, '05-dispute-labrador.json')))['body']
def write(name, req):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f: json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')
CA = '「The contention of the Dominion is that the “coast” which by the Commission and Proclamation of 1763, as modified by the subsequent statutes, was annexed to Newfoundland, is “a strip of maritime territory, extending from Cape Chidley at the entrance to Hudson Strait, to the eastern headland of the bay or harbour of Blanc Sablon on the Strait of Bellisle, and comprising, in its depth inland, only so much of the land immediately abutting on the sea, above low-water mark, as was accessible and useful to the British fishermen annually resorting to that coast …”」；加拿大並提議界線畫在「at a distance from high-water mark on the seacoast of the peninsula of Labrador of one mile」'
NF = '「the contention of the Colony of Newfoundland is that the boundary should be “a line drawn due north from Ance Sablon as far as the fifty-second degree of North latitude, and should be traced from thence northwards to Cape Chidley along the crest of the watershed of the rivers flowing into the Atlantic Ocean.”」'
RESULT = '「the boundary between Canada and Newfoundland in the Labrador Peninsula is a line drawn due north from the eastern boundary of the bay or harbour of Ance Sablon as far as the fifty-second degree of north latitude, and from thence westward along that parallel until it reaches the Romaine river, and then northward along the left or east bank of that river and its head waters to their source and from thence due north to the crest of the watershed or height of land there, and from thence westward and northward along the crest of the watershed of the rivers flowing into the Atlantic Ocean until it reaches Cape Chidley」'
BASIS = '樞密院司法委員會的裁決書本文（裁決機關自己的文件；對兩方而言都是第三方的官方紀錄）。Claude 看掃描圖逐字抄錄，2026-11-14，待複核。'
write('06-source-jcpc-1927.json', {'_placeholder': 'SRC_JCPC_LABRADOR_1927', '_post': '/api/v1/sources', 'body': {
    'sourceKind': 'trial_record', 'title': 'In the Matter of the Boundary between the Dominion of Canada and the Colony of Newfoundland in the Labrador Peninsula: Report of the Lords of the Judicial Committee of the Privy Council, delivered the 1st March, 1927 ([1927] UKPC 25)',
    'publisher': 'Judicial Committee of the Privy Council; printed by Harrison & Sons, Ltd., London, 1927', 'licenseCode': 'pd_expired',
    'licenseEvidenceUrl': 'https://www.bailii.org/uk/cases/UKPC/1927/1927_25.html', 'url': 'https://www.bailii.org/uk/cases/UKPC/1927/1927_25.pdf',
    'family': 'jcpc-labrador-1927', 'grade': 'A', 'gradeBasis': '裁決機關的裁決書本文（審判紀錄）。',
    'note': 'BAILII 提供的掃描 PDF（26 頁，沒有文字層），由 Tai 2026-11-14 用瀏覽器下載後提供；SHA-256 d77d06889740b97e996060068bf081f5d35564ced366a52d9e72c9d477e5a1aa。授權：1927 年的裁決書，已屬公有領域；BAILII 的掃描檔另有其使用條款，這裡只引用文字。'}})
def cite(n, ph, target, loc, note):
    write(f'{n}-citation-{ph.lower()}.json', {'_placeholder': ph, '_post': f'/api/v1/sovereignty-records/{ids[target]}/citations', 'body': {
        'sourceId': '{{SRC_JCPC_LABRADOR_1927}}', 'locator': loc, 'evidenceNote': note, 'grade': 'A', 'gradeBasis': BASIS}})
cite('07', 'CITE_CA_01_JCPC', 'CLAIM_CA_01', 'pp. 9–10（The contentions of the two parties）',
     '裁決書載明加拿大的主張：' + CA + '。證明加拿大主張紐芬蘭只有沿岸一條狹長地帶，內陸屬加拿大；本紀錄加上的內陸範圍取自資料集。')
for n, t in (('08', 'CLAIM_NF_04'), ('09', 'CLAIM_NF_05')):
    cite(n, f'CITE_{t[6:]}_JCPC', t, 'p. 10（The contentions of the two parties）',
         '裁決書載明紐芬蘭的主張：' + NF + ' 證明紐芬蘭主張的範圍一路到大西洋水系的分水嶺；本紀錄的內陸範圍取自資料集，與這條分水嶺線的細節沒有另外比對。')
write('10-retract-event.json', {'_placeholder': 'RETRACTED_EV_LABRADOR_AWARD_1927', '_post': f"/api/v1/events/{ids['EV_LABRADOR_AWARD_1927']}/retraction", '_meta': {'fix': True},
      'body': {'reason': '取得裁決書本文，事件改附裁決書與年鑑兩筆引文後重寫（事件引文不能事後追加）。'}})
ev = dict(old_ev)
ev['citations'] = [{'sourceId': '{{SRC_JCPC_LABRADOR_1927}}', 'locator': '標題頁；p. 23（裁決結論）',
                    'evidenceNote': '標題頁：「Report of the Lords of the Judicial Committee of the Privy Council, delivered the 1st March, 1927」。結論：' + RESULT + '。', 'grade': 'A', 'gradeBasis': BASIS}] + old_ev['citations']
ev['citations'][1]['sourceId'] = ids['SRC_CYB_1926']
ev['timeNote'] = {'zh-Hant': '裁決書 1927-03-01 宣讀。資料庫裡加拿大、紐芬蘭的疆界紀錄照資料集在 1927-03-11 換段，和裁決日差十天，原因還沒查（可能是樞密院令的日期），所以這個事件沒有接成那些紀錄的起訖事件。',
                  'en': 'Report delivered 1 March 1927. The border records switch on 1927-03-11 (dataset date); the ten-day difference is unexplained (possibly the date of the Order in Council), so this event is not linked as their start or end event.'}
write('11-event-jcpc-1927-v2.json', {'_placeholder': 'EV_LABRADOR_AWARD_1927_V2', '_post': '/api/v1/events', 'body': ev})
write('12a-retract-dispute.json', {'_placeholder': 'RETRACTED_DISPUTE_LABRADOR', '_post': f"/api/v1/sovereignty-disputes/{ids['DISPUTE_LABRADOR']}/retraction", '_meta': {'fix': True},
      'body': {'reason': '取得裁決書本文：兩方的主張現在都有 A 級出處，各方主張的說明重寫。'}})
pos = {'canada': {'zh-Hant': '主張紐芬蘭依 1763 年的委任狀與公告只取得沿岸一條狹長地帶（提議以高潮線向內陸一英里為界），其餘的拉布拉多內陸屬加拿大（魁北克省）。出處：1927 年樞密院裁決書 pp. 9–10（A）；加拿大年鑑 1926 p. 1036（A，己方官方記載）。',
                  'en': 'Contended that Newfoundland held only a strip of coast under the Commission and Proclamation of 1763 (proposing a line one mile inland from high-water mark), the rest of the Labrador interior being Canadian (Quebec). Sources: Privy Council report of 1927, pp. 9–10 (grade A); Canada Year Book 1926, p. 1036 (grade A).'},
       'dominion-of-newfoundland': {'zh-Hant': '主張界線從安斯薩布隆向正北到北緯 52 度，再沿流入大西洋各河的分水嶺向北到奇德利角，也就是整個大西洋坡面的內陸都屬紐芬蘭。出處：1927 年樞密院裁決書 p. 10（A）。裁決結果大致採納這條分水嶺線（南段改沿北緯 52 度到羅曼河）。',
                                    'en': 'Contended for a line due north from Ance Sablon to 52°N and thence northwards to Cape Chidley along the crest of the watershed of the rivers flowing into the Atlantic. Source: Privy Council report of 1927, p. 10 (grade A). The decision largely adopted this watershed line (with the southern section along the 52nd parallel to the Romaine river).'}}
slug_of = {c['claimantRegimeId']: None for c in old_dp['claims']}
claims = []
for c in old_dp['claims']:
    key = 'canada' if '加拿大' in c['position']['zh-Hant'][:12] and '主張拉布拉多內陸屬加拿大' in c['position']['zh-Hant'] else 'dominion-of-newfoundland'
    rec = c['recordId'].strip('{}'); claims.append({'claimantRegimeId': c['claimantRegimeId'], 'recordId': ids[rec], 'effective': None, 'position': pos[key]})
dp = {'slug': old_dp['slug'], 'kind': 'contested', 'claims': claims,
      'summary': {'zh-Hant': '拉布拉多半島內陸的歸屬。依裁決書，邊界問題最早在 1888 年前後提出，1903 年因紐芬蘭在漢密爾頓河一帶核發伐木許可而成為正式爭議，涉及超過 10 萬平方英里；雙方聲請交樞密院司法委員會裁決，1927-03-01 裁決大致採納紐芬蘭主張的分水嶺線。裁決以前兩方的主張並存，本系統不裁判當時誰有理。',
                  'en': 'Ownership of the interior of the Labrador Peninsula. According to the report, the boundary question was first raised about 1888 and became a serious controversy in 1903 when Newfoundland licensed timber cutting near the Hamilton River; more than 100,000 square miles were affected. Referred to the Judicial Committee of the Privy Council, which on 1 March 1927 largely adopted the watershed line claimed by Newfoundland. Before the decision both claims stood side by side.'}}
write('12b-dispute-labrador-v2.json', {'_placeholder': 'DISPUTE_LABRADOR_V2', '_post': '/api/v1/sovereignty-disputes', 'body': dp})
print([ (c['recordId'][-6:], 'CA' if c['position'] is pos['canada'] else 'NF') for c in claims])
