---
schema_version: 1
plan_id: world-line-implementation-plan
plan_name: World Line — 實作執行計畫（M1-M3 顆粒化）
status: active
owner: jack755051@gmail.com
date: 2026-08-27
related_prd: .claude/prds/world-line.md
related_constitution: .claude/constitutions/world-line.md
---

# World Line — 實作執行計畫

> **文件狀態**：本計畫是目前有效的執行清單。`active` 不代表所有工作完成；核取方塊才是進度來源。截至 2026-08-27，Phase 1 已完成（含後續補上的第 15 張 `regime_transition_events`），Phase 2 與 Phase 3 尚未開始。

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
| Phase 1 | M1：資料層定案，PostGIS extension 安裝完成 | ✅ 已完成（見 §2） |
| Phase 2 | M2：後端 MVP（中國史階段政權/疆域 CRUD + 時間區間查詢） | ⏳ 尚未開始，已顆粒化（見 §3） |
| Phase 3 | M3：前端整合（時間拉桿 + 地圖渲染 + 中國史資料上線） | ⏳ 尚未開始，已顆粒化（見 §4） |
| Phase 4 | M4：世界史階段擴充（多文明並存渲染、事件圖層與多重視角初版） | ⏸ 維持 PRD 原描述，M3 完成後再展開 |
| Phase 5 | M5：單一國家史深化（如台灣史）+ 教育對象開放評估 | ⏸ 維持 PRD 原描述，M4 完成後再展開 |

**全域範圍上限（適用所有階段）**：
- 不做遊戲化虛構劇情、不做未來推測（憲法 §1 永久排除，PRD §3 非範圍）
- 不做城市層級疆域（PRD R1 範圍限制）
- 不做史前歷史（階段性延後，非本輪任何 phase 處理）
- 每個 phase 完成的定義是「PRD 對應驗收門檻達成」，不是「順手多做一點」——多做的東西進 §5 待評估清單，不要塞進當前 phase

---

## 2. Phase 1（M1）：資料層定案

**目標**：把 PRD §6 的資料模型變成可 migration、可 seed、可驗證的 PostGIS 資料庫。初版建立 14 張領域表，2026-08-27 再以第二份 migration 補上第 15 張 `regime_transition_events`。I1/I2/I4 由 schema 直接強制；I3/I5 在本階段只驗證 schema 具備必要欄位，完整行為約束交由 Phase 2 應用層完成。

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

**⚠️ 事後補充（2026-08-26，真正跑 `docker compose up` 時發現）**：1.5-1.7 一開始只在臨時起的驗證容器上跑過 migration/seed，沒套用到 `docker-compose.yml` 真正在用的 `app_postgres`。使用者自己跑 `docker compose up` 後，`app_backend` 因為 `regimes` 表不存在（migration 沒套用過）而 crash loop。修法：`Program.cs` 在 seed 之前補上 `await seedDb.Database.MigrateAsync();`，讓 Development 環境啟動時自動套用 migration，重建 image 後 `app_backend` 穩定啟動，`app_postgres` 裡也確認查得到 5 筆政權資料。**這提醒了一件事：驗證用臨時容器測過，不等於真正的 docker-compose 流程測過**，之後每個 phase 收尾前應該找機會用真正的 `docker compose up` 走一次，不能只信任臨時容器的驗證結果。

**⚠️ 事後補充（2026-08-27）**：討論政權轉換邊（分裂/禪讓/滅亡）跟 `historical_events` 的關係時，發現兩者原本沒有因果連結——`regimes` 只記錄「發生過什麼轉換」，查不出「是哪個事件導致的」。拍板新增第 15 張表 `regime_transition_events`（多對多，`transition_kind` 區分 origin/destruction），已建立並套用 EF Core migration `AddRegimeTransitionEvents`。**PRD §6 已同步更新為 15 張表**，本文件 1.4 的「14 個 Entity 類別」文字保留原樣（不回溯改寫已完成任務的敘述），新增的 entity 視為 Phase 1 之後的一次獨立 schema 演進，不補記 commit 編號到 1.4。

**⚠️ 事後補充（2026-08-28）**：盤點發現 1.7 的種子資料只涵蓋 15 張表中的 6 張，`RegimeAlias`、`PlaceName`、`HistoricalEvent` 全家族（含 tags/perspectives/controversies）、`RegimeTransitionEvent` 這 9 張完全沒有測試資料；另外 I3（爭議並存）也沒被真正驗證到——原本 208-215 荊州區間只有單一政權各自標 `IsDisputed=true`，不是「同一政權、同一時間點、兩筆互相矛盾記錄」的真實情境。`api/Data/SeedData.cs` 已補上：(1) 蜀漢 208-215 年第二筆衝突疆域記錄，構成真正的 I3 測試組；(2) 2 筆 `RegimeAlias`（魏被蜀漢稱「賊」、吳被後世稱「孫吳」，`AliasType` 刻意留 null，等 §12 TODO 拍板受控值）；(3) 赤壁之戰（多重視角＋爭議點示範）與魏滅蜀/晉滅吳兩場戰事（`RegimeTransitionEvent` 連結既有轉換邊示範）。已在拋棄式 PostGIS 容器上跑過完整 migration + seed 驗證無誤（見下方驗證記錄），但**尚未套用到 `docker-compose.yml` 實際在跑的 `app_postgres`**——seed 邏輯是 idempotent-skip（`regimes` 表非空就跳過），現有 `app_postgres` 裡仍是舊種子資料快照，需要清空 `regimes` 系列表或重建 volume 才會套用新資料，此步驟需使用者確認後才執行（見 §7 開放問題）。

**2026-08-28 種子資料驗證記錄**：在拋棄式 PostGIS 容器（非 `docker-compose.yml` 的 `app_postgres`）上跑 `dotnet ef database update` + 啟動 API（觸發 `SeedAsync`），無任何 FK/約束錯誤；`psql` 確認 `regime_aliases`=2 筆、`historical_events`=3 筆、`historical_event_perspectives`=2 筆、`historical_event_controversies`=1 筆、`historical_event_tag_map`=5 筆、`regime_transition_events`=2 筆、`event_tags`=2 筆、`observer_categories`=1 筆；I3 測試組確認同一 `regime_id`（蜀漢）在 `[208,215)` 有兩筆 `is_disputed=true` 的記錄。

**⚠️ 事後補充（2026-08-28 第二次，回應「M1/M2 還缺什麼」的檢視）**：上一輪盤點漏了兩個缺口，本次一併補上：(1) `place_names` 仍是 0 筆，且 Phase 2 任務清單完全沒有排它的 API（見下方新增 2.9b）；(2) `regime_transition_events` 先前只驗證過 `transition_kind='destruction'`，`'origin'` 分支（分裂/禪讓觸發的建國）完全沒有種子資料測過。順帶把「三國正統之爭」這個史學史真實案例落地成資料，直接驗證方案 D（`lineage_presets` 解耦設計）到底能不能承載多重史觀並存，而不只是文件裡宣稱可以：

- `place_names` 補 4 筆：雒陽（東漢，避水德諱）／洛陽（魏晉，改回洛字，`ValidPeriod` 相接示範同地點改名）／成都（蜀漢，古今同名示範）／建業-南京（東吳）。
- 新增 `event-han-abdicates-wei-220`、`event-wei-abdicates-jin-265` 兩筆 `historical_events`，各掛一筆 `transition_kind='origin'` 的 `regime_transition_events`，補齊 origin 分支覆蓋；兩者只標「政權更替」標籤、不標「戰爭」，跟滅蜀/滅吳形成對照，示範多對多標籤能區分和平轉移與武力消滅。
- 新增第二個 `lineage_preset`「蜀漢正統論史觀」（漢→蜀漢→晉，晉的收錄理由跟傳統教科書史觀不同，寫在 `description`），刻意讓蜀漢（`regimes.status='被滅亡'`，不是「被取代(禪讓)」）進入某個 preset 的主線並跳過魏，驗證 preset 成員資格不需要遵循客觀轉換邊。
- 在 `event-han-abdicates-wei-220` 上掛一筆 `historical_event_controversies`：陳壽《三國志》（西晉）尊魏、習鑿齒《漢晉春秋》（東晉）與朱熹《資治通鑑綱目》（南宋）尊蜀漢，並在 `neutral_description` 點出三派分歧跟各自成書朝代的政治處境相關，不是純史料判斷。

驗證方式同上（拋棄式容器 `dotnet ef database update` + 觸發 `SeedAsync`），`dotnet build` 0 錯誤 0 警告；`psql` 確認 `place_names`=4、`historical_events`=5、`historical_event_controversies`=2、`lineage_presets`=2、`lineage_preset_members`=6、`regime_transition_events`=4（origin 2 + destruction 2）。**同樣尚未套用到 `docker-compose.yml` 的 `app_postgres`**，累積成同一個待你決策的動作，見 §7。

---

## 3. Phase 2（M2）：後端 MVP

**目標**：政權/疆域/事件的 CRUD 與查詢 API 全部能動，且合法轉換規則、EDTF 解析、reign_eras 查詢都在後端跑得起來。

> 任務順序**依相依關係排列**（不是隨意編號）：驗證/解析類的基礎工具（2.1-2.3）要先做，因為後面的寫入端點（2.5、2.10）會呼叫它們；純查詢端點（無依賴）可以穿插先做。

> **2026-08-28 更新**：對照 PRD §12「M2 前必須處理」清單，發現原任務清單有兩個缺口——(1) PRD §7/§12 已預期會有「M2 政權代稱 API」，但 2.1-2.15 沒有對應任務；(2) 統一回應格式決策沒有掛在任何任務上，容易被第一個實作的端點順手定案而非刻意拍板。新增 2.0（決策）與 2.9a（alias API），並把 2.12/2.13 的 JSON schema 前置決策明確寫進任務描述，避免這些 TODO 在實作時被忽略。編號沿用既有任務（2.4/2.10/2.12/2.13 等）不變動，避免打亂 PRD 裡對這些編號的既有引用。
>
> **2026-08-28 更新（第二次）**：`place_names`（憲法 §6 地名雙軌顯示）有 Entity、有 migration、現在也有 seed 資料，卻是唯一沒有任何 API 任務的領域表——不是刻意延後，是規劃時漏掉。新增 2.9b，緊跟在 2.9a alias API 之後（兩者都是查詢用的「辭典型」輔助資料，性質相近）。

### 任務清單

| 狀態 | # | 任務 | 產出 | 對應 PRD | Commit 建議 |
|---|---|---|---|---|---|
| [ ] | 2.0 | 統一回應格式與錯誤格式拍板 | 決定「直接回傳 resource/problem details」vs 包裝格式 `{ statusCode, message, data }`，並反映到 §7；後續所有端點依此格式實作 | §7、§12 TODO | 1 個（純文件決策，無程式碼） |
| [ ] | 2.1 | 後端政權狀態機合法轉換驗證器（C#，唯一信任來源） | `RegimeTransitionValidator` 服務，依憲法 §4 規則表判斷「存續→分裂／存續→被取代禪讓／存續→被滅亡」是否合法 | §5 XState 驗證分工 | 1 個 |
| [ ] | 2.2 | EDTF 套件整合 | 選定 .NET 生態的 EDTF 套件（若無成熟套件，見下方停止條件），封裝一個 `EdtfService`：格式驗證 + 換算 `start_decimal`/`end_decimal`（含閏年天數正確處理） | §5 EDTF 拍板 | 1 個 |
| [ ] | 2.3 | `reign_eras` 查詢端點 | `GET /api/v1/reign-eras?year={y}`（依年份查年號）、`GET /api/v1/regimes/:id/reign-eras`（依政權查所有年號） | §5 紀年轉換 | 1 個 |
| [ ] | 2.4 | 政權查詢端點（唯讀） | `GET /api/v1/regimes`（支援 `?year=`/`?period=` 過濾）、`GET /api/v1/regimes/:id` | §7 | 1 個 |
| [ ] | 2.5 | 政權寫入端點 | `POST /api/v1/regimes`（I2 校驗自稱名稱必填）、`PATCH /api/v1/regimes/:id`（呼叫 2.1 驗證器擋非法轉換） | §7 | 1 個 |
| [ ] | 2.6 | 疆域查詢端點（唯讀） | `GET /api/v1/regimes/:id/territories`、`GET /api/v1/territories?year={y}`（R2/Story 1 核心查詢） | §7 | 1 個 |
| [ ] | 2.7 | 疆域寫入 + 修正端點 | `POST /api/v1/regimes/:id/territories`（I1 校驗時間區間必填）、`PATCH /api/v1/territories/:id/correct`（I5 版本鏈：新增新版本、`superseded_by` 指回、不覆蓋刪除原記錄） | §7 | 1 個（修正邏輯較複雜，獨立驗證） |
| [ ] | 2.8 | 史觀主線 preset 查詢端點 | `GET /api/v1/lineage-presets`、`GET /api/v1/lineage-presets/:id/regimes` | §7 | 1 個 |
| [ ] | 2.9 | 政權持續性關係 CRUD | `GET /api/v1/regimes/:id/relations?year={y}`、`POST /api/v1/regimes/:id/relations` | §7 | 1 個 |
| [ ] | 2.9a | 政權代稱（Alias）CRUD | 先拍板 `alias_type` 受控值（若提不出比 observer relationship 更清楚的語意就直接移除該欄位，§12 TODO）；`GET /api/v1/regimes/:id/aliases`、`POST /api/v1/regimes/:id/aliases`（I4 校驗 `regime_id` FK 必存在） | §6、§7、§12 TODO | 1 個 |
| [ ] | 2.9b | 地名雙軌查詢端點 | `GET /api/v1/place-names?year={y}`（依年份查當時使用中的地名，`valid_period` 區間匹配）、`GET /api/v1/place-names/:id`；回傳含 `historical_name`/`modern_name`（可為 NULL）雙欄位，不做寫入端點（seed 已覆蓋首都示範，正式匯入前的來源治理見 `docs/data-governance.md`） | 憲法 §6、§7 | 1 個 |
| [ ] | 2.10 | 事件骨幹 CRUD | `GET /api/v1/events?year={y}`、`GET /api/v1/events/:id`、`POST /api/v1/events`（寫入時呼叫 2.2 EdtfService，含 `parent_event_id` 組成關係） | §7 | 1 個 |
| [ ] | 2.11 | 事件類型標籤 | `GET /api/v1/event-tags`（列出可用標籤）、事件寫入端點（2.10）支援帶 `tag_ids` 陣列建立 `historical_event_tag_map` | §6 事件三維度 | 1 個 |
| [ ] | 2.12 | 觀察者類別 + 多重視角敘事 | **寫入端點實作前先定義 `primary_sources`/`claimed_casualties` 的 JSON schema 與最小 citation 欄位（§12 TODO）**；`GET /api/v1/observer-categories`、`GET /api/v1/events/:id/perspectives`、`POST .../perspectives`（應用層驗證 `regime_id`/`observer_category_id` 至少擇一非 NULL） | §6、Story 3、§12 TODO | 1 個 |
| [ ] | 2.13 | 事件爭議點 | **寫入端點實作前先定義 `viewpoints` 的 JSON schema 與最小 citation 欄位（§12 TODO，可與 2.12 併案決定）**；`GET /api/v1/events/:id/controversies`、`POST .../controversies` | §6 notes §十.2、§12 TODO | 1 個 |
| [ ] | 2.14 | 最小 Auth middleware | **已拍板（2026-08-26）**：`.env` 存單一固定 `API_WRITE_KEY`，middleware 檢查所有 POST/PATCH request header（例：`X-API-Key`）是否相符，不符回 401；GET 端點不掛此 middleware | §5 Auth 拍板 | 1 個 |
| [ ] | 2.15 | 測試與契約驗證 | 單元測試（.NET 預設用 xUnit）涵蓋 2.1 狀態機驗證、2.2 EDTF 換算（含閏年案例）；integration test 涵蓋 2.4-2.13、2.9a 主要端點；ASP.NET 產生的 OpenAPI 必須包含所有已實作端點、request/response schema 與主要狀態碼 | PRD M2 驗收門檻 | 1 個 |

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

- 所有端點可用 `api/*.http` 檔案手動打通，且同一組端點可從 Development 環境的 `/openapi/v1.json` 查到契約
- 單元測試涵蓋 I1-I5 約束在 API 層的攔截行為，其中 I3（爭議並存）用 2026-08-28 補入的種子資料驗證：蜀漢 208-215 年有兩筆互相矛盾、皆標 `is_disputed=true` 的疆域記錄，API 查詢須能兩筆並列回傳，不可只回一筆或報錯
- 種子資料（Phase 1 的漢/魏/蜀/吳/晉，含 `reign_eras`、1 筆 `regime_relations`、2 筆 `regime_aliases`、4 筆 `place_names`、5 筆 `historical_events` 含多重視角/爭議點/`origin`+`destruction` 兩種轉換邊連結，見 2026-08-28 兩輪補充）能透過 API 完整查出；`GET /api/v1/lineage-presets` 須能同時查到「傳統教科書史觀」與「蜀漢正統論史觀」兩個並存的 preset，驗證方案 D 的多史觀承載能力不是只有文件宣稱

---

## 4. Phase 3（M3）：前端整合

**目標**：時間拉桿能拖、地圖能看到政權疆域**真正連續形變**（不是切換），中國史種子資料能在畫面上動起來。

> **明確範圍決定（2026-08-26 grill-me）**：本階段**只做唯讀/瀏覽功能**，不含任何政權/疆域/事件的新增或編輯表單 UI。Phase 1-3 期間資料寫入一律透過 Phase 2 的 API 直接打（Postman/`*.http`/script），不做圖形化編輯介面。這是刻意決定，不是遺漏——理由見 §5 Backlog「管理後台/編輯 UI」條目。

> **2026-08-28 更新**：拍板 UI 元件庫選型——採用 **Sanring UI**（`https://ui.sanring.dev/`，source-first Angular headless primitives，`@sanring/cli` 把元件原始碼複製進 `app/`，非傳統 npm 依賴）。需求 Angular 22.x / TypeScript >=6.0.0 <6.1.0，與現有 `app/package.json` 相符；唯一新增依賴是 **Tailwind CSS v4**（目前專案尚未安裝）。已解決 notes §十一「毛玻璃側邊抽屜／手風琴要不要用 headless component library」開放問題，見 PRD §5 B。新增任務 3.0 作為 Phase 3 前置工作。

### 任務清單

| 狀態 | # | 任務 | 產出 | 對應 PRD | Commit 建議 |
|---|---|---|---|---|---|
| [ ] | 3.0 | 引入 Sanring UI + Tailwind CSS v4（`app/` 前端樣式基礎建設） | `npx @sanring/cli init` 設定完成、Tailwind v4 安裝並接上 `sanring-theme.css`、以 Button 元件驗證 hover/focus 樣式與 Angular standalone import 皆正常 | §5 UI 元件庫 | 1 個 |
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

- [ ] TODO：Phase 2-3 尚無時程估計；若使用者需要粗略工時預估，需另外討論，不從任務數直接推導承諾日期
- [x] Phase 1 最小驗證樣本採漢／魏／蜀漢／吳／晉；它只用來驗證 schema 與轉換關係，疆域矩形和簡化年份不是正式史料。正式資料匯入前仍須遵守 `docs/data-governance.md`。
- [x] 2026-08-28 兩輪補充的種子資料（I3 衝突組/alias/events/place_names/第二個 lineage_preset/origin 轉換邊/正統性爭議點）已套用到 `docker-compose.yml` 的 `app_postgres`——使用者選擇「清空 `regimes` 系列表重種」。**過程中發現一個踩坑點**：光 `docker compose restart backend` 不會重建 image，容器仍在跑舊的編譯產物，`TRUNCATE` 後重啟只會種回舊版精簡 seed；改用 `docker compose up -d --build backend` 重新編譯映像檔後再種，才拿到完整的 15 張表資料。已用 `psql` 核對 `app_postgres` 內 `place_names`=4、`historical_events`=5、`historical_event_controversies`=2、`lineage_presets`=2（含兩個 preset 各自的 3 筆成員）、`regime_transition_events`=4、`regime_aliases`=2，與拋棄式容器驗證結果一致。
