import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideX } from '@lucide/angular';
import type { CoverageNoteDto } from '../../core/api/api-types';
import { hasKey, localized, t, type I18nKey, type Lang } from '../../core/i18n';

/**
 * 控制資料缺卡片（R9，點地圖上的點狀區塊時出現）：說明這裡「沒有合格來源判斷實際控制」及原因。
 * 只顯示 API 的涵蓋備註；不顯示任何控制類型，也不推測誰控制。
 */
@Component({
  selector: 'wl-gap-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideX],
  template: `
    <article data-testid="gap-card" class="wl-paper w-[300px] p-4" role="dialog" [attr.aria-label]="tr('legend.gap')">
      <header class="flex items-start justify-between gap-2 border-b border-wl-outline-variant pb-2">
        <div class="flex items-center gap-2">
          <span class="inline-block size-4 wl-gap-pattern border border-wl-outline-variant"></span>
          <h2 class="wl-title2">{{ tr('legend.gap') }}</h2>
        </div>
        <button type="button" class="wl-icon-btn" [attr.aria-label]="tr('card.close')" (click)="closed.emit()"><svg lucideX class="size-4"></svg></button>
      </header>
      <dl class="mt-2 grid grid-cols-[72px_1fr] gap-x-2 gap-y-1.5 wl-text2">
        <dt class="text-wl-on-surface-variant">{{ tr('gap.reason') }}</dt>
        <dd data-testid="gap-card-reason">{{ reason() }}</dd>
        <dt class="text-wl-on-surface-variant">{{ tr('card.validPeriod') }}</dt>
        <dd>{{ note().validPeriod.start ?? '…' }} – {{ note().validPeriod.end ?? '…' }}</dd>
        @if (text().text) {
          <dt class="text-wl-on-surface-variant">{{ tr('gap.note') }}</dt>
          <dd data-testid="gap-card-note">{{ text().text }}@if (text().untranslated) { <span class="wl-badge ml-1">{{ tr('untranslated') }}</span> }</dd>
        }
        @if (note().researchRef) {
          <dt class="text-wl-on-surface-variant">{{ tr('gap.ref') }}</dt>
          <dd class="break-all text-wl-on-surface-variant">{{ note().researchRef }}</dd>
        }
      </dl>
      <p class="mt-2 wl-text2 text-wl-on-surface-variant">{{ tr('legend.gap.note') }}</p>
    </article>
  `,
})
export class GapCard {
  readonly note = input.required<CoverageNoteDto>();
  readonly lang = input<Lang>('zh-Hant');
  readonly closed = output<void>();

  protected readonly reason = computed(() => {
    const key = `gap.reason.${this.note().reason}`;
    return hasKey(key) ? t(key, this.lang()) : this.note().reason;
  });
  protected readonly text = computed(() => localized(this.note().note as Record<string, string> | null, this.lang()));

  protected tr(key: I18nKey): string {
    return t(key, this.lang());
  }
}
