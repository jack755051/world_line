import { expect, test, type Page } from '@playwright/test';

/** §11.2 戰役模式：入口、階段播放（不自動播放）、Esc 恢復、手機全螢幕；截圖存 WL_SHOT_DIR（預設 tmp/campaign）。 */
const DIR = process.env['WL_SHOT_DIR'] ?? 'tmp/campaign';

async function openRegime(page: Page, w: number, h: number, date: string, center: [number, number], at: [number, number]): Promise<void> {
  await page.setViewportSize({ width: w, height: h });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(`/?date=${date}&axis=sovereignty`);
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await page.evaluate((c) => (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap.jumpTo({ center: c, zoom: 4 }), center);
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
  await page.waitForTimeout(800);
  const box = (await canvas.boundingBox())!;
  const p = await page.evaluate((l) => (window as unknown as { __wlMap: { project: (l: [number, number]) => { x: number; y: number } } }).__wlMap.project(l), at);
  await page.mouse.click(box.x + p.x, box.y + p.y);
  await expect(page.getByTestId('sovereignty-card')).toBeAttached();
}
/** 等地圖畫完目前日期（data-ready-for）再截圖。 */
async function settle(page: Page): Promise<void> {
  // 網址的日期稍晚才更新：一直重讀到 data-ready-for 等於網址日期
  await expect.poll(async () => {
    const d = new URL(page.url()).searchParams.get('date');
    return !!d && (await page.getByTestId('map-area').getAttribute('data-ready-for')) === d;
  }, { timeout: 20000 }).toBe(true);
  await page.waitForTimeout(1200);
}
const mapState = (page: Page) => page.evaluate(() => {
  const m = (window as unknown as { __wlMap: { getCenter: () => { lng: number; lat: number }; getZoom: () => number; getLayer: (id: string) => unknown } }).__wlMap;
  const c = m.getCenter();
  return { lng: +c.lng.toFixed(2), lat: +c.lat.toFixed(2), zoom: +m.getZoom().toFixed(2), layers: !!m.getLayer('campaign-sites') };
});

test('§11.2 敦克爾克：英國面板 ⚔ 入口 → P1 不自動播放 → 播到最後階段 → Esc 恢復日期、視角、面板', async ({ page }) => {
  await openRegime(page, 1440, 900, '1940-05-28', [0, 51], [-1.5, 52.5]);
  const entry = page.getByTestId('campaign-entry').filter({ hasText: '敦克爾克' });
  await expect(entry).toBeVisible();
  await page.mouse.move(5, 5);
  await page.screenshot({ path: `${DIR}/1440-entry.png` });
  const before = await mapState(page);
  await entry.click();
  const card = page.getByTestId('campaign-card');
  await expect(card).toHaveAttribute('data-status', 'ready');
  await expect(card).toHaveAttribute('data-phase', '1');
  expect(Math.round((await card.boundingBox())!.width)).toBe(360);
  await expect(page.getByTestId('regime-sheet')).toBeHidden();
  await expect.poll(() => mapState(page).then((s) => s.layers)).toBe(true);
  await page.waitForTimeout(3500);
  await expect(card).toHaveAttribute('data-phase', '1'); // 不自動播放
  await settle(page);
  await page.screenshot({ path: `${DIR}/1440-dunkirk-p1.png` });
  await page.getByTestId('campaign-phase-5').click();
  await expect(card).toHaveAttribute('data-status', 'ended');
  await expect(page).toHaveURL(/date=1940-06-0/);
  await settle(page);
  await page.screenshot({ path: `${DIR}/1440-dunkirk-last.png` });
  await page.keyboard.press('Escape');
  await expect(card).toHaveCount(0);
  await expect(page).toHaveURL(/date=1940-05-28/);
  await expect(page.getByTestId('sovereignty-card')).toBeVisible();
  await expect.poll(() => mapState(page)).toEqual(before);
});

test('§11.2 播放：每 3 秒前進、暫停後停住', async ({ page }) => {
  await openRegime(page, 1440, 900, '1940-05-28', [0, 51], [-1.5, 52.5]);
  await page.getByTestId('campaign-entry').first().click();
  const card = page.getByTestId('campaign-card');
  await expect(card).toHaveAttribute('data-status', 'ready');
  await page.getByTestId('campaign-play').click();
  await expect(card).toHaveAttribute('data-phase', '2', { timeout: 4500 });
  await page.getByTestId('campaign-play').click();
  await expect(card).toHaveAttribute('data-status', 'paused');
  await page.waitForTimeout(3500);
  await expect(card).toHaveAttribute('data-phase', '2');
  await page.getByTestId('campaign-close').click();
  await expect(card).toHaveCount(0);
});

test('§11.2 閃擊波蘭：波蘭面板入口，最後階段', async ({ page }) => {
  await openRegime(page, 1440, 900, '1939-09-10', [20, 52], [21, 52.2]);
  await page.getByTestId('campaign-entry').filter({ hasText: '波蘭' }).click();
  const card = page.getByTestId('campaign-card');
  await expect(card).toHaveAttribute('data-status', 'ready');
  await page.getByTestId('campaign-phase-3').click();
  await settle(page);
  await page.screenshot({ path: `${DIR}/1440-poland-p3.png` });
});

test('§11.2 淞滬：中華民國面板入口；戰線待考證、上旬日期', async ({ page }) => {
  await openRegime(page, 1440, 900, '1937-09-01', [112, 32], [112, 30]);
  await page.getByTestId('campaign-entry').filter({ hasText: '淞滬' }).click();
  const card = page.getByTestId('campaign-card');
  await page.getByTestId('campaign-phase-2').click();
  await expect(page.getByTestId('campaign-phase-dates')).toContainText('1937 年 10 月上旬');
  await expect(page.getByTestId('campaign-fronts-note')).toBeVisible();
  await expect(card).toHaveAttribute('data-phase', '2');
  await settle(page);
  await page.screenshot({ path: `${DIR}/1440-shanghai-p2.png` });
});

test('§11.2 手機 390：全螢幕，地圖上 60vh、卡片下 40vh，頂列與時間軸隱藏', async ({ page }) => {
  await openRegime(page, 390, 844, '1940-05-28', [0, 51], [-1.5, 52.5]);
  await page.getByTestId('campaign-entry').first().click();
  const card = page.getByTestId('campaign-card');
  await expect(card).toHaveAttribute('data-status', 'ready');
  await expect(page.getByTestId('topbar')).toHaveCount(0);
  await expect(page.getByTestId('timeline-wrap')).toBeHidden();
  const b = (await page.getByTestId('campaign-anchor').boundingBox())!;
  expect(Math.round(b.y + b.height)).toBe(844);
  expect(Math.abs(b.height - 844 * 0.4)).toBeLessThan(2);
  await settle(page);
  await page.screenshot({ path: `${DIR}/390-fullscreen.png` });
  await page.getByTestId('campaign-close').click();
  await expect(page.getByTestId('topbar')).toBeVisible();
});
