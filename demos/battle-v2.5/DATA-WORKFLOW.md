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

## 先後順序（Tai 2026-11-15）

**先補大部隊全程的位置，再補細節。** 憲法 Decision 5：集團軍／軍層級的部隊在整場戰役期間的位置沒有補齊之前，該戰役不作為正式入口。所以步驟 2（名冊）之後，先做「集團軍、軍層級在每個關鍵日的位置」（出處可以是文字敘述，畫在地名中心），再做態勢圖讀圖與師級細節。敦克爾克第一輪是反過來做的，結果 5/26 以前地圖上沒有任何部隊。

畫面的驗收規則（R1–R7）在 `design.md`「戰役頁規則」。

## 每場戰役的步驟

依序做。每一步的「完成條件」沒過，不往下走。

| 步 | 內容 | 產出 | 完成條件 |
|---|---|---|---|
| 0 | 範圍與來源計畫：起訖日、做到哪一層級、預計用哪些出處、哪些圖 | `PLAN.md` | 每一方至少排到一個己方或第三方出處（見「規則」第 2 點） |
| 1 | 來源登記：等級與依據、版本、網址；原文抓下來存檔並記雜湊 | `sources.json`、原文存檔 | 每個來源都有等級依據；原文存檔路徑寫進檔案 |
| 2 | 名冊與指揮官 | `r1-units.json`、`r7-commanders.json` | 每個單位至少一筆逐字引文；起訖日沒有出處就留空，不填預設值 |
| 3 | 態勢圖登記與讀圖：控制點、部隊標註、前線 | `digitized/<mapKey>.readings.json` → `.json` | 配準過門檻（一般圖 2 公里；全戰區圖 15 公里且只取集團軍群、集團軍、裝甲師，見 `docs/source-rules.md` 6a）；**每個標註都填 `unitKey`，或寫明為什麼對不到** |
| 4 | 文字位置、交戰、據點 | `r3`、`r5`、`r6` | 單位一律用步驟 2 的代號；地點給出處地名＋OSM 編號 |
| 5 | 前線 | `r4-fronts.json` | 每個有圖的日期，至少一條能分出兩方的接觸線；沒有就記在 `gapsByDate` |
| 6 | 自檢 | `checks/` | 見下一節，全部通過 |
| 7 | 交給展示頁：跑匯入、看匯入報告 | 展示頁的 `IMPORT-REPORT.md` | 見「驗收」 |

## 自檢（步驟 6）

1. **引文逐字核對**：每筆引文在存檔的原文裡找得到（現有的 `tools/battles/verify_quotes.py`）。
2. **批次有沒有跑完**：執行結果若是錯誤或被用量上限中斷，這一批的產出不提交，重跑到正常結束為止。敦克爾克這輪有兩批是中斷後直接提交的。
3. **讀圖要讀兩次**：同一張圖由兩次獨立執行各讀一遍，比對同號標註的位置差。差距超過該圖的精度就列為待確認，不取平均。
4. **標註對名冊**：統計每張圖有多少標註對到名冊。敦克爾克這輪是 390 個裡 0 個。
5. **多來源**：統計只有一個家族的筆數，以及只有對手方說法的筆數（見下一節）。
6. **預設值檢查**：起訖日等於戰役起訖日、且引文沒有提到日期的，改成留空。

## 規則：來源等級、獨立來源、可信程度

三件事分開判定，互不換算。2026-11-13 訂，取代「單一來源把等級降一級」的做法。
全專案共用的版本在 `docs/source-rules.md`；兩份不一致時以那一份為準，這裡只留戰役資料用得到的部分。

### 1. 來源等級：這份出處本身是什麼

沿用主專案 T1 的 A／B／C／X，這裡補上戰役資料的對照。等級評的是**實際讀到的那份文件**，不是它引用的書；等級評定後不因其他原因更動。

| 等級 | 戰役資料的範圍 | 例子 |
|---|---|---|
| A | 參戰方當時的原始檔案（戰鬥詳報、作戰日誌、命令）；國家機構編纂的官方戰史 | JACAR 陸軍檔案、Ellis |
| B | 具名學者的專書或期刊論文；第三方當時的官方紀錄；當事人戰後為官方撰寫的紀錄；學術專書的地圖 | 國史館館刊論文、FRUS 電報、Japanese Monograph |
| C | 合法、有具名作者或出版機構，但不到 B：通俗歷史、雜誌、機構網站的介紹文 | |
| X | 不收：Wikipedia、Wikidata、百度百科、個人網站、無署名內容 | |

每個來源在 `sources.json` 寫明評等依據。

### 2. 獨立來源：有幾方各自這樣說

- 同一機構、同一套底稿、或互相轉引的來源，算同一個「家族」，只算一個獨立來源。家族寫在 `battle.config.json`。
- 不要為了湊數把同一脈絡的來源拆成兩族。
- 另外記錄每筆資料的來源是**己方、對手方、還是第三方**。某一方的編制只有對手方的說法時，加註 `opposingOnly: true`。

### 3. 可信程度：這一筆資料目前查到什麼程度

| 可信程度 | 條件 |
|---|---|
| 已查證 | 一筆 A，或兩個獨立家族的 B，說法一致。**對手方的 A 不能單獨成立**：關於某一方的事實只有對手方來源時，一律待查證 |
| 待查證 | 有 A／B 來源，但不到上一列的門檻 |
| 推估 | 位置是從地圖讀出，或由文字地名連成線 |
| 說法衝突 | 兩個來源說法不同：兩個都留，寫進 `conflicts`，不自己選 |
| 不收 | 只有 C／X，或引文沒通過逐字核對：留在 seed 當線索 |

### 4. 能不能寫進資料庫

- 條件只有兩個：**原始等級是 A 或 B**，而且引文通過逐字核對。
- 寫入時一律是待審，並帶著第 3 點的可信程度；畫面依可信程度標示。
- 只有一個來源**不影響**能不能寫入，只影響可信程度。
- C 級不寫入戰役資料（主專案現行規則，不變）。

### 5. 一筆資料的不同欄位分開判定

一件事和它的精確日期，支持的來源可能不一樣多。支持較少的欄位降低精度或另列為候選，不要整筆丟掉。例：日軍攻占大場有兩個家族支持，只有「10/26」這一天是單一來源——寫入「十月下旬」，10/26 留作待查證的候選日期。

### 6. 查不到第二個來源時

照實標待查證，並在 `gaps` 寫明試過哪些來源、卡在哪裡、哪本紙本書可以補。不要放寬第 1、2 點來換取「已查證」。

欄位怎麼對到畫面：`sourced`＝已查證、`partial`＝待查證、讀圖＝推估、`gap`＝不顯示。

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
| 集團軍／軍層級的部隊，每個關鍵日都有位置 | 5/26 以前 0 支 | 全部（憲法 Decision 5 的最低上線標準） |
| 全景時同時出現的部隊牌 | 一百多個 | 不超過 20 個（R1） |
| 沒對到名冊的圖上標註上圖 | 81 個 | 0 個（R2） |

## 下一場的順序

先把敦克爾克補到上表的目標（主要是標註對名冊與第二來源），再做波蘭。流程在一場戰役上走通之前換下一場，同樣的缺口會再出現一次。
