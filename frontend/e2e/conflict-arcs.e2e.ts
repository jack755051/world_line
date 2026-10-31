import { expect, test, type Page } from '@playwright/test';

/**
 * 遠距交戰虛線弧（Tai 2026-10-31）：交戰雙方不相鄰時，在兩國間畫虛線弧，雙劍放弧線中點；
 * 只在點選政權後顯示（與雙劍同一份資料），畫在聚焦遮罩之上。
 * 需要開發 API（127.0.0.1:5052）上的 borders-us、borders-asia-1 等批次，以 `WL_E2E_BORDERS=1 WL_E2E_PORT=4201` 執行；不使用 mock，不寫入資料。
 */
test.skip(!process.env['WL_E2E_BORDERS'], '需要開發 API（5052）上的 borders／conflicts 資料');
const prefix = process.env['WL_SHOT_PREFIX'] ?? 'borders-app-v3';

type WlMap = { jumpTo: (o: object) => void; project: (l: [number, number]) => { x: number; y: number } };

async function open(page: Page, date: string, center: [number, number], zoom: number): Promise<void> {
  await page.goto(`/?date=${date}&axis=sovereignty`);
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await page.evaluate(([c, z]) => (window as unknown as { __wlMap: WlMap }).__wlMap.jumpTo({ center: c, zoom: z }), [center, zoom] as const);
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(3);
  await page.waitForTimeout(300);
}

async function clickLngLat(page: Page, lngLat: [number, number]): Promise<void> {
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  const box = await page.getByTestId('map-canvas').boundingBox();
  const p = await page.evaluate((ll) => (window as unknown as { __wlMap: WlMap }).__wlMap.project(ll), lngLat);
  await page.mouse.click((box?.x ?? 0) + p.x, (box?.y ?? 0) + p.y);
}

const US: [number, number] = [-98, 39];

test('1942-12-01：平時沒有虛線弧；點美國 → 與德、義、羅、保、匈、日的交戰都畫虛線弧；雙劍在弧線上且錯開、鏡頭自動框入所有弧線、在聚焦遮罩上可見；關閉就隱藏', async ({ page }) => {
  await open(page, '1942-12-01', [-45, 42], 2.2);
  const arcs = page.getByTestId('map-conflict-arc');
  await expect(arcs).toHaveCount(0);

  await clickLngLat(page, US);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('美利堅');
  await expect(page.getByTestId('map-focus-mask')).toHaveAttribute('data-active', 'true');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await expect(arcs).toHaveCount(6);
  await expect(page.getByTestId('map-conflict-icon')).toHaveCount(6);

  // 鏡頭自動框入所有弧線（Japan—US 不再跑出畫面）：等 arc-fit 完成、鏡頭停下
  await expect.poll(async () => Number((await page.getByTestId('map-canvas').getAttribute('data-arc-fit')) ?? 0)).toBeGreaterThan(0);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await page.waitForTimeout(300);
  // 弧線在遮罩之上；雙劍在自己的弧線上、彼此錯開；每條弧線都有一段、每個雙劍都在地圖可視區內（面板左側）
  const check = await page.evaluate(() => {
    const mask = document.querySelector('[data-testid="map-focus-mask"]')!;
    const svg = document.querySelector('[data-testid="map-conflict-arcs"]')!;
    const after = !!(mask.compareDocumentPosition(svg) & Node.DOCUMENT_POSITION_FOLLOWING);
    const canvas = document.querySelector('[data-testid="map-canvas"]')!.getBoundingClientRect();
    const sheet = document.querySelector('[data-testid="regime-sheet"]')?.getBoundingClientRect();
    const right = sheet ? sheet.left - canvas.left : canvas.width;
    const icons: { x: number; y: number }[] = [];
    let onArc = true;
    let hiddenArcs = 0;
    let iconsOut = 0;
    for (const line of document.querySelectorAll('[data-testid="map-conflict-arc"]')) {
      const id = line.getAttribute('data-record-id')!;
      const pts = line.getAttribute('points')!.split(' ').map((s) => s.split(',').map(Number));
      const vis = (x: number, y: number) => x >= 0 && x <= right && y >= 0 && y <= canvas.height;
      if (!pts.some(([x, y]) => vis(x, y))) hiddenArcs++;
      const icon = document.querySelector(`[data-testid="map-conflict-icon"][data-record-id="${id}"]`) as HTMLElement;
      const p = { x: parseFloat(icon.style.left), y: parseFloat(icon.style.top) };
      icons.push(p);
      if (!vis(p.x, p.y)) iconsOut++;
      if (!pts.some(([x, y]) => Math.hypot(x - p.x, y - p.y) < 2)) onArc = false;
    }
    let minGap = Infinity;
    for (let i = 0; i < icons.length; i++)
      for (let j = i + 1; j < icons.length; j++) minGap = Math.min(minGap, Math.hypot(icons[i].x - icons[j].x, icons[i].y - icons[j].y));
    return { after, onArc, hiddenArcs, iconsOut, minGap, dash: getComputedStyle(document.querySelector('[data-testid="map-conflict-arc"]')!).strokeDasharray };
  });
  expect(check.after).toBe(true);
  expect(check.dash).not.toBe('none');
  expect(check.onArc).toBe(true);
  expect(check.hiddenArcs).toBe(0); // 每條弧線都有一段在畫面內（日本—美國不再整條跑出畫面）
  expect(check.iconsOut).toBe(0); // 每個雙劍都在畫面內、可點
  expect(check.minGap).toBeGreaterThanOrEqual(30);

  await page.getByTestId('sovereignty-card-close').click();
  await expect(arcs).toHaveCount(0);
});

test('1942-12-01：相鄰的交戰（日本—中華民國）不畫弧，雙劍維持原位置', async ({ page }) => {
  await open(page, '1942-12-01', [112, 35], 3.2);
  await clickLngLat(page, [104, 30.6]); // 成都（中華民國控制區）
  await expect(page.getByTestId('sovereignty-card')).toBeVisible();
  await expect(page.getByTestId('map-conflict-icon')).toHaveCount(1);
  await expect(page.getByTestId('map-conflict-arc')).toHaveCount(0);
});

test('API：日本—英國的弧接到開戰地點哥打巴魯（英屬馬來亞，殖民地尚未建置），日本—美國接到珍珠港', async ({ page }) => {
  const res = await page.request.get('/api/v1/conflicts?date=1942-12-01');
  const fs = (await res.json()).data.featureCollection.features as { properties: { regimeASlug: string; regimeBSlug: string; arc: { from: number[]; to: number[]; eventEnd: string | null } | null } }[];
  const pick = (a: string, b: string) => fs.find((f) => f.properties.regimeASlug === a && f.properties.regimeBSlug === b)!.properties.arc!;
  expect(pick('empire-of-japan', 'united-kingdom').to).toEqual([102.24, 6.13]);
  expect(pick('empire-of-japan', 'united-kingdom').eventEnd).toBe('to');
  // 另一端＝日本控制區中離哥打巴魯最近的點（不是日本本土），弧線短、雙劍在馬來亞附近
  const jpUkFrom = pick('empire-of-japan', 'united-kingdom').from;
  expect(Math.hypot(jpUkFrom[0] - 102.24, jpUkFrom[1] - 6.13)).toBeLessThan(15);
  expect(pick('empire-of-japan', 'united-states-of-america').to).toEqual([-157.95, 21.36]);
  expect(pick('deutsches-reich', 'united-states-of-america').eventEnd).toBeNull();
});

test('截圖：1942-12-01 點美國的遠距交戰虛線弧', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await open(page, '1942-12-01', [-45, 42], 2.2);
  await page.waitForTimeout(800);
  await clickLngLat(page, US);
  await expect(page.getByTestId('map-conflict-arc')).toHaveCount(6);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await expect.poll(async () => Number((await page.getByTestId('map-canvas').getAttribute('data-arc-fit')) ?? 0)).toBeGreaterThan(0);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await page.mouse.move(5, 5);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-us-arcs-1942-12-01.png` });
});

test('1941-12-08：點日本 → 日本—英國的弧從日本控制區接到哥打巴魯，雙劍在弧線中點、在馬來亞附近（線與圖示一致）；開戰事件有正式出處', async ({ page }) => {
  const res = await page.request.get('/api/v1/conflicts?date=1941-12-08');
  const f = ((await res.json()).data.featureCollection.features as { properties: { recordId: string; regimeASlug: string; regimeBSlug: string; startEvent: { id: string } } }[])
    .find((x) => x.properties.regimeASlug === 'empire-of-japan' && x.properties.regimeBSlug === 'united-kingdom')!;
  const ev = (await (await page.request.get(`/api/v1/events/${f.properties.startEvent.id}`)).json()).data as { citations: { locator: string }[] };
  expect(ev.citations.length).toBeGreaterThan(0);

  await page.emulateMedia({ reducedMotion: 'reduce' });
  await open(page, '1941-12-08', [125, 25], 3);
  await clickLngLat(page, [138, 36]);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('日本');
  const arc = page.locator(`[data-testid="map-conflict-arc"][data-record-id="${f.properties.recordId}"]`);
  await expect(arc).toHaveCount(1);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await expect.poll(async () => Number((await page.getByTestId('map-canvas').getAttribute('data-arc-fit')) ?? 0)).toBeGreaterThan(0);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await page.waitForTimeout(400);
  const r = await page.evaluate((id) => {
    const pts = document.querySelector(`[data-testid="map-conflict-arc"][data-record-id="${id}"]`)!.getAttribute('points')!.split(' ').map((s) => s.split(',').map(Number));
    const icon = document.querySelector(`[data-testid="map-conflict-icon"][data-record-id="${id}"]`) as HTMLElement;
    const p = { x: parseFloat(icon.style.left), y: parseFloat(icon.style.top) };
    const kb = (window as unknown as { __wlMap: { project: (l: [number, number]) => { x: number; y: number } } }).__wlMap.project([102.24, 6.13]);
    const end = pts[pts.length - 1];
    const len = Math.hypot(pts[0][0] - end[0], pts[0][1] - end[1]);
    const lg = document.querySelector('[data-testid="legend"]')!.getBoundingClientRect();
    const cv = document.querySelector('[data-testid="map-canvas"]')!.getBoundingClientRect();
    const kbVisible = !(cv.left + kb.x >= lg.left && cv.left + kb.x <= lg.right && cv.top + kb.y >= lg.top && cv.top + kb.y <= lg.bottom);
    return { kbVisible, endToKb: Math.hypot(end[0] - kb.x, end[1] - kb.y), iconOnArc: pts.some(([x, y]) => Math.hypot(x - p.x, y - p.y) < 2), iconToKb: Math.hypot(p.x - kb.x, p.y - kb.y), len };
  }, f.properties.recordId);
  expect(r.endToKb).toBeLessThan(3); // 弧線終點＝哥打巴魯
  expect(r.kbVisible).toBe(true); // 哥打巴魯端不被圖例蓋住
  expect(r.iconOnArc).toBe(true);
  expect(r.iconToKb).toBeLessThanOrEqual(r.len); // 雙劍在弧線上、離事件地點不超過弧長（不在日本本土）
  await page.mouse.move(5, 5);
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-jp-uk-1941-12-08.png` });
});
