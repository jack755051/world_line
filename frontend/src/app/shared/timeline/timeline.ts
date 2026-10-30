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
import { LucidePause, LucidePlay, LucideSkipBack, LucideSkipForward } from '@lucide/angular';
import { SkeletonDirective } from '../../components/ui/skeleton';
import type { TimelineSnapshotDto } from '../../core/api/api-types';
import type { LoadStatus } from '../../core/atlas-data';
import { addDays, addMonths, clampDate, isIsoDate, toDayNumber } from '../../core/dates';
import { localized, t, type I18nKey, type Lang } from '../../core/i18n';
import { theaterLabel, tracksFor } from '../../core/theater-tracks';
import {
  COMPLETE_FROM,
  dateAt,
  fraction,
  monthTicks,
  nextSnapshotDate,
  prevSnapshotDate,
  rangeFor,
  yearTicks,
} from './timeline-scale';

interface Marker {
  snap: TimelineSnapshotDto;
  left: number;
  width: number | null;
}

/**
 * 時間軸（PRD §8.3、DESIGN.md Timeline，`shared/timeline`，自建）。
 * 一條拖拉桿配五條戰區軌道；快照標記來自 `/timeline/snapshots`，沒有快照的軌道以「控制資料缺」樣式顯示（R9）。
 */
@Component({
  selector: 'wl-timeline',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucidePlay, LucidePause, LucideSkipBack, LucideSkipForward, SkeletonDirective],
  host: { class: 'block h-full' },
  styles: `
    .track { position: relative; height: 12px; border-bottom: 1px solid var(--wl-color-outline-variant); }
    .pill { position: absolute; top: 2px; height: 8px; min-width: 8px; margin-left: -4px; border-radius: 9999px; background: var(--wl-color-map-ink); cursor: pointer; }
    .bar { position: absolute; top: 3px; height: 6px; border-radius: 1px; background: var(--wl-color-map-ink); cursor: pointer; }
    .pill:focus-visible, .bar:focus-visible { outline: 2px solid var(--wl-color-primary); outline-offset: 1px; }
  `,
  template: `
    <section data-testid="timeline" class="flex h-full items-stretch gap-4 border-t border-wl-outline-variant bg-wl-surface px-4 pt-3 pb-1.5"
      [attr.aria-label]="lang() === 'en' ? 'Timeline' : '時間軸'">
      <div class="flex w-[260px] flex-none flex-col justify-center gap-2">
        <div class="flex items-center gap-1.5">
          <button type="button" class="wl-icon-btn wl-outlined" data-testid="timeline-prev-snapshot" [disabled]="!prevDate()"
            [attr.aria-label]="tr('timeline.prev')" [attr.title]="tr('timeline.prev')" (click)="goPrev()"><svg lucideSkipBack class="size-4"></svg></button>
          <button type="button" class="wl-icon-btn wl-btn-primary" data-testid="timeline-play" [attr.aria-pressed]="playing()"
            [attr.aria-label]="playing() ? tr('timeline.pause') : tr('timeline.play')" [attr.title]="playing() ? tr('timeline.pause') : tr('timeline.play')"
            (click)="togglePlay()">
            @if (playing()) { <svg lucidePause class="size-4"></svg> } @else { <svg lucidePlay class="size-4"></svg> }
          </button>
          <button type="button" class="wl-icon-btn wl-outlined" data-testid="timeline-next-snapshot" [disabled]="!nextDate()"
            [attr.aria-label]="tr('timeline.next')" [attr.title]="tr('timeline.next')" (click)="goNext()"><svg lucideSkipForward class="size-4"></svg></button>
          <div class="wl-seg ml-2 whitespace-nowrap" data-testid="timeline-speed" role="group" [attr.aria-label]="tr('timeline.speed')">
            <button type="button" [attr.aria-pressed]="speed() === 'week'" (click)="speed.set('week')">{{ tr('timeline.speed.week') }}</button>
            <button type="button" [attr.aria-pressed]="speed() === 'month'" (click)="speed.set('month')">{{ tr('timeline.speed.month') }}</button>
          </div>
        </div>
        <label class="flex items-center gap-2 wl-text2 text-wl-on-surface-variant">{{ tr('timeline.dateInput') }}
          <input data-testid="timeline-date-input" type="text" inputmode="numeric" placeholder="YYYY-MM-DD" maxlength="10"
            class="h-7 w-[110px] rounded-wl-md border border-wl-outline bg-wl-surface-bright px-2 text-wl-on-surface tabular-nums focus:outline-2 focus:outline-wl-primary"
            [value]="date()" (keydown.enter)="commitInput($event)" (blur)="commitInput($event)" />
        </label>
      </div>

      <div class="relative flex min-w-0 flex-1">
        <ul class="flex w-[56px] flex-none flex-col gap-[2px] pt-[14px] wl-text2 text-wl-on-surface-variant" aria-hidden="true">
          @for (lt of tracks(); track lt.code) { <li class="h-[12px] leading-[12px] text-[11px] whitespace-nowrap">{{ lt.label[lang()] }}</li> }
        </ul>
        <div #bar class="relative flex-1 cursor-pointer select-none touch-none" (pointerdown)="onPointerDown($event)">
          <!-- 早於 1937-07 的期間：淡底＋「資料不保證完整」 -->
          @if (incompleteWidth() > 0) {
            <div class="absolute inset-y-0 left-0 bg-wl-surface-dim/60" [style.width.%]="incompleteWidth() * 100">
              <span class="absolute bottom-0 left-1 wl-text2 text-[10px] text-wl-on-surface-variant">{{ tr('timeline.incomplete') }}</span>
            </div>
          }
          @for (m of months(); track m.date) { <div class="absolute top-[14px] bottom-[16px] w-px bg-wl-outline-variant/40" [style.left.%]="m.f * 100"></div> }
          @for (y of years(); track y.date) {
            <div class="absolute top-[12px] bottom-[14px] w-px bg-wl-outline" [style.left.%]="y.f * 100"></div>
            <span class="absolute bottom-0 -translate-x-1/2 font-wl-serif text-[12px] text-wl-on-surface-variant tabular-nums" [style.left.%]="y.f * 100">{{ y.label }}</span>
          }

          <div class="absolute inset-x-0 top-[14px] flex flex-col gap-[2px]">
            @for (tk of tracks(); track tk.code) {
              <div class="track" [attr.data-testid]="'timeline-track-' + tk.code" [attr.data-empty]="trackEmpty(tk.code) ? 'true' : null"
                [class.wl-gap-pattern]="trackEmpty(tk.code)" [attr.title]="trackEmpty(tk.code) ? theaterName(tk.code) + '：' + tr('timeline.noSnapshots') : null">
                @if (snapshotsStatus() === 'loading') {
                  <div sanringSkeleton class="absolute inset-0"></div>
                }
                @for (m of markersFor(tk.code); track m.snap.id) {
                  <button type="button" data-testid="timeline-snapshot-marker" [class.pill]="m.width === null" [class.bar]="m.width !== null"
                    [style.left.%]="m.left * 100" [style.width.%]="m.width !== null ? m.width * 100 : null"
                    [attr.aria-label]="markerLabel(m.snap)" (pointerdown)="$event.stopPropagation()" (click)="jump(m.snap.asOf)"
                    (mouseenter)="hover.set(m)" (mouseleave)="hover.set(null)" (focus)="hover.set(m)" (blur)="hover.set(null)"></button>
                }
              </div>
            }
          </div>

          @if (snapshotsStatus() === 'error') {
            <div data-testid="timeline-error" class="absolute inset-x-0 top-[14px] flex items-center justify-center gap-2 wl-text2 text-wl-error">
              {{ tr('timeline.error') }}・<button type="button" class="wl-link" (pointerdown)="$event.stopPropagation()" (click)="retry.emit()">{{ tr('map.retry') }}</button>
            </div>
          }

          <!-- 把手：朱紅直線＋小圓鈕，日期顯示在上方 -->
          <div class="pointer-events-none absolute top-0 bottom-[12px]" [style.left.%]="handleF() * 100">
            <div class="absolute top-[12px] bottom-0 -ml-[0.75px] w-[1.5px] bg-wl-primary"></div>
          </div>
          <div data-testid="timeline-handle" role="slider" tabindex="0" class="absolute top-[2px] -ml-[6px] size-3 rounded-full bg-wl-primary outline-offset-2 focus-visible:outline-2 focus-visible:outline-wl-primary"
            [style.left.%]="handleF() * 100" [attr.aria-label]="tr('timeline.handle')" [attr.aria-valuemin]="dayMin()" [attr.aria-valuemax]="dayMax()"
            [attr.aria-valuenow]="dayNow()" [attr.aria-valuetext]="date()" (keydown)="onKey($event)" (pointerdown)="onPointerDown($event)"></div>
          <span class="pointer-events-none absolute -top-[10px] ml-2 wl-label text-wl-primary tabular-nums" [style.left.%]="handleF() * 100">{{ date() }}</span>

          @if (hover(); as h) {
            <div data-testid="timeline-marker-tooltip" role="tooltip" class="wl-paper pointer-events-none absolute bottom-full z-10 mb-2 w-[300px] -translate-x-1/2 p-2 wl-text2"
              [style.left.%]="h.left * 100">
              <div class="wl-label">{{ h.snap.asOf }}・{{ theaterName(h.snap.theaterCode) }}</div>
              @if (snapTitle(h.snap); as st) { <div>{{ st }}</div> }
              @for (g of groupSources(h.snap); track g.title) {
                <div class="mt-1">{{ g.title }}</div>
                @for (l of g.locators; track l) { <div class="wl-archival">・{{ l }}</div> }
              }
            </div>
          }
        </div>
      </div>
    </section>
  `,
})
export class Timeline {
  readonly date = input.required<string>();
  readonly snapshots = input<TimelineSnapshotDto[]>([]);
  readonly snapshotsStatus = input<LoadStatus>('idle');
  readonly lang = input<Lang>('zh-Hant');
  readonly dateChange = output<string>();
  readonly retry = output<void>();
  readonly invalidInput = output<string>();

  protected readonly playing = signal(false);
  protected readonly speed = signal<'week' | 'month'>('month');
  protected readonly hover = signal<Marker | null>(null);
  private readonly bar = viewChild.required<ElementRef<HTMLDivElement>>('bar');
  private timer: ReturnType<typeof setInterval> | undefined;

  protected readonly range = computed(() => {
    const dates = this.snapshots().map((s) => s.attestedPeriod?.start ?? s.asOf);
    const earliest = dates.length ? dates.reduce((a, b) => (a < b ? a : b)) : null;
    return rangeFor(earliest);
  });
  protected readonly years = computed(() => yearTicks(this.range()));
  protected readonly months = computed(() => monthTicks(this.range()));
  protected readonly handleF = computed(() => fraction(this.date(), this.range()));
  protected readonly incompleteWidth = computed(() => (this.range().start < COMPLETE_FROM ? fraction(COMPLETE_FROM, this.range()) : 0));
  protected readonly dayMin = computed(() => toDayNumber(this.range().start));
  protected readonly dayMax = computed(() => toDayNumber(this.range().end));
  protected readonly dayNow = computed(() => toDayNumber(this.date()));
  protected readonly tracks = computed(() => tracksFor(this.snapshots().map((s) => s.theaterCode)));
  private readonly snapDates = computed(() => this.snapshots().map((s) => s.asOf));
  protected readonly prevDate = computed(() => prevSnapshotDate(this.snapDates(), this.date()));
  protected readonly nextDate = computed(() => nextSnapshotDate(this.snapDates(), this.date()));

  private readonly markers = computed(() => {
    const r = this.range();
    const by = new Map<string, Marker[]>();
    for (const s of this.snapshots()) {
      const p = s.attestation === 'interval' ? s.attestedPeriod : null;
      const m: Marker = p?.start && p.end
        ? { snap: s, left: fraction(p.start, r), width: Math.max(0.002, fraction(p.end, r) - fraction(p.start, r)) }
        : { snap: s, left: fraction(s.asOf, r), width: null };
      by.set(s.theaterCode, [...(by.get(s.theaterCode) ?? []), m]);
    }
    return by;
  });

  constructor() {
    inject(DestroyRef).onDestroy(() => clearInterval(this.timer));
  }

  protected tr(key: I18nKey): string {
    return t(key, this.lang());
  }
  protected theaterName(code: string): string {
    return theaterLabel(code, this.lang());
  }
  protected markersFor(code: string): Marker[] {
    return this.markers().get(code) ?? [];
  }
  protected trackEmpty(code: string): boolean {
    return this.snapshotsStatus() === 'ok' && this.markersFor(code).length === 0;
  }
  protected snapTitle(s: TimelineSnapshotDto): string {
    return localized(s.title as Record<string, string> | null, this.lang()).text;
  }
  protected markerLabel(s: TimelineSnapshotDto): string {
    return `${s.asOf} ${this.theaterName(s.theaterCode)} ${this.snapTitle(s)}`;
  }

  /** 同一來源的多個 locator 合併顯示 */
  protected groupSources(s: TimelineSnapshotDto): { title: string; locators: string[] }[] {
    const by = new Map<string, string[]>();
    for (const x of s.primarySources) by.set(x.title, [...(by.get(x.title) ?? []), x.locator]);
    return [...by].map(([title, locators]) => ({ title, locators }));
  }

  protected jump(d: string): void {
    this.emit(d);
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

  protected togglePlay(): void {
    if (this.playing()) {
      this.stop();
      return;
    }
    this.playing.set(true);
    this.timer = setInterval(() => {
      const cur = this.date();
      const next = this.speed() === 'week' ? addDays(cur, 7) : addMonths(cur, 1);
      if (next > this.range().end) {
        this.emit(this.range().end);
        this.stop();
        return;
      }
      this.emit(next);
    }, 1000);
  }

  private stop(): void {
    clearInterval(this.timer);
    this.timer = undefined;
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

  protected onKey(e: KeyboardEvent): void {
    const cur = this.date();
    let next: string | null = null;
    switch (e.key) {
      case 'ArrowLeft':
        next = e.shiftKey ? addMonths(cur, -1) : addDays(cur, -1);
        break;
      case 'ArrowRight':
        next = e.shiftKey ? addMonths(cur, 1) : addDays(cur, 1);
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
