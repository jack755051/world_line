import { afterRenderEffect, ChangeDetectionStrategy, Component, computed, ElementRef, inject, input, output, untracked, viewChild } from '@angular/core';
import { LucideBookOpen } from '@lucide/angular';
import { SkeletonDirective } from '../../components/ui/skeleton';
import type { TheaterStateDto } from '../../core/api/api-types';
import type { LoadStatus } from '../../core/atlas-data';
import type { Axis } from '../../core/atlas-state';
import { formatDisplayDate } from '../../core/dates';
import { MOTION_DURATION, MotionService } from '../../core/motion';
import { t, type I18nKey, type Lang } from '../../core/i18n';
import { InterpChip } from '../../shared/interp-chip/interp-chip';

/**
 * 頂部列（PRD §8.1，`layout/top-bar`）。
 * 紀年：目前沒有紀年 API（`/eras` 未實作），依 §8.1 empty 規則只顯示西元，不顯示空白括號。
 * 檢視切換（實際控制／主權）：選取底塊用 motion 滑動（prefers-reduced-motion 時直接到位）。
 */
@Component({
  selector: 'wl-top-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideBookOpen, InterpChip, SkeletonDirective],
  host: { class: 'block' },
  template: `
    <header class="flex h-[var(--wl-topbar-height)] items-center gap-4 border-b border-wl-outline-variant bg-wl-surface px-4">
      <span class="font-wl-serif text-[17px] font-semibold tracking-wide text-wl-on-surface">World Line</span>
      <span class="h-6 w-px bg-wl-outline-variant" aria-hidden="true"></span>
      @if (loading()) {
        <div sanringSkeleton class="h-8 w-48"></div>
      } @else {
        <h1 data-testid="topbar-date" class="wl-display tabular-nums" [attr.datetime]="date()">{{ display() }}</h1>
      }
      <wl-interp-chip [status]="controlStatus()" [theaters]="theaters()" [featureCount]="featureCount()" [lang]="lang()" (jump)="jump.emit($event)" />
      <div class="ml-auto flex items-center gap-3">
        <div class="wl-seg wl-seg-anim" role="group" data-testid="axis-toggle" [attr.data-axis]="axis()" [attr.aria-label]="lang() === 'en' ? 'View' : '檢視'">
          <span #thumb class="wl-seg-thumb" data-testid="axis-toggle-thumb" aria-hidden="true"></span>
          <button #btnControl type="button" data-testid="axis-toggle-control" [attr.aria-pressed]="axis() === 'control'" (click)="pick('control')">{{ tr('axis.control') }}</button>
          <button #btnSov type="button" data-testid="axis-toggle-sovereignty" [attr.aria-pressed]="axis() === 'sovereignty'" (click)="pick('sovereignty')">{{ tr('axis.sovereignty') }}</button>
        </div>
        <div class="wl-seg" role="group" aria-label="語言 Language">
          <button type="button" data-testid="lang-toggle-zh" [attr.aria-pressed]="lang() === 'zh-Hant'" (click)="langChange.emit('zh-Hant')" lang="zh-Hant">中</button>
          <button type="button" data-testid="lang-toggle-en" [attr.aria-pressed]="lang() === 'en'" (click)="langChange.emit('en')" lang="en">EN</button>
        </div>
        <button type="button" data-testid="legend-toggle" class="wl-icon-btn wl-outlined size-8" [attr.aria-pressed]="legendOpen()"
          [attr.aria-label]="tr('legend.toggle')" [attr.title]="tr('legend.toggle')" (click)="legendToggle.emit()"><svg lucideBookOpen class="size-4"></svg></button>
      </div>
    </header>
  `,
})
export class TopBar {
  readonly date = input.required<string>();
  readonly lang = input<Lang>('zh-Hant');
  readonly loading = input(false);
  readonly legendOpen = input(true);
  readonly controlStatus = input<LoadStatus>('idle');
  readonly theaters = input<TheaterStateDto[] | null>(null);
  readonly featureCount = input(0);
  readonly axis = input<Axis>('control');
  readonly axisChange = output<Axis>();
  readonly langChange = output<Lang>();
  readonly legendToggle = output<void>();
  readonly jump = output<string>();

  protected readonly display = computed(() => formatDisplayDate(this.date(), this.lang()));
  private readonly motion = inject(MotionService);
  private readonly thumb = viewChild<ElementRef<HTMLElement>>('thumb');
  private readonly btnControl = viewChild<ElementRef<HTMLElement>>('btnControl');
  private readonly btnSov = viewChild<ElementRef<HTMLElement>>('btnSov');
  private placed = false;

  constructor() {
    // 選取底塊：第一次直接到位；之後切換用 motion 滑過去（減少動態時 MotionService 直接略過，這裡補上終態）
    afterRenderEffect(() => {
      const axis = this.axis();
      this.lang();
      const thumb = this.thumb()?.nativeElement;
      const btn = (axis === 'control' ? this.btnControl() : this.btnSov())?.nativeElement;
      if (!thumb || !btn) return;
      untracked(() => {
        const to = { x: btn.offsetLeft, width: btn.offsetWidth };
        const settle = () => {
          thumb.style.transform = `translateX(${to.x}px)`;
          thumb.style.width = `${to.width}px`;
        };
        if (!this.placed || this.motion.reduced()) {
          this.placed = true;
          settle();
          return;
        }
        void this.motion.animate(thumb, { transform: `translateX(${to.x}px)`, width: `${to.width}px` }, { duration: MOTION_DURATION.fast }).then(settle);
      });
    });
  }

  protected pick(axis: Axis): void {
    if (axis !== this.axis()) this.axisChange.emit(axis);
  }
  protected tr(key: I18nKey): string {
    return t(key, this.lang());
  }
}
