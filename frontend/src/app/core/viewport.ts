import { DestroyRef, Injectable, computed, inject, signal } from '@angular/core';
import { DOCUMENT } from '@angular/common';

/**
 * RWD 斷點（ARCHITECTURE.md §12）：xs 360–599、sm 600–767、md 768–1023、lg 1024–1439、xl ≥1440。
 * 另外：視窗高度小於 500px（手機橫放）時頂列與時間軸改成精簡版。
 * 觸控判斷用 `(hover: none) and (pointer: coarse)`，不用螢幕寬度。
 */
export type Breakpoint = 'xs' | 'sm' | 'md' | 'lg' | 'xl';
export const BREAKPOINTS = { sm: 600, md: 768, lg: 1024, xl: 1440 } as const;
export const COMPACT_HEIGHT = 500;
export const TOUCH_QUERY = '(hover: none) and (pointer: coarse)';

export function breakpointOf(w: number): Breakpoint {
  if (w >= BREAKPOINTS.xl) return 'xl';
  if (w >= BREAKPOINTS.lg) return 'lg';
  if (w >= BREAKPOINTS.md) return 'md';
  if (w >= BREAKPOINTS.sm) return 'sm';
  return 'xs';
}
/** 手機版（xs、sm）。 */
export function isPhone(bp: Breakpoint): boolean {
  return bp === 'xs' || bp === 'sm';
}
/** 精簡版頂列／時間軸：手機寬度，或視窗高度小於 500px。 */
export function isCompact(w: number, h: number): boolean {
  return isPhone(breakpointOf(w)) || (h > 0 && h < COMPACT_HEIGHT);
}

@Injectable({ providedIn: 'root' })
export class ViewportService {
  private readonly doc = inject(DOCUMENT);
  private readonly win = this.doc.defaultView;
  readonly width = signal(this.win?.innerWidth ?? 1280);
  readonly height = signal(this.win?.innerHeight ?? 800);
  readonly touch = signal(!!this.win?.matchMedia?.(TOUCH_QUERY).matches);
  readonly bp = computed(() => breakpointOf(this.width()));
  readonly phone = computed(() => isPhone(this.bp()));
  readonly compact = computed(() => isCompact(this.width(), this.height()));

  constructor() {
    const w = this.win;
    if (!w) return;
    const onResize = () => {
      this.width.set(w.innerWidth);
      this.height.set(w.innerHeight);
    };
    w.addEventListener('resize', onResize);
    const mq = w.matchMedia?.(TOUCH_QUERY);
    const onMq = (e: MediaQueryListEvent) => this.touch.set(e.matches);
    mq?.addEventListener?.('change', onMq);
    inject(DestroyRef).onDestroy(() => {
      w.removeEventListener('resize', onResize);
      mq?.removeEventListener?.('change', onMq);
    });
  }
}
