---
schema_version: 1
feature_id: world-line
feature_name: World Line — 歷史地圖 GIS 平台
status: active
owner: jack755051@gmail.com
last_updated: 2026-08-27
related_constitution: .claude/constitutions/world-line.md
related_adrs: []
---

# PRD: World Line — 歷史地圖 GIS 平台

> **文件狀態**：本 PRD 是目前有效的產品與技術基線。`active` 代表內容可作為實作依據，不代表功能已全部完成。實作進度以 `.claude/plans/world-line-implementation-plan.md` 的核取方塊為準：截至 2026-08-27，M1 資料層完成，M2 後端 MVP 與 M3 前端整合尚未開始。
>
> **狀態用語**：本文的「已拍板」表示決策已確認；「已實作」表示 repository 中已有對應程式碼與 migration；「待評估／TODO」不得被當成已承諾的行為。若敘述與可執行程式碼不一致，先視為文件漂移並修正，不以過時文字覆蓋實際行為。

> ⚠️ 本 PRD 基於 `.claude/constitutions/world-line.md` 產出。憲法本體的業務規則（R1-R3）、狀態機（§4）、不可變約束（I1-I5）已具備足夠明確度可作為 PRD 依據。若後續憲法內容變動，本 PRD 需重新走過 `prd-from-constitution` delta 比對流程。
>
> **2026-08-25 更新（第三輪，delta 比對）**：憲法 frontmatter `status` 已由 `draft` 拍板為 `active`，§10 原始 4 條開放問題全數解決（回填至憲法 §2 角色職責、§4 傳承關係鏈、§6 正式朝代/政權間互動術語）。經逐項比對，這些內容與本 PRD 既有的角色權限說明（§2）、方案 D lineage_presets 設計（§6）、historical_events/regime_relations 拆分（§6）**完全一致，無需修改對應段落**——本輪僅同步移除過時的「憲法尚未拍板」警語。
>
> **2026-08-25 更新（第一輪）**：透過 `/grill-me` 對本 PRD 逐項壓力測試，拍板了 12 項技術選型與資料模型決策（PostGIS 安裝方式、正式朝代分類、政權互動建模、事件多維度拆分、地圖引擎、資料供應策略、狀態機函式庫、紀年轉換、EDTF 解析、多重視角觀察者、斜線網底、開源資料授權），內容已回填至 §5/§6/§9/§12。
>
> **2026-08-25 更新（第二輪）**：延續 grill-me 訪談，再拍板 5 項：開發者/使用者角色職責、Auth 機制、設計交付模式、技術效能量化指標處理方式、XState 前後端狀態機驗證分工，內容已回填至 §2/§5/§7/§8/§9/§12。該輪訪談結束時只保留 CHGIS/CShapes 授權問題；2026-08-27 的一致性檢查另辨識出 EDTF 套件、API 格式與正式資料 citation 等 implementation blockers，見現行 §12。
>
> **2026-08-26 更新**：實作前重新檢視 `regime_territories` 發現既有 SQL 註解範例（`'[618, 907]'`）誤導成「一個政權一筆疆域記錄」，與憲法 §9「疆域連續變化」牴觸。已拍板修正：(1) 疆域快照密度採**事件驅動**（有史料佐證的變動才建快照，不強制固定週期，也不假裝逐年精確）；(2) 快照密度（資料儲存）與時間拉桿的拖動粒度（UI 互動）是兩回事，拉桿本身依憲法 §9 維持連續拖動，不可卡固定年份格；(3) `regime_territories.valid_period` 維持 `INT4RANGE`（年精度），不跟隨 `historical_events` 升級為 EDTF+decimal——疆域史料常態以年為單位記載，精確到日的疆域轉移（如條約割地）由對應的 `historical_events` 記錄承載日期精度即可，不需要疊加進疆域表。詳見 §6。
>
> **2026-08-27 更新**：發現 `regimes` 的轉換邊（`predecessor_regime_id`/`origin_transition_type`/`destroyed_by_regime_id`）只記錄「發生過什麼轉換」，沒有連到「是哪個 `historical_events` 導致的」。已拍板新增 `regime_transition_events` 多對多 join 表補上這個因果連結（`transition_kind` 區分起源/終止轉換），並已建立 EF Core migration `AddRegimeTransitionEvents` 套用到資料庫。詳見 §6。
>
> **2026-08-27 文件一致性更新**：依 repository 實況更新 M1 完成狀態；將 Auth 統一為固定 API Key；釐清 EDTF 已拍板的是「後端驗證與使用現成 parser」而非 npm 套件，具體 .NET 套件留給 M2.2 spike；OpenAPI 完整性移至 M2 驗收；補上 `docs/` 架構、開發、API 與資料治理入口。
>
> **2026-08-28 種子資料補強（第二輪）**：盤點 M1/M2 缺口發現兩件事：(1) `place_names` 表有 schema 卻完全沒有 seed 資料，且 Phase 2 任務清單漏排它的 API（已補 implementation plan 2.9b，見 §7）；(2) `regime_transition_events` 只驗證過 `transition_kind='destruction'`，`'origin'` 分支從未有種子資料測過。順帶把「三國正統之爭」這個真實史學史案例落地成資料，具體驗證方案 D（`lineage_presets` 解耦設計）真的能承載多史觀並存：新增第二個 preset「蜀漢正統論史觀」（漢→蜀漢→晉，晉的收錄理由跟傳統教科書史觀不同）、兩筆禪讓事件（漢禪魏/魏禪晉，補上 origin 轉換邊）、一筆引用陳壽《三國志》／習鑿齒《漢晉春秋》／朱熹《資治通鑑綱目》三方史觀的 `historical_event_controversies`，以及 4 筆 `place_names`（雒陽→洛陽示範同地點隨政權更迭改名、成都、建業-南京）。已在拋棄式 PostGIS 容器驗證無誤，尚未套用到 `docker-compose.yml` 的 `app_postgres`，見 implementation plan §7。

## 1. 背景 (Background)

傳統歷史知識透過書本傳遞時，是依「單一視角、按時間軸拆解」的方式敘述——例如以中國視角敘述唐朝歷史，便難以同步呈現同一時期阿拉伯帝國（大食）、歐洲政權的並行發展與互動關係。World Line 的核心動機（對應憲法 §1 業務目的、§7 Decision 1）是以 GIS／地圖取代這種單一視角敘事，讓使用者能夠「縱覽世界」：在同一個時間點上同時看到多個文明/政權的疆域與互動，並在需要時聚焦到單一政權觀察其與同時期周邊政權的關係（憲法 R2、R3）。

專案目前處於「先給自己（開發者本人）使用，後續再考慮教育用途」的階段（憲法 §1）。M1 資料層已完成：`api/` 已有 15 個領域 Entity、EF Core configurations、三份 migration、開發環境自動 migration 與中國史示範 seed；`regime_transition_events` 已補上政權轉換與歷史事件的因果連結，seed 資料現已覆蓋全部 15 張表（含先前缺漏的 `place_names`），並用兩個並存的 `lineage_presets` 示範方案 D 的多史觀解耦設計。`regime_territories(regime_id, valid_period)` 的 GiST 複合索引已建立（見 §5），I5 版本鏈（`superseded_by`）也已有種子資料機械驗證過（見 §6）。HTTP API 仍只有 scaffold 的 `WeatherForecast` controller，M2 業務端點尚未實作；`app/` 仍是 Angular 22 scaffold，M3 地圖與時間軸尚未實作。`docker-compose.yml` 已具備 frontend/backend/PostGIS/Redis 四個 service。可執行現況與啟動方式以 repository 根目錄 `README.md` 為準。

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

> 分兩類：**A. 既有專案技術棧（已定案沿用）**——`app/package.json`、`api/WorldLine.Api.csproj`、`docker-compose.yml` 的實際版本為準。**B. GIS 領域專屬技術**——最初來自 `.claude/notes/world-line-tech-candidates.md`；目前大部分已拍板，個別尚未決定的項目會明確標成「候選／待評估」，不得把 notes 中的舊候選文字當成現行決策。

### A. 既有技術棧（已定案沿用）

| 層 | 選型 | 理由 |
|---|---|---|
| Frontend | Angular ^22.1.0 | 既有專案偵測（`app/package.json`），CLI scaffold 已存在，沿用 |
| Backend | .NET 10 Web API（`net10.0`） | 既有專案偵測（`api/WorldLine.Api.csproj`），CLI scaffold 已存在，沿用 |
| DB | PostgreSQL 16（`postgis/postgis:16-3.4` 映像檔） | **已拍板（grill-me 2026-08-25）**：`docker-compose.yml` 的 postgres image 由純 `postgres:16-alpine` 改為 `postgis/postgis:16-3.4`，一行改動即取得 PostGIS extension，維護成本低於自建 init script，列入 M1 前置工作 |
| Cache | Redis 7-alpine | 既有專案偵測（`docker-compose.yml`），已備妥容器 |
| Auth | 單一固定 API Key（僅保護寫入端點） | **已拍板（grill-me 2026-08-25 第二輪；2026-08-26 implementation plan 細化）**：讀取端點（GET）第一階段不驗證；寫入端點（POST/PATCH）由 middleware 驗證環境變數 `API_WRITE_KEY` 與 request header `X-API-Key`。M2 尚未實作。JWT 與多使用者帳號不在第一階段範圍，待教育對象開放時再評估 |
| Deploy | Docker Compose | 既有專案偵測，frontend（Nginx，4200→80）/ backend（8080→5000）/ postgres（5432）/ redis（6379）四 service 已編排完成 |
| 監控 | TODO | 尚未評估，憲法/notes 未提及 |

### B. GIS 領域專屬技術

> 以下標「**已拍板**」的項目，均經 2026-08-25 `/grill-me` 逐項壓力測試後確認；標「候選」者未在本輪討論，維持待評估狀態。

| 層 | 選型 | 對應需求 | 狀態 |
|---|---|---|---|
| 地圖引擎 | MapLibre GL JS | 全球政權圖層渲染、時間過濾器（Filter Expressions） | **已拍板：Phase 1 單獨使用**。Deck.gl 保留為後續可疊加選項，待動畫流動效果（絲路貿易路線、傳播視覺化等）出現實際需求時再加，兩者設計上可疊加不衝突 |
| 高階視覺化 | Deck.gl（搭配 MapLibre） | 貿易路線/行軍路線/傳播軌跡等進階圖層 | **已拍板：Phase 1 不導入**，明確保留為後續疊加選項（見上） |
| 圖資壓縮與形變 | TopoJSON + Flubber.js | 疆域邊界共享壓縮、連續變化過渡動畫（對應憲法 §9） | **已拍板（2026-08-26 grill-me on implementation plan）：Phase 1（M3）就導入，非候選延後**。理由：憲法 §9 業務規則本體是「疆域必須連續變化呈現，非離散跳轉」（非僅拉桿操作連續），使用者明確要求「類似衛星雲圖」的真實形變效果，淡入淡出等簡化方案無法達到，纳入 M3 範圍，見 `.claude/plans/world-line-implementation-plan.md` Phase 3 |
| 空間幾何分析 | Turf.js | 政權標籤置中點計算、邊界簡化，**已拍板新增用途（2026-08-29）**：拓撲相交測試（`booleanIntersects`）計算疆域相鄰關係，供政權識別色的動態圖著色演算法使用（見 §6 設計原則、implementation plan 3.5） | `booleanIntersects` 這個用途已拍板並落地（`app/src/app/core/geometry/territory-adjacency.ts`）；標籤置中點/邊界簡化仍是候選，待實際需求出現再評估 |
| 政權狀態機 | XState | 存續/分裂/被取代/被滅亡狀態防呆（對應憲法 §4） | **已拍板：Phase 1 就導入**（使用者選擇一步到位，非採用建議的簡單 enum 方案，理由：避免後續遷移成本）。**驗證分工（grill-me 2026-08-25 第二輪追加拍板）**：前端 XState 僅負責 UI 層防呆與進度圖顯示；後端 C#（.NET，與 XState 不同語言無法直接共用同一份 library）獨立實作同一套合法轉換規則作為唯一信任來源，防止 API 被繞過前端直接呼叫寫入非法狀態轉換。雙方均以憲法 §4 列出的合法轉換規則（存續→分裂／存續→被取代禪讓／存續→被滅亡）作為 SSOT 文件依據，日後憲法 §4 若修訂需同步更新前後端兩份實作，避免規則飄移 |
| 紀年轉換 | 自建 `reign_eras` 查詢表 | 西元 ↔ 年號/廟號（武德、開元、日本昭和、民國年等）雙向映射（對應憲法 §9 多重紀年） | **已拍板：自建查詢表，不使用 `lunar-javascript`/`cnlunar`**——這兩個套件處理的是農曆換算，跟「年號查詢」是不同問題；憲法 §9 需求本質是一張「年號-政權-起訖年」查詢表，不是曆法計算 |
| 時間格式化 | Dayjs/Luxon + 自訂 BCE 擴充 | 處理無西元 0 年、負數年份；EDTF decimal 計算時用來正確處理閏年天數 | 候選，未在本輪討論，維持待評估 |
| 向量切片服務 | Martin（Rust）或 Tegola | 直連 PostGIS 動態切 MVT，避免巨量 GeoJSON 卡頓 | **已拍板：Phase 1 不導入**，Phase 1 用純 GeoJSON（見下），Phase 2 若遇全球渲染效能瓶頸再評估導入 |
| 靜態離線切片 | PMTiles | 單檔金字塔圖磚，適合離線/靜態主機 | **已拍板：Phase 1 不導入**，待出現具體離線/純靜態部署需求再評估 |
| 資料供應策略 | 純 GeoJSON | 後端直接回傳幾何資料，前端直接渲染 | **已拍板：Phase 1 採用**。理由：R1 範圍（中國史、朝代/國家層級）政權數量與疆域幾何複雜度可控，純 GeoJSON 已足夠，不需額外架設 Martin/Tegola 增加維運負擔；Phase 2「世界史」需同時渲染全球大量政權疆域，若遇效能瓶頸再回頭導入 MVT 動態切片；PMTiles 待「離線/純靜態部署」具體需求出現再評估 |
| EDTF 時間解析 | 自訂子集解析器（`api/Domain/EdtfService.cs`）+ `NodaTime` 3.3.3 負責曆法數學 | 精確到日/月/年/模糊區間的人類語意時間格式解析（對應憲法 §9、notes §五） | **已完成（2026-08-29，task 2.2）**：M2.2 spike 調查了 .NET 生態僅有的 EDTF 專用套件（`EDTF` by nharren，2015 年後未更新、只 target net45；`MoreDateTime` 的 EDTF 功能是 2026 年剛加的新功能，作者自承未完整覆蓋 ISO 8601-2:2019，且強制依賴 `Nager.Date` 假日套件），均不合格，觸發 implementation plan 停止條件。最終方案：EDTF 語法解析（`?`/`~`/負年份/年-月-日，只涵蓋憲法/notes 實際用到的子集，不追求完整規格覆蓋）自己寫，純字串處理風險低；曆法數學（閏年、負年份 day-of-year 計算）交給業界標準的 `NodaTime`（Jon Skeet 維護，321M 次下載，`CalendarSystem.Iso` 官方支援西元前 9998 年到西元 9999 年，絕對紀年慣例與 EDTF/ISO 8601 一致，不需要額外年份偏移轉換）。EDTF 字串仍是 single source of truth，decimal year 由後端寫入時自動推算 |
| UI 元件庫 | Sanring UI（`@sanring/cli`）+ Tailwind CSS v4 | 毛玻璃側邊抽屜／手風琴／多重視角分頁等 headless 元件（notes §十一原開放問題） | **已拍板（2026-08-28）**：source-first、非傳統 npm 依賴——CLI 把元件原始碼複製進 `app/` 原始碼樹，團隊自行維護。既有 `app/package.json`（Angular ^22.1.0、TypeScript ~6.0.2）與其需求（Angular 22.x、TypeScript >=6.0.0 <6.1.0）相符，僅需新增 Tailwind CSS v4 依賴。納入 Phase 3 前置任務，見 `.claude/plans/world-line-implementation-plan.md` Phase 3 任務 3.0 |
| GIS 資料庫擴充 | PostGIS extension（`postgis/postgis` 映像檔） | `GEOMETRY(MultiPolygon, 4326)` 儲存政權疆域、`int4range` 時間區間索引（GiST 複合索引） | **已實作（2026-08-28）**：`regime_territories(regime_id, valid_period)` 複合 GiST 索引已建立（migration `AddRegimeTerritoryGistIndex`，需 `btree_gist` extension 才能讓一般欄位跟 range 型別共用 GiST）。這條決策先前只在本表標「已拍板」，卻沒有被排進任何 phase 的任務清單，屬於「決定了沒人接手」的孤兒項目，已補上並套用到 `app_postgres` |
| 歷史地理原始資料 | OpenHistoricalMap（主要來源）＋ CHGIS／CShapes（輔助，僅限非商業情境） | 繪製政權疆域 GeoJSON 骨幹的資料來源 | **已拍板（grill-me 2026-08-25，含實際授權查證）**：OHM 為 CC0 公眾領域，作主要來源；CHGIS 僅限學術非商業使用，CShapes 為 CC BY-NC-SA 4.0（禁商業＋需 ShareAlike），兩者僅能在非商業情境使用；GeaCron 查無明確公開授權，**只作 UX 互動設計參考，不當資料來源**。⚠️ 使用者確認目前無商業化/收費計畫；若未來出現贊助/政府投資等資金來源，需重新確認 CHGIS/CShapes 的 NC 授權相容性（詳見 §9 風險） |
| 斜線網底配色 | 集中共用常數檔（非正式 Design Token 系統） | 爭議控制區（notes §十）視覺呈現一致性 | **已拍板：Phase 1 用單一共用常數檔**（如 `neutral-map-colors.ts`）集中管理顏色/間距，不建置正式 Design Token pipeline；待深色模式或多人協作需求出現再升級 |

## 6. 資料模型 (Data Model)

> 依憲法 I1-I5 設計政權/疆域 schema 骨幹，並整合 notes `historical_events` / `historical_event_perspectives` / `historical_event_controversies` 作為事件圖層。**2026-08-25 grill-me 更新**：憲法 §10「正式朝代 vs 子朝代/分裂政權」分類問題已拍板解法（非直接分類欄位，見下方方案 D 說明），政權互動、事件多維度拆分、多重視角觀察者等 schema 設計也一併定案，取代原本的 TODO 留白。

### 設計原則（grill-me 拍板摘要）

- **政權轉換邊是客觀事實，「正式朝代」標籤是史觀立場**：`regimes` 表只記錄禪讓/滅亡/分裂這些客觀發生過的轉換動作，不判斷誰是「正統」。「主線敘事」（例如傳統教科書史觀的漢→魏→晉→⋯⋯序列）改用獨立的 `lineage_presets` 表承載，明確標註是哪一種史觀，可並存多個 preset，核心政權圖保持中立（方案 D）。**已用種子資料驗證（2026-08-28）**：除「傳統教科書史觀」外，新增「蜀漢正統論史觀」（漢→蜀漢→晉，對應史學史真實存在的習鑿齒《漢晉春秋》/朱熹《資治通鑑綱目》尊蜀漢說），蜀漢在 `regimes.status` 是「被滅亡」而非「被取代(禪讓)」，這個 preset 仍把它放進主線並跳過魏，證明 preset 成員資格確實不需要遵循 `predecessor_regime_id` 那條客觀邊——解耦不只是文件宣稱，schema 真的撐得住
- **政權互動依「離散事件」vs「持續關係」拆兩張表**：戰爭/條約/會戰這類有明確起訖的事件進 `historical_events`；絲路貿易、朝貢、和親這類沒有單一時間點、更像持續狀態的關係進 `regime_relations`
- **事件本身有三個獨立維度**：時間長短由既有 EDTF 區間表達（不需新欄位）；類型（戰爭/貿易/革命/改革）用多對多標籤（不用單一 enum，因為像明治維新這種事件常同時橫跨多個類型）；組成關係（大戰爭包含小戰役）用 `parent_event_id` 自我參照，這個父子結構同時也是 notes §六語意縮放（Semantic Zooming）的資料基礎——年級尺度只顯示頂層事件，日/月級尺度才展開子事件
- **多重視角的「觀察者」不一定是政權**：`historical_event_perspectives.regime_id` 維持 nullable FK（給當事政權用），非政權主體（國際第三者、後世史學界等）改用受控的 `observer_categories` 對照表，不用自由文字，避免同一概念打出不同拼法
- **`regimes.status`／`origin_transition_type` 改用文化中立代碼，不用中文字面值**（2026-08-28，回應「西方/日式/非洲政權會不會有文化偏頗」的檢視）：原本直接存憲法 §4 的中文術語（「存續」「分裂」「被取代(禪讓)」「被滅亡」）當 enum 值，只有 5 筆 seed 資料就已經飄了（`status` 寫過「被取代(禪讓)」、`origin_transition_type` 寫過「被取代禪讓」，同一概念兩種字面值）；且「禪讓」是中國政治史特有的儀式性概念，套到羅馬共和轉帝制之類的非中國轉型會很勉強。改成 `'active'|'split'|'succeeded'|'conquered'` 中立代碼，UI/文件層再依語系對照回憲法的中文術語；憲法本身的業務詞彙不變，這純粹是儲存編碼方式的改變。**同一輪檢視發現一個目前還沒修的結構性缺口，見 §9 風險與 §12**：`predecessor_regime_id` 是單一 FK，只能表達「一對多分裂」，無法表達「多對一合併」（例如英格蘭+蘇格蘭→大不列顛這種歐洲史常見的政權合併），中國史很少出現這種轉換所以三國案例沒測到，留給 M4 世界史階段真的要放歐洲政權前處理
- **I5 版本鏈（`superseded_by`）已有種子資料機械驗證過**（2026-08-28）：先前 `superseded_by`/`correction_reason`/`corrected_at` 只有 schema 欄位，從沒被任何 seed row 真正賦值過，等於這條 FK 路徑連「能不能正常 insert/查詢」都沒驗證。已補一組漢朝 `[25,189)` 的原始版＋修正版，原始列的 `superseded_by` 指向修正列。跟既有的蜀漢 I3 衝突組（同區間兩筆皆 `is_disputed=true`、互不 supersede）刻意做對照：I3 是「同期並存的兩種史觀」，I5 是「新版本取代舊版本」，語意不同。M2 應用層的修正端點行為（2.7：擋直接 UPDATE/DELETE、強制走新增新版本流程）仍待實作，這裡只驗證 schema 層的資料形狀正確
- **一個政權在存續期間需要多筆疆域快照，不是一筆涵蓋全朝代**（2026-08-26 拍板）：`regime_territories` 是「快照表」，同一個 `regime_id` 依疆域實際變動筆數會有多筆記錄（例：唐朝 618-907 年間應有多筆，涵蓋擴張/收縮的不同階段），時間拉桿拖動時前端在快照之間做形變過渡動畫，快照本身不等於「離散跳轉」。快照密度**事件驅動**（有史料佐證的變動才建，不強制固定週期），疆域爭奪激烈的區域（如三國時期荊州）自然會比穩定期政權有更密集的快照；快照密度是「資料儲存」層面的事，跟時間拉桿的「拖動粒度」是兩回事——拉桿依憲法 §9 永遠連續拖動，不因快照稀疏而卡格。`valid_period` 維持 `INT4RANGE`（年精度），不跟隨 `historical_events` 升級為 EDTF+decimal：疆域史料常態以年為單位記載/推定，精確到日的疆域轉移（條約割地等）由對應的 `historical_events` 承載日期精度即可
- **政權識別色不是固定對照表，是每個時間切片動態算出來的**（2026-08-29 拍板，前端設計）：地圖是 choropleth 形式，任兩塊疆域都可能被拿來比較，色盲安全性要用最嚴格的「任兩色都要能分辨」標準檢驗——用 dataviz 技能驗證過的預設 8 色分類色盤跑這個標準，只有前 3 色能過。但這個限制的前提是「沒有實際計算相鄰關係、靠隨機/插入順序上色」；如果真的算出地理相鄰關係、只保證「相鄰不同色」（四色定理精神），標準會放寬到「相鄰配對」等級，8 色都能過。因此政權識別色的做法是：不幫每個政權寫死一個永久顏色，而是每個時間切片用貪婪圖著色演算法（`app/src/app/core/geometry/graph-coloring.ts`）即時分配，相鄰關係用 Turf.js 拓撲相交測試計算（`territory-adjacency.ts`），演算法會優先沿用前一次的色格以避免拖拉桿拖動時顏色無謂閃爍。系統色（介面底色/文字/邊框/狀態色，跟政權識別色分開）已定案於 `app/src/app/core/design/design-tokens.scss`。政權身份辨識的主要管道是點擊/hover 顯示名稱（Story 2、3），不是靠記憶顏色——顏色只是輔助疆域彼此有區別，不是身份的唯一或主要依據。疆域邊界線維持單一中性色，不跟填色搶識別色資源；爭議控制區維持既有拍板的斜線網底（§5、3.15）
- **政權轉換邊需要能追溯回導致它的具體事件**（2026-08-27 拍板）：`regimes.predecessor_regime_id`/`origin_transition_type`（起源轉換）與 `regimes.destroyed_by_regime_id`（終止轉換）原本只記錄「發生過什麼轉換」，沒有連到「是哪個事件導致的」。新增 `regime_transition_events` 多對多 join 表，用 `transition_kind`（`'origin'` | `'destruction'`）區分同一個政權可能同時掛著起源與終止兩種轉換各自的觸發事件；多對多是因為一次轉換可能由多個事件共同促成（例：一連串戰役才逼成禪讓），一個事件也可能同時觸發多個政權的轉換（例：一場戰役同時導致多個分裂政權誕生）
- **領域內容雙語支援用型別化翻譯表，只翻譯中立事實內容**（2026-08-29 拍板，2026-08-29 grill-me 兩輪修正，對應憲法 R4）：詳見下方「多語言內容設計」小節。翻譯（換語言講同一件事）跟史觀/史料傳統差異（不同語言史料內容本來就可能不同）是兩個獨立的軸——只有中立事實內容需要翻譯，立場性敘事（`historical_event_perspectives`）不翻譯、靠既有多重視角機制各自用原語言寫。**翻譯表本身最終定案是 5 張型別化 companion 表（`regime_translations` 等），不是單一通用表**——中途曾改成通用表（省開表數），但釐清這個專案的實際目標是給多使用者用、資料量會持續成長後，通用表放棄外鍵完整性（父列刪除時翻譯列不會自動級聯刪除，得靠應用層清孤兒資料）這個取捨在這個前提下不划算，改回型別化表換真外鍵 + `ON DELETE CASCADE`，詳見下方修訂記錄

### 多語言內容設計（憲法 R4，2026-08-29 拍板，2026-08-29 grill-me 兩輪修正）

**核心設計原則：「翻譯」跟「史觀/史料傳統」是兩個獨立的軸，不能混在一起處理**（2026-08-29 grill-me 釐清）：

- **中立事實內容**（政權自稱名稱、事件客觀骨幹、史觀 preset 名稱說明）——換一種語言講的是同一件事，沒有立場差異，適合機械翻譯。
- **有立場的敘事內容**（`historical_event_perspectives.narrative_summary`/`official_justification`、`historical_event_controversies.viewpoints`）——中文史料寫出來的視角跟英文/阿拉伯文史料寫出來的視角，內容本身可能就不一樣（側重點、細節、甚至部分事實認定），不是「同一段話換語言講」。**這類內容不翻譯，直接依照既有的多重視角機制（`historical_event_perspectives` + `observer_categories`）各自用原本的語言寫**——`observer_categories` 本來就是可擴充的受控詞彙表（已有「後世史學界（事後回顧）」），未來可以直接新增「中文史料傳統」「阿拉伯文史料傳統」等類別，不需要新結構。想看「中文史料怎麼講阿拉伯帝國」就直接看對應語言寫的那筆視角，沒有對應語言版本代表還沒寫，不是系統缺陷。避免把某個語言史料的內容硬翻成另一種語言、包裝成看似客觀中立的敘述。

**只有「中立事實內容」需要 schema 支援翻譯，每個要翻譯的父表各開一張型別化 `_translations` companion 表**（2026-08-29 grill-me 第二輪定案；中途曾走過單一通用表方案，修訂原因見下）：

```sql
-- 範例（其餘表比照同一 pattern：一張表一個真外鍵、一組 (parent_id, locale) 唯一鍵）
CREATE TABLE regime_translations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  regime_id UUID NOT NULL REFERENCES regimes(id) ON DELETE CASCADE,
  locale VARCHAR(5) NOT NULL,         -- ISO 639-1，如 'en'；未來若要地區變體可延伸 'en-US'
  self_name VARCHAR(128) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (regime_id, locale)
);
```

其餘 4 張表同一個 pattern：`regime_alias_translations`（FK → `regime_aliases`）、`historical_event_translations`（FK → `historical_events`，`event_id` 是字串型別對齊原表）、`lineage_preset_translations`（FK → `lineage_presets`）、`historical_event_controversy_translations`（FK → `historical_event_controversies`）。

**修訂記錄：為什麼從單一通用表改回型別化表**——通用表（`entity_type`/`entity_id`/`field_name`/`locale` 四欄定位一筆翻譯）少開 4 張表、跟訊息代碼字典（task 2.0）同一種「key → 對照文字」思路，一度定案並已建置驗證過。但重新檢視這個專案的實際目標——**不是單人自用的小工具，是要給其他使用者用、資料量會隨著史料涵蓋範圍持續成長**——通用表放棄外鍵完整性（`entity_id` 無法對任何一張表設真正外鍵，父列刪除時翻譯列得靠應用層自己清，沒有資料庫層級的保護網）這個取捨在這個前提下不成立：資料量小、單人測試時看不出問題，但正是「多人維護、資料量變大」這種情境下最容易在沒有任何錯誤提示的情況下悄悄累積孤兒資料。改回型別化表，換回真外鍵 + `ON DELETE CASCADE`，已用實際刪除測試驗證：刪除一個政權，對應的翻譯列會被資料庫自動級聯刪除，不需要應用層自己清。代價是回到 5 張表（而非 1 張），接受。

**父表欄位不是永遠固定存中文**——父表欄位存的是「這筆內容的原始語言」，語意上等於這筆內容最初被記載/建檔時用的語言，**跟著題材本身的史料傳統走，不是系統固定「中文是主、其他語言是翻譯」**。中國史題材（三國等）原始史料就是中文，中文欄位是原文不是翻譯；但如果之後某個題材的原始史料本來就是英文/法文（例如歐洲史的百年戰爭），主欄位存的應該是英文，中文才是 `_translations` 表裡 `locale='zh'` 的那一列——方向完全視題材出處而定，schema 對兩個方向都對稱支援。查詢時指定 `locale` 若有對照列則回傳翻譯內容，沒有則 fallback 回父表欄位——**加這些表不會讓既有內容自動變雙語，仍需要有人實際寫翻譯內容，schema 只是讓這件事變得可行、可漸進式補**。

**需要翻譯的欄位清單**（只有中立事實內容）：

| 父表 | 對應 companion 表 | 需要翻譯的欄位 | 說明 |
|---|---|---|---|
| `regimes` | `regime_translations` | `self_name` | |
| `regime_aliases` | `regime_alias_translations` | `alias_name` | 別名（例：「大食」）本身就是一個有自己 `id` 的獨立列，跟 `regimes.self_name` 沒有本質差異，一樣可以開一筆翻譯（如「大食」→「Dashi」音譯）。「這個代稱是哪個政權視角給的」（`observer_regime_id`）跟「這個代稱要用哪種語言呈現」（`locale`）是兩個獨立維度，互不干擾，套用跟上方「翻譯 vs 史觀立場」相同的正交原則 |
| `historical_events` | `historical_event_translations` | `name` | `sections` JSONB 內嵌文字（客觀骨幹的三層手風琴內容）性質上也屬中立事實，但要不要連帶翻譯、翻譯結構長怎樣還沒拍板——留到真的要擴充這張表時再決定，不在這裡先選 |
| `lineage_presets` | `lineage_preset_translations` | `preset_name`／`description` | |
| `historical_event_controversies` | `historical_event_controversy_translations` | `topic`／`neutral_description` | 僅這兩欄；`viewpoints`（誰主張什麼）屬於立場性內容，不翻譯，見上方核心原則 |

**明確不進翻譯範圍，改走多重視角機制**：`historical_event_perspectives.local_name`／`narrative_summary`／`official_justification`（整張表）、`historical_event_controversies.viewpoints`。

**次要/輔助內容，維持待評估、不現在處理**（優先權低，之後需要時比照同一個 pattern 各自開一張 companion 表）：`reign_eras.era_name`、`place_names.historical_name`/`modern_name`、`regime_relations.relation_type`/`description`、`event_tags.tag_name`、`observer_categories.category_name`。

**API 層影響**：唯讀端點需要能接受 `?locale=` 查詢參數（省略時預設回原始語言），例如 `GET /api/v1/regimes?locale=en`。已實作的 2.3（`reign_eras` 查詢）目前不支援，因為 `reign_eras` 不在翻譯範圍——之後真的要做時再補，不用現在回頭改。

### Schema 變動

```sql
-- 政權主體（I2：自稱名稱必填才能建立）
CREATE TABLE regimes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  self_name VARCHAR(128) NOT NULL,              -- 自稱名稱（I2 硬約束，例："唐"、"阿拔斯王朝"）
  status VARCHAR(32) NOT NULL,                  -- 'active'|'split'|'succeeded'|'conquered'（對應憲法 §4 存續／分裂／被取代(禪讓)／被滅亡，2026-08-28 改用中立代碼，見下方設計原則）

  -- 轉換邊（客觀事實層，方案 D：不判斷正統，只記錄發生過的轉換動作）
  predecessor_regime_id UUID REFERENCES regimes(id),  -- 因「分裂」或「被取代(禪讓)」而來的前身政權；獨立建國則為 NULL
  origin_transition_type VARCHAR(16),                 -- 'split'|'succeeded'|NULL（獨立建國，無前身；2026-08-28 改用中立代碼）
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
  alias_type VARCHAR(32),                         -- nullable 保留欄位；允許值／是否保留須在 M2 alias API 前拍板，見 §12
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 政權疆域快照表（I1：時間區間必填才能存在；I5：修正保留版本歷史不可覆蓋刪除）
-- ⚠️ 一個 regime_id 通常對應多筆記錄，不是一筆涵蓋整個政權存續期間！
-- 例：唐朝（regime 存續 618-907）不會只有一筆 valid_period='[618,907]'，
-- 而是依史料佐證的疆域變動事件驅動建多筆，例如 '[618,626]'、'[626,649]'、'[649,690]' ...
-- 快照密度事件驅動，不強制固定週期；時間拉桿的連續拖動由前端在快照間做形變插值處理，
-- 不等於資料庫要逐年存一筆（見 §6 設計原則）
CREATE TABLE regime_territories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  regime_id UUID NOT NULL REFERENCES regimes(id),
  valid_period INT4RANGE NOT NULL,                -- I1 硬約束，年精度（維持 INT4RANGE，不跟隨 historical_events 升級 EDTF，見上方設計原則）
  geom GEOMETRY(MultiPolygon, 4326) NOT NULL,      -- 需 PostGIS extension（見 §5 風險）
  is_disputed BOOLEAN DEFAULT FALSE,               -- 對應 I3：爭議並存標記
  superseded_by UUID REFERENCES regime_territories(id), -- I5：指向修正後的新版本，本列不刪除、不覆蓋
  correction_reason TEXT,                          -- I5：修正原因（史料修正機制，憲法 §8「類 git」）
  corrected_at TIMESTAMPTZ,                        -- I5：修改時間戳
  created_at TIMESTAMPTZ DEFAULT NOW(),
  version INT DEFAULT 0
);

-- 紀年年號查詢表（§5 已拍板：自建查詢表，不用農曆函式庫；2026-08-26 補：先前遺漏未加入本 schema）
CREATE TABLE reign_eras (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  regime_id UUID NOT NULL REFERENCES regimes(id),
  era_name VARCHAR(64) NOT NULL,          -- 例："貞觀"、"開元"、"昭和"、"民國"
  start_year INT NOT NULL,                -- 西元年，例：627
  end_year INT,                           -- 西元年，NULL 表示持續使用中／尚未確定結束年
  created_at TIMESTAMPTZ DEFAULT NOW()
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
    viewpoints JSONB                                  -- request JSON schema 與 citation 要求須在 M2.13 前定義，見 §12 與 docs/data-governance.md
);

-- 政權轉換邊 ↔ 導致它的事件（多對多，2026-08-27 拍板，見上方設計原則）
CREATE TABLE regime_transition_events (
    regime_id UUID NOT NULL REFERENCES regimes(id) ON DELETE CASCADE,
    event_id VARCHAR(64) NOT NULL REFERENCES historical_events(id) ON DELETE CASCADE,
    transition_kind VARCHAR(16) NOT NULL,            -- 'origin'（對應 predecessor_regime_id 起源轉換）| 'destruction'（對應 destroyed_by_regime_id 終止轉換）
    PRIMARY KEY (regime_id, event_id, transition_kind)
);
```

### 主要實體與關係

- `regimes` 1 --- N `regime_aliases`（I4 FK 約束，代稱不可孤兒）
- `regimes` 1 --- N `regime_territories`（I1 時間區間必填，I5 版本鏈以 `superseded_by` 自我參照而非覆蓋刪除）
- `regimes` 1 --- N `reign_eras`（年號查詢，§5 已拍板）
- `regimes` 自我參照 `predecessor_regime_id` / `destroyed_by_regime_id`（分裂/禪讓/滅亡轉換邊，客觀事實層，方案 D）
- `regimes` N --- N `regimes`（透過 `regime_relations`，持續性關係如貿易/朝貢/和親）
- `lineage_presets` 1 --- N `lineage_preset_members` N --- 1 `regimes`（史觀主線呈現層，與核心政權圖解耦）
- `regimes` 1 --- N `historical_event_perspectives`（nullable，非政權主體改連 `observer_categories`）
- `observer_categories` 1 --- N `historical_event_perspectives`
- `historical_events` 自我參照 `parent_event_id`（大事件/子事件組成關係，同時驅動語意縮放）
- `historical_events` N --- N `event_tags`（透過 `historical_event_tag_map`，取代單一 `event_type`）
- `historical_events` 1 --- N `historical_event_perspectives`
- `historical_events` 1 --- N `historical_event_controversies`
- `regimes` N --- N `historical_events`（透過 `regime_transition_events`，`transition_kind` 區分是起源轉換還是終止轉換的觸發事件，2026-08-27 拍板）

### DDD 邊界

- **Aggregate Root**: `Regime`（政權）、`HistoricalEvent`（歷史事件）、`LineagePreset`（史觀主線 preset）——三者為平行的獨立聚合根，對應 notes §七「疆域圖層 vs 事件圖層」解耦設計，`LineagePreset` 額外把「呈現用史觀立場」跟「客觀政權圖」解耦（方案 D）
- **內部 Entity**: `RegimeTerritory`（疆域版本記錄，含修正歷史）、`RegimeAlias`（他稱代稱）、`RegimeRelation`（政權間持續性關係）、`ReignEra`（年號查詢資料）、`LineagePresetMember`（preset 內的排序成員）、`EventTag`（事件類型標籤）、`RegimeTransitionEvent`（政權轉換邊與觸發事件的連接記錄）
- **Value Object**: `valid_period`（int4range）、EDTF 時間字串、`geom` 幾何值、`origin_transition_type`（分裂/被取代禪讓）
- **跨 Aggregate 連結**: `historical_event_perspectives.regime_id`、`lineage_preset_members.regime_id`、`regime_relations.regime_a_id/regime_b_id` 均以識別碼 FK 連結至 `Regime` 聚合，**不直接持有** `Regime` 實體引用

## 7. API 契約 (API Contract)

> 以下是 M2 的目標契約，不代表端點已實作。認證欄位已依 §5 拍板結果回填：GET（讀取）第一階段公開不驗證；POST/PATCH（寫入）需固定 API Key。可執行 API 現況與 OpenAPI 使用方式見 `docs/api.md`。

| Method | Path | 用途 | 認證 |
|---|---|---|---|
| GET | /api/v1/regimes | 依時間區間查詢政權清單（支援 `?year=` 或 `?period=` 過濾） | 公開（唯讀，見 §5） |
| GET | /api/v1/regimes/:id | 取得單一政權詳情（含自稱名稱、狀態、代稱清單） | 公開（唯讀） |
| POST | /api/v1/regimes | 新增政權（I2 校驗自稱名稱必填） | `X-API-Key`（見 §5） |
| PATCH | /api/v1/regimes/:id | 更新政權（狀態轉換須符合憲法 §4 合法轉換規則；前端 XState 做 UI 層防呆，後端獨立驗證為唯一信任來源，已拍板見 §5） | `X-API-Key` + 樂觀併發 |
| GET | /api/v1/regimes/:id/territories | 取得政權疆域歷史（含版本鏈，I5） | 公開（唯讀） |
| POST | /api/v1/regimes/:id/territories | 新增疆域記錄（I1 校驗時間區間必填） | `X-API-Key` |
| PATCH | /api/v1/territories/:id/correct | 史料修正端點（I5：產生新版本並保留原版本，非覆蓋更新，對應憲法 §8） | `X-API-Key` + 樂觀併發 |
| GET | /api/v1/territories?year={y} | 查詢某年份所有政權疆域並存快照（對應 R2、Story 1） | 公開（唯讀） |
| GET | /api/v1/events?year={y} | 查詢某時間點/區間的歷史事件（對應 notes §七 事件圖層） | 公開（唯讀） |
| GET | /api/v1/events/:id/perspectives | 取得事件的多重視角敘事（對應 Story 3、notes §十） | 公開（唯讀） |
| GET | /api/v1/events/:id/controversies | 取得事件爭議點列表 | 公開（唯讀） |
| GET | /api/v1/lineage-presets | 取得可用史觀主線 preset 清單（方案 D，§6） | 公開（唯讀） |
| GET | /api/v1/lineage-presets/:id/regimes | 取得某 preset 底下依序排列的政權序列 | 公開（唯讀） |
| GET | /api/v1/regimes/:id/relations?year={y} | 取得政權在某時間點的持續性關係（貿易/朝貢/同盟等，`regime_relations`） | 公開（唯讀） |
| GET | /api/v1/place-names?year={y} | 依年份查詢當時使用中的地名（憲法 §6 古地名為主、現代地名括號對照） | 公開（唯讀） |
| GET | /api/v1/place-names/:id | 取得單一地名詳情（含 `historical_name`/`modern_name`） | 公開（唯讀） |

M2 每個端點完成時都必須同步進入 ASP.NET 內建 OpenAPI，至少包含 request/response schema、成功狀態碼與主要 4xx 回應。正式的文字精修與範例補強可延後，但不得讓已實作端點缺席於產生出的契約。目前僅有 scaffold endpoint，詳見 `docs/api.md`。

**統一回應格式（已拍板，2026-08-28，task 2.0；2026-08-29 修訂 `message` 語意）**：採包裝格式，沿用 sanring 慣例，不用 ASP.NET 內建 `ProblemDetails`。

```json
// 成功
{ "statusCode": 200, "message": "FETCH_SUCCESS", "data": { /* resource 或陣列，query 無結果時為 [] 或 null，視端點語意 */ } }

// 失敗（驗證錯誤、找不到資源、狀態轉換不合法等）
{ "statusCode": 400, "message": "YEAR_REQUIRED", "data": null }
```

- 三欄固定：`statusCode`（對應 HTTP status code）、`message`、`data`（成功時放 resource，失敗時固定 `null`）。
- **`message` 放穩定代碼，不是人類可讀的中文句子**（2026-08-29 修訂）：前端拿代碼查自己的翻譯字典決定顯示文字，之後改中文措辭不會動到前端邏輯，也才能真的做多語系。代碼是 SCREAMING_SNAKE_CASE，成功代碼對應 HTTP 動詞語意（GET→`FETCH_SUCCESS`），錯誤代碼盡量對應到具體違反的欄位/規則（如 `YEAR_REQUIRED`），只有框架自動觸發、無法歸因到單一規則的情況才用通用代碼（`VALIDATION_ERROR`／`NOT_FOUND`／`INTERNAL_ERROR`）。**已知取捨**：多筆欄位驗證各自的詳細原因，單一代碼裝不下，換取代碼本身穩定可依賴——`[ApiController]` 自動觸發的 model-state 驗證失敗一律回通用 `VALIDATION_ERROR`，不逐欄位列出。代碼清單以 `api/Contracts/ApiMessageCodes.cs` 為權威來源，不在文件裡另外維護一份會漂移的複本。
- 不新增第 4 個欄位——維持三欄不變的封包形狀。
- 實作已落地（2026-08-29，task 2.3）：`api/Contracts/ApiResponse.cs`（包裝型別）+ `api/Infrastructure/ApiExceptionHandler.cs`（未捕捉例外走同一包裝）+ `Program.cs` 的 `ApiBehaviorOptions.InvalidModelStateResponseFactory`（`[ApiController]` 預設 400 也走同一包裝），後續端點直接沿用。
- **待拍板（AI 提案，2.5/2.7 動工前需確認）**：I5 樂觀併發（`version` 欄位）版本衝突要回 `409 Conflict` 還是 `412 Precondition Failed`？建議 409——這個專案的併發檢查是比對 request body 裡的 `version` 整數欄位，不是 HTTP 標準的 `If-Match`/`If-Unmodified-Since` 條件式請求標頭機制，412 在 HTTP 規格裡專指後者，用在這裡不夠精確；409 是較通用的「請求與資源目前狀態衝突」語意，更貼近實際做法。

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
  - empty：事件無 `sections` 時的文案與可用動作須在 M3.12 前拍板（見 §12）
  - error：事件詳情載入失敗
  - success：`backdrop-filter: blur(16px)` 毛玻璃抽屜 + 三層手風琴（背景起因/關鍵轉折時間點/歷史影響），點擊「關鍵轉折時間點」觸發地圖 `flyTo` + 時間軸雙向連動
- **多重視角分頁（Perspective Tabs）** — 對應 notes §十、Story 3：
  - loading：各視角敘事載入中
  - empty：事件只有客觀骨幹、沒有視角資料時的文案與 fallback 須在 M3.13 前拍板（見 §12）
  - error：視角資料載入失敗
  - success：客觀經過概要 + 各當事方視角分頁 + 爭議點區塊並列呈現；預設開啟哪個分頁須在 M3.13 前拍板（見 §12）

對應 Figma / design assets：**已拍板（grill-me 2026-08-25 第二輪）**——`design_output_mode: assets_only`，不引入 Figma 同步流程。理由：專案目前無設計稿，屬單人自用階段，先直接以 UI 元件庫（**2026-08-28 已選定 Sanring UI**，見 §5 B）+ MapLibre 拼介面；待有明確視覺規範需求或設計師/多人協作介入時再評估升級。

關鍵互動的 `data-testid` 不在 PRD 預先臆測名稱；M3 實作元件時依 3.16 E2E 主流程同步定義，並由測試 review 確認穩定性。

## 9. 風險與相依 (Risks & Dependencies)

### 風險

| 風險 | 影響 | 緩解 |
|---|---|---|
| ~~`docker-compose.yml` 用純 `postgres:16-alpine`，GIS 幾何欄位/空間索引無法運作~~ | ~~high~~ | **已解決（2026-08-25）**：拍板改用 `postgis/postgis:16-3.4` 映像檔，列入 M1 前置工作 |
| ~~憲法 R4（2026-08-29 新增）要求雙語內容，但既有 15 張表全部是單一語言欄位，且現有 seed 資料完全沒有英文版本~~ | ~~med~~ | **已解決（2026-08-29）**：5 張型別化 `_translations` companion 表（`regime_translations` 等，§6）+ 20 筆既有 seed 資料的英文翻譯已完成並套用到 `app_postgres`，真外鍵 + `ON DELETE CASCADE` 已用實際刪除測試驗證。`historical_events.sections` JSONB 是否連帶翻譯仍未拍板，留給實際擴充 `historical_event_translations` 時決定 |
| CHGIS／CShapes 授權為非商業限定（CC BY-NC-SA / 學術限定），若專案未來出現贊助或政府投資等資金來源，需重新確認授權相容性 | med | 使用者已確認目前無商業化/收費計畫，OHM（CC0）作主要資料來源可完全規避此風險；CHGIS/CShapes 僅輔助使用，若未來有資金來源介入，啟動前需重新查證或改用純 OHM 資料，詳見 §5 |
| 多重視角史料考據工作量大（notes §十設計要求「客觀骨幹 + 各方主觀敘事 + 爭議點」三層結構，每個跨國事件都需多方史料） | high | 第一階段（中國史）先聚焦內部政權疆域資料，多重視角功能可延後至世界史階段跨國事件出現時再逐步建置 |
| `regimes.predecessor_regime_id` 是單一 FK，只能表達「一對多分裂」，無法表達「多對一合併」（例如英格蘭+蘇格蘭→大不列顛）——中國史很少出現此類轉換，三國案例未觸發此缺口（2026-08-28 檢視發現） | med（會擋住 M4 世界史需要的歐洲政權資料） | M1/M2 現有資料不受影響，純新增（例如加一張 `regime_merge_sources` join table），不動現有欄位。列為 M4 世界史前必須處理，詳見 §12 |
| ~~政權「正式朝代 vs 子朝代/分裂政權」分類與傳承鏈定義未拍板~~ | ~~med~~ | **已解決（2026-08-25）**：不做分類欄位，改用 `regimes` 轉換邊（客觀事實）+ 獨立 `lineage_presets` 表（史觀主線呈現層），詳見 §6 方案 D |
| ~~EDTF + decimal year 的責任邊界已定，但 .NET 套件能力尚未驗證~~ | ~~med~~ | **已解決（2026-08-29）**：套件 spike 確認無合格 EDTF 套件，改採「自訂語法解析 + NodaTime 曆法引擎」混合方案，詳見 §5 |
| 斜線網底（爭議控制區）Shader 方案在大量爭議區同時繪製時的效能瓶頸 | low | Phase 1 採 Canvas Pattern 方案規避（已拍板，見 §5），成熟階段再評估升級 WebGL Shader |
| ~~GIS 專屬技術棧均為候選狀態~~ | ~~med~~ | **大部分已解決（2026-08-26）**：MapLibre、純 GeoJSON、XState、`reign_eras`、TopoJSON+Flubber 與資料授權均已拍板；剩餘候選為 Turf.js、Dayjs/Luxon，以及 EDTF 的具體 .NET 套件 |
| ~~XState 引入後，前端狀態機定義與後端業務規則驗證邏輯需要保持同步，若各自實作一套規則容易產生分歧~~ | ~~med~~ | **已解決（2026-08-25 第二輪）**：前端 XState 僅做 UI 防呆，後端 C# 獨立實作為唯一信任來源，兩邊皆以憲法 §4 合法轉換規則為 SSOT，見 §5 |
| 寫入端點預定使用固定 API Key，但金鑰產生與輪替方式尚未定義 | low | M2 先以環境變數 `API_WRITE_KEY` 保存單人開發 key，文件與 `.http` 範例不得寫入真實值；待多使用者需求出現時再升級正式金鑰／帳號管理 |

### 相依

- **上游**：憲法 `.claude/constitutions/world-line.md`（已於 2026-08-25 拍板為 `status: active`）；PostGIS extension 安裝需先於資料庫層完成；歷史地理原始資料（CHGIS 等）授權確認需先於資料建置階段完成。
- **下游**：目前無其他 team/service 依賴本 feature（單一專案，無已知下游影響範圍）。

## 10. 里程碑 (Milestones)

> 依憲法 §1 階段實施順序（中國史 → 世界史 → 單一國家史）給出粗略里程碑。M1 使用實際完成日期；尚未排程的未來里程碑維持 TODO，不自行腦補承諾日期。

| Milestone | 預計完成 | 內容 | 驗收門檻 |
|---|---|---|---|
| M1 | 2026-08-27 完成 | 資料層定案：15 張領域表、PostGIS、migration、seed 與 schema 可表達性驗證 | migration 可套用；I1/I2/I4 由 schema 擋下；I3/I5 所需欄位就緒並明確交由 M2 應用層強制 |
| M2 | TODO | 後端 MVP（中國史階段政權/疆域 CRUD + 時間區間查詢） | 單元測試 + integration test 綠；所有已實作端點出現在 ASP.NET OpenAPI |
| M3 | TODO | 前端整合（時間拉桿 + 地圖渲染 + 中國史資料上線，對應 Story 1、4） | 四態齊備、E2E 主流程綠 |
| M4 | TODO | 世界史階段擴充（多文明並存渲染，對應 R2；事件圖層與多重視角初版，對應 Story 3、5） | 品質門禁全綠 |
| M5 | TODO | 單一國家史深化階段（如台灣史）+ 教育對象開放評估（對應憲法 §1 未來擴充意圖） | Production smoke test 通過 |

## 11. 後續追蹤 (Follow-ups)

- 上線後 1 週：review 使用者（開發者自身）實際使用回饋，是否符合「縱覽世界」的核心體驗目標
- 30 天：檢視中國史階段資料完整度與正確性，決定是否啟動世界史階段擴充
- 90 天：檢視已拍板的技術決策（方案 D 史觀 preset、事件三維度拆分、Auth、角色權限、狀態機驗證分工等），依實作回饋決定是否需要正式 ADR 留存；尚未拍板事項以 §12 現行分類為準

## 12. 開放問題 (Open Questions)

> **2026-08-27 更新**：大部分產品與架構決策已拍板。以下保留已解決事項供追溯；尚未拍板事項分成「M2 前必須處理」與「情境觸發才處理」，避免低優先問題掩蓋真正的 implementation blocker。

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
- [x] EDTF parser 責任邊界與 decimal 計算時機 → 後端寫入時驗證並自動推算；具體 .NET 套件列為 M2.2 spike（§5）
- [x] 憲法 §2 開發者/使用者角色職責 → 憲法已正式拍板為開發者可寫可讀、使用者純唯讀（§2）
- [x] Auth 機制 → 寫入端點（POST/PATCH）使用單一固定 API Key；讀取端點（GET）第一階段公開（§5、§7）
- [x] 設計交付模式與 Figma 同步 → `assets_only`，不引入 Figma 同步流程（§8）
- [x] 技術效能量化指標 → 暫不設定具體數字，改採質化驗收標準，待實測後回填（§2）
- [x] XState 前後端狀態機驗證分工 → 前端僅做 UI 防呆，後端 C# 獨立實作為唯一信任來源，兩邊以憲法 §4 為 SSOT（§5、§9）
- [x] 統一回應格式與錯誤格式 → 包裝格式 `{ statusCode, message, data }`，沿用 sanring 慣例（§7，task 2.0）
- [x] `regimes.status`／`origin_transition_type` 的文化偏頗風險 → 改用中立代碼（`active`/`split`/`succeeded`/`conquered`），憲法中文術語維持不變，純儲存編碼調整（§6）

**M2 前必須處理**：

- [x] M2.2 驗證可用的 .NET EDTF 套件與支援範圍 → 無合格套件，改採自訂子集解析器 + NodaTime 曆法引擎，見 §5、implementation plan 2.2（2026-08-29 完成）
- [ ] TODO：M2 政權代稱 API 前決定 `regime_aliases.alias_type` 的受控值與用途；若無法提供比 observer relationship 更清楚的語意，移除欄位而不是保留自由文字。
- [ ] TODO：M2.12/M2.13 寫入端點前定義 `primary_sources`、`claimed_casualties`、`viewpoints` 的 JSON schema 與最小 citation 欄位。
- [x] 憲法 R4：implementation plan 2.16（5 張型別化 `_translations` companion 表，真外鍵 + `ON DELETE CASCADE`）、2.17（既有 seed 資料 20 筆英文翻譯）已完成並套用到 `app_postgres`，見 §6「多語言內容設計」。2.4/2.8/2.9a/2.10/2.13 這些尚未動工的查詢端點仍要支援 `?locale=`；2.12（`historical_event_perspectives`）不用，因為整張表都不進翻譯範圍。

**正式史料匯入前必須處理**：

- [ ] TODO：新增可重用的 source/citation model，讓政權、疆域、年號、關係與事件都能逐筆追溯來源、版本、locator 與授權；最低要求見 `docs/data-governance.md`。

**M3 前必須處理**：

- [ ] TODO：拍板事件詳情無 `sections`、事件無視角資料時的 empty state，以及 Perspective Tabs 預設分頁規則。

**M4（世界史）前必須處理**（2026-08-28 新增，回應文化偏頗檢視）：

- [ ] TODO：`regimes` 補上「多對一合併」轉換路徑（例如新增 `regime_merge_sources` join table），現有的 `predecessor_regime_id` 單一 FK 只能表達分裂，歐洲史常見的政權合併（personal union、統一戰爭）目前存不進去。純新增，不影響現有資料，但要在真正匯入第一筆需要合併語意的政權（例如大不列顛、德意志統一）之前完成，不要等到卡住才回頭改。
- [ ] TODO：`regime_territories` 的「政權＝固定邊界多邊形」假設，套到遊牧部落聯盟或非洲分節式政治體系是否成立，需要具體案例出現時再評估，目前只是標記為開放問題，不預先改 schema。
- [ ] TODO：羅馬/拜占庭/伊斯蘭等文明「政權身份連續存在、統治家族多次更替」的情況，現有 `regimes` 沒有獨立的「統治家族」概念（中國史因兩者重合而不需要）。M4 實際建置時若發現這個資訊需要被查詢/篩選（不只是敘事文字），才評估要不要加表。
- [ ] TODO：若 M4 要做「文明圈/宗教著色」地圖圖層，`civilization_sphere`／`legitimacy_type`／`religion` 這類屬性不可做成 `regimes` 的固定欄位——政權存續期間會變動（君士坦丁皈依基督教、唐朝佛道搖擺、蒙古帝國分裂出的汗國走向完全不同的宗教/合法性系統都是同一政權內的變化），且薩珊波斯/可薩/回鶻等真實案例已證明不能是寫死的小型 enum。資料須時間切片、詞彙表須可擴充，且要走既有 citation 治理。
- [ ] TODO：`historical_events.start_edtf`/`end_edtf` 只定義公曆，schema 沒有任何欄位記錄「原始史料用哪個曆法記載、如何換算成公曆」。`NodaTime`（task 2.2 已導入）內建伊斯蘭曆/波斯曆/希伯來曆的換算數學，但**沒有中國農曆、沒有中美洲曆法**，且函式庫支援不等於 schema 有對應欄位。正式匯入非中國史料前需決定「原始曆法系統」「原始曆法日期字串」「換算方法」要不要結構化成獨立欄位，還是留在未來 citation model 的自由文字 evidence note。完整分析見 `.claude/notes/world-line-civilizational-legitimacy-models.md` §十。
- [ ] 四大文明政權合法性模型的完整比對、上述兩條 TODO 的詳細推導見 `.claude/notes/world-line-civilizational-legitimacy-models.md`（M4 grill-me 參考素材）。

**低優先，情境觸發才需處理**：

- [ ] TODO：若未來出現贊助/政府投資等資金來源，需重新確認 CHGIS/CShapes 的 NC 授權相容性（見 §9），暫不需現在處理。
