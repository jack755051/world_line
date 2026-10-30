"""產生 requests/*.json（法、英政權與 1940 控制區；DRAFT，待 Tai 檢查，尚未寫入 appdb_ww2）。
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
# FRUS 1940 v. I（Doc. 235）與 FRUS 1942 v. I（Doc. 18）只是候選依據，沒有紀錄引用，不建來源（列在 README）。
src(4, 'SRC_USMA02', {
    'sourceKind': 'atlas_map',
    'title': 'Europe, 1936–1939: German Aggressions, 1936–1939',
    'publisher': 'United States Military Academy, Department of History',
    'publishedText': 'West Point Atlas, World War II European Theater（USMA 網站版）',
    'licenseCode': 'us_federal_pd',
    'licenseEvidenceUrl': 'https://commons.wikimedia.org/wiki/Category:World_War_II_maps_of_the_United_States_Military_Academy',
    'url': 'https://s3.amazonaws.com/usma-media/inline-images/academics/academic_departments/history/WWII%20Europe%20Med/WWIIEurope02.jpg',
    'archiveUrl': 'https://web.archive.org/web/20230921185042/https://www.westpoint.edu/academics/academic-departments/history/digital-history-center/atlases/world-war-two-europe',
    'catalogId': 'USMA WWII Europe/Med, Map 2',
    'localCopyPath': '/workspace/world-line-ww2/trace/WWIIEurope02.jpg',
    'note': '17 U.S.C. §105 公有領域（同 Map 15）。圖上有 GREAT BRITAIN、NORTH IRELAND 與 IRISH FREE STATE 的邊界，不列顛群島不在德國擴張範圍內。5100×3300，2026-10-30 下載。',
})
src(5, 'SRC_NATURAL_EARTH', {
    'sourceKind': 'dataset',
    'title': 'Natural Earth 1:10m Cultural Vectors — Admin 0 – Countries',
    'publisher': 'Natural Earth（North American Cartographic Information Society 支援）',
    'licenseCode': 'public_domain',
    'licenseEvidenceUrl': 'https://www.naturalearthdata.com/about/terms-of-use/',
    'url': 'https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/',
    'localCopyPath': '/workspace/world-line-ww2/trace/ne_10m_admin_0_countries.geojson',
    'note': '公有領域（官網 terms of use）。現代疆界，只當 auxiliary_geometry：英國本土取 ADM0_A3 = GBR，排除 1955 年才併入的 Rockall。',
})

def regime(n, ph, slug, qid, orig, lang, zh, en):
    w(f'02-regime-{n}-{slug}.json', ph, '/api/v1/regimes', {
        'slug': slug, 'wikidataQid': qid,
        'names': [{'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]})
regime(1, 'REGIME_FR3', 'french-third-republic', 'Q70802', 'République française', 'fr', '法蘭西共和國（第三共和）', 'French Republic (Third Republic)')
regime(2, 'REGIME_FR_STATE', 'french-state-vichy', 'Q69808', 'État français', 'fr', '法蘭西國（維琪）', 'French State (Vichy)')
regime(3, 'REGIME_FR_LIBRE', 'free-france', 'Q152582', 'France libre', 'fr', '自由法國', 'Free France')
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

w('05-control-2-uk-home.json', 'CR_UK_HOME', '/api/v1/control-records', {
    'controllerRegimeId': '{{REGIME_UK}}',
    'snapshotId': '{{SNAP_0715}}',
    'controlType': 'direct_rule',
    'validPeriod': {'start': '1939-09-03', 'end': '1945-09-03'},
    'isDisputed': False,
    'geometry': geo['CR_UK_HOME'],
    'citations': [
        {'sourceId': '{{SRC_USMA02}}', 'role': 'primary', 'locator': 'West Point Atlas WWII Europe, Map 2：GREAT BRITAIN、NORTH IRELAND 與 IRISH FREE STATE 邊界',
         'evidenceNote': '1936–39 年的政治邊界；不列顛與北愛爾蘭在德國擴張範圍之外。'},
        {'sourceId': '{{SRC_NATURAL_EARTH}}', 'role': 'auxiliary_geometry', 'locator': 'ne_10m_admin_0_countries，ADM0_A3 = GBR（排除 Rockall）',
         'evidenceNote': '現代英國本土幾何；北愛爾蘭邊界自 1925 年未變，與 Map 2 目視相符。'},
        {'sourceId': '{{SRC_USMA15}}', 'role': 'date_check', 'locator': 'West Point Atlas WWII Europe, Map 15',
         'evidenceNote': '1940-06-13～25：英格蘭南部在德軍推進範圍之外。'},
        {'sourceId': '{{SRC_FRUS_1939_I}}', 'role': 'date_check', 'locator': 'Doc. 419, p. 414',
         'evidenceNote': '英國 1939-09-03 照會：11 時前未獲保證即與德國進入戰爭狀態（起日）。'},
    ]}, meta={'requiresDecision': True, 'reason': '起訖日不是來源明文：起日取英國參戰日 1939-09-03、迄日取第一階段終點 1945-09-03，待 Tai 拍板'})

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

alignment(2, 'AL_UK_ALLIES_1939', 'united-kingdom-allies-1939', 'REGIME_UK', 'allies', '1939-09-03', None, [
    {'sourceId': '{{SRC_FRUS_1939_I}}', 'role': 'primary', 'locator': 'Doc. 419, p. 414（英國 1939-09-03 照會）',
     'evidenceNote': '照會：11 時（英國夏令時間）前未獲德國保證，兩國即自該時起進入戰爭狀態。'},
], {'zh-Hant': '候選 A（參戰日）。憲法 §6 例舉「聯合國家宣言簽署日或參戰日」；英國另有候選 B：1942-01-01 簽署聯合國家宣言（FRUS 1942 v. I, Doc. 18, pp. 25–26；選 B 時再建來源）。待 Tai 拍板，未決前不送。',
    'en': 'Candidate A (date of entry into the war). Candidate B: Declaration by United Nations, 1942-01-01 (FRUS 1942 I, Doc. 18, pp. 25–26). Pending Tai.'},
  meta={'requiresDecision': True, 'reason': '同盟的正式依據有爭議（參戰日 1939-09-03 或聯合國家宣言 1942-01-01），由 Tai 拍板'})

alignment(3, 'AL_FR3_ALLIES_1939', 'french-third-republic-allies-1939', 'REGIME_FR3', 'allies', '1939-09-03', '1940-06-25', [
    {'sourceId': '{{SRC_FRUS_1939_I}}', 'role': 'primary', 'locator': 'Doc. 421, p. 415（法國 1939-09-03 照會）',
     'evidenceNote': '法國照會：德國未答覆 9/1 照會，法國自 9/3 下午 5 時起履行對波蘭的義務。'},
    {'sourceId': '{{SRC_DGFP_D9}}', 'role': 'date_check', 'locator': 'pp. 671–676，德法停戰協定第 I、XXIII 條',
     'evidenceNote': '第 I 條：法國政府下令停止對德作戰；第 XXIII 條：法義停戰後 6 小時停火生效（1940-06-25）。'},
], {'zh-Hant': '候選 A（參戰日至停戰生效）。1940-06-25～07-10 第三共和屬哪一陣營未定（不推定）。憲法定義下 1940 年英法沒有共同簽署「聯合國家宣言」，屬爭議，待 Tai 拍板。',
    'en': 'Candidate A (entry into the war to the armistice). Camp for 1940-06-25 to 07-10 left undetermined. Pending Tai.'},
  meta={'requiresDecision': True, 'reason': '同盟的正式依據有爭議（參戰日或其他文件），由 Tai 拍板'})
print(sorted(os.listdir(OUT)))
