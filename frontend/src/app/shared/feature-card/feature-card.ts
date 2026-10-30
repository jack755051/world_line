import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideX } from '@lucide/angular';
import type { ControlFeatureProperties, TheaterStateDto } from '../../core/api/api-types';
import { hasKey, t, type I18nKey, type Lang } from '../../core/i18n';
import { theaterLabel } from '../../core/theater-tracks';
import { CitationPopover } from '../citation/citation-popover';
import { campOf, type Evidence } from '../map/map-style';

/**
 * 地圖控制區卡片（點地圖區塊時出現，Stitch W1 的「德國・軍事佔領」卡）。
 * 顯示政權名・控制類型、史料或推估、有效期間（含不確定區間）、戰區，以及來源按鈕（PRD §8.9）。
 * 完整的政權聚焦面板（§8.6）不在 C8 範圍。
 */
@Component({
  selector: 'wl-feature-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CitationPopover, LucideX],
  template: `
    <article data-testid="feature-card" class="wl-paper w-[300px] p-4" role="dialog" [attr.aria-label]="title()">
      <header class="flex items-start justify-between gap-2 border-b border-wl-outline-variant pb-2">
        <div>
          <h2 class="wl-title2" data-testid="feature-card-title">{{ title() }}</h2>
          @if (originalName()) { <p class="wl-text2 text-wl-on-surface-variant" [attr.lang]="originalLang() || null">{{ originalName() }}</p> }
        </div>
        <button type="button" class="wl-icon-btn" [attr.aria-label]="tr('card.close')" (click)="closed.emit()"><svg lucideX class="size-4"></svg></button>
      </header>
      <dl class="mt-2 grid grid-cols-[72px_1fr] gap-x-2 gap-y-1.5 wl-text2">
        <dt class="text-wl-on-surface-variant">{{ tr('card.evidence') }}</dt>
        <dd data-testid="feature-card-evidence">
          @if (evidence() === 'attested') {
            <span class="wl-stamp">{{ tr('evidence.attested') }} {{ attestedDate() }}</span>
          } @else {
            <span class="wl-chip-interp">{{ evidenceText() }}</span>
          }
        </dd>
        <dt class="text-wl-on-surface-variant">{{ tr('card.validPeriod') }}</dt>
        <dd>{{ period(props().validPeriod) }}
          @if (uncertainty(); as u) { <div class="text-wl-on-surface-variant">{{ u }}</div> }
        </dd>
        <dt class="text-wl-on-surface-variant">{{ tr('card.theater') }}</dt>
        <dd>{{ theater() }}</dd>
        <dt class="text-wl-on-surface-variant">{{ tr('card.camp') }}</dt>
        <dd data-testid="feature-card-camp" [attr.data-camp]="camp() ?? 'unassigned'">
          @if (props().controllerAlignment; as al) {
            {{ campLabel() }}（{{ period(al.validPeriod) }}）
            @for (c of primaryAlignmentCitations(); track c.sourceId + c.locator) {
              <div class="text-wl-on-surface-variant" data-testid="feature-card-camp-basis">{{ tr('card.campBasis') }}：{{ c.sourceTitle }}，{{ c.locator }}</div>
            }
          } @else {
            <span class="text-wl-on-surface-variant">{{ tr('legend.campUnassigned') }}</span>
          }
        </dd>
        @if (props().isDisputed) {
          <dt class="text-wl-on-surface-variant"></dt><dd><span class="wl-badge">{{ tr('card.disputed') }}</span></dd>
        }
      </dl>
      <footer class="mt-3 flex justify-end">
        <wl-citation-popover [citations]="props().citations" [lang]="lang()" />
      </footer>
    </article>
  `,
})
export class FeatureCard {
  readonly props = input.required<ControlFeatureProperties>();
  readonly regimeName = input<string>('');
  readonly originalName = input<string>('');
  readonly originalLang = input<string>('');
  readonly evidence = input<Evidence>('unknown');
  readonly theaterState = input<TheaterStateDto | null>(null);
  readonly lang = input<Lang>('zh-Hant');
  readonly closed = output<void>();

  protected readonly title = computed(() => {
    const key = `control.${this.props().controlType}`;
    const type = hasKey(key) ? t(key, this.lang()) : this.props().controlType;
    return `${this.regimeName() || '—'}・${type}`;
  });

  protected readonly attestedDate = computed(() => this.theaterState()?.attestingSnapshot?.asOf ?? '');

  protected readonly evidenceText = computed(() => {
    const s = this.theaterState();
    switch (this.evidence()) {
      case 'interpolated':
        return `${t('evidence.interpolated', this.lang())}：${s?.prevSnapshot?.asOf ?? '?'} → ${s?.nextSnapshot?.asOf ?? '?'}`;
      case 'outside':
        return t('evidence.outside', this.lang());
      default:
        return t('evidence.unknown', this.lang());
    }
  });

  protected readonly camp = computed(() => campOf(this.props().controllerAlignment));
  protected readonly campLabel = computed(() => {
    const c = this.camp();
    return c ? t(`camp.${c}` as I18nKey, this.lang()) : t('legend.campUnassigned', this.lang());
  });
  protected readonly primaryAlignmentCitations = computed(
    () => this.props().controllerAlignment?.citations.filter((c) => c.role === 'primary') ?? [],
  );

  protected readonly theater = computed(() => theaterLabel(this.props().theaterCode, this.lang()));

  protected readonly uncertainty = computed(() => {
    const v = this.props().validPeriod;
    const parts: string[] = [];
    const u = t('card.uncertain', this.lang());
    if (v.startUncertainty) parts.push(`${this.lang() === 'en' ? 'start' : '起'} ${u} ${this.period(v.startUncertainty)}`);
    if (v.endUncertainty) parts.push(`${this.lang() === 'en' ? 'end' : '迄'} ${u} ${this.period(v.endUncertainty)}`);
    return parts.join('；');
  });

  protected tr(key: I18nKey): string {
    return t(key, this.lang());
  }

  /** 區間為半開 [start, end)（PRD §7） */
  protected period(p: { start?: string | null; end?: string | null } | null | undefined): string {
    if (!p) return '';
    return `${p.start ?? '…'} – ${p.end ?? '…'}`;
  }
}
