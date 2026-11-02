import { expect, test, type Page } from '@playwright/test';

/** 等地圖載完並畫出至少一個控制區多邊形（data-rendered-features 由 queryRenderedFeatures 計算）。 */
async function waitForPolygons(page: Page): Promise<void> {
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-features')) ?? 0)).toBeGreaterThan(0);
}

/** 巴黎（2.35E, 48.86N）在 1940-07-15 德軍佔領區內；以地圖投影換成畫面座標（dev 模式掛在 window.__wlMap）。 */
async function screenPointOf(page: Page, lngLat: [number, number]): Promise<{ x: number; y: number }> {
  const box = await page.getByTestId('map-canvas').boundingBox();
  const p = await page.evaluate((ll) => {
    const map = (window as unknown as { __wlMap: { project: (l: [number, number]) => { x: number; y: number } } }).__wlMap;
    return map.project(ll);
  }, lngLat);
  return { x: (box?.x ?? 0) + p.x, y: (box?.y ?? 0) + p.y };
}

test('M0：開頁 → 看到多邊形 → 點開來源', async ({ page }) => {
  await page.goto('/?date=1940-07-15');
  await expect(page.getByTestId('topbar-date')).toHaveText('1940年7月15日');
  await waitForPolygons(page);
  await expect(page.getByTestId('interp-chip')).toHaveAttribute('data-state', 'attested');

  const pt = await screenPointOf(page, [2.35, 48.86]);
  await page.mouse.click(pt.x, pt.y);
  const card = page.getByTestId('feature-card');
  await expect(card).toBeVisible();
  await expect(page.getByTestId('feature-card-title')).toContainText('軍事佔領');

  await card.getByTestId('citation-button').click();
  const pop = page.getByTestId('citation-popover');
  await expect(pop).toBeVisible();
  const items = pop.getByTestId('citation-item');
  expect(await items.count()).toBeGreaterThan(0);
  // 主要來源（R7：地圖類、有圖號）排第一
  await expect(items.first().getByTestId('citation-locator')).not.toBeEmpty();
  await expect(items.first()).toContainText('主要');
});

test('兩快照之間顯示推估過渡，chip 列出戰區並可跳到前一快照', async ({ page }) => {
  await page.goto('/?date=1940-07-30');
  await waitForPolygons(page);
  const chip = page.getByTestId('interp-chip');
  await expect(chip).toHaveAttribute('data-state', 'interpolated');
  await chip.click();
  await expect(page.getByTestId('interp-theater-row')).toHaveCount(1);
  await page.getByTestId('interp-jump-prev').click();
  await expect(page.getByTestId('topbar-date')).toHaveText('1940年7月15日');
  await expect(page).toHaveURL(/date=1940-07-15/);
});

/** 快照日期一律問 API，不寫死筆數（資料會隨 seed 增加）。 */
async function snapshotDates(request: import('@playwright/test').APIRequestContext): Promise<string[]> {
  const res = await request.get('/api/v1/timeline/snapshots?pageSize=100');
  const body = await res.json();
  return ((body.data.items ?? body.data) as { asOf: string }[]).map((s) => s.asOf).sort();
}

test('時間軸：五條戰區軌道，無快照的軌道標為控制資料缺', async ({ page, request }) => {
  const dates = await snapshotDates(request);
  await page.goto('/?date=1940-07-15');
  await expect(page.getByTestId('timeline-track-west-europe')).toBeVisible();
  await expect(page.getByTestId('timeline-snapshot-marker')).toHaveCount(dates.length);
  for (const code of ['east-front', 'north-africa', 'pacific', 'china']) {
    await expect(page.getByTestId(`timeline-track-${code}`)).toHaveAttribute('data-empty', 'true');
  }
  await page.getByTestId('timeline-next-snapshot').click();
  await expect(page.getByTestId('topbar-date')).toHaveText('1940年8月15日');
});

test('日期格式無效 → 回到預設日期並提示', async ({ page }) => {
  // toast 數秒後自動消失；--workers=2 時開頁較慢，先開始等 toast 再導頁，避免 toast 已消失才檢查
  const toastSeen = expect(page.getByTestId('toast')).toContainText('日期格式無效', { timeout: 30_000 });
  await page.goto('/?date=1940-13-99');
  await expect(page.getByTestId('topbar-date')).toHaveText('1940年7月15日');
  await toastSeen;
});

test('早於所有資料的日期顯示「此日期尚無資料」並可跳到最近有資料的日期', async ({ page, request }) => {
  const [first] = await snapshotDates(request);
  const [y, m, d] = first.split('-').map(Number);
  // 開發庫（5442）與正式庫（5051）的主權層都已從 1908-10-05 起連續有資料，時間軸範圍內沒有真正「無資料」的日期。
  // 兩種設定都攔截這次開頁的主權／控制回應、清空圖徵，只驗證空白狀態的畫面與「跳到最近快照」（快照日期仍來自 API，不寫入資料）。
  const empty = async (route: import('@playwright/test').Route) => {
    const res = await route.fetch();
    const body = await res.json();
    if (body?.data?.featureCollection) body.data.featureCollection.features = [];
    if (body?.data) body.data.coverageNotes = [];
    await route.fulfill({ response: res, json: body });
  };
  await page.route('**/api/v1/sovereignty?*', empty);
  await page.route('**/api/v1/control?*', empty);
  await page.goto('/?date=1938-03-01');
  await expect(page.getByTestId('map-empty')).toBeVisible();
  await page.unrouteAll({ behavior: 'wait' });
  await page.getByTestId('map-empty-jump').click();
  await expect(page.getByTestId('topbar-date')).toHaveText(`${y}年${m}月${d}日`);
});

test('控制資料缺：點點狀區塊出現資料缺卡片（原因來自 API）；控制區卡片的「補充」列', async ({ page, request }) => {
  const dto = (await (await request.get('/api/v1/control?date=1940-07-15')).json()).data;
  test.skip(!(dto.coverageNotes ?? []).length, '此日期沒有控制資料缺備註');
  await page.goto('/?date=1940-07-15');
  await waitForPolygons(page);
  await expect.poll(async () => Number((await page.getByTestId('map-canvas').getAttribute('data-rendered-gaps')) ?? 0)).toBeGreaterThan(0);
  // 阿爾卑斯（Hautes-Alpes，Gap 市附近）
  await page.evaluate(() => (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap.jumpTo({ center: [6.3, 44.7], zoom: 7 }));
  await page.waitForTimeout(800);
  const pt = await screenPointOf(page, [6.3, 44.6]);
  await page.mouse.click(pt.x, pt.y);
  await expect(page.getByTestId('gap-card')).toBeVisible();
  await expect(page.getByTestId('gap-card-reason')).toHaveText('已調查，沒有合格來源');

  // 補充：有 controllerSupplements 的控制區，卡片要標「補充」
  const f = (dto.featureCollection.features as { properties: { controllerSupplements?: unknown[] } }[]).find((x) => (x.properties.controllerSupplements ?? []).length > 0);
  test.skip(!f, '此日期沒有補充事件');
  await page.goto('/?date=1940-07-15');
  await waitForPolygons(page);
  const paris = await screenPointOf(page, [2.35, 48.86]);
  await page.mouse.click(paris.x, paris.y);
  await expect(page.getByTestId('feature-card')).toBeVisible();
  await expect(page.getByTestId('feature-card-supplement-label')).toHaveText('補充');
});

// 陣營色只依 API 的 controllerAlignment（憲法 §6「陣營」）。不寫死資料：先問 API 當日陣營，再比對圖例；
// 沒有陣營切片的政權必須顯示「陣營未建置」。
const CAMP_KEY: Record<string, string> = { axis: 'axis', allies: 'allies', co_belligerent: 'cobelligerent', neutral: 'neutral' };
for (const date of ['1940-07-15', '1940-10-01']) {
  test(`圖例的陣營與 API 一致（${date}）`, async ({ page, request }) => {
    const res = await request.get(`/api/v1/control?date=${date}`);
    expect(res.ok()).toBeTruthy();
    const features = (await res.json()).data.featureCollection.features as {
      properties: { controllerRegimeId: string; controllerAlignment: { camp: string } | null };
    }[];
    expect(features.length).toBeGreaterThan(0);
    const expected = new Set(features.map((f) => (f.properties.controllerAlignment ? CAMP_KEY[f.properties.controllerAlignment.camp] : 'unassigned')));

    await page.goto(`/?date=${date}`);
    const items = page.getByTestId('legend-regime-item');
    await expect(items.first()).toBeVisible();
    const shown = new Set(await items.evaluateAll((els) => els.map((e) => e.getAttribute('data-camp') ?? '')));
    expect(shown).toEqual(expected);
    if (expected.has('unassigned')) await expect(page.getByTestId('legend')).toContainText('陣營未建置');
  });
}


// Stitch v2 對齊（DESIGN.md Timeline／Typography：只用 12px 等既有字級；圖例可收成左下小按鈕）
test('Stitch v2：時間軸標籤與年份 12px、年份不壓在軌道上、播放鈕非朱紅', async ({ page }) => {
  await page.goto('/?date=1940-07-15');
  await expect(page.getByTestId('timeline-track-west-europe')).toBeVisible();
  const labels = page.getByTestId('timeline-track-label');
  await expect(labels).toHaveCount(5);
  for (const fs of await labels.evaluateAll((els) => els.map((e) => getComputedStyle(e).fontSize))) expect(fs).toBe('12px');
  // 每個標籤與對應軌道垂直置中對齊（誤差 ≤ 2px）
  const codes = ['west-europe', 'east-front', 'north-africa', 'pacific', 'china'];
  for (let i = 0; i < codes.length; i++) {
    const l = await labels.nth(i).boundingBox();
    const t = await page.getByTestId(`timeline-track-${codes[i]}`).boundingBox();
    expect(Math.abs(l!.y + l!.height / 2 - (t!.y + t!.height / 2))).toBeLessThanOrEqual(2);
  }
  const years = page.getByTestId('timeline-year-label');
  expect(await years.first().evaluate((e) => getComputedStyle(e).fontSize)).toBe('12px');
  const lastTrack = await page.getByTestId('timeline-track-china').boundingBox();
  const year = await years.first().boundingBox();
  expect(year!.y).toBeGreaterThanOrEqual(lastTrack!.y + lastTrack!.height);
  const bg = await page.getByTestId('timeline-play').evaluate((e) => getComputedStyle(e).backgroundColor);
  expect(bg).not.toBe('rgb(178, 58, 38)');
  await page.getByTestId('timeline-speed').click();
  await expect(page.getByTestId('timeline-speed')).toHaveAttribute('data-speed', 'month');
});

test('Stitch v2：圖例收合成小按鈕，可再展開', async ({ page }) => {
  await page.goto('/?date=1940-07-15');
  await expect(page.getByTestId('legend')).toHaveAttribute('data-state', 'open');
  await page.getByTestId('legend-toggle').click();
  await expect(page.getByTestId('legend')).toHaveAttribute('data-state', 'collapsed');
  const box = await page.getByTestId('legend-expand').boundingBox();
  expect(box!.width).toBeLessThan(140);
  await page.getByTestId('legend-expand').click();
  await expect(page.getByTestId('legend')).toHaveAttribute('data-state', 'open');
});

test('找不到頁面：置中紙卡＋回主地圖', async ({ page }) => {
  await page.goto('/no-such-page');
  await expect(page.getByTestId('not-found-page')).toContainText('找不到頁面');
  await page.getByTestId('not-found-back').click();
  await expect(page.getByTestId('atlas-page')).toBeVisible();
});

/** 時間軸起點＝min(預設 1937-07-01, 最早快照, 最早事件)；不是 1 月 1 日時標「YYYY-MM」（timeline-scale rangeFor）。 */
async function expectedStartLabel(request: import('@playwright/test').APIRequestContext): Promise<string> {
  const ext = (await (await request.get('/api/v1/timeline/extent')).json()).data as { earliestEvent?: string | null };
  const start = [...(await snapshotDates(request)), ext.earliestEvent ?? '9999-12-31', '1937-07-01'].reduce((a, b) => (a < b ? a : b));
  return start.slice(0, 7);
}

test('配色：填色＝陣營、政權名稱標籤來自 API、圖例政權顯示邊框樣本、時間軸起點（依最早快照／事件，兩庫皆為 1908-10）', async ({ page, request }) => {
  const startLabel = await expectedStartLabel(request);
  const res = await request.get('/api/v1/control?date=1940-07-15');
  const features = (await res.json()).data.featureCollection.features as { properties: { controllerRegimeId: string; controlType: string } }[];
  await page.goto('/?date=1940-07-15');
  await waitForPolygons(page);
  await expect(page.getByTestId('timeline-start-label')).toHaveText(startLabel);
  // 圖例：每個政權至少一個邊框樣本，樣本的控制類型都出現在 API 資料中
  const types = new Set(features.map((f) => f.properties.controlType));
  const sw = page.getByTestId('legend-regime-swatch');
  await expect(sw.first()).toBeVisible();
  for (const t of await sw.evaluateAll((els) => els.map((e) => e.getAttribute('data-control-type') ?? ''))) expect(types.has(t)).toBe(true);
  // 地圖標籤：控制方政權＋主權層國名（兩庫皆有主權資料，一律加入）
  const ids = new Set(features.map((f) => f.properties.controllerRegimeId));
  const sov = (await (await request.get('/api/v1/sovereignty?date=1940-07-15')).json()).data.featureCollection.features as { properties: { regimeId: string } }[];
  for (const f of sov) ids.add(f.properties.regimeId);
  const labels = page.getByTestId('map-regime-label');
  await expect(labels.first()).toBeVisible();
  for (const id of await labels.evaluateAll((els) => els.map((e) => e.getAttribute('data-regime-id') ?? ''))) expect(ids.has(id)).toBe(true);
  await expect(page.getByTestId('legend-control-types-note')).toContainText('填色＝陣營');
});
