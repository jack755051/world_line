import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideX } from '@lucide/angular';
import type { SovereigntyEventRefDto, SovereigntyFeatureProperties } from '../../core/api/api-types';
import { localized, type Lang } from '../../core/i18n';
import { campOf } from '../map/map-style';

const TXT = {
  'zh-Hant': {
    period: '國界期間', status: '性質', deJure: '國界', notSovereign: '非主權（佔領行政區）', start: '起始變動', end: '結束變動',
    none: '本試驗範圍前即存在（不追溯）', open: '本試驗範圍內未結束', pending: '待查證', verified: '已查證', camp: '陣營（補充）',
    campNone: '陣營未建置', geometry: '國界來源', license: '幾何授權', osm: '含 OpenStreetMap 來源線段（ODbL）', close: '關閉',
    campNote: '陣營只作補充，不影響填色', until: '至',
  },
  en: {
    period: 'Valid', status: 'Status', deJure: 'Border', notSovereign: 'Not sovereign (occupation administration)', start: 'Began with', end: 'Ended with',
    none: 'Existed before this trial (not traced)', open: 'Not ended within this trial', pending: 'Pending verification', verified: 'Verified', camp: 'Camp (supplement)',
    campNone: 'Camp not set', geometry: 'Border source', license: 'Geometry licence', osm: 'Contains OpenStreetMap-derived segments (ODbL)', close: 'Close',
    campNote: 'Camp is supplementary and does not affect fill', until: 'to',
  },
} as const;
const CAMP_NAME: Record<string, { 'zh-Hant': string; en: string }> = {
  axis: { 'zh-Hant': '軸心', en: 'Axis' }, allies: { 'zh-Hant': '同盟', en: 'Allies' },
  cobelligerent: { 'zh-Hant': '共同交戰／合作', en: 'Co-belligerent' }, neutral: { 'zh-Hant': '中立／未結盟', en: 'Neutral' },
};

/**
 * 主權圖層（國界）資訊卡：政權名、國界期間、起訖疆界變動事件（有引用＝已查證，沒有＝「待查證」）、
 * 國界幾何來源（OHM 關係 id／版本、授權、署名），陣營只在這裡作補充。
 */
@Component({
  selector: 'wl-sovereignty-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideX],
  template: `
    <article data-testid="sovereignty-card" class="wl-paper w-[340px] p-4" role="dialog" [attr.aria-label]="regimeName()" [attr.data-layer-status]="props().layerStatus">
      <header class="flex items-start justify-between gap-2 border-b border-wl-outline-variant pb-2">
        <div>
          <h2 class="wl-title2" data-testid="sovereignty-card-title">{{ regimeName() }}</h2>
          @if (originalName()) { <p class="wl-text2 text-wl-on-surface-variant" [attr.lang]="originalLang() || null">{{ originalName() }}</p> }
        </div>
        <button type="button" class="wl-icon-btn" [attr.aria-label]="t().close" (click)="closed.emit()"><svg lucideX class="size-4"></svg></button>
      </header>
      <dl class="mt-2 grid grid-cols-[76px_1fr] gap-x-2 gap-y-1.5 wl-text2">
        <dt class="text-wl-on-surface-variant">{{ t().status }}</dt>
        <dd data-testid="sovereignty-card-status">{{ props().layerStatus === 'not_sovereign' ? t().notSovereign : t().deJure }}</dd>
        <dt class="text-wl-on-surface-variant">{{ t().period }}</dt>
        <dd>{{ props().validPeriod.start }} {{ t().until }} {{ props().validPeriod.end ?? '—' }}</dd>
        @for (row of events(); track row.key) {
          <dt class="text-wl-on-surface-variant">{{ row.label }}</dt>
          <dd [attr.data-testid]="'sovereignty-card-' + row.key">
            @if (row.ev; as ev) {
              <div>{{ summary(ev) }}（{{ ev.occurred.start }}）</div>
              @if (ev.verification === 'pending') {
                <span class="wl-chip-interp" data-testid="sovereignty-card-pending">{{ t().pending }}</span>
              } @else {
                <span class="wl-stamp">{{ t().verified }}</span>
                @for (c of ev.citations; track c.sourceId + c.locator) {
                  <div class="text-wl-on-surface-variant" data-testid="sovereignty-card-citation">{{ c.sourceTitle }}，{{ c.locator }}</div>
                }
              }
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
    </article>
  `,
})
export class SovereigntyCard {
  readonly props = input.required<SovereigntyFeatureProperties>();
  readonly regimeName = input('');
  readonly originalName = input('');
  readonly originalLang = input('');
  readonly lang = input<Lang>('zh-Hant');
  readonly closed = output<void>();

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
  protected readonly osmDerived = computed(() => {
    const f = this.props().geometry.flags as unknown as { osmDerivedWayCount?: number } | null;
    return (f?.osmDerivedWayCount ?? 0) > 0;
  });

  protected summary(ev: SovereigntyEventRefDto): string {
    return localized((ev.summary ?? {}) as Record<string, string>, this.lang()).text || ev.eventKind;
  }
}
