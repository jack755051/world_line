"""產生 requests/*.json（法、英政權、1940 控制區、陣營與補充事件、控制資料缺備註；DRAFT，待 Tai 檢查，尚未寫入 appdb_ww2）。
先跑 make_fruk.py 產生 ../zones-fr-uk-1940.geojson，再跑本檔。
_meta.requiresDecision = true 的請求預設不送（send_seed.py 要加 --include-pending）。
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.dirname(HERE)
OUT = os.path.join(SEED, 'requests')
geo = {f['properties']['id']: f['geometry'] for f in json.load(open(os.path.join(SEED, 'zones-fr-uk-1940.geojson')))['features']}
for f in os.listdir(OUT):
    if f.endswith('.json'): os.remove(os.path.join(OUT, f))

def w(name, placeholder, post, body, meta=None):
    req = {'_placeholder': placeholder, '_post': post}
    if meta: req['_meta'] = meta
    req['body'] = body
    json.dump(req, open(os.path.join(OUT, name), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(os.path.join(OUT, name), 'a').write('\n')

def src(n, ph, body): w(f'01-source-{n}-{ph.lower()}.json', ph, '/api/v1/sources', body)

FRUS_LIC = 'https://www.state.gov/copyright-information'
src(1, 'SRC_JO_19400711', {
    'sourceKind': 'official_record',
    'title': 'Journal officiel de la République française. Lois et décrets, 72e année, n° 167（1940-07-11）',
    'publisher': 'République française（Vichy 印行）',
    'publishedText': '1940-07-11',
    'licenseCode': 'pd_expired',
    'licenseEvidenceUrl': 'https://commons.wikimedia.org/wiki/File:R%C3%A9publique_fran%C3%A7aise_-_Journal_officiel_de_la_R%C3%A9publique_fran%C3%A7aise,_ann%C3%A9e_72,_n%C2%B0_167,_1940-07-11.djvu',
    'url': 'https://fr.wikisource.org/wiki/Loi_constitutionnelle_du_10_juillet_1940',
    'archiveUrl': 'https://gallica.bnf.fr/ark:/12148/bpt6k96279218',
    'catalogId': 'Gallica bpt6k96279218',
    'note': '官方法令公報；Commons 掃描檔標 Public domain（來源 Gallica）。p. 4513：Loi constitutionnelle du 10 juillet 1940（國民議會授權貝當政府以一個或多個法令頒布「法蘭西國」新憲法；Lebrun 以共和國總統身分公布，署 Vichy, 10 juillet 1940）。2026-10-30 在 Wikisource 轉錄頁與本期目錄核對頁碼；Gallica 被 Cloudflare 擋，原掃描未在 Gallica 直接開啟。',
})
src(2, 'SRC_DGFP_D9', {
    'sourceKind': 'official_record',
    'title': 'Documents on German Foreign Policy 1918–1945, Series D (1937–1945), Vol. IX: The War Years, March 18–June 22, 1940',
    'publisher': 'United States Department of State（Publication 6312）; United States Government Printing Office, Washington',
    'publishedText': '1956',
    'licenseCode': 'us_federal_pd',
    'licenseEvidenceUrl': 'https://avalon.law.yale.edu/wwii/frgearm.asp',
    'url': 'https://avalon.law.yale.edu/wwii/frgearm.asp',
    'catalogId': 'DGFP Series D vol. IX, pp. 671–676（Franco-German Armistice）',
    'note': '美國國務院出版（17 U.S.C. §105）。德法停戰協定英譯全文，pp. 671–676；條文以 Yale Avalon Project 轉錄（頁末註明出處為本書美國版 pp. 671–676）核對。archive.org 的英國版是借閱限定、HathiTrust 被 Cloudflare 擋，原書掃描頁未直接核對。',
})
src(3, 'SRC_FRUS_1939_I', {
    'sourceKind': 'official_record',
    'title': 'Foreign Relations of the United States, Diplomatic Papers, 1939, General, Volume I',
    'publisher': 'United States Department of State; United States Government Printing Office, Washington',
    'publishedText': '1956',
    'licenseCode': 'us_federal_pd',
    'licenseEvidenceUrl': FRUS_LIC,
    'url': 'https://history.state.gov/historicaldocuments/frus1939v01',
    'catalogId': 'FRUS 1939 v. I',
    'note': '美國國務院出版（17 U.S.C. §105）。Doc. 419（p. 414）：英國 1939-09-03 照會全文轉述；Doc. 421（p. 415）：法國照會。頁碼以 HistoryAtState TEI 原始檔的 <pb> 核對。',
})
# 2026-10-31 Tai 拍板：同盟以聯合國家宣言為主（FRUS 1942 v. I, Doc. 18），參戰照會只作「補充」；自由法國起日依 FRUS 1940 v. I, Doc. 235。
src(4, 'SRC_FRUS_1942_I', {
    'sourceKind': 'official_record',
    'title': 'Foreign Relations of the United States, Diplomatic Papers, 1942, General; the British Commonwealth; the Far East, Volume I',
    'publisher': 'United States Department of State; United States Government Printing Office, Washington',
    'publishedText': '1960',
    'licenseCode': 'us_federal_pd',
    'licenseEvidenceUrl': FRUS_LIC,
    'url': 'https://history.state.gov/historicaldocuments/frus1942v01/d18',
    'catalogId': 'FRUS 1942 v. I',
    'note': '美國國務院出版（17 U.S.C. §105）。Doc. 18（pp. 25–26）：Declaration by United Nations 全文，文末「Done at Washington January First, 1942」，英國由 Winston S. Churchill 簽署。頁碼以 HistoryAtState TEI 原始檔的 <pb> 核對（2026-10-30）。',
})
src(5, 'SRC_FRUS_1940_I', {
    'sourceKind': 'official_record',
    'title': 'Foreign Relations of the United States, Diplomatic Papers, 1940, General, Volume I',
    'publisher': 'United States Department of State; United States Government Printing Office, Washington',
    'publishedText': '1959',
    'licenseCode': 'us_federal_pd',
    'licenseEvidenceUrl': FRUS_LIC,
    'url': 'https://history.state.gov/historicaldocuments/frus1940v01/d235',
    'catalogId': 'FRUS 1940 v. I',
    'note': "美國國務院出版（17 U.S.C. §105）。Doc. 235（pp. 266–267）：美國駐法國副大使 Biddle 1940-06-24 自 Bordeaux 發出的電報，提到「last night's announcement of recognition of General de Gaulle's National Committee as the only sovereign authority of France」（英國 6/23 晚間的宣布）。頁碼以 HistoryAtState TEI 原始檔的 <pb> 核對（2026-10-30）。",
})
# SRC_USMA02、SRC_NATURAL_EARTH 只供英國本土（CR_UK_HOME）使用；英國本土 2026-10-31「需再聚焦」不寫，兩個來源也先不建（見 README）。

def regime(n, ph, slug, qid, orig, lang, zh, en):
    w(f'02-regime-{n}-{slug}.json', ph, '/api/v1/regimes', {
        'slug': slug, 'wikidataQid': qid,
        'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]})
regime(1, 'REGIME_FR3', 'french-third-republic', 'Q70802', 'République française', 'fr', '法蘭西共和國（第三共和）', 'French Republic (Third Republic)')
regime(2, 'REGIME_FR_STATE', 'french-state-vichy', 'Q69808', 'État français', 'fr', '法蘭西國（維琪）', 'French State (Vichy)')
def regime_named(n, ph, slug, qid, name):
    w(f'02-regime-{n}-{slug}.json', ph, '/api/v1/regimes', {'slug': slug, 'wikidataQid': qid, 'names': [name]})
# 自由法國起日 1940-06-23（Tai 2026-10-31 依建議）：政權狀態切片（regime_status_periods）尚未建置，
# 暫記在自稱名稱的 validPeriod（起日有據、迄日未定），依據見事件 EV_UK_RECOG_FF。
regime_named(3, 'REGIME_FR_LIBRE', 'free-france', 'Q152582', {
    'nameKind': 'self', 'originalText': 'France libre', 'originalLang': 'fr',
    'display': {'zh-Hant': '自由法國', 'en': 'Free France'}, 'isPrimary': True,
    'validPeriod': {'start': '1940-06-23', 'end': None}})
regime(4, 'REGIME_UK', 'united-kingdom', 'Q145', 'United Kingdom of Great Britain and Northern Ireland', 'en', '大不列顛及北愛爾蘭聯合王國', 'United Kingdom')

w('05-control-1-vichy-free-zone.json', 'CR_VICHY_FREE', '/api/v1/control-records', {
    'controllerRegimeId': '{{REGIME_FR_STATE}}',
    'snapshotId': '{{SNAP_0715}}',
    'controlType': 'direct_rule',
    'validPeriod': {'start': '1940-07-15', 'end': '1942-11-11'},
    'startUncertainty': {'start': '1940-07-11', 'end': '1940-07-16'},
    'isDisputed': False,
    'geometry': geo['CR_VICHY_FREE'],
    'citations': [
        {'sourceId': '{{SRC_LECONTE}}', 'role': 'primary', 'locator': 'Leconte 單張圖正面，館藏號 2015.3.1.230：分界線（線以南、以東為非佔領區）',
         'evidenceNote': '圖上印出的分界線；描線與 CR_MAIN 共用同一條線（27 個控制點配準，RMSE ≈ 2.4 km），兩區只共用邊界。'},
        {'sourceId': '{{SRC_AIN}}', 'role': 'auxiliary_geometry', 'locator': 'data.gouv.fr「Ligne de démarcation」layer 5（LineString）',
         'evidenceNote': '分界線座標（兩端延長 0.05° 後切割），與 CR_MAIN 相同。'},
        {'sourceId': '{{SRC_TRF}}', 'role': 'auxiliary_geometry', 'locator': 'DEPARTEMENTS_1940（doi:10.7910/DVN/ULQYM5）',
         'evidenceNote': '外框（含 Corse）；扣除 Basses-Alpes、Hautes-Alpes、Alpes-Maritimes、Savoie、Haute-Savoie 五省——義大利佔領區沒有合格來源，這五省留「控制資料缺」（R9），不把義大利佔領的市鎮標成維琪。'},
        {'sourceId': '{{SRC_DGFP_D9}}', 'role': 'date_check', 'locator': 'pp. 671–676，德法停戰協定第 II、III 條與附錄',
         'evidenceNote': '第 II 條：線以北、以西由德軍佔領；第 III 條：法國政府可在非佔領區設政府所在地並管理非佔領區；附錄描述分界線走向（Geneva–Dôle–Paray-le-Monial–Bourges–Tours 以東–Mont-de-Marsan–Orthez）。'},
        {'sourceId': '{{SRC_JO_19400711}}', 'role': 'date_check', 'locator': 'p. 4513，Loi constitutionnelle du 10 juillet 1940',
         'evidenceNote': '國民議會授權貝當政府頒布「法蘭西國」新憲法；控制方自此為法蘭西國，起日不確定區間由 1940-07-11 起。'},
        {'sourceId': '{{SRC_USMA15}}', 'role': 'date_check', 'locator': 'West Point Atlas WWII Europe, Map 15',
         'evidenceNote': '6/25 德軍最遠推進線越過後來的分界線，7 月中才退回（同 CR_MAIN 的起日與不確定區間）。'},
    ]})

# 英國本土控制紀錄（CR_UK_HOME）：Tai 2026-10-31「需再聚焦」，不寫；選項見 README。幾何仍保留在 zones-fr-uk-1940.geojson 備查。

def alignment(n, ph, slug, regime_ph, camp, start, end, citations, note, meta=None):
    w(f'06-alignment-{n}-{slug}.json', ph, '/api/v1/regimes/{{%s}}/alignments' % regime_ph,
      {'camp': camp, 'validPeriod': {'start': start, 'end': end}, 'citations': citations, 'note': note}, meta)

alignment(1, 'AL_FR_STATE_COBEL', 'french-state-co-belligerent', 'REGIME_FR_STATE', 'co_belligerent', '1940-07-11', None, [
    {'sourceId': '{{SRC_DGFP_D9}}', 'role': 'primary', 'locator': 'pp. 671–676，德法停戰協定第 III、X 條',
     'evidenceNote': '第 III 條：法國政府以一切手段支持德國佔領權的施行，佔領區官員須遵從德軍規定並「以正確方式合作」；第 X 條：禁止任何法國部隊或公民對德作戰。協定由法國政府簽署（1940-06-22），法蘭西國承接施行。'},
    {'sourceId': '{{SRC_JO_19400711}}', 'role': 'date_check', 'locator': 'p. 4513，Loi constitutionnelle du 10 juillet 1940',
     'evidenceNote': '授權頒布「法蘭西國」憲法；起日取法蘭西國成立（1940-07-11，Acte constitutionnel n° 1）。'},
], {'zh-Hant': '憲法 §6「陣營」明列維琪法國屬共同交戰／合作；Tai 2026-10-30 指示依停戰協定等正式文件。起日 1940-07-11 是法蘭西國成立日（Acte constitutionnel n° 1 原文未核對，只核對到 7-10 授權法）。迄日未定。候選替代起日：1940-10-24 Montoire 會談。',
    'en': 'Constitution §6 names Vichy France as co-belligerent/collaborator; basis: the Franco-German armistice. Start 1940-07-11 = founding of the French State (Constitutional Act No. 1 not checked against the original; the 10 July enabling law is). End undetermined. Alternative start: Montoire, 1940-10-24.'})

alignment(2, 'AL_UK_ALLIES_1942', 'united-kingdom-allies-1942', 'REGIME_UK', 'allies', '1942-01-01', None, [
    {'sourceId': '{{SRC_FRUS_1942_I}}', 'role': 'primary', 'locator': 'Doc. 18, pp. 25–26（Declaration by United Nations）',
     'evidenceNote': '聯合國家宣言全文，文末「Done at Washington January First, 1942」，英國由 Churchill 簽署；簽署國承諾以全部資源對三國同盟條約成員作戰、不單獨媾和。'},
], {'zh-Hant': 'Tai 2026-10-31 拍板：陣營只依有紀錄且最嚴謹的正式文件（聯合國家宣言）判定；1939-09-03 對德宣戰只作「補充」（事件 EV_UK_DECL_1939），不構成陣營切片。1942-01-01 以前英國陣營不建（前端顯示「陣營未建置」＋補充）。迄日未定。',
    'en': 'Decided by Tai 2026-10-31: camp follows the most rigorous formal document (Declaration by United Nations); the 1939-09-03 declaration of war is a supplement only (event EV_UK_DECL_1939). No camp before 1942-01-01. End undetermined.'})

# 第三共和：沒有簽署聯合國家宣言（1942 年已不存在），依原則 1 不建陣營切片；1939-09-03 照會只作補充（EV_FR3_DECL_1939）。
# 自由法國：未簽署聯合國家宣言，FRUS 中未找到正式加入文件，不建陣營切片；補充為英國承認（EV_UK_RECOG_FF）。

def event(n, ph, slug, kind, start, end, summary, participants, citations, time_note=None):
    body = {'eventKind': kind, 'occurred': {'start': start, 'end': end}, 'datePrecision': 'day',
            'summary': summary, 'participants': participants, 'citations': citations}
    if time_note: body['timeNote'] = time_note
    w(f'07-event-{n}-{slug}.json', ph, '/api/v1/events', body)

event(1, 'EV_UK_DECL_1939', 'uk-declares-war-on-germany', 'war', '1939-09-03', '1939-09-04',
      {'zh-Hant': '英國對德國進入戰爭狀態（陣營補充）', 'en': 'United Kingdom at war with Germany (camp supplement)'},
      [{'regimeId': '{{REGIME_UK}}', 'role': 'belligerent'}, {'regimeId': '{{REGIME_DE}}', 'role': 'belligerent'}],
      [{'sourceId': '{{SRC_FRUS_1939_I}}', 'locator': 'Doc. 419, p. 414（英國 1939-09-03 照會）',
        'evidenceNote': '照會：11 時（英國夏令時間）前未獲德國保證，兩國即自該時起進入戰爭狀態。'}],
      {'zh-Hant': '倫敦時間 11 時', 'en': '11 a.m. British Summer Time'})
event(2, 'EV_FR3_DECL_1939', 'france-at-war-with-germany', 'war', '1939-09-03', '1939-09-04',
      {'zh-Hant': '法國對德國進入戰爭狀態（陣營補充）', 'en': 'France at war with Germany (camp supplement)'},
      [{'regimeId': '{{REGIME_FR3}}', 'role': 'belligerent'}, {'regimeId': '{{REGIME_DE}}', 'role': 'belligerent'}],
      [{'sourceId': '{{SRC_FRUS_1939_I}}', 'locator': 'Doc. 421, p. 415（法國 1939-09-03 照會）',
        'evidenceNote': '法國照會：德國未答覆 9/1 照會，法國自 9/3 下午 5 時起履行對波蘭的義務。'}],
      {'zh-Hant': '巴黎時間 17 時', 'en': '5 p.m. Paris time'})
event(3, 'EV_UK_RECOG_FF', 'uk-recognizes-french-national-committee', 'political', '1940-06-23', '1940-06-24',
      {'zh-Hant': '英國宣布承認戴高樂的法國國家委員會（自由法國起點；陣營補充）', 'en': "UK announces recognition of General de Gaulle's French National Committee (start of Free France; camp supplement)"},
      [{'regimeId': '{{REGIME_UK}}', 'role': 'other'}, {'regimeId': '{{REGIME_FR_LIBRE}}', 'role': 'other'}],
      [{'sourceId': '{{SRC_FRUS_1940_I}}', 'locator': 'Doc. 235, pp. 266–267（美國駐法副大使 Biddle 1940-06-24 電報，Bordeaux）',
        'evidenceNote': "電報提到「last night's announcement of recognition of General de Gaulle's National Committee as the only sovereign authority of France」，即英國 6/23 晚間的宣布。"}])

# R9：義大利佔領的阿爾卑斯五省沒有合格來源 → 涵蓋備註（控制資料缺），前端以點狀樣式呈現（Tai 2026-10-31）。
w('08-coverage-1-alpine.json', 'GAP_ALPINE', '/api/v1/control-coverage-notes', {
    'theaterId': '{{THEATER_WE}}',
    'geometry': geo['GAP_ALPINE'],
    'validPeriod': {'start': '1940-07-15', 'end': '1942-11-11'},
    'reason': 'no_qualified_source',
    'note': {'zh-Hant': '義大利佔領區（1940-06-24 法義停戰後）沒有合格來源：Basses-Alpes、Hautes-Alpes、Alpes-Maritimes、Savoie、Haute-Savoie 五省（TRF-GIS 1940 省界）不畫，不標成維琪或義大利。',
             'en': 'Italian occupation zone: no qualified source. The five Alpine départements (TRF-GIS 1940 boundaries) are left as a data gap, not assigned to Vichy or Italy.'},
    'researchRef': 'data/seed/ww2/fr-uk-1940/README.md；build/make_fruk.py（ALPINE）',
})
print(sorted(os.listdir(OUT)))
