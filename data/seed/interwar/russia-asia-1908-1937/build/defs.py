"""俄國／亞洲 1908～1937 批次的來源、引用、政權、事件與新紀錄定義（build_ru.py 與 make_requests.py 共用）。"""
# ---------- 既有 id ----------
RG = {'russian-empire': '01a192dc-651a-7664-8858-ac617593d466', 'russian-provisional-government-1917': '01a19333-4dcf-7960-b9fc-6fa3354432ed',
      'russian-sfsr-1917': '01a19333-9b70-701d-a1e4-464af7aff56c', 'soviet-union': '01a18e71-cc2e-7f80-8d62-81879da43d7b',
      'empire-of-japan': '01a191c9-07d8-7a6d-969f-c702cc8df64c', 'republic-of-china-nationalist': '01a191c9-07f8-76a7-8497-ce49a6de97fa',
      'manchukuo': '01a191c9-07ff-7fd1-a279-449ef9d2591e', 'mongolian-peoples-republic': '01a191c9-0807-7ca7-9bc7-9bb8a9bb463b',
      'tuvan-peoples-republic': '01a191c9-0812-7009-82e5-decbbc0048dd', 'tibet-ganden-phodrang': '01a191c9-0819-7449-83e0-5f2b98bc43da',
      'imperial-state-of-iran': '01a1940e-f421-728e-9dfd-d8584ed22d48', 'kingdom-of-afghanistan': '01a1948c-dbbd-744f-8b2d-54f3e5ed0364'}
EV_DELIM, EV_SOVJP, EV_VERSAILLES = '01a193e1-5b4e-7911-8fc4-2a5440e13b20', '01a193e1-b30c-72c3-ba49-0df085d71e1f', '01a193a2-c078-7a9d-97e9-7608221cf3db'
EV_USSR = '01a193a2-c1eb-714c-83d8-20344b76c44a'
SRC_FRUS1910, SRC_FRUS1922V2, SRC_NE = '01a192dc-4b51-7b9d-9c36-c0412308202b', '01a193a2-bdcf-7d2d-8b4d-9b0aa9de440a', '01a18e71-c977-7a2c-afe3-cb56ea3ec9fa'
RU_SLUGS = ('russian-empire', 'russian-provisional-government-1917', 'russian-sfsr-1917', 'soviet-union')
IR_SLUGS = ('imperial-state-of-iran', 'soviet-occupied-iran-1941', 'british-occupied-iran-1941')

# ---------- 來源（正式出處）----------
SOURCES = [
 ('SRC_OHM_RUASIA', {'sourceKind': 'dataset', 'title': 'OpenHistoricalMap — boundary=administrative 關係（俄國 1908～1925 補完整、亞洲鄰國與分離政權 1908～1937、伊朗東部）',
   'publisher': 'OpenHistoricalMap contributors', 'licenseCode': 'cc0', 'licenseEvidenceUrl': 'https://www.openhistoricalmap.org/copyright',
   'url': 'https://overpass-api.openhistoricalmap.org/api/interpreter', 'publishedText': None,
   'note': 'OHM 整體以 CC0 1.0 釋出；本批關係的成員線段授權逐筆記在紀錄 provenance。'}),
 ('SRC_SBORNIK1952', {'sourceKind': 'treaty', 'title': 'Сборник договоров России с другими государствами, 1856–1917（俄國與他國條約彙編 1856～1917）',
   'publisher': 'Государственное издательство политической литературы（莫斯科）', 'authors': 'И. В. Козьменко 編；Е. А. Адамов 主編',
   'publishedText': '1952 年出版；線上全文逐篇標示原書頁碼（istmat.org「Исторические материалы」）', 'url': 'https://www.istmat.org/node/27109', 'licenseCode': 'pd_expired',
   'note': '授權依據：所引條約條文均於 1917 年以前公布（著作權已過期；且依俄羅斯民法典第 1259 條第 6 款，官方文件不受著作權保護）；本彙編 1952 年的編注部分不引用，只引用條文與頁碼。各篇頁碼取自 istmat.org 各篇「Источник」欄。'}),
 ('SRC_EICHELMANN1887', {'sourceKind': 'treaty', 'title': 'Хрестоматия русского международного права, ч. I（俄國國際法讀本，第一部）',
   'publisher': 'Киев（基輔）', 'authors': 'О. О. Эйхельман', 'publishedText': '1887 年出版', 'licenseCode': 'pd_expired',
   'url': 'http://ricolor.org/journal/34/istoria/3/',
   'note': '收錄 1881-12-09/21 俄波《裏海以東劃界專約》（阿哈爾—呼羅珊專約）全文；頁碼 383–386 轉引自 О. А. Гоков〈Русско-иранское разграничение 1881–1886 гг.〉（Россия в красках, 2013, № 34），原書未直接核對（待查證）。'}),
 ('SRC_SYEZDY3', {'sourceKind': 'official_record', 'title': 'Съезды Советов в документах. 1917–1936, т. III（蘇維埃代表大會文件集，第三卷）',
   'publisher': 'Москва（莫斯科）', 'publishedText': '1960 年出版；俄羅斯歷史學會電子歷史文件庫（ЭБИД）書目著錄',
   'url': 'https://docs.historyrussia.org/nodes/342350', 'licenseCode': 'pd_expired', 'note': '《蘇聯成立條約》（1922-12-30）pp. 18–22；書目資料取自 ЭБИД。授權依據：條約條文 1923 年以前已公布（著作權已過期；官方文件依俄羅斯民法典第 1259 條第 6 款亦不受著作權保護），只引用條文。'}),
 ('SRC_SZSSSR1924', {'sourceKind': 'official_record', 'title': 'Собрание законов и распоряжений Рабоче-Крестьянского Правительства СССР, 1924, № 19（蘇聯法令彙編 1924 年第 19 號）',
   'publisher': 'Управление делами СНК СССР（莫斯科）', 'publishedText': '1924 年；條文見俄羅斯歷史學會電子歷史文件庫（ЭБИД）',
   'url': 'https://docs.historyrussia.org/ru/nodes/521301', 'licenseCode': 'pd_expired', 'note': '蘇聯中央執行委員會 1924-10-27 決議〈關於中亞各蘇維埃共和國劃界及烏茲別克、土庫曼蘇維埃社會主義共和國加入蘇聯〉，ст. 187。授權依據：1924 年公布的官方法令（著作權已過期；官方文件依俄羅斯民法典第 1259 條第 6 款亦不受著作權保護）。'}),
]
def cite(src, loc, ev): return {'sourceId': '{{%s}}' % src if src.startswith('SRC_') else src, 'locator': loc, 'evidenceNote': ev}
BASIS = {
 'peking1860': cite('SRC_SBORNIK1952', '№ 12，pp. 74–84（1860-11-02/14 北京續增條約，第 1～3 條）', '俄中東段邊界：黑龍江、烏蘇里江、興凱湖至圖們江；西段劃界原則。'),
 'ili1881': cite('SRC_SBORNIK1952', '№ 29，pp. 211–221（1881-02-12/24 聖彼得堡條約〔伊犁條約〕）', '伊犁地區歸還中國、俄中西段邊界調整。'),
 'akhal1881': cite('SRC_EICHELMANN1887', 'ч. I, с. 383–386（1881-12-09/21 裏海以東劃界專約；頁碼待查證）', '俄國與波斯在裏海以東（阿特列克河至捷詹）的邊界。'),
 'afg1885': cite('SRC_SBORNIK1952', '№ 37，pp. 264–266（1885-08-29/09-10 俄英阿富汗劃界協定）', '俄屬中亞與阿富汗西北段邊界。'),
 'pamir1895': cite('SRC_SBORNIK1952', '№ 41，pp. 284–286（1895-02-27/03-11 俄英帕米爾勢力範圍劃分協定）', '帕米爾地區俄、阿邊界（噴赤河），瓦罕走廊。'),
 'khiva1873': cite('SRC_SBORNIK1952', '№ 19，pp. 129–134（1873-08-12/24 俄國與希瓦汗國條約）', '希瓦汗受俄國保護；阿姆河右岸歸俄國（第 1～3 條）。'),
 'bukhara1873': cite('SRC_SBORNIK1952', '№ 20，pp. 135–139（1873-09-28/10-10 俄國與布哈拉沙爾條約）', '布哈拉與俄國邊界維持不變、受俄國保護；阿姆河右岸原希瓦土地部分歸布哈拉（第 1～2 條）。1868 年俄布和約全文未找到正式出處（待查證）。'),
 'mongolia1912': cite('SRC_SBORNIK1952', '№ 66，pp. 410–420（1912-10-21/11-03 俄蒙協定；1913-10-23/11-05 中俄聲明）', '外蒙古自治、中國軍政人員撤離；1913 年中俄聲明：外蒙古在中國宗主權下自治。'),
 'ussr1922': cite('SRC_SYEZDY3', 'pp. 18–22（1922-12-30 蘇聯成立條約）', '俄羅斯、烏克蘭、白俄羅斯、外高加索四共和國組成蘇聯。'),
 'delim1924': cite('SRC_SZSSSR1924', 'ст. 187（1924-10-27 中央執行委員會決議）', '中亞民族劃界：撤銷布哈拉、花剌子模人民蘇維埃共和國，成立烏茲別克、土庫曼蘇維埃社會主義共和國。'),
 'korea1910': cite(SRC_FRUS1910, 'Doc. 705, pp. 681–682', '1910-08-22 日韓合併條約全文；日本政府聲明：條約自 1910-08-29 公布日起生效。'),
 'fer1922': cite(SRC_FRUS1922V2, 'Doc. 764、765（861.01/517、861.01/520）', '1922-11-14 遠東共和國政府交出權力、國民議會決議併入蘇俄；全俄中央執行委員會宣布遠東共和國為蘇俄不可分割的一部分。'),
}
# ---------- 新政權 ----------
REGIMES = [
 ('REGIME_QING', 'qing-dynasty', '大清', 'zh', '大清（清朝）', 'Qing Empire'),
 ('REGIME_ROC_BY', 'republic-of-china-beiyang', '中華民國', 'zh', '中華民國（北京政府）', 'Republic of China (Beiyang Government)'),
 ('REGIME_MN_BOGD', 'bogd-khanate-of-mongolia', 'Богд хаант Монгол Улс', 'mn', '博克多汗國（外蒙古）', 'Bogd Khanate of Mongolia'),
 ('REGIME_FER', 'far-eastern-republic', 'Дальневосточная Республика', 'ru', '遠東共和國', 'Far Eastern Republic'),
 ('REGIME_BUKH', 'emirate-of-bukhara', 'امارت بخارا', 'fa', '布哈拉酋長國（俄國保護國）', 'Emirate of Bukhara (Russian protectorate)'),
 ('REGIME_BPSR', 'bukharan-peoples-soviet-republic', 'Бухарская Народная Советская Республика', 'ru', '布哈拉人民蘇維埃共和國', "Bukharan People's Soviet Republic"),
 ('REGIME_KHIVA', 'khanate-of-khiva', 'Xiva xonligi', 'uz', '希瓦汗國（俄國保護國）', 'Khanate of Khiva (Russian protectorate)'),
 ('REGIME_KHPSR', 'khorezm-peoples-soviet-republic', 'Хорезмская Народная Советская Республика', 'ru', '花剌子模人民蘇維埃共和國', "Khorezm People's Soviet Republic"),
 ('REGIME_KOREA', 'korean-empire', '대한제국', 'ko', '大韓帝國（日本保護國）', 'Korean Empire (Japanese protectorate)'),
 ('REGIME_PERSIA', 'sublime-state-of-persia', 'دولت علیّه ایران', 'fa', '波斯', 'Persia (Sublime State of Persia)'),
 ('REGIME_AFG_EM', 'emirate-of-afghanistan', 'امارت افغانستان', 'fa', '阿富汗酋長國', 'Emirate of Afghanistan'),
 ('REGIME_JP_NSAKH', 'japanese-occupied-northern-sakhalin', '北樺太（保障占領）', 'ja', '日本佔領下的北庫頁島', 'Japanese-occupied northern Sakhalin'),
]
for ph, slug, *_ in REGIMES: RG[slug] = '{{%s}}' % ph
# ---------- 新事件 ----------
B, S, O = 'belligerent', 'signatory', 'other'
EVENTS = [
 # ph, date, kind, zh, en, participants[(slug, role)], citations, timeNote(zh,en) or None, verified
 ('EV_KR_ANNEX', '1910-08-29', 'treaty', '日韓合併條約生效，大韓帝國併入日本', 'Japan–Korea Annexation Treaty takes effect; Korea annexed by Japan',
  [('empire-of-japan', S), ('korean-empire', S)], [BASIS['korea1910']], ('8-22 簽字，8-29 公布生效（依日本政府聲明）。OHM 換版日為 8-27，本表依生效日。', 'Signed 22 Aug, effective on promulgation 29 Aug (OHM uses 27 Aug).'), True),
 ('EV_MN_AUTON', '1911-12-01', 'political', '外蒙古宣布脫離清朝自治（博克多汗國）', 'Outer Mongolia breaks away from the Qing (Bogd Khanate)',
  [('bogd-khanate-of-mongolia', O), ('qing-dynasty', O)], [BASIS['mongolia1912']], ('日期依 OHM 換版日（待查證）；1912 年俄蒙協定序文記中國軍政人員已撤離、哲布尊丹巴呼圖克圖被推為君主，可證自治事實，但未載日期。', 'Date per OHM (pending verification); the 1912 Russo-Mongolian agreement attests the fact but not the date.'), False),
 ('EV_ROC', '1912-01-01', 'political', '中華民國臨時政府在南京成立（清帝 1912-02-12 退位）', 'Provisional Government of the Republic of China established in Nanjing',
  [('republic-of-china-beiyang', O), ('qing-dynasty', O)], [], ('未找到正式出處（待查證）。日期依 OHM 換版日；清帝退位（1912-02-12）未分段。', 'No formal source located (pending); date per OHM.'), False),
 ('EV_KHIVA_END', '1920-02-02', 'political', '希瓦汗退位，花剌子模人民蘇維埃共和國取代希瓦汗國', 'Khan of Khiva abdicates; Khorezm People\'s Soviet Republic replaces the khanate',
  [('khanate-of-khiva', O), ('khorezm-peoples-soviet-republic', O)], [], ('未找到正式出處（待查證）。日期依 OHM；共和國 1920-04-26 正式宣布（未分）。', 'No formal source located (pending); date per OHM.'), False),
 ('EV_FER', '1920-04-06', 'political', '遠東共和國在上烏金斯克宣布成立', 'Far Eastern Republic proclaimed at Verkhneudinsk',
  [('far-eastern-republic', O), ('russian-sfsr-1917', O)], [], ('未找到正式出處（待查證）。日期依 OHM。', 'No formal source located (pending); date per OHM.'), False),
 ('EV_JP_NSAKH', '1920-01-01', 'campaign', '日軍佔領北庫頁島（至 1925 年）', 'Japanese occupation of northern Sakhalin (until 1925)',
  [('empire-of-japan', O), ('japanese-occupied-northern-sakhalin', O)], [], ('未找到正式出處（待查證）。日期依 OHM 換版日（只記年份）；日軍實際在 1920 年尼港事件後佔領，確切日期待查證；1925-05 撤出。', 'No formal source located (pending); OHM gives only the year 1920.'), False),
 ('EV_BUKH_END', '1920-09-02', 'campaign', '紅軍攻佔布哈拉，埃米爾出走，布哈拉人民蘇維埃共和國取代酋長國', 'Red Army takes Bukhara; the emir flees and the Bukharan People\'s Soviet Republic replaces the emirate',
  [('russian-sfsr-1917', B), ('emirate-of-bukhara', B), ('bukharan-peoples-soviet-republic', O)], [], ('未找到正式出處（待查證）。日期依 OHM；共和國 1920-10-08 正式宣布（未分）。', 'No formal source located (pending); date per OHM.'), False),
 ('EV_TUVA', '1921-08-14', 'political', '唐努烏梁海（圖瓦人民共和國）宣布成立', "Tuvan People's Republic proclaimed",
  [('tuvan-peoples-republic', O)], [], ('未找到正式出處（待查證）。日期依 OHM。', 'No formal source located (pending); date per OHM.'), False),
 ('EV_FER_END', '1922-11-15', 'political', '遠東共和國併入俄羅斯蘇維埃聯邦社會主義共和國', 'Far Eastern Republic merged into the RSFSR',
  [('far-eastern-republic', O), ('russian-sfsr-1917', O)], [BASIS['fer1922']], ('11-14 遠東共和國國民議會決議併入；11-15 全俄中央執行委員會宣布併入（依 FRUS 電報）。', 'Assembly voted on 14 Nov; Moscow declared incorporation (per FRUS telegrams).'), True),
 ('EV_MPR', '1924-11-26', 'political', '蒙古人民共和國宣布成立（第一部憲法）', "Mongolian People's Republic proclaimed (first constitution)",
  [('mongolian-peoples-republic', O)], [], ('未找到正式出處（待查證）。日期依 OHM。', 'No formal source located (pending); date per OHM.'), False),
 ('EV_AFG_KINGDOM', '1926-06-09', 'political', '阿曼諾拉汗改稱國王，阿富汗酋長國改為王國', 'Amanullah Khan takes the title of king; Afghanistan becomes a kingdom',
  [('emirate-of-afghanistan', O), ('kingdom-of-afghanistan', O)], [], ('未找到正式出處（待查證）。日期依 OHM。', 'No formal source located (pending); date per OHM.'), False),
 ('EV_BEIYANG_END', '1928-06-08', 'campaign', '國民革命軍進入北京，北京政府結束（北伐）', 'National Revolutionary Army enters Beijing; end of the Beiyang government',
  [('republic-of-china-nationalist', B), ('republic-of-china-beiyang', B)], [], ('未找到正式出處（待查證）。東北易幟（1928-12-29）未分段。', 'No formal source located (pending).'), False),
 ('EV_MANCHUKUO', '1932-03-01', 'political', '日本扶植的滿洲國宣布成立', 'Japanese-sponsored Manchukuo proclaimed',
  [('manchukuo', O), ('empire-of-japan', O), ('republic-of-china-nationalist', O)], [], ('未找到正式出處（待查證）。OHM 只記 1932 年；熱河 1933 年才被佔（未分段，OHM 幾何已含熱河）。', 'No formal source located (pending); Jehol (1933) not split.'), False),
 ('EV_IRAN_NAME', '1935-03-21', 'political', '波斯政府要求各國改稱「伊朗」', 'Persia asks foreign governments to call the country Iran',
  [('sublime-state-of-persia', O), ('imperial-state-of-iran', O)], [], ('未找到正式出處（待查證）。OHM 換版日只記 1935 年。', 'No formal source located (pending); OHM gives only the year 1935.'), False),
]
EVD = {e[0]: e for e in EVENTS}
def E(x): return None if x is None else ('{{%s}}' % x if x.startswith('EV_') else x)

# ---------- 新紀錄（亞洲 1908～1937、北庫頁島佔領）----------
# prio 1：分離／保護國／佔領（高於俄國）；3：大鄰國（低於俄國）
NEW = [
 # key, slug, lo, hi, rid, layer, prio, start_ev, end_ev, basis keys, note_zh, note_en
 ('JP_NSAKH', 'japanese-occupied-northern-sakhalin', '1920-01-01', '1925-01-20', 'NSAKH', 'not_sovereign', 0.5, 'EV_JP_NSAKH', EV_SOVJP, [], '日本佔領北庫頁島（北緯 50 度以北），非主權。幾何＝OHM 日本 2851273 與 2889779 之差。起日依 OHM（待查證）；1925-01-20 蘇日基本條約約定撤軍（實際 1925-05 撤出，未分）。', 'Japanese occupation of northern Sakhalin; not sovereign.'),
 ('BUKH', 'emirate-of-bukhara', '1908-10-05', '1920-09-02', 2961275, 'not_sovereign', 1, None, 'EV_BUKH_END', ['bukhara1873', 'afg1885', 'pamir1895'], '1873 年起為俄國保護國（非主權）；1917 年後實際獨立（未分）。1908-10-05 為本批起點。', 'Russian protectorate from 1873 (not sovereign).'),
 ('BPSR', 'bukharan-peoples-soviet-republic', '1920-09-02', '1924-10-27', 2851359, 'de_jure', 1, 'EV_BUKH_END', EV_DELIM, ['delim1924', 'afg1885', 'pamir1895'], '1924-10-27 中亞民族劃界後撤銷，土地分入烏茲別克、土庫曼蘇維埃社會主義共和國（蘇聯）。', 'Abolished in the 1924 national delimitation.'),
 ('KHIVA', 'khanate-of-khiva', '1908-10-05', '1920-02-02', 2851348, 'not_sovereign', 1, None, 'EV_KHIVA_END', ['khiva1873'], '1873 年起為俄國保護國（非主權）。1908-10-05 為本批起點。', 'Russian protectorate from 1873 (not sovereign).'),
 ('KHPSR', 'khorezm-peoples-soviet-republic', '1920-02-02', '1924-10-27', 2851346, 'de_jure', 1, 'EV_KHIVA_END', EV_DELIM, ['delim1924'], '1924-10-27 中亞民族劃界後撤銷。', 'Abolished in the 1924 national delimitation.'),
 ('FER', 'far-eastern-republic', '1920-04-06', '1922-11-15', 2958014, 'de_jure', 1, 'EV_FER', 'EV_FER_END', ['peking1860', 'fer1922'], '蘇俄扶植的緩衝國；北庫頁島 1920～1925 由日本佔領（另列）。', 'Soviet-sponsored buffer state; northern Sakhalin under Japanese occupation (separate record).'),
 ('KOREA', 'korean-empire', '1908-10-05', '1910-08-29', 2694487, 'not_sovereign', 1, None, 'EV_KR_ANNEX', ['korea1910'], '1905 年起為日本保護國（非主權）；1910-08-29 併入日本。1908-10-05 為本批起點。', 'Japanese protectorate from 1905 (not sovereign); annexed 29 Aug 1910.'),
 ('MN_BOGD', 'bogd-khanate-of-mongolia', '1911-12-01', '1924-11-26', 2957591, 'not_sovereign', 1, 'EV_MN_AUTON', 'EV_MPR', ['mongolia1912'], '1913 年中俄聲明：外蒙古在中國宗主權下自治（非主權）；1919～1921 中國軍隊重佔、1921 年人民革命（未分段）。', 'Autonomous under Chinese suzerainty (1913 declaration); 1919–1921 Chinese reoccupation not split.'),
 ('MPR', 'mongolian-peoples-republic', '1924-11-26', '1937-07-07', 2942671, 'de_jure', 1, 'EV_MPR', None, [], '接 1937-07-07 起的既有紀錄。', 'Continues into the existing record from 7 Jul 1937.'),
 ('TUVA', 'tuvan-peoples-republic', '1921-08-14', '1937-07-07', 2849759, 'de_jure', 1, 'EV_TUVA', None, [], '接 1937-07-07 起的既有紀錄。1912～1921 唐努烏梁海：1914-04-17 起為俄國保護（OHM 俄國幾何已含）；1912-01-01～1914-04-17 OHM 無政權（空白）。', 'Continues into the existing record from 7 Jul 1937.'),
 ('TIBET', 'tibet-ganden-phodrang', '1912-01-01', '1937-07-07', 2828810, 'de_jure', 1, None, None, [], '起日依 OHM（1912，待查證；十三世達賴 1913-02-13 宣告）。接 1937-07-07 起的既有紀錄。', 'Start per OHM (1912; pending). Continues into the existing record.'),
 ('MANCHUKUO', 'manchukuo', '1932-03-01', '1937-07-07', 2885965, 'not_sovereign', 1, 'EV_MANCHUKUO', None, [], '日本扶植（非主權）。熱河 1933 年才被佔，未分段。接 1937-07-07 起的既有紀錄。', 'Japanese puppet state (not sovereign). Continues into the existing record.'),
 ('QING1', 'qing-dynasty', '1908-10-05', '1911-12-01', 2694485, 'de_jure', 3, None, 'EV_MN_AUTON', ['peking1860', 'ili1881'], '含外蒙古、唐努烏梁海、西藏。1908-10-05 為本批起點。', 'Includes Outer Mongolia, Tannu Uriankhai and Tibet.'),
 ('QING2', 'qing-dynasty', '1911-12-01', '1912-01-01', 2957594, 'de_jure', 3, 'EV_MN_AUTON', 'EV_ROC', ['peking1860', 'ili1881'], '外蒙古已脫離（另列）。', 'Outer Mongolia separate.'),
 ('ROC_BY1', 'republic-of-china-beiyang', '1912-01-01', '1924-11-26', 2694664, 'de_jure', 3, 'EV_ROC', 'EV_MPR', ['peking1860', 'ili1881', 'mongolia1912'], 'OHM 此版含外蒙古（中國宗主權下自治），本表外蒙古另列博克多汗國。', 'OHM includes Outer Mongolia; recorded separately here.'),
 ('ROC_BY2', 'republic-of-china-beiyang', '1924-11-26', '1928-06-08', 2957589, 'de_jure', 3, 'EV_MPR', 'EV_BEIYANG_END', ['peking1860', 'ili1881'], '1928-06-08 北伐軍進入北京（待查證），改由國民政府。', 'Beiyang government until June 1928.'),
 ('ROC_N1', 'republic-of-china-nationalist', '1928-06-08', '1930-09-30', 2957589, 'de_jure', 3, 'EV_BEIYANG_END', None, ['peking1860', 'ili1881'], '國民政府（南京）。', 'Nationalist government (Nanjing).'),
 ('ROC_N2', 'republic-of-china-nationalist', '1930-09-30', '1935-01-01', 2889460, 'de_jure', 3, None, None, ['peking1860', 'ili1881'], '1932-03-01 起扣除滿洲國。', 'Manchukuo excluded from 1 Mar 1932.'),
 ('ROC_N3', 'republic-of-china-nationalist', '1935-01-01', '1937-07-07', 2694471, 'de_jure', 3, None, None, ['peking1860', 'ili1881'], '接 1937-07-07 起的既有紀錄。', 'Continues into the existing record.'),
 ('JP1', 'empire-of-japan', '1908-10-05', '1910-08-29', 2694483, 'de_jure', 3, None, 'EV_KR_ANNEX', [], '含台灣、南樺太、關東州。1908-10-05 為本批起點。', 'Includes Taiwan, Karafuto, Kwantung.'),
 ('JP2', 'empire-of-japan', '1910-08-29', '1919-06-28', 2694484, 'de_jure', 3, 'EV_KR_ANNEX', EV_VERSAILLES, ['korea1910'], '含朝鮮。', 'Includes Korea.'),
 ('JP3', 'empire-of-japan', '1919-06-28', '1920-01-01', 2889768, 'de_jure', 3, EV_VERSAILLES, None, [], 'OHM 此版起含南洋群島（委任統治，未另分）。', 'OHM includes the South Seas Mandate (not split).'),
 ('JP4', 'empire-of-japan', '1920-01-01', '1925-01-20', 2851273, 'de_jure', 3, None, EV_SOVJP, [], '北庫頁島佔領區另列（非主權）。', 'Occupied northern Sakhalin recorded separately.'),
 ('JP5', 'empire-of-japan', '1925-01-20', '1931-01-01', 2889779, 'de_jure', 3, EV_SOVJP, None, [], '蘇日基本條約後收回北庫頁島佔領區，依 OHM 此版範圍。', 'After the 1925 Soviet–Japanese Convention; northern Sakhalin no longer occupied.'),
 ('JP6', 'empire-of-japan', '1931-01-01', '1937-07-07', 2889894, 'de_jure', 3, None, None, [], '接 1937-07-07 起的既有紀錄。', 'Continues into the existing record.'),
 ('PERSIA', 'sublime-state-of-persia', '1908-10-05', '1935-03-21', 2694889, 'de_jure', 3, None, 'EV_IRAN_NAME', ['akhal1881'], '卡扎爾王朝；1925-12 起巴勒維王朝（同一國家，未分段）。1907 年英俄協約勢力範圍、一戰期間各國駐軍未分段。1908-10-05 為本批起點。', 'Qajar, then Pahlavi from Dec 1925 (not split).'),
 ('IRAN35', 'imperial-state-of-iran', '1935-03-21', '1939-01-01', 2694890, 'de_jure', 3, 'EV_IRAN_NAME', None, ['akhal1881'], '接 1939-01-01 起的既有紀錄。', 'Continues into the existing record from 1 Jan 1939.'),
 ('AFG1', 'emirate-of-afghanistan', '1908-10-05', '1926-06-09', 2961096, 'de_jure', 3, None, 'EV_AFG_KINGDOM', ['afg1885', 'pamir1895'], '1919 年拉瓦爾品第條約前外交由英國掌控（未分段）。1908-10-05 為本批起點。', 'British control of foreign affairs until 1919 (not split).'),
 ('AFG2', 'kingdom-of-afghanistan', '1926-06-09', '1937-07-07', 2822863, 'de_jure', 3, 'EV_AFG_KINGDOM', None, ['afg1885', 'pamir1895'], '接 1937-07-07 起的既有紀錄。', 'Continues into the existing record.'),
]
