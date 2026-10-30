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

test('1938-10-15：點柏林 → 德意志國卡片（蘇台德修正紀錄）；起始變動（分區佔領）已查證、結束變動待查證', async ({ page }) => {
  await page.goto('/?date=1938-10-15');
  await waitForBorders(page);
  await clickLngLat(page, [13.4, 52.5]);
  const card = page.getByTestId('sovereignty-card');
  await expect(card).toBeVisible();
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('德意志國');
  await expect(page.getByTestId('sovereignty-card-start')).toContainText('已查證');
  await expect(page.getByTestId('sovereignty-card-start').getByTestId('sovereignty-card-citation').first()).toContainText('Doc. 682, p. 702');
  await expect(page.getByTestId('sovereignty-card-end').getByTestId('sovereignty-card-pending')).toHaveText('待查證');
  await expect(page.getByTestId('sovereignty-card-geometry')).toContainText('relation/2704712 v208 ∪ (relation/2704711 v199');
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

test('實際控制 ↔ 主權切換：地圖過場、URL、圖例跟著換', async ({ page }) => {
  await page.goto('/?date=1939-04-15');
  await waitForBorders(page);
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-axis', 'control');
  await page.getByTestId('axis-toggle-sovereignty').click();
  await expect(page.getByTestId('axis-toggle-sovereignty')).toHaveAttribute('aria-pressed', 'true');
  await expect(canvas).toHaveAttribute('data-axis', 'sovereignty');
  await expect(page).toHaveURL(/axis=sovereignty/);
  await expect(page.getByTestId('legend')).toHaveAttribute('data-axis', 'sovereignty');
  await expect.poll(() => page.getByTestId('legend-sov-regime-item').count()).toBeGreaterThan(10);
  // 國界標籤：捷克斯洛伐克（1939-03-14 前）在 1939-04-15 已不存在，改驗 1938-10-15 的捷克斯洛伐克見下一個測試
  await page.getByTestId('axis-toggle-control').click();
  await expect(canvas).toHaveAttribute('data-axis', 'control');
  await expect(page).not.toHaveURL(/axis=sovereignty/);
});

test('?axis=sovereignty 直接進主權檢視；1938-10-15 捷克斯洛伐克有國名標籤', async ({ page }) => {
  await page.goto('/?date=1938-10-15&axis=sovereignty');
  await waitForBorders(page);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-axis', 'sovereignty');
  await page.evaluate(() => {
    const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
    map.jumpTo({ center: [16, 52], zoom: 3.55 });
  });
  await expect(page.getByTestId('map-regime-label').filter({ hasText: '捷克斯洛伐克' })).toHaveCount(1);
});

test('圖例收合有過場（closing → collapsed）；prefers-reduced-motion 時直接收合', async ({ page }) => {
  await page.goto('/?date=1939-04-15');
  await waitForBorders(page);
  const legend = page.getByTestId('legend');
  await expect(legend).toHaveAttribute('data-state', 'open');
  const states: string[] = [];
  await page.exposeFunction('wlState', (s: string) => states.push(s));
  await page.evaluate(() => {
    const el = document.querySelector('wl-legend')!;
    new MutationObserver(() => {
      const s = el.querySelector('[data-testid="legend"]')?.getAttribute('data-state');
      if (s) (window as unknown as { wlState: (s: string) => void }).wlState(s);
    }).observe(el, { subtree: true, attributes: true, childList: true });
  });
  await page.getByTestId('legend-toggle').click();
  await expect(legend).toHaveAttribute('data-state', 'collapsed');
  expect(states).toContain('closing');
  await page.getByTestId('legend-expand').click();
  await expect(legend).toHaveAttribute('data-state', 'open');

  await page.emulateMedia({ reducedMotion: 'reduce' });
  states.length = 0;
  await page.getByTestId('legend-toggle').click();
  await expect(legend).toHaveAttribute('data-state', 'collapsed');
  expect(states).not.toContain('closing');
});
