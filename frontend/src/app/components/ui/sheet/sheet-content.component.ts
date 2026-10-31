import { CdkTrapFocus } from '@angular/cdk/a11y';
import { Overlay, OverlayContainer, OverlayRef } from '@angular/cdk/overlay';
import { Platform } from '@angular/cdk/platform';
import { TemplatePortal } from '@angular/cdk/portal';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  Injector,
  TemplateRef,
  ViewContainerRef,
  afterNextRender,
  booleanAttribute,
  computed,
  effect,
  inject,
  input,
  signal,
  untracked,
  viewChild,
  contentChild,
} from '@angular/core';
import { LucideX } from '@lucide/angular';
import { cn } from '../shared/utils';
import {
  OVERLAY_ABSOLUTE_CLOSE_BUTTON_CLASS,
  OVERLAY_CLOSE_ICON_CLASS,
  OVERLAY_SURFACE_CLASS,
} from '../shared/component-styles';
import { SHEET_LEAVE_DURATION_MS } from '../shared/component-timing';
import { SheetComponent } from './sheet.component';
import { SheetDescriptionComponent } from './sheet-description.component';
import { SheetTitleComponent } from './sheet-title.component';
import { OVERLAY_BACKDROP_CLASS, SHEET_SURFACE_CLASS } from './sheet.styles';
import type { SheetSide } from './sheet.type';

const SIDE_CLASSES: Record<SheetSide, string> = {
  top: 'inset-x-0 top-0 border-b border-[var(--sanring-border)]',
  bottom: 'inset-x-0 bottom-0 border-t border-[var(--sanring-border)]',
  left: 'inset-y-0 left-0 h-full w-3/4 border-r border-[var(--sanring-border)] sm:max-w-sm',
  right: 'inset-y-0 right-0 h-full w-3/4 border-l border-[var(--sanring-border)] sm:max-w-sm',
};

const SIDE_ENTER: Record<SheetSide, string> = {
  top: 'animate-sheet-in-top',
  bottom: 'animate-sheet-in-bottom',
  left: 'animate-sheet-in-left',
  right: 'animate-sheet-in-right',
};

const SIDE_LEAVE: Record<SheetSide, string> = {
  top: 'animate-sheet-out-top',
  bottom: 'animate-sheet-out-bottom',
  left: 'animate-sheet-out-left',
  right: 'animate-sheet-out-right',
};

@Component({
  selector: 'sanring-sheet-content',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CdkTrapFocus, LucideX],
  host: {
    '(document:keydown.escape)': 'onEscape()',
  },
  template: `
    <ng-template #contentTemplate>
      <div [class]="backdropClass()" aria-hidden="true" (click)="requestClose()"></div>

      <div
        #panelDiv
        tabindex="-1"
        cdkTrapFocus
        [cdkTrapFocus]="sheet.isOpen()"
        [id]="sheet.panelId"
        role="dialog"
        aria-modal="true"
        [attr.aria-label]="computedAriaLabel()"
        [attr.aria-labelledby]="computedAriaLabelledBy()"
        [attr.aria-describedby]="computedAriaDescribedBy()"
        [class]="panelClass()"
        (animationend)="onLeaveAnimationEnd($event)"
      >
        <ng-content></ng-content>

        @if (showClose()) {
          <button
            type="button"
            [attr.aria-label]="closeAriaLabel()"
            (click)="requestClose()"
            [class]="closeButtonClass"
          >
            <svg lucideX [class]="closeIconClass"></svg>
            <span class="sr-only">關閉</span>
          </button>
        }
      </div>
    </ng-template>
  `,
})
export class SheetContentComponent {
  protected readonly sheet = inject(SheetComponent);
  private readonly destroyRef = inject(DestroyRef);
  private readonly overlay = inject(Overlay);
  private readonly overlayContainer = inject(OverlayContainer);
  private readonly platform = inject(Platform);
  private readonly viewContainerRef = inject(ViewContainerRef);
  private readonly injector = inject(Injector);

  private readonly contentTemplateRef = viewChild.required<TemplateRef<unknown>>('contentTemplate');
  private readonly panelDiv = viewChild<ElementRef<HTMLElement>>('panelDiv');
  private readonly title = contentChild(SheetTitleComponent);
  private readonly description = contentChild(SheetDescriptionComponent);

  protected readonly closeButtonClass = OVERLAY_ABSOLUTE_CLOSE_BUTTON_CLASS;
  protected readonly closeIconClass = OVERLAY_CLOSE_ICON_CLASS;

  readonly side = input<SheetSide>('right');
  readonly class = input<string | undefined>();
  readonly showClose = input(true, { transform: booleanAttribute });
  readonly closeAriaLabel = input('關閉面板');
  /** Accessible-name fallback used when no SheetTitle is projected. */
  readonly ariaLabel = input<string | undefined>('Sheet');
  /** Explicit labelling relationship; takes precedence over SheetTitle and ariaLabel. */
  readonly ariaLabelledBy = input<string | undefined>();
  /** Explicit description relationship; takes precedence over SheetDescription. */
  readonly ariaDescribedBy = input<string | undefined>();

  protected readonly computedAriaLabelledBy = computed(
    () => this.ariaLabelledBy() ?? (this.title() ? this.sheet.titleId : null),
  );
  protected readonly computedAriaDescribedBy = computed(
    () => this.ariaDescribedBy() ?? (this.description() ? this.sheet.descId : null),
  );
  protected readonly computedAriaLabel = computed(() =>
    this.computedAriaLabelledBy() ? null : (this.ariaLabel() ?? null),
  );

  private readonly _leaving = signal(false);
  private _leaveTimer: ReturnType<typeof setTimeout> | undefined;

  // Portal 到 cdk-overlay-container（<body> 底下），避免祖先元素的 transform/filter/contain
  // 劫走 position:fixed 的 containing block，並讓 z-index 跟其他 CDK overlay 共用同一套堆疊管理。
  private overlayRef?: OverlayRef;
  private portal?: TemplatePortal;

  // 關閉後把焦點還給開啟它的元素，符合 WAI-ARIA dialog pattern 的要求
  private previouslyFocusedElement: HTMLElement | null = null;

  // 開啟期間把背景內容標成 aria-hidden，避免螢幕閱讀器使用者還能導覽到面板背後的內容
  private hiddenSiblings: Element[] = [];

  // 只有真的在瀏覽器鎖過 scroll 才需要在 destroy 時解鎖；afterNextRender 保證 scroll-lock
  // effect 的內容只會在瀏覽器執行，SSR 時這個旗標會一直是 false，onDestroy 就不會誤觸 document
  private _scrollLocked = false;
  private _previousBodyOverflow: string | null = null;
  private _previousBodyPaddingRight: string | null = null;

  /** Keep DOM visible during leave animation */
  protected readonly shouldDisplay = computed(() => this.sheet.isOpen() || this._leaving());

  constructor() {
    // Scroll lock: hold lock while visible (including leave phase). Deferred into
    // afterNextRender — window/document are real browser globals here (not the
    // injected DOCUMENT token), so touching them outside a browser-only callback
    // would throw during SSR.
    effect(() => {
      const locked = this.shouldDisplay();
      afterNextRender(
        () => {
          if (locked) {
            this.lockScroll();
          } else {
            this.unlockScroll();
          }
        },
        { injector: this.injector },
      );
    });

    // Attach/detach the overlay portal alongside visibility
    effect(() => {
      if (this.shouldDisplay()) {
        this.attachOverlay();
      } else {
        this.detachOverlay();
      }
    });

    // Focus panel when opened. afterNextRender 等的是「Angular 這輪 DOM 變更真的
    // commit 完」，跟 overlay portal 何時掛進 DOM 是同一個時間點，不像裸的
    // setTimeout(0) 只是賭一個任意 macrotask，遇到較慢的 attach 就可能撲空。
    effect(() => {
      if (this.sheet.isOpen()) {
        afterNextRender(() => this.panelDiv()?.nativeElement.focus(), { injector: this.injector });
      }
    });

    // Detect external isOpen → false and play leave animation
    let prevOpen = false;
    effect(() => {
      const isOpen = this.sheet.isOpen();
      untracked(() => {
        if (prevOpen && !isOpen && !this._leaving()) {
          this._startLeave();
        }
        prevOpen = isOpen;
      });
    });

    this.destroyRef.onDestroy(() => {
      clearTimeout(this._leaveTimer);
      this.unlockScroll();
      this.detachOverlay();
      this.overlayRef?.dispose();
    });
  }

  private lockScroll(): void {
    if (!this._scrollLocked) {
      this._previousBodyOverflow = document.body.style.overflow;
      this._previousBodyPaddingRight = document.body.style.paddingRight;
    }

    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.paddingRight = `${scrollbarWidth}px`;
    document.body.style.overflow = 'hidden';
    this._scrollLocked = true;
  }

  private unlockScroll(): void {
    if (!this._scrollLocked) return;

    document.body.style.overflow = this._previousBodyOverflow ?? '';
    document.body.style.paddingRight = this._previousBodyPaddingRight ?? '';
    this._previousBodyOverflow = null;
    this._previousBodyPaddingRight = null;
    this._scrollLocked = false;
  }

  protected onEscape(): void {
    if (this.sheet.isOpen()) this.requestClose();
  }

  /** Trigger close with leave animation (used by backdrop click & Escape in content) */
  protected requestClose(): void {
    if (this._leaving() || !this.sheet.isOpen()) return;
    this.sheet.setOpen(false);
    // isOpen change is picked up by the effect above
  }

  protected readonly backdropClass = computed(() =>
    cn(
      OVERLAY_BACKDROP_CLASS,
      this._leaving() ? 'animate-sheet-backdrop-out' : 'animate-sheet-backdrop-in',
    ),
  );

  protected readonly panelClass = computed(() => {
    const side = this.side();
    return cn(
      OVERLAY_SURFACE_CLASS,
      SHEET_SURFACE_CLASS,
      SIDE_CLASSES[side],
      this._leaving() ? SIDE_LEAVE[side] : SIDE_ENTER[side],
      this.class(),
    );
  });

  private attachOverlay(): void {
    this.overlayRef ??= this.overlay.create({
      scrollStrategy: this.overlay.scrollStrategies.noop(),
      positionStrategy: this.overlay.position().global(),
    });

    if (this.overlayRef.hasAttached()) return;

    // document.activeElement / document.body.children are raw browser globals
    // (not the injected DOCUMENT token) — guard for SSR, same reasoning as the
    // scroll-lock effect above.
    if (this.platform.isBrowser) {
      this.previouslyFocusedElement = document.activeElement as HTMLElement | null;
      this.hideBackgroundFromAssistiveTech();
    }

    this.portal ??= new TemplatePortal(this.contentTemplateRef(), this.viewContainerRef);
    this.overlayRef.attach(this.portal);
  }

  private detachOverlay(): void {
    if (!this.overlayRef?.hasAttached()) return;

    this.overlayRef.detach();
    this.restoreBackgroundFromAssistiveTech();
    this.previouslyFocusedElement?.focus();
    this.previouslyFocusedElement = null;
  }

  private hideBackgroundFromAssistiveTech(): void {
    const overlayContainerElement = this.overlayContainer.getContainerElement();
    this.hiddenSiblings = Array.from(document.body.children).filter(
      (el) => el !== overlayContainerElement && !el.hasAttribute('aria-hidden'),
    );
    for (const el of this.hiddenSiblings) {
      el.setAttribute('aria-hidden', 'true');
    }
  }

  private restoreBackgroundFromAssistiveTech(): void {
    for (const el of this.hiddenSiblings) {
      el.removeAttribute('aria-hidden');
    }
    this.hiddenSiblings = [];
  }

  /** 退場 CSS 動畫（animate-sheet-out-*）真的播完時觸發，是結束 leaving 狀態的主要途徑 */
  protected onLeaveAnimationEnd(event: AnimationEvent): void {
    if (event.target !== event.currentTarget || !this._leaving()) return;
    this._endLeave();
  }

  private _startLeave(): void {
    this._leaving.set(true);
    // 保底 timer：animationend 因故沒觸發時（例如動畫被中途打斷）避免卡在 leaving 狀態出不來
    this._leaveTimer = setTimeout(() => this._endLeave(), SHEET_LEAVE_DURATION_MS);
  }

  private _endLeave(): void {
    clearTimeout(this._leaveTimer);
    this._leaveTimer = undefined;
    this._leaving.set(false);
  }
}
