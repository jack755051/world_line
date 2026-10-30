import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideBookOpen } from '@lucide/angular';
import { SkeletonDirective } from '../../components/ui/skeleton';
import type { TheaterStateDto } from '../../core/api/api-types';
import type { LoadStatus } from '../../core/atlas-data';
import { formatDisplayDate } from '../../core/dates';
import { t, type I18nKey, type Lang } from '../../core/i18n';
import { InterpChip } from '../../shared/interp-chip/interp-chip';

/**
 * 頂部列（PRD §8.1，`layout/top-bar`）。
 * 紀年：目前沒有紀年 API（`/eras` 未實作），依 §8.1 empty 規則只顯示西元，不顯示空白括號。
 * 主權檢視：沒有主權 API，切換鈕先停用並說明。
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
        <div class="wl-seg" role="group" [attr.aria-label]="lang() === 'en' ? 'View' : '檢視'">
          <button type="button" data-testid="axis-toggle-control" aria-pressed="true">{{ tr('axis.control') }}</button>
          <button type="button" data-testid="axis-toggle-sovereignty" aria-pressed="false" disabled [attr.title]="tr('axis.sovereignty.unavailable')">{{ tr('axis.sovereignty') }}</button>
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
  readonly langChange = output<Lang>();
  readonly legendToggle = output<void>();
  readonly jump = output<string>();

  protected readonly display = computed(() => formatDisplayDate(this.date(), this.lang()));
  protected tr(key: I18nKey): string {
    return t(key, this.lang());
  }
}
