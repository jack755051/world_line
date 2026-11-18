import { mkdir } from 'node:fs/promises';
import { expect, test, type Page } from '@playwright/test';

/**
 * 首都圖層驗證截圖：資訊面板顯示首都名稱、地圖上可見首都小圓點。
 * 執行：WL_SCREENSHOTS=1 WL_E2E_BORDERS=1 pnpm e2e e2e/capital-screenshots.e2e.ts --workers=1
 */
test.skip(!process.env['WL_SCREENSHOTS'], 'set WL_SCREENSHOTS=1 to capture capital screenshots');
test.use({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });

const OUT_DIR = '/tmp/wl-capitals';

test.beforeAll(async () => {
  await mkdir(OUT_DIR, { recursive: true });
});

async function ready(page: Page): Promise<void> {
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true', { timeout: 30_000 });
  await page.waitForTimeout(2000);
}

async function readyWithFeatures(page: Page): Promise<void> {
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true', { timeout: 30_000 });
  await expect
    .poll(async () => Number((await canvas.getAttribute('data-rendered-features')) ?? 0), { timeout: 20_000 })
    .toBeGreaterThan(0);
  await page.waitForTimeout(1200);
}

/** 用 __wlMap.project() 取得地理座標對應的畫布像素位置後點擊，觸發主權圖層 click。 */
async function clickAtLngLat(page: Page, lng: number, lat: number): Promise<void> {
  const canvas = page.getByTestId('map-canvas');
  const pos = await page.evaluate(
    ([lo, la]: [number, number]) => {
      const m = (window as unknown as { __wlMap?: { project(c: [number, number]): { x: number; y: number } } }).__wlMap;
      return m?.project([lo, la]) ?? null;
    },
    [lng, lat] as [number, number],
  );
  if (pos) await canvas.click({ position: { x: Math.round(pos.x), y: Math.round(pos.y) } });
}

test('C01 1939-09-22 德國首都柏林（資訊面板首都＋地圖圓點）', async ({ page }) => {
  await page.goto('/?date=1939-09-22');
  // 等主權圖層（不等控制區 features，因該日可能尚無控制資料）
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true', { timeout: 30_000 });
  await expect
    .poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0), { timeout: 20_000 })
    .toBeGreaterThan(0);
  await page.waitForTimeout(1200);

  // 縮放到柏林附近，讓柏林首都圓點可見
  await page.evaluate(() => {
    const m = (window as unknown as { __wlMap?: { jumpTo(o: object): void } }).__wlMap;
    m?.jumpTo({ center: [13.4, 52.5], zoom: 4.5 });
  });
  await page.waitForTimeout(1500);

  // 點選德意志國（柏林座標）
  await clickAtLngLat(page, 13.4, 52.5);
  await page.waitForTimeout(2000);

  await page.screenshot({ path: `${OUT_DIR}/capital-1939-09-22-germany.png` });
});

test('C02 1920-05-21 法國巴黎（交戰虛線從巴黎出發）', async ({ page }) => {
  await page.goto('/?date=1920-05-21');
  await ready(page);

  // 縮放到西歐，巴黎在中心
  await page.evaluate(() => {
    const m = (window as unknown as { __wlMap?: { jumpTo(o: object): void } }).__wlMap;
    m?.jumpTo({ center: [2.35, 48.85], zoom: 4 });
  });
  await page.waitForTimeout(1500);

  // 點選法國（巴黎座標）以開出政權資訊面板並顯示衝突弧線
  await clickAtLngLat(page, 2.35, 48.85);
  await page.waitForTimeout(2000);

  await page.screenshot({ path: `${OUT_DIR}/capital-1920-05-21-france.png` });
});
