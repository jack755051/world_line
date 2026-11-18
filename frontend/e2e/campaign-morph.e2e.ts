import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { expect, test, type Page, type Route } from '@playwright/test';

/**
 * §19.2.4 C2b：GSAP timeline 階段播放＋疆界漸變。所有 /api 與 /healthz 都用 route 攔截回測試資料——不連任何既有 API 或資料庫。
 * 測試資料只為驗證 UI，不是史料：政權多邊形是方框（隨日期變寬／分裂），名稱與 id 都標「測試」。
 * - T（測試政權甲）：每階段換一筆紀錄、方框逐步變寬 → morph。
 * - S（測試政權乙）：1940-06-01 起分裂成兩塊 → 拓撲不相容，退回交叉淡入淡出。
 * - N（測試政權丙）：幾何無來源（sourceId=null）→ 無出處，任何時候都不該畫出來。
 * 截圖存 WL_SHOT_DIR（預設 tmp/c2b-shots）；fps 量測寫到 WL_PERF_OUT（預設 tmp/c2b-fps.json）。
 */
const DIR = process.env['WL_SHOT_DIR'] ?? 'tmp/c2b-shots';
const PERF_OUT = process.env['WL_PERF_OUT'] ?? 'tmp/c2b-fps.json';
const staticCampaign = JSON.parse(readFileSync('public/campaigns/dunkirk_1940.json', 'utf8'));
const apiCampaign = {
  ...staticCampaign,
  phases: [...staticCampaign.phases, { seq: 6, key: 'p6', name_zh: '（測試資料）P6', start: '1940-06-04', end: '1940-06-05', summary_zh: '（測試資料，非史料）', summary_verified: false, sources: [] }],
};
const env = (data: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify({ statusCode: 200, message: 'ok', data }) });
const period = { start: '1939-09-01', end: null };
const geom = (sourceId: string | null) => ({ sourceId, sourceTitle: '測試', publisher: '測試', sourceLicenseCode: null, locator: '-', geometryLicense: 'test', attribution: null, ohmRelationId: null, ohmVersion: null, ohmFetchedAt: null, ohmStartRaw: null, ohmEndRaw: null, flags: null });
const ring = (x0: number, y0: number, x1: number, y1: number) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]];
const feature = (rec: string, regimeId: string, geometry: object, sourceId: string | null) => ({
  type: 'Feature', id: rec, geometry,
  properties: { recordId: rec, regimeId, regimeSlug: `test-${regimeId}`, layerStatus: 'established', validPeriod: period, startEvent: null, endEvent: null, geometry: geom(sourceId), note: '測試資料，非史料' },
});
const sovereignty = (date: string) => {
  const d = Math.round((Date.parse(date) - Date.parse('1940-05-26')) / 86_400_000);
  const split = d >= 6;
  return {
    date,
    featureCollection: {
      type: 'FeatureCollection',
      features: [
        feature(`test-T-${d}`, 'test-T', { type: 'Polygon', coordinates: [ring(1.9, 50.55, 2.3 + 0.08 * d, 50.95)] }, 'test-src'),
        feature(`test-S-${split ? 'b' : 'a'}`, 'test-S', split
          ? { type: 'MultiPolygon', coordinates: [[ring(2.55, 50.5, 2.75, 50.7)], [ring(2.85, 50.8, 3.05, 51.0)]] }
          : { type: 'Polygon', coordinates: [ring(2.55, 50.5, 3.05, 51.0)] }, 'test-src'),
        feature('test-N', 'test-N', { type: 'Polygon', coordinates: [ring(1.8, 51.05, 2.4, 51.25)] }, null),
      ],
    },
  };
};

async function mockApi(page: Page): Promise<void> {
  await page.route('**/healthz', (r) => r.fulfill(env({ status: 'Healthy', checks: [] })));
  await page.route('**/api/v1/**', async (r: Route) => {
    const u = new URL(r.request().url());
    const p = u.pathname.replace('/api/v1', '');
    if (p.startsWith('/campaigns/')) return r.fulfill(env(apiCampaign));
    if (p === '/sovereignty') return r.fulfill(env(sovereignty(u.searchParams.get('date') ?? '1940-05-26')));
    return r.fulfill(env([]));
  });
}

type Fc = { features: { properties: Record<string, unknown> }[] };
const sourceData = (page: Page, id: string) => page.evaluate(async (sid) => {
  const m = (window as unknown as { __wlCampaignMap: { getSource: (s: string) => { getData: () => Promise<unknown> } } }).__wlCampaignMap;
  return (await m.getSource(sid).getData()) as Fc;
}, id);

async function open(page: Page, width: number, height: number, reduced: boolean): Promise<void> {
  await page.setViewportSize({ width, height });
  await page.emulateMedia({ reducedMotion: reduced ? 'reduce' : 'no-preference' });
  await mockApi(page);
  await page.goto('/campaign/dunkirk_1940?phase=1');
  await expect(page.getByTestId('campaign-map')).toHaveAttribute('data-map-ready', 'true');
  await expect(page.getByTestId('campaign-map')).toHaveAttribute('data-borders', '1940-05-26');
}
/** 停在階段時：沒有任何「推估過渡」要素，只剩有出處的疆界。 */
async function expectSettled(page: Page): Promise<void> {
  await expect(page.getByTestId('campaign-map')).toHaveAttribute('data-transition', 'none');
  await expect(page.getByTestId('campaign-legend-transitional')).toHaveCount(0);
  await expect(page.getByText('推估過渡')).toHaveCount(0);
  expect((await sourceData(page, 'campaign-sov-tx')).features).toHaveLength(0);
  const stable = await sourceData(page, 'campaign-sov');
  expect(stable.features.length).toBeGreaterThan(0);
  for (const f of stable.features) {
    expect(f.properties['transitional']).toBeUndefined();
    expect((f.properties['geometry'] as { sourceId: string | null }).sourceId).toBeTruthy();
  }
}

test('§19.2.4 不自動播放；空白鍵播放→漸變（推估過渡圖例）→空白鍵暫停只剩有出處疆界；←／→ 切換；播完停在 ended', async ({ page }) => {
  await open(page, 1440, 900, false);
  const main = page.getByTestId('campaign-page');
  const card = page.getByTestId('campaign-card');
  await page.waitForTimeout(3500);
  await expect(card).toHaveAttribute('data-status', 'ready');
  await expect(main).toHaveAttribute('data-phase', '1');
  await expectSettled(page);

  await page.locator('body').click({ position: { x: 5, y: 5 } }).catch(() => undefined);
  await page.keyboard.press(' ');
  await expect(card).toHaveAttribute('data-status', 'playing');
  // 3 秒後進 P2：T 方框變寬（morph），S 不變（same）
  await expect(page.getByTestId('campaign-map')).toHaveAttribute('data-transition', 'morph', { timeout: 5000 });
  await expect(main).toHaveAttribute('data-phase', '2');
  await expect(page.getByTestId('campaign-legend-transitional')).toHaveText('推估過渡，非史料');
  await expect(page.getByTestId('campaign-legend-pending')).not.toContainText('推估過渡');
  const tx = await sourceData(page, 'campaign-sov-tx');
  expect(tx.features.length).toBeGreaterThan(0);
  for (const f of tx.features) expect(f.properties['transitional']).toBe(true);
  // 中途暫停 → 立即收尾
  await page.keyboard.press(' ');
  await expect(card).toHaveAttribute('data-status', 'paused');
  await expectSettled(page);
  await expect(page.getByTestId('campaign-map')).toHaveAttribute('data-borders', '1940-05-28');

  // 鍵盤 ←／→
  await page.keyboard.press('ArrowRight');
  await expect(main).toHaveAttribute('data-phase', '3');
  await expectSettled(page);
  await page.keyboard.press('ArrowLeft');
  await expect(main).toHaveAttribute('data-phase', '2');
  await expectSettled(page);

  // P3 → P4（06-01）S 分裂 → 拓撲不相容，含交叉淡入淡出
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press(' ');
  await expect(page.getByTestId('campaign-map')).toHaveAttribute('data-transition', 'mixed', { timeout: 5000 });
  const mixed = await sourceData(page, 'campaign-sov-tx');
  expect(new Set(mixed.features.map((f) => f.properties['kind']))).toEqual(new Set(['morph', 'fade']));
  // 播完停在 ended
  await expect(card).toHaveAttribute('data-status', 'ended', { timeout: 12_000 });
  await expect(main).toHaveAttribute('data-phase', '6');
  await expectSettled(page);
});

test('§19.2.4 reduced-motion：不做 morph，直接切換', async ({ page }) => {
  await open(page, 1440, 900, true);
  await page.evaluate(() => {
    const seen: string[] = [];
    (window as unknown as { __seen: string[] }).__seen = seen;
    const el = document.querySelector('[data-testid="campaign-map"]')!;
    new MutationObserver(() => seen.push(el.getAttribute('data-transition') ?? '')).observe(el, { attributes: true, attributeFilter: ['data-transition'] });
  });
  await page.getByTestId('campaign-play').click();
  await expect(page.getByTestId('campaign-page')).toHaveAttribute('data-phase', '4', { timeout: 12_000 });
  await expect(page.getByTestId('campaign-map')).toHaveAttribute('data-borders', '1940-06-01');
  expect(await page.evaluate(() => (window as unknown as { __seen: string[] }).__seen.filter((v) => v !== 'none'))).toEqual([]);
  await expect(page.getByText('推估過渡')).toHaveCount(0);
  await page.getByTestId('campaign-play').click();
  await expectSettled(page);
});

test('§19.2.4 (iii) 中間形狀不可點選：漸變中點擊形狀不會選取、不開彈窗、不改網址或播放狀態', async ({ page }) => {
  await open(page, 1440, 900, false);
  await page.getByTestId('campaign-play').click();
  await expect(page.getByTestId('campaign-map')).toHaveAttribute('data-transition', 'morph', { timeout: 5000 });
  const pt = await page.evaluate(() => {
    const m = (window as unknown as { __wlCampaignMap: { project: (p: [number, number]) => { x: number; y: number }; getCanvas: () => HTMLCanvasElement } }).__wlCampaignMap;
    const p = m.project([2.1, 50.75]);
    const r = m.getCanvas().getBoundingClientRect();
    return { x: r.left + p.x, y: r.top + p.y };
  });
  const url = page.url();
  const dialogs = await page.locator('[role="dialog"]').count();
  await page.mouse.click(pt.x, pt.y);
  expect(page.url()).toBe(url);
  await expect(page.locator('[role="dialog"]')).toHaveCount(dialogs);
  await expect(page.getByTestId('campaign-card')).toHaveAttribute('data-status', 'playing');
  const cursor = await page.evaluate(() => getComputedStyle(document.querySelector('[data-testid="campaign-map"] canvas')!).cursor);
  expect(cursor).not.toBe('pointer');
  await page.getByTestId('campaign-play').click();
  await expectSettled(page);
});

test('§19.2.4 (v) 效能：1440 寬播放期間 rAF 平均與 p5 fps（實測）', async ({ page }) => {
  await open(page, 1440, 900, false);
  await page.getByTestId('campaign-play').click();
  const r = await page.evaluate(() => new Promise<{ frames: number; avg: number; p5: number; ms: number }>((resolve) => {
    const dts: number[] = [];
    let last = performance.now();
    const t0 = last;
    const loop = (now: number) => {
      dts.push(now - last); last = now;
      if (now - t0 < 7500) requestAnimationFrame(loop);
      else {
        const ms = now - t0;
        const sorted = dts.slice(1).sort((a, b) => b - a); // 由慢到快
        const p95dt = sorted[Math.floor(sorted.length * 0.05)];
        resolve({ frames: dts.length - 1, avg: ((dts.length - 1) * 1000) / ms, p5: 1000 / p95dt, ms });
      }
    };
    requestAnimationFrame(loop);
  }));
  mkdirSync(PERF_OUT.replace(/\/[^/]+$/, ''), { recursive: true });
  writeFileSync(PERF_OUT, JSON.stringify({ viewport: '1440x900', windowMs: Math.round(r.ms), frames: r.frames, avgFps: +r.avg.toFixed(1), p5Fps: +r.p5.toFixed(1) }, null, 2));
  console.log(`[c2b-fps] avg=${r.avg.toFixed(1)} p5=${r.p5.toFixed(1)} frames=${r.frames} window=${Math.round(r.ms)}ms`);
  expect(r.avg).toBeGreaterThanOrEqual(55);
});

for (const [w, h] of [[360, 780], [1440, 900]] as const) {
  test(`截圖 ${w}px：漸變中途`, async ({ page }) => {
    await open(page, w, h, false);
    await page.getByTestId('campaign-play').click();
    await expect(page.getByTestId('campaign-map')).toHaveAttribute('data-transition', 'morph', { timeout: 5000 });
    await page.waitForTimeout(450);
    await page.screenshot({ path: `${DIR}/${w}-morph-mid.png` });
    await page.getByTestId('campaign-play').click();
    await expectSettled(page);
  });
}
