import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import {
  LucideCircleCheck,
  LucideCircleX,
  LucideInfo,
  LucideTriangleAlert,
  LucideX,
} from '@lucide/angular';
import { cn } from '../shared/utils';
import { OVERLAY_CLOSE_ICON_CLASS, OVERLAY_SURFACE_CLASS } from '../shared/component-styles';
import {
  OVERLAY_CLOSE_BUTTON_CLASS,
  TOAST_ACTION_BUTTON_CLASS,
  TOAST_DESCRIPTION_TEXT_CLASS,
  TOAST_ICON_CLASS,
  TOAST_SURFACE_CLASS,
  TOAST_TITLE_TEXT_CLASS,
} from './toast.styles';
import type { Toast, ToastAction, ToastType } from './toast.types';

const TYPE_ICON_CLASS: Partial<Record<ToastType, string>> = {
  success: 'text-[var(--sanring-success-40)]',
  error: 'text-[var(--sanring-error-40)]',
  warning: 'text-[var(--sanring-warn-40)]',
  info: 'text-[var(--sanring-info-40)]',
};

@Component({
  selector: 'sanring-toast',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideCircleCheck, LucideCircleX, LucideTriangleAlert, LucideInfo, LucideX],
  host: {
    // SR 播報由 ToastService 的 LiveAnnouncer 統一處理；
    // 這裡不再重複設 aria-live 或 role，避免重複播報。
    // Escape 鍵聚焦時可關閉 toast。
    '(keydown.escape)': 'dismissed.emit()',
  },
  template: `
    <div [class]="cardClass()" (animationend)="onAnimationEnd($event)">
      <!-- Type icon -->
      @switch (toast().type) {
        @case ('success') {
          <svg lucideCircleCheck [class]="iconClass()"></svg>
        }
        @case ('error') {
          <svg lucideCircleX [class]="iconClass()"></svg>
        }
        @case ('warning') {
          <svg lucideTriangleAlert [class]="iconClass()"></svg>
        }
        @case ('info') {
          <svg lucideInfo [class]="iconClass()"></svg>
        }
      }

      <!-- Text content -->
      <div class="flex min-w-0 flex-1 flex-col gap-0.5">
        @if (toast().title) {
          <p [class]="toastTitleClass">{{ toast().title }}</p>
        }
        @if (toast().description) {
          <p [class]="toastDescriptionClass">
            {{ toast().description }}
          </p>
        }
      </div>

      <!-- Optional action button -->
      @if (toast().action; as action) {
        <button type="button" [class]="actionBtnClass(action.class)" (click)="handleAction(action)">
          {{ action.label }}
        </button>
      }

      <!-- Dismiss button -->
      @if (toast().closable) {
        <button
          type="button"
          [class]="toastCloseButtonClass"
          [attr.aria-label]="dismissLabel()"
          (click)="dismissed.emit()"
        >
          <svg lucideX [class]="toastCloseIconClass"></svg>
        </button>
      }
    </div>
  `,
})
export class ToastComponent {
  protected readonly toastTitleClass = TOAST_TITLE_TEXT_CLASS;
  protected readonly toastDescriptionClass = TOAST_DESCRIPTION_TEXT_CLASS;
  protected readonly toastCloseButtonClass = OVERLAY_CLOSE_BUTTON_CLASS;
  protected readonly toastCloseIconClass = OVERLAY_CLOSE_ICON_CLASS;

  readonly toast = input.required<Toast>();
  /**
   * 進場動畫 class，由 ToasterComponent 根據 position 動態注入。
   * 預設對應 bottom-right（底部滑入）；單獨使用時可自行覆蓋。
   */
  /** 進場動畫 class，由 ToasterComponent 依 position 注入；單獨使用時可覆蓋 */
  readonly enterClass = input<string>('animate-toast-in-bottom');
  /** 關閉按鈕 aria-label，由 ToasterComponent 從 TOAST_CONFIG 注入以支援 i18n */
  readonly dismissLabel = input<string>('Dismiss notification');

  readonly dismissed = output<void>();
  /** 退場 CSS 動畫（animate-toast-leave）真的播完時觸發，讓外部知道可以真正移除這筆 toast */
  readonly leaveAnimationEnd = output<void>();

  protected readonly cardClass = computed(() =>
    cn(
      OVERLAY_SURFACE_CLASS,
      TOAST_SURFACE_CLASS,
      // leaving 時套退場動畫，否則套進場動畫（兩者互斥）
      this.toast().leaving ? 'animate-toast-leave' : this.enterClass(),
      this.toast().class,
    ),
  );

  protected readonly iconClass = computed(() =>
    cn(TOAST_ICON_CLASS, TYPE_ICON_CLASS[this.toast().type] ?? ''),
  );

  protected onAnimationEnd(event: AnimationEvent): void {
    if (event.target !== event.currentTarget || !this.toast().leaving) return;
    this.leaveAnimationEnd.emit();
  }

  protected actionBtnClass(extra?: string) {
    return cn(
      TOAST_ACTION_BUTTON_CLASS,
      extra,
    );
  }

  protected handleAction(action: ToastAction): void {
    const result = action.onClick();
    if (action.dismissOnAction !== false) {
      // async action：等 promise settle 再 dismiss；sync action：立即 dismiss
      if (result instanceof Promise) {
        result.finally(() => this.dismissed.emit());
      } else {
        this.dismissed.emit();
      }
    }
  }
}
