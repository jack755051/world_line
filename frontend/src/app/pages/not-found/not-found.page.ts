import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideArrowLeft } from '@lucide/angular';
import { t } from '../../core/i18n';

/** 找不到頁面（PRD §8.11；Stitch W7-3：置中紙卡＋22px 襯線標題＋次要按鈕「回主地圖」）。 */
@Component({
  selector: 'wl-not-found-page',
  imports: [RouterLink, LucideArrowLeft],
  host: { class: 'block h-full' },
  template: `
    <main data-testid="not-found-page" class="flex h-full items-center justify-center bg-wl-background">
      <div class="wl-paper flex w-[400px] flex-col items-center gap-5 px-8 py-8 text-center">
        <h1 class="wl-title1">{{ title }}</h1>
        <a routerLink="/" data-testid="not-found-back" class="wl-btn-secondary inline-flex h-9 items-center gap-2 px-5 wl-text2">
          <svg lucideArrowLeft class="size-3.5" aria-hidden="true"></svg>{{ back }}</a>
      </div>
    </main>
  `,
})
export class NotFoundPage {
  protected readonly title = t('notFound.title', 'zh-Hant');
  protected readonly back = t('notFound.back', 'zh-Hant');
}
