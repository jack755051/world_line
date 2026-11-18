# 人物閱讀與戰役互連：設計文件

> **Tai 決定（2026-11-07 13:12，核准實作）**：(1) 「領導人」分頁改名「人物」，P1 只放領導人；(2) 補齊現有人物資訊、生平、照片；(3) **戰役先不做**——本文中所有戰役 UI、戰役連結、人物↔戰役關聯（§3.1 第 5 點、§4.4、§5.3、§5.7 的 `/events/{id}/people`、§8 Q1）全部延後，P1 不放任何指向戰役的連結；(4) 照已同意的 UI 做完。照片改為 **P1 就支援**（取代 §8 Q4 建議），有授權來源才顯示。實作採用的具體做法見 §11。以下 §0–§10 保留設計當時的原文。

> 版本：2026-11-07（台北時間）。分支 `feature/person-reading-design`，自 main `22c6e84` 開出。
> 性質：**只做設計，不實作**。本文件沒有改任何 UI／後端程式、沒有寫 DB、沒有匯入資料。
> 依據：`.claude/constitutions/world-line.md`（業務憲法，`in_review`）、`ARCHITECTURE.md`、點子工坊提案 `.dev/design-input-person-campaign-nav.md`（未追蹤檔，**它沒有看過 repo**，本文逐點核對過）、以及實際讀過的程式碼（下文附路徑與行號）。
> 標記：**現有**＝親眼核對過、附路徑；**提案**＝新增或變更，未實作、未拍板；**缺口**＝需求要用、但 repo 裡沒有。

---

## 0. 審查摘要（給 Tai 先看）

1. **點子工坊提案的資料模型大半不存在。** 提案寫「既有·待核對」的 `persons`、`person_roles`、`media`、`parties` 在 repo 裡**都沒有**。實際有的是 `leader_records`（任期）＋ `leader_bios`（一人一筆生平），用 `leader_records.person_id → leader_bios.id` 連起來。提案另外「新增」的 `sources` 表**早就有了**，不能再建一張。本設計改成：**沿用 `leader_bios`／`leader_records`／`sources`，只補欄位和引用表**，不發明重複結構。
2. **戰役「專屬頁」目前不存在。** 現有的是主地圖上的「戰役模式」（`CampaignService` 狀態機＋左側說明卡），沒有路由、URL 不變，而且 production 預設關閉（`CAMPAIGNS_ENABLED = isDevMode()`）。提案裡的 `/campaigns/:slug?phase=` 是新路由，等於戰役改版。依 Tai 的條件「P1 戰役整合以實際存在的頁面為準」，**P1 只連到現有的戰役模式**；要不要做獨立路由列為待決（Q1）。
3. **URL 現在只有 `date`、`lang`、`axis`（加上開發用的 `boundarySource`、`debug`）。** 沒有 `cam`，也沒有記錄選了哪個政權或哪個分頁。所以**重新整理會失去 sheet 的選取、分頁和捲動位置**，這是現況，不是新問題；本設計不假設 Tai 接受，列為待決（Q2）。
4. **提案的關閉規則不安全。** 提案寫「history 有本站上一筆就 back」——瀏覽器不允許檢查任意 history，而且「同站的上一頁」不一定是這個對話框底下的那一頁。本設計改成：**只有 app 自己標記過「緊接的前一筆就是對應的底層」時才 `history.back()`，其他情況一律 `replace` 只拿掉 `person` 參數**，`date` 等其他參數保留。
5. **來源：現有生平是「逐欄位」，但不是「逐段」，也沒有接到 `sources` 表。** `leader_bios.field_sources` 是 jsonb（每欄位一組 `{source, url}` 自由文字），`leader_records.source` 也是自由文字。要做到逐段溯源、預設收合、「待補來源」，需要把引用接到既有 `sources` 表（提案）。
6. **生平補齊：本次不寫任何資料。** 先做缺口盤點，再逐筆查證，照「備份 → 試跑 → 寫入」。

---

## 1. 現況核對表（現有 vs 缺口）

### 1.1 後端資料與 API

| 項目 | 狀態 | 證據（路徑） | 說明 |
|---|---|---|---|
| `sources` 表 | **現有** | `backend/src/WorldLine.Api/Domain/Entities.cs:9`（`Source`）、`Infrastructure/WorldLineDbContext.cs:49` | 欄位：`source_kind`、`title`、`publisher`、`authors`、`published_text`、`license_code`、`license_evidence_url`、`url`、`archive_url`、`local_copy_path`、`catalog_id`、`note`。`source_kind` 受控詞彙見 `Domain/Vocabulary.cs`（`map`、`atlas_map`、`treaty`、`official_record`、`trial_record`、`peer_reviewed`、`official_history`、`dataset`） |
| 引用表格式（citation） | **現有** | `Entities.cs:197–215`（`EventCitation`：`event_id, source_id, locator, evidence_note`）；`RegimeAlignmentCitation`（多一個 `role`） | 這是本專案標準的「紀錄 ↔ 來源」連結格式，新的引用表應照抄 |
| 授權允許清單 | **現有** | `Domain/CitationPolicy.cs`（`PrimaryLicenseAllowlist`：`us_federal_pd`、`pd_expired`、`cc0`、`cc_by`、`cc_by_sa`）；前端 `frontend/src/app/core/licenses.ts` | 目前用來擋控制紀錄與陣營的 primary citation。見 §6.4：授權 metadata 和「可不可以引用」是兩回事 |
| `historical_events` | **現有** | `Entities.cs:149`、`WorldLineDbContext.cs:197` | `event_kind`（`war, campaign, battle, treaty, armistice, surrender, political, atrocity`，`Vocabulary.cs`）、`parent_event_id`、`occurred`（daterange，必須有界）、`location`（geometry，選填）、`summary`（jsonb 雙語） |
| `event_participants` | **現有** | `Entities.cs:197` | 只有 `event_id, regime_id, role`——**參與方是政權，不是人物** |
| `event_citations` | **現有** | `Entities.cs:209` | 事件已能逐筆接 `sources` |
| `leader_records` | **現有** | `Entities.cs:325`、`WorldLineDbContext.cs:391` | `regime_id`、`person_id`（→ `leader_bios`，選填）、`name`、`name_zh`、`role`（`head_of_state`／`head_of_government`）、`title`、`valid_period`、`source`（**自由文字**）、`source_url`、`verified`、撤回欄位 |
| `leader_bios` | **現有** | `Entities.cs:357`、`WorldLineDbContext.cs:367` | `name`、`name_zh`、`birth_date`(+precision)、`death_date`、`birth_place`／`party`／`summary`（jsonb 雙語）、`field_sources`（jsonb，**逐欄位** `{source, url}` 自由文字）、`is_test`、撤回欄位。**沒有照片欄位、沒有 wikidata_qid、沒有 slug** |
| `GET /leaders?date=[&regime=]` | **現有** | `Features/LeadersEndpoints.cs:21,94`；回應 `LeaderFeature`（`WorldLine.Contracts/Dtos.cs:366`） | 只回傳**當天在任**的領導人，附生平摘要（不含 `fieldSources`） |
| `GET /leader-bios/{id}` | **現有** | `LeadersEndpoints.cs:23`；`LeaderBioDto`（`Dtos.cs:407`） | 完整生平含 `fieldSources` |
| `PATCH /leader-records/{id}/person` | **現有** | `LeadersEndpoints.cs:29` | 連結任期與生平 |
| `GET /events/{id}`、`GET /regimes/{id}/events` | **現有** | `Features/EventsEndpoints.cs:27–28` | 回應 `EventDto` 含 participants、citations |
| `GET /sources/{id}` | **現有** | `Features/SourcesEndpoints.cs:14` | 前端來源 popover 用 |
| `persons`、`person_roles`、`media`、`parties` | **缺口**（提案誤標為既有） | 全 repo `git grep` 無結果 | 不新建 `persons`／`person_roles`：與 `leader_bios`／`leader_records` 重複 |
| 人物 ↔ 事件／戰役的連結 | **缺口** | — | 目前人物與事件之間沒有任何連結資料 |
| 照片／媒體 | **缺口** | — | 沒有任何圖片資產結構 |
| 逐段生平 | **缺口** | — | `summary` 是一整塊 jsonb |
| A/B/C/X 來源分級 | **缺口（無結構欄位）** | 已追蹤檔案中查無；只在未追蹤的考證 seed 備註文字裡出現（例：「等級 A（官方統計年鑑）」） | 分級目前只活在考證流程的備註裡，DB 沒有欄位。本設計保留分級、不重新定義它（§6.3） |
| 戰役資料欄位（D13） | **未決**（憲法 §10、ARCHITECTURE §8.2） | — | 本設計不替 D13 拍板 |

### 1.2 前端

| 項目 | 狀態 | 證據（路徑） | 說明 |
|---|---|---|---|
| 路由 | **現有** | `frontend/src/app/app.routes.ts` | 只有 `''`（`AtlasPage`）、`version`、`**`（not-found）。**沒有戰役路由、沒有人物路由** |
| URL 參數 | **現有** | `core/atlas-state.ts:42`（`parseAtlasQuery`：`date`、`lang`、`axis`）；`pages/atlas/atlas.page.ts:768`（初始化時讀**一次** snapshot）、`:845–862`（之後用 `replaceUrl: true`＋`queryParamsHandling: 'merge'` 寫回）；`core/boundary-source.ts:38`（`boundarySource`）、`core/debug.ts:5`（`debug=1`） | **沒有 `cam`／鏡頭參數**；**不記錄選取的政權或分頁**。因為只讀一次 snapshot，瀏覽器上一頁／下一頁目前**不會**讓日期跟著變 |
| 右側／底部 sheet | **現有** | `shared/regime-sheet/regime-sheet.ts:35–36`（`sanring-sheet` 外殼，`role="dialog" aria-modal="false"`，桌機 right／手機 bottom，snap `peek/half/full`） | |
| sheet 分頁 | **現有** | `shared/sovereignty-card/sovereignty-card.ts:75`（`SovereigntyTab = 'overview' \| 'events' \| 'leaders'`）；狀態在 `atlas.page.ts:493`（`sovTab` signal） | sheet 關閉後分頁會重設為 `overview`（`atlas.page.ts:1022`）。**沒有保存捲動位置的機制** |
| 領導人分頁 | **現有** | `sovereignty-card.ts:142–225` | 依角色列出任期；有生平的名字是按鈕，**在 sheet 內原地展開**生平（`aria-expanded`）；生平各欄位後面有「來源」外連（取 `fieldSources[欄位].url`）；`verified=false` 顯示待查證；`leader.source` 直接顯示文字 |
| 人物卡（姓名／照片／職位／任期／查看詳情） | **缺口** | — | 現在是清單列，不是卡片，沒有照片、沒有「查看詳情」 |
| 大型閱讀對話框 | **缺口** | `frontend/src/app/components/ui/` 只有 `alert, badge, button, popover, sheet, skeleton, spinner, tabs, toast, tooltip` | **沒有 dialog／modal 元件** |
| 來源 popover | **現有** | `shared/citation/citation-popover.ts`（按鈕 `aria-expanded`、`aria-haspopup="dialog"`，顯示授權與授權證據連結） | 可沿用為「來源（n）」展開後的內容樣式 |
| 戰役 | **現有：主地圖「戰役模式」，不是頁面** | `core/campaign.ts:8`（`CAMPAIGNS_ENABLED` 預設 `isDevMode()`，production 關閉）、`:11`（靜態 `public/campaigns/<key>.json`，schema `wl-campaign-web/0.1`）、`:39`（狀態 `idle/loading/ready/playing/paused/ended/error`）；`shared/campaign-card/campaign-card.ts`；`atlas.page.ts:209–213`（說明卡）、`:551–563`（`openCampaign`／`closeCampaign`） | 進出戰役模式**不改 URL**；離開時程式只還原**日期**（`campaignSaved = { date }`），ARCHITECTURE §11.2 寫的「恢復地圖視角和 sheet 狀態」在程式中未見完整實作。目前 3 筆：`dunkirk_1940`、`poland_1939`、`shanghai_1937`（`frontend/public/campaigns/index.json`），三筆的 `event_ids` 都是空陣列，**沒有人物欄位** |
| 戰役日期格式 | **現有** | `public/campaigns/index.json` | 同時存 `end`（不含當天，例 `1939-10-07`）與 `end_inclusive`（`1939-10-06`），符合半開區間規則 |
| Esc 處理 | **現有** | `atlas.page.ts:751–755` | 依序關戰役模式、衝突小卡 |

---

## 2. 點子工坊提案逐點核對

| 提案內容 | 判定 | 修正 |
|---|---|---|
| 分頁改名「人物」、P1 只放領導人 | ✅ 採用 | 沿用現有 `leaders` 分頁的資料（`GET /leaders`），分頁 value 是否改名屬實作細節 |
| 人物卡：姓名／照片／職務／任期／查看詳情 | ✅ 採用（Tai 已確認） | 照片目前**沒有資料結構**；無照片或照片授權不明時顯示中性佔位圖，不抓網路圖片（Q4） |
| `persons`、`person_roles`、`media`、`parties`「既有·待核對」 | ❌ **不存在** | 以 `leader_bios`（人）＋ `leader_records`（任期）取代；`party` 已是 `leader_bios.party` jsonb |
| 新增 `sources(...)` | ❌ **重複** | 已有 `sources` 表，直接用 |
| `paragraph_sources(paragraph_id, source_id, locator)` | 🔧 方向對、格式改 | 照現有 citation 表格式：`(paragraph_id, source_id, locator, evidence_note)` |
| `person_event_links(... source_id NOT NULL)` | 🔧 方向對 | 拆成連結本體＋引用表（照 `event_citations` 格式），可以多來源；見 §5 |
| P3 `person_relations`，participant 與 causal 不可互推 | ✅ 採用 | 「參與」和「因果主張」放在**不同的表**，不只是不同的 enum 值（§5.4） |
| 路由 `/campaigns/:slug?phase=` | ⚠️ **不存在，屬戰役改版** | P1 不做；連到現有戰役模式。獨立路由列 Q1 |
| `?person=<slug>` | 🔧 | 現在沒有 slug 欄位。P1 用 `leader_bios.id`（UUID），不需 migration；slug 是提案 |
| sheet 狀態存在記憶體 service | ✅ 採用 | 但要明說：重新整理就會遺失（Q2） |
| `history.state.personScroll` | ✅ 可用 | 寫在 app 自己 push 的那一筆 history entry 上 |
| 主地圖已有 `?date=&cam=` 「待核對」 | ❌ **只有 `date`，沒有 `cam`** | `cam` 列為提案，不自動改現行行為 |
| 關閉規則「history 有本站上一筆就 back」 | ❌ **不安全** | 改用 app 自己的標記，見 §4.3 |
| 重新整理「sheet 捲動回頂，可接受」 | ⚠️ 不能替 Tai 決定 | 列 Q2 |
| 來源按鈕 `aria-expanded`、無來源顯示文字 | ✅ 採用 | 但「待補來源」的段落仍要渲染一個靜態標籤，不渲染按鈕 |
| 「全部展開／收合」 | ✅ 採用 | 狀態不保存 |
| `role="dialog" aria-modal="true"`、焦點鎖定、關閉後焦點回卡片 | ✅ 採用 | 現有 sheet 是 `aria-modal="false"`；對話框開啟時 sheet 要 `inert` |
| 生平補全用 Wikidata P569/P570/P19/P102/P39/P18 | ⚠️ 修正 | Wikidata 只能當**線索**，不是合格史料（憲法 §6「合格史料」）；P18 照片另需逐張查授權。只寫已查證 |
| 「永不由生平文字自動在地圖畫人或部隊」 | ✅ 採用 | 寫進 §6.6 |

---

## 3. 範圍

### 3.1 P1（最小可交付）

1. **人物分頁**：只放領導人（`leader_records` 當天在任者）。每人一張卡：姓名（依語言取 `name_zh`／`name`）、照片（無則佔位）、職位（`role`＋`title`）、任期（`valid_period`，結束日依 §6.5 顯示）、「查看詳情」按鈕（只有連到有效、非測試生平時才出現；沿用 `ec7e7f8` 的判斷）。
2. **人物閱讀對話框**：桌機大視窗、手機全螢幕；**不要求地圖可見**。內容：基本欄位（每欄位附來源，預設收合）、生平段落（逐段來源）、任期清單、「相關事件／戰役」卡（只列**有來源連結**的）。
3. **底下 sheet 保留**：開關對話框不改變 sheet 的選取、分頁、捲動位置（記憶體內）。
4. **來源呈現**：§6 的規則全部適用。
5. **戰役連結**：只在「該戰役在現有戰役模式中存在且功能開關開啟」時才顯示連結；點了進入**現有**戰役模式（不新建頁面）。戰役模式的說明卡若有對應人物連結，可點開人物對話框。
6. **導覽與 history**：§4 全部適用。

P1 的前提（缺一就延後對應功能，不用假資料補）：
- 人物 ↔ 事件／戰役的有來源連結資料（§5.3）。沒有資料時「相關事件／戰役」區塊顯示「尚無有來源的相關事件」，不從政權參與方推測。
- 段落化生平（§5.2）。沒有段落化之前，現有 `summary` 整塊當作「一段」顯示，來源取 `field_sources.summary`；沒有來源就標「待補來源」。

### 3.2 P2

- 軍事人物（非元首／首腦）。資料模型需能表達非任期型角色（§5.5）。
- 人物出現在戰役「階段」的參與清單（需戰役資料有人物欄位且附來源）。
- 若 Tai 選 Q1(b)，做獨立戰役路由。

### 3.3 P3+

- 行動／影響／被動效果：「參與」與「因果主張」分開記錄（§5.4），每條都要附來源。
- 鏡頭參數 `cam` 進 URL（提案，見 §4.6）。

### 3.4 永不做

- 由生平或戰術概念文字**自動**把人物或部隊放上地圖。地圖上只畫「有日期、有地點、有來源」的戰役資料（例如戰役 JSON 中 `verified` 的箭頭與據點）。

---

## 4. 導覽狀態機與 history 規則

### 4.1 狀態

```
                    ┌──────────── 開人物（push）─────────────┐
                    │                                        ▼
  [Browse]  ── 選政權 ──▶ [Browse+Sheet] ── 開人物（push）──▶ [Person/over Browse]
     ▲                         │  ▲                              │
     │                     開戰役模式│  關戰役                      │ 點相關戰役
     │                         ▼  │                              ▼
     └──── 關戰役 ───── [Campaign] ◀──────── 進戰役（見 4.4）──────┘
                               │
                          點人物（push）
                               ▼
                       [Person/over Campaign]
```

- **底層（base）**：`Browse`（主地圖，可能帶 sheet）或 `Campaign`（現有戰役模式）。
- **疊層（overlay）**：`Person`，同時最多一層。不疊第二個人物對話框：在對話框內點另一個人物 = **replace** 目前的 `person` 參數（不再 push），避免 history 越疊越深。

### 4.2 URL（提案）

- 開人物：`?person=<leader_bios.id>`，與現有 `date`／`lang`／`axis` 合併（`queryParamsHandling: 'merge'`）。
- 因為是同一個路由（`''`），Angular 不會重建 `AtlasPage`，底下 sheet 的元件與記憶體狀態自然保留。
- 前端要**新增**訂閱 `queryParamMap` 的 `person` 參數（現在只讀一次 snapshot），這樣上一頁／下一頁才會開關對話框。**只處理 `person`**；`date` 的「只讀一次」現行行為不在本設計內順便更改。

### 4.3 關閉對話框（關鍵修正）

不能用「同站有上一頁就 back」：瀏覽器不讓網頁讀取任意 history 內容，`history.length` 也無法告訴你前一筆是誰；使用者可能從別的連結、書籤或另一個分頁的深連結進來。

規則（提案）：

1. **開啟時**由 app 自己 push 一筆 entry，並在這筆的 `history.state` 寫入標記，例如 `{ wlOverlay: { kind: 'person', token: <隨機 id>, baseToken: <底層 entry 的 token> } }`；同時在記憶體 service 記下「我剛 push 的 token」。
2. **關閉時**只有同時符合以下條件才 `history.back()`：
   - 目前 `history.state.wlOverlay.token` 等於 service 記下的 token（代表這一筆是本次執行期間 app 自己 push 的）；而且
   - 這一筆是**緊接在對應底層之後** push 的（push 時記錄的 `baseToken` 和開啟當下底層的 token 相同，中間沒有其他 push）。
3. **其他所有情況**（深連結直接開、重新整理後、token 對不上、service 已遺失）：`router.navigate([], { queryParams: { person: null }, queryParamsHandling: 'merge', replaceUrl: true })`——**只移除 `person`**，`date`、`lang`、`axis`、`boundarySource`、`debug` 以及日後的其他參數全部保留。
4. Esc、× 按鈕、手機頂列關閉鈕，都走同一個關閉函式。
5. 對話框開著時日期若被改動（例如對話框內點事件跳日期），現有的 `replaceUrl` 會改寫**目前這筆**（含 `person`）；此時底層 entry 的日期已過時，因此**改日期的動作要先關閉對話框**（走上述規則），再改日期。

### 4.4 人物 → 戰役 → 人物（巢狀）

現有戰役模式不改 URL，所以 P1 的做法是：

1. 對話框內點「相關戰役」：先依 §4.3 關閉對話框，再呼叫現有 `openCampaign(key)`。
2. 記憶體 service 記一個**返回目標**（單一格，不是堆疊）：`{ personId, personScroll }`。戰役說明卡顯示「← 返回 〈人名〉」。
3. 在戰役模式中點人物：push `?person=`（底層是 Campaign），關閉時依 §4.3 回到戰役模式，階段與日期不變。
4. 在這個人物對話框裡再點另一個戰役：返回目標**被覆寫**而不是累加（避免 人物→戰役→人物→戰役… 無限堆疊）。
5. 「← 返回 〈人名〉」被點：離開戰役模式（現有 `closeCampaign`，還原日期），再 push `?person=<personId>`，還原 `personScroll`。

### 4.5 上一頁／下一頁／重新整理（後援表）

| 情境 | 上一頁 | 下一頁 | 重新整理 |
|---|---|---|---|
| 主地圖開人物對話框 | 關閉對話框；sheet 選取／分頁／捲動仍在（記憶體） | 重開對話框（`person` 參數回來）；對話框捲動依 `history.state.personScroll` | 依 URL 重開對話框；**sheet 的選取、分頁、捲動位置遺失**（現況限制，Q2）；`date`／`lang`／`axis` 照常還原 |
| 戰役模式中開人物 | 關閉對話框，仍在戰役模式 | 重開 | 戰役模式不在 URL → **回到主地圖**，只重開人物對話框；「返回戰役」不顯示 |
| 人物 → 戰役（P1） | 因為進戰役前已關對話框，上一頁的行為等同現況（戰役模式不在 history 中）。**這是 P1 的已知限制**，若 Tai 選 Q1(b) 才會有完整的戰役 history | — | 回主地圖；返回目標（記憶體）遺失 → 不顯示「返回 〈人名〉」 |
| 深連結 `/?date=…&person=…` 直接開 | 離開本站（瀏覽器預設），app 不攔截 | — | 同深連結 |
| 對話框內關閉（深連結進來） | — | — | 走 `replace` 移除 `person`，**不** `history.back()` |
| `person` 參數指向不存在／已撤回的生平 | — | — | 不開對話框，toast「找不到這位人物的資料」，並 `replace` 移除 `person` |

### 4.6 直接 URL 帶 `date`／`cam`（提案，不自動改現行行為）

- `date` 已存在，維持現狀。
- `cam`（中心、縮放）是**提案**：現在不存在。若要加，需另外設計「何時寫入（moveend 防抖動＋replaceUrl）」與「與選取政權後自動 fitBounds 的優先順序」，不在 P1。
- 選取政權與分頁進 URL（例如 `regime=`、`tab=`）也是**提案**，取決於 Q2。

### 4.7 底層狀態保留（記憶體）

- 提案新增一個 `SheetMemory`（或擴充現有狀態）：key = `regimeId + tab`，值 = 捲動位置。開對話框前記錄、關閉後還原。
- 開對話框時 sheet 不關閉、不改分頁（現有 `onSheetHidden` 會把分頁重設為 `overview`，所以**對話框不可觸發 sheet 隱藏**）。
- 對話框開啟期間 sheet 設 `inert`，避免焦點跑進去。

---

## 5. 資料模型提案（全部為提案，未實作）

原則：**沿用** `leader_bios`（一人一筆）、`leader_records`（任期）、`sources`（來源）、citation 表格式（`*_citations(…, source_id, locator, evidence_note)`）。寫入一律走既有規則：只寫 verified、修正用撤回重寫（I5）、寫前備份＋dry-run。

### 5.1 生平欄位的來源接到 `sources`

現況 `field_sources` 是自由文字 jsonb。提案新增：

```
leader_bio_field_citations(
  bio_id      uuid  → leader_bios.id,
  field       text  CHECK IN ('name','birthDate','deathDate','birthPlace','party','portrait'),
  source_id   uuid  → sources.id,
  locator     text  NOT NULL,       -- 頁碼／條目／檔號
  evidence_note text NOT NULL,
  grade       text  NULL            -- 見 §6.3，不在本文定義值域
)
```

- 遷移期間：讀取時兩者並存；`field_sources` 只當「舊格式線索」顯示，**不算已查證**（見 §6.2）。
- `leader_records.source`（自由文字）同理，提案 `leader_record_citations(record_id, source_id, locator, evidence_note)`。

### 5.2 逐段生平

```
leader_bio_paragraphs(
  id uuid, bio_id uuid → leader_bios.id, ord int,
  text jsonb,            -- {"zh-Hant": "...", "en": "..."}，依 R4 雙語
  retracted_at, retraction_reason, created_at, version
)
leader_bio_paragraph_citations(paragraph_id, source_id, locator, evidence_note, grade NULL)
```

- **不設 `status=draft`**：依 I6，未查證的段落不進資料庫，留在 `data/seed/**`。資料庫裡的段落若沒有引用，前端就標「待補來源」，不標已查證。
- 現有 `leader_bios.summary` 在段落化前視為一段（§3.1）。

### 5.3 人物 ↔ 事件／戰役（「參與」）

```
person_event_participations(
  id uuid,
  bio_id uuid → leader_bios.id,
  event_id uuid NULL → historical_events.id,
  campaign_key text NULL,       -- 對應現有 public/campaigns/<key>.json；D13 定案後可改為 event_id
  role text,                    -- 例：commander、head_of_state_at_time…（值域待定）
  valid_period daterange NULL,  -- 半開區間
  retracted_at, retraction_reason, created_at, version,
  CHECK (num_nonnulls(event_id, campaign_key) = 1)
)
person_event_participation_citations(participation_id, source_id, locator, evidence_note, grade NULL)
```

- **至少一筆 citation 才能建立**（寫入層檢查，照 I6 精神）。
- 不從 `event_participants`（政權參與方）或任期重疊**推導**人物參與。
- `campaign_key` 是因應「戰役仍是靜態 JSON、D13 未決」的過渡設計；不替 D13 拍板。

### 5.4 P3：因果主張（與參與分表）

```
person_causal_claims(
  id uuid,
  subject_bio_id uuid,
  object_type text CHECK IN ('event','campaign','regime','bio'),
  object_id text,
  claim_kind text CHECK IN ('acted','influenced'),   -- 方向由 subject→object 表示，不另存 influenced_by
  claim_text jsonb,         -- 主張內容（雙語）
  retracted_at, …
)
person_causal_claim_citations(claim_id, source_id, locator, evidence_note, grade NULL)
```

- **「參與」與「因果主張」不同表**：參與是事實紀錄（有沒有在場、擔任什麼角色），因果是史學詮釋（影響了什麼）。不可由一方推出另一方。
- 有爭議的因果主張依 R8 多觀點並列，每個觀點各自附合格史料。

### 5.5 P2：軍事人物

`leader_bios` 名稱偏「領導人」，但結構本身就是「一人一筆」。P2 建議**沿用同一張表**（必要時改名或加 view），非元首角色用 §5.3 的參與紀錄或另一張 `person_roles`（**提案，P2 再議**）表示，不另建平行的 `persons` 表。

### 5.6 照片（Q4）

提案（P1 可先不做）：

```
media_assets(
  id uuid, kind text CHECK IN ('portrait'),
  file_url text, source_id uuid → sources.id,   -- 出處走既有 sources
  locator text, license_code text, license_evidence_url text,
  reuse_cleared boolean NOT NULL DEFAULT false, -- 是否已確認可在本站重製顯示（見 §6.4）
  attribution text, created_at …
)
leader_bios.portrait_media_id uuid NULL → media_assets.id
```

前端只在 `reuse_cleared = true` 時顯示照片；否則顯示佔位圖。

### 5.7 API（提案）

| 端點 | 說明 |
|---|---|
| `GET /leader-bios/{id}`（擴充） | 回應加 `fieldCitations[]`、`paragraphs[]`（各含 citations）、`participations[]`（含 citations）、`portrait`；保留現有欄位，向下相容 |
| `GET /leaders?date=&regime=`（不變） | 人物分頁卡片來源，已有 |
| `GET /events/{id}/people` | 戰役／事件 → 有來源的人物參與清單（P1 若戰役仍為 JSON，前端可改讀 `campaign_key` 對應清單） |
| 寫入：`POST /leader-bios/{id}/paragraphs`、`POST /leader-bios/{id}/field-citations`、`POST /person-event-participations`、各 `…/retraction` | 需 `X-API-Key`；無 citation 一律 400 |

### 5.8 前端（提案）

| 元件 | 說明 |
|---|---|
| `shared/person-card` | 人物卡 |
| `shared/person-dialog` | 閱讀對話框（需新增 dialog 基礎元件，可依 `components/ui/sheet` 的模式做 `components/ui/dialog`） |
| `shared/source-disclosure` | 「來源（n）」收合元件，內容沿用 `citation-popover` 的呈現 |
| `core/overlay-history.ts` | §4.3 的 token 標記與關閉判斷 |
| `core/sheet-memory.ts` | §4.7 |

---

## 6. 來源呈現規則

### 6.1 收合與版面

- 所有 sheet、卡片、詳情裡的來源**預設收合**；展開／收合不改變周圍元素位置以外的版面（按鈕位置固定，展開區在按鈕下方推開內容，不跳動標題）。
- 每段或每欄位後面一顆 `<button aria-expanded aria-controls>`「來源（n）」；展開後列出來源標題、出版者、locator、授權、證據備註。
- 無來源：顯示**文字**「待補來源」（不只靠顏色），不渲染按鈕。
- 頂部一顆「全部展開／收合」，狀態不保存。

### 6.2 逐段／逐欄位溯源，絕不冒充已查證

- 每個欄位、每個段落各自判斷，不因「這個人有部分來源」就整張卡標已查證。
- 判斷順序：
  1. 有 §5.1／§5.2 的 citation（接到 `sources`）→ 顯示來源，可標已查證。
  2. 只有舊格式 `field_sources` 自由文字或 `leader_records.source` 文字 → 顯示該文字作為「出處備註」，**不標已查證**。
  3. 什麼都沒有 → 「待補來源」。
- `leader_records.verified = true` 但沒有接 `sources` 的 citation：卡片照常顯示任期，但不出現「已查證」字樣（注意：`CreateLeaderRecordRequest.Verified` 預設是 `true`，`Dtos.cs:354`，這個旗標不能單獨當作查證證據）。

### 6.3 A/B/C/X 來源分級

- 保留考證流程現行的 A/B/C/X 分級。repo 已追蹤檔案中**沒有分級的結構化定義**，只在考證 seed 的備註裡出現。
- 提案在各 citation 表加可空的 `grade` 欄位，值域與定義**沿用考證組既有約定**，由考證組提供定義文件後再加 CHECK；本文不自行定義各級意義。
- 前端在來源展開區顯示分級；分級為空時不顯示，不猜測。

### 6.4 授權 metadata ≠ 可引用的權利

三件事分開記錄、分開判斷：

| 概念 | 意思 | 存放（現有／提案） |
|---|---|---|
| 授權 metadata | 這份作品本身以什麼授權發布（CC0、CC BY…） | 現有 `sources.license_code`、`license_evidence_url` |
| 重製／顯示的權利 | 本站能否**直接放出**該內容（照片、地圖圖片、長段原文） | 提案 `media_assets.reuse_cleared`；文字引文同理需人工判斷 |
| 作為證據引用 | 這份來源能否支撐一個事實（合格史料、分級） | citation 本身＋`grade` |

- 「引用一份來源當證據」不等於「可以重製它的內容」；反之，授權是 CC0 也不代表它是合格史料。
- 現有 `CitationPolicy` 用授權允許清單擋控制紀錄與陣營的 primary citation（R7 與使用者 2026-10-29「史實資料必須有使用權」）。本設計**不改**這個既有規則；人物生平的引用是否套用同一張允許清單，屬業務規則，若要定須先改憲法（不在本文拍板，列風險 R5）。

### 6.5 日期：exclusive 結束日

- 資料一律半開區間：`[start, end)`。例：`end = 1945-10-01` 表示到 **1945-09-30**。
- 顯示時任期、事件、戰役結束日一律顯示 `end − 1 天`（日精度時）；月／年精度依精度顯示，不憑空補日。
- 戰役 JSON 已同時有 `end` 與 `end_inclusive`，前端顯示用 `end_inclusive`，運算用 `end`。
- 迄日為空（仍持續或未知）顯示「迄今不明」，不推測。

### 6.6 地圖上的人物與部隊

- 生平、戰術概念文字**不能**觸發任何地圖繪製。
- 人物或部隊要出現在地圖上，必須來自「有日期、有地點、有來源」的戰役資料（例如戰役 JSON 中帶 `sources` 的 arrows／sites），而且呈現時要讀該筆的 `verified`，未查證者不可與已查證者用相同樣式（現有戰役圖層是否已區分，實作前另行核對）。

---

## 7. 生平補齊流程（本次不寫資料）

1. **缺口盤點**（唯讀）：對開發庫 `leader_bios`／`leader_records` 產出報表——每欄位空值數、沒有連生平的任期數、`field_sources` 只有文字沒有 URL 的筆數、`verified=true` 但 `source` 為「待查證」的矛盾筆數、`is_test` 殘留數。
2. **逐筆查證**：每一欄、每一段找合格史料（憲法 §6）；Wikidata 等只當線索。衝突的說法依 R8 並列，不擇一。
3. **寫入**：只寫已查證；每批先備份開發庫、dry-run、Tai 或主管確認後寫入；更正走撤回重寫（I5）。正式庫照 D14 另行同步。

---

## 8. 待 Tai 決定（只列真正未決）

| # | 題目 | 選項 | 建議 |
|---|---|---|---|
| Q1 | 戰役「專屬頁」怎麼落地？現況只有主地圖上的戰役模式（dev 限定、不改 URL） | (a) P1 把現有戰役模式當作專屬頁，只加連結；(b) 新增 `/campaigns/:key` 路由（屬戰役改版，另開設計） | (a)。(b) 等 P2 另立設計 |
| Q2 | 重新整理後 sheet 的選取／分頁／捲動要不要還原？ | (a) 接受遺失，只還原 `date`／`lang`／`axis`／`person`；(b) 把 `regime`、`tab` 加進 URL（捲動仍不還原） | 由 Tai 決定；(b) 會改變現行 URL 行為 |
| Q3 | 人物 URL 識別碼 | (a) 用 `leader_bios.id`（UUID，免 migration）；(b) 新增 `slug` 欄位（需 migration 與補資料） | (a)，日後要可讀網址再加 slug，舊 UUID 連結保留可用 |
| Q4 | P1 照片 | (a) P1 全部用佔位圖，照片待 `media_assets`＋重製權利流程；(b) P1 就做照片 | (a) |
| Q5 | 人物生平引用是否套用現有授權允許清單（`CitationPolicy`）？ | (a) 套用（只收 PD／CC 來源）；(b) 不套用，任何合格史料都可當證據，但重製內容另審 | 屬業務規則，需先改憲法；設計兩者都支援 |

---

## 9. 風險

| # | 風險 | 對策 |
|---|---|---|
| R1 | 有來源的人物 ↔ 事件連結資料目前為零，P1「相關事件／戰役」可能大多是空的 | 空狀態文案清楚；絕不從政權參與方或任期重疊推測 |
| R2 | 戰役模式 production 關閉，P1 戰役連結在正式站看不到 | 連結依 `CAMPAIGNS_ENABLED` 顯示；正式站開放與否另由 Tai 決定 |
| R3 | 現有 `leader_records.verified` 預設 `true`、`source` 為自由文字，可能讓未接 `sources` 的資料看起來像已查證 | §6.2：已查證只依 citation 判斷 |
| R4 | history 標記實作錯誤會讓「關閉」把使用者帶離本站 | §4.3 預設走 replace；只有 token 完全對上才 back；e2e 覆蓋深連結、重新整理、上一頁／下一頁、巢狀四種情境 |
| R5 | 授權規則與「可引用」混用，可能誤擋合格史料或誤放無權重製的照片 | §6.4 三欄分開；照片預設不顯示 |
| R6 | 現有 `date` 只讀一次 snapshot，上一頁／下一頁時日期不跟著變；加入 `person` 監聽後兩者行為不一致 | 本設計只處理 `person`；日期 history 行為若要改另案 |
| R7 | 現有 `onSheetHidden` 會重設分頁，對話框若誤觸 sheet 隱藏就丟失狀態 | 對話框只 `inert` sheet，不關閉 |
| R8 | A/B/C/X 分級沒有結構化定義，`grade` 欄位可能各填各的 | 值域待考證組定義後再加 CHECK |
| R9 | 戰役仍是靜態 JSON、D13 未決，`campaign_key` 過渡欄位日後要遷移 | 遷移時以撤回重寫處理，保留舊紀錄 |

---

## 10. 地理圖層（獨立未來提案，不阻擋人物工作）

範圍：**地形、河流、城市**的地圖圖層。**不是**附近搜尋，**不是** RAG；本文不設計、也不做任何搜尋或 RAG。

規則（提案）：

1. **現代高程底圖不是歷史證據。** 地形暈渲只作視覺背景，圖例須明示「現代地形，僅供參考」；不能拿來支撐任何疆界、戰線或事件位置的判斷。
2. **會變動的地物要依時間。** 河道（例：黃河 1938 花園口決堤後改道）、海岸線、城市範圍與名稱都要帶有效區間（半開區間），依時間軸日期篩選，同主權／控制圖層的規則。
3. **不得用無來源的現代資料代替。** 沒有歷史來源的河道或城市，不顯示，而不是改放現代版本；城市名依憲法 §6「地名」規則（當時名稱，括號附現代名）。
4. **來源與授權**：沿用 `sources`，並套用 §6.4 三欄分開；R7 的地圖授權規則適用。
5. **與現有圖層的關係**：放在 ARCHITECTURE §4.1 的「底圖」與「疆界面」之間或底圖層內；不能影響標籤碰撞規則（§4.2）與圖磚效能目標（§9.7）。
6. **注意現況**：現有戰役 JSON 的據點座標用 OpenStreetMap Nominatim（現代地名庫）定位（例：`frontend/public/campaigns/poland_1939.json`）；這是「把歷史地名對到座標」，不是歷史地理證據。地理圖層上線時需同樣在資料上區分。

不在本提案：一級行政區（已在 M4-c，資料源 OpenHistoricalMap）、任何搜尋功能。

---

## 11. P1 實作採用的做法（2026-11-07，分支 `feature/person-cards`）

依 Tai 2026-11-07 13:12 決定實作人物部分；戰役部分全部延後。以下是與 §5、§6 提案不同或更具體的地方。

### 11.1 資料（新增式 migration `20261107051907_PersonPortraitAndFieldCitations`）
- `leader_bios` 新增：`death_date_precision`（day／month／year）、`wikidata_qid`（只當辨識線索）、照片欄位 `portrait_url`、`portrait_source_url`、`portrait_author`、`portrait_license_code`、`portrait_license_url`、`portrait_attribution`、`portrait_retrieved_on`，以及 `superseded_by`（撤回重寫後指向新版）。
  - CHECK：照片 URL 有值時，出處頁、授權、署名、查證日期都必須有；授權限 `CitationPolicy.PrimaryLicenseAllowlist`（us_federal_pd、pd_expired、cc0、cc_by、cc_by_sa）。
  - 取代 §5.6 的 `media_assets`：P1 一人一張照片，直接放在 `leader_bios` 最簡單；之後要多張照片再改。
- 新表 `leader_bio_field_citations(id, bio_id, field, source_id, locator, evidence_note, accessed_on, retracted_at, retraction_reason, created_at)`：§5.1 的實作。`field` ∈ name、nameZh、birthDate、deathDate、birthPlace、party、summary、portrait。I5 trigger：不可 DELETE、撤回不可逆。`grade` 欄位**沒有加**（§6.3 值域未定）。
- **沒有做**：§5.2 逐段表（`leader_bio_paragraphs`）。目前 `summary` 視為一段，以 `field = 'summary'` 掛來源；前端已經按段落渲染（以空行分段，各段都掛同一組 summary 來源），日後有逐段表再拆。§5.1 的 `leader_record_citations` 也沒有做，任期來源仍顯示 `leader_records.source` 自由文字，標為「出處備註」。
- 沒有刪除或修改任何既有欄位；`field_sources` 保留，前端當舊格式備註顯示。

### 11.2 API
| 端點 | 說明 |
|---|---|
| `GET /leader-bios/{id}`（擴充） | 加 `deathDatePrecision`、`wikidataQid`、`portrait`、`supersededBy`、`fieldCitations[]`（含完整 `source`）、`terms[]`（此人全部有效任期＋政權自稱名）。已撤回的生平仍回傳 |
| `GET /leaders?date=`（擴充） | `bio` 摘要加 `deathDatePrecision`、`portrait` |
| `POST /leader-bios`（擴充） | 可帶 `deathDatePrecision`、`wikidataQid`、`portrait`、`citations[]`（同一交易寫入） |
| `POST /leader-bios/{id}/field-citations` | 補一筆欄位引用；`locator`、`accessedOn` 必填，`sourceId` 必須存在 |
| `POST /leader-bio-field-citations/{id}/retraction` | 撤回引用（I5） |
| `POST /leader-bios/{id}/revisions` | 撤回重寫（I5）：同一交易內撤回舊版（記原因、`superseded_by`）、建新版、任期改連新版、複製舊版有效引用 |

### 11.3 前端
- 分頁值仍是 `leaders`（data-testid 不變），文案改「人物」／People。
- `shared/person-card`、`shared/person-dialog`、`shared/source-disclosure`、`core/overlay-history`（§4.3 的 token 規則；`canGoBack` 有單元測試）、`core/person-format`（結束日顯示 `end − 1 天`、依精度顯示日期、照片可否顯示）。
- §4.7 的 `SheetMemory`：沒有另外做 service。對話框是疊層，底下面板不卸載，選取／分頁本來就保留；開啟前記下面板捲動位置，關閉後若有變動才還原，焦點回到觸發的「查看詳情」按鈕。
- 戰役：沒有任何戰役連結、返回目標、路由（Tai：戰役先不做）。
- 已撤回且有 `supersededBy` 的 `?person=` 連結會 replace 成新版 id；沒有新版就 toast「找不到這位人物的資料」並移除 `person`。

### 11.4 已查證的判斷
- 前端**不顯示「已查證」字樣**：結構化引用與舊格式備註都放在「來源（n）」收合區，舊格式那筆另外註明「未接結構化來源，非查證標記」。`leader_records.verified` 不用來判斷任何顯示。
