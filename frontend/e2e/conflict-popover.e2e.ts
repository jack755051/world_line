import { expect, test, type Page } from '@playwright/test';

/** §13 衝突小卡＋比例尺。截圖存 WL_SHOT_DIR（預設 tmp/conflict）。 */
const DIR = process.env['WL_SHOT_DIR_CONFLICT'] ?? 'tmp/conflict';
type WlMap = { project: (l: [number, number]) => { x: number; y: number }; jumpTo: (o: object) => void; getZoom: () => number };

async function openFinland(page: Page, w: number, h: number): Promise<void> {
  await page.setViewportSize({ width: w, height: h });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/?date=1939-11-30&axis=sovereignty');
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.jumpTo({ center: [27, 62], zoom: 4 }));
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
  await page.waitForTimeout(800);
  const box = (await canvas.boundingBox())!;
  const p = await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.project([25.5, 62.5]));
  await page.mouse.click(box.x + p.x, box.y + p.y);
  await expect(page.getByTestId('sovereignty-card')).toBeAttached();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  const icon = page.getByTestId('map-conflict-icon').first();
  await expect(icon).toBeVisible();
  await icon.click();
  await expect(page.getByTestId('conflict-card')).toBeVisible();
}

test('§13 1440：點 1939-11-30 蘇芬衝突 → 圖示旁 320px 小卡，面板不變；無戰役簡報；在時間線上看選取事件', async ({ page }) => {
  await openFinland(page, 1440, 900);
  const card = page.getByTestId('conflict-card');
  expect(Math.round((await card.boundingBox())!.width)).toBe(320);
  await expect(page.locator('.maplibregl-popup')).toHaveCount(1);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('芬蘭');
  await expect(page.getByTestId('conflict-card-campaign')).toHaveCount(0);
  await expect(page.getByTestId('conflict-card-location')).toHaveCount(0);
  await page.mouse.move(5, 5);
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${DIR}/1440-winter-war.png` });
  await page.getByTestId('conflict-card-timeline').click();
  await expect(page.locator('[data-testid="sovereignty-card-timeline-item"][data-selected="true"]')).toHaveCount(1);
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${DIR}/1440-winter-war-timeline.png` });
});

test('§13 390：衝突底部面板 peek 140px → half', async ({ page }) => {
  await openFinland(page, 390, 844);
  const sh = page.getByTestId('conflict-sheet');
  await expect(sh).toHaveAttribute('data-snap', 'peek');
  expect(Math.round((await sh.boundingBox())!.height)).toBe(140);
  await expect(page.getByTestId('conflict-card-start')).toHaveCount(0);
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${DIR}/390-winter-war-peek.png` });
  await page.getByTestId('conflict-sheet-handle').click();
  await expect(sh).toHaveAttribute('data-snap', 'half');
  await expect(page.getByTestId('conflict-card-start')).toBeVisible();
  await page.screenshot({ path: `${DIR}/390-winter-war-half.png` });
});

test('§13 比例尺：公里、圖例按鈕右邊、zoom<3 隱藏、戰役模式移到說明卡右邊', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/?date=1939-11-30&axis=sovereignty');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true');
  const scale = page.getByTestId('map-scale');
  await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.jumpTo({ center: [27, 62], zoom: 4.5 }));
  await expect(scale).toBeVisible();
  await expect(scale).toContainText('km');
  const area = (await page.getByTestId('map-area').boundingBox())!;
  const b = (await scale.boundingBox())!;
  expect(Math.round(b.x - area.x)).toBe(60);
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${DIR}/1440-scale.png` });
  await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.jumpTo({ zoom: 2.5 }));
  await expect(scale).toBeHidden();
});
