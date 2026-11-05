import { ChangeDetectionStrategy, Component, ElementRef, Injector, afterNextRender, computed, effect, inject, input, output, signal, untracked, viewChild } from '@angular/core';
import { LucideX } from '@lucide/angular';
import { SheetComponent, SheetDescriptionComponent, SheetHeaderComponent, SheetTitleComponent } from '../../components/ui/sheet';
import { OVERLAY_ABSOLUTE_CLOSE_BUTTON_CLASS, OVERLAY_CLOSE_ICON_CLASS, OVERLAY_SURFACE_CLASS } from '../../components/ui/shared/component-styles';
import { cn } from '../../components/ui/shared/utils';
import { SHEET_SURFACE_CLASS } from '../../components/ui/sheet/sheet.styles';
import type { Lang } from '../../core/i18n';
import { MotionService } from '../../core/motion';

/** 進場／退場時長與曲線：照 sanring sheet（--animate-sheet-in-*：.35s cubic-bezier(.16,1,.3,1)；out：.2s ease-in）。 */
export const SHEET_MOTION = { in: { duration: 0.35, ease: [0.16, 1, 0.3, 1] }, out: { duration: 0.2, ease: 'easeIn' } } as const;
export type SheetState = 'closed' | 'opening' | 'open' | 'closing';

const SIDE_CLASS = {
  right: 'inset-y-0 right-0 h-full border-l border-[var(--sanring-border)]',
  bottom: 'inset-x-0 bottom-0 border-t border-[var(--sanring-border)]',
} as const;
const OFFSCREEN = { right: 'translateX(100%)', bottom: 'translateY(100%)' } as const;
const ONSCREEN = { right: 'translateX(0%)', bottom: 'translateY(0%)' } as const;

/**
 * 政權／衝突資訊的側邊面板（Tai 2026-10-31：參考 sanring UI Sheet 的外觀與互動）。
 * 外觀、標題／描述區、右上角關閉鈕都用 sanring sheet 的同一組 class 與 SheetHeader／Title／Description 元件；
 * 但 sanring 的 SheetContent 是 modal（背景遮罩、鎖捲動、焦點鎖、背景 aria-hidden），會擋住地圖與時間軸，
 * 這裡改成非 modal、放在地圖區內：地圖仍可點（換政權、點空白關閉）、時間軸仍可換日期。
 * 滑入／滑出用 motion，時長曲線同 sanring；prefers-reduced-motion 時直接出現／消失。
 */
@Component({
  selector: 'wl-regime-sheet',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent, SheetHeaderComponent, SheetTitleComponent, SheetDescriptionComponent, LucideX],
  host: { '(document:keydown.escape)': 'onEscape()' },
  template: `
    @if (visible()) {
      <sanring-sheet #s [isOpen]="open()">
        <section #panel data-testid="regime-sheet" role="dialog" aria-modal="false" tabindex="-1"
          [attr.aria-labelledby]="s.titleId" [attr.aria-describedby]="description() ? s.descId : null"
          [attr.data-side]="side()" [attr.data-state]="state()" [class]="panelClass()"
          [attr.data-size]="size()" [style.width.px]="side() === 'right' ? size() : null" [style.height.px]="side() === 'bottom' ? (dragSize() ?? size()) : null">
          <!-- §10 v2：右側面板寬度固定三檔，不再拖拉（Tai 2026-11-04） -->
          @if (side() === 'bottom') {
            <!-- bottom sheet 三段高度（96px／50vh／90vh）：點把手或上下拖切換 -->
            <button type="button" data-testid="regime-sheet-snap" [attr.data-snap]="snap()" [attr.aria-label]="snapLabel()"
              class="mx-auto flex h-11 w-full flex-none cursor-grab touch-none items-center justify-center" (pointerdown)="startSnapDrag($event)" (click)="cycleSnap()">
              <span class="h-1 w-8 rounded-full bg-wl-outline-variant"></span></button>
          }
          <sanring-sheet-header align="start" class="min-h-[56px] flex-none pr-8">
            <div class="flex min-w-0 flex-wrap items-baseline gap-x-2">
              <sanring-sheet-title [attr.data-testid]="titleTestId()">{{ title() }}</sanring-sheet-title>
              <!-- §10：標頭顯示首都（政權名稱、首都、關閉按鈕） -->
              @if (subtitle()) { <span data-testid="regime-sheet-capital" class="wl-text2 text-wl-on-surface-variant">{{ subtitle() }}</span> }
            </div>
            @if (description()) {
              <sanring-sheet-description data-testid="regime-sheet-description" [attr.lang]="descriptionLang() || null">{{ description() }}</sanring-sheet-description>
            }
          </sanring-sheet-header>
          <div data-testid="regime-sheet-body" class="flex min-h-0 flex-1 flex-col"><ng-content /></div>
          <button type="button" [attr.data-testid]="closeTestId()" [attr.aria-label]="closeLabel()" [class]="closeClass" (click)="closed.emit()">
            <svg lucideX [class]="closeIconClass"></svg>
          </button>
        </section>
      </sanring-sheet>
    }
  `,
})
export class RegimeSheet {
  readonly open = input(false);
  readonly side = input<'right' | 'bottom'>('right');
  /** 右側時是寬度、底部時是高度（px）。 */
  readonly size = input(384);
  /** 底部 bottom sheet 目前段位。 */
  readonly snap = input<'peek' | 'half' | 'full'>('half');
  readonly snapChange = output<'peek' | 'half' | 'full'>();
  readonly title = input('');
  readonly description = input('');
  /** 標頭第二資訊（政權的首都，§10）。 */
  readonly subtitle = input('');
  readonly descriptionLang = input('');
  readonly titleTestId = input('regime-sheet-title');
  readonly closeTestId = input('regime-sheet-close');
  readonly lang = input<Lang>('zh-Hant');
  /** 使用者按關閉鈕或 Esc。 */
  readonly closed = output<void>();
  /** 退場動畫結束、面板已移除。 */
  readonly hidden = output<void>();

  private readonly motion = inject(MotionService);
  private readonly injector = inject(Injector);
  private readonly panel = viewChild<ElementRef<HTMLElement>>('panel');
  protected readonly visible = signal(false);
  readonly state = signal<SheetState>('closed');
  private token = 0;

  protected readonly closeClass = OVERLAY_ABSOLUTE_CLOSE_BUTTON_CLASS;
  protected readonly closeIconClass = OVERLAY_CLOSE_ICON_CLASS;
  protected readonly closeLabel = computed(() => (this.lang() === 'en' ? 'Close panel' : '關閉面板'));
  protected readonly panelClass = computed(() => cn(OVERLAY_SURFACE_CLASS, SHEET_SURFACE_CLASS, 'absolute z-30 rounded-none outline-none', SIDE_CLASS[this.side()]));

  constructor() {
    effect(() => {
      const o = this.open();
      untracked(() => void (o ? this.enter() : this.leave()));
    });
  }

  private rendered(): Promise<void> {
    return new Promise((r) => afterNextRender(() => r(), { injector: this.injector }));
  }

  private async enter(): Promise<void> {
    const t = ++this.token;
    if (this.visible() && this.state() !== 'closing') return;
    const side = this.side();
    this.visible.set(true);
    this.state.set('opening');
    await this.rendered();
    const el = this.panel()?.nativeElement;
    if (t !== this.token || !el) return;
    el.focus({ preventScroll: true });
    await this.motion.animate(el, { transform: [OFFSCREEN[side], ONSCREEN[side]] }, SHEET_MOTION.in as never);
    if (t === this.token) this.state.set('open');
  }

  private async leave(): Promise<void> {
    if (!this.visible()) return;
    const t = ++this.token;
    const side = this.side();
    this.state.set('closing');
    const el = this.panel()?.nativeElement;
    if (el) await this.motion.animate(el, { transform: [ONSCREEN[side], OFFSCREEN[side]] }, SHEET_MOTION.out as never);
    if (t !== this.token) return;
    this.visible.set(false);
    this.state.set('closed');
    this.hidden.emit();
  }

  protected readonly snapLabel = computed(() => (this.lang() === 'en' ? 'Change panel height' : '切換面板高度'));
  private snapDragged = false;
  protected cycleSnap(): void {
    if (this.snapDragged) return void (this.snapDragged = false);
    const order = ['peek', 'half', 'full'] as const;
    this.snapChange.emit(order[(order.indexOf(this.snap()) + 1) % order.length]);
  }
  /** §12：拖拉時面板高度跟著手指，放開吸附到最接近的一段（peek／half／full）。 */
  protected readonly dragSize = signal<number | null>(null);
  readonly snapFor = input<((px: number) => 'peek' | 'half' | 'full') | null>(null);
  protected startSnapDrag(e: PointerEvent): void {
    const y0 = e.clientY;
    const h0 = this.size();
    this.snapDragged = false;
    const move = (ev: PointerEvent) => {
      const dy = ev.clientY - y0;
      if (Math.abs(dy) < 4 && this.dragSize() === null) return;
      this.dragSize.set(Math.max(48, h0 - dy));
    };
    const up = (ev: PointerEvent) => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
      window.removeEventListener('pointercancel', up);
      const dy = ev.clientY - y0;
      this.dragSize.set(null);
      if (Math.abs(dy) < 24) return;
      this.snapDragged = true;
      const pick = this.snapFor();
      if (pick) return void this.snapChange.emit(pick(h0 - dy));
      const order = ['peek', 'half', 'full'] as const;
      const i = order.indexOf(this.snap()) + (dy < 0 ? 1 : -1);
      this.snapChange.emit(order[Math.max(0, Math.min(2, i))]);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
    window.addEventListener('pointercancel', up);
  }

  protected onEscape(): void {
    if (this.open()) this.closed.emit();
  }
}
