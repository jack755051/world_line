import { isPlatformBrowser } from '@angular/common';
import { DestroyRef, Injectable, InjectionToken, NgZone, PLATFORM_ID, inject, signal } from '@angular/core';
import { gsap } from 'gsap';

/** UI 動畫時長（秒）。地圖圖層不透明度改用 MapLibre 自己的 paint transition（毫秒，見 AXIS_TRANSITION_MS）。 */
export const MOTION_DURATION = { fast: 0.18, base: 0.26 } as const;
/** 「實際控制」↔「主權」切換時地圖圖層不透明度的 MapLibre transition 時長（不是 GSAP）。 */
export const AXIS_TRANSITION_MS = 320;

/** ARCHITECTURE §17.3 數值表（秒；D0–D6 已決，Tai 2026-11-11 13:15）。開慢關快。 */
export const MOTION_SPEC = {
  dialog: { open: { duration: 0.24, ease: 'power2.out' }, close: { duration: 0.16, ease: 'power2.in' } },
  dialogMobile: { open: { duration: 0.26, ease: 'power3.out' }, close: { duration: 0.18, ease: 'power2.in' } },
  backdrop: { open: { duration: 0.2, ease: 'power1.out' }, close: { duration: 0.15, ease: 'power1.in' } },
  sheet: { open: { duration: 0.35, ease: 'expo.out' }, close: { duration: 0.2, ease: 'power2.in' } },
  /** reduced-motion 時彈窗只淡入（其餘直接切換）。 */
  reducedFade: { duration: 0.1, ease: 'power1.out' },
  /** 關閉動畫逾時保險：超過就強制卸載。 */
  closeTimeoutMs: 300,
} as const;

/** 全域時間倍率（1＝正常）。測試可提供 0：一律走終態、不建立動畫。 */
export const MOTION_TIME_SCALE = new InjectionToken<number>('MOTION_TIME_SCALE', { providedIn: 'root', factory: () => 1 });

const QUERY = '(prefers-reduced-motion: reduce)';

/** 目前是否要減少動態。沒有 matchMedia（SSR、jsdom）時當作「要減少」：不播動畫、直接到終態。 */
export function prefersReducedMotion(): boolean {
  return typeof window === 'undefined' || typeof window.matchMedia !== 'function' || window.matchMedia(QUERY).matches;
}

/** 每個屬性 `[from, to]`（from 為 null＝從目前值）或只給終值。 */
export type Keyframes = Record<string, unknown>;
export interface MotionOptions {
  duration?: number;
  ease?: string;
  /** 結束後清掉這次動到的 inline 樣式（開啟類動畫用；關閉類別用，否則卸載前會閃回）。 */
  clear?: boolean;
  transformOrigin?: string;
}
/** 元件不直接 import gsap：型別也由這裡轉出。 */
export type MotionTimeline = gsap.core.Timeline;
export type MotionTweenVars = gsap.TweenVars;
export interface MotionContext {
  /** 建立綁在這個 context 的暫停中 timeline（已套用全域時間倍率）。 */
  timeline(): MotionTimeline;
  revert(): void;
}

const TRANSFORM_KEYS = new Set(['x', 'y', 'xPercent', 'yPercent', 'scale', 'scaleX', 'scaleY', 'rotate', 'rotation', 'transform']);

/**
 * UI 動畫（GSAP core；ARCHITECTURE §17，D0 已決以 GSAP 取代 motion）。
 * 集中：reduced-motion 判斷、§17.3 時長／ease、時間倍率、gsap.context 輔助；所有 tween 在 NgZone 外跑。
 * 非瀏覽器、無 matchMedia（jsdom／Vitest）、使用者要求減少動態或時間倍率為 0 時一律直接到終態。
 * 測試可用 `{ provide: MotionService, useValue: fake }` 取代。
 */
@Injectable({ providedIn: 'root' })
export class MotionService {
  private readonly zone = inject(NgZone);
  private readonly browser = isPlatformBrowser(inject(PLATFORM_ID));
  /** 全域時間倍率（MOTION_TIME_SCALE）。 */
  readonly timeScale = inject(MOTION_TIME_SCALE);
  /** 即時反映系統設定（使用者切換「減少動態」時會更新）。 */
  readonly reduced = signal(!this.browser || prefersReducedMotion());
  private readonly pending = new WeakMap<Element, () => void>();

  constructor() {
    if (!this.browser || typeof window.matchMedia !== 'function') return;
    const mq = window.matchMedia(QUERY);
    const on = () => this.reduced.set(mq.matches);
    mq.addEventListener?.('change', on);
    inject(DestroyRef).onDestroy(() => mq.removeEventListener?.('change', on));
  }

  /** 環境能播動畫（瀏覽器、有 matchMedia、倍率 > 0）；不看 reduced-motion。 */
  canAnimate(): boolean {
    return this.browser && typeof window.matchMedia === 'function' && this.timeScale > 0;
  }

  /** 視窗寬度 ≥ md（768px）。 */
  isDesktop(): boolean {
    return this.browser && typeof window.matchMedia === 'function' && window.matchMedia('(min-width: 768px)').matches;
  }

  /**
   * 單一 tween：播放並在結束時 resolve；減少動態／不能播時立即 resolve、不改元素樣式。
   * 同一元素再呼叫會接手（舊的 promise 立即 resolve，不疊加）。只該傳 transform／opacity。
   */
  animate(el: Element, keyframes: Keyframes, opts: MotionOptions = {}): Promise<void> {
    if (this.reduced() || !this.canAnimate()) return Promise.resolve();
    const from: Record<string, unknown> = {};
    const to: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(keyframes)) {
      if (Array.isArray(v)) {
        if (v[0] != null) from[k] = v[0];
        to[k] = v[1];
      } else to[k] = v;
    }
    this.pending.get(el)?.();
    return new Promise<void>((resolve) => {
      const done = () => {
        if (this.pending.get(el) === done) this.pending.delete(el);
        resolve();
      };
      this.pending.set(el, done);
      const clear = opts.clear ? [...new Set(Object.keys(to).map((k) => (TRANSFORM_KEYS.has(k) ? 'transform' : k)))].join(',') : undefined;
      const vars: gsap.TweenVars = {
        ...to,
        duration: (opts.duration ?? MOTION_DURATION.base) / this.timeScale,
        ease: opts.ease ?? 'power2.out',
        overwrite: true,
        onComplete: done,
        ...(clear ? { clearProps: clear } : {}),
        ...(opts.transformOrigin ? { transformOrigin: opts.transformOrigin } : {}),
      };
      this.zone.runOutsideAngular(() => (Object.keys(from).length ? gsap.fromTo(el, from, vars) : gsap.to(el, vars)));
    });
  }

  /** 建立 gsap.context（scope＝元件根元素）；傳 DestroyRef 時銷毀自動 revert。 */
  context(scope: Element, destroyRef?: DestroyRef): MotionContext {
    const ctx = this.zone.runOutsideAngular(() => gsap.context(() => undefined, scope));
    destroyRef?.onDestroy(() => ctx.revert());
    return {
      timeline: () =>
        this.zone.runOutsideAngular(() => {
          let tl!: gsap.core.Timeline;
          ctx.add(() => (tl = gsap.timeline({ paused: true })));
          return tl.timeScale(this.timeScale || 1);
        }),
      revert: () => ctx.revert(),
    };
  }

  /** 在 Angular zone 外執行（動畫回呼不觸發變更偵測）。 */
  outside<T>(fn: () => T): T {
    return this.zone.runOutsideAngular(fn);
  }
  /** 回到 Angular zone（只用在「關閉動畫結束 → 卸載」這類狀態點）。 */
  inside<T>(fn: () => T): T {
    return this.zone.run(fn);
  }

  /** §17.2 P5 人物↔戰役頁轉場：只預留介面，目前 no-op。 */
  pageTransition(_from: Element | null, _to: Element | null): Promise<void> {
    return Promise.resolve();
  }
}
