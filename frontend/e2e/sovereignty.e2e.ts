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
  // 聚焦會讓地圖飛到被選政權；等鏡頭停下再換算座標
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
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

test('1938-10-05：蘇台德為德軍分區進駐中（非主權斜線，慕尼黑協定 DGFP D/II No. 675）；1938-10-15 已劃入德國', async ({ page }) => {
  await page.goto('/?date=1938-10-05');
  await waitForBorders(page);
  await jump(page, [14.5, 50.2], 5.5);
  await clickLngLat(page, [12.87, 50.23]); // 卡爾斯巴德（Karlsbad）
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('蘇台德');
  await expect(page.getByTestId('sovereignty-card-status')).toContainText('非主權');
  await expect(page.getByTestId('sovereignty-card-start')).toContainText('已查證');
  await expect(page.getByTestId('sovereignty-card-start').getByTestId('sovereignty-card-citation').first()).toContainText('No. 675, pp. 1014–1015');
  await expect(page.getByTestId('sovereignty-card-body')).toContainText('簡化');
  // 布拉格仍屬捷克斯洛伐克
  await page.keyboard.press('Escape');
  await clickLngLat(page, [14.42, 50.08]);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('捷克');
  await page.goto('/?date=1938-10-15');
  await waitForBorders(page);
  await jump(page, [14.5, 50.2], 5.5);
  await clickLngLat(page, [12.87, 50.23]);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('德意志國');
});

test('1943-10-01：羅馬屬義大利社會共和國（非主權）、南義屬義大利王國（AMGOT 分段待查證）；1944-10-01 雅典屬希臘王國、巴黎屬法國臨時政府', async ({ page }) => {
  await page.goto('/?date=1943-10-01');
  await waitForBorders(page);
  await jump(page, [13, 42], 5.5);
  await clickLngLat(page, [12.5, 41.9]); // 羅馬
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('義大利社會共和國');
  await expect(page.getByTestId('sovereignty-card-status')).toContainText('非主權');
  await page.keyboard.press('Escape');
  await clickLngLat(page, [15.0, 40.6]); // 薩萊諾以東
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('義大利');
  await expect(page.getByTestId('sovereignty-card')).toHaveAttribute('data-layer-status', 'de_jure');
  // 起始變動（AMGOT 分段日）只有 OHM 日期：待查證，不補造出處
  await expect(page.getByTestId('sovereignty-card-start')).toContainText('待查證');
  await page.goto('/?date=1944-10-01');
  await waitForBorders(page);
  await jump(page, [2.35, 48.86], 5.5);
  await clickLngLat(page, [2.35, 48.86]);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('法蘭西共和國臨時政府');
  await page.goto('/?date=1944-11-01');
  await waitForBorders(page);
  await jump(page, [23.7, 38.2], 5.5);
  await clickLngLat(page, [23.4, 38.3]); // 雅典西北
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('希臘');
  await expect(page.getByTestId('sovereignty-card')).toHaveAttribute('data-layer-status', 'de_jure');
});

test('1940 波羅的海：06-20 里加屬拉脫維亞共和國（補空白）、07-25 考納斯屬立陶宛蘇維埃共和國（不再重疊）、08-04 里加仍屬拉脫維亞蘇維埃共和國', async ({ page }) => {
  for (const [date, at, title] of [
    ['1940-06-20', [24.1, 56.95], '拉脫維亞'],
    ['1940-07-25', [23.9, 54.9], '立陶宛'],
    ['1940-08-04', [24.1, 56.95], '拉脫維亞'],
  ] as const) {
    await page.goto(`/?date=${date}`);
    await waitForBorders(page);
    await jump(page, [24, 56], 5.5);
    await clickLngLat(page, [...at]);
    await expect(page.getByTestId('sovereignty-card-title')).toContainText(title);
  }
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('蘇維埃');
});

test('美國：1941-12-01 堪薩斯屬美利堅合眾國、馬尼拉屬菲律賓自治邦；1942-12-01 對德宣戰的衝突已開始', async ({ page }) => {
  await page.goto('/?date=1941-12-01');
  await waitForBorders(page);
  await jump(page, [-98, 39], 3.2);
  await clickLngLat(page, [-98.5, 38.5]);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('美利堅合眾國');
  await expect(page.getByTestId('sovereignty-card')).toHaveAttribute('data-layer-status', 'de_jure');
  // 關閉面板後鏡頭會回到原位，所以重新開頁再看菲律賓
  await page.goto('/?date=1941-12-01');
  await waitForBorders(page);
  await jump(page, [121, 14.6], 5);
  await clickLngLat(page, [121.1, 14.7]);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('菲律賓自治邦');
  const res = await page.request.get('/api/v1/conflicts?date=1942-12-01') // 經 4201 的 proxy 到開發 API;
  const slugs = ((await res.json()).data.featureCollection.features as { properties: { regimeASlug: string; regimeBSlug: string } }[])
    .map((f) => `${f.properties.regimeASlug}/${f.properties.regimeBSlug}`);
  expect(slugs).toContain('deutsches-reich/united-states-of-america');
});

test('亞洲第一批：1941-12-15 東京與首爾屬大日本帝國、重慶屬中華民國、長春屬滿洲國（非主權）、曼谷屬泰國；1945-08-30 平壤屬蘇聯民政署（非主權）', async ({ page }) => {
  for (const [date, at, title, layer] of [
    ['1941-12-15', [139.7, 35.7], '大日本帝國', 'de_jure'],
    ['1941-12-15', [126.98, 37.57], '大日本帝國', 'de_jure'],
    ['1941-12-15', [106.55, 29.56], '中華民國', 'de_jure'],
    ['1941-12-15', [125.32, 43.88], '滿洲國', 'not_sovereign'],
    ['1941-12-15', [100.5, 13.75], '泰國', 'de_jure'],
    ['1945-08-30', [125.75, 39.03], '蘇聯民政署', 'not_sovereign'],
  ] as const) {
    await page.goto(`/?date=${date}`);
    await waitForBorders(page);
    await jump(page, [...at], 5);
    await clickLngLat(page, [...at]);
    await expect(page.getByTestId('sovereignty-card-title')).toContainText(title);
    await expect(page.getByTestId('sovereignty-card')).toHaveAttribute('data-layer-status', layer);
  }
  // 日本佔領區 OHM 沒有邊界、未分出：華中（安徽）仍畫為中華民國
  await page.goto('/?date=1940-01-01');
  await waitForBorders(page);
  await jump(page, [116.4, 32], 5);
  await clickLngLat(page, [116.4, 32]);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('中華民國');
  const res = await page.request.get('/api/v1/conflicts?date=1943-06-01');
  const slugs = ((await res.json()).data.featureCollection.features as { properties: { regimeASlug: string; regimeBSlug: string } }[])
    .map((f) => `${f.properties.regimeASlug}/${f.properties.regimeBSlug}`);
  expect(slugs).toEqual(expect.arrayContaining(['empire-of-japan/republic-of-china-nationalist', 'empire-of-japan/united-states-of-america', 'empire-of-japan/united-kingdom']));
  expect(slugs).not.toContain('soviet-union/empire-of-japan');
});

test('國界補完整：1941-12-15 新西伯利亞、塔什干、烏蘇里斯克屬蘇聯，凡城屬土耳其（不再被東經 42 度裁切）', async ({ page }) => {
  for (const [at, title] of [
    [[82.9, 55.0], '蘇'],
    [[69.25, 41.3], '蘇'],
    [[131.95, 43.8], '蘇'],
    [[43.38, 38.5], '土耳其'],
  ] as const) {
    await page.goto('/?date=1941-12-15&axis=sovereignty');
    await waitForBorders(page);
    await jump(page, [...at], 4.5);
    await clickLngLat(page, [...at]);
    await expect(page.getByTestId('sovereignty-card-title')).toContainText(title);
    await expect(page.getByTestId('sovereignty-card-geometry')).toContainText('完整，不受歐陸框裁切');
  }
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
  // 面板滑入動畫中量測會差幾 px：等位置穩定在地圖區內
  await expect.poll(async () => { const b = (await card.boundingBox())!; return Math.max(b.y + b.height - (area.y + area.height), b.x + b.width - (area.x + area.width)); }, { timeout: 3000 }).toBeLessThanOrEqual(0.5);
  const box = (await card.boundingBox())!;
  expect(box.y).toBeGreaterThanOrEqual(area.y);
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

test('小視窗：點下方的政權，側邊面板不超出地圖區、內部可捲動', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 560 });
  await page.goto('/?date=1939-10-23&axis=sovereignty');
  await waitForBorders(page);
  const area = (await page.getByTestId('map-area').boundingBox())!;
  await jump(page, [19.94, 50.06], 4);
  await page.evaluate((dy) => {
    const map = (window as unknown as { __wlMap: { panBy: (o: [number, number], opt: object) => void } }).__wlMap;
    map.panBy([0, dy], { animate: false });
  }, -(area.height / 2 - 40));
  await page.waitForTimeout(300);
  await clickLngLat(page, [19.94, 50.06]);
  const sheet = page.getByTestId('regime-sheet');
  await expect(sheet).toHaveAttribute('data-state', 'open');
  await expect(sheet).toHaveAttribute('data-side', 'right');
  const box = (await sheet.boundingBox())!;
  expect(box.y).toBeGreaterThanOrEqual(area.y - 0.5);
  expect(box.y + box.height).toBeLessThanOrEqual(area.y + area.height + 0.5);
  expect(box.x + box.width).toBeLessThanOrEqual(area.x + area.width + 0.5);
  const scrollable = await page.getByTestId('sovereignty-card-body').evaluate((el) => el.scrollHeight > el.clientHeight);
  expect(scrollable).toBe(true);
});

test('1942-11-01：德國、蘇聯國界與東方佔領行政區（非主權斜線）；出處或待查證', async ({ page }) => {
  await page.goto('/?date=1942-11-01&axis=sovereignty');
  await waitForBorders(page);
  await jump(page, [22, 52], 3.55);
  await clickLngLat(page, [30.52, 50.45]); // 基輔
  const card = page.getByTestId('sovereignty-card');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('烏克蘭總督轄區');
  const start = page.getByTestId('sovereignty-card-start');
  await expect(start.getByTestId('sovereignty-card-verified')).toBeVisible();
  await expect(start.getByTestId('sovereignty-card-citation-toggle').first()).toHaveText('NCA III, Doc. 197-PS, p. 210');

  await clickAt(page, [24.1, 56.95]); // 里加
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('東方總督轄區');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');

  await clickAt(page, [13.4, 52.5]); // 柏林：起始變動（東加利西亞併入總督府）沒有正式出處 → 待查證
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('德意志國');
  await expect(page.getByTestId('sovereignty-card-start').getByTestId('sovereignty-card-pending')).toHaveText('待查證');
  await expect(page.getByTestId('sovereignty-card-start').getByTestId('sovereignty-card-no-citation')).toBeVisible();
});

/** 先把地圖中心移到該點再點擊，避免資訊卡蓋住點擊位置。 */
async function clickAt(page: Page, lngLat: [number, number]): Promise<void> {
  // 先等上一次聚焦的飛行結束，再把點移到可見區中央（面板左側）
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await jump(page, lngLat, 5);
  await clickLngLat(page, lngLat);
}

test('1942-12-01：南歐、東南歐與法國（佔領行政區為非主權斜線）；出處或待查證', async ({ page }) => {
  await page.goto('/?date=1942-12-01&axis=sovereignty');
  await waitForBorders(page);
  const card = page.getByTestId('sovereignty-card');
  const title = page.getByTestId('sovereignty-card-title');
  const start = page.getByTestId('sovereignty-card-start');

  await clickAt(page, [15.98, 45.81]); // 札格雷布
  await expect(title).toContainText('克羅埃西亞獨立國');
  await expect(card).toHaveAttribute('data-layer-status', 'de_jure');
  await expect(start.getByTestId('sovereignty-card-verified')).toBeVisible();

  await clickAt(page, [20.46, 44.82]); // 貝爾格勒
  await expect(title).toContainText('塞爾維亞軍事指揮官轄區');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');
  await expect(start.getByTestId('sovereignty-card-verified')).toBeVisible();

  await clickAt(page, [19.26, 42.44]); // 波德戈里察：總督轄區設立沒有正式出處 → 待查證
  await expect(title).toContainText('蒙特內哥羅總督轄區');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');
  await expect(start.getByTestId('sovereignty-card-pending')).toHaveText('待查證');

  await clickAt(page, [3.43, 46.13]); // 維琪：1942-11-11 起全境佔領
  await expect(title).toContainText('法蘭西國（維琪）');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');
  await expect(start.getByTestId('sovereignty-card-verified')).toBeVisible();

  await clickAt(page, [30.73, 46.48]); // 敖德薩
  await expect(title).toContainText('外涅斯特里亞');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');
  await clickAt(page, [28.86, 47.01]); // 基希涅夫（比薩拉比亞）
  await expect(title).toContainText('羅馬尼亞王國');
  await expect(card).toHaveAttribute('data-layer-status', 'de_jure');
});

test('1942-11-01：維琪法國在 11-11 前仍為原紀錄（主權），尚無義大利佔領的法國地區', async ({ page }) => {
  await page.goto('/?date=1942-11-01&axis=sovereignty');
  await waitForBorders(page);
  await clickAt(page, [3.43, 46.13]);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('法蘭西國（維琪）');
  await expect(page.getByTestId('sovereignty-card')).toHaveAttribute('data-layer-status', 'de_jure');
});

test('舊資料修正：1942-11-01 阿爾及利亞仍屬維琪；1942-12-01 阿爾及利亞為盟軍佔領、荷挪丹為非主權', async ({ page }) => {
  await page.goto('/?date=1942-11-01&axis=sovereignty');
  await waitForBorders(page);
  const card = page.getByTestId('sovereignty-card');
  const title = page.getByTestId('sovereignty-card-title');
  const start = page.getByTestId('sovereignty-card-start');
  await clickAt(page, [3.06, 36.75]); // 阿爾及爾：法國本土的省份，依事實國界屬維琪
  await expect(title).toContainText('法蘭西國（維琪）');
  await expect(card).toHaveAttribute('data-layer-status', 'de_jure');

  await page.goto('/?date=1942-12-01&axis=sovereignty');
  await waitForBorders(page);
  await clickAt(page, [3.06, 36.75]); // 阿爾及爾：11-08 盟軍登陸後
  await expect(title).toContainText('盟軍佔領下的法屬北非');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');
  await expect(start.getByTestId('sovereignty-card-verified')).toBeVisible();

  await clickAt(page, [4.9, 52.37]); // 阿姆斯特丹
  await expect(title).toContainText('德國佔領下的荷蘭');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');

  await clickAt(page, [10.75, 59.91]); // 奧斯陸
  await expect(title).toContainText('德國佔領下的挪威');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');
  await expect(start.getByTestId('sovereignty-card-verified')).toBeVisible();

  await clickAt(page, [9.5, 56.2]); // 日德蘭：政府仍在，政權仍記為丹麥王國，但標非主權
  await expect(title).toContainText('丹麥');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');
});

test('1941-12-01：補空白第一段（德國、蘇聯、東方與烏克蘭總督轄區、羅馬尼亞）', async ({ page }) => {
  await page.goto('/?date=1941-12-01&axis=sovereignty');
  await waitForBorders(page);
  const card = page.getByTestId('sovereignty-card');
  const title = page.getByTestId('sovereignty-card-title');
  const start = page.getByTestId('sovereignty-card-start');
  await clickAt(page, [30.52, 50.45]); // 基輔
  await expect(title).toContainText('烏克蘭總督轄區');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');
  await expect(start.getByTestId('sovereignty-card-verified')).toBeVisible();
  await clickAt(page, [24.1, 56.95]); // 里加
  await expect(title).toContainText('東方總督轄區');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');
  await clickAt(page, [37.62, 55.75]); // 莫斯科
  await expect(title).toContainText('蘇維埃');
  await expect(card).toHaveAttribute('data-layer-status', 'de_jure');
  await clickAt(page, [13.4, 52.5]); // 柏林
  await expect(title).toContainText('德意志國');
  await clickAt(page, [28.86, 47.01]); // 基希涅夫
  await expect(title).toContainText('羅馬尼亞王國');
});

test('1943-07-01／1944-10-01／1945-03-01：補空白第二段（德國、蘇聯、總督轄區、波蘭臨時政府）', async ({ page }) => {
  const card = page.getByTestId('sovereignty-card');
  const title = page.getByTestId('sovereignty-card-title');
  await page.goto('/?date=1943-07-01&axis=sovereignty');
  await waitForBorders(page);
  await clickAt(page, [30.52, 50.45]); // 基輔
  await expect(title).toContainText('烏克蘭總督轄區');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');
  await clickAt(page, [37.62, 55.75]); // 莫斯科
  await expect(title).toContainText('蘇維埃');
  await page.goto('/?date=1944-10-01&axis=sovereignty');
  await waitForBorders(page);
  await clickAt(page, [24.1, 56.95]); // 里加
  await expect(title).toContainText('東方總督轄區');
  await clickAt(page, [25.28, 54.69]); // 維爾紐斯
  await expect(title).toContainText('蘇維埃');
  await clickAt(page, [30.52, 50.45]); // 基輔
  await expect(title).toContainText('蘇維埃');
  await clickAt(page, [21.01, 52.23]); // 華沙：總督府（occupation-1 從德國紀錄拆出）
  await expect(title).toContainText('總督府');
  await expect(page.getByTestId('sovereignty-card-status')).toHaveText('德國佔領（非主權）');
  await page.goto('/?date=1945-03-01&axis=sovereignty');
  await waitForBorders(page);
  await clickAt(page, [21.01, 52.23]); // 華沙
  await expect(title).toContainText('波蘭臨時政府');
  await expect(card).toHaveAttribute('data-layer-status', 'not_sovereign');
});

async function baseColorAt(page: Page, lngLat: [number, number]): Promise<string | null> {
  return page.evaluate((ll) => {
    const map = (window as unknown as { __wlMap: { project: (l: [number, number]) => { x: number; y: number }; queryRenderedFeatures: (p: [number, number], o: object) => { properties: Record<string, string> }[] } }).__wlMap;
    const p = map.project(ll);
    return map.queryRenderedFeatures([p.x, p.y], { layers: ['sov-hatch-base'] })[0]?.properties['wlBase'] ?? null;
  }, lngLat);
}
const lum = (hex: string | null) => (hex ? [16, 8, 0].reduce((a, sh) => a + ((parseInt(hex.slice(1), 16) >> sh) & 255), 0) : NaN);

test('1942-11-01：佔領區依佔領國上色（併入最深、總督府／專員轄區中等、軍事管理最淺）；性質「德國佔領（非主權）」；芬蘭維持自己的色；點德國時佔領區一起亮起', async ({ page }) => {
  await page.goto('/?date=1942-11-01&axis=sovereignty');
  await waitForBorders(page);
  const card = page.getByTestId('sovereignty-card');
  const title = page.getByTestId('sovereignty-card-title');
  const status = page.getByTestId('sovereignty-card-status');

  await clickAt(page, [7.75, 48.58]); // 史特拉斯堡
  await expect(title).toContainText('亞爾薩斯');
  await expect(status).toHaveText('德國併入（非主權）');
  await expect(status).toHaveAttribute('data-control-kind', 'annexed');
  await expect(page.getByTestId('sovereignty-card-occupation-basis')).toContainText('待查證');
  const annexed = await baseColorAt(page, [7.75, 48.58]);

  await clickAt(page, [6.13, 49.61]); // 盧森堡
  await expect(title).toContainText('盧森堡');
  await expect(status).toHaveText('德國併入（非主權）');

  await clickAt(page, [14.42, 50.08]); // 布拉格
  await expect(title).toContainText('保護國');
  await expect(status).toHaveText('德國佔領（非主權）');
  await expect(status).toHaveAttribute('data-control-kind', 'civil_administration');

  await clickAt(page, [21.01, 52.23]); // 華沙
  await expect(title).toContainText('總督府');
  await expect(status).toHaveAttribute('data-control-kind', 'civil_administration');
  const civil = await baseColorAt(page, [21.01, 52.23]);

  await clickAt(page, [20.46, 44.82]); // 貝爾格勒
  await expect(title).toContainText('塞爾維亞');
  await expect(status).toHaveText('德國佔領（非主權）');
  await expect(status).toHaveAttribute('data-control-kind', 'military_administration');
  const military = await baseColorAt(page, [20.46, 44.82]);
  expect(lum(annexed)).toBeLessThan(lum(civil));
  expect(lum(civil)).toBeLessThan(lum(military));

  await clickAt(page, [23.73, 37.98]); // 雅典：德義保共同佔領，缺分區 → 標主要佔領方並註記
  await expect(status).toHaveText('義大利佔領（非主權）');
  await expect(page.getByTestId('sovereignty-card-co-occupied')).toContainText('主要佔領方');

  await clickAt(page, [24.94, 60.17]); // 赫爾辛基：芬蘭不是佔領區
  await expect(card).toHaveAttribute('data-layer-status', 'de_jure');
  await expect(page.getByTestId('sovereignty-card-occupation')).toHaveCount(0);

  await clickAt(page, [13.4, 52.5]); // 柏林：德國本土；佔領／併入區一起挖亮
  await expect(title).toContainText('德意志國');
  await expect(status).toHaveText('國界');
  await expect.poll(async () => Number((await page.getByTestId('map-canvas').getAttribute('data-focus-occupied')) ?? 0)).toBeGreaterThan(10);
  // 圖例：三種深淺（面板開著時圖例可能被收合，只驗存在於 DOM 或展開後可見）
  await page.keyboard.press('Escape');
  if (await page.getByTestId('legend-expand').isVisible()) await page.getByTestId('legend-expand').click();
  await expect(page.getByTestId('legend-sov-occupation-annexed')).toHaveCount(1);
  await expect(page.getByTestId('legend-sov-occupation-military_administration')).toContainText('軍事管理');
});

test('API：德國投降後到 1945-09-02 歐洲不留白（盟軍佔領德國、奧地利、盧森堡、多德卡尼斯；波茨坦後波蘭含奧得—尼斯河以東、蘇聯含柯尼斯堡）', async ({ page }) => {
  type F = { properties: { regimeSlug: string; layerStatus: string; occupation: unknown; endEvent: { id: string } | null } };
  const on = async (d: string) => ((await (await page.request.get(`/api/v1/sovereignty?date=${d}`)).json()).data.featureCollection.features as F[]);
  const slugs = (fs: F[]) => fs.map((f) => f.properties.regimeSlug);
  const jun = await on('1945-06-01');
  for (const s of ['allied-occupied-germany', 'republic-of-austria-1945', 'grand-duchy-of-luxembourg', 'british-military-administration-dodecanese', 'polish-provisional-government-1945',
    'democratic-federal-yugoslavia', 'czechoslovak-republic', 'kingdom-of-italy', 'provisional-government-french-republic', 'soviet-union', 'kingdom-of-romania'])
    expect(slugs(jun)).toContain(s);
  expect(slugs(jun)).not.toContain('deutsches-reich');
  expect(slugs(jun)).not.toContain('independent-state-of-croatia');
  const de = jun.find((f) => f.properties.regimeSlug === 'allied-occupied-germany')!;
  expect(de.properties.layerStatus).toBe('not_sovereign');
  expect(de.properties.occupation).toBeTruthy();
  const sep = await on('1945-09-02');
  for (const s of ['allied-occupied-germany', 'polish-provisional-government-national-unity', 'soviet-union', 'kingdom-of-greece', 'republic-of-finland'])
    expect(slugs(sep)).toContain(s);
  expect(slugs(sep)).not.toContain('polish-provisional-government-1945');
  // 波茨坦後：布雷斯勞（弗羅茨瓦夫）屬波蘭、柯尼斯堡屬蘇聯
  const at = async (d: string, lng: number, lat: number) => (await (await page.request.get(`/api/v1/sovereignty?date=${d}`)).json()).data.featureCollection.features
    .filter((f: { geometry: { type: string; coordinates: number[][][][] } }) => inside(f.geometry, lng, lat)).map((f: F) => f.properties.regimeSlug);
  expect(await at('1945-07-01', 17.04, 51.11)).toEqual(['allied-occupied-germany']);
  expect(await at('1945-08-10', 17.04, 51.11)).toEqual(['polish-provisional-government-national-unity']);
  expect(await at('1945-08-10', 20.51, 54.71)).toEqual(['soviet-union']);
});

function inside(g: { type: string; coordinates: number[][][][] | number[][][] }, x: number, y: number): boolean {
  const polys = (g.type === 'Polygon' ? [g.coordinates] : g.coordinates) as number[][][][];
  return polys.some((rings) => {
    let c = false;
    for (const ring of rings)
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [xi, yi] = ring[i], [xj, yj] = ring[j];
        if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
      }
    return c;
  });
}
