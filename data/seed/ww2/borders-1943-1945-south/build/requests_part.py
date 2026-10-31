# 由 make_requests.py exec：來源、政權、事件、撤回、主權紀錄請求檔
def write(name, ph, post, body, meta=None, geom=None):
    req = {'_placeholder': ph, '_post': post, **({'_geometryFrom': geom} if geom else {}), **({'_meta': meta} if meta else {}), 'body': body}
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')
GPO = 'United States Department of State; United States Government Printing Office, Washington'
SOURCES = [
    ('SRC_OHM_4345S', {'sourceKind': 'dataset',
        'title': 'OpenHistoricalMap — boundary=administrative, admin_level=2／3 關係（南歐、東南歐、法國、比利時、丹麥、芬蘭、捷克斯洛伐克，1941～1945-05）',
        'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
        'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter',
        'publishedText': '新抓的關係 Overpass osm_base 2026-10-31T09:55:15Z；其餘沿用先前批次的固定版本；逐筆見 borders-1943-1945-south/ohm-manifest.json',
        'note': 'OHM 整體以 CC0 1.0 釋出；部分成員線段帶 license=CC BY 4.0 標籤（逐筆在主權紀錄標示）。'}),
    ('SRC_FRUS_1943_II', {'title': 'Foreign Relations of the United States, Diplomatic Papers, 1943, Europe, Volume II', 'url': 'frus1943v02'}),
    ('SRC_FRUS_1944_V', {'title': 'Foreign Relations of the United States, Diplomatic Papers, 1944, The Near East, South Asia, and Africa, The Far East, Volume V', 'url': 'frus1944v05'}),
    ('SRC_FRUS_1945_IV', {'title': 'Foreign Relations of the United States, Diplomatic Papers, 1945, Europe, Volume IV', 'url': 'frus1945v04'}),
]
for i, (ph, b) in enumerate(SOURCES, 1):
    if ph.startswith('SRC_FRUS'):
        b = {'sourceKind': 'official_record', 'title': b['title'], 'publisher': GPO, 'licenseCode': 'us_federal_pd',
             'licenseEvidenceUrl': 'https://www.state.gov/copyright-information', 'url': 'https://history.state.gov/historicaldocuments/' + b['url']}
    write(f'01-source-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sources', b, {'priorPlaceholder': False})

REGIMES = [
    ('REGIME_IT_RSI', 'italian-social-republic', 'Repubblica Sociale Italiana', 'it', '義大利社會共和國（德國扶植）', 'Italian Social Republic (German-sponsored)', 'FRUS 1943 II Doc. 331（the newly established “Republican Fascist” Government）；義文名為通行稱呼'),
    ('REGIME_DE_OCC_IT', 'german-occupation-italy-operational-zones', 'German occupation of Italy', 'en', '德軍直接管轄的義大利地區（作戰區）', 'Italian areas under direct German administration (operational zones)', 'OHM relation/2961564 name；原文名待查證'),
    ('REGIME_AMGOT', 'amgot-italy', 'Allied Military Government of Occupied Territories', 'en', '盟軍佔領區軍政府（義大利）', 'Allied Military Government of Occupied Territories (Italy)', 'OHM relation/2800536 name'),
    ('REGIME_DE_DODECANESE', 'german-occupation-dodecanese', 'German occupation of the Dodecanese', 'en', '德軍佔領的多德卡尼斯群島', 'German-occupied Dodecanese', 'OHM relation/2920370；原文名待查證'),
    ('REGIME_DE_OCC_AL', 'german-occupation-albania', 'German occupation of Albania', 'en', '德軍佔領下的阿爾巴尼亞', 'German-occupied Albania', 'OHM relation/2800553 name'),
    ('REGIME_AL_DG', 'albanian-democratic-government-1944', 'Qeveria Demokratike e Shqipërisë', 'sq', '阿爾巴尼亞民主政府', 'Democratic Government of Albania', 'FRUS 1944 III Doc. 203（“Albanian Democratic Government”）；阿文名為通行稱呼'),
    ('REGIME_DE_OCC_ME', 'german-occupation-montenegro', 'German occupation of Montenegro', 'en', '德軍佔領下的蒙特內哥羅', 'German-occupied Montenegro', 'OHM relation/2855621 name'),
    ('REGIME_DFY', 'democratic-federal-yugoslavia', 'Demokratska Federativna Jugoslavija', 'sh', '南斯拉夫民主聯邦', 'Democratic Federal Yugoslavia', 'OHM relation/2923084 name；塞克文名為通行稱呼'),
    ('REGIME_FR_PROV', 'provisional-government-french-republic', 'Gouvernement provisoire de la République française', 'fr', '法蘭西共和國臨時政府', 'Provisional Government of the French Republic', 'FRUS 1944 III Doc. 692（Provisional Government France）；法文名為通行稱呼'),
    ('REGIME_CFLN', 'french-committee-of-national-liberation', 'Comité français de la Libération nationale', 'fr', '法蘭西民族解放委員會', 'French Committee of National Liberation', 'FRUS 1943 II Doc. 104（French Committee of National Liberation）；法文名為通行稱呼'),
    ('REGIME_RK_BNF', 'reichskommissariat-belgien-nordfrankreich', 'Reichskommissariat Belgien-Nordfrankreich', 'de', '比利時—北法帝國專員公署（德國佔領）', 'Reichskommissariat Belgium–Northern France (German occupation)', 'OHM relation/2748552 name'),
    ('REGIME_HU_PROV', 'hungarian-provisional-national-government', 'Ideiglenes Nemzeti Kormány', 'hu', '匈牙利臨時國民政府', 'Hungarian Provisional National Government', 'FRUS 1944 III Doc. 899（armistice agreement with Hungary）；匈文名為通行稱呼'),
]
for i, (ph, slug, orig, lang, zh, en, src) in enumerate(REGIMES, 1):
    write(f'02-regime-{i:02d}-{slug}.json', ph, '/api/v1/regimes', {'slug': slug, 'names': [
        {'nameKind': 'self', 'originalText': orig, 'originalLang': lang, 'display': {'zh-Hant': zh, 'en': en}, 'isPrimary': True}]},
        {'priorPlaceholder': False, 'nameSource': src})

def ev(i, ph, kind, start, zh, en, parts, cites, tn=None, precision='day'):
    d0 = datetime.date.fromisoformat(start + ('-01' if precision == 'month' else ''))
    if precision == 'month':
        e = (d0.replace(day=28) + datetime.timedelta(days=4)).replace(day=1).isoformat(); start = d0.isoformat()
    else:
        e = (d0 + datetime.timedelta(days=1)).isoformat()
    body = {'eventKind': kind, 'occurred': {'start': start, 'end': e}, 'datePrecision': precision, 'summary': {'zh-Hant': zh, 'en': en},
            'participants': [{'regimeId': '{{%s}}' % r, 'role': role} for r, role in parts],
            'citations': [{'sourceId': '{{%s}}' % s, 'locator': l, 'evidenceNote': n} for s, l, n in cites]}
    if tn: body['timeNote'] = {'zh-Hant': tn[0], 'en': tn[1]}
    write(f'03-event-{i:02d}-{ph.lower()}.json', ph, '/api/v1/events', body, {'verification': 'verified' if cites and not (tn and '待查證' in tn[0]) else 'pending（待查證）'})
P = lambda *rs: [(r, 'belligerent') for r in rs]
NOSRC = lambda rel: ('尚未取得正式出處（待查證）；日期依 OHM ' + rel + '。', 'No formal source yet; date from OHM ' + rel + '.')
USN = ('美國是主要參與方，但政權表尚無美國（下一批補）。', 'The US was a principal party but is not yet in the regime table.')
E = [
 ('EV_IT_ARMISTICE', 'armistice', '1943-09-08', '義大利停戰（9 月 3 日簽字，9 月 8 日公布）；德軍隨即佔領義大利北部、中部', 'Italian armistice (signed 3 Sep, announced 8 Sep 1943)',
  [('REGIME_IT', 'signatory'), ('REGIME_UK', 'signatory')],
  [('SRC_FRUS_1943_II', 'Doc. 639, pp. 711–712', '駐阿爾及爾副領事 1943-09-11 電（編者註）：義大利停戰協定 1943-09-03 簽字，至 9 月 8 日才公布。'),
   ('SRC_FRUS_1943_II', 'Doc. 326, pp. 361–363', '艾森豪 1943-09-08 宣布義大利停戰。')], USN),
 ('EV_RSI', 'political', '1943-09-23', '德國扶植的義大利社會共和國成立', 'German-sponsored Italian Social Republic established', [('REGIME_IT_RSI', 'other'), ('REGIME_DE', 'other')],
  [('SRC_FRUS_1943_II', 'Doc. 331, pp. 367–370', '艾森豪 1943-09-18 電：巴多格里奧政府唯一的競爭者是據稱在北義新成立的「共和法西斯」政府，在德國支持下運作。')],
  ('日期依 OHM relation/2794958 的 start_date；FRUS 1943-09-18 電已提到新成立，正式成立日待查證。', 'Date from OHM; FRUS mentions it on 18 Sep 1943; exact date pending.')),
 ('EV_AMGOT', 'political', '1943-09-17', '盟軍佔領區軍政府（AMGOT）轄區（OHM 版本起始）', 'AMGOT area in Italy (OHM version start)', [('REGIME_AMGOT', 'other'), ('REGIME_IT', 'other')], [],
  ('尚未取得正式出處（待查證）；日期依 OHM relation/2800536。西西里自 1943 年 7 月即由盟軍軍政府管理。', 'No formal source yet; date from OHM. Sicily was under AMG from July 1943.')),
 ('EV_IT_1943_11', 'political', '1943-11-14', '義大利王國政府轄區變動（OHM 版本交替）', 'Change in the area of the Kingdom of Italy (OHM version change)', [('REGIME_IT', 'other')], [], NOSRC('relation/2794960／2956707')),
 ('EV_AMGOT_END', 'political', '1944-03', '盟軍軍政府地區交還義大利王國政府', 'AMGOT areas handed back to the Italian government', [('REGIME_AMGOT', 'other'), ('REGIME_IT', 'other')], [],
  ('尚未取得正式出處（待查證）；OHM relation/2800536 end_date 只標 1944-03，紀錄取 03-01。', 'No formal source; OHM gives only 1944-03.'), 'month'),
 ('EV_IT_1944_08', 'war', '1944-08-25', '盟軍推進，義大利王國政府轄區擴大（OHM 版本交替）', 'Allied advance; Kingdom of Italy area enlarged (OHM version change)', P('REGIME_IT', 'REGIME_DE', 'REGIME_IT_RSI'), [], NOSRC('relation/2794959／2794957')),
 ('EV_CASERTA', 'surrender', '1945-04-29', '卡塞塔投降：義大利境內德軍向盟軍投降（不含伊松佐河以東的威尼斯朱利亞）', 'Surrender at Caserta of German forces in Italy (excluding Venezia Giulia east of the Isonzo)',
  [('REGIME_DE', 'signatory'), ('REGIME_UK', 'signatory')],
  [('SRC_FRUS_1945_III', 'Doc. 558, p. 772', '柯克 1945-04-28 電（編者註）：投降書 4 月 29 日在卡塞塔簽字，範圍含義大利全境，但伊松佐河以東的威尼斯朱利亞除外，另含奧地利西部與中部一部分。')], USN),
 ('EV_AL_DG', 'political', '1944-10-20', '霍查在培拉特宣布成立阿爾巴尼亞民主政府', 'Hoxha proclaims the Albanian Democratic Government at Berat', [('REGIME_AL_DG', 'other')],
  [('SRC_FRUS_1944_III', 'Doc. 203, p. 282', '英國大使館 1944-11-03 備忘錄：霍查 10 月 20 日在培拉特宣布第一個「阿爾巴尼亞民主政府」成立。'),
   ('SRC_FRUS_1944_III', 'Doc. 209, p. 288', '國務院 1944-11-21 致英國大使館：英方不擬承認該政府。')]),
 ('EV_AL_LIB', 'war', '1944-11-29', '德軍撤離，阿爾巴尼亞全境由民族解放軍控制', 'German forces withdraw; Albania under the National Liberation Army', P('REGIME_AL_DG', 'REGIME_DE'), [], NOSRC('relation/2800553／2878108')),
 ('EV_ME_LIB', 'war', '1944-12-15', '德軍撤出蒙特內哥羅', 'German forces leave Montenegro', P('REGIME_DFY', 'REGIME_DE'), [], NOSRC('relation/2855621 end_date')),
 ('EV_BELGRADE', 'war', '1944-10-20', '貝爾格勒解放（德國佔領的塞爾維亞結束）', 'Liberation of Belgrade (end of the German-occupied Serbia administration)', P('REGIME_DFY', 'REGIME_SU', 'REGIME_DE'), [],
  ('尚未取得正式出處（待查證）；通行日期 10-20，OHM relation/2692357 end_date 為 1944-10-22（紀錄依 OHM）。', 'No formal source yet; commonly 20 Oct; OHM gives 22 Oct (records follow OHM).')),
 ('EV_BG_1943', 'political', '1943-07', '保加利亞佔領區範圍調整（OHM 版本交替）', 'Change in the Bulgarian-occupied area (OHM version change)', [('REGIME_BG', 'other'), ('REGIME_GR_OCC', 'other')], [],
  ('尚未取得正式出處（待查證）；OHM relation/2695478 end_date 只標 1943-07，紀錄取 07-01。', 'No formal source; OHM gives only 1943-07.'), 'month'),
 ('EV_BG_NEUTRAL', 'political', '1944-08-26', '保加利亞宣布完全中立，要求德軍撤出', 'Bulgaria declares complete neutrality and asks German troops to leave', [('REGIME_BG', 'other'), ('REGIME_DE', 'other')],
  [('SRC_FRUS_1944_III', 'Doc. 295, p. 372', '駐蘇大使 1944-08-26 電：保加利亞外長告知蘇聯代辦，政府決定採「完全中立」，8 月 25 日要求德國撤軍。'),
   ('SRC_FRUS_1944_III', 'Doc. 300, pp. 376–377', '駐蘇大使 1944-08-28 電：保加利亞政府就完全中立的決定通知蘇方。')]),
 ('EV_GR_LIB', 'war', '1944-10-12', '德軍撤出雅典，希臘政府 10 月 18 日返回', 'German forces leave Athens; Greek Government returns on 18 Oct', P('REGIME_GR', 'REGIME_DE'),
  [('SRC_FRUS_1944_V', 'Doc. 143, pp. 136–137', '駐希臘大使 1944-11-09 電（編者註）：柯克 10 月 13 日自卡塞塔電報「雅典已自由……希臘國旗在衛城飄揚」。'),
   ('SRC_FRUS_1944_V', 'Doc. 228, pp. 222–223', '代理國務卿 1944-10-24 電：希臘政府已於 10 月 18 日返回雅典。')],
  ('日期依 OHM relation/2920399 end_date（10-12）；FRUS 載 10-13 電報雅典已解放。', 'Date from OHM (12 Oct); FRUS has a 13 Oct report that Athens was free.')),
 ('EV_HU_OCC', 'war', '1944-03-19', '德軍佔領匈牙利', 'German occupation of Hungary', [('REGIME_DE', 'belligerent'), ('REGIME_HU', 'other')],
  [('SRC_FRUS_1944_III', 'Doc. 787, p. 852', '國務卿 1944-03-23 電（註）：德軍 3 月 19 日佔領布達佩斯。')]),
 ('EV_HU_ARMISTICE', 'armistice', '1945-01-20', '匈牙利臨時國民政府與盟國在莫斯科簽訂停戰協定', 'Armistice between Hungary (provisional government) and the Allies signed in Moscow',
  [('REGIME_HU_PROV', 'signatory'), ('REGIME_SU', 'signatory'), ('REGIME_UK', 'signatory')],
  [('SRC_FRUS_1944_III', 'Doc. 899, pp. 980–981', '1945-01-20 電：談判結束，1 月 20 日簽訂對匈牙利停戰協定，伏羅希洛夫代表簽字。'),
   ('SRC_FRUS_1945_IV', 'Doc. 761, pp. 800–801', '英國駐蘇代辦 1945-01-20 函：談及對匈牙利停戰協定條款。')],
  ('紀錄的國界變動依 OHM relation/2878067 start_date（1945-02-01）。' + USN[0], 'Border change in the records follows OHM (1 Feb 1945). ' + USN[1])),
 ('EV_RO_TRANSYLVANIA', 'political', '1945-03-09', '北特蘭西瓦尼亞恢復羅馬尼亞管理', 'Romanian administration re-established in northern Transylvania', [('REGIME_RO', 'other'), ('REGIME_SU', 'other')],
  [('SRC_FRUS_1945_V', 'Doc. 370, p. 509', '格羅查 1945-03-10 致羅斯福（註）：格羅查與史達林 3 月 8、9 日互電，蘇方同意在特蘭西瓦尼亞恢復羅馬尼亞管理。')]),
 ('EV_ICELAND', 'political', '1944-06-17', '冰島共和國成立（與丹麥的共主邦聯結束）', 'Republic of Iceland comes into being (union with Denmark ends)', [('REGIME_DK', 'other')],
  [('SRC_FRUS_1944_III', 'Doc. 910, pp. 991–992', '代理國務卿 1944-06-05 通電：冰島共和國將於 1944-06-17 正式成立。')]),
 ('EV_KOSICE', 'political', '1945-04-04', '貝奈斯在科希策任命捷克斯洛伐克新政府', 'Beneš appoints a new Czechoslovak Government at Košice', [('REGIME_CS', 'other')],
  [('SRC_FRUS_1945_IV', 'Doc. 436, pp. 430–433', '駐蘇大使 1945-03-31 電（註）：貝奈斯 4 月 3 日抵科希策，4 月 4 日接受倫敦政府總理辭職，任命費林格為總理組成新政府。')]),
 ('EV_DK_LIB', 'surrender', '1945-05-05', '丹麥境內德軍投降生效，丹麥解放', 'Surrender of German forces in Denmark takes effect; Denmark liberated', P('REGIME_DK', 'REGIME_DE', 'REGIME_UK'), [], NOSRC('relation/2851793（佔領狀態依既有資料）')),
 ('EV_RKBN', 'political', '1944-07-18', '比利時、北法的德國軍事管理改為帝國專員公署', 'German military administration of Belgium and northern France replaced by a Reichskommissariat', [('REGIME_RK_BNF', 'other'), ('REGIME_DE', 'other')], [],
  NOSRC('relation/2748552 start_date')),
 ('EV_BRUSSELS', 'war', '1944-09-03', '盟軍解放布魯塞爾', 'Allied forces liberate Brussels', P('REGIME_BE', 'REGIME_UK', 'REGIME_DE'), [], NOSRC('relation/2748552 end_date')),
 ('EV_FR_0809', 'political', '1944-08-09', '法蘭西共和國臨時政府頒布恢復共和法統的命令（法蘭西國結束）', 'Ordinance restoring republican legality (end of the French State)', [('REGIME_FR_PROV', 'other'), ('REGIME_FR_STATE', 'other')], [],
  NOSRC('relation/2696300 end_date')),
 ('EV_PARIS', 'war', '1944-08-25', '盟軍進入巴黎', 'Allied forces enter Paris', P('REGIME_FR_PROV', 'REGIME_DE'),
  [('SRC_FRUS_1944_III', 'Doc. 673, pp. 730–731', '駐英大使 1944-08-26 電（註）：盟軍 1944-08-25 進入巴黎。')], USN),
 ('EV_GPRF_RECOG', 'political', '1944-10-23', '美、英、蘇、加承認法蘭西共和國臨時政府', 'US, UK, USSR and Canada recognize the Provisional Government of the French Republic',
  [('REGIME_FR_PROV', 'other'), ('REGIME_UK', 'other'), ('REGIME_SU', 'other')],
  [('SRC_FRUS_1944_III', 'Doc. 692, pp. 747–748', '駐法臨時政府代表 1944-10-23 電：與英、蘇、加代表一同面交承認法國臨時政府的信函。'),
   ('SRC_FRUS_1944_III', 'Doc. 688, p. 745', '1944-10 承認法國臨時政府的安排。')], USN),
 ('EV_CORSICA', 'war', '1943-10-04', '科西嘉解放，改由法蘭西民族解放委員會管理', 'Corsica liberated; under the French Committee of National Liberation', P('REGIME_CFLN', 'REGIME_DE'), [],
  ('尚未取得正式出處（待查證）；通行日期 1943-10-04（OHM 沒有科西嘉的分段）。', 'No formal source yet; commonly 4 Oct 1943 (no OHM split for Corsica).')),
 ('EV_CFLN', 'political', '1943-06-03', '法蘭西民族解放委員會在阿爾及爾成立', 'French Committee of National Liberation constituted in Algiers', [('REGIME_CFLN', 'other')],
  [('SRC_FRUS_1943_II', 'Doc. 104, pp. 134–135', '駐阿爾及爾總領事 1943-06-03 電：新成立的法蘭西民族解放委員會派馬西格利正式通知其組成，並附官方公報。')]),
]
for i, e in enumerate(E, 1): ev(i, *e)

RETRACT = [  # (舊 id, 標籤, 原因)
 ('01a19041-0a90-7cff-b566-1a2b7a3dd34b', 'it_1942_07', 'kingdom-of-italy'), ('01a19041-0bce-799b-95d6-50db7d1e4a78', 'al_1942_07', 'albania-under-italy'),
 ('01a19041-0b46-7084-b967-898a34fd81fb', 'bg_1942_07', 'tsardom-of-bulgaria'), ('01a19041-0b6b-70a9-9a80-ce3fcec7ac54', 'gr_1942_07', 'occupied-greece-hellenic-state'),
 ('01a19041-0b89-742d-bfa7-f2c3d5b7bb30', 'hr_1942_07', 'independent-state-of-croatia'), ('01a19041-0ba2-791b-b062-72cd5367eeed', 'rs_1942_07', 'military-commander-serbia'),
 ('01a19041-0bbf-7ff0-a9d2-1b13ee6275c5', 'me_1942_07', 'italian-governorate-montenegro'),
 ('01a19134-d25e-7228-b308-ade10efcb239', 'hu_1941_12', 'kingdom-of-hungary'), ('01a19041-0b00-74c4-a68b-d831695e1524', 'hu_1942_07', 'kingdom-of-hungary'),
 ('01a19134-d23d-725b-9b44-cd7153378230', 'ro_1941_08', 'kingdom-of-romania'), ('01a19041-0b1c-78a3-8164-2af7f61af627', 'ro_1942_07', 'kingdom-of-romania'),
 ('01a19134-d24a-7ba1-b660-ca36d9bfa165', 'tr_1941_08', 'transnistria-governorate'), ('01a19041-0b2e-754a-89b8-8188817c3b4a', 'tr_1942_07', 'transnistria-governorate'),
 ('01a19041-0aae-7707-b117-28a42de2c707', 'itfr_1942_11', 'italian-occupation-zone-france'), ('01a1904a-6c5b-7d24-bdf0-d6f8b70c524b', 'vichy_1942_11', 'french-state-vichy'),
 ('01a19112-06fb-7337-b8a2-d562c539d620', 'fna_1942_11', 'french-north-africa-allied-occupation'),
]
for i, (rid, tag, slug) in enumerate(RETRACT, 1):
    write(f'04-retract-{i:02d}-{tag}.json', f'RETRACTED_{tag.upper()}', f'/api/v1/sovereignty-records/{rid}/retraction',
          {'reason': f'{slug}：原紀錄止於試驗期間邊界（1942-07-01／1943-01-01），造成之後的空白；改以 borders-1943-1945-south 依 OHM 版本起訖重新分段（同一 OHM 版本合併為一筆），撤回後重新新增。'},
          {'fix': True})

def lic(rels):
    rs = [MAN[r] for r in rels]
    attr = sorted({a for r in rs if r['attribution'] for a in r['attribution'].split('; ')})
    return ('cc_by' if any(r['geometry_license'] == 'cc_by' for r in rs) else 'cc0'), ('; '.join(attr) or None)
def rec(i, ph, regime, fix, main, rels, locator, layer, start, end, sev, eev, nzh, nen):
    m = MAN[main]; gl, attr = lic(rels)
    body = {'regimeId': '{{%s}}' % regime, 'geometry': None, 'validPeriod': {'start': start, 'end': end}, 'layerStatus': layer,
            'geometrySourceId': '{{SRC_OHM_4345S}}', 'geometryLocator': locator, 'geometryLicense': gl, 'attribution': attr,
            'startEventId': ('{{%s}}' % sev) if sev else None, 'endEventId': ('{{%s}}' % eev) if eev else None,
            'ohmRelationId': main, 'ohmVersion': m['ohm_version'], 'ohmFetchedAt': m['fetched_at'], 'ohmStartRaw': m['start_date'], 'ohmEndRaw': m['end_date'],
            'provenance': {'memberWayLicense': m['member_way_license'], 'osmDerivedWayCount': sum(MAN[r]['osm_derived_way_count'] for r in rels),
                           'ohmFixme': m['fixme'], 'ohmAdminLevel': m['admin_level'], 'ohmChangeset': m['ohm_changeset'], 'ohmTimestamp': m['ohm_timestamp'],
                           'coastline': '{{SRC_NE_LAND}}', 'derivedFrom': [f'relation/{r} v{MAN[r]["ohm_version"]}' for r in rels], 'derivation': locator,
                           'trialWindow': '1941～1945-05-09（補南歐等空白）'},
            'note': {'zh-Hant': nzh, 'en': nen}}
    write(f'05-sovereignty-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sovereignty-records', body, {'ohmName': m['name']}, geom=fix)
for i, r in enumerate(R, 1): rec(i, *r)
print('ok', len(R), 'records;', len(E), 'events;', len(RETRACT), 'retractions')
