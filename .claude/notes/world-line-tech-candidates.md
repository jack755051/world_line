# World Line — 技術選型候選清單（PRD 訪談用暫存筆記）

> 用途：`/supervisor:prd world-line` 訪談時的候選技術輸入素材。
>
> **文件狀態（2026-08-27）**：本檔保留訪談前的候選與探索脈絡，不是現行技術決策 SSOT。凡是「候選／待選型／checklist」文字都可能已過時；現行決策以 `.claude/prds/world-line.md` 為準，實作進度以 `.claude/plans/world-line-implementation-plan.md` 為準。尤其 npm `edtf` 只保留為早期候選，不代表 .NET 後端的定案套件。
> 非正式文件（不是憲法、不是 ADR、不是 PRD），不寫入 `.claude/constitutions/world-line.md`。
> 來源：使用者 2026-08-24 查閱整理。

---

## 快速目錄導覽 (ToC)

- **[技術選型與架構]**
  - [一、GIS 與時間軸架構（資料層 / 切片層 / 渲染層）](#一gis-與時間軸架構資料層--切片層--渲染層)
  - [二、套件與引擎工具鏈推導清單](#二套件與引擎工具鏈依業務規則時間軸連續變化視角切換多重紀年模糊區間海量向量圖資推導)
  - [三、開源歷史地理資料來源](#三開源歷史地理資料來源繪製-geojson-疆域的基礎骨幹)
- **[UI 互動與中立史觀設計]**
  - [四、前端互動架構草圖](#四前端互動架構草圖ui-層概念非最終設計)
  - [六、時間軸多尺度縮放（Adaptive Zoom）](#六時間軸多尺度縮放adaptive-zoom)
  - [七、圖層分工：疆域圖層 vs 事件圖層](#七圖層分工疆域圖層-vs-事件圖層)
  - [八、時空演進複合事件（以安史之亂為例）](#八時空演進複合事件spatio-temporal-composite-event)
  - [十、跨國爭端與多重視角並列（Multi-perspectivism）](#十跨國爭端與多重視角並列multi-perspectivism對應憲法-156)
- **[資料模型與 Schema 草案]**
  - [五、時間精度架構：EDTF + 小數年份雙欄位模型](#五時間精度架構edtf--小數年份雙欄位模型解決精確到日vs只到年世紀問題)
  - [九、historical_events 資料表 Schema 草案](#九historical_events-資料表-schema-草案)
  - [十.2、爭議事件多重視角資料模型](#2-爭議事件的結構化資料模型)
- **[待辦與決策追蹤]**
  - [十一、待 PRD 訪談時確認的選型問題（Checklist）](#十一待-prd-訪談時確認的選型問題草擬供-supervisor-反問參考)

---

## 一、GIS 與時間軸架構（資料層 / 切片層 / 渲染層）

### 1. 資料層：PostgreSQL + PostGIS
- 幾何儲存：`GEOMETRY(MultiPolygon, 4326)`，儲存政權不同階段疆界
- 時間約束（對應憲法 I1）：PostgreSQL 原生區間型別 `int4range(start_year, end_year, '[]')`，例如 `[618, 907]`
- 索引：GiST 複合索引（空間 `GIST(geom)` + 時間 `GIST(valid_period)`），支援 `valid_period @> 618` 毫秒級查詢

### 2. 資料供應：動態向量圖磚 / GeoJSON 切片
- 小範圍/聚焦模式：直接回傳 GeoJSON，方便前端形變過渡動畫
- 全球宏觀視野：`ST_AsMVT` 動態切成 Mapbox Vector Tiles (MVT)，或依世紀/年代建快取

### 3. 前端地圖引擎（候選，待選型）
- **MapLibre GL JS**：開源、效能佳、原生支援時間過濾器（Filter Expressions），GPU 端切換顯示
- **Deck.gl + MapLibre**：適合未來擴充貿易路線、行軍路線、傳播軌跡等高階視覺化

---

## 二、套件與引擎工具鏈（依業務規則「時間軸連續變化」「視角切換」「多重紀年」「模糊區間」「海量向量圖資」推導）

| 層級 | 候選工具 | 對應需求 |
|---|---|---|
| 底圖渲染 | MapLibre GL JS + Deck.gl | 全球政權圖層渲染、多邊形著色、貿易路線飛線 |
| 圖資壓縮與形變 | TopoJSON + Flubber.js | 縮減邊界傳輸量（共享邊界 arcs，體積減 70-80%）、疆域膨脹/退縮平滑過渡動畫（對應憲法 §9 連續變化） |
| 空間幾何分析 | Turf.js (`@turf/turf`) | 動態計算朝代文字置中點（`turf.centroid`/`centerOfMass`）、邊界距離檢測、多邊形簡化（`turf.simplify`） |
| 時間與狀態 | D3-Scale (時間比例尺) + XState | 西元/BCE 連續滑桿拉動；政權狀態機（存續/分裂/禪讓取代/亡於武力，對應憲法 §4）防呆攔截 |
| 紀年轉換 | `lunar-javascript` / `cnlunar` / 年號對照表 | 西元年 ↔ 廟號/年號（武德、貞觀、開元）雙向映射（對應憲法 §9 多重紀年） |
| 時間格式化 | Dayjs/Luxon + 自訂 BCE 擴充 | JS 原生 Date 不支援西元前/無西元0年，需自訂處理負數年份（如 -221 = 西元前221年） |
| 向量切片服務 | Martin Tile Server（Rust）或 Tegola | 直連 PostGIS 動態切 MVT/PBF，餵給 MapLibre GL，避免巨量 GeoJSON 卡頓 |
| 靜態/離線切片 | PMTiles | 單一檔案金字塔圖磚，支援 HTTP Range Request，適合離線展示/純靜態主機（S3/R2） |

---

## 三、開源歷史地理資料來源（繪製 GeoJSON 疆域的基礎骨幹）

| 專案 | 簡介 |
|---|---|
| CHGIS（哈佛中國歷史地理資訊系統） | 中國歷代疆域、政區演變、地名 Shapefile/GeoJSON |
| CShapes / Historical GIS Datasets | 全球近現代與部分古代邊界演變標準空間資料集 |
| OpenHistoricalMap (OHM) | 歷史版 OSM，以 `start_date`/`end_date` 標籤組織全球歷史圖資 |
| GeaCron | 商業級歷史時間軸地圖，可作互動原型參照對象 |

---

## 四、前端互動架構草圖（UI 層概念，非最終設計）

- 全域時間軸（Global Time Scrubber）：底層數值對齊西元年，支援負數（西元前，如 -221）
- 播放器：自動向前播放（類氣象雲圖），支援「年」或「大事記關鍵影格」跳轉
- 多重視角動態標註：依「觀察主體（Active Focus）」動態算 Label（對應憲法 §6 命名機制）
  - 全球客觀視角 vs 唐朝主觀視角（阿拉伯→大食、拜占庭→拂菻）
- 點擊政權聚焦（對應憲法 §3 R3）：高亮存續區間、地圖平滑聚焦、列出同時期周邊政權

---

## 五、時間精度架構：EDTF + 小數年份雙欄位模型（解決「精確到日」vs「只到年/世紀」問題）

### 1. 問題背景
古代事件通常只有「年」（甚至模糊到世紀），但近代史（十月革命、七七事變）需精確到「月／日」。
- 資料庫只用單純「年（整數）」→ 無法表達 `1937-07-07`
- 直接用原生 `DATE`/`TIMESTAMP` → 無法儲存「西元前 221 年（無月日）」，也無法處理「西元 0 年不存在」的曆法問題

解法：**「時間連續數值軸（浮點數）」+「階層式日期結構（EDTF）」雙欄位並存**，同時滿足「人類語意」與「電腦索引計算」。

### 2. 雙層時間資料模型
事件與疆域應同時具備語意欄位與索引欄位：

```
event-marco-polo-bridge
  name:            "七七事變（盧溝橋事變）"
  edtf_date:       "1937-07-07"     -- 人類語意 / 國際標準（支援月/日/區間/模糊）
  start_decimal:   1937.514         -- 電腦計算 / 拉桿滑動 / PostGIS 索引專用
  end_decimal:     1937.514
  geom:            POINT(116.216, 39.851)
```

### 3. 人類與歷史學標準：EDTF（Extended Date/Time Format，ISO 8601-2 延伸）
- 精確到日：`1937-07-07`（七七事變）
- 精確到月／區間：`1917-11-07/1917-11-08` 或 `1917-11/1917-12`（十月革命）
- 僅精確到年：`0618`（唐朝建立）
- 模糊/爭議年份：`1046?`（武王伐紂推測年份，問號標記不確定性）

### 4. 機器索引：小數年份（Decimal Year）
供前端 Slider 與 PostGIS 做平滑數值過濾：
- 公式：`DecimalYear = Year + (DayOfYear / TotalDaysInYear)`
- 範例：`1937-07-07` → `1937 + 188/365 ≈ 1937.515`
- 查詢 `WHERE valid_period @> 1937.515` 仍可毫秒級完成（沿用 §1 的 GiST 時間索引）

---

## 六、時間軸多尺度縮放（Adaptive Zoom）

從「看 2000 年的唐代宏觀版圖」切到「看 1937 年 7 月 7 日的抗日戰爭」時，時間軸粒度需動態改變。

### 1. 雙層時間軸（Dual-level Scrubber）
- **主軸**：以「世紀／年」為單位快速滑動（例：`1800 — 1900 — 1937 — 2000`）
- **副軸（展開軸）**：拉桿停在近代或點擊特定事件時，下方展開「月／日」局部精細時間軸（例：`5月 — 6月 — 7月7日 — 8月 — 9月`）

### 2. 語意縮放（Semantic Zooming）
| 尺度 | 地圖顯示內容 |
|---|---|
| 年級尺度（Year Scale） | 政權疆域面（Polygons）＋ 百年大事件 |
| 日/月尺度（Day/Month Scale） | 事件標記點（Marker／Heatmap）＋ 部隊行軍箭頭（LineString） |

---

## 七、圖層分工：疆域圖層 vs 事件圖層

「政權疆域」與「歷史事件」應為兩套獨立但相互關聯的圖層：

| 圖層類型 | 幾何型態 | 時間粒度 | 典型範例 | 表現方式 |
|---|---|---|---|---|
| 疆域圖層（Regime Area） | `MultiPolygon` | 以「年」或「政權變遷期」為單位 | 唐朝疆域 (618–907)、中華民國疆域 (1937) | 半透明填色區塊、邊界線 |
| 事件圖層（Historical Event） | `Point` / `LineString` | 精確到「日」、「月」、「區間」 | 盧溝橋事變 (1937-07-07)、赤壁之戰 (208) | 閃爍紅點、衝突圖示、戰役進攻箭頭 |

互動邏輯（以拉到 `1937-07-07` 為例）：
1. 底圖穩定渲染 1937 年的大陸與各勢力疆域（Polygon，不隨事件變動）
2. 事件圖層依浮點時間高亮「宛平城盧溝橋」紅色標記（Point）
3. 點擊該點 → 側邊欄彈出事件詳情，可點「聚焦此戰役時間線」→ 時間軸自動切換為日級微觀模式（§6 副軸展開）

**設計優勢**：政權底圖與事件疊加層解耦，事件的範圍/路線不會破壞既有疆域結構。

---

## 八、時空演進複合事件（Spatio-temporal Composite Event）

跨越數年、空間動態遷移的重大事件（如安史之亂 755–763、黃巢之亂 875–884），需要比 §七 單點事件更複雜的資料與互動結構。

### 1. 觸發點呈現原則：不建議直接綁死首都
事件觸發點若一律放在首都會失去地理真實性（安史之亂爆發於**范陽／幽州**而非長安／洛陽；武昌起義在武昌而非北京）。

### 2. 兩種顯示狀態
- **常態檢視**（未聚焦，時間軸滑過 755 年）：
  - 事件起始點標記（Origin Point）：在事件**爆發原點**（范陽、冤句/曹州）顯示脈動/發光圖示（Pulse Marker），標註「755 安史之亂爆發」
  - 時間軸關鍵標記（Keyframe Pin）：滑桿上方標記活躍區間 `[755 === 763]`
- **事件聚焦狀態**（點擊標記/打開詳情）：
  - 疊加渲染「影響範圍多邊形（Influence Polygon）」＋「進攻動線箭頭（Route Line）」（例：范陽 → 洛陽 → 長安）

### 3. 互動流程與動效
1. **Camera 運鏡**：點擊事件點後 `map.flyTo({ center: [范陽座標], zoom: 5.5, pitch: 30 })` 平滑移動並帶微透視視角
2. **圖層高亮（Spatial Overlay）**：載入影響範圍圖層（半透明條紋/漸層多邊形，覆蓋河北、河南、關中）＋動態進軍箭頭（LineString）
3. **毛玻璃側邊抽屜（Glassmorphism Drawer）**：
   - 視覺：`backdrop-filter: blur(16px); background: rgba(20,20,25,0.75); border: 1px solid rgba(255,255,255,0.1);`
   - 內嵌手風琴（Accordion）三層：
     - 第一層：背景與起因（安祿山起兵、范陽節度使背景）
     - 第二層：關鍵轉折時間點（點擊「756年 潼關失陷」→ 地圖視角轉向潼關 + 時間軸前進到 756，時間與地圖雙向連動）
     - 第三層：歷史影響（人口銳減、藩鎮割據形成）

---

## 九、`historical_events` 資料表 Schema 草案

需同時滿足「精確起訖時間」「原點座標」「影響範圍面」「進軍路徑線」「結構化手風琴內容」：

```sql
CREATE TABLE historical_events (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,                  -- 例: "安史之亂"
    event_type VARCHAR(32) NOT NULL,              -- rebellion / war / treaty ...

    -- 時間維度（對應 §五：EDTF + decimal 雙欄位）
    start_edtf VARCHAR(32) NOT NULL,              -- '0755-12-16'
    end_edtf VARCHAR(32) NOT NULL,                -- '0763-02-17'
    start_decimal NUMERIC(8,3) NOT NULL,          -- 755.956
    end_decimal NUMERIC(8,3) NOT NULL,            -- 763.131

    -- 空間幾何（PostGIS，對應 §八）
    origin_point GEOMETRY(Point, 4326),           -- 爆發點（范陽座標）
    influence_area GEOMETRY(MultiPolygon, 4326),  -- 整體波及範圍
    routes GEOMETRY(MultiLineString, 4326),       -- 進軍/遷移路徑

    -- 結構化富文本（對應 §八 手風琴三層內容）
    sections JSONB                                -- [{ title: "背景", content: "..." }, ...]
);
```

地圖過濾範例（時間軸拖到 758.0 年）：

```sql
SELECT id, name,
       ST_AsGeoJSON(origin_point) AS origin,
       ST_AsGeoJSON(influence_area) AS area,
       ST_AsGeoJSON(routes) AS routes,
       sections
FROM historical_events
WHERE start_decimal <= 758.0 AND end_decimal >= 758.0;
```

> 註：此表與 §一資料層的政權疆域表（`int4range` + `MultiPolygon`）為平行的兩張表，對應 §七的圖層分工——政權底圖穩定渲染，事件表作為疊加層查詢，兩者用 `start_decimal/end_decimal` 或 `int4range` 同一套時間過濾邏輯即可對齊。

---

## 十、跨國爭端與多重視角並列（Multi-perspectivism，對應憲法 §1／§5／§6）

跨國歷史事件（戰役、條約、外交衝突）最忌諱「由單一敘事立場撰寫定論」。中立客觀的核心不是「抹平差異、寫折衷文字」，而是**結構化並列多重視角與可溯源史料**，把裁判權交給讀者。

### 1. UI／互動架構：多重視角分頁（Perspective Tabs）
毛玻璃手風琴彈窗不寫成單一維度的「故事」，而是「客觀事實骨幹 + 各方主觀敘事」並列：

```
📜 七七事變（盧溝橋事變 / 蘆溝橋事件 / Marco Polo Bridge Incident）
時間: 1937-07-07 起 | 地點: 北平西南宛平城・盧溝橋
--------------------------------------------------------------
[ 🌐 客觀經過概要 ] [ 🇹🇼 中華民國視角 ] [ 🇯🇵 日本帝國視角 ] [ 🌍 國際第三者視角 ]
--------------------------------------------------------------
> 關鍵爭議點（Controversies）
  - 第一槍責任歸屬：中日雙方各執一詞，戰後史學界考證假說並列呈現
> 參戰兵力與傷亡數據（並列呈現，不採單一來源）
```

具體規範：
- **多重命名並列（Title Aliasing）**：標題同時列出當事各國官方歷史稱呼（例：`七七事變 / 蘆溝橋事件 / Marco Polo Bridge Incident`；`黑船事件 / 黑船來航 / Perry Expedition`），呼應憲法 §6 命名視角機制
- **切換觀察者（Active Observer）**：使用者切換「以日本視角縱覽 19 世紀」時，黑船事件預設展開日方敘事；切換「以美方視角」則展開培里遠征敘事，呼應憲法 §5 追溯自稱
- **並列文獻引註（Primary Source Citations）**：不由系統做道德裁判，直接引述當時雙方官方文告、條約原文、當事人日記，交給讀者評判

### 2. 爭議事件的結構化資料模型
在 `historical_events`（§九）之外，另拆兩張表承載「各方敘事」與「爭議點」：

```sql
CREATE TABLE historical_event_perspectives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(64) REFERENCES historical_events(id),

    regime_id VARCHAR(64) NOT NULL,             -- 該視角主體，例 "regime-roc" / "regime-japan-empire"

    local_name VARCHAR(128) NOT NULL,           -- 該方對此事件的稱呼，例 "盧溝橋事變" vs "蘆溝橋事件"
    narrative_summary TEXT NOT NULL,            -- 該方立場主張與敘述
    official_justification TEXT,                -- 該方行動的官方理由
    primary_sources JSONB,                      -- [{ "title": "廬山聲明", "author": "蔣中正", "year": 1937 }]

    claimed_casualties JSONB                    -- { "own_loss": "約100人", "enemy_loss": "不詳" }，雙方數據常有出入，並列而非取捨
);

CREATE TABLE historical_event_controversies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(64) REFERENCES historical_events(id),
    topic VARCHAR(128) NOT NULL,                -- 例 "第一槍由誰射擊"、"開戰動機"
    neutral_description TEXT NOT NULL,          -- 中立陳述目前史學界研究現況
    viewpoints JSONB                            -- 各方學說/證據清單
);
```

> 與 §九 的關係：`historical_events` 是「客觀事實骨幹」（時間、地點、幾何），`historical_event_perspectives` 是「各方主觀敘事層」，一對多；`historical_event_controversies` 承載史學界尚無定論的爭議點，避免系統替使用者下結論。

### 3. 空間地圖上的中立呈現技巧
文字之外，地圖繪製方式本身也可能帶有立場：
- **爭議控制區用斜線網底／斑馬紋（Hatched Pattern）**：領土歸屬在當時有爭議或交火重疊區（如日俄戰爭時期的中國東北），不填單一國家色，改用雙方代表色交替斜線或標註「軍事爭奪區／中立國宣告區」
- **事件圖示用無情緒中立符號**：避免帶價值判斷的圖標（正義之劍 vs 侵略火燄），統一用專業軍事/歷史地圖符號（交叉刀劍 = 交戰點、虛線 = 部隊動線、圓圈 = 條約簽署地）
- **邊界變更以條約為時間錨點**：例如以 1905 年《朴資茅斯條約》為錨點展示庫頁島南部控制權轉移前後，以國際條約作為邊界演變的客觀依據，而非任一方單方宣告

### 4. 撰寫歷史文案的四大中立準則
| 準則 | 避免（單一主觀敘事） | 推薦（結構化中立敘事） |
|---|---|---|
| 用詞去情緒化 | 「美帝國主義野蠻逼迫日本開國」 | 「美國海軍准將培里率艦隊抵達浦賀，要求江戶幕府解除鎖國並通商（黑船來航）」 |
| 動機歸屬交代 | 「日軍蓄意製造事端發動侵略」 | 「中方主張日軍藉故挑釁並砲擊城防；日方則宣稱遭中方部隊槍擊而還擊，雙方停戰談判破裂後爆發全面衝突」 |
| 多方命名尊重 | 僅寫「日俄戰爭」 | 標註「日俄戰爭（日：日露戦争 / 俄：Русско-японская война）」並補充大清帝國宣告中立的背景 |
| 數據落差並列 | 只採其中一國公布的傷亡數字 | 表格化「中方統計 / 日方統計 / 現代第三方學者估計」三欄並列 |

### 5. 斜線網底（Hatched Pattern）技術實作方案（MapLibre GL JS）
呼應上方 §3「爭議控制區使用斜線網底」，MapLibre GL JS 實作有三種主流方案，取捨在於「動態程度」vs「開發成本」：

| 方案 | 作法 | 優點 | 缺點 |
|---|---|---|---|
| ① 圖片紋理（Image Pattern） | 準備一張無縫平鋪的斜線 PNG，`map.loadImage()` 載入後以 `fill-pattern` 套用到 `fill` 圖層 | 實作最簡單、效能最好、瀏覽器相容性最佳 | 紋理是靜態像素，縮放地圖時斜線粗細/間距不變；換色需準備多張圖 |
| ② Canvas 動態產生（Canvas Pattern） | 用離屏 `<canvas>` 以 `strokeStyle`/`lineWidth` 畫 45° 斜線，執行期產生後 `map.addImage()` | 比方案①靈活，可在執行期依需求（如深色模式）重新產生不同顏色紋理，開發成本低 | 本質仍是靜態像素貼圖，縮放時同樣有方案①的問題 |
| ③ 自訂 WebGL Shader（Custom Layer） | 撰寫 `type: 'custom'` 圖層，在 fragment shader 用 `gl_FragCoord` + `sin`/`mod`/`step` 計算斜線，斜線間距/顏色/動畫皆為 Uniform 變數 | 完全動態：縮放時斜線視覺寬度可保持一致、可做流動動畫呼應憲法 §9「連續變化」 | 技術門檻高（需 WebGL/Shader 知識），且需自行處理 GeoJSON 多邊形三角化（Tesselation） |

**分階段建議**：
- **MVP 階段**：採方案②（Canvas 動態產生），開發成本低、又比純靜態 PNG 靈活，足以先滿足「中立灰階斜線標示爭議區」的視覺需求。
- **成熟階段（對應時間軸形變動畫成熟後）**：若要讓斜線網底縮放不失真、並做出流動動畫呼應疆域「連續變化」的視覺語言，再升級到方案③（Shader）。

> 對應 §十一原本的開放問題「斜線網底在 MapLibre GL 效能疑慮」：結論是效能瓶頸主要出現在方案③的多邊形三角化與大量爭議區同時 Shader 繪製時，MVP 用方案②可先規避此風險。

---

## 十一、待 PRD 訪談時確認的選型問題（草擬，供 supervisor 反問參考）
- [ ] 地圖引擎最終選：MapLibre GL JS 單獨 vs 搭配 Deck.gl？
- [ ] 資料供應策略：純 GeoJSON vs MVT（Martin/Tegola）vs PMTiles 靜態？三者是否分階段導入？
- [ ] 是否現階段就導入 XState 管理政權狀態機，或先用簡單 enum + 應用層邏輯？
- [ ] 紀年轉換庫：`lunar-javascript` 是否涵蓋非中國紀年（日本昭和、民國年等），或需自建年號對照表？
- [ ] 西元前/連續時間軸的底層數值型別與運算模組要不要自建，還是有更成熟的 library？
- [ ] 開源歷史地理資料（CHGIS/OHM/CShapes）授權條款是否符合本專案使用情境（含未來教育用途）？
- [ ] EDTF 字串是否用現成 parser（如 npm `edtf`）解析，或自建正則/欄位驗證？後端要不要在寫入時強制校驗格式？
- [ ] `start_decimal`/`end_decimal` 的計算時機：寫入時由後端從 EDTF 自動推算，還是留給資料建置腳本離線批次算好？平閏年造成的誤差是否需要更精確的公式？
- [ ] 事件圖層與疆域圖層在前端的疊圖管理（z-index、圖層開關 UI）要怎麼設計？是否需要圖層控制面板？
- [ ] 毛玻璃側邊抽屜／手風琴的 UI 元件要自建 CSS，還是用 Radix/shadcn 之類的 headless component library？
- [ ] `influence_area`/`routes` 幾何資料的繪製精度取捨：走嚴謹史學考據（可能大量缺資料）還是先用示意性/近似路線滿足視覺呈現，未來再逐步精修？
- [ ] 「爆發原點」座標的史料來源與標準：由誰考據、如何標註不確定性（例如座標本身也可能有模糊區間）？
- [ ] `historical_event_perspectives` 的 `regime_id` 要不要強制對應到已建檔的政權實體，還是允許自由文字（例如「國際第三者」這種非政權主體）？
- [ ] 多重視角分頁（Perspective Tabs）預設要顯示哪一個 Tab：跟隨使用者當前「Active Focus」政權，還是永遠先開「客觀經過概要」？
- [ ] `historical_event_controversies` 的 `viewpoints` 結構要不要標準化 schema（例如強制附學者/文獻來源），避免變成無來源的猜測堆疊？
- [x] ~~爭議控制區的斜線網底（Hatched Pattern）在 MapLibre GL 用 pattern fill 實作是否有效能疑慮~~ → 已有初步技術方案，見 §十.5（MVP 用 Canvas Pattern，成熟階段再升級 Shader）
- [ ] 斜線網底 MVP 方案（Canvas Pattern）的顏色/間距參數要不要做成可設定的「中立配色 Design Token」，避免不同開發者各自硬編碼出不一致的視覺語言？
