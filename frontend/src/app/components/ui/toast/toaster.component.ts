import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { cn } from '../shared/utils';
import { TOAST_CONFIG } from './toast.config';
import { ToastComponent } from './toast.component';
import { ToastService } from './toast.service';
import type { ToastPosition } from './toast.types';

const POSITION_CLASSES: Record<ToastPosition, string> = {
  'top-right': 'top-4 right-4',
  'top-left': 'top-4 left-4',
  'top-center': 'top-4 left-1/2 -translate-x-1/2',
  'bottom-right': 'bottom-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
};

// 使用 styles.css @theme 定義的自定義動畫（不依賴 tailwindcss-animate）
const ENTER_CLASS: Record<ToastPosition, string> = {
  'top-right':     'animate-toast-in-top',
  'top-left':      'animate-toast-in-top',
  'top-center':    'animate-toast-in-top',
  'bottom-right':  'animate-toast-in-bottom',
  'bottom-left':   'animate-toast-in-bottom',
  'bottom-center': 'animate-toast-in-bottom',
};

const DEFAULT_TOAST_HEIGHT = 72;
const PEEK_PX = 12;

@Component({
  selector: 'sanring-toaster',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ToastComponent],
  // SR 播報由 ToastService 的 LiveAnnouncer 統一處理，不在 DOM 設 aria-live，
  // 避免 LiveAnnouncer + DOM live region 雙重播報。
  template: `
    @if (stacked()) {
      <div
        [class]="stackWrapperClass()"
        [style.height.px]="stackHeight()"
        (mouseenter)="toastSvc.pauseAll()"
        (mouseleave)="toastSvc.resumeAll()"
      >
        @for (toast of stackedToasts(); track toast.id; let i = $index) {
          <div
            class="absolute inset-x-0 transition-all duration-300 ease-out"
            [style.z-index]="maxToasts() - i"
            [style.bottom.px]="isBottom() ? i * peekPx : undefined"
            [style.top.px]="isBottom() ? undefined : i * peekPx"
            [style.transform]="stackScale(i)"
            [style.opacity]="stackOpacity(i)"
          >
            <sanring-toast
              [toast]="toast"
              [enterClass]="enterClass()"
              [dismissLabel]="dismissLabel()"
              (dismissed)="toastSvc.dismiss(toast.id)"
              (leaveAnimationEnd)="toastSvc.completeLeave(toast.id)"
            />
          </div>
        }
      </div>
    } @else {
      <div
        [class]="listWrapperClass()"
        (mouseenter)="toastSvc.pauseAll()"
        (mouseleave)="toastSvc.resumeAll()"
      >
        @for (toast of listToasts(); track toast.id) {
          <sanring-toast
            [toast]="toast"
            [enterClass]="enterClass()"
            (dismissed)="toastSvc.dismiss(toast.id)"
            (leaveAnimationEnd)="toastSvc.completeLeave(toast.id)"
          />
        }
      </div>
    }
  `,
})
export class ToasterComponent {
  readonly position = input<ToastPosition>('bottom-right');
  readonly maxToasts = input<number>(3);
  readonly stacked = input<boolean>(true);
  readonly toastHeight = input<number>(DEFAULT_TOAST_HEIGHT);

  protected readonly peekPx = PEEK_PX;
  protected readonly toastSvc = inject(ToastService);
  private readonly toastConfig = inject(TOAST_CONFIG);
  /** 從 TOAST_CONFIG 取得關閉按鈕 aria-label，統一支援 i18n 覆蓋 */
  protected readonly dismissLabel = computed(() => this.toastConfig.dismissLabel);

  protected readonly isBottom = computed(() => this.position().startsWith('bottom'));
  protected readonly enterClass = computed(() => ENTER_CLASS[this.position()]);

  protected readonly stackedToasts = computed(() =>
    [...this.toastSvc.toasts()].slice(-this.maxToasts()).reverse(),
  );

  protected readonly listToasts = computed(() => {
    const all = this.toastSvc.toasts();
    return this.isBottom() ? all : [...all].reverse();
  });

  protected readonly stackHeight = computed(
    () => this.toastHeight() + (this.stackedToasts().length - 1) * PEEK_PX,
  );

  private readonly positionClass = computed(() => POSITION_CLASSES[this.position()]);

  protected readonly stackWrapperClass = computed(() =>
    cn('fixed z-50 w-full max-w-sm pointer-events-none', this.positionClass()),
  );

  protected readonly listWrapperClass = computed(() =>
    cn(
      'fixed z-50 flex w-full max-w-sm gap-2 p-4 pointer-events-none',
      this.isBottom() ? 'flex-col' : 'flex-col-reverse',
      this.positionClass(),
    ),
  );

  protected stackScale(i: number): string {
    return i === 0 ? 'none' : `scale(${(1 - i * 0.04).toFixed(3)})`;
  }

  protected stackOpacity(i: number): number {
    return i === 0 ? 1 : Math.max(0.4, 1 - i * 0.2);
  }
}
