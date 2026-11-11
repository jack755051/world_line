import { Injectable, signal } from '@angular/core';
import type { Axis } from './atlas-state';
import type { Lang } from './i18n';

/**
 * §19.2.5 雙向跳轉：地圖 → 戰役頁時存的返回快照。
 * 放在記憶體 service（同一個分頁內有效），同時寫進 history.state（重新整理戰役頁後按瀏覽器上一頁仍可還原）。
 * 返回目標只存一格：戰役 → 戰役時覆寫、不累加（沿用 §14.4）。捲動位置只在快照裡，不進 URL（Q4＝b）。
 */
export interface ReturnSnapshot {
  route: 'atlas';
  date: string;
  lang: Lang;
  axis: Axis;
  camera: { center: [number, number]; zoom: number; bearing: number } | null;
  regimeId: string | null;
  sheetTab: string | null;
  sheetScrollTop: number | null;
  personId?: string | null;
}

export const RETURN_STATE_KEY = 'wlReturn';

export function isReturnSnapshot(v: unknown): v is ReturnSnapshot {
  const s = v as ReturnSnapshot | null;
  return !!s && s.route === 'atlas' && typeof s.date === 'string';
}

/** 讀目前 history entry 上的快照（沒有就回 null）。 */
export function snapshotFromHistory(): ReturnSnapshot | null {
  if (typeof history === 'undefined') return null;
  const v = (history.state as Record<string, unknown> | null)?.[RETURN_STATE_KEY];
  return isReturnSnapshot(v) ? v : null;
}

/** 返回地圖用的 query params（date、lang、axis、regime、tab；跟 Q4＝b 的 URL 一致）。 */
export function atlasQueryFor(s: Pick<ReturnSnapshot, 'date' | 'lang' | 'axis' | 'regimeId' | 'sheetTab'>): Record<string, string | null> {
  return {
    date: s.date,
    lang: s.lang === 'en' ? 'en' : null,
    axis: s.axis === 'sovereignty' ? 'sovereignty' : null,
    regime: s.regimeId,
    tab: s.regimeId && s.sheetTab && s.sheetTab !== 'overview' ? s.sheetTab : null,
  };
}

@Injectable({ providedIn: 'root' })
export class CampaignReturn {
  /** 唯一一格。 */
  readonly slot = signal<ReturnSnapshot | null>(null);
  /** 地圖頁剛被還原過的快照：只用一次。 */
  private pendingRestore: ReturnSnapshot | null = null;

  save(s: ReturnSnapshot): void {
    this.slot.set(s);
  }
  /** 戰役頁按「返回」或瀏覽器上一頁：交給地圖頁還原一次。 */
  armRestore(s: ReturnSnapshot): void {
    this.pendingRestore = s;
  }
  /** 地圖頁建立時取用：記憶體優先，其次 history.state。 */
  takeRestore(): ReturnSnapshot | null {
    const s = this.pendingRestore ?? snapshotFromHistory();
    this.pendingRestore = null;
    this.slot.set(null); // 回到地圖後返回目標失效；之後直接開戰役 URL 時顯示「開啟地圖」
    return s;
  }
  clear(): void {
    this.slot.set(null);
    this.pendingRestore = null;
  }
}
