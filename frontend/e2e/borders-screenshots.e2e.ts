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
  await page.getByTestId('legend-expand').click(); // §10-3：圖例預設關閉
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
  // 亞洲第二批（東南亞殖民地與日本佔領）：關島、威克、阿留申、東南亞到荷屬東印度都在框內
  ['asia', '1942-06-01', [122, 20], 2.6],
  ['asia', '1944-10-01', [122, 20], 2.6],
  ['asia', '1945-08-15', [122, 20], 2.6],
  // 亞洲第三批（填補）：阿拉伯半島、英屬印度、婆羅洲、帝汶到新幾內亞與澳洲北部都在框內
  ['asia-fill', '1942-06-01', [98, 12], 2.7],
  ['asia-fill', '1944-06-01', [98, 12], 2.7],
  ['europe', '1945-06-01', [16, 50], 3.3],
  ['europe', '1945-09-01', [16, 50], 3.3],
] as const) {
  test(`截圖：${date} ${{ world: '全圖', us: '美國本土與屬地', asia: '亞洲太平洋', 'asia-fill': '亞洲太平洋（第三批填補）', europe: '歐洲（德國投降後）' }[name]}`, async ({ page }) => {
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

// 方案 A：1937 以前「資料不保證完整」改為日期旁的 ⓘ（可聚焦、有說明文字），首次造訪顯示一次 toast，地圖上不再有提示框
test('時間軸：1937 以前日期旁顯示 ⓘ、首次造訪 toast 一次', async ({ page }) => {
  await page.goto('/?date=1940-07-15');
  await page.evaluate(() => localStorage.removeItem('wl.incompleteToastSeen'));
  await page.goto('/?date=1913-01-01&axis=sovereignty');
  const info = page.getByTestId('timeline-incomplete-info');
  await expect(info).toBeVisible();
  await expect(info).toHaveAttribute('aria-label', '本時段資料不保證完整');
  const ib = await info.boundingBox();
  const db = await page.getByTestId('timeline-date-button').boundingBox();
  expect(ib!.x).toBeGreaterThanOrEqual(db!.x + db!.width - 1);
  expect(ib!.x - (db!.x + db!.width)).toBeLessThan(24);
  await expect(page.getByText('1937 年 7 月以前的資料不保證完整').first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('map-incomplete-period-hint')).toHaveCount(0);
  await page.goto('/?date=1920-06-15&axis=sovereignty');
  await expect(page.getByTestId('timeline-incomplete-info')).toBeVisible();
  await page.waitForTimeout(1500);
  await expect(page.getByText('1937 年 7 月以前的資料不保證完整')).toHaveCount(0);
  await page.goto('/?date=1940-07-15&axis=sovereignty');
  await expect(page.getByTestId('timeline-incomplete-info')).toHaveCount(0);
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

// 兩次大戰之間 A 批（1918-11-12～1923）：凡爾賽與各和約、繼承國、波蘇戰爭、希土戰爭、魯爾佔領
for (const [date, focus, waitConflict] of [
  ['1919-07-01', [19.5, 52.0], true], // 波蘭：波蘇戰爭、與西烏克蘭爭東加利西亞（凡爾賽簽字後）
  ['1921-04-01', [22.0, 39.6], true], // 希臘：希土戰爭（對安卡拉大國民議會政府；里加和約後兩週）
  ['1923-08-01', [10.5, 51.0], false], // 德國：法比佔領魯爾（洛桑條約簽字後）
] as const) {
  test(`截圖：${date} 歐洲與近東（兩次大戰之間 A 批）`, async ({ page }) => {
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
    if (waitConflict) await expect(page.getByTestId('sovereignty-card-conflict').first()).toBeVisible({ timeout: 40_000 });
    await page.mouse.move(5, 5);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `tmp/borders-shots/${prefix}-interwar-${date}.png` });
  });
}

// 兩次大戰之間 B 批（1924～1938）：洛迦諾與萊茵蘭撤軍、薩爾回歸、西班牙內戰、德奧合併（接二戰既有資料）
for (const [date, focus, waitConflict] of [
  ['1926-01-01', [6.95, 50.9], false], // 萊茵蘭科隆區（英軍佔領，1926-01-31 撤出）
  ['1935-03-01', [7.0, 49.3], false], // 薩爾回歸德國當天
  ['1937-06-01', [-0.8, 39.5], true], // 西班牙共和國：西班牙內戰
  ['1938-03-13', [14.5, 47.6], false], // 德奧合併當天（二戰既有紀錄）
] as const) {
  test(`截圖：${date} 歐洲與近東（兩次大戰之間 B 批）`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(`/?date=${date}&axis=sovereignty`);
    const canvas = page.getByTestId('map-canvas');
    await expect(canvas).toHaveAttribute('data-map-ready', 'true');
    await page.evaluate(() => {
      const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
      map.jumpTo({ center: [12, 45], zoom: 3.3 });
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
    if (waitConflict) await expect(page.getByTestId('sovereignty-card-conflict').first()).toBeVisible({ timeout: 40_000 });
    await page.mouse.move(5, 5);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `tmp/borders-shots/${prefix}-interwar-${date}.png` });
  });
}

// 北非、近東與冰島 1939～1945：利比亞戰役、火炬行動、突尼西亞戰役、敘黎、伊拉克、伊朗
for (const [date, focus] of [
  ['1941-07-01', [23.96, 32.0]], // 托布魯克被圍（英軍佔領區）；敘利亞戰役將結束
  ['1942-11-15', [10.17, 36.8]], // 火炬行動後，軸心國佔領突尼斯
  ['1943-06-01', [14.0, 26.0]], // 突尼西亞戰役結束：法國軍管費贊、英國軍政府
] as const) {
  test(`截圖：${date} 北非與近東（北非、近東與冰島批）`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(`/?date=${date}&axis=sovereignty`);
    const canvas = page.getByTestId('map-canvas');
    await expect(canvas).toHaveAttribute('data-map-ready', 'true');
    await page.evaluate(() => {
      const map = (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap;
      map.jumpTo({ center: [22, 32], zoom: 3.0 });
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
    await page.screenshot({ path: `tmp/borders-shots/${prefix}-nafrica-${date}.png` });
  });
}
