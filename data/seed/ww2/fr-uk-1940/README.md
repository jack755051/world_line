# 法、英政權與 1940 控制區（DRAFT）

> **狀態：DRAFT — 待 Tai 檢查。尚未寫入 appdb_ww2。**
> 預設 dry-run：`python3 send_seed.py`；Tai 同意後 `--send`。
> 2026-10-31 依 Tai 拍板改版（見下）；被取代的請求檔移到 `superseded-2026-10-31/`（不送出，保留備查）。
> 前置 id（SNAP_0715、SRC_LECONTE、SRC_AIN、SRC_TRF、SRC_USMA15）讀 `../france-1940-07-15/sent-ids.json`。

## Tai 的決定（2026-10-30）

- 先補法國與英國的政權與 1940 控制區，讓地圖看得到德、法、英之間的領土變化；缺口 API 之後再做。
- 陣營依憲法 §6；英、法（第三共和）、自由法國屬同盟，維琪屬共同交戰／合作；每段都要有文件化的正式依據。英法 1940 年的「同盟」依據若有爭議，列出候選由 Tai 決定。

## Tai 的決定（2026-10-31）

1. 陣營「目前如果有記錄，並且最嚴謹的才算。所以應該以B為主，但是可以以A補充」：同盟以**聯合國家宣言**（1942-01-01）為準；1939-09-03 的參戰照會只作「補充」，不構成陣營切片。
2. 英國本土「需再聚焦」：不寫（選項見下）。→ 2026-10-31 Tai 同意選項 B，寫在 `../pre-armistice-1940/`（只有 1940-06-12，見該 README「英國本土（選項 B）」）。
3. 自由法國依建議：政權起日 1940-06-23（FRUS 1940 v. I, Doc. 235）；陣營照原則 1，可以補充。
4. 停戰前快照：另一批 `../pre-armistice-1940/`。
5. 阿爾卑斯五省在前端要看得到「控制資料缺」。

## 政權

目前 API 的政權只有名稱，沒有起訖欄位（`regime_status_periods`／`regime_transitions` 屬缺口 API，尚未實作）。下表的起訖日只記在這裡，不送進 DB。

| 代號 | slug | 自稱 | 起訖（本批依據） | 出處 |
|---|---|---|---|---|
| REGIME_FR3 | french-third-republic | République française | …～1940-07-10（最後一天） | JO 1940-07-11 n° 167 p. 4513：7-10 憲法性法律（Lebrun 以共和國總統公布） |
| REGIME_FR_STATE | french-state-vichy | État français | 1940-07-11～ | 同上（授權頒布「法蘭西國」憲法）；7-11 Acte constitutionnel n° 1 原文**未核對**（JO 7-12 期沒有公有領域掃描可開） |
| REGIME_FR_LIBRE | free-france | France libre | 1940-06-23～（記在自稱名稱的 validPeriod；政權狀態切片尚未實作） | FRUS 1940 v. I, Doc. 235, pp. 266–267（事件 EV_UK_RECOG_FF） |
| REGIME_UK | united-kingdom | United Kingdom of Great Britain and Northern Ireland | 本期間無變動 | — |

## 控制區

| 紀錄 | 控制方 | 期間 [start, end) | 類型 | 面積 | 幾何來源 | primary |
|---|---|---|---|---|---|---|
| CR_VICHY_FREE | 法蘭西國 | 1940-07-15 – 1942-11-11（起日不確定 07-11～07-15） | direct_rule | 219,166 km² | 分界線：Ain 座標（對照 Leconte，與 CR_MAIN 共用）；外框：TRF-GIS 1940；扣除與義大利接壤的 5 省 | Leconte（cc0） |
| GAP_ALPINE | —（控制資料缺） | 1940-07-15 – 1942-11-11 | 涵蓋備註 no_qualified_source | 27,585 km² | TRF-GIS 1940 五省；與控制區留約 2 m 退縮 | — |

- 維琪自由區與法國那批全部控制區（含待決的東北禁區）在 1e-5° 網格上的交集面積都是 0。
- **義大利佔領區**：沒有合格來源（`docs/research/ww2-data-sources.md` §4.3）。為了不把義大利佔領的市鎮標成維琪，Basses-Alpes、Hautes-Alpes、Alpes-Maritimes、Savoie、Haute-Savoie 五省（27,586 km²）不畫，地圖上是「控制資料缺」（R9）。
- **自由區迄日 1942-11-11** 沿用 CR_MAIN（Anton 行動），本批引用的來源沒有明文寫出這個日期。
- **Rockall** 1955 年才由英國宣布併入，1940 年不屬英國，從 Natural Earth 的 GBR 排除。
- **阿爾卑斯五省**改送成涵蓋備註 GAP_ALPINE（`POST /control-coverage-notes`），前端以點狀「控制資料缺」樣式呈現（R9）。
- **英國本土**（原 CR_UK_HOME）：不寫，見「英國本土：選項」。幾何仍在 `zones-fr-uk-1940.geojson` 備查。

## 陣營（依 2026-10-31 拍板）

| 代號 | 政權 | 陣營 | 期間 | primary | date_check |
|---|---|---|---|---|---|
| AL_FR_STATE_COBEL | 法蘭西國 | co_belligerent | 1940-07-11 – （未定） | DGFP D IX pp. 671–676，停戰協定第 III、X 條 | JO 1940-07-11 p. 4513 |
| AL_UK_ALLIES_1942 | 英國 | allies | 1942-01-01 – （未定） | FRUS 1942 v. I, Doc. 18, pp. 25–26（聯合國家宣言，英國由 Churchill 簽署） | — |

- **第三共和**：沒有簽聯合國家宣言（1942 年已不存在），不建陣營切片。
- **自由法國**：沒有簽聯合國家宣言（法國 1944-12-26 才加入，當時是臨時政府），FRUS 也沒找到正式加入文件，不建陣營切片。
- 1942-01-01 以前的英國、整段的第三共和與自由法國：前端顯示「陣營未建置」，另列「補充」。

### 補充（事件＋引用；前端卡片標「補充」，不參與陣營判定）

| 代號 | 日期 | 參與方（角色） | 引用 |
|---|---|---|---|
| EV_UK_DECL_1939 | 1939-09-03 | 英國、德國（belligerent） | FRUS 1939 v. I, Doc. 419, p. 414（英國照會） |
| EV_FR3_DECL_1939 | 1939-09-03 | 第三共和、德國（belligerent） | FRUS 1939 v. I, Doc. 421, p. 415（法國照會） |
| EV_UK_RECOG_FF | 1940-06-23 | 英國、自由法國（other） | FRUS 1940 v. I, Doc. 235, pp. 266–267（美國駐法副大使 Biddle 1940-06-24 電報：「last night's announcement of recognition of General de Gaulle's National Committee as the only sovereign authority of France」） |

- 呈現方式：`GET /control` 的每個控制區帶 `controllerSupplements`＝控制方在該日當天或之前參與、且附引用的 war／treaty／political 事件。
- 資料結構：用 PRD §6.3 已定義的 `event_participants`、`event_citations`（2026-10-31 實作，AI 提案・待拍板）。

## 英國本土：選項（Tai「需再聚焦」；2026-10-31 選 B，實作見 `../pre-armistice-1940/README.md`）

> 更正：下表說 Map 13 圖框含肯特，是依配準推算；實際看圖，Map 13 該處畫成海面與標題框，沒有畫英國陸地，所以 06-04 不寫。

| 選項 | 做法 | 依據 | 問題 |
|---|---|---|---|
| A 長區間 | 一筆 [1939-09-03, 1945-09-03) | 參戰日、第一階段終點 | 起訖不是來源明文（原 CR_UK_HOME，已移到 superseded） |
| B 逐快照單日紀錄 | 每個有畫到英國的地圖日期各寫一筆 [d, d+1)，只畫圖框內看得到的部分，其餘列控制資料缺 | USMA Map 13（6/4，圖框含肯特）、Map 14（6/12，圖框含倫敦與英格蘭東南）、Map 15（6/13–25）等 | 最嚴謹；但筆數多、英國大部分會是缺口；Map 2（1936–39）不是單日 |
| C 多圖夾出的區間 | 以最早與最晚兩張都畫出英國未被佔領的地圖日期為起訖，中間屬推估 | 同 B | 憲法 §6：只有來源明文確立整段期間才算史料，C 的中段仍是推估 |
| D 戰區外依主權推定 | 把英國本土放在 west-europe 戰區範圍外，前端依主權推定控制（R9 例外），不建控制紀錄 | 憲法 R9、PRD §6.4 | 英國有空戰（不列顛之戰），「曾發生戰事」的地區依 R9 必須在戰區內；且戰區範圍、主權主張尚未實作（§12 Q5） |

建議：B（每張圖單日、圖框外列缺口），與停戰前快照同一做法。

## 沒有寫的

- **海峽群島**（德國 1940-06-30 起佔領 Guernsey、07-01 Jersey）：R7 要求控制紀錄的 primary 是有使用權的地圖並標圖號，目前沒找到。USMA Map 15 只標地名，Map 53 是 1944 年。英國官方戰史（HMSO 1950 年代）在英國已過皇家著作權期，但在美國可能因 URAA 回復保護，使用權待確認。
- **義大利佔領區**：同上，沒有合格來源。
- **停戰前快照**：已另做一批 `../pre-armistice-1940/`（USMA Map 13、14）。
- **第三共和 1940-06-25～07-10 的非佔領區控制**：在 07-15 快照之前，本批不做。
- **英國海外領地、曼島**：不在本批範圍。曼島是皇家屬地，不屬英國本土。

## 來源

| 代號 | 種類 | 授權 | 用途 |
|---|---|---|---|
| SRC_JO_19400711 | official_record | pd_expired（官方法令；Commons 標 Public domain） | date_check |
| SRC_DGFP_D9 | official_record | us_federal_pd（國務院 Publication 6312） | 陣營 primary、date_check |
| SRC_FRUS_1939_I | official_record | us_federal_pd | 補充事件引用 |
| SRC_FRUS_1942_I | official_record | us_federal_pd（1960） | 英國陣營 primary |
| SRC_FRUS_1940_I | official_record | us_federal_pd（1959） | 自由法國起日（補充事件引用） |

沿用法國那批：SRC_LECONTE（cc0）、SRC_AIN、SRC_TRF（cc_by）、SRC_USMA15。SRC_USMA02、SRC_NATURAL_EARTH 只供英國本土使用，英國本土未寫，先不建（請求檔在 superseded）。

## 檔案

- `zones-fr-uk-1940.geojson`：維琪自由區、GAP_ALPINE（送成涵蓋備註）、英國本土（未送，備查）。
- `superseded-2026-10-31/`：被 2026-10-31 拍板取代的請求檔（英國 1939 同盟、第三共和同盟、英國本土與其來源），不送出。
- `requests/`：依檔名順序送出。
- `send_seed.py`：送出工具。
- `build/make_fruk.py`：幾何（box 上 `~/.venvs/gis/bin/python`，讀 `/workspace/world-line-ww2/trace/`）。
- `build/make_requests_fruk.py`：產生請求檔。
- 測試 `SeedFrUk1940Tests`：在 Testcontainers 重播法國、陣營與本批，檢查陣營、補充事件、自由法國起日與 GAP_ALPINE。
