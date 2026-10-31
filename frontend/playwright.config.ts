import { defineConfig, devices } from '@playwright/test';

/**
 * E2E（PRD §10 M0 驗收：開頁 → 看到多邊形 → 點開來源）。
 * 跑的是真實 API：先在本機啟動後端（`docker compose up`，API 127.0.0.1:5051，資料庫 appdb_ww2），
 * 前端由 Playwright 啟動 dev server（proxy 到 API）。E2E 不使用 mock，也不寫入任何資料。
 */
const port = Number(process.env['WL_E2E_PORT'] ?? 4310);

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  reporter: [['list']],
  outputDir: 'tmp/playwright-results',
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    viewport: { width: 1440, height: 900 },
    locale: 'zh-TW',
    timezoneId: 'Asia/Taipei',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } }],
  webServer: {
    // WL_E2E_BORDERS=1：一律 proxy 到開發 API（5052，proxy.borders-dev.json），避免自動啟動的 dev server 誤連 5051／appdb_ww2
    command: `pnpm exec ng serve --port ${port} --host 127.0.0.1${process.env['WL_E2E_BORDERS'] ? ' --proxy-config proxy.borders-dev.json' : ''}`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: true,
    timeout: 180_000,
  },
});
