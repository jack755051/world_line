import { NgTemplateOutlet } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideX } from '@lucide/angular';
import type { RegimeEventDto, SovereigntyFeatureProperties } from '../../core/api/api-types';
import type { Lang } from '../../core/i18n';
import { EventRef } from '../event-ref/event-ref';
import { SANRING_TABS_IMPORTS } from '../../components/ui/tabs';
import { campOf } from '../map/map-style';

const TXT = {
  'zh-Hant': {
    period: '國界期間', status: '性質', deJure: '國界', notSovereign: '非主權（佔領行政區）', start: '起始變動', end: '結束變動',
    none: '本試驗範圍前即存在（不追溯）', open: '本試驗範圍內未結束', camp: '陣營（補充）',
    campNone: '陣營未建置', geometry: '國界來源', license: '幾何授權', osm: '含 OpenStreetMap 來源線段（ODbL）', close: '關閉',
    campNote: '陣營只作補充，不影響填色', until: '至',
    conflicts: '相關衝突（當日進行中）', noConflicts: '當日沒有進行中的衝突', events: '事件', noEvents: '沒有相關事件',
    loading: '載入中…', tabOverview: '概要', note: '註記', tabEvents: '事件', tabsLabel: '政權資訊分頁', loadError: '事件載入失敗', jump: '跳到此日', now: '目前日期',
    role: { belligerent: '交戰方', signatory: '簽署方', other: '相關', border_start: '國界起始', border_end: '國界結束', conflict_start: '開戰', conflict_end: '停戰／投降' } as Record<string, string>,
  },
  en: {
    period: 'Valid', status: 'Status', deJure: 'Border', notSovereign: 'Not sovereign (occupation administration)', start: 'Began with', end: 'Ended with',
    none: 'Existed before this trial (not traced)', open: 'Not ended within this trial', camp: 'Camp (supplement)',
    campNone: 'Camp not set', geometry: 'Border source', license: 'Geometry licence', osm: 'Contains OpenStreetMap-derived segments (ODbL)', close: 'Close',
    campNote: 'Camp is supplementary and does not affect fill', until: 'to',
    conflicts: 'Conflicts (ongoing on this date)', noConflicts: 'No ongoing conflict on this date', events: 'Events', noEvents: 'No related events',
    loading: 'Loading…', tabOverview: 'Overview', note: 'Note', tabEvents: 'Events', tabsLabel: 'Regime details', loadError: 'Could not load events', jump: 'Go to this date', now: 'Current date',
    role: { belligerent: 'Belligerent', signatory: 'Signatory', other: 'Related', border_start: 'Border begins', border_end: 'Border ends', conflict_start: 'War begins', conflict_end: 'War ends' } as Record<string, string>,
  },
} as const;
export type SovereigntyTab = 'overview' | 'events';
const CAMP_NAME: Record<string, { 'zh-Hant': string; en: string }> = {
  axis: { 'zh-Hant': '軸心', en: 'Axis' }, allies: { 'zh-Hant': '同盟', en: 'Allies' },
  cobelligerent: { 'zh-Hant': '共同交戰／合作', en: 'Co-belligerent' }, neutral: { 'zh-Hant': '中立／未結盟', en: 'Neutral' },
};

/**
 * 主權圖層（國界）資訊卡：政權名、國界期間、起訖疆界變動事件（同一結構：事件名稱、日期、查證狀態、出處；
 * 出處預設只顯示簡短引用，點一下展開完整書目；沒有正式出處就標「待查證」，不補造）、
 * 國界幾何來源（OHM 關係 id／版本、授權、署名），陣營只在這裡作補充。
 */
@Component({
  selector: 'wl-sovereignty-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideX, EventRef, NgTemplateOutlet, ...SANRING_TABS_IMPORTS],
  template: `
    <article data-testid="sovereignty-card" [class]="embedded() ? 'flex min-h-0 flex-1 flex-col' : 'wl-paper flex max-h-[inherit] min-h-0 w-[340px] flex-col p-4'"
      [attr.role]="embedded() ? null : 'dialog'" [attr.aria-label]="embedded() ? null : regimeName()" [attr.data-layer-status]="props().layerStatus">
      @if (!embedded()) {
      <header class="flex flex-none items-start justify-between gap-2 border-b border-wl-outline-variant pb-2">
        <div>
          <h2 class="wl-title2" data-testid="sovereignty-card-title">{{ regimeName() }}</h2>
          @if (originalName()) { <p class="wl-text2 text-wl-on-surface-variant" [attr.lang]="originalLang() || null">{{ originalName() }}</p> }
        </div>
        <button type="button" class="wl-icon-btn" [attr.aria-label]="t().close" (click)="closed.emit()"><svg lucideX class="size-4"></svg></button>
      </header>
      }
      @if (embedded()) {
      <!-- 分頁（sanring Tabs，底層 @angular/aria：tablist／tab／tabpanel、方向鍵、Home／End）：概要＝性質、期間、起訖變動、陣營、國界來源與相關衝突；事件＝時間線 -->
      <sanring-tabs variant="line" class="flex min-h-0 flex-1 flex-col gap-0" [defaultValue]="tab()" (valueChange)="onTab($event)">
        <sanring-tabs-list class="w-full flex-none" selectionMode="follow" [wrap]="true" [attr.aria-label]="t().tabsLabel">
          <sanring-tabs-trigger value="overview" data-testid="sovereignty-card-tab-overview">{{ t().tabOverview }}</sanring-tabs-trigger>
          <sanring-tabs-trigger value="events" data-testid="sovereignty-card-tab-events">{{ t().tabEvents }}
            @if (eventsStatus() === 'ok' && (regimeEvents()?.length ?? 0) > 0) {
              <span data-testid="sovereignty-card-tab-events-count" class="rounded-sm bg-wl-surface-container-high px-1 text-[11px] tabular-nums text-wl-on-surface-variant">{{ regimeEvents()?.length }}</span>
            }
          </sanring-tabs-trigger>
        </sanring-tabs-list>
        <div data-testid="sovereignty-card-body" class="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1">
          <sanring-tabs-content value="overview" class="mt-3">
            <div data-testid="sovereignty-card-panel-overview">
              <ng-container *ngTemplateOutlet="overview" />
        <!-- 相關衝突：與地圖上的雙劍同一份資料；點一項切到衝突詳情 -->
        <section data-testid="sovereignty-card-conflicts" class="mt-4 border-t border-wl-outline-variant pt-3">
          <h3 class="wl-sub-title mb-1.5">{{ t().conflicts }}</h3>
          @for (c of conflicts(); track c.recordId) {
            <button type="button" data-testid="sovereignty-card-conflict" [attr.data-record-id]="c.recordId"
              class="mb-1 flex w-full items-center gap-2 rounded-[var(--sanring-radius-xs)] border border-wl-outline-variant px-2 py-1.5 text-left wl-text2 hover:bg-wl-surface-container-high"
              (click)="conflictSelect.emit(c.recordId)">
              <svg viewBox="0 0 32 32" class="size-4 flex-none text-wl-error" fill="currentColor" aria-hidden="true"><path d="M27.5 4.5 L25.8 9 L12.2 22.6 L9.4 19.8 L23 6.2 Z M4.5 4.5 L9 6.2 L22.6 19.8 L19.8 22.6 L6.2 9 Z" /></svg>
              <span class="min-w-0 flex-1">{{ c.title }}</span>
              <span class="flex-none text-wl-on-surface-variant tabular-nums">{{ c.since }}</span>
            </button>
          } @empty {
            <p class="wl-text2 text-wl-on-surface-variant">{{ t().noConflicts }}</p>
          }
        </section>
            </div>
          </sanring-tabs-content>
          <sanring-tabs-content value="events" class="mt-3">
            <div data-testid="sovereignty-card-panel-events">
        <!-- 事件時間線：與此政權相關、有日期的事件（結構同起訖變動：名稱 → 日期 → 查證＋出處）；點日期跳到該日 -->
        <section data-testid="sovereignty-card-timeline" class="">
          <h3 class="sr-only">{{ t().events }}</h3>
          @switch (eventsStatus()) {
            @case ('loading') { <p class="wl-text2 text-wl-on-surface-variant">{{ t().loading }}</p> }
            @case ('error') { <p class="wl-text2 text-wl-error">{{ t().loadError }}</p> }
            @default {
              <ol class="relative ml-1 border-l border-wl-outline-variant">
                @for (e of timeline(); track e.ev.id) {
                  <li data-testid="sovereignty-card-timeline-item" [attr.data-event-id]="e.ev.id" [attr.data-when]="e.when" class="relative mb-3 pl-4 wl-text2"
                    [class.opacity-60]="e.when === 'future'">
                    <span class="absolute -left-[5px] top-1.5 size-2.5 rounded-full border border-wl-outline" [class.bg-wl-secondary]="e.when === 'now'" [class.bg-wl-surface]="e.when !== 'now'" aria-hidden="true"></span>
                    <div class="mb-0.5 flex flex-wrap items-center gap-1.5">
                      <button type="button" data-testid="sovereignty-card-timeline-jump" class="tabular-nums font-semibold underline decoration-dotted underline-offset-2 hover:text-wl-secondary"
                        [attr.aria-label]="t().jump + ' ' + e.ev.occurred.start" (click)="eventJump.emit(e.ev.occurred.start ?? '')">{{ e.ev.occurred.start }}</button>
                      @for (r of e.roles; track r) { <span class="rounded-sm bg-wl-surface-container-high px-1 text-[11px] text-wl-on-surface-variant">{{ r }}</span> }
                      @if (e.when === 'now') { <span class="text-[11px] text-wl-secondary">{{ t().now }}</span> }
                    </div>
                    <wl-event-ref [ev]="e.ev" prefix="sovereignty-card-timeline" [lang]="lang()" />
                  </li>
                } @empty {
                  <li class="pl-4 wl-text2 text-wl-on-surface-variant">{{ t().noEvents }}</li>
                }
              </ol>
            }
          }
        </section>
            </div>
          </sanring-tabs-content>
        </div>
      </sanring-tabs>
      } @else {
      <div data-testid="sovereignty-card-body" class="mt-2 min-h-0 overflow-y-auto overscroll-contain pr-1">
        <ng-container *ngTemplateOutlet="overview" />
      </div>
      }
      <ng-template #overview>
      <dl class="grid grid-cols-[76px_1fr] gap-x-2 gap-y-1.5 wl-text2">
        <dt class="text-wl-on-surface-variant">{{ t().status }}</dt>
        <dd data-testid="sovereignty-card-status">{{ props().layerStatus === 'not_sovereign' ? t().notSovereign : t().deJure }}</dd>
        <dt class="text-wl-on-surface-variant">{{ t().period }}</dt>
        <dd>{{ props().validPeriod.start }} {{ t().until }} {{ props().validPeriod.end ?? '—' }}</dd>
        @if (noteText(); as n) {
          <dt class="text-wl-on-surface-variant">{{ t().note }}</dt>
          <dd data-testid="sovereignty-card-note" class="min-w-0 whitespace-pre-line">{{ n }}</dd>
        }
        @for (row of events(); track row.key) {
          <dt class="text-wl-on-surface-variant">{{ row.label }}</dt>
          <dd [attr.data-testid]="'sovereignty-card-' + row.key" class="min-w-0">
            @if (row.ev; as ev) {
              <!-- 起始／結束變動同一結構：事件名稱 → 日期 → 查證狀態＋出處（Tai 2026-10-31；與衝突卡共用 wl-event-ref） -->
              <wl-event-ref [ev]="ev" prefix="sovereignty-card" [lang]="lang()" />
            } @else {
              <span class="text-wl-on-surface-variant">{{ row.key === 'start' ? t().none : t().open }}</span>
            }
          </dd>
        }
        <dt class="text-wl-on-surface-variant">{{ t().camp }}</dt>
        <dd data-testid="sovereignty-card-camp" [attr.data-camp]="camp() ?? 'unassigned'">
          {{ campText() }}
          <div class="text-wl-on-surface-variant">{{ t().campNote }}</div>
        </dd>
        <dt class="text-wl-on-surface-variant">{{ t().geometry }}</dt>
        <dd data-testid="sovereignty-card-geometry">
          <div>{{ props().geometry.sourceTitle }}</div>
          <div class="text-wl-on-surface-variant">{{ props().geometry.locator }}</div>
          <div class="text-wl-on-surface-variant">{{ t().license }}：{{ props().geometry.geometryLicense }}@if (props().geometry.attribution; as a) {；{{ a }}}</div>
          @if (osmDerived()) { <div class="text-wl-on-surface-variant" data-testid="sovereignty-card-osm">{{ t().osm }}</div> }
        </dd>
      </dl>
      </ng-template>
    </article>
  `,
})
export class SovereigntyCard {
  readonly props = input.required<SovereigntyFeatureProperties>();
  readonly regimeName = input('');
  readonly originalName = input('');
  readonly originalLang = input('');
  readonly lang = input<Lang>('zh-Hant');
  /** 放在側邊面板（wl-regime-sheet）裡：不畫紙卡外框與標題列（標題、關閉鈕由面板提供）。 */
  readonly embedded = input(false);
  /** 當日與此政權相關的衝突（地圖雙劍同一份）。 */
  readonly conflicts = input<{ recordId: string; title: string; since: string }[]>([]);
  readonly regimeEvents = input<RegimeEventDto[] | null>(null);
  readonly eventsStatus = input<'idle' | 'loading' | 'ok' | 'error'>('idle');
  /** 目前日期：時間線標示「目前」（最後一個不晚於此日的事件）與之後的事件。 */
  readonly currentDate = input('');
  /** 目前分頁（embedded 時）：由頁面保存，切換政權時保留（例如連續比較各政權的事件），面板關閉後回到「概要」。 */
  readonly tab = input<SovereigntyTab>('overview');
  readonly tabChange = output<SovereigntyTab>();
  readonly closed = output<void>();
  readonly conflictSelect = output<string>();
  readonly eventJump = output<string>();
  protected onTab(v: string) {
    if (v === 'overview' || v === 'events') this.tabChange.emit(v);
  }
  protected readonly timeline = computed(() => {
    const d = this.currentDate();
    const list = this.regimeEvents() ?? [];
    let nowIdx = -1;
    list.forEach((e, i) => {
      if (d && (e.occurred.start ?? '') <= d) nowIdx = i;
    });
    return list.map((ev, i) => ({
      ev,
      roles: [...new Set(ev.roles.map((r) => this.t().role[r] ?? r))],
      when: (i === nowIdx ? 'now' : i < nowIdx ? 'past' : 'future') as 'past' | 'now' | 'future',
    }));
  });

  protected readonly t = computed(() => TXT[this.lang() === 'en' ? 'en' : 'zh-Hant']);
  protected readonly camp = computed(() => campOf(this.props().regimeAlignment ?? null));
  protected readonly campText = computed(() => {
    const c = this.camp();
    return c ? CAMP_NAME[c][this.lang() === 'en' ? 'en' : 'zh-Hant'] : this.t().campNone;
  });
  protected readonly events = computed(() => [
    { key: 'start', label: this.t().start, ev: this.props().startEvent },
    { key: 'end', label: this.t().end, ev: this.props().endEvent },
  ]);
  /** 紀錄註記（幾何簡化、OHM 缺漏等說明）：依介面語言，沒有就用另一語言。 */
  protected readonly noteText = computed(() => {
    const n = (this.props() as unknown as { note?: Record<string, string> | null }).note;
    if (!n) return '';
    return (this.lang() === 'en' ? n['en'] || n['zh-Hant'] : n['zh-Hant'] || n['en']) ?? '';
  });
  protected readonly osmDerived = computed(() => {
    const f = this.props().geometry.flags as unknown as { osmDerivedWayCount?: number } | null;
    return (f?.osmDerivedWayCount ?? 0) > 0;
  });
}
