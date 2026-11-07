import { addDays, isIsoDate } from './dates';
import type { Lang } from './i18n';
import type { LeaderPortrait } from './api/world-line-api';

/** 照片授權允許清單（與後端 CitationPolicy.PrimaryLicenseAllowlist 相同）。 */
export const PORTRAIT_LICENSES: ReadonlySet<string> = new Set(['us_federal_pd', 'pd_expired', 'cc0', 'cc_by', 'cc_by_sa']);

/** 照片可顯示：授權在允許清單，且出處頁、署名、查證日期都有。否則前端一律顯示中性佔位圖。 */
export function portraitDisplayable(p: LeaderPortrait | null | undefined): p is LeaderPortrait {
  return !!p && !!p.url && /^https:\/\//.test(p.url) && !!p.sourceUrl && !!p.attribution && !!p.retrievedOn && PORTRAIT_LICENSES.has(p.licenseCode);
}

/** 依精度顯示日期（year → 1913、month → 1935-12、day/未知 → 1882-01-30）。不補造月日。 */
export function formatPartialDate(date: string | null | undefined, precision: 'day' | 'month' | 'year' | null | undefined): string {
  if (!date) return '';
  if (precision === 'year') return date.slice(0, 4);
  if (precision === 'month') return date.slice(0, 7);
  return date.slice(0, 10);
}

/** 半開區間 [start, end) 的最後一天（end − 1 天）；end 為空回傳 null。 */
export function inclusiveEnd(end: string | null | undefined): string | null {
  if (!end || !isIsoDate(end)) return null;
  return addDays(end, -1);
}

/** 任期顯示：「1933-01-30 – 1945-04-29」；迄日不含當天；沒有迄日時顯示「迄今不明」。 */
export function formatTerm(p: { start: string | null; end: string | null }, lang: Lang): string {
  const last = inclusiveEnd(p.end);
  const open = lang === 'en' ? 'end unknown' : '迄今不明';
  return `${p.start ?? '…'} – ${last ?? open}`;
}

/** 依語言取雙語欄位（沒有就用另一語言）。 */
export function pickLocalized(field: Record<string, string | undefined> | null | undefined, lang: Lang): string {
  if (!field) return '';
  return (lang === 'en' ? field['en'] || field['zh-Hant'] : field['zh-Hant'] || field['en']) ?? '';
}
