# 戰役資料：從取得到展示頁的完整流程

日期：2026-11-13。對象：在 `feature/person-cards` 上做資料取得的流程（派工者與執行者）。
`DATA-REQUESTS.md` 說的是「要什麼」，這份說的是「照什麼順序做、每一步怎麼算做完」。
依據是敦克爾克這一輪的實際結果（`battles/dunkirk-1940/IMPORT-REPORT.md`）。

## 分工

| 誰 | 做什麼 | 不做什麼 |
|---|---|---|
| 主線資料流程 | 找出處、抄引文、讀圖、產出 `data/seed/battles/<slug>/` | 不改展示頁 |
| 展示頁 | `tools/import_battle_data.py` 把上面的資料夾轉成畫面要的檔，並產出匯入報告 | 不查資料、不補、不推定、不自動對應單位 |

展示頁缺什麼，一律寫在匯入報告的「還缺什麼」，回到主線補，不在展示頁這邊補。

## 每場戰役的步驟

依序做。每一步的「完成條件」沒過，不往下走。

| 步 | 內容 | 產出 | 完成條件 |
|---|---|---|---|
| 0 | 範圍與來源計畫：起訖日、做到哪一層級、預計用哪些出處、哪些圖 | `PLAN.md` | 每一方至少排到一個己方或第三方出處（見「多來源」） |
| 1 | 來源登記：等級與依據、版本、網址；原文抓下來存檔並記雜湊 | `sources.json`、原文存檔 | 每個來源都有等級依據；原文存檔路徑寫進檔案 |
| 2 | 名冊與指揮官 | `r1-units.json`、`r7-commanders.json` | 每個單位至少一筆逐字引文；起訖日沒有出處就留空，不填預設值 |
| 3 | 態勢圖登記與讀圖：控制點、部隊標註、前線 | `digitized/<mapKey>.readings.json` → `.json` | 配準過門檻；**每個標註都填 `unitKey`，或寫明為什麼對不到** |
| 4 | 文字位置、交戰、據點 | `r3`、`r5`、`r6` | 單位一律用步驟 2 的代號；地點給出處地名＋OSM 編號 |
| 5 | 前線 | `r4-fronts.json` | 每個有圖的日期，至少一條能分出兩方的接觸線；沒有就記在 `gapsByDate` |
| 6 | 自檢 | `checks/` | 見下一節，全部通過 |
| 7 | 交給展示頁：跑匯入、看匯入報告 | 展示頁的 `IMPORT-REPORT.md` | 見「驗收」 |

## 自檢（步驟 6）

1. **引文逐字核對**：每筆引文在存檔的原文裡找得到（現有的 `tools/battles/verify_quotes.py`）。
2. **批次有沒有跑完**：執行結果若是錯誤或被用量上限中斷，這一批的產出不提交，重跑到正常結束為止。敦克爾克這輪有兩批是中斷後直接提交的。
3. **讀圖要讀兩次**：同一張圖由兩次獨立執行各讀一遍，比對同號標註的位置差。差距超過該圖的精度就列為待確認，不取平均。
4. **標註對名冊**：統計每張圖有多少標註對到名冊。敦克爾克這輪是 390 個裡 0 個。
5. **多來源**：統計只有一個來源的筆數（見下一節）。
6. **預設值檢查**：起訖日等於戰役起訖日、且引文沒有提到日期的，改成留空。

## 多來源

逐字核對只能證明「書上這樣寫」，不能證明寫的是對的。所以另外要求：

- 每一方的編制，至少有一個**該方自己的**或**第三方的** A／B 出處。只靠對手一方的官方戰史不算查證完成。敦克爾克這輪 64 個單位裡 62 個只有 Ellis 一個來源，德、法軍的編制都是英方說法。
- 兩個來源說法不同時，兩個都留，寫進 `conflicts`（欄位、各自的值與引文），不要自己選一個。
- 拿不到第二個來源就照實標：`status: "partial"`，並在 `gaps` 寫明試過哪些來源、卡在哪裡。

等級怎麼對到畫面：`sourced`＝已查證、`partial`＝待查證、讀圖＝推估、`gap`＝不顯示。

## 交付格式（展示頁實際會讀的欄位）

匯入程式讀 `data/seed/battles/<slug>/` 下這些檔；欄位名照敦克爾克這一輪，不要每場戰役換一套。

| 檔案 | 必要欄位 |
|---|---|
| `sources.json` | `<sourceKey>: {title, grade, url}` |
| `r1-units.json` | `units[]: unitKey, nameOrig, nameZh, echelon, parentKey, side, period, citations[], status` |
| `r7-commanders.json` | `commanders[]: unitKey, name, nameZh, tenure{start,end}, citations[], personKey, bioId` |
| `r3-unit-positions.json` | `positions[]: unitKey, date, placeAsInSource, place{nameOsm, osm{type,id}}, relation, citations[]` |
| `r4-fronts.json` | `fronts[]: date, side, lineKind, label, vertices[{lonlat}], mapRef{mapKey, citation, url, grade}, precision_m` |
| `r4-leadin-fronts.json` | `fronts[]: date, side, label, vertices[{placeAsInSource, place{osm}}], citations[]` |
| `r5-engagements.json` | `engagements[]: key, nameZh, period{start,end}, place{asInSource, osm}, attackers[], defenders[], citations[], status` |
| `r6-site-control.json` | `sites[]: placeAsInSource, place{osm}, date, controllerAfter, event, citations[], status` |
| `phase-leadin.json`、`<slug>.research.json` | 階段：名稱、起訖、引文；**主期階段也要有摘要文字** |
| `digitized/<mapKey>.json` | `mapDate, source{citation,url}, threshold{passes, loo_p95_km}, precision_m, control_points{名稱:{lonlat, osm}}, features[{label, sideGuess, echelon, lonlat, unitKey}]` |

每筆引文：`sourceKey, locator, quote, url, grade, quoteCheck{status}`。

共用工具請收在 `tools/battles/`，戰役當參數。敦克爾克的配準程式目前放在它自己的資料夾裡（`dunkirk_1940/tools/georef_ellis.py`），做下一場時不要再複製一份。

## 驗收（步驟 7）

在展示頁目錄跑 `python3 -I tools/import_battle_data.py <battle-id>`，看它寫出的 `IMPORT-REPORT.md`：

| 指標 | 敦克爾克現況 | 目標 |
|---|---|---|
| 圖上標註對到名冊 | 0／390 | 能辨認的都對到；對不到的寫明原因 |
| 只有一個來源的單位 | 62／64 | 每一方都有己方或第三方出處 |
| 有接觸線的日期 | 4 天（5/26–5/29），5/30 之後沒有 | 每個有圖的日期都有，或記明圖上沒畫 |
| 主期階段摘要 | 0／6 | 每個階段一段，附引文 |
| 疆界 | 只有紀錄編號 | 另外匯出幾何檔，或提供可離線讀的切片 |
| 查不到座標的地名 | 0 | 0 |

## 下一場的順序

先把敦克爾克補到上表的目標（主要是標註對名冊與第二來源），再做波蘭。流程在一場戰役上走通之前換下一場，同樣的缺口會再出現一次。
