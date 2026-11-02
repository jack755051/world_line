import { expect, test, type Page } from '@playwright/test';

/**
 * 國名標籤底塊驗證截圖：水平文字＋米白半透明底塊。
 * 執行：WL_SCREENSHOTS=1 WL_E2E_BORDERS=1 pnpm e2e e2e/label-screenshots.e2e.ts --workers=1
 */
test.skip(!process.env['WL_SCREENSHOTS'], 'set WL_SCREENSHOTS=1 to capture label screenshots');
test.use({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });

const OUT_DIR = '/tmp/wl-labels';

async function ready(page: Page): Promise<void> {
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true', { timeout: 30_000 });
  await page.waitForTimeout(2000);
}

test('ussr 1942-11-01 蘇聯標籤底塊', async ({ page }) => {
  await page.goto('/?date=1942-11-01');
  await ready(page);
  await page.evaluate(() => {
    const m = (window as unknown as { __wlMap: { jumpTo: (opts: object) => void } }).__wlMap;
    if (m) m.jumpTo({ center: [55, 58], zoom: 2.5 });
  });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${OUT_DIR}/ussr.png` });
});

test('czechia 1938-01-01 捷克斯洛伐克標籤底塊', async ({ page }) => {
  await page.goto('/?date=1938-01-01');
  await ready(page);
  await page.evaluate(() => {
    const m = (window as unknown as { __wlMap: { jumpTo: (opts: object) => void } }).__wlMap;
    if (m) m.jumpTo({ center: [16, 49.8], zoom: 5.5 });
  });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${OUT_DIR}/czechia.png` });
});

test('tibet 1942-01-01 西藏標籤底塊', async ({ page }) => {
  await page.goto('/?date=1942-01-01');
  await ready(page);
  await page.evaluate(() => {
    const m = (window as unknown as { __wlMap: { jumpTo: (opts: object) => void } }).__wlMap;
    if (m) m.jumpTo({ center: [88, 32], zoom: 4 });
  });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${OUT_DIR}/tibet.png` });
});
