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

test('1942-12-01：平時沒有虛線弧；點美國 → 與德、義、羅、保、匈的交戰畫虛線弧（日美經阿留申相鄰，只有雙劍）；雙劍在弧線上且錯開、鏡頭自動框入所有弧線、在聚焦遮罩上可見；關閉就隱藏', async ({ page }) => {
  await open(page, '1942-12-01', [-45, 42], 2.2);
  const arcs = page.getByTestId('map-conflict-arc');
  await expect(arcs).toHaveCount(0);

  await clickLngLat(page, US);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('美利堅');
  await expect(page.getByTestId('map-focus-mask')).toHaveAttribute('data-active', 'true');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  // 日佔阿留申（1942-06 起）與美國阿拉斯加相接，日美算相鄰：不畫弧，雙劍留在珍珠港；其餘 5 個交戰仍畫弧
  await expect(arcs).toHaveCount(5);
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

type ArcFeature = { geometry: { coordinates: number[] }; properties: { recordId: string; regimeASlug: string; regimeBSlug: string; adjacent: boolean | null; arc: { from: number[]; to: number[]; eventEnd: string | null } | null } };
async function conflictsOn(page: Page, date: string): Promise<ArcFeature[]> {
  const res = await page.request.get(`/api/v1/conflicts?date=${date}`);
  return (await res.json()).data.featureCollection.features as ArcFeature[];
}
const pick = (fs: ArcFeature[], a: string, b: string) => fs.find((f) => f.properties.regimeASlug === a && f.properties.regimeBSlug === b)!;

test('API：屬地算宗主國的控制範圍——日英經英屬緬甸與日佔印度支那相鄰；緬甸失陷後經英屬印度與日佔緬甸相鄰；泰英弧從美塞接到英屬印度；日美 1941-12 接到珍珠港、1942-12 經阿留申相鄰', async ({ page }) => {
  // 1941-12-10：英屬緬甸（regime_dependencies → 英國）與日本軍事管理下的法屬印度支那相接 → 相鄰，雙劍在開戰地點哥打巴魯
  let jpUk = pick(await conflictsOn(page, '1941-12-10'), 'empire-of-japan', 'united-kingdom');
  expect(jpUk.properties.adjacent).toBe(true);
  expect(jpUk.properties.arc).toBeNull();
  expect(jpUk.geometry.coordinates).toEqual([102.24, 6.13]);
  // 1942-12-01：馬來亞、緬甸都已是日佔區；英屬印度（regime_dependencies → 英國）與日佔緬甸相接 → 相鄰，不畫弧，雙劍仍在哥打巴魯
  const d1201 = await conflictsOn(page, '1942-12-01');
  jpUk = pick(d1201, 'empire-of-japan', 'united-kingdom');
  expect(jpUk.properties.adjacent).toBe(true);
  expect(jpUk.properties.arc).toBeNull();
  expect(jpUk.geometry.coordinates).toEqual([102.24, 6.13]);
  // 泰英：開戰地點在泰緬邊境美塞，弧從美塞接到最近的英國控制範圍（英屬印度東北），不再接到英國本土
  const thUk = pick(d1201, 'kingdom-of-thailand', 'united-kingdom').properties.arc!;
  expect(thUk.from).toEqual([99.88, 20.43]);
  expect(thUk.eventEnd).toBe('from');
  expect(Math.hypot(thUk.to[0] - thUk.from[0], thUk.to[1] - thUk.from[1])).toBeLessThan(10);
  expect(thUk.to[0]).toBeGreaterThan(88); // 在印度東北，不在歐洲
  // 日美：1941-12-10 從日本控制區（南洋群島）接到珍珠港；1942-12-01 日佔阿留申與阿拉斯加相接 → 相鄰、不畫弧
  const jpUs41 = pick(await conflictsOn(page, '1941-12-10'), 'empire-of-japan', 'united-states-of-america').properties.arc!;
  expect(jpUs41.to).toEqual([-157.95, 21.36]);
  expect(jpUs41.eventEnd).toBe('to');
  const jpUs42 = pick(d1201, 'empire-of-japan', 'united-states-of-america');
  expect(jpUs42.properties.adjacent).toBe(true);
  expect(jpUs42.properties.arc).toBeNull();
  expect(pick(d1201, 'deutsches-reich', 'united-states-of-america').properties.arc!.eventEnd).toBeNull();
});

test('截圖：1942-12-01 點美國的遠距交戰虛線弧', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await open(page, '1942-12-01', [-45, 42], 2.2);
  await page.waitForTimeout(800);
  await clickLngLat(page, US);
  await expect(page.getByTestId('map-conflict-arc')).toHaveCount(5); // 日美經阿留申相鄰，不畫弧
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await expect.poll(async () => Number((await page.getByTestId('map-canvas').getAttribute('data-arc-fit')) ?? 0)).toBeGreaterThan(0);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await page.mouse.move(5, 5);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-us-arcs-1942-12-01.png` });
});

test('1941-12-08：點日本 → 日本—英國相鄰（英屬緬甸接日佔印度支那）不畫弧，雙劍在開戰地點哥打巴魯；開戰事件有正式出處', async ({ page }) => {
  const f = pick(await conflictsOn(page, '1941-12-08'), 'empire-of-japan', 'united-kingdom');
  expect(f.properties.adjacent).toBe(true);
  const res = await page.request.get('/api/v1/conflicts?date=1941-12-08');
  const startId = ((await res.json()).data.featureCollection.features as { properties: { recordId: string; startEvent: { id: string } } }[])
    .find((x) => x.properties.recordId === f.properties.recordId)!.properties.startEvent.id;
  const ev = (await (await page.request.get(`/api/v1/events/${startId}`)).json()).data as { citations: { locator: string }[] };
  expect(ev.citations.length).toBeGreaterThan(0);

  await page.emulateMedia({ reducedMotion: 'reduce' });
  await open(page, '1941-12-08', [125, 25], 3);
  await clickLngLat(page, [138, 36]);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('日本');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await expect(page.locator(`[data-testid="map-conflict-arc"][data-record-id="${f.properties.recordId}"]`)).toHaveCount(0);
  const icon = page.locator(`[data-testid="map-conflict-icon"][data-record-id="${f.properties.recordId}"]`);
  await expect(icon).toHaveCount(1);
  await page.waitForTimeout(400);
  const d = await page.evaluate((id) => {
    const el = document.querySelector(`[data-testid="map-conflict-icon"][data-record-id="${id}"]`) as HTMLElement;
    const kb = (window as unknown as { __wlMap: { project: (l: [number, number]) => { x: number; y: number } } }).__wlMap.project([102.24, 6.13]);
    return Math.hypot(parseFloat(el.style.left) - kb.x, parseFloat(el.style.top) - kb.y);
  }, f.properties.recordId);
  expect(d).toBeLessThan(40); // 雙劍在哥打巴魯（容許錯開位移）
  await page.mouse.move(5, 5);
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-jp-uk-1941-12-08.png` });
});

test('截圖：1942-12-01 點英國（英德、英義畫弧，泰英短弧從美塞接到英屬印度；日英相鄰只剩哥打巴魯的雙劍）', async ({ page }) => {
  const fs = (await conflictsOn(page, '1942-12-01')).filter((x) => x.properties.regimeASlug === 'united-kingdom' || x.properties.regimeBSlug === 'united-kingdom');
  const withArc = fs.filter((x) => x.properties.arc).length;
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await open(page, '1942-12-01', [40, 40], 1.8);
  await page.waitForTimeout(800);
  await clickLngLat(page, [-1.5, 52.5]); // 英格蘭中部
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('聯合王國');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await expect(page.getByTestId('map-conflict-icon')).toHaveCount(fs.length);
  await expect(page.getByTestId('map-conflict-arc')).toHaveCount(withArc);
  await expect.poll(async () => Number((await page.getByTestId('map-canvas').getAttribute('data-arc-fit')) ?? 0)).toBeGreaterThan(0);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await page.mouse.move(5, 5);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-arcs-1942-12-01-uk.png` });
});
