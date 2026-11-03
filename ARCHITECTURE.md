# World Line — 架構文件（ARCHITECTURE.md，草稿）

> **狀態：Tai 2026-11-03 20:54 回覆「依據建議」，已核准 D1–D6、D9（見 §8）。本文件是進度的唯一依據。只在 feature 分支 commit，未 push。**
> 版本：2026-11-03 20:52（台北時間 UTC+8）。這版接續 20:23 的初稿（`~/wl-drafts/ARCHITECTURE.md`），並依開發憲法改寫，沒有從頭重做。
> 盤點依據（皆唯讀）：
> - `.claude/constitutions/world-line.md`：業務憲法，status `in_review`，是唯一的需求依據
> - `.claude/prds/world-line-ww2.md`、`.claude/plans/world-line-ww2-plan.md`
> - 兩個 repo 的 `git log` 與目錄結構
> - 程式本身，包括 `backend/src/WorldLine.Api/Features/*Endpoints.cs` 和 `frontend/src/app/**`
> - 主管進度筆記 `STATUS.md`
>
> 文件分工：
> - 憲法：業務規則
> - PRD：規格
> - 本文件：模組怎麼切、資料怎麼流、前後端介面長什麼樣、現在做到哪裡
>
> 業務含義要改，先改憲法（憲法「維護方式」第 1、3 條）。結構有變，就同步更新本文件。
> 狀態標記：✅ 已完成（附 commit）｜🔧 未完成｜❓ 未決定（要 Tai 拍板，見 §8）

---

## 1. 系統總覽

### 1.1 元件

| 元件 | 位置 | 技術 |
|---|---|---|
| 前端 | `frontend/`（Angular 專案，程式在 `frontend/src/app`） | Angular 22、TypeScript、Tailwind 4、sanring UI（`components/ui`）、MapLibre GL JS、Vitest、Playwright |
| API | `backend/`（`WorldLine.slnx`；`src/WorldLine.Api`、`src/WorldLine.Contracts`、`tests/WorldLine.Api.Tests`） | .NET 10 Minimal API、EF Core 10＋Npgsql＋NetTopologySuite；OpenAPI 輸出到 `backend/openapi/v1.json`，前端用 `gen:api` 產生 `core/api-schema.ts` |
| 資料庫 | Docker | PostgreSQL 18＋PostGIS 3.6（`postgis/postgis:18-3.6`，Apple Silicon 上以 amd64 模擬） |
| Redis | **目前沒有** | PRD §5 明定第一階段不加 Redis，compose 裡也沒有。觸發條件見 PRD §11。快取目前做在 API 的 `DateIntervalCache` 與前端 `core/atlas-data` |
| 部署 | `compose.yaml`（專案名 `worldline-ww2`） | 只有 `postgres` 和 `api` 兩個服務，`web` 還沒加進來。埠只綁 127.0.0.1 |

> 註：任務說明寫的 `app/`、`api/` 和實際目錄不同，實際是 `frontend/`、`backend/`。

### 1.2 環境與連接埠

| 埠 | 用途 | 對應 | 規則 |
|---|---|---|---|
| 4200 | `ng serve` 預設埠 | `proxy.conf.json` → 5051 | 開發分支驗收不用這個埠 |
| 4201 | `feature/russia-unclip-loading` 的 `ng serve` | `proxy.borders-dev.json` → 5052 | 驗收截圖和 e2e 都用這個埠（`WL_E2E_BORDERS=1 WL_E2E_PORT=4201`） |
| 5052 | 開發 API | 開發庫 `worldline-borders-dev-db`（127.0.0.1:5442） | 寫入前先備份並 dry-run，只寫 verified 資料 |
| **5051** | **正式 API 容器 `worldline-ww2-api-1`** | **正式庫 `appdb_ww2`（`worldline-ww2-postgres-1`，127.0.0.1:5432）** | **不碰。Tai 說「可以同步」之後才同步** |

### 1.3 Repo 與分支

- `~/01_Projects/world_line`：目前在 `develop`。`main` 和 `develop` 都指向 `4842636`，兩者相同。
- `~/01_Projects/world_line_russia`：worktree，分支 `feature/russia-unclip-loading`。
  - 比 `develop` 多 72 個 commit，都沒有 push。
  - `stash@{0}`（wl-occl-fix2-html）是舊的 HTML 碰撞修補，**不採用**。
  - 有一個未追蹤檔 `frontend/e2e/accept-visual.e2e.ts`。
- 開發流程：Claude Code 經 mac-mini `~/cc-queue`（`start.sh`、`status.sh`）執行。同一個 repo 一次只跑一個佇列。

---

## 2. 資料流

```
史料（地圖集／年鑑／官方紀錄；R7）
  → 資料建置檔（data/seed/**，含 verified／待查證，依時期拆段，I1、I6）
  → 主管驗收 → 備份 → dry-run → 只送 verified
  → POST /api/v1/*（X-API-Key；寫入層強制 I1/I2/I4/I6；更正 = /{id}/retraction + 新紀錄，I5）
  → PostgreSQL/PostGIS（版本化、保留撤回時間與原因）
  → GET /api/v1/…?date=YYYY-MM-DD（後端 DateIntervalCache；幾何依 zoom 簡化、座標 5 位小數）
  → frontend core/api/world-line-api.ts（統一回應 { statusCode, message, data }）
  → core/atlas-data.ts（依 /timeline/change-points 做區間快取、LRU、預載前後區間）
  → core/atlas-state.ts（date、axis、focus、lang 等狀態，同步到 URL）
  → shared/map/atlas-map.ts（GeoJSON source → MapLibre fill／line／symbol layer；HTML 疊層：聚焦蒙版、交戰弧線、掃描亮線）
    ＋ shared/sovereignty-card（右側面板）＋ shared/timeline（底部）
```

### 2.1 前端實際呼叫的讀取端點（`core/api/world-line-api.ts`）

| 端點 | 前端用途 |
|---|---|
| `GET /sovereignty?date=&zoom=` | 主權多邊形（地圖底色、國名標籤來源、聚焦蒙版要留出的輪廓） |
| `GET /control?date=` | 實際控制區、佔領、控制資料缺備註、戰區快照狀態 |
| `GET /conflicts?date=` | 交戰關係（弧線從首都出發） |
| `GET /capitals?date=` | 首都點（`capital-dot`／`capital-label`） |
| `GET /leaders?date=`、`GET /leader-bios/{id}` | 右側面板「領導人」分頁、生平展開 |
| `GET /regimes`（batch）、`GET /regimes/{id}` | 政權名稱與詳情 |
| `GET /regimes/{id}/events` | 右側面板「事件」分頁 |
| `GET /sources/{id}` | 來源 popover |
| `GET /timeline/extent`、`/timeline/snapshots`、`/timeline/change-points` | 時間軸範圍、快照標記、快取區間 |
| `GET /healthz` | 健康檢查 |

後端另有兩個讀取端點，前端目前沒用：`GET /events/{id}`、`GET /regimes/{id}/interactions`。後端還有一個 `GET /regimes/{id}/alignments`。

### 2.2 寫入端點（需要 `X-API-Key`，只給開發者用）

- **新增**：
  - `POST /sources`、`/regimes`、`/regime-relations`、`/regimes/{id}/alignments`
  - `/theaters`、`/control-snapshots`、`/control-records`、`/control-coverage-notes`
  - `/sovereignty-records`、`/occupation-attributions`、`/conflict-records`、`/capital-records`
  - `/leader-records`、`/leader-bios`、`/events`、`/events/{id}/participants`
- **撤回**：
  - `POST …/{id}/retraction`，適用 control-records、control-coverage-notes、sovereignty-records、occupation-attributions、conflict-records、capital-records、events
  - `POST /regimes/{id}/alignments/{alignmentId}/retraction`
- **沒有任何 DELETE 端點**（I5）。

> PRD §7 列了但還沒實作的端點：`/control/gaps`、`/sovereignty/at`、`/frontlines`、`/regimes/{id}/status`、`/events?from=&to=`、`/controversies`、`/places`、`/eras`、`/…/versions`、`/revisions`、`/imports/geojson?dryRun=`。這些屬於 PRD 原里程碑，不在本文件 M1–M4 的範圍。

### 2.3 日期規則（共用）

- 區間為半開區間，結束日不含當天。
- 第一階段範圍是 1908-01-01～1945-09-30。
- 條約以生效日為準，簽署日寫在備註。
- 佔領是疊在原政權上的控制區。

---

## 3. 模組劃分（從程式實際盤點）

### 3.1 前端

| 模組 | 職責 | 主要檔案 | 介面（輸入 → 輸出） |
|---|---|---|---|
| API client | 呼叫 `/api/v1`、拆 envelope | `core/api/world-line-api.ts`、`core/api/api-types.ts`、`core/api-schema.ts`（產生檔） | 日期／id → DTO |
| 資料與快取 | 依日期取主權、控制、衝突、首都、領導人；change-point 區間快取、LRU、預載 | `core/atlas-data.ts`、`core/change-points.ts` | `date`（signal）→ 各圖層資料 signal＋載入狀態 |
| 全域狀態 | date、axis、focus、lang、legendOpen，同步 URL | `core/atlas-state.ts` | signals |
| 共用工具 | 日期、雙語、政權名稱、引用縮寫、動畫時長 | `core/dates.ts`、`i18n.ts`、`regime-names.ts`、`citation-short.ts`、`motion.ts`、`theater-tracks.ts` | 純函式 |
| 主頁 | 組合地圖、面板、時間軸、tooltip、載入蒙版 | `pages/atlas/atlas.page.ts` | 接各元件的 input／output |
| **地圖** | MapLibre 初始化、底圖、主權／控制 fill 與 line、斜線網底、選取外框、鏡頭（扣掉面板的 padding） | `shared/map/atlas-map.ts`、`map-style.ts`、`sovereignty-style.ts`、`hatch.ts` | 輸入：各圖層 GeoJSON、axis、focusedRecord。輸出：`featureClick`、`sovereigntyClick`、`gapClick`、`emptyClick`、`featureHover`、`userMove` |
| **標籤** | 國名 `regime-label`、首都 `capital-dot`／`capital-label`（MapLibre symbol layer）；浮動 UI 障礙物 `regime-label-obstacles`；排序鍵、短名、面積、字寬量測 | `atlas-map.ts`（圖層定義、`regimeLabelSortKey`、`shortRegimeText`、`regimeLabelArea`）、`label-placement.ts`（`uiObstacleBoxes`、`pickCapitalAnchorSide`、`measureLabelWidth`） | 輸入：label features。輸出：GL 畫面；可用 `queryRenderedFeatures` 讀已顯示的標籤 |
| **聚焦蒙版** | 選取政權時，其他地方蓋一層半透明紙色並模糊；被選政權的輪廓用 `clip-path: path(evenodd, …)` 排除；同時算鏡頭 padding | `shared/map/focus.ts`（`focusMaskPath`、`polygonRings`、`geometryBounds`、`focusPadding`）＋`atlas-map.ts` 的 `#focusMask`（**HTML 層，在 MapLibre canvas 之上**） | 輸入：`focusedRecord` 的幾何 |
| 交戰弧線 | 首都到首都的弧線與雙劍圖示（HTML／SVG 疊層） | `shared/map/conflict-arc.ts`、`shared/conflict-card` | 輸入 conflicts，輸出 `conflictClick` |
| **掃描動畫** | 跳年時把舊圖快照蓋在新圖上，亮線由左往右露出新年份 | `shared/map/scan-reveal.ts`、`scan-snapshot.ts` | 輸入：舊 canvas 快照與 phase（idle／waiting／sweeping） |
| **右側面板** | 政權或控制區詳情，分頁 `overview`、`events`、`leaders` | `shared/regime-sheet/regime-sheet.ts`（sheet 外殼）、`shared/sovereignty-card/sovereignty-card.ts`、`feature-card`、`gap-card` | 輸入：選取的 props、regimeEvents、leaders、capital、`loadBio`。輸出：`tabChange`、`conflictSelect`、`eventJump` |
| **領導人與生平** | 領導人任期清單；只有帶有效生平的名字可以點，點了展開生平 | `sovereignty-card.ts`（Leaders 分頁）＋API `leaders`、`leader-bios` | `loadBio(id)` → `LeaderBio` |
| **事件** | 政權事件清單、事件連結（跳日期） | `sovereignty-card.ts`（Events 分頁）、`shared/event-ref` | `eventJump(date)` |
| **時間軸** | 拖拉桿、播放（速度可切週或月）、日期輸入、快照標記；目前有五條戰區軌道和「資料不完整」區塊 | `shared/timeline/timeline.ts`、`timeline-scale.ts` | 輸入：date、snapshots、ready。輸出：`dateChange`、`playingChange`、`invalidInput`、`retry` |
| 圖例、推估提示、來源 | 圖例（也是標籤障礙物）、推估 chip、來源 popover | `shared/legend`、`shared/interp-chip`、`shared/citation` | — |
| 版面 | app shell、頂部列 | `layout/app-shell`、`layout/top-bar` | — |

### 3.2 後端（`backend/src/WorldLine.Api`）

| 模組（`Features/*Endpoints.cs`） | 職責 | 主要資料 |
|---|---|---|
| Sources | 史料來源（R7、I6） | sources |
| Regimes／RegimeRelations／RegimeAlignments | 政權本體、自稱與他稱（I2、I4）、關係與互動（R3）、陣營（§6） | regimes、regime_names、regime_relations、regime_alignments |
| Sovereignty／Occupations | 主權主張（R6）、佔領歸屬 | sovereignty records＋citations、occupation_attributions |
| Control／ControlCoverageNotes／Theaters | 實際控制、控制資料缺備註（R9）、戰區與快照 | control_records、control_coverage_notes、theaters、control_snapshots |
| Conflicts／Events | 交戰、事件與參與方 | conflict_records、events、event_participants |
| Capitals | 首都（依期間） | capital_records |
| Leaders | 元首或首腦任期、生平 | leader_records、leader_bios |
| Timeline | extent、snapshots、change-points | 由各表推導 |

- **共用**：`Common/ApiKeyFilter`、`DateIntervalCache`、`ApiExceptionHandler`、`Mapping`。
- **領域**：`Domain/CitationPolicy`（I6）、`Entities`、`Vocabulary`。
- **基礎設施**：`Infrastructure/WorldLineDbContext`、`DbSetup`，以及 migration。
- **測試**：`tests/WorldLine.Api.Tests`，用 Testcontainers 起 PostGIS，seed 批次各有測試。

---

## 4. 地圖圖層規則（Tai 2026-11-03 20:54 確認）

> Tai 回覆「依據建議」確認本節規則，做法見 D2、D9。
> 所有規則對任何政權一體適用，**零國家特例**：程式裡不能出現國家 id、名稱、日期或座標的特殊處理。

### 4.1 圖層順序（由下到上）

1. 底圖：海、陸地、海岸線
2. 疆界面：主權和控制的 fill、line、斜線網底
3. 一般標籤：國名、首都，日後加上行政區名
4. 虛化蒙版：只在選取政權時出現
5. 選取政權標籤
6. 浮動 UI：圖例、右側面板、時間軸

### 4.2 規則

- **(a) 虛化蒙版**
  - 只在選取了政權時出現；沒選取時，地圖完全不虛化。
  - 蒙版不遮蓋被選取政權的輪廓，輪廓內保持清楚。
  - 取消選取時蒙版淡出。
- **(b) 被選取政權的名字**
  - 國名和首都放在蒙版之上，一定顯示。日後該政權的一級行政區名也放這層。
  - 一般標籤層不再重複畫它的國名和首都。
  - 其他標籤撞到它時，由其他標籤讓開。
- **(c) 其他名字（一般標籤）**，照主流地圖的做法：
  1. **依國土面積自動決定最小顯示縮放**：國土在目前縮放下裝不下名字，就不顯示；放大到裝得下才出現。門檻由面積和字寬自動算，不逐國設定。
  2. **碰撞交給 MapLibre**：`text-allow-overlap=false`，用 `symbol-sort-key` 依面積排重要度，撞到時保留重要的，另一個隱藏。
  3. **圖例和右側面板當障礙物**：標籤自動避開。
  4. 不為了硬塞名字而縮字、換行或縮寫；首都標籤沿用同一套規則。
  5. **國名依視窗定位（M1-g，Tai 2026-11-03 21:27 核准，精神依 Imhof）**：
     - 國名放在該政權「目前畫面可見國土」中面積最大的那一塊（多塊國土、殖民地一律同規則）。
     - 「可見」指地圖畫面扣掉圖例與右側面板之後的範圍。
     - 位置用 polylabel（pole of inaccessibility）：該可見塊內離邊界最遠的點。
     - 視窗移動（moveend）就重算。
     - 可見塊的螢幕寬度裝不下名字就不顯示（沿用 label-fit 門檻）。
     - 被選取政權例外：一定顯示，同樣用可見塊定位。
     - 零國家特例：既有的手動標籤點覆寫（`LABEL_OVERRIDES`，西藏）一併移除。

### 4.3 驗收（對照規則，不對照國家清單）

- 抽 4 個日期（1924-06-15、1930-06-15、1940-06-15、1945-06-15），各截縮放 3 和 4.7 兩張圖。
- 每個日期另選一個政權，截一張選取狀態的圖。
- 截圖裡不能有：互相重疊的名字、被圖例或面板蓋住的名字、被蒙版蓋住的選取政權名字或輪廓。
- 名字因為裝不下而隱藏，**不算失敗**。
- 選取政權的國名、首都和輪廓要清楚（不被蒙版模糊）。

### 4.4 現況和規則的差距（盤點發現）

| 規則 | 現況 | 差距 |
|---|---|---|
| (a) | 已有：`atlas-map.ts` 的 `#focusMask` 是 HTML 層，用 `backdrop-blur` 加 evenodd `clip-path` 排除被選政權的環（Tai 2026-10-31 起） | 大致符合，要驗證蒙版只在選取時出現 |
| (b) | 標籤畫在 MapLibre canvas 裡，而蒙版是蓋在 canvas 上的 HTML 層。被選政權的名字只要超出它的輪廓，就會被模糊 | **未做**。做法要決定，見 §8 D2 |
| (c)-1 | `regime-label` 沒有依面積設的最小縮放；首都 `capital-label` 是固定 `minzoom: 3.5` | **未做** |
| (c)-2 | ✅ `8da6c22`（symbol layer、sort-key、障礙物） | 符合 |
| (c)-3 | ✅ `8da6c22`（`regime-label-obstacles`） | 符合 |
| (c)-4 | `844daaf` 加了依面積縮字、換行、短名、8 個錨點；`3a7fadf` 讓「大、中型國名被隱藏」直接判失敗 | **和新規則衝突**，見 §8 D1 |

---

## 5. 里程碑 → 模組

### M1 標籤與遮擋

| 模組 | 內容 | 狀態 |
|---|---|---|
| M1-a symbol layer | 國名和首都改用 MapLibre symbol layer，加上 sort-key、variable anchor、UI 障礙物 | ✅ `8da6c22` |
| M1-b 掃描改讀已渲染標籤 | e2e 改用 `queryRenderedFeatures` 計算 | ✅ `de039e2` |
| M1-c 大、中型國名被隱藏算失敗 | 收緊 e2e 判定 | ↩️ `3a7fadf` 依 D1 撤回（revert `ac55f48`） |
| M1-d 縮字、換行、短名、多錨點 | 和規則 (c)-4 衝突 | ↩️ `844daaf` 依 D1 撤回（revert `d58bef6`） |
| M1-e 名字寬度對比國家螢幕寬度決定顯示 | 規則 (c)-1，門檻依 D9：`label-fit.ts` 算最小縮放，寫在 GL filter（`['zoom']` 依圖磚整數縮放評估，所以門檻是保守的：裝得下才顯示，最多晚不到 1 級出現）；首都同門檻；障礙格改 24px 鋪滿 | ✅ `74b5d93` `1cdffff` |
| M1-f 選取政權標籤在蒙版之上 | 規則 (b)，HTML 層 `map-selected-labels`（D2）；一般層同政權國名、首都、圓點用 filter 排除；HTML 框加入障礙格 | ✅ `74b5d93` |
| M1-g 國名依視窗定位 | 規則 (c)-5 | ✅ 3428329（快驗：/workspace/wl-sym-quick2；熱跳 ready 中位 537ms，c4dfca3 為 800ms） |
| M1-h 驗收 | 依 §4.3 抽 4 個日期：2026-11-03 21:16 快速驗收完成（截圖 box `/workspace/wl-sym-quick/`）；合併前夜間背景跑一次 56 個日期的完整掃描 | 🔧 夜間掃描未跑 |
| （不採用） | 舊 HTML 碰撞修補 `684224c` `7f3729b` `402cd53` `51f637d` `02aca83` 已被 symbol layer 取代；未 commit 的部分在 `stash@{0}` | — |

### M2 把已驗收的功能合併到 main

| 模組 | 內容 | 狀態 |
|---|---|---|
| M2-a 領導人分頁與生平 | `3eb2162` `3782293` `24b0595` `41c294a` `addbcfc` `459d37e` `da87b15` `ec7e7f8` `efe0767`；seed `1ea2875` `daaa730` `668095f` `e1bd309` `1f0a193` | ✅ 已驗收，🔧 還沒合併 |
| M2-b 右側面板 | `c6aa304` `e45b44e` `c713ff0` `4f11eec` | ✅ 已驗收，🔧 還沒合併 |
| M2-c 掃描亮線 | `06023c2` `b6ace56` `67df45c` `a87f357` `3907961` `d3b59e5` `c4dfca3` | ✅ 已驗收，🔧 還沒合併 |
| M2-d 合併 | 依 D3：M1 夜間完整掃描通過後整條分支併 main 並回報 commit 清單與測試結果 | 🔧 等 M1 |

### M3 介面

| 模組 | 內容 | 狀態 |
|---|---|---|
| M3-a 時間軸方案 A（Tai 16:35 選定） | 見下方細節；PRD §8.3 已同步（D6） | 🔧 未開始 |
| M3-b 生平點擊提示 | 有生平的人名加 chevron 箭頭、hover 狀態和灰字「點擊查看生平」；沒有生平的不加。可點的判斷已有：`ec7e7f8` | 🔧 未開始 |
| M3-c 戰役標籤和彈窗 | 「事件」分頁中屬於戰役的事件加「戰役」標籤，點了開彈窗；彈窗不是全螢幕，也不會自己跳出。事件的起訖日只存在資料裡（events 已有 `occurred` 區間），不畫在時間軸上。原型：1939 波蘭戰役，含蘇聯 9/17 入侵 | 🔧 未開始 ❓ D7 |

M3-a 時間軸方案 A 的細節：
- 單行，高約 48px，依序是播放鍵、日期按鈕、全寬滑桿、「⋯」選單。
- 速度放進選單，預設每秒 1 週。
- 刻度：每 5 年一個文字刻度，每年一個小點。
- 「資料不完整」改成日期旁的 ⓘ，加上首次造訪時出現一次的 toast。
- 鍵盤：空白鍵播放，←／→ 移一週，Shift＋←／→ 移一年。
- 拿掉五條戰區軌道（`theater-tracks`）和事件色帶。

### M4 資料（只寫開發庫 5052／5442）

| 模組 | 內容 | 狀態 |
|---|---|---|
| M4-a 德國任期修正 | 照 I5 撤回後重寫，事前備份並 dry-run | 🔧 未寫庫。筆數有出入 ❓ D8 |
| M4-b 各洲政權 seed 寫庫 | 每批先備份、dry-run，只寫 verified；待查證的留在 seed 檔 | 🔧 未寫庫 |
| M4-c 一級行政區 | 排在全球國家補全之後；資料來源 OpenHistoricalMap（CC0，D4、憲法 §10），CHGIS、NHGIS、MPIDR 只用來對照考證；名稱套用 §4 規則 | 🔧 未開始 |
| M4-d 只重掃疆界有變動的年份 | 資料寫庫後，只對受影響的 change-point 年份跑標籤掃描（腳本已支援 `WL_SWEEP_DATES`） | 🔧 未開始 |

### 5.1 對照原計畫

PRD §10 與計畫檔的 M0–M6、S 軌（戰區與全球主權骨架）是另一套編號。本文件的 M1–M4 是現階段的工程主線。

- M0 骨架其實已經完成，部分成果已在 develop（`ff9f00e`、`4842636`）。
- 計畫檔的核取方塊和 README 的「目前狀態」已依 D5 同步。

---

## 6. 開發流程（照開發憲法）

每件事都走這 6 步。前一步沒過，就不進下一步。

1. **定規則**：寫成通用規則，不寫程式，給 Tai 確認。
2. **寫進本文件**：標明屬於哪個里程碑和模組。結構有變，就同步更新本文件。
3. **拆小步驟並答三題**：做過了嗎？會不會跟其他模組衝突？怎麼驗收？
   - 三題都答得出來才派工；答不出來就停下來，一次問 Tai。
   - 主管只負責里程碑和模組兩層，只有小步驟才進 `~/cc-queue`，每一步都標明對應哪個里程碑和模組。
4. **開發**：`~/cc-queue` 由 Claude Code 執行，在 feature 分支 commit，不 push。
5. **快速驗收**：跑單元測試（`ng test`、`dotnet test`），再抽 4 個日期截圖，對照第 1 步的規則看有沒有違反。
   - 不做逐日期的大掃描。
   - 有新資料時，只掃疆界有變動的年份。
6. **合併前**：夜間背景跑一次 56 個日期的完整掃描，通過才合併。

規則：
- 發現工作已經做過，或要推翻已確認的規則，就先停下來問 Tai，不自己重做。
- 回報只在完成、卡住或需要決策時發一次。

**需要 Tai 本人在聊天裡親口同意的事**（其他 bot 的轉述不算）：
- push 到遠端、合併到 main、部署
- 刪除檔案或資料
- 改系統設定、安裝全域套件
- 改 Tailscale 或 SSH 設定

另外：任何密鑰都不能印出或外洩，`.env` 不能進版控。

---

## 7. 資料規則（憲法 I1、I5、I6、§9）

1. **只寫 verified**：只有具正式出處的資料（欄位）能標 verified，也只有 verified 能寫入資料庫。待查證的留在 `data/seed/**`（I6）。
2. **部分核實依時期拆段**：出處只能支撐部分期間時，拆成多段（I1）。
3. **寫前備份加 dry-run**：每次寫庫前先備份開發庫，再 dry-run，確認之後才送出。
4. **更正用撤回重寫，不刪除**：撤回原紀錄（保留撤回時間與原因），再寫入新紀錄。不用 DELETE（I5）。
5. **條約用生效日**，簽署日寫在備註（§9）。
6. **範圍**：1908-01-01～1945-09-30（§1）。
7. **只寫開發庫**（5052／5442）。正式庫 `appdb_ww2`（5051）要等 Tai 說「可以同步」。

---

## 8. 決策與未決定事項

### 8.1 已拍板（Tai 2026-11-03 20:54「依據建議」）

| # | 決定 |
|---|---|
| D1 | 用新的 revert commit 撤回 `844daaf`（縮字、換行、短名、多錨點）與 `3a7fadf`（大、中型國名被隱藏判失敗），不改寫歷史 |
| D2 | 選取政權的國名與首都畫在蒙版之上的 HTML 層；蒙版維持 HTML＋模糊 |
| D3 | M1 夜間完整掃描通過後，整條分支一起併 main；在那之前不合併、不 push |
| D4 | 一級行政區資料來源採 OpenHistoricalMap（CC0），已寫進憲法 §10；其餘只對照考證 |
| D5 | 進度唯一依據是本文件；README「目前狀態」與計畫檔核取方塊同步更新 |
| D6 | PRD §8.3 依時間軸方案 A 改寫（已改） |
| D9 | 規則 (c) 的門檻：名字寬度對比該國螢幕寬度（可由面積推算最小顯示縮放）；首都用同一門檻 |

### 8.2 仍未決定

| # | 事項 | 選項／說明 |
|---|---|---|
| D7 | 戰役彈窗的內容範圍 | 階段數、地圖要不要動畫、粒度；「戰役」的判定是用 `event_kind=battle` 還是新增欄位 |
| D8 | 德國任期修正的筆數 | 任務說明寫 8 筆，之前的紀錄寫 9 筆任期不符。要以哪份清單為準？ |
| D10 | 掃描亮線和新標籤層的相容性 | `scan-snapshot.ts` 會複製 HTML 國名層，但國名已移進 canvas。要在合併前驗證跳年畫面沒有標籤殘影或缺漏 |
| D11 | 憲法 status 還是 `in_review`（計畫 A4） | Tai 審查後改成 `active`？ |
| D12 | 沿用既有的開放問題 | 主權軸資料集（憲法 §10、PRD Q0）；推估過渡插值方式（PRD Q3）；冷跳（目前決定維持現狀） |
