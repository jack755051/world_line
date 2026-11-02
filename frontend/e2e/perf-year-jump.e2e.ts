/**
 * 前端跳年效能量測（Tai 2026-11-02）。
 * 預設 skip；設定環境變數 WL_PERF=1 才跑。
 * 跳年序列：1914-08-01 → 1942-11-01 → 1918-06-01 → 1939-09-01，共 3 跳，
 * 重複 3 次取中位數，結果 append 到 /tmp/wl_perf_report2.md。
 *
 * 用法：
 *   WL_PERF=1 npx playwright test perf-year-jump.e2e.ts
 *   WL_PERF=1 WL_PERF_LABEL="優化後" npx playwright test perf-year-jump.e2e.ts
 */
import { test, type Page } from '@playwright/test';
import { appendFileSync, existsSync, writeFileSync } from 'node:fs';

const SEQUENCE: [string, string][] = [
  ['1914-08-01', '1942-11-01'],
  ['1942-11-01', '1918-06-01'],
  ['1918-06-01', '1939-09-01'],
];

/** 等地圖就緒（data-ready-for === forDate && render=idle && no map-busy）；回傳等待毫秒。 */
async function waitMapReady(page: Page, forDate: string, timeout = 25000): Promise<number> {
  const t0 = Date.now();
  const area = page.getByTestId('map-area');
  const canvas = page.getByTestId('map-canvas');
  for (let i = 0; i < Math.ceil(timeout / 25); i++) {
    const [readyFor, render, busyCount] = await Promise.all([
      area.getAttribute('data-ready-for'),
      canvas.getAttribute('data-render'),
      page.getByTestId('map-busy').count(),
    ]);
    if (readyFor === forDate && render === 'idle' && busyCount === 0) return Date.now() - t0;
    await page.waitForTimeout(25);
  }
  return Date.now() - t0; // 超時仍回傳（不拋）
}

/** 執行一輪跳年序列，回傳各跳時間（ms）。 */
async function oneRun(page: Page): Promise<number[]> {
  const input = page.getByTestId('timeline-date-input');
  // 先回到起始日
  await input.fill('1914-08-01');
  await input.press('Enter');
  await waitMapReady(page, '1914-08-01', 25000);

  const times: number[] = [];
  for (const [, to] of SEQUENCE) {
    const t0 = Date.now();
    await input.fill(to);
    await input.press('Enter');
    await page.waitForTimeout(50); // 讓 Angular effect 觸發
    const elapsed = await waitMapReady(page, to, 25000);
    times.push(Date.now() - t0 - 50 + elapsed); // 加回等待前的 50ms
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

  const allRuns: number[][] = [];
  for (let r = 0; r < 3; r++) {
    allRuns.push(await oneRun(page));
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
