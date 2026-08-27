# API Guide

本文件區分「目前可呼叫的 API」與「PRD 目標契約」。詳細產品用途見 [PRD §7](../.claude/prds/world-line.md#7-api-契約-api-contract)，實作任務見 [implementation plan Phase 2](../.claude/plans/world-line-implementation-plan.md#3-phase-2m2後端-mvp)。

## 目前狀態

截至 2026-08-27，只有 .NET scaffold endpoint：

| Method | Path | Auth | 用途 |
|---|---|---|---|
| `GET` | `/weatherforecast` | 無 | Scaffold smoke test；不是 World Line 業務 API |

Docker：

```bash
curl http://localhost:5000/weatherforecast
```

Host `dotnet run --launch-profile http`：

```bash
curl http://localhost:5151/weatherforecast
```

`api/WorldLine.Api.http` 目前也只包含這個 request。PRD 中的 `/api/v1/*` 全部是 M2 目標，現階段不能呼叫。

## OpenAPI

ASP.NET OpenAPI 只在 Development 環境公開：

- Docker：http://localhost:5000/openapi/v1.json
- Host：http://localhost:5151/openapi/v1.json

M2 每完成一個 endpoint，都必須同步確認 OpenAPI 包含：

- path、method 與 query/path parameters；
- request body 與 response schema；
- 成功狀態碼；
- 主要 validation、authentication、not found 與 concurrency failure 狀態碼。

OpenAPI 是可執行契約，不取代 PRD 中「為什麼需要這個 endpoint」的說明。

## M2 目標資源

以下群組均尚未實作：

| Resource | 目標能力 | Plan 任務 |
|---|---|---|
| Reign eras | 依年份或政權查年號 | 2.3 |
| Regimes | 依時間查詢、單筆查詢、新增、合法狀態更新 | 2.4-2.5 |
| Territories | 政權疆域歷史、年份快照、新增與 I5 修正鏈 | 2.6-2.7 |
| Lineage presets | 列出史觀主線與排序政權 | 2.8 |
| Regime relations | 依時間查持續關係與新增關係 | 2.9 |
| Historical events | EDTF 查詢、父子事件、建立事件 | 2.10 |
| Tags | 事件多標籤 | 2.11 |
| Perspectives | 政權或 observer category 的敘事 | 2.12 |
| Controversies | 事件爭議點 | 2.13 |

完整 method/path 清單保留在 PRD §7 與 implementation plan，避免本文件在 endpoint 尚未實作前複製一份容易漂移的假契約。

## 已拍板的契約邊界

- 業務 API 使用 `/api/v1` prefix。
- 第一階段 GET 公開。
- POST/PATCH 使用固定 `X-API-Key`，值來自 backend 環境變數 `API_WRITE_KEY`；middleware 尚未實作。
- 政權狀態機與 EDTF 驗證必須由 backend 執行。
- 疆域回傳策略第一階段採 GeoJSON，不導入 MVT/PMTiles。
- I5 修正端點新增 replacement row 並保留原資料，不得直接覆蓋或刪除原史料。

## 尚未拍板的契約項目

在第一個業務 endpoint 實作前，必須決定並寫入 PRD/OpenAPI：

- 統一回應採直接 resource + RFC problem details，或 `{ statusCode, message, data }` wrapper；
- 列表分頁欄位、預設排序與最大 page size；
- 樂觀併發使用 body `version`、header `ETag/If-Match` 或其他方式；
- 日期／range query 的錯誤格式與邊界語意；
- GeoJSON 是直接回 `FeatureCollection`，或包在一般 response 中。

不得在不同 controller 各自選擇不同格式。

## Reverse proxy 注意事項

Production frontend image 的 Nginx 會把 `/api/` request 轉發到 backend，但目前 `proxy_pass http://backend:8080/;` 的尾端斜線會移除 `/api/` prefix。當 backend 開始實作 `/api/v1/*` 時，需先統一 browser-facing path 與 backend route，並加入 integration/E2E 測試，避免 `/api/v1` 被轉成 `/v1`。

Angular dev server 目前沒有 proxy configuration；詳見 [development guide](development.md)。

## Endpoint 完成檢查表

- [ ] 行為可追溯到 PRD user story／invariant。
- [ ] OpenAPI schema 與狀態碼完整。
- [ ] `api/*.http` 有可執行範例，且不含秘密值。
- [ ] GET/POST/PATCH 的 auth 規則一致。
- [ ] Validation 與 domain error 有 integration test。
- [ ] 幾何與時間欄位符合 [data governance](data-governance.md)。
- [ ] README/API 現況與 implementation plan 已同步更新。
