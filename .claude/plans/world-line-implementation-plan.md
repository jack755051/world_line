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

**⚠️ 事後補充（2026-08-28 第三次，「M1 是不是完全沒漏洞」的檢視）**：重新盤查 migration/entity 設定/seed 資料，又抓到兩個先前沒發現的缺口，兩個都已修：

- **PRD §5 拍板要用的 `regime_territories(regime_id, valid_period)` GiST 複合索引，先前沒被排進任何 phase 的任務清單**——是一個「決定了卻沒人接手」的孤兒項目。已在 `RegimeTerritoryConfiguration` 加上 `HasIndex(...).HasMethod("gist")`，並在 `WorldLineDbContext` 宣告 `btree_gist` extension（一般欄位要跟 `int4range` 共用 GiST 索引的必要條件），產出並套用 migration `AddRegimeTerritoryGistIndex`。
- **I5 版本鏈（`superseded_by`）從沒被種子資料真正跑過**——欄位跟 FK 一直都在，但沒有任何一筆種子資料賦值過，連「這條 FK 能不能正常 insert/查詢」都沒驗證。已補一組漢朝 `[25,189)` 的原始版＋修正版，原始列 `superseded_by` 指向修正列，`correction_reason`/`corrected_at` 一併填寫，跟既有蜀漢 I3 衝突組（同區間兩筆皆爭議、互不 supersede）刻意做語意對照。

驗證方式同上（新開一個拋棄式容器，因為這次連 migration 都變了）：`dotnet ef database update` 套用 3 份 migration 無誤，`pg_indexes` 確認 `ix_regime_territories_regime_id_valid_period` 是 `USING gist (regime_id, valid_period)`；`SeedAsync` 跑完後查漢朝 `[25,189)` 那兩筆，原始列的 `superseded_by` 確實解析到修正列的 id、修正列本身乾淨未被 supersede。已套用到 `docker-compose.yml` 的 `app_postgres`（migration 直接對現有資料庫執行、不掉資料；seed 沿用 truncate + `docker compose up -d --build backend` 的既定流程）並複查一致。至此 M1（Phase 1）沒有已知的未追蹤缺口。

**⚠️ 事後補充（2026-08-28 第四次，「西方/日式/非洲政權會不會有文化偏頗」的檢視）**：`regimes.status`／`origin_transition_type` 原本直接存憲法 §4 的中文術語當 enum 值——只有 5 筆 seed 資料就已經飄了（`status` 用「被取代(禪讓)」、`origin_transition_type` 用「被取代禪讓」，同一概念兩種字面值），且「禪讓」是中國政治史特有概念，套到非中國政權的轉型會很勉強。已改成中立代碼 `'active'|'split'|'succeeded'|'conquered'`，憲法本身業務詞彙不變（純儲存編碼調整，不觸發回寫憲法）。無 schema 變動、不需要新 migration，純資料值改寫，已套用到 `app_postgres`（同樣是 truncate + `docker compose up -d --build backend`）並確認一致。同一輪還發現一個目前**沒有修**、留給 M4 世界史階段的結構性缺口：`predecessor_regime_id` 是單一 FK，只能表達分裂（一對多），無法表達合併（多對一，例如英格蘭+蘇格蘭→大不列顛），中國史很少出現此類轉換所以三國案例沒測到；已記錄進 PRD §9 風險表與 §12「M4 前必須處理」，不在本階段動 schema。

---

## 3. Phase 2（M2）：後端 MVP

**目標**：政權/疆域/事件的 CRUD 與查詢 API 全部能動，且合法轉換規則、EDTF 解析、reign_eras 查詢都在後端跑得起來。

> 任務順序**依相依關係排列**（不是隨意編號）：驗證/解析類的基礎工具（2.1-2.3）要先做，因為後面的寫入端點（2.5、2.10）會呼叫它們；純查詢端點（無依賴）可以穿插先做。

> **2026-08-28 更新**：對照 PRD §12「M2 前必須處理」清單，發現原任務清單有兩個缺口——(1) PRD §7/§12 已預期會有「M2 政權代稱 API」，但 2.1-2.15 沒有對應任務；(2) 統一回應格式決策沒有掛在任何任務上，容易被第一個實作的端點順手定案而非刻意拍板。新增 2.0（決策）與 2.9a（alias API），並把 2.12/2.13 的 JSON schema 前置決策明確寫進任務描述，避免這些 TODO 在實作時被忽略。編號沿用既有任務（2.4/2.10/2.12/2.13 等）不變動，避免打亂 PRD 裡對這些編號的既有引用。
>
> **2026-08-28 更新（第二次）**：`place_names`（憲法 §6 地名雙軌顯示）有 Entity、有 migration、現在也有 seed 資料，卻是唯一沒有任何 API 任務的領域表——不是刻意延後，是規劃時漏掉。新增 2.9b，緊跟在 2.9a alias API 之後（兩者都是查詢用的「辭典型」輔助資料，性質相近）。
>
> **2026-08-29 更新**：憲法新增 R4（中英雙語內容支援），新增 2.16（雙語 schema）與 2.17（既有 seed 資料英文翻譯內容），並回頭在尚未動工的查詢端點任務描述補上「依賴 2.16、支援 `?locale=`」。2.3（`reign_eras`）已完成且不在翻譯範圍，不回頭改。
>
> **2026-08-29 更新（grill-me 第一輪修正）**：原設計是每個父表各開一張型別化 `_translations` companion 表（5 張），且把 `historical_event_perspectives` 也列進翻譯範圍。經討論釐清「翻譯」跟「史觀/史料傳統差異」是兩個獨立的軸——立場性敘事（`historical_event_perspectives`、`historical_event_controversies.viewpoints`）不該被翻譯抹平，應該靠既有多重視角機制（`observer_categories` 擴充「中文史料傳統」/「英文史料傳統」等類別）各自用原語言寫，翻譯只處理中立事實內容。範圍縮小為 4 張表的中立欄位（`regimes.self_name`、`historical_events.name`、`lineage_presets`、`historical_event_controversies.topic`/`neutral_description`）。2.12（`historical_event_perspectives`）改回不依賴 2.16，因為整張表都不進翻譯範圍。
>
> **2026-08-29 更新（grill-me 第二輪修正）**：第一輪同時把翻譯表從「5 張型別化表」改成「1 張通用表」（`content_translations`，`entity_type`/`entity_id`/`field_name`/`locale`），已建置並套用過。但重新檢視這個專案的實際目標——不是單人自用小工具，是要給其他使用者用、資料量會持續成長——通用表放棄外鍵完整性（父列刪除時翻譯列不會自動級聯刪除）這個取捨不成立，**改回 5 張型別化表**（`regime_translations`／`regime_alias_translations`／`historical_event_translations`／`lineage_preset_translations`／`historical_event_controversy_translations`，各自真外鍵 + `ON DELETE CASCADE`），並把先前補回的 `regime_aliases` 一併納入。詳見 PRD §6「多語言內容設計」修訂記錄。

### 任務清單

| 狀態 | # | 任務 | 產出 | 對應 PRD | Commit 建議 |
|---|---|---|---|---|---|
| [x] | 2.0 | 統一回應格式與錯誤格式拍板 | **已拍板（2026-08-28）**：包裝格式 `{ statusCode, message, data }`，沿用 sanring 慣例，不用 ASP.NET `ProblemDetails`；具體契約形狀已寫入 §7。實作方式（共用 `ApiResponse<T>` + 全域 exception handler/result filter）留給第一個真正動工的端點決定，本任務只定案契約形狀 | §7、§12 TODO | 1 個（純文件決策，無程式碼） |
| [x] | 2.1 | 後端政權狀態機合法轉換驗證器（C#，唯一信任來源） | `RegimeTransitionValidator` 服務，依憲法 §4 規則表判斷「存續→分裂／存續→被取代禪讓／存續→被滅亡」是否合法。**已完成（2026-08-29）**：`api/Domain/RegimeStatus.cs`（enum + 字串代碼轉換）+ `api/Domain/RegimeTransitionValidator.cs`（`IRegimeTransitionValidator`，涵蓋 status 轉換合法性 + predecessor/origin_transition_type 一致性），已註冊進 DI（`Program.cs`）。14 組案例手動驗證全過（合法轉換、終止狀態不可逆、未知代碼、起源連結一致性），正式單元測試留給 2.15 建測試專案時補上 | §5 XState 驗證分工 | 1 個 |
| [x] | 2.2 | EDTF 套件整合 | 選定 .NET 生態的 EDTF 套件（若無成熟套件，見下方停止條件），封裝一個 `EdtfService`：格式驗證 + 換算 `start_decimal`/`end_decimal`（含閏年天數正確處理）。**已完成（2026-08-29）**：觸發停止條件——`EDTF`（nharren）2015 年後未更新且只 target net45，`MoreDateTime` 的 EDTF 功能剛加不久、作者自承未完整覆蓋規格、強制依賴 `Nager.Date`——兩者都不合格。改採「自訂語法解析＋`NodaTime` 曆法引擎」混合方案：`api/Domain/EdtfService.cs` 解析 `?`/`~`/負年份/年-月-日子集，`api/Domain/EdtfDate.cs` 的 `ToDecimalYear()` 用 `NodaTime.CalendarSystem.Iso` 算閏年與 day-of-year（官方支援西元前 9998~西元 9999 年，絕對紀年慣例跟 EDTF 一致不用轉換）。15 組案例手動驗證全過（含 1900/2000/2024 閏年邊界、BCE、非法月份/日期、空字串），正式單元測試留給 2.15 | §5 EDTF 拍板 | 1 個 |
| [x] | 2.3 | `reign_eras` 查詢端點 | `GET /api/v1/reign-eras?year={y}`（依年份查年號）、`GET /api/v1/regimes/:id/reign-eras`（依政權查所有年號）。**已完成（2026-08-29）**：這是第一個真正動工的端點，順帶把 task 2.0 拍板的回應包裝格式落地成共用基礎建設——`api/Contracts/ApiResponse.cs`（`{statusCode,message,data}`）、`api/Infrastructure/ApiExceptionHandler.cs`（未捕捉例外也走同一包裝）、`Program.cs` 的 `ApiBehaviorOptions.InvalidModelStateResponseFactory`（`[ApiController]` 自動 400 也走同一包裝），後續所有端點直接沿用不用重做。`year` 缺漏回 400、政權不存在回 404、半開區間 `[start_year,end_year)` 語意跟 `regime_territories` 一致。已用真正的 `app_postgres`（已灌好的 seed 資料）跑過 curl 驗證：year=225 正確查到 3 個跨政權年號、缺 year 正確 400、不存在的政權 id 正確 404，OpenAPI 文件也正確收錄兩個路徑。**已知限制**：`{regimeId:guid}` 路由約束若比對失敗（例如網址帶非 GUID 字串）會落到 ASP.NET 預設的 404，不會走 `ApiResponse` 包裝——之後端點若都用同一種 `:guid` 路由約束，這個不一致會一直存在，先記下來不擋這個任務。**⚠️ 事後補充（2026-08-29，同一天）**：`message` 欄位語意重新拍板——從「人類可讀中文句子」改成「穩定代碼（`api/Contracts/ApiMessageCodes.cs`），前端自己查翻譯字典」，因為原本的中文句子沒辦法讓前端穩定分辨錯誤原因、也做不了多語系。已回頭改掉 2.3 剛寫好的程式碼（`YearRequired`→`YEAR_REQUIRED`、`RegimeNotFound`→`REGIME_NOT_FOUND` 等），重新跑過 curl 驗證三個案例都正確回代碼，詳見 PRD §7 | §5 紀年轉換 | 1 個 |
| [x] | 2.4 | 政權查詢端點（唯讀） | `GET /api/v1/regimes`（支援 `?year=`/`?period=` 過濾）、`GET /api/v1/regimes/:id`。**依賴 2.16**：`self_name` 在翻譯範圍內，查詢要支援 `?locale=`（省略時回原始語言，`regime_translations` 有對應列時回翻譯內容，見 PRD §6「多語言內容設計」）。**已完成（2026-08-29）**：`api/Controllers/RegimesController.cs`。`?year=` 濾條件重用跟 2.6 疆域端點同一套「當年有效（未被 I5 取代）疆域快照」判斷，語意一致；省略 `year` 回全部政權（前端建 id→名稱對照表不用管目前顯示哪個年份，見任務 3.5b）。**`?period=` 沒有實作**——契約表只寫了名字沒定義形狀（兩個 int？字串範圍？），沒有具體規格可以照做，不猜測實作，留待真的有需求時再拍板。**刻意不含代稱清單**：PRD §7 契約表原本寫「含自稱名稱、狀態、代稱清單」，但代稱 `alias_type` 受控值是 2.9a 的未解開放問題，不提前碰。已用真實種子資料驗證：無 `locale` 回中文原文、`?locale=en` 正確回英文翻譯、`?year=225` 正確篩出魏/蜀漢/吳（跟 2.6 疆域端點同一批）、不存在的 id 回 404，OpenAPI 正確收錄兩個路徑 | §7 | 1 個 |
| [ ] | 2.5 | 政權寫入端點 | `POST /api/v1/regimes`（I2 校驗自稱名稱必填）、`PATCH /api/v1/regimes/:id`（呼叫 2.1 驗證器擋非法轉換）。**2.1 的 `RegimeTransitionValidator` 是純函式、不查 DB**，這裡要另外補兩條跨政權的 referential 檢查：(1) `predecessor_regime_id` 引用的政權必須存在、且狀態要能合理支撐這次轉換（例如不能引用一個已經 `conquered` 的政權當前身）；(2) 「分裂」轉換依憲法 §4 範例是一分多個，若同一個 `predecessor_regime_id`＋`origin_transition_type='split'` 底下只掛了 1 個子政權，是否要擋下來（≥2 個）——這條 §4 沒有逐字講死上限/下限，需要時回報討論，不要自行腦補 | §7 | 1 個 |
| [x] | 2.6 | 疆域查詢端點（唯讀） | `GET /api/v1/regimes/:id/territories`、`GET /api/v1/territories?year={y}`（R2/Story 1 核心查詢）。**已完成（2026-08-29，提前於 2.4 前完成）**：`api/Controllers/TerritoriesController.cs`，回傳標準 GeoJSON `FeatureCollection`（`NetTopologySuite.IO.GeoJSON4STJ` 套件掛 `GeoJsonConverterFactory` 到 `Program.cs` 的 JSON 選項，`MultiPolygon` 自動序列化成標準 geometry），前端 MapLibre 可以直接當 geojson source 用不用轉換。**不依賴 2.16**（疆域形狀沒有語言問題，不像 2.4 的政權名稱需要 `?locale=`），所以能先於 2.4 動工——回應地圖要先看到東西的實際需求。`year` 查詢用 `NpgsqlRange<int>.Contains()`，已實測會正確轉譯成 SQL `@>` range 運算子。只回「目前有效」的快照：排除 `SupersededBy` 非 null 的舊版本（I5 修正鏈），但保留 `IsDisputed=true` 的並存史觀版本（I3，不是新舊關係）。已用真正的 `app_postgres` 種子資料 curl 驗證：year=225 正確回 3 筆（魏/蜀漢/吳，排除已終止的漢跟未建立的晉）、year=210 正確回 4 筆（含 2 筆並存的蜀漢爭議版本 + 1 筆吳）、year=100 正確只回 1 筆漢（I5 修正版，原始版正確被排除）、缺 year 回 400、不存在的政權 id 回 404，OpenAPI 文件正確收錄兩個路徑。**附帶修正一個環境問題**：本機 `curl localhost:5000` 撞到 macOS AirPlay 接收器服務（回應 `Server: AirTunes`，佔用該 port），跟使用者確認後把 `docker-compose.yml` 的後端對外 port 從 5000 改成 5050，連帶更新 README/docs/api.md/docs/development.md | §7 | 1 個 |
| [ ] | 2.7 | 疆域寫入 + 修正端點 | `POST /api/v1/regimes/:id/territories`（I1 校驗時間區間必填）、`PATCH /api/v1/territories/:id/correct`（I5 版本鏈：新增新版本、`superseded_by` 指回、不覆蓋刪除原記錄） | §7 | 1 個（修正邏輯較複雜，獨立驗證） |
| [x] | 2.8 | 史觀主線 preset 查詢端點 | `GET /api/v1/lineage-presets`、`GET /api/v1/lineage-presets/:id/regimes`。**依賴 2.16**：`preset_name`/`description` 在翻譯範圍內，同 2.4 支援 `?locale=`。**已完成（2026-08-30，為了 Story 4/task 3.9 補上的缺口）**：`api/Controllers/LineagePresetsController.cs`。**動工前發現並解決一個 schema 缺口**：PRD Story 4 AC#3 要求「使用者未指定特定史觀時，依 `lineage_presets` 中的預設 preset 顯示主線」，但 `lineage_presets` 表完全沒有欄位可以回答「哪一個是預設」——不是靠插入順序或名稱字串猜（那樣之後新增/調整 preset 順序會意外改變預設值，是隱性行為，違反這個專案一貫「不讓資料的巧合順序承載真正商業語意」的原則），新增 `LineagePreset.IsDefault`（migration `AddLineagePresetIsDefault`，純新增欄位不影響既有資料）明確標記；種子資料把「傳統教科書史觀」標成 `IsDefault=true`，「蜀漢正統論史觀」維持預設值 `false`。應用層目前不強制「最多一筆為 true」——task 2.8 範圍只有唯讀端點，沒有寫入端點，不會有人透過 API 改出兩個預設，等真的有寫入端點時再補這條約束。`GET /lineage-presets/:id/regimes` 的政權欄位刻意跟既有 `RegimeResponse` 同一組（`selfName`/`status`/`predecessorRegimeId`/`originTransitionType`/`destroyedByRegimeId`），不重新設計一套——這是 task 3.9 畫「主線上相鄰兩個政權之間是禪讓還是滅亡」需要的同一批資料。已用真實容器 curl 驗證：`GET /lineage-presets` 正確回兩筆、`isDefault` 只有「傳統教科書史觀」是 `true`、`?locale=en` 正確翻譯兩個 preset 名稱；`GET /lineage-presets/:id/regimes` 正確回漢→魏→晉三筆、`sortOrder` 1/2/3、`status`/`predecessorRegimeId`/`originTransitionType` 都對；不存在的 preset id 回 404 `LINEAGE_PRESET_NOT_FOUND`。沒有另外寫 xUnit 測試，延續既有慣例 | §7 | 1 個 |
| [x] | 2.9 | 政權持續性關係 CRUD | `GET /api/v1/regimes/:id/relations?year={y}`、`POST /api/v1/regimes/:id/relations` | §7 | 1 個 |

> **2026-08-30 完成**：`api/Controllers/RegimeRelationsController.cs`。**沒有 `?locale=`**：
> `relation_type`/`description` 是 PRD §6 明確列在「次要/輔助內容，維持待評估、不現在
> 處理」的翻譯範圍外，這是 PRD 已經先拍板過的決定，不用這個任務重新決定（跟 2.10 的
> `sections` 是「動工前才決定」不同）。**`year` 必填**：跟 territories/events 同一個
> 慣例（查詢時間點是必填，不是選填的列表過濾條件），缺 `year` 回 400
> `YEAR_REQUIRED`。**關係表本身對稱**（`regime_a_id`/`regime_b_id` 沒有主從之分），
> `GET /regimes/:id/relations` 回傳這個政權出現在任一端的所有關係列。**POST 請求
> body 刻意不重複 `regimeAId`**：路由裡的 `{regimeId}` 就是關係的一端，body 只需要
> `otherRegimeId` 指定另一端是誰，避免路由參數跟 body 兩個等效欄位不一致時該聽誰的
> 這種歧義。**新增三個額外驗證**（PRD 沒有逐字講，但屬於基本資料完整性，不需要另外
> 拍板，跟 2.10「結束不能早於開始」同一個處理原則）：`otherRegimeId` 不能等於路由的
> `regimeId`（不能跟自己有關係，400 `RELATION_SAME_REGIME`）、`otherRegimeId` 必須是
> 存在的政權（400 `RELATION_OTHER_REGIME_NOT_FOUND`，跟「路由的 `regimeId` 本身不存在」
> 刻意分開成 404 `REGIME_NOT_FOUND`——一個是找不到 URL 指的資源，一個是 body 裡引用的
> 資源不存在，語意不同）、`endYear` 必須晚於 `startYear`（半開區間 `[start,end)` 要真的
> 圈出至少一年，400 `RELATION_END_BEFORE_START`）。**沒有「取得單一關係」的端點**（計畫
> 範圍只有列表查詢+新增），`POST` 成功後的 `Location` header 指回這個政權的關係列表
> （集合本身），不是指向一個不存在的單筆資源端點。已用真實容器 curl 驗證：GET 依年份
> 查詢（含孫劉聯盟 208-219 年在範圍內/225 年已跳出範圍兩種案例）、GET 缺 `year`（400）、
> GET 路由政權不存在（404）、POST 缺 `X-API-Key`（401）、POST 自己跟自己建關係（400）、
> POST 引用不存在的 `otherRegimeId`（400）、POST 結束不晚於開始（400）、POST 路由政權
> 不存在（404）、POST 成功（201）——九種案例全數驗證通過，測試資料事後從
> `app_postgres` 手動刪除。沒有另外寫 xUnit 測試，延續既有慣例。
| [x] | 2.9a | 政權代稱（Alias）CRUD | 先拍板 `alias_type` 受控值（若提不出比 observer relationship 更清楚的語意就直接移除該欄位，§12 TODO）；`GET /api/v1/regimes/:id/aliases`、`POST /api/v1/regimes/:id/aliases`（I4 校驗 `regime_id` FK 必存在）。**依賴 2.16**（2026-08-29 修正納入）：`alias_name` 在翻譯範圍內，同 2.4 支援 `?locale=` | §6、§7、§12 TODO | 1 個 |

> **2026-08-30 完成**（Story 3 的後端前置任務——5 個 Story 裡當時只剩 Story 3 卡在這個
> 決策沒動，使用者確認優先做完讓 Story 3 通）：
>
> **`alias_type` 受控值決策**：不是憑空發明分類，動工前先看種子資料既有的兩筆代稱
> （`weiAlias`「賊」／`wuAlias`「孫吳」），發現兩者的「他稱理由」本質不同——政治敵意
> vs. 史學消歧義——`observer_regime_id`（只回答「誰給的稱呼」，可為 null）回答不了
> 「為什麼這樣稱呼」，確認語意站得住腳，拍板保留欄位。定 4 個值（`political`／
> `scholarly`／`transliteration`／`geographic`，理由與例子見 `api/Domain/
> RegimeAliasType.cs` 的類別文件），純字串常數＋`HashSet` 驗證，不做成真正的 enum
> （跟 `RegimeStatus` 不同——這裡沒有狀態機/合法轉換規則要驗證，只是描述性分類，不用
> 那麼重的機制）。種子資料回填：`weiAlias`＝`political`、`wuAlias`＝`scholarly`。
>
> **端點**：`api/Controllers/RegimeAliasesController.cs`，跟 `RegimeRelationsController`
> 同一套「路由參數是主體，body 不重複填」慣例。POST 額外驗證：`observerRegimeId`（若
> 有指定）必須是存在的政權（400 `OBSERVER_REGIME_NOT_FOUND`）、`aliasType`（若有指定）
> 必須是四個受控值之一（400 `INVALID_ALIAS_TYPE`）。沒有「取得單一代稱」端點，跟 2.9
> 同一個範圍決定。已用真實容器 curl 驗證：GET 魏的代稱正確回「賊」/political、GET 吳
> 的代稱正確回「孫吳」/scholarly、`?locale=en` 正確回英文翻譯（"Sun Wu"）、GET 漢的
> 代稱正確回空陣列（漢沒有他稱記錄）、GET 不存在的政權 id 回 404、POST 缺 API Key
> 回 401、POST 不存在的 regimeId 回 404、POST `observerRegimeId` 不存在回 400、POST
> `aliasType` 不是受控值回 400、POST 成功回 201（測試資料事後從 `app_postgres` 手動
> 刪除，不留在種子資料裡），OpenAPI 正確收錄 GET/POST 兩個 method。沒有另外寫 xUnit
> 測試，延續既有慣例
| [ ] | 2.9b | 地名雙軌查詢端點 | `GET /api/v1/place-names?year={y}`（依年份查當時使用中的地名，`valid_period` 區間匹配）、`GET /api/v1/place-names/:id`；回傳含 `historical_name`/`modern_name`（可為 NULL）雙欄位，不做寫入端點（seed 已覆蓋首都示範，正式匯入前的來源治理見 `docs/data-governance.md`） | 憲法 §6、§7 | 1 個 |
| [x] | 2.10 | 事件骨幹 CRUD | `GET /api/v1/events?year={y}`、`GET /api/v1/events/:id`、`POST /api/v1/events`（寫入時呼叫 2.2 EdtfService，含 `parent_event_id` 組成關係）。**2.2 的 `EdtfService.TryParse` 只驗證單一字串合法性，不驗證跨欄位邏輯**——這裡要另外補一條檢查：換算出的 `end_decimal` 不可早於 `start_decimal`（避免使用者填反開始/結束時間），憲法/PRD 沒有明講這條但屬於基本資料完整性，不需要另外拍板。**依賴 2.16**：`name` 在翻譯範圍內，同 2.4 支援 `?locale=`；`sections` JSONB 要不要連帶翻譯尚未拍板，見 PRD §6，這裡動工前要先決定。**已完成（2026-08-30）**：`api/Controllers/EventsController.cs`。**動工前先解決的開放問題**：`sections` 要不要連帶翻譯——決定**先不擴充**，`historical_event_translations` 目前只有 `Name` 欄位，`?locale=` 只影響 `name`，`sections` 一律回資料庫原始內容；這不是隨便繞過問題，是這個問題裡範圍最小、不用新增 schema 就能回答的那部分（要不要新增 `sections` 翻譯欄位是更大的內容設計問題，留給真的要擴充翻譯範圍時再決定）。**`GET /events?year=`的查詢語意**：事件用 decimal 精度年份，「查某一年」定義成查詢區間跟該整年 `[year, year+1)` 有重疊（`start_decimal < year+1 AND end_decimal >= year`）——跟 territories/reign_eras 用 INT4RANGE 半開區間同一個語意的 decimal 版本，已用邊界案例驗證（year=219 不含 208/220 年的事件，year=220 剛好含 220 年那筆）。**路由刻意不用 `{id:guid}`**：`historical_events.id` 是手動指定的字串 slug（例："event-chibi-208"），不是 GUID，跟 `RegimesController` 不是同一種資源識別碼型別。**`sections` 的序列化**：資料庫存 jsonb 原始文字（`HistoricalEvent.Sections` 是 `string?`），回應時解析回真正的巢狀 `JsonElement`，不是把整個 JSON 字串再包一層字串（不然前端要多做一次 `JSON.parse()`，等於把「jsonb 存成字串」這個後端實作細節洩漏出去），已用真實種子資料的赤壁之戰 `sections` 驗證回應是巢狀物件不是雙重編碼字串。**POST 請求 body 刻意排除的範圍**（`CreateHistoricalEventRequest` 類別註解有記錄）：`origin_point`/`influence_area`/`routes` 這三個地理欄位刻意先只做唯讀（現有種子資料完全沒填過，也還沒有前端消費端可以驗證寫入格式對不對）；`tag_ids` 不在這裡，2.11 的計畫敘述明確寫是要回頭擴充這個端點的 request body，不是 2.10 自己的範圍。**新增這個 API 第一個真正落地的 POST 端點**，順帶定案 `ApiMessageCodes.CreateSuccess`（`CREATE_SUCCESS`）——沿用 task 2.0 的命名慣例（成功代碼對應 HTTP 動詞語意）第一次真正套用到 POST。**發現並修正一個小落差**：`historical_events.start_decimal`/`end_decimal` 是 `numeric(8,3)`，`POST` 當下組回應物件用的是 `EdtfDate.ToDecimalYear()` 算出來的完整精度小數，但 `SaveChangesAsync()` 之後資料庫實際存的是四捨五入到 3 位小數的版本——用真實容器測了一次「POST 回應 vs 緊接著 GET 回應」發現兩個數字對不起來（`208.74863387978142076502732240` vs `208.749`），修正成寫入前先 `Math.Round(x, 3)` 對齊，重測後兩者一致。已用真實容器 curl 驗證：GET 依年份查詢（含邊界案例）、GET 單筆（含 404）、`?locale=en` 正確回英文翻譯（赤壁之戰→"Battle of Red Cliffs"）、POST 缺 `X-API-Key`（401，掛在 task 2.14 middleware 底下）、POST 錯誤 EDTF（400 `INVALID_EDTF`）、POST 結束早於開始（400 `EVENT_END_BEFORE_START`）、POST 引用不存在的 `parentEventId`（400 `PARENT_EVENT_NOT_FOUND`）、POST 成功（201，含 `sections`/`parentEventId`）、POST 重複 `id`（409 `EVENT_ID_ALREADY_EXISTS`）——九種案例全數驗證通過，測試用的事件事後從 `app_postgres` 手動刪除，不留在種子資料裡。沒有另外寫 xUnit 測試，延續這個專案從 2.0 開始的既有慣例（curl 真實容器驗證，自動化測試留給 2.15 統一補） | §7 | 1 個 |
| [ ] | 2.11 | 事件類型標籤 | `GET /api/v1/event-tags`（列出可用標籤）、事件寫入端點（2.10）支援帶 `tag_ids` 陣列建立 `historical_event_tag_map` | §6 事件三維度 | 1 個 |
| [ ] | 2.12 | 觀察者類別 + 多重視角敘事 | **寫入端點實作前先定義 `primary_sources`/`claimed_casualties` 的 JSON schema 與最小 citation 欄位（§12 TODO）**；`GET /api/v1/observer-categories`、`GET /api/v1/events/:id/perspectives`、`POST .../perspectives`（應用層驗證 `regime_id`/`observer_category_id` 至少擇一非 NULL）。**不依賴 2.16**：`historical_event_perspectives` 整張表不進翻譯範圍（立場性敘事，靠多重視角機制各自用原語言寫，見 PRD §6）；`observer_categories` 未來可擴充「中文史料傳統」等類別，本任務不用先做，等實際需要時再插入 | §6、Story 3、§12 TODO | 1 個 |
| [ ] | 2.13 | 事件爭議點 | **寫入端點實作前先定義 `viewpoints` 的 JSON schema 與最小 citation 欄位（§12 TODO，可與 2.12 併案決定）**；`GET /api/v1/events/:id/controversies`、`POST .../controversies`。**依賴 2.16**：僅 `topic`/`neutral_description` 在翻譯範圍內（中立敘述），`viewpoints`（誰主張什麼）不翻譯，同 2.4 支援 `?locale=` | §6 notes §十.2、§12 TODO | 1 個 |
| [x] | 2.16 | 雙語內容 schema（憲法 R4） | **最終定案（2026-08-29 grill-me 第二輪）**：5 張型別化 `_translations` companion 表（`regime_translations`／`regime_alias_translations`／`historical_event_translations`／`lineage_preset_translations`／`historical_event_controversy_translations`），各自真外鍵 + `ON DELETE CASCADE`，見 PRD §6「多語言內容設計」。範圍限中立事實內容——`historical_event_perspectives`、`viewpoints` 不進範圍。`historical_events.sections` JSONB 要不要連帶翻譯要先拍板再動工。**已完成**：5 個 Entity + 5 個 Configuration，migration `ReplaceContentTranslationsWithTypedTables`（先移除第一輪的通用表 `content_translations`，再建 5 張新表，均純 schema 變動不影響其他既有表）。已在拋棄式容器驗證：seed 資料正確寫入 5 張表、實際執行刪除測試確認級聯刪除正常運作（刪一筆 `regimes` 資料，對應 `regime_translations` 列自動消失，不需要應用層清）；已套用到 `app_postgres` 並複查一致 | §6、憲法 R4 | 1 個 |
| [x] | 2.17 | 既有 seed 資料英文翻譯內容 | 幫 2.16 的翻譯範圍（漢/魏/蜀漢/吳/晉自稱名稱、既有 2 筆 `regime_aliases`、赤壁/漢禪魏/魏禪晉事件名稱、兩個 lineage preset 名稱/說明、曹操兵力爭議的 topic/neutral_description）補上英文內容。**這是內容撰寫工作，不是純工程工作**——翻譯品質需要人工核對，不是機械轉換；可以分批進行，不需要一次補齊全部才能讓 schema/API 上線（沒有翻譯的內容 fallback 回中文，見 PRD §6）。**已完成（2026-08-29）**：20 筆翻譯資料分散在 5 張型別化表裡，涵蓋 5 個政權自稱、2 筆他稱、5 個事件名稱、2 個 lineage preset 名稱+說明、2 筆爭議點 topic+neutral_description。已在拋棄式容器驗證全部正確 join 回對應中文列；已套用到 `app_postgres`（truncate + `docker compose up -d --build backend`）並複查一致 | §6、憲法 R4 | 依內容量拆多個 commit |
| [x] | 2.14 | 最小 Auth middleware | **已拍板（2026-08-26）**：`.env` 存單一固定 `API_WRITE_KEY`，middleware 檢查所有 POST/PATCH request header（例：`X-API-Key`）是否相符，不符回 401；GET 端點不掛此 middleware。**已完成（2026-08-30，M2 後端下一輪的第一個任務，優先於 2.9/2.10 等寫入端點——先把守門機制建好，之後每個新端點生下來就有保護，不用事後回頭補）**：`api/Infrastructure/ApiWriteKeyMiddleware.cs`，比對 `X-API-Key` header 跟環境變數 `API_WRITE_KEY`，用 `CryptographicOperations.FixedTimeEquals`（固定時間比較，避免 timing attack 側錄字元——單人自用階段風險很低，但幾乎零成本，沒理由不做對）。**只擋 POST/PATCH**（`HttpMethods.Post`/`HttpMethods.Patch`），GET 完全不掛這層檢查；**`API_WRITE_KEY` 環境變數本身沒設定時回 500（`INTERNAL_ERROR`）而不是靜默放行**——避免部署忘記設定這個變數時，寫入端點意外變成完全公開。新增 `ApiMessageCodes.Unauthorized`（`UNAUTHORIZED`），跟現有的 `ApiResponse.Error()` 包裝格式一致。`.env`／`.env.example` 補上 `API_WRITE_KEY`（`.env.example` 原本已有註解掉的 placeholder，這次拍板實作、取消註解並更新說明；`docs/api.md`、`README.md` 同步更新）；`docker-compose.yml` 不用額外改——backend 服務本來就有 `env_file: .env`，新變數自動注入容器，不需要另外列進 `environment:` 區塊。**驗證方式跟既有慣例（curl 真實容器）一致，但這個任務比較特殊**：因為 2.5/2.7/2.9 等真正的寫入端點都還沒做，沒有真實 POST/PATCH 業務端點可以測——利用「middleware 註冊在 `MapControllers()` 之前、對任何 request path 都生效（不管路由存不存在）」這個管線順序特性，直接對任意 `/api/v1/...` 路徑送 POST/PATCH 驗證四種狀況：GET 不受影響（200，照舊）、POST 缺 key（401 `UNAUTHORIZED`）、POST 錯誤 key（401）、POST 正確 key（通過 middleware，落到路由層，因為 `RegimesController` 目前只有 GET action，正確回 405 Method Not Allowed——這個 405 本身就是「middleware 已放行、問題出在下一層路由」的證據）、PATCH 缺 key（401，確認 PATCH 也有被擋）。`dotnet build` 過，`docker compose up -d --build backend` 部署後五種案例 curl 全部驗證通過。**沒有另外寫 xUnit 測試**：`api/` repository 目前完全沒有測試專案，這個專案從 2.0 開始的既有慣例是「curl 真實容器驗證，自動化測試留給 2.15 統一補」，這個任務延續同一個慣例，不提前偏離 | §5 Auth 拍板 | 1 個 |
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
>
> **2026-08-29 更新**：M2 task 2.0 修訂 `ApiResponse.message` 語意（改成穩定代碼，非中文句子）後，發現原本的任務清單沒有對應的前端消費端——新增 3.14a，把「代碼→顯示文字」的對照集中管理，避免各元件各自寫死判斷式。多語系本身不是已拍板的產品目標（憲法未提及），這裡先只求「集中管理」，不是先做語言切換功能。

> **2026-08-29 完成 3.0**：`npx @sanring/cli init`（componentPath 用預設 `src/app/components/ui`）+ `add button` 驗證完成；Tailwind v4 用官方 PostCSS 外掛安裝（`tailwindcss`、`@tailwindcss/postcss`、`postcss`，新增 `app/.postcssrc.json`），`styles.scss` 用 `@import 'tailwindcss';`（Sass 對這行的 deprecation warning 是已知/預期噪音——這是 Tailwind v4 官方文件對 Angular 專案的建法，實測編譯後的 CSS 有完整展開的 utility class，不是留一行沒被解析的裸 import）。**`src/sanring-theme.css` 語意層已全部 alias 到 `design-tokens.scss` 的 `--wl-*`**（background/foreground/muted/border/border-strong/surface/control/primary/圓角/字型），不是併存兩套色盤；同時移除了原檔案的 `[data-theme='light']` 深色/淺色雙軌設計（Sanring 預設 :root 是深色，跟本專案「❌ 不做深色模式」的既定範圍衝突且我們不會去設那個屬性），改成單一淺色語意層。已用 `ng build`（Tailwind utility class 有展開、無編譯錯誤）、`ng test`（12/12 過，新增一條驗證 `sanringBtn` directive 有掛上的測試）、`ng serve` 後直接讀取編譯後的 CSS（`focus-visible:ring-[var(--sanring-border-strong)]`、`hover:bg-[var(--sanring-active)]` 等規則都正確產生並指到重新 alias 過的 `--sanring-*`/`--wl-*` 變數）三種方式驗證；因為這次對話環境沒有連上 Chrome 擴充功能，沒有做到瀏覽器截圖層級的目視驗證（顏色/hover 的實際渲染結果建議之後找機會用瀏覽器實際看一次）。
>
> **2026-08-29 追加**：原本刻意留下的缺口（Sanring 原廠品牌色階 `--sanring-primary-10..90`/`coral/sun/info/success/warn/error` 未對齊 `--wl-*`）當天追加拍板全面收斂——不保留任何 Sanring 原廠色碼。primary/neutral/coral 從 `--wl-primary-*`/`--wl-gray-*`/`--wl-secondary-*` 十階以 OKLCH 明度重新取樣；success/warn/error 是全新色相（錨點 `--wl-status-good/-warning/-critical`），用「錨點色度佔該明度 sRGB 色域邊界比例」等比縮放算出其餘 8 階；sun/info 直接 `var()` 參照 warn/primary，不複製色碼。**過程中發現並修正一個方法論錯誤**：第一版沿用 design-tokens.scss 產生次色橙時「借主色藍的色度曲線形狀縮放」的手法，套到 success/warn/error 這幾個色相跟藍色色域邊界形狀差很多的情況時，色相在深色階被 RGB 裁切裁到嚴重漂移（warn 從錨點 H=78.5° 漂到 H=33° 附近，將近 50 度），改成「色域邊界比例縮放」（每一階都用自己明度下的 sRGB 色域邊界當基準，不借用藍色的絕對色度數字）後，三個色相家族最大偏差都 <1.2°。換算過程與方法比較見 `app/scripts/gen-sanring-theme-ramps.mjs`。全域樣式改用 `@use` 載入 `sanring-theme.css`（原本用 `@import` 會在編譯結果多一個無意義的分號，`@use` 沒有這個問題）。已重新 `ng build`/`ng test`（12/12）驗證。

> **2026-08-29 完成 3.2**：`app/src/app/map/`（`MapComponent`，用 `afterNextRender` 在瀏覽器端初始化，signal-based `viewChild.required`）。**底圖決策：不接外部瓦片服務**，MapLibre style 只有一個 `background` 圖層，背景色即時讀取 `--wl-page` 的 computed 值（不寫死色碼，避免跟 design-tokens.scss 兩處維護不同步）。理由記在 `map.ts` 開頭註解：疆域資料本來就是自己從 OHM 取 GeoJSON、不依賴第三方瓦片服務這個方向已經定案；歷史地圖疊在現代底圖（現代國界/地名）上有時代錯置問題；零外部依賴/零 API key/流量限制風險，符合目前單人自用階段。之後真的需要海岸線等物理地理參考時，疊一層公眾領域的靜態海岸線 GeoJSON 即可，不必為此換成瓦片服務。`maplibre-gl` 6.x 沒有 default export，用具名匯入 `Map as MapLibreMap`（避開跟內建 `Map` 撞名）。**測試**：`maplibre-gl` 需要真的 WebGL，JSDOM 測試環境沒有，spec 用 `vi.mock` + `vi.hoisted()`（避開 `vi.mock` 提升到檔案最頂端導致的 TDZ 問題）換成假的 `Map`/`NavigationControl`，只驗證我們自己的 wiring（容器元素、style 內容、`addControl`、`ngOnDestroy` 呼叫 `remove()`），不重測 MapLibre 本身。**production bundle 預算**：MapLibre GL JS 本身就有一定重量（gzip 後約 260KB），原本 Angular CLI scaffold 的預設值（500kB warning / 1MB error）是給空殼機案設的，不是這個專案刻意選的門檻，已調高為 1.5MB/2.5MB。已用 `ng build`（含新預算）、`ng test`（16/16）、實際重建 `docker compose up -d --build frontend` 容器並用 curl 驗證正確 bundle 有部署上去三種方式驗證；同樣因為沒連上 Chrome 擴充功能，沒做到瀏覽器截圖層級的目視驗證。
>
> **2026-08-29 追加修正（`app/nginx.conf`）**：使用者重建容器後瀏覽器回報 `Failed to load module script: ... non-JavaScript MIME type of "text/html"`——根因是 `nginx.conf` 原本沒有設定任何 `Cache-Control`，瀏覽器快取了舊版 `index.html`（裡面 `<script>` 指到舊的雜湊檔名），改版後舊檔名在新映像檔裡已經不存在，SPA fallback（`try_files $uri $uri/ /index.html;`）對這個 `.js` 請求也回傳 `index.html` 本身（text/html），瀏覽器對 `<script type="module">` 做 MIME 檢查就報錯。這不是單次手動重新整理就能一勞永逸解決的問題——每次改版都會重演。修正：雜湊檔名的靜態資源（`.js`/`.css`/字型/圖片）設 `Cache-Control: public, max-age=31536000, immutable`（內容變檔名就變，放心長期快取）；`index.html` 本身設 `Cache-Control: no-cache, no-store, must-revalidate`（每次都要跟伺服器確認）；同時把 SPA fallback 限定在非靜態資源路徑，靜態資源請求不到直接回 404（已用 curl 驗證：請求不存在的雜湊檔名回 404，不再誤回 index.html）。
>
> **2026-08-29 再追加修正（同一天，使用者重新整理後回報第二個相關錯誤）**：上面的修正解決了 index.html 快取問題，但緊接著冒出同類型的新錯誤，指向不同檔案——`maplibre-gl-worker.mjs`。根因是**兩個獨立問題疊在一起**：(1) MapLibre GL 的 tile worker 是執行期用 `new Worker(url, {type: "module"})` 動態組出網址載入的，esbuild 沒辦法靜態分析追蹤到這個檔案，不會自動打包進 bundle，所以這個檔案原本根本沒有出現在 build output 裡——已在 `angular.json` 的 `assets` 加一筆，把 `node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs` 複製到 build output 根目錄。(2) 補上檔案後請求變成 200，但 `Content-Type` 是 `application/octet-stream`——nginx 內建 mime.types 沒有 `.mjs` 副檔名的對照，瀏覽器對 module worker 一樣做嚴格 MIME 檢查，型別不對照樣被拒絕；修正用 `location = /maplibre-gl-worker.mjs { default_type application/javascript; }`（曾經試過在 `types { include mime.types; ... }` 裡追加一筆想「沿用標準表+加一筆」，結果 `mime.types` 這個檔案本身就是用 `types { ... }` 包起來的一整個檔案，巢狀 include 直接讓 nginx 整個啟動失敗，容器一直重啟——已改用範圍限定在單一 location 的 `default_type` 寫法）。這個檔案是從 `node_modules` 原封不動複製、檔名不隨內容變動（不像 `main-XXXX.js` 那樣雜湊），所以套用 `no-cache, must-revalidate`（跟 `index.html` 同一個道理），不能套用雜湊檔名那條「放心快取一年」的規則，否則下次升級 maplibre-gl 版本，瀏覽器會一直吃到升級前的舊版 worker。已用 curl 驗證 `Content-Type: application/javascript`、`Cache-Control: no-cache, must-revalidate`，並確認這個修正沒有連帶破壞其他 JS/CSS/index.html 原本的 header。
>
> **2026-08-29 第三次追加修正（無痕視窗排除快取因素後，冒出同類但指向另一個檔案的錯誤）**：使用者照建議用無痕視窗測試，證實不是瀏覽器快取問題——是真的還有一個檔案沒處理：`maplibre-gl-shared.mjs`。根因：`maplibre-gl-worker.mjs`（上一輪已修好、正確複製進 build output 的那支）本身是真的 ES module 原始碼，內部用相對路徑 `import ... from "./maplibre-gl-shared.mjs"` 匯入一個 sibling chunk——瀏覽器載入 module worker 時會照這行 import 再發一次獨立的網路請求，不會因為 worker 主檔案修好了就沒事，兩支檔案都要存在且型別正確才行。已確認這是這條 import 鏈的最後一站（`maplibre-gl-shared.mjs` 本身沒有再 import 其他相對路徑檔案）。修正：(1) `angular.json` assets 再加一筆複製 `maplibre-gl-shared.mjs`；(2) 把 nginx.conf 原本「只認 `maplibre-gl-worker.mjs` 這一個確切檔名」的 location 改成正規表達式 `location ~* \.mjs$`，通用處理「任何 .mjs 檔案」而不是逐一列檔名——這類「函式庫自帶原始碼、不進打包流程」的裸檔案，之後升級 maplibre-gl 版本或引入其他有 worker 的函式庫都可能再出現同一種檔案，這次改成通用規則，不用每次多一個檔名就回來改一次設定檔。已用 curl 驗證兩支 `.mjs` 都回 200／`application/javascript`／`no-cache, must-revalidate`，且沒有影響雜湊資源與 index.html 原本的 header。
>
> **2026-08-29 使用者實機瀏覽器驗證完成**：三輪 nginx/asset 修正後，使用者在真實瀏覽器（含無痕視窗排除快取因素）確認 Console 已無任何模組載入錯誤，且直接互動驗證：`document.querySelector('.maplibregl-canvas')?.getBoundingClientRect()` 回傳 `width: 1800, height: 1236`（容器/畫布尺寸正常，不是塌陷成 0）；滑鼠在地圖區域按住拖曳，游標正確從一般箭頭變成抓取手勢（grab/grabbing），確認拖曳平移手勢有被地圖接收。畫面本身呈現空白／接近純白，是任務本身刻意選擇「不接底圖、單一中性背景色」的預期結果，不是 bug——之前誤用「羅盤圖示會不會轉」當互動驗證指標是錯的判斷方式（羅盤只在旋轉手勢時才會動，平移/縮放本來就不會讓它轉），已在對話中更正。至此任務 3.2 補上了先前只做到 curl/build 層級、缺的「瀏覽器實機目視+互動」驗證這一步，前面記錄的「沒連上 Chrome 擴充功能」缺口已補齊。

> **2026-08-29 完成 3.1**：`app/src/app/core/regime/`——`regime-status.enum.ts`（`RegimeStatus` 字串聯集型別 + `isLegalRegimeStatusTransition()`/`getLegalNextRegimeStatuses()` 兩個純函式，跟後端 `api/Domain/RegimeStatus.cs`/`RegimeStatusCodes.cs` 的代碼字面值完全對齊）、`regime-status.machine.ts`（XState 5 狀態圖，狀態直接是 active/split/succeeded/conquered 四個字面量，三個終止狀態標記 `type: 'final'`）。**兩份手寫表示刻意不共用程式碼**：狀態圖手寫成 XState 慣用的字面量結構（能直接餵給 XState 視覺化工具），純函式版本給不需要真的跑 actor 的地方（例如靜態渲染進度圖）用；跟後端「C#/TypeScript 沒辦法共用同一份 library，只能各自實作、以憲法 §4 為 SSOT」同一個處理原則，這裡在前端內部也刻意採用同一個「兩份獨立表示＋測試互相比對」的模式，不是自己找麻煩。**測試**：`regime-status.enum.spec.ts` 窮舉全部 4×4=16 組 (from, to) 配對（3 組合法、13 組不合法，含同狀態/逆轉/終止狀態互轉）；`regime-status.machine.spec.ts` 驗證機器初始狀態、三條合法轉換各自到達正確的終止狀態、終止狀態不接受任何後續事件，並逐一比對機器的實際轉換結果跟 `isLegalRegimeStatusTransition()` 是否一致（防止兩份手寫表示日後飄掉沒被發現）。**目前只有定義檔，還沒接進任何元件**——跟任務 3.5 的 `territory-adjacency.ts`/`graph-coloring.ts` 同一個模式，先把通用邏輯做好、測完，等 Story 4（任務 3.9：政權狀態轉換視覺呈現）真的要畫進度圖/狀態徽章時再接上去；`ng build` 已確認沒有元件匯入的情況下 esbuild 正確 tree-shake 掉，不會平白增加 bundle 大小。已用 `ng build`、`ng test`（53/53，新增 37 條）驗證。

### 任務清單

| 狀態 | # | 任務 | 產出 | 對應 PRD | Commit 建議 |
|---|---|---|---|---|---|
| [x] | 3.0 | 引入 Sanring UI + Tailwind CSS v4（`app/` 前端樣式基礎建設） | `npx @sanring/cli init` 設定完成、Tailwind v4 安裝並接上 `sanring-theme.css`、以 Button 元件驗證 hover/focus 樣式與 Angular standalone import 皆正常 | §5 UI 元件庫 | 1 個 |
| [x] | 3.1 | 前端 XState 政權狀態機定義（UI 層防呆，非信任來源） | 前端 state machine 定義檔 | §5 | 1 個 |
| [x] | 3.2 | MapLibre GL JS 整合 + 底圖 | 地圖能顯示、能平移縮放 | §5、§8 | 1 個 |
| [x] | 3.3 | 時間軸 Scrubber 主軸（世紀/年） | 可連續拖動元件，對應憲法 §9「非離散跳轉」 | §8 notes §六 | 1 個 |
| [ ] | 3.4 | 時間軸 Scrubber 副軸（月/日展開） | 聚焦近代事件時下方展開精細軸。**刻意不做**：用途是「聚焦近代事件時下方展開精細軸」，但事件資料（`historical_events`，task 2.10+）根本還沒做，沒有東西可以展開——不做無資料可展示的 UI，等事件端點做出來、真的有東西要展開時再回頭做 | §8 notes §六 | 1 個（依賴 3.3） |
| [x] | 3.5 | 政權疆域圖層渲染（基礎版，GeoJSON + MapLibre filter expressions） | 拖動時間拉桿時，依快照篩出當下應顯示的疆域（尚未做形變，見 3.6）。**部分完成（2026-08-29）**：資料管線已打通並實際渲染出真的疆域形狀（見下方說明），**尚未完成的是「拖動時間拉桿換年份」這件事本身**——因為時間拉桿（3.3/3.4）根本還沒做，目前是固定年份（225，寫死在 `MapComponent.TERRITORY_YEAR`），等 3.3/3.4 做完、真的有拉桿可以拖，再回頭把這裡改成拉桿即時觸發重新查詢/重新著色，才算完整達成本任務的驗收標準，不提前打勾。已完成的部分：`app/src/app/core/geometry/territory-styling.ts`（`assignTerritoryColorSlots()` 串接 `territory-adjacency.ts`＋`graph-coloring.ts`，把色格索引寫回 GeoJSON feature properties；`buildColorSlotMatchExpression()` 組出 MapLibre `fill-color` match expression）、`app/src/app/core/design/territory-colors.ts`（**政權識別色實際色碼清單已拍板**，見下方說明）、`MapComponent` 接上 `HttpClient` 打 `GET /api/v1/territories?year=...`，`map.on('load', ...)` 後渲染 `territories-fill`（依色格著色）+ `territories-border`（統一中性色）兩個圖層。**已修正一個先前記錄有誤的色盲安全性判斷**：先前記錄「因為這裡是真正算相鄰關係後才分配，只需要『相鄰配對』寬鬆標準，8 色都能過」——這個推論套用錯了 dataviz 技能的 `--pairs adjacent` 模式（那是給堆疊圖/折線圖「畫面上只有固定順序相鄰的顏色會真的貼在一起」的圖表用的，地圖是任意拓撲，不適用）。實測分類色第 3-8 格（6 色）跑 `--pairs all`（正確的嚴格標準）會 FAIL，拿掉 magenta 之後剩下 5 色（aqua/yellow/green/violet/red）全數過關，已改用這 5 色，詳見 `territory-colors.ts` 的驗證記錄。**已用真實瀏覽器＋容器驗證**：`docker compose up -d --build frontend backend`、curl 確認部署的 JS bundle 含新程式碼、API proxy 正常；`ng build`/`ng test`（59/59，含新增的 `territory-styling.spec.ts`＋改寫過的 `map.spec.ts`——過程中發現並修正一個測試假象：舊版 `FakeMap` mock 沒有 `on()` 方法，`initMap()` 呼叫 `.on('load', ...)` 時拋出的例外被 Angular 的 `afterNextRender` 機制吞掉、沒有讓測試失敗，導致先前的測試「綠燈但沒有真的驗證到」，已補上完整的 `on()`/`addSource()`/`addLayer()` mock 並用 `HttpTestingController` 驗證真正的請求/渲染流程）。**未做到瀏覽器截圖層級的目視驗證**（畫面實際顏色/形狀），因為這次對話環境沒有連上 Chrome 擴充功能，建議之後找機會實際看一眼 | Story 1 | 1 個 |

> **2026-08-29 追加（同一天，使用者實機看到三個矩形後回報「沒有標示，也沒有地圖」）**：釐清了兩件事——(1) 沒有地圖（海岸線/地名）是任務 3.2 已經確認過的刻意決定，不是還沒載入好；(2) 沒有標示是因為 `territories` 端點本來就沒有政權名稱（只有 `regimeId`），這個缺口用 task 2.4（見上）補上後，接著在前端加了政權名稱標籤：`app/src/app/core/geometry/territory-labels.ts`（`computeTerritoryLabelPoints()`，用 Turf.js `centroid` 算每個政權的標籤定位點，同一政權多筆疆域快照只標一次）、`MapComponent` 改用 `forkJoin` 同時打 `territories`＋`regimes`（不加 `?year=` 一次拿全部政權建好 id→名稱對照表），`renderLabels()` 用 `maplibregl.Marker` 掛真正的 HTML 元素顯示政權名稱。**刻意不用 MapLibre 原生 symbol 圖層的 `text-field`**——那需要外部字型 glyphs（PBF）服務，違反任務 3.2 已拍板的「零外部依賴」原則，CJK 字型的 glyphs 又特別龐大，自架也不划算；改用 `Marker` 直接吃瀏覽器原生字型渲染，樣式檔 `app/src/app/map/map-labels.global.scss`（**必須是全域樣式，不能放進元件範圍的 `map.scss`**——`Marker` 的 DOM 元素是 MapLibre 自己插入頁面的，不會拿到 Angular Emulated encapsulation 的 host 屬性，跟 `maplibre-gl.css` 本身必須全域載入同一個道理），用白色 `text-shadow` 模擬地圖標籤常見的 halo 效果，不管疊在哪個色格上都看得清楚。已用 `ng build`/`ng test`（62/62，新增 `territory-labels.spec.ts`＋`map.spec.ts` 補上 `FakeMarker` mock）、`docker compose up -d --build frontend`＋curl 驗證部署的 bundle 含新程式碼、`/api/v1/regimes` proxy 正常。
>
> **2026-08-29 完成 3.3，3.5 補打勾**：任務 3.3（時間軸 Scrubber 主軸）完成——`app/src/app/core/time/timeline-state.ts`（`TimelineState`，`providedIn: 'root'` 的 signal 服務，`year` 是全域「目前顯示年份」狀態；範圍暫定 1-300 年，只涵蓋目前唯一有的三國史種子資料，不是世界史最終該有的範圍，之後要跟著擴大甚至改成依實際資料動態算上下限）、`app/src/app/time-scrubber/`（`TimeScrubberComponent`，原生 `<input type="range">`——瀏覽器原生支援真正連續拖動，不用自己刻拖曳手勢邏輯；只負責寫入 `TimelineState.year`，不管拖動後要做什麼，職責單一）。**3.4（副軸）刻意不做**：需要事件資料才有東西可以展開，事件端點（2.10+）還沒做，不做無資料可展示的 UI。`MapComponent` 改用 `toObservable(timeline.year).pipe(debounceTime(150))` 訂閱年份變化（避免拖桿時每個中間值都發一次請求），换年份時改走 `getSource('territories').setData()` 更新資料，不重新 `addSource`/`addLayer`（MapLibre 官方建議的動態資料更新方式，避免圖層閃爍重建）；政權清單只在地圖初始化時抓一次，不隨年份重複查。**同時把圖著色的穩定性機制真正接上了**：`assignTerritoryColorSlots()` 現在會傳入上一次的指派結果（`previousColorAssignment`），拖拉桿換年份時同一個政權不會無謂換色閃爍——這個機制在 `graph-coloring.ts` 一開始就做了，但要等真的有「換年份」這件事才用得到，3.3 完成才第一次真正被呼叫。**3.5 這裡補打勾**：3.5 原本卡在「拖動時間拉桿時...篩出當下應顯示的疆域」這條驗收標準做不到（沒有拉桿），3.3 做完後這件事本身已經達成（拖桿→重新查詢→重新渲染），3.5 的驗收標準明確排除的只有「形變」（那是另外標注的 3.6），不排除「換年份」本身，所以 3.5 現在可以打勾。已用 `ng build`/`ng test`（68/68，`map.spec.ts` 大幅重寫涵蓋 debounce 換年份走 `setData()` 而非重建圖層、政權/疆域各自失敗的錯誤處理）、`docker compose up -d --build frontend`＋curl 在 year=100（應只有漢）跟 year=270（應有吳+晉）兩個不同年份實測 `territories` 端點回傳筆數正確驗證。
>
> **2026-08-29 修正種子資料：漢的疆域沒有跟著劇情縮小，導致跟蜀漢/吳整塊重疊**（使用者實際拖拉桿看到 208-220 年間漢/蜀漢/吳三個矩形疊在一起後發現）。根因：`regime_territories` 裡漢原本只有一筆 `[189,220)` 涵蓋全境的示意矩形，沒有跟著劉備/孫權崛起而縮小——208 年赤壁之戰後，荊州/江東實際上已經不在漢廷（曹操挾天子）手上，但漢的疆域快照直到 220 年都沒變過。**使用者提出精準的修正方向**：東漢在概念上包含後來分裂出的三國，但魏正式建立（220 年禪讓）之前，東漢朝廷的「實質控制」範圍其實約等於曹操的地盤——禪讓是儀式性的主權轉移，不是打下新領土，魏建國時的疆域理論上該跟曹操禪讓前的實際控制範圍一致。已修正：漢的 `[189,220)` 一筆拆成兩筆——`[189,208)` 維持原本涵蓋全境的示意範圍（劉備/孫權尚未成勢），`[208,220)` 縮小、直接沿用魏建國第一筆疆域的座標（緯度 32-42，跟蜀漢/吳的緯度 22-32 剛好在 32 度交界、不重疊）。已 truncate `app_postgres` 相關表格＋`docker compose up -d --build backend` 重新播種，用 curl 驗證 year=210（4 筆，漢/蜀漢×2 爭議版本/吳，漢的座標已縮小到北方且跟其他三筆緯度不重疊）、year=190（漢仍是原本涵蓋全境的大矩形）、year=225（漢完全消失，只剩魏/蜀漢/吳）三個年份都正確，並確認前端 proxy 也拿到修正後的資料。
>
> **2026-08-29 補上爭議控制區斜線網底**（同一天，使用者接著問「213 年蜀漢跟東吳為什麼會重疊」——這次不是資料錯誤，是刻意設計：蜀漢版本A（經度 100-114）跟東吳（經度 112-122）在荊州爭議期間真的有重疊的宣稱範圍，兩者都標 `isDisputed=true`，但前端從沒把這個「有爭議」的狀態畫出來，看起來就像 bug）。補上 `app/src/app/core/geometry/territory-dispute-pattern.ts`（`darkenHex()`、`createDiagonalHatchImageData()` 畫 45 度可無縫拼接的斜線 tile、`territoryHatchImageId()`）＋ `MapComponent` 新增 `territories-disputed-hatch` 圖層（疊在 `territories-fill` 之上，`filter: isDisputed==true`，`fill-pattern` 用跟 `fill-color` 同一組 `colorSlot` 對照，只是換成網底圖樣而不是純色）。**網底色相跟識別色一樣、只是加深一階（tone-on-tone），不是另外挑一個全域固定顏色**——PRD §5 原本拍板「集中共用常數檔存固定網底顏色」，實際做的時候改了：tone-on-tone 才能讓「同一個政權的爭議/非爭議疆域」一眼看出是同一個政權，固定顏色會讓爭議疆域看起來像第六種身份色，反而搞混。**Canvas 2D 繪製，不是 WebGL Shader**（維持 §5/§9 風險表原本的選型）。**測試上的插曲**：`createDiagonalHatchImageData()` 需要真的 Canvas 2D context，JSDOM 沒有，原本想用 `vi.mock()` mock 掉，結果 Angular 的 Vitest 整合直接報錯「不支援對相對路徑模組用 vi.mock()，請用 Angular TestBed」——改把這個函式包成 `TerritoryHatchPatternService`（`providedIn: 'root'`），`map.spec.ts` 改用 `TestBed` provider 換成假的實作。已用 `ng build`/`ng test`（72/72）、`docker compose up -d --build frontend`＋curl 確認部署的 bundle 含新程式碼、`territories` 端點在 year=213 仍正確回傳驗證。
>
> **2026-08-29 修正斜線網底套用到非爭議疆域的 bug**（使用者拖桿到 208-214 年，回報連「漢」也被畫上網底——漢的 `isDisputed` 確認是 `false`，用瀏覽器 Console 直接 `fetch` 驗證過收到的資料本身是對的，問題出在前端渲染）。原本用 `filter: ['==', ['get','isDisputed'], true]` 排除非爭議疆域，第一次建圖層時的資料（預設年份 225）剛好 0 筆爭議疆域，換年份用 `source.setData()` 帶入新資料後，filter 疑似沒有正確重新套用，導致這個圖層對所有疆域都渲染（根因不完全確定，懷疑是 MapLibre 的 filter 在動態換資料時的邊界案例，沒有進一步深挖底層原因）。**改成不依賴 filter**：拿掉 `filter`，讓所有疆域都進這個圖層，改用 `paint.fill-opacity` 的 `case` expression（`['case', ['==', ['get','isDisputed'], true], 1, 0]`）決定要不要顯示——paint 屬性保證每次 `setData()` 都會重新求值，不依賴 filter 在動態資料下的重新套用行為，繞開這個未查明根因的邊界案例，換一個更保險的實作方式解決，不是原地打補丁。已新增 `map.spec.ts` 測試明確驗證這個圖層現在用 `fill-opacity` case expression、不是 `filter`（避免以後不小心改回去又踩到同一個坑卻沒有測試攔截）。已用 `ng build`/`ng test`（72/72）、`docker compose up -d --build frontend`＋curl 確認部署的 bundle 含新的 opacity expression。
>
> **2026-08-29 再次重寫：斜線網底改成即時算幾何交集，不是靠 `isDisputed` 旗標**（使用者
> 重新整理後仍看到漢有網底，逐步排查後發現是更根本的設計問題，不只是渲染 bug）。使用者
> 問「為什麼蜀漢/東吳整塊疆域都是斜線，不是只有兩者重疊的那一小塊」，並用二戰後英法美
> 蘇瓜分德國當類比：佔領區邊界是條約明訂，沒有史料分歧，若套用「一整筆疆域記錄標
> `is_disputed` 就整塊畫網底」的邏輯，會荒謬地把整個佔領區都畫成爭議——這個類比成立，
> 點出第一版斜線網底的設計本身就有問題，不是實作細節的 bug。**新增
> `app/src/app/core/geometry/territory-overlap.ts`**（`computeTerritoryOverlaps()`，
> 用 Turf.js `intersect()` 即時算任兩塊疆域的幾何交集，bbox 粗篩＋只對真正有交集的候選
> 對做精確運算；不分「同政權不同版本」的 I3 史觀分歧還是「不同政權」的邊界爭奪，兩種
> 都代表「這塊地同時有一個以上宣稱」，語意上是同一件事）。`MapComponent` 改成獨立的
> `territory-overlaps` GeoJSON source（換年份時重新算、`setData()` 更新，跟
> `territories` source 同一套模式）+ `territory-overlaps-hatch` 圖層，斜線只出現在真的
> 有面積重疊的地方，`isDisputed` 資料庫欄位不再驅動任何渲染（保留當 I3 型態的史觀分歧
> metadata，之後可能用在點擊詳情面板，不是現在的範圍）。**網底改用單一中性色**（不是
> tone-on-tone）——重疊區可能同時牽涉兩個以上不同色相的政權，不屬於任何單一政權的識別色；
> `territory-dispute-pattern.ts` 拿掉不再需要的 `territoryHatchImageId()`（只需要一張
> 圖樣，不用再依 colorSlot 分 5 張）。**種子資料順帶微調**：把東吳 208-215 年那筆疆域拆
> 成「江東核心」（`Rect(116,22,122,32)`，不受爭議）+「荊州爭議地帶」（`Rect(112,22,116,32)`，
> 跟蜀漢宣稱重疊）——這個拆分本身現在已經不影響斜線渲染（改用幾何交集後不需要手動拆），
> 但仍保留作為更精確的歷史資料模型（孫氏江東本土從沒被質疑過，不該跟荊州爭議混在同一筆）。
> 已更新 `map.spec.ts`（兩個 source、三個圖層、單一網底圖樣的新架構）、新增
> `territory-overlap.spec.ts`（5 組測試：真的重疊/只共邊接觸/完全不接觸/同政權自己
> 重疊/三塊兩兩重疊各自算一次）。已用 `ng build`/`ng test`（76/76）、
> `docker compose up -d --build frontend`＋curl 確認部署的 bundle 含新程式碼、
> `territories` 端點在 year=210 正確回傳 5 筆（東吳拆成兩筆後）驗證。
>
> **2026-08-29 修正更根本的問題：圖著色的節點是「疆域記錄」，不是「政權」**（使用者
> 部署後回報「蜀漢變成綠色+黃色兩種顏色，且只有綠色部分有斜線」，並準確描述成「東吳
> 內部出現確認的蜀漢領地、蜀漢內也有東吳的飛地」——這不是渲染細節問題，是色格指派的
> 演算法節點選錯了）。根因：`assignTerritoryColorSlots()` 原本直接把
> `featureCollection` 裡每一筆疆域記錄當成圖著色的節點；一個政權若同時有多筆疆域記錄
> （I3 史觀分歧的兩個並存版本、或核心/邊界拆成兩筆），這些記錄彼此幾何上互相重疊，
> 反而被圖著色演算法判定成「這幾筆需要分開上色」，變成同一個政權在畫面上出現兩種顏色
> ——使用者看到的「飛地」其實是同一個政權的另一筆記錄被分到了另一個政權常出現的顏色，
> 造成視覺上像是被對方領土包圍。修正：`app/src/app/core/geometry/territory-styling.ts`
> 改成先依 `regimeId` 分組，新增 `computeRegimeAdjacency()`——相鄰關係在「政權」這個
> 層級計算（政權 A 任一筆疆域跟政權 B 任一筆疆域有實際拓撲相交，這兩個政權才算相鄰），
> 圖著色也在政權層級跑，結果套用回該政權底下每一筆疆域記錄，同一個政權不管底下有幾筆
> 記錄永遠只有一個顏色。新增 2 條測試明確涵蓋這個情境（同政權多筆重疊記錄拿到同一色格；
> 同政權兩筆只是共邊相鄰，不影響色格指派，只有跟其他政權的關係才影響）。已用
> `ng build`/`ng test`（78/78）、`docker compose up -d --build frontend` 重新部署驗證。
>
> **2026-08-29 定案斜線網底的精確規則**：使用者把規則講到最簡：「政權掌控區用顏色表示，
> 政權重疊區域才用斜線」。核對後發現 `territory-overlap.ts` 原本沒有完全對齊這句話——
> 刻意讓「同一個政權自己兩個史觀版本互相重疊」也算進斜線範圍，這不是「政權重疊」，是
> 同一個政權自己的事，改成只算**不同政權**之間的幾何交集：`computeTerritoryOverlaps()`
> 改吃 `TerritoryWithRegime`（多一個 `regimeId` 欄位），比對兩筆疆域的 `regimeId` 是否
> 相同，相同就直接跳過、不算重疊。新增 2 條測試明確涵蓋（同政權自己重疊不算數；同政權
> 重疊+跟別政權重疊同時發生時，只有跟別政權那組算數）。已用 `ng build`/`ng test`
> （79/79）、`docker compose up -d --build frontend` 重新部署驗證。
>
> **2026-08-29 補上重疊區底色**：使用者截圖回報重疊區看起來只有「東吳的顏色+網底」，
> 看不出蜀漢也宣稱這塊地，問「兩邊的政權衝突區範圍應該要一樣吧」。先用 Turf.js 直接算
> 過一次確認：交集本來就是單一、無歧義的一塊幾何範圍（不是蜀漢跟東吳各自算出兩塊不同
> 大小的區域），不是計算錯誤，是**渲染**——`territory-overlaps-hatch` 的網底圖樣背景是
> 透明的（只有斜線本身不透明），疊在 `territories-fill` 上面時，透明部分會透出底下
> 「剛好排在後面那個政權」的顏色，看起來像這塊地只屬於其中一個政權。詢問使用者要「中性
> 底色」還是「兩色混合」，選了前者：新增 `territory-overlaps-fill` 圖層（不透明中性色，
> 沿用 `--wl-territory-border` 同一色系），排在 `territory-overlaps-hatch` 之前，先蓋掉
> 底下兩個政權各自的填色，網底斜線才疊上去——不透明中性底色本身就足以傳達「這裡不屬於
> 任何單一政權」，不需要混色。已用 `ng build`/`ng test`（79/79，新增底色圖層的斷言）、
> `docker compose up -d --build frontend` 重新部署驗證。
>
> **2026-08-29 定案「爭議區」的資料塑模方式：喀什米爾模型**（使用者拿現實的中印/印巴
> 喀什米爾邊界爭議當類比）：爭議區的定義是「雙方宣稱的範圍本身就是同一塊」，不是「兩個
> 不同形狀的矩形剛好有一小段重疊」——原本蜀漢版本 A（100-114）跟東吳爭議地帶
> （112-116）只有 112-114 這一小段真的重疊，各自宣稱的範圍都比實際重疊區大很多，不
> 合理。改成蜀漢跟東吳的「荊州爭議地帶」用**完全相同的座標**（`Rect(111,26,116,32)`），
> 兩邊各自的核心區（蜀漢 100-111、東吳 116-122）維持獨立不變。**取代了原本 I3 示範用的
> 蜀漢兩個並存版本**（自己對借荊州範圍的史觀分歧）——那個示範跟「跟東吳的邊界爭議」是
> 同一個歷史問題的兩種建模方式，同時維持兩者太複雜，選擇保留跟東吳的邊界爭議（更貼近
> 「政權重疊區才算爭議」這條已拍板規則的實際用例）；I3 並存版本機制本身的 schema 支援
> 不受影響，只是這筆種子資料不再拿它示範，之後有更適合的案例（例如不涉及跨政權邊界的
> 單純史觀分歧）再補。已用 Turf.js 直接驗證：兩筆完全相同座標的疆域交集後，回傳的
> 就是同一塊完整範圍，不再有「宣稱範圍>實際重疊」的落差。已 truncate `app_postgres`
> 相關表格＋`docker compose up -d --build backend` 重新播種，curl 驗證 year=210 蜀漢/
> 東吳的爭議地帶座標完全一致（111-116，緯度26-32）。
>
> **2026-08-30 重疊區底色從中性灰改成專屬紅色階**（使用者要求「幫我多加一組色票在
> design token 當中，是需要紅色的 50-900 的」，對應前一則喀什米爾模型定案後的自然延伸：
> 重疊區的視覺語意其實是「內容」——有政權主張衝突——不是「結構」，不該跟疆域邊界線共用
> `--wl-territory-border` 那個中性色 token）。新增 `design-tokens.scss` 的
> `--wl-dispute-50` ~ `--wl-dispute-900` 十階紅色階，錨點沿用既有的 `--wl-status-critical`
> （`#d03b3b`），不是另外挑一個新紅色——語意上「爭議」跟既有的「危急/嚴重」狀態色同屬一個
> 色相家族；也刻意不用 `territory-colors.ts` 政權識別色清單裡已經在用的那個紅（分類色
> slot 8），避免疆域填色跟爭議標記的紅色混淆成同一件事。生成方法沿用本次對話稍早驗證過
> 的**色域邊界比例縮放**（`maxChromaInGamut(L,H)` 二分搜尋 + `ratio = 錨點彩度 / 錨點
> L的色域邊界彩度`），不是「借用其他色相的彩度曲線形狀」那個已知有嚴重色相漂移問題的方法
> （Sanring success/warn/error 色階踩過的坑）。實測色相偏差最大 8 度（集中在幾乎無彩度的
> 50 階，可忽略），其餘各階都在 0.5 度內；`--wl-dispute-500`（`#b83333`）配白字對比
> 5.90:1、配淺色面板 5.75:1，均通過 WCAG AA。`MapComponent` 的 `territory-overlaps-fill`
> 與 `territory-overlaps-hatch`（含 `hatchPatterns.create()` 的網底基準色）改吃
> `--wl-dispute-500`，`territories-border`（疆域邊界線本身）維持不變、仍是
> `--wl-territory-border` 中性灰——兩者刻意分開，一個是結構語意一個是內容語意。
> `territory-dispute-pattern.ts` 的網底繪製邏輯本身不用改（`createDiagonalHatchImageData()`
> 不關心呼叫端傳什麼底色，只負責加深一階畫斜線），只更新了檔案開頭過時的「中性色」說明
> 文字。已用 `ng build`/`ng test`（79/79）、`docker compose up -d --build frontend`
> 重新部署，curl 確認後端 `territories` 端點正常回應驗證。
| [x] | 3.6 | **疆域快照間形變過渡動畫（Flubber.js）** | 拖動拉桿時，兩筆快照之間的疆域邊界真正連續變形，不是切換/淡入淡出——對應憲法 §9「疆域必須連續變化呈現，非離散跳轉」核心要求（2026-08-26 拍板：從 Backlog 移入本階段，非候選）。**已完成（2026-08-30）**：新增 `app/src/app/core/geometry/territory-morph.ts`（`buildMorphPlan()`＋`sampleMorphPlan()`，純函式，Flubber.js `interpolate()` 插值疆域環的座標點）、`morph-animation-scheduler.service.ts`（`MorphAnimationScheduler`，DI 包裝 `requestAnimationFrame`，理由跟 `TerritoryHatchPatternService` 包裝 Canvas 2D 一樣——Angular 的 Vitest 整合不支援對相對路徑模組用 `vi.mock()`，測試要透過 TestBed provider 換成「一步跳到終點」的假時序，不用真的等 500ms 動畫跑完）。`MapComponent` 換年份時改呼叫 `applyTerritories()`：第一次載入或使用者有 `prefers-reduced-motion: reduce` 偏好時直接 `settle()`（跳過動畫），否則 `buildMorphPlan(舊資料, 新資料)` 後跑一輪 500ms、ease-in-out-cubic 緩動的補間動畫，逐幀 `setData()`。**配對策略**：先依 `regimeId` 分組，同一政權底下的疆域列（可能有 1-2 筆，例如爭議期間的核心區+爭議區）用環的形心座標排出決定性順序後逐一配對；兩個年份疆域列數量不一致時（政權新成立/滅亡、或進出爭議期間），多出來的部分歸類 entering/leaving，改用淡入/淡出（`morphOpacity` 屬性），不強行插值（沒有唯一解）。**重疊區網底也跟著淡**：`territory-overlap.ts` 的 `computeTerritoryOverlaps()` 擴充成回傳 `{geometry, opacity}`（取兩個來源政權疆域列 `morphOpacity` 的較小值），不會在來源政權自己都還沒完全出現時就先以滿版強度顯示重疊斜線。**刻意的 V1 範圍限制**（已在程式碼註解記錄，不是遺漏）：只讀每個 feature 的第一個 polygon/第一個環（目前種子資料的 `MultiPolygon` 一律單一 polygon 單一環，之後真的匯入有多部分/有洞的史料幾何才需要擴充）；標籤（`Marker`）不逐幀跟著疆域形狀移動，只在動畫終點更新一次。已用真實矩形資料在 Node 直接呼叫 flubber 驗證兩個關鍵行為：`{string:false}` 回傳插值點陣列而不是 SVG path 字串（`@types/flubber` 的型別定義沒有覆蓋這個分支，程式碼裡有轉型註解說明）、插值結果不保留輸入的閉環格式（首尾同點），所以 `sampleMorphPlan()` 補上 `closeRing()`。已用 `ng build`（1.43MB/319KB，在任務 3.2 為 MapLibre 提高過的 1.5MB/2.5MB 預算內）、`ng test`（93/93，新增 `territory-morph.spec.ts`＋`territory-overlap.spec.ts` 的 opacity 測試＋`map.spec.ts` 一個專門驗證「拖拉桿拖得比動畫時長還快時，新動畫會取消舊動畫、不會被過期幀的資料蓋掉」競態情境的測試）、`docker compose up -d --build frontend`＋curl 確認部署的 bundle 含 `flubber`／`morphOpacity` 關鍵字驗證 | Story 1、§9 | 1 個 |

> **2026-08-30 修正三個實機回報的問題**：
> 1. **動畫時長太短**（使用者：「有邊疆調整的年度，會顯得有點突兀」）——`MORPH_DURATION_MS` 從 500ms 調高到 900ms。
> 2. **矩形疆域形變時看起來像在旋轉/不對稱拉伸**（使用者：「目前都是方形的領土，領土改變時為什麼會有旋轉或者左右拉伸不同的動畫效果」）。根因：`territory-morph.ts` 原本一律把兩個環丟給 flubber 的 `interpolate()` 猜對應關係——那個演算法是設計給「不知道兩個形狀頂點對應關係」的一般情況用的，會先把環重新取樣成更密的點集，再嘗試幾種起點位移、挑「總移動量最小」的當對應關係。這個專案的疆域資料目前一律是 `Rect()` 產生的矩形，相鄰年份快照之間頂點數永遠相同、順序永遠一致，對應關係其實是已知的，讓 flubber 猜反而在「只有一條邊移動、其餘角完全沒動」這種簡單情況下選到跟直覺不符的對應關係，看起來像在旋轉。**修正**：新增 `buildRingInterpolator()`，頂點數相同時直接逐點線性插值（不動的角保證完全不動，移動的邊保證走最短直線路徑），頂點數不同時（之後真的匯入形狀被重新繪製過的史料）才退回用 flubber。
> 3. **禪讓/滅國這種和平或武力的政權更迭，換年份動畫過程中會閃過一整塊紅色爭議斜線**（使用者：「目前如果是朝代更迭 漢->魏，魏->晉 為什麼都會是紅色斜線的政權衝突區？」）。根因：這個專案刻意讓禪讓/滅國前後兩個政權的疆域座標完全一致（魏建國疆域＝曹操禪讓前的漢朝實際控制地盤，見下方任務 3.6 第三次修正的說明）——形變動畫換年份跨過交接的那一刻，舊政權那筆疆域正在淡出（`morphRole:'leaving'`）、新政權那筆正在淡入（`morphRole:'entering'`），兩者座標完全相同，`computeTerritoryOverlaps()` 的幾何交集判斷把這個「同一塊地換了主人」的動畫過場假象，誤判成「兩個政權同時宣稱同一塊地」的真實政權衝突。**修正**：`computeTerritoryOverlaps()` 新增 `morphRole` 參數，明確排除 entering×leaving 這一種配對（matched 對 entering/leaving，或 entering 對 entering、leaving 對 leaving 這些配對維持原樣照算，只有這一種組合是「交接瞬間的視覺假象」）。
>
> 已用 `ng build`（clean）、`ng test`（99/99，新增 `territory-morph.spec.ts` 的逐點插值/morphRole 標記測試＋`territory-overlap.spec.ts` 的 entering×leaving 排除測試）、`docker compose up -d --build frontend`＋curl 確認部署的 bundle 含 `morphRole`／`900` 關鍵字驗證。
>
> **同時修正 SeedData.cs 的一個政權更迭資料缺口**（使用者：「263年蜀漢被魏攻入後滅亡，那魏並沒有接管蜀漢的領地這是為什麼？」）——這是資料問題，不是渲染問題：魏原本只有北方核心疆域 3 筆快照，263 年蜀漢滅亡後，蜀漢原本的益州疆域直接從地圖上消失、變成無主之地，沒有反映「魏滅蜀」實際發生的地盤轉移。**修正**：魏新增一筆 `[263,265)` 疆域（南方，座標沿用蜀漢滅亡前最後一筆 `Rect(100,26,108,32)`）；晉的 `[265,280)` 這段同樣拆成北方核心+南方（原蜀地）兩筆——跟漢禪魏的處理原則一致：政權更迭不會讓已經被佔領的土地憑空消失，疆域理論上該直接銜接原本的控制範圍。已 truncate `app_postgres` 相關表格＋`docker compose up -d --build backend` 重新播種，curl 驗證 year=262（蜀漢仍在）、year=264（蜀漢消失、魏出現兩筆疆域記錄）、year=270（晉出現兩筆疆域記錄，涵蓋原魏+原蜀地）都正確。
>
> **已知限制（2026-08-30，使用者確認擱置）**：魏 263 年併吞蜀漢後的疆域畫法（北方核心+南方新併吞兩筆分開的矩形），視覺上看起來像「兩塊拼起來」不是一整塊——用 `ST_Touches`/`ST_Distance` 驗證過兩塊矩形確實有接觸（`distance=0`），不是浮空的兩塊，只是接觸的邊只佔北方矩形寬度一小段（104-123 裡的 104-108），看起來像掛在角落。曾評估改成單一合併外接矩形（lon 100-123、lat 26-42），但驗證後發現這個範圍會把吳的實際疆域（lon 108-122、lat 20-32）幾乎整塊包進去，等於把吳的領土誤植成魏的——矩形疊代示意資料的形狀/位置限制，沒有更好的單一矩形解法。使用者確認**先擱置，等之後真的匯入 OpenHistoricalMap 真實史料（非矩形多邊形）時，這個「矩形示意資料形狀限制」會自然消失，不需要現在特別花時間優化**，不是被遺忘沒處理。
| [x] | 3.7 | 政權聚焦模式（點擊疆域→高亮+周邊政權清單） | Story 2 完整流程 | Story 2 | 1 個 |

> **2026-08-30 完成 3.7 AC#1、AC#2（AC#3 當時刻意未做，見下方說明；同一天稍後
> task 2.9/2.10 做完後回頭補上，見本任務區塊最後一則更新）**：
>
> **AC#1（點擊聚焦+高亮+周邊政權清單）**：`MapComponent` 新增 `map.on('click', ...)`
> + `queryRenderedFeatures()` 判斷點擊到哪個 regimeId（不是自己重新算幾何），寫進新的
> `RegimeFocusState`（`providedIn:'root'`，跟 `TimelineState` 同一個「地圖跟其他元件是
> 兄弟關係，用 service 集中管理」的理由）。渲染面：`territories-fill` 的 `fill-opacity`
> 改成聚焦政權維持不透明、其餘政權大幅降低（「聚光燈」效果，用 `['case', ...]`
> expression，跟形變動畫的 `morphOpacity` 相乘組合，兩者不衝突）；新增
> `territories-focus-outline` 圖層（`--wl-focus-ring` 色、比一般邊界粗，疊在所有圖層
> 最上層）。周邊政權清單重用圖著色也在用的同一套「政權層級相鄰關係」判斷（把
> `territory-styling.ts` 的 `computeRegimeAdjacency()` 匯出，新增
> `core/geometry/regime-focus.ts` 的 `findNeighboringRegimeIds()` 重用它，不是另外
>發明一套「周邊」定義）——每次疆域資料定案或聚焦目標改變都重算一次，拖拉桿換年份時
> 高亮/清單會自動跟著更新。新增 `RegimeFocusPanelComponent`（掛在 `App` 的 `.map-area`
> 右上角）顯示聚焦政權名稱+周邊清單。**政權名稱對照表抽成共用 service**
> （`RegimeDirectoryService`，`providedIn:'root'`，`shareReplay(1)` 快取）：原本是
> `MapComponent` 私有欄位，面板元件也需要同一份，改成兩邊共用、只打一次
> `/api/v1/regimes`。
>
> **AC#2（存續區間高亮+超出範圍警示）**：`RegimeFocusState` 聚焦時額外打
> `GET /api/v1/regimes/:id/territories`（task 2.6 既有端點），取所有疆域列的
> `startYear`/`endYear` 邊界算 `lifetimeRange`（min/max，近似「存續期間」，不逐年
> 精確——疆域快照本身就是事件驅動的離散記錄，這是目前資料精度下唯一可行的定義）。
> **過期請求防護**：聚焦目標可能在請求還沒回來前就再次改變，`loadLifetimeRange()` 回應
> 時會比對「現在聚焦的還是不是當初發請求的那個政權」，不是的話直接丟棄——已用專門的
> 競態測試驗證（`regime-focus-state.spec.ts`）。`TimeScrubberComponent` 疊一條半透明
> 色帶標示這個區間（换算成拉桿範圍內的百分比定位）——**刻意不客製原生 `<input
> type=range>` 的 `::-webkit-slider-runnable-track`/`::-moz-range-track` 偽元素**
> 去畫，那兩個是不同瀏覽器引擎分開的 API，會打架既有的 `accent-color` 簡化方案，改用
> 疊一層獨立的裝飾用 `<div>`（`pointer-events: none`）。超出區間時的警示文字顯示在
> `RegimeFocusPanelComponent`（「此政權於西元 X 年尚未建立/已不存在」），不重複做在
> 拉桿上。
>
> **AC#3（互動清單，連結 `historical_events`/`regime_relations` 記錄）刻意不做**：
> 後端對應端點（task 2.9 政權關係、2.10 事件骨幹）都還沒實作，沒有資料可以連結，跟
> 任務 3.4（時間軸副軸）因為事件資料還沒做而刻意跳過是同一個處理原則——等 2.9/2.10
> 做出來後再回頭補這個 AC，3.7 不因此卡住不打勾（跟 3.5 曾經因為缺一個子項目沒打勾、
> 之後補齊才打勾的處理方式一致，這次改成直接記錄「大部分完成、剩一個明確待辦」）。
>
> 已用 `ng build`（1.45MB/325KB，budget 內）、`ng test`（125/125，新增 25 條：
> `regime-focus.spec.ts`＋`regime-directory.service.spec.ts`＋
> `regime-focus-state.spec.ts`（含過期請求競態測試）＋`regime-focus-panel.spec.ts`＋
> `map.spec.ts`／`time-scrubber.spec.ts`／`app.spec.ts` 的新增案例）、
> `docker compose up -d --build frontend`＋curl 確認部署的 bundle 含
> `territories-focus-outline`／`regime-focus` 關鍵字驗證。這次對話環境沒有連上 Chrome
> 擴充功能，沒有做到瀏覽器截圖層級的目視驗證，建議之後找機會實際點一次看看。
>
> **2026-08-30 修正實機截圖回報的版面問題 + 引入 Sanring `Collapsible`**：使用者截圖
> 回報聚焦面板（原本掛在地圖右上角）會蓋住 MapLibre 的 `NavigationControl`（+/-/指南針，
> 同樣掛在 `top-right`）。**面板改到左上角**，跟 `NavigationControl` 完全對角分開，不用
> 動 `NavigationControl` 的位置。使用者接著提議改用 Sanring `Sheet`，但自己在同一句話
> 裡就發現問題：`Sheet` 是包在 CDK Dialog 之上的真．模態框（鎖 `<body>` 捲動、背景
> `aria-hidden`、可點擊關閉的遮罩、focus trap），這些行為是「專心看這塊內容、暫時不管
> 背景」設計的，跟「同時看地圖高亮+讀面板」的需求方向相反，沒有選項可以關掉模態行為——
> 使用者確認**不用 Sheet，維持固定面板 + 引入 `Collapsible`**（見 AskUserQuestion 的
> 選擇）。已用 `npx @sanring/cli add collapsible` 安裝（`app/src/app/components/ui/
> collapsible/`，這個元件本身沒有預設樣式，純邏輯 + a11y 屬性，視覺完全由專案樣式決定，
> 跟已裝的 `Button`——有預設 variant 樣式——不一樣）。「同時期周邊政權」這個區塊包進
> `<sanring-collapsible [open]="true">`，觸發鈕在 `regime-focus-panel.html`；**政權
> 名稱（標題）跟存續區間警告刻意留在 Collapsible 外面、永遠可見**——警告是「這個政權
> 現在不存在」這種重要資訊，不該被收合狀態藏起來。已用 `ng build`（1.48MB/335KB，
> budget 內）、`ng test`（127/127，新增 2 條收合/展開的互動測試）、
> `docker compose up -d --build frontend`＋curl 確認部署驗證。
>
> **2026-08-30 追加存續期間顯示、Sanring `Tag`、「同時期其他地區政權」清單**：使用者
> 提三個需求，逐一釐清資料來源後拍板：
> 1. **政權存活時間**——確認先只用年份精度（`RegimeFocusState.lifetimeRange` 已經有
>    這份資料），顯示在標題下方，例如「西元 220–265 年」。日期精度（例如「221年5月
>    15日」）需要查 `historical_events` 裡禪讓/滅國事件的確切 EDTF 日期，那個查詢端點
>    （task 2.10）還沒做，先不做。
> 2. **「三國」這種歷史分期標籤**——確認**先不做，但記下來之後要處理**：目前
>    `regimes` schema 完全沒有「歷史分期」概念，`lineage_presets` 是史觀方案不是分期；
>    現有種子資料也全部落在同一個分期，加了也沒有區分度，等之後真的匯入跨分期的世界史
>    資料再回頭設計這塊怎麼從資料庫查出來，不要用前端寫死的對照表撐過去。
> 3. **同時期其他地區政權清單**（例如聚焦唐朝時列出不接壤的阿拉伯帝國）——確認要做。
>    新增 `regime-focus.ts` 的 `findOtherContemporaryRegimeIds()`：這批當年有效的疆域
>    資料裡，除了聚焦政權自己跟已經算出來的周邊政權以外，其餘政權全部算進去，不用額外
>    查詢。**目前種子資料規模下這個清單大概率是空的**（漢/魏/蜀漢/吳/晉彼此地理相鄰），
>    不是邏輯錯誤，已在程式碼/面板空狀態文案裡都有說明，等之後匯入世界史資料才會開始
>    出現東西。
>
> **政權名稱改用 Sanring `Tag` 呈現**（`npx @sanring/cli add tag`，同批裝了依賴
> `Badge` 跟 `@lucide/angular`）：使用者原本要「文字色＝該政權在地圖上的顏色」這種
> 動態配色，但 `Tag`/`Badge` 的配色是走固定語意 variant（`default`/`secondary`/
> `destructive`/`outline`/`ghost`），沒有設計成讓每個實例帶入任意顏色——跟使用者
> 確認後，**拍板不硬套動態配色，固定用同一個 variant 呈現所有政權名稱**（周邊政權用
> `secondary`、同時期其他地區政權用 `outline`，用不同 variant 區分兩個清單的語意，
> 不是嘗試精確對應地圖顏色）。已用 `ng build`（1.50MB/338KB，把 `maximumWarning`
> 從 1.5MB 調到 1.8MB——這次新增的是真的功能性 UI 元件，不是意外肥大，跟任務 3.2
> 為 MapLibre 調高預算同一個處理原則）、`ng test`（135/135，新增 8 條：存續期間顯示、
> Tag 呈現周邊清單、「同時期其他地區政權」清單的顯示/排序/空狀態、`map.spec.ts` 驗證
> 不相鄰政權正確分流到 `otherContemporaryRegimeIds` 而非 `neighborRegimeIds`）、
> `docker compose up -d --build frontend`＋curl 確認部署驗證。
>
> **2026-08-30 補完 AC#3（互動清單）——task 2.9/2.10 都做完後回頭補上**：使用者一開始
> 問「互動清單是哪裡定義的」，追問到底才發現 schema 沒有一張通用的「事件參與者」關聯表
> 可以查「哪些政權涉入了哪個事件」，只有兩個各自不完整的機制：`regime_transition_events`
> （只連轉換的一方，另一方要從 `regimes.predecessor_regime_id`/`destroyed_by_regime_id`
> 反查）、`historical_event_perspectives.regime_id`（種子資料原本只有蜀漢對赤壁之戰
> 留了視角，東吳完全沒留，配不出「蜀漢↔東吳」這組互動）。跟使用者確認方向後**選項 2：
> 兩套機制都用，並補一筆東吳視角種子資料**（不是只用轉換事件那套範圍較窄但簡單的做法）。
>
> **後端新增 `GET /api/v1/regimes/{regimeId}/events?year={y}`**（`EventsController.
> GetInteractionsByRegime()`，任務 2.10 的延伸）：合併兩個來源，任一成立就算一筆互動——
> (1) 政權轉換事件，含反向查詢（這個政權是別人的 predecessor/destroyer 時，也要從對方
> 的 `regime_transition_events` 找出事件）；(2) 多重視角敘事，同一事件下這個政權跟
> 另一個政權都留下視角才算（不是單方面有視角就算）。持續性關係沿用既有的
> `GET /regimes/:id/relations`（task 2.9），不用新端點。`api/Data/SeedData.cs` 補上
> 東吳對赤壁之戰的視角（`LocalName = "東吳視角"`），敘事重心刻意跟蜀漢視角不同（蜀漢
> 視角強調「孫劉兩家結盟、聯軍以寡擊眾」，東吳視角強調周瑜/江東水軍才是決勝主力——
> 這是史學界真實存在的敘事分歧，不是為了測試隨便複製一份）。已用真實容器 curl 驗證
> 六種組合：轉換事件正向（蜀漢/魏在 263 年）、反向（魏/蜀漢在 263 年，從魏這邊查也
> 要看到同一個事件）、視角互動正向反向（蜀漢/吳、吳/蜀漢在 208 年赤壁之戰）、缺
> `year`（400）、政權不存在（404）。
>
> **前端**：`RegimeFocusState` 新增 `eventInteractions`/`relationInteractions` 兩個
> signal，`toggle()` 時同步（不等 debounce，跟 `loadLifetimeRange()` 一樣的道理——
> 聚焦是離散動作）查詢；另外訂閱 `timeline.year`（debounce 150ms）在已聚焦狀態下拖拉桿
> 換年份時重新查——**這裡踩到一個真的會製造偽陽性測試的坑**：一開始把
> `focusedRegimeId`／`timeline.year` 兩個信號合併進同一個 `toObservable` 訂閱，
> 結果 `toggle()` 呼叫一次會讓這個訂閱的第一次 emit 又觸發一次一模一樣的查詢（重複
> 打兩次 API）；改成 `toggle()` 裡同步呼叫、建構子只單獨訂閱 `timeline.year`（讀
> `focusedRegimeId()` 判斷要不要查，但不當作觸發源）解決重複呼叫，同時大幅縮小了
> debounce 相關的測試面積（原本 debounce 版本會讓所有呼叫 `toggle()` 的既有測試在
> `afterEach` 的 `httpMock.verify()` 噴「還有未處理的請求」，因為請求要等 150ms debounce
> 才真的發出、測試沒等那麼久就結束了——**這批既有測試原本會變成「意外綠燈」，因為
> debounce 還沒觸發時 `verify()` 根本看不到那個請求**，跟這個專案先前踩過的
> `afterNextRender` 吞例外是同一類「非同步時序讓測試看起來過但沒真的測到」的陷阱，
> 已在 `map.spec.ts`／`regime-focus-panel.spec.ts`／`regime-focus-state.spec.ts`／
> `time-scrubber.spec.ts` 補齊對應的 `httpMock.expectOne().flush()`）。面板新增「互動
> 記錄」collapsible 區塊，**只顯示跟目前周邊政權清單有交集的互動**（AC#3 原文是「聚焦
> 政權與周邊政權之間」，`RegimeFocusState` 回傳的是這個政權全部已知互動、過濾交給面板
> 的 computed 做）；「可點擊追溯」目前只是純文字，還不能真的點開——事件/關係詳情畫面
> （task 3.12）還沒做，先把「有哪些互動」列出來。已用 `ng build`（1.50MB/338KB，
> budget 內）、`ng test`（140/140，新增 5 條：互動清單同步查詢跟換算/debounce 換年份
> 重新查/未聚焦時不查/過濾周邊/空狀態）、`docker compose up -d --build backend frontend`
> ＋curl 確認部署驗證，AC#1/AC#2/AC#3 全數完成，3.7 完整達成。
| [x] | 3.8 | 政權命名視角切換（自稱／他稱代稱） | Story 3 完整流程 | Story 3 | 1 個 |

> **2026-08-30 完成**（Story 3 最後一塊拼圖，依賴 task 2.9a 拍板的 `alias_type` 決策，
> 完成後 5 個 Story 全數達成）：
>
> **AC#1（客觀視角顯示自稱）驗證後確認已滿足，不用新增程式碼**——地圖標籤本來就一律
> 顯示 `RegimeDirectoryService.nameOf()`，這本身就是「全球客觀視角」；`NamingViewpoint
> State.observerRegimeId` 預設 `null`，維持這個既有行為，AC#1 不需要額外邏輯，只需要
> 確保新加的視角邏輯預設不啟動。
>
> **AC#3（孤兒代稱資料完整性）驗證後確認已滿足，不用新增程式碼**——`regime_aliases.
> regime_id` 是必填 FK（`RegimeAliasConfiguration.cs`），孤兒代稱在 DB 層面物理上不
> 可能存在。用真實容器直接對 `app_postgres` 跑 `INSERT INTO regime_aliases (...)
> VALUES (..., '00000000-...', ...)`，確認被 `fk_regime_aliases_regimes_regime_id`
> 約束擋下（`ERROR: insert or update on table "regime_aliases" violates foreign key
> constraint`）——這是 I4「不可容忍孤兒代稱資料上線」比應用層檢查更強的保證，不需要
> 前端另外寫一層「載入時檢查孤兒資料」的防呆邏輯。
>
> **AC#2（視角切換＋代稱顯示＋可追溯性，本任務主要工作）**：
> - `app/src/app/core/regime/naming-viewpoint-state.ts`（`NamingViewpointState`）：
>   目前選擇的觀察政權 id，`null`＝客觀視角。**刻意跟 `RegimeFocusState`（任務 3.7）
>   分開**——3.7 的「聚焦」是點擊疆域→高亮+顯示周邊/互動面板，這裡的「視角」是全域性
>   改變地圖上*所有*標籤怎麼命名，服務完全不同的問題，硬共用同一個 signal 會讓兩件事
>   的意圖糾纏在一起。
> - `app/src/app/core/regime/regime-alias-directory.service.ts`
>   （`RegimeAliasDirectoryService`）：後端沒有「一次查全部代稱」的端點，依賴
>   `RegimeDirectoryService.all()`（這次順便補上）先知道有哪些政權，`forkJoin` 對每個
>   政權各發一次 `GET /regimes/:id/aliases`。**刻意延後載入，不在地圖初始化時跟著
>   `RegimeDirectoryService` 一起預先抓**：多數使用者全程停留在客觀視角，代稱資料完全
>   用不到，只有使用者第一次切換到某個特定觀察視角才觸發（`ensureLoaded()` 沿用
>   `shareReplay(1)` 快取，之後切換視角不重新查）。
> - `MapComponent.renderLabels()`：`observerRegimeId` 非 `null` 時查
>   `aliasFor(regimeId, observerId)`，查得到才換代稱顯示、查無資料 fallback 回自稱
>   （跟翻譯 fallback 同一個原則）。顯示代稱的標籤額外加 `.territory-label-clickable`
>   （打開 `pointer-events`，其餘標籤維持 `pointer-events: none` 不擋地圖拖曳手勢）、
>   原生 `title` 屬性顯示「自稱：OOO」（hover 可追溯，不用自己刻 tooltip UI）、
>   click 直接呼叫 `focusState.toggle(regimeId)`（複用任務 3.7 既有的聚焦面板機制，
>   面板標題本來就顯示真正的自稱名稱，不用為這個 AC 另外做一個顯示自稱的 UI）。
> - `app/src/app/naming-viewpoint-selector/`（`NamingViewpointSelectorComponent`）：
>   下拉選單，「全球客觀視角」+ 全部政權（依名稱排序），掛在頁首跟 `<app-lineage-
>   sequence>` 並排。**列出全部政權，不篩掉目前沒有代稱資料的**——「任何政權都可以是
>   觀察者」這個概念成立，跟「這個觀察者目前有沒有留下代稱記錄」是兩回事，沒有資料時
>   fallback 顯示自稱不是錯誤狀態。
>
> **目前種子資料還沒有 PRD 原文舉例的「唐朝視角看阿拉伯帝國＝大食」**（那個時代的政權
> 還沒匯入），實際驗證改用種子資料裡真實存在的案例：切換到「以蜀漢視角」，魏的標籤
> 正確顯示代稱「賊」（task 2.9a 種子資料，蜀漢文書視角稱魏為賊），hover 顯示「自稱：
> 魏」，點擊正確開啟聚焦面板並顯示真正的自稱「魏」。
>
> 已用 `ng build`（clean）、`ng test`（206/206，新增 22 條：`regime-alias-directory.
> service.spec.ts`、`naming-viewpoint-state.spec.ts`、`naming-viewpoint-selector.
> spec.ts`、`regime-directory.service.spec.ts` 補上 `all()`、`map.spec.ts` 新增「命名
> 視角切換（任務 3.8）」describe 區塊涵蓋客觀視角不預先載入代稱/切換視角後代稱+
> fallback 正確顯示/hover title+可點擊樣式/點擊觸發聚焦/切回客觀視角不重複載入五種
> 情境）、`docker compose up -d --build backend frontend`＋curl 對真實容器驗證
> `GET /regimes/:id/aliases` 資料形狀跟前端測試 mock 一致、部署的 bundle 用 esbuild
> 轉義後的 `\uXXXX` 形式比對確認新程式碼真的在裡面（`全球客觀視角`／`自稱：`／
> `territory-label-clickable` 均命中）。**沒有做到真實瀏覽器的視覺/互動驗證**（這次
> 對話環境沒有連上 Chrome 擴充功能）——click/hover 邏輯是用 jsdom 直接 dispatch 真實
> DOM 事件驗證（不是純粹的邏輯 mock），但畫面實際呈現效果（例如底線樣式、hover
> tooltip 的瀏覽器原生外觀）建議之後找機會實機看一眼
>
> **2026-08-31 追加種子資料：唐朝／伍麥亞王朝／阿拔斯王朝**（使用者要求把 AC#2 原文
> 舉例的案例補成真的資料，不是只用蜀漢/魏的替代案例打勾）——`api/Data/SeedData.cs`
> 新增第三段獨立區塊（跟原本 1.7 的三國資料完全不相干，時間上刻意留白 189-618 年，
> 見該區塊開頭說明）：
> - **政權**：唐（`active`）、伍麥亞王朝（`conquered`，750 年被阿拔斯革命推翻）、
>   阿拔斯王朝（`active`）。**阿拔斯不是伍麥亞「分裂」或「禪讓」出來的**——阿拔斯家族
>   主張的正統性來自先知叔父阿拔斯的血統，是一場革命推翻，`predecessor_regime_id`/
>   `origin_transition_type` 刻意留 null，「誰打贏了誰」記錄在被滅政權自己的
>   `destroyed_by_regime_id`（跟蜀漢/吳被滅時魏/晉自己不會有對應 origin 欄位同一個
>   處理原則，見下方 task 3.9 說明）——這是本專案第一次示範「被滅亡」在非中國史脈絡
>   下的案例，且不是攻滅戰爭而是革命起事，驗證了 `conquered` 狀態的定義不侷限於
>   「一方軍事攻滅另一方」這種敘事。
> - **代稱**：白衣大食（伍麥亞）／黑衣大食（阿拔斯），都掛在「唐視角」下——刻意各建
>   一筆而非一個泛用「大食」套在兩個政權上，因為唐代史料（《舊唐書》《新唐書》
>   〈大食傳〉）依旗幟顏色確實區分兩個先後政權，這樣才是真正驗證 AC#2「代稱」概念，
>   不是隨便湊一個名字。
> - **疆域**：唐 2 筆（618-751 涵蓋安西四鎮西抵中亞的極盛範圍；751 怛羅斯戰敗後收縮）
>   ＋伍麥亞 1 筆（661-750）＋阿拔斯 1 筆（750-900，示意終點，非史實終點）。**唐朝
>   西境跟阿拉伯帝國東境在中亞真的有地理重疊**——這正是怛羅斯之戰的地緣背景，不是
>   矩形示意資料湊巧重疊；751 年後唐朝收縮、兩者不再重疊，是本專案目前唯一橫跨兩個
>   不同文明政權、疆域重疊有真實史地意義的案例（PRD §6 原本就以「唐朝 618-907 年間
>   應有多筆快照」當作事件驅動密度的示範例子，這批資料正好回應那個既有的設計預期）。
> - **事件**：阿拔斯革命（750，`RegimeTransitionEvent` 連回伍麥亞的 `destruction`
>   邊，補齊「每個 conquered 政權都有連結觸發事件」這條既有慣例）＋怛羅斯之戰（751，
>   唐／阿拔斯雙方視角，跟赤壁之戰蜀漢/東吳雙方視角同一個模式，讓 task 3.7 AC#3
>   互動清單能配對出「唐↔阿拔斯」這組真正跨文明的互動）。**爭議點**：怛羅斯戰俘傳播
>   造紙術入伊斯蘭世界之說——通俗敘事 vs. 現代史學界對「戰俘傳播是否為唯一途徑」的
>   保留態度，跟赤壁之戰的曹操兵力爭議同一個「真實存在的史學爭議，非虛構案例」原則。
> - 全部新增內容（政權/代稱/事件）都補了英文翻譯，維持既有雙語慣例。
> - **`TimelineState` 拉桿上限從 300 延伸到 950**（`app/src/app/core/time/timeline-
>   state.ts`），189-618 年之間刻意留白，不是 bug；PRD §12 對應的 M4 TODO（拉桿精度
>   隨史料密度調整）已更新記錄這次延伸，維持原本「現在還不是真痛點」的判斷。
>
> 已用 `dotnet build`（clean）、`ng build`（clean）、`ng test`（206/206，`time-
> scrubber.spec.ts` 一處寫死 1-300 的註解改成不寫死具體數字）、truncate+reseed 過
> `app_postgres`、`docker compose up -d --build backend frontend`＋curl 對真實容器
> 驗證：8 筆政權（原 5 筆三國＋新 3 筆）、白衣/黑衣大食代稱正確掛在唐視角下（含
> `?locale=en` 翻譯）、year=700 疆域正確回傳唐+伍麥亞（有重疊）、year=800 正確回傳
> 唐+阿拔斯（不重疊，伍麥亞已消失）、`GET /regimes/:唐/events?year=751` 正確配對出
> 唐↔阿拔斯的怛羅斯之戰互動、事件詳情正確回傳巢狀 `sections`。`GET /events/:id/
> controversies` 端點本身還沒做（task 2.13 尚未動工，屬於既有缺口，不是這次新增的
> 問題）——爭議點資料已經正確寫進資料庫，只是目前沒有 API 能查回來，跟赤壁之戰/漢禪
> 魏那兩筆既有爭議點資料狀態一致
| [x] | 3.9 | 政權狀態轉換視覺呈現（分裂/禪讓/滅亡三種視覺區分） | Story 4 完整流程 | Story 4 | 1 個 |

> **2026-08-30 完成**（Story 4，使用者確認做完 Story 5 後接著做，依先前分析的
> 「Story5→4→3」優先順序，見 3.7 前後的討論）：
>
> **AC#1（分裂年份同時顯示多個新政權疆域）驗證後確認已滿足，不用新增程式碼**——
> task 3.6 的形變動畫本來就用 `morphRole: 'entering'/'leaving'` 處理「這個年份疆域
> 列數量變多/變少」的情況（新政權淡入、不強行插值，見 3.6 說明），一對多的分裂情況
> 跟「政權被取代/滅亡」這種一對一在資料結構上沒有差異，同一套機制已經涵蓋。**用真實
> 容器 curl 逐年驗證確認實際發生的年份**（先前以為是 220/221 年漢→魏那個轉折點，
> 實際查證後發現那其實是 1:1 替換，見下方更正）：year=200 只有「漢」一筆；
> year=208（劉備/孫權崛起，見 3.5 的種子資料說明）一次新增「蜀漢」跟「吳」兩個政權
> （含爭議期間各自的核心區+爭議區共 4 筆新疆域，加上漢原本那 1 筆共 5 筆），才是
> 真正「一個政權在畫面上同時多出好幾個新政權疆域」的分裂時刻；220 年的漢→魏是單一
> 政權對單一政權的禪讓替換（entering×leaving 一對一配對，跟 AC#2 的「終止方式」相關，
> 不是 AC#1 講的「分裂」）。
>
> **AC#2（禪讓／滅亡視覺區分，本任務主要工作）**：憲法原話「取代跟消滅應該是兩種不同
> 的定義」——新增純函式模組 `app/src/app/core/regime/regime-transition-display.ts`
> （`describeRegimeOrigin()`/`describeRegimeEnd()`），把 `RegimeStatus` 狀態機
> （`api/Domain/RegimeStatus.cs`，前端對照 `regime-status.enum.ts`）轉成中文敘述＋
> `sanring-tag` 的固定語意 `variant`：`succeeded`（禪讓）用 `default`、`conquered`
> （被滅亡）用 `destructive`（紅），兩者視覺上一定不同色，不可能混淆；`split`（分裂）
> 用 `secondary`；`active`（仍存續）不顯示終止 Tag。**動工前先解決了 destroyedByRegimeId
> 語意的疑點**（見 3.9 動工前的 grep 記錄）：這個欄位依 PRD §6 只在 `conquered` 時
> 填值，`succeeded` 時後繼者要反查 `predecessorRegimeId`，不是資料缺口。**`RegimeDirectoryService`
> 從只有 `{id, selfName}` 擴充成完整欄位**（`status`/`predecessorRegimeId`/
> `originTransitionType`/`destroyedByRegimeId`），新增 `regimeOf()`/`successorOf()`/
> `splitChildrenOf()` 三個查詢方法——後兩個是反查方法，跟 `EventsController.
> GetInteractionsByRegime()` 反查政權轉換事件另一方同一個模式（後端也沒有另外存一份
> 反向關係表）。`RegimeFocusPanelComponent` 標題下方新增「起源／終止」兩個 Tag
> （`originDescription`/`endDescription` 兩個 computed，見元件文件說明）。
>
> **AC#3（未指定史觀時顯示預設主線）**：task 2.8 的 `GET /lineage-presets`＋
> `GET /lineage-presets/:id/regimes` 這次才真正接上前端——新增
> `app/src/app/core/regime/default-lineage.service.ts`（`DefaultLineageService`，
> `shareReplay(1)` 快取，`switchMap` 串接兩個請求：先查出 `isDefault===true` 的
> preset，再查它的政權序列）跟 `app/src/app/lineage-sequence/`
> （`LineageSequenceComponent`，箭頭串接的 `sanring-tag` 顯示「傳統教科書史觀主線：
> 漢→魏→晉」），掛在 `App` 的 header，跟標題並排靠右。**刻意只顯示這一條預設序列，不做
> 史觀切換 UI**——AC#3 原文只要求「未指定特定史觀時」顯示預設主線，沒有要求切換功能，
> 蜀漢/東吳等分裂期政權仍可在地圖上點擊聚焦查看，只是不在這條主線序列裡，這是 PRD §6
> 「方案 D」本來就拍板的設計。
>
> 已用 `dotnet build`（clean）、`ng build`（clean，budget 內，esbuild `--charset=ascii`
> escape 過的中文字串已用 `\uXXXX` 形式比對確認新程式碼真的在部署的 bundle 裡，不是
> 憑「應該有」猜測）、`ng test`（188/188，新增 19 條：`regime-transition-display.spec.ts`
> 窮舉四種狀態的文字/variant、`regime-directory.service.spec.ts` 補上
> `regimeOf()`/`successorOf()`/`splitChildrenOf()`、`regime-focus-panel.spec.ts`
> 新增「任務 3.9 AC#2」區塊驗證漢/魏/蜀漢/晉四種狀態的 Tag 文字與 variant class、
> `default-lineage.service.spec.ts`/`lineage-sequence.spec.ts` 涵蓋主線序列載入/
> 查無預設 preset 時的空狀態）、`docker compose up -d --build backend frontend`＋curl
> 對真實容器驗證 `/api/v1/regimes`（漢/魏/蜀漢/吳/晉五筆狀態機欄位皆正確）跟
> `/api/v1/lineage-presets/:id/regimes`（漢→魏→晉，`sortOrder` 1/2/3）。
| [x] | 3.10 | EDTF 精度/不確定性 UI 標示（模糊年份提示） | Story 5 完整流程 | Story 5 | 1 個 |

> **2026-08-30 完成**（使用者確認三個 Story 裡優先做這個，理由：唯一沒有後端阻塞的
> ——`historical_events.start_edtf`/`end_edtf` 這個原始字串 task 2.10 早就整包回傳
> 了，不像 Story 3/4 各自卡在 2.9a 的受控值決策/2.8 端點還沒做）：
>
> **AC#3（模糊區間查詢）驗證後確認已經滿足，不用新增程式碼**：`GET /events?year=`
> 的區間比對（`start_decimal < year+1 AND end_decimal >= year`）本來就不管日期本身
> 精不精確、有沒有 `?`/`~` 標記，只看換算出來的 decimal 數值有沒有落在查詢年份的整年
> 區間裡——用真實容器 POST 一筆帶 `?` 標記的事件（`"1046?"`）、`GET year=1046` 驗證
> 確實能查到，`GET /events/:id` 驗證原始字串的 `?` 標記完整往返不遺失。
>
> **AC#1/AC#2 是這個任務真正要做的**：新增 `app/src/app/core/time/edtf-display.ts`
> （純函式，`parseEdtf()`/`formatEdtfDateLabel()`/`formatEdtfQualifierLabel()`）——
> **語法解析規則刻意跟後端 `EdtfService.TryParse()` 用同一個子集**（`-?YYYY(-MM(-DD)?)?`
> 加選用尾綴 `?`/`~`），不支援完整 EDTF 規格的世紀/年代/季節語法（後端本來就沒實作）；
> 這裡只做「解析成顯示用的結構」，不重做曆法驗證（月份 1-12、日期依月份/閏年正確範圍
> 這些交給後端 `NodaTime` 驗證過才寫進資料庫，前端不重複驗證一次，見 `edtf-display.ts`
> 的說明）。新增 `EdtfDateComponent`（`app/src/app/edtf-date/`）呈現：**AC#1** 只顯示
> 史料實際記載到的精度（年精度就只到年，不會因為後端內部把月/日補成 1 月 1 日就跟著
> 偽造出更精確的假象），精度層級靠「顯示到哪一級」本身表達，不另外疊加文字說明；
> **AC#2** `?`/`~` 標記轉成「推測年份」/「約略年份」提示，用獨立的 `<span>` 包起來、
> 顏色比主要日期淡，跟確定的日期在視覺上分開。
>
> **後端小擴充**：`GET /regimes/:id/events`（task 3.7 AC#3 用的互動查詢端點）原本只回
> `startDecimal`/`endDecimal`（純數字），這次追加 `startEdtf`/`endEdtf` 兩個原始字串
> 欄位——decimal 換算過程本身就會把精度層級跟不確定標記這些資訊丟失，UI 要呈現這些
> 資訊只能從原始字串取得，沒有其他資料來源。
>
> **實際接上的畫面**：task 3.7 的政權聚焦面板「互動記錄」清單，每筆離散事件下方多一行
> 起訖日期（`<app-edtf-date>`，起訖相同時只顯示一個，不同時顯示成範圍）——目前唯一有
> 事件資料觸及到使用者畫面的地方，沒有為了展示這個功能另外生一個孤立的頁面。
>
> 已用 `dotnet build`（clean）、`ng build`（1.51MB/339KB，budget 內）、`ng test`
> （165/165，新增 25 條：`edtf-display.spec.ts` 涵蓋年/月/日精度、`?`/`~` 標記、負
> 年份、無法解析的 fallback；`edtf-date.spec.ts` 涵蓋元件渲染跟 qualifier 獨立 span；
> 面板既有測試補上 `startEdtf`/`endEdtf` 欄位跟一則日期顯示斷言）、真實容器 curl 驗證
> AC#3、`docker compose up -d --build backend frontend` 部署驗證。
| [ ] | 3.11 | reign_eras 年號標籤顯示（對應時間拉桿位置顯示年號） | UI 顯示「貞觀元年」等 | §5 紀年轉換 | 1 個 |
| [ ] | 3.12 | 事件詳情抽屜（毛玻璃 + 三層手風琴） | notes §八互動草圖落地 | §8 | 1 個 |
| [ ] | 3.13 | 多重視角分頁（Perspective Tabs） | notes §十互動草圖落地 | §8、Story 3 | 1 個 |
| [ ] | 3.14 | 四態齊備（loading/empty/error/success，依 §8 逐頁核對） | 每個主要頁面四態都有畫面 | §8 | 1 個 |
| [ ] | 3.14a | API 訊息代碼對照字典 | 對應後端 `api/Contracts/ApiMessageCodes.cs`（task 2.0 修訂，2026-08-29）：`ApiResponse.message` 回傳的是穩定代碼（如 `YEAR_REQUIRED`）不是中文句子，前端要有一個集中的 `message-codes.ts`（或同等檔案）把代碼對照成顯示文字，不能讓各元件各自寫 `if (message === 'XXX')` 散落各處。現階段只需要中文一種語言（多語系本身不是已拍板的產品目標，見 PRD §7），但字典結構要跟訊息代碼本身分離，之後真的要加語言不用重構呼叫端。新增代碼時要記得同步更新這份字典，避免前後端代碼集合漂移 | §7 task 2.0 | 1 個 |
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
