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

test('時間軸：五條戰區軌道，無快照的軌道標為控制資料缺', async ({ page }) => {
  await page.goto('/?date=1940-07-15');
  await expect(page.getByTestId('timeline-track-west-europe')).toBeVisible();
  await expect(page.getByTestId('timeline-snapshot-marker')).toHaveCount(2);
  for (const code of ['east-front', 'north-africa', 'pacific', 'china']) {
    await expect(page.getByTestId(`timeline-track-${code}`)).toHaveAttribute('data-empty', 'true');
  }
  await page.getByTestId('timeline-next-snapshot').click();
  await expect(page.getByTestId('topbar-date')).toHaveText('1940年8月15日');
});

test('日期格式無效 → 回到預設日期並提示', async ({ page }) => {
  await page.goto('/?date=1940-13-99');
  await expect(page.getByTestId('topbar-date')).toHaveText('1940年7月15日');
  await expect(page.getByTestId('toast')).toContainText('日期格式無效');
});

test('早於所有資料的日期顯示「此日期尚無資料」並可跳到最近有資料的日期', async ({ page }) => {
  await page.goto('/?date=1938-03-01');
  await expect(page.getByTestId('map-empty')).toBeVisible();
  await page.getByTestId('map-empty-jump').click();
  await expect(page.getByTestId('topbar-date')).toHaveText('1940年7月15日');
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

