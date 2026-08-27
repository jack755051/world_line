# Development Guide

本文件提供可重現的開發操作。若只想用 Docker 啟動整套服務，先看根目錄 [README](../README.md)。

## 前置需求

| 工具 | 版本／需求 |
|---|---|
| .NET SDK | 10.x |
| Node.js | 22.x |
| npm | 11.x；鎖定版本見 `app/package.json` |
| Docker | 支援 Compose v2 |
| EF Core CLI | 10.x；只有建立或人工操作 migration 時需要 |

Repository 目前沒有 `.config/dotnet-tools.json`，因此 `dotnet-ef` 尚未被鎖成 repository-local tool。若本機找不到 `dotnet ef`，需先安裝相容的 10.x CLI；後續應補 local tool manifest，消除版本漂移。

## 環境變數

`.env.example` 是 Docker Compose 的範本：

| 變數 | Current 用途 | 是否機密 |
|---|---|---|
| `POSTGRES_DB` | 建立本機資料庫，並組成容器 backend connection string | 否 |
| `POSTGRES_USER` | 本機資料庫帳號 | 否 |
| `POSTGRES_PASSWORD` | 本機資料庫密碼 | 是；不得提交真實值 |
| `API_WRITE_KEY` | M2 預定的寫入 API Key | 尚未實作、目前不需設定 |

`.NET` 不會自動載入 repository 根目錄的 `.env`。在 host 上執行 backend 時，必須透過環境變數或未進版控的 local settings 明確提供 `ConnectionStrings__DefaultConnection`。

## 開發模式 A：全部使用 Docker

```bash
cp .env.example .env
docker compose config --quiet
docker compose up --build
```

檢查：

```bash
curl http://localhost:5000/weatherforecast
curl http://localhost:5000/openapi/v1.json
```

查看服務狀態與 log：

```bash
docker compose ps
docker compose logs backend postgres
```

停止服務但保留資料：

```bash
docker compose down
```

## 開發模式 B：相依服務使用 Docker，程式跑在 host

啟動 PostGIS 與 Redis：

```bash
docker compose up -d postgres redis
```

啟動 backend；密碼需與 `.env` 一致：

```bash
cd api
ConnectionStrings__DefaultConnection='Host=localhost;Port=5432;Database=appdb;Username=postgres;Password=change_me' dotnet run --launch-profile http
```

Backend HTTP 位址為 http://localhost:5151。Development 啟動會：

1. 套用尚未執行的 EF Core migrations。
2. 若 `regimes` 完全沒有資料，加入漢／魏／蜀漢／吳／晉示範 seed。
3. 公開 `/openapi/v1.json`。

Seed 的 idempotency 是「只要已有任何 regime 就整批略過」，不是逐筆 upsert。資料庫若只有部分 seed，不會自動補齊。

另開終端啟動 frontend：

```bash
cd app
npm ci
npm start
```

Frontend 位址為 http://localhost:4200。目前 dev-server 沒有 `/api` proxy；業務串接開始前需補上設定。

## Migration 工作流程

先確認 model 可以編譯：

```bash
dotnet build api/WorldLine.Api.csproj
```

列出 migration：

```bash
dotnet ef migrations list --project api/WorldLine.Api.csproj --startup-project api/WorldLine.Api.csproj
```

建立 migration 時使用能說明 schema 意圖的名稱：

```bash
dotnet ef migrations add DescriptiveMigrationName --project api/WorldLine.Api.csproj --startup-project api/WorldLine.Api.csproj
```

Migration 產生後必須：

1. Review `Up`、`Down` 與 model snapshot，不只確認命令成功。
2. 在實際 `docker-compose.yml` 流程套用，不能只測臨時資料庫。
3. 確認既有資料的 migration path，不只驗證空資料庫。
4. 若表或約束改變，同步更新 PRD §6、架構文件與資料治理文件。

Development 的自動 migration 只供本機使用。正式環境的備份、migration approval 與 rollback 流程尚未設計，首次部署前必須補齊。

## 驗證

目前可執行的 repository-level checks：

```bash
docker compose config --quiet
dotnet build api/WorldLine.Api.csproj
npm --prefix app run build
npm --prefix app test -- --watch=false
```

目前限制：

- 沒有 backend test project。
- 前端只有 scaffold unit tests。
- 沒有 E2E runner。
- 正式業務 endpoint 尚未實作，因此 OpenAPI 目前不能作為業務驗收。

Phase 2 完成後，backend unit/integration tests 與 OpenAPI completeness 都是必要門檻；Phase 3 完成後需增加主要使用流程 E2E。

## 常見問題

### `Connection string 'DefaultConnection' not found`

Host 上執行 `dotnet run` 時沒有提供 `ConnectionStrings__DefaultConnection`。使用本文件的 inline environment variable，並確認資料庫名稱、帳號與密碼和 `.env` 一致。

### 修改 `.env` 密碼後仍無法登入 PostgreSQL

PostgreSQL image 只在第一次建立資料 volume 時初始化帳號與密碼。修改 `.env` 不會改寫既有 volume 中的帳號。優先使用原密碼或在資料庫內安全地修改；若要刪除 volume 重建，先確認其中沒有需要保留的資料。

### Backend 啟動時 migration 或 seed 失敗

先檢查 `docker compose ps` 與 `docker compose logs postgres backend`。確認 PostGIS healthcheck 通過、connection string 正確，以及 migration history 和 repository migration 檔案一致。

### `ng e2e` 找不到 target

目前尚未設定 E2E runner，這是預期狀態。不要臨時把 `ng e2e` 加入 CI；應在 M3 選定 runner 後連同第一條主流程測試一起導入。

## 完成定義

一項功能不能只以「可以在本機跑」視為完成。至少應同時具備：

- implementation plan 對應任務與驗收條件已更新；
- 自動化測試或清楚記錄的暫時手動驗證；
- OpenAPI／`api/*.http` 與實際 endpoint 一致；
- README 或操作文件沒有留下過時現況；
- migration、seed 與正式史料界線清楚；
- 新增環境變數已加入範例與說明，未提交秘密值。
