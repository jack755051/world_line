import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal, untracked } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { LucideCircleAlert, LucideCloudOff, LucideInfo, LucideRotateCw } from '@lucide/angular';
import { SkeletonDirective } from '../../components/ui/skeleton';
import { SpinnerComponent } from '../../components/ui/spinner';
import { ToastService } from '../../components/ui/toast';
import { AtlasData } from '../../core/atlas-data';
import { AtlasState, parseAtlasQuery } from '../../core/atlas-state';
import { t, type I18nKey, type Lang } from '../../core/i18n';
import { regimeSelfName } from '../../core/regime-names';
import { TopBar } from '../../layout/top-bar/top-bar';
import { FeatureCard } from '../../shared/feature-card/feature-card';
import { GapCard } from '../../shared/gap-card/gap-card';
import { Legend, type LegendRegime, type LegendSovereigntyRegime } from '../../shared/legend/legend';
import { MotionService } from '../../core/motion';
import { AtlasMap, type MapFeatureEvent, type MapGapEvent, type MapSovereigntyEvent } from '../../shared/map/atlas-map';
import { decorateSovereignty, regimeColor, sovereigntyLabels } from '../../shared/map/sovereignty-style';
import { SovereigntyCard } from '../../shared/sovereignty-card/sovereignty-card';
import { campTonesFrom, controlLabels, decorateFeatures, gapFeatures } from '../../shared/map/map-style';
import { Timeline } from '../../shared/timeline/timeline';
import { COMPLETE_FROM, nearestDate } from '../../shared/timeline/timeline-scale';

/**
 * 主地圖頁（`/`，PRD §8.0）。版面：頂部列 56px＋全幅地圖＋左下圖例 280px＋底部時間軸 112px。
 * 地圖只顯示後端 API 的資料；每個控制區都帶 API 回傳的引用（I6），點區塊 → 卡片 → 「來源」popover。
 */
@Component({
  selector: 'wl-atlas-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TopBar, AtlasMap, Legend, Timeline, FeatureCard, GapCard, SovereigntyCard, SkeletonDirective, SpinnerComponent, LucideCircleAlert, LucideRotateCw, LucideCloudOff, LucideInfo],
  host: { class: 'block h-full' },
  template: `
    <main data-testid="atlas-page" class="h-full" [attr.lang]="lang()" aria-label="主地圖">
      @switch (data.health()) {
        @case ('checking') {
          <!-- Stitch W7-1：頂部列骨架＋紙色地圖區＋時間軸框架骨架（不畫任何資料） -->
          <div data-testid="app-skeleton" class="flex h-full flex-col" aria-busy="true">
            <div class="flex h-[var(--wl-topbar-height)] items-center gap-4 border-b border-wl-outline-variant bg-wl-surface px-4">
              <div sanringSkeleton class="h-4 w-24"></div><span class="h-6 w-px bg-wl-outline-variant" aria-hidden="true"></span>
              <div sanringSkeleton class="h-6 w-48"></div><div sanringSkeleton class="h-4 w-14"></div>
              <div class="ml-auto flex items-center gap-3"><div sanringSkeleton class="h-7 w-36"></div><div sanringSkeleton class="h-7 w-16"></div><div sanringSkeleton class="size-7"></div></div>
            </div>
            <div class="flex-1 bg-[#ece4d2]"></div>
            <div class="flex h-[var(--wl-timeline-height)] items-center gap-4 border-t border-wl-outline-variant bg-wl-surface px-4">
              <div class="flex w-[300px] flex-none items-center gap-1.5">
                <div sanringSkeleton class="size-7"></div><div sanringSkeleton class="size-7"></div><div sanringSkeleton class="size-7"></div>
                <span class="mx-1 h-5 w-px bg-wl-outline-variant" aria-hidden="true"></span><div sanringSkeleton class="h-7 w-14"></div><div sanringSkeleton class="h-7 w-28"></div>
              </div>
              <div class="flex flex-1 gap-2">
                <div class="flex w-[48px] flex-none flex-col gap-[6px]">@for (i of skeletonRows; track i) { <div sanringSkeleton class="h-[6px] w-full"></div> }</div>
                <div class="flex flex-1 flex-col gap-[6px]">@for (i of skeletonRows; track i) { <div sanringSkeleton class="h-[6px] w-full"></div> }</div>
              </div>
            </div>
          </div>
        }
        @case ('down') {
          <div data-testid="app-offline" class="flex h-full items-center justify-center bg-wl-background">
            <div class="wl-paper flex w-[420px] flex-col items-center gap-2 px-8 py-10 text-center" role="alert">
              <svg lucideCloudOff class="size-6 text-wl-error" aria-hidden="true"></svg>
              <h1 class="mt-2 wl-title1">{{ tr('offline.title') }}</h1>
              <p data-testid="app-offline-status" class="wl-text2 text-wl-on-surface-variant">{{ tr('offline.health', { status: data.healthStatus() ?? tr('offline.noResponse') }) }}</p>
              <button type="button" data-testid="app-retry" class="wl-btn-primary mt-4 inline-flex h-9 min-w-[132px] items-center justify-center gap-2 px-6 wl-text1 font-semibold" (click)="boot()">
                <svg lucideRotateCw class="size-4"></svg>{{ tr('map.retry') }}</button>
            </div>
          </div>
        }
        @default {
          <div class="flex h-full flex-col">
            <wl-top-bar [date]="state.date()" [lang]="lang()" [legendOpen]="state.legendOpen()" [controlStatus]="data.controlStatus()"
              [theaters]="data.control()?.theaters ?? null" [featureCount]="featureCount()" [axis]="state.axis()" (axisChange)="setAxis($event)"
              (langChange)="state.lang.set($event)" (legendToggle)="state.legendOpen.set(!state.legendOpen())" (jump)="setDate($event)" />
            <div class="relative flex-1 overflow-hidden bg-[#cfdbe0]">
              <wl-atlas-map [collection]="collection()" [labels]="allLabels()" [gaps]="gaps()" [selectedVersionId]="selected()?.versionId ?? null" [engineErrorText]="tr('map.engineError')"
 [axis]="state.axis()" [reducedMotion]="motion.reduced()"
                [sovereignty]="sovereigntyFc()" [showCamps]="showCamps()" [selectedRecordId]="selectedSov()?.recordId ?? null"
                (featureClick)="onFeatureClick($event)" (gapClick)="onGapClick($event)" (sovereigntyClick)="onSovereigntyClick($event)"
                (emptyClick)="clearSelection()" (featureHover)="hover.set($event)" />

              <!-- 陣營外框圖層（補充，可開關；Tai 2026-10-31：政權優先於陣營，填色不變） -->
              <button type="button" data-testid="camp-layer-toggle" class="wl-paper absolute right-4 top-4 z-10 flex items-center gap-2 px-3 py-1.5 wl-text2"
                [attr.aria-pressed]="showCamps()" (click)="showCamps.set(!showCamps())">
                <span class="inline-block size-3 border border-wl-outline" [class.bg-wl-secondary]="showCamps()"></span>{{ lang() === 'en' ? 'Camp outlines (supplement)' : '陣營外框（補充）' }}
              </button>

              @if (firstLoad()) {
                <div data-testid="map-loading" class="pointer-events-none absolute inset-0 flex items-center justify-center">
                  <span class="wl-paper flex items-center gap-2 px-4 py-2 wl-text1"><sanring-spinner size="sm" ariaLabel="loading" />{{ tr('map.loading', { date: state.date() }) }}</span>
                </div>
              } @else if (data.controlStatus() === 'loading') {
                <div class="absolute inset-x-0 top-0 h-0.5 overflow-hidden bg-wl-surface-container-high" aria-hidden="true"><div class="h-full w-1/3 animate-pulse bg-wl-secondary"></div></div>
              }

              @if (data.controlStatus() === 'error') {
                <div data-testid="map-error" class="absolute left-1/2 top-4 -translate-x-1/2">
                  <div class="wl-alert-error shadow-[var(--wl-shadow-panel)]" role="alert">
                    <svg lucideCircleAlert class="size-4 flex-none"></svg>
                    <span class="font-semibold">{{ tr('map.error') }}</span>
                    @if (data.controlDate(); as shown) { <span data-testid="map-error-showing" class="wl-text2 text-wl-on-surface-variant">{{ tr('map.errorShowing', { date: shown }) }}</span> }
                    <button type="button" data-testid="map-retry" class="wl-btn-secondary ml-4 h-7 px-3 wl-text2 text-wl-error" (click)="reloadControl()">{{ tr('map.retry') }}</button>
                  </div>
                </div>
              }

              @if (isEmpty()) {
                <div data-testid="map-empty" class="absolute inset-0 flex items-center justify-center">
                  <div class="wl-paper flex flex-col items-center gap-3 p-6">
                    <p class="wl-title2">{{ tr('map.empty') }}</p>
                    @if (nearest(); as n) {
                      <button type="button" data-testid="map-empty-jump" class="wl-btn-primary h-9 px-4" (click)="setDate(n)">{{ tr('map.emptyJump') }}（{{ n }}）</button>
                    }
                  </div>
                </div>
              }

              @if (state.date() < completeFrom) {
                <div data-testid="map-incomplete-period-hint" class="absolute left-4 top-4 wl-paper flex items-center gap-1.5 px-3 py-1.5 wl-text2"><svg lucideInfo class="size-3.5 text-wl-on-surface-variant" aria-hidden="true"></svg>{{ tr('map.incomplete') }}</div>
              }

              @if (hoverInfo(); as h) {
                <div data-testid="map-tooltip" role="tooltip" class="wl-paper pointer-events-none absolute z-10 px-3 py-2 wl-text2"
                  [style.left.px]="h.x + 12" [style.top.px]="h.y + 12">
                  <div class="wl-sub-title">{{ h.name }}・{{ h.type }}</div>
                  <div [class.text-wl-tertiary]="h.attested" [class.text-wl-on-surface-variant]="!h.attested">{{ h.evidence }}</div>
                </div>
              }

              @if (selectedInfo(); as s) {
                <div class="absolute z-20" [style.left.px]="s.x" [style.top.px]="s.y">
                  <wl-feature-card [props]="s.props" [regimeName]="s.name" [originalName]="s.original" [originalLang]="s.originalLang"
                    [evidence]="s.evidence" [theaterState]="s.theater" [lang]="lang()" (closed)="selected.set(null)" />
                </div>
              }

              @if (selectedSovInfo(); as s) {
                <div class="absolute z-20" [style.left.px]="s.x" [style.top.px]="s.y">
                  <wl-sovereignty-card [props]="s.props" [regimeName]="s.name" [originalName]="s.original" [originalLang]="s.originalLang" [lang]="lang()"
                    (closed)="selectedSov.set(null)" />
                </div>
              }

              @if (selectedGapInfo(); as g) {
                <div class="absolute z-20" [style.left.px]="g.x" [style.top.px]="g.y">
                  <wl-gap-card [note]="g.note" [lang]="lang()" (closed)="selectedGap.set(null)" />
                </div>
              }

              <div class="absolute bottom-4 left-4 z-10">
                <wl-legend [open]="state.legendOpen()" [lang]="lang()" [regimes]="legendRegimes()" [regimesStatus]="data.regimesStatus()"
                  [axis]="state.axis()" [sovRegimes]="legendSovRegimes()" [sovRegimesStatus]="data.sovereigntyStatus()"
                  (toggle)="state.legendOpen.set(!state.legendOpen())" />
              </div>
            </div>
            <div class="h-[var(--wl-timeline-height)] flex-none">
              <wl-timeline [date]="state.date()" [snapshots]="data.snapshots()" [snapshotsStatus]="data.snapshotsStatus()" [lang]="lang()"
                (dateChange)="setDate($event)" (retry)="data.loadSnapshots()" (invalidInput)="onInvalidInput()" />
            </div>
          </div>
        }
      }
    </main>
  `,
})
export class AtlasPage {
  protected readonly state = inject(AtlasState);
  protected readonly data = inject(AtlasData);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly toast = inject(ToastService, { optional: true });

  protected readonly completeFrom = COMPLETE_FROM;
  protected readonly skeletonRows = [0, 1, 2, 3, 4];
  protected readonly lang = this.state.lang;
  protected readonly selected = signal<MapFeatureEvent | null>(null);
  protected readonly hover = signal<MapFeatureEvent | null>(null);
  protected readonly selectedGap = signal<MapGapEvent | null>(null);
  protected readonly selectedSov = signal<MapSovereigntyEvent | null>(null);
  protected readonly showCamps = signal(false);
  protected readonly motion = inject(MotionService);
  /** 圖例：主權圖層中的政權（一政權一列；同政權多筆合併）。 */
  protected readonly legendSovRegimes = computed<LegendSovereigntyRegime[]>(() => {
    const regs = this.data.regimes();
    const out = new Map<string, LegendSovereigntyRegime>();
    for (const f of this.data.sovereignty()?.featureCollection.features ?? []) {
      const p = f.properties;
      const prev = out.get(p.regimeId);
      const pending = p.startEvent?.verification === 'pending' || p.endEvent?.verification === 'pending';
      out.set(p.regimeId, {
        id: p.regimeId,
        name: regimeSelfName(regs[p.regimeId], this.lang())?.display ?? p.regimeSlug,
        color: regimeColor(p.regimeSlug),
        notSovereign: (prev?.notSovereign ?? false) || p.layerStatus === 'not_sovereign',
        pending: (prev?.pending ?? false) || pending,
      });
    }
    return [...out.values()].sort((a, b) => a.name.localeCompare(b.name, this.lang() === 'en' ? 'en' : 'zh-Hant'));
  });
  /** 主權圖層（國界）：填色依政權；陣營只作補充。 */
  protected readonly sovereigntyFc = computed(() => decorateSovereignty(this.data.sovereignty()));
  protected readonly sovereigntyCount = computed(() => this.data.sovereignty()?.featureCollection.features.length ?? 0);
  protected readonly selectedSovInfo = computed(() => {
    const e = this.selectedSov();
    const f = e && this.data.sovereignty()?.featureCollection.features.find((x) => x.properties.recordId === e.recordId);
    if (!e || !f) return null;
    const reg = this.data.regimes()[f.properties.regimeId];
    const name = regimeSelfName(reg, this.lang());
    return {
      x: Math.max(8, Math.min(e.x + 12, window.innerWidth - 360)),
      y: Math.max(8, Math.min(e.y - 40, window.innerHeight - 560)),
      props: f.properties,
      name: name?.display ?? f.properties.regimeSlug,
      original: name?.original ?? '',
      originalLang: reg?.names.find((n) => n.nameKind === 'self')?.originalLang ?? '',
    };
  });
  private readonly everLoaded = signal(false);

  /** 載入失敗而顯示舊日期資料時，不沿用舊的史料判斷：一律以推估（不明）樣式呈現（PRD §8.5 error 保守原則）。 */
  /** 陣營色（憲法 §6「陣營」）：只依 API 回傳的 controllerAlignment；沒有就是「陣營未建置」色，不推定。 */
  private readonly campTones = computed(() => campTonesFrom(this.data.control()));
  protected readonly collection = computed(() => {
    const dto = this.data.control();
    const { toneFor } = this.campTones();
    if (dto && this.data.controlStatus() === 'error' && this.data.showingStale()) return decorateFeatures({ ...dto, theaters: [] }, toneFor);
    return decorateFeatures(dto, toneFor);
  });
  /** 控制資料缺（R9）：只畫 API 的涵蓋備註；顯示舊日期資料時不畫（避免把別天的缺口當成今天的）。 */
  protected readonly gaps = computed(() =>
    this.data.controlStatus() === 'error' && this.data.showingStale() ? gapFeatures(null) : gapFeatures(this.data.control()),
  );
  protected readonly selectedGapInfo = computed(() => {
    const g = this.selectedGap();
    const note = g && this.data.control()?.coverageNotes?.find((n) => n.id === g.gapId);
    return g && note ? { x: Math.max(8, g.x + 12), y: Math.max(8, g.y - 40), note } : null;
  });
  protected readonly featureCount = computed(() => this.data.control()?.featureCollection.features.length ?? 0);
  protected readonly firstLoad = computed(() => !this.everLoaded() && this.data.controlStatus() !== 'error');
  protected readonly isEmpty = computed(
    () => this.data.controlStatus() === 'ok' && this.featureCount() === 0 && !this.data.showingStale()
      && this.data.sovereigntyStatus() !== 'loading' && this.sovereigntyCount() === 0,
  );
  protected readonly nearest = computed(() => nearestDate(this.data.snapshots().map((s) => s.asOf), this.state.date()));

  protected readonly legendRegimes = computed<LegendRegime[]>(() => {
    const feats = this.collection().features;
    const ids = [...new Set(feats.map((f) => f.properties.controllerRegimeId))];
    const regs = this.data.regimes();
    return ids
      .filter((id) => regs[id])
      .map((id) => {
        const mine = feats.filter((f) => f.properties.controllerRegimeId === id);
        return {
          id,
          name: regimeSelfName(regs[id], this.lang())?.display ?? id,
          tone: this.campTones().toneFor(id),
          camp: this.campTones().campFor(id),
          controlTypes: [...new Set(mine.map((f) => f.properties.controlType))],
          attested: mine.every((f) => f.properties.evidence === 'attested'),
        };
      });
  });

  /** 政權名稱標籤：只用 API 的政權自稱（PRD §8.2），查不到名稱的政權不標。 */
  protected readonly labels = computed(() => {
    const regs = this.data.regimes();
    const dto = this.data.control();
    if (!dto || (this.data.controlStatus() === 'error' && this.data.showingStale())) return [];
    return controlLabels(dto, (id) => regimeSelfName(regs[id], this.lang())?.display ?? null);
  });

  /** 國名標籤＋控制區政權標籤（控制區標籤在後，畫在國名上面）。 */
  protected readonly allLabels = computed(() => {
    const regs = this.data.regimes();
    const sov = sovereigntyLabels(this.data.sovereignty(), (id) => regimeSelfName(regs[id], this.lang())?.display ?? null);
    // 主權檢視只標國名；實際控制檢視國名在下、控制區政權標籤在上
    return this.state.axis() === 'sovereignty' ? sov : [...sov, ...this.labels()];
  });

  private findFeature(versionId: string) {
    return this.data.control()?.featureCollection.features.find((f) => f.properties.versionId === versionId) ?? null;
  }

  private describe(versionId: string) {
    const f = this.findFeature(versionId);
    if (!f) return null;
    const p = f.properties;
    const name = regimeSelfName(this.data.regimes()[p.controllerRegimeId], this.lang());
    const theater = this.data.control()?.theaters.find((x) => x.theaterCode === p.theaterCode) ?? null;
    const decorated = this.collection().features.find((x) => x.properties.versionId === versionId);
    return { p, name, theater, evidence: decorated?.properties.evidence ?? 'unknown' };
  }

  protected readonly hoverInfo = computed(() => {
    const h = this.hover();
    if (!h || this.selected()) return null;
    const d = this.describe(h.versionId);
    if (!d) return null;
    const key = `control.${d.p.controlType}` as I18nKey;
    const ev = d.evidence === 'attested'
      ? `${this.tr('evidence.attested')} ${d.theater?.attestingSnapshot?.asOf ?? ''}`
      : `${this.tr('evidence.interpolated')}，${this.lang() === 'en' ? 'not attested; nearest snapshot' : '非史料；最近史料'}：${d.theater?.prevSnapshot?.asOf ?? d.theater?.nextSnapshot?.asOf ?? '—'}`;
    return { x: h.x, y: h.y, name: d.name?.display ?? '—', type: this.tr(key), evidence: ev, attested: d.evidence === 'attested' };
  });

  protected readonly selectedInfo = computed(() => {
    const s = this.selected();
    if (!s) return null;
    const d = this.describe(s.versionId);
    if (!d) return null;
    return {
      x: Math.max(8, s.x + 12),
      y: Math.max(8, s.y - 40),
      props: d.p,
      name: d.name?.display ?? '',
      original: d.name?.original ?? '',
      originalLang: this.data.regimes()[d.p.controllerRegimeId]?.names.find((n) => n.nameKind === 'self')?.originalLang ?? '',
      evidence: d.evidence,
      theater: d.theater,
    };
  });

  private debounce: ReturnType<typeof setTimeout> | undefined;

  constructor() {
    const q = parseAtlasQuery(this.route.snapshot.queryParams as Record<string, string | undefined>);
    this.state.date.set(q.date);
    this.state.lang.set(q.lang);
    this.state.axis.set(q.axis);
    if (q.invalidDate) queueMicrotask(() => this.toast?.info(t('toast.invalidDate', q.lang)));

    effect(() => {
      if (this.data.controlStatus() === 'ok') untracked(() => this.everLoaded.set(true));
    });

    // 日期改變 → 載入控制區（拖動時去抖動 120ms）＋寫回 URL
    effect(() => {
      const date = this.state.date();
      const lang = this.state.lang();
      const axis = untracked(() => this.state.axis());
      untracked(() => {
        if (this.data.health() === 'up') {
          clearTimeout(this.debounce);
          this.debounce = setTimeout(() => {
            void this.data.loadControl(date);
            void this.data.loadSovereignty(date);
          }, this.everLoaded() ? 120 : 0);
        }
        void this.router.navigate([], {
          relativeTo: this.route,
          queryParams: { date, lang: lang === 'en' ? 'en' : null, axis: axis === 'sovereignty' ? 'sovereignty' : null },
          queryParamsHandling: 'merge',
          replaceUrl: true,
        });
      });
    });

    // 檢視軸改變 → 只寫回 URL（不重新載入資料）
    effect(() => {
      const axis = this.state.axis();
      untracked(() =>
        void this.router.navigate([], {
          relativeTo: this.route,
          queryParams: { axis: axis === 'sovereignty' ? 'sovereignty' : null },
          queryParamsHandling: 'merge',
          replaceUrl: true,
        }),
      );
    });

    inject(DestroyRef).onDestroy(() => clearTimeout(this.debounce));
    void this.boot();
  }

  protected async boot(): Promise<void> {
    if (!(await this.data.checkHealth())) return;
    void this.data.loadSnapshots();
    void this.data.loadControl(this.state.date());
    void this.data.loadSovereignty(this.state.date());
  }

  protected reloadControl(): void {
    void this.data.loadControl(this.state.date());
  }

  protected setDate(d: string): void {
    this.clearSelection();
    this.state.setDate(d);
  }

  protected onFeatureClick(e: MapFeatureEvent): void {
    this.hover.set(null);
    this.selectedSov.set(null);
    this.selectedGap.set(null);
    this.selected.set(e);
  }

  protected setAxis(axis: 'control' | 'sovereignty'): void {
    this.state.axis.set(axis);
    if (axis === 'sovereignty') {
      this.selected.set(null);
      this.selectedGap.set(null);
    }
  }

  protected onSovereigntyClick(e: MapSovereigntyEvent): void {
    this.hover.set(null);
    this.selected.set(null);
    this.selectedGap.set(null);
    this.selectedSov.set(e);
  }

  protected onGapClick(e: MapGapEvent): void {
    this.hover.set(null);
    this.selected.set(null);
    this.selectedGap.set(e);
  }

  protected clearSelection(): void {
    this.selected.set(null);
    this.selectedGap.set(null);
    this.selectedSov.set(null);
  }

  protected onInvalidInput(): void {
    this.toast?.warning(this.lang() === 'en' ? 'Use YYYY-MM-DD' : '日期格式請用 YYYY-MM-DD');
  }

  protected tr(key: I18nKey, vars?: Record<string, string | number>): string {
    return t(key, this.lang() as Lang, vars);
  }
}
