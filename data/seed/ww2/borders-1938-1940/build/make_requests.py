#!/usr/bin/env python3
"""由 ohm-manifest.json＋本檔的政權／事件對照，產生 requests/*.json（主權圖層試驗 1938–1940，DRAFT）。
- 幾何不內嵌：sovereignty 請求以 `_geometryFrom` 指向 borders-ohm-1938-1940.geojson 的 OHM 關係 id，送出時才讀入。
- `_meta.priorPlaceholder: true` 的來源／政權在正式庫已存在（france-1940-07-15、fr-uk-1940、alignments 批次），
  send_seed.py 若在前置 id 表找到就略過，不重建。
- 事件沒有合格引用 → 不附 citations，API 回 verification = pending（「待查證」）。不推測。
"""
import json, os, re, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'requests')
man = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json'), encoding='utf-8'))}
geo_ids = {f['id'] for f in json.load(open(os.path.join(ROOT, 'borders-ohm-1938-1940.geojson')))['features']}

USGPO = 'United States Department of State; United States Government Printing Office, Washington'
SOURCES = [
    ('SRC_OHM', False, dict(sourceKind='dataset', title='OpenHistoricalMap — boundary=administrative, admin_level=2 關係（歐陸，1938–1940 試驗）',
        publisher='OpenHistoricalMap contributors', licenseCode='cc0', licenseEvidenceUrl='https://www.openhistoricalmap.org/copyright',
        url='https://overpass-api.openhistoricalmap.org/api/interpreter',
        publishedText='Overpass osm_base 2026-10-30T19:22:26Z；逐筆關係版本見 ohm-manifest.json',
        note='OHM 整體以 CC0 1.0 釋出；部分成員線段另帶 license=CC BY 4.0 標籤（逐筆在 sovereignty 紀錄的 geometryLicense／attribution 標示），另有線段來源標示 OSM 匯入（ODbL 疑慮，待 Tai 決定）。')),
    ('SRC_NE_LAND', False, dict(sourceKind='dataset', title='Natural Earth 1:10m Physical Vectors — Land（v5.1.1）',
        publisher='Natural Earth（North American Cartographic Information Society 支援）', licenseCode='public_domain',
        licenseEvidenceUrl='https://www.naturalearthdata.com/about/terms-of-use/', url='https://naciscdn.org/naturalearth/10m/physical/ne_10m_land.zip',
        note='只用來裁切海岸線（不是疆界依據）。')),
    ('SRC_FRUS_1938_I', False, dict(sourceKind='official_record', title='Foreign Relations of the United States, Diplomatic Papers, 1938, General, Volume I',
        publisher=USGPO, licenseCode='us_federal_pd', licenseEvidenceUrl='https://www.state.gov/copyright-information',
        url='https://history.state.gov/historicaldocuments/frus1938v01', publishedText='1955')),
    ('SRC_FRUS_1939_I', True, dict(sourceKind='official_record', title='Foreign Relations of the United States, Diplomatic Papers, 1939, General, Volume I',
        publisher=USGPO, licenseCode='us_federal_pd', licenseEvidenceUrl='https://www.state.gov/copyright-information',
        url='https://history.state.gov/historicaldocuments/frus1939v01', publishedText='1956')),
    ('SRC_FRUS_1939_II', False, dict(sourceKind='official_record', title='Foreign Relations of the United States, Diplomatic Papers, 1939, General, The British Commonwealth and Europe, Volume II',
        publisher=USGPO, licenseCode='us_federal_pd', licenseEvidenceUrl='https://www.state.gov/copyright-information',
        url='https://history.state.gov/historicaldocuments/frus1939v02', publishedText='1956')),
    ('SRC_FRUS_1940_I', True, dict(sourceKind='official_record', title='Foreign Relations of the United States, Diplomatic Papers, 1940, General, Volume I',
        publisher=USGPO, licenseCode='us_federal_pd', licenseEvidenceUrl='https://www.state.gov/copyright-information',
        url='https://history.state.gov/historicaldocuments/frus1940v01', publishedText='1959')),
    ('SRC_FRUS_1940_III', False, dict(sourceKind='official_record', title='Foreign Relations of the United States, Diplomatic Papers, 1940, The British Commonwealth, The Soviet Union, The Near East and Africa, Volume III',
        publisher=USGPO, licenseCode='us_federal_pd', licenseEvidenceUrl='https://www.state.gov/copyright-information',
        url='https://history.state.gov/historicaldocuments/frus1940v03', publishedText='1958')),
    ('SRC_DGFP_D4_GPO', False, dict(sourceKind='official_record', title='Documents on German Foreign Policy 1918–1945, Series D (1937–1945), Volume IV: The Aftermath of Munich, October 1938–March 1939（美國國務院版）',
        publisher='U.S. Department of State（Publication 3883）／United States Government Printing Office, Washington', licenseCode='us_federal_pd',
        licenseEvidenceUrl='https://www.state.gov/copyright-information', url='https://archive.org/details/in.ernet.dli.2015.78774', publishedText='1951')),
    ('SRC_DGFP_D8_GPO', False, dict(sourceKind='official_record', title='Documents on German Foreign Policy 1918–1945, Series D (1937–1945), Volume VIII: The War Years, September 4, 1939–March 18, 1940（美國國務院版）',
        publisher='U.S. Department of State／United States Government Printing Office, Washington', licenseCode='us_federal_pd',
        licenseEvidenceUrl='https://www.state.gov/copyright-information', url='https://archive.org/details/documentsongerma014726mbp', publishedText='1954')),
    ('SRC_DGFP_D9', True, dict(sourceKind='official_record', title='Documents on German Foreign Policy 1918–1945, Series D (1937–1945), Vol. IX: The War Years, March 18–June 22, 1940',
        publisher='United States Department of State（Publication 6312）; United States Government Printing Office, Washington', licenseCode='us_federal_pd',
        licenseEvidenceUrl='https://avalon.law.yale.edu/wwii/frgearm.asp', url='https://avalon.law.yale.edu/wwii/frgearm.asp', publishedText='1956')),
]

# (placeholder, priorPlaceholder, slug, self 原文, 語言, zh-Hant, en, wikidata（取自 OHM 關係的 wikidata 標籤；沒有就留空）)
REGIMES = [
    ('REGIME_DE', True, 'deutsches-reich', 'Deutsches Reich', 'de', '德意志國', 'German Reich'),
    ('REGIME_FR3', True, 'french-third-republic', 'République française', 'fr', '法蘭西共和國（第三共和）', 'French Republic (Third Republic)'),
    ('REGIME_FR_STATE', True, 'french-state-vichy', 'État français', 'fr', '法蘭西國（維琪）', 'French State (Vichy)'),
    ('REGIME_UK', True, 'united-kingdom', 'United Kingdom of Great Britain and Northern Ireland', 'en', '大不列顛及北愛爾蘭聯合王國', 'United Kingdom'),
    ('REGIME_AT', False, 'federal-state-of-austria', 'Bundesstaat Österreich', 'de', '奧地利聯邦國', 'Federal State of Austria'),
    ('REGIME_CS', False, 'czechoslovak-republic', 'Republika Československá', 'cs', '捷克斯洛伐克共和國', 'Czechoslovak Republic'),
    ('REGIME_SK', False, 'slovak-state-1939', 'Slovenský štát', 'sk', '斯洛伐克國', 'Slovak State'),
    ('REGIME_HU', False, 'kingdom-of-hungary', 'Magyar Királyság', 'hu', '匈牙利王國', 'Kingdom of Hungary'),
    ('REGIME_PL', False, 'polish-republic', 'Rzeczpospolita Polska', 'pl', '波蘭共和國', 'Republic of Poland'),
    ('REGIME_DANZIG', False, 'free-city-of-danzig', 'Freie Stadt Danzig', 'de', '但澤自由市', 'Free City of Danzig'),
    ('REGIME_LT', False, 'republic-of-lithuania', 'Lietuvos Respublika', 'lt', '立陶宛共和國', 'Republic of Lithuania'),
    ('REGIME_LT_SSR', False, 'lithuanian-ssr', 'Lietuvos Tarybų Socialistinė Respublika', 'lt', '立陶宛蘇維埃社會主義共和國', 'Lithuanian Soviet Socialist Republic'),
    ('REGIME_LV', False, 'republic-of-latvia', 'Latvijas Republika', 'lv', '拉脫維亞共和國', 'Republic of Latvia'),
    ('REGIME_LV_SSR', False, 'latvian-ssr', 'Latvijas Padomju Sociālistiskā Republika', 'lv', '拉脫維亞蘇維埃社會主義共和國', 'Latvian Soviet Socialist Republic'),
    ('REGIME_EE', False, 'republic-of-estonia', 'Eesti Vabariik', 'et', '愛沙尼亞共和國', 'Republic of Estonia'),
    ('REGIME_EE_SSR', False, 'estonian-ssr', 'Eesti Nõukogude Sotsialistlik Vabariik', 'et', '愛沙尼亞蘇維埃社會主義共和國', 'Estonian Soviet Socialist Republic'),
    ('REGIME_SU', False, 'soviet-union', 'Союз Советских Социалистических Республик', 'ru', '蘇維埃社會主義共和國聯盟', 'Union of Soviet Socialist Republics'),
    ('REGIME_FI', False, 'republic-of-finland', 'Suomen tasavalta', 'fi', '芬蘭共和國', 'Republic of Finland'),
    ('REGIME_RO', False, 'kingdom-of-romania', 'Regatul României', 'ro', '羅馬尼亞王國', 'Kingdom of Romania'),
    ('REGIME_BG', False, 'tsardom-of-bulgaria', 'Царство България', 'bg', '保加利亞王國', 'Tsardom of Bulgaria'),
    ('REGIME_AL', False, 'albanian-kingdom', 'Mbretëria Shqiptare', 'sq', '阿爾巴尼亞王國', 'Albanian Kingdom'),
    ('REGIME_AL_IT', False, 'albania-under-italy', 'Mbretëria Shqiptare', 'sq', '阿爾巴尼亞王國（義大利國王兼領）', 'Albanian Kingdom under Italy'),
    ('REGIME_IT', False, 'kingdom-of-italy', "Regno d'Italia", 'it', '義大利王國', 'Kingdom of Italy'),
    ('REGIME_IT_AEGEAN', False, 'italian-aegean-islands', "Isole italiane dell'Egeo", 'it', '義屬愛琴海群島', 'Italian Islands of the Aegean'),
    ('REGIME_MILVERW_BE', False, 'mil-admin-belgium-northern-france', 'Militärverwaltung in Belgien und Nordfrankreich', 'de', '比利時與北法軍政府', 'Military Administration in Belgium and Northern France'),
    ('REGIME_BE', False, 'kingdom-of-belgium', 'Royaume de Belgique', 'fr', '比利時王國', 'Kingdom of Belgium'),
    ('REGIME_NL', False, 'kingdom-of-the-netherlands', 'Koninkrijk der Nederlanden', 'nl', '荷蘭王國', 'Kingdom of the Netherlands'),
    ('REGIME_LU', False, 'grand-duchy-of-luxembourg', 'Grand-Duché de Luxembourg', 'fr', '盧森堡大公國', 'Grand Duchy of Luxembourg'),
    ('REGIME_YU', False, 'kingdom-of-yugoslavia', 'Краљевина Југославија', 'sr', '南斯拉夫王國', 'Kingdom of Yugoslavia'),
    ('REGIME_GR', False, 'kingdom-of-greece', 'Βασίλειον της Ελλάδος', 'el', '希臘王國', 'Kingdom of Greece'),
    ('REGIME_TR', False, 'republic-of-turkey', 'Türkiye Cumhuriyeti', 'tr', '土耳其共和國', 'Republic of Turkey'),
    ('REGIME_ES_REP', False, 'spanish-republic', 'República Española', 'es', '西班牙共和國', 'Spanish Republic'),
    ('REGIME_ES_STATE', False, 'spanish-state', 'Estado Español', 'es', '西班牙國', 'Spanish State'),
    ('REGIME_PT', False, 'portuguese-republic', 'República Portuguesa', 'pt', '葡萄牙共和國', 'Portuguese Republic'),
    ('REGIME_CH', False, 'swiss-confederation', 'Schweizerische Eidgenossenschaft', 'de', '瑞士聯邦', 'Swiss Confederation'),
    ('REGIME_IE', False, 'ireland-eire', 'Éire', 'ga', '愛爾蘭', 'Ireland'),
    ('REGIME_DK', False, 'kingdom-of-denmark', 'Kongeriget Danmark', 'da', '丹麥王國', 'Kingdom of Denmark'),
    ('REGIME_NO', False, 'kingdom-of-norway', 'Kongeriket Norge', 'nb', '挪威王國', 'Kingdom of Norway'),
    ('REGIME_SE', False, 'kingdom-of-sweden', 'Konungariket Sverige', 'sv', '瑞典王國', 'Kingdom of Sweden'),
    ('REGIME_AD', False, 'principality-of-andorra', "Principat d'Andorra", 'ca', '安道爾', 'Andorra'),
    ('REGIME_MC', False, 'principality-of-monaco', 'Principauté de Monaco', 'fr', '摩納哥', 'Monaco'),
    ('REGIME_LI', False, 'principality-of-liechtenstein', 'Fürstentum Liechtenstein', 'de', '列支敦斯登', 'Liechtenstein'),
    ('REGIME_SM', False, 'republic-of-san-marino', 'Repubblica di San Marino', 'it', '聖馬利諾', 'San Marino'),
    ('REGIME_VA', False, 'vatican-city-state', 'Stato della Città del Vaticano', 'it', '梵蒂岡城國', 'Vatican City State'),
    ('REGIME_GI', False, 'gibraltar-crown-colony', 'Gibraltar', 'en', '直布羅陀（英國殖民地）', 'Gibraltar (British crown colony)'),
    ('REGIME_MT', False, 'malta-crown-colony', 'Malta', 'en', '馬爾他（英國殖民地）', 'Malta (British crown colony)'),
    ('REGIME_IM', False, 'isle-of-man', 'Isle of Man', 'en', '曼島（英國皇家屬地）', 'Isle of Man (Crown dependency)'),
    ('REGIME_GG', False, 'bailiwick-of-guernsey', 'Bailiwick of Guernsey', 'en', '根西（英國皇家屬地）', 'Bailiwick of Guernsey (Crown dependency)'),
    ('REGIME_JE', False, 'bailiwick-of-jersey', 'Bailiwick of Jersey', 'en', '澤西（英國皇家屬地）', 'Bailiwick of Jersey (Crown dependency)'),
]

REL_REGIME = {
    2693085: 'REGIME_DE', 2704712: 'REGIME_DE', 2704711: 'REGIME_DE', 2704710: 'REGIME_DE', 2704709: 'REGIME_DE', 2704716: 'REGIME_DE',
    2704715: 'REGIME_DE', 2704714: 'REGIME_DE', 2704713: 'REGIME_DE',
    2858751: 'REGIME_AT', 2692764: 'REGIME_CS', 2747874: 'REGIME_CS', 2857482: 'REGIME_CS',
    2692769: 'REGIME_SK', 2692768: 'REGIME_SK', 2747847: 'REGIME_SK',
    2695633: 'REGIME_HU', 2747873: 'REGIME_HU', 2747872: 'REGIME_HU', 2747871: 'REGIME_HU', 2747817: 'REGIME_HU',
    2692205: 'REGIME_PL', 2741574: 'REGIME_PL', 2691478: 'REGIME_DANZIG',
    2692218: 'REGIME_LT', 2855606: 'REGIME_LT', 2848250: 'REGIME_LT', 2694785: 'REGIME_LT_SSR',
    2704702: 'REGIME_LV', 2694787: 'REGIME_LV_SSR', 2801387: 'REGIME_EE', 2694790: 'REGIME_EE_SSR',
    2851157: 'REGIME_SU', 2848248: 'REGIME_SU', 2848241: 'REGIME_SU', 2851878: 'REGIME_SU', 2848258: 'REGIME_SU',
    2848256: 'REGIME_SU', 2848811: 'REGIME_SU', 2848812: 'REGIME_SU',
    2959045: 'REGIME_FI', 2692833: 'REGIME_FI',
    2693259: 'REGIME_RO', 2693258: 'REGIME_RO', 2693257: 'REGIME_RO', 2693256: 'REGIME_RO',
    2848878: 'REGIME_BG', 2855603: 'REGIME_BG', 2800554: 'REGIME_AL', 2855615: 'REGIME_AL_IT',
    2851104: 'REGIME_IT', 2696324: 'REGIME_IT', 2920371: 'REGIME_IT_AEGEAN',
    2696299: 'REGIME_FR3', 2747868: 'REGIME_FR_STATE', 2748553: 'REGIME_MILVERW_BE',
    2800293: 'REGIME_BE', 2883430: 'REGIME_NL', 2748545: 'REGIME_LU', 2747831: 'REGIME_YU', 2873762: 'REGIME_GR',
    2801012: 'REGIME_TR', 2864004: 'REGIME_TR', 2860484: 'REGIME_ES_REP', 2862761: 'REGIME_ES_STATE',
    2807009: 'REGIME_PT', 2798802: 'REGIME_CH', 2693292: 'REGIME_UK', 2692985: 'REGIME_IE', 2869937: 'REGIME_DK',
    2851798: 'REGIME_NO', 2870046: 'REGIME_SE', 2739874: 'REGIME_AD', 2693418: 'REGIME_MC', 2746467: 'REGIME_LI',
    2853735: 'REGIME_SM', 2751259: 'REGIME_VA', 2692855: 'REGIME_GI', 2801185: 'REGIME_MT', 2693293: 'REGIME_IM',
    2828270: 'REGIME_GG', 2828299: 'REGIME_JE',
}
NOT_SOVEREIGN = {2748553}

def C(src, locator, note): return dict(sourceId='{{%s}}' % src, locator=locator, evidenceNote=note)
# (placeholder, kind, start, end(exclusive), zh, en, citations, timeNote zh/en or None)
EVENTS = [
    ('EV_ANSCHLUSS', 'political', '1938-03-13', '1938-03-14', '德奧合併：《奧地利與德意志國重新統一法》', 'Anschluss: law on the reunion of Austria with the German Reich',
     [C('SRC_FRUS_1938_I', 'Doc. 454, p. 438', '美國駐奧公使 Wiley 電報轉述「奧地利與德意志國重新統一」憲法性法律第 1 條。'),
      C('SRC_FRUS_1938_I', 'Doc. 457, p. 441', '德國方面同日（1938-03-13，林茨）公布的重新統一法。')], None),
    ('EV_MUNICH', 'treaty', '1938-09-29', '1938-10-01', '慕尼黑協定：蘇台德地區割予德國（1938-09-29 夜簽、09-30 凌晨簽字日期）', 'Munich Agreement: cession of the Sudeten German territory',
     [C('SRC_FRUS_1938_I', 'Doc. 682, p. 702', '美國駐捷公使 Carr 9 月 30 日電報：協定內容與 10 月 1–10 日分區佔領；註腳指向 DGFP D/II 文件 675, p. 1014（協定本文）。')],
     ('協定文本日期為 1938-09-29，簽字於 9 月 30 日凌晨；OHM 以 09-30 為捷克斯洛伐克疆界變動日。', 'Dated 29 September 1938, signed in the early hours of 30 September; OHM uses 30 Sept.')),
    ('EV_ZAOLZIE', 'political', '1938-10-02', '1938-11-02', '波蘭取得切申（Zaolzie）等地（OHM 變動日 1938-11-01）', 'Poland takes Teschen (Zaolzie) and other border areas (OHM change 1938-11-01)', [], None),
    ('EV_VIENNA1', 'treaty', '1938-11-02', '1938-11-03', '第一次維也納仲裁：斯洛伐克南部與喀爾巴阡烏克蘭南部劃歸匈牙利', 'First Vienna Award: southern Slovakia and southern Carpatho-Ukraine to Hungary',
     [C('SRC_DGFP_D4_GPO', 'Doc. 99, pp. 118–126（仲裁本文 pp. 125–126）', '1938-11-02 維也納仲裁紀錄與仲裁文本。')], None),
    ('EV_DE_CS_BORDER_1938', 'treaty', '1938-11-20', '1938-11-22', '德捷邊界最終劃定（OHM 變動日 1938-11-21）', 'Final German–Czechoslovak boundary delimitation (OHM change 1938-11-21)', [], None),
    ('EV_SLOVAK_INDEP', 'political', '1939-03-14', '1939-03-15', '斯洛伐克宣布獨立（斯洛伐克國成立）', 'Slovakia declares independence',
     [C('SRC_FRUS_1939_I', 'Doc. 58, pp. 60–61', '美國駐捷公使 Carr 經布拉格總領事轉報：斯洛伐克宣布獨立係德國策動。')], None),
    ('EV_CARPATHO', 'political', '1939-03-14', '1939-03-19', '匈牙利佔領並併入喀爾巴阡烏克蘭', 'Hungary occupies and annexes Carpatho-Ukraine',
     [C('SRC_DGFP_D4_GPO', 'Doc. 236, p. 275', '匈牙利出兵喀爾巴阡烏克蘭的相關電報。'), C('SRC_DGFP_D4_GPO', 'Doc. 237, p. 276', '同上，德方回應。')],
     ('3 月 14–18 日間進行；OHM 以 03-14 為匈牙利疆界變動日。', 'Took place 14–18 March; OHM uses 14 March.')),
    ('EV_PROTECTORATE', 'political', '1939-03-15', '1939-03-17', '捷克斯洛伐克解體：希特勒—哈卡會談與波希米亞—摩拉維亞保護國成立', 'Dissolution of Czechoslovakia: Hitler–Hácha meeting and the Protectorate of Bohemia and Moravia',
     [C('SRC_DGFP_D4_GPO', 'Doc. 228, p. 263', '1939-03-15 凌晨希特勒與哈卡會談紀錄。'),
      C('SRC_DGFP_D4_GPO', 'Doc. 229, p. 270', '1939-03-15 德捷聲明：捷克人民的命運交由德國元首。'),
      C('SRC_DGFP_D4_GPO', 'Doc. 246, p. 283', '1939-03-16 建立波希米亞—摩拉維亞保護國的元首命令（第 1 條：屬於大德意志國領土）。')],
     ('OHM 以 1939-03-16 將保護國併入德國國界。', 'OHM includes the Protectorate in the Reich boundary from 16 March 1939.')),
    ('EV_MEMEL', 'treaty', '1939-03-22', '1939-03-24', '立陶宛將梅梅爾（克萊佩達）地區割予德國', 'Lithuania cedes the Memel (Klaipėda) Territory to Germany',
     [C('SRC_FRUS_1939_I', 'Doc. 81, pp. 87–88', '美國駐立陶宛使館報告立陶宛已割讓梅梅爾。'), C('SRC_FRUS_1939_I', 'Doc. 80, p. 87', '同事件前一日的報告。')],
     ('條約 1939-03-22 簽字；OHM 德國 03-22、立陶宛 03-23 變動。', 'Treaty signed 22 March 1939; OHM changes Germany on 22 and Lithuania on 23 March.')),
    ('EV_HU_SK_1939', 'political', '1939-03-23', '1939-04-05', '匈斯邊界衝突後匈牙利取得斯洛伐克東部一帶（OHM 變動日 1939-04-04）', 'Hungary gains a strip of eastern Slovakia after the border war (OHM change 1939-04-04)', [], None),
    ('EV_ALBANIA', 'political', '1939-04-07', '1939-04-17', '義大利入侵並兼領阿爾巴尼亞（04-12 制憲會議獻冠、04-16 義王接受）', 'Italy invades Albania; crown offered to Victor Emmanuel III (12 Apr) and accepted (16 Apr)',
     [C('SRC_FRUS_1939_II', 'Doc. 363, pp. 410–411', '阿爾巴尼亞王冠由義大利國王兼領的報告。'), C('SRC_FRUS_1939_II', 'Doc. 357, pp. 403–404', '義大利出兵阿爾巴尼亞的報告。')],
     ('OHM 以 1939-04-12 為政權替換日。', 'OHM uses 12 April 1939.')),
    ('EV_SPAIN_1939', 'political', '1939-04-01', '1939-04-02', '西班牙內戰結束，國民軍政權統治全境（OHM 政權替換日 1939-04-01）', 'End of the Spanish Civil War; Nationalist state over all Spain (OHM regime change 1939-04-01)', [], None),
    ('EV_HATAY', 'treaty', '1939-06-23', '1939-06-30', '哈塔伊（亞歷山大勒塔）併入土耳其（OHM 變動日 1939-06-29）', 'Hatay (Alexandretta) annexed by Turkey (OHM change 1939-06-29)', [], None),
    ('EV_DANZIG', 'political', '1939-09-01', '1939-09-02', '但澤自由市併入德國（OHM 但澤止於 1939-09-01）', 'Free City of Danzig incorporated into Germany (OHM Danzig ends 1939-09-01)', [], None),
    ('EV_POLAND_PARTITION', 'treaty', '1939-09-28', '1939-09-29', '波蘭被瓜分：德蘇邊界暨友好條約', 'Partition of Poland: German–Soviet Boundary and Friendship Treaty',
     [C('SRC_DGFP_D8_GPO', 'Doc. 157, pp. 164–165', '1939-09-28 德蘇邊界暨友好條約本文（劃定雙方在前波蘭領土上的利益分界）。'),
      C('SRC_FRUS_1939_I', 'Doc. 514, p. 495（編者註）', '編者註：蘇聯最高蘇維埃於 1939 年 11 月初將西烏克蘭、西白俄羅斯併入烏克蘭與白俄羅斯兩加盟共和國。')],
     ('OHM 以 1939-10-06（波蘭最後抵抗結束）為波蘭國界終止與蘇聯國界變動日；蘇聯法律上的併入為 11 月初。', 'OHM ends Poland and changes the USSR on 6 Oct 1939; formal Soviet incorporation was early November.')),
    ('EV_DE_EASTERN_DECREE', 'political', '1939-10-08', '1939-10-27', '德國以元首命令併入波蘭西部（1939-10-08 公布、10-26 生效；OHM 變動日 1939-10-26）', 'German decree annexing western Poland (8 Oct, effective 26 Oct 1939; OHM change 26 Oct)', [],
     ('線索：NCA 第 III 冊 Doc. 066-PS, pp. 111–112 引用此命令（RGBl. I S. 2042），但未載本文與生效日，故仍標待查證。', 'Lead: NCA vol. III, Doc. 066-PS, pp. 111–112 cites the decree (RGBl. I p. 2042) without its text or effective date; still pending.')),
    ('EV_VILNIUS', 'treaty', '1939-10-10', '1939-10-29', '蘇聯依蘇立互助條約將維爾紐斯地區交予立陶宛（OHM 變動日 1939-10-28）', 'USSR transfers the Vilnius region to Lithuania under the mutual-assistance treaty (OHM change 1939-10-28)',
     [C('SRC_FRUS_1939_I', 'Doc. 1063, pp. 968–970', '莫洛托夫向美國大使表示：蘇聯將維爾紐斯（Wilno）歸還立陶宛。文件未載實際移交日（OHM 用 10-28）。')], None),
    ('EV_SK_POLISH_AREAS', 'political', '1939-11-21', '1939-11-22', '斯洛伐克取得原波蘭北部邊境地區（OHM 變動日 1939-11-21）', 'Slovakia gains former Polish border areas (OHM change 1939-11-21)', [], None),
    ('EV_MOSCOW_PEACE', 'treaty', '1940-03-12', '1940-03-13', '蘇芬《莫斯科和約》：芬蘭割讓卡累利阿地峽等地', 'Treaty of Moscow: Finland cedes the Karelian Isthmus and other areas to the USSR',
     [C('SRC_FRUS_1940_I', 'Doc. 287, pp. 314–317', '1940-03-12 蘇芬和約本文。'), C('SRC_FRUS_1940_I', 'Doc. 286, p. 314', '和約簽字的報告。')], None),
    ('EV_EUPEN', 'political', '1940-05-18', '1940-05-19', '德國併入奧伊彭—馬爾梅迪（OHM 變動日 1940-05-18）', 'Germany annexes Eupen-Malmedy (OHM change 1940-05-18)', [], None),
    ('EV_DE_19400601', 'political', '1940-06-01', '1940-06-02', 'OHM 德國國界版本變動（1940-06-01，內容待查）', 'OHM German Reich boundary version change on 1940-06-01 (content unknown)', [], None),
    ('EV_ARMISTICE_FR_DE', 'armistice', '1940-06-22', '1940-06-23', '德法停戰協定（貢比涅；1940-06-25 生效）', 'Franco-German Armistice (Compiègne; in force 25 June 1940)',
     [C('SRC_DGFP_D9', 'pp. 671–676，德法停戰協定第 III、X 條', '停戰協定本文：佔領區（第 III 條）等。locator 沿用 fr-uk-1940 已審 seed。')],
     ('OHM 法蘭西共和國止於 06-22、法蘭西國與比北軍政府始於 06-25（停戰生效）。', 'OHM ends the French Republic on 22 June; French State and the Military Administration begin 25 June.')),
    ('EV_ARMISTICE_FR_IT', 'armistice', '1940-06-24', '1940-06-25', '法義停戰協定（羅馬）', 'Franco-Italian Armistice (Rome)',
     [C('SRC_FRUS_1940_III', 'Doc. 837, p. 909（註腳）', '註腳：法義停戰協定 1940-06-24 簽字。')],
     ('OHM 以 06-24 把義軍佔領的芒通一帶畫入義大利國界；這是佔領而非法理割讓（待 Tai 決定）。', 'OHM adds the Italian-occupied Menton area to Italy from 24 June; occupation, not de jure cession (decision pending).')),
    ('EV_BE_MILADMIN', 'political', '1940-05-28', '1940-06-26', '比利時投降後由德國軍政府管轄（OHM 比利時止於 1940-06-25）', 'Belgium under German military administration after capitulation (OHM Belgium ends 1940-06-25)', [], None),
    ('EV_LV_OCCUPATION', 'political', '1940-06-16', '1940-06-18', '蘇聯最後通牒與進駐拉脫維亞（OHM 拉脫維亞止於 1940-06-16）', 'Soviet ultimatum and occupation of Latvia (OHM Latvia ends 1940-06-16)', [], None),
    ('EV_BESSARABIA', 'political', '1940-06-26', '1940-06-29', '蘇聯最後通牒，羅馬尼亞割讓比薩拉比亞與北布科維納', 'Soviet ultimatum; Romania cedes Bessarabia and northern Bukovina',
     [C('SRC_FRUS_1940_I', 'Doc. 501, pp. 479–480', '蘇聯對羅馬尼亞最後通牒。'), C('SRC_FRUS_1940_I', 'Doc. 502, pp. 480–481', '最後通牒後續。'),
      C('SRC_FRUS_1940_I', 'Doc. 506, pp. 484–485', '羅馬尼亞 6 月 28 日接受。')], None),
    ('EV_LT_SSR', 'political', '1940-07-21', '1940-07-22', '立陶宛「人民議會」宣布蘇維埃制度並請求加入蘇聯', 'Lithuanian "People\'s Seimas" proclaims Soviet rule and requests admission to the USSR',
     [C('SRC_FRUS_1940_I', 'Doc. 417, p. 404', '美國駐立陶宛公使報告：1940-07-21 宣布建立蘇維埃制度並請求加入蘇聯。')], None),
    ('EV_LV_SSR', 'political', '1940-07-21', '1940-07-22', '拉脫維亞議會宣布蘇維埃制度（OHM 拉脫維亞蘇維埃共和國始於 1940-07-21）', 'Latvian Saeima proclaims Soviet rule (OHM Latvian SSR begins 1940-07-21)', [], None),
    ('EV_EE_SSR', 'political', '1940-07-21', '1940-07-23', '愛沙尼亞議會宣布蘇維埃制度並決議加入蘇聯', 'Estonian parliament proclaims Soviet rule and resolves to join the USSR',
     [C('SRC_FRUS_1940_I', 'Doc. 408, p. 399', '1940-07-21 新議會議程：蘇維埃化、與蘇聯合併；註腳：7 月 22 日通過合併決議。'),
      C('SRC_FRUS_1940_I', 'Doc. 410, p. 400', '7 月 22 日議會通過「愛沙尼亞蘇維埃社會主義共和國加入蘇聯」宣言。')], None),
    ('EV_LUX_CDZ', 'political', '1940-07-29', '1940-07-30', '盧森堡改由德國民政長官管轄（OHM 盧森堡止於 1940-07-29）', 'Luxembourg placed under a German Chief of Civil Administration (OHM Luxembourg ends 1940-07-29)', [], None),
    ('EV_CDZ_ANNEX', 'political', '1940-08-02', '1940-08-03', '亞爾薩斯、洛林、盧森堡事實併入德國（OHM 變動日 1940-08-02；無國際承認的法理割讓）', 'De facto annexation of Alsace, Lorraine and Luxembourg (OHM change 1940-08-02; no recognised de jure cession)', [], None),
    ('EV_LT_ADMITTED', 'political', '1940-08-03', '1940-08-04', '蘇聯最高蘇維埃接納立陶宛蘇維埃共和國加入蘇聯', 'USSR Supreme Soviet admits the Lithuanian SSR',
     [C('SRC_FRUS_1940_I', 'Doc. 421, p. 406', '1940-08-04 電報：最高蘇維埃昨日（08-03）通過接納立陶宛加入蘇聯。'),
      C('SRC_FRUS_1940_I', 'Doc. 412, pp. 401–402', '美國 1940-07-23 聲明不承認波羅的海三國被併入（法理爭議）。')], None),
    ('EV_LV_ADMITTED', 'political', '1940-08-05', '1940-08-06', '蘇聯接納拉脫維亞蘇維埃共和國加入蘇聯', 'USSR admits the Latvian SSR',
     [C('SRC_FRUS_1940_I', 'Doc. 425, pp. 409–410', '拉脫維亞外交部照會：自 8 月 5 日起為蘇聯一部分。'),
      C('SRC_FRUS_1940_I', 'Doc. 412, pp. 401–402', '美國不承認聲明（法理爭議）。')], None),
    ('EV_EE_ADMITTED', 'political', '1940-08-06', '1940-08-08', '蘇聯接納愛沙尼亞蘇維埃共和國加入蘇聯', 'USSR admits the Estonian SSR',
     [C('SRC_FRUS_1940_I', 'Doc. 421, p. 406（註腳）', '註腳：依 980 號電報，最高蘇維埃決議接納愛沙尼亞（註腳記為 8 月 7 日，OHM 為 8 月 6 日）。'),
      C('SRC_FRUS_1940_I', 'Doc. 412, pp. 401–402', '美國不承認聲明（法理爭議）。')],
     ('FRUS 註腳記 8 月 7 日、OHM 記 8 月 6 日，故期間取兩天。', 'FRUS footnote says 7 Aug, OHM 6 Aug; the event spans both days.')),
    ('EV_VIENNA2', 'treaty', '1940-08-30', '1940-08-31', '第二次維也納仲裁：北特蘭西瓦尼亞劃歸匈牙利', 'Second Vienna Award: Northern Transylvania to Hungary',
     [C('SRC_FRUS_1940_I', 'Doc. 529, pp. 501–502', '仲裁本文。'), C('SRC_FRUS_1940_I', 'Doc. 530, pp. 502–503', '仲裁後續報告。')], None),
    ('EV_CRAIOVA', 'treaty', '1940-09-07', '1940-09-08', '克拉約瓦條約：羅馬尼亞將南多布羅加割予保加利亞', 'Treaty of Craiova: Romania cedes Southern Dobruja to Bulgaria',
     [C('SRC_FRUS_1940_I', 'Doc. 535, p. 506', '美國駐羅馬尼亞公使 9 月 8 日電報：雙方昨日於克拉約瓦簽約，割讓 Durostor 與 Caliacra 兩省並交換人口。')], None),
]

# 關係 → (起事件, 迄事件)。只在 1938-01-01–1940-12-31 範圍內的變動對應事件；之前就存在的疆界不追溯。
REL_EVENTS = {
    2858751: (None, 'EV_ANSCHLUSS'), 2693085: (None, 'EV_ANSCHLUSS'), 2704712: ('EV_ANSCHLUSS', 'EV_DE_CS_BORDER_1938'),
    2704711: ('EV_DE_CS_BORDER_1938', 'EV_PROTECTORATE'), 2704710: ('EV_PROTECTORATE', 'EV_MEMEL'), 2704709: ('EV_MEMEL', 'EV_DE_EASTERN_DECREE'),
    2704716: ('EV_DE_EASTERN_DECREE', 'EV_EUPEN'), 2704715: ('EV_EUPEN', 'EV_DE_19400601'), 2704714: ('EV_DE_19400601', 'EV_CDZ_ANNEX'),
    2704713: ('EV_CDZ_ANNEX', None),
    2692764: (None, 'EV_MUNICH'), 2747874: ('EV_MUNICH', 'EV_VIENNA1'), 2857482: ('EV_VIENNA1', 'EV_SLOVAK_INDEP'),
    2692769: ('EV_SLOVAK_INDEP', 'EV_HU_SK_1939'), 2692768: ('EV_HU_SK_1939', 'EV_SK_POLISH_AREAS'), 2747847: ('EV_SK_POLISH_AREAS', None),
    2695633: (None, 'EV_VIENNA1'), 2747873: ('EV_VIENNA1', 'EV_CARPATHO'), 2747872: ('EV_CARPATHO', 'EV_HU_SK_1939'),
    2747871: ('EV_HU_SK_1939', 'EV_VIENNA2'), 2747817: ('EV_VIENNA2', None),
    2692205: (None, 'EV_ZAOLZIE'), 2741574: ('EV_ZAOLZIE', 'EV_POLAND_PARTITION'), 2691478: (None, 'EV_DANZIG'),
    2692218: (None, 'EV_MEMEL'), 2855606: ('EV_MEMEL', 'EV_VILNIUS'), 2848250: ('EV_VILNIUS', 'EV_LT_ADMITTED'),
    2694785: ('EV_LT_SSR', 'EV_LT_ADMITTED'), 2704702: (None, 'EV_LV_OCCUPATION'), 2694787: ('EV_LV_SSR', 'EV_LV_ADMITTED'),
    2801387: (None, 'EV_EE_SSR'), 2694790: ('EV_EE_SSR', 'EV_EE_ADMITTED'),
    2851157: (None, 'EV_POLAND_PARTITION'), 2848248: ('EV_POLAND_PARTITION', 'EV_VILNIUS'), 2848241: ('EV_VILNIUS', 'EV_MOSCOW_PEACE'),
    2851878: ('EV_MOSCOW_PEACE', 'EV_BESSARABIA'), 2848258: ('EV_BESSARABIA', 'EV_LT_ADMITTED'), 2848256: ('EV_LT_ADMITTED', 'EV_LV_ADMITTED'),
    2848811: ('EV_LV_ADMITTED', 'EV_EE_ADMITTED'), 2848812: ('EV_EE_ADMITTED', None),
    2959045: (None, 'EV_MOSCOW_PEACE'), 2692833: ('EV_MOSCOW_PEACE', None),
    2693259: (None, 'EV_BESSARABIA'), 2693258: ('EV_BESSARABIA', 'EV_VIENNA2'), 2693257: ('EV_VIENNA2', 'EV_CRAIOVA'), 2693256: ('EV_CRAIOVA', None),
    2848878: (None, 'EV_CRAIOVA'), 2855603: ('EV_CRAIOVA', None),
    2800554: (None, 'EV_ALBANIA'), 2855615: ('EV_ALBANIA', None),
    2851104: (None, 'EV_ARMISTICE_FR_IT'), 2696324: ('EV_ARMISTICE_FR_IT', None),
    2696299: (None, 'EV_ARMISTICE_FR_DE'), 2747868: ('EV_ARMISTICE_FR_DE', None), 2748553: ('EV_BE_MILADMIN', None),
    2800293: (None, 'EV_BE_MILADMIN'), 2748545: (None, 'EV_LUX_CDZ'),
    2860484: (None, 'EV_SPAIN_1939'), 2862761: ('EV_SPAIN_1939', None),
    2801012: (None, 'EV_HATAY'), 2864004: ('EV_HATAY', None),
}

def ohm_date(s):
    """OHM 日期 → YYYY-MM-DD；只有年份時取 1 月 1 日（原字串另存 ohmStartRaw／ohmEndRaw）。"""
    if s is None: return None
    if re.fullmatch(r'\d{4}', s): return f'{s}-01-01'
    if re.fullmatch(r'\d{4}-\d{2}', s): return f'{s}-01'
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', s): return s
    raise ValueError(s)

def pad(s): return s if len(s.split('-')[0]) == 4 else s.zfill(10)

def write(name, obj):
    json.dump(obj, open(os.path.join(OUT, name), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

if os.path.isdir(OUT): shutil.rmtree(OUT)   # 只清本批自己產生的 requests/
os.makedirs(OUT)
for i, (ph, prior, body) in enumerate(SOURCES, 1):
    write(f'01-source-{i:02d}-{ph.lower()}.json', {'_placeholder': ph, '_post': '/api/v1/sources', '_meta': {'priorPlaceholder': prior}, 'body': body})
wd = {}
for rid, r in man.items():
    if rid in REL_REGIME and r.get('wikidata'): wd.setdefault(REL_REGIME[rid], r['wikidata'])
for i, (ph, prior, slug, orig, lang, zh, en) in enumerate(REGIMES, 1):
    body = {'slug': slug, 'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]}
    if not prior and wd.get(ph): body['wikidataQid'] = wd[ph]
    write(f'02-regime-{i:02d}-{slug}.json', {'_placeholder': ph, '_post': '/api/v1/regimes', '_meta': {'priorPlaceholder': prior, 'wikidataFrom': 'OHM 關係 wikidata 標籤' if body.get('wikidataQid') else None}, 'body': body})
for i, (ph, kind, start, end, zh, en, cites, tn) in enumerate(EVENTS, 1):
    body = {'eventKind': kind, 'occurred': {'start': start, 'end': end}, 'datePrecision': 'day', 'summary': {'zh-Hant': zh, 'en': en}, 'citations': cites}
    if tn: body['timeNote'] = {'zh-Hant': tn[0], 'en': tn[1]}
    write(f'03-event-{i:02d}-{ph.lower()}.json', {'_placeholder': ph, '_post': '/api/v1/events',
        '_meta': {'verification': 'verified' if cites else 'pending（待查證）'}, 'body': body})
missing = sorted(set(man) - set(REL_REGIME))
assert not missing, f'未對應政權的關係：{missing}'
recs = sorted(man.values(), key=lambda r: (REL_REGIME[r['ohm_relation_id']], pad(ohm_date(r['start_date']))))
for i, r in enumerate(recs, 1):
    rid = r['ohm_relation_id']
    if rid not in geo_ids: continue
    se, ee = REL_EVENTS.get(rid, (None, None))
    flags = {'memberWayLicense': r['member_way_license'], 'osmDerivedWayCount': r['osm_derived_way_count'],
             'ohmFixme': r['fixme'], 'ohmRelationSource': r['relation_source'], 'ohmAdminLevel': r['admin_level'],
             'ohmChangeset': r['ohm_changeset'], 'ohmTimestamp': r['ohm_timestamp'], 'coastline': '{{SRC_NE_LAND}}',
             'licenseReview': 'osm_derived_ways' if r['osm_derived_way_count'] else None}
    body = {
        'regimeId': '{{%s}}' % REL_REGIME[rid], 'geometry': None,
        'validPeriod': {'start': ohm_date(r['start_date']), 'end': ohm_date(r['end_date'])},
        'layerStatus': 'not_sovereign' if rid in NOT_SOVEREIGN else 'de_jure',
        'geometrySourceId': '{{SRC_OHM}}', 'geometryLocator': f"relation/{rid} v{r['ohm_version']}",
        'geometryLicense': r['geometry_license'], 'attribution': r['attribution'],
        'startEventId': '{{%s}}' % se if se else None, 'endEventId': '{{%s}}' % ee if ee else None,
        'ohmRelationId': rid, 'ohmVersion': r['ohm_version'], 'ohmFetchedAt': r['fetched_at'],
        'ohmStartRaw': r['start_date'], 'ohmEndRaw': r['end_date'], 'provenance': flags,
    }
    if rid in NOT_SOVEREIGN:
        body['note'] = {'zh-Hant': 'OHM 列為國家層級（admin_level=2），實為德國佔領軍政府，非主權；只為避免地圖空白而顯示（待 Tai 決定）。',
                        'en': 'Listed by OHM at admin_level=2 but a German occupation administration, not a sovereign; shown only to avoid a blank map (decision pending).'}
    write(f'04-sovereignty-{i:03d}-r{rid}.json', {'_placeholder': f'SOV_R{rid}', '_post': '/api/v1/sovereignty-records',
        '_geometryFrom': rid, '_meta': {'ohmName': r['name'], 'ohmNameEn': r['name_en']}, 'body': body})
print('requests:', len(os.listdir(OUT)))
