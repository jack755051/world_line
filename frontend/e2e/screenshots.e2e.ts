import { expect, test, type Page } from '@playwright/test';

/**
 * 實際畫面截圖（給設計稿比對用）。預設跳過；`WL_SCREENSHOTS=1 pnpm e2e e2e/screenshots.e2e.ts` 才執行，輸出到 tmp/screens/。
 * 只讀真實 API；離線與錯誤狀態用 page.route 攔截請求模擬（只在本測試檔內，不寫入任何資料）。
 */
test.skip(!process.env['WL_SCREENSHOTS'], 'set WL_SCREENSHOTS=1 to capture screenshots');
test.use({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });

const out = (name: string) => `${process.env['WL_SCREENS_DIR'] ?? 'tmp/screens'}/${name}.png`;

async function ready(page: Page): Promise<void> {
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-features')) ?? 0)).toBeGreaterThan(0);
  await page.waitForTimeout(800);
}

async function clickLngLat(page: Page, lngLat: [number, number]): Promise<void> {
  const box = await page.getByTestId('map-canvas').boundingBox();
  const p = await page.evaluate((ll) => (window as unknown as { __wlMap: { project: (l: [number, number]) => { x: number; y: number } } }).__wlMap.project(ll), lngLat);
  await page.mouse.click((box?.x ?? 0) + p.x, (box?.y ?? 0) + p.y);
}

test('01 主地圖 1940-07-15（史料快照）', async ({ page }) => {
  await page.goto('/?date=1940-07-15');
  await ready(page);
  await page.screenshot({ path: out('01-main-1940-07-15') });
});

test('02 控制區卡片＋來源 popover', async ({ page }) => {
  await page.goto('/?date=1940-07-15');
  await ready(page);
  await clickLngLat(page, [2.35, 48.86]);
  await page.getByTestId('regime-sheet').getByTestId('citation-button').first().click();
  await expect(page.getByTestId('citation-item').first()).toBeVisible();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: out('02-feature-card-citation') });
});

test('03 推估過渡 1940-07-30＋chip popover', async ({ page }) => {
  await page.goto('/?date=1940-07-30');
  await ready(page);
  await page.getByTestId('interp-chip').click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: out('03-interpolated-1940-07-30') });
});

test('04 1940-08-15 亞爾薩斯－摩澤爾改為直接統治（EN）', async ({ page }) => {
  await page.goto('/?date=1940-08-15&lang=en');
  await ready(page);
  await page.getByTestId('legend-toggle').click();
  await page.screenshot({ path: out('04-1940-08-15-en-legend-closed') });
});

test('05 此日期尚無資料 1900-01-01', async ({ page }) => {
  await page.goto('/?date=1900-01-01');
  await expect(page.getByTestId('map-empty')).toBeVisible();
  await page.waitForTimeout(800);
  await page.screenshot({ path: out('05-empty-1938-03-01') });
});

test('06 時間軸 ⋯ 選單打開', async ({ page }) => {
  await page.goto('/?date=1940-07-15');
  await ready(page);
  await page.getByTestId('timeline-menu-button').click();
  await expect(page.getByTestId('timeline-menu')).toBeVisible();
  await page.waitForTimeout(300);
  await page.screenshot({ path: out('06-timeline-menu'), clip: { x: 0, y: 600, width: 1440, height: 300 } });
});

test('07 API 無法連線（攔截 /healthz）', async ({ page }) => {
  await page.route('**/healthz', (r) => r.abort());
  await page.goto('/?date=1940-07-15');
  await expect(page.getByTestId('app-offline')).toBeVisible();
  await page.screenshot({ path: out('07-api-offline') });
});

test('08 地圖資料載入失敗（攔截第二次 /control）', async ({ page }) => {
  await page.goto('/?date=1940-07-15');
  await ready(page);
  await page.route('**/api/v1/control?*', (r) => r.abort());
  await page.getByTestId('timeline-date-input').fill('1941-01-01');
  await page.getByTestId('timeline-date-input').press('Enter');
  await expect(page.getByTestId('map-error')).toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({ path: out('08-map-error-keeps-last') });
});

test('09 首次載入 skeleton', async ({ page }) => {
  await page.route('**/healthz', async (r) => {
    await new Promise((res) => setTimeout(res, 3000));
    await r.continue();
  });
  await page.goto('/?date=1940-07-15');
  await expect(page.getByTestId('app-skeleton')).toBeVisible();
  await page.screenshot({ path: out('09-first-load-skeleton') });
});

test('10 找不到頁面', async ({ page }) => {
  await page.goto('/no-such-page');
  await expect(page.getByTestId('not-found-page')).toBeVisible();
  await page.waitForTimeout(400);
  await page.screenshot({ path: out('10-not-found') });
});

test('11 網址日期無效 → toast', async ({ page }) => {
  await page.goto('/?date=1940-13-99');
  await ready(page);
  await expect(page.getByTestId('toast')).toContainText('日期格式無效');
  await page.screenshot({ path: out('11-invalid-date-toast') });
});

test('12 早期時段提示 1935-05-01', async ({ page }) => {
  await page.goto('/?date=1935-05-01');
  await expect(page.getByTestId('timeline-incomplete-info')).toBeVisible();
  await page.waitForTimeout(800);
  await page.screenshot({ path: out('12-early-period-1935-05-01') });
});

test('13 圖例收合（1940-07-15）', async ({ page }) => {
  await page.goto('/?date=1940-07-15');
  await ready(page);
  await page.getByTestId('legend-toggle').click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: out('13-legend-collapsed') });
});
