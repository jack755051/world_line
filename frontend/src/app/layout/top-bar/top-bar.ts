import { afterRenderEffect, ChangeDetectionStrategy, Component, computed, DestroyRef, ElementRef, inject, input, output, signal, untracked, viewChild } from '@angular/core';
import { DOCUMENT, NgTemplateOutlet } from '@angular/common';
import { LucideBookOpen, LucideEllipsis, LucideGlobe } from '@lucide/angular';
import type { Breakpoint } from '../../core/viewport';
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
  imports: [LucideBookOpen, LucideEllipsis, LucideGlobe, NgTemplateOutlet, InterpChip, SkeletonDirective],
  host: { class: 'block' },
  template: `
    @if (compact()) {
      <!-- §12 手機（xs、sm）或高度 <500px：48px，只放 logo＋World Line、日期（H1）、⋯ 選單 -->
      <header data-testid="topbar" data-compact="true" class="flex h-[var(--wl-topbar-height)] items-center gap-2 border-b border-wl-outline-variant bg-wl-surface px-3">
        <span class="flex flex-none items-center gap-1.5 whitespace-nowrap">
          <svg lucideGlobe class="size-6 text-wl-primary" aria-hidden="true"></svg>
          <span data-testid="topbar-brand" class="font-wl-serif text-[16px] font-semibold text-wl-on-surface">World Line</span>
        </span>
        <button type="button" data-testid="topbar-date" class="mx-auto h-10 min-w-0 whitespace-nowrap px-2 font-mono text-[16px] font-bold tabular-nums text-wl-on-surface"
          [attr.datetime]="date()" [attr.aria-label]="(lang() === 'en' ? 'Date ' : '日期 ') + date()" (click)="datePick.emit()">{{ date() }}</button>
        <div class="relative flex-none" #menuWrap>
          <button type="button" data-testid="topbar-menu-button" class="wl-icon-btn size-10" aria-haspopup="menu" [attr.aria-expanded]="menuOpen()"
            [attr.aria-label]="lang() === 'en' ? 'Menu' : '選單'" (click)="menuOpen.set(!menuOpen())"><svg lucideEllipsis class="size-5"></svg></button>
          @if (menuOpen()) {
            <div data-testid="topbar-menu" role="menu" class="wl-paper absolute right-0 top-full z-40 mt-1 flex w-[240px] flex-col gap-2 p-2 wl-text2 shadow-[var(--wl-shadow-panel)]">
              <ng-container [ngTemplateOutlet]="axisSeg" />
              <ng-container [ngTemplateOutlet]="langSeg" />
              <button type="button" role="menuitemcheckbox" data-testid="camp-layer-toggle" [attr.aria-checked]="showCamps()" [attr.aria-pressed]="showCamps()"
                class="flex min-h-11 items-center gap-2 rounded-wl-sm px-2 text-left hover:bg-wl-surface-container" (click)="campsToggle.emit()">
                <span class="inline-block size-4 border border-wl-outline" [class.bg-wl-secondary]="showCamps()"></span>{{ campText() }}</button>
              <button type="button" role="menuitem" data-testid="topbar-menu-legend" class="flex min-h-11 items-center gap-2 rounded-wl-sm px-2 text-left hover:bg-wl-surface-container"
                (click)="menuOpen.set(false); legendToggle.emit()"><svg lucideBookOpen class="size-4"></svg>{{ tr('legend.title') }}</button>
            </div>
          }
        </div>
      </header>
    } @else {
    <header data-testid="topbar" class="flex h-[var(--wl-topbar-height)] items-center gap-4 border-b border-wl-outline-variant bg-wl-surface px-4">
      <span class="whitespace-nowrap font-wl-serif text-[17px] font-semibold tracking-wide text-wl-on-surface">World Line</span>
      <span class="h-6 w-px bg-wl-outline-variant" aria-hidden="true"></span>
      @if (loading()) {
        <div sanringSkeleton class="h-8 w-48"></div>
      } @else {
        <h1 data-testid="topbar-date" class="whitespace-nowrap tabular-nums" [class.wl-display]="bp() !== 'md'" [class.wl-title1]="bp() === 'md'" [attr.datetime]="date()">{{ display() }}</h1>
      }
      <wl-interp-chip [status]="controlStatus()" [theaters]="theaters()" [featureCount]="featureCount()" [lang]="lang()" (jump)="jump.emit($event)" />
      <div class="ml-auto flex items-center gap-3">
        <ng-container [ngTemplateOutlet]="axisSeg" />
        <ng-container [ngTemplateOutlet]="langSeg" />
        <!-- 陣營外框（補充）：§12 不再浮在地圖上，移進頂列 -->
        <button type="button" data-testid="camp-layer-toggle" class="wl-outlined flex h-8 items-center gap-1.5 whitespace-nowrap rounded-wl-md px-2 wl-text2 hover:bg-wl-surface-container"
          [attr.aria-pressed]="showCamps()" [attr.title]="campText()" (click)="campsToggle.emit()">
          <span class="inline-block size-3 border border-wl-outline" [class.bg-wl-secondary]="showCamps()"></span>{{ bp() === 'md' ? (lang() === 'en' ? 'Camps' : '陣營') : campText() }}</button>
        <button type="button" data-testid="legend-toggle" class="wl-icon-btn wl-outlined size-8" [attr.aria-pressed]="legendOpen()"
          [attr.aria-label]="tr('legend.toggle')" [attr.title]="tr('legend.toggle')" (click)="legendToggle.emit()"><svg lucideBookOpen class="size-4"></svg></button>
      </div>
    </header>
    }
    <ng-template #axisSeg>
      <div class="wl-seg wl-seg-anim" role="group" data-testid="axis-toggle" [attr.data-axis]="axis()" [attr.aria-label]="lang() === 'en' ? 'View' : '檢視'"
        [class.w-[120px]]="bp() === 'md'" [class.w-full]="compact()" [class.min-h-11]="compact()">
        <span #thumb class="wl-seg-thumb" data-testid="axis-toggle-thumb" aria-hidden="true"></span>
        <button #btnControl type="button" class="flex-1 whitespace-nowrap" data-testid="axis-toggle-control" [class.!h-11]="compact()" [attr.aria-pressed]="axis() === 'control'" (click)="pick('control')">{{ tr('axis.control') }}</button>
        <button #btnSov type="button" class="flex-1 whitespace-nowrap" data-testid="axis-toggle-sovereignty" [class.!h-11]="compact()" [attr.aria-pressed]="axis() === 'sovereignty'" (click)="pick('sovereignty')">{{ tr('axis.sovereignty') }}</button>
      </div>
    </ng-template>
    <ng-template #langSeg>
      <div class="wl-seg" role="group" aria-label="語言 Language" [class.w-[72px]]="bp() === 'md'" [class.w-full]="compact()" [class.min-h-11]="compact()">
        <button type="button" class="flex-1" data-testid="lang-toggle-zh" [class.!h-11]="compact()" [attr.aria-pressed]="lang() === 'zh-Hant'" (click)="langChange.emit('zh-Hant')" lang="zh-Hant">中</button>
        <button type="button" class="flex-1" data-testid="lang-toggle-en" [class.!h-11]="compact()" [attr.aria-pressed]="lang() === 'en'" (click)="langChange.emit('en')" lang="en">EN</button>
      </div>
    </ng-template>
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
  /** §12：斷點與精簡版（手機或高度 <500px）。 */
  readonly bp = input<Breakpoint>('xl');
  readonly compact = input(false);
  readonly showCamps = input(false);
  readonly campsToggle = output<void>();
  /** 手機版點日期：開啟時間軸的日期輸入（同一個日期選擇器）。 */
  readonly datePick = output<void>();
  protected readonly menuOpen = signal(false);
  private readonly menuWrap = viewChild<ElementRef<HTMLElement>>('menuWrap');
  protected readonly campText = computed(() => (this.lang() === 'en' ? 'Camp outlines (supplement)' : '陣營外框（補充）'));

  protected readonly display = computed(() => formatDisplayDate(this.date(), this.lang()));
  private readonly motion = inject(MotionService);
  private readonly thumb = viewChild<ElementRef<HTMLElement>>('thumb');
  private readonly btnControl = viewChild<ElementRef<HTMLElement>>('btnControl');
  private readonly btnSov = viewChild<ElementRef<HTMLElement>>('btnSov');
  private placed = false;

  constructor() {
    // ⋯ 選單：點外面或 Esc 收起
    const doc = inject(DOCUMENT);
    const onDown = (e: PointerEvent) => {
      if (this.menuOpen() && !this.menuWrap()?.nativeElement.contains(e.target as Node)) this.menuOpen.set(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && this.menuOpen()) this.menuOpen.set(false);
    };
    doc.addEventListener('pointerdown', onDown, true);
    doc.addEventListener('keydown', onKey);
    inject(DestroyRef).onDestroy(() => {
      doc.removeEventListener('pointerdown', onDown, true);
      doc.removeEventListener('keydown', onKey);
    });
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
