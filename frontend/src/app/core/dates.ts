/**
 * 日期工具。資料一律用 `YYYY-MM-DD`（PRD §7），以 UTC 計算避免時區位移。
 * 歷史日期（1908–1945；WW1 試驗起 1908）一律記格里曆，不處理儒略曆（俄、希、保、塞等當時用儒略曆的日期，資料端已換算）。
 */
const ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

export function isIsoDate(value: string | null | undefined): value is string {
  if (!value) return false;
  const m = ISO.exec(value);
  if (!m) return false;
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return d.getUTCFullYear() === +m[1] && d.getUTCMonth() === +m[2] - 1 && d.getUTCDate() === +m[3];
}

export function toDayNumber(iso: string): number {
  const m = ISO.exec(iso);
  if (!m) throw new Error(`invalid date ${iso}`);
  return Math.round(Date.UTC(+m[1], +m[2] - 1, +m[3]) / 86_400_000);
}

export function fromDayNumber(day: number): string {
  const d = new Date(day * 86_400_000);
  const y = d.getUTCFullYear().toString().padStart(4, '0');
  const mo = (d.getUTCMonth() + 1).toString().padStart(2, '0');
  const da = d.getUTCDate().toString().padStart(2, '0');
  return `${y}-${mo}-${da}`;
}

export function addDays(iso: string, days: number): string {
  return fromDayNumber(toDayNumber(iso) + days);
}

/** 加減月份；目標月沒有該日時取月底（例：01-31 +1 月 → 02-28／29）。 */
export function addMonths(iso: string, months: number): string {
  const m = ISO.exec(iso);
  if (!m) throw new Error(`invalid date ${iso}`);
  const total = +m[1] * 12 + (+m[2] - 1) + months;
  const y = Math.floor(total / 12);
  const mo = total - y * 12;
  const last = new Date(Date.UTC(y, mo + 1, 0)).getUTCDate();
  const day = Math.min(+m[3], last);
  return `${y.toString().padStart(4, '0')}-${(mo + 1).toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
}

export function clampDate(iso: string, min: string, max: string): string {
  if (iso < min) return min;
  if (iso > max) return max;
  return iso;
}

const EN_MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

/** 頂部列大字日期（DESIGN.md：「1940年7月15日」）。 */
export function formatDisplayDate(iso: string, lang: 'zh-Hant' | 'en'): string {
  const m = ISO.exec(iso);
  if (!m) return iso;
  return lang === 'en' ? `${+m[3]} ${EN_MONTHS[+m[2] - 1]} ${m[1]}` : `${+m[1]}年${+m[2]}月${+m[3]}日`;
}
