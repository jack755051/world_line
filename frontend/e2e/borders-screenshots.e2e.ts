import { expect, test } from '@playwright/test';

/**
 * 主權圖層試驗截圖（WL_E2E_BORDERS=1 時才跑）：五個日期，全歐視角，主權檢視，輸出到 tmp/borders-shots/。
 * 檔名前綴 WL_SHOT_PREFIX（預設 borders-app-v2）。
 */
const prefix = process.env['WL_SHOT_PREFIX'] ?? 'borders-app-v2';
test.skip(!process.env['WL_E2E_BORDERS'], '需要開發 API（5052）上的 borders-1938-1940 資料');

for (const date of ['1938-01-01', '1938-10-15', '1939-04-15', '1939-10-15', '1940-09-15']) {
  test(`截圖 ${date}`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(`/?date=${date}&axis=sovereignty`);
    const canvas = page.getByTestId('map-canvas');
    await expect(canvas).toHaveAttribute('data-map-ready', 'true');
    await expect(canvas).toHaveAttribute('data-axis', 'sovereignty');
    await page.evaluate(() => {
      const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
      map.jumpTo({ center: [16, 52], zoom: 3.55 });
    });
    await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `tmp/borders-shots/${prefix}-${date}.png` });
  });
}

test('截圖：1939-10-23 德佔波蘭資訊卡（出處收合、徽章在事件名稱下方）', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/?date=1939-10-23&axis=sovereignty');
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await page.evaluate(() => {
    const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
    map.jumpTo({ center: [16, 52], zoom: 3.55 });
  });
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
  await page.waitForTimeout(1000);
  const box = await canvas.boundingBox();
  const p = await page.evaluate(() => {
    const map = (window as unknown as { __wlMap: { project: (l: [number, number]) => { x: number; y: number } } }).__wlMap;
    return map.project([19.94, 50.06]);
  });
  await page.mouse.click((box?.x ?? 0) + p.x, (box?.y ?? 0) + p.y);
  await expect(page.getByTestId('sovereignty-card')).toBeVisible();
  await page.mouse.move(5, 5);
  await page.waitForTimeout(500);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-card-1939-10-23.png` });
});

test('截圖：展開的圖例（主權檢視只留國界說明）', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/?date=1939-10-23&axis=sovereignty');
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-map-ready', 'true');
  await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
  await expect(page.getByTestId('legend')).toHaveAttribute('data-state', 'open');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `tmp/borders-shots/${prefix}-legend-1939-10-23.png` });
});

for (const date of ['1941-12-01', '1942-11-01', '1942-12-01', '1943-07-01', '1943-10-01', '1944-10-01', '1945-05-01']) {
  test(`截圖：${date} 歐洲國界與佔領行政區（德、蘇、南歐、東南歐、法國）`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(`/?date=${date}&axis=sovereignty`);
    const canvas = page.getByTestId('map-canvas');
    await expect(canvas).toHaveAttribute('data-map-ready', 'true');
    await page.evaluate(() => {
      const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
      map.jumpTo({ center: [16, 48], zoom: 3.3 });
    });
    await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `tmp/borders-shots/${prefix}-${date}.png` });
  });
}

for (const [name, date, center, zoom] of [
  ['world', '1942-12-01', [-20, 30], 1.5],
  ['us', '1942-12-01', [-110, 40], 2.4],
  ['world', '1941-12-15', [60, 35], 1.5],
  ['asia', '1941-12-15', [118, 28], 2.6],
  ['asia', '1943-06-01', [118, 28], 2.6],
  ['asia', '1945-08-01', [118, 28], 2.6],
  ['europe', '1945-06-01', [16, 50], 3.3],
  ['europe', '1945-09-01', [16, 50], 3.3],
] as const) {
  test(`截圖：${date} ${{ world: '全圖', us: '美國本土與屬地', asia: '亞洲太平洋', europe: '歐洲（德國投降後）' }[name]}`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(`/?date=${date}&axis=sovereignty`);
    const canvas = page.getByTestId('map-canvas');
    await expect(canvas).toHaveAttribute('data-map-ready', 'true');
    await page.evaluate(([c, z]) => {
      const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
      map.jumpTo({ center: c, zoom: z });
    }, [center, zoom] as const);
    await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(0);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `tmp/borders-shots/${prefix}-${name}-${date}.png` });
  });
}

// WW1 第一批（1908～1914）：歐洲、巴爾幹與北非；點選聚焦政權後才顯示該政權的衝突雙劍
for (const [date, focus] of [
  ['1908-10-07', [16.4, 48.2]], // 奧匈（起事件＝波士尼亞併吞）
  ['1913-01-01', [33, 39]], // 鄂圖曼：第一次巴爾幹戰爭四條戰線
  ['1913-09-01', [33, 39]], // 鄂圖曼：與保加利亞的第二次戰事（到君士坦丁堡和約）
  ['1914-07-28', [16.4, 48.2]], // 奧匈：對塞爾維亞宣戰
] as const) {
  test(`截圖：${date} 歐洲、巴爾幹與北非（WW1 第一批）`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(`/?date=${date}&axis=sovereignty`);
    const canvas = page.getByTestId('map-canvas');
    await expect(canvas).toHaveAttribute('data-map-ready', 'true');
    await page.evaluate(() => {
      const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
      map.jumpTo({ center: [18, 42], zoom: 3.3 });
    });
    await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
    await page.waitForTimeout(1000);
    const box = await canvas.boundingBox();
    const p = await page.evaluate((ll) => {
      const map = (window as unknown as { __wlMap: { project: (l: [number, number]) => { x: number; y: number } } }).__wlMap;
      return map.project([ll[0], ll[1]]);
    }, focus);
    await page.mouse.click((box?.x ?? 0) + p.x, (box?.y ?? 0) + p.y);
    await expect(page.getByTestId('sovereignty-card')).toBeVisible();
    await page.mouse.move(5, 5);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `tmp/borders-shots/${prefix}-europe-${date}.png` });
  });
}

// 時間軸 1937 以前淡底的「資料不保證完整」標籤：蓋在戰區軌道上、不被軌道線穿過（Tai 2026-11-01）
test('時間軸：1937 以前「資料不保證完整」標籤在軌道之上、可讀', async ({ page }) => {
  await page.goto('/?date=1913-01-01&axis=sovereignty');
  const label = page.getByTestId('timeline-incomplete-label');
  await expect(label).toBeVisible();
  const topmost = await label.evaluate((el) => {
    // 標籤本身不吃滑鼠（pointer-events: none），量繪製順序時暫時打開
    (el as HTMLElement).style.pointerEvents = 'auto';
    (el.parentElement as HTMLElement).style.pointerEvents = 'auto';
    const r = el.getBoundingClientRect();
    const pts = [[0.5, 0.5], [0.15, 0.5], [0.85, 0.5], [0.5, 0.2], [0.5, 0.8]];
    return pts.every(([fx, fy]) => {
      const hit = document.elementFromPoint(r.left + r.width * fx, r.top + r.height * fy);
      return hit === el || el.contains(hit);
    });
  });
  expect(topmost).toBe(true);
  const bg = await label.evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(bg).not.toMatch(/rgba\(.*,\s*0\)$|transparent/);
});

// WW1 第二批（1914-08～1918-11-11）：宣戰與參戰、佔領區、布列斯特、停戰；點選聚焦政權後才顯示該政權的衝突雙劍
for (const [date, focus] of [
  ['1915-06-01', [10.5, 51.0]], // 德意志帝國：比利時、法國北部佔領區；東西兩線
  ['1916-12-01', [16.4, 48.2]], // 奧匈：塞爾維亞、蒙特內哥羅軍事總督府；羅馬尼亞戰線
  ['1918-03-04', [10.5, 51.0]], // 德意志帝國：布列斯特和約翌日，東方佔領區與新國家
  ['1918-11-11', [2.5, 47.0]], // 法國：貢比涅停戰當日
] as const) {
  test(`截圖：${date} 歐洲與近東（WW1 第二批）`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(`/?date=${date}&axis=sovereignty`);
    const canvas = page.getByTestId('map-canvas');
    await expect(canvas).toHaveAttribute('data-map-ready', 'true');
    await page.evaluate(() => {
      const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
      map.jumpTo({ center: [22, 47], zoom: 3.1 });
    });
    await expect.poll(async () => Number((await canvas.getAttribute('data-rendered-sovereignty')) ?? 0)).toBeGreaterThan(5);
    await page.waitForTimeout(1000);
    const box = await canvas.boundingBox();
    const p = await page.evaluate((ll) => {
      const map = (window as unknown as { __wlMap: { project: (l: [number, number]) => { x: number; y: number } } }).__wlMap;
      return map.project([ll[0], ll[1]]);
    }, focus);
    await page.mouse.click((box?.x ?? 0) + p.x, (box?.y ?? 0) + p.y);
    await expect(page.getByTestId('sovereignty-card')).toBeVisible();
    // 衝突 API 在這幾個日期要 8～9 秒（交戰方多、要算相鄰／弧線），等清單出現再截
    await expect(page.getByTestId('sovereignty-card-conflict').first()).toBeVisible({ timeout: 40_000 });
    await page.mouse.move(5, 5);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `tmp/borders-shots/${prefix}-ww1-${date}.png` });
  });
}
