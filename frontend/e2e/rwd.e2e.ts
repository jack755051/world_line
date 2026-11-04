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

for (const w of [360, 390, 768, 1024, 1440]) {
  test(`§12 時間軸 ${w}px：年份標籤不重疊、不超出滑桿；手機兩行 56px、每 10 年`, async ({ page }) => {
    await open(page, w);
    const tl = page.getByTestId('timeline');
    const boxes = await page.locator('[data-testid=timeline-year-label], [data-testid=timeline-start-label]').evaluateAll((els) =>
      els.map((e) => { const r = e.getBoundingClientRect(); return { l: r.left, r: r.right, t: e.textContent?.trim() ?? '' }; }).sort((a, b) => a.l - b.l));
    expect(boxes.length).toBeGreaterThan(1);
    for (let i = 1; i < boxes.length; i++) expect(boxes[i].l, `${boxes[i - 1].t} / ${boxes[i].t}`).toBeGreaterThanOrEqual(boxes[i - 1].r + 2);
    expect(boxes[boxes.length - 1].r).toBeLessThanOrEqual(w);
    if (w < 768) {
      expect(Math.round((await tl.boundingBox())!.height)).toBe(56);
      const years = (await page.getByTestId('timeline-year-label').allTextContents()).map((t) => +t.trim());
      expect(years.every((y) => y % 10 === 0)).toBe(true);
      await expect(page.getByTestId('timeline-date-input')).toHaveValue('1940-06');
      expect(Math.round((await page.getByTestId('timeline-handle').boundingBox())!.width)).toBe(24);
    }
  });
}

test('§12 時間軸手機：拖動滑桿時把手上方浮出 YYYY-MM', async ({ page }) => {
  await open(page, 390);
  const h = (await page.getByTestId('timeline-handle').boundingBox())!;
  await page.mouse.move(h.x + h.width / 2, h.y + h.height / 2);
  await page.mouse.down();
  await page.mouse.move(h.x - 60, h.y + h.height / 2, { steps: 4 });
  await expect(page.getByTestId('timeline-drag-tip')).toHaveText(/^\d{4}-\d{2}$/);
  await page.mouse.up();
  await expect(page.getByTestId('timeline-drag-tip')).toHaveCount(0);
});

test('§12 時間軸手機：年份標籤整個在時間軸內（不被切掉）', async ({ page }) => {
  await open(page, 390);
  const tl = (await page.getByTestId('timeline').boundingBox())!;
  for (const b of await page.getByTestId('timeline-year-label').evaluateAll((els) => els.map((e) => e.getBoundingClientRect().bottom)))
    expect(b).toBeLessThanOrEqual(tl.y + tl.height);
});

type WlMap = { jumpTo(o: unknown): void; project(ll: [number, number]): { x: number; y: number }; getPadding(): { bottom: number } };
async function selectGermany(page: Page): Promise<void> {
  await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.jumpTo({ center: [10.5, 51], zoom: 4 }));
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
  await page.waitForTimeout(400);
  const box = (await page.getByTestId('map-canvas').boundingBox())!;
  const p = await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.project([10.5, 51]));
  await page.mouse.click(box.x + p.x, box.y + p.y);
  await expect(page.getByTestId('sovereignty-card-title')).toContainText('德意志國');
}

test('§12 政權面板手機：點國家開到 peek 120px；拖把手（可點範圍 44px）往上放開吸附到最近一段；padding.bottom＝面板高；面板停在時間軸上方', async ({ page }) => {
  await open(page, 390);
  await selectGermany(page);
  const sheet = page.getByTestId('regime-sheet');
  await expect(sheet).toHaveAttribute('data-state', 'open');
  await expect.poll(async () => Math.round((await sheet.boundingBox())!.height)).toBe(120);
  const handle = (await page.getByTestId('regime-sheet-snap').boundingBox())!;
  expect(Math.round(handle.height)).toBe(44);
  await page.mouse.move(handle.x + handle.width / 2, handle.y + 20);
  await page.mouse.down();
  await page.mouse.move(handle.x + handle.width / 2, handle.y - 280, { steps: 8 });
  expect(Math.round((await sheet.boundingBox())!.height)).toBeGreaterThan(300); // 跟著手指
  await page.mouse.up();
  await expect(page.getByTestId('regime-sheet-snap')).toHaveAttribute('data-snap', 'half');
  await expect.poll(async () => Math.round((await sheet.boundingBox())!.height)).toBe(422);
  await expect.poll(async () => Math.round((await page.evaluate(() => (window as unknown as { __wlMap: WlMap }).__wlMap.getPadding())).bottom)).toBeGreaterThanOrEqual(422);
  const tl = (await page.getByTestId('timeline').boundingBox())!;
  const sb = (await sheet.boundingBox())!;
  expect(Math.abs(sb.y + sb.height - tl.y)).toBeLessThanOrEqual(1);
});

test('§12 L1 圖例手機：沒有 ⓘ 與圖例分頁；⋯ 選單「圖例」開獨立 bottom sheet（≤60vh、兩欄、色票 20px、13px）；往下滑或點地圖關閉；選政權時也能開', async ({ page }) => {
  await open(page, 390);
  await expect(page.getByTestId('legend-expand')).toHaveCount(0);
  await page.getByTestId('topbar-menu-button').click();
  await page.getByTestId('topbar-menu-legend').click();
  const ls = page.getByTestId('legend-sheet');
  await expect(ls).toBeVisible();
  expect((await ls.boundingBox())!.height).toBeLessThanOrEqual(844 * 0.6 + 1);
  const sw = (await page.getByTestId('legend-sov-fill').locator('.sw').boundingBox())!;
  expect(Math.round(sw.width)).toBe(20);
  expect(await page.getByTestId('legend-sov-fill').evaluate((e) => getComputedStyle(e).fontSize)).toBe('13px');
  expect(await page.getByTestId('legend-sov-fill').evaluate((e) => getComputedStyle(e.parentElement!).gridTemplateColumns.split(' ').length)).toBe(2);
  // 往下滑關閉
  const h = (await page.getByTestId('legend-sheet-handle').boundingBox())!;
  await page.mouse.move(h.x + h.width / 2, h.y + 20);
  await page.mouse.down();
  await page.mouse.move(h.x + h.width / 2, h.y + 140, { steps: 6 });
  await page.mouse.up();
  await expect(ls).toHaveCount(0);
  // 點地圖關閉；選了政權也能開，不是政權面板的分頁
  await page.getByTestId('topbar-menu-button').click();
  await page.getByTestId('topbar-menu-legend').click();
  await expect(ls).toBeVisible();
  await page.mouse.click(195, 80);
  await expect(ls).toHaveCount(0);
  await selectGermany(page);
  await expect(page.getByTestId('sheet-tab-legend')).toHaveCount(0);
  await page.getByTestId('topbar-menu-button').click();
  await page.getByTestId('topbar-menu-legend').click();
  await expect(ls).toBeVisible();
});

test('§12 手機選取政權：政權名字一定顯示，而且在底部面板上方（peek 與 half）', async ({ page }) => {
  await open(page, 390);
  await selectGermany(page);
  const sheet = page.getByTestId('regime-sheet');
  for (const snap of ['peek', 'half']) {
    if (snap === 'half') await page.getByTestId('regime-sheet-snap').click();
    await expect(page.getByTestId('regime-sheet-snap')).toHaveAttribute('data-snap', snap);
    await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-camera', 'idle');
    await page.waitForTimeout(600);
    const name = page.getByTestId('map-selected-label').filter({ hasText: '德意志國' });
    await expect(name).toHaveCount(1);
    await expect(name).toBeVisible();
    const nb = (await name.boundingBox())!;
    const sb = (await sheet.boundingBox())!;
    expect(nb.y + nb.height, snap).toBeLessThanOrEqual(sb.y);
    expect(nb.y).toBeGreaterThanOrEqual(48);
  }
});
