import { expect, test } from '@playwright/test';

/**
 * 戰役 P0 手感原型（/campaigns/dunkirk-1940/proto，示例資料）。
 * 跑法：WL_E2E_BORDERS=1 WL_E2E_PORT=4203 pnpm exec playwright test e2e/battle-proto.e2e.ts
 * flag 關閉的行為：BATTLE_PROTO_ENABLED = isDevMode() && BATTLE_PROTO_DEV_SWITCH（src/app/core/features.ts）。
 * production build 的 isDevMode()=false → canMatch 失敗 → 落到 not-found；單元測試涵蓋 battleProtoEnabled(false,…)。
 * 要在 e2e 內實測「關閉」：把 BATTLE_PROTO_DEV_SWITCH 暫改 false 後重跑下面「flag 關閉」那條（預設 skip）。
 */
const URL = '/campaigns/dunkirk-1940/proto';
type Dbg = { map: { getStyle: () => { sources: Record<string, unknown>; layers: { id: string }[] }; queryRenderedFeatures: (o: object) => unknown[]; project: (l: [number, number]) => { x: number; y: number } }; sources: () => string[]; layers: () => string[] };
const win = () => window as unknown as { __bpDebug?: Dbg; __wlMap?: { getStyle: () => { sources: Record<string, unknown>; layers: { id: string }[] } } };

test.describe('戰役 P0 原型', () => {
  test('進入、橫幅、符號、內插標示、資訊卡、離開不殘留', async ({ page }) => {
    await page.goto(`${URL}?date=1940-05-13&speed=4`);
    await expect(page.getByTestId('bp-map')).toHaveAttribute('data-ready', 'true');
    await expect(page.getByTestId('bp-banner')).toContainText('示例資料，非史料');
    await expect(page.getByTestId('bp-legend')).toBeVisible();

    // 4 個示例 source、單位符號畫出來
    await expect.poll(() => page.evaluate(() => win().__bpDebug?.sources().sort())).toEqual(['bp-arrows', 'bp-engagements', 'bp-fronts', 'bp-land', 'bp-theater', 'bp-units']);
    await expect.poll(() => page.evaluate(() => win().__bpDebug!.map.queryRenderedFeatures({ layers: ['bp-units-div'] }).length), { timeout: 20000 }).toBeGreaterThan(5);

    // 播放 → 出現「位置內插（推估）」
    await page.getByTestId('bp-play').click();
    await expect(page.getByTestId('bp-interp-badge')).toContainText('位置內插（推估）');
    await page.getByTestId('bp-play').click(); // 暫停

    // 鍵盤：空白鍵播放／暫停
    await page.keyboard.press('Space');
    await expect(page.getByTestId('bp-play')).toHaveAttribute('aria-pressed', 'true');
    await page.keyboard.press('Space');
    await expect(page.getByTestId('bp-play')).toHaveAttribute('aria-pressed', 'false');

    // 點單位 → 資訊卡
    const pt = await page.evaluate(() => {
      const f = win().__bpDebug!.map.queryRenderedFeatures({ layers: ['bp-units-div'] })[0] as { geometry: { coordinates: [number, number] } };
      return win().__bpDebug!.map.project(f.geometry.coordinates);
    });
    const box = (await page.getByTestId('bp-map').boundingBox())!;
    await page.mouse.click(box.x + pt.x, box.y + pt.y);
    await expect(page.getByTestId('bp-card')).toBeVisible();
    await expect(page.getByTestId('bp-card')).toContainText('示例');

    // 離開 → 回主地圖，不殘留 bp-* source/layer，除錯 hook 清除
    await page.goto('/');
    await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true');
    const left = await page.evaluate(() => {
      const w = win();
      const st = w.__wlMap!.getStyle();
      return { hook: w.__bpDebug === undefined, sources: Object.keys(st.sources).filter((s) => s.startsWith('bp-')), layers: st.layers.map((l) => l.id).filter((l) => l.startsWith('bp-')) };
    });
    expect(left).toEqual({ hook: true, sources: [], layers: [] });
  });

  test('SPA 內離開（回主地圖）也清掉 bp-*', async ({ page }) => {
    await page.goto(URL);
    await expect(page.getByTestId('bp-map')).toHaveAttribute('data-ready', 'true');
    await page.evaluate(() => { history.pushState({}, '', '/version'); window.dispatchEvent(new PopStateEvent('popstate')); });
    await expect.poll(() => page.evaluate(() => win().__bpDebug === undefined)).toBe(true);
  });

  test('單步前後與日期寫入網址', async ({ page }) => {
    await page.goto(`${URL}?date=1940-05-13`);
    await expect(page.getByTestId('bp-map')).toHaveAttribute('data-ready', 'true');
    await page.getByTestId('bp-next').click();
    await expect(page.getByTestId('bp-date')).toHaveText('1940-05-20', { timeout: 5000 });
    await expect.poll(() => new URL(page.url()).searchParams.get('date')).toBe('1940-05-20');
  });

  test.skip('flag 關閉 → 進 not-found（需把 BATTLE_PROTO_DEV_SWITCH 改 false）', async ({ page }) => {
    await page.goto(URL);
    await expect(page.getByTestId('not-found-page')).toBeVisible();
    await expect(page.getByTestId('bp-banner')).toHaveCount(0);
  });
});
