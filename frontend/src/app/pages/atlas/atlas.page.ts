import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal, untracked } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { LucideCircleAlert, LucideCloudOff, LucideRotateCw } from '@lucide/angular';
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
import { Legend, type LegendRegime } from '../../shared/legend/legend';
import { AtlasMap, type MapFeatureEvent, type MapGapEvent } from '../../shared/map/atlas-map';
import { campTonesFrom, decorateFeatures, gapFeatures } from '../../shared/map/map-style';
import { Timeline } from '../../shared/timeline/timeline';
import { COMPLETE_FROM, nearestDate } from '../../shared/timeline/timeline-scale';

/**
 * 主地圖頁（`/`，PRD §8.0）。版面：頂部列 56px＋全幅地圖＋左下圖例 280px＋底部時間軸 112px。
 * 地圖只顯示後端 API 的資料；每個控制區都帶 API 回傳的引用（I6），點區塊 → 卡片 → 「來源」popover。
 */
@Component({
  selector: 'wl-atlas-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TopBar, AtlasMap, Legend, Timeline, FeatureCard, GapCard, SkeletonDirective, SpinnerComponent, LucideCircleAlert, LucideRotateCw, LucideCloudOff],
  host: { class: 'block h-full' },
  template: `
    <main data-testid="atlas-page" class="h-full" [attr.lang]="lang()" aria-label="主地圖">
      @switch (data.health()) {
        @case ('checking') {
          <div data-testid="app-skeleton" class="flex h-full flex-col" aria-busy="true">
            <div class="flex h-[var(--wl-topbar-height)] items-center gap-4 border-b border-wl-outline-variant bg-wl-surface px-4">
              <div sanringSkeleton class="h-5 w-24"></div><div sanringSkeleton class="h-8 w-48"></div><div sanringSkeleton class="ml-auto h-7 w-40"></div>
            </div>
            <div class="flex-1 bg-[#ece4d2]"></div>
            <div class="h-[var(--wl-timeline-height)] border-t border-wl-outline-variant bg-wl-surface p-4"><div sanringSkeleton class="h-full w-full"></div></div>
          </div>
        }
        @case ('down') {
          <div data-testid="app-offline" class="flex h-full items-center justify-center bg-wl-background">
            <div class="wl-paper flex w-[420px] flex-col items-center gap-3 p-8 text-center" role="alert">
              <span class="flex size-10 items-center justify-center rounded-wl-lg bg-wl-error-container text-wl-error"><svg lucideCloudOff class="size-5"></svg></span>
              <h1 class="wl-title1">{{ tr('offline.title') }}</h1>
              <p class="wl-alert-error justify-center">{{ tr('offline.health', { status: data.healthStatus() ?? tr('offline.noResponse') }) }}</p>
              <button type="button" data-testid="app-retry" class="wl-btn-primary inline-flex h-9 items-center gap-2 px-4" (click)="boot()">
                <svg lucideRotateCw class="size-4"></svg>{{ tr('map.retry') }}</button>
            </div>
          </div>
        }
        @default {
          <div class="flex h-full flex-col">
            <wl-top-bar [date]="state.date()" [lang]="lang()" [legendOpen]="state.legendOpen()" [controlStatus]="data.controlStatus()"
              [theaters]="data.control()?.theaters ?? null" [featureCount]="featureCount()"
              (langChange)="state.lang.set($event)" (legendToggle)="state.legendOpen.set(!state.legendOpen())" (jump)="setDate($event)" />
            <div class="relative flex-1 overflow-hidden bg-[#cfdbe0]">
              <wl-atlas-map [collection]="collection()" [gaps]="gaps()" [selectedVersionId]="selected()?.versionId ?? null" [engineErrorText]="tr('map.engineError')"
                (featureClick)="onFeatureClick($event)" (gapClick)="onGapClick($event)" (emptyClick)="clearSelection()" (featureHover)="hover.set($event)" />

              @if (firstLoad()) {
                <div data-testid="map-loading" class="pointer-events-none absolute inset-0 flex items-center justify-center">
                  <span class="wl-paper flex items-center gap-2 px-4 py-2 wl-text1"><sanring-spinner size="sm" ariaLabel="loading" />{{ tr('map.loading', { date: state.date() }) }}</span>
                </div>
              } @else if (data.controlStatus() === 'loading') {
                <div class="absolute inset-x-0 top-0 h-0.5 overflow-hidden bg-wl-surface-container-high" aria-hidden="true"><div class="h-full w-1/3 animate-pulse bg-wl-secondary"></div></div>
              }

              @if (data.controlStatus() === 'error') {
                <div data-testid="map-error" class="absolute left-1/2 top-4 -translate-x-1/2">
                  <div class="wl-alert-error wl-paper" role="alert">
                    <svg lucideCircleAlert class="size-4 flex-none"></svg>
                    <span>{{ tr('map.error') }}@if (data.controlDate(); as shown) {；{{ tr('map.errorShowing', { date: shown }) }}}</span>
                    <button type="button" data-testid="map-retry" class="wl-btn-secondary ml-2 h-7 px-3" (click)="reloadControl()">{{ tr('map.retry') }}</button>
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
                <div data-testid="map-incomplete-period-hint" class="absolute right-4 top-4 wl-paper px-3 py-1.5 wl-text2">{{ tr('map.incomplete') }}</div>
              }

              @if (hoverInfo(); as h) {
                <div data-testid="map-tooltip" role="tooltip" class="wl-paper pointer-events-none absolute z-10 px-2 py-1 wl-text2"
                  [style.left.px]="h.x + 12" [style.top.px]="h.y + 12">
                  <div class="wl-label">{{ h.name }}・{{ h.type }}</div>
                  <div class="text-wl-on-surface-variant">{{ h.evidence }}</div>
                </div>
              }

              @if (selectedInfo(); as s) {
                <div class="absolute z-20" [style.left.px]="s.x" [style.top.px]="s.y">
                  <wl-feature-card [props]="s.props" [regimeName]="s.name" [originalName]="s.original" [originalLang]="s.originalLang"
                    [evidence]="s.evidence" [theaterState]="s.theater" [lang]="lang()" (closed)="selected.set(null)" />
                </div>
              }

              @if (selectedGapInfo(); as g) {
                <div class="absolute z-20" [style.left.px]="g.x" [style.top.px]="g.y">
                  <wl-gap-card [note]="g.note" [lang]="lang()" (closed)="selectedGap.set(null)" />
                </div>
              }

              <div class="absolute bottom-4 left-4 z-10">
                <wl-legend [open]="state.legendOpen()" [lang]="lang()" [regimes]="legendRegimes()" [regimesStatus]="data.regimesStatus()"
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
  protected readonly lang = this.state.lang;
  protected readonly selected = signal<MapFeatureEvent | null>(null);
  protected readonly hover = signal<MapFeatureEvent | null>(null);
  protected readonly selectedGap = signal<MapGapEvent | null>(null);
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
    () => this.data.controlStatus() === 'ok' && this.featureCount() === 0 && !this.data.showingStale(),
  );
  protected readonly nearest = computed(() => nearestDate(this.data.snapshots().map((s) => s.asOf), this.state.date()));

  protected readonly legendRegimes = computed<LegendRegime[]>(() => {
    const ids = [...new Set((this.data.control()?.featureCollection.features ?? []).map((f) => f.properties.controllerRegimeId))];
    const regs = this.data.regimes();
    return ids
      .filter((id) => regs[id])
      .map((id) => ({
        id,
        name: regimeSelfName(regs[id], this.lang())?.display ?? id,
        tone: this.campTones().toneFor(id),
        camp: this.campTones().campFor(id),
      }));
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
    return { x: h.x, y: h.y, name: d.name?.display ?? '—', type: this.tr(key), evidence: ev };
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
    if (q.invalidDate) queueMicrotask(() => this.toast?.warning(t('toast.invalidDate', q.lang, { date: q.date })));

    effect(() => {
      if (this.data.controlStatus() === 'ok') untracked(() => this.everLoaded.set(true));
    });

    // 日期改變 → 載入控制區（拖動時去抖動 120ms）＋寫回 URL
    effect(() => {
      const date = this.state.date();
      const lang = this.state.lang();
      untracked(() => {
        if (this.data.health() === 'up') {
          clearTimeout(this.debounce);
          this.debounce = setTimeout(() => void this.data.loadControl(date), this.everLoaded() ? 120 : 0);
        }
        void this.router.navigate([], {
          relativeTo: this.route,
          queryParams: { date, lang: lang === 'en' ? 'en' : null },
          queryParamsHandling: 'merge',
          replaceUrl: true,
        });
      });
    });

    inject(DestroyRef).onDestroy(() => clearTimeout(this.debounce));
    void this.boot();
  }

  protected async boot(): Promise<void> {
    if (!(await this.data.checkHealth())) return;
    void this.data.loadSnapshots();
    void this.data.loadControl(this.state.date());
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
    this.selectedGap.set(null);
    this.selected.set(e);
  }

  protected onGapClick(e: MapGapEvent): void {
    this.hover.set(null);
    this.selected.set(null);
    this.selectedGap.set(e);
  }

  protected clearSelection(): void {
    this.selected.set(null);
    this.selectedGap.set(null);
  }

  protected onInvalidInput(): void {
    this.toast?.warning(this.lang() === 'en' ? 'Use YYYY-MM-DD' : '日期格式請用 YYYY-MM-DD');
  }

  protected tr(key: I18nKey, vars?: Record<string, string | number>): string {
    return t(key, this.lang() as Lang, vars);
  }
}
