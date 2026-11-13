# 敦克爾克 1940：戰役資料取得計畫（R1–R8）

- 日期：2026-11-13。依據：Tai 2026-11-13 11:03 決定啟動戰役資料需求（World Line 主管 11:31 轉達）；需求清單 `world_line-battle-demo/demos/battle-v2.5/DATA-REQUESTS.md`（R1–R8，唯讀參考）。
- 狀態：**只是計畫，尚未開始取資料**。順序：敦克爾克 → 波蘭 → 淞滬。
- 資料夾：本戰役新檔一律放 `data/seed/battles/dunkirk_1940/`（沿用既有 slug `dunkirk_1940`）。既有的 `data/seed/battles/dunkirk_1940.{research.json,seed.json,dry-run.md}` 不搬、不改，新檔引用它們。

## 0. 範圍與共同規則

| 項目 | 規則 |
|---|---|
| 主期 | 1940-05-26～06-04（研究檔定義的橋頭堡戰役；發電機行動為子事件）。單位、位置、交戰做到師級，依 Ellis 7 張態勢圖逐日 |
| 前段 | 1940-05-10～05-25 只做：疆界（R8）、概略前線（R4，粗精度）、階段說明。**不做單位細節**（不做 R1 位置、R3、R5 細項） |
| 來源等級 | 只收 A、B、具名 C。個人網站禁用（generals.dk 與 2026-11-13 禁用的 10 個網域；verify.py `DATED_BANNED_HOSTS`）。Wikipedia、Wikidata 只當候選線索，不當出處 |
| 引文 | 每筆附書目、章節／頁碼或圖號、網址、逐字摘句（≤ 80 字）、等級、取用日 |
| 地圖 | 出處必須精確到圖號或圖頁（例：Ellis Situation Map facing p. 214）。從地圖讀出的位置、前線一律標「推估」並記精度（見 §3） |
| 疆界 | R8 只用主專案的主權資料（`sovereignty_records`，OpenHistoricalMap 來源），**不手描** |
| 人物 | R7 以人物代號（將領研究檔 key）對到剛寫入的 leader_bios；沒有 bio 的先列「待補人物」，之後再補 |
| 查無 | 一律進 `gaps`，不補、不猜 |

> **與 DATA-REQUESTS.md 的差異（請主管確認，見 §7 Q1、Q2）**：需求清單寫「只收 A／B」「不要給推估座標」；主管 11:31 的規則是「A／B／具名 C」「地圖數位化的位置標推估」。本計畫依主管規則；地點仍同時給「出處地名＋OSM 物件編號」。

## 1. 庫內現況（已有的東西）

| 檔案 | 內容 |
|---|---|
| `data/seed/battles/dunkirk_1940.research.json`（dynamo-research/0.1） | A 級來源 2 個（Ellis 官方戰史、Ramsay 報告／London Gazette 38017）；6 個階段（5/26、5/28、5/29、5/30、6/1、6/3）；`mapSources`：Ellis 態勢圖 7 張＋示意圖 3 張＋USMA 6/4 圖 1 張；7 個 gaps |
| `data/seed/battles/dunkirk_1940.seed.json`（wl-battle-seed/0.2） | 參戰方 4 個、24 個要素（5 條前線、7 支箭頭、12 個據點，幾何多為推估）、**單位 0 個**、單位候選 5 個（番號未對出處）、12 個 gaps |
| `data/campaigns/dunkirk_1940.json`（wl-campaign/0.1-proposal） | 5 個階段與日期出處（展示頁 `import_campaign.py` 的輸入） |
| 展示頁 `battles/dunkirk-1940/battle.json` | 45 個單位、19 場交戰、436 筆位置、12 條前線：**全部是示例資料（維基百科），要整批換掉** |
| 主權資料（5442 開發庫，唯讀查過） | 1940-05-10 有效：french-third-republic、kingdom-of-belgium、kingdom-of-the-netherlands、grand-duchy-of-luxembourg、deutsches-reich（此筆迄 1940-05-18，之後換下一筆）、united-kingdom，皆 de_jure、附 OHM relation id |
| 人物 | 將領生平剛寫入開發庫（2026-11-13），對照見 §4 |

## 2. 各需求項目

### R1 部隊名冊（主期，做到師）
- **要的**：原文名、中文名、層級（集團軍群／集團軍／軍／師；海、空軍只列指揮層級，見 Q6）、上級單位、陣營、本戰役起訖日（含比軍 5/28 投降、法軍 6/4 投降）。
- **來源**：
  - A：Ellis《The War in France and Flanders 1939–1940》（HMSO 1953；HyperWar 轉錄），正文 ch. XI–XVI 與附錄的英軍戰鬥序列（BEF Order of Battle）。
  - A：Gort 勳爵報告（Lord Gort's Despatches，London Gazette Supplement 37573，1946-10-10）。
  - A：法國陸軍史料處《Les grandes unités françaises : historiques succincts》（SHAT），法軍第 1 集團軍、XVI 軍等條目。取得方式待查（Gallica 或 SHD 網站）。
  - A（官方戰史英譯）：MGFA《Germany and the Second World War》Vol. II（Oxford UP），德軍 A、B 集團軍群編組。
  - B：K.-H. Frieser《The Blitzkrieg Legend》（Naval Institute Press，2005），補德軍裝甲軍與師級番號。
  - 比軍：比利時官方或學術來源待查。查無則比軍只做到軍級，其餘列入 gaps。
- **已有**：seed 的單位候選 5 個（Kleist 裝甲集群、第 6 集團軍、Hoth 集群等，未對出處）。
- **產出**：`r1-units.json`：
  `units[]: {unitKey, nameOrig, nameZh, echelon, parentKey, side, regimeSlug, period:{start,end,startPrecision,endPrecision}, citations[], status}`

### R2 地圖來源（最重要）
- **要的**：圖檔網址、圖號或圖頁、圖上日期、授權依據、有無城鎮圓點（配準用）、圖上每個部隊標註對到哪個 R1 單位。
- **來源**：
  - A：Ellis 態勢圖 7 張（HyperWar `maps/UK-NWE-Flanders-5.jpg`～`-11.jpg`）：
    - 26 May（facing p. 182）
    - 27 May（facing p. 200）
    - The Withdrawal to the Coast（facing p. 202）
    - 28 May（facing p. 214）
    - 29 May（facing p. 224）
    - 30 May（facing p. 238）
    - 1 June（facing p. 244）
  - A：Ellis 示意圖：
    - Sea Routes（p. 185）
    - Dunkirk Harbour（p. 222）
    - German Situation Map 24 May（封底內頁，前段用）
  - A 或 B 待決：USMA《Campaign Atlas WWII European Theater》WWIIEurope13「Situation 4 June 1940」，補 6/2–6/4 缺圖。前段可加同圖集的 Campaign in the West 圖，圖號待查。上次 TLS 錯誤未下載，需改用 S3 鏡像網址重試。
- **授權**：
  - Ellis 是 HMSO 1953 皇家版權，UK 政府出版品 50 年後屬公有領域；需逐張寫明依據。
  - USMA 是美國聯邦政府著作，17 U.S.C. §105。
- **產出**：
  - `r2-maps.json`：`maps[]: {mapKey, citation, figure, facingPage, mapDate, url, license, hasTownDots, grade, verified, unitLabels[{label, unitKey|null}]}`
  - 每張可數位化的圖再出一份 `digitized/<mapKey>.readings.json`，格式照展示頁 `tools/georef.py`：control_points（城鎮：像素＋經緯度，經緯度取 OSM）、features（像素＋unit_id）。

### R3 部隊位置文字來源（補沒有地圖的日子）
- **要的**：「某部隊、某日、在某地」，一句一筆引文；地名用出處原文，附 OSM 物件編號。
- **來源**：Ellis ch. XI–XVI（A）、Gort 報告（A）、Ramsay 報告逐日敘述 p. 3296 起與附錄（A；研究檔 gap「未逐頁取用」）。
- **產出**：`r3-unit-positions.json`：
  `positions[]: {unitKey, date, datePrecision, placeAsInSource, osm:{type,id}, basis:"text", citations[]}`

### R4 前線
- **要的**：日期，以及依序的地名頂點或 R2 地圖數位化結果。
- **主期**：以 Ellis 7 張態勢圖數位化，6/2–6/4 用 USMA 圖或文字頂點。
- **前段 5/10–5/25**：只做概略前線，來源為 Ellis 前段章節與 German Situation Map 24 May；精度標粗。
- **已有**：seed 有 5 條前線，幾何為推估，需依圖重畫。
- **產出**：`r4-fronts.json`：
  `fronts[]: {date, phase, vertices:[{placeAsInSource, osm, lonlat}], basis:"map-digitized"|"text-vertices", mapRef, estimate:"推估", precision_m, precisionNote, citations[]}`

### R5 交戰（主期）
- **要的**：名稱、起訖日、地點、攻守雙方部隊（對到 R1）。
- **來源**：Ellis（A）為主，Frieser（B）補德方，法軍部分用 SHAT（A）。展示頁的 19 場只當候選清單，逐場找出處，找不到就刪除或列入 gaps。
- **產出**：`r5-engagements.json`：
  `engagements[]: {key, nameOrig, nameZh, period, place:{asInSource, osm}, attackers[unitKey], defenders[unitKey], citations[], status}`

### R6 據點易手日
- **要的**：地名、日期、易手後的控制方。
- **已有**：seed 有 12 個據點，其中 Bergues、Malo-les-Bains 待查證。
- **來源**：Ellis、Ramsay（A）。
- **產出**：`r6-site-control.json`：
  `sites[]: {placeAsInSource, osm, date, datePrecision, controllerSide, controllerRegimeSlug, citations[]}`

### R7 指揮官
- **要的**：部隊（對到 R1）、人名、任期、人物代號。
- **來源**：同 R1。任期只取本戰役期間有出處的日期。
- **產出**：`r7-commanders.json`：
  `commanders[]: {unitKey, personKey|null, bioId|null, name, nameZh, tenure:{start,end,precision}, citations[], bioStatus:"has_bio"|"missing"}`
- 缺 bio 的人另列 `r7-missing-people.json`，之後走將領生平流程補。

### R8 當年疆界
- **要的**：1940-05-10 法、比、荷、盧、德、英的疆界多邊形。
- **做法**：
  - 腳本以唯讀方式取主權資料：5052 的 `GET /api/v1/sovereignty?date=1940-05-10`，或唯讀查 5442。
  - 只記錄參照：`sovereignty_records.id`、`ohm_relation_id`、`ohm_version`、valid_period、layer_status。不複製、不修改幾何。
  - 德國那筆在 5/18 換段（Eupen-Malmedy），需注意。
  - 前段如要逐日疆界，也用同一做法取 5/10、5/15（荷蘭投降）、5/18、5/28（比利時投降）的日切片。
- **產出**：
  - `r8-borders.manifest.json`：`{date, regimes[{slug, recordId, ohmRelationId, ohmVersion, validPeriod, layerStatus}], fetchedFrom, fetchedAt}`
  - 腳本 `build_r8_manifest.py`。

### 共用檔
- `sources.json`：來源登記，每個來源附 grade 與 gradeBasis。
- `gaps.json`：查無或矛盾，格式沿用研究檔的 gaps。
- `phase-leadin.json`：前段 5/10–5/25 的階段說明，含日期出處。
- 全部檔案頂層加 `schema: "dunkirk-data/0.1"`、`researchedOn`、`gradePolicy: "ABC-named"`。

## 3. 推估標記與精度怎麼記

每一筆從地圖讀出的位置或前線頂點，都帶以下欄位：

| 欄位 | 內容 |
|---|---|
| `estimate` | 固定填「推估」。出處直接給地名的文字位置不標推估，但仍附 OSM 編號 |
| `basis` | `map-digitized`（地圖數位化）、`text-place`（文字地名）或 `text-vertices`（文字頂點） |
| `mapRef` | `{mapKey, citation, figure／facingPage, mapDate}`，精確到圖號或圖頁 |
| `method` | 配準方法（georef.py 二次多項式）、控制點數 |
| `precision_m` | 照 georef.py 算：留一法誤差 95 百分位加讀圖與標註框誤差。Ellis 圖比例較大，標註框誤差預估 5–10 km，波蘭圖用 20 km，待第一張圖實測後定 |
| `precisionNote` | 繁體中文一句說明精度來源 |
| `fit` | 該張圖的整體配準統計：殘差中位數、留一中位數、留一 95 百分位、可疑控制點 |

時間精度另記 `datePrecision`。態勢圖標的是「evening of」，記為 day，並在 note 寫「傍晚狀態」。

## 4. 指揮官對照（初步，以 key 比對；任期與部隊待 R1／R7 取出處後確認）

**已有 bio（將領研究檔 key → 開發庫 leader_bios）**

| 方面 | 人物 | key |
|---|---|---|
| 英方 | Gort | `johnvereker6thviscountgort` |
| 英方 | Brooke | `alanbrooke1stviscountalanbrooke` |
| 英方 | Alexander | `haroldalexander1stearlalexanderoftunis` |
| 英方 | Montgomery | `bernardmontgomery1stviscountmontgomeryofalamein` |
| 英方 | Ramsay | `bertramramsay` |
| 英方 | Dowding | `hughdowding` |
| 英方 | Park | `keithpark`（bio 已建，但段落全因禁用網域待補） |
| 法方 | Weygand | `maximeweygand` |
| 法方 | Gamelin | `mauricegamelin`（前段，5/19 去職） |
| 德方 | Brauchitsch | `walthervonbrauchitsch` |
| 德方 | Halder | `franzhalder` |
| 德方 | Rundstedt | `gerdvonrundstedt` |
| 德方 | Bock | `fedorvonbock` |
| 德方 | Kleist | `paulludwigewaldvonkleist` |
| 德方 | Kluge | `gunthervonkluge` |
| 德方 | Küchler | `georgvonkuchler` |
| 德方 | Guderian | `heinzguderian` |
| 德方 | Hoth | `hermannhoth` |
| 德方 | Rommel | `erwinrommel` |
| 德方 | Göring | `hermanngoring` |
| 德方 | Kesselring | `albertkesselring` |
| 德方 | Sperrle | `hugosperrle` |
| 德方 | Richthofen | `wolframvonrichthofen` |

- **庫內原有 bio（非將領研究檔）**：Leopold III（比軍總司令；Q12973 只當識別碼）。

**缺 bio（待補人物，初列）**

| 方面 | 人物 |
|---|---|
| 法方 | Blanchard（第 1 集團軍群）、Billotte（前段，5/23 歿）、Prioux（第 1 集團軍）、Abrial（北方海軍司令）、Fagalde（XVI 軍）、de la Laurencie（III 軍）、Molinié（里爾守軍） |
| 英方 | Pownall（BEF 參謀長）、Ronald Adam（III 軍）、Michael Barker（I 軍）、Tennant（敦克爾克海軍指揮官）、Wake-Walker（海上指揮）、BEF 各師師長 |
| 德方 | Reichenau（第 6 集團軍）、Reinhardt（XLI 裝甲軍）、Hoepner（XVI 裝甲軍）、Schmidt（XXXIX 軍）、各軍、師長 |

- 師級指揮官大多沒有 bio。R7 先只填 `bioStatus:"missing"`，名單交給主管排入生平流程。

## 5. 步驟與費用（本機 claude -p，sonnet）

| 步驟 | 內容 | 低 | 中 | 高 |
|---|---|---|---|---|
| 1 | 來源取得與登記：Ellis 各章、Gort 報告、Ramsay 全文、SHAT、MGFA 可用性；sources.json | $0.8 | $1.5 | $2.5 |
| 2 | R2：7＋3 張圖核對日期、授權、城鎮圓點；USMA 圖重抓；r2-maps.json | $0.5 | $1 | $2 |
| 3 | R1＋R7：名冊與指揮官（英、法、比、德到師） | $1.5 | $3 | $5 |
| 4 | R4＋R2 數位化：逐張做 readings.json（看圖讀像素＋OSM 控制點），跑 georef.py | $2 | $4 | $7 |
| 5 | R3、R5、R6：文字位置、交戰、易手日 | $1.5 | $3 | $5 |
| 6 | R8 manifest 腳本（唯讀）＋前段階段說明 | $0.3 | $0.8 | $1.5 |
| 7 | 自檢：verify 類腳本（等級、禁用網域、引文長度、推估欄位）、交叉比對、報告 | $0.5 | $1 | $2 |
| | **合計** | **$7.1** | **$14.3** | **$25** |

- 每步完成就 commit，不寫庫、不 push。寫庫另行授權。
- 步驟 3 與 4 可平行，其餘依序。

## 6. 風險

- **A／B 才進庫的 schema 限制**：battle_* 引文表的 CHECK 只收 A／B（ARCHITECTURE §19 表 4）。具名 C 只能留在 seed，進庫需另做 migration（見 Q1）。
- **配準可行性**：Ellis 圖如果城鎮圓點太少，控制點不足，精度會很差。第一張圖試做後才知道實際精度。
- **法、比、德方原始資料取得難**：SHAT《historiques succincts》、MGFA 原書、德軍 Lagekarten（Bundesarchiv 或 NARA 微縮）可能拿不到全文，法、德方師級資料可能缺；比軍資料最弱。
- **轉錄站依賴**：Ellis 經 HyperWar（ibiblio，已歸類 official_history A，內容為官方戰史轉錄）取用，頁碼以轉錄標記為準。版本年份 1953／1954 矛盾仍待核。
- **USMA 圖下載**：上次遇到 TLS 錯誤。不使用 curl -k，改找官方 S3 網址。
- **示例資料污染**：展示頁的 45 單位、19 交戰源自維基百科，只能當候選線索，不能沿用任何欄位值。
- **人物缺口**：師級指揮官多數無 bio，R7 的人物對照比例會偏低。
- **費用**：圖像判讀（步驟 4）成本波動最大。

## 7. 待主管決定

1. **具名 C 級**：戰役資料要收具名 C 嗎？需求清單寫 A／B，主管規則寫 A／B／具名 C。若收，是否同意日後為 battle_* 引文表做跟生平同樣的 C 級 migration，或 C 只留在 seed？
2. **推估座標**：需求清單寫「不要給推估座標」，主管規則是地圖數位化標推估加精度。是否確認採後者，並同時保留 OSM 編號？
3. **USMA 戰史圖集的等級**：A（軍方圖集）還是 B？研究檔原寫「建議 B，待決」。
4. **層級範圍**：海軍（艦艇、Ramsay 的撤退船隊）與空軍（RAF 11 Group、Luftflotte 2、VIII Fliegerkorps）要不要進 R1？建議只列指揮層級，不列艦艇和中隊。
5. **比軍**：如果查不到 A／B 師級來源，比軍是否只做到軍級？
6. **缺 bio 的指揮官**：是否另排一批將領生平研究（初列約 20 位，含師長會更多）？還是 R7 先留空？
7. **前段 5/10–5/25 的逐日疆界**：只取 5/10 一個切片，還是加 5/15、5/18、5/28 的切片？
8. **Ellis 版本年份**：1953 還是 1954，以哪個為準（研究檔 gap）？戰役名稱「Battle of Dunkirk」的 A／B 出處缺口要不要在本輪一併處理？

## 本機開發庫寫入（2026-11-13 20:50，Tai 20:43 同意）

- 範圍：只有 dunkirk_1940，只寫 5442/worldline_borders_dev；寫入前備份 `~/wl-db-backups/worldline_borders_dev-20261113-205020-pre-dunkirk1940.dump`（sha256 229be178…8a3935）。
- 工具：`tools/battles/write_battle_sql.py dunkirk_1940`（產生 SQL）→ `tools/battles/db_write.py dunkirk_1940`（dry-run，ROLLBACK）→ `--apply`（COMMIT）。報告見 `db/`。
- 寫入列數：historical_events 1、battle_profiles 1（pending）、battle_profile_citations 5、event_participants 4、battle_phases 6、battle_phase_citations 14、battle_map_features 65（27 條 source_map 前線、38 個 source_text 地點）、battle_map_feature_citations 88、battle_units 64、battle_unit_citations 82、sources 3（Ellis、Gort、Ramsay）。
- 全部 status=pending、verified=false；只寫 A/B 引文，NDB（C 級）沒有寫進去。
- 跳過 16 筆（12 個交戰：候選、序幕、Calais；3 個部隊；1 個控制點 Soex），清單見 `db/dunkirk_1940.write-plan.json`。
- 22 位沒有傳記的指揮官只標 gap（gaps.json，kind=commander_missing_bio，新增 21 筆，另 1 筆原本就有），不補。
- 第二輪地圖判讀的 87 個待查證標籤沿用原本的標記。
- API 版本目前沒有箭頭（研究資料裡沒有 A/B 引文支持的箭頭）。
