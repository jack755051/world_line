# Historical Data Governance

World Line 的價值取決於史料可追溯性，而不只是 schema 能接受資料。本文件定義正式歷史資料的最低建檔與修訂標準，落實業務憲法的中立性、時間不確定性與 I1-I5。

## 適用範圍與目前限制

本規則適用於政權、疆域、年號、政權關係、歷史事件、觀察視角與爭議資料。

`SeedData.cs` 的漢／魏／蜀漢／吳／晉資料只用來驗證 schema、FK、時間區間與轉換關係：矩形疆域、簡化年份和敘述不可當成正式史料發布。

目前 schema 尚未為所有政權與疆域記錄提供結構化 citation 關聯。**在補上 citation/source model 前，不應開始不可逆的大量正式資料匯入。** 可以做研究與轉換 prototype，但必須把來源保留在可回填的 staging 資料中。

## 最低來源紀錄

每筆正式資料至少要能追溯到下列資訊；若多個來源共同支持同一結論，逐一記錄：

| 欄位 | 要求 |
|---|---|
| Title | 書名、論文名、資料集或檔案名稱 |
| Author/Publisher | 作者、研究機構或發布單位 |
| Version/Published at | 版本、出版年或資料集 release |
| Locator | ISBN、DOI、stable URL、archive ID、頁碼或圖層名稱 |
| License | CC0、CC BY、NC 限制或其他使用條款 |
| Accessed at | 線上來源的查閱日期 |
| Evidence note | 此來源支持哪個名稱、時間、幾何或觀點，以及必要的轉換說明 |

搜尋結果摘要、未保存來源的 AI 回答或無法定位的二手轉述，不能單獨作為正式資料依據。

## 來源與授權

- OpenHistoricalMap 可作主要開放資料來源，但匯入時仍需保存資料版本與取得日期。
- CHGIS 與 CShapes 只能在其非商業／學術授權允許的情境下使用；資金或發布模式改變時必須重新檢查。
- GeaCron 僅能作 UX 參考，不作資料來源。
- 不同授權來源混合成衍生幾何前，要確認 attribution、share-alike 與散布限制。
- 無法確認授權的資料只可留在隔離的研究區，不得進入可發布資料集。

授權結論的產品決策以 PRD §5/§9 為準；本文件規範逐筆如何保存證據。

## 名稱與觀察視角

- `regimes.self_name` 保存政權自稱，是建立政權的必要條件（I2）。
- 他稱放在 `regime_aliases`，必須連回自稱政權（I4）。
- 能辨認命名者時填 `observer_regime_id`；不能辨認時才能使用通用他稱。
- 「朝代／帝國／國家」是觀察視角，不得偷放成政權不可變的固定分類。
- 古地名優先顯示，現代地名只作對照；不要用現代行政疆界反推古代認同。

## 時間精度

### 疆域與持續關係

`regime_territories.valid_period` 與 `regime_relations.valid_period` 使用年精度 `int4range`。目前 seed 與應用慣例採半開區間 `[start, end)`：start year 包含、end year 不包含。若史料寫「存續至 220 年底」，轉換時必須明確決定是否存成 `[start, 221)`，並在 evidence note 保留原始說法；不可只看數字猜測 inclusive/exclusive。

疆域快照密度由史料支持的變動事件驅動，不固定逐年建立，也不能因 UI 想要平滑動畫而虛構中間邊界。

### 歷史事件

- `start_edtf`／`end_edtf` 保存原始時間語意，是 single source of truth。
- `start_decimal`／`end_decimal` 由後端解析 EDTF 後產生，不人工分別填寫。
- 年、月、日、約略 `~`、不確定 `?` 與區間必須在 UI 保留原精度，不可補成看似精確的日期。
- BCE、無西元 0 年與閏年案例必須由 M2 的 EDTF 測試固定行為。

### 年號

`reign_eras.start_year`／`end_year` 是顯示與查詢用的西元映射。建立年號時需記錄登基／改元等邊界採用的史料規則；同一年內多次改元不能只靠 year 欄位假裝精確，必要時應連到具日期精度的 historical event。

## 幾何資料

- 政權疆域使用 `MultiPolygon`、WGS84、SRID 4326。
- 匯入前要驗證 geometry 非空、座標系正確、ring 合法，並記錄簡化或修補工具與參數。
- 海岸線、河道與現代底圖只是定位輔助；不能讓現代精確邊界造成古代疆域也同樣精確的錯覺。**2026-08-31 落地（任務 3.17）**：`app/src/app/map/map.ts` 疊了一層 Natural Earth 1:50m 陸地色塊當地理方位參考，只用單一中性色平塗（`--wl-map-land`），沒有任何額外細節（河流/等高線/現代國界都沒有），視覺重量刻意壓低到明顯次於政權疆域填色，避免使用者把「陸地形狀畫得比較精確」誤讀成「疆域範圍也一樣精確」——這批陸地資料本身是現代測量成果，跟古代政權的疆域紀錄是兩個不相關的精度來源，不能混為一談。
- 有爭議或來源互相衝突的疆域可並存，但必須標記 `is_disputed`，並分別保存支持來源。
- TopoJSON/Flubber 產生的中間形狀是視覺插值，不得寫回資料庫冒充史料快照。

## 客觀骨幹、觀點與爭議

- `historical_events` 只放可交叉核對的客觀骨幹。
- 當事政權或後世史學敘事放在 `historical_event_perspectives`，並標明 regime 或受控 observer category。
- 尚無共識的問題放在 `historical_event_controversies`，neutral description 不替任一方下結論。
- 傷亡數字、正當性敘述與命名爭議保留「誰主張什麼」，不要合併成沒有來源的單一真值。
- `viewpoints`／`primary_sources` 目前是 JSONB；正式匯入前需定義 JSON schema 或標準化 citation model，避免每筆資料格式不同。

## 修訂與版本保留

I5 要求正式史料不能直接覆蓋刪除。疆域修訂流程應為：

1. 建立新的 replacement row。
2. 在原 row 的 `superseded_by` 指向新 row。
3. 填寫 correction reason、時間與支持來源。
4. 查詢預設回傳最新有效版本，但保留追溯完整鏈的能力。

這套流程要在 M2 API 層強制；目前 schema 只有欄位與 FK，尚未阻止直接 UPDATE/DELETE。修正已被修正過的資料時，多層鏈與併發規則尚需在實作前拍板。

## 正式資料進入主資料庫前的檢查表

- [ ] 自稱與所有他稱的觀察者關係清楚。
- [ ] 每個時間值保留原始精度與區間語意。
- [ ] 每個幾何有來源、版本、授權與轉換紀錄。
- [ ] 爭議資料已標記並保留相互衝突的來源。
- [ ] 客觀事件、主觀敘事與爭議點沒有混在同一欄位。
- [ ] 不包含 seed 的示範矩形或簡化年份。
- [ ] 修訂採版本鏈，不覆蓋舊資料。
- [ ] 授權允許目前的使用與發布方式。
- [ ] 至少一位非原建檔者或未依賴同一摘要的 review 流程完成；單人階段可用延時複核與來源逐項核對代替。
