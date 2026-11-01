/**
 * 主權／衝突圖層的「變動區間」（GET /timeline/change-points）：相鄰兩個變動點之間每天的結果相同。
 * 日期一律 YYYY-MM-DD（四位數年份），字串比較即日期先後。
 */

/** date 所在區間的鍵（不大於 date 的最大變動點；比全部都早＝'-'）。沒有變動點資料時用日期本身。 */
export function intervalKey(points: readonly string[] | null, date: string): string {
  if (!points) return date;
  let lo = 0;
  let hi = points.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (points[mid] <= date) {
      ans = mid;
      lo = mid + 1;
    } else hi = mid - 1;
  }
  return ans >= 0 ? points[ans] : '-';
}

/** YYYY-MM-DD 加 n 天（UTC，不受時區影響）。 */
export function addDaysIso(date: string, n: number): string {
  const [y, m, d] = date.split('-').map(Number);
  const t = new Date(Date.UTC(y, m - 1, d + n));
  return `${String(t.getUTCFullYear()).padStart(4, '0')}-${String(t.getUTCMonth() + 1).padStart(2, '0')}-${String(t.getUTCDate()).padStart(2, '0')}`;
}

/** 區間前後相鄰各取一個日期（預先載入用，移植自 992baba）：next＝下一個變動點；prev＝本區間起點的前一天（第一個區間則 null）。 */
export function neighborDates(points: readonly string[], date: string): { prev: string | null; next: string | null } {
  const start = intervalKey(points, date);
  const next = points.find((d) => d > date) ?? null;
  return { prev: start === '-' ? null : addDaysIso(start, -1), next };
}

/** 有上限的 LRU 快取（移植自 992baba）：命中時移到最新，超過上限丟掉最久沒用的。 */
export class LruCache<T> {
  private readonly map = new Map<string, T>();
  constructor(readonly max: number) {}

  get(key: string): T | undefined {
    const v = this.map.get(key);
    if (v === undefined) return undefined;
    this.map.delete(key);
    this.map.set(key, v);
    return v;
  }

  has(key: string): boolean {
    return this.map.has(key);
  }

  set(key: string, value: T): void {
    this.map.delete(key);
    this.map.set(key, value);
    while (this.map.size > this.max) this.map.delete(this.map.keys().next().value as string);
  }

  get size(): number {
    return this.map.size;
  }
}
