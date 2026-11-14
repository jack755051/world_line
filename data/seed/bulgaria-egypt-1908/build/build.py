#!/usr/bin/env python3
"""產生 bulgaria-egypt-1908 的幾何與請求檔。只讀開發庫，不寫任何資料。
補兩處「匯入時留白、待決定」的地方（Tai 2026-11-14：先做保加利亞和埃及）：
  保加利亞公國 1908-01-01～1908-10-05：幾何沿用保加利亞沙皇國第一筆（1908-10-05 起）；結束事件＝保加利亞宣布獨立
  埃及赫迪夫國 1908-01-01～1914-12-18：幾何沿用埃及蘇丹國第一筆（1914-12-18 起）；結束事件＝英國宣布埃及為保護國
兩者都另記一筆主權爭議：鄂圖曼帝國的宗主權（不畫範圍）。
用法：python3 -I build/build.py
"""
import json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
BG_NEXT, EG_NEXT = '01a192dd-823f-711c-a091-3e993e162a30', '01a19333-5453-77f3-8cb6-bf9477c49303'
EV_BG, EV_EG = '01a192dc-78de-7005-9929-16c3ac95baad', '01a19333-4eff-7788-b7a7-63b5d1408ff9'
OTTOMAN = '01a192dc-65fb-7644-a296-6b5865e4b806'
FRUS1908, FRUS1914 = '01a192dc-49cc-7427-b95f-6f655ec63adb', '01a19333-4d17-728d-b285-5c0ebf9fadef'
def q(sql):
    return subprocess.run(['docker', 'exec', 'worldline-borders-dev-db', 'psql', '-X', '-U', 'worldline', '-d', 'worldline_borders_dev', '-At', '-c', sql], check=True, capture_output=True, text=True).stdout.strip()
def rec(i):
    return json.loads(q(f"select row_to_json(t) from (select geometry_source_id, geometry_locator, geometry_license, attribution, ohm_relation_id, ohm_version, ohm_fetched_at, ohm_start_raw, ohm_end_raw, provenance, round((st_area(geom::geography)/1e6)::numeric) km2, st_asgeojson(geom, 7)::json geom from sovereignty_records where id = '{i}' and retracted_at is null) t"))
bg, eg = rec(BG_NEXT), rec(EG_NEXT)
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': 'BG_1908', 'properties': {}, 'geometry': bg['geom']}, {'type': 'Feature', 'id': 'EG_1908', 'properties': {}, 'geometry': eg['geom']}]},
          open(os.path.join(ROOT, 'bulgaria-egypt-1908-derived.geojson'), 'w'))
def write(name, obj): json.dump(obj, open(os.path.join(ROOT, 'requests', name), 'w'), ensure_ascii=False, indent=1)
write('01-source-hertslet-iv.json', {'_placeholder': 'SRC_HERTSLET_EUROPE_IV', '_post': '/api/v1/sources', 'body': {
    'sourceKind': 'treaty', 'title': 'The Map of Europe by Treaty, vol. IV (1875–1891)', 'publisher': 'Edward Hertslet (ed.); Butterworths, London, 1891',
    'licenseCode': 'pd_expired', 'licenseEvidenceUrl': 'https://archive.org/details/mapofeuropebytre04hert', 'url': 'https://archive.org/details/mapofeuropebytre04hert',
    'family': 'hertslet-treaties', 'grade': 'A',
    'gradeBasis': '英國外交部圖書館長編的條約彙編，收錄條約與議定書本文；條約本文是 A。',
    'note': '2026-11-14 取自 archive.org 的掃描全文（mapofeuropebytre04hert_djvu.txt，SHA-256 1696f95d469278bf0566ef6427dffb97004ad167f877f389be7d1f66ae1047e1）。引文對過光學辨識文字；辨識文字的頁碼不可靠，所以引用位置寫文件編號與條號。'}})
def regime(n, ph, slug, orig, lang, zh, en):
    write(f'{n}-regime-{slug}.json', {'_placeholder': ph, '_post': '/api/v1/regimes', '_meta': {'nameSource': 'Claude 依通行寫法填的自稱原文，還沒有附出處，待查證'},
          'body': {'slug': slug, 'wikidataQid': None, 'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]}})
regime('02', 'REGIME_BG_PRINCIPALITY', 'principality-of-bulgaria', 'Княжество България', 'bg', '保加利亞公國', 'Principality of Bulgaria')
regime('03', 'REGIME_EG_KHEDIVATE', 'khedivate-of-egypt', 'الخديوية المصرية', 'ar', '埃及赫迪夫國', 'Khedivate of Egypt')
def sov(n, ph, regime_ph, feat, src, start, end, ev, zh, en, nxt):
    write(f'{n}-sovereignty-{ph.lower()}.json', {'_placeholder': ph, '_post': '/api/v1/sovereignty-records', '_geometryFrom': feat, '_meta': {'km2': float(src['km2']), 'shapeFromRecord': nxt}, 'body': {
        'regimeId': '{{%s}}' % regime_ph, 'geometry': None, 'validPeriod': {'start': start, 'end': end}, 'layerStatus': 'de_jure',
        'geometrySourceId': src['geometry_source_id'], 'geometryLocator': src['geometry_locator'] + '（沿用下一個政權第一筆的形狀）', 'geometryLicense': src['geometry_license'], 'attribution': src['attribution'],
        'startEventId': None, 'endEventId': ev, 'ohmRelationId': src['ohm_relation_id'], 'ohmVersion': src['ohm_version'], 'ohmFetchedAt': src['ohm_fetched_at'], 'ohmStartRaw': src['ohm_start_raw'], 'ohmEndRaw': src['ohm_end_raw'],
        'provenance': {**(src['provenance'] or {}), 'fix': {'batch': 'bulgaria-egypt-1908', 'shapeFromRecord': nxt, 'reason': '這段期間匯入時留白待決定；Tai 2026-11-14 決定補上。形狀沿用緊接其後的政權第一筆（資料集把那個形狀的起日記在政權更替當天）'}},
        'note': {'zh-Hant': zh, 'en': en}}})
sov('04', 'SOV_BG_1908', 'REGIME_BG_PRINCIPALITY', 'BG_1908', bg, '1908-01-01', '1908-10-05', EV_BG,
    '保加利亞公國（含 1886 年起由保加利亞親王兼任總督的東魯米利亞）。依 1878 年柏林條約是鄂圖曼蘇丹宗主權下的自治納貢公國，1908-10-05 宣布獨立。形狀沿用獨立後保加利亞沙皇國第一筆紀錄，沒有另外查證 1908 年初的邊界細節。',
    'Principality of Bulgaria, including Eastern Roumelia (governed by the Prince of Bulgaria as Governor-General since 1886): an autonomous tributary principality under the suzerainty of the Sultan (Treaty of Berlin, 1878) until it proclaimed independence on 5 October 1908. Shape copied from the first record of the Tsardom.', BG_NEXT)
sov('05', 'SOV_EG_1908', 'REGIME_EG_KHEDIVATE', 'EG_1908', eg, '1908-01-01', '1914-12-18', EV_EG,
    '埃及赫迪夫國：名義上屬鄂圖曼蘇丹宗主權，1882 年起由英國佔領；1914-12-18 英國宣布終止鄂圖曼宗主權、改為英國保護國。形狀沿用埃及蘇丹國第一筆紀錄，沒有另外查證 1908–1914 年間西界與西奈一帶的邊界細節。',
    'Khedivate of Egypt: nominally under the suzerainty of the Ottoman Sultan and under British occupation since 1882, until Britain declared the suzerainty terminated and a protectorate established on 18 December 1914. Shape copied from the first record of the Sultanate.', EG_NEXT)
def cite(n, ph, target, source, locator, note, grade, basis):
    write(f'{n}-citation-{ph.lower()}.json', {'_placeholder': ph, '_post': '/api/v1/sovereignty-records/{{%s}}/citations' % target,
          'body': {'sourceId': source, 'locator': locator, 'evidenceNote': note, 'grade': grade, 'gradeBasis': basis}})
B1 = '具名學者編著的歷史地圖集圖版（學術地圖集為 B）。Claude 目視比對，2026-11-14，待考證複核。'
B2 = '學術機構出版的歷史地圖集圖版（學術地圖集為 B）。Claude 目視比對，2026-11-14，待考證複核。'
cite('06', 'CITE_BG_BERLIN', 'SOV_BG_1908', '{{SRC_HERTSLET_EUROPE_IV}}', 'No. 530, Treaty of Berlin, 13 July 1878, Art. I；No. 611, Arrangement of 5 April 1886, § 1',
     '柏林條約第 1 條：「Bulgaria is constituted an autonomous and tributary Principality under the suzerainty of His Imperial Majesty the Sultan」。1886 年協議第 1 項：「The Governor-Generalship of Eastern Roumelia shall be entrusted to the Prince of Bulgaria」。證明公國的地位，以及東魯米利亞由保加利亞親王兼管；不證明 1908 年的邊界位置。',
     'A', '條約與列強協議本文（英國官方條約彙編所收）。對過 archive.org 掃描的辨識文字，2026-11-14。')
cite('07', 'CITE_BG_FRUS', 'SOV_BG_1908', FRUS1908, 'Doc. 45（美國駐布加勒斯特公使 1908-10-06 函所附，保加利亞外交部長 1908-10-05 照會譯文）',
     '保加利亞外交部長照會：「His Highness the Prince, my August Sovereign … has proclaimed Bulgaria of the north and of the south an independent monarchy.」證明到 1908-10-05 為止元首是親王、國家還不是獨立君主國，而且範圍含南北保加利亞（南保加利亞即東魯米利亞）。',
     'A', '保加利亞政府自己的正式照會（美國國務院外交文件彙編所收的譯文）。逐字核對過 history.state.gov 的頁面文字，2026-11-14。')
cite('08', 'CITE_BG_SHEPHERD', 'SOV_BG_1908', '{{SRC_SHEPHERD_1911}}', 'pp. 166–167, Europe at the Present Time（archive.org 掃描頁 n158–n159）',
     '圖版畫出：保加利亞（含索菲亞、普列文、瓦爾納，以及巴爾幹山以南的菲利波波利一帶），與鄂圖曼的歐洲土耳其、塞爾維亞、羅馬尼亞相鄰。圖版是 1911 年（獨立之後），但 1908 到 1911 年保加利亞的邊界沒有變動，輪廓與本紀錄相符。比例尺很小，只能確認到輪廓與鄰接關係。', 'B', B1)
cite('09', 'CITE_EG_FRUS', 'SOV_EG_1908', FRUS1914, 'Doc. 274, pp. 152–153（英國大使 1914-12-18 照會及所附外交部電報）',
     '英國外交部電報：「His Majesty’s Government consider that the suzerainty of Turkey over Egypt is terminated, and they have advised His Majesty to place Egypt under his protection」。證明到 1914-12-18 為止，英國官方承認土耳其（鄂圖曼）對埃及有宗主權；不證明邊界位置。',
     'A', '英國政府的正式照會（美國國務院外交文件彙編所收）。逐字核對過 history.state.gov 的頁面文字，2026-11-14。')
cite('10', 'CITE_EG_SHEPHERD', 'SOV_EG_1908', '{{SRC_SHEPHERD_1911}}', 'pp. 174–175, The Partition of Africa（archive.org 掃描頁 n166–n167）',
     '圖版畫出：埃及（含西奈半島，南到瓦迪哈勒法一帶，西接的黎波里的利比亞沙漠），圖例註明「Egypt tributary to the Ottoman Empire, and subject to the financial control of Great Britain」。輪廓與地位都與本紀錄相符。比例尺 1:40,000,000，只能確認到輪廓與鄰接關係。', 'B', B1)
cite('11', 'CITE_EG_CMHA', 'SOV_EG_1908', '{{SRC_CMHA_1924}}', 'Map 130, Africa in 1910（archive.org 掃描頁 n589–n590）',
     '圖版畫出：埃及標名，以英國色著色、外圍加一圈鄂圖曼色的邊框（英國佔領、名義上屬鄂圖曼），含西奈半島與錫瓦，南接英埃蘇丹、西接的黎波里。輪廓與本紀錄相符。只能確認到輪廓與鄰接關係。', 'B', B2)
def dispute(n, ph, slug, zh, en, rec_ph, regime_ph, own_zh, own_en, ott_zh, ott_en, eff=(True, False)):
    write(f'{n}-dispute-{slug}.json', {'_placeholder': ph, '_post': '/api/v1/sovereignty-disputes', 'body': {'slug': slug, 'summary': {'zh-Hant': zh, 'en': en}, 'claims': [
        {'claimantRegimeId': '{{%s}}' % regime_ph, 'recordId': '{{%s}}' % rec_ph, 'effective': eff[0], 'position': {'zh-Hant': own_zh, 'en': own_en}},
        {'claimantRegimeId': OTTOMAN, 'recordId': None, 'effective': eff[1], 'position': {'zh-Hant': ott_zh, 'en': ott_en}}]}})
dispute('12', 'DISPUTE_BG', 'bulgaria-ottoman-suzerainty-1908',
        '保加利亞公國的地位：依 1878 年柏林條約是鄂圖曼蘇丹宗主權下的自治納貢公國，實際上自行治理；1908-10-05 宣布獨立後這層關係才結束。這不是兩國爭奪同一塊地，而是名義上的宗主權與實際自治並存；本系統兩者都記，不裁判哪一個才算主權。',
        'Status of the Principality of Bulgaria: under the Treaty of Berlin (1878) an autonomous tributary principality under the suzerainty of the Sultan, self-governing in practice, until it proclaimed independence on 5 October 1908. Nominal suzerainty and actual autonomy stood side by side; both are recorded.',
        'SOV_BG_1908', 'REGIME_BG_PRINCIPALITY',
        '實際治理保加利亞與東魯米利亞。出處：柏林條約第 1 條、1886 年協議（Hertslet 第 4 卷，A）；保加利亞外交部長 1908-10-05 照會（FRUS 1908 Doc. 45，A）。',
        'Governed Bulgaria and Eastern Roumelia in practice. Sources: Treaty of Berlin Art. I and the Arrangement of 1886 (Hertslet vol. IV, grade A); note of the Bulgarian foreign minister, 5 October 1908 (FRUS 1908, Doc. 45, grade A).',
        '依柏林條約第 1 條對保加利亞公國有宗主權（Hertslet 第 4 卷，A）。資料庫裡鄂圖曼帝國的紀錄不含保加利亞，這項宗主權沒有另外畫範圍。',
        'Held suzerainty over the Principality under Art. I of the Treaty of Berlin (Hertslet vol. IV, grade A). The Ottoman record does not include Bulgaria; no separate extent is drawn for the suzerainty.')
dispute('13', 'DISPUTE_EG', 'egypt-ottoman-suzerainty-1908-1914',
        '埃及的地位：名義上屬鄂圖曼蘇丹宗主權，由赫迪夫治理，1882 年起由英國佔領並控制財政。1914-12-18 英國宣布鄂圖曼宗主權終止、埃及成為英國保護國。英國在這之前沒有主張埃及的主權，所以不列為主張方；本系統不裁判當時誰才算主權者。',
        'Status of Egypt: nominally under the suzerainty of the Ottoman Sultan, governed by the Khedive, and under British occupation and financial control since 1882. On 18 December 1914 Britain declared the suzerainty terminated and Egypt a British protectorate. Britain made no claim to sovereignty before that date and is not listed as a claimant.',
        'SOV_EG_1908', 'REGIME_EG_KHEDIVATE',
        '赫迪夫政府實際治理埃及（在英國佔領之下）。出處：Shepherd 1911 pp. 174–175 圖例「Egypt tributary to the Ottoman Empire, and subject to the financial control of Great Britain」（B）。',
        'The Khedivial government administered Egypt (under British occupation). Source: Shepherd 1911, pp. 174–175, legend "Egypt tributary to the Ottoman Empire, and subject to the financial control of Great Britain" (grade B).',
        '對埃及有宗主權，到 1914-12-18 為止。出處：英國外交部 1914-12-18 電報稱「the suzerainty of Turkey over Egypt is terminated」（FRUS 1914 Supplement Doc. 274，A，第三方／佔領方的官方文件）；鄂圖曼自己的出處還沒取得。沒有另外畫範圍。',
        'Held suzerainty over Egypt until 18 December 1914. Source: British Foreign Office telegram of that date, "the suzerainty of Turkey over Egypt is terminated" (FRUS 1914 Supplement, Doc. 274, grade A; a document of the occupying power). No Ottoman source obtained yet. No separate extent is drawn.',
        eff=(None, None))   # 埃及當時實際由誰作主（赫迪夫或英國佔領當局）沒有查，不標
print('bg km2', bg['km2'], 'eg km2', eg['km2'])
