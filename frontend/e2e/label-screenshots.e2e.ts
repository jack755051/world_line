import { expect, test, type Page } from '@playwright/test';

/**
 * Task A 標籤修正驗證截圖：Mercator 投影 labelPoint + 狹長國旋轉。
 * 執行：WL_SCREENSHOTS=1 WL_E2E_BORDERS=1 pnpm e2e e2e/label-screenshots.e2e.ts --workers=1
 */
test.skip(!process.env['WL_SCREENSHOTS'], 'set WL_SCREENSHOTS=1 to capture label screenshots');
test.use({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });

const out = (name: string) => `${process.env['WL_SCREENS_DIR'] ?? 'tmp/screens'}/${name}.png`;

async function ready(page: Page): Promise<void> {
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true', { timeout: 30_000 });
  // 等主權圖層或控制圖層任一有資料即可（部分早期日期只有主權資料）
  await page.waitForTimeout(2000);
}

async function readyWithFeatures(page: Page): Promise<void> {
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true', { timeout: 30_000 });
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-features')) ?? 0), { timeout: 20_000 }).toBeGreaterThan(0);
  await page.waitForTimeout(1200);
}

test('L01 1942-11-01 全圖（蘇聯標籤不偏南）', async ({ page }) => {
  await page.goto('/?date=1942-11-01');
  await ready(page);
  await page.screenshot({ path: out('L01-1942-11-01-ussr-label') });
});

test('L02 1942-11-01 東歐特寫（蘇聯 + 德國標籤）', async ({ page }) => {
  await page.goto('/?date=1942-11-01');
  await ready(page);
  // 縮放到東歐中心（lng=40, lat=55）
  await page.evaluate(() => {
    const m = (window as unknown as { __wlMap: { jumpTo: (opts: object) => void } }).__wlMap;
    if (m) m.jumpTo({ center: [40, 55], zoom: 3.5 });
  });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: out('L02-1942-11-01-eastern-europe-zoom') });
});

test('L03 1938-01-01 捷克斯洛伐克（狹長標籤）', async ({ page }) => {
  await page.goto('/?date=1938-01-01');
  await ready(page);
  // 縮放到中歐（捷克）
  await page.evaluate(() => {
    const m = (window as unknown as { __wlMap: { jumpTo: (opts: object) => void } }).__wlMap;
    if (m) m.jumpTo({ center: [16, 50], zoom: 5 });
  });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: out('L03-1938-01-01-czechoslovakia-label') });
});

test('L04 1942-01-01 西藏標籤', async ({ page }) => {
  await page.goto('/?date=1942-01-01');
  await ready(page);
  // 縮放到西藏（lng=88, lat=32）
  await page.evaluate(() => {
    const m = (window as unknown as { __wlMap: { jumpTo: (opts: object) => void } }).__wlMap;
    if (m) m.jumpTo({ center: [88, 32], zoom: 4 });
  });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: out('L04-1942-01-01-tibet-label') });
});
