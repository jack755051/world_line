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

test('§10-2／§10-4：≥1440 面板寬 400、可拖拉到 480 並記住；面板底部停在時間軸上方，時間軸全寬；padding.right＝面板寬＋16', async ({ page }) => {
  await open(page, 1440);
  await selectGermany(page);
  const sheet = page.getByTestId('regime-sheet');
  await expect.poll(async () => Math.round((await sheet.boundingBox())!.width)).toBe(400);
  const tl = (await page.locator('wl-timeline').boundingBox())!;
  const sb = (await sheet.boundingBox())!;
  expect(Math.abs(sb.y + sb.height - tl.y)).toBeLessThanOrEqual(1);
  expect(Math.round(tl.width)).toBe(1440);
  const handle = page.getByTestId('regime-sheet-resize');
  const hb = (await handle.boundingBox())!;
  await page.mouse.move(hb.x + hb.width / 2, hb.y + 300);
  await page.mouse.down();
  await page.mouse.move(hb.x - 200, hb.y + 300, { steps: 6 });
  await page.mouse.up();
  await expect.poll(async () => Math.round((await sheet.boundingBox())!.width)).toBe(480);
  expect(await page.evaluate(() => localStorage.getItem('wl.sheetWidth'))).toBe('480');
  await page.getByTestId('sovereignty-card-close').click();
  await expect(sheet).toHaveCount(0);
  await expect.poll(async () => (await padding(page)).right).toBe(0);
  await selectGermany(page);
  await expect.poll(async () => Math.round((await sheet.boundingBox())!.width)).toBe(480);
});

test('§10-2：1024–1439 面板寬 360，不可拖拉', async ({ page }) => {
  await open(page, 1024);
  await selectGermany(page);
  await expect.poll(async () => Math.round((await page.getByTestId('regime-sheet').boundingBox())!.width)).toBe(360);
  await expect(page.getByTestId('regime-sheet-resize')).toHaveCount(0);
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
