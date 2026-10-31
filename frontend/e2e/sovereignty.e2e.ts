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

async function jump(page: Page, center: [number, number], zoom: number): Promise<void> {
  await page.evaluate(([c, z]) => {
    const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
    map.jumpTo({ center: c, zoom: z });
  }, [center, zoom] as const);
  await page.waitForTimeout(300);
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
  // 主權檢視圖例只留國界說明，不列「目前畫面中的政權」（Tai 2026-10-31）
  await expect(page.getByTestId('legend-sov-fill')).toBeVisible();
  await expect(page.getByTestId('legend-sov-regime-item')).toHaveCount(0);
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

test('1939-10-23：德佔波蘭資訊卡不被時間軸／視窗邊緣擋住；出處預設簡短、點開完整；徽章在事件名稱下方', async ({ page }) => {
  await page.goto('/?date=1939-10-23&axis=sovereignty');
  await waitForBorders(page);
  await jump(page, [16, 52], 3.55);
  await clickLngLat(page, [19.94, 50.06]); // 克拉科夫
  const card = page.getByTestId('sovereignty-card');
  await expect(card).toBeVisible();
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('德佔波蘭軍事管理');
  const area = (await page.getByTestId('map-area').boundingBox())!;
  const box = (await card.boundingBox())!;
  expect(box.y).toBeGreaterThanOrEqual(area.y);
  expect(box.y + box.height).toBeLessThanOrEqual(area.y + area.height + 0.5);
  expect(box.x).toBeGreaterThanOrEqual(area.x);
  expect(box.x + box.width).toBeLessThanOrEqual(area.x + area.width + 0.5);

  const start = page.getByTestId('sovereignty-card-start');
  await expect(start.getByTestId('sovereignty-card-event-name')).toContainText('德蘇邊界暨友好條約');
  await expect(start.getByTestId('sovereignty-card-event-date')).toHaveText('1939-09-28');
  await expect(start.getByTestId('sovereignty-card-evidence').getByTestId('sovereignty-card-verified')).toHaveText('已查證');
  const toggles = start.getByTestId('sovereignty-card-citation-toggle');
  await expect(toggles.first()).toHaveText('DGFP D/VIII, Doc. 157, pp. 164–165');
  await expect(toggles.nth(1)).toHaveText(/^FRUS 1939 I, Doc\. 514, p\. 495/);
  await expect(start.getByTestId('sovereignty-card-citation-full')).toHaveCount(0);
  await toggles.first().click();
  await expect(start.getByTestId('sovereignty-card-citation-full')).toContainText('Documents on German Foreign Policy 1918–1945, Series D');
  await toggles.first().click();
  await expect(start.getByTestId('sovereignty-card-citation-full')).toHaveCount(0);

  const end = page.getByTestId('sovereignty-card-end');
  await expect(end.getByTestId('sovereignty-card-event-name')).toContainText('法蘭克就任總督');
  await expect(end.getByTestId('sovereignty-card-event-date')).toHaveText('1939-10-25');
  await expect(end.getByTestId('sovereignty-card-evidence').getByTestId('sovereignty-card-verified')).toBeVisible();
  await expect(end.getByTestId('sovereignty-card-citation-toggle').first()).toHaveText(/^DGFP D\/VIII, Doc\. 477, p\. 560/);
});

test('1939-10-23：德意志國結束變動沒有正式出處 → 待查證＋尚無正式出處（不補造）', async ({ page }) => {
  await page.goto('/?date=1939-10-23&axis=sovereignty');
  await waitForBorders(page);
  await clickLngLat(page, [13.4, 52.5]);
  const end = page.getByTestId('sovereignty-card-end');
  await expect(end.getByTestId('sovereignty-card-evidence').getByTestId('sovereignty-card-pending')).toHaveText('待查證');
  await expect(end.getByTestId('sovereignty-card-no-citation')).toHaveText('尚無正式出處');
  await expect(end.getByTestId('sovereignty-card-citation')).toHaveCount(0);
});

test('小視窗：點下方的政權，卡片往上長、內部可捲動，不超出地圖區', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 560 });
  await page.goto('/?date=1939-10-23&axis=sovereignty');
  await waitForBorders(page);
  const area = (await page.getByTestId('map-area').boundingBox())!;
  // 把克拉科夫移到地圖區下緣附近（距下緣 40px）再點
  await jump(page, [19.94, 50.06], 4);
  await page.evaluate((dy) => {
    const map = (window as unknown as { __wlMap: { panBy: (o: [number, number], opt: object) => void } }).__wlMap;
    map.panBy([0, dy], { animate: false });
  }, -(area.height / 2 - 40));
  await page.waitForTimeout(300);
  await clickLngLat(page, [19.94, 50.06]);
  const card = page.getByTestId('sovereignty-card');
  await expect(card).toBeVisible();
  const box = (await card.boundingBox())!;
  expect(box.y).toBeGreaterThanOrEqual(area.y);
  expect(box.y + box.height).toBeLessThanOrEqual(area.y + area.height + 0.5);
  const scrollable = await page.getByTestId('sovereignty-card-body').evaluate((el) => el.scrollHeight > el.clientHeight);
  expect(scrollable).toBe(true);
});
