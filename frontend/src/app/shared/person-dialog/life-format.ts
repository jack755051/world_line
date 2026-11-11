import type { Lang } from '../../core/i18n';

type Precision = 'day' | 'month' | 'year' | null | undefined;

/** 傳記式生卒（人物彈窗版頭）：大字年份、小字「生於…卒於…」、享年。 */
export interface LifeText {
  /** 大字：`1874 – 1965`、`1874 –`、`– 1965`；生卒都沒有＝空字串（不顯示區塊）。 */
  years: string;
  /** 「1874年11月30日」／「30 November 1874」；依精度，不補造月日。 */
  born: string;
  died: string;
  /** 享年：生卒兩端都精確到日才寫；否則空字串（不寫「約」，避免假裝精確）。 */
  age: string;
}

const MONTHS_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

interface Ymd { y: number; m: number; d: number; p: 'day' | 'month' | 'year' }

/** 解析日期；精度未標時，完整 YYYY-MM-DD 視為日（與 formatPartialDate 一致）。 */
function parse(date: string | null | undefined, precision: Precision): Ymd | null {
  const mt = /^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?/.exec(date ?? '');
  if (!mt) return null;
  const y = +mt[1], m = +(mt[2] ?? 0), d = +(mt[3] ?? 0);
  let p: Ymd['p'] = precision ?? (d ? 'day' : m ? 'month' : 'year');
  if (p === 'day' && !d) p = m ? 'month' : 'year';
  if (p === 'month' && !m) p = 'year';
  return { y, m, d, p };
}

function fmt(x: Ymd, lang: Lang): string {
  if (lang === 'en') {
    if (x.p === 'year') return `${x.y}`;
    if (x.p === 'month') return `${MONTHS_EN[x.m - 1]} ${x.y}`;
    return `${x.d} ${MONTHS_EN[x.m - 1]} ${x.y}`;
  }
  if (x.p === 'year') return `${x.y}年`;
  if (x.p === 'month') return `${x.y}年${x.m}月`;
  return `${x.y}年${x.m}月${x.d}日`;
}

/** 滿歲：卒日未到當年生日就減一；卒日即生日算已滿。 */
export function ageAtDeath(born: { y: number; m: number; d: number }, died: { y: number; m: number; d: number }): number {
  const before = died.m < born.m || (died.m === born.m && died.d < born.d);
  return died.y - born.y - (before ? 1 : 0);
}

export function lifeText(birthDate: string | null | undefined, birthPrecision: Precision, deathDate: string | null | undefined, deathPrecision: Precision, lang: Lang): LifeText {
  const b = parse(birthDate, birthPrecision);
  const d = parse(deathDate, deathPrecision);
  const years = b && d ? `${b.y} – ${d.y}` : b ? `${b.y} –` : d ? `– ${d.y}` : '';
  let age = '';
  if (b && d && b.p === 'day' && d.p === 'day') {
    const n = ageAtDeath(b, d);
    if (n >= 0) age = lang === 'en' ? `aged ${n}` : `享年 ${n} 歲`;
  }
  return { years, born: b ? fmt(b, lang) : '', died: d ? fmt(d, lang) : '', age };
}
