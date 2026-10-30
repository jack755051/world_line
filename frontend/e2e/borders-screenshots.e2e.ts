import { expect, test } from '@playwright/test';

/** 主權圖層試驗截圖（WL_E2E_BORDERS=1 時才跑）：五個日期，全歐視角，輸出到 tmp/borders-shots/。 */
test.skip(!process.env['WL_E2E_BORDERS'], '需要開發 API（5052）上的 borders-1938-1940 資料');

for (const date of ['1938-01-01', '1938-10-15', '1939-04-15', '1939-10-15', '1940-09-15']) {
  test(`截圖 ${date}`, async ({ page }) => {
    await page.goto(`/?date=${date}`);
    const canvas = page.getByTestId('map-canvas');
    await expect(canvas).toHaveAttribute('data-map-ready', 'true');
    await page.evaluate(() => {
      const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
      map.jumpTo({ center: [16, 52], zoom: 3.55 });
    });
    await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `tmp/borders-shots/borders-app-${date}.png` });
  });
}
