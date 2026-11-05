# Changelog

本文件依 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/) 格式撰寫，版本號遵循 [語意化版本](https://semver.org/lang/zh-TW/)。

---

## [0.0.1] - 2026-11-05

**涵蓋範圍：專案自 scaffold（`c94092e`）至 `c6633a3` 的全部開發。**

### 新增

#### 前後端骨架
- `feat(api)` 建立 .NET 10 Minimal API 骨架（`WorldLine.slnx`、`WorldLine.Api`、`WorldLine.Contracts`、`WorldLine.Api.Tests`）
- `feat(app)` 建立 Angular 22 + TypeScript + Tailwind CSS v4 前端骨架，整合 Sanring UI 元件庫
- `feat(api)` 加入 EF Core 10 + Npgsql + NetTopologySuite，完成初始 migration 與 PostGIS 支援
- `feat(api)` 建立 Clean Architecture 分層（Domain / Application / Infrastructure / Presentation）與 Repository Pattern
- `feat(api)` 實作統一回應格式 `ApiResponse<T>`、全域 Exception Filter、`DateIntervalCache`

#### 地圖與時間軸
- `feat(app)` 整合 MapLibre GL JS，實作底圖、主權多邊形填色與國名標籤（`capital-dot` / `capital-label`）
- `feat(app)` 實作連續地域漸變動畫（snapshot 間補間）
- `feat(app)` 拖拽式時間軸 Scrubber（主軸年份 + 副軸月份展開）
- `feat(app)` 聚焦蒙版（點選政權後突顯並遮蔽其他區域）、交戰弧線由首都出發
- `feat(app)` 底部時間軸加入版權署名列（© 2026 Sanring Tech. All rights reserved. ／ 開發者 Charlie Tai），桌機左右分列、手機置中

#### 國界、主權與控制區
- `feat(api)` 實作 `GET /sovereignty?date=&zoom=` 主權多邊形端點，依 zoom 層級簡化幾何
- `feat(api)` 實作 `GET /control?date=` 實際控制區與佔領端點
- `feat(api)` 實作 `GET /conflicts?date=` 交戰關係端點
- `feat(boundaries)` 生產環境預設使用同源 `/tiles/boundaries`、`/tiles/overlay`（PMTiles 圖磚），前端不再直接呼叫開發 Martin/nginx

#### 首都
- `feat(api)` 實作 `GET /capitals?date=` 首都點端點
- `feat(seed)` 完成首都 batch1–5（逾 100 筆，涵蓋歐洲、亞洲、美洲主要國家）

#### 領導人與生平
- `feat(api)` 建立 `leaders`、`leader_tenures`、`leader_bios` 資料表與端點（`GET /leaders?date=`、`GET /leader-bios/{id}`）
- `feat(seed)` 完成領導人 batch1–2（德國、英國、法國、義大利、蘇聯、美國、日本、中華民國等，約 150 筆任期）及生平 batch1 v2（UK 12 筆 + DE 25 筆）

#### 右側政權面板（§10 / §10 v2）
- `feat(app)` 政權面板（§10）：政權名稱、首都、事件、領導人分頁；`drag-handle` 可調寬度
- `feat(app)` §10 v2：固定面板寬度（432 / 384 / 360 px）、事件卡片展開（引用出處 C1、Show on map）、left rail 節點指示器、現在日期標線（T2）

#### 戰役簡報（§11.2 campaign）
- `feat(app)` CampaignService、CampaignPlayer 狀態機（無自動播放、3 秒/階段、末尾停止）
- `feat(app)` 戰役卡片（桌機 360px 左欄 / 手機底部 40vh）、地圖 fronts / arrows（arrowhead SDF 圖示）/ sites 圖層
- `feat(app)` 生產環境 `CAMPAIGNS_ENABLED = isDevMode()`，正式版隱藏所有戰役簡報入口

#### 衝突彈出視窗（§13）
- `feat(app)` MapLibre Popup 錨定衝突圖示（anchor 避開面板／時間軸）、手機衝突 sheet 140px peek/half；Esc / 空點 / 超出日期範圍自動關閉
- `feat(app)` 比例尺（km only，zoom < 3 隱藏，campaign 卡旁顯示）

#### RWD 響應式設計（§12）
- `feat(app)` 斷點 xs/sm/md/lg/xl + compact（height < 500）+ touch query（ViewportService）
- `feat(app)` 手機底部面板 peek 120 / half 50 vh / full 100 vh，手指跟隨並吸附，`safe-area-inset-bottom`
- `feat(app)` 手機頂部列（48px）：logo + World Line、ISO 日期（開啟時間軸日期輸入）、⋯ 選單（視角 / 語言 / 戰役 / 圖例）
- `feat(app)` 手機底部圖例改為獨立 bottom sheet（max 60vh、2 欄格線），取代 ⓘ 按鈕

#### 產品更名與品牌
- `feat(app)` 使用者可見產品名稱改為 **Sanring World Line**
- `feat(app)` 套用 Sanring World Line logo，地圖預設中心改為 1941 年波蘭（`[21.0, 51.8]`）

---

### 資料

- 1908–1945 全球主權邊界底圖來源：OpenHistoricalMap（OHM `admin_level=2`）
  - 歐洲（德、英、法、波蘭、捷克、低地國、斯堪地那維亞、巴爾幹等）
  - 蘇聯及蘇聯佔領區（1939–1945）
  - 亞洲（日本、中華民國、滿洲國、東南亞）
  - 非洲（74 政權、127 筆主權紀錄）
  - 北美（加拿大、紐芬蘭、聖皮耶與密克隆、美國）
  - 拉丁美洲（66 段邊界、37 政權）
  - 南亞、東南亞、大洋洲（1908–1937-07-06，新政權 27、主權紀錄 68）
- 首都資料：覆蓋歐洲、美洲、亞洲主要政權，逾 100 筆
- 領導人資料：德、英、法、義、蘇、美、日、中華民國等政權，約 150 筆任期
- 生平資料：UK 12 筆、DE 25 筆
- 戰役資料（campaign JSON）：但澤戰役 Fall Weiss（1939）、淞滬會戰（1937）、敦克爾克（1940）

---

### 部署

- `chore(docker)` 新增 `docker-compose.yaml`（開發，`postgres` + `api`，埠僅綁 `127.0.0.1`）
- `deploy` 新增 `docker-compose.prod.yml`（正式，`nginx` web + `martin` 圖磚 + `api` + `postgis` + `redis`；僅 nginx 開 80/443）
- `deploy` 新增 `scripts/prod-images.sh`（建置並推送正式映像至 `sanring` registry）
- `deploy` 以 Cloudflare Tunnel 取代 Caddy，`web` 服務改為 nginx，埠改 `127.0.0.1:4080`
- `docs(README)` 加入正式映像建置推送、VPS 操作、資料搬遷、PMTiles 圖磚上傳、Cloudflare Tunnel 完整說明

---

### 修正

- `fix(deploy)` 修正 `prod-images.sh` 中全形標點導致 `ENV_FILE` 變數展開失敗（非 UTF-8 locale 下 unbound variable）
- `fix(map)` 修正首都標籤被聚焦蒙版邊緣截斷；已選政權外的首都予以隱藏
- `fix(map)` 修正維琪法國國名與地圖出處重複、圖磚模式空態
- `fix(map)` 國名標籤一般化適配（依面積縮放字型、折行、短名稱更多錨點）以確保大型政權持續顯示標籤
- `fix(seed)` 修正 34 筆遺留首都的時間邊界，使其不超出政權存續期間
- `fix(seed)` 修正領導人 batch2（80 筆錯誤資料軟撤回並補回驗證版本；加入 15 筆英國君主、張伯倫、法國總統）
- `fix(leader)` 修正缺少 `retractedAt` 的生平記錄被錯誤視為已撤回；隱藏空白生平欄位

---

[0.0.1]: https://github.com/jack755051/world_line/compare/c94092e...c6633a3
