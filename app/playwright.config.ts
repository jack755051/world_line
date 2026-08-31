import { defineConfig, devices } from '@playwright/test';

/**
 * 任務 3.16：E2E 測試主流程。**只用 Playwright 自己的 Chromium，不透過 claude-in-chrome
 * 擴充功能**——這次對話環境裡，擴充功能開的分頁會被 Chrome 當成背景分頁處理
 * （`document.visibilityState === 'hidden'`），`requestAnimationFrame` 整個不跑，
 * MapLibre 的 WebGL 渲染迴圈永遠完成不了第一幀、`'load'` 事件永遠不觸發，見
 * implementation plan 任務 3.12 的記錄。**Playwright 自己啟動的瀏覽器分頁沒有這個
 * 問題**（已用一次性 spike 測試驗證：`document.visibilityState` 回傳 `'visible'`，
 * `GET /api/v1/territories` 正常發出），這是這個對話環境裡唯一能真的讓 WebGL 地圖
 * 跑起來的自動化路徑，也是選 Playwright（而不是先確認過的其他工具）的直接理由。
 *
 * `baseURL` 指向 `docker-compose.yml` 的 frontend service（見 README/docs/
 * development.md），測試執行前要先 `docker compose up -d --build frontend backend`。
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: false, // 主流程測試本來就是單一情境從頭走到尾，不需要平行化
  use: {
    baseURL: 'http://localhost:4200',
    viewport: { width: 1600, height: 900 }, // 固定尺寸——測試裡用地圖投影公式算點擊座標，尺寸要可預期
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
