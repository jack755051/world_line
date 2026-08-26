---
schema_version: 1
plan_id: world-line-implementation-plan
plan_name: World Line — 實作執行計畫（M1-M3 顆粒化）
status: draft
owner: jack755051@gmail.com
date: 2026-08-26
related_prd: .claude/prds/world-line.md
related_constitution: .claude/constitutions/world-line.md
---

# World Line — 實作執行計畫

> 這份文件**不是 PRD**（不重複寫 user story / tech stack 理由，那些定案內容都在 `.claude/prds/world-line.md`）。
> 它只回答：**PRD §10 里程碑（M1-M5）具體要怎麼拆成可執行的任務、每個階段做到哪裡就該停、以及還沒排進任何階段但已知要做的事放哪裡。**
>
> M1-M3 是近期、範圍明確，顆粒化到「一個任務一次 commit」等級。M4-M5（世界史、單一國家史）目前只保留 PRD 原有的階段描述，**不做過早細化**——等 M1-M3 跑完、有實際回饋後再回來展開，避免對還沒開始的階段預先設計太多。
>
> **2026-08-26 更新（grill-me 第二輪，針對本計畫文件本身）**：拍板 4 項：(1) Phase 3 明確不做編輯 UI，資料寫入純靠 API；(2) Phase 2/3 補上 Commit 欄位並拆細任務（例：原本混在一起的事件相關端點拆成 4 個獨立任務）；(3) Auth 金鑰採環境變數存單一固定 key；(4) TopoJSON+Flubber.js 形變動畫從 Backlog 移入 Phase 3 正式任務（3.6），因為淡入淡出等簡化方案無法滿足憲法 §9「疆域連續變化」的核心要求。過程中也發現 `reign_eras` 表先前只在 PRD §5 拍板要用、卻沒有真的加進 §6 schema，已一併補上（PRD 與本計畫的 Phase 1 任務 1.4 都已更新為 14 張表）。

---

## 1. 總覽

| 階段 | 對應 PRD 里程碑 | 這份文件的顆粒化狀態 |
|---|---|---|
| Phase 1 | M1：Schema + API 定案，PostGIS extension 安裝完成 | ✅ 已顆粒化（見 §2） |
| Phase 2 | M2：後端 MVP（中國史階段政權/疆域 CRUD + 時間區間查詢） | ✅ 已顆粒化（見 §3） |
| Phase 3 | M3：前端整合（時間拉桿 + 地圖渲染 + 中國史資料上線） | ✅ 已顆粒化（見 §4） |
| Phase 4 | M4：世界史階段擴充（多文明並存渲染、事件圖層與多重視角初版） | ⏸ 維持 PRD 原描述，M3 完成後再展開 |
| Phase 5 | M5：單一國家史深化（如台灣史）+ 教育對象開放評估 | ⏸ 維持 PRD 原描述，M4 完成後再展開 |

**全域範圍上限（適用所有階段）**：
- 不做遊戲化虛構劇情、不做未來推測（憲法 §1 永久排除，PRD §3 非範圍）
- 不做城市層級疆域（PRD R1 範圍限制）
- 不做史前歷史（階段性延後，非本輪任何 phase 處理）
- 每個 phase 完成的定義是「PRD 對應驗收門檻達成」，不是「順手多做一點」——多做的東西進 §5 待評估清單，不要塞進當前 phase

---

## 2. Phase 1（M1）：資料層定案

**目標**：把 PRD §6 的 14 張表從紙上設計變成可以真的建表、真的能驗證 I1-I5 約束的資料庫。

### 任務清單

| 狀態 | # | 任務 | 產出 | Commit 建議 |
|---|---|---|---|---|
| [x] | 1.1 | `docker-compose.yml` postgres image 換成 `postgis/postgis:16-3.4` | 容器可跑，`SELECT postgis_version();` 有回應 | 1 個 commit |
| [x] | 1.2 | `api/` 加入 `Npgsql.EntityFrameworkCore.PostgreSQL` + `Npgsql.EntityFrameworkCore.PostgreSQL.NetTopologySuite` NuGet 套件 | `WorldLine.Api.csproj` 依賴更新 | 併入 1.3 |
| [x] | 1.3 | 建立 `WorldLineDbContext` | 空 DbContext 可注入、可連線 | 1 個 commit |
| [x] | 1.4 | 依 PRD §6 建立 **14 個** Entity 類別（`Regime`/`RegimeAlias`/`RegimeTerritory`/`ReignEra`/`PlaceName`/`LineagePreset`/`LineagePresetMember`/`RegimeRelation`/`HistoricalEvent`/`EventTag`/`HistoricalEventTagMap`/`ObserverCategory`/`HistoricalEventPerspective`/`HistoricalEventControversy`）——**⚠️ `ReignEra` 是 2026-08-26 grill-me 補回的，先前 §5 拍板要用但漏掉沒進 schema，見 PRD §6 更新紀錄** | Entity 類別 + Fluent API 設定（FK、`INT4RANGE`、`GEOMETRY` 型別對應） | 拆 3 個 commit：①政權群組（Regime/RegimeAlias/RegimeTerritory/ReignEra/PlaceName）②史觀與關係群組（LineagePreset/LineagePresetMember/RegimeRelation）③事件群組（HistoricalEvent/EventTag/HistoricalEventTagMap/ObserverCategory/HistoricalEventPerspective/HistoricalEventControversy） |
| [x] | 1.5 | 產出並套用第一份 EF Core migration | `dotnet ef database update` 成功，**14 張表**都建起來 | 1 個 commit |
| [x] | 1.6 | 驗證 I1-I5 約束在 schema 層可行 | 手動測試：漏填時間區間會被擋（I1）、漏填自稱名稱會被擋（I2）、`regime_aliases.regime_id` FK 擋孤兒代稱（I4）——寫成簡短驗證筆記，不必是正式測試套件 | 不需額外 commit，併入 1.5 |
| [x] | 1.7 | 種子資料（seed data）：**上限＝5-8 筆政權**（建議：漢、曹魏、蜀漢、東吳、西晉），涵蓋分裂/禪讓/滅亡三種轉換邊都至少出現一次，外加 1 個 `lineage_presets`（「傳統教科書史觀」）示範。**`regime_territories` 每個政權至少 2-3 筆快照**（不可一個政權只放一筆涵蓋全存續期間的疆域），建議蜀漢/東吳各自針對荊州易手（208/215/219 年前後）多放 1-2 筆快照，用來驗證「事件驅動快照密度」在同一區域可以比穩定期政權密集。**外加每個政權至少 1-2 筆 `reign_eras`**（例：蜀漢「章武」「建興」）、**外加至少 1 筆 `regime_relations`**（例：赤壁之戰前孫劉聯盟關係，用來驗證這張表也能查得到） | 一份可重複執行的 seed script | 1 個 commit |

### 範圍上限（本階段不做）

- ❌ 不寫任何 API endpoint（那是 Phase 2）
- ❌ 不寫任何前端程式碼
- ❌ 不匯入完整歷史資料集（CHGIS/OHM 的正式資料匯入是 Phase 2 後段或 Phase 4 的事，這裡只要能驗證 schema 正確的最小樣本）
- ❌ 不處理監控（PRD §5 標 TODO，不在 M1 範圍）

### 停止條件（遇到以下情況先回報，不要硬做）

- 某個 Entity 的 Fluent API 設定卡在 NetTopologySuite 版本相容性問題超過合理排查時間 → 回報，可能需要調整套件版本或改用原生 SQL migration
- I1-I5 某條約束發現在 schema 層做不到（例如需要跨表 CHECK constraint，PostgreSQL 原生不支援）→ 回報，討論要不要下放到應用層驗證

### 驗證標準

- `docker compose up` 後 API 容器能連上 postgis 容器
- `dotnet ef database update` 無錯誤
- 種子資料能重複執行（idempotent 或先清空再灌）

### 1.6 驗證筆記（2026-08-26，手動測試，非正式測試套件）

在暫時起的 dev PostGIS 容器上跑 `dotnet ef migrations add InitialCreate` + `dotnet ef database update`，14 張表（含 `__EFMigrationsHistory`）全部建立成功，PostGIS/tiger/topology 相關表也隨映像檔一起就緒。手動用 `psql` 驗證約束：

- **I2**（自稱名稱必填）：`INSERT INTO regimes (...)` 不帶 `self_name` → `null value in column "self_name"` NOT NULL 擋下 ✅
- **I1**（時間區間必填）：`INSERT INTO regime_territories (...)` 不帶 `valid_period` → `null value in column "valid_period"` NOT NULL 擋下 ✅
- **I4**（他稱代稱不可孤兒）：`INSERT INTO regime_aliases` 的 `regime_id` 指向不存在的政權 → FK constraint `fk_regime_aliases_regimes_regime_id` 擋下 ✅
- **I3**（爭議並存標記）與 **I5**（修正保留版本歷史）：這兩條不是單純 NOT NULL/FK 能表達的約束（I3 需要「同期間不可有兩筆互相矛盾的非爭議記錄」這種跨列邏輯，I5 是「用 API 產生新版本而非直接 UPDATE/DELETE」的操作流程約束），schema 層只能提供必要欄位（`is_disputed`、`superseded_by`/`correction_reason`/`corrected_at`），實際約束邏輯留到 Phase 2 應用層（2.7 疆域修正端點）強制執行，不在本階段（Phase 1）驗證範圍內。

---

## 3. Phase 2（M2）：後端 MVP

**目標**：政權/疆域/事件的 CRUD 與查詢 API 全部能動，且合法轉換規則、EDTF 解析、reign_eras 查詢都在後端跑得起來。

> 任務順序**依相依關係排列**（不是隨意編號）：驗證/解析類的基礎工具（2.1-2.3）要先做，因為後面的寫入端點（2.5、2.10）會呼叫它們；純查詢端點（無依賴）可以穿插先做。

### 任務清單

| 狀態 | # | 任務 | 產出 | 對應 PRD | Commit 建議 |
|---|---|---|---|---|---|
| [ ] | 2.1 | 後端政權狀態機合法轉換驗證器（C#，唯一信任來源） | `RegimeTransitionValidator` 服務，依憲法 §4 規則表判斷「存續→分裂／存續→被取代禪讓／存續→被滅亡」是否合法 | §5 XState 驗證分工 | 1 個 |
| [ ] | 2.2 | EDTF 套件整合 | 選定 .NET 生態的 EDTF 套件（若無成熟套件，見下方停止條件），封裝一個 `EdtfService`：格式驗證 + 換算 `start_decimal`/`end_decimal`（含閏年天數正確處理） | §5 EDTF 拍板 | 1 個 |
| [ ] | 2.3 | `reign_eras` 查詢端點 | `GET /api/v1/reign-eras?year={y}`（依年份查年號）、`GET /api/v1/regimes/:id/reign-eras`（依政權查所有年號） | §5 紀年轉換 | 1 個 |
| [ ] | 2.4 | 政權查詢端點（唯讀） | `GET /api/v1/regimes`（支援 `?year=`/`?period=` 過濾）、`GET /api/v1/regimes/:id` | §7 | 1 個 |
| [ ] | 2.5 | 政權寫入端點 | `POST /api/v1/regimes`（I2 校驗自稱名稱必填）、`PATCH /api/v1/regimes/:id`（呼叫 2.1 驗證器擋非法轉換） | §7 | 1 個 |
| [ ] | 2.6 | 疆域查詢端點（唯讀） | `GET /api/v1/regimes/:id/territories`、`GET /api/v1/territories?year={y}`（R2/Story 1 核心查詢） | §7 | 1 個 |
| [ ] | 2.7 | 疆域寫入 + 修正端點 | `POST /api/v1/regimes/:id/territories`（I1 校驗時間區間必填）、`PATCH /api/v1/territories/:id/correct`（I5 版本鏈：新增新版本、`superseded_by` 指回、不覆蓋刪除原記錄） | §7 | 1 個（修正邏輯較複雜，獨立驗證） |
| [ ] | 2.8 | 史觀主線 preset 查詢端點 | `GET /api/v1/lineage-presets`、`GET /api/v1/lineage-presets/:id/regimes` | §7 | 1 個 |
| [ ] | 2.9 | 政權持續性關係 CRUD | `GET /api/v1/regimes/:id/relations?year={y}`、`POST /api/v1/regimes/:id/relations` | §7 | 1 個 |
| [ ] | 2.10 | 事件骨幹 CRUD | `GET /api/v1/events?year={y}`、`GET /api/v1/events/:id`、`POST /api/v1/events`（寫入時呼叫 2.2 EdtfService，含 `parent_event_id` 組成關係） | §7 | 1 個 |
| [ ] | 2.11 | 事件類型標籤 | `GET /api/v1/event-tags`（列出可用標籤）、事件寫入端點（2.10）支援帶 `tag_ids` 陣列建立 `historical_event_tag_map` | §6 事件三維度 | 1 個 |
| [ ] | 2.12 | 觀察者類別 + 多重視角敘事 | `GET /api/v1/observer-categories`、`GET /api/v1/events/:id/perspectives`、`POST .../perspectives`（應用層驗證 `regime_id`/`observer_category_id` 至少擇一非 NULL） | §6、Story 3 | 1 個 |
| [ ] | 2.13 | 事件爭議點 | `GET /api/v1/events/:id/controversies`、`POST .../controversies` | §6 notes §十.2 | 1 個 |
| [ ] | 2.14 | 最小 Auth middleware | **已拍板（2026-08-26）**：`.env` 存單一固定 `API_WRITE_KEY`，middleware 檢查所有 POST/PATCH request header（例：`X-API-Key`）是否相符，不符回 401；GET 端點不掛此 middleware | §5 Auth 拍板 | 1 個 |
| [ ] | 2.15 | 測試 | 單元測試（.NET 預設用 xUnit）涵蓋 2.1 狀態機驗證、2.2 EDTF 換算（含閏年案例）；integration test 涵蓋 2.4-2.13 主要端點 | PRD M2 驗收門檻 | 1 個 |

### 範圍上限（本階段不做）

- ❌ 不做前端串接（Phase 3）
- ❌ 不產出正式 OpenAPI 文件精修（先用 ASP.NET 內建 OpenAPI，細節排到後面）
- ❌ 不做 MVT/PMTiles（PRD 已拍板 Phase 1 純 GeoJSON，這裡端點直接回 GeoJSON 即可）
- ❌ 不擴充 Auth 到正式使用者帳號/JWT 登入系統，維持 2.14 的單一固定 key 方案（PRD §5 已拍板的最小方案，多使用者升級見 §5 Backlog）
- ❌ 不做任何前端會用到的「編輯表單」相關後端邏輯（例如批次匯入 API）——2.5/2.7/2.9/2.10 等寫入端點只求「打得通」，UI 串接與批次工具不在本階段

### 停止條件

- EDTF 在 .NET 生態找不到成熟套件、需要自己刻完整 parser 且工作量明顯超出「一個 phase」的量級 → 回報，重新評估是否退回自訂正則的簡化版本（先只支援憲法/notes 實際會用到的格式子集，不追求完整 EDTF 規格覆蓋）
- 政權狀態機驗證邏輯發現憲法 §4 沒講清楚的邊界情況（例如「分裂後又被取代」這種複合轉換）→ 回報，不要自行腦補規則
- I5 疆域修正端點（2.7）的版本鏈邏輯發現需要支援「修正一筆已經被修正過的記錄」這種鏈式情境，且憲法/PRD 沒講清楚多層修正要怎麼呈現 → 回報

### 驗證標準

- 所有端點可用 Postman/`*.http` 檔案手動打通
- 單元測試涵蓋 I1-I5 約束在 API 層的攔截行為
- 種子資料（Phase 1 的漢/魏/蜀/吳/晉，含 `reign_eras` 與 1 筆 `regime_relations`）能透過 API 完整查出，包含轉換邊與 lineage_preset

---

## 4. Phase 3（M3）：前端整合

**目標**：時間拉桿能拖、地圖能看到政權疆域**真正連續形變**（不是切換），中國史種子資料能在畫面上動起來。

> **明確範圍決定（2026-08-26 grill-me）**：本階段**只做唯讀/瀏覽功能**，不含任何政權/疆域/事件的新增或編輯表單 UI。Phase 1-3 期間資料寫入一律透過 Phase 2 的 API 直接打（Postman/`*.http`/script），不做圖形化編輯介面。這是刻意決定，不是遺漏——理由見 §5 Backlog「管理後台/編輯 UI」條目。

### 任務清單

| 狀態 | # | 任務 | 產出 | 對應 PRD | Commit 建議 |
|---|---|---|---|---|---|
| [ ] | 3.1 | 前端 XState 政權狀態機定義（UI 層防呆，非信任來源） | 前端 state machine 定義檔 | §5 | 1 個 |
| [ ] | 3.2 | MapLibre GL JS 整合 + 底圖 | 地圖能顯示、能平移縮放 | §5、§8 | 1 個 |
| [ ] | 3.3 | 時間軸 Scrubber 主軸（世紀/年） | 可連續拖動元件，對應憲法 §9「非離散跳轉」 | §8 notes §六 | 1 個 |
| [ ] | 3.4 | 時間軸 Scrubber 副軸（月/日展開） | 聚焦近代事件時下方展開精細軸 | §8 notes §六 | 1 個（依賴 3.3） |
| [ ] | 3.5 | 政權疆域圖層渲染（基礎版，GeoJSON + MapLibre filter expressions） | 拖動時間拉桿時，依快照篩出當下應顯示的疆域（尚未做形變，見 3.6） | Story 1 | 1 個 |
| [ ] | 3.6 | **疆域快照間形變過渡動畫（TopoJSON + Flubber.js）** | 拖動拉桿時，兩筆快照之間的疆域邊界真正連續變形，不是切換/淡入淡出——對應憲法 §9「疆域必須連續變化呈現，非離散跳轉」核心要求（2026-08-26 拍板：從 Backlog 移入本階段，非候選） | Story 1、§9 | 1-2 個（拓撲前處理 1 個、Flubber 整合+播放時機控制 1 個） |
| [ ] | 3.7 | 政權聚焦模式（點擊疆域→高亮+周邊政權清單） | Story 2 完整流程 | Story 2 | 1 個 |
| [ ] | 3.8 | 政權命名視角切換（自稱／他稱代稱） | Story 3 完整流程 | Story 3 | 1 個 |
| [ ] | 3.9 | 政權狀態轉換視覺呈現（分裂/禪讓/滅亡三種視覺區分） | Story 4 完整流程 | Story 4 | 1 個 |
| [ ] | 3.10 | EDTF 精度/不確定性 UI 標示（模糊年份提示） | Story 5 完整流程 | Story 5 | 1 個 |
| [ ] | 3.11 | reign_eras 年號標籤顯示（對應時間拉桿位置顯示年號） | UI 顯示「貞觀元年」等 | §5 紀年轉換 | 1 個 |
| [ ] | 3.12 | 事件詳情抽屜（毛玻璃 + 三層手風琴） | notes §八互動草圖落地 | §8 | 1 個 |
| [ ] | 3.13 | 多重視角分頁（Perspective Tabs） | notes §十互動草圖落地 | §8、Story 3 | 1 個 |
| [ ] | 3.14 | 四態齊備（loading/empty/error/success，依 §8 逐頁核對） | 每個主要頁面四態都有畫面 | §8 | 1 個 |
| [ ] | 3.15 | 共用常數檔（斜線網底顏色/間距，§5 已拍板方案） | `neutral-map-colors.ts` 或同等檔案 | §5 | 1 個 |
| [ ] | 3.16 | E2E 測試主流程（時間拖動→疆域形變→聚焦→事件詳情） | E2E 測試綠燈 | PRD M3 驗收門檻 | 1 個 |

### 範圍上限（本階段不做）

- ❌ **不做任何政權/疆域/事件的新增或編輯表單 UI**（見上方範圍決定）
- ❌ 不做 Deck.gl（PRD 已拍板 Phase 1 不導入）
- ❌ 不做 MVT/PMTiles 資料供應（PRD 已拍板 Phase 1 純 GeoJSON）
- ❌ 不做正式 Design Token 系統（PRD 已拍板先用共用常數檔）
- ❌ 不做深色模式
- ❌ 不做世界史階段的跨文明資料（那是 M4，這裡只用中國史種子資料）

### 停止條件

- MapLibre 的時間過濾在資料量變大（超過種子資料規模）時出現明顯效能問題 → 回報，這是提早驗證「Phase 1 純 GeoJSON 夠不夠用」的訊號，不要默默切換到 MVT
- 語意縮放（年級 vs 日/月級切換顯示內容）的互動規則發現 notes 草稿沒講清楚的邊界情況 → 回報，不要自行拍板 UX 細節
- **3.6 形變動畫**：若兩筆相鄰快照的多邊形拓撲差異過大（例如環數/頂點數差異懸殊，Flubber.js 演算法產生扭曲、自相交等視覺上明顯錯誤的中間形狀）→ 回報，不要為了「動畫要連續」硬把明顯失真的中間形狀端出來；可能需要在該區間補充更多快照（回頭調整 Phase 1 seed 密度）或該區間退回簡單交叉淡化當例外處理，此為需要使用者判斷的取捨，不由 AI 自行決定

### 驗證標準

- 手動走一遍 Story 1-5 的 Acceptance Criteria，全部過
- 手動確認 3.6 形變動畫：拖動拉桿經過荊州易手種子資料區間，疆域邊界應可見連續移動，不是生硬切換
- E2E 測試涵蓋主流程
- `npm run build` 無錯誤，四態畫面截圖存查

---

## 5. 待評估／後續延伸清單（Backlog，不綁定特定 phase）

> 這些是 grill-me 過程中討論過、但明確決定「現在不做」的項目，或是 PRD §5 表格裡標「候選，未在本輪討論」的項目。放在這裡是為了不遺忘，但**不預先排進 M1-M3**，避免過早設計沒有具體使用情境的東西。

- **管理後台/資料編輯 UI**——Phase 1-3 刻意不做（見 Phase 3 範圍決定），資料寫入純靠 API 直打。待需要多人協作編輯史料，或開發者自己覺得手動打 API 太痛苦時，再評估要不要做一個最小的表單頁面
- Turf.js（政權標籤置中點計算、邊界簡化）——等實際遇到標籤重疊/多邊形過於複雜再評估
- **形變動畫的插值不確定性標示**（TopoJSON+Flubber.js 已於 2026-08-26 拉進 Phase 3 任務 3.6，非 Backlog，此處僅保留一項延伸子議題）：快照間隔稀疏時做形變插值，畫面呈現的「漸變」不代表史料證實的逐年精確疆域，UI 上要不要標示「此區間為視覺插值推算」——3.6 先求「連續變化不生硬」這個核心要求達標，這個「插值不確定性標示」的精緻化留到 Phase 3 跑完後視覺呈現有餘裕再評估
- Dayjs/Luxon BCE 擴充——等真的需要顯示西元前政權（例如秦朝 -221）時再確認函式庫選擇
- Deck.gl 疊加（貿易路線動畫、傳播視覺化）——待 Phase 4 世界史階段有具體路線視覺化需求時評估
- Martin/Tegola 動態切片、PMTiles 靜態切片——待 Phase 4 全球資料量體造成效能瓶頸時評估
- 正式 Design Token 系統——待深色模式或多人協作需求出現時評估
- 監控（Prometheus/OpenTelemetry/Grafana）——尚未評估，等有實際維運需求
- Auth 升級為多使用者/角色權限系統——待開放教育對象使用時評估（憲法 §1 階段順序）
- CHGIS/CShapes 授權重新確認——僅在出現贊助/政府投資等資金來源時才需處理（見 PRD §9）
- `historical_event_controversies.viewpoints` 是否標準化 schema（強制附學者/文獻來源）——待第一個真實跨國爭議事件建檔時再細化

---

## 6. 建議執行順序

1. Phase 1 全部任務 → 驗證標準過 → commit 收尾
2. Phase 2 全部任務 → 驗證標準過 → commit 收尾
3. Phase 3 全部任務 → 驗證標準過 → commit 收尾
4. 回頭檢視 §5 Backlog，依 Phase 1-3 實作過程中的實際痛點，挑選真正需要的項目才處理
5. 展開 Phase 4（M4 世界史）的顆粒化計畫——此時才具體規劃，不在本文件內預先展開

## 7. 開放問題

- [ ] TODO：Phase 1-3 沒有時程估計（PRD 本身日期也全標 TODO），若使用者需要粗略工時預估，需另外討論
- [ ] TODO：種子資料（Phase 1 §2 任務 1.7）的「漢/魏/蜀/吳/晉」是否為使用者認可的最小驗證樣本，或有其他偏好的測試資料集
