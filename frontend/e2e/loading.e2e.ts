import { expect, test, type Page, type Route } from '@playwright/test';

/**
 * 全畫面載入蒙版（Tai 2026-11-02）：大幅跳日期或拖到其他區域時，國界／控制區請求或 MapLibre 切片超過約 300ms 未完成，
 * 蒙版蓋住整個視窗（含時間軸與側欄）、「載入中」置於視窗正中央，擋住操作（pointer-events 開啟）；
 * 蒙版淡入；資料到位後淡出（減少動態時直接出現／消失）。
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
/** 蒙版擋住操作時，用 force 繞過覆蓋層直接填入輸入框。 */
async function jumpForce(page: Page, date: string): Promise<void> {
  await page.getByTestId('timeline-date-input').fill(date, { force: true });
  await page.getByTestId('timeline-date-input').press('Enter');
}

test('大幅跳日期且載入慢：掃描揭露層播報「載入中」（不再蓋全畫面蒙版）；完成後淡入新國界', async ({ page }) => {
  await open(page, '1939-10-23');
  await delay(page, { '1944-10-01': 1800 });
  const canvas = page.getByTestId('map-canvas');
  const fade0 = Number(await canvas.getAttribute('data-sov-fade'));
  await jump(page, '1944-10-01');
  const busy = page.getByTestId('map-busy');
  await expect(busy).toBeAttached();
  await expect(busy).toHaveAttribute('role', 'status');
  await expect(busy).toContainText('載入中');
  // 跳年改用掃描揭露（06023c2，plan B）：不再蓋全畫面蒙版，改為快照＋亮線掃出新圖，「載入中」由掃描層的 status 播報
  await expect(page.getByTestId('map-scan')).toBeAttached();
  await expect(page.getByTestId('map-busy-scrim')).toHaveCount(0);
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
  if (Date.now() - t0 < 380) await expect(page.getByTestId('map-busy-scrim')).toHaveCount(0);
  await expect(page.getByTestId('map-busy')).toBeAttached(); // 掃描揭露層的 status（06023c2 後不再有全畫面蒙版）
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
  // 蒙版擋住操作：用 force 繞過覆蓋層跳到新日期（模擬鍵盤或程式化導航）
  await jumpForce(page, '1944-10-01');
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
