import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { LucideBookOpen, LucideChevronDown, LucideChevronUp } from '@lucide/angular';
import { SkeletonDirective } from '../../components/ui/skeleton';
import type { LoadStatus } from '../../core/atlas-data';
import { t, type I18nKey, type Lang } from '../../core/i18n';
import { CAMP_FILL, CAMP_TONES, CAMP_UNASSIGNED_TONE, CONTROL_TYPES, darken, type Camp } from '../map/map-style';

export interface LegendRegime {
  id: string;
  name: string;
  tone: string;
  /** 當日陣營；null＝陣營未建置 */
  camp?: Camp | null;
  /** 此政權在畫面中的控制類型（決定邊框／紋理樣本） */
  controlTypes?: string[];
  /** 此政權在畫面中的區塊是否全為史料快照（否＝推估過渡虛線邊框） */
  attested?: boolean;
}

/**
 * 圖例（PRD §8.4，`shared/legend`，左下浮動、可收合）。
 * 樣式說明固定顯示；「目前畫面中的政權」來自 API 載入的控制區。
 */
@Component({
  selector: 'wl-legend',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideChevronDown, LucideChevronUp, LucideBookOpen, SkeletonDirective],
  host: { class: 'block' },
  styles: `
    .sw { width: 22px; height: 14px; flex: none; border-radius: 2px; }
    .sw-wide { width: 32px; }
    .row { display: flex; align-items: center; gap: 8px; }
  `,
  template: `
    @if (!open()) {
      <!-- 收合：左下小按鈕「圖例」（Stitch W2／W3／W7-6） -->
      <section data-testid="legend" data-state="collapsed" [attr.aria-label]="tr('legend.title')">
        <button type="button" data-testid="legend-expand" class="wl-paper flex h-8 items-center gap-1.5 px-3 wl-text2 text-wl-on-surface hover:bg-wl-surface-container-high"
          (click)="toggle.emit()" [attr.aria-expanded]="false" aria-controls="wl-legend-body">
          <svg lucideBookOpen class="size-3.5"></svg>{{ tr('legend.title') }}<svg lucideChevronUp class="size-3.5 text-wl-on-surface-variant"></svg>
        </button>
      </section>
    } @else {
    <section data-testid="legend" data-state="open" class="wl-paper w-[280px] overflow-hidden" [attr.aria-label]="tr('legend.title')">
      <button type="button" class="flex w-full items-center justify-between px-4 py-3 text-left" (click)="toggle.emit()"
        [attr.aria-expanded]="open()" aria-controls="wl-legend-body">
        <span class="wl-title2">{{ tr('legend.title') }}</span>
        <svg lucideChevronDown class="size-4 text-wl-on-surface-variant"></svg>
      </button>
      @if (open()) {
        <div id="wl-legend-body" class="flex max-h-[calc(100vh-56px-112px-120px)] flex-col gap-4 overflow-y-auto border-t border-wl-outline-variant px-4 py-3 wl-text2">
          <div>
            <h3 class="wl-label mb-2">{{ tr('legend.controlTypes') }}</h3>
            <ul class="flex flex-col gap-1.5">
              @for (ct of controlTypes; track ct) {
                <li class="row" [attr.data-testid]="'legend-control-type-' + ct">
                  <span class="sw sw-wide" [style]="swatch(ct)"></span>{{ tr(ctKey(ct)) }}
                </li>
              }
            </ul>
            <p data-testid="legend-control-types-note" class="mt-1.5 text-wl-on-surface-variant">{{ tr('legend.controlTypes.note') }}</p>
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
                <span class="sw" [style]="'background:' + bands + ';border:0.75px solid rgba(58,47,40,.7)'"></span>{{ tr('evidence.attested') }}</span>
              <span data-testid="legend-interpolated" class="row flex-1 rounded-wl-sm border border-dashed border-wl-secondary px-2 py-1">
                <span class="sw" [style]="'background:linear-gradient(rgba(236,228,210,.5),rgba(236,228,210,.5)),' + bands + ';border:1.5px dashed #3a2f28'"></span>{{ tr('evidence.interpolated') }}</span>
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
                  <li class="row items-start" data-testid="legend-regime-item" [attr.data-camp]="r.camp ?? 'unassigned'">
                    <span class="flex flex-none gap-1 pt-[2px]">
                      @for (ct of r.controlTypes?.length ? r.controlTypes : ['direct_rule']; track ct) {
                        <span class="sw" data-testid="legend-regime-swatch" [attr.data-control-type]="ct" [style]="regimeSwatch(ct, r)" [attr.title]="tr(ctKey(ct))"></span>
                      }
                    </span>
                    <span>{{ r.name }}<span class="text-wl-on-surface-variant">・{{ r.camp ? tr(campKey(r.camp)) : tr('legend.campUnassigned') }}</span>
                      @if (r.controlTypes?.length) { <span class="block text-wl-on-surface-variant">{{ typesText(r) }}</span> }</span>
                  </li>
                }
              </ul>
              <p class="mt-1.5 text-wl-on-surface-variant">{{ tr('legend.regimes.note') }}</p>
            }
          </div>
        </div>
      }
    </section>
    }
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
    return CAMP_FILL[c];
  }

  /** 四個陣營代表色的色帶：控制類型樣本用它示意紋理，避免被誤認成某一個陣營（Tai 2026-10-31）。 */
  protected readonly bands = (() => {
    const c = [CAMP_FILL.axis, CAMP_FILL.allies, CAMP_FILL.cobelligerent, CAMP_FILL.neutral];
    return `linear-gradient(90deg, ${c[0]} 0 25%, ${c[1]} 25% 50%, ${c[2]} 50% 75%, ${c[3]} 75% 100%)`;
  })();
  private readonly bandsDark = (() => {
    const c = [CAMP_FILL.axis, CAMP_FILL.allies, CAMP_FILL.cobelligerent, CAMP_FILL.neutral].map((x) => darken(x, 0.25));
    return `linear-gradient(90deg, ${c[0]} 0 25%, ${c[1]} 25% 50%, ${c[2]} 50% 75%, ${c[3]} 75% 100%)`;
  })();

  /**
   * 控制類型樣本（DESIGN.md Control types）：填色用四色帶（填色＝陣營），紋理／邊框表示控制類型。
   * 交戰中用兩方色交錯斜線（軸心 × 同盟示意）。
   */
  protected swatch(ct: string): string {
    const paper = '#ece4d2';
    switch (ct) {
      case 'direct_rule':
        return `background:${this.bands};opacity:.85;border:0.75px solid rgba(58,47,40,.4)`;
      case 'military_occupation':
        return `background:linear-gradient(rgba(236,228,210,.4),rgba(236,228,210,.4)),${this.bands};border:2px solid;border-image:${this.bandsDark} 1`;
      case 'puppet_administration':
        return `background:${this.bands};opacity:.85;border:1.5px dotted #3a2f28`;
      case 'partial':
        return `background:repeating-linear-gradient(-45deg, transparent 0 1.5px, ${paper} 1.5px 6px),${this.bands};border:0.75px solid rgba(58,47,40,.4)`;
      default:
        return `background:repeating-linear-gradient(-45deg, ${CAMP_FILL.axis} 0 1.5px, transparent 1.5px 6px),repeating-linear-gradient(45deg, ${CAMP_FILL.allies} 0 1.5px, ${paper} 1.5px 6px);border:0.75px solid rgba(58,47,40,.4)`;
    }
  }

  /** 「目前畫面中的政權」：用該政權的陣營填色＋它在地圖上實際的邊框／紋理（與 map-style 同規則）。 */
  protected regimeSwatch(ct: string, r: LegendRegime): string {
    const c = r.tone;
    const edge = darken(c, 0.25);
    const paper = '#ece4d2';
    const outline = r.attested === false ? 'border:1.5px dashed #3a2f28' : '';
    const op = r.attested === false ? 0.55 : 1;
    switch (ct) {
      case 'military_occupation':
        return `background:color-mix(in srgb, ${c} ${Math.round(60 * op)}%, ${paper});${outline || `border:2px solid ${edge}`}`;
      case 'puppet_administration':
        return `background:color-mix(in srgb, ${c} ${Math.round(85 * op)}%, ${paper});${outline || 'border:1.5px dotted #3a2f28'}`;
      case 'partial':
        return `background:repeating-linear-gradient(-45deg, ${c} 0 1.5px, ${paper} 1.5px 6px);${outline || `border:0.75px solid ${c}`}`;
      case 'contested':
        return `background:repeating-linear-gradient(-45deg, ${c} 0 1.5px, transparent 1.5px 6px),repeating-linear-gradient(45deg, ${edge} 0 1.5px, ${paper} 1.5px 6px);${outline || `border:0.75px solid ${c}`}`;
      default:
        return `background:color-mix(in srgb, ${c} ${Math.round(85 * op)}%, ${paper});${outline || 'border:0.75px solid rgba(58,47,40,.7)'}`;
    }
  }

  protected typesText(r: LegendRegime): string {
    return (r.controlTypes ?? []).map((ct) => this.tr(this.ctKey(ct))).join('、');
  }
}
