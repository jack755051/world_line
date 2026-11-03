import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  computed,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { LucideCalendar, LucideEllipsis, LucideInfo, LucidePause, LucidePlay } from '@lucide/angular';
import type { TimelineSnapshotDto } from '../../core/api/api-types';
import type { LoadStatus } from '../../core/atlas-data';
import { addDays, addMonths, clampDate, isIsoDate, toDayNumber } from '../../core/dates';
import { t, type I18nKey, type Lang } from '../../core/i18n';
import { COMPLETE_FROM, dateAt, fraction, nextSnapshotDate, prevSnapshotDate, rangeFor, yearTicks } from './timeline-scale';
import { timelineShortcut } from './timeline-keys';

export type TimelineSpeed = 'day' | 'week' | 'month';
const SPEEDS: readonly TimelineSpeed[] = ['day', 'week', 'month'];

/**
 * 時間軸（PRD §8.3 方案 A，Tai 2026-11-03 16:35 選定；ARCHITECTURE M3-a）。
 * 單行約 48px：播放鍵、日期按鈕（可直接輸入）、全寬滑桿（每 5 年文字刻度＋每年小點）、「⋯」選單（速度，預設每秒 1 週；上一個／下一個快照）。
 * 資料不完整改為日期旁的 ⓘ（首次造訪的 toast 由頁面負責）。分洲軌道與事件色帶已拿掉。
 * 拖曳、點擊都只送 `dateChange`，冷跳／熱跳沿用頁面 `setDate` 的既有邏輯。
 */
@Component({
  selector: 'wl-timeline',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucidePlay, LucidePause, LucideCalendar, LucideInfo, LucideEllipsis],
  host: { class: 'block h-full' },
  styles: `
    .rail { position: absolute; left: 0; right: 0; top: 50%; height: 4px; margin-top: -8px; border-radius: 2px; background: var(--wl-color-surface-container-high); }
    .rail-incomplete { position: absolute; left: 0; top: 50%; height: 4px; margin-top: -8px; border-radius: 2px 0 0 2px;
      background: repeating-linear-gradient(135deg, var(--wl-color-surface-container-high) 0 3px, var(--wl-color-surface-dim) 3px 6px); }
    .dot { position: absolute; top: 50%; width: 3px; height: 3px; margin: 1px 0 0 -1.5px; border-radius: 9999px; background: var(--wl-color-outline-variant); }
    .dot.major { width: 1px; height: 5px; margin: 0 0 0 -0.5px; border-radius: 0; background: var(--wl-color-outline); }
  `,
  template: `
    <section data-testid="timeline" class="relative flex h-full items-center gap-2 border-t border-wl-outline-variant bg-wl-surface px-3"
      [attr.aria-label]="lang() === 'en' ? 'Timeline' : '時間軸'">
      <button type="button" class="wl-icon-btn wl-outlined flex-none" data-testid="timeline-play" [attr.aria-pressed]="playing()" [attr.data-playing]="playing() ? 'true' : null"
        [attr.aria-label]="playing() ? tr('timeline.pause') : tr('timeline.play')" [attr.title]="(playing() ? tr('timeline.pause') : tr('timeline.play')) + '（' + tr('timeline.key.space') + '）'"
        (click)="togglePlay()">
        @if (playing()) { <svg lucidePause class="size-3.5"></svg> } @else { <svg lucidePlay class="size-3.5"></svg> }
      </button>

      <!-- 日期按鈕：外觀是按鈕，點了可直接輸入 YYYY-MM-DD（沿用既有日期欄，Enter／離開時送出） -->
      <label data-testid="timeline-date-button" class="flex h-7 flex-none cursor-text items-center gap-1.5 rounded-wl-md border border-wl-outline bg-wl-surface-bright px-2 hover:bg-wl-surface-container focus-within:outline-2 focus-within:outline-wl-primary">
        <svg lucideCalendar class="size-3.5 flex-none text-wl-on-surface-variant" aria-hidden="true"></svg>
        <span class="sr-only">{{ tr('timeline.dateInput') }}</span>
        <input data-testid="timeline-date-input" type="text" inputmode="numeric" placeholder="YYYY-MM-DD" maxlength="10"
          class="w-[84px] bg-transparent wl-text2 font-semibold text-wl-on-surface tabular-nums outline-none"
          [value]="date()" (keydown.enter)="commitInput($event)" (blur)="commitInput($event)" (keydown.escape)="cancelInput($event)" />
      </label>
      @if (incomplete()) {
        <span data-testid="timeline-incomplete-info" tabindex="0" role="img" class="flex size-6 flex-none items-center justify-center rounded-full text-wl-on-surface-variant hover:bg-wl-surface-container focus-visible:outline-2 focus-visible:outline-wl-primary"
          [attr.aria-label]="tr('map.incomplete')" [attr.title]="tr('map.incomplete')"><svg lucideInfo class="size-4" aria-hidden="true"></svg></span>
      }

      <!-- 全寬滑桿 -->
      <div #bar data-testid="timeline-slider" class="relative mx-2 h-full min-w-0 flex-1 cursor-pointer select-none touch-none" (pointerdown)="onPointerDown($event)">
        <div class="rail"></div>
        @if (incompleteWidth() > 0) {
          <div data-testid="timeline-incomplete" class="rail-incomplete" [style.width.%]="incompleteWidth() * 100"></div>
        }
        @for (y of years(); track y.date) {
          <div class="dot pointer-events-none" data-testid="timeline-year-dot" [class.major]="!!y.label" [style.left.%]="y.f * 100"></div>
          @if (y.label) {
            <span data-testid="timeline-year-label" class="pointer-events-none absolute top-1/2 mt-[6px] -translate-x-1/2 font-wl-serif text-[12px] leading-[14px] text-wl-on-surface-variant tabular-nums"
              [style.left.%]="y.f * 100">{{ y.label }}</span>
          }
        }
        @if (startLabel(); as sl) {
          <span data-testid="timeline-start-label" class="pointer-events-none absolute left-0 top-1/2 mt-[6px] font-wl-serif text-[12px] leading-[14px] text-wl-on-surface-variant tabular-nums">{{ sl }}</span>
        }
        <div data-testid="timeline-handle" role="slider" tabindex="0"
          class="absolute top-1/2 -mt-[12px] -ml-[6px] size-3 rounded-full border-2 border-wl-surface bg-wl-primary shadow outline-offset-2 focus-visible:outline-2 focus-visible:outline-wl-primary"
          [style.left.%]="handleF() * 100" [attr.aria-label]="tr('timeline.handle')" [attr.aria-valuemin]="dayMin()" [attr.aria-valuemax]="dayMax()"
          [attr.aria-valuenow]="dayNow()" [attr.aria-valuetext]="date()" (keydown)="onKey($event)" (pointerdown)="onPointerDown($event)"></div>
      </div>

      <!-- ⋯ 選單 -->
      <div class="relative flex-none">
        <button type="button" #menuBtn class="wl-icon-btn" data-testid="timeline-menu-button" aria-haspopup="menu" [attr.aria-expanded]="menuOpen()"
          [attr.aria-label]="tr('timeline.menu')" [attr.title]="tr('timeline.menu')" (click)="toggleMenu()"><svg lucideEllipsis class="size-4"></svg></button>
        @if (menuOpen()) {
          <div data-testid="timeline-menu" role="menu" class="wl-paper absolute bottom-full right-0 z-30 mb-2 w-[220px] p-1 wl-text2 shadow-[var(--wl-shadow-panel)]">
            <div class="px-2 pt-1 pb-0.5 wl-label text-wl-on-surface-variant">{{ tr('timeline.speed') }}</div>
            @for (sp of speeds; track sp) {
              <button type="button" role="menuitemradio" data-testid="timeline-speed-option" [attr.data-speed]="sp" [attr.aria-checked]="speed() === sp"
                class="flex w-full items-center justify-between rounded-wl-sm px-2 py-1 text-left hover:bg-wl-surface-container" (click)="setSpeed(sp)">
                <span class="tabular-nums">{{ speedText(sp) }}</span>@if (speed() === sp) { <span aria-hidden="true">✓</span> }
              </button>
            }
            <div class="my-1 h-px bg-wl-outline-variant" aria-hidden="true"></div>
            <button type="button" role="menuitem" data-testid="timeline-prev-snapshot" [disabled]="!prevDate()"
              class="flex w-full rounded-wl-sm px-2 py-1 text-left hover:bg-wl-surface-container disabled:opacity-40" (click)="goPrev()">{{ tr('timeline.prev') }}</button>
            <button type="button" role="menuitem" data-testid="timeline-next-snapshot" [disabled]="!nextDate()"
              class="flex w-full rounded-wl-sm px-2 py-1 text-left hover:bg-wl-surface-container disabled:opacity-40" (click)="goNext()">{{ tr('timeline.next') }}</button>
            @if (snapshotsStatus() === 'error') {
              <div data-testid="timeline-error" class="px-2 py-1 text-wl-error">{{ tr('timeline.error') }}・<button type="button" class="wl-link" (click)="retry.emit()">{{ tr('map.retry') }}</button></div>
            }
            <div class="my-1 h-px bg-wl-outline-variant" aria-hidden="true"></div>
            <div data-testid="timeline-keys-help" class="px-2 py-1 text-[11px] leading-[16px] text-wl-on-surface-variant">{{ tr('timeline.keys') }}</div>
          </div>
        }
      </div>
    </section>
  `,
})
export class Timeline {
  readonly date = input.required<string>();
  readonly snapshots = input<TimelineSnapshotDto[]>([]);
  readonly snapshotsStatus = input<LoadStatus>('idle');
  /** 其他資料（事件）的最早日期；早於預設起點時，時間軸起點往前延伸。 */
  readonly earliestData = input<string | null>(null);
  readonly lang = input<Lang>('zh-Hant');
  /** 地圖資料與繪製都完成（播放等它為真才前進下一格，不會一路閃載入中）。 */
  readonly ready = input(true);
  readonly dateChange = output<string>();
  /** 播放開始／停止（頁面據此在播放時不顯示地圖載入指示）。 */
  readonly playingChange = output<boolean>();
  readonly retry = output<void>();
  readonly invalidInput = output<string>();

  protected readonly speeds = SPEEDS;
  protected readonly playing = signal(false);
  protected readonly speed = signal<TimelineSpeed>('week');
  protected readonly menuOpen = signal(false);
  private readonly bar = viewChild.required<ElementRef<HTMLDivElement>>('bar');
  private readonly menuBtn = viewChild<ElementRef<HTMLButtonElement>>('menuBtn');
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private timer: ReturnType<typeof setInterval> | undefined;

  protected readonly range = computed(() => {
    const dates = this.snapshots().map((s) => s.attestedPeriod?.start ?? s.asOf);
    const extra = this.earliestData();
    if (extra && isIsoDate(extra)) dates.push(extra);
    const earliest = dates.length ? dates.reduce((a, b) => (a < b ? a : b)) : null;
    return rangeFor(earliest);
  });
  /** 每 5 年一個文字刻度、每年一個小點；有起點標籤時最左端 5% 內的年份不標字（避免疊字，刻點照畫）。 */
  protected readonly years = computed(() => {
    const ys = yearTicks(this.range(), 16, 5);
    return this.startLabel() ? ys.map((y) => (y.f < 0.05 ? { ...y, label: undefined } : y)) : ys;
  });
  protected readonly startLabel = computed(() => (this.range().start.slice(5) === '01-01' ? null : this.range().start.slice(0, 7)));
  protected readonly handleF = computed(() => fraction(this.date(), this.range()));
  protected readonly incompleteWidth = computed(() => (this.range().start < COMPLETE_FROM ? fraction(COMPLETE_FROM, this.range()) : 0));
  protected readonly incomplete = computed(() => this.date() < COMPLETE_FROM);
  protected readonly dayMin = computed(() => toDayNumber(this.range().start));
  protected readonly dayMax = computed(() => toDayNumber(this.range().end));
  protected readonly dayNow = computed(() => toDayNumber(this.date()));
  private readonly snapDates = computed(() => this.snapshots().map((s) => s.asOf));
  protected readonly prevDate = computed(() => prevSnapshotDate(this.snapDates(), this.date()));
  protected readonly nextDate = computed(() => nextSnapshotDate(this.snapDates(), this.date()));

  constructor() {
    const doc = inject(DOCUMENT);
    const onKeydown = (e: KeyboardEvent) => this.onGlobalKey(e);
    const onPointer = (e: PointerEvent) => {
      if (this.menuOpen() && !this.host.nativeElement.querySelector('[data-testid=timeline-menu]')?.parentElement?.contains(e.target as Node)) this.closeMenu(false);
    };
    // capture：地圖 canvas 有焦點時也由時間軸處理方向鍵（攔下 MapLibre 的鍵盤平移，避免同時移地圖又換日期）
    doc.addEventListener('keydown', onKeydown, true);
    doc.addEventListener('pointerdown', onPointer, true);
    inject(DestroyRef).onDestroy(() => {
      clearInterval(this.timer);
      doc.removeEventListener('keydown', onKeydown, true);
      doc.removeEventListener('pointerdown', onPointer, true);
    });
  }

  protected tr(key: I18nKey): string {
    return t(key, this.lang());
  }
  protected speedText(sp: TimelineSpeed): string {
    return this.tr(sp === 'day' ? 'timeline.speed.day' : sp === 'week' ? 'timeline.speed.week' : 'timeline.speed.month');
  }

  protected toggleMenu(): void {
    this.menuOpen.set(!this.menuOpen());
  }
  protected closeMenu(refocus: boolean): void {
    this.menuOpen.set(false);
    if (refocus) this.menuBtn()?.nativeElement.focus();
  }
  protected setSpeed(sp: TimelineSpeed): void {
    this.speed.set(sp);
  }

  protected goPrev(): void {
    const d = this.prevDate();
    if (d) this.emit(d);
  }
  protected goNext(): void {
    const d = this.nextDate();
    if (d) this.emit(d);
  }

  private emit(d: string): void {
    const r = this.range();
    this.dateChange.emit(clampDate(d, r.start, r.end));
  }

  /** 全域快捷鍵：空白鍵播放、←／→ 一週、Shift＋←／→ 一年；輸入框、選單、修飾鍵一律不作用（timeline-keys.ts）。 */
  private onGlobalKey(e: KeyboardEvent): void {
    if (e.key === 'Escape' && this.menuOpen()) {
      e.preventDefault();
      this.closeMenu(true);
      return;
    }
    const s = timelineShortcut(e);
    if (!s) return;
    e.preventDefault();
    e.stopPropagation();
    if (s.kind === 'toggle') this.togglePlay();
    else this.step(s.unit, s.dir);
  }

  private step(unit: 'week' | 'year', dir: 1 | -1): void {
    const cur = this.date();
    this.emit(unit === 'week' ? addDays(cur, 7 * dir) : addMonths(cur, 12 * dir));
  }

  protected togglePlay(): void {
    if (this.playing()) {
      this.stop();
      return;
    }
    this.playing.set(true);
    this.playingChange.emit(true);
    // 每 100ms 檢查一次：距上一格至少 1 秒「而且」上一格的地圖已畫好才前進（資料慢時等資料，不跳過、不閃載入中）
    let last = Date.now();
    this.timer = setInterval(() => {
      if (Date.now() - last < Timeline.STEP_MS || !this.ready()) return;
      last = Date.now();
      const cur = this.date();
      const sp = this.speed();
      const next = sp === 'day' ? addDays(cur, 1) : sp === 'week' ? addDays(cur, 7) : addMonths(cur, 1);
      if (next > this.range().end) {
        this.emit(this.range().end);
        this.stop();
        return;
      }
      this.emit(next);
    }, 100);
  }

  static readonly STEP_MS = 1000;

  private stop(): void {
    clearInterval(this.timer);
    this.timer = undefined;
    if (this.playing()) this.playingChange.emit(false);
    this.playing.set(false);
  }

  protected commitInput(e: Event): void {
    const el = e.target as HTMLInputElement;
    const v = el.value.trim();
    if (v === this.date()) return;
    if (isIsoDate(v)) this.emit(v);
    else {
      el.value = this.date();
      this.invalidInput.emit(v);
    }
  }
  protected cancelInput(e: Event): void {
    const el = e.target as HTMLInputElement;
    el.value = this.date();
    el.blur();
  }

  /** 把手的鍵盤操作和全域快捷鍵一致：←／→ 一週，Shift 一年；PageUp／PageDown 上一個／下一個快照；Home／End 頭尾。 */
  protected onKey(e: KeyboardEvent): void {
    const cur = this.date();
    let next: string | null = null;
    switch (e.key) {
      case ' ':
        e.preventDefault();
        this.togglePlay();
        return;
      case 'ArrowLeft':
        next = e.shiftKey ? addMonths(cur, -12) : addDays(cur, -7);
        break;
      case 'ArrowRight':
        next = e.shiftKey ? addMonths(cur, 12) : addDays(cur, 7);
        break;
      case 'PageUp':
        next = this.prevDate();
        break;
      case 'PageDown':
        next = this.nextDate();
        break;
      case 'Home':
        next = this.range().start;
        break;
      case 'End':
        next = this.range().end;
        break;
      default:
        return;
    }
    e.preventDefault();
    if (next) this.emit(next);
  }

  protected onPointerDown(e: PointerEvent): void {
    const el = this.bar().nativeElement;
    const at = (clientX: number) => {
      const rect = el.getBoundingClientRect();
      if (rect.width <= 0) return;
      this.emit(dateAt((clientX - rect.left) / rect.width, this.range()));
    };
    at(e.clientX);
    el.setPointerCapture?.(e.pointerId);
    const move = (ev: PointerEvent) => at(ev.clientX);
    const up = () => {
      el.removeEventListener('pointermove', move);
      el.removeEventListener('pointerup', up);
      el.removeEventListener('pointercancel', up);
    };
    el.addEventListener('pointermove', move);
    el.addEventListener('pointerup', up);
    el.addEventListener('pointercancel', up);
  }
}
