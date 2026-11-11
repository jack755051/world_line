# B3 生卒 12 筆矛盾修正：差異清單（dry-run，未寫庫）

依據：Tai 2026-11-11 21:24（World Line 主管轉達）；consistency-check.md／consistency-findings.json 建議＋五項預設做法。由 `data/seed/leaders/b3-trial/fix12/patch_fix12.py` 產生。

| 處理 | 筆數 | 人物（欄位） |
|---|---|---|
| 以基本資料為準 | 3 | 伍廷芳（生日、出生地）、Hansson（卒日）→ 段落撤回重寫，基本資料不變，記已解決 conflict |
| 以段落為準 | 1 | Mironas（卒日）→ 基本資料改 1953-02-18，補 Seimas 引文、撤回 VLE 引文，記已解決 conflict |
| 保留年份＋記 conflict | 2 | Noronha、Lyzohub（生日）→ 降為年精度，記帶限定詞 conflict |
| 留空＋記 conflict | 6 | Ávila Camacho（生日改 NULL、not_found 改 conflict）、Leygues（補 conflict）；Meierovics、Negrín、Said Halim、Hilmi 已符合（NULL＋既有 conflict），不變 |

## 1. 基本資料（leader_bios）

| 人物 | 欄位 | 舊值 | 新值 | 理由／來源 |
|---|---|---|---|---|
| 弗拉達斯·米羅納斯（Vladas Mironas，`01a1b545-5f9a-74f7-b257-4aca0ce09d17`） | death_date | 1953-02-17（day） | 1953-02-18（day） | 以段落為準：Seimas（A）「Mirė 1953 m. vasario 18 d.」 |
| 伊薩亞斯·德諾羅尼亞（José Isaías de Noronha，`c414bfc4-ad7e-4565-b494-541ad432dfa5`） | birth_date | 1873-07-06（day） | 1873-01-01（year） | 保留年份＋conflict（§16.7.3 放寬規則） |
| 費奧多爾·利佐胡布（Fedir Lyzohub，`01a1c35f-186c-7459-94d9-f5c3a548ec1c`） | birth_date | 1851-11-06（day） | 1851-01-01（year） | 保留年份＋conflict（§16.7.3 放寬規則） |
| 曼努埃爾·阿維拉·卡馬喬（Manuel Ávila Camacho，`01a1aa4a-da74-77db-baee-0f57adbb1f2c`） | birth_date | 1897-04-24（day） | NULL（—） | 留空＋conflict（年份互斥 1896／1897） |

## 2. 欄位引文（leader_bio_field_citations）

- 新增 弗拉達斯·米羅納斯（Vladas Mironas，`01a1b545-5f9a-74f7-b257-4aca0ce09d17`） deathDate：「Mirė 1953 m. vasario 18 d. Vladimiro kalėjime (Rusija)」（A）https://www.lrs.lt/pls/inter/w5_show?p_r=4165&p_d=159798&p_k=1　id `4b911b09-6013-5fe2-9a2c-564eb06a3ea8`
- 撤回 弗拉達斯·米羅納斯（Vladas Mironas，`01a1b545-5f9a-74f7-b257-4aca0ce09d17`） deathDate：「Vladas 1880 06 22 Kuodiškių vienkiemis (Panemunio vlsč.) 1953 02 17 Vladimir」https://www.vle.lt/straipsnis/vladas-mironas/　id `01a1b545-5f9b-7b3a-9c61-4d35e19af689`

## 3. 缺漏（leader_bio_gaps）

| 人物 | target | 動作 | 內容 |
|---|---|---|---|
| 佩爾·阿爾賓·漢森（Per Albin Hansson，`01a1b4b0-6fe9-72db-be2c-915cf61baa62`） | field:deathDate | 撤回 not_found `b889729c-fc03-4370-97b2-a5599bad9353` | 改記 conflict |
| 弗拉達斯·米羅納斯（Vladas Mironas，`01a1b545-5f9a-74f7-b257-4aca0ce09d17`） | field:deathDate | 撤回 not_found `6577e30e-8143-4527-8f09-fe46a719b292` | 改記 conflict |
| 曼努埃爾·阿維拉·卡馬喬（Manuel Ávila Camacho，`01a1aa4a-da74-77db-baee-0f57adbb1f2c`） | field:birthDate | 撤回 not_found `1fe2799d-5faf-4525-9d9a-317ae27d3551` | 改記 conflict |
| 伍廷芳（Wu Tingfang，`01a1c437-b43f-7116-bd87-22313035593e`） | field:birthDate | 新增 conflict（已解決，resolved_by `01a1c437-b43f-78cb-b8df-0150971deb93`） | BnF 權威記錄 1842-07-30 vs X-Boorman 轉載《民國人物傳記辭典》9 July 1842；Tai 2026-11-11 21:24 以基本資料（BnF，A）為準，段落改版 |
| 伍廷芳（Wu Tingfang，`01a1c437-b43f-7116-bd87-22313035593e`） | field:birthPlace | 新增 conflict（已解決，resolved_by `01a1c437-b440-77da-ba1d-3f3f9a4ebbc6`） | BnF 權威記錄 Malacca vs X-Boorman 轉載《民國人物傳記辭典》Singapore；Tai 2026-11-11 21:24 以基本資料（BnF，A）為準，段落改版 |
| 佩爾·阿爾賓·漢森（Per Albin Hansson，`01a1b4b0-6fe9-72db-be2c-915cf61baa62`） | field:deathDate | 新增 conflict（已解決，resolved_by `01a1b4b0-6fea-7f53-ae6b-4357e7174ee7`） | Malmö stad、BnF 1946-10-06 vs Lex、SNL 1946-10-05；Tai 2026-11-11 21:24 以基本資料為準，段落改版 |
| 弗拉達斯·米羅納斯（Vladas Mironas，`01a1b545-5f9a-74f7-b257-4aca0ce09d17`） | field:deathDate | 新增 conflict（已解決，resolved_by `4b911b09-6013-5fe2-9a2c-564eb06a3ea8`） | Seimas（A）1953-02-18 vs Visuotinė lietuvių enciklopedija 1953 02 17；Tai 2026-11-11 21:24 以段落（Seimas）為準，基本資料改為 1953-02-18 |
| 伊薩亞斯·德諾羅尼亞（José Isaías de Noronha，`c414bfc4-ad7e-4565-b494-541ad432dfa5`） | field:birthDate | 新增 conflict（未解決） | 保留現有值："1873-01-01"；[birthDate (day)] Arquivo Nacional（field_sources）1873-07-06 vs FGV CPDOC DHBB「no dia 6 de junho de 1873」；年份一致，依 §16.7.3 保留年份（Tai 2026-11-11 21:24） |
| 費奧多爾·利佐胡布（Fedir Lyzohub，`01a1c35f-186c-7459-94d9-f5c3a548ec1c`） | field:birthDate | 新增 conflict（未解決） | 保留現有值："1851-01-01"；[birthDate (day)] Encyclopedia of Ukraine「b 6 November 1851」vs Український історичний журнал「народився в жовтні 1851 р.」；年份一致，依 §16.7.3 保留年份（Tai 2026-11-11 21:24） |
| 曼努埃爾·阿維拉·卡馬喬（Manuel Ávila Camacho，`01a1aa4a-da74-77db-baee-0f57adbb1f2c`） | field:birthDate | 新增 conflict（未解決） | Museo de los Presidentes Coahuilenses（field_sources）1897-04-24 vs gob.mx「Nació el 24 de abril de 1896」；年份互斥，依 §16 該欄留空（Tai 2026-11-11 21:24） |
| 喬治·萊格（Georges Leygues，`cbb09808-0930-40ae-b03a-51d7d1d3c8a6`） | field:birthDate | 新增 conflict（未解決） | Assemblée nationale fiche 1857-10-26 vs Sycomore 1856-10-29（field_sources 註記；段落採 Sycomore「Né le 29 octobre 1856」）；年份互斥，依 §16 該欄維持空（Tai 2026-11-11 21:24） |
| 齊格弗里茲·安納·梅耶羅維奇（Zigfrīds Anna Meierovics，`01a1b51c-8311-70df-b77c-97d89e470686`） | field:birthDate | 不變 | 該欄已為 NULL，且已有未解 conflict 缺漏（e1702877-f64e-401e-970c-065bd6639065）；不需變更 |
| 胡安·內格林（Juan Negrín López，`01a1b52a-620e-7c9f-9408-9cb081f47412`） | field:birthDate | 不變 | 該欄已為 NULL，且已有未解 conflict 缺漏（c9609ab9-47f8-4476-8848-12f6c24e6e95）；不需變更 |
| 賽義德·哈利姆帕夏（Said Halim Pasha，`01a1b512-3353-74ad-a495-5ee6c8e7d198`） | field:birthDate | 不變 | 該欄已為 NULL，且已有未解 conflict 缺漏（9cb2e36c-fc09-42b9-b3a8-373e9bacbb5a）；不需變更 |
| 侯賽因·希勒米帕夏（Hüseyin Hilmi Paşa，`01a1c37d-aa7e-7cda-b68d-029070be86f1`） | field:deathDate | 不變 | 該欄已為 NULL，且已有未解 conflict 缺漏（f12ecfd5-9b85-4dba-98d0-cfc8d0c8eca1）；不需變更 |

## 4. 段落改版（leader_bio_paragraphs 撤回重寫＋superseded_by）

### 伍廷芳（Wu Tingfang，`01a1c437-b43f-7116-bd87-22313035593e`） 第 1 段

- 舊 `37d0857a-9d93-462a-931b-05bb2c756887` → 新 `836f299d-c379-5617-ac54-3b6e3cc977d9`；period [1842-07-09,1898-01-01)（day/year）→ [1842-07-30,1898-01-01)（day/year）
- 舊英文：According to the Biographical Dictionary of Republican China, Wu T'ing-fang was born on 9 July 1842 at Singapore. He was called to the English bar in 1876, becoming the first Chinese barrister, and in 1897 he was appointed minister to the United States, Spain and Peru.
- 新英文：According to the BnF authority record, Wu Tingfang was born on 30 July 1842 in Malacca. He was called to the English bar in 1876, becoming the first Chinese barrister, and in 1897 he was appointed minister to the United States, Spain and Peru.
- 舊中文：據《民國人物傳記辭典》條目，伍廷芳生於1842年7月9日，出生於新加坡；1876年取得英國律師資格，成為首位華人大律師，1897年被任命為駐美國、西班牙與秘魯公使。
- 新中文：據法國國家圖書館（BnF）權威記錄，伍廷芳於1842年7月30日生於馬六甲；1876年取得英國律師資格，成為首位華人大律師，1897年被任命為駐美國、西班牙與秘魯公使。
- 引文：沿用 3 筆（複製到新段落）；不沿用：
  - 「Although Wu T'ing-fang was born at Singapore」（條目正文）https://xboorman.enpchina.eu/biographie/wu-tingfang/：出生地 Singapore 與 BnF Malacca 矛盾（Tai 21:24 以基本資料為準）
  - 「Wu T'ing-fang (9 July 1842-23 June 1922)」（條目正文）https://xboorman.enpchina.eu/biographie/wu-tingfang/：生日 9 July 1842 與 BnF 1842-07-30 矛盾（Tai 21:24 以基本資料為準）
- 新增引文：「1842-07-30, Malacca (Malaisie)」（Naissance，A）https://catalogue.bnf.fr/ark:/12148/cb16776173k

### 佩爾·阿爾賓·漢森（Per Albin Hansson，`01a1b4b0-6fe9-72db-be2c-915cf61baa62`） 第 3 段

- 舊 `6456dabd-c1ae-4bf2-a3b7-f79d036c9c9b` → 新 `05ee61f7-a876-5030-a4cd-46ec4329e784`；period [1932-01-01,1946-10-05)（year/day）→ [1932-01-01,1946-10-07)（year/day）
- 舊英文：In 1932, in the midst of the economic crisis, Hansson became leader of a Social Democratic minority government, and in 1933 reached the so-called crisis settlement with the Agrarian League. His government was replaced by an Agrarian League government in summer 1936, but in September that year he formed a government again. After the outbreak of the Winter War in December 1939 he formed a national coalition government, and externally Sweden’s formal, later somewhat contested neutrality was secured. He died in Stockholm on 5 October 1946.
- 新英文：In 1932, in the midst of the economic crisis, Hansson became leader of a Social Democratic minority government, and in 1933 reached the so-called crisis settlement with the Agrarian League. His government was replaced by an Agrarian League government in summer 1936, but in September that year he formed a government again. After the outbreak of the Winter War in December 1939 he formed a national coalition government, and externally Sweden’s formal, later somewhat contested neutrality was secured. He died on 6 October 1946.
- 舊中文：1932年經濟危機中，漢森出任社會民主黨少數政府的領導人，1933年與農民聯盟達成「危機協議」。1936年夏天其政府被農民聯盟政府取代，同年9月他再度組閣。1939年12月冬季戰爭爆發後他組成國家聯合政府，對外確保瑞典形式上、後來頗受爭議的中立。他於1946年10月5日在斯德哥爾摩逝世。
- 新中文：1932年經濟危機中，漢森出任社會民主黨少數政府的領導人，1933年與農民聯盟達成「危機協議」。1936年夏天其政府被農民聯盟政府取代，同年9月他再度組閣。1939年12月冬季戰爭爆發後他組成國家聯合政府，對外確保瑞典形式上、後來頗受爭議的中立。他於1946年10月6日逝世。
- 引文：沿用 9 筆（複製到新段落）；不沿用：
  - 「5. oktober 1946, Stockholm, Sverige」（Faktaboks）https://lex.dk/Per_Albin_Hansson：卒日 5. oktober 1946 與基本資料 1946-10-06 矛盾（Tai 21:24 以基本資料為準）；逝世地 Stockholm 僅此引文支持，新版刪去地點
- 新增引文：「Mort : 1946-10-06」（Mort，A）https://catalogue.bnf.fr/ark:/12148/cb13327459z

## 5. 注意

- Hansson、Mironas、伍廷芳的 conflict 記為**已解決**（resolved_at＋resolved_by_citation_id 指向採用的欄位引文），因 §16「欄位有 conflict 時該欄須為 NULL」只適用未解決者；若 Tai 認為應記未解決，該欄依規則須改 NULL 或降精度。
- Hansson 新版刪去逝世地「Stockholm」：唯一支持的引文（Lex「5. oktober 1946, Stockholm, Sverige」）日期與採用值矛盾而不沿用；死亡地本次不補（Tai 預設 4）。
- Ávila Camacho 的 field_sources.birthDate 仍為 verified 1897-04-24（jsonb 說明欄不改）；欄位值改 NULL。
- seed：run100 的 research.json 不改；修正版段落見 `fix12/paragraphs.patched.json`（seed 格式，含 supersedes）。日後若在空庫重建，需在 run100 寫入後套用本 patch。
- 寫庫需另經同意；plan.sql 結尾為 ROLLBACK、沒有 COMMIT。
