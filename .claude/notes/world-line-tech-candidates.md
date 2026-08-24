# World Line — 技術選型候選清單（PRD 訪談用暫存筆記）

> 用途：`/supervisor:prd world-line` 訪談時的候選技術輸入素材。
> 非正式文件（不是憲法、不是 ADR、不是 PRD），不寫入 `.claude/constitutions/world-line.md`。
> 來源：使用者 2026-08-24 查閱整理。

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

## 待 PRD 訪談時確認的選型問題（草擬，供 supervisor 反問參考）
- [ ] 地圖引擎最終選：MapLibre GL JS 單獨 vs 搭配 Deck.gl？
- [ ] 資料供應策略：純 GeoJSON vs MVT（Martin/Tegola）vs PMTiles 靜態？三者是否分階段導入？
- [ ] 是否現階段就導入 XState 管理政權狀態機，或先用簡單 enum + 應用層邏輯？
- [ ] 紀年轉換庫：`lunar-javascript` 是否涵蓋非中國紀年（日本昭和、民國年等），或需自建年號對照表？
- [ ] 西元前/連續時間軸的底層數值型別與運算模組要不要自建，還是有更成熟的 library？
- [ ] 開源歷史地理資料（CHGIS/OHM/CShapes）授權條款是否符合本專案使用情境（含未來教育用途）？
