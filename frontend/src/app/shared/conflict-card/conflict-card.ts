import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideX } from '@lucide/angular';
import type { ConflictFeatureProperties } from '../../core/api/api-types';
import type { Lang } from '../../core/i18n';
import { EventRef } from '../event-ref/event-ref';

const TXT = {
  'zh-Hant': {
    kind: '性質', war: '交戰（衝突圖示）', period: '衝突期間', start: '開戰', end: '停戰／投降', open: '本試驗範圍內未結束',
    until: '至', location: '圖示位置', close: '關閉',
  },
  en: {
    kind: 'Type', war: 'Hostilities (conflict marker)', period: 'Period', start: 'Began with', end: 'Ended with', open: 'Not ended within this trial',
    until: 'to', location: 'Marker placement', close: 'Close',
  },
} as const;

/**
 * 衝突（交叉雙劍圖示）資訊卡：結構與政權卡一致——標題、期間、開戰事件與停戰／投降事件
 * （期間以開戰／停戰事件日期表示，含停戰當日；同一個 wl-event-ref：事件名稱 → 日期 → 查證狀態＋出處；缺出處標「待查證」，不補造），最後是圖示位置的算法說明。
 */
@Component({
  selector: 'wl-conflict-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideX, EventRef],
  template: `
    <article data-testid="conflict-card" class="wl-paper flex max-h-[inherit] min-h-0 w-[340px] flex-col p-4" role="dialog" [attr.aria-label]="title()">
      <header class="flex flex-none items-start justify-between gap-2 border-b border-wl-outline-variant pb-2">
        <h2 class="wl-title2" data-testid="conflict-card-title">{{ title() }}</h2>
        <button type="button" class="wl-icon-btn" data-testid="conflict-card-close" [attr.aria-label]="t().close" (click)="closed.emit()"><svg lucideX class="size-4"></svg></button>
      </header>
      <dl data-testid="conflict-card-body" class="mt-2 grid min-h-0 grid-cols-[76px_1fr] gap-x-2 gap-y-1.5 overflow-y-auto overscroll-contain pr-1 wl-text2">
        <dt class="text-wl-on-surface-variant">{{ t().kind }}</dt>
        <dd>{{ t().war }}</dd>
        <dt class="text-wl-on-surface-variant">{{ t().period }}</dt>
        <dd data-testid="conflict-card-period">{{ props().startEvent.occurred.start }} {{ t().until }} {{ props().endEvent?.occurred?.start ?? '—' }}</dd>
        <dt class="text-wl-on-surface-variant">{{ t().start }}</dt>
        <dd data-testid="conflict-card-start" class="min-w-0"><wl-event-ref [ev]="props().startEvent" prefix="conflict-card" [lang]="lang()" /></dd>
        <dt class="text-wl-on-surface-variant">{{ t().end }}</dt>
        <dd data-testid="conflict-card-end" class="min-w-0">
          @if (props().endEvent; as ev) {
            <wl-event-ref [ev]="ev" prefix="conflict-card" [lang]="lang()" />
          } @else {
            <span class="text-wl-on-surface-variant">{{ t().open }}</span>
          }
        </dd>
        <dt class="text-wl-on-surface-variant">{{ t().location }}</dt>
        <dd data-testid="conflict-card-location" class="text-wl-on-surface-variant">{{ props().locationMethod }}</dd>
      </dl>
    </article>
  `,
})
export class ConflictCard {
  readonly props = input.required<ConflictFeatureProperties>();
  readonly nameA = input('');
  readonly nameB = input('');
  readonly lang = input<Lang>('zh-Hant');
  readonly closed = output<void>();

  protected readonly t = computed(() => TXT[this.lang() === 'en' ? 'en' : 'zh-Hant']);
  protected readonly title = computed(
    () => `${this.nameA() || this.props().regimeASlug} — ${this.nameB() || this.props().regimeBSlug}`,
  );
}
