/**
 * 前端跳年效能量測（Tai 2026-11-02）。
 * 預設 skip；設定環境變數 WL_PERF=1 才跑。
 * 跳年序列：1914-08-01 → 1942-11-01 → 1918-06-01 → 1939-09-01，共 3 跳，
 * 重複 3 次取中位數，結果 append 到 /tmp/wl_perf_report2.md。
 *
 * 設定 WL_PERF_PHASES=1 可額外在 console 輸出各分段耗時（需後端開啟）。
 * 各分段由 atlas-map.ts 的 [wl:perf:sov] console.log 提供：
 *   fetch=API 回應、signal=JSON解析+快取、effect=Angular reactivity、
 *   setdata=setData dispatch、worker=MapLibre Worker+GPU render
 *
 * 用法：
 *   WL_PERF=1 npx playwright test perf-year-jump.e2e.ts
 *   WL_PERF=1 WL_PERF_LABEL="優化後" npx playwright test perf-year-jump.e2e.ts
 *   WL_PERF=1 WL_PERF_PHASES=1 WL_PERF_LABEL="分段量測" npx playwright test perf-year-jump.e2e.ts
 */
import { test, type Page } from '@playwright/test';
import { appendFileSync, existsSync, writeFileSync } from 'node:fs';

const SEQUENCE: [string, string][] = [
  ['1914-08-01', '1942-11-01'],
  ['1942-11-01', '1918-06-01'],
  ['1918-06-01', '1939-09-01'],
];

/**
 * 等地圖就緒（data-ready-for === forDate）；回傳等待毫秒。
 * 量測終點：新日期國界已畫完（mapReady = loadsStartedFor===date && !mapDataLoading && !mapRenderBusy），
 * 不等蒙版淡出動畫（舊版等 map-busy 消失導致多計 220ms）。
 */
async function waitMapReady(page: Page, forDate: string, timeout = 25000): Promise<number> {
  const t0 = Date.now();
  const area = page.getByTestId('map-area');
  for (let i = 0; i < Math.ceil(timeout / 25); i++) {
    if ((await area.getAttribute('data-ready-for')) === forDate) return Date.now() - t0;
    await page.waitForTimeout(25);
  }
  return Date.now() - t0; // 超時仍回傳（不拋）
}

/** 執行一輪跳年序列，回傳各跳時間（ms）。若 capturePhases=true 則同時收集分段 console 訊息。 */
async function oneRun(page: Page, capturePhases = false): Promise<number[]> {
  const input = page.getByTestId('timeline-date-input');
  const phases: string[] = [];
  const listener = (msg: import('@playwright/test').ConsoleMessage) => {
    if (msg.text().startsWith('[wl:perf:sov]')) phases.push(msg.text());
  };
  if (capturePhases) page.on('console', listener);

  // 先回到起始日
  await input.fill('1914-08-01');
  await input.press('Enter');
  await waitMapReady(page, '1914-08-01', 25000);

  const times: number[] = [];
  for (const [, to] of SEQUENCE) {
    const t0 = Date.now();
    await input.fill(to);
    await input.press('Enter');
    // 量測從 fill+Enter 完成到 mapReady（data-ready-for===to）的總時間
    await waitMapReady(page, to, 25000);
    times.push(Date.now() - t0);
  }

  if (capturePhases) {
    page.off('console', listener);
    for (const p of phases) console.log('  📊', p);
  }
  return times;
}

function median(vals: number[]): number {
  const s = [...vals].sort((a, b) => a - b);
  return s[Math.floor(s.length / 2)];
}

test('perf: year jump median (3 runs)', async ({ page }) => {
  if (!process.env['WL_PERF']) {
    test.skip(true, '設定 WL_PERF=1 才執行效能量測');
  }
  test.setTimeout(600_000);

  await page.goto('/?date=1914-08-01&axis=sovereignty');
  await page.getByTestId('map-canvas').waitFor({ state: 'visible' });
  // 等第一次就緒（冷快取可能較慢）
  await waitMapReady(page, '1914-08-01', 30000);

  const capturePhases = !!process.env['WL_PERF_PHASES'];
  const allRuns: number[][] = [];
  for (let r = 0; r < 3; r++) {
    if (capturePhases) console.log(`\n--- run ${r + 1} ---`);
    allRuns.push(await oneRun(page, capturePhases));
  }

  const medians = SEQUENCE.map((_, i) => median(allRuns.map((run) => run[i])));

  const label = process.env['WL_PERF_LABEL'] ?? '量測';
  const rows = SEQUENCE.map(
    ([from, to], i) =>
      `| ${from} → ${to} | ${allRuns.map((r) => r[i]).join(' / ')} | **${medians[i]}** |`,
  );
  const report = [
    `\n## ${label} (${new Date().toISOString()})`,
    '',
    '| 跳年 | 各次 ms (r1 / r2 / r3) | 中位數 ms |',
    '|------|------------------------|-----------|',
    ...rows,
    '',
  ].join('\n');

  const reportPath = '/tmp/wl_perf_report2.md';
  if (!existsSync(reportPath)) writeFileSync(reportPath, '# World Line 跳年效能報告\n', 'utf8');
  appendFileSync(reportPath, report, 'utf8');

  for (const [i, [from, to]] of SEQUENCE.entries()) {
    console.log(JSON.stringify({ from, to, medianMs: medians[i], runs: allRuns.map((r) => r[i]) }));
  }
  console.log('\n--- 完整報告已 append 至', reportPath, '---');
});
