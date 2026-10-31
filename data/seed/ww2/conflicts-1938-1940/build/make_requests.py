#!/usr/bin/env python3
"""產生衝突圖示試驗（歐陸 1938–1940）的 requests/*.json。

- 每個衝突對應一個有日期的開戰事件；停戰／投降事件可空（試驗範圍內未結束）。
- 引用只用已核對原文的 FRUS（history.state.gov，美國聯邦政府著作，公有領域）；頁碼以 history.state.gov 的 pg_N 頁面核對。
- 找不到正式出處的結束事件：不附引用 → API 回 verification = pending（「待查證」），日期依據寫在 summary／timeNote。
- 圖示位置：build/locations.sql（兩國主權圖層在開戰日的共同邊界，最長一段的中點）。
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'requests')

def write(name, ph, post, body, meta=None):
    req = {'_placeholder': ph, '_post': post, **({'_meta': meta} if meta else {}), 'body': body}
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')

def day_after(d):
    import datetime
    return (datetime.date.fromisoformat(d) + datetime.timedelta(days=1)).isoformat()

write('01-source-01-src_frus_1940_ii.json', 'SRC_FRUS_1940_II', '/api/v1/sources', {
    'sourceKind': 'official_record',
    'title': 'Foreign Relations of the United States, Diplomatic Papers, 1940, General and Europe, Volume II',
    'publisher': 'United States Department of State; United States Government Printing Office, Washington',
    'licenseCode': 'us_federal_pd',
    'licenseEvidenceUrl': 'https://www.state.gov/copyright-information',
    'url': 'https://history.state.gov/historicaldocuments/frus1940v02',
}, {'priorPlaceholder': True})

# (placeholder, kind, date, zh, en, participants, citations[(src, locator, note)], timeNote)
EVENTS = [
    ('EV_WAR_DE_PL', 'war', '1939-09-01', '德國進攻波蘭，德波進入戰爭狀態', 'Germany attacks Poland; state of war between Germany and Poland',
     ['REGIME_DE', 'REGIME_PL'],
     [('SRC_FRUS_1939_I', 'Doc. 403, pp. 402–403', '但澤領事 9/1 電：但澤參議院正式通知，德波自當日 4 時 45 分起處於戰爭狀態。'),
      ('SRC_FRUS_1939_I', 'Doc. 402, p. 402', '柏林代辦 9/1 電：希特勒發布公告，宣稱以武力回應波蘭。')], None),
    ('EV_WAR_FR_DE', 'war', '1939-09-03', '法國對德國進入戰爭狀態', 'France at war with Germany',
     ['REGIME_FR3', 'REGIME_DE'],
     [('SRC_FRUS_1939_I', 'Doc. 421, p. 415', '柏林代辦 9/3 電：法國大使遞交照會，德國未答覆 9/1 照會，法國自 9/3 下午 5 時起履行對波蘭的義務。')],
     ('巴黎時間 17 時', '5 p.m. Paris time')),
    ('EV_WAR_SU_PL', 'war', '1939-09-17', '蘇軍越過波蘭東部邊界', 'Soviet troops cross into eastern Poland',
     ['REGIME_SU', 'REGIME_PL'],
     [('SRC_FRUS_1939_I', 'Doc. 437, p. 428', '駐蘇大使 9/17 電：蘇軍當日拂曉沿整條邊界進入波蘭東部。'),
      ('SRC_FRUS_1939_I', 'Doc. 440, p. 430', '駐法大使 9/17 電：波蘭照會稱蘇軍多處越界，構成公然侵略。')], None),
    ('EV_WAR_SU_FI', 'war', '1939-11-30', '蘇聯進攻芬蘭（冬季戰爭開始）', 'Soviet Union attacks Finland (Winter War begins)',
     ['REGIME_SU', 'REGIME_FI'],
     [('SRC_FRUS_1939_I', 'Doc. 1113, p. 1007', '駐芬公使 11/30 電：芬方未曾攻擊，蘇方當日 7 時起在泰里約基、庫奧卡拉一帶陸海砲擊。')], None),
    ('EV_WAR_DE_DK', 'war', '1940-04-09', '德軍進入丹麥（與挪威同日）', 'German forces enter Denmark (same day as Norway)',
     ['REGIME_DE', 'REGIME_DK'],
     [('SRC_FRUS_1940_I', 'Doc. 61, pp. 144–145', '柏林代辦 4/9 電：德軍最高統帥部公報稱德軍當日清晨起「接管丹麥與挪威的保護」，已登陸。')], None),
    ('EV_WAR_DE_NL', 'war', '1940-05-10', '德國進攻荷蘭，荷蘭宣告與德國處於戰爭狀態', 'Germany invades the Netherlands; the Netherlands considers itself at war',
     ['REGIME_DE', 'REGIME_NL'],
     [('SRC_FRUS_1940_I', 'Doc. 133, pp. 188–189', '駐荷公使 5/10 電：荷蘭外交部通知荷蘭自認與德國處於戰爭狀態，德軍已越界。')], None),
    ('EV_WAR_DE_BE', 'war', '1940-05-10', '德國進攻比利時', 'Germany invades Belgium',
     ['REGIME_DE', 'REGIME_BE'],
     [('SRC_FRUS_1940_I', 'Doc. 138, p. 192', '駐比大使 5/10 電：德國大使當日 8 時 40 分通知比國外長德國已決定採取軍事措施；外長拒絕聽取聲明並表示憤慨。')], None),
    ('EV_WAR_DE_LU', 'war', '1940-05-10', '德國對盧森堡採取軍事行動', 'Germany takes military action against Luxembourg',
     ['REGIME_DE', 'REGIME_LU'],
     [('SRC_FRUS_1940_I', 'Doc. 137, pp. 190–192', '柏林代辦 5/10 電：里賓特洛甫當日 5 時 30 分召見荷、比、盧使節，宣布以軍事措施「維護」三國中立。')], None),
    ('EV_WAR_IT_FR', 'war', '1940-06-10', '義大利對法國宣戰（6/11 起進入戰爭狀態）', 'Italy declares war on France (state of war from 11 June)',
     ['REGIME_IT', 'REGIME_FR3'],
     [('SRC_FRUS_1940_II', 'Doc. 835, pp. 716–717', '義大利駐美大使 6/11 照會：6/10 下午 4 時 30 分齊亞諾通知法國大使，義大利自 6/11 起與法國處於戰爭狀態。')],
     ('6/10 通知、6/11 起生效', 'Notified 10 June; effective 11 June')),
    ('EV_WAR_IT_GR', 'war', '1940-10-28', '義大利進攻希臘（希義戰爭開始）', 'Italy attacks Greece (Greco-Italian War begins)',
     ['REGIME_IT', 'REGIME_GR'],
     [('SRC_FRUS_1940_III', 'Doc. 428, p. 545', '駐希公使 10/28 電：義大利公使凌晨 3 時遞交最後通牒，6 時到期。'),
      ('SRC_FRUS_1940_III', 'Doc. 429, p. 546', '駐希公使 10/28 電：通牒到期後阿爾巴尼亞邊境兩軍接觸、砲擊；塔托伊機場、科林斯運河遭轟炸。')], None),
    # ── 結束事件 ──
    ('EV_SURR_NL', 'surrender', '1940-05-14', '荷蘭軍隊奉命停止戰鬥（澤蘭省戰事持續）', 'Dutch command orders its troops to cease fighting (fighting continues in Zeeland)',
     ['REGIME_DE', 'REGIME_NL'],
     [('SRC_FRUS_1940_I', 'Doc. 151, p. 199', '柏林代辦 5/14 電：德軍統帥部公告，鹿特丹投降後荷軍統帥部下令停止戰鬥，澤蘭仍在作戰。')], None),
    ('EV_SURR_BE', 'surrender', '1940-05-28', '比利時國王率軍投降', 'King of the Belgians capitulates with the army',
     ['REGIME_DE', 'REGIME_BE'],
     [('SRC_FRUS_1940_I', 'Doc. 166, pp. 208–209', '駐法大使 5/28 電：比利時首相皮埃洛廣播稱國王違背政府決定，與敵方單獨談判。')], None),
    ('EV_END_DE_PL', 'surrender', '1939-10-06', '德波戰事結束（日期待查證；暫依 OHM 波蘭國界止於 1939-10-06）', 'End of German–Polish hostilities (date pending; provisionally the OHM end of Poland, 1939-10-06)',
     ['REGIME_DE', 'REGIME_PL'], [], ('尚未取得正式出處', 'No formal source yet')),
    ('EV_END_SU_PL', 'surrender', '1939-10-06', '蘇波戰事結束（日期待查證；暫依 OHM 波蘭國界止於 1939-10-06）', 'End of Soviet–Polish hostilities (date pending; provisionally the OHM end of Poland, 1939-10-06)',
     ['REGIME_SU', 'REGIME_PL'], [], ('尚未取得正式出處', 'No formal source yet')),
    ('EV_END_DE_DK', 'surrender', '1940-04-09', '丹麥停止抵抗（日期待查證；暫以德軍進入當日）', 'Denmark ceases resistance (date pending; provisionally the day of the German entry)',
     ['REGIME_DE', 'REGIME_DK'], [], ('尚未取得正式出處', 'No formal source yet')),
    ('EV_END_DE_LU', 'surrender', '1940-05-10', '盧森堡被德軍佔領、戰事結束（日期待查證；暫以德軍進入當日）', 'Luxembourg occupied, hostilities end (date pending; provisionally the day of the German entry)',
     ['REGIME_DE', 'REGIME_LU'], [], ('尚未取得正式出處', 'No formal source yet')),
]
for i, (ph, kind, d, zh, en, parts, cites, tn) in enumerate(EVENTS, 1):
    body = {
        'eventKind': kind, 'occurred': {'start': d, 'end': day_after(d)}, 'datePrecision': 'day',
        'summary': {'zh-Hant': zh, 'en': en},
        'participants': [{'regimeId': '{{%s}}' % p, 'role': 'belligerent'} for p in parts],
        'citations': [{'sourceId': '{{%s}}' % s, 'locator': loc, 'evidenceNote': note} for s, loc, note in cites],
    }
    if tn: body['timeNote'] = {'zh-Hant': tn[0], 'en': tn[1]}
    write(f'02-event-{i:02d}-{ph.lower()}.json', ph, '/api/v1/events', body,
          {'verification': 'verified' if cites else 'pending'})

# (key, A, B, start, end, lon, lat, 邊界政權說明)
LOC = 'OHM 主權圖層（sovereignty_records）在開戰日 {d} 的 {pair} 共同邊界，最長一段的中點（build/locations.sql）'
CONFLICTS = [
    ('DE_PL', 'REGIME_DE', 'REGIME_PL', 'EV_WAR_DE_PL', 'EV_END_DE_PL', 16.1391, 51.8947, '1939-09-01', '德—波'),
    ('FR_DE', 'REGIME_FR3', 'REGIME_DE', 'EV_WAR_FR_DE', 'EV_ARMISTICE_FR_DE', 7.7947, 49.0657, '1939-09-03', '法—德'),
    ('SU_PL', 'REGIME_SU', 'REGIME_PL', 'EV_WAR_SU_PL', 'EV_END_SU_PL', 27.5495, 51.6363, '1939-09-17', '蘇—波'),
    ('SU_FI', 'REGIME_SU', 'REGIME_FI', 'EV_WAR_SU_FI', 'EV_MOSCOW_PEACE', 30.4728, 64.1980, '1939-11-30', '蘇—芬'),
    ('DE_DK', 'REGIME_DE', 'REGIME_DK', 'EV_WAR_DE_DK', 'EV_END_DE_DK', 9.1003, 54.8726, '1940-04-09', '德—丹'),
    ('DE_NL', 'REGIME_DE', 'REGIME_NL', 'EV_WAR_DE_NL', 'EV_SURR_NL', 6.4068, 51.8547, '1940-05-10', '德—荷'),
    ('DE_BE', 'REGIME_DE', 'REGIME_BE', 'EV_WAR_DE_BE', 'EV_SURR_BE', 6.3775, 50.4410, '1940-05-10', '德—比'),
    ('DE_LU', 'REGIME_DE', 'REGIME_LU', 'EV_WAR_DE_LU', 'EV_END_DE_LU', 6.3833, 49.8342, '1940-05-10', '德—盧'),
    ('IT_FR', 'REGIME_IT', 'REGIME_FR3', 'EV_WAR_IT_FR', 'EV_ARMISTICE_FR_IT', 6.7182, 44.9621, '1940-06-10', '義—法'),
    ('IT_GR', 'REGIME_IT', 'REGIME_GR', 'EV_WAR_IT_GR', None, 20.6076, 40.0765, '1940-10-28', '義屬阿爾巴尼亞—希臘'),
]
for i, (k, a, b, s, e, lon, lat, d, pair) in enumerate(CONFLICTS, 1):
    write(f'03-conflict-{i:02d}-{k.lower()}.json', f'CF_{k}', '/api/v1/conflict-records', {
        'regimeAId': '{{%s}}' % a, 'regimeBId': '{{%s}}' % b,
        'startEventId': '{{%s}}' % s, 'endEventId': ('{{%s}}' % e) if e else None,
        'location': {'type': 'Point', 'coordinates': [lon, lat]},
        'locationMethod': LOC.format(d=d, pair=pair),
    })
print('ok', len(EVENTS), 'events', len(CONFLICTS), 'conflicts')
