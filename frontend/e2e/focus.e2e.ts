import { expect, test, type Page } from '@playwright/test';

/**
 * 政權聚焦＋側邊面板（Tai 2026-10-31）：點政權 → 地圖飛到該政權當前領土、置於面板左側可見區中央；
 * 其他地方蓋半透明紙色並模糊；政權資訊在右側滑出的面板（窄螢幕在底部）。點空白處、關閉、Esc、換日期恢復。
 * 需要開發 API（5052），以 `WL_E2E_BORDERS=1 WL_E2E_PORT=4201` 執行；不使用 mock，不寫入資料。
 */
test.skip(!process.env['WL_E2E_BORDERS'], '需要開發 API（5052）上的 borders 資料');
const prefix = process.env['WL_SHOT_PREFIX'] ?? 'borders-app-v3';
type WlMap = { jumpTo: (o: object) => void; project: (l: [number, number]) => { x: number; y: number }; getZoom: () => number };

async function open(page: Page, date: string): Promise<void> {
  await page.goto(`/?date=${date}&axis=sovereignty`);
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.jumpTo({ center: [16, 50], zoom: 3.4 }));
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
  await page.waitForTimeout(300);
}
async function clickLngLat(page: Page, lngLat: [number, number]): Promise<void> {
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  const box = (await page.getByTestId('map-canvas').boundingBox())!;
  const p = await page.evaluate((ll) => (window as unknown as { __wlMap: WlMap }).__wlMap.project(ll), lngLat);
  await page.mouse.click(box.x + p.x, box.y + p.y);
}
const project = (page: Page, ll: [number, number]) => page.evaluate((l) => (window as unknown as { __wlMap: WlMap }).__wlMap.project(l), ll);

const BERLIN: [number, number] = [13.4, 52.5];
const KRAKOW: [number, number] = [19.94, 50.06];

test('點德國 → 飛到德國、置於面板左側可見區中央；遮罩模糊其他地方；右側面板滑入；點空白處恢復', async ({ page }) => {
  await open(page, '1939-10-23');
  const canvas = page.getByTestId('map-canvas');
  const mask = page.getByTestId('map-focus-mask');
  await expect(mask).toHaveAttribute('data-active', 'false');
  const zoom0 = await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.getZoom());

  await clickLngLat(page, BERLIN);
  const sheet = page.getByTestId('regime-sheet');
  await expect(sheet).toHaveAttribute('data-state', 'open');
  await expect(sheet).toHaveAttribute('data-side', 'right');
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('德意志國');
  await expect(page.getByTestId('regime-sheet-description')).toContainText('Deutsches Reich');
  await expect(canvas).not.toHaveAttribute('data-focus-record', '');
  await expect(mask).toHaveAttribute('data-active', 'true');
  await expect(canvas).toHaveAttribute('data-camera', 'idle');
  // 遮罩：模糊＋半透明，clip-path 挖空被選政權
  const style = await mask.evaluate((el) => ({ f: getComputedStyle(el).backdropFilter, c: (el as HTMLElement).style.clipPath }));
  expect(style.f).toContain('blur');
  expect(style.c).toMatch(/^path\(evenodd/);
  // 置中：柏林落在面板左側的可見區內、大致居中
  const area = (await page.getByTestId('map-area').boundingBox())!;
  const sbox = (await sheet.boundingBox())!;
  const p = await project(page, BERLIN);
  expect(p.x).toBeLessThan(sbox.x - area.x);
  expect(Math.abs(p.x - (sbox.x - area.x) / 2)).toBeLessThan((sbox.x - area.x) * 0.3);
  expect(await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.getZoom())).toBeGreaterThan(zoom0);

  // 點空白處（北海）：面板滑出、遮罩取消、飛回原視角
  await clickLngLat(page, [3, 56]);
  await expect(sheet).toHaveCount(0);
  await expect(mask).toHaveAttribute('data-active', 'false');
  await expect(canvas).toHaveAttribute('data-camera', 'idle');
  expect(Math.abs((await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.getZoom())) - zoom0)).toBeLessThan(0.05);
});

test('換政權時面板內容直接換；點衝突圖示 → 衝突卡也在面板內、仍聚焦原政權；Esc 關閉；換日期恢復', async ({ page }) => {
  await open(page, '1939-09-15');
  await clickLngLat(page, [21.01, 52.23]); // 華沙
  const sheet = page.getByTestId('regime-sheet');
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('波蘭');
  const rec = await page.getByTestId('map-canvas').getAttribute('data-focus-record');
  await page.getByTestId('map-conflict-icon').first().click();
  await expect(sheet.getByTestId('conflict-card')).toBeVisible();
  await expect(page.getByTestId('conflict-card-title')).toContainText('—');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-focus-record', rec!);
  await page.keyboard.press('Escape');
  await expect(sheet).toHaveCount(0);
  await expect(page.getByTestId('map-focus-mask')).toHaveAttribute('data-active', 'false');

  await clickLngLat(page, BERLIN);
  await expect(sheet).toHaveAttribute('data-state', 'open');
  await page.getByTestId('timeline-date-input').fill('1939-10-23');
  await page.getByTestId('timeline-date-input').press('Enter');
  await expect(sheet).toHaveCount(0);
  await expect(page.getByTestId('map-focus-mask')).toHaveAttribute('data-active', 'false');
});

test('面板內：相關衝突（與地圖雙劍同步、點項目切到衝突詳情、可返回）；事件時間線（出處／查證徽章、點日期跳過去並重新聚焦）', async ({ page }) => {
  await open(page, '1939-09-20');
  await clickLngLat(page, [21.01, 52.23]); // 華沙：德—波、蘇—波
  const sheet = page.getByTestId('regime-sheet');
  await expect(sheet).toHaveAttribute('data-state', 'open');
  const items = page.getByTestId('sovereignty-card-conflict');
  const icons = page.getByTestId('map-conflict-icon');
  await expect(icons).toHaveCount(2);
  await expect(items).toHaveCount(2);
  // 雙劍在蒙版之上：圖示中心點到的元素就是圖示本身
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  const topIsIcon = await icons.first().evaluate((el) => {
    const r = el.getBoundingClientRect();
    return el.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2));
  });
  expect(topIsIcon).toBe(true);
  await items.first().click();
  await expect(sheet.getByTestId('conflict-card')).toBeVisible();
  await expect(icons).toHaveCount(2);
  await page.getByTestId('regime-sheet-back').click();
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('波蘭');

  // 時間線：德國 1939-10-23，事件有已查證／待查證徽章；點 1939-09-01 跳過去，德國仍聚焦
  await open(page, '1939-10-23');
  await clickLngLat(page, BERLIN);
  const tl = page.getByTestId('sovereignty-card-timeline-item');
  await expect.poll(() => tl.count()).toBeGreaterThan(5);
  await expect(page.getByTestId('sovereignty-card-timeline').getByTestId('sovereignty-card-timeline-verified').first()).toBeVisible();
  await expect(page.getByTestId('sovereignty-card-timeline').getByTestId('sovereignty-card-timeline-pending').first()).toBeVisible();
  await expect(tl.locator('xpath=self::*[@data-when="now"]')).toHaveCount(1);
  await page.getByTestId('sovereignty-card-timeline-jump').filter({ hasText: '1939-09-01' }).first().click();
  await expect(page).toHaveURL(/date=1939-09-01/);
  await expect(sheet).toHaveAttribute('data-state', 'open');
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('德意志國');
  await expect(page.getByTestId('map-focus-mask')).toHaveAttribute('data-active', 'true');
});

test('減少動態：面板直接出現（不播滑入動畫、motion 不改元素樣式），鏡頭直接跳到政權', async ({ page }) => {
  // 版面最小寬度 1024px（--wl-min-width），實際不會出現 < 640px 的窄版；底部面板只在單元測試驗
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await open(page, '1939-10-23');
  await clickLngLat(page, BERLIN);
  const sheet = page.getByTestId('regime-sheet');
  await expect(sheet).toHaveAttribute('data-state', 'open');
  await expect(sheet).toHaveAttribute('data-side', 'right');
  expect(await sheet.evaluate((el) => (el as HTMLElement).style.transform)).toBe('');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  const area = (await page.getByTestId('map-area').boundingBox())!;
  const sbox = (await sheet.boundingBox())!;
  expect((await project(page, BERLIN)).x).toBeLessThan(sbox.x - area.x);
});

for (const [name, ll] of [['germany', BERLIN], ['poland', KRAKOW]] as const) {
  test(`截圖：1939-10-23 點${name === 'germany' ? '德國' : '波蘭（德佔波蘭軍事管理）'}的聚焦效果`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await open(page, '1939-10-23');
    await page.waitForTimeout(800);
    await clickLngLat(page, ll);
    await expect(page.getByTestId('regime-sheet')).toHaveAttribute('data-state', 'open');
    await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
    await page.mouse.move(5, 5);
    await page.waitForTimeout(800);
    await page.screenshot({ path: `tmp/borders-shots/${prefix}-focus-1939-10-23-${name}.png` });
  });
}
