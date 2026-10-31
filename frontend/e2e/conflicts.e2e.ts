import { expect, test, type Page } from '@playwright/test';

/**
 * 衝突圖示（交叉雙劍，歐陸 1938–1940 試驗）。需要開發 API（127.0.0.1:5052）上的 borders-1938-1940 與 conflicts-1938-1940 批次，
 * 以 `WL_E2E_BORDERS=1 WL_E2E_PORT=4201 pnpm e2e` 執行；不使用 mock，不寫入資料。
 * Tai 2026-10-31：圖示平時不顯示；點選政權後只顯示與該政權相關的衝突；關掉資訊卡就隱藏。
 */
test.skip(!process.env['WL_E2E_BORDERS'], '需要開發 API（5052）上的 borders／conflicts 資料');
const prefix = process.env['WL_SHOT_PREFIX'] ?? 'borders-app-v3';

async function open(page: Page, date: string): Promise<void> {
  await page.goto(`/?date=${date}&axis=sovereignty`);
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await page.evaluate(() => {
    const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
    map.jumpTo({ center: [16, 52], zoom: 3.55 });
  });
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
  await page.waitForTimeout(300);
}

async function clickLngLat(page: Page, lngLat: [number, number]): Promise<void> {
  // 聚焦會讓地圖飛到被選政權；等鏡頭停下再換算座標
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  const box = await page.getByTestId('map-canvas').boundingBox();
  const p = await page.evaluate((ll) => {
    const map = (window as unknown as { __wlMap: { project: (l: [number, number]) => { x: number; y: number } } }).__wlMap;
    return map.project(ll);
  }, lngLat);
  await page.mouse.click((box?.x ?? 0) + p.x, (box?.y ?? 0) + p.y);
}

const WARSAW: [number, number] = [21.01, 52.23];
const BERLIN: [number, number] = [13.4, 52.5];

test('1939-09-15：平時沒有衝突圖示；點波蘭 → 只出現德—波雙劍；點圖示開衝突卡；關卡片 → 圖示隱藏', async ({ page }) => {
  await open(page, '1939-09-15');
  const icons = page.getByTestId('map-conflict-icon');
  await expect(icons).toHaveCount(0);

  await clickLngLat(page, WARSAW);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('波蘭');
  await expect(icons).toHaveCount(1); // 蘇波衝突 9/17 才開始；德法衝突與波蘭無關
  await expect(icons.first().locator('svg')).toBeVisible();

  await icons.first().click();
  await expect(page.getByTestId('sovereignty-card')).toHaveCount(0);
  const card = page.getByTestId('conflict-card');
  await expect(card).toBeVisible();
  await expect(page.getByTestId('conflict-card-title')).toContainText('—');
  const start = page.getByTestId('conflict-card-start');
  await expect(start.getByTestId('conflict-card-event-date')).toHaveText('1939-09-01');
  await expect(start.getByTestId('conflict-card-evidence').getByTestId('conflict-card-verified')).toHaveText('已查證');
  const toggles = start.getByTestId('conflict-card-citation-toggle');
  await expect(toggles).toHaveCount(2);
  await expect(toggles.first()).toHaveText(/^FRUS 1939 I, Doc\. 40[23]/);
  await toggles.first().click();
  await expect(start.getByTestId('conflict-card-citation-full')).toContainText('Foreign Relations of the United States');
  const end = page.getByTestId('conflict-card-end');
  await expect(end.getByTestId('conflict-card-event-date')).toHaveText('1939-10-06');
  await expect(end.getByTestId('conflict-card-pending')).toHaveText('待查證');
  await expect(end.getByTestId('conflict-card-no-citation')).toHaveText('尚無正式出處');
  await expect(icons).toHaveCount(1); // 衝突卡開著，焦點政權不變

  await page.getByTestId('conflict-card-close').click();
  await expect(card).toHaveCount(0);
  await expect(icons).toHaveCount(0);
});

test('1939-09-15：點德國 → 德—波、法—德兩個圖示；關掉政權卡就隱藏', async ({ page }) => {
  await open(page, '1939-09-15');
  await clickLngLat(page, BERLIN);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('德意志國');
  await expect(page.getByTestId('map-conflict-icon')).toHaveCount(2);
  await page.getByTestId('sovereignty-card-close').click();
  await expect(page.getByTestId('map-conflict-icon')).toHaveCount(0);
});

test('1939-09-20：點波蘭 → 德—波、蘇—波兩個圖示；1940-06-15 點法國有法—德、義—法；1940-06-23 法德停戰後點義大利只剩義—法', async ({ page }) => {
  await open(page, '1939-09-20');
  await clickLngLat(page, WARSAW);
  await expect(page.getByTestId('map-conflict-icon')).toHaveCount(2);

  const center = async () => {
    await page.evaluate(() => {
      const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
      map.jumpTo({ center: [6, 47], zoom: 4.5 }); // 法、義移到畫面中央，避開左下圖例
    });
    await page.waitForTimeout(300);
  };
  await open(page, '1940-06-15');
  await center();
  await clickLngLat(page, [2.35, 47.5]);
  await expect(page.getByTestId('sovereignty-card')).toBeVisible();
  await expect(page.getByTestId('map-conflict-icon')).toHaveCount(2);

  // 開發庫的主權圖層 1940-06-23 起沒有法國（法蘭西第三共和止於 1940-06-22），改點義大利
  await open(page, '1940-06-23');
  await center();
  await clickLngLat(page, [12.5, 42.5]);
  await expect(page.getByTestId('sovereignty-card')).toBeVisible();
  const icons = page.getByTestId('map-conflict-icon');
  await expect(icons).toHaveCount(1);
  await icons.first().click();
  await expect(page.getByTestId('conflict-card-end').getByTestId('conflict-card-event-date')).toHaveText('1940-06-24');
  await expect(page.getByTestId('conflict-card-end').getByTestId('conflict-card-verified')).toBeVisible();
});

test('截圖：1939-09-15 點波蘭後的衝突圖示與衝突卡', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await open(page, '1939-09-15');
  await page.waitForTimeout(800);
  await clickLngLat(page, WARSAW);
  await expect(page.getByTestId('map-conflict-icon')).toHaveCount(1);
  await page.mouse.move(5, 5);
  await page.waitForTimeout(500);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-conflicts-1939-09-15.png` });
  await page.getByTestId('map-conflict-icon').first().click();
  await expect(page.getByTestId('conflict-card')).toBeVisible();
  await page.mouse.move(5, 5);
  await page.waitForTimeout(500);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-conflict-card-1939-09-15.png` });
});
