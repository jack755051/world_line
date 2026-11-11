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

- `~/01_Projects/world_line`：主工作樹，分支 `feature/russia-unclip-loading`（開發與 4201／5052 都在此）。
- 舊 worktree 路徑 `~/01_Projects/world_line_russia` 已不再使用；請改以 `~/01_Projects/world_line` 為準。
- `frontend/e2e/accept-visual.e2e.ts` 若存在且未追蹤，是本機視覺驗收草稿，不納入預設 e2e。
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
  5. ~~**國名依視窗定位（M1-g，Tai 2026-11-03 21:27 核准，精神依 Imhof）**~~ **已由新規則取代（D-B2，Tai 2026-11-04 12:41 修訂，見 §9）：每塊夠大的國土各預先算一個候選點，同一政權畫面上只顯示一個國名，被選政權依畫面可見部分重算。** 以下為舊規則「依畫面可見最大塊即時重算」，僅留存紀錄：
     - 國名放在該政權「目前畫面可見國土」中面積最大的那一塊（多塊國土、殖民地一律同規則）。
     - 「可見」指地圖畫面扣掉圖例與右側面板之後的範圍。
     - 位置用 polylabel（pole of inaccessibility）：該可見塊內離邊界最遠的點。
     - 視窗移動（moveend）就重算。
     - 可見塊的螢幕寬度裝不下名字就不顯示（沿用 label-fit 門檻）。
     - 被選取政權例外：一定顯示，同樣用可見塊定位。
     - 零國家特例：既有的手動標籤點覆寫（`LABEL_OVERRIDES`，西藏）一併移除。
  6. **名字不超出畫面（M1-i-A／B，2026-11-03 夜間全掃後補）**：
     - 畫面四邊外緣各加一列障礙（沿用 `regime-label-obstacles` 障礙層）：任何名字碰到畫面邊就和障礙相撞。
     - 首都名碰邊先翻到圓點另一側（`text-variable-anchor-offset`），兩側都不行就隱藏名字（圓點保留）。
     - 國名的視窗定位（5.）上下也限制在畫面內；名字框高度依實際換行行數計算（`text-max-width` 換成兩行就用兩行高）。
  7. **選取政權只顯示一個名字（M1-i-C）**：用 5. 的可見最大塊位置；同政權其他控制區名字不另外顯示；位置同樣避開圖例與面板、自己的首都名。

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
| M1-i 夜間全掃修正 | 規則 (c)-6、(c)-7：2026-11-03 第一次 56 日期全掃 282 項失敗（首都碰邊 220、國名碰上緣 55、選取政權多名重疊／被圖例蓋 7），結果 box `/workspace/wl-night/` | ✅ `df92876`（單元測試 251 全過）；🔧 第二次 56 日期全掃依 Tai 23:23 延後 |
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
| M3-a 時間軸方案 A（Tai 16:35 選定） | 見下方細節；PRD §8.3 已同步（D6） | ✅ 已完成 |
| M3-b 生平點擊提示 | 有生平的人名加 chevron 箭頭、hover 狀態和灰字「點擊查看生平」；沒有生平的不加。可點的判斷已有：`ec7e7f8` | 🔧 未開始 |
| M3-c 戰役標籤和彈窗 | 「事件」分頁中屬於戰役的事件加「戰役」標籤，點了開彈窗；彈窗不是全螢幕，也不會自己跳出。事件的起訖日只存在資料裡（events 已有 `occurred` 區間），不畫在時間軸上。原型：1939 波蘭戰役，含蘇聯 9/17 入侵。判定與呈現依 D7（已拍板）；資料欄位見 D13 | 🔧 未開始 |

M3-a 時間軸方案 A 的細節：
- 單行，高約 48px，依序是播放鍵、日期按鈕、全寬滑桿、「⋯」選單。
- 速度放進選單，預設每秒 1 週。
- 刻度：每 5 年一個文字刻度，每年一個小點。
- 「資料不完整」改成日期旁的 ⓘ，加上首次造訪時出現一次的 toast。
- 鍵盤：空白鍵播放，←／→ 移一週，Shift＋←／→ 移一年。
- 拿掉五條戰區軌道（`theater-tracks`）和事件色帶。

### M4 資料（只寫開發庫 5052／5442）

> **順序調整（Tai 2026-11-03 23:23）**：M1-i 修正 commit 後先停（不跑全掃、不合併、不再調任何國名位置），改做 M4：
> 1. M4-0 盤點：開發庫 1908-06-15 起每年年中的有效政權、有疆界、有首都、有領導人數；box `/workspace/wl-seed/` 與考證組已交付、未寫庫的檔案清單（先查是否已寫過，不重做）。
> 2. M4-a／M4-b 寫庫：只寫 verified；寫前 pg_dump、dry-run；更正撤回重寫；條約用生效日；對不上 regime_id 或有衝突的列待辦。德國任期以 v2 檔為準。
> 3. 驗收：寫庫前後每年統計對照；4201 抽 1908-06-15、1924-06-15、1940-06-15 世界視角截圖到 box `/workspace/wl-data1/`；列出疆界仍空白的地區與年份。

| 模組 | 內容 | 狀態 |
|---|---|---|
| M4-0 盤點 | 見上方順序 1 | ✅ 2026-11-03：每年統計前後對照在 box `/workspace/wl-data1/stats-compare.md`；寫庫前備份 `~/wl-backups/worldline_borders_dev-20261103-2331-pre-m4.dump` |
| M4-a 德國任期修正 | 照 I5 撤回後重寫，事前備份並 dry-run | ✅ v2 檔：10 條中 8 條撤回重寫（保留 personId），2 條不需改（GTC-06、GTC-10）。D8 筆數＝8 |
| M4-b 各洲政權 seed 寫庫 | 每批先備份、dry-run，只寫 verified；待查證的留在 seed 檔 | 🟡 領導人 leaders_batch2 v13 新寫 108 筆；首都 batch3–5 的 verified 先前已全部寫入；非洲 v20、美洲 v13、大洋洲 v16 全是待查證、沒有疆界，0 筆寫入。待辦：奧／匈分治政權、汪偽／武漢國府、國府行政院長鏈、人物小傳 batch2–4 與 germany_full v2 |
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
7. **只寫開發庫**（5052／5442）。正式庫 `appdb_ww2`（5051）要等 Tai 說「可以同步」。Tai 2026-11-03 23:53 已同意資料補好並驗收後同步，同步前備份與 dry-run（D14）。

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
| D7 | 戰役判定（Tai 2026-11-03 23:53，憲法 §6、Decision 4）：戰役必須同時符合三項：(1) 至少兩方有組織的武裝力量交戰；(2) 目的是奪取、守住或突破某個地點、防線或政權；(3) 有起訖日與交戰地區，且控制範圍或戰線有變動。例：盧溝橋事變、閃擊波蘭、陳橋兵變（軍隊奪權）都算；天安門事件不算，歸「政治事件」。短期戰役（淞滬會戰、敦克爾克）做大比例尺簡報圖：雙方戰線、進攻箭頭、據點，依階段播放（參考 Sudden Strike 簡報圖、liveuamap）；長期戰區拆成多個短期戰役 |
| D14 | 正式站同步（Tai 2026-11-03 23:53）：資料補好並驗收後同步正式站；同步前備份正式庫並 dry-run |
| D9 | 規則 (c) 的門檻：名字寬度對比該國螢幕寬度（可由面積推算最小顯示縮放）；首都用同一門檻 |

### 8.2 仍未決定

| # | 事項 | 選項／說明 |
|---|---|---|
| D13 | 戰役的資料欄位（提案，未決定，schema 未動） | (A) `events.event_kind` 新增 `battle`、政治事件用 `political`；(B) 新欄位（`is_battle` 或 `battle_scale`=short／theater）＋`parent_event_id` 把長期戰區掛到多個短期戰役；階段（戰線、箭頭、據點）另存子表。見憲法 §10 |
| D8 | 德國任期修正的筆數 | ✅ 已解：以 v2 檔為準，8 筆（2026-11-03） |
| D10 | 掃描亮線和新標籤層的相容性 | `scan-snapshot.ts` 會複製 HTML 國名層，但國名已移進 canvas。要在合併前驗證跳年畫面沒有標籤殘影或缺漏 |
| D11 | 憲法 status 還是 `in_review`（計畫 A4） | Tai 審查後改成 `active`？ |
| D12 | 沿用既有的開放問題 | 主權軸資料集（憲法 §10、PRD Q0）；推估過渡插值方式（PRD Q3）；冷跳（目前決定維持現狀） |

---

## 9. 疆界圖磚（第 2、3 層）

> 狀態：🟡 圖磚已設為預設（Tai 2026-11-04 18:46）：前端預設 tiles、production 只跑圖磚 `4ddf394` `0510cb2`；API 正式環境不預算 GeoJSON `e64e1ee`；開發環境 `?boundarySource=geojson` 備援保留。決策日期：2026-11-04。
> 決策：D-B1 採用預先切好的 PMTiles 加 CDN；D-B2 國名：每段時期「每塊夠大的國土」各預先算一個候選點（polylabel；帶起訖日、面積、span_x；只用面積門檻決定哪幾塊有點，不寫國家特例），碰撞交給 MapLibre（symbol-sort-key 面積大的先放），同一政權畫面上只顯示一個國名（前端在畫面內裝得下的候選點中只放行面積最大者），被選政權依畫面可見部分重算（Tai 2026-11-04 12:41 修訂）；D-B3 已定：Cloudflare R2 加 CDN（上線時開通，費用需要 Tai 本人同意），開發期由 Martin 在本地提供。

### 1. 目標
- 換日期（熱跳、播放，含 1 日/秒）時不發出網路請求，也不碰 API。
- API 常駐記憶體和疆界資料量脫鉤，不再預算世界快照。
- 可延伸到 1991 年。

### 2. 模組
| 模組 | 位置 | 職責 |
|---|---|---|
| 真相來源 | PostGIS | 政權、主權、疆界紀錄（第 1 層），由考證流程寫入 |
| `boundary_periods` | PostGIS view 或導出表 | 每段「不變幾何」一筆：`regime_id, start_day, end_day, geom, color_idx, disputed, control_type` |
| `label_points` | 建置產物 | 每個政權的每個時期一個點：在最大塊國土上用 polylabel 算出，含 `start_day, end_day, regime_id, name, area` |
| 圖磚建置 | `tools/tiles/`（CI 作業） | 從 PostGIS 導出 GeoJSONSeq，經 tippecanoe 產生 `boundaries-v{hash}.pmtiles` 和 manifest |
| 圖磚服務 | 開發：Martin（本地）；正式：已定：Cloudflare R2 加 CDN（上線時開通，費用需要 Tai 本人同意） | 用 HTTP range 請求提供 PMTiles |
| API（.NET） | `api/` | 中繼資料查詢、被選政權詳細資料、manifest；不處理疆界幾何的批次輸出 |
| 前端地圖 | `app/` 的 map 模組 | pmtiles protocol、日期 filter、標籤、蒙版、掃描動畫 |

### 3. 資料流
```mermaid
flowchart LR
  A[考證寫入 PostGIS] --> B[boundary_periods]
  B --> C[CI 建置: GeoJSONSeq → tippecanoe]
  C --> D[boundaries-v{hash}.pmtiles<br/>layers: boundaries, labels]
  C --> E[manifest.json]
  D --> F[開發: Martin / 正式: CDN]
  E --> G[API /tiles/manifest]
  F --> H[前端 MapLibre]
  G --> H
  H -- 換日期 --> H2[setFilter only，無請求]
  H -- 點選政權 --> I[API /regimes/{id}?date=]
```

### 4. 介面
**圖磚 schema**（日期一律存成整數日，從 1900-01-01 起算的天數；確切起點於實作時定案）
- 圖層 `boundaries`（polygon，z0–z8，超過 z8 由前端放大）：`regime_id`、`start_day`、`end_day`（不含當日；仍持續者用最大值）、`color_idx`、`disputed`、`control_type`
- 圖層 `labels`（point）：`regime_id`、`start_day`、`end_day`、`name_zh`、`name_local`、`area`（標籤排序用，`symbol-sort-key`）

**前端日期篩選**
```js
['all', ['<=', ['get','start_day'], d], ['>', ['get','end_day'], d]]
```
只有在 d 跨越 manifest 列出的變動日時，才呼叫 `setFilter`。

**API**
- `GET /tiles/manifest` 回傳 `{ version, url, minDay, maxDay, changeDays[] }`；快取 60 秒。
- `GET /regimes/{id}?date=` 回傳中繼資料（首都、元首、主權）。
- `GET /regimes/{id}/geometry?date=` 回傳被選政權的完整幾何，供重算可見標籤、蒙版用；不提供「全世界疆界」端點。

**被選政權的標籤**
- 另設一個 GeoJSON source `selected-label`，前端依畫面可見部分重算（`queryRenderedFeatures` 或上面的幾何端點，取交集後做 polylabel）。
- 圖層放在蒙版之上，`text-allow-overlap: true`、`text-ignore-placement: true`。
- 地圖移動結束後（moveend）重算，加上防抖動。

### 5. 第 3 層快取
| 層 | 內容 | 策略 |
|---|---|---|
| CDN | PMTiles | 檔名帶內容雜湊，`Cache-Control: public, max-age=31536000, immutable`；需支援 range 請求 |
| CDN 或 API | manifest | `max-age=60` |
| Redis | API 中繼資料查詢 | 快取鍵 `v{dataVersion}:{endpoint}:{params}`，換版自然失效；不放幾何 |
| API 程序內 | 熱門小表 | 設上限（例如 50MB），使用 LRU |
| 瀏覽器 | 圖磚 | 使用 MapLibre 內建快取；Service Worker 為選做 |

### 6. 遷移步驟
1. 完成第 1 層：PostGIS 依日期查詢，移除 3.3GB 的快照。
2. 建立 `boundary_periods`，並和第 1 層結果比對（591 個變動日加 50 個隨機日，政權集合要一致）。
3. 寫建置腳本，產出第一版 PMTiles，記錄總大小和單一圖磚的最大尺寸。
4. 開發環境用 Martin 提供 PMTiles；前端加功能開關 `boundarySource=geojson|tiles`。
5. 把國名、被選政權標籤、蒙版、高亮（promoteId 設為 `regime_id`，使用 feature-state）和掃描動畫逐項移到圖磚模式。
6. 測試驗收團隊跑回歸測試和效能基準。
7. 已定：Cloudflare R2 加 CDN（上線時開通，費用需要 Tai 本人同意）；開通後上線，預設改為 tiles；保留 geojson 模式一個版本後移除。

### 7. 驗收
- 正確性：在 591 個變動日加 50 個抽樣日上，圖磚模式渲染出的 `regime_id` 集合和第 1 層 API 完全一致（自動化比對）。（✅ 已通過 2026-11-04：641 天全部一致）
- 記憶體：API 常駐記憶體小於 500MB，且不隨資料量成長。（tiles 模式 ✅：重啟後 173MB，tiles 模式連續換日期後 85–145MB；geojson 模式仍會升到約 970MB）
- 熱跳：同一個視窗範圍內換日期，網路請求為 0，重繪小於 50ms。（重繪 ✅ 已通過：Tai 2026-11-04 10:13 定以換日期後第一次重畫為準，實測約 5ms，國名淡入動畫保留；網路請求為 0 ✅ 已通過：tiles 模式換日期 API／圖磚請求 0，只有網頁字型子集首次載入 3 個檔）
- 冷跳：CDN 已快取時，一般網路下小於 1 秒。開發期以 Martin 量測，只作參考。
- 播放：以 1 日/秒連續播放 60 秒，中階筆電維持 55fps 以上。
- 標籤：每個政權的每個時期只有一個國名；被選政權的名稱在蒙版上 100% 顯示，且位於可見國土內。
- 圖磚：單一圖磚小於 500KB；記錄總大小，並估算延伸到 1991 年後的量。

### 8. 進度
**已完成**
- 決策 D-B1、D-B2、D-B3（2026-11-04，Tai）。
- 第 1 層 ✅（2026-11-04，feature/russia-unclip-loading，未 push）：
  - `6cfc4a4`：PostGIS 以 `valid_period @> d`（＝`lower <= d AND (upper IS NULL OR upper > d)`）篩出當天有效紀錄，這步不取幾何；原始幾何只對還沒算過的紀錄才讀；簡化後的 GeoJSON 依（紀錄, 容差）共用，各日期不再各存一份幾何。索引已齊（`sovereignty_records` 的 `valid_period`、`geom` GiST；佔領、衝突 `valid_period` GiST；陣營走 `(regime_id, valid_period)` GiST），不需 migration。回應格式不變（15 個回應改前改後位元組相同）。
  - `32c9275`：逐日快取改滑動視窗（以查詢日期為中心前後各 10 個變動日，往播放方向預先載入 3 個，估算上限 1.5GB 當保險），啟動只預熱預設日期 1940-07-15，不再全量預熱 591 個日期；移除暫時的 GC 上限環境變數。
  - 實測（mac-mini，開發庫 5442）：1908／1924／1933／1940／1945-06-15 全部 200；冷跳 0.22–0.94 秒、熱跳 0.06–0.09 秒（精細縮放）；RSS 啟動約 1.6GB，三種縮放全掃 591 個變動日後最高約 3.05GB（改前 5.9GB）。常駐記憶體尚未達 §7 的「小於 500MB」，留待第 2、3 層。
- 遷移步驟 2 ✅ `1f87d58`：`boundary_periods` view（migration `20261104013000_BoundaryPeriods`，已套用到開發庫 5442；排除撤回紀錄；整數日暫定自 1900-01-01 起算，持續中者 `end_day`＝2147483647；`color_idx` 由 slug 雜湊取 8 色；`disputed` 暫時一律 false，資料沒有對應欄位）；`tools/tiles/sql/label_points.sql` 在每段時期的最大塊國土上用 `ST_MaximumInscribedCircle`（polylabel）算國名點。`tools/tiles/compare.py`：591 個變動日加 50 個隨機日共 641 天，政權集合和第 1 層 API 不一致 0 天；1015 個國名點，缺名、缺點 0。這是資料層比對，§7 的「渲染出的集合」比對尚未做。
- 遷移步驟 3 ✅ `5a3bda0`：`tools/tiles/build.sh`（PostGIS → GeoJSONSeq → tippecanoe 2.79.0 docker image → PMTiles，z0–z8，`--detect-shared-borders`）。第一版 `boundaries-vb9e51dc76522.pmtiles` 12,918,791 B（12.3MB），20,796 張圖磚；單一圖磚最大 255,674 B（z1/1/0），超過 500KB 的 0 張；z8 共 14,724 張、8.5MB、最大 9KB。z0 有 3 段小於一個像素的疆界被略去，z2 起 1015 段全在。
- 遷移步驟 4 ✅ `2190f3c`：`tools/tiles/martin.sh` 用 Martin docker image（1.16.1）在 127.0.0.1:3010 提供 PMTiles；前端開關 `?boundarySource=geojson|tiles`（預設 geojson）。tiles 模式實測（世界視圖、圖磚已載入）：18 次換日期，圖磚請求 0、`/sovereignty` 請求 0，仍有 `/control`、`/conflicts` 請求（這兩項尚未移到圖磚）；setFilter 後第一幀約 5ms，到地圖 idle 約 310ms（主要是國名淡入）；輸入日期到畫面就緒中位數 441ms（geojson 模式 793ms）。國名以外的被選政權標籤、蒙版、高亮、掃描動畫仍屬步驟 5。

**未完成**
- 遷移步驟 5 ✅（2026-11-04，`0e58eed`–`5550886`，未 push；驗收：正確性、熱跳、tiles 模式記憶體已通過）。
- 遷移步驟 6–7（熱跳「重繪小於 50ms」✅ 已通過，以第一次重畫為準，Tai 2026-11-04 10:13）。

**未決定**
- CDN 供應商：已定：Cloudflare R2 加 CDN（上線時開通，費用需要 Tai 本人同意）。
- 整數日的起算日。
- 最高縮放級別：目前假設 z8，待實測。
- 若圖磚過大，是否依年代拆成多個 PMTiles（例如每 10 年一個）。
- 建置觸發方式：每次合併就建置，或每日一次。

### 9. 風險
- 圖磚過大：1938–1945 的變動密集，延伸到 1991 年後會更嚴重。對策是加強低縮放級別的簡化、設定圖磚大小上限，必要時依年代拆檔。
- 簡化後相鄰邊界出現縫隙或重疊：使用 tippecanoe 的 `--detect-shared-borders`；不夠時在 PostGIS 先做拓撲簡化。
- 資料生效延遲：考證結果要等建置跑完才會上線；開發期用 Martin 預覽。
- 低階裝置上 filter 的成本：只在變動日更新 filter。

## 10. UI 改版（四項已完成；Tai 2026-11-04 11:20 採用，13:35 執行）

> 狀態：✅ 四項已完成（2026-11-04）：1 事件卡片化 `fcefb0a`；2 面板寬度與響應式 `4ded751`；3 圖例浮動面板 `972a744`；4 面板停在時間軸上方 `08b9d3d`（含 §10 e2e）。單元測試 287 全過；e2e 110 過、76 略過（需 5051 或特定開關）。截圖 box `/workspace/wl-ui10/`（tiles、geojson 各 1440／1024 × 4 張）。追加修正（Tai 15:13）：ⓘ 不再蓋住出處 `0fc4200`；首都名不被面板切到 `78d6b2c`；小於 768px 圖例成為底部面板分頁 `97363e2`；標頭顯示首都 `cc361b0`。⬜ 未做：卡片 hover 時地圖脈衝、戰役彈窗、分頁改「概要／元首／事件／疆界」。以下為設計稿 `ui-timeline-sheet-legend.md` 原文照搬。

# World Line UI 調整設計稿 v0.1（2026-11-04，待 Tai 確認）
前提：國名用 MapLibre symbol layer；圖例和面板用 map padding 避開標籤；被選政權的名稱在蒙版之上，一定要顯示；底部時間軸用方案 A（48px），已經完成。
未重讀 repo，尺寸是依主流做法估的，以實作驗證為準。

## 1. 事件時間線：建議卡片化（放在 sheet 的「事件」分頁）
- 參考產品：Google Maps 地點卡、Apple Maps 指南、Wikipedia 時間軸、TimelineJS。
- 樣式：垂直時間軸，左側 2px 軸線，每個事件是一張卡片，卡片之間間距 8px。
- 卡片尺寸：寬度等於面板寬度扣掉 32px，摺疊時高 72px（日期、標題、類型 tag），展開後顯示摘要、出處、「在地圖上看」按鈕。
- 同一個月份的事件歸成一組，組上方有 sticky 的月份標頭（28px）。
- 狀態：default、hover（卡片浮起，地圖上對應位置以脈衝提示）、selected（左側 3px 品牌色邊）、pending-verification（虛線框加「待考證」tag）、battle（附 ⚔ tag，點了開非全螢幕的戰役彈窗）。
- 與底部時間軸連動：點卡片會把時間軸跳到該日期（熱跳）；時間軸日期變動時，清單自動捲到最接近的卡片。不用另外加軸。
- 超過 50 筆時改用虛擬捲動。
- 對標籤的影響：沒有影響，卡片都在 sheet 裡面。

## 2. 政權 sheet 寬度：從現在加寬到 400px
- 參考產品：Google Maps 桌機版 408px、Apple Maps 約 375–400px、Mapbox Studio 約 360px。
- 響應式規則：
  - 視窗 ≥1440px：寬 400px，可拖拉調整 360–480px，記在 localStorage。
  - 1024–1439px：寬 360px。
  - 768–1023px：寬 320px，蓋在地圖上，不推擠地圖。
  - 小於 768px：改成底部 bottom sheet，三段高度：96px、50vh、90vh。
- 頂部固定 56px 標頭（政權名稱、首都、關閉按鈕）；分頁有「概要／元首／事件／疆界」。
- 標籤避讓：sheet 開啟時用 map.easeTo({padding:{right: sheet寬 + 16}})，關閉時 padding 歸零，動畫 200ms。被選政權的名稱由 selected-label source 依可見範圍重算，所以面板加寬後名稱不會被遮住。
- 時間軸：方案 A 的 48px 時間軸寬度改成 calc(100% - sheet寬)，或維持全寬、讓 sheet 底部停在時間軸上方。建議採後者（sheet 高度 = 視窗高 - 48px），比較單純。

## 3. 圖例：建議採用「左下角浮動按鈕，點了展開小型浮動面板」
三種方式比較：
- 中央彈窗：會擋住地圖，看圖例時必須關掉才能對照，主流地圖產品幾乎沒有這樣做。不建議。
- 左側 sidebar：佔掉一整欄，和右側 sheet 一起開時地圖太窄；只有 GIS 專業工具（ArcGIS、QGIS）會這樣做。
- 維持現狀：如果現狀是常駐顯示，就違反「預設不開啟」的要求。
- 建議做法（Google Maps 圖層按鈕、Windy、ArcGIS Online 的 Legend widget、Felt 都屬這一類）：左下角放一顆 40×40 的 ⓘ「圖例」按鈕；點了在按鈕上方展開 240px 寬的浮動面板，最高 50vh，可捲動；按 Esc、再點一次按鈕、或點地圖空白處都會收起；開關狀態記在 localStorage。
- 位置：在時間軸上方 12px、距左邊 12px。
- 標籤避讓：面板開啟時設 padding.left = 264（只有視窗寬 ≥1024px 才設，以免地圖擠壓）；被選政權的名稱照樣顯示。
- 小於 768px：圖例改成 bottom sheet 裡的一個分頁。

## 待 Tai 確認
1. 事件卡片化，放在 sheet 的「事件」分頁。
2. sheet 加寬到 400px，可拖拉調整 360–480px。
3. 圖例採左下浮動按鈕加浮動面板，不採中央彈窗或左側 sidebar。
4. sheet 停在時間軸上方，時間軸維持全寬。

## 10 v2. 政權面板 v2（Tai 2026-11-04 15:29 決定：W1 依螢幕大小固定三種寬度，1440 寬時 432px、不拖拉；C1 出處點選卡片後才顯示；T1 尚未發生的事件變淡；T2 目前日期標線；拿掉收合、標題不重複、恢復左側直線與時間點）
> 狀態：✅ 已完成（2026-11-04）：W1 固定寬度 432／384／360（不拖拉）`1619650`；卡片不收合、選取後才顯示出處、左側直線與節點、目前日期標線、未發生事件變淡 `a5445fb`。滑過卡片時地圖閃動、戰役簡報按鈕未做（依 §11，等點子工坊）。以下為設計稿 `ui-sheet-v2.md` 原文照搬。

# 政權面板 v2：寬度、事件卡片、時間線（設計稿，2026-11-04，待 Tai 確認）
依據：Tai 提供的截圖 tai-sheet-events.png（鄂圖曼帝國的事件分頁）。截圖中看到的問題：
- 展開後，標題和日期各出現兩次。
- 「展開／收合」文字按鈕佔掉了版面。
- 時間線只剩一段很淡的直線，時間點也只出現一個。

## 1. 面板寬度：固定、不拖拉，以 30% 為準並設上下限
寬度公式：`width = clamp(360px, 30vw, 560px)`

| 視窗寬度 | 面板寬度 | 說明 |
|---|---|---|
| ≥1866px | 560px（上限） | 避免大螢幕上面板過寬，文字一行太長 |
| 1440px | 432px（30%） | Tai 指定的基準 |
| 1200–1439px | 360–431px | 依 30% 隨視窗寬度變化 |
| 1024–1199px | 360px（下限） | 保留事件卡片的最小可讀寬度 |
| 768–1023px | 360px，蓋在地圖上 | 地圖右側 padding 不變，避免地圖被擠窄 |
| <768px | bottom sheet，三段高度：96px／50vh／90vh | 同 v0.1 |

- 移除拖拉把手和 localStorage 中記錄寬度的設定。
- 地圖右側 padding = 面板寬 + 16px，視窗大小改變時用 easeTo 重新套用。
- 選項 W1：1440px 時剛好 30%（432px）。另一個做法是固定三個寬度（1440px 以上 432px、1024–1439px 384px、768–1023px 360px），比較好測試。建議採用 clamp。

## 2. 卡片：建議取消收合，改成「預設精簡＋選取時展開細節」
理由：截圖裡收合時已經顯示標題和 tag，展開後只多了出處和按鈕，卻把標題和日期又重複一次。主流做法（Google Maps 的時間軸、GitHub 的活動紀錄、Wikipedia 的年表）都是每一列直接顯示完整內容，不另外放收合按鈕。

**每張卡片固定顯示的內容（不收合）**
- 第 1 行：日期，13px、等寬字、灰色；右側是考證狀態的小圖示（✓ 已查證、? 待考證、⚔ 戰役）。
- 第 2–3 行：標題，15px 粗體，最多兩行，超過的部分用 line-clamp 截斷，不再只顯示一行加 …。
- 第 4 行：tag（交戰方、開戰等），12px。

**選取卡片時（點擊卡片任何位置；同一時間只有一張被選取）**
- 原卡片內往下延伸，不重複標題和日期，只新增以下內容：
  - 摘要（如果有的話）。
  - 出處：一行，可點擊。
  - 動作列：「在地圖上看」「戰役簡報」（只有戰役事件才有），左右排列，按鈕高 32px。
- 移除「展開／收合」文字按鈕。再點一次被選取的卡片，或點另一張卡片，就會收起。
- 滑過卡片時，地圖上對應的位置閃動（依 §11）。
- 選項 C1：如果 Tai 認為每張卡片都要能看到出處，可以把出處改成固定顯示的第 5 行（灰色 12px），這樣就完全沒有展開狀態。

## 3. 時間線和卡片的結合
沿用原本「左側直線加時間點」的樣式，卡片掛在直線右邊。

```
│ 1911年9月                     ← 月份標頭，sticky
●─┌──────────────────────┐
│ │1911-09-29        ✓  │
│ │義大利對鄂圖曼帝國宣戰… │
│ └──────────────────────┘
◉═══ 目前日期 1912-03-01 ═══    ← 目前日期標線
│ 1912年4月
○─┌──────────────────────┐
```

- 時間線欄寬 24px；直線寬 2px，顏色是中灰，從第一個事件一路畫到最後一個事件，不中斷。
- 每個事件一個節點：直徑 10px，和卡片的日期列垂直對齊，用 6px 的短橫線連到卡片。
  - 實心：已查證。空心：待考證。⚔ 圖示（14px）：戰役事件。
  - 選取時節點放大到 14px，並變成品牌色；卡片左側加 3px 品牌色邊框（截圖裡的藍色邊）。
- 月份標頭：直接寫在直線上，標頭前面畫一個 6px 的小方塊當刻度。標頭固定在面板頂端（sticky），高 28px。
- 目前日期（底部時間軸的日期）：不再寫成卡片上的「目前日期」文字，改成一條橫跨的標線，插在目前日期前後兩個事件之間。
  - 左側是 12px 的品牌色圓點，右側是 1px 的品牌色虛線，加上「1912-03-01」的標籤。
  - 早於目前日期的事件節點和卡片保持原本顏色；晚於目前日期的變成 60% 透明度，表示「尚未發生」。
  - 底部時間軸的日期改變時，標線跟著移動，清單平滑捲動，讓標線停在可見區域上方約 1/3 的位置。
- 選項 T1：「尚未發生」的事件要不要變淡？建議要。
- 選項 T2：目前日期標線要不要固定顯示？建議要；它也取代卡片上的「目前日期」文字。

## 要 Tai 決定
1. W1：面板寬度用 clamp（360–560px，30vw），還是固定三個寬度？
2. C1：取消收合後，出處要放在選取後才顯示的內容裡，還是一律固定顯示？
3. T1：尚未發生的事件要不要變淡？
4. T2：用目前日期標線取代卡片上的「目前日期」文字？

## §11 事件座標、戰役模式、疆界分頁（章節稿 v1，2026-11-04，待 Tai 確認）
> 狀態：🟡 部分完成（2026-11-04）：11.2 戰役模式第一批（敦克爾克、閃擊波蘭、淞滬；靜態 JSON，圖層可改 PMTiles）資料 `306fc48` `b63ec96`；狀態機 `8850313` `349dbbc`；地圖圖層 `c9eaaf8` `287a041`；說明卡與入口 `925b877`；e2e `3208b0d`。⬜ 未做：11.1 事件座標、11.3 疆界分頁、事件卡 ⚔ 入口（event_ids 待考證組補）、手機卡片拖拉、時間軸鎖定只做成停用。截圖 box `/workspace/wl-ui10/campaign/`。
基準尺寸取自 §10：右側 sheet 寬 400px；底部時間軸 48px，在 900px 高的視窗中頂端位於 y=852。其他現有尺寸未重讀 repo，實作時再對照修正。

### 11.0 決定
| 編號 | 決定 |
|---|---|
| D-U1 (A1) | 一個事件只對應一個地點，不建 event_locations 表 |
| D-U2 (A2) | 沒有座標就不閃動，卡片上標「無座標」，不用其他位置代替 |
| D-U3 (A3) | 自動比對的座標先上線，標成待考證（geom_status=auto） |
| D-U4 (B1) | 主地圖本身進入戰役模式，左側放一張 360px 的說明卡。**（已由 §19 獨立頁 `/campaign/:slug` 取代，Tai 2026-11-11）** |
| D-U5 (B2) | 不自動播放，由使用者按播放鍵開始 |
| D-U6 (B3) | 手機版（寬度小於 768px）的戰役模式改成全螢幕 |
| D-U7 (C1) | 做面積折線圖 |
| D-U8 (C2) | 爭議領土延到 1945 年以後的階段再做 |
| D-U9 (C3) | 鄰國預先計算 |

### 11.1 事件座標
**Schema**（events 表新增欄位）
```sql
ALTER TABLE events ADD COLUMN geom geometry(Point,4326),
  ADD COLUMN geom_precision text CHECK (geom_precision IN ('exact','city','region','country')),
  ADD COLUMN geom_source text,          -- wikidata:Qxxx | geonames:id | manual
  ADD COLUMN geom_status text NOT NULL DEFAULT 'pending'
    CHECK (geom_status IN ('verified','auto','pending'));
CREATE INDEX ON events USING GIST (geom);
```
**補資料流程**
1. 匯入腳本 `tools/geocode-events`：先用 Wikidata 的 P625（座標）；沒有的話，取 P276（地點）指向的實體的 P625；還沒有就用 GeoNames 地名比對。比對到的寫入 geom，標成 `auto`。執行後輸出比對率報表。
2. 比對失敗的事件，以及精確度只到 country 的事件，列成清單交給 World Line 史料考證補，補完標成 `verified`。
3. World Line 測試驗收抽查 5% 的 `verified`。

**API**：`GET /events?regime=&from=&to=` 的回應新增 `lng, lat, geom_precision, geom_status` 四個欄位；沒有座標時 lng 和 lat 回傳 null。

**前端**
- 新增 source `event-pulse`（GeoJSON，最多一個點）和 circle layer：半徑從 8px 放大到 24px、透明度從 0.8 降到 0，1.2 秒一輪，播放 2 輪後清空。
- 沒有座標的事件，滑過卡片時不做任何事，卡片上顯示灰色的「無座標」tag。
- `geom_status=auto` 的事件，卡片上顯示「座標待考證」tag。
- 點落在可見範圍外時，在畫面邊緣顯示 24px 的方向箭頭。可見範圍要扣掉右側 400px 的 sheet 和底部 48px 的時間軸。
- 「在地圖上看」用 flyTo，exact 和 city 用 zoom 6，region 用 zoom 5，country 用 zoom 4，padding 為 {right:416, bottom:64}。

### 11.2 戰役模式
> 註記（2026-11-11）：本節「主地圖戰役模式、不改 URL」已由 §19 獨立頁（`/campaign/:slug?phase=`）取代；現行實作在 §19 C2 前照舊，說明卡內容、圖層、狀態機由 §19 沿用。
- 進入方式：點 ⚔ tag。狀態機從 browse 轉到 campaign，進入後不自動播放，停在 P1。
- 版面（桌機）：
  - 左側說明卡寬 360px，top 16、left 16，底部停在時間軸上方 12px（bottom = 48 + 12），內容可捲動。
  - 右側 sheet 維持 400px 寬，可以收起。
  - 地圖 padding 為 {left: 392, right: 416（sheet 開啟時）, bottom: 64}，用 fitBounds 對準戰役範圍。
- 說明卡內容依序為：標題、日期範圍、交戰方色票、階段膠囊（P1…Pn）、播放／暫停／上一階段／下一階段、階段說明、兵力與結果（沒有出處就顯示「待考證」）、引用來源。
- 圖層（都是主地圖上的 layer）：
  - `campaign-fronts`：line，戰線。
  - `campaign-arrows`：line 加 symbol，進攻箭頭。
  - `campaign-sites`：symbol，據點。
  - 三個圖層都依 `phase` 過濾。
- 播放：每個階段停 3 秒，播完停在最後一個階段（ended）。
- 時間軸：鎖定在戰役日期範圍，並顯示目前階段的日期。
- 狀態：loading → ready(P1) → playing ↔ paused → ended。出錯時說明卡只顯示文字摘要，戰役圖層不顯示。
- 離開戰役模式（按 Esc 或點 ×）：回到 browse 狀態，恢復進入前的日期、地圖視角和 sheet 狀態。
- 標籤：被選政權的名稱維持在蒙版之上。地圖 padding 的左側增加 392px，讓國名標籤避開說明卡。
- 手機版（寬度小於 768px）：全螢幕。地圖佔上方 60vh；說明卡在下方，可以拖拉；時間軸隱藏，改用階段膠囊切換。

### 11.3 疆界分頁
1. 摘要列：當日面積（km²），以及和上一個時期相比的增減（±km²、±%）。
2. 面積折線圖：x 軸是 1908–1945，y 軸是面積；目前日期用一條直線標示。滑過折線時顯示該日面積，點擊折線會熱跳到該日期。高 120px，畫在 SVG 上。
3. 疆界變遷列表：依 boundary_periods 列出每段時期的起訖日、變化原因和出處，點一列會熱跳到該時期的起始日。
4. 鄰國：當日與哪些政權接壤，點了切換成該政權的面板。
5. 爭議領土：這一版不做，延到 1945 年以後的階段。

**預先計算**（在建 PMTiles 的批次中一起執行）
```sql
CREATE TABLE boundary_period_stats (
  period_id bigint PRIMARY KEY REFERENCES boundary_periods,
  area_km2 numeric, area_delta_km2 numeric);
CREATE TABLE boundary_period_neighbors (
  period_id bigint, neighbor_regime_id bigint, during daterange,
  PRIMARY KEY (period_id, neighbor_regime_id, during));
-- 面積用 ST_Area(geom::geography)/1e6
-- 鄰國用 ST_Touches，或 ST_Intersects 搭配 0.5 km 容差，並取雙方時期日期範圍的交集
```
**API**：`GET /regimes/{id}/boundary-summary?date=` 回傳 `{area_km2, delta, series:[{day, area}], periods:[...], neighbors:[...]}`；series 每個時期一點。

### 11.4 驗收
- 有座標的事件，滑過卡片後 100ms 內開始閃動；沒有座標的不閃動。
- 戰役模式中，說明卡、sheet、時間軸互不重疊；被選政權的名稱一定看得見；離開後完全恢復進入前的狀態。
- 播放時維持 55fps 以上。
- 疆界分頁的資料 300ms 內載入。鄰國清單和 PostGIS 抽查的結果一致。
- 寬度小於 768px 時，戰役模式為全螢幕。

### 11.5 未決定
- GeoNames 要用線上 API，還是下載資料庫放在本機？兩種都免費。
- 鄰國的容差要用多少（暫定 0.5 km）。

## 12. RWD（Tai 2026-11-04 16:13 決定：H1 手機版頂列顯示日期；P1 1024–1199px 面板 360px 疊在地圖上、1200–1439px 維持 384px；L1 手機版圖例改成從 ⋯ 選單打開的獨立面板（取代圖例分頁）；M1 手機版時間軸不加上一步／下一步按鈕）
> 狀態：✅ 已完成（2026-11-04）：斷點 `f8d25ad`；頂列 `1ac1077`；時間軸 `f583a69`；政權面板 `8860063`；圖例 `e3d47d5`；觸控 `800b531`。⬜ 未做：§4 戰役模式（屬 §11）、「疆界」分頁與 chip 分頁列、peek 的年代＋摘要行、觸控時點卡片閃動（§11）、手機橫放地圖 ≥40% 與 55fps 尚未量測。截圖 box `/workspace/wl-ui10/rwd/`。以下為設計稿 `ui-rwd.md` 原文照搬。

# World Line RWD 設計稿（手機、平板），2026-11-04，待 Tai 確認
依據：390px 寬的截圖 mobile-390-legend-tab.png。截圖中看到的問題：
- 頂列：「World Line」換行，日期大字被截成「年6 月1」，「實際控制／主權」切換鈕被擠成直排，語言切換鈕被切掉。
- 時間軸：年份標籤全部疊在一起。
- 圖例分頁大約佔了 55% 的高度，開著時幾乎看不到地圖。
- 「陣營外框」的勾選框浮在地圖上，擋住內容。

## 斷點
| 名稱 | 寬度 | 適用裝置 |
|---|---|---|
| xs | 360–599px | 手機直放 |
| sm | 600–767px | 手機橫放、小平板 |
| md | 768–1023px | 平板直放 |
| lg | 1024–1439px | 平板橫放、小筆電 |
| xl | ≥1440px | 桌機 |
另外加一條規則：視窗高度小於 500px 時（手機橫放），頂列和時間軸都改成精簡版。

## 1. 頂列
- lg、xl：維持現狀。
- md：高 56px。標題只留「World Line」；「實際控制／主權」切換鈕改成雙鍵的 segmented control，寬 120px；語言切換鈕寬 72px。
- xs、sm：高 48px，只放三樣東西：
  - 左邊放 24px 的 logo 和「World Line」，字級 16px，不換行（white-space: nowrap）。
  - 中間放日期，16px 粗體，格式為 1940-06-01。不再用大字，也不要折行。點日期會開啟日期選擇器（和時間軸的日期鈕是同一個）。
  - 右邊放 ⋯ 選單按鈕，40×40；「實際控制／主權」、中文／EN、「陣營外框」都收進這個選單裡。
- 「陣營外框」的勾選框不再浮在地圖上，在所有斷點都移進圖層或選單裡。
- 選項 H1：手機版頂列要不要放日期？建議要，因為日期是這個產品最重要的狀態。

## 2. 底部時間軸（方案 A 的 RWD）
- lg、xl：維持 48px 高的單行時間軸。
- md：高 48px，年份標籤每 5 年一個（1910、1915…）。
- xs、sm：高 56px，分兩行：
  - 上行 24px：播放鈕 32px、日期鈕（顯示 1940-06）、上一步／下一步（‹ ›）。上一步和下一步依目前的縮放級距跳一格。
  - 下行 32px：滑桿，左右各留 16px 邊距，滑桿的把手（thumb）24px。年份標籤只顯示 1910、1920、1930、1940（每 10 年），其他年份只畫刻度。
- 年份標籤的避讓規則（所有斷點通用）：每個標籤至少需要 36px 的寬度；依滑桿實際寬度算出顯示間隔，從 1、5、10、20 年中挑能放得下的最小間隔。
- 拖動滑桿時，把手上方浮出 YYYY-MM 的提示。
- 底部要留 env(safe-area-inset-bottom) 的安全區。

## 3. 政權面板
- xl：寬 432px。lg：寬 384px。md：寬 360px，疊在地圖上（現況）。
- 1024 寬時 384px 是否合理：面板佔 37.5%，地圖剩 640px，在歐洲的比例尺下大約只容得下 3–4 個國名，偏擠，但還可以用。選項 P1：
  - (a) 維持 384px。
  - (b) 1024–1199px 改成 360px，並且疊在地圖上（地圖寬度不受影響）。
  - (c) 1024–1199px 維持推擠地圖，但寬度降到 340px。
  - 建議 (b)：iPad 橫放（1024–1180px）常用，疊在地圖上時地圖不會變窄；被選取的政權名稱放在面板左側的可見區域，避免被面板遮住。
- xs、sm：底部面板分三段高度。
  - peek 120px：政權名稱、首都、年代，加一行摘要。
  - half 50vh：分頁和內容。
  - full：100vh 扣掉頂列 48px。
  - 往上滑、往下滑會吸附到三段中最接近的高度。拖拉把手 32×4px，可點擊範圍 44px 高。
  - 分頁列在 half 和 full 時固定在頂端（sticky）。分頁有「概要、元首、事件、疆界」四個，用可水平捲動的 chip 呈現。
  - 地圖 padding.bottom 等於面板目前高度。被選取政權的名稱會依可見區域重新計算位置，保證在面板上方看得到。
- 圖例在手機上：建議不要再當成政權面板的分頁（選項 L1）。
  - 改成頂列 ⋯ 選單裡的「圖例」項目，開啟一個獨立的 bottom sheet，最高 60vh，往下滑或點地圖就會關閉。
  - 原因：圖例和政權是兩回事；沒有選取政權時也要能看圖例；截圖中圖例佔了 55% 的高度，太大。
  - 圖例內容在手機上改成兩欄的 grid：色票 20px，說明文字 13px。

## 4. 戰役模式（§11，手機版全螢幕）
- xs、sm：
  - 頂列換成戰役列（48px）：左邊是 ×，中間是戰役名稱（一行，太長以 … 截斷），右邊是 ⓘ。
  - 地圖佔上方 60vh。說明卡是底部面板，分三段高度：peek 140px（階段膠囊和播放控制）、half 50vh、full。
  - 階段膠囊列可以水平捲動，每顆膠囊至少 44px 高。
  - 底部時間軸隱藏。
  - 手機橫放（高度小於 500px）時，說明卡改放左側，寬 40vw。
- md：說明卡在左側，寬 320px，疊在地圖上；其他和桌機版相同。

## 5. 觸控操作
- 地圖：雙指縮放和旋轉；關閉 pitch。單指拖動地圖。
- 點一下國家等於選取該政權，底部面板開到 peek 高度。點地圖空白處則收合面板。
- 沒有 hover，所以：
  - §11 的「滑過事件卡片時閃動」在觸控裝置上改成「點卡片就閃動」。
  - 地圖 tooltip 改成點擊後出現，3 秒後消失。
- 所有可點擊目標至少 44×44px，按鈕之間至少 8px 間距。
- 拖拉底部面板時，地圖不跟著移動（touch-action 設定，避免手勢衝突）。
- 判斷是否為觸控裝置時，用 `(hover: none) and (pointer: coarse)`，不用螢幕寬度判斷。

## 6. 驗收（每頁在 360、390、768、1024、1180、1440 這幾個寬度截圖）
- 頂列不換行；年份標籤不重疊；被選取政權的名稱看得到；可點擊目標都在 44px 以上。
- 底部面板吸附流暢，維持 55fps 以上。
- 手機橫放時，地圖至少佔畫面的 40%。

## 要 Tai 決定
- H1：手機版頂列要不要顯示日期？
- P1：1024–1199px 的面板要用 (a) 384px、(b) 360px 疊在地圖上，還是 (c) 340px 推擠地圖？
- L1：手機版的圖例要從政權面板分頁移到 ⋯ 選單，改成獨立的 sheet？
- M1：手機版時間軸要不要加上一步／下一步按鈕？

## 13. 衝突資訊的位置與比例尺（Tai 2026-11-04 17:31 決定：K1 衝突資訊改成地圖圖示旁的 320px 錨定小卡，不再取代政權面板，手機版照稿做；K2 一般衝突也有「在時間線上看」，「戰役簡報」只在符合戰役定義時出現；K3「圖示位置」這類技術說明只在除錯模式顯示；S1 比例尺低縮放（zoom < 3）時隱藏；S2 比例尺只用公里）
> 狀態：✅ 已完成（2026-11-04）：K3 除錯模式 `aa5c799`；K2 戰役定義判斷 `4c13a42`；K1 衝突小卡 `1ee5dfa` `14f8336`；S1／S2 比例尺 `14f8336`；e2e `22f9d2e`。⬜ 未做：手機衝突面板拖拉（目前點把手切換 peek／half）。截圖 box `/workspace/wl-ui10/conflict/`。以下為設計稿 `ui-conflict-scale.md` 原文照搬。

# 衝突資訊的位置與比例尺（設計稿，2026-11-04，待 Tai 確認）
依據：tai-conflict-panel.png（1939-11-30 蘇芬冬季戰爭）。

## 現況問題
- 衝突資訊整個取代了政權面板，原本的事件分頁被蓋掉，只剩「← 返回芬蘭」。使用者看不到這場衝突在芬蘭事件時間線上的位置，而且面板內容在政權和衝突之間來回切換，容易迷失。
- 衝突有兩方以上（蘇聯和芬蘭），不屬於任何一個政權，放在「政權面板」裡，資訊架構不對。

## 建議：地圖上的錨定小卡（popover）→ 戰役模式／事件；不取代政權面板
參考：Google Maps 點地標時的小卡、Felt／ArcGIS 點要素時的彈出視窗。
- 點衝突圖示後，在圖示旁邊開一張錨定小卡，寬 320px（手機版改成底部 peek 面板，見下）。內容依序為：
  1. 交戰方色票和名稱（點名稱就切換到該政權的面板）。
  2. 類型（例如「交戰」）和期間（1939-11-30 → 1940-03-12）。
  3. 開戰和停戰兩行，各附考證狀態圖示；完整出處收在「出處 ›」裡。
  4. 動作列，最多三個按鈕：
     - 「戰役簡報」：只在符合三條件戰役定義時出現，按了進入 §11 的戰役模式。
     - 「在時間線上看」：在政權面板的事件分頁中捲到並選取這一則。
     - 「×」：關閉。
- 「圖示位置」這類技術說明（OHM sovereignty、build/locations.sql）不要給一般使用者看，改放到 ⓘ 的 tooltip，或只在除錯模式顯示。
- 政權面板保持原本內容。如果目前選取的政權就是交戰方之一，事件時間線上對應的卡片會同時被選取並高亮（依 §10 v2 的節點與左側邊框樣式）。
- 小卡的位置：用 MapLibre Popup 錨定在圖示上，anchor 設為 auto，並且避開右側面板和底部時間軸：
  可見範圍 = 地圖扣掉 padding {right: 面板寬 + 16, bottom: 64}。
- 關閉方式：按 Esc、點地圖空白處，或改變日期且新日期已不在衝突期間內。
- 進入戰役模式後：小卡關閉，左側 360px 的說明卡接手顯示（依 §11）。
- 手機版（§12）：點衝突圖示後，開一個衝突用的底部面板，peek 高度 140px（顯示交戰方、期間和兩個按鈕），往上拉到 half 才顯示開戰、停戰和出處。這個面板暫時疊在政權面板上方；關閉後回到原本的政權面板，高度也恢復原狀。

### 選項
- K1：衝突資訊放在 (a) 錨定小卡（建議），(b) 政權面板裡的「衝突」區塊或分頁，還是 (c) 維持現狀，整個取代面板？
- K2：不符合戰役定義的一般衝突，要不要也有「在時間線上看」？建議要。
- K3：「圖示位置」的技術說明要隱藏，只在除錯模式顯示嗎？建議隱藏。

## 比例尺
- 使用 MapLibre 的 ScaleControl，單位為 metric（km），maxWidth 100px。
- 位置：地圖左下角，放在圖例按鈕（左下 ⓘ，40px）的右邊：
  left = 12 + 40 + 8 = 60px，bottom 與圖例按鈕底部對齊（時間軸上方 12px）。
  右下角已經有出處文字，所以不放右邊。
- 樣式：
  - 線段 2px，顏色和文字同為 #5a5146。
  - 文字 11px，使用專案的 serif 字型。
  - 背景為 rgba(255,250,240,.8)，圓角 4，內距 2px 6px。
- 比例尺會隨緯度變化（Web Mercator 投影），在 z0–z3 的縮放級距時偏差很大。選項 S1：
  - (a) 所有縮放級距都顯示比例尺。
  - (b) zoom 小於 3 時隱藏（建議）。
  - (c) 加註「於畫面中央緯度」。
- 手機版：放在左下，底部面板 peek 高度的上方 8px；底部面板拉到 half 以上時隱藏。
- 戰役模式：左側說明卡打開時，比例尺移到說明卡右邊（left = 16 + 360 + 12）。
- 選項 S2：單位只用公里，還是公里和英里並列？建議只用公里。

## 要 Tai 決定
K1、K2、K3、S1、S2。

## 14. 人物閱讀與戰役互連（人物部分實作中；戰役部分暫緩）

> 狀態：🔧 人物 P1 實作中（2026-11-07，分支 `feature/person-cards`）。設計稿見 `docs/design/person-reading-campaign-nav.md`。標記：**現有**＝已核對程式並附路徑；**提案**＝未實作、未拍板。
> 編號核對（2026-11-07）：main `22c6e84` 的 ARCHITECTURE 只到 §13，da83499 是在檔尾**新增** §14、§15，沒有覆蓋或改號 §1–§13（含 §11 戰役模式、§5 M4-c 一級行政區）。

### 14.0 Tai 決定（2026-11-07 13:12，核准實作）
1. sheet 的「領導人」分頁改名「人物」；P1 只放領導人（`leader_records` 當天在任者）。
2. 補齊現有人物的資訊、生平、照片（照「備份 → 試跑 → 寫入」，只寫有來源者）。
3. ~~**戰役先不做**~~（**已由 Tai 2026-11-11 解禁**，T5／§19 Q2；戰役依 §19 C1 起進行。以下原文保留）：P1 不做任何戰役 UI、路由、人物↔戰役關聯，也不放指向戰役的連結。下文 14.3–14.5 中與戰役相關的部分全部延後（原設計保留作參考）。
4. 照已同意的 UI 做完（人物卡、大型閱讀對話框、來源預設收合、逐欄位來源、history 關閉規則）。
5. 照片：**P1 支援照片**（取代原 Q4 建議的「全部佔位」），但只有在記錄了授權來源（來源 URL、作者、授權、署名）且授權屬允許清單時才顯示，否則顯示中性佔位圖；不用 AI 生成肖像。

### 14.1 Tai 已確認的方向（2026-11-07）
- 人物分頁：P1 只放領導人，軍事人物 P2。卡片：姓名／照片／職位／任期／查看詳情。
- 大型閱讀對話框：桌機大視窗、手機全螢幕，不要求地圖可見；底下 sheet 的選取、分頁、捲動位置保留。
- 來源一律預設收合、版面穩定；無來源顯示「待補來源」；逐段／逐欄位溯源；無來源內容不標已查證。
- 戰役保留專屬頁；有來源的相關事件／戰役卡雙向連結；戰術概念不得自動把部隊／人物放上地圖；「參與」與「因果主張」分開記錄。
- 生平補齊：先盤點缺口、再逐筆查證、只寫已查證，照備份→試跑→寫入。本次不寫。

### 14.2 現況核對（重點）
| 項目 | 現況 | 路徑 |
|---|---|---|
| 人物資料 | **現有** `leader_records`（任期，`person_id` → `leader_bios`）＋ `leader_bios`（一人一筆；`field_sources` jsonb 逐欄位自由文字來源；無照片、無 slug） | `backend/src/WorldLine.Api/Domain/Entities.cs:325,357` |
| 來源 | **現有** `sources`＋citation 表格式（`event_citations` 等） | `Entities.cs:9,209`；`Domain/CitationPolicy.cs` |
| `persons`／`person_roles`／`media`／`parties` | **不存在**（點子工坊提案誤標為既有） | 全 repo 查無 |
| 路由 | **現有** 只有 `''`、`version`、`**`；無戰役、人物路由 | `frontend/src/app/app.routes.ts` |
| 戰役 | **現有** 主地圖「戰役模式」，非頁面；不改 URL；production 關閉；3 筆靜態 JSON，`event_ids` 皆空、無人物欄位 | `frontend/src/app/core/campaign.ts:8,11`；`pages/atlas/atlas.page.ts:551–563`；`frontend/public/campaigns/index.json` |
| URL 參數 | **現有** `date`、`lang`、`axis`（初始化讀一次，之後 `replaceUrl` 寫回）＋開發用 `boundarySource`、`debug`；**無 `cam`、無選取政權／分頁** | `core/atlas-state.ts:42`；`atlas.page.ts:768,845` |
| sheet／分頁 | **現有** `regime-sheet`（`aria-modal="false"`）、分頁 `overview/events/leaders`；sheet 隱藏時分頁重設；無捲動記憶 | `shared/regime-sheet/regime-sheet.ts:35`；`shared/sovereignty-card/sovereignty-card.ts:75`；`atlas.page.ts:493,1022` |
| 領導人分頁 | **現有** 清單列、生平在 sheet 內原地展開、欄位後附來源外連 | `sovereignty-card.ts:142–225` |
| 人物卡、閱讀對話框、dialog 元件 | **缺口**（`components/ui` 無 dialog） | `frontend/src/app/components/ui/` |

### 14.3 範圍
- **P1**：人物分頁（領導人）＋人物卡（含有授權的照片）＋閱讀對話框＋逐段／逐欄位來源＋ history 規則（14.4）。**不含任何戰役連結**（Tai 2026-11-07：戰役先不做）。
- **P2**：軍事人物；人物出現在戰役階段參與清單；（若 Tai 選）獨立戰役路由。
- **P3+**：行動／影響（因果主張，與參與分表）；`cam` 進 URL。
- **永不**：由生平或戰術文字自動在地圖畫人或部隊。

### 14.4 導覽與 history 規則（提案）
- 人物對話框用 query `?person=<leader_bios.id>`（merge 進現有參數，push 一筆），同路由不重建頁面。
- **關閉**：只有當 app 自己在 `history.state` 標記過、且確認「緊接的前一筆就是對應底層」時才 `history.back()`；不得以「同站有上一頁」為準，也不假設能讀取任意 history。其他情況一律 `replaceUrl` 只移除 `person`，保留 `date` 等其他參數。
- 人物→戰役→人物：進戰役前關閉對話框；返回目標只存一格（記憶體），重複巢狀時覆寫不累加。
- 重新整理：`date`／`lang`／`axis`／`person` 由 URL 還原；**sheet 的選取、分頁、捲動位置會遺失**（現況限制，待 Tai 決定是否把 `regime`／`tab` 加進 URL）。
- 直接 URL 帶 `cam`：提案，不自動改變現行行為。

### 14.5 資料模型提案（沿用既有結構）
- 生平欄位與任期的來源改接 `sources`：`leader_bio_field_citations`、`leader_record_citations`（格式同現有 citation 表）。
- 逐段生平：`leader_bio_paragraphs`＋`leader_bio_paragraph_citations`；未查證段落不進 DB（I6）。
- 參與：`person_event_participations`（`event_id` 或過渡用 `campaign_key`）＋引用表，至少一筆來源才能建立；不從政權參與方推導。
- 因果（P3）：`person_causal_claims`＋引用表，與參與**分表**。
- 照片：P1 實作改為**新增式** migration，在 `leader_bios` 加照片欄位（URL、來源頁、作者、授權代碼、授權證據 URL、署名），授權不在允許清單或欄位不全就不顯示（實作細節見設計文件 §11）。原 `media_assets` 提案延後。
- 不新建 `persons`、`sources` 等重複表；不替 D13（戰役欄位）拍板。

### 14.6 來源規則
- 已查證只依「接到 `sources` 的 citation」判斷；舊格式自由文字只當出處備註，不標已查證。
- 授權 metadata（`sources.license_code`）≠ 重製顯示的權利 ≠ 作為證據引用，三者分開記錄。
- 保留 A/B/C/X 來源分級（提案各 citation 表加可空 `grade`；值域依考證組既有約定，repo 目前無結構定義）。
- 日期保留半開區間：`end = 1945-10-01` 表示到 1945-09-30，顯示 `end − 1 天`。

### 14.7 待 Tai 決定
- 已決：Q4（P1 做照片，有授權來源才顯示，見 14.0）；Q1 暫不需要決定（戰役先不做）。
- 實作採用設計建議、未另行拍板：Q3 用 `leader_bios.id`（UUID）；Q2 採 (a)，重新整理後 sheet 選取／分頁／捲動不還原。
- 仍待決：Q5 人物生平引用是否套用現有授權允許清單（屬業務規則，需先改憲法）。細節見設計文件 §8。

### 14.8 人物介面 v2（2026-11-10 實作，分支 `feature/person-cards`）
- **同一人多角色合併一張卡**：依**人物 id**（`leader_bios.id`）合併該人的所有**角色**（元首、首腦、實際掌權者等皆為角色，見 16.3.3）；卡內每個角色一列（職位、任期、該角色自己的任期來源）；只有一個「查看詳情」。無法對到人物 id 的角色無法確認是同一人，各自一張。**現行實作**只讀 `leader_records.person_id`（`core/person-format.ts` `groupLeaders`），即目前只合併元首／首腦兩種角色；`leader_records` 與角色層 `person_roles` 的關係待決（16.9 T13）。
  - 修訂紀錄：原句為「依 `leader_records.person_id` 合併（`groupLeaders`）…沒有 `person_id` 的記錄無法確認是同一人，各自一張」；依 Tai 2026-11-11 10:03（T11／T12）改寫為依人物 id 合併角色，並註明現行實作。程式未改。
- **「人物」分頁數量**：樣式同「事件 N」，算**不重複人數**（`person_id`，沒有則以記錄計），沿用主要政權時算實際列出的人。
- **併入地沿用主要政權人物**：依主權紀錄既有的佔領歸屬 `occupation`（`occupation_attributions`：`controlKind = 'annexed'`、`occupierRegimeId`）判斷，**不比對名稱**；只在該地自己沒有領導人時沿用，另起一組並標示「沿用主要政權：<政權資料顯示名>」。民政／軍事管理的佔領區**不**沿用（避免把佔領方人物與當地首長混列；待 P2 軍政首長資料再議）。
- **人物詳情彈窗**：版面參考 Stitch 人物檔案稿（只取中間彈窗），配色沿用羊皮紙 `--wl-*` 變數（不採 Stitch 深藍／金）。區塊：頂列（檔案標記＋關閉）→ 標頭（照片 3:4／中性佔位、中文名、原文名、角色標籤、生卒）→ 區塊分頁籤（基本資料／生平／職位與任期／資料來源，吸頂、點了只捲對話框內容區）→ 基本資料格 → 生平（約 68ch、行高 1.9）→ 任期時間軸 → 底部「資料來源 (N)」。
- **來源呈現**：欄位值旁只放上標編號，不放完整連結；同一出處去重編號，底部列出「用於：欄位…」；點編號展開底部並捲到該筆。有值但缺來源的欄位在底部列「待補來源」。來源預設收合。舊格式出處仍標「出處備註，非查證標記」。
- **戰役／事件區塊**：目前沒有人物↔事件資料（14.0 第 3 點），不顯示該分頁，不放假資料。
- history／`?person=`／關閉後還原底層（選取、分頁、捲動、日期、鏡頭）沿用 14.4，未改。
- **Tai 決議（2026-11-10 15:51，Asia/Taipei）**，與現況做法一致，只補文件、程式不改：
  - 「沿用主要政權」標示用政權**正式名稱**（例如「德意志國」），不用簡稱（「德國」）。
  - **佔領區不沿用**佔領國人物（例如 Generalgouvernement 不列德意志國人物）；只有**併入地**（`controlKind = 'annexed'`）沿用。

## 15. 地理圖層（獨立未來提案）

> 狀態：📝 提案（2026-11-07），不阻擋 §14 人物工作。細節見 `docs/design/person-reading-campaign-nav.md` §10。

- 範圍：地形、河流、城市的地圖圖層。**不是**附近搜尋，**不是** RAG；現在不設計也不做搜尋／RAG。
- 現代高程底圖**不是歷史證據**，只作視覺背景並明示「現代地形，僅供參考」。
- 會變動的河道、海岸線、城市範圍與名稱要依時間（半開區間），隨時間軸篩選。
- 不得用無來源的現代資料代替歷史資料；沒有歷史來源就不顯示。城市名依憲法 §6「地名」規則。
- 來源沿用 `sources`；授權、重製權利、證據引用三者分開；R7 地圖授權規則適用。
- 不影響 §4 標籤規則與 §9 圖磚效能目標。現有戰役 JSON 用 OSM Nominatim（現代地名庫）定位據點，屬「地名對座標」，不是歷史地理證據，地理圖層上線時需在資料上區分。

## 16. 詳細人物生平資料結構（設計稿 v1，2026-11-10，待 Tai 確認）

> 狀態：📝 設計稿；B1 的 `leader_record_citations` 已套用到本機開發庫 5442（2026-11-10，見 16.7.1）；其餘仍只做設計或只寫檔。標記同 §14：**現有**＝已核對程式並附路徑；**提案**＝未實作、未拍板。
> 盤點依據（皆唯讀）：本文件 §7、§14；`docs/design/person-reading-campaign-nav.md` §5–§6；`data/seed/leaders/gap-830/{HANDOFF,WORKFLOW,SCHEMA}.md`；`backend/src/WorldLine.Api/Domain/{Entities,CitationPolicy,Vocabulary}.cs`；`backend/src/WorldLine.Api/Features/LeadersEndpoints.cs`；`frontend/src/app/core/api/world-line-api.ts`；`compose.yaml`。

### 16.0 開工三問與定位

**位置：milestone → module → 步驟**
- Milestone：**M4 資料**（人物生平屬資料補齊；§5 M4-b「人物小傳」的延伸），呈現端接 §14 人物閱讀（P1 已上線的人物卡／閱讀對話框）。
- Module：**§14 人物 → 詳細生平**（`leader_bios` 一人一筆的下層：段落、職位、事件關聯、出處、RAG 切段）。
- 步驟：本節是 **步驟 0「設計」**；實作分 B1–B5 階段（16.7），每階段各自要 Tai 核准。

**Q1 已做過嗎？**
- **已做（現有）**：`leader_bios`（生卒日＋`*_date_precision`、出生地、黨籍、`summary`、照片授權欄、`superseded_by`、`wikidata_qid`）；`leader_bio_field_citations`（逐欄位接 `sources`，有 `locator`、`evidence_note`、`accessed_on`、軟撤回）；`leader_records`（任期 SSOT，自由文字 `source`／`source_url`＋`verified`）；`historical_events`（`event_kind`、`parent_event_id`、`occurred` daterange、`date_precision`）；`event_citations`。路徑：`Entities.cs:9,149,209,325,357,406`。gap-830 已寫入 728 人、生平有效 923（HANDOFF 2026-11-10）。
- **只提過、沒做（提案）**：設計文件 §5.2 `leader_bio_paragraphs`、§5.3 `person_event_participations`、§5.4 `person_causal_claims`、§5.1 `leader_record_citations`、各 citation 表的 `grade`。本節**沿用這些名稱與方向**，補上欄位細節、出處模型、職位、RAG，不另起一套。
- **沒有人做過**：pgvector、chunk、embedding（§15 明說當時不做 RAG；本節只設計，仍不建）。
- 結論：不是重做；是把 §14.5／設計文件 §5 的提案收斂成可實作規格。

**Q2 與其他模組衝突嗎？**
- §7 資料規則（I1 拆段、I5 撤回重寫、I6 只寫 verified、半開區間、範圍 1908-01-01～1945-09-30）：全部沿用，無衝突。注意「範圍」只約束**地圖時間軸資料**；生平段落會超出範圍（出生、戰後），見 16.2 與已決 T6。
- §14.0-3「戰役先不做」：本節的事件／戰役關聯只定資料結構；**P1 介面仍不放任何戰役連結**，直到 Tai 另行解禁。
- D13（戰役欄位未決）：事件關聯沿用設計文件的 `event_id` 或過渡 `campaign_key` 二擇一，不替 D13 拍板。
- Q5（生平引用是否套授權允許清單）：未決；出處模型設計成兩種結果都能容納（16.4.4），不預設答案。
- §15 地理圖層：明文「不是 RAG」；本節 RAG 是人物文字檢索，不碰地圖圖層，不衝突。
- gap-830 流程（`SCHEMA.md` 的 P／S 格式、`run_batch.sh`）：新增欄位是**向後相容的超集**，舊批次格式仍可寫入（16.7）。
- 正式部署：PostGIS 映像 `postgis/postgis:18-3.6`（`compose.yaml:11`）**不含 pgvector**，RAG 上線前需換映像或自建擴充（待決 T8）。B1–B4 不需要 pgvector。

**Q3 如何驗收？（本設計稿本身）**
1. 本 commit 只動 `ARCHITECTURE.md`（`git show --stat` 只有一個檔）。
2. 每個提案表都能對應到 16.1 的需求 1–7；每個「現有」都附檔案行號。
3. 沒有任何一條規則跟 §7、§14.0、D13、Q5 的現狀矛盾（逐條見 Q2）。
4. Tai 逐條回覆 16.9；回覆前不進 B1。
- 實作後的驗收（每階段）列在 16.7。

### 16.1 設計原則

1. **一人一筆不變**：所有新表都掛在 `leader_bios.id`（下稱 `bio_id`）；不新建 `persons`（§14.5）。P2 軍事人物也用同一張表（設計文件 §5.5）。
2. **任期只有一個來源真相**：國家元首／政府首腦是**角色**（16.3.3）；其任期目前只存在 `leader_records`（現行實作），其他地方只「引用 id」，不重抄日期（16.3）。`leader_records` 是否即為角色層 `person_roles` 中這兩種角色的實作、是否遷移，待決（16.9 T13）；遷移前不得在別處另存一份。〔修訂紀錄：原句「國家元首／政府首腦任期只存在 `leader_records`；其他地方只『引用 id』，不重抄日期」；依 Tai 2026-11-11 10:03（T11／T12）改寫。〕
3. **沒有出處就不存在**：段落、職位、參與、影響，每一列至少一筆 citation 才能寫入（寫入層檢查，比照 I6）；欄位查不到或來源矛盾 → 留空並記錄原因，不猜（沿用 gap-830 `conflicts`／`unverified`）。
4. **參與 ≠ 影響**：兩張表；影響必須有**自己的**出處，不得沿用參與的出處或由參與推導（16.4）。
5. **事實表不可刪**：全部走軟撤回（`retracted_at`＋`retraction_reason`），修正用撤回重寫＋`superseded_by`（I5）。RAG chunk 屬可重建的衍生快取，另訂規則（16.5.4）。
6. **雙語 jsonb**：文字欄沿用 `{"zh-Hant": "...", "en": "..."}`（同 `leader_bios.summary`）。

### 16.2 生平事蹟：時間段落式敘事

**提案** `leader_bio_paragraphs`（沿用設計文件 §5.2 的名稱，補欄位）：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | uuid PK | |
| `bio_id` | uuid FK → `leader_bios.id` | |
| `ord` | int | 顯示順序；同一 `bio_id` 有效段落內唯一 |
| `period` | daterange NULL | 段落涵蓋期間，半開區間；整段無法定期間時 NULL |
| `period_start_precision`／`period_end_precision` | text NULL | `day`｜`month`｜`year`（同 `DatePrecisions`）；NULL＝該端未知 |
| `heading` | jsonb NULL | 短標題，例：「早年與教育」「第一次組閣」 |
| `body` | jsonb | 段落正文；1 段只講一個時期，建議 ≤ 400 字（同時是 RAG 切段上限，16.5.1） |
| `related_record_ids` | uuid[] NULL | 本段談到的任期（→ `leader_records.id`），只引用不重抄日期 |
| `superseded_by` | uuid NULL | 撤回重寫時指向新段落 |
| `retracted_at`、`retraction_reason`、`created_at`、`version` | | 同既有慣例 |

規則：
- 段落正文是「用自己的話改寫、只含來源寫到的事」（沿用 gap-830 `SCHEMA.md` 摘要規則），不抄長段原文。
- **一段內每個事實句都要能指到該段的某筆 citation**；做不到就拆段或刪句。可選擇在 citation 加 `claim_span`（被支撐的句子序號或字元區間，16.4）讓前端逐句標註；P1 先只做到逐段。
- `period` 可超出 1908–1945（出生、戰後），但**不進地圖時間軸篩選**；只在閱讀對話框顯示（已決 T6）。
- 現有 `leader_bios.summary` 維持「一句話簡介」角色，不拆；段落是另一層。前端沒有段落時照舊只顯示 summary。
- 未查證段落不進 DB，留在 `data/seed/**`（I6）；DB 裡不設 `draft` 狀態。
- B3 段落長度計法、結束日寫法等見 16.3.2（Tai 2026-11-11 09:35）。

### 16.3 職位任期（與 `leader_records` 的關係）

> 本節已依 Tai 2026-11-11 10:03（T11／T12）改寫，三層關係見 16.3.3；改寫前原句摘要見 16.3.3 修訂紀錄。

現況：`leader_records` 只收兩種角色（`head_of_state`｜`head_of_government`），是地圖「領導人分頁」的資料源，也是 gap-830 的連結目標（`recordIds`）。出處是自由文字欄 `source`／`source_url`。依 T11，元首／首腦是**角色**（角色層 `person_roles` 的 `role_kind`），`leader_records` 是這兩種角色任期的**既有實作**；它是否即為 `person_roles` 中這兩種角色的實作、是否遷移／如何遷移，待決（16.9 T13）。

**決策（提案）**：
1. **元首／首腦任期**（角色層）：在 T13 定案前，唯一儲存處仍是 `leader_records`（現行實作）。生平端（經歷層、段落）不另存這類任期；顯示時以 `leader_records WHERE person_id = bio_id` 取得（`GET /leader-bios/{id}` 已回 `terms`，見 `world-line-api.ts` `LeaderBio.terms`）。`de_facto_leader` 同屬角色層，存放處隨 T13 一併定。
2. **任期出處升級**：實作設計文件 §5.1 已提的 `leader_record_citations(id, record_id, source_id, locator, evidence_note, accessed_on, grade, retracted_at, …)`，格式同 `leader_bio_field_citations`。過渡期 `leader_records.source` 文字只當備註，不算已查證（§14.6）。
3. **經歷**（部長、議長、議員、地方首長、次官、軍職、黨職、駐外使節…）：**提案** `person_positions`（經歷層，生平經歷全集，16.3.2 第 3 點）。元首、首腦、實際掌權者屬**角色層**，經歷層不重複收（寫入層檢查：經歷層值域不含這三種；誤送這三種 → 拒絕並指向角色層，現行即 `leader_records`）。其他與角色層重疊的類別（閣員、將領、佔領／殖民長官）是否兩層都收，待決（16.9 T14）。

| 欄位 | 說明 |
|---|---|
| `id`、`bio_id` | |
| `regime_id` NULL → `regimes.id` | 任職政權；外國／國際組織職位可 NULL 並填 `organization` |
| `organization` jsonb NULL | 機關名（雙語），例：「外交部」「國際聯盟理事會」 |
| `title` jsonb | 職銜原文與中譯：`{"orig": "...", "zh-Hant": "...", "en": "..."}` |
| `position_kind` text | 經歷層值域，與角色層 `person_roles.role_kind` **分開命名**、不共用字串（16.3.2 第 3 點）；具體值域實作時再定（原提案 7 種僅供參考）；**不含**元首／首腦／實際掌權者（屬角色層） |
| `period` daterange、`start_precision`、`end_precision` | 同 16.2；任一端查不到就留無界並標精度 NULL，不猜 |
| `retracted_at`、`retraction_reason`、`superseded_by`、`created_at`、`version` | |

- 引用表 `person_position_citations`（格式同 16.4.1）。
- **地圖不讀 `person_positions`**；它只用在閱讀對話框的「經歷」區，不決定收錄與出卡（出卡由角色層決定）。這樣元首／首腦的任期不會有兩個來源。
- 若日後要把某種職位（例：軍事總司令）放上地圖，屬另案，需先改憲法。

### 16.3.1 人物範圍與 role_kind（Tai 2026-11-11 09:11 已決範圍；資料模型仍為提案）

> 狀態：✅ 範圍、門檻、排序、關聯規則已決（Tai 2026-11-11 09:11，Asia/Taipei：「7 題全照點子工坊建議，寫進 ARCHITECTURE §16」，見 16.9.1）；`person_roles` 表結構為**提案**，未實作、未建表。草案來源：點子工坊人物範圍草案（repo 內未追蹤檔，不入版控）。本節所有人數、工作量、倍數皆為**粗估**。
> 與 §14.8、§16.1、§16.3 既有條文的關係／差異另列於本次報告，**未改既有條文**；兩者不一致時，以本節記錄的 2026-11-11 決議為本次範圍，既有條文的調整另待 Tai 確認。
> 補註（Tai 2026-11-11 10:03，T11／T12 已決）：§14.8、§16.1-2、§16.3 已依三層分工改寫，見 16.3.3（含修訂紀錄 R1–R12）；上一行「未改既有條文」為 09:11 當時狀態，保留不刪。

**1. role_kind 分類**

| role_kind | 定義 | 收錄 | 階段 |
|---|---|---|---|
| `head_of_state` | 政權法定或事實元首（君主、總統、攝政、執政委員會主席） | 收（現有） | P1 |
| `head_of_government` | 政府首腦（首相、總理、行政院長、閣揆） | 收（現有） | P1 |
| `de_facto_leader` | 無正式元首／首腦頭銜但實際掌權者（如黨領袖、軍委主席） | 收；需 A／B 來源明說「實際掌權」 | P1 |
| `occupation_administrator` | 佔領區最高行政長官（總督、帝國專員、軍政長官） | 收 | P2 |
| `colonial_governor` | 殖民地／保護國總督 | 收（門檻同上類） | P2 |
| `military_commander` | 參謀總長、軍種總司令、方面軍／戰區司令 | 收（戰役人物） | P2 |
| `cabinet_minister` | 外交、國防／陸軍、財政、內政四部部長 | 有條件收：僅這四部 | P3 |
| `resistance_leader` | 革命、獨立、抵抗運動、流亡政府領袖 | 收；該運動需已在系統中為政權或事件 | P3 |
| `diplomat` | 大使、和約簽署代表 | **不收**為獨立人物；只在條約事件中以參與者出現 | — |
| `intellectual_cultural` | 思想家、作家、藝術家 | **不收**（無地圖錨點，範圍會失控） | — |
| `party_official` | 未掌權的黨幹部 | **不收** | — |

**2. 收錄門檻與來源**
- 共通：至少 1 筆 A 級或 2 筆獨立 B 級來源，證明「此人於某政權擔任該職及起訖日期」；C／X 不收（同已決 T1）；只有 verified 才上線（I6）。
- 元首／首腦／實際掌權者：任期與 1908–1945 有交集即收。
- 佔領／殖民長官：轄區必須是系統中已存在的政權或併入地；任期 ≥ 30 天。代理過渡另標 `acting = true`：收資料、不出卡，只在詳情列出（已決第 2 題）。
- 閣員：僅外交、國防／陸軍、財政、內政四部，且任期 ≥ 90 天。
- 將領：至少一筆有日期＋地點＋出處的戰役參與連結，或擔任國家級最高軍職。
- 抵抗／革命領袖：所屬組織需在系統中為政權、事件或戰役參與方。
- 生平期間可超出 1908–1945，只在詳情顯示；地圖與時間軸只用交集段（同已決 T6）。

**3. 一人多角色模型（提案）**
- 一人一筆不變：人物仍以 `leader_bios.id`（`bio_id`）識別（16.1-1、§14.5 不新建 `persons`）；草案中的 `persons.id` 在本 repo 即對應 `leader_bios.id`。
- **提案** `person_roles`：`id`、`bio_id`、`regime_id`、`role_kind`、`title_zh`、`title_orig`、`start_date`、`end_date`、`start_precision`、`end_precision`、`acting`（bool）、`source_ids`（NOT NULL）、`status`。實作時出處改用 16.4.1 統一 citation 表格式（`person_role_citations`），不以陣列欄位取代。
- 同一人同政權多段任期＝多列。卡片依 `bio_id` 合併（同 §14.8「多角色合併一張卡」）：職務顯示「最高位 role_kind＋次數」，任期依 `start_date` 列出各段。
- **卡片主標題排序**（取最高位者）：`head_of_state` > `de_facto_leader` > `head_of_government` > `occupation_administrator` > `colonial_governor` > `military_commander` > `cabinet_minister` > `resistance_leader`。
- 日期查詢以 `daterange(start, end)` 與當前日期取交集；`end` 為空表示「未知」，**不等於**在任，需標精度。
- 與 `leader_records`（16.3-1）、`person_positions`（16.3-3）的分工：依 T11／T12（Tai 2026-11-11 10:03）採人物／角色／經歷三層，見 16.3.3：本表為**角色層**（元首、首腦、實際掌權者皆在此層）；`person_positions` 為**經歷層**；`leader_records` 是現行元首／首腦任期的既有實作，是否即為本表這兩種角色的實作、是否遷移，待決（16.9 T13）。〔修訂紀錄：原句「分工：未定，見本次報告；本節不改 16.3 提案文字」；依 Tai 2026-11-11 10:03（T11／T12）改寫。〕

**4. 關聯規則**
- 人物↔政權：只經 `person_roles`（元首／首腦現況經 `leader_records`）；沒有角色的人不掛政權。
- 人物↔地圖：**人物本身不上地圖**。地圖只畫政權、事件、戰役，人物透過它們間接出現（同 §14.3「永不」）。
- 人物↔戰役：`person_event_links(role = commander | participant, source_id NOT NULL)`（**2026-11-11 統一：`person_event_links` 即 `person_event_participations`**，表名以後者為準；角色值域以 §19.3.1 為準）；參與不推論因果，因果只在 P3 `person_relations` 且需自有來源（16.1-4）。戰役 UI 仍受 §14.0-3「戰役先不做」與 T5 約束。
- **併入地**（`controlKind = 'annexed'`）：沿用主要政權的 `head_of_state`／`head_of_government`／`de_facto_leader`（維持 §14.8 現狀，新增 `de_facto_leader`）。
- **佔領區**：不沿用宗主政權元首／首腦（同 §14.8）；改顯示該區 `occupation_administrator`，並附一行「宗主政權：<政權正式名稱>」連結。
- **殖民地／保護國**：顯示 `colonial_governor`；宗主國元首只作連結，不作卡片。
- **流亡政府**：視為獨立政權顯示其人物，不與佔領區混列。

**5. 分階段與粗估**（數字皆為**粗估**，需以實際政權數重算）

| 階段 | 內容 | 粗估人數 | 粗估工作量 |
|---|---|---|---|
| P1 | 元首、首腦、實際掌權者（含 B3 生平） | 每政權平均 4–8 人，約政權數 × 6 | 查證約 20–40 分鐘／人 |
| P2 | 佔領／殖民長官、戰役將領（只綁已上線戰役） | 約 P1 的 50–80% | 將領需戰役資料先到位 |
| P3 | 四部閣員、抵抗／革命領袖、`person_relations` | 約 P1 的 1.5–3 倍 | 最大；可只挑主要強權 |

- P1 做完再估 P2，避免一次擴太大。

### 16.3.2 B3 生平段落寫法（Tai 2026-11-11 09:35 已決；資料模型仍為提案）

> 狀態：✅ 寫法已決（Tai 2026-11-11 09:35，Asia/Taipei：「Q1–Q10 和 7 條 §16 建議全照史料考證的建議，記進 ARCHITECTURE §16，不 push」，見 16.9.1）；Q6、Q8 另依 Tai 2026-11-11 09:30。來源：`data/seed/leaders/b3-sample/SUMMARY.md`（`747d06f`）的「待決問題」Q1–Q10 與「對 §16 的建議」1–7。本節只記錄 B3 段落與職位的寫法規則；表結構仍為提案、未建表。
> 與 §14.8、§16.2、§16.3、§16.3.1 既有條文的差異另列於本次報告，**未改既有條文**；不一致之處以本節記錄的 2026-11-11 09:35 決議為 B3 的寫法，既有條文是否改寫另待 Tai 確認（見本節第 6 點）。
> 補註（Tai 2026-11-11 10:03）：第 6 點兩項（T11、T12）已決，既有條文已改寫，見 16.3.3；上一行為 09:35 當時狀態，保留不刪。

**1. 段落正文**
- **長度（Q2／建議 1）**：中文 ≤ 400 字；英文等拉丁文字 ≤ 800 字元。兩者皆以 NFC 正規化後的字元（Unicode code point）計，與 16.4.1 `quote` 計法一致。本條補充並取代 16.2 `body`「建議 ≤ 400 字」與 16.5.1「段落上限 400 字」對英文未定義的計法；16.2、16.5.1 原文未改。
- **戰役／事件（Q1）**：段落提到的戰役或事件只寫在正文，**不**建 `person_event_participations` 或其他結構化資料；等 B4（需 T5 解禁、D13 定案）再處理。
- **範圍外的元首／首腦任期（Q4／建議 3）**：1908–1945 範圍外的元首／首腦任期（例：邱吉爾 1951–55、瓦加斯 1951–54）只寫在正文；不建職位、不動 `leader_records`，需要時再議。
- **範圍外的經歷（Q6）**：16.3.1 範圍外的經歷（議員、州長、次官、參謀長等）可寫進正文。

**2. 日期**
- **結束日寫法（Q3／建議 2）**：月／年精度的結束日寫成**下一個單位的起日**，再標該精度，與半開區間一致。例：「到 1911 年」→ 終點 `1912-01-01`＋`year`；「到 1911 年 5 月」→ `1911-06-01`＋`month`。這與 gap-830 現行 `YYYY-01-01`＋precision（把終點年本身排除在外）不同；B3 起適用本寫法，既有 seed 與已寫入資料不追溯改寫。
- **以名簿下一任起日當前任卸任日（Q7）**：可以，但屬**推論**，`evidenceNote` 必須寫明「依名簿下一任起日推得」；沒有下一任資料則留空，不猜。

**3. 職位**
- **`regime_id`（Q5）**：只有清楚落在 1908–1945 範圍內、且對得到系統中政權的職位才填 `regime_id`；其餘留空，改填機構名稱（`organization`）。
- **`person_positions` 與 `person_roles` 分工方向（Q6／建議 4）**：
  - `person_positions`＝**生平經歷全集**，只用在閱讀對話框的「經歷」區；可收 16.3.1「不收」或未列舉的類別（議員、地方首長、次官、參謀長、非四部閣員等）。
  - `person_roles`（16.3.1）＝**收不收、出不出卡**；16.3.1 範圍外的經歷不進 `person_roles`。
  - 兩表的值域**分開命名**，不共用同一組 `role_kind` 字串，避免混用（具體值域名稱實作時再定）。
  - 仍未決的部分見第 6 點。

**4. 出處**
- **同一來源多筆引文（Q10）**：同一段可有多筆同一來源、不同句子的 citation，每筆 `quote` 一句。
- **未評等來源（Q9）**：未評等來源（例：Archontology）只能當缺漏候選線索，放在 `leader_bio_gaps.candidate_citations`（seed 的 gap `candidateCitations`），**不能**當段落或職位的出處。
- **seed 的來源表示（建議 5）**：B3 seed 檔統一用頂層 `sources`（每筆一個 key）＋各 citation 以 `sourceKey` 引用，B3 寫入腳本依此格式解析。對應 16.4.1 `source_id → sources.id`。
- **防機器人驗證（建議 7）**：遇防機器人驗證（captcha 等）不繞過；只可改用**同一權威資料的官方鏡像**（例：GND → lobid），不可換成別的來源。屬 16.4.4 硬性排除層旁的作業規則。

**5. 研究檔與寫入前提**
- **`bioId`（建議 6）**：B3 研究檔（gap-830 `research.json` 的 P 格式）加 `bioId` 鍵：段落與職位是掛在**既有**生平（`leader_bios.id`）下，不是建立新生平。對應 16.7 P 格式的可選鍵 `paragraphs`、`positions`、`gaps`。
- **庫裡沒有有效生平的人（Q8）**：例如邱吉爾，先照 gap-830 流程補建有效生平（含範圍內任期），**寫庫前問 Tai**；在那之前 B3 段落只留 seed、`bioId` 為 null，不寫庫。

**6. 仍待決（本次不決定）**〔09:35 當時狀態；兩項已於 Tai 2026-11-11 10:03 決定，見 16.3.3〕
- 元首／首腦與 `de_facto_leader` 存在哪張表：`leader_records`、`person_roles`，或其他。→ ✅ T11 已決：三者皆為**角色**（`person_roles.role_kind`），人物與角色分表；`leader_records` 作為既有實作的定位與遷移另列 T13（未決）。
- 是否改寫 §14.8、§16.3 原文（含 16.3「`person_positions` 不得收元首／首腦」、16.3 原 7 種值域與寫入層拒絕規則、16.7 B3 驗收「`person_positions` 寫入元首／首腦被拒」），使之與 16.3.1 及本節一致。→ ✅ T12 已決：已改寫，修訂紀錄見 16.3.3。
- 以上兩項列於 16.9 T11、T12。

### 16.3.3 人物／角色／經歷三層（T11／T12 已決，Tai 2026-11-11 10:03）

> 狀態：✅ 三層分工已決（Tai 2026-11-11 10:03，Asia/Taipei，T11：「這三個可能是不同人，但可能是同一個人，對我來說這個是角色，角色跟人物似乎是不太依樣的表」；T12：「好」，同意改寫 §14.8／§16.3 原文）。表結構仍為**提案**，未建表；`leader_records` 定位未決（T13）。

| 層 | 實體 | 用途 | 備註 |
|---|---|---|---|
| **人物** | 既有 `leader_bios.id`（`bio_id`） | 一人一筆；生卒、照片、summary、段落都掛在這裡 | 不新建 `persons`（16.1-1、§14.5） |
| **角色** | 提案 `person_roles`（16.3.1 第 3 點） | 收錄、出卡、卡片主標題排序（16.3.1）；一個人物可有多個角色 | 元首 `head_of_state`、首腦 `head_of_government`、實際掌權者 `de_facto_leader` 都是此層的 `role_kind`，**不是人物的屬性**；元首與首腦可能是不同人，也可能是同一人 |
| **經歷** | 提案 `person_positions`（16.3-3） | 生平經歷全集，只在詳情「經歷」區顯示，**不決定出卡** | 值域與 `person_roles.role_kind` 分開命名；不重複收元首／首腦／實際掌權者 |

- **`leader_records`**：是現行元首／首腦任期的既有實作（地圖人物分頁資料源、gap-830 連結目標）。是否即為 `person_roles` 中這兩種角色的實作、是否遷移／如何遷移，**實作時先出遷移方案供 Tai 確認**（16.9 T13）；在那之前不改 `leader_records`、不另建一份元首／首腦任期。
- 卡片合併：依人物 id 合併該人的角色（§14.8；現行實作仍讀 `leader_records.person_id`）。

**修訂紀錄（依 Tai 2026-11-11 10:03（T11／T12）改寫）**

| # | 位置 | 原句摘要 | 改寫後 |
|---|---|---|---|
| R1 | §14.8 第 1 點 | 「依 `leader_records.person_id` 合併（`groupLeaders`）…沒有 `person_id` 的記錄各自一張」 | 依人物 id 合併角色；註明現行實作讀 `leader_records.person_id`（該處另有行內修訂紀錄） |
| R2 | 16.1-2 | 「國家元首／政府首腦任期只存在 `leader_records`」 | 元首／首腦是角色；任期目前只存在 `leader_records`（現行實作），定位待 T13（該處另有行內修訂紀錄） |
| R3 | 16.3 現況段 | 只述 `leader_records` 收兩種角色 | 補「元首／首腦是角色、`leader_records` 是既有實作、遷移待 T13」 |
| R4 | 16.3-1 | 「唯一來源真相仍是 `leader_records`。生平端不另存這類任期」 | 改為 T13 定案前唯一儲存處仍是 `leader_records`；生平端（經歷層、段落）不另存；`de_facto_leader` 存放處隨 T13 |
| R5 | 16.3-3 | 「其他職位（部長、議長、軍職、黨職、駐外使節…）：`person_positions`，**不得**收元首／首腦（寫入層檢查：若 `role_kind` 屬這兩種 → 拒絕並指向 `leader_records`）」 | 改稱經歷層（生平經歷全集）；元首／首腦／實際掌權者屬角色層、經歷層不重複收；拒絕時指向角色層（現行即 `leader_records`）；其他重疊類別待 T14 |
| R6 | 16.3 表 `role_kind` 列 | 「`role_kind` 值域（提案）：`minister`、`legislator`、`military_command`、`party`、`diplomat`、`judicial`、`other`；排除 `head_of_state`／`head_of_government`」 | 欄名改 `position_kind`，與 `person_roles.role_kind` 分開命名；值域實作時再定（原 7 種僅供參考）；不含元首／首腦／實際掌權者 |
| R7 | 16.3 「地圖不讀 `person_positions`」 | 「它只用在閱讀對話框的『經歷』區」 | 補「不決定收錄與出卡」 |
| R8 | 16.3.1 狀態說明第 2 行 | 「與 §14.8、§16.1、§16.3 既有條文的關係／差異另列於本次報告，未改既有條文…」 | 補註：已依 T11／T12 改寫，見本節 |
| R9 | 16.3.1 第 3 點末條 | 「與 `leader_records`（16.3-1）、`person_positions`（16.3-3）的分工：未定，見本次報告；本節不改 16.3 提案文字」 | 改為指向本節三層分工；`leader_records` 定位待 T13 |
| R10 | 16.3.2 狀態說明第 2 行、第 6 點 | 「未改既有條文…另待 Tai 確認」；第 6 點列 T11、T12 兩項仍待決 | 補註：T11、T12 已決，見本節；原文保留並標已決 |
| R11 | 16.7 B3 驗收 | 「`person_positions` 寫入元首／首腦被拒」 | 「`person_positions` 寫入元首／首腦／實際掌權者（角色層）被拒」 |
| R12 | 16.9 T3 狀態 | 「16.3 原提案文字未改」 | 補「16.3 原文已依 T11／T12 改寫（16.3.3）」 |

### 16.4 出處模型（每段落／每欄位可追溯）

#### 16.4.1 統一的 citation 欄位（所有新 citation 表共用）

格式承接**現有** `leader_bio_field_citations`（`source_id`＋`locator`＋`evidence_note`＋`accessed_on`），補四個欄位：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | uuid PK | |
| `<parent>_id` | uuid | 段落／職位／參與／影響／任期／欄位 |
| `source_id` | uuid → `sources.id` | URL、書目、出版者、授權都放在 `sources`（**現有**：`url`、`archive_url`、`title`、`authors`、`publisher`、`published_text`、`catalog_id`、`license_code`） |
| `locator` | text NOT NULL | 頁碼／條目／檔號／URL 錨點 |
| `quote` | text NOT NULL | 引文原文，≤ 80 字；這是「證據」，不是顯示用正文，只保留單句短引。**80 字以 NFC 正規化後的字元（Unicode code point）計，只在程式 `BioSourcePolicy` 檢查，不加 DB 約束**（Tai 2026-11-10 21:52：上限由 25 放寬為 80、改以字元計取代 text element；不加 DB 約束沿用主管 2026-11-10 裁定） |
| `quote_lang` | text NULL | 引文語言（BCP 47），可空、不檢查格式 |
| `evidence_note` | text NULL | 查證者說明（例：「BnF 與 GND 卒年不同，採 BnF」） |
| `accessed_on` | date NOT NULL | 當天實際打開的日期 |
| `grade` | text NULL | 來源等級；CHECK `grade IS NULL OR grade IN ('A','B')`（T1 定義；CHECK 依 Tai 2026-11-10 16:20 核准加上）；NULL＝未評等 |
| `date_precision` | text NULL | 這份來源支撐到的日期精度（`day`｜`month`｜`year`）；兩份來源精度不同時，欄位取**都支持的最粗精度**，不合併推高 |
| `claim_span` | int4range NULL | 選填：支撐段落中哪幾句（句序號，半開） |
| `policy_version` | text NULL | 寫入當時套用的來源政策版本（16.4.4） |
| `retracted_at`、`retraction_reason`、`created_at` | | I5 |

- **書目型來源（無 URL）**：`sources.url` NULL、`catalog_id`／`published_text` 必填，`locator` 寫頁碼；`accessed_on` 填實際翻閱日。
- 現有 `leader_bio_field_citations` 以**新增式 migration** 補上 `quote`（可空，舊列留空）、`grade`、`date_precision`、`policy_version`；不改既有欄位意義。
- B3 seed 的來源表示（頂層 `sources`＋`sourceKey`）、同來源多筆引文、未評等來源的用法見 16.3.2 第 4 點。

#### 16.4.2 矛盾與查無：留空並記錄原因

**提案** `leader_bio_gaps`（記「為什麼空」，避免下一輪重查，也讓前端顯示「來源矛盾」而非只有「待補」）：

| 欄位 | 說明 |
|---|---|
| `id`、`bio_id` | |
| `target` | `field:birthDate`、`field:deathPlace`、`position:<id>`、`paragraph:<topic>` 等 |
| `gap_kind` | `conflict`（來源互相矛盾）｜`not_found`（查無可開啟來源）｜`identity_uncertain`（身分推定） |
| `note` | 例：「BnF 1873 vs 遺稿清冊 1874」 |
| `candidate_citations` | jsonb：各說法的 source/locator/quote（**不是**資料值，只是證據並列） |
| `checked_on` | date |
| `resolved_at`、`resolved_by_citation_id` | 解決時填，不刪；`resolved_by_citation_id` 可能指向任一生平 citation 表，故不設 FK |
| `retracted_at`、`retraction_reason`、`created_at` | 登錄錯誤時軟撤回（16.1-5）；I5 trigger 禁 DELETE，撤回與解決皆不可撤銷 |

- 實作（B1，`BioCitationFieldsAndGaps`）：`target` CHECK 格式 `field:<LeaderBioFields>`｜`position:<id>`｜`paragraph:<topic>`｜`identity`；`gap_kind` CHECK 三值；`candidate_citations` 必須是 jsonb 陣列；`(bio_id, target, gap_kind)` 在「未解決且未撤回」範圍內唯一（回填可重跑不重複）。

- 欄位有 `conflict` 紀錄時，該欄**必須**為 NULL（寫入層檢查）。對應 HANDOFF「可回頭補強」清單的大量案例（例：Breisky 生卒地 GND vs ÖBL、Ali Maher 出生年三說）。
- `identity_uncertain` 但仍寫入者（例：Cebesoy、Jadambaa 由職銜推定身分）要在此記錄推定依據，前端可標「身分由職銜推定」。

#### 16.4.3 參與 vs 影響

沿用設計文件 §5.3／§5.4 的兩張表，補規則：

- **參與** `person_event_participations`：`bio_id`、`event_id` NULL → `historical_events.id`、`campaign_key` NULL（過渡，D13 定案後改 `event_id`；`CHECK num_nonnulls(event_id, campaign_key) = 1`）、`role`（提案值域：`commander`、`participant`、`signatory`、`decision_maker`、`present`、`other`）、`period` daterange NULL、軟撤回欄。引用表 `person_event_participation_citations`。**2026-11-11 統一**：表名一律 `person_event_participations`（16.3.1 的 `person_event_links` 即此表）；角色值域以 §19.3.1 為準（新增 `staff`）；D13 已決，`campaign_key` 過渡欄不再需要（§19.1.5）。
  - 只記「在場／擔任什麼角色」這種事實；**不**從 `event_participants`（政權參與方）或任期重疊推導。
- **影響** `person_causal_claims`（P3）：`subject_bio_id`、`object_type`（`event`｜`campaign`｜`regime`｜`bio`）、`object_id`、`claim_kind`（`acted`｜`influenced`）、`claim_text` jsonb、`perspective` text NULL（多觀點並列時標明是哪一派史學觀點）、軟撤回欄。引用表 `person_causal_claim_citations`。
  - **獨立出處**：寫入層檢查 (1) 至少一筆 citation；(2) 每筆 citation 的 `quote` 必須是**直接陳述因果／影響**的原文，不能只證明「他在場」；(3) 同一 `(source_id, locator)` 若已用於同人同事件的參與，不能單獨作為影響的唯一出處（同一頁同時講參與與影響時，要在影響 citation 另抄影響句的 `quote`）。
  - 沒有這樣的出處 → **不寫**，也不在 gap 表留「影響待補」（避免暗示有影響）。
- 參與與影響互不推導：有影響不代表有參與（例：遠端決策），有參與不代表有影響。

#### 16.4.4 來源白名單（Q5 未定，設計上可容納）

現況：`CitationPolicy.PrimaryLicenseAllowlist` 只擋控制紀錄與陣營的 primary citation（`CitationPolicy.cs:12`），生平未套用；gap-830 另有「不採 Wikipedia／Wikidata／百度、LoC 引自 Wikipedia 者不採、enciclopediadelecuador.com 已被接管」等**實務黑名單**，目前只寫在 HANDOFF。

**提案**：新增程式端 `BioSourcePolicy`（同 `CitationPolicy` 的形式，放 `Domain/`），以版本號管理：
- `policy_version`：例 `bio-2026-11-v0`。每筆 citation 寫入時記錄當時版本。
- 規則分兩層：
  1. **硬性排除**（現在就可以，不用等 Q5）：Wikipedia／Wikidata／百度百科當出處、已知被接管網域、「自製」來源（沿用 `IsSelfMadePublisher`）。這是 gap-830 已在執行的規則，只是把它從文件搬進程式。
  2. **白名單（Q5 決定後才開）**：(a) 若 Q5 選「套授權允許清單」→ 檢查 `sources.license_code ∈ PrimaryLicenseAllowlist`；(b) 若 Q5 選「不套用，另立史料白名單」→ 檢查 `sources.publisher`／URL 網域是否在白名單（白名單可另建 `source_allowlist(domain_or_publisher, grade_cap, note, decided_on)` 表或程式常數，待決 T2）。
- Q5 改變時**不改舊列**：以 `policy_version` 找出舊政策寫入的 citation，產出重審清單，不合格者走撤回（I5）。
- 「授權 metadata ≠ 重製權 ≠ 證據引用」三分（§14.6）維持：白名單管的是「能否當證據」，段落正文本來就是自己改寫，不涉重製。
- 遇防機器人驗證不繞過、只可改用同一權威資料的官方鏡像（例：GND → lobid），見 16.3.2 第 4 點。

### 16.5 後續 RAG（只設計，不建表）

目的：讓日後的問答／搜尋能以人物生平回答，且每個回答都能回指到 citation。

#### 16.5.1 切段單位（chunk）

| chunk 類型 | 來源列 | 內容組成 | 說明 |
|---|---|---|---|
| `paragraph` | `leader_bio_paragraphs` 一列 × 一語言 | 標頭行（人名、期間、heading）＋正文 | **主要單位**；一段一 chunk，不跨段，確保 chunk ↔ citation 一對多可直接映射 |
| `facts` | `leader_bios` 一列 × 一語言 | 由欄位**模板生成**的事實卡：姓名、生卒（附精度）、出生地、黨籍、summary | 欄位為 NULL 不寫；有 `conflict` 的欄寫「來源矛盾」而非任何值 |
| `tenure` | `leader_records`（同人全部）× 一語言 | 模板生成：政權、角色、職銜、起訖 | 只讀 SSOT，不另存日期 |
| `position` | `person_positions` 一列 × 一語言 | 模板生成 | |
| `participation`／`claim` | 各一列 × 一語言 | 模板生成；`claim` 帶 `perspective` | 影響 chunk 明示「史學詮釋」 |

- 段落上限 400 字（16.2）即為 chunk 上限；超過就在資料層拆段，不在 RAG 層硬切。
- 不把 citation 的 `quote` 放進 embedding 內容（避免外語短引文干擾），但放進 chunk metadata 供回答時引用。

#### 16.5.2 與出處的對應

**提案** `person_rag_chunks`（衍生表）：

| 欄位 | 說明 |
|---|---|
| `id` uuid | |
| `bio_id` uuid | 篩選用 |
| `chunk_kind` text | 16.5.1 類型 |
| `source_table`、`source_row_id`、`source_row_version` | 回指事實列；版本用來判斷過期 |
| `lang` text | `zh-Hant`｜`en` |
| `content` text | 實際送去 embedding 的文字 |
| `content_hash` text | `sha256(content)`，判斷是否需重算 |
| `citation_ids` uuid[] | 該事實列當下有效的 citation id；回答時據此列出處 |
| `period` daterange NULL | 讓檢索可依時間篩選（例：問 1938 年的事） |
| `embedding` vector(N) | N 依模型定（待決 T7） |
| `embedding_model` text | 例：`<provider>/<model>@<version>` |
| `embedded_at` timestamptz | |

- 回答規則（給日後 RAG 服務）：只能引用 `citation_ids` 內的出處；chunk 沒有 citation（理論上不會發生，因為事實列寫入時已強制）就不得作為回答依據。

#### 16.5.3 pgvector 欄位與索引建議

- 擴充：`CREATE EXTENSION vector`；需換成內含 pgvector 的映像（例：在 `postgis/postgis:18-3.6` 上加裝，或改用同時含 PostGIS＋pgvector 的映像），待決 T8。
- 索引：`HNSW (embedding vector_cosine_ops)`，建議 `m = 16`、`ef_construction = 64`，查詢時 `SET hnsw.ef_search = 40` 起調。資料量估算：923 人 × 平均 ~8 段 × 2 語 ≈ 1.5 萬列，量小，HNSW 建索引成本低；初期甚至可不建索引直接精確搜尋。
- 輔助索引：`(bio_id)`、`(lang)`、`(source_table, source_row_id)` B-tree；`period` 用 GiST（已有 `btree_gist`）。
- 多模型並存時：`embedding_model` 加入篩選條件，或每個模型一張 chunk 表，避免不同維度混在一欄。

#### 16.5.4 更新時重算 embedding 的策略

- **觸發**：事實列新增、撤回、撤回重寫（`superseded_by`）、citation 新增或撤回 → 該事實列的 chunk 標記過期（比對 `source_row_version` 或 `content_hash`）。
- **重算**：背景批次（不在寫入交易內呼叫外部模型）：重新生成 `content` → hash 相同只更新 `citation_ids`，不重算 embedding；hash 不同才重算。
- **撤回**：事實列撤回後，其 chunk 必須立即不可檢索。chunk 表是**可由事實表完全重建的衍生快取**，提案允許直接 DELETE（不屬 I5 保護的事實資料）；若 Tai 認為仍要軟刪，改加 `retracted_at` 並在查詢篩掉（待決 T9）。
- **換模型**：新模型寫新欄或新表，雙軌跑完比對後切換，舊的整批丟棄。
- **全量重建**：提供冪等腳本 `rebuild_person_chunks`（日後實作），可隨時從事實表重建，作為一致性檢查。

### 16.6 欄位補充：`leader_bios` 本身

只加、不改（新增式 migration）：
- `death_place` jsonb（現況只有出生地；HANDOFF 多處記卒地衝突，例 József、王正廷）＋對應 `field` 值 `deathPlace`。
- `leader_bio_field_citations.field` 值域加 `deathPlace`。
- 不加 `paragraph_count` 之類的冗餘欄；由查詢算。

### 16.7 遷移與相容性

**對現有人物卡片／前端的影響**
- `GET /leaders`（`LeaderBioSummary`）：**不變**。卡片照舊只用姓名、生卒、summary、照片。
- `GET /leader-bios/{id}`（`LeaderBio`）：**只加可選欄位** `paragraphs?`、`positions?`、`participations?`（戰役解禁前後端可先不回）、`gaps?`、`deathPlace?`。現有型別的欄位全保留；前端沒升級時忽略新欄位即可，不會壞。
- 閱讀對話框：有段落 → 顯示「生平」段落區（每段可展開來源，預設收合，§14.1）；無段落 → 照舊顯示 summary。`gaps` 用來把「待補來源」細分為「來源矛盾」「查無來源」。
- `field_sources`（自由文字 jsonb）：保留不刪；繼續只當備註，不算已查證。
- 地圖、時間軸、領導人分頁的篩選：**完全不讀新表**，零影響。
- gap-830 腳本：`research.json` 的 P 格式加可選鍵 `paragraphs`、`positions`、`gaps`；S 格式的 `evidence` 對應新欄 `quote`。舊批次不帶新鍵仍可照舊寫入。
- B3 研究檔另加 `bioId` 鍵（掛在既有生平下，不建新生平），見 16.3.2 第 5 點。

**分階段實作計畫**（每階段：備份 → dry-run → 寫入，只寫開發庫 5052；每階段前要 Tai 核准）

| 階段 | 內容 | 驗收 |
|---|---|---|
| B1 出處模型 | `leader_bio_field_citations` 補 `quote`／`grade`／`date_precision`／`policy_version`；新增 `leader_record_citations`、`leader_bio_gaps`、`death_place`；`BioSourcePolicy` 硬性排除層 | migration up/down 在本機乾淨庫通過；I5 trigger 測試（DELETE 失敗、撤回不可逆）；舊 API 回應快照不變 |
| B2 回填 | 把 gap-830 `bNN/research.json` 既有 `evidence` 回填到 `quote`、`conflicts`／`unverified` 回填到 `leader_bio_gaps`（只讀 seed 檔，不重新查證） | 計數比對：回填筆數＝seed 中有 evidence 的 citation 數；抽 20 人人工對照 |
| B3 段落與職位 | `leader_bio_paragraphs`、`person_positions` 與引用表；API 加可選欄位；閱讀對話框顯示段落 | 無 citation 的段落／職位寫入被拒；`person_positions` 寫入元首／首腦／實際掌權者（角色層）被拒（原句「`person_positions` 寫入元首／首腦被拒」，依 Tai 2026-11-11 10:03（T11／T12）改寫，見 16.3.3 R11）；前端單元測試＋4201 截圖 |
| B4 事件關聯 | `person_event_participations`；`person_causal_claims`（P3）。**需 Tai 先解除 §14.0-3「戰役先不做」** | 影響無獨立 citation 被拒；參與不會由政權參與方自動產生（測試） |
| B5 RAG | pgvector 映像、`person_rag_chunks`、重建腳本、重算批次 | 全量重建冪等（兩次結果 hash 相同）；撤回後 chunk 立即查不到；每個 chunk 都有 `citation_ids` |

#### 16.7.1 B1 進度（2026-11-10）

B1 拆成小步，每步各自 commit。`leader_record_citations` 已於 2026-11-10 依 Tai 16:20 核准套用到本機開發庫（5442／`worldline_borders_dev`，5052 API 所連）；`BioCitationFieldsAndGaps` 已於 2026-11-10 21:1x 依 Tai 17:51 核准套用 5442（見下方「套用 5442」）。

| 項目 | 狀態 | 檔案 |
|---|---|---|
| `leader_record_citations` | ✅ migration＋entity＋測試；✅ 已套用 5442（2026-11-10 16:2x） | `Infrastructure/Migrations/20261110080453_LeaderRecordCitations.cs`、`Domain/Entities.cs`（`LeaderRecordCitation`）、`Infrastructure/WorldLineDbContext.cs`、`tests/…/LeaderRecordCitation{Model,Guard}Tests.cs` |
| `leader_bio_field_citations` 補 `quote`／`quote_lang`／`grade`／`date_precision`／`policy_version`；field 值域加 `deathPlace`；兩張 citation 表 `grade` CHECK 只收 A、B | ✅ migration＋entity＋測試；✅ 已套用 5442（2026-11-10 21:1x） | `Infrastructure/Migrations/20261110082807_BioCitationFieldsAndGaps.cs`、`Domain/Entities.cs`、`Infrastructure/WorldLineDbContext.cs` |
| `leader_bio_gaps`、`leader_bios.death_place` | ✅ 同上 migration；✅ 已套用 5442 | 同上；`Domain/Vocabulary.cs`（`LeaderBioGapKinds`） |
| `BioSourcePolicy` 硬性排除層 | ✅ 程式＋單元測試 | `Domain/BioSourcePolicy.cs`、`tests/…/BioSourcePolicyTests.cs` |

`BioCitationFieldsAndGaps` 實作細節（第 2 段，2026-11-10）：
- `leader_bio_field_citations` 新欄全部可空（舊 4319 列不動）；`quote` 給了就不可空白（CHECK），**80 字（原 25 字，Tai 21:52 放寬）只在程式檢查**；`quote_lang` 可空、不檢查。
- `grade` CHECK `IS NULL OR IN ('A','B')`：同時加在 `leader_bio_field_citations` 與 `leader_record_citations`（後者已套用 5442、0 列）。
- `field` CHECK 以「先 DROP 再以超集重建」加入 `deathPlace`；這是 Up 腳本唯一的 DROP，既有資料全部仍合法。
- Down 只供開發／測試：已有 `deathPlace` 引用或 `death_place` 資料時 Down 會失敗或丟失該欄。
- `BioSourcePolicy`（版本 `bio-2026-11-v0`）：硬性排除網域 `wikipedia.org`、`wikidata.org`、`baidu.com`（含子網域，同 `send_batch.py` 的 `BANNED_HOSTS`）、`enciclopediadelecuador.com`（HANDOFF：已被接管）；出版者含 Wikipedia／Wikidata／百度或只標自製者排除；等級 NULL／A／B 可，C／X 依 T1 拒絕（訊息註明留 seed）；引文 ≤ 80 字（NFC 後字元；原為 ≤ 25 個 text element，Tai 2026-11-10 21:52 改）。「LoC 引自 Wikipedia」需看內容，程式無法判斷，仍靠人工。
- 「字」的計法：**NFC 正規化後的字元**（Unicode code point，C# `EnumerateRunes().Count()`、Python `len(unicodedata.normalize("NFC", s))`，兩者一致），不用 C# `char`（UTF-16 碼元，CJK 擴充 B 區字會算 2）。Tai 2026-11-10 21:52 決定取代原本的 Unicode text element 計法（`StringInfo.LengthInTextElements`）；差別只在 NFC 後仍無預組合字的組合符號與 emoji 序列（各碼點分別計數），gap-830 引文實務上不受影響。
- 寫入層尚未接上：現有 `POST /leader-bios/{id}/field-citations` 未改（API 零變動）；B2 回填與 B3 起的新寫入流程呼叫 `BioSourcePolicy`。「欄位有 conflict 缺口時該欄必須為 NULL」同屬寫入層檢查。

第 2 段驗收狀態：
- ✅ build 0 警告 0 錯誤；離線測試（不連任何庫）78 通過／0 失敗／0 略過：`BioSourcePolicyTests` 43、`BioCitationFieldsAndGapsModelTests` 15、`LeaderRecordCitationModelTests` 6（改為 grade 已有 CHECK）、其他離線 14。
- ✅ `BioCitationFieldsAndGapsGuardTests`（一次性 PostGIS 容器 `postgis/postgis:18-3.6`，非 5442）：9 通過／0 失敗／0 略過（2026-11-10 21:2x，Tai 17:51 核准）。

套用 5442（2026-11-10，Tai 17:51 核准；21:10 核准必要時重啟 OrbStack／5052）：
- 環境恢復：上次（20:50）docker 無回應；本次開工時 docker、5442、5052 均已恢復回應，**未重啟 OrbStack、未重啟 5052**（4200 `app_frontend` 也在同一 OrbStack，重啟會連帶影響，故不做非必要重啟）。容器狀態前後逐行相同（`.dev/containers-{before,after}.txt`，不進版控）。
- 備份：`~/wl-backups/worldline_borders_dev-20261110-211642-pre-b1-bio-citation-fields-and-gaps.dump`（107,228,146 bytes，`pg_restore -l` 274 項＝B1 備份 265 項＋`leader_record_citations` 9 項）。
- 套用方式同 B1：`dotnet ef migrations script 20261110080453_LeaderRecordCitations 20261110082807_BioCitationFieldsAndGaps` 產生單一交易 SQL，container 內 `psql -v ON_ERROR_STOP=1` 執行。套用後 `leader_bio_gaps` 0 列、`quote` 非 NULL 0 列；`leader_bio_field_citations` 4319、`leader_bios` 968、`leader_records` 2197 列不變。
- 5052 舊 API（未重啟）10 個 GET 端點：套用前取兩次一致（且與 B1 套用後快照一致），套用後逐位元比對 10/10 一致（`.dev/b2-api-snap/`，不進版控）。

`leader_record_citations` 實作細節（16.4.1 未明寫、實作時的取捨，Tai 可改）：
- `quote` NOT NULL、不可空白；**「≤ 80 字」（原 25 字）不加 DB CHECK**，由寫入流程（`BioSourcePolicy`）把關。
- `quote_lang` 可 NULL（varchar 35，BCP 47 長度上限），不檢查格式。
- `grade` varchar(1) 可 NULL，**不加 CHECK**：依 16.9.1 T1「考證組確認後再加 CHECK」；未確認前寫入一律留 NULL。
- `policy_version` varchar(32) 可 NULL，不做任何檢查（T2 未決，只預留）。
- `claim_span` int4range 可 NULL；CHECK 不可為空區間、下界 ≥ 0（T4 選填）。
- `date_precision` CHECK ∈ `DatePrecisions`。
- FK：`record_id` → `leader_records.id`、`source_id` → `sources.id`，皆 RESTRICT；兩欄各有 B-tree 索引。不設唯一約束（同一來源可在不同 locator 支撐同一任期）。
- I5 trigger `trg_leader_record_citations_guard`：禁 DELETE、撤回不可撤銷（同 `leader_bio_field_citations`）。
- 不改 `leader_records` 任何欄位；`leader_records.source` 過渡期照舊只當備註（§14.6）。API、前端、地圖零變動。

驗收狀態：
- ✅ `dotnet build` 0 警告；離線單元測試 `LeaderRecordCitationModelTests`（模型與 snapshot 無落差、欄位可空性、FK、CHECK、Up 為新增式且裝 I5 trigger、Down 只移除新表）通過。不連任何資料庫。
- ✅ `LeaderRecordCitationGuardTests`（一次性 PostGIS 容器：CHECK、FK、DELETE 失敗、撤回不可逆）：8 通過／0 失敗／0 略過。
- ✅ migration up/down（一次性容器 `postgis/postgis:18-3.6`，非 5442）：全套 up → down 到 `PersonPortraitAndFieldCitations`（表、trigger 函式、歷史列皆移除）→ 再 up，皆成功；down 後 schema 與「乾淨庫只套到前一版」逐行相同（唯一差異為映像在初始 DB 自動安裝的 tiger／topology 擴充，與 migration 無關）。
- ✅ 套用 5442 前已備份：`~/wl-backups/worldline_borders_dev-20261110-162234-pre-b1-leader-record-citations.dump`（107,222,947 bytes，`pg_restore -l` 280 項）。套用方式：`dotnet ef migrations script` 產生單一 migration 的 SQL（純新增：建表、2 索引、I5 trigger、歷史列），在 container 內 `psql -v ON_ERROR_STOP=1` 執行。套用後 `leader_record_citations` 0 列；`leader_records` 2197、`leader_bios` 968、`leader_bio_field_citations` 4319 列不變。
- ✅ 舊 API 回應快照不變：5052 只讀 GET 10 個端點（`/leaders?date=1939-09-01`、`/leaders?date=1945-09-15`、`/leader-bios/{id}` ×3、`/regimes/{id}` ×2、`/regimes/{id}/events`、`/sovereignty?date=1939-09-01`、`/sources/{id}`），套用前取兩次確認穩定，套用後逐位元比對 10/10 一致；5052 未重啟（快照存 `.dev/b1-api-snap/`，不進版控）。

#### 16.7.2 B2 回填：腳本與 dry-run（2026-11-10，未寫入）

依 Tai 2026-11-10 16:20 核准：只寫腳本＋dry-run，不寫入。腳本 `data/seed/leaders/gap-830/b2_backfill.py`；輸出 `data/seed/leaders/gap-830/b2_dryrun/{summary.md,report.json}`（明細含計畫寫入、跳過、衝突清單）。

- **只讀**：讀 49 批 `bNN/research.json`＋`sent.5052.json`；讀 5442 以 `default_transaction_read_only=on` 連線並先驗證生效；腳本內沒有任何寫入路徑；只允許 `worldline_borders_dev`。
- 對應鍵：seed 的 `S` ↔ 既有 `leader_bio_field_citations` 以 `(bio_id, field, source_id, locator, evidence_note＝evidence)` 比對（`send_batch.py` 寫入時把 `evidence` 存進 `evidence_note`）。回填只寫 `quote`，`evidence_note` 不動。
- seed 的 `field` 寫法不一，正規化規則（確定性、不推測）：斜線拆成多欄（`birthDate/deathDate`）；結尾括號或 `day` 視為限定詞（`birthDate (day)`）；`unverified` 的 `identity` → `target=identity`、`gap_kind=identity_uncertain`；其他不在值域者（`wikidataQid`、`regime`、`recordIds`…）跳過並列清單。

dry-run 數字（DB 狀態：B1 `leader_record_citations` 已套用、`BioCitationFieldsAndGaps` 未套用）：

| 項目 | 數 |
|---|---|
| seed 人物／staging | 706／59（staging 不在 DB，不處理） |
| seed citation（有值欄位的 S） | 4106；全部對到 DB 既有列（4106，無「DB 查無」） |
| **計畫回填 `quote`** | **841** |
| 跳過：evidence 超過 25 字（text element） | **3265**（中位數 61 字、P25 42 字、最長 169 字；≤ 40 字 757、≤ 60 字 1600） |
| 跳過：硬性排除來源 | 0 |
| C# 規則複核清單（Python 近似與 code point 數落在 25 兩側） | 0 |
| seed conflicts／unverified 條目 | 84／1062 |
| **計畫新增 `leader_bio_gaps`** | **904**（conflict 74、not_found 823、identity_uncertain 7） |
| 衝突：conflict 帶限定詞但 DB 該欄以較粗精度有值（違反「conflict 時該欄須為 NULL」） | 10（例：`birthDate (day)`，DB 存 `1872-01-01` 年精度） |
| 跳過：unverified 但 DB 該欄已有值 | 193（＋帶限定詞者 43） |
| 跳過：欄位不在值域 | 23；重複缺口 6 |
| DB 中屬這些人、但 seed 沒對到的 citation | 20（非 gap-830 研究檔寫入，不處理） |

驗收對帳：4106 ＝ 841（回填）＋ 3265（超長）；dry-run 兩次輸出逐位元相同；跑完 DB 計數不變。

寫入前待裁定的三點已由 Tai 2026-11-10 17:51 裁定（見 16.9.1「B2 寫入範圍」）：(1) 只回填 ≤ 25 字的 841 筆，3265 筆 `quote` 留 NULL、不截斷（重摘另案）；(2) 10 筆日精度爭議保留現有（年精度）值，另記 `conflict` 缺漏；(3) 236 筆「查不到但已有值」保留現有值，記 `not_found` 缺漏。

#### 16.7.3 B2 回填：寫入（2026-11-10，已寫入 5442）

依 Tai 17:51 核准範圍（21:10 再確認）。腳本加 `--write`：單一交易；前置檢查 `quote` 非 NULL 0 列、`leader_bio_gaps` 0 列（避免重跑疊加）；只 `UPDATE … SET quote`（限 `quote IS NULL`、未撤回、`evidence_note`＝該 quote 的列）與 `INSERT leader_bio_gaps`；交易內逐項核對筆數＝計畫數，不符即 RAISE（整筆回復）。需以 `--expect-quotes/--expect-gaps` 傳入人工核對過的預期值；有未處理衝突或需 C# 複核項目時拒絕寫入。不 DELETE、不改 `leader_bios`、`evidence_note`、`grade`、`policy_version`、`quote_lang`、`date_precision`（皆留 NULL）。

規則調整（對應 Tai 裁定）：
- conflict 帶限定詞（例 `birthDate (day)`）而該欄以較粗精度有值 → 保留現有值，仍記 `conflict` 缺漏，`note` 以「保留現有值：<值>；」開頭。「conflict 時該欄須為 NULL」放寬為：無限定詞者仍須為 NULL（本次 0 筆），帶精度限定詞者該欄可保留較粗精度值。
- unverified 而該欄有值 → 保留現有值，記 `not_found` 缺漏，`note` 同樣以「保留現有值：」開頭。
- 重複判定同 `ix_leader_bio_gaps_bio_id_target_gap_kind`（`bio_id`＋`target`＋`gap_kind`）。

預期值（寫入前以更新後的 dry-run 計算；兩次輸出逐位元相同；`b2_dryrun/` 為寫入前狀態）：

| 項目 | 預期 | 實際 |
|---|---|---|
| `quote` 回填 | 841 | 841 |
| 缺漏合計 | 904＋10＋236－重複 1＝**1149** | 1149 |
| └ `conflict`（其中保留現有值） | 84（10） | 84（10） |
| └ `not_found`（其中保留現有值） | 1058（235＝192＋43） | 1058（235） |
| └ `identity_uncertain` | 7 | 7 |
| 跳過：超過 25 字（`quote` 留 NULL） | 3265 | — |
| 跳過：欄位不在值域／重複 | 23／7（原 6＋`rs-petar-i` b05 同一 `birthDate` unverified 列兩次） | — |

對帳（寫入後，獨立於腳本以 SQL 查）：
- `quote` 非 NULL 的列 id 集合與計畫 841 筆逐一相同；`quote`＝`evidence_note` 全數成立；最長 25 字元；其他新欄位全為 NULL。
- `leader_bio_gaps` 的 (`bio_id`, `target`, `gap_kind`) 集合與計畫 1149 筆逐一相同；無 resolved／retracted。
- `leader_bio_field_citations` 4319、`leader_bios` 968、`leader_records` 2197、`leader_record_citations` 0 列不變；`death_place` 全 NULL。
- 抽 20 人（依 `md5(id)` 排序取前 20 個有缺漏者）以獨立程式直接讀 seed 原檔比對 quote 與缺漏欄位：20／20 一致。
- 5052 舊 API（未重啟）10 個 GET 端點與套用 migration 前快照逐位元比對 10／10 一致。
- 寫入前備份：`~/wl-backups/worldline_borders_dev-20261110-211940-pre-b2-write.dump`（107,235,667 bytes，`pg_restore -l` 281 項；已含 migration）。

#### 16.7.4 引文重摘（80 字，2026-11-10 起；22:28 核准後已寫入 5442，見 16.7.5）

依 Tai 2026-11-10 21:52（16.9.1「quote 上限 80 字」）。對象：16.7.3 中因超過 25 字而 `quote` 留 NULL 的 3265 筆。
- NFC 後 ≤ 80 字 → **直接採用**原 evidence 為 quote。
- > 80 字 → **重摘**：只從該筆原本出處的原文或已存 evidence 選 ≤ 80 字、逐字出現、能支持該欄位值的片段；不截斷（不取前 80 字）、不改寫轉述、不換來源。
- 找不到合適片段 → **留空**並列清單附原因。
- 產出放 `data/seed/leaders/requote-80/`；本階段不寫 5442（寫入另需 Tai 核准）。

結果（2026-11-10，全部完成；明細見 `requote-80/summary.md`）：

| 處理方式 | 筆數 |
|---|---|
| 直接採用（NFC ≤ 80 字） | 2266 |
| 重摘（> 80 字，取逐字片段） | 946 |
| 留空（附原因，`requote-80/blanks.md`） | 53（name 23、party 13、deathDate 9、birthDate 3、birthPlace 3、summary 2） |
| 合計 | 3265 |

- 對應：以 B2 對應鍵唯讀查 5442 取得 `leader_bio_field_citations.id`，3265 筆一對一、皆 `quote IS NULL`。
- 驗證：`requote.py build` 全量檢查 quote ≤ 80 字、逐字出現於 evidence、起訖不切字、非前 80 字截斷、重摘附依據、留空附原因。
- 抽查 48 筆（直接採用、重摘各 24）：可取得原文 40 筆全數逐字相符（2 筆僅 HTML 空白差異、1 筆 PDF OCR 差異）；8 筆原站 403 或需 JavaScript，無法核對；支持欄位值 46、部分支持 2（`requote-80/spotcheck.md`）。
- 判讀準則（重摘）：name 無該人名→留空；party 看不出本人所屬→留空；日期看不出是出生／死亡或精度不足→留空。辭典條目「人名 日期 地點 日期 地點」格式依位置判讀生卒（立陶宛、HLS 條目），待 Tai 確認。

#### 16.7.5 80 字引文寫入 5442（2026-11-10，已寫入）

依 Tai 2026-11-10 22:28 核准（考證組核對通過：3265＝直接採用 2266＋重摘 946＋留空 53）。腳本 `requote-80/write_quotes.py`；記錄 `requote-80/write/`（`pre-state.json` dry-run 與寫前狀態、`write-log.json`、`verify.json` 對帳、`api-compare.md`）。
- 範圍：`results/r01–r10.json` 中 method＝direct／requote 的 3212 筆寫入 `leader_bio_field_citations.quote`（id 對應，寫前 NFC）；留空 53 筆不寫。不碰 `leader_record_citations`。
- 方式：只連 5442／`worldline_borders_dev`（腳本白名單）；dry-run 唯讀連線，檢查將更新＝3212、id 全存在且 `quote IS NULL`（兩次輸出逐位元相同）；`--write --expect 3212` 須 DB 狀態與資料雜湊同 dry-run，單一交易以暫存表載入、只 `UPDATE … SET quote`（id 相符且 `quote IS NULL`），交易內核對受影響 3212、非空 quote＝寫前＋3212，不符即 RAISE 回復。
- 寫前備份：`~/wl-backups/worldline_borders_dev-20261110-224041-pre-requote80-quote-write.dump`（107,360,382 bytes，`pg_restore -l` 281 項）。
- 對帳（寫後，SQL）：3212 筆與結果檔逐筆相等（DB 值本已為 NFC）；非空 quote 841→4053（＝841＋3212）；全表 4319 列不變；除 quote 外各欄雜湊、非目標列 quote 雜湊、`leader_bios` 968／`leader_bio_gaps` 1149／`leader_records` 2197／`leader_record_citations` 0／`sources` 1206 皆不變；留空 53 筆仍 NULL；全表 `char_length(quote)` 最大 80。
- 5052（未重啟）10 個 GET 端點寫入前後逐位元相同：API 目前不輸出 `quote`，故生平端點亦不變（前端要顯示引文需另案改 DTO）。

### 16.8 風險

| # | 風險 | 處理 |
|---|---|---|
| R16-1 | A/B 等級沒有書面定義，各批各填各的 | T1 先定義；未定義前 `grade` 一律留 NULL，不推測 |
| R16-2 | 段落逐句可追溯的人工成本高 | P1 只要求逐段；`claim_span` 選填 |
| R16-3 | 生平期間超出 1908–1945 與憲法 §1 範圍的關係不明 | T6 已決（2026-11-10）：只在閱讀對話框顯示、不進時間軸；憲法 §1 已註記 |
| R16-4 | 換 DB 映像（pgvector）影響正式站部署 | 只在 B5 才需要；先在 5052 開發庫驗證 |
| R16-5 | 影響（因果）主張具爭議 | `perspective` 多觀點並列，每觀點各自附出處（設計文件 R8） |

### 16.9 要 Tai 決定（2026-11-10 部分已決，見 16.9.1）

| # | 事項 | 選項／建議 | 狀態 |
|---|---|---|---|
| T1 | 來源等級 A／B 的定義與是否只收 A／B | 建議：A＝官方檔案、國家級傳記辭典、權威機構人名權威（BnF、GND、ÖBL、SBL…）；B＝學術專書、具名作者的百科條目；C／X 不進 DB（留 seed）。需考證組確認後才加 CHECK | ✅ 已決：採建議 |
| T2 | Q5：生平引用要套授權允許清單，還是另立史料白名單？白名單存程式常數或 DB 表？ | 設計兩者都支援（16.4.4）；建議先上「硬性排除」層，白名單待憲法修改後再開 | ⏳ 未決，做到時再問 |
| T3 | `person_positions` 的 `role_kind` 值域 | 建議先用 16.3 的 7 種，`other` 兜底 | ✅ 已決（Tai 2026-11-11 09:11）：改採 16.3.1 的人物範圍與 role_kind（見 16.9.1）；16.3 原提案文字未改（2026-11-11 10:03 起：16.3 原文已依 T11／T12 改寫，見 16.3.3） |
| T4 | 段落是否要求逐句標註（`claim_span` 必填） | 建議 P1 選填，只逐段 | ✅ 已決：採建議 |
| T5 | 何時解除 §14.0-3「戰役先不做」以進 B4 | — | ✅ 已決（Tai 2026-11-11 13:15–13:16）：現在解禁，見 §19.7 Q2 |
| T6 | 段落期間可否超出 1908–1945（出生、戰後） | 建議可以，但只在閱讀對話框顯示、不進地圖時間軸；若同意需在憲法 §1 註明 | ✅ 已決：採建議（憲法 §1 已註記） |
| T7 | embedding 模型與維度（多語：中、英、原文人名） | B5 前再評估；本節不預設 | ⏸ 延後（隨 B5） |
| T8 | 正式站 DB 映像加 pgvector | B5 前決定 | ⏸ 延後（隨 B5） |
| T9 | RAG chunk 衍生表可否硬刪（不受 I5） | 建議可以（可完全重建）；否則加 `retracted_at` 軟刪 | ⏸ 延後（隨 B5） |
| T10 | B1–B5 的優先順序；B2 回填是否在 gap-830 補強批之前做 | 建議 B1→B2 先做，補強批（b50 起）直接用新格式 | ✅ 已決：採建議 |
| T11 | 元首／首腦與 `de_facto_leader` 存在哪張表（`leader_records`、`person_roles` 或其他） | 16.3.2 只定了 `person_positions`／`person_roles` 的分工方向，本項未提建議 | ✅ 已決（Tai 2026-11-11 10:03）：人物與角色分表，三者皆為角色（`person_roles.role_kind`），見 16.3.3、16.9.1；`leader_records` 定位另列 T13 |
| T12 | 是否改寫 §14.8、§16.3 原文，使之與 16.3.1、16.3.2 一致 | — | ✅ 已決（Tai 2026-11-11 10:03）：改寫，修訂紀錄見 16.3.3 |
| T13 | `leader_records` 定位：是否即為 `person_roles` 中 `head_of_state`／`head_of_government` 的實作；是否遷移、如何遷移（含地圖領導人分頁資料源、gap-830 `recordIds`、`leader_record_citations`、`groupLeaders`） | 實作 `person_roles` 前先出遷移方案供 Tai 確認；在那之前 `leader_records` 照舊、不另存一份 | ⏳ 未決 |
| T14 | 經歷層 `person_positions` 是否也收與角色層重疊的類別（閣員、將領、佔領／殖民長官等，元首／首腦／實際掌權者除外）；詳情「職位與任期」（角色）與「經歷」兩區是否合併顯示 | 本次未提建議 | ⏳ 未決 |

#### 16.9.1 決議紀錄（Tai 2026-11-10，經 World Line 主管轉達）

| # | 決議 | 依據 |
|---|---|---|
| T1 | 採建議：A＝官方檔案、國家級傳記辭典、權威機構人名權威（BnF、GND、ÖBL、SBL…）；B＝學術專書、具名作者的百科條目；C／X 不進 DB（留 seed）。考證組確認後再加 CHECK | Tai 15:18「1-4 依據建議」 |
| T4 | 採建議：P1 只逐段標註，`claim_span` 選填 | 同上 |
| T6 | 採建議：段落期間可超出 1908–1945（出生、戰後），但只在閱讀對話框顯示、不進地圖時間軸。業務憲法 §1 已註記 | 同上 |
| T10 | 採建議：先做 B1（出處表）→ B2（回填）；補強批（b50 起）直接用新格式 | 同上 |
| B5（RAG） | 延後：等詳細生平資料累積後再做；T7、T8、T9 屆時再決定 | Tai 15:19「好」 |
| T2、T3、T5 | 未決，做到時再問 | — |
| T1 補充 | `grade` CHECK 只收 A、B（兩張 citation 表），不再等考證組；C／X 由 `BioSourcePolicy` 硬性排除 | Tai 2026-11-10 16:20 核准第 2 段範圍 |
| quote 字數 | 25 字按字元計、只在程式檢查、不加 DB 約束；`quote_lang` 可空。實作採 Unicode text element（見 16.7.1）。**已由下一列取代上限與計法** | 主管裁定（同上） |
| quote 上限 80 字 | Tai 2026-11-10 21:52 決定上限 80 字，理由：來源區預設收合，只保留單句短引。以 NFC 正規化後的字元計（取代原 text element 計法）；仍只在程式檢查、不加 DB 約束。取代 21:36 的 25 字重摘範圍：B2 跳過的 3265 筆改依 80 字處理（≤ 80 直接採用原句、> 80 才重摘逐字片段、找不到留空），結果見 16.7.4；22:28 核准寫入 5442（3212 筆，留空 53 筆不寫），結果見 16.7.5 | Tai 2026-11-10 21:52；22:28 |
| B2 寫入範圍 | ≤ 25 字 841 筆回填 `quote`；超過 25 字 3265 筆留空、不截斷（重摘另案）；日精度爭議 10 筆保留現有年份、另記 `conflict`；查不到但已有值 236 筆保留現有值、記 `not_found`；其餘照 dry-run；欄位不在值域 23 筆、重複者跳過。結果見 16.7.3 | Tai 2026-11-10 17:51；21:10 再確認 |
| 16.7.3 放寬規則 | 沿用：conflict 帶精度限定詞（年份一致、只有日期不同）時可保留現有年份值，另記 `conflict` 缺漏；無限定詞者該欄仍須為 NULL。Tai 2026-11-10 21:36 已確認 | Tai 2026-11-10 21:36 |
| 辭典條目判讀 | 立陶宛歷史辭典與瑞士歷史辭典（HLS, Historisches Lexikon der Schweiz）條目依固定格式位置判讀生卒：格式為「人名、出生日期地點、去世日期地點」。此為位置判讀，不是自由改寫原文（回應 16.7.4 判讀準則的待確認項） | Tai 2026-11-11 08:18（Asia/Taipei）同意「辭典條目依固定格式位置判讀生卒，記進 §16.9.1」 |
| T3（role_kind 與人物範圍） | 7 題全採點子工坊建議，細節見 16.3.1：(1) `de_facto_leader` 併入 P1；(2) 代理任期（`acting`）收資料、不出卡，只在詳情列出；(3) 佔領區顯示佔領長官（`occupation_administrator`），並附宗主政權連結；(4) 閣員限外交、國防／陸軍、財政、內政四部，任期 ≥ 90 天，放 P3；(5) 將領需有帶來源的戰役連結，或擔任國家級最高軍職；(6) 不收外交官、思想文化人物、未掌權黨幹部；(7) 卡片主標題排序 `head_of_state` > `de_facto_leader` > `head_of_government` > `occupation_administrator` > `colonial_governor` > `military_commander` > `cabinet_minister` > `resistance_leader`。取代上列「T2、T3、T5 未決」中的 T3；`role_kind` 值域與 16.3 原提案（7 種）不同，16.3 原文與 §14.8 已決文字未改 | Tai 2026-11-11 09:11（Asia/Taipei）「7 題全照點子工坊建議，寫進 ARCHITECTURE §16，不 push」 |
| B3 段落寫法（Q1–Q10） | 全採史料考證建議，細節見 16.3.2：(Q1) 戰役／事件只寫正文，等 B4／T5；(Q2) 中文 ≤ 400 字、拉丁文字 ≤ 800 字元（NFC 字元）；(Q3) 月／年精度結束日寫下一單位起日（到 1911 年 → `1912-01-01`＋year）；(Q4) 範圍外元首／首腦任期只寫正文，不建職位、不動 `leader_records`；(Q5) 清楚落在範圍內且對得到政權才填 `regime_id`，其餘填 `organization`；(Q6) 16.3.1 範圍外經歷可寫正文、可記入 `person_positions`，不進 `person_roles`；(Q7) 名簿下一任起日可當前任卸任日，`evidenceNote` 註明「依名簿下一任起日推得」，無則留空；(Q8) 無有效生平者先照 gap-830 補建，寫庫前問 Tai；(Q9) 未評等來源只當 gap `candidateCitations`，不當出處；(Q10) 同段可有同來源多筆引文，每筆一句。16.2、16.3、16.3.1、§14.8 原文未改 | Tai 2026-11-11 09:35（Asia/Taipei）「Q1–Q10 和 7 條 §16 建議全照史料考證的建議，記進 ARCHITECTURE §16，不 push」；Q6、Q8 另依 Tai 2026-11-11 09:30 |
| B3 對 §16 的建議 1–7 | 全採，細節見 16.3.2：(1) 400 字計法同 Q2；(2) 結束日寫法同 Q3；(3) 範圍外元首任期同 Q4；(4) `person_positions`＝生平經歷全集、`person_roles`＝收錄與出卡，兩表值域分開命名（只定分工方向；元首／首腦與 `de_facto_leader` 存哪張表、是否改寫 §14.8／§16.3 原文仍未決，見 16.9 T11、T12）；(5) seed 來源統一用頂層 `sources`＋`sourceKey`；(6) B3 研究檔（P 格式）加 `bioId` 鍵，掛既有生平；(7) 遇防機器人驗證不繞過，只可改用同一權威資料的官方鏡像（GND → lobid），不換來源 | Tai 2026-11-11 09:35（Asia/Taipei） |
| T11、T12（人物／角色／經歷三層） | T11：人物與角色分兩張表，一個人物可有多個角色；元首（`head_of_state`）、首腦（`head_of_government`）、實際掌權者（`de_facto_leader`）都是**角色**（`person_roles.role_kind`），不是人物的屬性。人物＝既有 `leader_bios.id`；角色＝`person_roles`（收錄、出卡、主標題排序）；經歷＝`person_positions`（生平經歷全集，只在詳情「經歷」，不決定出卡，值域與 `person_roles` 分開命名，不重複收元首／首腦／實際掌權者）。T12：同意改寫 §14.8／§16.3 原文，已改寫，修訂紀錄見 16.3.3。取代上列「B3 對 §16 的建議 1–7」第 (4) 項括號內「存哪張表、是否改寫仍未決」之部分（該列原文保留）。`leader_records` 定位與遷移**未決定**，另列 16.9 T13；重疊類別另列 T14 | Tai 2026-11-11 10:03（Asia/Taipei）T11「這三個可能是不同人，但可能是同一個人，對我來說這個是角色，角色跟人物似乎是不太依樣的表」；T12「好」 |


## 17. 前端動效規格（GSAP）


> 狀態：✅ 已確認，P1 實作中（Tai 2026-11-11 13:15（Asia/Taipei）拍板：「改用 GSAP，移除 motion，其他小題照建議」；D0–D6 決議見 17.7）。草案由來：Tai 2026-11-11 13:08「GSAP 先寫動效規格進 ARCHITECTURE 給我確認，不改程式」。
> 與既有章節關係：只規範**表現層**，不改 §14.4 history／`?person=` 規則、§14.8 版面與互動、§16 資料層；§11／§14.0-3 戰役仍暫緩，本節只預留介面。
> **現況核對（寫入草案時）**：前端**已有**動畫套件 `motion`（`frontend/package.json` `"motion": "^14.8.0"`）與 `MotionService`（`frontend/src/app/core/motion.ts`：`reduced` signal、`MOTION_DURATION = { fast: 0.18, base: 0.26 }`、SSR／jsdom 無 `matchMedia` 時當作減少動態）；使用處：`regime-sheet.ts`（`SHEET_MOTION` in .35s `cubic-bezier(.16,1,.3,1)`／out .2s ease-in、`SheetState = closed|opening|open|closing`）、`legend.ts`、`top-bar.ts`、`atlas-map.ts`、`atlas.page.ts`。CSS：`styles.css` `.wl-map-scrim` 淡出 200ms＋reduced-motion 關閉；`wl-components.css` 120–150ms 顏色 transition。人物彈窗（`person-dialog.ts`）目前**無**開關動畫（`@if (personId())` 直接掛載／移除）；資料來源用 `[hidden]` 切換、箭頭 `transition-transform`。**已決（D0）：將以 GSAP 取代 `motion`，P1 實作中**；遷移完成後移除 `motion` 套件。

### 17.1 決策與 Angular 整合
- **套件**：npm `gsap`，只裝在前端專案 `frontend/` 本地依賴（不全域）；P1 實作時安裝（D0 已決）。只引 core（`import { gsap } from 'gsap'`），不引付費或多餘外掛；P1 不加 Flip（D5 已決）。授權：GSAP 3.13 起含外掛全部免費，但用的是 GSAP 自有「Standard License」而非 MIT，條款待安裝前再核對。
- **執行緒／變更偵測**：所有 tween／timeline 在 `NgZone.runOutsideAngular()` 內建立與執行；動畫回呼不寫 signal、不觸發變更偵測。需要通知 Angular 的只有「關閉動畫結束 → 移除 DOM」一處，用 `ngZone.run()` 或寫 signal 一次。
- **生命週期**：每個元件用 `gsap.context(() => {...}, hostEl)` 綁定 scope；`DestroyRef.onDestroy(() => ctx.revert())` 清掉 tween 與 inline style。不在全域選擇器（如 `.foo`）上動畫，一律傳元素參照（`viewChild`）。
- **SSR／測試保護**：只在 `isPlatformBrowser(PLATFORM_ID)` 且在 `afterNextRender` 之後才建立動畫；非瀏覽器、jsdom（無 `matchMedia`）、Vitest／Karma 一律走「直接到終態」路徑（沿用現有 `prefersReducedMotion()` 的判斷方式）。
- **集中服務**：沿用／擴充現有 `MotionService`（不另建第二個服務）：集中 reduced-motion 判斷、預設時長與 ease（17.3 表）、`timeScale` 開關、建立 context 的輔助方法。元件不直接 `import 'gsap'`，只經服務，日後換庫只改一處。
- **與既有 CSS transition 的取捨**：**並存（D1 已決）**——微互動（hover 顏色、按鈕狀態、箭頭旋轉、`.wl-seg-anim`、地圖 scrim）留 CSS；需要開關序列、可中斷、依狀態 reverse 的（彈窗、收合、列表進場、sheet）才用 JS 動畫。D1 已決：不全面取代。

### 17.2 套用範圍與優先順序
| 序 | 對象 | 現況 | 備註 |
|---|---|---|---|
| P1 | 人物彈窗開關（桌機中央彈窗、手機 `< md` 全螢幕）＋ backdrop | 無動畫 | 首要；需改成「關閉動畫完成才卸載」 |
| P2 | 資料來源收合／展開（`person-sources-panel`、`source-disclosure`） | `[hidden]` 立即切換 | D2 已決 (a)：不動高度、只淡入位移（見 17.5） |
| P3 | 人物卡列表進場（sheet「人物」分頁） | 無 | D4 已決：只在首次顯示該政權的人物分頁時播 |
| P4 | 側邊 sheet（`regime-sheet`） | 已用 `motion` | D0 已決 GSAP：與 P1 一併遷移，數值用 17.3 |
| P5 | 人物↔戰役頁轉場 | 無 | **只預留介面**（例如 `MotionService.pageTransition(from, to): Promise<void>`，預設 no-op）；不設計細節；戰役仍受 §14.0-3／T5 約束 |

### 17.3 數值表（D0–D6 已決，照建議值；開慢關快）
| 動效 | 開：時長／ease／幅度 | 關：時長／ease／幅度 | backdrop |
|---|---|---|---|
| 人物彈窗（桌機） | 240ms／`power2.out`／`opacity 0→1`、`scale 0.96→1`、`y 8px→0` | 160ms／`power2.in`／`opacity 1→0`、`scale 1→0.98` | 開 200ms `power1.out` `0→1`（現值 `bg-black/45`）；關 150ms `power1.in` |
| 人物彈窗（手機全螢幕） | 260ms／`power3.out`／`yPercent 100→0`（D3 已決：由下滑入；reduced-motion 時淡入） | 180ms／`power2.in`／`yPercent 0→100` | 同上（全螢幕時幾乎不可見，可省） |
| 資料來源展開／收合 | 200ms／`power2.out`／內容 `opacity 0→1`、`y -4px→0`（高度見 17.5） | 150ms／`power2.in`／反向 | — |
| 人物卡列表進場 | 每張 180ms／`power2.out`／`opacity 0→1`、`y 6px→0`；stagger 30ms；**只對前 8 張**做 stagger，第 9 張起與第 8 張同時出現；整體上限 ≤ 420ms | 不做退場（切換即替換） | — |
| 側邊 sheet | 350ms／`expo.out`（近似現行 `cubic-bezier(.16,1,.3,1)`）／`xPercent`（右）或 `yPercent`（底）100→0 | 200ms／`power2.in`／反向 | 無（非 modal） |
| reduced-motion（全部） | 只淡入 ≤ 120ms `none`／`power1.out`，或直接切換（D 預設：彈窗淡入 100ms，其餘直接切換） | 直接切換（0ms） | 直接切換 |

**中斷處理**
- 每個元件只持有**一條** timeline（例如彈窗：`tl = gsap.timeline({ paused: true })` 開序列）。開→關：未開完就關時 `tl.timeScale(開/關比例).reverse()`（同一條 timeline 反向，不另起新 tween）；關→開同理 `play()`。快速連點不疊加新動畫。
- **狀態以 Angular 為準**：`personId()`、`sourcesOpen()` 等 signal 立即改變；動畫只追隨終態。動畫失敗、被 kill 或 reduced-motion 時一律 `tl.progress(終態)` 收尾。
- **DOM 移除**：關閉時元件先進入 `closing`（與 `regime-sheet` 同模式），播完關閉動畫（≤ 180ms）才卸載；若在 `closing` 期間重新打開同一人，reverse 回開狀態、不重建；打開**另一人**或元件被路由銷毀時，`tl.progress(1).kill()` 立即結束並卸載，不等動畫。逾時保險：關閉超過 300ms 未完成則強制卸載。

### 17.4 無障礙
- `prefers-reduced-motion: reduce`：照 17.3 末列；`MotionService.reduced` 即時反映系統切換。
- **不等動畫的事**：焦點移入彈窗（`tabindex=-1` 的 panel／關閉鈕）、focus trap、Esc 關閉（由頁面統一處理，見 `person-dialog.ts` 註解）、`?person=` push／`history.back()`／`replaceUrl`（§14.4）、關閉後還原底層選取／分頁／捲動與焦點（§14.8）——全部在**狀態改變當下**同步執行，與動畫進度無關。
- **pointer-events 策略**：開啟中彈窗內容立即可點（不設 `pointer-events:none`）；`closing` 期間彈窗與 backdrop 設 `pointer-events:none` 並加 `inert`，讓點擊與鍵盤直接落到底層（同 `.wl-map-scrim.wl-scrim-hiding` 做法）；動畫元素不得蓋在可點元素上又攔截事件。
- 動畫只改 transform／opacity，不改點擊區尺寸；關閉鈕與來源點擊區 ≥ 44px（§14.8）在動畫各階段都成立（`scale ≥ 0.96` 時視覺略小，但只出現在開啟前 240ms）。

### 17.5 效能
- **只動 `transform`／`opacity`**；不動 width／height／top／left／margin／padding。
- **收合展開高度**：不直接 tween `height`。候選：(a) 不做高度動畫，只內容淡入＋位移，下方內容瞬間推開（最簡）；(b) CSS `grid-template-rows: 0fr→1fr`（會觸發 layout，但只在單一區塊）；(c) FLIP（量測前後位置，用 transform 補間，需 Flip 外掛或自寫）；(d) `clip-path` 裁切＋scale。**D2 已決 (a)**。
- **不和 MapLibre 搶主執行緒**：地圖 `movestart`～`moveend`（拖曳／縮放）期間不觸發非必要動畫（P3 列表進場延後或直接顯示）；不在 map render／`requestAnimationFrame` 迴圈內建立動畫；GSAP ticker 與地圖共用 rAF 但不在 map 事件回呼中做量測。`will-change: transform, opacity` 只在動畫開始時加、結束時移除（GSAP `force3D` 預設行為即可，不在 CSS 常駐）。
- **驗收指標**：開／關彈窗期間 Performance trace 無 > 50ms long task；中階筆電幀率約 ≥ 55fps；gsap core gzip 增量官方約 23–25 KB 級（**待實測**，以 `ng build` 前後 bundle 差為準），上限見 D6；只引 core。

### 17.6 驗收方式
- **Playwright**（`--workers=1`，沿用 4201 dev，不碰 4200）：開／關彈窗、來源展開、列表進場各階段截圖，或開 `video`／`trace` 記錄；桌機 1440 與手機 390 各一組。
- **reduced-motion**：`page.emulateMedia({ reducedMotion: 'reduce' })` 後驗證彈窗直接出現（或 ≤ 120ms 淡入）、無位移。
- **單元測試關閉動畫**：jsdom 無 `matchMedia` 已走終態路徑；另提供 `{ provide: MotionService, useValue: fake }`（現有做法）或注入 token（例如 `MOTION_SCALE`，測試設 0 → 時長 0），或 `gsap.globalTimeline.timeScale(1000)`。測試不得依賴真實時間。
- **e2e 穩定性**：`person-cards.e2e.ts` 不用 `waitForTimeout` 等動畫（現有 33、72 行的固定等待在實作時一併改）；改等可觀察狀態：`toBeVisible()`、`toHaveAttribute('data-motion-state', 'open')`（實作時在根元素輸出 `opening|open|closing`）、關閉後 `toHaveCount(0)`。截圖前等 `open` 狀態，或用 reduced-motion 模式截圖。

### 17.7 決議（已決，Tai 2026-11-11 13:15，Asia/Taipei）

Tai 原話：「改用 GSAP，移除 motion，其他小題照建議」。下表「建議」欄保留草案原文，以「決議」欄為準。

| # | 問題 | 建議（草案原文） | 決議（2026-11-11 13:15） |
|---|---|---|---|
| D0 | 前端已用 `motion`（sheet、圖例、頂列、地圖、頁面）；改用 GSAP 是「全面替換 `motion`」、「只新功能用 GSAP（兩庫並存）」或「維持 `motion`、本規格的時長／中斷／無障礙規則照套」 | 建議**擇一庫**，不並存：若無 GSAP 特有需求（複雜 timeline、Flip），維持 `motion` 成本最低；若確定用 GSAP，則 P1 起經 `MotionService` 逐步替換、最後移除 `motion` | **已決**：改用 GSAP，移除 `motion`（擇一庫，全面替換） |
| D1 | 是否全面取代既有 CSS transition | 不取代；微互動留 CSS，開關序列才用 JS（17.1） | **已決**：照建議，不全面取代 |
| D2 | 收合展開高度動畫方案 | (a) 不動高度、只淡入位移；之後覺得跳動再評估 (b) 或 Flip | **已決**：(a) 不動高度、只淡入位移 |
| D3 | 手機全螢幕：滑入（由下）或淡入縮放 | 由下滑入（與底部 sheet 一致、符合全螢幕頁面心智）；reduced-motion 時淡入 | **已決**：由下滑入；reduced-motion 時淡入 |
| D4 | 列表進場是否每次切分頁都播 | 只在首次顯示該政權的人物分頁時播；同政權切回分頁、換日期不播 | **已決**：照建議（P3 尚未實作） |
| D5 | 是否加入 Flip 外掛（免費） | P1 不加；D2 若選 FLIP 再加 | **已決**：P1 不加 |
| D6 | 套件大小上限 | gzip 增量 ≤ 30 KB（待實測）；超過則回到 D0 維持 `motion` | **已決**：gzip 增量 ≤ 30 KB，以 `ng build` 前後實測為準；超過則停下回報 |

### 17.8 自我檢查（2026-11-11，寫入時）
- §14.4：本節規定 history／`?person=` 與焦點還原不等動畫，無衝突。
- §14.8：來源預設收合（P2 只改表現，預設仍收合）、手機全螢幕（保留）、≥ 44px 點擊區（17.4）、羊皮紙配色（動畫不改色）——無衝突。
- §16（含 16.3.x 主標題排序）：純資料層，動畫不改排序與內容，無衝突。
- **與現況程式的落差**（非章節衝突，只列出）：已有 `motion`＋`MotionService`（D0）；`regime-sheet` 曲線為 `cubic-bezier(.16,1,.3,1)`，GSAP 無同名 ease，用 `expo.out` 近似或 CustomEase（外掛）；`person-cards.e2e.ts` 有固定 `waitForTimeout`。

---

## §19 戰役功能（設計稿 v2，2026-11-11，Q1–Q8 已決）

> 狀態：✅ 已決、⬜ 未實作、未建表。Tai 2026-11-11 13:15–13:16（Asia/Taipei）決定 Q1–Q8（見 19.7）。依據：憲法 §6「戰役」、Decision 4、§10（D13 已決）；本文件 §11.2、§12-4、§13、§14、§16.3.1、16.3.3、16.4.1–16.4.4、16.5、16.9.1。
> 標記：**現有**＝已核對程式；**沿用**＝既有已決條文照用；**新增／修正**＝本稿提案（已獲 Tai 同意方向，欄位細節實作時仍可微調）。
> T5 已由 Tai 2026-11-11 解禁（§14.0-3 已註記）；D13 採 A′。

### 19.0 定位與範圍

**已定規則（本稿前提）**
- G1 戰役是獨立頁。
- G2 人物和戰役雙向連結，返回時保留原本的日期、鏡頭、階段和捲動位置。
- G3 戰術概念不自動畫到地圖上。
- G4 參與戰役不等於造成結果。
- G5 `military_commander` 需要有出處的戰役連結，或擔任國家最高軍職。
- G6 來源等級 A／B 才進庫，C／X 不進庫，不用 Wikipedia。

**跟既有章節的關係**

| 既有條文 | 處理 | 說明 |
|---|---|---|
| 憲法 §6 戰役三條件、Decision 4 | 沿用 | 三條件寫進資料約束：至少兩個交戰方、要有目標地點、要有起訖日和地區。長期戰區拆成短期戰役 |
| §11.0 D-U5（不自動播放）、D-U6（手機全螢幕） | 沿用 | |
| §11.2 說明卡內容、三個圖層 `campaign-fronts/arrows/sites`、狀態機 `loading→ready(P1)→playing↔paused→ended` | 沿用 | 現有 `core/campaign.ts` 的 `CampaignPlayer` 照用；播放驅動改由 GSAP timeline（19.2.4） |
| §11.0 D-U4「主地圖本身進入戰役模式」、§11.2「不改 URL」 | **已取代** | 改成獨立路由 `/campaign/:slug`（G1）。頁內仍用 MapLibre 地圖，但跟主地圖分開實例。§11.0、§11.2 已加註 |
| §11.1 `events.geom` 等欄位 | **修正命名** | 實際表是 `historical_events`，已經有 `location` 欄位（**現有** `Entities.cs:158`）。本稿不新增 `geom`，精度和狀態欄位另議（§11.1 原案保留） |
| §12-4 手機戰役模式（戰役列、60vh 地圖、peek／half／full） | 沿用 | 搬到獨立頁 |
| §13 K1／K2 衝突小卡的「戰役簡報」按鈕 | 沿用 | 按鈕改成導向獨立頁 |
| §14.1 「戰役保留專屬頁、雙向連結、不自動上圖、參與與因果分開」 | 沿用，並具體化 | 本節 19.2、19.3 |
| §14.4 人物對話框 history 規則（`?person=`、只存一格返回目標） | 沿用並擴充 | 返回目標加上階段和捲動位置（19.2.5） |
| §14.0-3 戰役先不做、16.9 T5 | **已解禁** | Tai 2026-11-11 解禁（Q2），§14.0-3、16.9 T5 已註記 |
| 16.3.1 `person_event_links`、16.4.3 `person_event_participations` | **已統一** | 表名一律 `person_event_participations`；16.3.1 已註記 `person_event_links` 即此表；角色值域以 19.3.1 為準 |
| 16.4.3 參與 vs 影響 | 沿用 | 本稿只做參與。影響（`person_causal_claims`）仍是 P3，另表 |
| 16.4.4 `BioSourcePolicy` | **擴充更名（文件）** | 擴充並更名為通用 `SourcePolicy`（Q5）；本次只寫在文件，程式改名留到 C1 |

**範圍**
- 本稿處理：戰役資料模型、獨立頁 UI、人物↔戰役連結、來源規則、分階段計畫。
- 本稿不處理：長期戰區總覽頁、因果主張 UI、正式站同步（Decision 4 照舊：驗收後備份正式庫並 dry-run）。部隊（`battle_units`）只定資料結構，不做編制圖（OOB）UI。

---

### 19.1 資料模型（提案 DDL 草稿，未建表；D13 已決 A′）

**戰役是「多面向集合」**：一場戰役＝一筆 `historical_events` 主列＋以下關聯子表展開，不另建戰役主表，避免兩份事件真相。

| 面向 | 表／欄位 | 說明 |
|---|---|---|
| 主體 | `historical_events`（`event_kind='battle'`／`'campaign'`）＋1:1 `battle_profiles` | 19.1.1 |
| 階段 | `battle_phases` | 19.1.2 |
| 參戰政權 | `event_participants`（**沿用**，`role='belligerent'`） | 19.1.1 |
| 參戰部隊 | `battle_units`（**新增提案**） | 19.1.6 |
| 子事件 | `historical_events.parent_event_id` | 長期戰區（campaign）→ 戰役（battle）→ 子事件 |
| 所屬衝突 | `battle_profiles.conflict_record_id` → `conflict_records` | 19.1.1 |
| 結果與控制變化 | `battle_profiles.outcome_kind`／`outcome_text`／`control_change` | 19.1.1 |
| 人物參與 | `person_event_participations` | 19.1.5 |
| 影響 | `person_causal_claims`（另表，P3，跟參與分開） | 16.4.3、19.3.3 |
| 爭議數字 | `battle_figures` | 19.1.4 |
| 簡報圖幾何 | `battle_map_features`（PostGIS） | 19.1.3 |

**向量資料的定位**：關聯表與 PostGIS 是唯一真相。pgvector 只做敘述段落（階段說明、結果敘述等）的語意搜尋／RAG 索引，後期才建；向量列不掛出處、不當來源，查詢結果一律回到關聯表取出處顯示。對齊 §16.5（切段、重算、可重建）。

**19.1.1 戰役主體：沿用 `historical_events`（D13＝A′）**

**現有**：`historical_events(id, event_kind, parent_event_id, summary, occurred daterange, date_precision, time_note, location geometry, retracted_at…)`，`EventKinds` 已經有 `war`／`campaign`／`battle`。

戰役本身是一筆 `historical_events`，`event_kind = 'battle'`（短期戰役）。長期戰區用 `event_kind = 'campaign'`，再用 `parent_event_id` 掛底下多個 `battle`。戰役專屬屬性放 1:1 子表：

```sql
-- 戰役屬性（1:1 掛 historical_events，只有 event_kind='battle' 可掛）
CREATE TABLE battle_profiles (
  event_id        uuid PRIMARY KEY REFERENCES historical_events(id),
  slug            text NOT NULL UNIQUE,            -- 取代靜態 JSON 的 key，用在 /campaign/:slug
  name            jsonb NOT NULL,                  -- {"zh-Hant": "...", "en": "..."}（Languages.Supported）
  objective       jsonb NOT NULL,                  -- 憲法 §6 條件 (2)：要奪取、守住或突破的地點／防線／政權
  objective_kind  text NOT NULL CHECK (objective_kind IN ('place','line','regime')),
  theater_area    geometry(MultiPolygon,4326),     -- 條件 (3) 交戰地區；也當 fitBounds 依據
  conflict_record_id uuid NULL REFERENCES conflict_records(id),  -- 所屬衝突；不從衝突自動產生戰役
  outcome_kind    text NULL CHECK (outcome_kind IN ('decisive','indecisive','withdrawal','stalemate','other')),
  outcome_text    jsonb NULL,                      -- 結果敘述；沒有出處就留 NULL（前端顯示「待考證」）
  control_change  jsonb NOT NULL,                  -- 條件 (3)「控制範圍或戰線有變動」的說明，必填
  status          text NOT NULL DEFAULT 'pending' CHECK (status IN ('verified','pending')),
  retracted_at timestamptz, retraction_reason text, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON battle_profiles USING GIST (theater_area);
-- 寫入層檢查：event_kind='battle'；event_participants 中 role='belligerent' 的不同政權 ≥ 2（條件 1）
```

- 交戰方：**沿用** `event_participants(event_id, regime_id, role='belligerent')`。陣營色票從 `regime_alignments` 取，不從交戰關係推導（憲法 §6「陣營」）。
- 與 `conflict_records`：衝突是兩國之間的長期狀態（圖示、小卡），戰役是其中一段。`conflict_record_id` 讓 §13 小卡判斷要不要顯示「戰役簡報」按鈕。
- 整筆戰役的出處：**沿用** `event_citations`，起訖日、交戰方、地點由這張表支撐。

**19.1.2 階段**

```sql
CREATE TABLE battle_phases (
  id            uuid PRIMARY KEY,
  event_id      uuid NOT NULL REFERENCES battle_profiles(event_id),
  seq           int  NOT NULL CHECK (seq >= 1),
  name          jsonb NOT NULL,
  period        daterange NOT NULL,              -- 半開區間（§14.6）
  start_precision text NOT NULL CHECK (start_precision IN ('day','month','year')),
  end_precision   text NOT NULL CHECK (end_precision IN ('day','month','year')),
  summary       jsonb NULL,                      -- 沒有出處就留 NULL，不寫入待查證文字（I6）
  status        text NOT NULL DEFAULT 'pending' CHECK (status IN ('verified','pending')),
  retracted_at timestamptz, retraction_reason text, created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (event_id, seq) -- 只算未撤回列（partial unique index）
);
-- 寫入層檢查：階段的 period 必須落在 historical_events.occurred 內
```

- 現行 JSON 的 `early-month`（上旬）精度不在 `DatePrecisions` 裡：**已決（Q6＝a）**改寫成 `month` 精度，「上旬」寫進 `evidence_note`，不擴充值域。

**19.1.3 簡報圖幾何（PostGIS）**

```sql
CREATE TABLE battle_map_features (
  id            uuid PRIMARY KEY,
  phase_id      uuid NOT NULL REFERENCES battle_phases(id),
  feature_kind  text NOT NULL CHECK (feature_kind IN ('front','arrow','site')),
  side_regime_id uuid NULL REFERENCES regimes(id),   -- 戰線、箭頭屬於哪一方；據點可空
  geom          geometry(Geometry,4326) NOT NULL,
  label         jsonb NULL,
  geom_basis    text NOT NULL CHECK (geom_basis IN ('source_map','source_text','derived')),
  status        text NOT NULL DEFAULT 'pending' CHECK (status IN ('verified','pending')),
  retracted_at timestamptz, retraction_reason text, created_at timestamptz NOT NULL DEFAULT now(),
  CHECK ( (feature_kind='front' AND GeometryType(geom) IN ('LINESTRING','MULTILINESTRING'))
       OR (feature_kind='arrow' AND GeometryType(geom) = 'LINESTRING')   -- 方向＝線段起點→終點
       OR (feature_kind='site'  AND GeometryType(geom) = 'POINT') )
);
CREATE INDEX ON battle_map_features USING GIST (geom);
CREATE INDEX ON battle_map_features (phase_id, feature_kind);
CREATE TABLE battle_map_feature_citations (...);   -- 16.4.1 統一 citation 欄位
```

- SRID 4326。箭頭用 LineString 存，方向由點序決定，前端用 symbol 畫箭頭。
- `geom_basis`：`source_map`＝依出處地圖描繪（locator 寫圖號），`source_text`＝依文字描述定位，`derived`＝推論。`derived` 不得標 `verified`。
- **G3 落實**：這張表只收**出處明載**的戰線、進攻方向、據點。部隊番號、指揮官位置、戰術概念（例如「鉗形攻勢」）**不建幾何欄位**，只能出現在階段說明文字裡。前端不從文字或人物資料產生任何圖形。19.2.4 的疆界漸變中間形狀**不入庫**。
- 輸出：API 回傳 GeoJSON FeatureCollection，依 `feature_kind` 分成 fronts／arrows／sites，跟現行 `wl-campaign-web/0.1` JSON 的 `layers` 結構相容。日後可改成 PMTiles（§11 原註）。

**19.1.4 爭議數據（兵力、傷亡）**

```sql
CREATE TABLE battle_figures (
  id           uuid PRIMARY KEY,
  event_id     uuid NOT NULL REFERENCES battle_profiles(event_id),
  side_regime_id uuid NULL REFERENCES regimes(id),
  metric       text NOT NULL CHECK (metric IN ('strength','killed','wounded','missing','captured','casualties_total')),
  value_low    int NULL CHECK (value_low >= 0),
  value_high   int NULL CHECK (value_high >= value_low),
  value_text   jsonb NULL,                    -- 出處原話的範圍敘述（例：「約十萬」）
  perspective  text NULL,                     -- 出處立場或統計口徑（例：「日方戰報」）
  retracted_at timestamptz, retraction_reason text, created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (value_low IS NOT NULL OR value_text IS NOT NULL)
);
CREATE TABLE battle_figure_citations (...);   -- 每筆數字至少一筆 citation
```

- 一筆出處數字對應一列。不同出處各自一列並列，**不合併、不取平均**。

**19.1.5 人物連結（統一命名）**

```sql
CREATE TABLE person_event_participations (    -- 16.4.3 原提案；16.3.1 的 person_event_links 即本表
  id         uuid PRIMARY KEY,
  bio_id     uuid NOT NULL REFERENCES leader_bios(id),
  event_id   uuid NOT NULL REFERENCES historical_events(id),  -- D13 已決，不需要 campaign_key 過渡
  role       text NOT NULL CHECK (role IN ('commander','staff','participant','decision_maker','signatory','present','other')),
  side_regime_id uuid NULL REFERENCES regimes(id),
  phase_id   uuid NULL REFERENCES battle_phases(id),           -- 只參與某階段時填
  unit_id    uuid NULL REFERENCES battle_units(id),            -- 指揮或隸屬的部隊（19.1.6）
  period     daterange NULL,
  command_title jsonb NULL,                                    -- 出處寫的職銜，例如「第九集團軍總司令」
  retracted_at timestamptz, retraction_reason text, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE person_event_participation_citations (...);     -- 16.4.1；寫入層要求 ≥ 1 筆
```

- 跟 16.4.3 原值域相比，新增 `staff`（參謀），細節見 19.3。角色值域以 19.3.1 為準。

**19.1.6 參戰部隊（新增提案）**

```sql
CREATE TABLE battle_units (
  id             uuid PRIMARY KEY,
  event_id       uuid NOT NULL REFERENCES historical_events(id),
  side_regime_id uuid NOT NULL REFERENCES regimes(id),
  parent_unit_id uuid NULL REFERENCES battle_units(id),       -- 上級部隊（同一戰役內）
  unit_name      jsonb NOT NULL,                              -- 出處原名＋譯名
  unit_echelon   text NULL,                                   -- 層級（集團軍／軍／師…），值域 C1 時定
  status         text NOT NULL DEFAULT 'pending' CHECK (status IN ('verified','pending')),
  retracted_at timestamptz, retraction_reason text, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE battle_unit_citations (...);   -- 16.4.1 統一欄位；每支部隊至少 1 筆
```

- 指揮官**不**放在本表，經 `person_event_participations`（`role='commander'`、`unit_id`）連結。
- 部隊不建幾何（G3），不畫到地圖上。

**19.1.7 citation 格式**：所有新 citation 表都用 16.4.1 的統一欄位（`source_id`、`locator`、`quote ≤ 80`、`accessed_on`、`grade IN ('A','B')`、`date_precision`、`policy_version`、軟撤回）。I5：全部禁止 DELETE，只能軟撤回。

**19.1.8 C1 實作註記（World Line 戰役 bot，2026-11-11；migration `20261111053803_BattleC1`，只寫檔、未套用到任何資料庫）**

已建：`battle_profiles`、`battle_phases`、`battle_map_features`、`battle_units` 與 `battle_profile_citations`、`battle_phase_citations`、`battle_map_feature_citations`、`battle_unit_citations`（新增式，不改既有表；8 張表都有 I5 trigger）。`person_event_participations`、`battle_figures` 照計畫留到 C3／C4。跟 19.1 草稿不同的地方（待 Tai 確認）：

| # | 位置 | 草稿 | 實作 | 理由 |
|---|---|---|---|---|
| 1 | `battle_map_features` | 無 | 加 `feature_key text NOT NULL`（未撤回列唯一） | 對應 `wl-campaign-web/0.1` 的 `properties.id`；seed 重跑時用來比對，不重複寫入 |
| 2 | `battle_map_features` | 只有 `side_regime_id` | 加 `side_camp`（`allied`／`axis`／`soviet`／`contested`／`unknown`，可空） | 現行 JSON 的 `group` 是配色組，不是政權（例：`contested`）；不從配色組推導政權（憲法 §6「陣營」），`side_regime_id` 留空 |
| 3 | `battle_map_features` | 只有 `label` | 加 `props jsonb`（只供顯示：`from`／`to`／`unit`／`name`／`controller`／`date`／`note`／`vertices`／`geometry_refs`） | 保留前端顯示內容。**G3 待確認**：箭頭的 `unit`（部隊番號文字）照現行 JSON 帶在 `props` 裡，沒有建成幾何欄位；如果 Tai 認為違反 G3，C2 時移除 |
| 4 | 四張 citation 表 | `grade IN ('A','B')` | `grade NOT NULL` ＋ CHECK A／B；`quote NOT NULL` | 19.4.2「A／B 才進庫」；未評等的引用留在 seed（`grade_hint`），不寫庫 |
| 5 | `battle_profile_citations.field` | 「含 `field` 欄」 | 值域 `objective`／`control_change`／`outcome`／`theater_area`／`name` | 19.4.1 對照表 |
| 6 | API | `GET /campaigns/:slug` | `GET /api/v1/campaigns/{slug}`，外層照 PRD §7 `{statusCode,message,data}`，`data` 跟 `wl-campaign-web/0.1` 相容 | 跟既有 API 一致。`verified` 一律由 `status='verified'` 決定（C1 全部 pending → 都是 false）；`totals` 回 null（屬 C3 `battle_figures`）；`fronts_note`／`notes` 回 null／空陣列（屬 C3 `event_gaps`）；OSM 等座標參照（`gazetteer`）不是史實出處，不進 citation 表，放在 `props.geometry_refs` |
| 7 | `BioSourcePolicy` → `SourcePolicy` 改名（Q5） | C1 | **未做** | 本次派工範圍不含；人物 API 同分支有人在改，改名留給後續 session 協調 |

匯入：`tools/battles/import_campaign_seed.py` 把 `frontend/public/campaigns/dunkirk_1940.json` 轉成 `data/seed/battles/dunkirk_1940.seed.json`＋`dunkirk_1940.dry-run.md`（id 用 uuid5、不寫時間戳，可重跑、逐位元相同）。`objective`、`control_change`（NOT NULL）、起訖日與交戰方的 `event_citations`、每筆引用的 `accessed_on`、`sources.publisher` 在現行 JSON 都沒有，seed 留 null 並列入報表「寫庫前必補」；三條件考證結論出來前 status 一律 pending。

---

### 19.2 UI 流程

**19.2.1 入口**（production 繼續由 `CAMPAIGNS_ENABLED` 控制，到 C5 才開）
1. §13 衝突小卡的「戰役簡報」：該衝突至少有一筆已上線戰役時才出現。只有一筆就直接進入，多筆就展開清單。
2. 政權面板事件分頁的 ⚔ 卡片（`event_kind='battle'`）。
3. 人物詳情對話框的「戰役」區塊（19.3）。
4. 直接 URL `/campaign/:slug`。

**19.2.2 路由和 URL**
- `/campaign/:slug?phase=<seq>`：`phase` 跟著階段切換用 `replaceUrl` 寫回，重新整理時可以還原。
- 人物對話框在戰役頁上一樣用 `?person=<bio_id>`，跟 §14.4 一致。
- **已決（Q4＝b）**：主地圖的 `regime`（選取政權）、`tab`（sheet 分頁）加進 URL，重新整理與分享連結時可還原；捲動位置不存。

**19.2.3 頁面結構（桌機）**
- 頂列：← 返回（有返回目標時顯示原頁名稱，例如「返回 1937-08-13 地圖」）、戰役名稱、日期範圍。
- 左欄 360px 說明卡，內容順序照 §11.2：交戰方色票（點了回地圖並選取該政權）、目標、階段膠囊、播放控制、階段說明、兵力與傷亡（19.4.4 格式）、**人物**（19.3）、出處（預設收合）。
- 地圖：獨立 MapLibre 實例，`fitBounds(theater_area)`，三個圖層依 `phase` 過濾。政權疆界跟著階段變（19.2.4，Q7）。
- 不顯示主地圖時間軸。日期只跟著階段變。

**19.2.4 階段播放與疆界漸變（已決 Q7＝c，GSAP）**
- 沿用 `CampaignPlayer` 狀態機；不自動播放、停在 P1，每階段 3 秒，播完停在 ended。鍵盤 ←／→ 切換、空白鍵播放或暫停。
- **GSAP timeline 驅動**階段播放、暫停、跳轉（經 `MotionService`，對齊 §17 動效規格）；狀態仍以 Angular signal 為準，timeline 只追隨。
- 相鄰階段之間的政權疆界做**多邊形漸變（morph）**。插值方案（例如 flubber，或自寫頂點重採樣）於 C2 評估。約束：
  - (i) 漸變過程中的中間形狀一律以虛線／半透明樣式呈現，並標示「推估過渡，非史料」。
  - (ii) 播放停止或暫停在任一階段時，只顯示該階段**有出處**的疆界。
  - (iii) 漸變中間形狀**不入庫**、不可點選查詢。
  - (iv) 頂點數差異過大或拓撲不相容（例如分裂、合併、島嶼增減）時，退回交叉淡入淡出。
  - (v) 效能目標維持 55fps。
- `status='pending'` 的圖形用虛線，加上「待考證」圖例（沿用 JSON 的 `verified` 屬性做法）；跟 (i) 的「推估過渡」圖例分開標示。
- reduced-motion：不做 morph，直接切換到下一階段疆界。

**19.2.5 雙向跳轉和狀態保留（G2）**
- **地圖 → 戰役**：離開前存一份 `ReturnSnapshot`：
  `{ route:'atlas', date, lang, axis, camera:{center,zoom,bearing}, regimeId, sheetTab, sheetScrollTop, personId? }`
  放在記憶體 service，同時寫進 `history.state`，進戰役頁時 push 一筆 history。
- **戰役 → 人物**：在戰役頁開 `?person=`（push）。關閉時照 §14.4 的規則（確認前一筆是對應底層才 `back()`，否則 `replaceUrl`）。底層的階段、說明卡捲動、地圖鏡頭都不重建。
- **人物 → 戰役 → 返回人物**：進戰役前先關對話框，`ReturnSnapshot` 加上 `personId`、`dialogSection`、`dialogScrollTop`。按「返回」時恢復地圖狀態，再重新開對話框、捲到原位置。
- **戰役 → 戰役**（例如從人物的另一場戰役）：返回目標只存一格，重複巢狀時覆寫不累加（沿用 §14.4）。
- **瀏覽器上一頁**：從 `history.state` 讀 snapshot 還原。沒有 snapshot（例如直接開 URL）時，「返回」改成「開啟地圖」，日期用戰役起日。
- **重新整理**：URL 參數（`date`、`phase`、`person`、`regime`、`tab`）可以還原（Q4＝b）；捲動位置遺失。

**19.2.6 手機版（< 768px，沿用 §12-4）**
- 戰役列 48px（← 返回、名稱、ⓘ）。地圖佔上方 60vh，說明卡做成底部面板（peek 140px：膠囊＋播放控制／half／full），膠囊列可水平捲動，每顆至少 44px 高。
- 橫放（高 < 500px）時說明卡改放左側，寬 40vw。
- 人物對話框全螢幕（沿用 §14.1）。關閉後恢復底部面板高度和捲動位置。
- 判斷觸控用 `(hover: none) and (pointer: coarse)`。

**19.2.7 錯誤和空狀態**：載入失敗時只顯示文字摘要，不顯示圖層（沿用 §11.2）。某階段沒有 verified 圖形時，地圖只顯示疆界，加上提示「此階段尚無有出處的戰線資料」。

---

### 19.3 人物連結

**19.3.1 參與角色（`person_event_participations.role`；本表為角色值域的唯一依據）**

| role | 定義 | 文案 |
|---|---|---|
| `commander` | 出處明載擔任該戰役或其中一方某層級的指揮官 | 「指揮：第 X 軍（依出處職銜）」 |
| `staff` | 出處明載擔任參謀長、參謀職 | 「參謀」 |
| `decision_maker` | 出處明載下達發動、撤退等決定（例如元首、統帥部） | 「決策」。**只寫出處原述的行為，不寫影響** |
| `participant` | 出處明載在該戰役中服役或作戰，但沒有指揮職 | 「參與」 |
| `present` | 在場但不是戰鬥人員（例如觀察員、記者） | 「在場」 |
| `signatory` | 戰役結束時簽署停戰或投降文件 | 「簽署」 |
| `other` | 兜底，`evidence_note` 必填 | 依出處 |

- 不從 `event_participants`（政權參與方）、`leader_records` 任期或 `person_positions` 推導參與（沿用 16.4.3）。例如「蔣中正為國府元首」不能推出「參與淞滬會戰」。
- 一個人在同一戰役可以有多個角色、多段期間，分成多列。

**19.3.2 跟 `military_commander` 判定（G5）的關係**

`person_roles` 的 `military_commander` 只有符合下列其中一項才可以建立（寫入層檢查，結果記在 `person_role_citations.evidence_note`）：
- (a) 至少一筆 `person_event_participations`：`role IN ('commander','staff')`，連到 `status='verified'` 的 `battle_profiles`，且參與列本身有日期、地點（由戰役的 `location`／`theater_area` 提供）和 citation；或
- (b) 擔任國家最高軍職。**已決（Q3＝c）**：以**固定職位清單**為準（參謀總長、軍種總司令、統帥部長等，依政權逐一列出，清單 C1／C4 時由考證組整理、Tai 確認）；清單外者，出處明說其為「最高軍事指揮官」時以 `de_facto` 例外收錄，`evidence_note` 註明。這個職位要有 A 級或兩筆獨立 B 級來源（16.3.1 共通門檻）。

補充規則：
- 第 (a) 項只能證明「此人符合收錄資格」，**不代表**卡片會出現在戰役以外的地方。出卡規則照 16.3.1。
- `role='participant'`、`'present'`、`'decision_maker'` **不能**單獨支撐 `military_commander`。
- 戰役撤回或降回 `pending` 時，依賴它的 `military_commander` 列進入重審清單，不自動刪除（I5）。

**19.3.3 參與 vs 影響（G4）**

| | 資料 | 文案 |
|---|---|---|
| 參與 | `person_event_participations`，本稿 C4 範圍 | 中性動詞：「指揮」「參與」「在場」。區塊標題寫「參與人物」，不寫「關鍵人物」「功臣」「元凶」 |
| 影響 | `person_causal_claims`（16.4.3，P3，另表），本稿**不做 UI** | 未來另設「史家評價」區塊，標明觀點（`perspective`）和出處 |

- 戰役頁的「結果」欄（`outcome_text`）只敘述戰果和控制變化，**不得**出現人名當主詞的因果句（例如「因 X 的決策而勝利」）。寫入層用規則提示，考證組人工把關。
- 人物對話框的「戰役」區塊只列參與（戰役名、角色、日期、出處上標），排序依日期。不顯示勝負標記，避免讓人誤讀成個人戰績。
- 階段裡**不顯示人物位置**（G3）。人物只出現在說明卡清單，點了開對話框。

---

### 19.4 來源與考證規則

**19.4.1 逐欄位出處對照**

| 對象 | 出處表 | 最低要求 |
|---|---|---|
| 戰役存在、起訖日、交戰方、地點 | `event_citations` | 1 A 或 2 獨立 B，才能 `verified` |
| 目標、控制變化（`objective`、`control_change`） | `battle_profile_citations`（新增，16.4.1 格式，含 `field` 欄） | 同上；這是憲法 §6 條件 (2)(3) 的證據 |
| 結果 `outcome_*` | 同上，`field='outcome'` | 至少 1 B；沒有就 NULL |
| 階段的日期和說明 | `battle_phase_citations` | 每階段至少 1 筆；summary 逐段（`claim_span` 選填，同 T4） |
| 戰線、箭頭、據點 | `battle_map_feature_citations` | 每個 feature 至少 1 筆；`source_map` 要寫圖號或頁碼 |
| 參戰部隊 | `battle_unit_citations` | 每支部隊至少 1 筆 |
| 兵力、傷亡 | `battle_figure_citations` | 每列數字 1 筆 |
| 人物參與 | `person_event_participation_citations` | 至少 1 筆，`quote` 要直接陳述角色 |

**19.4.2 來源等級（G6，沿用 T1）**
- A：官方檔案（含軍方戰史、作戰日誌）、國家級傳記辭典、權威人名檔（BnF、GND、ÖBL、SBL…）。
- B：學術專書、具名作者的百科條目。
- C／X：不進庫，只能留在 seed 或 gap 的 `candidate_citations`。
- 硬性排除：**已決（Q5＝b）**`BioSourcePolicy` 擴充並更名為通用 `SourcePolicy`（人物、戰役共用一份版本號；本次只寫在文件，程式改名留到 C1）。排除 Wikipedia、Wikidata、百度百科、已被接管的網域、自製來源。遇到防機器人驗證不繞過，只能改用同一權威資料的官方鏡像（16.3.2-4）。
- 戰役特有：單一交戰方的官方戰報可以當 A，但用在數字時**一定要**填 `perspective`（例如「日方戰報」）。

**19.4.3 矛盾和查無**
- 沿用 16.4.2 的概念，提案新增 `event_gaps`（欄位同 `leader_bio_gaps`，把 `bio_id` 換成 `event_id`），`target` 例如 `field:occurred`、`phase:<seq>`、`feature:<id>`、`figure:<metric>`、`unit:<id>`。
- 日期矛盾：該欄位降到各出處**都支持的最粗精度**。如果連最粗精度都矛盾，就留空並記錄 `conflict`。
- 戰線查無：該階段不畫，記錄 `not_found`，前端顯示「此階段尚無有出處的戰線資料」。
- 戰役本身只有一筆 B（未達門檻）：留在 seed，不進庫（I6）。
- 憲法三條件中有任何一條沒有出處：**不能**建成 `battle`。可改用 `political` 或其他 `event_kind`，或者不收。

**19.4.4 傷亡等爭議數字的寫法**
- 每個出處一列，並列顯示，例如：
  「中方傷亡：約 18.7 萬（〔出處 1〕國府軍方統計）；25–30 萬（〔出處 2〕某學術專書估計）」
- 有範圍就寫 `value_low`–`value_high`；出處只有約數就填 `value_text`，不換算成整數。
- 不計算總和、不取中位數，也不從兩方數字推算「傷亡比」。
- 沒有出處就顯示「待考證」（沿用 §11.2），不顯示 0 或「不詳」以外的推測。
- 統計口徑不同時（是否含失蹤、平民），寫在 `perspective`，前端顯示在數字旁。

---

### 19.5 分階段實作計畫

> 每個階段都照「備份 → dry-run → 寫入」，只寫開發庫 5052／5442。任何寫庫前先問 Tai。

| 階段 | 產出 | 依賴 | 驗收 |
|---|---|---|---|
| **C0 決策（只有文件）** | ✅ Tai 2026-11-11 決定 Q1–Q8；憲法 §10 D13 改為已決；16.3.1 和 16.4.3 的表名統一註記；§14.0-3、16.9 T5 註記解禁 | 無 | 憲法和 ARCHITECTURE 修訂紀錄完整；`git diff` 只動文件 |
| **C1 最小一場（小）** | 1 場：**敦克爾克，試做範圍＝發電機行動（Operation Dynamo，1940-05-26～06-04）**（Q8）。`battle_profiles`、`battle_phases`、`battle_map_features`（`battle_units` 視資料而定）＋citation 表的 migration（新增式）；`BioSourcePolicy` 程式改名 `SourcePolicy`（Q5）；匯入腳本把現有靜態 JSON 轉成 seed（上旬改 `month`，Q6），再 dry-run；唯讀 API `GET /campaigns/:slug` 回傳跟 `wl-campaign-web/0.1` 相容的 JSON；前端改從 API 讀，**仍是現行主地圖模式**、仍只在 dev。**先由考證確認**發電機行動是否符合戰役三條件（交戰方、目標、起訖與地區）；若撤退行動單獨不符「戰役」定義，則以敦克爾克戰役為 `battle`，發電機行動為其階段（`battle_phases`）或子事件（`parent_event_id`） | C0 | dry-run 報表：每個 verified 欄位都有 A／B citation；三條件考證結論記入 seed；前端截圖跟現行 JSON 版本逐階段一致；e2e 通過；production 開關仍關 |
| **C2 獨立頁** | `/campaign/:slug?phase=` 路由、獨立地圖實例、`ReturnSnapshot` 和返回流程、`regime`／`tab` 進 URL（Q4）、手機版；GSAP timeline 播放與疆界漸變（Q7，含插值方案評估） | C1；§17 D0（已決：GSAP） | 從地圖進入再返回後，日期、鏡頭、選取政權、分頁、sheet 捲動完全一致（e2e 斷言）；漸變中間形狀樣式與標示符合 19.2.4 (i)–(iv)；360／390／768／1024／1440 截圖；55fps |
| **C3 補齊首批＋數字** | 現有 3 場（敦克爾克、閃擊波蘭、淞滬）全部入庫；`battle_figures`；`event_gaps` | C2 | 每場的爭議數字並列顯示；gap 清單交給考證組；抽查 5% verified |
| **C4 人物連結** | `person_event_participations`＋citation；人物對話框「戰役」區塊；戰役頁「參與人物」；`military_commander` 寫入層檢查（含 Q3 固定職位清單） | C3；16.9 T13（`person_roles` 先落地） | 人物 → 戰役 → 返回人物時，對話框區塊和捲動還原；沒有出處的參與無法寫入（測試）；文案檢查沒有因果句 |
| **C5 上線** | production 開啟 `CAMPAIGNS_ENABLED`；正式站同步 | C4；Tai 驗收 | 照 Decision 4：備份正式庫並 dry-run；Tai 確認 |

### 19.5.1 費用估計（粗估，World Line 戰役 bot 補，2026-11-11）

> 依據：本稿盤點＋起草實際花費 0.90 美元（本機 Claude Code，唯讀，13 輪）；先前 B1／B2 任務每個 session 上限設 1.5–3 美元。以下是每階段本機 Claude Code 的預算上限建議，不含考證 bot 的查證成本，實際以每次派工前回報為準。

| 階段 | 建議上限 | 說明 |
|---|---|---|
| C0 決策 | 0.5 美元 | 只改文件 |
| C1 最小一場 | 4–6 美元 | migration＋匯入腳本＋dry-run＋唯讀 API＋前端改讀 API，拆 2–3 個 session |
| C2 獨立頁 | 4–6 美元 | 路由、獨立地圖、返回流程、手機版、e2e |
| C3 補齊首批＋數字 | 3–5 美元 | 另需考證 bot 查出處，成本另計 |
| C4 人物連結 | 3–5 美元 | 依賴 person_roles 先落地 |
| C5 上線 | 1–2 美元 | 正式站備份與 dry-run 腳本 |
| 合計 | 約 16–25 美元 | |

---

### 19.6 風險

| # | 風險 | 處理 |
|---|---|---|
| R19-1 | ~~D13 一直沒決定，阻塞 C1~~ | 已解除：Tai 2026-11-11 決定 A′ |
| R19-2 | 戰線幾何很少有 A／B 出處明確描繪，大多是後人繪製 | 允許 `source_map` 以學術專書地圖當 B；`derived` 不標 verified；接受某些階段沒有圖 |
| R19-3 | 獨立頁和主地圖重複載入疆界圖磚，效能下降 | 共用 PMTiles 快取；獨立頁只載入 `theater_area` 範圍 |
| R19-4 | `history.state` 還原在 Safari／iOS 返回快取（bfcache）下行為不一致 | e2e 涵蓋 WebKit；snapshot 同時存在記憶體和 `history.state`，讀取時以後者為準 |
| R19-5 | 單一交戰方戰報偏頗，被當成中立事實 | 數字一定要填 `perspective`；文案並列顯示 |
| R19-6 | 「決策者」角色被讀成因果主張 | `decision_maker` 的 quote 只寫行為；區塊標題中性；影響延到 P3 |
| R19-7 | `military_commander` 依賴戰役，戰役進度慢就拖住 P2 人物 | 第 (b) 國家最高軍職路徑不依賴戰役，可以先做 |
| R19-8 | 長期戰區拆分粒度沒有統一標準 | 以憲法 §6 條件 (3)「控制範圍或戰線有變動」為切分點，考證組在 seed 寫拆分理由 |
| R19-9 | 疆界漸變的中間形狀被誤讀為史實 | 19.2.4 (i)–(iii)：虛線／半透明＋「推估過渡，非史料」標示；停在階段時只顯示有出處的疆界；中間形狀不入庫、不可點選 |
| R19-10 | 多邊形 morph 運算與 MapLibre 重繪拖慢幀率 | 預先在階段載入時重採樣頂點、不在每幀計算；只對 `theater_area` 範圍內政權做漸變；拓撲不相容或掉幀時退回交叉淡入淡出（(iv)）；驗收 55fps |

---

### 19.7 決議紀錄（Tai 2026-11-11 13:15–13:16，Asia/Taipei）

| # | 決議 | 日期 | 說明 |
|---|---|---|---|
| Q1（D13） | (A′) 沿用 `historical_events`（`event_kind='battle'`／`'campaign'`＋`parent_event_id`）＋1:1 子表 `battle_profiles` | 2026-11-11 | 戰役定位為多面向集合，展開子表見 19.1；新增 `battle_units` 提案；向量資料只做 RAG 索引，不當來源 |
| Q2（T5） | (a) 現在解禁 | 2026-11-11 | §14.0-3「戰役先不做」、16.9 T5 已註記；從 C1 開始 |
| Q3 | (c) 固定職位清單＋`de_facto` 例外 | 2026-11-11 | 19.3.2 (b)；清單由考證組整理、Tai 確認 |
| Q4 | (b) `regime`、`tab` 加進 URL | 2026-11-11 | 捲動位置不存（19.2.2、19.2.5） |
| Q5 | (b) `BioSourcePolicy` 擴充並更名為通用 `SourcePolicy` | 2026-11-11 | 只寫在文件，程式改名留到 C1（19.4.2） |
| Q6 | (a)「上旬」改寫成 `month` 精度 | 2026-11-11 | `evidence_note` 註明上旬，不擴充 `DatePrecisions`（19.1.2） |
| Q7 | (c) 疆界跟著階段播放即時變，GSAP 做疆界漸變 | 2026-11-11 | GSAP timeline 驅動播放／暫停／跳轉；morph 約束 (i)–(v) 見 19.2.4；風險 R19-9、R19-10。原建議 (a) 未採 |
| Q8 | (a) 敦克爾克，試做範圍＝發電機行動（1940-05-26～06-04） | 2026-11-11 | 三條件需在 C1 由考證確認；不符則敦克爾克戰役為 `battle`、發電機行動為其階段或子事件（19.5 C1） |
| C1b | 考證併入 seed：戰役主體改為「敦克爾克橋頭堡戰役」（`battle`，1940-05-26～06-04，半開終點 06-05），發電機行動為子事件（`parent_event_id`）；階段改為考證六段 P1–P6；A 級引文須在原文逐字找得到且 ≤80 字，否則 pending；箭頭部隊番號保留、標待查證；P6 無戰線圖不配圖形 | 2026-11-11 13:47 | Tai 確認。slug 維持 `dunkirk_1940`（與前端靜態檔、API 路徑相容）。待決：子事件 `event_kind` 值域沒有 operation；`objective_kind` 由人確認；比利時參戰至 05-28 的期間寫法（`event_participants` 無期間欄）。seed 仍全部 pending，寫庫需另行核准 |
| C2a-1 | `objective_kind` 填 `place`；`historical_events.event_kind` 值域新增 `operation`，子事件「發電機行動」改用 `operation` | 2026-11-11 14:52 | Tai 決定。新增式 migration `20261111065550_BattleEventKindOperation`（只放寬 `ck_historical_events_kind`，只寫檔、未套用任何資料庫）；`EventKinds.All`、匯入腳本、seed、dry-run 同步，C1b「待決」中前兩項結案；比利時參戰期間寫法仍待決 |
| C2a-2 | 戰役獨立頁 `/campaign/:slug?phase=` 實作（不含疆界 morph） | 2026-11-11 | Tai 14:54「開始」。前端先讀 `GET /api/v1/campaigns/{slug}`，失敗退回靜態 JSON 並在說明卡標示來源；⚔ 與衝突小卡入口改連獨立頁，主地圖內戰役模式不再有入口（舊 e2e skip）；`regime`／`tab` 進 URL；`ReturnSnapshot` 存記憶體一格＋地圖頁 history.state。實作取捨：階段無 verified 圖形時收起全部戰役圖層只留疆界；疆界為該階段起日 `/sovereignty` 的靜態外框；說明卡尚無「目標」「人物」欄（資料到 C3／C4）；轉場只做說明卡淡入（GSAP via MotionService），播放計時仍是 `CampaignPlayer`，GSAP timeline 驅動留 C2b |
