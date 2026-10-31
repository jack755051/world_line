# WW1 第一批：1908-10-06 波士尼亞併吞 → 1914-07-28 奧匈對塞爾維亞宣戰（DRAFT，待 Tai 檢查）

範圍：歐洲、北非、近東（OHM 裁切框 -20,15～60,72）。期間半開區間 [1908-10-06, 1914-07-29)；1914-07-29 是本批試驗期間終點，不是政權迄日（無迄事件）。
**只寫入本機開發庫**（worldline-borders-dev，API 127.0.0.1:5052，DB 5442）；寫入 appdb_ww2（5051）要另取得 Tai 同意。

## 檔案

| 檔案 | 說明 |
|---|---|
| `build/fetch.py` | 依 relation id 從 OHM Overpass 抓 60 筆關係（`out meta geom`＋成員線段 tags），存 `raw/`（不進版控） |
| `build/build.py` | 組多邊形 → 框裁切 → Natural Earth 10m 陸地裁切 → 簡化（約 50 m）→ `borders-ohm-ww1-1.geojson`＋`ohm-manifest.json` |
| `build/make_requests.py` | 組合幾何（鄂圖曼分段、倫敦割讓區、摩洛哥、西班牙）、QA、產生 `requests/*.json`、`ww1-1908-1914-derived.geojson`、`qa.json` |
| `ohm-manifest.json` | 釘選清單：id、版本、changeset、時間戳、抓取時間（UTC）、成員線段授權統計、OSM 來源線段數 |
| `send_seed.py` | 依序送出（預設 dry-run；拒絕 5051；API key 從 --env 安靜讀取） |
| `db-export/`（不進版控） | 開發庫唯讀匯出：本期間已有的主權紀錄（QA 與葡萄牙修正用），備份在 `~/01_Projects/world_line_backups/` |

用法：
```
python3 send_seed.py --base http://127.0.0.1:5052 --env ../../../../.env.borders-dev --prior ../../../../.dev/sent-ids.borders-dev.json --ids ../../../../.dev/sent-ids.ww1-balkans-1908-1914-dev.json [--send]
```

OHM Overpass `osm_base`：2026-10-31T16:11:17Z（UTC）。

## 主權紀錄（45 筆，另撤回 1 筆）

| placeholder | 政權 | 期間 | 層級 | 幾何 | 授權 | OSM 線段 | 起事件 | 迄事件 |
|---|---|---|---|---|---|---|---|---|
| SOV_AH | REGIME_AH | 1908-10-06～1914-07-29 | de_jure | relation/2692361 v267 | cc_by | 176 | EV_BOSNIA | — |
| SOV_DE_EMP | REGIME_DE_EMP | 1908-10-06～1914-07-29 | de_jure | relation/2692425 v259 | cc0 | 176 | — | — |
| SOV_RU_EMP | REGIME_RU_EMP | 1908-10-06～1914-07-29 | de_jure | relation/2849760 v126 | cc_by | 0 | — | — |
| SOV_IT | REGIME_IT | 1908-10-06～1914-07-29 | de_jure | relation/2696424 v118 | cc_by | 0 | — | — |
| SOV_FR3 | REGIME_FR3 | 1908-10-06～1914-07-29 | de_jure | relation/2866012 v31 | cc_by | 2 | — | — |
| SOV_UK_GBI | REGIME_UK_GBI | 1908-10-06～1914-07-29 | de_jure | relation/2828388 v26 | cc0 | 0 | — | — |
| SOV_BE | REGIME_BE | 1908-10-06～1914-07-29 | de_jure | relation/2797729 v43 | cc0 | 3 | — | — |
| SOV_DK | REGIME_DK | 1908-10-06～1914-07-29 | de_jure | relation/2869935 v14 | cc0 | 0 | — | — |
| SOV_NO | REGIME_NO | 1908-10-06～1914-07-29 | de_jure | relation/2692537 v28 | cc_by | 0 | — | — |
| SOV_SE | REGIME_SE | 1908-10-06～1914-07-29 | de_jure | relation/2692524 v33 | cc_by | 0 | — | — |
| SOV_MORESNET | REGIME_MORESNET | 1908-10-06～1914-07-29 | de_jure | relation/2696520 v6 | cc0 | 0 | — | — |
| SOV_TN | REGIME_TN | 1908-10-06～1914-07-29 | de_jure | relation/2690947 v20 | cc0 | 0 | — | — |
| SOV_MR | REGIME_MR | 1912-01-01～1914-07-29 | de_jure | relation/2917211 v3 | cc0 | 0 | — | — |
| SOV_CY | REGIME_CY_BR | 1908-10-06～1914-07-29 | not_sovereign | relation/2848136 v6 | cc0 | 0 | — | — |
| SOV_CRETE | REGIME_CRETE | 1908-10-06～1913-08-10 | not_sovereign | relation/2692586 v8 | cc0 | 0 | — | EV_BUCHAREST |
| SOV_OT_A | REGIME_OT | 1908-10-06～1912-04-27 | de_jure | relation/2746682 v88 ∪ 利比亞（relation/2690837 v18 ∪ relation/2803190 v11） | cc0 | 0 | — | EV_DODECANESE |
| SOV_OT_B | REGIME_OT | 1912-04-27～1912-10-18 | de_jure | (relation/2746682 v88 − relation/2830316 v10) ∪ 利比亞（relation/2690837 v18 ∪ relation/2803190 v11） | cc0 | 0 | EV_DODECANESE | EV_OUCHY |
| SOV_OT_C | REGIME_OT | 1912-10-18～1912-11-28 | de_jure | relation/2746682 v88 − relation/2830316 v10 | cc0 | 0 | EV_OUCHY | EV_AL_INDEP |
| SOV_OT_D | REGIME_OT | 1912-11-28～1913-05-30 | de_jure | relation/2746682 v88 − relation/2830316 v10 − relation/2807008 v25 | cc0 | 0 | EV_AL_INDEP | EV_LONDON |
| SOV_OT_E | REGIME_OT | 1913-05-30～1914-07-29 | de_jure | relation/2849728 v55 − relation/2848136 v6 − relation/2830316 v10 − 阿爾巴尼亞 | cc0 | 0 | EV_LONDON | — |
| SOV_LONDON | REGIME_LONDON | 1913-05-30～1913-08-10 | not_sovereign | relation/2746682 v88 − relation/2849728 v55 − 多德卡尼斯 − 阿爾巴尼亞 − 克里特 − 塞、希、保、蒙、羅當期範圍 | cc0 | 0 | EV_LONDON | EV_BUCHAREST |
| SOV_GR_A | REGIME_GR | 1908-10-06～1913-08-10 | de_jure | relation/2692556 v29 | cc0 | 0 | — | EV_BUCHAREST |
| SOV_GR_B | REGIME_GR | 1913-08-10～1914-07-29 | de_jure | relation/2692585 v40 | cc0 | 0 | EV_BUCHAREST | — |
| SOV_RS_A | REGIME_RS | 1908-10-06～1913-08-10 | de_jure | relation/2692716 v47 | cc0 | 0 | — | EV_BUCHAREST |
| SOV_RS_B | REGIME_RS | 1913-08-10～1914-07-29 | de_jure | relation/2746681 v36 | cc0 | 0 | EV_BUCHAREST | — |
| SOV_MN_P | REGIME_MN_P | 1908-10-06～1910-08-28 | de_jure | relation/2692715 v22 | cc0 | 0 | — | EV_MN_KINGDOM |
| SOV_MN_K_A | REGIME_MN_K | 1910-08-28～1913-05-30 | de_jure | relation/2958264 v1 | cc0 | 0 | EV_MN_KINGDOM | EV_LONDON |
| SOV_MN_K_B | REGIME_MN_K | 1913-05-30～1914-07-29 | de_jure | relation/2739656 v22 | cc0 | 0 | EV_LONDON | — |
| SOV_BG_A | REGIME_BG | 1908-10-05～1913-08-10 | de_jure | relation/2742283 v27 | cc0 | 0 | EV_BG_INDEP | EV_BUCHAREST |
| SOV_BG_B | REGIME_BG | 1913-08-10～1914-07-29 | de_jure | relation/2746680 v29 | cc0 | 0 | EV_BUCHAREST | — |
| SOV_RO_A | REGIME_RO | 1908-10-06～1913-08-10 | de_jure | relation/2692219 v68 | cc0 | 0 | — | EV_BUCHAREST |
| SOV_RO_B | REGIME_RO | 1913-08-10～1914-07-29 | de_jure | relation/2693260 v64 | cc0 | 0 | EV_BUCHAREST | — |
| SOV_AL_PROV | REGIME_AL_PROV | 1912-11-28～1914-02-21 | not_sovereign | relation/2807008 v25 | cc0 | 0 | EV_AL_INDEP | EV_AL_PRINCIPALITY |
| SOV_AL_PR | REGIME_AL_PR | 1914-02-21～1914-07-29 | de_jure | relation/2855613 v8 | cc0 | 0 | EV_AL_PRINCIPALITY | — |
| SOV_IT_AEGEAN | REGIME_IT_AEGEAN | 1912-04-27～1914-07-29 | not_sovereign | relation/2830316 v10 | cc0 | 0 | EV_DODECANESE | — |
| SOV_LY_TR | REGIME_LY_TR | 1912-10-18～1914-07-29 | de_jure | relation/2690837 v18 | cc0 | 0 | EV_OUCHY | — |
| SOV_LY_CY | REGIME_LY_CY | 1912-10-18～1914-07-29 | de_jure | relation/2803190 v11 | cc0 | 0 | EV_OUCHY | — |
| SOV_ES_A | REGIME_ES_K | 1908-10-06～1912-11-27 | de_jure | relation/2860487 v20 | cc_by | 0 | — | EV_ES_MOROCCO |
| SOV_ES_B | REGIME_ES_K | 1912-11-27～1914-07-29 | de_jure | relation/2860486 v24 − relation/2860424 v10 | cc_by | 0 | EV_ES_MOROCCO | — |
| SOV_MA_ES | REGIME_MA_ES | 1912-11-27～1914-07-29 | de_jure | relation/2860424 v10 | cc_by | 0 | EV_ES_MOROCCO | — |
| SOV_MA_SULT | REGIME_MA_SULT | 1908-10-06～1912-03-30 | de_jure | (relation/2866014 v8 ∪ relation/2866017 v9) − relation/2860487 v20 | cc_by | 0 | — | EV_FEZ |
| SOV_MA_FR_A | REGIME_MA_FR | 1912-03-30～1912-11-27 | de_jure | relation/2866016 v9 ∪ 前段蘇丹國範圍 | cc_by | 0 | EV_FEZ | EV_ES_MOROCCO |
| SOV_MA_FR_B | REGIME_MA_FR | 1912-11-27～1914-07-29 | de_jure | (relation/2866016 v9 ∪ 蘇丹國範圍) − relation/2860424 v10 − relation/2860486 v24 | cc_by | 0 | EV_ES_MOROCCO | — |
| SOV_PT_K | REGIME_PT_K | 1908-10-06～1910-10-05 | de_jure | relation/2959467 v2 | cc_by | 0 | — | EV_PT_REPUBLIC |
| SOV_PT_REPUBLIC | 01a18e71-ccc4-76ef-a4ef-157823b5a1ca | 1910-10-05～1951-06-11 | de_jure | relation/2807009 v14 | cc_by | 0 | EV_PT_REPUBLIC | — |

- 沿用既有政權：義大利王國、羅馬尼亞、希臘、比利時、丹麥、挪威、瑞典、保加利亞、法蘭西第三共和、義屬愛琴海群島、葡萄牙共和國。
- 本期間已有、未動的紀錄：安道爾、瑞士、根西、直布羅陀、曼島、澤西、列支敦斯登、盧森堡、摩納哥、馬爾他、聖馬利諾、荷蘭。
- **葡萄牙共和國修正**：既有紀錄起日 1910-01-01（OHM 只到年）→ 撤回（04-retract-01），自 1910-10-05 革命重送，幾何原樣沿用。1910-10-05 以前畫葡萄牙王國（OHM 2959467）。
- **OSM（ODbL）來源線段**：奧匈 2692361、德意志帝國 2692425 各 176 段，比利時 2797729 3 段、法國 2866012 2 段；依 1938–1940 批次的決定保留並標 `provenance.licenseReview = osm_derived_ways`。
- 留白（OHM 無資料，待查證）：埃及、蘇丹、阿拉伯半島內陸、波斯、冰島、法羅群島、里奧德奧羅；茅利塔尼亞 1912 年以前。

## 事件（22 筆）

| placeholder | 日期 | 類型 | 摘要 | 出處 |
|---|---|---|---|---|
| EV_BG_INDEP | 1908-10-05 | political | 保加利亞宣布獨立（斐迪南稱沙皇） | Doc. 44, p. 56（SRC_FRUS_1908） |
| EV_BOSNIA | 1908-10-06 | political | 奧匈帝國宣布併吞波士尼亞與赫塞哥維納，自新帕扎爾桑賈克撤軍 | Doc. 30, pp. 36–38（SRC_FRUS_1908）；pp. 286–289（SRC_AJIL_AH_TR_1909） |
| EV_MN_KINGDOM | 1910-08-28 | political | 蒙特內哥羅親王尼古拉一世稱王，親王國改為王國 | **待查證** |
| EV_PT_REPUBLIC | 1910-10-05 | political | 葡萄牙革命：君主制廢除、共和國成立 | Doc. 905, pp. 825–826（SRC_FRUS_1910）；Doc. 904, p. 825（SRC_FRUS_1910） |
| EV_IT_TR_WAR | 1911-09-29 | war | 義大利對鄂圖曼帝國宣戰（義土戰爭，爭奪的黎波里塔尼亞與昔蘭尼加） | Doc. 402（SRC_FRUS_1911） |
| EV_DODECANESE | 1912-04-27 | campaign | 義大利佔領多德卡尼斯群島（4 月底起，5 月 4 日登陸羅德島） | Art. 2, pp. 58–59（SRC_AJIL_OUCHY_1912） |
| EV_FEZ | 1912-03-30 | treaty | 菲斯條約：摩洛哥成為法國保護國 | pp. 207–209（SRC_AJIL_FEZ_1912） |
| EV_MN_WAR | 1912-10-08 | war | 蒙特內哥羅對鄂圖曼帝國宣戰（第一次巴爾幹戰爭開始） | Doc. 1792（SRC_FRUS_1912） |
| EV_BALKAN_WAR | 1912-10-18 | war | 塞爾維亞、保加利亞、希臘對鄂圖曼帝國宣戰（第一次巴爾幹戰爭） | Doc. 1795（SRC_FRUS_1912）；Doc. 1796（SRC_FRUS_1912）；Doc. 1797（SRC_FRUS_1912） |
| EV_OUCHY | 1912-10-18 | treaty | 烏契（洛桑）和約：義土戰爭結束，鄂圖曼自的黎波里塔尼亞、昔蘭尼加撤出 | pp. 58–62（SRC_AJIL_OUCHY_1912）；Doc. 785（SRC_FRUS_1912） |
| EV_ES_MOROCCO | 1912-11-27 | treaty | 法西摩洛哥條約：劃定西班牙在摩洛哥北部的保護區 | pp. 81–99（SRC_AJIL_FR_ES_1912） |
| EV_AL_INDEP | 1912-11-28 | political | 阿爾巴尼亞在發羅拉宣布獨立，成立臨時政府 | **待查證** |
| EV_LONDON | 1913-05-30 | treaty | 倫敦和約：鄂圖曼割讓伊諾斯—米迪亞線以西領土與克里特，第一次巴爾幹戰爭結束 | pp. 12–13（SRC_AJIL_LONDON_1913）；Doc. 1655（SRC_FRUS_1913） |
| EV_BALKAN2 | 1913-06-29 | war | 保加利亞攻擊塞爾維亞、希臘陣地（第二次巴爾幹戰爭） | Doc. 76, pp. 78–81（SRC_FRUS_1913） |
| EV_RO_WAR | 1913-07-10 | war | 羅馬尼亞對保加利亞宣戰 | **待查證** |
| EV_OT_BG2 | 1913-07-12 | war | 鄂圖曼軍越過伊諾斯—米迪亞線進攻保加利亞（7 月 22 日收復埃迪爾內） | **待查證** |
| EV_BUCHAREST | 1913-08-10 | treaty | 布加勒斯特和約：第二次巴爾幹戰爭結束，劃分馬其頓與南多布羅加 | pp. 13–27（SRC_AJIL_BUCHAREST_1913） |
| EV_CONSTANTINOPLE | 1913-09-29 | treaty | 君士坦丁堡和約：保加利亞與鄂圖曼議和，埃迪爾內歸鄂圖曼 | pp. 27–45（SRC_AJIL_CONSTANTINOPLE_1913） |
| EV_ATHENS | 1913-11-14 | treaty | 雅典和約：希臘與鄂圖曼議和 | pp. 46–55（SRC_AJIL_ATHENS_1913）；Doc. 1658（SRC_FRUS_1913） |
| EV_AL_PRINCIPALITY | 1914-02-21 | political | 維德親王威廉接受阿爾巴尼亞王位，阿爾巴尼亞親王國成立 | **待查證** |
| EV_SARAJEVO | 1914-06-28 | political | 奧匈皇儲法蘭茲·斐迪南大公在塞拉耶佛遇刺 | pp. 222–223（SRC_AJIL_YELLOW_BOOK_1914） |
| EV_AH_RS_WAR | 1914-07-28 | war | 奧匈帝國對塞爾維亞宣戰 | No. 80, pp. 229–230（SRC_AJIL_YELLOW_BOOK_1914）；No. 75 (2)（SRC_AJIL_YELLOW_BOOK_1914） |

出處：FRUS 1908／1910／1911／1912／1913（美國聯邦公有領域）；條約英譯本文取自 The American Journal of International Law, Supplement: Official Documents（1909–1915 年美國出版，著作權已過期，JSTOR Early Journal Content，archive.org 公開全文），各篇一筆來源。
找不到正式出處的 5 筆標「待查證」、不附引用：蒙特內哥羅稱王、阿爾巴尼亞獨立、羅馬尼亞參戰、鄂圖曼反攻保加利亞、維德親王即位。

## 衝突（10 筆，雙劍）

| placeholder | 雙方 | 起 → 迄 | 位置 |
|---|---|---|---|
| CF_IT_OT | REGIME_IT — REGIME_OT | EV_IT_TR_WAR → EV_OUCHY | [13.1913, 32.8872] |
| CF_MN_OT | REGIME_MN_K — REGIME_OT | EV_MN_WAR → EV_LONDON | [19.8927, 42.6381] |
| CF_BG_OT | REGIME_BG — REGIME_OT | EV_BALKAN_WAR → EV_LONDON | [24.9107, 41.7278] |
| CF_RS_OT | REGIME_RS — REGIME_OT | EV_BALKAN_WAR → EV_LONDON | [21.141, 43.1098] |
| CF_GR_OT | REGIME_GR — REGIME_OT | EV_BALKAN_WAR → EV_LONDON | [21.6524, 39.7538] |
| CF_BG_RS | REGIME_BG — REGIME_RS | EV_BALKAN2 → EV_BUCHAREST | [22.7525, 43.3832] |
| CF_BG_GR | REGIME_BG — REGIME_GR | EV_BALKAN2 → EV_BUCHAREST | [22.65, 41.05] |
| CF_RO_BG | REGIME_RO — REGIME_BG | EV_RO_WAR → EV_BUCHAREST | [25.4896, 43.6484] |
| CF_OT_BG2 | REGIME_OT — REGIME_BG | EV_OT_BG2 → EV_CONSTANTINOPLE | [26.5555, 41.6771] |
| CF_AH_RS | REGIME_AH — REGIME_RS | EV_AH_RS_WAR → （未結束） | [19.6402, 44.96] |

位置：開戰日兩國共同邊界最長一段的中點；不相鄰的（義—土、保—希、土—保第二次）取主要戰區，見各筆 `locationMethod`。蒙特內哥羅在第二次巴爾幹戰爭對保參戰未建紀錄（待查證）。

## QA

- 抽樣日 1908-10-06, 1908-10-07, 1910-09-01, 1911-01-01, 1912-06-01, 1912-11-01, 1913-01-01, 1913-07-01, 1913-09-01, 1914-03-01, 1914-07-28：新紀錄＋未動的既有紀錄兩兩重疊面積都 < 0.001 平方度（`qa.json`）。
- 倫敦割讓區（1913-05-30～08-10）：鄂圖曼 1908 版 − 1913 版 − 多德卡尼斯 − 阿爾巴尼亞 − 克里特 − 各國當期範圍；布加勒斯特後的剩餘空白 0.002 平方度。

## 待 Tai 決定／待查證

1. 利比亞在烏契和約前畫成鄂圖曼（用 OHM 義屬範圍近似），義軍 1911-10 起佔領沿岸未分。
2. 埃迪爾內 1913-05-30～07-22 依 OHM 畫入鄂圖曼（實際由保軍控制）。
3. 倫敦割讓區未分塞、希、保佔領區；阿爾巴尼亞臨時政府期間的塞、希、蒙佔領也未分。
4. 摩洛哥：1912-03-30 後的法國保護國含 OHM 2866016 缺的中南部約 12 平方度；1907 年起法軍佔領的舍維亞、烏季達併入蘇丹國。
5. 茅利塔尼亞、葡萄牙王國的起訖只到年；羅馬尼亞新界用和約日（OHM 為 8 月 30 日）。
6. 5 筆待查證事件（見上）。
