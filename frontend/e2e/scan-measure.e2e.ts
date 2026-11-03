/**
 * scan-measure.e2e.ts - World Line 跳年效能基準量測（Tai 2026-11-03）
 *
 * 預設 skip；設定 WL_SCAN_MEASURE=1 才執行。
 * WL_SCAN_OUT   指定輸出 JSON 路徑（預設 /tmp/wl-scan2/baseline.json）
 * WL_SCAN_LABEL 指定標籤（預設 baseline）
 *
 * 量測定義：
 * - 冷跳：每次用新的 browser context 開 /?date=1938-01-01，
 *   等 [data-testid=map-area][data-ready-for="1938-01-01"]，
 *   在 [data-testid=timeline-date-input] 填 1940-07-01 按 Enter，
 *   計時到 data-ready-for="1940-07-01"（readyMs）；
 *   另記「視覺完成」時間：到畫面上不再有 [data-testid=map-scan] 也沒有
 *   [data-testid=map-busy-scrim] 為止（目前版本若沒有就等於 ready 時間）。
 * - 熱跳：同一頁面內 1940-07-01 → 1938-01-01 → 1940-07-01 來回
 *   （兩個日期都已載入過），每次都量同樣兩個時間。
 * - 冷跳重複 9 次、熱跳 18 次，各取中位數；viewport 1440×900，locale zh-TW。
 * - FPS：每次跳年從 Enter 到視覺完成之間，在頁面內用 requestAnimationFrame 計幀，
 *   記平均 FPS 與最長單幀（ms）；取中位數。
 * - 結果寫到 WL_SCAN_OUT（預設 /tmp/wl-scan2/baseline.json）
 *   格式：{ label, head, cold:{median_ms, visual_median_ms, runs:[]},
 *           hot:{...}, fps:{median, worst_frame_ms_median} }
 */

import { test, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
import path from 'node:path';

const DATE_A = '1938-01-01';
const DATE_B = '1940-07-01';
const COLD_RUNS = 9;
const HOT_RUNS = 18;

function median(vals: number[]): number {
  if (vals.length === 0) return 0;
  const s = [...vals].sort((a, b) => a - b);
  return s[Math.floor(s.length / 2)];
}

interface RunResult {
  readyMs: number;
  visualMs: number;
  avgFps: number;
  worstFrameMs: number;
}

/** 輪詢 map-area[data-ready-for] 直到符合目標日期；超時靜默返回。 */
async function waitMapReady(page: Page, forDate: string, timeout = 30000): Promise<void> {
  const area = page.getByTestId('map-area');
  for (let i = 0; i < Math.ceil(timeout / 25); i++) {
    if ((await area.getAttribute('data-ready-for')) === forDate) return;
    await page.waitForTimeout(25);
  }
}

/** 在頁面內啟動 rAF 幀計時器（每次呼叫會重置前次資料）。 */
async function startFpsTracking(page: Page): Promise<void> {
  await page.evaluate(() => {
    // 停止前一次殘留的 loop
    if ((window as any).__wlFps) (window as any).__wlFps.stopped = true;
    (window as any).__wlFps = {
      frameTimes: [] as number[],
      lastTs: performance.now(),
      stopped: false,
    };
    const loop = (ts: number) => {
      const dt = ts - (window as any).__wlFps.lastTs;
      // 排除異常幀（< 0 或 > 500ms 代表頁面暫停）
      if (dt > 0 && dt < 500) (window as any).__wlFps.frameTimes.push(dt);
      (window as any).__wlFps.lastTs = ts;
      if (!(window as any).__wlFps.stopped) requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  });
}

/** 停止 rAF 計時器並回傳平均 FPS 與最長單幀 ms。 */
async function stopFpsTracking(page: Page): Promise<{ avgFps: number; worstFrameMs: number }> {
  return page.evaluate(() => {
    (window as any).__wlFps.stopped = true;
    const frames: number[] = (window as any).__wlFps.frameTimes;
    if (frames.length < 2) return { avgFps: 0, worstFrameMs: 0 };
    const totalTime = frames.reduce((a, b) => a + b, 0);
    const avgFps = totalTime > 0 ? +((frames.length / totalTime) * 1000).toFixed(1) : 0;
    const worstFrameMs = +Math.max(...frames).toFixed(1);
    return { avgFps, worstFrameMs };
  });
}

/**
 * 執行一次日期跳轉並回傳量測結果：
 * - readyMs：從 Enter 到 data-ready-for 符合目標日期。
 * - visualMs：從 Enter 到畫面無 map-scan 且無 map-busy-scrim（若元素不存在則≈readyMs）。
 * - avgFps / worstFrameMs：rAF 統計。
 */
async function doJump(page: Page, toDate: string): Promise<RunResult> {
  const input = page.getByTestId('timeline-date-input');

  await startFpsTracking(page);

  const t0 = Date.now();
  await input.fill(toDate);
  await input.press('Enter');

  // 等資料就緒
  await waitMapReady(page, toDate, 30000);
  const readyMs = Date.now() - t0;

  // 等視覺指示器消失（若元素不在 DOM 中，isVisible 立即回傳 false → 直接結束）
  for (let i = 0; i < 400; i++) {
    const scanVis = await page.getByTestId('map-scan').isVisible().catch(() => false);
    const scrimVis = await page.getByTestId('map-busy-scrim').isVisible().catch(() => false);
    if (!scanVis && !scrimVis) break;
    await page.waitForTimeout(25);
  }
  const visualMs = Date.now() - t0;

  const fps = await stopFpsTracking(page);
  return { readyMs, visualMs, ...fps };
}

test('scan: baseline measurement (cold + hot jumps)', async ({ browser }) => {
  if (!process.env['WL_SCAN_MEASURE']) {
    test.skip(true, '設定 WL_SCAN_MEASURE=1 才執行量測');
  }
  test.setTimeout(1_200_000); // 20 分鐘上限

  const label = process.env['WL_SCAN_LABEL'] ?? 'baseline';
  const outPath = process.env['WL_SCAN_OUT'] ?? '/tmp/wl-scan2/baseline.json';
  const port = process.env['WL_E2E_PORT'] ?? '4201';
  const baseUrl = `http://127.0.0.1:${port}`;

  // 取得目前 HEAD commit hash
  let head = 'unknown';
  try {
    head = execSync('git rev-parse HEAD').toString().trim();
  } catch {
    try {
      head = execSync('git rev-parse HEAD', {
        cwd: path.resolve(__dirname, '../../'),
      })
        .toString()
        .trim();
    } catch {
      head = 'unknown';
    }
  }

  // ── 冷跳量測 ──────────────────────────────────────────────────────────────
  console.log(`\n[scan-measure] 開始冷跳量測（${COLD_RUNS} 次，${DATE_A} → ${DATE_B})...`);
  const coldRuns: RunResult[] = [];

  for (let i = 0; i < COLD_RUNS; i++) {
    const ctx = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      locale: 'zh-TW',
      timezoneId: 'Asia/Taipei',
    });
    const page = await ctx.newPage();
    try {
      await page.goto(`${baseUrl}/?date=${DATE_A}`);
      await page.getByTestId('map-area').waitFor({ state: 'attached', timeout: 30000 });
      await waitMapReady(page, DATE_A, 30000);

      const result = await doJump(page, DATE_B);
      coldRuns.push(result);
      console.log(
        `  冷 #${i + 1}: ready=${result.readyMs}ms visual=${result.visualMs}ms ` +
          `fps=${result.avgFps} worst=${result.worstFrameMs}ms`,
      );
    } finally {
      await ctx.close();
    }
  }

  // ── 熱跳量測 ──────────────────────────────────────────────────────────────
  console.log(`\n[scan-measure] 開始熱跳量測（${HOT_RUNS} 次，${DATE_A} ↔ ${DATE_B})...`);
  const hotRuns: RunResult[] = [];

  const hotCtx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: 'zh-TW',
    timezoneId: 'Asia/Taipei',
  });
  const hotPage = await hotCtx.newPage();
  try {
    // 暖機：先載入 DATE_A，再跳到 DATE_B，再回 DATE_A，最後停在 DATE_B
    await hotPage.goto(`${baseUrl}/?date=${DATE_A}`);
    await hotPage.getByTestId('map-area').waitFor({ state: 'attached', timeout: 30000 });
    await waitMapReady(hotPage, DATE_A, 30000);
    await doJump(hotPage, DATE_B); // 暖機跳至 B
    await doJump(hotPage, DATE_A); // 暖機回 A
    await doJump(hotPage, DATE_B); // 停在 B 作為熱跳起點

    // 熱跳：從 DATE_B 開始，交替 B→A→B→A...
    let currentDate = DATE_B;
    for (let i = 0; i < HOT_RUNS; i++) {
      const target = currentDate === DATE_B ? DATE_A : DATE_B;
      const result = await doJump(hotPage, target);
      hotRuns.push(result);
      currentDate = target;
      console.log(
        `  熱 #${i + 1} →${target}: ready=${result.readyMs}ms visual=${result.visualMs}ms ` +
          `fps=${result.avgFps} worst=${result.worstFrameMs}ms`,
      );
    }
  } finally {
    await hotCtx.close();
  }

  // ── 計算中位數 ─────────────────────────────────────────────────────────────
  const coldMedianMs = median(coldRuns.map((r) => r.readyMs));
  const coldVisualMedianMs = median(coldRuns.map((r) => r.visualMs));
  const hotMedianMs = median(hotRuns.map((r) => r.readyMs));
  const hotVisualMedianMs = median(hotRuns.map((r) => r.visualMs));

  const allFps = [...coldRuns, ...hotRuns].map((r) => Math.round(r.avgFps));
  const allWorst = [...coldRuns, ...hotRuns].map((r) => Math.round(r.worstFrameMs));
  const fpsMedian = median(allFps);
  const worstFrameMedian = median(allWorst);

  // ── 寫出 JSON ──────────────────────────────────────────────────────────────
  const output = {
    label,
    head,
    cold: {
      median_ms: coldMedianMs,
      visual_median_ms: coldVisualMedianMs,
      runs: coldRuns,
    },
    hot: {
      median_ms: hotMedianMs,
      visual_median_ms: hotVisualMedianMs,
      runs: hotRuns,
    },
    fps: {
      median: fpsMedian,
      worst_frame_ms_median: worstFrameMedian,
    },
  };

  mkdirSync(path.dirname(outPath), { recursive: true });
  writeFileSync(outPath, JSON.stringify(output, null, 2), 'utf8');

  const summary =
    `[scan-measure] ${label} | HEAD=${head.slice(0, 8)} | ` +
    `冷跳中位數=${coldMedianMs}ms(視覺${coldVisualMedianMs}ms) | ` +
    `熱跳中位數=${hotMedianMs}ms(視覺${hotVisualMedianMs}ms) | ` +
    `FPS中位數=${fpsMedian} 最長幀中位數=${worstFrameMedian}ms`;
  console.log('\n' + summary);
  console.log(`\n結果已寫入 ${outPath}`);
});
