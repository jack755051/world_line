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

test('1942-12-01：平時沒有虛線弧；點美國 → 與德、義、羅、保、匈、日的交戰都畫虛線弧，雙劍在弧線中點，在聚焦遮罩上可見；關閉就隱藏', async ({ page }) => {
  await open(page, '1942-12-01', [-45, 42], 2.2);
  const arcs = page.getByTestId('map-conflict-arc');
  await expect(arcs).toHaveCount(0);

  await clickLngLat(page, US);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('美利堅');
  await expect(page.getByTestId('map-focus-mask')).toHaveAttribute('data-active', 'true');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await expect(arcs).toHaveCount(6);
  await expect(page.getByTestId('map-conflict-icon')).toHaveCount(6);

  // 弧線在遮罩之上（DOM 順序在遮罩之後、同一堆疊層），且雙劍中心＝弧線中點（取樣點 24/48）
  const check = await page.evaluate(() => {
    const mask = document.querySelector('[data-testid="map-focus-mask"]')!;
    const svg = document.querySelector('[data-testid="map-conflict-arcs"]')!;
    const after = !!(mask.compareDocumentPosition(svg) & Node.DOCUMENT_POSITION_FOLLOWING);
    const out: { id: string; dx: number; dy: number }[] = [];
    for (const line of document.querySelectorAll('[data-testid="map-conflict-arc"]')) {
      const id = line.getAttribute('data-record-id')!;
      const pts = line.getAttribute('points')!.split(' ').map((s) => s.split(',').map(Number));
      const icon = document.querySelector(`[data-testid="map-conflict-icon"][data-record-id="${id}"]`) as HTMLElement;
      const mid = pts[Math.floor(pts.length / 2)];
      out.push({ id, dx: Math.abs(parseFloat(icon.style.left) - mid[0]), dy: Math.abs(parseFloat(icon.style.top) - mid[1]) });
    }
    return { after, dash: getComputedStyle(document.querySelector('[data-testid="map-conflict-arc"]')!).strokeDasharray, out };
  });
  expect(check.after).toBe(true);
  expect(check.dash).not.toBe('none');
  for (const o of check.out) {
    expect(o.dx).toBeLessThan(2);
    expect(o.dy).toBeLessThan(2);
  }

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

test('截圖：1942-12-01 點美國的遠距交戰虛線弧', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await open(page, '1942-12-01', [-45, 42], 2.2);
  await page.waitForTimeout(800);
  await clickLngLat(page, US);
  await expect(page.getByTestId('map-conflict-arc')).toHaveCount(6);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  // 面板開著時把鏡頭拉遠，讓大西洋上的弧線與歐洲端點都在畫面內
  await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.jumpTo({ center: [-40, 40], zoom: 1.9 }));
  await page.mouse.move(5, 5);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-us-arcs-1942-12-01.png` });
});
