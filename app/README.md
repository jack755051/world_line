# World Line Web App

這是 World Line 的 Angular 22 前端。完整專案狀態、Docker 啟動方式與文件導覽請先看 repository 根目錄的 [README](../README.md)。

## 目前狀態

前端仍是 Angular CLI scaffold，尚未實作 PRD 中的 MapLibre 地圖、時間軸、政權聚焦、多重視角與事件抽屜。現有 unit test 只驗證 scaffold component，不代表業務功能已完成。

## 前置需求

- Node.js 22
- npm 11（實際版本以 `package.json` 的 `packageManager` 為準）

## 安裝與啟動

在 `app/` 目錄執行：

```bash
npm ci
npm start
```

開發伺服器位於 http://localhost:4200，修改檔案後會自動重新編譯。

目前尚未設定 Angular dev-server 的 `/api` proxy；在前端開始串接後端前，需新增 proxy configuration 或使用明確的開發環境 API base URL。Docker/Nginx build 已把 `/api/` 反向代理到 backend container，但這不會套用到 `npm start`。

## 常用指令

```bash
# Development server
npm start

# Production build
npm run build

# 單次執行 unit tests
npm test -- --watch=false

# 持續監看 build
npm run watch
```

建置輸出位於 `dist/app/browser/`，Dockerfile 會把它複製到 Nginx runtime image。

## 測試狀態

- Unit test runner：Vitest，由 Angular build system 執行。
- 目前測試：`src/app/app.spec.ts` 的 scaffold smoke tests。
- E2E：尚未選擇或設定 runner，`angular.json` 沒有 `e2e` target，因此目前不要使用 `ng e2e` 作為驗證指令。

M3 預計加入時間軸、疆域形變、政權聚焦與事件詳情的主要 E2E 流程；進度以 [實作計畫](../.claude/plans/world-line-implementation-plan.md) 為準。

## 程式碼產生

需要 Angular schematic 時，使用專案鎖定的 CLI：

```bash
npx ng generate component component-name
npx ng generate --help
```

新增功能時，同步補上 unit test；新增可互動的主要流程時，待 E2E runner 建立後補上 E2E coverage。
