import { Injectable, signal } from '@angular/core';
import { isIsoDate } from './dates';
import type { Lang } from './i18n';

export type Axis = 'control' | 'sovereignty';

/**
 * 主地圖頁的全域狀態（PRD §5「前端狀態管理」：Signals＋Service，同步到 query string）。
 * URL 同步由 AtlasPage 負責（讀一次 query、之後以 replaceUrl 寫回）。
 */
@Injectable({ providedIn: 'root' })
export class AtlasState {
  /** C8／M0 的預設日期：1940-07-15（PRD §8.2 loading 文案、計畫 C8）。 */
  static readonly defaultDate = '1940-07-15';

  readonly date = signal(AtlasState.defaultDate);
  readonly axis = signal<Axis>('control');
  readonly lang = signal<Lang>('zh-Hant');
  readonly legendOpen = signal(true);

  setDate(value: string): boolean {
    if (!isIsoDate(value)) return false;
    this.date.set(value);
    return true;
  }
}

export interface ParsedQuery {
  date: string;
  lang: Lang;
  axis: Axis;
  invalidDate: boolean;
}

/** 解析 `?date=&axis=&lang=`；日期格式錯時回預設日期並標記 invalidDate（PRD §8.11）。 */
export function parseAtlasQuery(q: Record<string, string | undefined>): ParsedQuery {
  const rawDate = q['date'];
  const dateOk = isIsoDate(rawDate);
  return {
    date: dateOk ? rawDate : AtlasState.defaultDate,
    invalidDate: rawDate !== undefined && !dateOk,
    lang: q['lang'] === 'en' ? 'en' : 'zh-Hant',
    // 主權檢視尚未建置（無主權 API），一律回到實際控制
    axis: 'control',
  };
}
