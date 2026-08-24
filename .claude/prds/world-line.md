---
schema_version: 1
feature_id: world-line
feature_name: World Line — 歷史地圖 GIS 平台
status: draft
owner: jack755051@gmail.com
last_updated: 2026-08-24
related_constitution: .claude/constitutions/world-line.md
related_adrs: []
---

# PRD: World Line — 歷史地圖 GIS 平台

> ⚠️ 本 PRD 基於 `.claude/constitutions/world-line.md`（frontmatter `status: draft`，**尚未由業務 owner 拍板為 `active`**）產出。憲法本體的業務規則（R1-R3）、狀態機（§4）、不可變約束（I1-I5）已具備足夠明確度可作為 PRD 依據，但憲法 §10 列出的 4 條開放問題尚未拍板，本 PRD 對應段落一律標記 TODO，不代為假設。若後續憲法內容變動，本 PRD 需重新走過 `prd-from-constitution` delta 比對流程。

## 1. 背景 (Background)

傳統歷史知識透過書本傳遞時，是依「單一視角、按時間軸拆解」的方式敘述——例如以中國視角敘述唐朝歷史，便難以同步呈現同一時期阿拉伯帝國（大食）、歐洲政權的並行發展與互動關係。World Line 的核心動機（對應憲法 §1 業務目的、§7 Decision 1）是以 GIS／地圖取代這種單一視角敘事，讓使用者能夠「縱覽世界」：在同一個時間點上同時看到多個文明/政權的疆域與互動，並在需要時聚焦到單一政權觀察其與同時期周邊政權的關係（憲法 R2、R3）。

專案目前處於「先給自己（開發者本人）使用，後續再考慮教育用途」的階段（憲法 §1），尚未有任何業務程式碼——`app/`（Angular 22 scaffold）與 `api/`（.NET 10 Web API scaffold，僅 `WeatherForecast` 預設 controller）都是 CLI 預設輸出，`docker-compose.yml` 已備妥 frontend/backend/postgres/redis 四個 service 的容器編排骨架。本 PRD 是本專案第一份正式功能規格文件，銜接憲法與後續實作。

## 2. 目標 (Goals)

- **業務目標**：
  - 依憲法 §1 階段實施順序，優先完成「中國史」政權/疆域資料的地圖化呈現，作為第一階段可用產品；後續依序擴充至「世界史」（多文明並存，對應 R2）與「單一國家史」（如台灣史）。
  - 服務對象階段性明確：第一階段僅需滿足開發者本人（使用者自己）的使用需求，教育用途為後續階段目標，非本 PRD 範圍內的驗收標準。
- **技術目標**：TODO——憲法與 notes 皆未提供效能 / SLA 數字（如 p95 latency、併發使用者數、資料量體規模），禁止腦補，待使用者於下一輪確認補充。
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
- [ ] Given 聚焦政權與周邊政權之間存在已建檔的互動事件（如貿易、戰爭），when 顯示互動清單，then 應列出可點擊追溯至對應 `historical_events` 記錄的入口（TODO：互動清單的完整互動類型定義，見 §12 Open Questions，對應憲法 §10 R3 相關術語缺口）

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
- [ ] Given 「正式朝代」與「子朝代/分裂政權」的分類定義（TODO，憲法 §10 未拍板），when 系統呈現政權列表，then 暫以憲法已確認案例（漢→晉為正式傳承主線，三國期間政權為分裂期政權）作為顯示邏輯基礎，精確分類規則待補（見 §12）

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
| DB | PostgreSQL 16-alpine | 既有專案偵測（`docker-compose.yml`）。**⚠️ 需改用 `postgis/postgis` 映像檔或於現有 `postgres:16-alpine` 容器內手動安裝 PostGIS extension**——目前 compose 用的是純 postgres image，不含 PostGIS，GIS 幾何欄位（`GEOMETRY`/`GEOGRAPHY`）與空間索引無法直接運作，需列入 M1 前置工作 |
| Cache | Redis 7-alpine | 既有專案偵測（`docker-compose.yml`），已備妥容器 |
| Auth | TODO | 憲法與 notes 均未提及認證機制，第一階段僅開發者自用，是否需要 JWT/Session 待確認（見 §12） |
| Deploy | Docker Compose | 既有專案偵測，frontend（Nginx，4200→80）/ backend（8080→5000）/ postgres（5432）/ redis（6379）四 service 已編排完成 |
| 監控 | TODO | 尚未評估，憲法/notes 未提及 |

### B. GIS 領域專屬技術（候選，待選型，來自 notes）

| 層 | 候選 | 對應需求 | 狀態 |
|---|---|---|---|
| 地圖引擎 | MapLibre GL JS | 全球政權圖層渲染、時間過濾器（Filter Expressions） | 候選（notes §一.3、§十一 checklist 第 1 項待決） |
| 高階視覺化 | Deck.gl（搭配 MapLibre） | 貿易路線/行軍路線/傳播軌跡等進階圖層 | 候選，是否第一階段就導入待決 |
| 圖資壓縮與形變 | TopoJSON + Flubber.js | 疆域邊界共享壓縮、連續變化過渡動畫（對應憲法 §9） | 候選 |
| 空間幾何分析 | Turf.js | 政權標籤置中點計算、邊界簡化 | 候選 |
| 政權狀態機 | XState（或簡單 enum + 應用層邏輯） | 存續/分裂/被取代/被滅亡狀態防呆（對應憲法 §4） | 候選，notes §十一 checklist 第 3 項待決是否第一階段導入 |
| 紀年轉換 | `lunar-javascript` / `cnlunar` / 自建年號對照表 | 西元 ↔ 年號/廟號（武德、開元等）雙向映射（對應憲法 §9 多重紀年） | 候選，涵蓋範圍待確認（notes §十一 checklist 第 4 項） |
| 時間格式化 | Dayjs/Luxon + 自訂 BCE 擴充 | 處理無西元 0 年、負數年份 | 候選 |
| 向量切片服務 | Martin（Rust）或 Tegola | 直連 PostGIS 動態切 MVT，避免巨量 GeoJSON 卡頓 | 候選，資料供應策略待定（notes §十一 checklist 第 2 項） |
| 靜態離線切片 | PMTiles | 單檔金字塔圖磚，適合離線/靜態主機 | 候選，與 MVT 動態方案分階段導入策略待定 |
| EDTF 時間解析 | npm `edtf` 或自建 parser | 精確到日/月/年/模糊區間的人類語意時間格式（對應憲法 §9、notes §五） | 候選 |
| GIS 資料庫擴充 | PostGIS extension | `GEOMETRY(MultiPolygon, 4326)` 儲存政權疆域、`int4range` 時間區間索引（GiST 複合索引） | 候選但高確定性——技術上為必要擴充，僅安裝方式（映像檔 vs 手動裝）待確認 |
| 歷史地理原始資料 | CHGIS / CShapes / OpenHistoricalMap / GeaCron | 繪製政權疆域 GeoJSON 骨幹的資料來源 | 候選，授權條款待確認（notes §十一 checklist） |

## 6. 資料模型 (Data Model)

> 依憲法 I1-I5 設計政權/疆域 schema 骨幹，並整合 notes `historical_events` / `historical_event_perspectives` / `historical_event_controversies` 作為事件圖層。憲法 §10 尚未拍板的「正式朝代 vs 子朝代/分裂政權」分類與傳承鏈結構，本節保留為 TODO 欄位，不代為拍板定義。

### Schema 變動

```sql
-- 政權主體（I2：自稱名稱必填才能建立）
CREATE TABLE regimes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  self_name VARCHAR(128) NOT NULL,              -- 自稱名稱（I2 硬約束，例："唐"、"阿拔斯王朝"）
  status VARCHAR(32) NOT NULL,                  -- 存續 / 分裂 / 被取代(禪讓) / 被滅亡（憲法 §4 狀態機）
  -- TODO：「正式朝代」vs「子朝代/分裂政權」分類欄位定義未拍板，憲法 §10 開放問題，暫不建欄位，待確認後補
  -- TODO：分裂/傳承關係鏈（如曹魏/蜀漢/東吳與漢朝的傳承關係）是否需要 parent_regime_id 或獨立的 regime_lineage 表，憲法 §10 開放問題，暫留白
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  version INT DEFAULT 0                          -- 樂觀併發
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
    event_type VARCHAR(32) NOT NULL,               -- rebellion / war / treaty ...
    start_edtf VARCHAR(32) NOT NULL,                -- EDTF 人類語意時間（對應憲法 §9）
    end_edtf VARCHAR(32) NOT NULL,
    start_decimal NUMERIC(8,3) NOT NULL,            -- 電腦計算用小數年份（notes §五）
    end_decimal NUMERIC(8,3) NOT NULL,
    origin_point GEOMETRY(Point, 4326),
    influence_area GEOMETRY(MultiPolygon, 4326),
    routes GEOMETRY(MultiLineString, 4326),
    sections JSONB,                                 -- 手風琴三層結構化內容
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 各方主觀敘事層（來自 notes §十.2，對應憲法多重視角/中立呈現原則）
CREATE TABLE historical_event_perspectives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(64) REFERENCES historical_events(id),
    regime_id UUID REFERENCES regimes(id),           -- TODO：是否強制對應已建檔政權，或允許自由文字主體（如"國際第三者"），notes §十一 checklist 未決
    local_name VARCHAR(128) NOT NULL,
    narrative_summary TEXT NOT NULL,
    official_justification TEXT,
    primary_sources JSONB,
    claimed_casualties JSONB
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
- `regimes` 1 --- N `historical_event_perspectives`（TODO：是否強制 FK，見上）
- `historical_events` 1 --- N `historical_event_perspectives`
- `historical_events` 1 --- N `historical_event_controversies`
- `regimes` 之間的分裂/傳承關係：TODO，憲法 §10 開放問題，暫無 schema 表達方式

### DDD 邊界

- **Aggregate Root**: `Regime`（政權）、`HistoricalEvent`（歷史事件）——兩者為平行的獨立聚合根，對應 notes §七「疆域圖層 vs 事件圖層」解耦設計
- **內部 Entity**: `RegimeTerritory`（疆域版本記錄，含修正歷史）、`RegimeAlias`（他稱代稱）
- **Value Object**: `valid_period`（int4range）、EDTF 時間字串、`geom` 幾何值
- **跨 Aggregate 連結**: `historical_event_perspectives.regime_id` 以識別碼 FK 連結至 `Regime` 聚合，**不直接持有** `Regime` 實體引用

## 7. API 契約 (API Contract)

> 僅列核心 resource 的基本 CRUD 端點草案，query 參數細節與完整 request/response schema 待補（TODO）。

| Method | Path | 用途 | 認證 |
|---|---|---|---|
| GET | /api/v1/regimes | 依時間區間查詢政權清單（支援 `?year=` 或 `?period=` 過濾） | TODO（見 §5 Auth 待確認） |
| GET | /api/v1/regimes/:id | 取得單一政權詳情（含自稱名稱、狀態、代稱清單） | TODO |
| POST | /api/v1/regimes | 新增政權（I2 校驗自稱名稱必填） | TODO |
| PATCH | /api/v1/regimes/:id | 更新政權（狀態轉換須符合憲法 §4 合法轉換規則，TODO：後端是否需實作狀態機防呆邏輯，或交由前端 XState 候選方案處理，見 §12） | TODO + 樂觀併發 |
| GET | /api/v1/regimes/:id/territories | 取得政權疆域歷史（含版本鏈，I5） | TODO |
| POST | /api/v1/regimes/:id/territories | 新增疆域記錄（I1 校驗時間區間必填） | TODO |
| PATCH | /api/v1/territories/:id/correct | 史料修正端點（I5：產生新版本並保留原版本，非覆蓋更新，對應憲法 §8） | TODO + 樂觀併發 |
| GET | /api/v1/territories?year={y} | 查詢某年份所有政權疆域並存快照（對應 R2、Story 1） | TODO |
| GET | /api/v1/events?year={y} | 查詢某時間點/區間的歷史事件（對應 notes §七 事件圖層） | TODO |
| GET | /api/v1/events/:id/perspectives | 取得事件的多重視角敘事（對應 Story 3、notes §十） | TODO |
| GET | /api/v1/events/:id/controversies | 取得事件爭議點列表 | TODO |

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

對應 Figma / design assets：TODO——本 PRD 尚未涉及第二層 Figma 同步決策（是否啟用、MCP 或 import_script、目標檔案），需於使用者確認後補充（見「使用者待確認事項」）。

關鍵互動的 `data-testid` 預埋清單：TODO——待前端實作階段依實際元件結構補上。

## 9. 風險與相依 (Risks & Dependencies)

### 風險

| 風險 | 影響 | 緩解 |
|---|---|---|
| `docker-compose.yml` 目前用純 `postgres:16-alpine` 而非 `postgis/postgis` 映像檔，GIS 幾何欄位/空間索引無法直接運作 | high | M1 前置工作：改用 `postgis/postgis` 映像檔，或於現有容器內以初始化腳本安裝 PostGIS extension |
| 開源歷史地理資料（CHGIS/OHM/CShapes/GeaCron）授權條款未確認是否符合本專案使用情境（含未來教育用途） | high | 待使用者確認各資料源授權條款，見 §12 |
| 多重視角史料考據工作量大（notes §十設計要求「客觀骨幹 + 各方主觀敘事 + 爭議點」三層結構，每個跨國事件都需多方史料） | high | 第一階段（中國史）先聚焦內部政權疆域資料，多重視角功能可延後至世界史階段跨國事件出現時再逐步建置 |
| 政權「正式朝代 vs 子朝代/分裂政權」分類與傳承鏈定義未拍板（憲法 §10），可能影響 schema 設計方向 | med | 待憲法 owner 拍板後再定案 `regimes` 表的傳承關係欄位，目前 schema 保留 TODO 空白，不預先假設結構 |
| EDTF + decimal year 雙欄位模型的轉換精度（平閏年誤差）與計算時機（寫入時後端自動推算 vs 離線批次）未定 | med | notes §十一已列為待決問題，待選型階段確認，見 §12 |
| 斜線網底（爭議控制區）Shader 方案在大量爭議區同時繪製時的效能瓶頸 | low | notes 已建議 MVP 階段採 Canvas Pattern 方案規避，成熟階段再升級 WebGL Shader |
| GIS 專屬技術棧（MapLibre/Deck.gl/Martin/PMTiles 等）均為候選狀態，尚未拍板，可能影響前端資料供應架構設計方向 | med | 待 §12 選型問題確認後定案，避免提前深度綁定候選技術 |

### 相依

- **上游**：憲法 `.claude/constitutions/world-line.md` 需由業務 owner 確認並將 `status` 改為 `active`（目前為 `draft`）；PostGIS extension 安裝需先於資料庫層完成；歷史地理原始資料（CHGIS 等）授權確認需先於資料建置階段完成。
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
- 90 天：檢視是否需要針對「正式朝代 vs 子朝代/分裂政權」分類（憲法 §10）、GIS 技術選型候選（§12）等 open questions 開立對應 ADR

## 12. 開放問題 (Open Questions)

> 完整帶入憲法 §10 的 4 條 TODO，以及 notes §十一 checklist 中尚未解決的關鍵選型問題。**憲法本體開放問題與 notes 未拍板技術選型問題性質不同**，前者需業務 owner 拍板、後者需技術選型會議確認，禁止 AI 代為假設。

**來自憲法 §10（業務規則層，需業務 owner 拍板）**：

- [ ] TODO：「正式朝代」與「子朝代/分裂政權」的精確分類定義（例：判定條件是什麼？子朝代是否有獨立疆域規則？）——使用者已提出概念雛形（漢→晉為正式傳承，三國期間政權為子朝代/分裂政權），但尚未拍板精確定義。
- [ ] TODO：分裂產生的政權（如曹魏/蜀漢/東吳）是否需記錄與原政權的正式傳承關係鏈，或視為獨立政權——待與上一題一併細化，本 PRD §6 schema 已預留空白，待確認後補欄位設計。
- [ ] TODO：憲法 §2 領域角色中「開發者」「使用者」兩個角色的具體業務職責尚未展開描述。
- [ ] TODO：憲法 R3 提及的「政權間互動」（例如貿易/戰爭/外交）目前沒有對應的憲法 §6 術語定義，未來可能需要補充，本 PRD Story 2 的互動清單完整類型定義因此暫留白。

**來自 notes §十一（GIS 技術選型層，需技術選型確認，至少列出關鍵項目）**：

- [ ] TODO：地圖引擎最終選型——MapLibre GL JS 單獨使用，還是搭配 Deck.gl？
- [ ] TODO：資料供應策略——純 GeoJSON vs MVT（Martin/Tegola）vs PMTiles 靜態，三者是否分階段導入？
- [ ] TODO：是否現階段就導入 XState 管理政權狀態機，或先用簡單 enum + 應用層邏輯？
- [ ] TODO：紀年轉換庫涵蓋範圍——`lunar-javascript` 是否涵蓋非中國紀年（日本昭和、民國年等），或需自建年號對照表？
- [ ] TODO：斜線網底（爭議控制區）的顏色/間距參數是否需做成可設定的「中立配色 Design Token」？
- [ ] TODO：開源歷史地理資料（CHGIS/OHM/CShapes）授權條款是否符合本專案使用情境（含未來教育用途）？
- [ ] TODO：`historical_event_perspectives.regime_id` 是否強制對應已建檔政權實體，還是允許「國際第三者」等非政權主體的自由文字？
- [ ] TODO：EDTF 字串是否用現成 parser（npm `edtf`）解析，`start_decimal`/`end_decimal` 由後端寫入時自動推算還是離線批次計算，平閏年誤差是否需要更精確公式？

**其他 PRD 產出過程中發現的待確認事項**：

- [ ] TODO：Auth 機制（§5）——第一階段僅開發者自用，是否仍需 JWT/Session？
- [ ] TODO：設計交付模式（`design_output_mode`）與是否需要 Figma 同步（`figma_sync_mode`/`figma_target`）尚未確認，見下方「使用者待確認事項」。
