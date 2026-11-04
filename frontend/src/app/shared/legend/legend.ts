import { NgTemplateOutlet } from '@angular/common';
import { afterNextRender, ChangeDetectionStrategy, Component, computed, effect, ElementRef, inject, Injector, input, output, signal, untracked, viewChild } from '@angular/core';
import { LucideInfo } from '@lucide/angular';
import { SkeletonDirective } from '../../components/ui/skeleton';
import type { Axis } from '../../core/atlas-state';
import type { LoadStatus } from '../../core/atlas-data';
import { MOTION_DURATION, MotionService } from '../../core/motion';
import { t, type I18nKey, type Lang } from '../../core/i18n';
import { CAMP_FILL, CAMP_TONES, CAMP_UNASSIGNED_TONE, CONTROL_TYPES, darken, type Camp } from '../map/map-style';
import { occupationTint, regimeColor } from '../map/sovereignty-style';

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
 * 樣式說明固定顯示；實際控制檢視的「目前畫面中的政權」來自 API 載入的控制區。
 * 主權檢視只留「國界（主權圖層）」的說明，不列政權清單（全球都顯示時會太擠；Tai 2026-10-31），政權看資訊卡。
 * 收合／展開用 motion 做高度與透明度過場；prefers-reduced-motion 時直接切換。
 */
@Component({
  selector: 'wl-legend',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LucideInfo, SkeletonDirective, NgTemplateOutlet],
  host: { class: 'block', '(document:keydown.escape)': 'onEscape()' },
  styles: `
    .sw { width: 22px; height: 14px; flex: none; border-radius: 2px; }
    .sw-wide { width: 32px; }
    .row { display: flex; align-items: center; gap: 8px; }
  `,
  template: `
    <!-- 圖例（ARCHITECTURE.md §10-3）：左下 40×40 ⓘ 按鈕，點了在按鈕上方展開 240px 寬浮動面板（最高 50vh，可捲動）；
         Esc、再點一次按鈕、點地圖空白處收起；開關狀態記在 localStorage（AtlasState）。 -->
    @if (mode() === 'embedded') {
      <!-- 小於 768px：圖例是底部面板裡的一個分頁（§10-3） -->
      <section data-testid="legend-tab-panel" data-state="embedded" [attr.data-axis]="axis()" class="flex min-h-0 flex-1 flex-col" [attr.aria-label]="tr('legend.title')">
        <ng-container [ngTemplateOutlet]="bodyTpl" [ngTemplateOutletContext]="{ embedded: true }" />
      </section>
    } @else {
    <section data-testid="legend" [attr.data-state]="mode() === 'button' || (!open() && !closing()) ? 'collapsed' : closing() ? 'closing' : 'open'" [attr.data-axis]="axis()"
      class="flex flex-col items-start gap-2" [attr.aria-label]="tr('legend.title')">
    @if (mode() === 'floating' && (open() || closing())) {
    <div #panel data-testid="legend-panel" id="wl-legend-panel" class="wl-paper flex max-h-[50vh] w-[240px] flex-col overflow-hidden">
      <div class="flex flex-none items-center justify-between px-4 py-3">
        <span class="wl-title2">{{ tr('legend.title') }}</span>
      </div>
      <ng-container [ngTemplateOutlet]="bodyTpl" [ngTemplateOutletContext]="{ embedded: false }" />
    </div>
    }
      <button type="button" data-testid="legend-expand" class="wl-paper flex size-10 items-center justify-center text-wl-on-surface hover:bg-wl-surface-container-high"
        [attr.aria-label]="tr('legend.title')" [attr.title]="tr('legend.title')" [attr.aria-expanded]="open()" aria-controls="wl-legend-panel" (click)="toggle.emit()">
        <svg lucideInfo class="size-5"></svg></button>
    </section>
    }
    <ng-template #bodyTpl let-embedded="embedded">
        <div id="wl-legend-body" class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto wl-text2" [class.border-t]="!embedded" [class.border-wl-outline-variant]="!embedded" [class.px-4]="!embedded" [class.py-3]="!embedded" [class.pt-2]="embedded">
          <!-- 主權圖層（國界試驗 1938–1940） -->
          <div data-testid="legend-sovereignty">
            <h3 class="wl-label mb-2">{{ lang() === 'en' ? 'Borders (sovereignty layer)' : '國界（主權圖層）' }}
              @if (axis() === 'control') { <span class="font-normal text-wl-on-surface-variant">{{ lang() === 'en' ? '· faded backdrop' : '・淡色底圖' }}</span> }</h3>
            <ul class="flex flex-col gap-1.5">
              <li class="row" data-testid="legend-sov-fill"><span class="sw" [style.background]="sovSample" style="border:0.75px solid rgba(58,47,40,.75)"></span>{{ lang() === 'en' ? 'Fill = regime (one colour each)' : '填色＝政權（一政權一色）' }}</li>
              <li class="row" data-testid="legend-sov-not-sovereign"><span class="sw" [style.background]="sovHatch" style="border:1px dashed #3a2f28"></span>{{ lang() === 'en' ? 'Hatched, dashed edge = not sovereign' : '斜線＋虛線邊＝非主權' }}</li>
              <!-- 佔領區：底色＝佔領國色，依控制程度三種深淺（以德國色示範） -->
              @for (k of occKinds; track k.kind) {
                <li class="row" [attr.data-testid]="'legend-sov-occupation-' + k.kind"><span class="sw" [style.background]="k.bg" style="border:1px dashed #3a2f28"></span>{{ lang() === 'en' ? k.en : k.zh }}</li>
              }
              <li class="row" data-testid="legend-sov-blank"><span class="sw border border-wl-outline-variant" style="background:#ece4d2"></span>{{ lang() === 'en' ? 'Blank = no qualified source yet (pending)' : '空白＝尚無合格出處（待查證）' }}</li>
            </ul>
            <p class="mt-1 text-wl-on-surface-variant">{{ lang() === 'en' ? 'Borders as drawn by OpenHistoricalMap (de facto). Camp is a supplement only.' : '國界依 OpenHistoricalMap 所畫的事實國界；陣營只作補充。' }}</p>
          </div>
          @if (axis() !== 'sovereignty') {
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
          }
        </div>
    </ng-template>
  `,
})
export class Legend {
  readonly open = input(false);
  /** floating＝左下按鈕＋浮動面板；button＝只有按鈕（小於 768px，圖例在底部面板分頁）；embedded＝放在底部面板分頁裡。 */
  readonly mode = input<'floating' | 'button' | 'embedded'>('floating');
  readonly lang = input<Lang>('zh-Hant');
  readonly regimes = input<LegendRegime[]>([]);
  readonly regimesStatus = input<LoadStatus>('idle');
  readonly axis = input<Axis>('control');
  readonly toggle = output<void>();

  /** 收合過場進行中（面板仍在 DOM 內播放收合動畫）。 */
  protected readonly closing = signal(false);
  private readonly panel = viewChild<ElementRef<HTMLElement>>('panel');
  private readonly motion = inject(MotionService);
  private readonly injector = inject(Injector);
  private prevOpen: boolean | undefined;
  private run = 0;

  protected readonly sovSample = 'linear-gradient(90deg, #a99dc4 0 33%, #c9a87c 33% 66%, #8fb39a 66% 100%)';
  protected readonly sovHatch = 'repeating-linear-gradient(-45deg, #a99dc4 0 1.5px, #ece4d2 1.5px 5px)';
  /** 佔領區三種深淺（德國色示範）：併入最深、民政中等、軍事管理最淺；都疊佔領國色加深的斜線 */
  protected readonly occKinds = (
    [
      ['annexed', '佔領國色・深＝併入（正式或事實）', 'Occupier colour, dark = annexed (formal or de facto)'],
      ['civil_administration', '中＝民政（帝國專員轄區、保護國、總督府）', 'Medium = civil administration (Reichskommissariat, protectorate, General Government)'],
      ['military_administration', '淺＝軍事管理', 'Light = military administration'],
    ] as const
  ).map(([kind, zh, en]) => ({
    kind, zh, en,
    bg: `repeating-linear-gradient(-45deg, ${darken(regimeColor('deutsches-reich'), 0.3)} 0 1.5px, transparent 1.5px 5px), ${occupationTint('deutsches-reich', kind)}`,
  }));

  constructor() {
    effect(() => {
      const open = this.open();
      const prev = this.prevOpen;
      this.prevOpen = open;
      if (prev === undefined || prev === open) return;
      untracked(() => (open ? this.animateOpen() : this.animateClose()));
    });
  }

  /** 展開：等新面板畫出來後，高度從收合按鈕（32px）長到內容高度、淡入。 */
  private animateOpen(): void {
    const run = ++this.run;
    this.closing.set(false);
    afterNextRender(
      () => {
        const el = this.panel()?.nativeElement;
        if (!el || run !== this.run || this.motion.reduced()) return;
        const h = el.scrollHeight;
        void this.motion
          .animate(el, { height: ['40px', `${h}px`], opacity: [0.4, 1] }, { duration: MOTION_DURATION.base })
          .then(() => run === this.run && (el.style.height = ''));
      },
      { injector: this.injector },
    );
  }

  /** 收合：面板留在 DOM 播放高度縮回 32px＋淡出，結束後才換成收合按鈕。 */
  private animateClose(): void {
    const run = ++this.run;
    const el = this.panel()?.nativeElement;
    if (!el || this.motion.reduced()) {
      this.closing.set(false);
      return;
    }
    this.closing.set(true);
    void this.motion
      .animate(el, { height: [`${el.offsetHeight}px`, '40px'], opacity: [1, 0] }, { duration: MOTION_DURATION.fast })
      .then(() => {
        if (run !== this.run) return;
        el.style.height = '';
        el.style.opacity = '';
        this.closing.set(false);
      });
  }

  protected onEscape(): void {
    if (this.open() && this.mode() === 'floating') this.toggle.emit();
  }

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
