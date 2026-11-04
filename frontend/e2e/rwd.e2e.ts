import { expect, test, type Page } from '@playwright/test';

/** §12 RWD：各斷點頂列不換行、年份標籤不重疊、可點擊目標 ≥44px（手機）。 */
async function open(page: Page, w: number, h = 844): Promise<void> {
  await page.setViewportSize({ width: w, height: h });
  await page.goto('/?date=1940-06-01&axis=sovereignty');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true');
}

for (const w of [360, 390, 768, 1024, 1180, 1440]) {
  test(`§12 頂列 ${w}px：單行不換行、不溢出`, async ({ page }) => {
    await open(page, w);
    const bar = page.getByTestId('topbar');
    const r = await bar.evaluate((el) => ({ h: el.getBoundingClientRect().height, sw: el.scrollWidth, cw: el.clientWidth,
      date: (() => { const d = el.querySelector('[data-testid=topbar-date]') as HTMLElement; const lh = parseFloat(getComputedStyle(d).lineHeight) || 20; return d.getBoundingClientRect().height <= Math.max(lh, 40) * 1.2; })() }));
    expect(r.h).toBe(w < 768 ? 48 : 56);
    expect(r.sw).toBeLessThanOrEqual(r.cw + 1);
    expect(r.date).toBe(true);
  });
}

test('§12 頂列手機：日期 ISO、⋯ 選單有檢視／語言／陣營外框／圖例，按鈕 ≥44px；陣營外框不再浮在地圖上', async ({ page }) => {
  await open(page, 390);
  await expect(page.getByTestId('topbar-date')).toHaveText('1940-06-01');
  await expect(page.getByTestId('camp-layer-toggle')).toHaveCount(0);
  const mb = (await page.getByTestId('topbar-menu-button').boundingBox())!;
  expect(mb.width).toBeGreaterThanOrEqual(40);
  await page.getByTestId('topbar-menu-button').click();
  await expect(page.getByTestId('topbar-menu')).toBeVisible();
  for (const id of ['axis-toggle-control', 'lang-toggle-en', 'camp-layer-toggle', 'topbar-menu-legend'])
    expect((await page.getByTestId(id).boundingBox())!.height).toBeGreaterThanOrEqual(44);
  await page.getByTestId('camp-layer-toggle').click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camp-layer', 'on');
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('topbar-menu')).toHaveCount(0);
});
