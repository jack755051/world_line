import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideChevronDown } from '@lucide/angular';
import { SkeletonDirective } from '../../components/ui/skeleton';
import type { LoadStatus } from '../../core/atlas-data';
import { t, type I18nKey, type Lang } from '../../core/i18n';
import { CAMP_TONES, CAMP_UNASSIGNED_TONE, CONTROL_TYPES, darken, type Camp } from '../map/map-style';

export interface LegendRegime {
  id: string;
  name: string;
  tone: string;
}

/**
 * 圖例（PRD §8.4，`shared/legend`，左下浮動、可收合）。
 * 樣式說明固定顯示；「目前畫面中的政權」來自 API 載入的控制區。
 */
@Component({
  selector: 'wl-legend',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideChevronDown, SkeletonDirective],
  host: { class: 'block' },
  styles: `
    .sw { width: 22px; height: 14px; flex: none; border-radius: 2px; }
    .row { display: flex; align-items: center; gap: 8px; }
  `,
  template: `
    <section data-testid="legend" class="wl-paper w-[280px] overflow-hidden" [attr.aria-label]="tr('legend.title')">
      <button type="button" class="flex w-full items-center justify-between px-4 py-3 text-left" (click)="toggle.emit()"
        [attr.aria-expanded]="open()" aria-controls="wl-legend-body">
        <span><span class="wl-title2">{{ tr('legend.title') }}</span>
          <span class="ml-2 wl-text2 text-wl-on-surface-variant">{{ tr('legend.mode.control') }}</span></span>
        <svg lucideChevronDown class="size-4 transition-transform" [class.rotate-180]="!open()"></svg>
      </button>
      @if (open()) {
        <div id="wl-legend-body" class="flex max-h-[calc(100vh-56px-112px-120px)] flex-col gap-4 overflow-y-auto border-t border-wl-outline-variant px-4 py-3 wl-text2">
          <div>
            <h3 class="wl-label mb-2">{{ tr('legend.controlTypes') }}</h3>
            <ul class="flex flex-col gap-1.5">
              @for (ct of controlTypes; track ct) {
                <li class="row" [attr.data-testid]="'legend-control-type-' + ct">
                  <span class="sw" [style]="swatch(ct)"></span>{{ tr(ctKey(ct)) }}
                </li>
              }
            </ul>
          </div>
          <div data-testid="legend-control-gap">
            <div class="row"><span class="sw wl-gap-pattern border border-wl-outline-variant"></span><span class="wl-label">{{ tr('legend.gap') }}</span></div>
            <p class="mt-1 text-wl-on-surface-variant">{{ tr('legend.gap.note') }}</p>
          </div>
          <div class="row" data-testid="legend-frontline"><span class="sw" style="height:0;border-top:2.5px solid #3a2f28"></span>{{ tr('legend.frontline') }}</div>
          <div>
            <h3 class="wl-label mb-2">{{ tr('legend.evidence') }}</h3>
            <div class="flex gap-2">
              <span data-testid="legend-attested" class="row flex-1 rounded-wl-sm border border-wl-outline-variant px-2 py-1">
                <span class="sw" [style]="'background:' + unassigned + ';opacity:.6;border:2px solid ' + unassignedEdge"></span>{{ tr('evidence.attested') }}</span>
              <span data-testid="legend-interpolated" class="row flex-1 rounded-wl-sm border border-dashed border-wl-secondary px-2 py-1">
                <span class="sw" [style]="'background:' + unassigned + ';opacity:.33;border:1.5px dashed ' + unassignedEdge"></span>{{ tr('evidence.interpolated') }}</span>
            </div>
          </div>
          <div>
            <h3 class="wl-label mb-2">{{ tr('legend.camps') }}</h3>
            <ul class="grid grid-cols-2 gap-1.5">
              @for (c of camps; track c) {
                <li class="row" [attr.data-testid]="'legend-camp-' + c"><span class="sw" [style.background]="campTone(c)"></span>{{ tr(campKey(c)) }}</li>
              }
              <li class="row col-span-2" data-testid="legend-camp-unassigned"><span class="sw" [style.background]="unassigned"></span>{{ tr('legend.campUnassigned') }}</li>
            </ul>
            <p class="mt-1 text-wl-on-surface-variant">{{ tr('legend.camps.unassigned') }}</p>
          </div>
          <div>
            <h3 class="wl-label mb-2">{{ tr('legend.regimes') }}</h3>
            @if (regimesStatus() === 'loading' && regimes().length === 0) {
              <div class="flex flex-col gap-1.5"><div sanringSkeleton class="h-4 w-40"></div><div sanringSkeleton class="h-4 w-32"></div></div>
            } @else if (regimesStatus() === 'error') {
              <p class="text-wl-error">{{ tr('legend.regimes.error') }}</p>
            } @else if (regimes().length === 0) {
              <p class="text-wl-on-surface-variant">{{ tr('legend.regimes.empty') }}</p>
            } @else {
              <ul class="flex flex-col gap-1.5">
                @for (r of regimes(); track r.id) {
                  <li class="row" data-testid="legend-regime-item"><span class="sw" [style.background]="r.tone"></span>{{ r.name }}</li>
                }
              </ul>
            }
          </div>
        </div>
      }
    </section>
  `,
})
export class Legend {
  readonly open = input(true);
  readonly lang = input<Lang>('zh-Hant');
  readonly regimes = input<LegendRegime[]>([]);
  readonly regimesStatus = input<LoadStatus>('idle');
  readonly toggle = output<void>();

  protected readonly controlTypes = CONTROL_TYPES;
  protected readonly camps = Object.keys(CAMP_TONES) as Camp[];
  protected readonly unassigned = CAMP_UNASSIGNED_TONE;
  protected readonly unassignedEdge = darken(CAMP_UNASSIGNED_TONE, 0.25);
  private readonly sample = computed(() => this.unassigned);

  protected tr(key: I18nKey): string {
    return t(key, this.lang());
  }
  protected ctKey(ct: string): I18nKey {
    return `control.${ct}` as I18nKey;
  }
  protected campKey(c: Camp): I18nKey {
    return `camp.${c}` as I18nKey;
  }
  protected campTone(c: Camp): string {
    return CAMP_TONES[c][0];
  }

  /** 圖例樣本與地圖同規則（DESIGN.md Control types），色票用「陣營未建置」色示意線條樣式。 */
  protected swatch(ct: string): string {
    const c = this.sample();
    const edge = darken(c, 0.25);
    switch (ct) {
      case 'direct_rule':
        return `background:${c};opacity:.85;border:0.75px solid rgba(58,47,40,.4)`;
      case 'military_occupation':
        return `background:color-mix(in srgb, ${c} 60%, #ece4d2);border:2px solid ${edge}`;
      case 'puppet_administration':
        return `background:${c};opacity:.85;border:1.5px dotted #3a2f28`;
      case 'partial':
        return `background:repeating-linear-gradient(-45deg, ${c} 0 1.5px, #ece4d2 1.5px 6px);border:0.75px solid ${c}`;
      default:
        return `background:repeating-linear-gradient(-45deg, ${c} 0 1.5px, transparent 1.5px 6px),repeating-linear-gradient(45deg, ${edge} 0 1.5px, #ece4d2 1.5px 6px);border:0.75px solid ${c}`;
    }
  }
}
