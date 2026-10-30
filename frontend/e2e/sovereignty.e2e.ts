import { expect, test, type Page } from '@playwright/test';

/**
 * 主權圖層（國界，feature/borders-1938-1940 試驗）。需要已寫入 borders-1938-1940 批次的開發 API（127.0.0.1:5052），
 * 前端用 `ng serve --port 4201 --proxy-config proxy.borders-dev.json`，以 `WL_E2E_BORDERS=1 WL_E2E_PORT=4201 pnpm e2e` 執行。
 * 正式 appdb_ww2（5051）尚無這批資料，未設 WL_E2E_BORDERS 時略過。不使用 mock，不寫入資料。
 */
test.skip(!process.env['WL_E2E_BORDERS'], '需要開發 API（5052）上的 borders-1938-1940 資料');

async function waitForBorders(page: Page): Promise<void> {
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
}

async function clickLngLat(page: Page, lngLat: [number, number]): Promise<void> {
  const box = await page.getByTestId('map-canvas').boundingBox();
  const p = await page.evaluate((ll) => {
    const map = (window as unknown as { __wlMap: { project: (l: [number, number]) => { x: number; y: number } } }).__wlMap;
    return map.project(ll);
  }, lngLat);
  await page.mouse.click((box?.x ?? 0) + p.x, (box?.y ?? 0) + p.y);
}

test('1938-10-15：點柏林 → 德意志國卡片；起始變動（德奧合併）已查證、結束變動待查證', async ({ page }) => {
  await page.goto('/?date=1938-10-15');
  await waitForBorders(page);
  await clickLngLat(page, [13.4, 52.5]);
  const card = page.getByTestId('sovereignty-card');
  await expect(card).toBeVisible();
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('德意志國');
  await expect(page.getByTestId('sovereignty-card-start')).toContainText('已查證');
  await expect(page.getByTestId('sovereignty-card-start').getByTestId('sovereignty-card-citation').first()).toContainText('Doc. 454');
  await expect(page.getByTestId('sovereignty-card-end').getByTestId('sovereignty-card-pending')).toHaveText('待查證');
  await expect(page.getByTestId('sovereignty-card-geometry')).toContainText('relation/2704712 v208');
  await expect(page.getByTestId('sovereignty-card-osm')).toBeVisible();
  // 陣營只作補充（開發庫沒有陣營切片 → 未建置，不推定）
  await expect(page.getByTestId('sovereignty-card-camp')).toHaveAttribute('data-camp', 'unassigned');
});

test('陣營外框圖層可開關，預設關閉', async ({ page }) => {
  await page.goto('/?date=1939-04-15');
  await waitForBorders(page);
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-camp-layer', 'off');
  await page.getByTestId('camp-layer-toggle').click();
  await expect(canvas).toHaveAttribute('data-camp-layer', 'on');
  await expect(page.getByTestId('camp-layer-toggle')).toHaveAttribute('aria-pressed', 'true');
});

test('1940-09-15：布魯塞爾屬比北軍政府，卡片標示非主權', async ({ page }) => {
  await page.goto('/?date=1940-09-15');
  await waitForBorders(page);
  await clickLngLat(page, [4.35, 50.85]);
  await expect(page.getByTestId('sovereignty-card')).toHaveAttribute('data-layer-status', 'not_sovereign');
  await expect(page.getByTestId('sovereignty-card-status')).toContainText('非主權');
});
