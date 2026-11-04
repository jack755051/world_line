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

> 狀態：草稿，待 Tai 確認。決策日期：2026-11-04。
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

> 狀態：✅ 四項已完成（2026-11-04）：1 事件卡片化 `fcefb0a`；2 面板寬度與響應式 `4ded751`；3 圖例浮動面板 `972a744`；4 面板停在時間軸上方 `08b9d3d`（含 §10 e2e）。單元測試 287 全過；e2e 110 過、76 略過（需 5051 或特定開關）。截圖 box `/workspace/wl-ui10/`（tiles、geojson 各 1440／1024 × 4 張）。⬜ 未做：小於 768px 時圖例改成 bottom sheet 分頁、卡片 hover 時地圖脈衝、戰役彈窗、標頭顯示首都、分頁改「概要／元首／事件／疆界」。以下為設計稿 `ui-timeline-sheet-legend.md` 原文照搬。

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
> 狀態：⬜ 開發中。以下為設計稿 `ui-sheet-v2.md` 原文照搬。

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
基準尺寸取自 §10：右側 sheet 寬 400px；底部時間軸 48px，在 900px 高的視窗中頂端位於 y=852。其他現有尺寸未重讀 repo，實作時再對照修正。

### 11.0 決定
| 編號 | 決定 |
|---|---|
| D-U1 (A1) | 一個事件只對應一個地點，不建 event_locations 表 |
| D-U2 (A2) | 沒有座標就不閃動，卡片上標「無座標」，不用其他位置代替 |
| D-U3 (A3) | 自動比對的座標先上線，標成待考證（geom_status=auto） |
| D-U4 (B1) | 主地圖本身進入戰役模式，左側放一張 360px 的說明卡 |
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
