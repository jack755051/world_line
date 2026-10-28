# 二戰（1937-07～1945-09）史料來源調查報告

- 調查日期：2026-10-27
- 目的：在動工前確認「主權軸」與「控制軸」的資料是否真的拿得到、授權能不能用，避免重演三國版因缺資料而停擺的情況。
- 方法：授權一律回到第一手頁面核對（GitHub API、資料集官網、Wikimedia Commons 檔案頁原始碼、館藏紀錄）。主權資料集有實際下載，並抽查 1937～1945 的內容。查不到第一手證據的項目一律標為「**未驗證**」。
- 對應憲法：R6（主權／控制分軸）、R7（史料來源政策）、I6（每筆資料都要附來源），見 [`.claude/constitutions/world-line.md`](../../.claude/constitutions/world-line.md)。

> **一句話結論**：主權軸可行，但沒有任何一份現成資料集能直接用，必須「CC0 骨架＋人工補主張」。控制軸做「歐洲／太平洋的戰役級快照」可行；做「全球、逐月」**一個人做不到**，而且中國戰區、東非、東南亞（印支、泰國）缺乏可用的公有領域地圖，逐月資料在來源上根本不存在。建議改成「有來源才有快照」的事件驅動模式（見第 6 節）。

---

## 1. 主權軸（法理疆界）候選資料集

### 1.1 總覽

| 資料集 | 授權（第一手） | 時間粒度 | 1937–45 覆蓋 | 建議 |
|---|---|---|---|---|
| OpenHistoricalMap (OHM) | **CC0**（資料） | 精確到日（`start_date`/`end_date`） | 豐富：有滿洲國、法蘭西國（維琪）、斯洛伐克、克羅埃西亞，德國分 10 個時段 | **主力骨架**，但每筆都要另外補來源 |
| CShapes 2.0（ETH Zürich） | **CC BY-NC-SA 4.0** | 精確到日（`gwsdate`/`gwedate`） | 只收「國際體系成員」，**刻意不收**戰時併吞與傀儡政權 | 僅作交叉比對，**不要把幾何併入資料庫** |
| historical-basemaps（aourednik） | **GPL-3.0** | 只有 1938、1945 兩個年份快照 | 錯誤多（見下） | **不建議** |
| europe-historical-geojson（ioggstream） | BSD-3-Clause | 只有 1914／1915 | 無 | **不適用** |
| Natural Earth | 公有領域 | 只有現代 | 無 | 只當現代底圖、海岸線用 |
| GeaCron | 版權所有、商業授權 | 每年 1 月 1 日 | 有 | 商業，不可用 |
| Euratlas | 付費授權（簡易授權 €160 起） | 每 100 年 | 無 1940 年 | 不適用 |

### 1.2 OpenHistoricalMap

- **授權**：「In general, OpenHistoricalMap data is in the public domain under a CC0 dedication」；署名只是禮貌性要求；少數個別圖徵可能有額外要求。來源：<https://wiki.openstreetmap.org/wiki/OpenHistoricalMap/Reuse>
- **衍生資料庫／商用**：CC0 不限制，也沒有 copyleft。這是所有候選裡授權最寬鬆的一份。
- **實測**（2026-10-27 透過 OHM Overpass API `https://overpass-api.openhistoricalmap.org/api/interpreter`，查詢所有帶 `start_date` 的 `admin_level=2` relation）：共 4,155 筆，其中 **372 筆**的時間區間與 1937–1945 重疊。
  - 有：`Manchukuo`（1932～1945-08-17）、`French State`（1940-06-25～1942-11-11 等 3 段）、`Military Administration in Belgium and Northern France`（1940-06-25～）、`Slovak Republic`、`Independent State of Croatia`、`Italian East Africa`（1936-06-01～1941-11-27）、`Estonia SSR`／`Latvian SSR`／`Lithuanian SSR`（1940-07-21～08）、`Austria`（1922～1938-03-13，1945-04-27～）、`German Reich` 共 10 個時段（例如 1938-03-13、1938-11-21、1939-03-16……）、`Japanese occupation of Malaya`、`Second Philippine Republic` 等。
  - **缺口**：沒有汪精衛政權、華北臨時政府、蒙疆（中國戰區的傀儡政權缺）；`Poland` 1939-10-06～1945-08 之間是空的；中國只有 `China` 一個多段 relation，沒有分出佔領區。
  - **品質問題**：372 筆中只有 **42 筆（11%）帶 `source*` 標籤**，而且來源包括 Wikipedia、YouTube、worldstatesmen.org、Wikimedia 上的自繪圖。有些日期明顯錯誤（`German Occupation` 的 start 1939-09-03 晚於 end 1939-05-08）。`French Republic` 結束於 1940-06-22、`French State` 開始於 1940-06-25，與法制上 1940-07-10／11 憲法法律的時間點不一致。341 筆有 `wikidata` 標籤，可以用來回查。
- **結論**：可以當幾何骨架（CC0 沒有授權負擔），但依 I6／R7「無來源不可建立」，每筆 OHM 疆域都要另外補一個可引用的來源，並人工核對日期。

### 1.3 CShapes 2.0

- **授權**：CC BY-NC-SA 4.0。時間範圍 1886–2019。格式有 CSV、GeoJSON、Shapefile、SQL、R 套件。引用：Schvitz et al. 2022, *Journal of Conflict Resolution* 66(1):144–61。來源：<https://icr.ethz.ch/data/cshapes/>
- **授權影響**：
  - NC（非商業）：免費教育用途沒問題，但**以後如果要商業化，就必須整份移除**。
  - SA（相同方式分享）：只要把 CShapes 幾何併進資料庫並對外散布，**整個衍生資料庫都必須以 BY-NC-SA 釋出**，而且會跟 OHM 的 CC0 部分混在一起，難以切割。
  - 建議：只拿來交叉比對日期（日期屬於事實，本身不受著作權保護），**不要複製幾何**。
- **實測**（下載 `CShapes-2.0.csv`，44.5 MB，710 筆；自寫點在多邊形內測試）：
  - 有精確日期的變動：捷克斯洛伐克 1938-09-30（蘇台德）、1938-11-02（第一次維也納仲裁）；羅馬尼亞 1940-06-28（比薩拉比亞）、1940-09-07；波羅的海三國在 **1940-06-01** 結束、併入蘇聯（實際併入是 1940-08，CShapes 用的是佔領日）；冰島 1944-06-17。
  - **刻意不收**的情況：奧地利 1919-09-10～2019-12-31 一段到底（**沒有德奧合併**）；維也納、布拉格、華沙 1939–45 分別仍落在奧地利、捷克斯洛伐克、波蘭；哈爾濱 1921–1945 屬於 China（**沒有滿洲國**）；阿迪斯阿貝巴 1907–1952 屬於 Ethiopia（**沒有義屬東非**）；法國 1919–2019 一段（沒有維琪、亞爾薩斯-摩澤爾）。
  - 這是 Gleditsch & Ward 國家體系的編碼邏輯（戰時佔領不算國家消滅），**不是「主權主張」資料**。正好對應憲法 R6 的「承認方」視角之一（同盟國／戰後國際社會不承認的併吞），可以當成一種視角，但不能代表軸心國那一方的主張。
- **結論**：當「戰後國際承認視角」的參考很好用，但不能當主資料。

### 1.4 historical-basemaps（aourednik/historical-basemaps）

- **授權**：GitHub API 回傳 `spdx_id: GPL-3.0`。README 自稱「work in progress」，並建議學術用途要先與其他來源核對。來源：<https://github.com/aourednik/historical-basemaps>、<https://api.github.com/repos/aourednik/historical-basemaps>
- **copyleft 影響**：GPL-3.0 用在資料上本來就很怪（它是為程式碼寫的）。只要前端把 GeoJSON 下載到使用者瀏覽器，就構成「散布」，衍生的資料檔就必須以 GPL-3.0 釋出、提供「原始碼」。這點與 OHM 的 CC0 相容（CC0 可以併入 GPL），但反過來就不能把 GPL 部分再以 CC0 釋出。實際後果怎麼認定屬於法律解讀，**不由本報告判斷**。
- **時間粒度**：`geojson/` 目錄在 1930 年之後只有 `world_1930`、`world_1938`、`world_1945`、`world_1960`（已用 GitHub API 列出完整目錄確認）。
- **實測 1938／1945 內容**（下載後列出所有 `NAME|SUBJECTO`）：
  - 1938：中國標為 `Chinese warlords`；**沒有滿洲國**；`Cambodia`、`Cochin China` 標為 `Empire of Japan`（**時代錯誤**，1938 年仍屬法屬印度支那）；出現 `Israel`、同時出現 `India` 與 `British Raj`。
  - 1945：出現 `Israel`、`Pakistan`、`Bangladesh`、`Indonesia`、`Taiwan|Taiwan`（都是時代錯誤）；`Manchuria|Manchuria`。
  - `BORDERPRECISION` 欄位在檢查到的所有圖徵都是 3（「依國際法確定」），**沒有參考價值**。
- **結論**：只有 2 個時間點，又有嚴重的時代錯誤，再加上 GPL。**不建議採用**。

### 1.5 其他

- **europe-historical-geojson**：BSD-3-Clause；README 說明範圍是「維也納會議到一戰」，檔案只有 `mappe-1914.yaml`、`mappe-1915.yaml`。來源：<https://github.com/ioggstream/europe-historical-geojson>
- **Natural Earth**：「All versions of Natural Earth raster + vector map data found on this website are in the public domain」。來源：<https://www.naturalearthdata.com/about/terms-of-use/>。只有現代疆界，可以拿海岸線、河流來做底圖。
- **GeaCron**：頁尾寫「Copyright © 2011 - geacron.com - All Rights Reserved」，有「Commercial Offer」，地圖是「每年年初」的狀態。來源：<http://geacron.com/the-geacron-project/>。屬於商業資料，不可用。
- **Euratlas**：GIS 資料要付費購買，1700 年版簡易授權 €160、擴充授權 €640。來源：<https://www.euratlas.com/shop/1_gis_1700.html>、<https://euratlas.net/history/europe/gis.html>

### 1.6 主權軸建議

1. 以 **OHM（CC0）** 為幾何骨架，逐筆補上可引用的來源（條約、官方公報、教科書級史書）。
2. 以 **CShapes 2.0** 交叉比對日期，作為「戰後國際承認」視角的參考，**只引用日期，不複製幾何**。
3. 中國戰區的傀儡政權（華北臨時政府、維新政府、汪政權、蒙疆）OHM 都沒有，要自己數位化。可用的公有領域底圖見 2.4 節（West Point 的「China 1941」等）。

---

## 2. 控制軸（實際控制、軍事佔領）候選地圖

規則（憲法 R7）：只用有明確出版者、屬於公有領域或 CC 授權的地圖，每筆紀錄都要標出圖集與頁碼／圖號。

### 2.1 美國西點軍校歷史系（USMA Department of History）戰役圖集

- **來源與現況**：
  - 舊站 `dean.usma.edu`、新站 `westpoint.edu/.../digital-history-center/atlases/world-war-two-europe`、`.../world-war-two-asia` 在 2026-10-27 **都回應 404**。系所已改名為 History and War Studies：<https://www.westpoint.edu/academics/departments/history-and-war-studies>
  - 圖檔本身仍在 S3，例如 `https://s3.amazonaws.com/usma-media/inline-images/academics/academic_departments/history/WWII%20Europe%20Med/WWIIEurope15.jpg` 實測回應 200，解析度 5101×3300。
  - 目錄頁可從 Wayback 取得：<https://web.archive.org/web/2023/https://www.westpoint.edu/academics/academic-departments/history/digital-history-center/atlases/world-war-two-europe>、<https://web.archive.org/web/2023/https://www.westpoint.edu/academics/academic-departments/history/digital-history-center/atlases/world-war-two-asia>
  - **風險**：官方頁面已下線，要盡快把需要的圖檔與目錄存到本地。
- **授權依據**：Wikimedia Commons 上這批圖一律標 `{{PD-USGov-Military-Army}}`，依據是 17 U.S.C. §105（聯邦雇員職務著作）。例如 <https://commons.wikimedia.org/wiki/File:1940FranceJune.jpg>、<https://commons.wikimedia.org/wiki/File:WWIIEurope34.jpg>。Commons 轉錄的舊站說明寫著：「The maps were created by the United States Military Academy's Department of History and are the digital versions from the atlases printed by the United States Defense Printing Agency」（見 <https://commons.wikimedia.org/wiki/File:Japanese_Occupation_-_Map.jpg>）。
- **灰色地帶**：舊站的 map_sources 頁（<https://web.archive.org/web/20070702081939/http://www.dean.usma.edu/history/web03/atlases/map_sources.htm>）列出紙本版由商業出版社發行：*Atlas of The Second World War: Europe and the Mediterranean*（Avery, 1985）、*Atlas of The Second World War: Asia and the Pacific*（Square One, 1985）、Esposito 主編的 *West Point Atlas of American Wars* Vol. II（Praeger, 1959）。
  - Praeger 版在 LoC 有著作權登記號 A 425-010：<https://www.loc.gov/item/59007452>。是否續展，**未驗證**。
  - 一般見解是：地圖本身由軍校職員繪製，屬聯邦著作，商業版只能主張新增部分的權利。**引用時請引用軍校數位版的圖號，不要引用商業版的頁碼**。
- **時間粒度**：戰役級，一張圖涵蓋數天到數月，不是逐月。
- **歐洲／地中海圖集目錄**（共 83 號，從 Wayback 目錄抓出）：
  - 波蘭 3–7；挪威 8；西線 1940 9–15；芬蘭 16a–c；巴爾幹 17–18
  - 東線 19–32（1941-06 到 1945-03，大約每 2–4 個月一張）
  - 北非 33–42；義大利 45–52；西北歐 53–82；佔領區 83
- **亞洲／太平洋圖集目錄**（約 55 號）中**與中國相關**的：
  - 「China, 1941」
  - 「Chinese Territory Seized Prior to July 1937 and Major Japanese Drives in 1937」
  - 「China, Japanese Advances During 1938 and 1939」
  - 「Allied Reorganization, 30 March 1942 and Area Under Japanese Control, 6 August 1942」
  - 「Operation ICHIGO, April–December 1944 and Situation 31 December」
  - 「Operation ICHIGO, 1945 and Final Operations in the War」
  - 「Areas Under Allied Japanese Control, 15 August 1945」
  - 東南亞：「The Imperial Powers, 1 September 1939」、「Japanese Centrifugal Offensive」、「Southern Asia … January–May 1942」、緬甸 3 張
- **另一本圖集**：中國內戰圖集第 4 號「Japanese Occupation, 1940」、第 5 號「Situation at the End of World War Two」（Wayback 目錄：<https://web.archive.org/web/2007/http://www.dean.usma.edu/history/web03/atlases/chinese%20civil%20war/chinese%20civil%20war%20index.htm>；Commons：<https://commons.wikimedia.org/wiki/File:Japanese_Occupation_-_Map.jpg>、<https://commons.wikimedia.org/wiki/File:Situation_at_the_End_of_World_War_Two.PNG>）
- **地理配準難度**：中等偏低。大比例尺小、有經緯網格（A–D／1–4 格）、城市點清楚，用 10–20 個城市控制點就能配準。圖上的投影沒有標示，邊緣誤差可能到數十公里，以國家／控制區層級來說可以接受。

### 2.2 美國陸軍軍事史中心（CMH）「Green Books」與戰役小冊

- **授權依據**：美國政府出版品，17 U.S.C. §105。圖書館編目註記：「pursuant to Title 17 Section 105 of the United States Code, this file is not subject to copyright protection and is in the public domain」（引自 umbrasearch 的 CMH PDF 紀錄：<https://umbrasearch.org/catalog/280f89c35dd1b22a17bdeb6ba70f0e3c02ce1d54>）。
  - CMH 官網 history.army.mil 在 2026-10-27 對自動化請求一律回 403，官方的重用聲明**未能直接讀到**。
  - 個別書目的前頁可能另有聲明，要逐冊確認。
- **取得管道**：
  - HyperWar 鏡像：<https://www.ibiblio.org/hyperwar/>。例如 Ziemke《Stalingrad to Berlin》（CMH Pub 30-5，1968 初版）：<https://www.ibiblio.org/hyperwar/USA/USA-EF-Defeat/index.html>
  - GPO 的 FDLP PURL
  - UT Austin PCL 的 CMH 圖片摘錄：<https://maps.lib.utexas.edu/maps/historical/history_ww2.html>（2026-10-27 被 Anubis 擋，**未能直接讀取**）
- **相關書目**：
  - 東線：Ziemke《Stalingrad to Berlin》、《Moscow to Stalingrad》
  - 中緬印：Romanus & Sunderland 三冊（CMH Pub 9-1、9-2、9-3；Commons 有 <https://commons.wikimedia.org/wiki/File:CMH_Pub_9-1_Stilwell_in_China.pdf>）
  - 戰役小冊《China Defensive 1942–1945》（CMH Pub 72-38，Mark D. Sherry 著，有彩色地圖，含 Ichigo 計畫 1944-04 圖；書目：<https://cmu.marmot.org/Record/.b58027981>）
  - 中緬印戰區地圖彙整：<https://cbi-theater.com/maps/_Map_source.html>
- **時間粒度**：戰役級，**各冊的圖目都還沒逐冊核對**。
- **地理配準難度**：中等。多為黑白線圖，部分有經緯網。

### 2.3 美國國會圖書館（LoC）

- **「World War II Military Situation Maps」**：
  - 內容：第 12 集團軍群每日態勢圖，416 張圖、115 份報告，範圍 **1944-06-06～1945-07-26**，美國政府出版。
  - 館方權利說明：不知道有美國著作權或其他限制，「providing access … for noncommercial, educational, and research purposes」。
  - 館藏說明：<https://www.loc.gov/collections/world-war-ii-maps-military-situation-maps-from-1944-to-1945/about-this-collection/>；單張範例：<https://www.loc.gov/resource/g5701s.ict21313/>
  - loc.gov 對自動化請求回 403，權利文字是透過搜尋摘要轉述，建議人工開頁確認。
  - **用途**：西線 1944-06 之後可以做到日級，但以第一階段的國家層級來說太細。**只有西北歐有這套**，其他戰區沒有同等資料。
- **中國戰區**：LoC 地圖目錄有 1937–39 年的中、日民間出版戰況圖，例如大阪每日新聞社 1938《最新支那戰局全圖》、中國地圖社 1937 戰況圖、1939 日本陸軍「1937-08～1939-03 進軍圖」，以及一張 1944 年中國後方戰場圖（附軍事活動索引）。
  - 檢索結果頁：<https://loc.gov/maps/?all=true&dates=1930-1939&fa=partof%3Acatalog%7Csubject%3Asino-japanese+war%7Clocation%3Achina%7Csubject%3Achina>
  - **授權推論（未經法律確認）**：日本法人名義著作在當時的保護期是公表後 50 年，1938 年出版的到 1988 年已經屆滿，美國 URAA 不會回復保護，因此在日、美兩地可能都屬於公有領域。中國地圖社的圖，在中華民國舊著作權法下推論相同。**每張都要逐張確認作者身分（法人或自然人）**。
  - 這些是報紙或宣傳圖，**準確度與立場都需要對照**。

### 2.4 中國戰區（最弱的一環，專項調查）

| 候選 | 授權 | 粒度 | 評估 |
|---|---|---|---|
| West Point 亞洲圖集（6–7 張中國圖，見 2.1） | 美國聯邦 PD | 1937、1938–39、1941、1942-08、1944-12、1945、1945-08-15 | **唯一能系統性使用的 PD 來源**，但一年不到一張 |
| West Point 中國內戰圖集 #4、#5 | 美國聯邦 PD | 1940、1945 | 同上 |
| CMH 中緬印三冊、《China Defensive》小冊 | 美國聯邦 PD | 1942–45，集中在 Ichigo、滇西、緬北 | 偏向美軍視角，華北、華中敵後少 |
| 《Why We Fight VI: The Battle of China》（1944）影片截圖 | 美國政府 PD（OWI） | 1944 | 宣傳片，**不建議**當史料，例：<https://commons.wikimedia.org/wiki/File:Japanese_zones_of_control.png> |
| ABCA Map Review No. 73《China, Scene of the Fourteen Years' Invasion》（倫敦，1945） | ANU 標示「Copyright Expired」、Open Access | 1945 | 英國陸軍時事局出品，可作補充。<https://dspace-prod.anu.edu.au/items/151d905b-933d-497d-b31a-b4053537446e/full> |
| 日方《戰史叢書》（防衛廳防衛研修所戰史室，1966–1980，102 卷；含《支那事變陸軍作戰》附圖） | 頁面標示「Copyright © The National Institute for Defense Studies. All Rights Reserved.」 | 戰役級，最詳細 | **不是公有領域**。日本國家著作屬法人名義，保護期為公表後 70 年，推估約到 2036–2050 年。全文可在線上閱覽，但**不符 R7**。<https://www.nids.mod.go.jp/military_archives/senshi_sousyo.html> |
| 美軍《Japanese Monographs》（例如 No. 178《North China Area Operations Record, July 1937–May 1941》） | 由駐遠東美軍司令部監修，**PD 地位未驗證** | 作戰級 | 文字為主、附圖少。指南：<https://www.ibiblio.org/pha/monos/guide.html> |
| JACAR（亞洲歷史資料中心）的戰時日方原始檔案 | 原始文件多屬 1945 年前的政府文書；JACAR 本身的影像利用條款**未能取得**（官網找不到條款頁） | 不定 | 史料價值高，但要逐件找、逐件判斷 |
| Stanford 外邦圖（日軍參謀本部陸地測量部地形圖） | 編目標示「This item is in the public domain. There are no restrictions on use.」<https://geo.btaa.org/catalog/stanford-ch237ht4777> | 地形圖，非態勢圖 | 只能當配準底圖，**不含控制區資訊** |
| 中研院地圖數位典藏 | 授權條款**未查到** | — | 有台灣日治地圖，但沒有找到淪陷區圖層。<https://gis.rchss.sinica.edu.tw/mapdap/> |
| 現成 GIS 資料集 | — | — | **沒有找到**任何 1937–45 中國佔領區的開放 GIS 資料。學術上最接近的是 D. Serfass〈Mapping China under Japanese Occupation〉（Bloomsbury 2022，書中章節，非開放資料） |

**中國戰區的結論**：
- 有 PD 來源可支撐的中國快照大約只有 **7–9 個時間點**（1937 末、1938 末、1939 末、1940、1941、1942-08、1944-12、1945-08）。
- 而且這些圖畫的都是日軍「佔領區」的外輪廓。憲法 §6 定義的「不完全控制」（點線佔領以外的游擊區、敵後根據地）**沒有任何 PD 地圖畫過**。
- 中國戰區在 PD 條件下**不可能逐月**。

### 2.5 東線（德蘇）

- **West Point 歐洲圖集 19–32**：14 張，1941-06～1945-03，大約每季一張，PD。
- **CMH**：Ziemke 兩冊，PD，圖較多，可補到大約每 1–2 個月一張（**需逐冊核對圖目**）。
- **德軍 OKH「Lage Ost」每日態勢圖**：
  - 館藏：NARA RG 242（擄獲德國檔案）。NARA 新數位化的系列有「German Situation Maps of the Western Front, 1944-1945」（NAID 40432392）、「Various German World War II Maps, 1939-1945」（NAID 40480105），出處：<https://dupuyinstitute.org/2017/03/03/new-wwii-german-maps-at-the-national-archives/>。該文（2017）說高解析掃描「尚未上線」，目前是否已上線**未驗證**。
  - **授權**：德國戰時未出版的不具名作品，德國保護期已過；但在美國可能被 URAA 回復保護，保護期可能長達建立後 120 年。**法律灰色地帶，不建議當主要引用**。
- **Glantz《August Storm》**（Leavenworth Papers No. 7，美國陸軍指揮參謀學院 CSI 1983，書目：<https://lib.ecu.edu/catalog-preview/catalog/993077>；姊妹作 No. 8 的 DTIC PDF：<https://apps.dtic.mil/sti/tr/pdf/ADA143942.pdf>）：
  - 作者當時是現役軍官、由陸軍出版，**推論**屬 PD（未逐頁確認版權頁）。
  - 涵蓋 1945-08 滿洲戰役，可以補上蘇日戰爭。

### 2.6 太平洋、東南亞

- **太平洋**：West Point 亞洲圖集覆蓋良好，菲律賓、荷屬東印度、新幾內亞、所羅門、馬里亞納、雷伊泰、呂宋、沖繩都有圖（PD）。Commons 已有 23 張，分類：<https://commons.wikimedia.org/wiki/Category:Pacific_War_maps_of_the_United_States_Military_Academy>。
- **馬來亞、荷屬東印度、緬甸**：West Point 有，緬甸另有 CMH 中緬印三冊。
- **法屬印度支那、泰國**：1940-09 日軍進駐北部、1941-07 進駐南部、1941 年泰法戰爭割地、1945-03 明號作戰，這幾件事**都沒有找到 PD 地圖**。West Point 只有「The Imperial Powers, 1939」與「Southeast Asia 1941」概觀圖。**這是缺口**。

### 2.7 非洲、中東

- **北非（利比亞、埃及、突尼西亞）**：West Point 歐洲圖集 33–42（PD），大約每次攻勢一張。
- **東非（義屬東非 1940–41、英屬索馬利蘭 1940-08 失守、馬達加斯加 1942）**：**沒有找到美國 PD 圖**。
  - 英國官方戰史 Playfair《The Mediterranean and Middle East》Vol. I（HMSO 1954）有，HyperWar 有鏡像：<https://www.ibiblio.org/hyperwar/UN/UK/UK-Med-I/index.html>。
  - 授權推論：皇家著作權在英國是出版後 50 年，2004 年已屆滿，英國境內是 PD；但美國 URAA 可能把它回復保護到出版後 95 年（2049）。是否可用要看主機與使用者所在地，**屬法律判斷，未驗證**。
- **中東（1941 伊拉克、敘利亞、伊朗）**：伊朗部分有 CMH《The Persian Corridor and Aid to Russia》（PD，未逐圖核對）；敘利亞、伊拉克只有英國官方戰史，同上屬灰色地帶。
- **西非、赤道非洲（自由法國與維琪之爭）**：屬於主權歸屬變動，不是戰線問題，可以用日期表處理，不需要地圖。

### 2.8 Wikimedia Commons 衍生圖的使用原則

- **可用**：檔案頁的 Source 指向具名出版者，且授權模板與出版者相符。例如 West Point 系列 `{{PD-USGov-Military-Army}}`，分類：<https://commons.wikimedia.org/wiki/Category:World_War_II_maps_of_the_United_States_Military_Academy>（76 個成員）。
- **不可用（違反 R7「自製不採用」）**：
  - <https://commons.wikimedia.org/wiki/File:Vichy_france_map.png>：沒有標出版來源。
  - <https://commons.wikimedia.org/wiki/File:Carte_régionale_et_zonale_de_la_France_occupée_de_1940_à_1943.png>：`{{own}}`、CC BY-SA 4.0，2025 年由使用者綜合部落格、新聞圖片等繪製。

---

## 3. 覆蓋矩陣（戰區 × 來源）

圖例：● 可用、PD 已確認、有圖號｜◐ 部分可用或需逐冊核對｜△ 法律灰色或只能當參考｜✕ 無

| 戰區 \ 來源 | West Point 歐洲 | West Point 亞洲 | West Point 中國內戰 | CMH Green Books／小冊 | LoC 12AG 每日圖 | LoC 1937–39 中日民間圖 | 英國官方戰史 | 德軍 Lage／日本戰史叢書 | 可達粒度（PD 條件下） |
|---|---|---|---|---|---|---|---|---|---|
| 西歐 1939–40 | ● 9–15 | ✕ | ✕ | ✕ | ✕ | ✕ | △ | △ | 戰役級（1940-05～06 約每週） |
| 西北歐 1944–45 | ● 53–83 | ✕ | ✕ | ◐ | ●（日級） | ✕ | △ | △ | 日級 |
| 東線 1941–45 | ● 19–32 | ✕ | ✕ | ◐ Ziemke | ✕ | ✕ | ✕ | △ Lage Ost | 季級，CMH 可補到約 1–2 月 |
| 芬蘭 1939–40、1944 | ● 16a–c | ✕ | ✕ | ✕ | ✕ | ✕ | ✕ | ✕ | 戰役級，**1941–44 繼續戰爭是缺口** |
| 巴爾幹 1941–45 | ● 17–18、31 | ✕ | ✕ | ◐ | ✕ | ✕ | △ | △ | 戰役級，**1941–44 分割佔領的內部界線是缺口** |
| 義大利 1943–45 | ● 45–52 | ✕ | ✕ | ◐ | ✕ | ✕ | △ | △ | 戰役級 |
| 北非 1940–43 | ● 33–42 | ✕ | ✕ | ◐ | ✕ | ✕ | △ | ✕ | 每次攻勢 |
| **東非 1940–41** | ✕ | ✕ | ✕ | ✕ | ✕ | ✕ | △ | ✕ | **缺口** |
| 中東 1941 | ✕（只有 43 號概觀） | ✕ | ✕ | ◐ 波斯走廊 | ✕ | ✕ | △ | ✕ | **大致缺口** |
| **中國 1937–45** | ✕ | ◐ 6–7 張 | ● #4、#5 | ◐ 1942–45 | ✕ | △ 1937–39 | △ ABCA 1945 | △ 戰史叢書（有版權） | **約每年一張，無敵後根據地** |
| 滿洲、蒙古（諾門罕 1939、1945-08） | ✕ | ◐ 1945 | ◐ #5 | ◐ August Storm | ✕ | ✕ | ✕ | △ | 事件級 |
| **印支、泰國** | ✕ | ◐ 概觀 | ✕ | ✕ | ✕ | ✕ | ✕ | △ | **缺口** |
| 馬來亞、荷屬東印度、菲律賓 | ✕ | ● | ✕ | ◐ Morton | ✕ | ✕ | △ | △ | 戰役級 |
| 緬甸 | ✕ | ● 3 張 | ✕ | ◐ 中緬印三冊 | ✕ | ✕ | △ | △ | 戰役級 |
| 中、西太平洋 | ✕ | ● 約 20 張 | ✕ | ◐ | ✕ | ✕ | ✕ | △ | 戰役級（島嶼控制簡單） |

**最大的缺口**（依嚴重程度排序）：
1. **中國戰區**：時間太稀，而且完全沒有「不完全控制」的資料。
2. **法屬印度支那、泰國**。
3. **東非與中東**：只有英國官方戰史，美國著作權狀態不明。
4. **巴爾幹分割佔領的內部界線、芬蘭繼續戰爭**。
5. **全戰區的靜止期**：例如中國 1940–44、東線 1942 夏以前的北段。這些時期 PD 地圖只畫「戰役」，不畫「現況」，月份之間是空的。

---

## 4. 試做建議：1940-07 法國

### 4.1 要產出的紀錄（依憲法 R6）

**控制紀錄**（時間點 1940-07-15 前後）：
1. 德國軍事佔領區（北部與大西洋沿岸）
2. 維琪直接統治區（自由區）
3. 義大利軍事佔領區（芒通一帶與阿爾卑斯邊境幾個市鎮）
4. （選做）北部兩省劃歸駐布魯塞爾的德軍軍事管理當局
5. （選做）亞爾薩斯-摩澤爾：屬於德國佔領區內的實質併入，正式行政措施從 1940-08 開始

**主權主張**：
1. 法蘭西國（維琪）對法國本土全境（含佔領區）的主張。承認方：德國、美國（直到 1942）等。
2. 自由法國：1940-07 時幾乎沒有領土。新赫布里底的歸附日期，法國國防部記為 **1940-07-18**（<https://www.defense.gouv.fr/chemins-memoire/histoire-memoires/ressources-historiques/seconde-guerre-mondiale/resister/france-libre/ralliement>），另一來源記為 **1940-07-22**（<https://theatrum-belli.com/le-bataillon-du-pacifique-une-unite-meconnue-des-forces-francaises-libres/?pdf=377747>）。這筆正好可以拿來測試憲法「時間不確定性」的處理。
3. 政權狀態變更：第三共和 → 法蘭西國，1940-07-10／11。注意 OHM 用的是 06-22／06-25，要人工修正並記錄修正原因（I5）。

### 4.2 使用的來源（附引用資訊）

| 用途 | 來源 | 引用資訊 | 授權 |
|---|---|---|---|
| 分界線的法律定義 | 《德法停戰協定》第 II 條及附件（1940-06-22 簽署） | US Dept. of State Pub. 6312, *Documents on German Foreign Policy 1918–1945*, Series D, Vol. IX, pp. 671–676 (GPO, 1956)；線上全文：<https://avalon.law.yale.edu/wwii/frgearm.asp> | 美國政府出版品，PD |
| 分界線的當時地圖（主要底圖） | Éditions André Leconte 出版，Gaston Maillet et Cie 印製，L. Guilmin 製圖，《Nouvelle carte de France par régions administratives au 1.800.000e (ligne de démarcation)》，1940-06-22～1943-03-01 間印行 | 巴黎博物館聯盟／Musée de la Libération de Paris – musée du Général Leclerc – musée Jean Moulin，館藏號 **2015.3.1.230**：<https://www.parismuseescollections.paris.fr/fr/musee-jean-moulin/oeuvres/nouvelle-carte-de-france-par-regions-administratives-au-1800000e-ligne-de>；Commons 正面：<https://commons.wikimedia.org/wiki/File:Nouvelle_carte_de_France_par_régions_administratives_au_1.800.000e_(ligne_de_démarcation),_2015.3.1.230(1).jpg> | **CC0**（館方標示） |
| 分界線幾何輔助（對照用） | Département de l'Ain，「Ligne de démarcation」資料集：依停戰協定文字與 Michelin 1:200,000 地圖建置，單一 LineString，全長約 1,219 km，範圍從庇里牛斯山到瑞士邊界，時間範圍 1940-06-22～1942-11-11 | <https://www.data.gouv.fr/datasets/ligne-de-demarcation>（GeoJSON：`https://departement-ain.opendata.arcgis.com/api/download/v1/items/73760b9eff0849f6afedc3d8b68b98ce/geojson?layers=5`） | **Licence Ouverte 2.0**（`lov2`，相容 CC BY） |
| 停戰當下德軍的最遠推進線（說明 06-25 到 07 月德軍後撤到分界線） | USMA Dept. of History, WWII European Theater atlas, **Map 15**「Campaign in the West, 1940 – The Pursuit, 13–25 June」 | `https://s3.amazonaws.com/usma-media/inline-images/academics/academic_departments/history/WWII%20Europe%20Med/WWIIEurope15.jpg`；Commons：<https://commons.wikimedia.org/wiki/File:1940FranceJune.jpg> | 美國聯邦 PD |
| 義大利進攻範圍 | 同上 Map 15（只有 06-21 的進攻箭頭與阿爾卑斯前線） | 同上 | 同上 |

### 4.3 試做時要注意的事

1. **Map 15 畫的不是分界線**。圖上的藍線是「Approximate limit of German advances by 25 June」（已親自看圖確認），範圍比分界線更南（德軍到過里昂、格勒諾布爾、波爾多以南）。德軍在 1940-07 上旬後撤到分界線以北。所以 1940-06-25 與 1940-07-15 是兩個不同的快照，正好可以測試 R6 的時間處理。
2. **Leconte 圖的限制**：
   - 比例尺 1:1,800,000，紙本只有 26×15 cm（館方記錄），這次從 Commons 取得的圖檔寬約 1920 px（原檔是否更大**未確認**）。
   - 印行時間是區間（1940–1943），可能反映後來的調整。
   - 東北部疑似有另一條紅線（禁區界線），要看高解析檔確認。
   - **沒有畫義大利佔領區**。
3. **義大利佔領區沒有找到 PD 地圖或可引用的圖號**。Commons 上只有 `{{own}}` 自繪圖，不符 R7。《法義停戰協定》（1940-06-24）全文在 Avalon 與法文維基文庫都**找不到**，需要另外查（候選：Gallica 上的官方公報，或義大利 Gazzetta Ufficiale；**未驗證**）。義大利佔領區只有十幾個市鎮，就算用市鎮清單人工標示，誤差也小，但目前**卡在來源**。
4. **Ain 資料集**不是「圖集＋圖號」型的來源。建議在資料模型裡把它定位為「輔助幾何」，主要引用仍然掛停戰協定和 Leconte 圖，並由開發者（使用者本人）決定 R7 是否接受這類政府開放資料。
5. **預估工時**：配準 Leconte 圖 1–2 小時；以 Ain 線為基礎切出佔領區與自由區多邊形 2–3 小時；義大利區（找到來源後）1–2 小時；主權主張與日期表 2 小時；來源引用與核對 2 小時。**合計大約 1.5–2 個工作天**。

---

## 5. 「全球逐月控制快照」可行性評估

### 5.1 數量

- 1937-07～1945-09 共 **99 個月**。
- 同時進行中的戰區：1937–39 只有中國（加上 1939 的歐洲），1942–44 高峰期有 8–10 個。平均每月約 5 個「戰區 × 月」單位，**總共約 500 個**。

### 5.2 單位工時（以法國試做推估）

| 情況 | 每單位工時 |
|---|---|
| 有現成 PD 圖對應該月 | 2–4 小時（配準可重複使用、描多邊形、引用、對齊相鄰戰區邊界） |
| 沒有對應圖，要從前後兩張圖判斷 | 依憲法 §9 只能標成「推估過渡」，不能當成史料快照 |
| 交界處、主權主張、雙語名稱、QA | 另加大約 30% |

### 5.3 總量

- **500 單位 × 3 小時 × 1.3 ≈ 2,000 小時**，等於一個人全職約 1 年，業餘（每週 10 小時）約 4 年。
- **更根本的問題**：以第 3 節的矩陣來看，有 PD 來源支撐的「戰區 × 月」大約只有 **25–35%**。其中西北歐 1944–45 與太平洋島嶼戰役比較密，中國、東南亞、東非、中東很稀。其餘 65–75% 的月份**依 R7 不能建立史料快照**。
- 「全球逐月」在**來源層面**就做不到，不只是人力問題。

### 5.4 判定

| 目標 | 可行性 |
|---|---|
| 主權軸，全球，精確到日 | **可行**（OHM 骨架＋人工補來源），大約 150–250 小時 |
| 控制軸，全球，逐月 | **不可行**（一人＋R7 條件下） |
| 控制軸，「有來源才有快照」的事件驅動，全球 | **可行**，大約 150–250 個快照，400–800 小時 |

### 5.5 縮小範圍的建議（供使用者拍板，AI 不代為決定）

1. **改成事件驅動快照**：快照日期等於來源圖的日期，不是固定每月。前端時間軸照樣可以逐月拖動，月份之間顯示最近的史料快照或「推估過渡」（憲法 §9 已支援）。這是**最關鍵的調整**。
2. **全球基準層改為每季**（1937-07 起約 33 個時間點），只在大型戰役期間加密（1940-05～06 西線、1941-06～12 東線、1941-12～1942-05 南方作戰、1944-06～1945-05 歐洲）。
3. **中國戰區明說限制**：只做 7–9 個 West Point／CMH 快照，「佔領區」以外一律標為「不完全控制、來源不足」，不畫根據地。日後如果取得《戰史叢書》授權或中研院資料，再補。
4. **東非、中東、印支、泰國第一階段先不畫控制，只做主權**，在介面上標「控制資料缺」。
5. **優先順序**：法國試做 → 西歐 1939–40 → 東線（West Point 14 張）→ 太平洋（West Point）→ 中國 → 其餘。前三項全部是 PD、有圖號，可以先驗證資料模型與工作流程。
6. **儘快把 West Point 的 S3 圖檔與 Wayback 目錄存到本地**。官方頁面已經 404，S3 也可能隨時下線。

---

## 6. 未驗證／待辦清單

- [ ] Esposito／Praeger 1959（A 425-010）是否有續展登記（Stanford 續展資料庫查詢無結果，可能是頁面靠 JS 載入）。
- [ ] CMH 官網的重用聲明原文（history.army.mil 對自動化請求回 403），以及 Ziemke、Romanus & Sunderland、《China Defensive》逐冊的圖目。
- [ ] LoC 12AG 系列與 1937–39 中日地圖的 Rights Advisory 原文（loc.gov 回 403，目前依據搜尋摘要）。
- [ ] 《法義停戰協定》全文的可引用來源，以及義大利佔領區的市鎮清單來源。
- [ ] JACAR 影像利用條款。
- [ ] NARA RG 242 德軍態勢圖是否已上線，以及美國著作權狀態。
- [ ] 英國官方戰史在美國的 URAA 回復狀態，以及本專案主機所在地適用哪國法律。
- [ ] Glantz《August Storm》的版權頁。

---

## 附錄 A：本次實測紀錄

- historical-basemaps：`curl https://api.github.com/repos/aourednik/historical-basemaps/contents/geojson` 列出目錄；下載 `world_1938.geojson`（254 個圖徵）與 `world_1945.geojson`（227 個圖徵），用 Python 列出 `NAME|SUBJECTO`。
- CShapes 2.0：下載 `https://icr.ethz.ch/data/cshapes/CShapes-2.0.csv`，篩選與 1937–1945 重疊的列，並對哈爾濱、維也納、布拉格、華沙、布拉提斯拉瓦、阿迪斯阿貝巴、南京、里加、史特拉斯堡、維爾紐斯、利沃夫做點在多邊形內測試。
- OHM：Overpass 查詢 `relation["boundary"="administrative"]["admin_level"="2"]["start_date"]`，取得 4,155 筆，其中 372 筆與 1937–45 重疊，42 筆帶 `source*` 標籤。
- Ain 分界線：下載 GeoJSON，確認是 1 條 LineString、2,938 個點，bbox 為 (-1.31, 43.07)–(6.08, 47.34)。
- West Point：從 Wayback 2023 版目錄頁抓出歐洲與亞洲圖集全部標題；S3 圖檔 `WWIIEurope15.jpg` 實測可下載（5101×3300），並人工看圖確認圖上藍線是「Approximate limit of German advances by 25 June」。
