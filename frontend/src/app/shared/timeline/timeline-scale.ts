import { toDayNumber, fromDayNumber } from '../../core/dates';

/** 時間軸預設範圍（PRD §8.3）：1937-07-01～1945-09-30；起點可依資料最早日期往前延伸（§12 Q15 已拍板；WW1 試驗 1908 起靠事件最早日延伸）。 */
export const DEFAULT_RANGE = { start: '1937-07-01', end: '1945-09-30' } as const;
/** 早於此日的期間以淡色底標示「資料不保證完整」（憲法 §1、DESIGN.md Timeline） */
export const COMPLETE_FROM = '1937-07-01';

export interface Range {
  start: string;
  end: string;
}

export function rangeFor(earliestData: string | null | undefined): Range {
  const start = earliestData && earliestData < DEFAULT_RANGE.start ? earliestData : DEFAULT_RANGE.start;
  return { start, end: DEFAULT_RANGE.end };
}

/** 日期 → 0..1 比例 */
export function fraction(date: string, r: Range): number {
  const a = toDayNumber(r.start);
  const b = toDayNumber(r.end);
  return Math.min(1, Math.max(0, (toDayNumber(date) - a) / (b - a)));
}

/** 0..1 比例 → 日期（四捨五入到日） */
export function dateAt(f: number, r: Range): string {
  const a = toDayNumber(r.start);
  const b = toDayNumber(r.end);
  return fromDayNumber(Math.round(a + Math.min(1, Math.max(0, f)) * (b - a)));
}

export interface Tick {
  date: string;
  f: number;
  label?: string;
}

/** 年刻度；範圍很長（例：WW1 試驗 1908 起）時只每 N 年標年份，最多約 maxLabels 個（刻線照畫）。 */
/** `labelEvery` 指定時固定每 N 年標字（M3-a 方案 A：每 5 年一個文字刻度、每年一個小點）。 */
export function yearTicks(r: Range, maxLabels = 16, labelEvery?: number): Tick[] {
  const ticks: Tick[] = [];
  const y0 = +r.start.slice(0, 4);
  const y1 = +r.end.slice(0, 4);
  const step = labelEvery ?? [1, 2, 5, 10, 20, 50, 100].find((s) => (y1 - y0 + 1) / s <= maxLabels) ?? 100;
  for (let y = y0; y <= y1; y++) {
    const d = `${y}-01-01`;
    if (d >= r.start && d <= r.end) ticks.push({ date: d, f: fraction(d, r), label: y % step === 0 ? String(y) : undefined });
  }
  return ticks;
}

export function monthTicks(r: Range): Tick[] {
  const ticks: Tick[] = [];
  let y = +r.start.slice(0, 4);
  let m = +r.start.slice(5, 7);
  for (;;) {
    const d = `${y}-${String(m).padStart(2, '0')}-01`;
    if (d > r.end) break;
    if (d >= r.start && m !== 1) ticks.push({ date: d, f: fraction(d, r) });
    m++;
    if (m > 12) {
      m = 1;
      y++;
    }
  }
  return ticks;
}

/** 依目前日期找上一個／下一個快照日期（不含當日）。 */
export function prevSnapshotDate(dates: readonly string[], current: string): string | null {
  let best: string | null = null;
  for (const d of dates) if (d < current && (best === null || d > best)) best = d;
  return best;
}

export function nextSnapshotDate(dates: readonly string[], current: string): string | null {
  let best: string | null = null;
  for (const d of dates) if (d > current && (best === null || d < best)) best = d;
  return best;
}

/** 最近的快照日期（地圖 empty 時「跳到最近有資料的日期」用）。 */
export function nearestDate(dates: readonly string[], current: string): string | null {
  let best: string | null = null;
  let bestDist = Infinity;
  const c = toDayNumber(current);
  for (const d of dates) {
    const dist = Math.abs(toDayNumber(d) - c);
    if (dist < bestDist) {
      best = d;
      bestDist = dist;
    }
  }
  return best;
}
