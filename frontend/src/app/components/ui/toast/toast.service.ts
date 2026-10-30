import { Injectable, inject, signal } from '@angular/core';
import { LiveAnnouncer, _IdGenerator } from '@angular/cdk/a11y';
import { TOAST_CONFIG } from './toast.config';
import type { Toast, ToastOptions } from './toast.types';
import { TOAST_LEAVE_FALLBACK_MS } from '../shared/component-timing';

/**
 * Headless 設計：不帶 providedIn，由消費端決定 scope。
 *
 * 全域 toast（最常見）：
 *   // app.config.ts
 *   providers: [ToastService]
 *
 * 局部 toast（功能模組/獨立 widget）：
 *   @Component({ providers: [ToastService] })
 *   export class FeatureComponent { }
 */
@Injectable()
export class ToastService {
  private readonly announcer = inject(LiveAnnouncer);
  private readonly config = inject(TOAST_CONFIG);
  private readonly idGenerator = inject(_IdGenerator);
  private readonly _toasts = signal<Toast[]>([]);

  // Auto-dismiss timer tracking (three maps for pause/resume support):
  private readonly _timers = new Map<string, ReturnType<typeof setTimeout>>();
  private readonly _startedAt = new Map<string, number>();
  private readonly _remaining = new Map<string, number>();
  // Leaving-animation fallback timers: keyed by id. Normally superseded by
  // completeLeave() firing from the component's animationend handler first.
  private readonly _leavingTimers = new Map<string, ReturnType<typeof setTimeout>>();

  readonly toasts = this._toasts.asReadonly();

  show(options: ToastOptions): string {
    const id = this.idGenerator.getId('sanring-toast-', true);
    const toast: Toast = {
      type: 'default',
      duration: this.config.defaultDuration,
      closable: true,
      ...options,
      id,
    };

    this._toasts.update((prev) => {
      const next = [...prev, toast];
      if (next.length > this.config.maxVisible) {
        next.slice(0, next.length - this.config.maxVisible).forEach((t) => this._clearTimer(t.id));
        return next.slice(next.length - this.config.maxVisible);
      }
      return next;
    });

    // LiveAnnouncer 是唯一的 SR 播報層，DOM 不再設 aria-live
    const label = [toast.title, toast.description].filter(Boolean).join(' — ');
    if (label) {
      this.announcer.announce(label, toast.type === 'error' ? 'assertive' : 'polite');
    }

    if (toast.duration > 0) this._startTimer(id, toast.duration);

    return id;
  }

  success(title: string, options?: Omit<ToastOptions, 'type' | 'title'>): string {
    return this.show({ ...options, title, type: 'success' });
  }

  error(title: string, options?: Omit<ToastOptions, 'type' | 'title'>): string {
    return this.show({ ...options, title, type: 'error' });
  }

  warning(title: string, options?: Omit<ToastOptions, 'type' | 'title'>): string {
    return this.show({ ...options, title, type: 'warning' });
  }

  info(title: string, options?: Omit<ToastOptions, 'type' | 'title'>): string {
    return this.show({ ...options, title, type: 'info' });
  }

  dismiss(id: string): void {
    this._clearTimer(id);
    // 1. 標記 leaving → 觸發退場 CSS 動畫（animate-toast-leave）
    this._toasts.update((prev) => prev.map((t) => (t.id === id ? { ...t, leaving: true } : t)));
    // 2. 主要路徑：ToastComponent 偵測到 animationend 後呼叫 completeLeave() 真正移除。
    //    這個 timer 只是它因故沒觸發時的保底機制，避免卡在 leaving 狀態出不來。
    const handle = setTimeout(() => this.completeLeave(id), TOAST_LEAVE_FALLBACK_MS);
    this._leavingTimers.set(id, handle);
  }

  /** 退場 CSS 動畫真的播完時由 ToastComponent 呼叫；也是保底 timer 到期時的呼叫對象 */
  completeLeave(id: string): void {
    const handle = this._leavingTimers.get(id);
    if (handle !== undefined) clearTimeout(handle);
    this._leavingTimers.delete(id);
    this._toasts.update((prev) => prev.filter((t) => t.id !== id));
  }

  dismissAll(): void {
    // 取消所有進行中的退場動畫計時器
    this._leavingTimers.forEach((handle) => clearTimeout(handle));
    this._leavingTimers.clear();
    // 合併 _timers 與 _remaining 的 id，確保 paused 狀態下也能全部清除
    const allIds = new Set([...this._timers.keys(), ...this._remaining.keys()]);
    allIds.forEach((id) => this._clearTimer(id));
    this._toasts.set([]);
  }

  /** Hover 開始時呼叫：暫停所有 timer，記錄剩餘時間 */
  pauseAll(): void {
    const now = Date.now();
    this._timers.forEach((handle, id) => {
      clearTimeout(handle);
      const startedAt = this._startedAt.get(id) ?? now;
      const remaining = this._remaining.get(id) ?? 0;
      this._remaining.set(id, Math.max(0, remaining - (now - startedAt)));
    });
    this._timers.clear();
    this._startedAt.clear();
  }

  /** Hover 結束時呼叫：用剩餘時間重啟 timer */
  resumeAll(): void {
    this._remaining.forEach((remaining, id) => {
      if (remaining > 0) this._startTimer(id, remaining);
    });
  }

  private _startTimer(id: string, duration: number): void {
    const handle = setTimeout(() => this.dismiss(id), duration);
    this._timers.set(id, handle);
    this._startedAt.set(id, Date.now());
    this._remaining.set(id, duration);
  }

  private _clearTimer(id: string): void {
    const handle = this._timers.get(id);
    if (handle !== undefined) clearTimeout(handle);
    this._timers.delete(id);
    this._startedAt.delete(id);
    this._remaining.delete(id);
  }
}
