import { expect, test, type Page, type Route } from '@playwright/test';

/**
 * 載入指示（Tai 2026-10-31）：大幅跳日期或拖到其他區域時，國界／控制區請求或 MapLibre 切片超過約 300ms 未完成，
 * 地圖蓋上半透明蒙版、「載入中」置於地圖正中央（Tai 2026-11-01，原為左上角）；蒙版淡入、不攔截滑鼠；完成後隱藏、新國界淡入（減少動態時直接出現）。
 * 快速連續跳日期：舊請求被中止（不讓舊資料蓋掉新資料）。
 * 需要開發 API（5052），以 `WL_E2E_BORDERS=1 WL_E2E_PORT=4201` 執行；用 page.route 只延遲回應，不 mock 內容、不寫入資料。
 */
test.skip(!process.env['WL_E2E_BORDERS'], '需要開發 API（5052）上的 borders 資料');
const prefix = process.env['WL_SHOT_PREFIX'] ?? 'borders-app-v3';
type WlMap = { jumpTo: (o: object) => void; querySourceFeatures: (s: string) => { properties: { recordId: string } }[] };

async function open(page: Page, date: string): Promise<void> {
  await page.goto(`/?date=${date}&axis=sovereignty`);
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.jumpTo({ center: [16, 48], zoom: 3.3 }));
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
  await expect(page.getByTestId('map-busy')).toHaveCount(0);
}
async function jump(page: Page, date: string): Promise<void> {
  await page.getByTestId('timeline-date-input').fill(date);
  await page.getByTestId('timeline-date-input').press('Enter');
}
/** 只延遲指定日期的國界／控制區回應（內容仍來自開發 API）。 */
async function delay(page: Page, dates: Record<string, number>): Promise<void> {
  await page.route(/\/api\/v1\/(sovereignty|control)\?/, async (route: Route) => {
    const d = new URL(route.request().url()).searchParams.get('date') ?? '';
    const ms = dates[d] ?? 0;
    if (ms) await new Promise((r) => setTimeout(r, ms));
    await route.continue().catch(() => undefined); // 已被前端中止的請求
  });
}

test('大幅跳日期且載入慢：300ms 後出現半透明蒙版與置中的「載入中」、不擋操作；完成後隱藏並淡入新國界', async ({ page }) => {
  await open(page, '1939-10-23');
  await delay(page, { '1944-10-01': 1800 });
  const canvas = page.getByTestId('map-canvas');
  const fade0 = Number(await canvas.getAttribute('data-sov-fade'));
  await jump(page, '1944-10-01');
  const busy = page.getByTestId('map-busy');
  await expect(busy).toBeVisible();
  await expect(busy).toHaveAttribute('role', 'status');
  await expect(busy).toContainText('載入中');
  await expect(busy).toHaveCSS('pointer-events', 'none');
  // 蒙版：蓋滿地圖、半透明、不攔截滑鼠；「載入中」置於地圖正中央
  const scrim = page.getByTestId('map-busy-scrim');
  await expect(scrim).toBeVisible();
  await expect(scrim).toHaveCSS('pointer-events', 'none');
  const bg = await scrim.evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(bg).not.toBe('rgba(0, 0, 0, 0)');
  const alpha = Number((/\/\s*([\d.]+)\s*\)$/.exec(bg) ?? /^rgba\([^,]+,[^,]+,[^,]+,\s*([\d.]+)\)$/.exec(bg))?.[1]); // 半透明：0 < alpha < 1
  expect(alpha).toBeGreaterThan(0);
  expect(alpha).toBeLessThan(1);
  const cb = (await canvas.boundingBox())!;
  const sb = (await scrim.boundingBox())!;
  const bb = (await busy.boundingBox())!;
  expect(Math.abs(sb.width - cb.width)).toBeLessThan(2);
  expect(Math.abs(sb.height - cb.height)).toBeLessThan(2);
  expect(Math.abs(bb.x + bb.width / 2 - (cb.x + cb.width / 2))).toBeLessThan(4);
  expect(Math.abs(bb.y + bb.height / 2 - (cb.y + cb.height / 2))).toBeLessThan(4);
  await page.mouse.move(5, 5);
  await page.waitForTimeout(200);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-loading-1944-10-01.png` });
  await expect(busy).toHaveCount(0, { timeout: 8000 });
  await expect.poll(async () => Number(await canvas.getAttribute('data-sov-fade'))).toBe(fade0 + 1);
  await expect(page).toHaveURL(/date=1944-10-01/);
});

test('延遲顯示：載入開始後約 300ms 內不出現 spinner（避免快速載入時閃爍）', async ({ page }) => {
  await open(page, '1939-10-23');
  await delay(page, { '1942-11-01': 1500 });
  const t0 = Date.now();
  await jump(page, '1942-11-01');
  await page.waitForTimeout(200);
  if (Date.now() - t0 < 380) await expect(page.getByTestId('map-busy')).toHaveCount(0);
  await expect(page.getByTestId('map-busy')).toBeVisible();
  await expect(page.getByTestId('map-busy')).toHaveCount(0, { timeout: 8000 });
});

test('快速連續跳日期：舊請求被中止，晚到的舊資料不會蓋掉新日期', async ({ page, request }) => {
  await open(page, '1939-10-23');
  await delay(page, { '1941-12-01': 2500 });
  const aborted: string[] = [];
  page.on('requestfailed', (r) => {
    if (/\/api\/v1\/sovereignty\?/.test(r.url())) aborted.push(new URL(r.url()).searchParams.get('date') ?? '');
  });
  await jump(page, '1941-12-01');
  await expect(page.getByTestId('map-busy')).toBeVisible();
  await jump(page, '1944-10-01');
  await expect(page.getByTestId('map-busy')).toHaveCount(0, { timeout: 8000 });
  await expect.poll(() => aborted).toContain('1941-12-01');
  await page.waitForTimeout(2800); // 超過舊請求的延遲
  const want = ((await (await request.get('/api/v1/sovereignty?date=1944-10-01')).json()) as { data: { featureCollection: { features: { properties: { recordId: string } }[] } } })
    .data.featureCollection.features.map((f) => f.properties.recordId);
  const have = await page.evaluate(() => [...new Set((window as unknown as { __wlMap: WlMap }).__wlMap.querySourceFeatures('sovereignty').map((f) => f.properties.recordId))]);
  expect(have.length).toBeGreaterThan(5);
  for (const id of have) expect(want).toContain(id);
  await expect(page).toHaveURL(/date=1944-10-01/);
});

test('減少動態：仍顯示載入指示，但新國界不播淡入', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await open(page, '1939-10-23');
  await delay(page, { '1943-10-01': 1200 });
  const canvas = page.getByTestId('map-canvas');
  const fade0 = Number(await canvas.getAttribute('data-sov-fade'));
  await jump(page, '1943-10-01');
  await expect(page.getByTestId('map-busy')).toBeVisible();
  await expect(page.getByTestId('map-busy')).toHaveCount(0, { timeout: 8000 });
  await page.waitForTimeout(500);
  expect(Number(await canvas.getAttribute('data-sov-fade'))).toBe(fade0);
});
