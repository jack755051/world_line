---
schema_version: 1
feature_id: world-line-ww2
feature_name: World Line — 二戰第一階段（M4）
status: active
owner: jack755051@gmail.com
last_updated: 2026-10-03
related_constitution: .claude/constitutions/world-line.md
related_prds: [".claude/prds/world-line.md"]
related_adrs: []
---

# PRD: World Line — 二戰第一階段（M4）

> 階段 PRD。共用的技術選型、目前已實作的 schema／API 慣例、UI 共通頁面在核心 PRD `world-line.md`；本檔只寫二戰階段**要做的範圍與變動**。M4 完成後，已實作的 schema／API 併回核心 PRD。
>
> 依據：憲法 2026-10-02 改版（grill-me Q1-Q14）＋ PRD 層工程決策（使用者 2026-10-02 選定：擴充 `regime_territories` 當控制軸、`int4range`→`daterange`、預設顯示實際控制、網底＝非完整掌控）。

## 1. 背景

古代中國史料（魏／蜀漢疆域）在 CHGIS、中研院 CCTS、OpenHistoricalMap 三個管道皆無法取得可用資料，第一階段改為二戰（憲法 §7 Decision 2）。二戰是「多政權同時並存、跨洲互動」的極端案例，正好驗證 R2／R3；史料多、授權清楚、精度高（大量公有領域軍事地圖可供數位化）。

## 2. 範圍 (Scope) vs 非範圍

### ✅ 範圍

- [ ] 1937-07～1945-09 全球所有戰區的政權、主權主張、實際控制資料建置與地圖呈現，粒度為「國家／控制區」層級（憲法 §1 策略轉向、R1 補充）
- [ ] 主權／實際控制兩軸並存：控制紀錄含控制類型（直接統治／軍事佔領／傀儡代管／不完全控制／交戰中）；主權主張可多筆並存並標主張方與承認方（憲法 R6、§6）
- [ ] 地圖預設呈現實際控制，主權主張可切換檢視（PRD 層拍板，2026-10-02）
- [ ] 戰線＝敵對控制區之間的邊界，由後端 PostGIS 推導，不獨立描繪（憲法 §6「戰線」）
- [ ] 不完全控制／交戰中區域以斜線網底呈現（憲法 §6、§5 斜線網底列）
- [ ] 控制區快照為月或轉折點粒度，快照之間連續形變，但**推估過渡**須與**史料快照**明確區分呈現（憲法 §9 2026-10-02 修訂）
- [ ] 政權狀態機新增流亡／被併吞／復國三種轉換（憲法 §4 近代擴充轉換）
- [ ] 每筆主權主張與控制紀錄附來源引用，控制軸只採用有明確出處且為公有領域或 CC 授權的底圖數位化（憲法 R7、I6）
- [ ] 重大戰役、政治事件與暴行事件（如南京大屠殺、猶太大屠殺）以歷史事件呈現；觀點須有合格史料支撐，否認論不入列（憲法 R8）
- [ ] 「二戰起點」以爭議點並列呈現（1931／1937／1939），系統不裁定（憲法 §9）

### ❌ 非範圍（階段性延後，非永久排除）

- ❌ 政治／軍事以外的第二個歷史維度（經濟／後勤、人口／人道、宗教、文化、疾病等）與維度切換器——憲法 R5 已確立多維度方向，但**二戰第一階段只交付政治／軍事維度**，第二個維度上線時才做切換器（階段性延後，非永久排除）
- ❌ 戰線層級（獨立描繪的週級戰線、軍團／集團軍級進軍箭頭）與部隊層級（師級軌跡、日級精度）——憲法 R1 補充，屬二戰深化階段（階段性延後，非永久排除）
- ❌ 「點線佔領」的點／線建模（城市 Point＋鐵路 LineString）——第一階段以「不完全控制」多邊形概括，精確建模屬二戰深化階段
- ❌ 新增前端套件（Deck.gl、整包 D3）——見核心 PRD §5（grill-me Q7）
- 跨階段的永久排除項見核心 PRD §3

## 3. 使用者故事

### Story 6: 二戰實際控制與主權主張檢視（對應憲法 R6、R2）

- **As a** 使用者
- **I want to** 把時間拉桿拖到 1940 年 7 月
- **So that** 我能同時看到德國佔領的法國北部、維琪法國控制的南部，並能切換檢視「法國主權由誰主張、誰承認」（維琪法國、自由法國）

**Acceptance Criteria**:
- [ ] Given 時間拉桿停在 1940-07，when 地圖以預設模式渲染，then 依實際控制紀錄著色，同一時間全球各戰區控制區同時顯示（R2）
- [ ] Given 使用者切換到主權檢視，when 地圖渲染，then 依「實際生效」的主權主張著色；點擊某地區可看到該地區所有並存的主權主張及各自的承認方（R6）
- [ ] Given 某控制紀錄的控制類型為「不完全控制」或「交戰中」，when 地圖渲染，then 該區域以斜線網底呈現，與完整掌控（實心色塊）視覺上明確區分
- [ ] Given 兩個敵對控制區相鄰，when 地圖渲染，then 顯示由後端推導的戰線

### Story 7: 史料快照與推估過渡區分（對應憲法 §9 2026-10-02 修訂）

- **As a** 使用者
- **I want to** 拖動時間拉桿經過 1941 年 8 月到 9 月（基輔包圍戰）
- **So that** 我能看到控制區連續變化，同時清楚知道哪些畫面是史料、哪些是系統推估

**Acceptance Criteria**:
- [ ] Given 時間拉桿停在某筆控制快照的日期，when 地圖渲染，then 以「史料快照」樣式呈現，並可查看該快照的來源引用（I6）
- [ ] Given 時間拉桿停在兩筆快照之間，when 地圖渲染形變插值結果，then 邊界以推估樣式呈現（例：虛線邊界、降低不透明度）並標示「推估過渡」，同時顯示前後最近的史料快照日期
- [ ] Given 拉桿持續拖動，when 跨過快照日期，then 形變維持連續（不離散跳轉，憲法 §9），僅呈現樣式在史料與推估之間切換

### Story 8: 近代政權狀態轉換（對應憲法 §4 近代擴充轉換）

- **As a** 使用者
- **I want to** 查看波蘭（1939 流亡倫敦）、奧地利（1938 被併吞、1945 復國）的政權狀態
- **So that** 我能區分「流亡」「被併吞」「被滅亡」「被佔領」這幾種不同的處境

**Acceptance Criteria**:
- [ ] Given 某政權狀態為「流亡」，when 顯示該政權，then 標示為流亡狀態，且該政權仍可作為主權主張方出現（R6）
- [ ] Given 某政權以「被併吞」終止，when 顯示狀態，then 視覺／文字上與「被滅亡」明確區分
- [ ] Given 某政權由流亡或被併吞恢復為存續（復國），when 拖動拉桿跨過復國日期，then 狀態轉換正確呈現
- [ ] Given 某政權僅被軍事佔領（例：1945 年後的日本），when 顯示狀態，then 政權狀態仍為「存續」，佔領只呈現在實際控制軸

### Story 9: 爭議與暴行事件的多視角邊界（對應憲法 R8）

- **As a** 使用者
- **I want to** 查看南京大屠殺的事件詳情
- **So that** 我能看到有學術依據的不同傷亡估計並列，而不會看到否認論被當成同等觀點

**Acceptance Criteria**:
- [ ] Given 事件有多個傷亡估計觀點，when 顯示爭議點區塊，then 各觀點並列，且每個觀點都附合格史料引用
- [ ] Given 一筆觀點完全沒有來源引用，when 透過 API 寫入，then 應被拒絕（R8）；來源是否「合格」（憲法 §6 判準）無法由程式判斷，由資料建置者在數位化時審查，不在 API 層假裝能驗證
- [ ] Given 事件「二戰起點」，when 顯示，then 1931／1937／1939 三種起點以爭議點並列，系統不標示任何一者為正確（憲法 §9）

## 4. 資料模型變動（相對核心 PRD §6，對應憲法 R6、I1、I3、I6、§4、§9）

### 設計原則

- **主權與實際控制分兩軸，各自一張表**（使用者 2026-10-02 選定）：`regime_territories` **擴充為控制軸**（加 `control_type`），三國等既有資料自動視為「直接統治」，前端只走一條疆域渲染路徑；新增 `sovereignty_claims` 承載主權軸。不採「單表加 axis 欄位」，因為主張方／承認方等欄位對控制紀錄沒有意義。
- **疆域時間精度 `int4range` → `daterange`**（使用者 2026-10-02 選定）：月快照需要日精度；PostgreSQL `date` 可表達到西元前 4713 年，古代資料不受影響，既有年區間 `[y1,y2)` 遷移為 `[y1-01-01, y2-01-01)`；GiST 複合索引沿用（`btree_gist` 已裝）。**取代** 2026-08-26「`valid_period` 維持 `INT4RANGE`、不跟隨事件升級」的決策——當時的前提「疆域史料常態以年為單位記載」對二戰不成立。不改用 EDTF＋decimal，因為會失去 range 型別的 GiST 區間索引。
- **史料快照日期＝控制紀錄 `valid_period` 的下界**：每筆控制紀錄代表一張有出處的地圖「截至某日」的狀態；相鄰兩筆快照下界之間的形變插值即為「推估過渡」（憲法 §9）。前端依此判斷目前拉桿位置是否落在史料快照日期上，不需額外欄位。
- **主權主張可多筆並存**：同一地區同時可有不同主張方的主張（I3 改寫後只限制「同一主張方」的矛盾正式版本）；`is_effective` 標記「當時實際生效」那一筆，供主權檢視預設著色；有爭議的個案以 `historical_event_controversies` 記錄，不建通則（憲法 R6）。
- **政權狀態需要時間切片**：既有 `regimes.status` 是單一值，只能表達「最終狀態」；流亡（波蘭 1939–1945）、被併吞後復國（奧地利 1938–1945）是**期間性**狀態，新增 `regime_status_periods` 記錄狀態隨時間變化，`regimes.status` 保留為目前／最終狀態以維持既有 API 相容。新狀態代碼：`exiled`（流亡）、`annexed`（被併吞）；復國不是獨立狀態，是由 `exiled`／`annexed` 回到 `active` 的轉換，`regime_transition_events.transition_kind` 新增 `'restoration'` 掛觸發事件。被併吞的併吞方沿用 `destroyed_by_regime_id`（語意擴大為「終止方政權」）。後端 `RegimeTransitionValidator` 與前端 XState 定義需同步加入新轉換（§5 驗證分工原則不變）。
- **I6 由應用層強制**：主權主張與控制紀錄寫入端點須至少帶一筆 citation，否則拒絕；沿用 2026-08-31 已實作的 `sources` ＋ `*_citations` 模型（`evidence_note` 必填）。既有三國資料的 citation 回填不在第一階段範圍（凍結資料）。
- **戰線不存表**：由 API 依查詢日期即時以 PostGIS 推導敵對控制區的共用邊界（憲法 §6「戰線」、grill-me Q7）；「敵對」判定依交戰事件或 `regime_relations.relation_type='敵對'`，具體規則留到實作任務拍板。

```sql
-- 控制軸：擴充既有疆域表
ALTER TABLE regime_territories
  ALTER COLUMN valid_period TYPE daterange USING daterange(make_date(lower(valid_period),1,1), make_date(upper(valid_period),1,1)),
  ADD COLUMN control_type VARCHAR(24) NOT NULL DEFAULT 'direct_rule';
  -- 'direct_rule'（直接統治）|'military_occupation'（軍事佔領）|'puppet_administration'（傀儡代管）
  -- |'partial'（不完全控制）|'contested'（交戰中）；中立代碼，應用層驗證（比照 regimes.status 慣例）
  -- ⚠️ 負年份（西元前）的 make_date 轉換需在 migration 實作時驗證

-- 主權軸
CREATE TABLE sovereignty_claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claimant_regime_id UUID NOT NULL REFERENCES regimes(id), -- 主張方
  valid_period DATERANGE NOT NULL,                          -- I1
  geom GEOMETRY(MultiPolygon, 4326) NOT NULL,
  is_effective BOOLEAN NOT NULL DEFAULT FALSE,              -- 當時實際生效（主權檢視預設著色依據）
  is_disputed BOOLEAN NOT NULL DEFAULT FALSE,               -- I3 例外：同一主張方的爭議並存版本
  superseded_by UUID REFERENCES sovereignty_claims(id),     -- I5 版本鏈
  correction_reason TEXT,
  corrected_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  version INT DEFAULT 0
);

-- 承認方（多對多，承認本身也有時間性：例 美國對波羅的海併入的不承認政策）
CREATE TABLE sovereignty_claim_recognitions (
  claim_id UUID NOT NULL REFERENCES sovereignty_claims(id) ON DELETE CASCADE,
  recognizer_regime_id UUID NOT NULL REFERENCES regimes(id),
  stance VARCHAR(16) NOT NULL,                              -- 'recognized'|'not_recognized'
  valid_period DATERANGE NOT NULL,
  PRIMARY KEY (claim_id, recognizer_regime_id, valid_period)
);

-- I6：沿用既有 citation pattern
CREATE TABLE sovereignty_claim_citations ( /* 同 regime_territory_citations：claim_id + source_id + locator + evidence_note */ );

-- 政權狀態時間切片（流亡／被併吞等期間性狀態）
CREATE TABLE regime_status_periods (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  regime_id UUID NOT NULL REFERENCES regimes(id) ON DELETE CASCADE,
  status VARCHAR(32) NOT NULL,                              -- 既有 4 碼 + 'exiled'|'annexed'
  valid_period DATERANGE NOT NULL
);
```

### 主要實體與關係（新增）

- `regimes` 1 --- N `sovereignty_claims`（主張方；2026-10-02）
- `sovereignty_claims` N --- N `regimes`（透過 `sovereignty_claim_recognitions`，承認方與時間）
- `regimes` 1 --- N `regime_status_periods`（期間性狀態；2026-10-02）

## 5. API 契約變動（目標契約，尚未實作）

回應格式、認證、OpenAPI 要求沿用核心 PRD §7。

| Method | Path | 用途 | 認證 |
|---|---|---|---|
| GET | /api/v1/territories?date={yyyy-mm-dd} | 控制軸快照查詢，回傳含 `controlType`、所屬快照日期（`valid_period` 下界）與前後最近快照日期（供 Story 7 推估過渡標示）；既有 `?year=` 保留相容（視為該年 1 月 1 日） | 公開（唯讀） |
| POST | /api/v1/regimes/:id/territories | 既有端點加上 `controlType`、`validPeriod` 改日期區間，並**強制至少一筆 citation**（I6） | `X-API-Key` |
| GET | /api/v1/sovereignty-claims?date={yyyy-mm-dd} | 主權軸查詢，含 `isEffective` 與承認方清單（R6） | 公開（唯讀） |
| POST | /api/v1/sovereignty-claims | 新增主權主張（I1 時間區間、I6 citation 必填） | `X-API-Key` |
| PATCH | /api/v1/sovereignty-claims/:id/correct | 史料修正（I5 版本鏈，同 territories correct） | `X-API-Key` + 樂觀併發 |
| POST | /api/v1/sovereignty-claims/:id/recognitions | 新增承認／不承認紀錄 | `X-API-Key` |
| GET | /api/v1/frontlines?date={yyyy-mm-dd} | PostGIS 即時推導的敵對控制區邊界（不存表） | 公開（唯讀） |
| GET | /api/v1/regimes/:id/status-periods | 政權期間性狀態（流亡／被併吞等） | 公開（唯讀） |

## 6. UI 流程變動

四態與共通頁面沿用核心 PRD §8。

- **二戰階段主地圖補充（2026-10-02）** — 對應 Story 6、7：
  - 軸切換：預設「實際控制」，可切換到「主權」檢視（使用者 2026-10-02 選定）
  - 時間拉桿預設範圍 1937-07～1945-09、主刻度為月；仍可往回拉到古代（三國資料保留，grill-me Q14），地圖預設中心移到歐亞大陸
  - 史料快照／推估過渡：位於兩筆快照之間時，邊界改為推估樣式並顯示「推估過渡」標籤與前後最近快照日期；具體樣式（虛線、不透明度數值）於實作任務拍板
  - 斜線網底：完整掌控＝實心色塊，非完整掌控（重疊、不完全控制、交戰中）＝斜線（§5）
  - empty：拉到 1937-07 以前且無資料的時段時，沿用既有空狀態提示；1931 起的零星資料（如滿洲國）照常顯示但不保證完整

### 技術決策（細節見核心 PRD §5 對應列）

- Deck.gl：本階段不導入，綁定 M5 部隊層級軌跡
- D3：不導入整包；時間軸沿用 task 3.3／3.4，範圍改 1937–1945、主刻度月
- 戰線：後端 PostGIS 推導，不在前端用 Turf 計算
- 斜線網底：語意擴大為「非完整掌控」，沿用同一套 Canvas Pattern
- 史料：主權軸開放資料集；控制軸 QGIS 地理配準手描（公有領域／CC 底圖），每筆 citation 指到頁碼／圖號

## 7. 風險

| 風險 | 影響 | 緩解 |
|---|---|---|
| **二戰控制軸必須手動數位化**（2026-10-02 查證：無現成開放授權的每月控制區資料集）——1937-1945 全球月快照的描圖量很大，是第一階段最大的進度風險 | high | 先以「轉折點快照」起步（例：1939-09、1940-06、1941-06、1941-12、1942-11、1943-07、1944-06、1945-05、1945-08），再逐步加密；底圖限定公有領域／CC（R7），每張圖描完立即寫 citation，不累積「事後補來源」的技術債 |
| 主權軸開放資料集授權（GPL-3.0 copyleft 對衍生資料庫的影響）未決 | med | 由使用者自行判斷（§8）；未決前可先做控制軸，主權軸資料暫緩匯入 |
| `valid_period` `int4range`→`daterange` migration 會碰到既有查詢（2.6 territories、3.5 前端篩選）與西元前年份轉換 | med | migration 任務內一併改查詢與測試；用全新 volume 重建資料庫驗證（比照 2026-08-31 吳疆域匯入的驗證方式） |
| 中國戰區「點線佔領」以多邊形概括，精度有限 | low | 已知限制，以「不完全控制」網底誠實呈現；點線建模列為二戰深化階段 |

## 8. 驗收與開放問題

**M4 驗收門檻**：Story 6-9 AC 全過；I1／I3／I5／I6 由測試覆蓋；E2E 涵蓋二戰主流程；既有三國 E2E 不退化。

**M4 前必須處理**：

- [ ] TODO（使用者自行判斷）：主權軸採用哪一份開放資料集（historical-basemaps GPL-3.0／europe-historical-geojson BSD-3 僅歐洲／CShapes CC BY-NC-SA 等），GPL copyleft 影響屬法律判斷，不由 AI 拍板（憲法 §10）。
- [ ] TODO：「敵對」控制區的判定規則（戰線推導用），實作任務動工前拍板。
- [ ] TODO：推估過渡的具體視覺樣式（虛線、不透明度數值、標籤位置），實作任務動工前拍板。
- [ ] TODO：二戰第一階段轉折點快照日期清單（§9 風險表為初步建議，需使用者確認）。
