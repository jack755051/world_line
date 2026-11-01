# 主權圖層試驗：歐陸 1938–1940（DRAFT，待 Tai 檢查）

## Tai 的決定（2026-10-31 04:10 台北時間，Tai 本人同意）

1. **主權圖層採事實國界**：照 OpenHistoricalMap（OHM）所畫的事實國界（含總督府、亞爾薩斯—洛林、波羅的海三國等事實併入），不改成法理國界。
2. **OHM 的空白與重疊**：有合格出處時自己補（撤回再新增，I5）；沒有出處的維持空白並標註「待查證」。補法見下方「空白與重疊修正（05-*）」。
3. **保留 17 筆含 OpenStreetMap（ODbL）來源線段的邊界**，在本發布說明標註（見「授權與署名」）。修正紀錄若由這些關係衍生，`provenance.osmDerivedWayCount` 為所有來源關係的合計，`licenseReview = osm_derived_ways`。
4. **英國屬地維持現狀**：仍是獨立政權，地圖上與英國同色。本批的英國屬地是直布羅陀、馬爾他、曼島、根西、澤西 5 個政權（指示寫 6 筆；義屬愛琴海群島另與義大利同色，不屬英國）。


分支 `feature/borders-1938-1940`。**只寫入本機開發／測試資料庫，沒有寫入正式 appdb_ww2。**

## 這批做什麼

- 新增「主權圖層」（法理國界，`sovereignty_records`），與既有的控制區圖層（`control_records`）分開。
- 幾何來自 OpenHistoricalMap（OHM）`boundary=administrative`、`admin_level=2` 的關係，逐筆釘選**關係 id＋版本＋抓取時間**。
- 以 Natural Earth 1:10m Land 裁切海岸線，再裁到歐陸試驗框（經度 −12～42、緯度 34～72）。
- 每個疆界變動都對應一個事件（`historical_events`）；事件附條約或官方文件引用。**找不到合格出處的事件不附引用，API 回 `verification = pending`，前端顯示「待查證」。不推測。**
- 地圖填色依政權（一個政權一種顏色）；陣營只在資訊卡作補充（Tai：政權優先於陣營）。

## 檔案

| 檔案 | 用途 |
|---|---|
| `build/q.txt` | Overpass 查詢：歐洲範圍內所有 admin_level=2 關係（`out meta` 取版本） |
| `build/fetch.py` | 逐筆抓關係幾何與成員線段標籤（`relation(id);out meta geom;way(r);out tags;`），記抓取時間 |
| `build/build.py` | 組多邊形（outer − inner）→ 歐陸框 → Natural Earth 陸地裁切 → 簡化 0.0005°（約 50 m）→ 精度 1e-4°；輸出 GeoJSON＋`ohm-manifest.json` |
| `build/make_requests.py` | 政權、事件、關係→政權／事件對照；產生 `requests/*.json` |
| `build/qa.py` | 每個變動日與截圖日檢查重疊與空白，輸出 `qa.json` |
| `ohm-manifest.json` | 82 筆關係的釘選清單（id、版本、changeset、時間戳、抓取時間、成員線段授權統計、OSM 來源線段數） |
| `borders-ohm-1938-1940.geojson` | 裁切後幾何（feature id＝OHM 關係 id） |
| `requests/` | 10 個來源、49 個政權、36 個事件、82 筆主權紀錄 |
| `send_seed.py` | 依序送出（預設 dry-run；拒絕送到 5051） |

重建：`python3 build/fetch.py`（需要 `sel.json` 清單）→ `python3 build/build.py`（需要 shapely、pyshp、`ne/ne_10m_land.*`）→ `python3 build/make_requests.py` → `python3 build/qa.py`。
注意：OHM 會持續被編輯，**重抓會得到不同版本**；以本批 `ohm-manifest.json` 的版本為準。

## 版本釘選

- Overpass `osm_base`：2026-10-30T19:22:26Z（台北時間 10-31 03:22）。逐筆抓取時間見 `ohm-manifest.json` 的 `fetched_at`（UTC）。
- 每筆主權紀錄存 `ohmRelationId`、`ohmVersion`、`ohmFetchedAt`、原始 `start_date`／`end_date` 字串（只有年份的日期以 1 月 1 日存入，原字串另存）。
- 幾何換版＝撤回舊紀錄後新增（I5），不原地修改。

## 授權與署名（release notes）

**OpenHistoricalMap**：整體以 **CC0 1.0** 釋出（https://www.openhistoricalmap.org/copyright）。我們仍署名：
「疆界資料：OpenHistoricalMap contributors（CC0）」。

**逐筆幾何授權**（`geometryLicense`）：成員線段帶 `license=CC BY 4.0` 標籤的關係，整筆標為 `cc_by` 並附署名；其餘標 `cc0`。
82 筆中 37 筆為 `cc_by`。需要署名的原始來源：

- © Instituto Geográfico Nacional de España（CNIG，Líneas límite municipales），CC BY 4.0 — 西班牙、葡萄牙、安道爾、法國
- © Geodetska uprava Republike Slovenije（GURS），CC BY 4.0 — 德國（1938-03 起）、奧地利、匈牙利、義大利、南斯拉夫
- © Kartverket（挪威測繪局），CC BY 4.0 — 挪威、瑞典、芬蘭
- OCHA／HDX COD-AB Ukraine（OHM 線段標示 CC BY 4.0）— 波蘭、蘇聯、德國（1939-10 起）

**海岸線**：Natural Earth 1:10m Land v5.1.1，公有領域。只用來裁切，不是疆界依據。

**OSM 來源線段（Tai 2026-10-31 決定保留並標註）**：部分線段的 `source` 標示來自 OpenStreetMap 匯入（例：Kreisgrenzen Deutschland 2005、cadastre-dgi-fr、「OSM Contributors」）。
OSM 為 ODbL，與 OHM 的 CC0 宣告可能不相容。涉及 17 筆：德國 8 筆（2693085、2704709–2704712、2704714–2704716）、捷克斯洛伐克 2692764、法國 2696299、比利時 2800293、荷蘭 2883430、比北軍政府 2748553、蘇聯 3 筆（2851157、2848248、2848241）與芬蘭 2959045 各 1 段。
每筆的數量記在 `provenance.osmDerivedWayCount`，`provenance.licenseReview = "osm_derived_ways"`。

**未採用**：CShapes（CC BY-NC-SA，非商用）只作內部比對，不入庫；Cliopatria 本批未用。

## 疆界變動事件與出處

| 事件 | 日期 | 內容 | 狀態 | 出處（locator） |
|---|---|---|---|---|
| EV_ANSCHLUSS | 1938-03-13 | 德奧合併：《奧地利與德意志國重新統一法》 | 已查證 | SRC_FRUS_1938_I Doc. 454, p. 438；SRC_FRUS_1938_I Doc. 457, p. 441 |
| EV_MUNICH | 1938-09-29 | 慕尼黑協定：蘇台德地區割予德國（1938-09-29 夜簽、09-30 凌晨簽字日期） | 已查證 | SRC_FRUS_1938_I Doc. 682, p. 702 |
| EV_ZAOLZIE | 1938-10-02 | 波蘭取得切申（Zaolzie）等地（OHM 變動日 1938-11-01） | **待查證** | — |
| EV_VIENNA1 | 1938-11-02 | 第一次維也納仲裁：斯洛伐克南部與喀爾巴阡烏克蘭南部劃歸匈牙利 | 已查證 | SRC_DGFP_D4_GPO Doc. 99, pp. 118–126（仲裁本文 pp. 125–126） |
| EV_DE_CS_BORDER_1938 | 1938-11-20 | 德捷邊界最終劃定（OHM 變動日 1938-11-21） | **待查證** | — |
| EV_SLOVAK_INDEP | 1939-03-14 | 斯洛伐克宣布獨立（斯洛伐克國成立） | 已查證 | SRC_FRUS_1939_I Doc. 58, pp. 60–61 |
| EV_CARPATHO | 1939-03-14 | 匈牙利佔領並併入喀爾巴阡烏克蘭 | 已查證 | SRC_DGFP_D4_GPO Doc. 236, p. 275；SRC_DGFP_D4_GPO Doc. 237, p. 276 |
| EV_PROTECTORATE | 1939-03-15 | 捷克斯洛伐克解體：希特勒—哈卡會談與波希米亞—摩拉維亞保護國成立 | 已查證 | SRC_DGFP_D4_GPO Doc. 228, p. 263；SRC_DGFP_D4_GPO Doc. 229, p. 270；SRC_DGFP_D4_GPO Doc. 246, p. 283 |
| EV_MEMEL | 1939-03-22 | 立陶宛將梅梅爾（克萊佩達）地區割予德國 | 已查證 | SRC_FRUS_1939_I Doc. 81, pp. 87–88；SRC_FRUS_1939_I Doc. 80, p. 87 |
| EV_HU_SK_1939 | 1939-03-23 | 匈斯邊界衝突後匈牙利取得斯洛伐克東部一帶（OHM 變動日 1939-04-04） | **待查證** | — |
| EV_ALBANIA | 1939-04-07 | 義大利入侵並兼領阿爾巴尼亞（04-12 制憲會議獻冠、04-16 義王接受） | 已查證 | SRC_FRUS_1939_II Doc. 363, pp. 410–411；SRC_FRUS_1939_II Doc. 357, pp. 403–404 |
| EV_SPAIN_1939 | 1939-04-01 | 西班牙內戰結束，國民軍政權統治全境（OHM 政權替換日 1939-04-01） | **待查證** | — |
| EV_HATAY | 1939-06-23 | 哈塔伊（亞歷山大勒塔）併入土耳其（OHM 變動日 1939-06-29） | **待查證** | — |
| EV_DANZIG | 1939-09-01 | 但澤自由市併入德國（OHM 但澤止於 1939-09-01） | **待查證** | — |
| EV_POLAND_PARTITION | 1939-09-28 | 波蘭被瓜分：德蘇邊界暨友好條約 | 已查證 | SRC_DGFP_D8_GPO Doc. 157, pp. 164–165；SRC_FRUS_1939_I Doc. 514, p. 495（編者註） |
| EV_DE_EASTERN_DECREE | 1939-10-08 | 德國以元首命令併入波蘭西部（1939-10-08 公布、10-26 生效；OHM 變動日 1939-10-26） | **待查證** | — |
| EV_VILNIUS | 1939-10-10 | 蘇聯依蘇立互助條約將維爾紐斯地區交予立陶宛（OHM 變動日 1939-10-28） | 已查證 | SRC_FRUS_1939_I Doc. 1063, pp. 968–970 |
| EV_SK_POLISH_AREAS | 1939-11-21 | 斯洛伐克取得原波蘭北部邊境地區（OHM 變動日 1939-11-21） | **待查證** | — |
| EV_MOSCOW_PEACE | 1940-03-12 | 蘇芬《莫斯科和約》：芬蘭割讓卡累利阿地峽等地 | 已查證 | SRC_FRUS_1940_I Doc. 287, pp. 314–317；SRC_FRUS_1940_I Doc. 286, p. 314 |
| EV_EUPEN | 1940-05-18 | 德國併入奧伊彭—馬爾梅迪（OHM 變動日 1940-05-18） | **待查證** | — |
| EV_DE_19400601 | 1940-06-01 | OHM 德國國界版本變動（1940-06-01，內容待查） | **待查證** | — |
| EV_ARMISTICE_FR_DE | 1940-06-22 | 德法停戰協定（貢比涅；1940-06-25 生效） | 已查證 | SRC_DGFP_D9 pp. 671–676，德法停戰協定第 III、X 條 |
| EV_ARMISTICE_FR_IT | 1940-06-24 | 法義停戰協定（羅馬） | 已查證 | SRC_FRUS_1940_III Doc. 837, p. 909（註腳） |
| EV_BE_MILADMIN | 1940-05-28 | 比利時投降後由德國軍政府管轄（OHM 比利時止於 1940-06-25） | **待查證** | — |
| EV_LV_OCCUPATION | 1940-06-16 | 蘇聯最後通牒與進駐拉脫維亞（OHM 拉脫維亞止於 1940-06-16） | **待查證** | — |
| EV_BESSARABIA | 1940-06-26 | 蘇聯最後通牒，羅馬尼亞割讓比薩拉比亞與北布科維納 | 已查證 | SRC_FRUS_1940_I Doc. 501, pp. 479–480；SRC_FRUS_1940_I Doc. 502, pp. 480–481；SRC_FRUS_1940_I Doc. 506, pp. 484–485 |
| EV_LT_SSR | 1940-07-21 | 立陶宛「人民議會」宣布蘇維埃制度並請求加入蘇聯 | 已查證 | SRC_FRUS_1940_I Doc. 417, p. 404 |
| EV_LV_SSR | 1940-07-21 | 拉脫維亞議會宣布蘇維埃制度（OHM 拉脫維亞蘇維埃共和國始於 1940-07-21） | **待查證** | — |
| EV_EE_SSR | 1940-07-21 | 愛沙尼亞議會宣布蘇維埃制度並決議加入蘇聯 | 已查證 | SRC_FRUS_1940_I Doc. 408, p. 399；SRC_FRUS_1940_I Doc. 410, p. 400 |
| EV_LUX_CDZ | 1940-07-29 | 盧森堡改由德國民政長官管轄（OHM 盧森堡止於 1940-07-29） | **待查證** | — |
| EV_CDZ_ANNEX | 1940-08-02 | 亞爾薩斯、洛林、盧森堡事實併入德國（OHM 變動日 1940-08-02；無國際承認的法理割讓） | **待查證** | — |
| EV_LT_ADMITTED | 1940-08-03 | 蘇聯最高蘇維埃接納立陶宛蘇維埃共和國加入蘇聯 | 已查證 | SRC_FRUS_1940_I Doc. 421, p. 406；SRC_FRUS_1940_I Doc. 412, pp. 401–402 |
| EV_LV_ADMITTED | 1940-08-05 | 蘇聯接納拉脫維亞蘇維埃共和國加入蘇聯 | 已查證 | SRC_FRUS_1940_I Doc. 425, pp. 409–410；SRC_FRUS_1940_I Doc. 412, pp. 401–402 |
| EV_EE_ADMITTED | 1940-08-06 | 蘇聯接納愛沙尼亞蘇維埃共和國加入蘇聯 | 已查證 | SRC_FRUS_1940_I Doc. 421, p. 406（註腳）；SRC_FRUS_1940_I Doc. 412, pp. 401–402 |
| EV_VIENNA2 | 1940-08-30 | 第二次維也納仲裁：北特蘭西瓦尼亞劃歸匈牙利 | 已查證 | SRC_FRUS_1940_I Doc. 529, pp. 501–502；SRC_FRUS_1940_I Doc. 530, pp. 502–503 |
| EV_CRAIOVA | 1940-09-07 | 克拉約瓦條約：羅馬尼亞將南多布羅加割予保加利亞 | 已查證 | SRC_FRUS_1940_I Doc. 535, p. 506 |
| EV_SUDETEN_OCCUPATION | 1938-10-01 → 10-10 | 德軍依慕尼黑協定分區佔領蘇台德（10-10 大致完成）【05 修正】 | 已查證 | SRC_FRUS_1938_I Doc. 682, p. 702；Doc. 700, pp. 721–722；Doc. 710, pp. 734、735 |
| EV_DANZIG_ANNEX | 1939-09-01 | 但澤自由市宣布併入德國（佛斯特宣言）【05 修正；取代待查證的 EV_DANZIG】 | 已查證 | SRC_FRUS_1939_I Doc. 402, p. 402；Doc. 403, pp. 402–403 |
| EV_GG_CIVIL_ADMIN_R2 | 1939-10-25 | 德佔波蘭軍事管理結束、法蘭克就任總督（OHM 變動日 10-26）【05 修正】 | 已查證 | SRC_DGFP_D8_GPO Doc. 477, p. 560，編者註 2–3 |

出處說明：FRUS 依 HistoryAtState/frus TEI（`<pb>` 頁碼）逐頁核對；DGFP D/IV（GPO 1951，Department of State Publication 3883）、D/VIII（GPO 1954）依 archive.org OCR 核對；
DGFP D/IX 停戰協定 locator 沿用 fr-uk-1940 已審 seed。美國聯邦政府出版品，`us_federal_pd`。

## 關係 → 政權 → 起訖事件

| OHM 關係 | 版本 | 政權 slug | OHM 期間 | 幾何授權 | OSM 來源線段 | 起事件 | 迄事件 |
|---|---|---|---|---|---|---|---|
| 2739874 | v11 | principality-of-andorra | 1278 → （無） | cc_by |  |  |  |
| 2800554 | v26 | albanian-kingdom | 1928-09-01 → 1939-04-12 | cc0 |  |  | EV_ALBANIA |
| 2855615 | v8 | albania-under-italy | 1939-04-12 → 1941-06-07 | cc0 |  | EV_ALBANIA |  |
| 2858751 | v5 | federal-state-of-austria | 1922-10-01 → 1938-03-13 | cc_by |  |  | EV_ANSCHLUSS |
| 2800293 | v50 | kingdom-of-belgium | 1920-01-10 → 1940-06-25 | cc0 | 3 |  | EV_BE_MILADMIN |
| 2848878 | v18 | tsardom-of-bulgaria | 1919-11-27 → 1940-09-07 | cc0 |  |  | EV_CRAIOVA |
| 2855603 | v12 | tsardom-of-bulgaria | 1940-09-07 → 1941-04-30 | cc0 |  | EV_CRAIOVA |  |
| 2798802 | v31 | swiss-confederation | 1874-09-23 → 1967-10-03 | cc0 |  |  |  |
| 2692764 | v97 | czechoslovak-republic | 1936-07-03 → 1938-09-30 | cc0 | 176 |  | EV_MUNICH |
| 2747874 | v53 | czechoslovak-republic | 1938-09-30 → 1938-11-02 | cc0 |  | EV_MUNICH | EV_VIENNA1 |
| 2857482 | v25 | czechoslovak-republic | 1938-11-02 → 1939-03-14 | cc0 |  | EV_VIENNA1 | EV_SLOVAK_INDEP |
| 2691478 | v25 | free-city-of-danzig | 1920-12-24 → 1939-09-01 | cc0 |  |  | EV_DANZIG |
| 2693085 | v290 | deutsches-reich | 1936-07-03 → 1938-03-13 | cc0 | 232 |  | EV_ANSCHLUSS |
| 2704712 | v208 | deutsches-reich | 1938-03-13 → 1938-11-21 | cc_by | 232 | EV_ANSCHLUSS | EV_DE_CS_BORDER_1938 |
| 2704711 | v199 | deutsches-reich | 1938-11-21 → 1939-03-16 | cc_by | 56 | EV_DE_CS_BORDER_1938 | EV_PROTECTORATE |
| 2704710 | v193 | deutsches-reich | 1939-03-16 → 1939-03-22 | cc_by | 56 | EV_PROTECTORATE | EV_MEMEL |
| 2704709 | v195 | deutsches-reich | 1939-03-22 → 1939-10-26 | cc_by | 56 | EV_MEMEL | EV_DE_EASTERN_DECREE |
| 2704716 | v194 | deutsches-reich | 1939-10-26 → 1940-05-18 | cc_by | 56 | EV_DE_EASTERN_DECREE | EV_EUPEN |
| 2704715 | v190 | deutsches-reich | 1940-05-18 → 1940-06-01 | cc_by | 56 | EV_EUPEN | EV_DE_19400601 |
| 2704714 | v190 | deutsches-reich | 1940-06-01 → 1940-08-02 | cc_by | 56 | EV_DE_19400601 | EV_CDZ_ANNEX |
| 2704713 | v191 | deutsches-reich | 1940-08-02 → 1941-04-14 | cc_by |  | EV_CDZ_ANNEX |  |
| 2869937 | v15 | kingdom-of-denmark | 1932-01-30 → 1944-06-17 | cc0 |  |  |  |
| 2801387 | v30 | republic-of-estonia | 1918-02-24 → 1940-07-21 | cc0 |  |  | EV_EE_SSR |
| 2694790 | v29 | estonian-ssr | 1940-07-21 → 1940-08-06 | cc0 |  | EV_EE_SSR | EV_EE_ADMITTED |
| 2860484 | v25 | spanish-republic | 1931 → 1939-04-01 | cc_by |  |  | EV_SPAIN_1939 |
| 2862761 | v19 | spanish-state | 1939-04-01 → 1956-04-07 | cc_by |  | EV_SPAIN_1939 |  |
| 2959045 | v9 | republic-of-finland | 1920-10-14 → 1940-03-12 | cc_by | 1 |  | EV_MOSCOW_PEACE |
| 2692833 | v29 | republic-of-finland | 1940-03-12 → 1944-09-19 | cc_by |  | EV_MOSCOW_PEACE |  |
| 2696299 | v155 | french-third-republic | 1918-11-22 → 1940-06-22 | cc_by | 58 |  | EV_ARMISTICE_FR_DE |
| 2747868 | v94 | french-state-vichy | 1940-06-25 → 1942-11-11 | cc_by |  | EV_ARMISTICE_FR_DE |  |
| 2828270 | v5 | bailiwick-of-guernsey | 1290 → 1987-05-14 | cc0 |  |  |  |
| 2692855 | v5 | gibraltar-crown-colony | 1713 → （無） | cc0 |  |  |  |
| 2873762 | v14 | kingdom-of-greece | 1936-09-17 → 1941-04-30 | cc0 |  |  |  |
| 2695633 | v49 | kingdom-of-hungary | 1921-11-10 → 1938-11-02 | cc_by |  |  | EV_VIENNA1 |
| 2747873 | v27 | kingdom-of-hungary | 1938-11-02 → 1939-03-14 | cc_by |  | EV_VIENNA1 | EV_CARPATHO |
| 2747872 | v38 | kingdom-of-hungary | 1939-03-14 → 1939-04-04 | cc_by |  | EV_CARPATHO | EV_HU_SK_1939 |
| 2747871 | v37 | kingdom-of-hungary | 1939-04-04 → 1940-08-30 | cc_by |  | EV_HU_SK_1939 | EV_VIENNA2 |
| 2747817 | v41 | kingdom-of-hungary | 1940-08-30 → 1941-12-14 | cc_by |  | EV_VIENNA2 |  |
| 2692985 | v26 | ireland-eire | 1937-12-29 → 2006-04-04 | cc0 |  |  |  |
| 2693293 | v13 | isle-of-man | 1333-08-09 → 1987-05-15 | cc0 |  |  |  |
| 2851104 | v65 | kingdom-of-italy | 1929-06-07 → 1940-06-24 | cc_by |  |  | EV_ARMISTICE_FR_IT |
| 2696324 | v127 | kingdom-of-italy | 1940-06-24 → 1941-04-18 | cc_by |  | EV_ARMISTICE_FR_IT |  |
| 2920371 | v2 | italian-aegean-islands | 1921 → 1943-09-11 | cc0 |  |  |  |
| 2828299 | v4 | bailiwick-of-jersey | 1290 → 1987-05-14 | cc0 |  |  |  |
| 2746467 | v5 | principality-of-liechtenstein | 1806-07-12 → 1960-03-17 | cc0 |  |  |  |
| 2692218 | v53 | republic-of-lithuania | 1923-01-19 → 1939-03-23 | cc0 |  |  | EV_MEMEL |
| 2855606 | v12 | republic-of-lithuania | 1939-03-23 → 1939-10-28 | cc0 |  | EV_MEMEL | EV_VILNIUS |
| 2848250 | v17 | republic-of-lithuania | 1939-10-28 → 1940-08-03 | cc0 |  | EV_VILNIUS | EV_LT_ADMITTED |
| 2694785 | v38 | lithuanian-ssr | 1940-07-21 → 1940-08-04 | cc0 |  | EV_LT_SSR | EV_LT_ADMITTED |
| 2748545 | v31 | grand-duchy-of-luxembourg | 1840-09-12 → 1940-07-29 | cc0 |  |  | EV_LUX_CDZ |
| 2704702 | v61 | republic-of-latvia | 1920-01-01 → 1940-06-16 | cc0 |  |  | EV_LV_OCCUPATION |
| 2694787 | v55 | latvian-ssr | 1940-07-21 → 1940-08-04 | cc0 |  | EV_LV_SSR | EV_LV_ADMITTED |
| 2693418 | v10 | principality-of-monaco | 1861-02-02 → 1942-11-11 | cc0 |  |  |  |
| 2748553 | v33 | mil-admin-belgium-northern-france | 1940-06-25 → 1944-07-18 | cc0 | 1 | EV_BE_MILADMIN |  |
| 2801185 | v6 | malta-crown-colony | 1814-05-30 → 1964-09-21 | cc0 |  |  |  |
| 2883430 | v24 | kingdom-of-the-netherlands | 1848-10-14 → 1949-04-23 | cc0 | 3 |  |  |
| 2851798 | v15 | kingdom-of-norway | 1925-08-14 → 2004 | cc_by |  |  |  |
| 2692205 | v214 | polish-republic | 1924-06-22 → 1938-11-01 | cc_by |  |  | EV_ZAOLZIE |
| 2741574 | v118 | polish-republic | 1938-11-01 → 1939-10-06 | cc_by |  | EV_ZAOLZIE | EV_POLAND_PARTITION |
| 2807009 | v14 | portuguese-republic | 1910 → 1951-06-11 | cc_by |  |  |  |
| 2693259 | v71 | kingdom-of-romania | 1921 → 1940-06-28 | cc0 |  |  | EV_BESSARABIA |
| 2693258 | v55 | kingdom-of-romania | 1940-06-28 → 1940-08-30 | cc0 |  | EV_BESSARABIA | EV_VIENNA2 |
| 2693257 | v58 | kingdom-of-romania | 1940-08-30 → 1940-09-07 | cc0 |  | EV_VIENNA2 | EV_CRAIOVA |
| 2693256 | v65 | kingdom-of-romania | 1940-09-07 → 1941-08-19 | cc0 |  | EV_CRAIOVA |  |
| 2870046 | v9 | kingdom-of-sweden | 1932-01-30 → 1979-07-01 | cc_by |  |  |  |
| 2692769 | v47 | slovak-state-1939 | 1939-03-14 → 1939-04-04 | cc0 |  | EV_SLOVAK_INDEP | EV_HU_SK_1939 |
| 2692768 | v47 | slovak-state-1939 | 1939-04-04 → 1939-11-21 | cc0 |  | EV_HU_SK_1939 | EV_SK_POLISH_AREAS |
| 2747847 | v36 | slovak-state-1939 | 1939-11-21 → 1945-04-04 | cc0 |  | EV_SK_POLISH_AREAS |  |
| 2853735 | v9 | republic-of-san-marino | 1740-02-05 → （無） | cc0 |  |  |  |
| 2851157 | v93 | soviet-union | 1926 → 1939-10-06 | cc_by | 1 |  | EV_POLAND_PARTITION |
| 2848248 | v96 | soviet-union | 1939-10-06 → 1939-10-28 | cc_by | 1 | EV_POLAND_PARTITION | EV_VILNIUS |
| 2848241 | v100 | soviet-union | 1939-10-28 → 1940-03-12 | cc_by | 1 | EV_VILNIUS | EV_MOSCOW_PEACE |
| 2851878 | v86 | soviet-union | 1940-03-12 → 1940-06-28 | cc_by |  | EV_MOSCOW_PEACE | EV_BESSARABIA |
| 2848258 | v98 | soviet-union | 1940-06-28 → 1940-08-03 | cc_by |  | EV_BESSARABIA | EV_LT_ADMITTED |
| 2848256 | v101 | soviet-union | 1940-08-03 → 1940-08-05 | cc_by |  | EV_LT_ADMITTED | EV_LV_ADMITTED |
| 2848811 | v98 | soviet-union | 1940-08-05 → 1940-08-06 | cc_by |  | EV_LV_ADMITTED | EV_EE_ADMITTED |
| 2848812 | v98 | soviet-union | 1940-08-06 → 1941-07-17 | cc_by |  | EV_EE_ADMITTED |  |
| 2801012 | v40 | republic-of-turkey | 1924-08-06 → 1939-06-29 | cc0 |  |  | EV_HATAY |
| 2864004 | v20 | republic-of-turkey | 1939-06-29 → 1964-05-15 | cc0 |  | EV_HATAY |  |
| 2693292 | v51 | united-kingdom | 1922-12-05 → 1987-05-15 | cc0 |  |  |  |
| 2751259 | v6 | vatican-city-state | 1929-02-11 → （無） | cc0 |  |  |  |
| 2747831 | v50 | kingdom-of-yugoslavia | 1929-10-03 → 1941-04-06 | cc_by |  |  |  |

## QA：OHM 資料本身的空白與重疊（修正前；修正見下一節）

`qa.json` 全表。重點：

| 期間 | 問題 |
|---|---|
| 1938-09-30 → 11-21 | 蘇台德空白：OHM 捷克斯洛伐克 09-30 縮小，但德國到 11-21 才擴大 |
| 1939-03-14 → 03-16 | 波希米亞—摩拉維亞空白兩天 |
| 1939-03-22（一天） | 梅梅爾同時屬於德國與立陶宛 |
| 1939-09-01 → 10-26 | 但澤空白 |
| 1939-10-06 → 10-26 | 波蘭中部（總督府區）空白 24 平方度 |
| 1939-10-26 起 | OHM 德國關係 2704716 起**把總督府畫進德國國界**；法理上總督府未被併入（待 Tai 決定） |
| 1939-10-26 → 1940-06-16 | 拉脫維亞—白俄羅斯—立陶宛交界小塊空白（0.11 平方度） |
| 1940-03-12 → 06-28 | **比薩拉比亞重疊**：OHM 蘇聯 2851878 已含比薩拉比亞（OHM 錯誤） |
| 1940-05-18 → 06-25 | 奧伊彭—馬爾梅迪同時屬於德國與比利時 |
| 1940-06-16 → 07-21 | 拉脫維亞空白（OHM 拉脫維亞止於 06-16） |
| 1940-06-22 → 06-25 | 法國（含阿爾及利亞北部、科西嘉）空白三天 |
| 1940-06-25 → 08-02 | 亞爾薩斯—洛林空白 |
| 1940-07-21 → 08-04 | 立陶宛蘇維埃共和國與立陶宛（→ 08-03）、蘇聯（08-03）重疊 |

截圖日受影響：1938-10-15（蘇台德空白）、1939-10-15（波蘭中部、但澤空白）。

## 空白與重疊修正（05-*，2026-10-31）

`build/fixes.py` 產生 `borders-fixes-1938-1940.geojson`（衍生幾何，feature id＝`FIX_*`）與 `requests/05-*.json`：
`05-1-*` 新事件（附出處）與新政權 → `05-2-*` 撤回原紀錄 → `05-3-*` 重新新增。衍生幾何只用本批已釘版的 OHM 幾何做集合運算，不手繪。
公式：補上的範圍＝（後一版國界 ∩ 前一版擁有者）−當日其他有效紀錄。

| 問題 | 處理 | 新紀錄 | 出處 |
|---|---|---|---|
| 蘇台德空白 1938-09-30 → 11-21 | 德國自 **1938-10-10**（佔領大致完成）起含蘇台德：`2704712 ∪ ((2704711 ∩ 2692764) − 10-15 其他紀錄)`。原 SOV_R2704712 撤回，拆成 03-13→10-10（原幾何）與 10-10→11-21（含蘇台德） | SOV_R2704712_A、SOV_FIX_REICH_SUDETEN；事件 EV_SUDETEN_OCCUPATION | FRUS 1938 I Doc. 682, p. 702；Doc. 700, pp. 721–722；Doc. 710, pp. 734、735 |
| 蘇台德 **10-01 → 10-10** | **維持空白、待查證**：分五區逐步佔領，本批沒有分區幾何 | — | — |
| 但澤空白 1939-09-01 → 10-26 | 德國自 **1939-09-01** 起含但澤：`2704709 ∪ 2691478`。原 SOV_R2704709 撤回拆成兩筆；但澤自由市紀錄撤回重加，迄事件改為已查證的 EV_DANZIG_ANNEX | SOV_R2704709_A、SOV_FIX_REICH_DANZIG、SOV_R2691478_B；事件 EV_DANZIG_ANNEX | FRUS 1939 I Doc. 402, p. 402；Doc. 403, pp. 402–403 |
| 波蘭中部空白 1939-10-06 → 10-26 | 新政權「德佔波蘭軍事管理（Oberbefehlshaber Ost）」，**非主權**（斜線）：`(2741574 ∩ 2704716) − 10-15 其他紀錄 − 2691478` | SOV_FIX_MILVERW_PL_R2；政權 REGIME_MILVERW_PL；事件 EV_GG_CIVIL_ADMIN_R2 | 分界線：DGFP D/VIII Doc. 157, pp. 164–165（德蘇邊界暨友好條約）；軍事管理與 10-25 法蘭克就任：DGFP D/VIII Doc. 477, p. 560 編者註 2–3 |
| 比薩拉比亞重疊 1940-03-12 → 06-28 | OHM 蘇聯 2851878 v86 誤含比薩拉比亞與北布科維納：撤回後以 `2851878 − 2693259`（扣羅馬尼亞）重加 | SOV_FIX_SU_NO_BESSARABIA | 蘇聯 1940-06-26 才以最後通牒要求割讓：FRUS 1940 I Docs. 501、502、506（EV_BESSARABIA） |

**頁碼更正（05-4-*）**：EV_GG_CIVIL_ADMIN（05-1-03）原寫 Doc. 477 **p. 561**，核對 OCR 頁首後編者註實在 **p. 560**。事件沒有撤回端點，所以新增更正事件 EV_GG_CIVIL_ADMIN_R2，
撤回 SOV_FIX_MILVERW_PL 後以 SOV_FIX_MILVERW_PL_R2 重加（幾何、期間不變）。舊事件 EV_GG_CIVIL_ADMIN 留在庫中但已無紀錄引用。

修正後 QA（`build/fixes.py` 輸出；重疊門檻 0.005 平方度、空白門檻 0.05 平方度）：

| 日期 | 重疊 | 空白 |
|---|---|---|
| 1938-10-05 | 無 | 蘇台德 2.301、1.131、0.305（10-01～10-10 分區佔領，待查證） |
| 1938-10-15 | 無 | 0.109（切申／Zaolzie，波蘭 1938-11-01 才含；EV_ZAOLZIE 待查證） |
| 1939-09-15 | 無 | 無 |
| 1939-10-15 | 無 | 0.113（拉脫維亞—白俄羅斯—立陶宛交界，OHM 細縫，未修） |
| 1940-04-01 | 無 | 0.113（同上） |
| 1940-06-27 | 無 | 拉脫維亞 9.766（06-16→07-21）、亞爾薩斯—洛林 1.78（06-25→08-02）：未在本輪範圍，維持空白 |

未處理（仍待查證，維持 OHM 原樣）：梅梅爾 1939-03-22 一天重疊、波希米亞—摩拉維亞 03-14→03-16 空白、奧伊彭—馬爾梅迪 1940-05-18→06-25 重疊、法國 06-22→06-25 空白、
立陶宛蘇維埃共和國 07-21→08-04 重疊、拉脫維亞 06-16→07-21 空白、亞爾薩斯—洛林 06-25→08-02 空白、切申 1938-09-30→11-01 空白。

## （已決定）原「需要 Tai 決定」清單

1. **法理 vs. OHM 的事實併入**：總督府、亞爾薩斯—洛林—盧森堡（1940-08-02 起）、波羅的海三國（美國不承認）、芒通（義佔）在 OHM 都畫進併入國。主權圖層要照 OHM、還是改成法理（需另找來源）？
2. **非主權實體**：「比利時與北法軍政府」在 OHM 是 admin_level 2。本批標 `not_sovereign`、斜線顯示；也可以不顯示（比利時會空白）。
3. **OSM（ODbL）來源線段**是否可接受；不接受就要換掉德、捷、法、比、荷的幾何。
4. **空白與重疊**：等 OHM 修，還是我們自己補（補要有來源）？
5. **待查證事件**（15 個）要不要繼續找出處（FRUS 1939 vol. IV 近東、DGFP D/VI、D/X 等尚未下載）。
6. 英國屬地（直布羅陀、馬爾他、曼島、根西、澤西）目前是獨立政權、與英國同色；是否併入英國。
