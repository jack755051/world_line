# src/app 目錄

依 PRD §5「目錄結構」：

| 目錄 | 內容 |
|---|---|
| `core/` | api client、`api-schema.ts`（`gen:api` 產生）、i18n、狀態（Signals） |
| `layout/` | app shell、top bar |
| `pages/` | `atlas`（主地圖頁 `/`）、`not-found` |
| `shared/` | map、timeline、legend、citation 等領域元件 |
| `components/ui/` | sanring UI 元件（`npx @sanring/cli add <component>` 安裝） |

樣式一律用 `--wl-*` token（`src/styles/wl-tokens.css`，數值來自 `design/stitch/DESIGN.md`）。
