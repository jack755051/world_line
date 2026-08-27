# World Line

World Line 是以 GIS 與時間軸呈現世界歷史的網頁專案。核心目標是在同一時間點比較多個政權的疆域、名稱、傳承與互動，同時保留史觀差異、時間不確定性與史料修正歷程。

## 目前狀態

截至 2026-08-27，專案仍在早期開發階段：

| 階段 | 狀態 | Repository 現況 |
|---|---|---|
| M1 資料層 | 已完成 | 15 張領域表、PostGIS、EF Core migrations、中國史示範 seed |
| M2 後端 MVP | 尚未開始 | 目前只有 `WeatherForecast` scaffold endpoint；業務 API、寫入驗證與 API Key 尚未實作 |
| M3 前端整合 | 尚未開始 | Angular scaffold 可啟動；MapLibre、時間軸與業務頁面尚未實作 |

Redis 容器已編排，但後端尚未接入快取。README 中的「目前狀態」描述已存在的功能；PRD 和 implementation plan 描述目標與後續工作，兩者不可混為一談。

## 文件導覽

| 文件 | 用途 | 權威範圍 |
|---|---|---|
| [業務憲法](.claude/constitutions/world-line.md) | 業務目的、術語、狀態機、I1-I5 不可變約束 | 業務規則 SSOT |
| [PRD](.claude/prds/world-line.md) | 使用者故事、技術決策、目標資料模型與 API 契約 | 已拍板的產品／技術基線 |
| [實作計畫](.claude/plans/world-line-implementation-plan.md) | M1-M3 任務、進度、停止條件與驗收方式 | 實作進度 SSOT |
| [架構說明](docs/architecture.md) | Current/Target 架構、資料流與責任邊界 | 工程架構入口 |
| [開發指南](docs/development.md) | 本機啟動、migration、seed、驗證與疑難排解 | 開發操作入口 |
| [API 說明](docs/api.md) | 可用 endpoint、OpenAPI、目標契約與認證狀態 | API 現況入口 |
| [歷史資料治理](docs/data-governance.md) | 來源、精度、爭議、修訂與 seed 使用規則 | 正式史料建檔準則 |
| [技術候選筆記](.claude/notes/world-line-tech-candidates.md) | PRD 訪談時的原始候選素材 | 僅供追溯，不是現行決策 |

若文件互相矛盾，先依「業務憲法 → PRD → 實作計畫」確認意圖，再以程式碼、migration 和測試確認實際行為，並在同一個變更中修正漂移文件。

## 技術與服務

- 前端：Angular 22，位於 `app/`
- 後端：.NET 10 Web API，位於 `api/`
- 資料庫：PostgreSQL 16 + PostGIS 3.4
- 快取：Redis 7（已編排，尚未被應用程式使用）
- 容器：Docker Compose；前端 production build 由 Nginx 提供

## 使用 Docker 快速開始

### 前置需求

- Docker Desktop 或相容的 Docker Engine，需支援 `docker compose`
- Git

### 啟動

1. 建立本機環境檔，並把預設密碼改成只供本機使用的值：

   ```bash
   cp .env.example .env
   ```

2. 驗證 Compose 設定並建置、啟動所有服務：

   ```bash
   docker compose config --quiet
   docker compose up --build
   ```

3. 服務入口：

   | 服務 | 位址 | 備註 |
   |---|---|---|
   | 前端 | http://localhost:4200 | 目前顯示 Angular scaffold |
   | 後端 API | http://localhost:5000 | Development 環境 |
   | OpenAPI JSON | http://localhost:5000/openapi/v1.json | 目前只包含 scaffold API |
   | PostgreSQL/PostGIS | localhost:5432 | 僅供本機開發連線 |
   | Redis | localhost:6379 | 尚未接入後端 |

4. 另開終端確認後端可回應：

   ```bash
   curl http://localhost:5000/weatherforecast
   ```

Development 環境啟動後端時會自動套用尚未執行的 EF Core migrations，並在 `regimes` 為空時加入示範 seed。示範疆域是用來驗證 schema 的矩形，不是可發布的正式歷史資料。

停止服務：

```bash
docker compose down
```

此指令保留資料 volume。任何刪除 volume 的操作都會移除本機資料庫，應先確認資料是否可重建。

## 本機開發

完整步驟見 [開發指南](docs/development.md)。最短流程如下。

先只啟動相依服務：

```bash
docker compose up -d postgres redis
```

後端需明確提供 connection string；`.NET` 不會自動讀取 repository 根目錄的 `.env`：

```bash
cd api
ConnectionStrings__DefaultConnection='Host=localhost;Port=5432;Database=appdb;Username=postgres;Password=change_me' dotnet run --launch-profile http
```

若修改過 `.env` 的資料庫名稱、帳號或密碼，請同步替換上面的值。本機 HTTP API 位於 http://localhost:5151，OpenAPI 位於 http://localhost:5151/openapi/v1.json。

前端：

```bash
cd app
npm ci
npm start
```

前端開發伺服器位於 http://localhost:4200。

## 基本驗證

```bash
docker compose config --quiet
dotnet build api/WorldLine.Api.csproj
npm --prefix app run build
npm --prefix app test -- --watch=false
```

目前 repository 尚無後端 test project，也尚未設定前端 E2E runner；兩者列在後續里程碑，不能把 scaffold test 當成業務驗收。

## 安全與資料注意事項

- `.env` 已被 gitignore；不要提交真實密碼或未來的 `API_WRITE_KEY`。
- `POSTGRES_PASSWORD=change_me` 只是範例，啟動前應更換。
- Docker Compose 目前使用 Development 環境並對 host 開放資料庫與 Redis port，不是 production hardening 設定。
- 正式史料不得直接沿用 seed 的簡化年份或矩形疆域；請遵守 [歷史資料治理](docs/data-governance.md)。

## 文件維護規則

完成一項實作時，至少同步檢查：

1. 實作計畫的任務狀態是否更新。
2. README「目前狀態」與可用 endpoint 是否改變。
3. PRD 的決策、風險、Open Questions 是否仍正確。
4. OpenAPI、`api/*.http` 與 migration 是否反映實際行為。
5. 涉及史料欄位或匯入時，資料治理規則是否仍能落實。
