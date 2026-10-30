# 停戰前快照：1940-06-04、1940-06-12（DRAFT）

> **狀態：DRAFT — 待 Tai 檢查。尚未寫入 appdb_ww2。**
> 預設 dry-run：`python3 send_seed.py`；Tai 同意後 `--send`。
> 前置 id：THEATER_WE、REGIME_DE、SRC_TRF（`../france-1940-07-15/sent-ids.json`），REGIME_FR3、REGIME_UK（`../fr-uk-1940/sent-ids.json`，法英那批要先寫入）。

## Tai 的決定（2026-10-31）

- 用 USMA WWII Europe Map 13（Situation 4 June 1940）與 Map 14（Situation 12 June 1940）做停戰前快照，兩張都是美國聯邦公有領域。
- 幾何要能追溯到地圖；地圖畫不清楚的標「控制資料缺」或拆成不確定區，不推測；照憲法的精度規則。
- 英國本土（2026-10-31，Tai 同意選項 B）：每張快照當天各一筆 [d, d+1)，只寫地圖上看得到的範圍；來源不夠的日期不寫。

## 快照與期間

| 快照 | 來源 | 期間 [start, end) |
|---|---|---|
| SNAP_0604 | USMA Map 13 | 1940-06-04 – 06-05（只有當天） |
| SNAP_0612 | USMA Map 14 | 1940-06-12 – 06-13（只有當天） |

兩張圖都是「Situation X June」的單日戰況。憲法 §6、§9：快照對應特定日期；只有來源明文確立一整段期間時才能延長。所以每筆紀錄只撐一天，兩個快照之間屬推估（前端 theater state = interpolated），不延長。
**Tai 2026-10-31 決定：快照延伸到同一政權或區域的下一張快照。**（快照本身的 asOfNote 仍寫「不延長」：快照沒有撤回端點，文字留著，以本節為準。）

| 原紀錄 | 原期間 | 新紀錄 | 新期間 | 狀態 |
|---|---|---|---|---|
| CR_DE_0604 | [06-04, 06-05) | CR_DE_0604_CF | [06-04, 06-12)，endUncertainty [06-05, 06-13) | `05`／`06` 已寫入 |
| CR_FR3_0604 | [06-04, 06-05) | CR_FR3_0604_CF | 同上 | `05`／`06` 已寫入 |
| GAP_FRAME／MAGINOT／DUNKIRK_0604 | [06-04, 06-05) | *_CF | [06-04, 06-12) | `05`／`07` 已寫入 |
| CR_DE_0612、CR_FR3_0612、CR_UK_0612、GAP_*_0612 | [06-12, 06-13) | — | 不變 | Tai 2026-10-31 決定維持只算一天（下一張 07-15 只涵蓋法國；第三共和 07-10 結束；英國之後沒有快照） |

- 06-04 那批的下一張快照（06-12）用 Map 14 圖框內紀錄＋圖框外缺口涵蓋整個法、比、盧、荷，沒有歧義。
- 修正走 I5「撤回＋新增」：`05` 呼叫 `POST /control-records/{id}/retraction`、`POST /control-coverage-notes/{id}/retraction`（2026-10-31 新增端點，AI 提案・待拍板），`06`、`07` 新增延伸版本；幾何、控制方、類型、出處都不變。
- endUncertainty [06-05, 06-13)：地圖只證明 6/4 當天，實際變化可能在 6/5～6/12 之間。

## 控制區

| 紀錄 | 控制方 | 類型 | 面積 | 幾何 |
|---|---|---|---|---|
| CR_DE_0604 | 德意志國 | military_occupation | 54,940 km² | Map 13 戰線＋Maginot 帶以北，限圖框內；扣 CR_NORD |
| CR_FR3_0604 | 第三共和 | direct_rule | 35,727 km² | Map 13 戰線以南，限圖框內 |
| CR_DE_0612 | 德意志國 | military_occupation | 103,086 km² | Map 14 同上 |
| CR_FR3_0612 | 第三共和 | direct_rule | 159,656 km² | Map 14 同上 |
| CR_UK_0612 | 英國 | direct_rule | 70,235 km² | Map 14 圖框內、標題框以外看得到的英格蘭東南（標「ENGLAND」，與德軍區不同色），邊界內縮 11 km |

### 英國本土（選項 B）

| 日期 | 結果 | 理由 |
|---|---|---|
| 1940-06-04 | 不寫 | Map 13 圖框西北角（肯特所在位置）畫成海面與標題框，沒有畫英國陸地。（fr-uk README 先前說「Map 13 圖框含肯特」是依配準推算，實際看圖沒有畫出，已更正。） |
| 1940-06-12 | CR_UK_0612＋GAP_UK_0612 | Map 14 畫出英格蘭東南（Bristol–Coventry–Norwich 以南）。 |
| 1940-07-15、08-15 | 不寫 | 這兩個快照的地圖（Leconte 分界線圖等）只畫法國；USMA Map 15 是 6/13–25 的期間圖，不是這兩天。沒有同日的合格地圖。 |

- 配準：Map 14 原本的三次多項式只用法國、比、荷的控制點，外推到英格蘭北緣誤差 9–12 km（以 Norwich、Coventry 驗證）。英國另用 21 個英格蘭與海峽兩岸控制點（`build/trace/gcp-map14-uk.json`；Norwich、Coventry、Southampton、Portland 為新增，像素座標目讀圓點中心）做仿射配準：殘差 RMS 3.39 km、最大 7.78 km，留一驗證最大 10.64 km。
- 看得到的範圍＝圖框 − 標題框（像素 752,257–1570,636），再往內縮 11 km（留一驗證最大誤差），確保紀錄只落在圖上確實畫到的地方。陸地外框用 Natural Earth GBR（海岸線）。
- 其餘英國領土（圖框外、標題框下、內縮帶，含蘇格蘭、威爾斯、北愛爾蘭）＝GAP_UK_0612（not_yet_digitized，173,547 km²），不推測。
- 預覽：`/workspace/world-line-c8/uk-0612-overlay-map14.png`（box）。

- 法國外框：TRF-GIS 1940 省界；比、盧、荷：Natural Earth（現代疆界，auxiliary_geometry）。
- **扣掉 CR_NORD**（Nord＋Pas-de-Calais，已寫入，[1940-06-04, 1944-07-16)，德國）：同控制方不可重疊（I3）。
- ⚠ **Eupen-Malmedy**：1940-05-18 已被德國併入，這裡仍算在比利時的 military_occupation 內（圖上沒有分開畫）。
- ⚠ **荷蘭**：1940-05-29 起是德國文官的帝國專員公署，不是軍事管理；圖上只畫在德軍後方，這裡沿用 military_occupation。

## 控制資料缺（control_coverage_notes，R9）

| 備註 | 日期 | 原因 | 面積 | 範圍 |
|---|---|---|---|---|
| GAP_FRAME_0604 | 06-04 | not_yet_digitized | 514,023 km² | Map 13 圖框外（法國中南部、荷蘭北部） |
| GAP_MAGINOT_0604 | 06-04 | no_qualified_source | 1,534 km² | Maginot 帶與國界之間的狹長地帶（圖上沒標誰控制） |
| GAP_DUNKIRK_0604 | 06-04 | no_qualified_source | 80 km² | 敦克爾克防線在比利時境內的部分（Nord 境內已由 CR_NORD 涵蓋） |
| GAP_FRAME_0612 | 06-12 | not_yet_digitized | 337,344 km² | Map 14 圖框外（約北緯 47.3° 以南、荷蘭北部） |
| GAP_MAGINOT_0612 | 06-12 | no_qualified_source | 3,239 km² | Maginot 帶外側（含亞爾薩斯萊茵河沿岸） |
| GAP_CAUX_0612 | 06-12 | no_qualified_source | 2,644 km² | Pays de Caux：12 June 線西端以西、8 June 點線以西；圖註「Elements of Tenth Army and British surrendered 12 June」 |
| GAP_LINEBREAK_0612 | 06-12 | no_qualified_source | 332 km² | 12 June 線在 Châlons 東南斷開約 10 km，以斷點中點畫圓 |
| GAP_UK_0612 | 06-12 | not_yet_digitized | 173,547 km² | 英國本土在 Map 14 上沒畫到的部分（見上） |

- Maginot 帶外側的西界：以「戰線與要塞帶交會點」的經線切開，這是建構線，不是圖上的線。
- 缺口與控制區之間留約 2 m 退縮（大於 1e-5° 網格捨入量），確保送出座標與同日控制紀錄的浮點交集面積為 0。

## 描圖與配準（可追溯到地圖）

1. **控制點**（`build/trace/gcp-map13.json`、`gcp-map14.json`）：圖上城市圓點的像素座標 ↔ 城市經緯度。先目讀，再用圓環樣板在 ±35 px 內自動對準。
2. **配準**：EPSG:3035 平面上的三次多項式；殘差 > 3 km 的點視為讀錯剔除。

| 圖 | 控制點 | 擬合殘差 RMS／最大 | 留一驗證 RMS／最大 |
|---|---|---|---|
| Map 13 | 50 | 1.58 km／2.82 km | 2.1 km／4.9 km |
| Map 14 | 37 | 1.55 km／2.82 km | 2.4 km／7.1 km |

3. **線條**（`build/trace/lines-map13.json`、`lines-map14.json`）：`build/trace_lines.py` 以顏色門檻＋形態學＋骨架化從原圖自動擷取，不手畫：粗藍實線（戰線）與 Maginot 網格帶的中心線。
4. **手讀的多邊形**（像素座標寫在 `build/make_prearmistice.py`）：敦克爾克防線（Map 13 虛線）、Pays de Caux（Map 14 的 8 June 點線＋塞納河口）。
5. **切割**：`build/make_prearmistice.py` 把線轉成經緯度、兩端各延長 0.15°，切開圖框內的陸地；線右側（南／西）＝法國、左側＝德國。外圈閉合只走英吉利海峽與底圖以外。
6. 精度：第一階段是國家／控制區層級（憲法 R1），本批只表達控制區，不另畫戰線；配準誤差約 2 km 等級，與圖上粗戰線的線寬（約 10 px ≈ 2 km）同一量級。

## 來源

| 代號 | 種類 | 授權 | 用途 |
|---|---|---|---|
| SRC_USMA13 | atlas_map | us_federal_pd | 06-04 primary |
| SRC_USMA14 | atlas_map | us_federal_pd | 06-12 primary |
| SRC_NATURAL_EARTH | dataset | public_domain | auxiliary_geometry（比、盧、荷、英國外框） |

沿用法國那批：SRC_TRF（cc_by，1940 省界）。

## 檔案

- `zones-pre-armistice-1940.geojson`：全部控制區與缺口（含面積、配準殘差）。
- `requests/`：依檔名順序送出；`send_seed.py`：送出工具（dry-run 預設）。
- `build/trace_lines.py`：從原圖擷取線條；`build/make_prearmistice.py`：幾何；`build/make_requests_pre.py`：產生請求檔。（box 上用 `~/.venvs/gis/bin/python`，讀 `/workspace/world-line-ww2/trace/`。）
- 測試 `SeedPreArmistice1940Tests`：在 Testcontainers 重播法國、陣營、法英與本批，檢查快照當天有控制區與缺口、隔天不延長。
