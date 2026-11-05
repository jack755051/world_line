import { expect, test, type Page } from '@playwright/test';

/**
 * UI 改版（ARCHITECTURE.md §10）：政權面板寬度與拖拉、圖例浮動面板、面板停在底部時間軸上方（時間軸維持全寬）。
 * 需要開發 API（5052），以 `WL_E2E_BORDERS=1 WL_E2E_PORT=4201` 執行；不使用 mock，不寫入資料。
 */
test.skip(!process.env['WL_E2E_BORDERS'], '需要開發 API（5052）上的 borders 資料');
type WlMap = { jumpTo: (o: object) => void; project: (l: [number, number]) => { x: number; y: number }; getPadding: () => { left: number; right: number } };

async function open(page: Page, w: number): Promise<void> {
  await page.setViewportSize({ width: w, height: 900 });
  await page.goto('/?date=1940-06-01&axis=sovereignty');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true');
  await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.jumpTo({ center: [12, 50], zoom: 4 }));
  await expect.poll(async () => Number((await page.getByTestId('map-canvas').getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
}
async function selectGermany(page: Page): Promise<void> {
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  const box = (await page.getByTestId('map-canvas').boundingBox())!;
  const p = await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.project([10.5, 51]));
  await page.mouse.click(box.x + p.x, box.y + p.y);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('德意志國');
}
const padding = (page: Page) => page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.getPadding());

test('§10 v2 W1／§10-4：≥1440 面板寬 432、不能拖拉；面板底部停在時間軸上方，時間軸全寬；padding.right＝面板寬＋16', async ({ page }) => {
  await open(page, 1440);
  await selectGermany(page);
  const sheet = page.getByTestId('regime-sheet');
  await expect.poll(async () => Math.round((await sheet.boundingBox())!.width)).toBe(432);
  const tl = (await page.locator('wl-timeline').boundingBox())!;
  const sb = (await sheet.boundingBox())!;
  expect(Math.abs(sb.y + sb.height - tl.y)).toBeLessThanOrEqual(1);
  expect(Math.round(tl.width)).toBe(1440);
  await expect(page.getByTestId('regime-sheet-resize')).toHaveCount(0);
  // padding 以 easeTo 200ms 套用：等動畫結束再讀
  await expect.poll(async () => (await padding(page)).right).toBeGreaterThanOrEqual(448);
  await page.getByTestId('sovereignty-card-close').click();
  await expect(sheet).toHaveCount(0);
  await expect.poll(async () => (await padding(page)).right).toBe(0);
});

test('§10 v2 W1＋§12 P1：1024–1199 面板寬 360 疊在地圖上（padding.right 0）、1200–1439 寬 384，不能拖拉', async ({ page }) => {
  await open(page, 1024);
  await selectGermany(page);
  await expect.poll(async () => Math.round((await page.getByTestId('regime-sheet').boundingBox())!.width)).toBe(360);
  await expect(page.getByTestId('regime-sheet-resize')).toHaveCount(0);
  await open(page, 1280);
  await selectGermany(page);
  await expect.poll(async () => Math.round((await page.getByTestId('regime-sheet').boundingBox())!.width)).toBe(384);
});

test('§10-3：圖例預設關閉；左下按鈕展開 240px 浮動面板、padding.left＝264；Esc 與點地圖空白處收起', async ({ page }) => {
  await open(page, 1440);
  const legend = page.getByTestId('legend');
  await expect(legend).toHaveAttribute('data-state', 'collapsed');
  const btn = (await page.getByTestId('legend-expand').boundingBox())!;
  expect(Math.round(btn.width)).toBe(40);
  const area = (await page.getByTestId('map-area').boundingBox())!;
  expect(Math.round(btn.x - area.x)).toBe(12);
  expect(Math.round(area.y + area.height - (btn.y + btn.height))).toBe(12);
  await page.getByTestId('legend-expand').click();
  await expect(legend).toHaveAttribute('data-state', 'open');
  const panel = (await page.getByTestId('legend-panel').boundingBox())!;
  expect(Math.round(panel.width)).toBe(240);
  expect(panel.y + panel.height).toBeLessThanOrEqual(btn.y);
  await expect.poll(async () => (await padding(page)).left).toBe(264);
  await page.keyboard.press('Escape');
  await expect(legend).toHaveAttribute('data-state', 'collapsed');
  await page.getByTestId('legend-expand').click();
  await expect(legend).toHaveAttribute('data-state', 'open');
  // 點海上空白處（北大西洋，避開左下圖例面板）
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  const p = await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.project([-12, 57]));
  const box = (await page.getByTestId('map-canvas').boundingBox())!;
  await page.mouse.click(box.x + p.x, box.y + p.y);
  await expect(legend).toHaveAttribute('data-state', 'collapsed');
  await expect.poll(async () => (await padding(page)).left).toBe(0);
});

test('出處文字不被左下 ⓘ 圖例按鈕蓋住（1440、1024）', async ({ page }) => {
  for (const w of [1440, 1024]) {
    await open(page, w);
    const btn = (await page.getByTestId('legend-expand').boundingBox())!;
    const attrib = (await page.locator('.maplibregl-ctrl-attrib').boundingBox())!;
    const overlap = attrib.x < btn.x + btn.width && attrib.x + attrib.width > btn.x && attrib.y < btn.y + btn.height && attrib.y + attrib.height > btn.y;
    expect(overlap).toBe(false);
  }
});

test('首都名不被面板或蒙版邊緣切到：選取 1940 德意志國（1024）時一般層不畫其他首都名；未選取時首都名不在面板、圖例底下', async ({ page }) => {
  type M = { queryRenderedFeatures: (o: object) => { geometry: { coordinates: [number, number] }; properties: Record<string, string> }[]; project: (l: [number, number]) => { x: number; y: number }; getContainer: () => HTMLElement };
  const capitalsUnder = () => page.evaluate(() => {
    const m = (window as unknown as { __wlMap: M }).__wlMap;
    const cr = m.getContainer().getBoundingClientRect();
    const rects = ['wl-regime-sheet [data-testid="regime-sheet"]', '[data-testid="legend"]'].map((s) => document.querySelector(s)?.getBoundingClientRect()).filter((r) => r && r.width) as DOMRect[];
    const ctx = document.createElement('canvas').getContext('2d')!;
    ctx.font = '11px sans-serif';
    const bad: string[] = [];
    const fs = m.queryRenderedFeatures({ layers: ['capital-label'] });
    for (const f of fs) {
      const p = m.project(f.geometry.coordinates);
      const x = p.x + cr.left, y = p.y + cr.top, w = ctx.measureText(f.properties['label'] ?? '').width + 8;
      // 名字在圓點左或右（碰撞時翻邊）：兩側都會壓到面板／圖例、或圓點本身在底下，就算被擋住
      const hit = (l: number, r2: number) => rects.some((r) => l < r.right && r2 > r.left && y - 8 < r.bottom && y + 8 > r.top);
      const dotUnder = rects.some((r) => x >= r.left && x <= r.right && y >= r.top && y <= r.bottom);
      if (dotUnder || (hit(x - w, x) && hit(x, x + w))) bad.push(f.properties['label']);
    }
    return { n: fs.length, bad };
  });
  await open(page, 1024);
  await page.getByTestId('legend-expand').click();
  await page.waitForTimeout(800);
  expect((await capitalsUnder()).bad).toEqual([]);
  await page.getByTestId('legend-expand').click();
  await selectGermany(page);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await page.waitForTimeout(800);
  expect((await capitalsUnder()).n).toBe(0);
  await expect(page.getByTestId('map-selected-label').filter({ hasText: '柏林' })).toHaveCount(1);
});

test('§10：政權面板標頭顯示首都', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/?date=1940-06-01&axis=sovereignty');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true');
  await selectGermany(page);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('德意志國');
  await expect(page.getByTestId('regime-sheet-capital')).toHaveText('首都・柏林');
});
