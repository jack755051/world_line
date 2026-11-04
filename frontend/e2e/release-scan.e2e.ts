import { expect, test } from '@playwright/test';
import { writeFileSync, mkdirSync } from 'node:fs';

/**
 * 上線前掃描（WL_RELEASE_SCAN=1 才跑）：預設圖磚模式，1908–1945 抽樣日期 × 桌機／手機寬度，
 * 收集主控台錯誤、頁面例外、API／圖磚 4xx／5xx、版面遮擋（頂列／時間軸／圖例互相重疊、頂列溢出），寫到 tmp/release-scan/。
 */
test.skip(!process.env['WL_RELEASE_SCAN'], '只在 WL_RELEASE_SCAN=1 時跑');
const OUT = 'tmp/release-scan';
const DATES = ['1908-10-05', '1912-10-20', '1914-08-01', '1918-11-11', '1920-08-10', '1923-07-24', '1929-10-29', '1933-01-30', '1936-03-07',
  '1938-10-01', '1939-09-15', '1940-07-15', '1941-06-22', '1942-11-01', '1943-09-08', '1944-06-06', '1945-05-08', '1945-09-02'];
const SIZES = [{ w: 1440, h: 900 }, { w: 390, h: 844 }];

test('預設（無參數）1440：圖磚模式截圖', async ({ page }) => {
  mkdirSync('tmp/tiles', { recursive: true });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true');
  await expect(page.getByTestId('map-area')).toHaveAttribute('data-ready-for', /\d{4}-\d{2}-\d{2}/, { timeout: 30000 });
  await page.waitForTimeout(2500);
  const src = await page.evaluate(() => {
    const m = (window as unknown as { __wlMap: { getStyle: () => { sources: Record<string, { type: string }> } } }).__wlMap;
    return Object.entries(m.getStyle().sources).map(([k, v]) => `${k}:${v.type}`);
  });
  expect(src.some((s) => s.endsWith(':vector'))).toBe(true);
  await page.screenshot({ path: 'tmp/tiles/default-tiles.png' });
});

for (const { w, h } of SIZES) {
  test(`掃描 ${w}px：${DATES.length} 個日期`, async ({ page }) => {
    test.setTimeout(DATES.length * 30000);
    mkdirSync(OUT, { recursive: true });
    const rows: Record<string, unknown>[] = [];
    let cur = '';
    const consoleErr: string[] = [];
    const bad: string[] = [];
    page.on('console', (m) => { if (m.type() === 'error') consoleErr.push(`${cur} ${m.text().slice(0, 200)}`); });
    page.on('pageerror', (e) => consoleErr.push(`${cur} PAGEERROR ${e.message.slice(0, 200)}`));
    page.on('response', (r) => { if (r.status() >= 400) bad.push(`${cur} ${r.status()} ${r.url().slice(0, 160)}`); });
    page.on('requestfailed', (r) => { const f = r.failure()?.errorText ?? ''; if (!/ERR_ABORTED/.test(f)) bad.push(`${cur} FAILED ${f} ${r.url().slice(0, 160)}`); });
    await page.setViewportSize({ width: w, height: h });
    for (const d of DATES) {
      cur = d;
      const t0 = Date.now();
      await page.goto(`/?date=${d}`);
      await expect(page.getByTestId('map-canvas')).toHaveAttribute('data-map-ready', 'true', { timeout: 30000 });
      let ready = true;
      try { await expect(page.getByTestId('map-area')).toHaveAttribute('data-ready-for', d, { timeout: 25000 }); } catch { ready = false; }
      await page.waitForTimeout(800);
      const layout = await page.evaluate(() => {
        const box = (id: string) => { const e = document.querySelector(`[data-testid="${id}"]`) as HTMLElement | null; if (!e || e.offsetParent === null) return null; const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom }; };
        const hit = (a: ReturnType<typeof box>, b: ReturnType<typeof box>) => !!a && !!b && a.l < b.r - 1 && b.l < a.r - 1 && a.t < b.b - 1 && b.t < a.b - 1;
        const top = box('topbar'), tl = box('timeline'), leg = box('legend-anchor'), scale = box('map-scale');
        const bar = document.querySelector('[data-testid="topbar"]') as HTMLElement | null;
        return {
          topbarOverflow: bar ? bar.scrollWidth > bar.clientWidth + 1 : null,
          topbarVsTimeline: hit(top, tl), legendVsTimeline: hit(leg, tl), scaleVsTimeline: hit(scale, tl), scaleVsLegend: hit(scale, leg),
          bodyOverflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
          rendered: Number(document.querySelector('[data-testid="map-canvas"]')?.getAttribute('data-rendered-sovereignty') ?? 0),
          empty: !!document.querySelector('[data-testid="map-empty"]'), error: !!document.querySelector('[data-testid="map-error"]'),
        };
      });
      rows.push({ date: d, ready, ms: Date.now() - t0, ...layout });
      await page.screenshot({ path: `${OUT}/${w}-${d}.png` });
    }
    writeFileSync(`${OUT}/scan-${w}.json`, JSON.stringify({ rows, consoleErr, bad }, null, 1));
  });
}
