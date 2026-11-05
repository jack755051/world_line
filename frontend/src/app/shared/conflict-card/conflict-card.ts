import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideX } from '@lucide/angular';
import type { ConflictFeatureProperties } from '../../core/api/api-types';
import type { Lang } from '../../core/i18n';
import { EventRef } from '../event-ref/event-ref';
import { isDebugMode } from '../../core/debug';

const TXT = {
  'zh-Hant': {
    kind: '性質', war: '交戰（衝突圖示）', period: '衝突期間', start: '開戰', end: '停戰／投降', open: '本試驗範圍內未結束',
    until: '至', location: '圖示位置', close: '關閉', campaign: '戰役簡報', timeline: '在時間線上看',
  },
  en: {
    kind: 'Type', war: 'Hostilities (conflict marker)', period: 'Period', start: 'Began with', end: 'Ended with', open: 'Not ended within this trial',
    until: 'to', location: 'Marker placement', close: 'Close', campaign: 'Campaign briefing', timeline: 'Show in timeline',
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
    <article data-testid="conflict-card" [class]="embedded() ? 'flex min-h-0 flex-1 flex-col' : inSheet() ? 'flex min-h-0 w-full flex-col px-4 pb-3' : 'wl-paper flex max-h-[inherit] min-h-0 w-[320px] max-w-full flex-col p-4'"
      [attr.role]="embedded() ? null : 'dialog'" [attr.aria-label]="embedded() ? null : title()">
      @if (!embedded() && !peek()) {
      <header class="flex flex-none items-start justify-between gap-2 border-b border-wl-outline-variant pb-2">
        <h2 class="wl-title2" data-testid="conflict-card-title">{{ title() }}</h2>
        <button type="button" class="wl-icon-btn" data-testid="conflict-card-close" [attr.aria-label]="t().close" (click)="closed.emit()"><svg lucideX class="size-4"></svg></button>
      </header>
      }
      <!-- §13：交戰方色票＋名稱（點名稱切到該政權面板） -->
      <div class="mt-2 flex flex-none flex-wrap gap-x-3 gap-y-1 wl-text2">
        <button type="button" data-testid="conflict-card-side-a" class="inline-flex items-center gap-1 hover:underline" (click)="regimeSelect.emit('a')"><i class="inline-block size-3 rounded-sm" [style.background]="colorA()"></i>{{ nameA() || props().regimeASlug }}</button>
        <button type="button" data-testid="conflict-card-side-b" class="inline-flex items-center gap-1 hover:underline" (click)="regimeSelect.emit('b')"><i class="inline-block size-3 rounded-sm" [style.background]="colorB()"></i>{{ nameB() || props().regimeBSlug }}</button>
      </div>
      <dl data-testid="conflict-card-body" class="mt-2 grid min-h-0 grid-cols-[76px_1fr] gap-x-2 gap-y-1.5 overflow-y-auto overscroll-contain pr-1 wl-text2">
        @if (!peek()) {
        <dt class="text-wl-on-surface-variant">{{ t().kind }}</dt>
        <dd>{{ t().war }}</dd>
        }
        <dt class="text-wl-on-surface-variant">{{ t().period }}</dt>
        <dd data-testid="conflict-card-period">{{ props().startEvent.occurred.start }} {{ t().until }} {{ props().endEvent?.occurred?.start ?? '—' }}</dd>
        @if (!peek()) {
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
        }
        @if (debug() && !peek()) {
          <!-- §13 K3：技術說明只在除錯模式顯示 -->
          <dt class="text-wl-on-surface-variant">{{ t().location }}</dt>
          <dd data-testid="conflict-card-location" class="text-wl-on-surface-variant">{{ props().locationMethod }}</dd>
        }
      </dl>
      @if (!embedded()) {
        <!-- §13 動作列：戰役簡報（符合戰役定義才出現）／在時間線上看／× -->
        <div class="mt-3 flex flex-none flex-wrap items-center gap-2">
          @for (c of campaigns(); track c.key) {
            <button type="button" data-testid="conflict-card-campaign" class="wl-btn-primary h-8 px-3 wl-text2" (click)="campaignOpen.emit(c.key)">⚔ {{ t().campaign }}</button>
          }
          <button type="button" data-testid="conflict-card-timeline" class="wl-btn-secondary h-8 px-3 wl-text2" (click)="timelineShow.emit()">{{ t().timeline }}</button>
          @if (peek()) {
            <button type="button" class="wl-icon-btn ml-auto" data-testid="conflict-card-close" [attr.aria-label]="t().close" (click)="closed.emit()"><svg lucideX class="size-4"></svg></button>
          }
        </div>
      }
    </article>
  `,
})
export class ConflictCard {
  readonly props = input.required<ConflictFeatureProperties>();
  readonly nameA = input('');
  readonly nameB = input('');
  readonly lang = input<Lang>('zh-Hant');
  /** 放在側邊面板裡：不畫紙卡外框與標題列。 */
  readonly embedded = input(false);
  readonly closed = output<void>();
  readonly colorA = input('#9ca3af');
  readonly colorB = input('#9ca3af');
  /** 符合戰役定義的戰役（§13 K2）；空陣列＝不顯示「戰役簡報」。 */
  readonly campaigns = input<{ key: string; name_zh: string }[]>([]);
  /** 手機 peek（140px）：只顯示交戰方、期間和按鈕。 */
  readonly peek = input(false);
  /** 手機衝突面板裡：不畫紙卡外框、滿寬。 */
  readonly inSheet = input(false);
  readonly regimeSelect = output<'a' | 'b'>();
  readonly timelineShow = output<void>();
  readonly campaignOpen = output<string>();
  /** 除錯模式（§13 K3）；測試可直接覆寫。 */
  readonly debug = input(isDebugMode());

  protected readonly t = computed(() => TXT[this.lang() === 'en' ? 'en' : 'zh-Hant']);
  readonly title = computed(
    () => `${this.nameA() || this.props().regimeASlug} — ${this.nameB() || this.props().regimeBSlug}`,
  );
}
