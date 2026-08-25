---
schema_version: 1
feature_id: world-line
feature_name: World Line — 歷史地圖 GIS 平台
status: draft
owner: jack755051@gmail.com
last_updated: 2026-08-25
related_constitution: .claude/constitutions/world-line.md
related_adrs: []
---

# PRD: World Line — 歷史地圖 GIS 平台

> ⚠️ 本 PRD 基於 `.claude/constitutions/world-line.md` 產出。憲法本體的業務規則（R1-R3）、狀態機（§4）、不可變約束（I1-I5）已具備足夠明確度可作為 PRD 依據。若後續憲法內容變動，本 PRD 需重新走過 `prd-from-constitution` delta 比對流程。
>
> **2026-08-25 更新（第三輪，delta 比對）**：憲法 frontmatter `status` 已由 `draft` 拍板為 `active`，§10 原始 4 條開放問題全數解決（回填至憲法 §2 角色職責、§4 傳承關係鏈、§6 正式朝代/政權間互動術語）。經逐項比對，這些內容與本 PRD 既有的角色權限說明（§2）、方案 D lineage_presets 設計（§6）、historical_events/regime_relations 拆分（§6）**完全一致，無需修改對應段落**——本輪僅同步移除過時的「憲法尚未拍板」警語。
>
> **2026-08-25 更新（第一輪）**：透過 `/grill-me` 對本 PRD 逐項壓力測試，拍板了 12 項技術選型與資料模型決策（PostGIS 安裝方式、正式朝代分類、政權互動建模、事件多維度拆分、地圖引擎、資料供應策略、狀態機函式庫、紀年轉換、EDTF 解析、多重視角觀察者、斜線網底、開源資料授權），內容已回填至 §5/§6/§9/§12。
>
> **2026-08-25 更新（第二輪）**：延續 grill-me 訪談，再拍板 5 項：開發者/使用者角色職責、Auth 機制、設計交付模式、技術效能量化指標處理方式、XState 前後端狀態機驗證分工，內容已回填至 §2/§5/§7/§8/§9/§12。剩餘未拍板：僅剩「CHGIS/CShapes 授權於資金來源變動時需重新確認」一項（低優先，見 §9/§12），其餘全數定案。

## 1. 背景 (Background)

傳統歷史知識透過書本傳遞時，是依「單一視角、按時間軸拆解」的方式敘述——例如以中國視角敘述唐朝歷史，便難以同步呈現同一時期阿拉伯帝國（大食）、歐洲政權的並行發展與互動關係。World Line 的核心動機（對應憲法 §1 業務目的、§7 Decision 1）是以 GIS／地圖取代這種單一視角敘事，讓使用者能夠「縱覽世界」：在同一個時間點上同時看到多個文明/政權的疆域與互動，並在需要時聚焦到單一政權觀察其與同時期周邊政權的關係（憲法 R2、R3）。

專案目前處於「先給自己（開發者本人）使用，後續再考慮教育用途」的階段（憲法 §1），尚未有任何業務程式碼——`app/`（Angular 22 scaffold）與 `api/`（.NET 10 Web API scaffold，僅 `WeatherForecast` 預設 controller）都是 CLI 預設輸出，`docker-compose.yml` 已備妥 frontend/backend/postgres/redis 四個 service 的容器編排骨架。本 PRD 是本專案第一份正式功能規格文件，銜接憲法與後續實作。

## 2. 目標 (Goals)

- **業務目標**：
  - 依憲法 §1 階段實施順序，優先完成「中國史」政權/疆域資料的地圖化呈現，作為第一階段可用產品；後續依序擴充至「世界史」（多文明並存，對應 R2）與「單一國家史」（如台灣史）。
  - 服務對象階段性明確：第一階段僅需滿足開發者本人（使用者自己）的使用需求，教育用途為後續階段目標，非本 PRD 範圍內的驗收標準。
  - **角色與權限**（已拍板，grill-me 2026-08-25 第二輪）：開發者（使用者自己）＝可寫可讀，擁有新增/修正政權與疆域資料的職責（對應憲法 I5 史料修正機制）；使用者（含未來教育對象）＝純唯讀，僅能瀏覽/查詢，無資料編輯權限。呼應憲法 §1「先給自己再給教育」的階段順序，落地為 §7 API 契約的權限設計依據。
- **技術目標**：暫不設定量化數字（如 p95 latency、併發使用者數、資料量體規模）——已拍板（grill-me 2026-08-25 第二輪），因第一階段僅開發者單人自用，無併發壓力，設定具體數字無實質意義。改採質化驗收標準：時間拉桿拖動、地圖疆域渲染需「操作流暢、無明顯卡頓」；待進入世界史階段或有實際效能瓶頸時，依實測數據回填具體指標（標記待補，非永久排除）。
- **使用者目標**：
  - 使用者可透過時間拖拉桿連續拖動觀察疆域隨時間連續變化（非離散跳轉），呼應憲法 §9「類似氣象雲圖」的體驗期待。
  - 使用者可「縱覽世界」——在同一時間點同時檢視多個政權的疆域並存狀態（對應 R2）。
  - 使用者可聚焦單一政權，檢視該政權與同時期周邊政權的互動關係（對應 R3）。

## 3. 範圍 (Scope) vs 非範圍 (Non-Goals)

### ✅ 範圍

- [ ] 第一階段（中國史）政權與疆域資料的建置與地圖呈現，粒度僅到「朝代/國家」層級，**不含城市層級**（對應憲法 R1：「第一階段只呈現到朝代/國家層級，如果完成宏觀的史觀後再繼續深入到城市的發展」）
- [ ] 時間拖拉桿驅動的疆域連續變化呈現（對應憲法 §9）
- [ ] 多政權同時並存檢視（對應 R2：唐朝＋阿拉伯帝國＋歐洲政權疆域並列）
- [ ] 政權聚焦檢視與同時期周邊政權互動呈現（對應 R3）
- [ ] 政權命名視角切換機制（自稱／他稱代稱，可追溯回自稱本體，對應憲法 §6、I4）
- [ ] 政權狀態機呈現（存續／分裂／被取代-禪讓／被滅亡，對應憲法 §4，兩種終止狀態不可合併）
- [ ] 史料修正的版本保留機制（類 git，保留原版本＋時間戳＋原因，對應憲法 §5 I5、§8）
- [ ] 模糊／爭議年份區間的呈現與查詢（對應憲法 §9）

### ❌ 非範圍（明確不做，避免 scope creep）

- ❌ **遊戲化虛構劇情**（永久排除，憲法 §1 原話：「不做遊戲化虛構劇情」）
- ❌ **未來推測**（永久排除，憲法 §1 原話：「也不做未來推測」）

> ⚠️ **史前歷史不屬於上述兩項同類的「永久排除」**，而是**階段性延後**——憲法 §1 原話：「史前歷史先等整個完成後再處理」。本 PRD 第一階段（中國史）與後續世界史/單一國家史階段皆不含史前歷史，但此排除性質是「本階段尚未排入」，不可視為與遊戲化劇情/未來推測相同性質的永久業務邊界，未來可能重新評估納入時程。

- ❌ 城市層級的疆域/政區細節（第一階段範圍外，待 R1 宏觀史觀完成後才評估，對應憲法 R1）
- ❌ 宗教／語言／科技／文化／疾病／飲食等主題的傳播與分合呈現（憲法 §1 明確標註為「後續擴充意圖」，非本階段範圍）

## 4. 使用者故事 (User Stories)

### Story 1: 多政權並存檢視（對應 R2）

- **As a** 使用者
- **I want to** 拖動時間拉桿到西元 7-8 世紀
- **So that** 我可以同時在地圖上看到唐朝、阿拉伯帝國（大食）與同時期歐洲政權的疆域並列呈現，而非只看單一政權的敘事

**Acceptance Criteria**:
- [ ] Given 時間拉桿停在西元 700 年，when 頁面渲染地圖，then 唐朝、阿拉伯帝國、同時期歐洲政權的疆域圖層應同時顯示於同一張地圖上
- [ ] Given 時間拉桿連續拖動（例如從西元 650 年拖到 750 年），when 拖動過程中，then 各政權疆域應呈現連續形變過渡動畫，而非離散跳轉切換（對應憲法 §9）
- [ ] Given 某一年份沒有任何政權疆域資料（資料缺漏），when 使用者拖到該年份，then 地圖應顯示空狀態提示（而非報錯或顯示錯誤年份資料）

### Story 2: 政權聚焦與周邊互動（對應 R3）

- **As a** 使用者
- **I want to** 點擊聚焦某個政權（例如唐朝）
- **So that** 我可以看到該政權在該時段與周邊其他政權的互動關係，而不需要切換到其他敘事視角

**Acceptance Criteria**:
- [ ] Given 使用者點擊地圖上的唐朝疆域，when 觸發聚焦模式，then 地圖應高亮唐朝疆域並列出同時期周邊政權清單
- [ ] Given 已進入聚焦模式，when 使用者拖動時間拉桿，then 聚焦政權的存續區間應被高亮標示，超出存續區間時應提示「此政權於該時間點尚未建立/已不存在」
- [ ] Given 聚焦政權與周邊政權之間存在已建檔的離散互動事件（如戰爭、條約），when 顯示互動清單，then 應列出可點擊追溯至對應 `historical_events` 記錄的入口；若是持續性關係（如貿易、朝貢），則列出對應 `regime_relations` 記錄的入口（已拍板，見 §6）

### Story 3: 觀察視角切換與名稱可追溯性（對應憲法 §6 命名機制、I4）

- **As a** 使用者
- **I want to** 切換「全球客觀視角」與「聚焦唐朝視角」
- **So that** 我能看到政權名稱依觀察視角動態改變（例如阿拉伯帝國在唐朝視角下顯示為「大食」），同時仍能追溯回其自稱本體

**Acceptance Criteria**:
- [ ] Given 使用者處於全球客觀視角，when 地圖渲染政權標籤，then 應顯示各政權自稱名稱（憲法 I2：政權建立必須有自稱名稱）
- [ ] Given 使用者切換為「聚焦唐朝視角」，when 地圖渲染同時期的阿拉伯帝國，then 標籤應顯示唐朝視角下的代稱「大食」，且點擊/hover 後可追溯回「阿拉伯帝國」自稱本體（對應 I4：他稱代稱不可為孤兒資料）
- [ ] Given 某政權存在他稱代稱資料，但找不到對應的自稱政權本體，when 系統載入資料，then 應視為資料完整性錯誤並阻擋顯示（I4 硬約束，不可容忍孤兒代稱資料上線）

### Story 4: 政權狀態轉換呈現（對應憲法 §4 狀態機）

- **As a** 使用者
- **I want to** 拖動時間拉桿經過政權分裂/被取代/被滅亡的轉折年份（例如漢朝末年到三國時期）
- **So that** 我能清楚看到政權狀態轉換的過程，並區分「被取代（禪讓）」與「被滅亡」這兩種不同性質的終止方式

**Acceptance Criteria**:
- [ ] Given 時間拉桿拖到政權分裂年份，when 地圖渲染，then 應同時顯示分裂後的多個新政權疆域（例：漢朝→曹魏／蜀漢／東吳三個獨立疆域區塊）
- [ ] Given 某政權以「被取代（禪讓）」方式終止（例：曹魏→西晉），when 顯示該政權狀態，then UI 呈現方式須與「被滅亡」（例：蜀漢被曹魏滅亡）在視覺/文字上明確區分為兩種不同狀態，不可合併呈現（憲法原話：「取代跟消滅應該是兩種不同的定義」）
- [ ] Given 系統呈現政權列表的預設「主線」視圖，when 使用者未指定特定史觀，then 依 `lineage_presets` 中的預設 preset（例：「傳統教科書史觀」，內含漢→曹魏→西晉序列）顯示主線；蜀漢/東吳等分裂期政權仍完整存在於資料庫，可在細節模式中查看（方案 D，已拍板，見 §6）

### Story 5: 模糊／爭議年份的呈現與查詢（對應憲法 §9、notes EDTF 設計）

- **As a** 使用者
- **I want to** 查詢一個只有模糊年份記載的歷史事件或政權疆域（例如武王伐紂的推測年份）
- **So that** 我能理解該時間資訊的不確定性，而不是被系統誤導成精確日期

**Acceptance Criteria**:
- [ ] Given 某筆疆域/事件資料的時間僅精確到年或世紀（EDTF 如 `0755`），when 呈現該資料的時間標籤，then UI 應明確標示精度層級（年/月/日），不可偽裝成比實際史料更精確的日期
- [ ] Given 某筆事件時間帶有不確定標記（EDTF `?` 如 `1046?`），when 呈現該事件，then UI 應顯示「推測年份」等不確定性提示
- [ ] Given 使用者查詢某一年份範圍內的資料，when 該年份落在某疆域紀錄的模糊區間內，then 該筆資料應被視為符合查詢條件納入結果（允許區間匹配，對應憲法 §9「允許區間」）

## 5. 技術選型 (Tech Stack)

> 分兩類：**A. 既有專案技術棧（已定案沿用）**——依 4 層優先級偵測，`app/package.json`、`api/WorldLine.Api.csproj`、`docker-compose.yml` 已有明確版本鎖定，優先權高於 sanring 通用預設。**B. GIS 領域專屬技術（候選，待選型）**——來自 `.claude/notes/world-line-tech-candidates.md`，屬於「非正式輸入素材」，尚未經使用者拍板，僅供本階段規劃參考，最終選型須於 §12 Open Questions 對應項目確認後定案。

### A. 既有技術棧（已定案沿用）

| 層 | 選型 | 理由 |
|---|---|---|
| Frontend | Angular ^22.1.0 | 既有專案偵測（`app/package.json`），CLI scaffold 已存在，沿用 |
| Backend | .NET 10 Web API（`net10.0`） | 既有專案偵測（`api/WorldLine.Api.csproj`），CLI scaffold 已存在，沿用 |
| DB | PostgreSQL 16（`postgis/postgis:16-3.4` 映像檔） | **已拍板（grill-me 2026-08-25）**：`docker-compose.yml` 的 postgres image 由純 `postgres:16-alpine` 改為 `postgis/postgis:16-3.4`，一行改動即取得 PostGIS extension，維護成本低於自建 init script，列入 M1 前置工作 |
| Cache | Redis 7-alpine | 既有專案偵測（`docker-compose.yml`），已備妥容器 |
| Auth | 單一 API Key/JWT（僅保護寫入端點） | **已拍板（grill-me 2026-08-25 第二輪）**：讀取端點（GET）第一階段不加限制；寫入端點（POST/PATCH）加最小驗證，避免 `docker-compose.yml` 已備妥容器隨時可能部署到內網/雲端後，寫入端點完全裸露被任意竄改/刪除史料（違反 I5 版本保留精神）。日後開放多使用者/教育對象時，讀取端點是否也要驗證再重新評估 |
| Deploy | Docker Compose | 既有專案偵測，frontend（Nginx，4200→80）/ backend（8080→5000）/ postgres（5432）/ redis（6379）四 service 已編排完成 |
| 監控 | TODO | 尚未評估，憲法/notes 未提及 |

### B. GIS 領域專屬技術

> 以下標「**已拍板**」的項目，均經 2026-08-25 `/grill-me` 逐項壓力測試後確認；標「候選」者未在本輪討論，維持待評估狀態。

| 層 | 選型 | 對應需求 | 狀態 |
|---|---|---|---|
| 地圖引擎 | MapLibre GL JS | 全球政權圖層渲染、時間過濾器（Filter Expressions） | **已拍板：Phase 1 單獨使用**。Deck.gl 保留為後續可疊加選項，待動畫流動效果（絲路貿易路線、傳播視覺化等）出現實際需求時再加，兩者設計上可疊加不衝突 |
| 高階視覺化 | Deck.gl（搭配 MapLibre） | 貿易路線/行軍路線/傳播軌跡等進階圖層 | **已拍板：Phase 1 不導入**，明確保留為後續疊加選項（見上） |
| 圖資壓縮與形變 | TopoJSON + Flubber.js | 疆域邊界共享壓縮、連續變化過渡動畫（對應憲法 §9） | 候選，未在本輪討論，維持待評估 |
| 空間幾何分析 | Turf.js | 政權標籤置中點計算、邊界簡化 | 候選，未在本輪討論，維持待評估 |
| 政權狀態機 | XState | 存續/分裂/被取代/被滅亡狀態防呆（對應憲法 §4） | **已拍板：Phase 1 就導入**（使用者選擇一步到位，非採用建議的簡單 enum 方案，理由：避免後續遷移成本）。**驗證分工（grill-me 2026-08-25 第二輪追加拍板）**：前端 XState 僅負責 UI 層防呆與進度圖顯示；後端 C#（.NET，與 XState 不同語言無法直接共用同一份 library）獨立實作同一套合法轉換規則作為唯一信任來源，防止 API 被繞過前端直接呼叫寫入非法狀態轉換。雙方均以憲法 §4 列出的合法轉換規則（存續→分裂／存續→被取代禪讓／存續→被滅亡）作為 SSOT 文件依據，日後憲法 §4 若修訂需同步更新前後端兩份實作，避免規則飄移 |
| 紀年轉換 | 自建 `reign_eras` 查詢表 | 西元 ↔ 年號/廟號（武德、開元、日本昭和、民國年等）雙向映射（對應憲法 §9 多重紀年） | **已拍板：自建查詢表，不使用 `lunar-javascript`/`cnlunar`**——這兩個套件處理的是農曆換算，跟「年號查詢」是不同問題；憲法 §9 需求本質是一張「年號-政權-起訖年」查詢表，不是曆法計算 |
| 時間格式化 | Dayjs/Luxon + 自訂 BCE 擴充 | 處理無西元 0 年、負數年份；EDTF decimal 計算時用來正確處理閏年天數 | 候選，未在本輪討論，維持待評估 |
| 向量切片服務 | Martin（Rust）或 Tegola | 直連 PostGIS 動態切 MVT，避免巨量 GeoJSON 卡頓 | **已拍板：Phase 1 不導入**，Phase 1 用純 GeoJSON（見下），Phase 2 若遇全球渲染效能瓶頸再評估導入 |
| 靜態離線切片 | PMTiles | 單檔金字塔圖磚，適合離線/靜態主機 | **已拍板：Phase 1 不導入**，待出現具體離線/純靜態部署需求再評估 |
| 資料供應策略 | 純 GeoJSON | 後端直接回傳幾何資料，前端直接渲染 | **已拍板：Phase 1 採用**。理由：R1 範圍（中國史、朝代/國家層級）政權數量與疆域幾何複雜度可控，純 GeoJSON 已足夠，不需額外架設 Martin/Tegola 增加維運負擔；Phase 2「世界史」需同時渲染全球大量政權疆域，若遇效能瓶頸再回頭導入 MVT 動態切片；PMTiles 待「離線/純靜態部署」具體需求出現再評估 |
| EDTF 時間解析 | npm `edtf` | 精確到日/月/年/模糊區間的人類語意時間格式解析（對應憲法 §9、notes §五） | **已拍板：使用現成套件**，不自建正則解析器（EDTF 規格邊界情況多，如不確定標記 `?`、約略標記 `~`、開放區間、負數西元前年份，自建風險大於收益）；寫入時後端強制驗證格式；`start_decimal`/`end_decimal` 由後端寫入當下自動推算（EDTF 字串為 single source of truth，不手動分別填兩欄；閏年天數由標準日期函式庫正確處理，不需另外設計誤差公式） |
| GIS 資料庫擴充 | PostGIS extension（`postgis/postgis` 映像檔） | `GEOMETRY(MultiPolygon, 4326)` 儲存政權疆域、`int4range` 時間區間索引（GiST 複合索引） | **已拍板**，見上方 DB 列 |
| 歷史地理原始資料 | OpenHistoricalMap（主要來源）＋ CHGIS／CShapes（輔助，僅限非商業情境） | 繪製政權疆域 GeoJSON 骨幹的資料來源 | **已拍板（grill-me 2026-08-25，含實際授權查證）**：OHM 為 CC0 公眾領域，作主要來源；CHGIS 僅限學術非商業使用，CShapes 為 CC BY-NC-SA 4.0（禁商業＋需 ShareAlike），兩者僅能在非商業情境使用；GeaCron 查無明確公開授權，**只作 UX 互動設計參考，不當資料來源**。⚠️ 使用者確認目前無商業化/收費計畫；若未來出現贊助/政府投資等資金來源，需重新確認 CHGIS/CShapes 的 NC 授權相容性（詳見 §9 風險） |
| 斜線網底配色 | 集中共用常數檔（非正式 Design Token 系統） | 爭議控制區（notes §十）視覺呈現一致性 | **已拍板：Phase 1 用單一共用常數檔**（如 `neutral-map-colors.ts`）集中管理顏色/間距，不建置正式 Design Token pipeline；待深色模式或多人協作需求出現再升級 |

## 6. 資料模型 (Data Model)

> 依憲法 I1-I5 設計政權/疆域 schema 骨幹，並整合 notes `historical_events` / `historical_event_perspectives` / `historical_event_controversies` 作為事件圖層。**2026-08-25 grill-me 更新**：憲法 §10「正式朝代 vs 子朝代/分裂政權」分類問題已拍板解法（非直接分類欄位，見下方方案 D 說明），政權互動、事件多維度拆分、多重視角觀察者等 schema 設計也一併定案，取代原本的 TODO 留白。

### 設計原則（grill-me 拍板摘要）

- **政權轉換邊是客觀事實，「正式朝代」標籤是史觀立場**：`regimes` 表只記錄禪讓/滅亡/分裂這些客觀發生過的轉換動作，不判斷誰是「正統」。「主線敘事」（例如傳統教科書史觀的漢→魏→晉→⋯⋯序列）改用獨立的 `lineage_presets` 表承載，明確標註是哪一種史觀，可並存多個 preset，核心政權圖保持中立（方案 D）
- **政權互動依「離散事件」vs「持續關係」拆兩張表**：戰爭/條約/會戰這類有明確起訖的事件進 `historical_events`；絲路貿易、朝貢、和親這類沒有單一時間點、更像持續狀態的關係進 `regime_relations`
- **事件本身有三個獨立維度**：時間長短由既有 EDTF 區間表達（不需新欄位）；類型（戰爭/貿易/革命/改革）用多對多標籤（不用單一 enum，因為像明治維新這種事件常同時橫跨多個類型）；組成關係（大戰爭包含小戰役）用 `parent_event_id` 自我參照，這個父子結構同時也是 notes §六語意縮放（Semantic Zooming）的資料基礎——年級尺度只顯示頂層事件，日/月級尺度才展開子事件
- **多重視角的「觀察者」不一定是政權**：`historical_event_perspectives.regime_id` 維持 nullable FK（給當事政權用），非政權主體（國際第三者、後世史學界等）改用受控的 `observer_categories` 對照表，不用自由文字，避免同一概念打出不同拼法

### Schema 變動

```sql
-- 政權主體（I2：自稱名稱必填才能建立）
CREATE TABLE regimes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  self_name VARCHAR(128) NOT NULL,              -- 自稱名稱（I2 硬約束，例："唐"、"阿拔斯王朝"）
  status VARCHAR(32) NOT NULL,                  -- 存續 / 分裂 / 被取代(禪讓) / 被滅亡（憲法 §4 狀態機）

  -- 轉換邊（客觀事實層，方案 D：不判斷正統，只記錄發生過的轉換動作）
  predecessor_regime_id UUID REFERENCES regimes(id),  -- 因「分裂」或「被取代(禪讓)」而來的前身政權；獨立建國則為 NULL
  origin_transition_type VARCHAR(16),                 -- '分裂' | '被取代禪讓' | NULL（獨立建國，無前身）
  destroyed_by_regime_id UUID REFERENCES regimes(id), -- 若 status='被滅亡'，記錄消滅方政權；其餘狀態為 NULL

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  version INT DEFAULT 0                          -- 樂觀併發
);

-- 史觀主線 preset（方案 D：把「正式朝代」這種立場判斷從核心政權圖移出來，變成明確標註來源的獨立呈現層）
CREATE TABLE lineage_presets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  preset_name VARCHAR(128) NOT NULL,            -- 例："傳統教科書史觀"、"蜀漢正統論史觀"
  description TEXT,                             -- 這個 preset 代表哪一種史觀立場、由誰／依據什麼提出
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE lineage_preset_members (
  preset_id UUID NOT NULL REFERENCES lineage_presets(id),
  regime_id UUID NOT NULL REFERENCES regimes(id),
  sort_order INT NOT NULL,                      -- 在這個 preset 顯示序列中的順序
  PRIMARY KEY (preset_id, regime_id)
);

-- 政權間持續性關係（絲路貿易、朝貢、和親、同盟、敵對等，跟「離散事件」性質不同）
CREATE TABLE regime_relations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  regime_a_id UUID NOT NULL REFERENCES regimes(id),
  regime_b_id UUID NOT NULL REFERENCES regimes(id),
  relation_type VARCHAR(32) NOT NULL,           -- 貿易 / 朝貢 / 和親 / 同盟 / 敵對 ...
  valid_period INT4RANGE NOT NULL,              -- 關係存續的時間區間（同 I1 精神，時間區間必填）
  route GEOMETRY(MultiLineString, 4326),        -- 可選：關係對應的路線（例：絲路貿易路線）
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 政權他稱代稱（I4：必須可追溯回自稱本體，不可為孤兒資料）
CREATE TABLE regime_aliases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  regime_id UUID NOT NULL REFERENCES regimes(id), -- FK 強制約束，落實 I4
  observer_regime_id UUID REFERENCES regimes(id),  -- 給予此代稱的觀察視角主體（例：唐朝視角下稱阿拉伯帝國為"大食"），可為 NULL 代表通用他稱
  alias_name VARCHAR(128) NOT NULL,               -- 例："大食"、"拂菻"
  alias_type VARCHAR(32),                         -- TODO：朝代/帝國/國家三種觀察視角標籤如何落地成欄位值，憲法 §6 術語表定義為「觀察視角產物」而非固定屬性，schema 設計方式待 PRD 下一輪或實作階段細化
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 政權疆域（I1：時間區間必填才能存在；I5：修正保留版本歷史不可覆蓋刪除）
CREATE TABLE regime_territories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  regime_id UUID NOT NULL REFERENCES regimes(id),
  valid_period INT4RANGE NOT NULL,                -- I1 硬約束，例：'[618, 907]'
  geom GEOMETRY(MultiPolygon, 4326) NOT NULL,      -- 需 PostGIS extension（見 §5 風險）
  is_disputed BOOLEAN DEFAULT FALSE,               -- 對應 I3：爭議並存標記
  superseded_by UUID REFERENCES regime_territories(id), -- I5：指向修正後的新版本，本列不刪除、不覆蓋
  correction_reason TEXT,                          -- I5：修正原因（史料修正機制，憲法 §8「類 git」）
  corrected_at TIMESTAMPTZ,                        -- I5：修改時間戳
  created_at TIMESTAMPTZ DEFAULT NOW(),
  version INT DEFAULT 0
);

-- 地名雙軌顯示（憲法 §6 術語表：古地名為主，括號附現代地名）
CREATE TABLE place_names (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  historical_name VARCHAR(128) NOT NULL,           -- 例："長安"
  modern_name VARCHAR(128),                        -- 例："西安"（可為 NULL，古今同名時可省略）
  valid_period INT4RANGE,                           -- 地名使用的時間區間
  geom GEOMETRY(Point, 4326),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 歷史事件骨幹（來自 notes §九，客觀事實層）
CREATE TABLE historical_events (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    parent_event_id VARCHAR(64) REFERENCES historical_events(id), -- 組成關係：大事件（二戰/明治維新）底下的子事件（戰役/具體改革），同時驅動語意縮放（notes §六）顯示層級——年級尺度只顯示頂層事件，日/月級尺度展開子事件
    start_edtf VARCHAR(32) NOT NULL,                -- EDTF 人類語意時間（對應憲法 §9），時間長短由區間本身表達，不需額外欄位
    end_edtf VARCHAR(32) NOT NULL,
    start_decimal NUMERIC(8,3) NOT NULL,            -- 電腦計算用小數年份（notes §五），寫入時由後端自動從 EDTF 推算
    end_decimal NUMERIC(8,3) NOT NULL,
    origin_point GEOMETRY(Point, 4326),
    influence_area GEOMETRY(MultiPolygon, 4326),
    routes GEOMETRY(MultiLineString, 4326),
    sections JSONB,                                 -- 手風琴三層結構化內容
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 事件類型標籤（多對多，取代單一 event_type 欄位——同一事件常橫跨多類型，例：明治維新同時是政治改革+社會現代化+外交重整）
CREATE TABLE event_tags (
    id SERIAL PRIMARY KEY,
    tag_name VARCHAR(32) NOT NULL UNIQUE           -- 例："war"、"trade"、"reform"、"revolution"、"treaty"
);

CREATE TABLE historical_event_tag_map (
    event_id VARCHAR(64) NOT NULL REFERENCES historical_events(id),
    tag_id INT NOT NULL REFERENCES event_tags(id),
    PRIMARY KEY (event_id, tag_id)
);

-- 非政權觀察者的受控類別（取代自由文字，避免同一概念打出不同拼法）
CREATE TABLE observer_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(64) NOT NULL UNIQUE      -- 種子資料至少含："國際第三者（當代旁觀）"、"後世史學界（事後回顧）"，可隨時擴充新類別
);

-- 各方主觀敘事層（來自 notes §十.2，對應憲法多重視角/中立呈現原則）
CREATE TABLE historical_event_perspectives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(64) REFERENCES historical_events(id),
    regime_id UUID REFERENCES regimes(id),           -- 當事政權視角；非政權主體則留 NULL
    observer_category_id INT REFERENCES observer_categories(id), -- regime_id 為 NULL 時應指向此表（國際第三者/後世史學界等），不允許自由文字
    local_name VARCHAR(128) NOT NULL,
    narrative_summary TEXT NOT NULL,
    official_justification TEXT,
    primary_sources JSONB,
    claimed_casualties JSONB
    -- 應用層驗證：regime_id 與 observer_category_id 至少擇一非 NULL
);

-- 爭議點層（來自 notes §十.2）
CREATE TABLE historical_event_controversies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(64) REFERENCES historical_events(id),
    topic VARCHAR(128) NOT NULL,
    neutral_description TEXT NOT NULL,
    viewpoints JSONB                                  -- TODO：是否需標準化 schema（強制附學者/文獻來源），notes §十一 checklist 未決
);
```

### 主要實體與關係

- `regimes` 1 --- N `regime_aliases`（I4 FK 約束，代稱不可孤兒）
- `regimes` 1 --- N `regime_territories`（I1 時間區間必填，I5 版本鏈以 `superseded_by` 自我參照而非覆蓋刪除）
- `regimes` 自我參照 `predecessor_regime_id` / `destroyed_by_regime_id`（分裂/禪讓/滅亡轉換邊，客觀事實層，方案 D）
- `regimes` N --- N `regimes`（透過 `regime_relations`，持續性關係如貿易/朝貢/和親）
- `lineage_presets` 1 --- N `lineage_preset_members` N --- 1 `regimes`（史觀主線呈現層，與核心政權圖解耦）
- `regimes` 1 --- N `historical_event_perspectives`（nullable，非政權主體改連 `observer_categories`）
- `observer_categories` 1 --- N `historical_event_perspectives`
- `historical_events` 自我參照 `parent_event_id`（大事件/子事件組成關係，同時驅動語意縮放）
- `historical_events` N --- N `event_tags`（透過 `historical_event_tag_map`，取代單一 `event_type`）
- `historical_events` 1 --- N `historical_event_perspectives`
- `historical_events` 1 --- N `historical_event_controversies`

### DDD 邊界

- **Aggregate Root**: `Regime`（政權）、`HistoricalEvent`（歷史事件）、`LineagePreset`（史觀主線 preset）——三者為平行的獨立聚合根，對應 notes §七「疆域圖層 vs 事件圖層」解耦設計，`LineagePreset` 額外把「呈現用史觀立場」跟「客觀政權圖」解耦（方案 D）
- **內部 Entity**: `RegimeTerritory`（疆域版本記錄，含修正歷史）、`RegimeAlias`（他稱代稱）、`RegimeRelation`（政權間持續性關係）、`LineagePresetMember`（preset 內的排序成員）、`EventTag`（事件類型標籤）
- **Value Object**: `valid_period`（int4range）、EDTF 時間字串、`geom` 幾何值、`origin_transition_type`（分裂/被取代禪讓）
- **跨 Aggregate 連結**: `historical_event_perspectives.regime_id`、`lineage_preset_members.regime_id`、`regime_relations.regime_a_id/regime_b_id` 均以識別碼 FK 連結至 `Regime` 聚合，**不直接持有** `Regime` 實體引用

## 7. API 契約 (API Contract)

> 僅列核心 resource 的基本 CRUD 端點草案，query 參數細節與完整 request/response schema 待補（TODO）。認證欄位已依 §5 拍板結果回填：GET（讀取）第一階段公開不驗證；POST/PATCH（寫入）需 API Key/JWT。

| Method | Path | 用途 | 認證 |
|---|---|---|---|
| GET | /api/v1/regimes | 依時間區間查詢政權清單（支援 `?year=` 或 `?period=` 過濾） | 公開（唯讀，見 §5） |
| GET | /api/v1/regimes/:id | 取得單一政權詳情（含自稱名稱、狀態、代稱清單） | 公開（唯讀） |
| POST | /api/v1/regimes | 新增政權（I2 校驗自稱名稱必填） | API Key/JWT（見 §5） |
| PATCH | /api/v1/regimes/:id | 更新政權（狀態轉換須符合憲法 §4 合法轉換規則；前端 XState 做 UI 層防呆，後端獨立驗證為唯一信任來源，已拍板見 §5） | API Key/JWT + 樂觀併發 |
| GET | /api/v1/regimes/:id/territories | 取得政權疆域歷史（含版本鏈，I5） | 公開（唯讀） |
| POST | /api/v1/regimes/:id/territories | 新增疆域記錄（I1 校驗時間區間必填） | API Key/JWT |
| PATCH | /api/v1/territories/:id/correct | 史料修正端點（I5：產生新版本並保留原版本，非覆蓋更新，對應憲法 §8） | API Key/JWT + 樂觀併發 |
| GET | /api/v1/territories?year={y} | 查詢某年份所有政權疆域並存快照（對應 R2、Story 1） | 公開（唯讀） |
| GET | /api/v1/events?year={y} | 查詢某時間點/區間的歷史事件（對應 notes §七 事件圖層） | 公開（唯讀） |
| GET | /api/v1/events/:id/perspectives | 取得事件的多重視角敘事（對應 Story 3、notes §十） | 公開（唯讀） |
| GET | /api/v1/events/:id/controversies | 取得事件爭議點列表 | 公開（唯讀） |
| GET | /api/v1/lineage-presets | 取得可用史觀主線 preset 清單（方案 D，§6） | 公開（唯讀） |
| GET | /api/v1/lineage-presets/:id/regimes | 取得某 preset 底下依序排列的政權序列 | 公開（唯讀） |
| GET | /api/v1/regimes/:id/relations?year={y} | 取得政權在某時間點的持續性關係（貿易/朝貢/同盟等，`regime_relations`） | 公開（唯讀） |

詳細 request / response schema 見 OpenAPI `TODO`（尚未產出，待 M1 階段補上）。

統一回應格式：TODO——沿用 sanring 慣例 `{ statusCode, message, data: T }` / 列表用 `PaginatedResponse<T>`，待實作階段於 `api/` 專案確認是否套用。

## 8. UI 流程 (UI Flow)

> 對齊 notes §四、§六、§八、§十 的互動草圖。主要頁面與四態齊備，細節待前端實作階段補充 `data-testid`。

- **主地圖頁（Global Map View）** — 四態：
  - loading：地圖底圖與初始年份政權疆域載入中骨架畫面
  - empty：拖到某年份無任何政權/事件資料時顯示空狀態提示
  - error：GIS 資料載入失敗（PostGIS 查詢異常）時顯示錯誤重試 CTA
  - success：地圖渲染多政權疆域圖層 + 雙層時間軸 Scrubber（主軸「世紀/年」+ 副軸「月/日」展開，對應 notes §六）+ 語意縮放（年級尺度顯示疆域面，日/月尺度顯示事件標記點）
- **政權聚焦頁（Regime Focus Mode）** — 對應 Story 2：
  - loading：聚焦政權資料與周邊政權清單載入中
  - empty：該政權於當前時間點尚未建立/已不存在時的提示
  - error：聚焦資料查詢失敗
  - success：地圖高亮聚焦政權疆域 + 周邊政權互動清單側欄
- **事件詳情抽屜（Event Detail Drawer）** — 對應 notes §八毛玻璃側邊抽屜、Story 5：
  - loading：抽屜展開動畫 + 內容骨架
  - empty：TODO（事件無 sections 內容時如何呈現，notes 未定義，待補）
  - error：事件詳情載入失敗
  - success：`backdrop-filter: blur(16px)` 毛玻璃抽屜 + 三層手風琴（背景起因/關鍵轉折時間點/歷史影響），點擊「關鍵轉折時間點」觸發地圖 `flyTo` + 時間軸雙向連動
- **多重視角分頁（Perspective Tabs）** — 對應 notes §十、Story 3：
  - loading：各視角敘事載入中
  - empty：TODO（若某事件僅有客觀骨幹、無任一方視角資料時如何呈現，待補）
  - error：視角資料載入失敗
  - success：客觀經過概要 + 各當事方視角分頁 + 爭議點區塊並列呈現，預設開啟分頁邏輯 TODO（見 §12）

對應 Figma / design assets：**已拍板（grill-me 2026-08-25 第二輪）**——`design_output_mode: assets_only`，不引入 Figma 同步流程。理由：專案目前無設計稿、無 UI 元件庫選型，屬單人自用階段，先直接以既有 UI 元件庫（待選型）+ MapLibre 拼介面；待有明確視覺規範需求或設計師/多人協作介入時再評估升級。

關鍵互動的 `data-testid` 預埋清單：TODO——待前端實作階段依實際元件結構補上。

## 9. 風險與相依 (Risks & Dependencies)

### 風險

| 風險 | 影響 | 緩解 |
|---|---|---|
| ~~`docker-compose.yml` 用純 `postgres:16-alpine`，GIS 幾何欄位/空間索引無法運作~~ | ~~high~~ | **已解決（2026-08-25）**：拍板改用 `postgis/postgis:16-3.4` 映像檔，列入 M1 前置工作 |
| CHGIS／CShapes 授權為非商業限定（CC BY-NC-SA / 學術限定），若專案未來出現贊助或政府投資等資金來源，需重新確認授權相容性 | med | 使用者已確認目前無商業化/收費計畫，OHM（CC0）作主要資料來源可完全規避此風險；CHGIS/CShapes 僅輔助使用，若未來有資金來源介入，啟動前需重新查證或改用純 OHM 資料，詳見 §5 |
| 多重視角史料考據工作量大（notes §十設計要求「客觀骨幹 + 各方主觀敘事 + 爭議點」三層結構，每個跨國事件都需多方史料） | high | 第一階段（中國史）先聚焦內部政權疆域資料，多重視角功能可延後至世界史階段跨國事件出現時再逐步建置 |
| ~~政權「正式朝代 vs 子朝代/分裂政權」分類與傳承鏈定義未拍板~~ | ~~med~~ | **已解決（2026-08-25）**：不做分類欄位，改用 `regimes` 轉換邊（客觀事實）+ 獨立 `lineage_presets` 表（史觀主線呈現層），詳見 §6 方案 D |
| ~~EDTF + decimal year 轉換精度與計算時機未定~~ | ~~med~~ | **已解決（2026-08-25）**：用 npm `edtf` 套件解析＋寫入時驗證＋後端自動算 decimal，閏年天數交給標準日期函式庫處理 |
| 斜線網底（爭議控制區）Shader 方案在大量爭議區同時繪製時的效能瓶頸 | low | Phase 1 採 Canvas Pattern 方案規避（已拍板，見 §5），成熟階段再評估升級 WebGL Shader |
| ~~GIS 專屬技術棧均為候選狀態~~ | ~~med~~ | **大部分已解決（2026-08-25）**：地圖引擎、資料供應策略、狀態機、紀年轉換、EDTF 解析、歷史資料授權均已拍板，詳見 §5；剩餘候選（TopoJSON+Flubber、Turf.js、Dayjs/Luxon）尚未深入討論，維持待評估 |
| ~~XState 引入後，前端狀態機定義與後端業務規則驗證邏輯需要保持同步，若各自實作一套規則容易產生分歧~~ | ~~med~~ | **已解決（2026-08-25 第二輪）**：前端 XState 僅做 UI 防呆，後端 C# 獨立實作為唯一信任來源，兩邊皆以憲法 §4 合法轉換規則為 SSOT，見 §5 |
| 寫入端點加了最小 API Key/JWT，但金鑰/密鑰的產生、儲存與輪替方式尚未定義 | low | 實作階段需補：單人自用階段可先用環境變數存放單一固定 key，待多使用者需求出現時再升級為正式使用者/金鑰管理機制（新增風險，因 §5 拍板最小 Auth 而產生） |

### 相依

- **上游**：憲法 `.claude/constitutions/world-line.md`（已於 2026-08-25 拍板為 `status: active`）；PostGIS extension 安裝需先於資料庫層完成；歷史地理原始資料（CHGIS 等）授權確認需先於資料建置階段完成。
- **下游**：TODO——目前專案無其他下游依賴本 feature 的 team/service（單一專案，無已知下游影響範圍）。

## 10. 里程碑 (Milestones)

> 依憲法 §1 階段實施順序（中國史 → 世界史 → 單一國家史）給出粗略里程碑，**所有日期一律標 TODO**，憲法與 notes 均未提供時程資訊，禁止腦補。

| Milestone | 預計完成 | 內容 | 驗收門檻 |
|---|---|---|---|
| M1 | TODO | Schema + API 定案（政權/疆域/事件模型），PostGIS extension 安裝完成 | OpenAPI signed off；I1-I5 約束於 schema 層可驗證 |
| M2 | TODO | 後端 MVP（中國史階段政權/疆域 CRUD + 時間區間查詢） | 單元測試 + integration test 綠 |
| M3 | TODO | 前端整合（時間拉桿 + 地圖渲染 + 中國史資料上線，對應 Story 1、4） | 四態齊備、E2E 主流程綠 |
| M4 | TODO | 世界史階段擴充（多文明並存渲染，對應 R2；事件圖層與多重視角初版，對應 Story 3、5） | 品質門禁全綠 |
| M5 | TODO | 單一國家史深化階段（如台灣史）+ 教育對象開放評估（對應憲法 §1 未來擴充意圖） | Production smoke test 通過 |

## 11. 後續追蹤 (Follow-ups)

- 上線後 1 週：review 使用者（開發者自身）實際使用回饋，是否符合「縱覽世界」的核心體驗目標
- 30 天：檢視中國史階段資料完整度與正確性，決定是否啟動世界史階段擴充
- 90 天：檢視已拍板的 17 項技術決策（方案 D 史觀 preset、事件三維度拆分、Auth、角色權限、狀態機驗證分工等）視實作回饋決定是否需要正式 ADR 留存決策紀錄；§12 僅剩 CHGIS/CShapes 授權（資金來源變動時）一項待觀察

## 12. 開放問題 (Open Questions)

> **2026-08-25 更新（第二輪）**：原始 16 條開放問題中，17 條已透過兩輪 `/grill-me` 拍板（決策內容回填至 §2/§5/§6/§7/§8/§9，此處不重複列出，僅標記已解決；第二輪新增的 5 項亦計入）。僅剩 1 條未拍板，且性質為「未來若情境變化才需處理」，非本階段阻塞項。

**已解決（詳見 §2/§5/§6/§7/§8/§9）**：
- [x] 正式朝代/子朝代分類定義 → 方案 D（`lineage_presets` 獨立表，§6）
- [x] 分裂政權傳承關係鏈 → `predecessor_regime_id`/`destroyed_by_regime_id` 轉換邊（§6）
- [x] 政權間互動（R3）建模方式 → 離散事件用 `historical_events`、持續關係用 `regime_relations`（§6）
- [x] 事件的時間長短/類型/組成關係如何拆分 → EDTF 區間／多標籤／`parent_event_id`（§6）
- [x] 地圖引擎選型 → MapLibre GL JS 單獨，Deck.gl 留待後續疊加（§5）
- [x] 資料供應策略 → Phase 1 純 GeoJSON（§5）
- [x] XState 導入時機 → Phase 1 即導入（§5）
- [x] 紀年轉換庫涵蓋範圍 → 自建 `reign_eras` 表，不用 `lunar-javascript`/`cnlunar`（§5）
- [x] 斜線網底 Design Token 化 → 先用共用常數檔（§5）
- [x] 開源歷史地理資料授權 → OHM 為主，CHGIS/CShapes 限非商業，GeaCron 僅作 UX 參考（§5、§9）
- [x] `historical_event_perspectives.regime_id` 是否強制 FK → nullable FK + `observer_categories` 受控對照表（§6）
- [x] EDTF parser 選型與 decimal 計算時機 → npm `edtf` + 寫入時後端自動推算（§5）
- [x] 憲法 §2 開發者/使用者角色職責 → 開發者可寫可讀、使用者純唯讀（§2）——⚠️ 此為 PRD 實作層級的暫定解讀，供 §7 API 權限設計使用；憲法本體 §10 仍將此列為未拍板事項，若業務 owner 日後於憲法正式拍板此職責定義，需依 `prd-from-constitution` delta 流程重新比對本 PRD 是否一致
- [x] Auth 機制 → 寫入端點（POST/PATCH）加最小 API Key/JWT，讀取端點（GET）第一階段公開不驗證（§5、§7）
- [x] 設計交付模式與 Figma 同步 → `assets_only`，不引入 Figma 同步流程（§8）
- [x] 技術效能量化指標 → 暫不設定具體數字，改採質化驗收標準，待實測後回填（§2）
- [x] XState 前後端狀態機驗證分工 → 前端僅做 UI 防呆，後端 C# 獨立實作為唯一信任來源，兩邊以憲法 §4 為 SSOT（§5、§9）

**尚未拍板（低優先，情境觸發才需處理）**：

- [ ] TODO：若未來出現贊助/政府投資等資金來源，需重新確認 CHGIS/CShapes 的 NC 授權相容性（見 §9），暫不需現在處理。
