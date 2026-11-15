import { readFileSync } from 'node:fs';
import { expect, test, type Page, type Route } from '@playwright/test';

/**
 * §19.2 戰役獨立頁（C2a）。所有 /api 與 /healthz 都用 route 攔截回測試資料——不連任何既有 API 或資料庫。
 * 測試資料只為驗證 UI 流程，不是史料：政權多邊形是方框、事件是編號；戰役圖層沿用 public/campaigns 的靜態 JSON，
 * API 版本另加一個無圖形的 P6（對應 C1b 六階段，P6 無戰線圖）。
 * 截圖存 WL_SHOT_DIR（預設 tmp/c2a-shots）。
 */
const DIR = process.env['WL_SHOT_DIR'] ?? 'tmp/c2a-shots';
const UK = '11111111-1111-4111-8111-111111111111';
const staticCampaign = JSON.parse(readFileSync('public/campaigns/dunkirk_1940.json', 'utf8'));
const apiCampaign = {
  ...staticCampaign,
  phases: [...staticCampaign.phases, { seq: 6, key: 'p6', name_zh: '（測試資料）P6', start: '1940-06-04', end: '1940-06-05', summary_zh: '（測試資料，非史料）', summary_verified: false, sources: [] }],
};
const env = (data: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify({ statusCode: 200, message: 'ok', data }) });
const period = { start: '1939-09-01', end: null };
const geom = { sourceId: 's', sourceTitle: '測試', publisher: '測試', sourceLicenseCode: null, locator: '-', geometryLicense: 'test', attribution: null, ohmRelationId: null, ohmVersion: null, ohmFetchedAt: null, ohmStartRaw: null, ohmEndRaw: null, flags: null };
const box = (x0: number, y0: number, x1: number, y1: number) => ({ type: 'Polygon', coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] });
const sovereignty = (date: string) => ({
  date,
  featureCollection: {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature', id: 'rec-uk', geometry: box(-6, 50, 1.6, 58.5),
      properties: { recordId: 'rec-uk', regimeId: UK, regimeSlug: 'united-kingdom', layerStatus: 'established', validPeriod: period, startEvent: null, endEvent: null, geometry: geom, note: null },
    }],
  },
});
const events = Array.from({ length: 40 }, (_, i) => ({
  id: `00000000-0000-4000-8000-${String(i).padStart(12, '0')}`, eventKind: 'political',
  occurred: { start: `1939-${String((i % 12) + 1).padStart(2, '0')}-01`, end: null }, summary: null, verification: 'pending', citations: [], roles: [], additions: null, names: [],
}));

type ApiMode = 'api' | 'static-fallback';
async function mockApi(page: Page, mode: ApiMode = 'api'): Promise<void> {
  await page.addInitScript(() => localStorage.setItem('wl.boundarySource', 'geojson'));
  await page.route('**/healthz', (r) => r.fulfill(env({ status: 'Healthy', checks: [] })));
  await page.route('**/api/v1/**', async (r: Route) => {
    const u = new URL(r.request().url());
    const p = u.pathname.replace('/api/v1', '');
    const date = u.searchParams.get('date') ?? '1940-05-28';
    if (p.startsWith('/campaigns/')) return mode === 'api' ? r.fulfill(env(apiCampaign)) : r.fulfill({ status: 503, body: '' });
    if (p === '/sovereignty') return r.fulfill(env(sovereignty(date)));
    if (p === '/control') return r.fulfill(env({ date, featureCollection: { type: 'FeatureCollection', features: [] }, theaters: [], coverageNotes: [] }));
    if (p === '/conflicts') return r.fulfill(env({ date, featureCollection: { type: 'FeatureCollection', features: [] } }));
    if (p === '/timeline/change-points') return r.fulfill(env({ version: 1, points: ['1939-09-01', '1940-05-26', '1940-06-05'], controlPoints: [] }));
    if (p === '/timeline/extent') return r.fulfill(env({ earliestEvent: '1937-07-07', latestEvent: '1945-09-02' }));
    if (p === '/timeline/snapshots') return r.fulfill(env({ items: [], total: 0, page: 1, pageSize: 100 }));
    if (p === '/capitals') return r.fulfill(env({ date, features: [] }));
    if (p === '/leaders') return r.fulfill(env({ date, features: [] }));
    if (/^\/regimes\/[^/]+\/events$/.test(p)) return r.fulfill(env(events));
    if (p === '/regimes') return r.fulfill(env([{ id: UK, slug: 'united-kingdom', wikidataQid: null, names: [{ lang: 'zh-Hant', name: '英國', display: '英國', isPrimary: true, validPeriod: period }] }]));
    if (/^\/regimes\/[^/]+$/.test(p)) return r.fulfill(env({ id: UK, slug: 'united-kingdom', wikidataQid: null, names: [] }));
    return r.fulfill(env([]));
  });
}

const atlasCamera = (page: Page) => page.evaluate(() => {
  const m = (window as unknown as { __wlMap: { getCenter: () => { lng: number; lat: number }; getZoom: () => number; getBearing: () => number } }).__wlMap;
  const c = m.getCenter();
  return { lng: +c.lng.toFixed(4), lat: +c.lat.toFixed(4), zoom: +m.getZoom().toFixed(3), bearing: +m.getBearing().toFixed(2) };
});
const sheetScroll = (page: Page) => page.evaluate(() => document.querySelector<HTMLElement>('[data-testid="regime-sheet"] [data-testid="sovereignty-card-body"]')?.scrollTop ?? -1);

async function atlasState(page: Page) {
  const u = new URL(page.url());
  return {
    date: u.searchParams.get('date'), regime: u.searchParams.get('regime'), tab: u.searchParams.get('tab'),
    camera: await atlasCamera(page), scroll: await sheetScroll(page),
    tabSelected: await page.locator('[data-testid="regime-sheet"] [role="tab"][aria-selected="true"]').first().textContent().catch(() => null),
  };
}

async function openAtlasWithRegime(page: Page): Promise<void> {
  // 這個檔測的是原本的戰役頁（/campaign/:slug）；敦克爾克的入口預設已改開新版 /battle/
  await page.addInitScript(() => sessionStorage.setItem('wl.battlePage', 'classic'));
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(`/?date=1940-05-28&axis=sovereignty&regime=${UK}&tab=events`);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true');
  await expect(page.getByTestId('campaign-entry').first()).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`regime=${UK}`));
  await expect(page).toHaveURL(/tab=events/);
  // 自訂鏡頭與面板捲動（返回後要逐值一致）
  await page.waitForTimeout(600);
  await page.evaluate(() => (window as unknown as { __wlMap: { jumpTo: (o: object) => void } }).__wlMap.jumpTo({ center: [-1.2345, 53.4321], zoom: 4.567 }));
  await expect.poll(() => page.evaluate(() => {
    const b = document.querySelector<HTMLElement>('[data-testid="regime-sheet"] [data-testid="sovereignty-card-body"]');
    if (!b) return 0;
    b.scrollTop = 180;
    return b.scrollTop;
  })).toBe(180);
}

test('§19.2.5 地圖 → 戰役頁 → 瀏覽器上一頁／返回鈕：日期、鏡頭、選取政權、分頁、sheet 捲動完全一致；重新整理 phase 從網址還原', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page);
  await openAtlasWithRegime(page);
  const before = await atlasState(page);
  expect(before.date).toBe('1940-05-28');
  expect(before.scroll).toBe(180);

  // 1) 進戰役頁 → 切到 P3 → 重新整理（phase 從網址還原）→ 瀏覽器上一頁（history.state 還原）
  await page.getByTestId('campaign-entry').first().click();
  await expect(page).toHaveURL(/\/campaign\/dunkirk_1940\?phase=1/);
  const main = page.getByTestId('campaign-page');
  await expect(main).toHaveAttribute('data-source', 'api');
  await expect(page.getByTestId('campaign-back')).toContainText('返回 1940-05-28 地圖');
  await page.getByTestId('campaign-phase-3').click();
  await expect(page).toHaveURL(/phase=3/);
  await page.reload();
  await expect(main).toHaveAttribute('data-phase', '3');
  await expect(page.getByTestId('campaign-card')).toHaveAttribute('data-phase', '3');
  await page.goBack();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true');
  await expect.poll(() => sheetScroll(page), { timeout: 8000 }).toBe(180);
  expect(await atlasState(page)).toEqual(before);

  // 2) 再進一次，改用頁面上的「返回」鈕（記憶體快照）
  await page.getByTestId('campaign-entry').first().click();
  await expect(page).toHaveURL(/\/campaign\/dunkirk_1940/);
  await expect(page.getByTestId('campaign-card')).toHaveAttribute('data-status', 'ready');
  await page.keyboard.press('ArrowRight');
  await expect(page).toHaveURL(/phase=2/);
  await page.getByTestId('campaign-back').click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true');
  await expect.poll(() => sheetScroll(page), { timeout: 8000 }).toBe(180);
  expect(await atlasState(page)).toEqual(before);
});

test('§19.2.5／19.2.7 直接開 URL：返回鈕改「開啟地圖」；P6 無圖形顯示空狀態；pending 有「待考證」圖例', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page);
  await page.goto('/campaign/dunkirk_1940?phase=6');
  await expect(page.getByTestId('campaign-page')).toHaveAttribute('data-phase', '6');
  await expect(page.getByTestId('campaign-back')).toContainText('開啟地圖');
  await expect(page.getByTestId('campaign-empty-phase')).toHaveText(/此階段尚無有出處的戰線資料/);
  await page.getByTestId('campaign-phase-2').click();
  await expect(page.getByTestId('campaign-empty-phase')).toHaveCount(0);
  await expect(page.getByTestId('campaign-legend-pending')).toContainText('待考證');
  await expect(page.getByTestId('campaign-map')).toHaveAttribute('data-map-ready', 'true');
  // 三個圖層依 phase 過濾
  const filter = await page.evaluate(() => JSON.stringify((window as unknown as { __wlCampaignMap: { getFilter: (id: string) => unknown } }).__wlCampaignMap.getFilter('campaign-arrows')));
  expect(filter).toContain('2');
  await page.getByTestId('campaign-back').click();
  await expect(page).toHaveURL(/\/\?date=1940-05-26/);
});

test('§19.5 C1：API 讀不到 → 退回靜態 JSON 並標示；找不到的戰役 → 錯誤狀態不顯示圖層', async ({ page }) => {
  await mockApi(page, 'static-fallback');
  await page.goto('/campaign/dunkirk_1940');
  await expect(page.getByTestId('campaign-page')).toHaveAttribute('data-source', 'static');
  await expect(page.getByTestId('campaign-source-kind')).toContainText('靜態 JSON');
  await page.goto('/campaign/no_such_campaign');
  await expect(page.getByTestId('campaign-page-error')).toBeVisible();
  await expect(page.getByTestId('campaign-legend')).toHaveCount(0);
});

for (const [w, h] of [[360, 780], [390, 844], [768, 1024], [1024, 768], [1440, 900]] as const) {
  test(`截圖 ${w}px：戰役頁 P1、P6`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await mockApi(page);
    await page.goto('/campaign/dunkirk_1940?phase=1');
    await expect(page.getByTestId('campaign-map')).toHaveAttribute('data-map-ready', 'true');
    if (w < 768) {
      await expect(page.getByTestId('campaign-sheet')).toHaveAttribute('data-snap', 'peek');
      const pill = await page.getByTestId('campaign-phase-1').boundingBox();
      if (await page.evaluate(() => matchMedia('(hover: none) and (pointer: coarse)').matches)) expect(pill!.height).toBeGreaterThanOrEqual(44);
    } else {
      expect(Math.round((await page.getByTestId('campaign-aside').boundingBox())!.width)).toBe(360);
    }
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${DIR}/${w}-p1.png` });
    if (w < 768) await page.getByTestId('campaign-sheet-handle').click();
    await page.getByTestId('campaign-phase-6').click();
    await expect(page.getByTestId('campaign-empty-phase')).toBeVisible();
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${DIR}/${w}-p6.png` });
  });
}

test('敦克爾克的戰役簡報入口開新版戰役頁（/battle/），「← 地圖」回到原本的日期與政權', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page);
  await page.goto(`/?date=1940-05-28&axis=sovereignty&regime=${UK}&tab=events`);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true');
  await page.getByTestId('campaign-entry').filter({ hasText: '敦克爾克' }).click();
  await expect(page).toHaveURL(/\/battle\/index\.html\?battle=dunkirk-1940&app=1&back=/);
  await expect.poll(() => page.evaluate(() => (window as unknown as { __ready?: boolean }).__ready === true), { timeout: 20000 }).toBe(true);
  // 正式頁模式：只列有出處的戰役、沒有「未查證資料」開關
  await expect(page.locator('#bt-menu a')).toHaveCount(1);
  await expect(page.locator('#layers .chip', { hasText: '未查證資料' })).toHaveCount(0);
  await page.locator('#app-back').click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true');
  await expect(page).toHaveURL(/date=1940-05-28/);
  await expect(page).toHaveURL(new RegExp(`regime=${UK}`));
  await expect(page.getByTestId('sovereignty-card-title')).toBeVisible();
});
