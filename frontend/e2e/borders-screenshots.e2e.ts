import { expect, test } from '@playwright/test';

/**
 * 主權圖層試驗截圖（WL_E2E_BORDERS=1 時才跑）：五個日期，全歐視角，主權檢視，輸出到 tmp/borders-shots/。
 * 檔名前綴 WL_SHOT_PREFIX（預設 borders-app-v2）。
 */
const prefix = process.env['WL_SHOT_PREFIX'] ?? 'borders-app-v2';
test.skip(!process.env['WL_E2E_BORDERS'], '需要開發 API（5052）上的 borders-1938-1940 資料');

for (const date of ['1938-01-01', '1938-10-15', '1939-04-15', '1939-10-15', '1940-09-15']) {
  test(`截圖 ${date}`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(`/?date=${date}&axis=sovereignty`);
    const canvas = page.getByTestId('map-canvas');
    await expect(canvas).toHaveAttribute('data-map-ready', 'true');
    await expect(canvas).toHaveAttribute('data-axis', 'sovereignty');
    await page.evaluate(() => {
      const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
      map.jumpTo({ center: [16, 52], zoom: 3.55 });
    });
    await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `tmp/borders-shots/${prefix}-${date}.png` });
  });
}

test('截圖：1939-10-23 德佔波蘭資訊卡（出處收合、徽章在事件名稱下方）', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/?date=1939-10-23&axis=sovereignty');
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await page.evaluate(() => {
    const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
    map.jumpTo({ center: [16, 52], zoom: 3.55 });
  });
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
  await page.waitForTimeout(1000);
  const box = await canvas.boundingBox();
  const p = await page.evaluate(() => {
    const map = (window as unknown as { __wlMap: { project: (l: [number, number]) => { x: number; y: number } } }).__wlMap;
    return map.project([19.94, 50.06]);
  });
  await page.mouse.click((box?.x ?? 0) + p.x, (box?.y ?? 0) + p.y);
  await expect(page.getByTestId('sovereignty-card')).toBeVisible();
  await page.mouse.move(5, 5);
  await page.waitForTimeout(500);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-card-1939-10-23.png` });
});

test('截圖：展開的圖例（主權檢視只留國界說明）', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/?date=1939-10-23&axis=sovereignty');
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
  await expect(page.getByTestId('legend')).toHaveAttribute('data-state', 'open');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-legend-1939-10-23.png` });
});

test('截圖：1942-11-01 德國、蘇聯國界與東方佔領行政區', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/?date=1942-11-01&axis=sovereignty');
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await page.evaluate(() => {
    const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
    map.jumpTo({ center: [24, 52], zoom: 3.4 });
  });
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-1942-11-01.png` });
});
