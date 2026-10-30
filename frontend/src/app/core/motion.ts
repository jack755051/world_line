import { DestroyRef, Injectable, inject, signal } from '@angular/core';
import { animate } from 'motion';

/** UI 動畫時長（秒）。地圖圖層不透明度改用 MapLibre 自己的 paint transition（毫秒，見 AXIS_TRANSITION_MS）。 */
export const MOTION_DURATION = { fast: 0.18, base: 0.26 } as const;
/** 「實際控制」↔「主權」切換時地圖圖層不透明度的 MapLibre transition 時長。 */
export const AXIS_TRANSITION_MS = 320;

const QUERY = '(prefers-reduced-motion: reduce)';

/** 目前是否要減少動態。沒有 matchMedia（SSR、jsdom）時當作「要減少」：不播動畫、直接到終態。 */
export function prefersReducedMotion(): boolean {
  return typeof window === 'undefined' || typeof window.matchMedia !== 'function' || window.matchMedia(QUERY).matches;
}

export type Keyframes = Record<string, unknown>;
export interface MotionOptions {
  duration?: number;
  ease?: string | number[];
}

/**
 * UI 動畫（motion）。尊重 prefers-reduced-motion：使用者要求減少動態時不播放、立即完成。
 * 測試可用 `{ provide: MotionService, useValue: fake }` 取代。
 */
@Injectable({ providedIn: 'root' })
export class MotionService {
  /** 即時反映系統設定（使用者切換「減少動態」時會更新）。 */
  readonly reduced = signal(prefersReducedMotion());

  constructor() {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
    const mq = window.matchMedia(QUERY);
    const on = () => this.reduced.set(mq.matches);
    mq.addEventListener?.('change', on);
    inject(DestroyRef).onDestroy(() => mq.removeEventListener?.('change', on));
  }

  /** 播放並在結束時 resolve；減少動態時立即 resolve、不改元素樣式。 */
  async animate(el: Element, keyframes: Keyframes, opts: MotionOptions = {}): Promise<void> {
    if (this.reduced()) return;
    const controls = animate(el, keyframes as never, { duration: opts.duration ?? MOTION_DURATION.base, ease: (opts.ease ?? 'easeOut') as never });
    await controls.finished;
  }
}
