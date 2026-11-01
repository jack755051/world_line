import { expect, test, type Page } from '@playwright/test';
import { writeFileSync, mkdirSync } from 'node:fs';

/**
 * 效能量測（WL_E2E_BORDERS=1 時才跑；只讀，不寫資料）：Tai 2026-11-01「播放一直載入中、跳日期不連貫」。
 * - 跳日期：每次換日期的 API 請求數、到新日期畫面就緒（shownMs：map-area data-ready-for＝該日、MapLibre idle、無載入指示；
 *   舊版前端沒有 data-ready-for，會等到逾時，只看 ms）、到全部安靜（無進行中請求、MapLibre idle、沒有載入指示）的時間、載入指示是否出現。
 * - 播放：15 秒內前進幾格、最長一格間隔、載入指示累計出現時間、請求數。
 * 結果寫到 tmp/perf/perf-<WL_PERF_LABEL>.json（預設 run）。
 */
test.skip(!process.env['WL_E2E_BORDERS'], '需要開發 API（5052）');
const label = process.env['WL_PERF_LABEL'] ?? 'run';
const API = /\/api\/v1\/(sovereignty|conflicts|control)\?/;

function track(page: Page) {
  const s = { pending: 0, count: 0, bytes: 0 };
  page.on('request', (r) => { if (API.test(r.url())) { s.pending++; s.count++; } });
  page.on('requestfinished', async (r) => {
    if (!API.test(r.url())) return;
    s.pending--;
    try { s.bytes += (await r.sizes()).responseBodySize; } catch { /* 已關閉 */ }
  });
  page.on('requestfailed', (r) => { if (API.test(r.url())) s.pending--; });
  return s;
}
async function busyWatch(page: Page) {
  await page.evaluate(() => {
    const w = window as unknown as { __busy: { since: number | null; total: number; shows: number } };
    w.__busy = { since: null, total: 0, shows: 0 };
    const tick = () => {
      const on = !!document.querySelector('[data-testid="map-busy"]');
      const b = w.__busy;
      if (on && b.since === null) { b.since = performance.now(); b.shows++; }
      if (!on && b.since !== null) { b.total += performance.now() - b.since; b.since = null; }
      requestAnimationFrame(tick);
    };
    tick();
  });
}
const busy = (page: Page) => page.evaluate(() => {
  const b = (window as unknown as { __busy: { since: number | null; total: number; shows: number } }).__busy;
  return { shows: b.shows, ms: Math.round(b.total + (b.since !== null ? performance.now() - b.since : 0)) };
});
/** 畫面就緒：新日期的主權／衝突／控制區都已顯示、地圖畫完、沒有載入指示（不等背景預先載入）。 */
async function shown(page: Page, to: string) {
  const area = page.getByTestId('map-area');
  for (let i = 0; i < 600; i++) {
    const idle = (await page.getByTestId('map-canvas').getAttribute('data-render')) === 'idle';
    if ((await area.getAttribute('data-ready-for')) === to && idle && (await page.getByTestId('map-busy').count()) === 0) return;
    await page.waitForTimeout(25);
  }
}
async function settled(page: Page, s: { pending: number }) {
  const canvas = page.getByTestId('map-canvas');
  let ok = 0;
  for (let i = 0; i < 600; i++) {
    const idle = (await canvas.getAttribute('data-render')) === 'idle';
    const noBusy = (await page.getByTestId('map-busy').count()) === 0;
    ok = idle && noBusy && s.pending === 0 ? ok + 1 : 0;
    if (ok >= 2) return;
    await page.waitForTimeout(50);
  }
}

test('效能：跳日期與播放', async ({ page }) => {
  test.setTimeout(240_000);
  const s = track(page);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/?date=1942-12-01&axis=sovereignty');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true');
  await settled(page, s);
  await busyWatch(page);
  const jumps: { to: string; shownMs: number; ms: number; requests: number; kb: number; busyShows: number }[] = [];
  const input = page.getByTestId('timeline-date-input');
  for (const to of ['1942-12-08', '1943-06-01', '1915-06-01', '1918-03-04', '1939-10-23', '1942-12-01', '1942-12-15']) {
    const c0 = s.count, b0 = s.bytes, bz = await busy(page);
    const t0 = Date.now();
    await input.fill(to);
    await input.press('Enter');
    await page.waitForTimeout(150); // 換日期去抖動 120ms
    await shown(page, to);
    const shownMs = Date.now() - t0;
    await settled(page, s); // 含背景預先載入全部結束
    const bz1 = await busy(page);
    jumps.push({ to, shownMs, ms: Date.now() - t0, requests: s.count - c0, kb: Math.round((s.bytes - b0) / 1024), busyShows: bz1.shows - bz.shows });
  }

  // 播放 15 秒（一週一格）
  await input.fill('1942-11-01');
  await input.press('Enter');
  await page.waitForTimeout(150);
  await settled(page, s);
  const c0 = s.count, b0 = await busy(page);
  const dates: { d: string; t: number }[] = [];
  const start = Date.now();
  await page.getByTestId('timeline-play').click();
  let last = '';
  while (Date.now() - start < 15_000) {
    const d = await input.inputValue();
    if (d !== last) { dates.push({ d, t: Date.now() - start }); last = d; }
    await page.waitForTimeout(50);
  }
  await page.getByTestId('timeline-play').click();
  const b1 = await busy(page);
  const gaps = dates.slice(1).map((x, i) => x.t - dates[i].t);
  const play = { steps: dates.length - 1, maxGapMs: Math.max(0, ...gaps), requests: s.count - c0, busyShows: b1.shows - b0.shows, busyMs: b1.ms - b0.ms, last: last };
  const out = { label, jumps, play };
  mkdirSync('tmp/perf', { recursive: true });
  writeFileSync(`tmp/perf/perf-${label}.json`, JSON.stringify(out, null, 2));
  console.log(JSON.stringify(out));
});
