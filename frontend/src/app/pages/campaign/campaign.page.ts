import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, computed, effect, inject, isDevMode, signal, untracked, viewChild } from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import type { FeatureCollection } from 'geojson';
import type { FilterSpecification, GeoJSONSource, LayerSpecification, Map as MlMap } from 'maplibre-gl';
import { CAMPAIGNS_ENABLED, CampaignPlayer, fetchCampaign, type Campaign, type CampaignSourceKind, type CampaignStatus } from '../../core/campaign';
import { CampaignReturn, atlasQueryFor, snapshotFromHistory, type ReturnSnapshot } from '../../core/campaign-return';
import { WorldLineApi } from '../../core/api/world-line-api';
import { MotionService } from '../../core/motion';
import { interpolate, planMorph, sourcedBorders, type BorderFC, type MorphPlan } from '../../core/border-morph';
import { CampaignCard } from '../../shared/campaign-card/campaign-card';
import { MAPLIBRE_WORKER_URL, buildBaseStyle } from '../../shared/map/atlas-map';
import {
  ARROWHEAD_IMAGE, CAMPAIGN_LAYER_IDS, CAMPAIGN_SOURCES, FRONT_COLOR, arrowheadImage, campaignFilters, campaignLayers, campaignSourceData,
} from '../../shared/map/campaign-layers';

/** 這個階段有沒有「有出處」（verified）的戰線／箭頭／據點；沒有就顯示 §19.2.7 的空狀態提示。 */
export function phaseHasVerified(c: Campaign, phase: number): boolean {
  const all = [...c.layers.fronts.features, ...c.layers.arrows.features, ...c.layers.sites.features];
  return all.some((f) => f.properties.phase === phase && f.properties.verified === true);
}
export function phaseHasPending(c: Campaign, phase: number): boolean {
  const all = [...c.layers.fronts.features, ...c.layers.arrows.features, ...c.layers.sites.features];
  return all.some((f) => f.properties.phase <= phase && f.properties.verified === false);
}
/** `?phase=` → 合法階段序號（缺或不合法回 1）。 */
export function parsePhase(raw: string | null | undefined, count: number): number {
  const n = Number(raw);
  return Number.isInteger(n) && n >= 1 && n <= count ? n : 1;
}

const SOV_FILL = 'campaign-sov-fill';
const SOV_LINE = 'campaign-sov-line';
/** §19.2.4 (i)(iii)：漸變中間形狀專用 source／圖層（虛線、半透明；不掛任何點擊或查詢事件）。 */
export const SOV_TX_SOURCE = 'campaign-sov-tx';
export const SOV_TX_LAYERS = ['campaign-sov-tx-fill', 'campaign-sov-tx-line'] as const;
/** 漸變時長（秒）：每階段 3 秒中的前 1.2 秒。 */
export const MORPH_SEC = 1.2;
const EMPTY_FC: BorderFC = { type: 'FeatureCollection', features: [] };

/**
 * §19.2 戰役獨立頁 `/campaign/:slug?phase=`（C2a 頁面；C2b：GSAP timeline 播放＋疆界漸變）。
 * - 獨立 MapLibre 實例，fitBounds(theater_area)，三個圖層依 phase 過濾；疆界只顯示該階段起日的主權紀錄。
 * - 左欄說明卡（手機：底部面板 peek／half／full）；階段切換沿用 CampaignPlayer，轉場經 MotionService（GSAP）。
 * - 戰術概念不自動畫上地圖；階段中不顯示人物位置；文案只用中性動詞，不寫因果句。
 */
@Component({
  selector: 'wl-campaign-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CampaignCard, NgTemplateOutlet],
  host: { class: 'flex h-dvh w-full flex-col overflow-hidden bg-wl-surface', '(window:keydown)': 'onKey($event)' },
  template: `
    <header data-testid="campaign-topbar" class="flex flex-none items-center gap-3 border-b border-wl-outline-variant bg-wl-surface px-3"
      [class.h-12]="mobile()" [class.h-14]="!mobile()">
      <button type="button" data-testid="campaign-back" class="flex h-11 min-w-11 flex-none items-center gap-1 rounded px-2 wl-text2 font-semibold hover:bg-wl-surface-container"
        [attr.data-has-return]="!!snapshot()" (click)="back()">← {{ mobile() ? (snapshot() ? '返回' : '地圖') : backLabel() }}</button>
      <div class="min-w-0 flex-1">
        <h1 data-testid="campaign-page-title" class="truncate wl-title2 leading-tight">{{ campaign()?.name_zh ?? (status() === 'error' ? '戰役' : '載入中…') }}</h1>
        @if (!mobile() && campaign(); as c) { <div class="wl-text2 text-wl-on-surface-variant">{{ c.start }} – {{ c.end_inclusive }}</div> }
      </div>
      @if (mobile()) {
        <button type="button" data-testid="campaign-info" class="flex size-11 flex-none items-center justify-center rounded hover:bg-wl-surface-container" aria-label="說明卡" (click)="cycleSheet()">ⓘ</button>
      }
    </header>

    <main data-testid="campaign-page" class="relative flex min-h-0 flex-1" [class.flex-col]="mobile() && !landscape()"
      [attr.data-status]="status()" [attr.data-phase]="phase()" [attr.data-source]="source()" [attr.data-layout]="layoutKind()">
      @if (!mobile() || landscape()) {
        <aside data-testid="campaign-aside" class="flex min-h-0 flex-none flex-col p-3" [style.width]="landscape() ? '40vw' : '360px'" [class.p-3]="!landscape()" [class.p-1]="landscape()">
          <ng-container *ngTemplateOutlet="cardTpl" />
        </aside>
      }
      <div class="relative min-h-0 min-w-0 flex-1" [style.height]="mobile() && !landscape() ? '60vh' : null" [style.flex]="mobile() && !landscape() ? '0 0 60vh' : null">
        <!-- MapLibre 會把容器設成 position:relative：外層負責定位，內層給地圖 -->
        <div class="absolute inset-0"><div #mapEl data-testid="campaign-map" class="h-full w-full" [attr.data-map-ready]="mapReady()" [attr.data-borders]="bordersFor()" [attr.data-transition]="transition()"></div></div>
        @if (status() === 'error') {
          <div data-testid="campaign-page-error" role="alert" class="absolute inset-x-4 top-4 rounded bg-wl-surface p-4 wl-text1 shadow-[var(--wl-shadow-panel)]">
            找不到這場戰役的資料，或資料載入失敗。地圖不顯示戰役圖層。</div>
        }
        @if (campaign(); as c) {
          @if (status() !== 'error' && !hasVerified()) {
            <div data-testid="campaign-empty-phase" role="status" class="absolute left-1/2 top-3 -translate-x-1/2 rounded bg-wl-surface/95 px-3 py-1.5 wl-text2 shadow-[var(--wl-shadow-panel)]">
              此階段尚無有出處的戰線資料</div>
          }
          <div data-testid="campaign-legend" class="absolute bottom-3 right-3 rounded bg-wl-surface/95 px-3 py-2 wl-text2 shadow-[var(--wl-shadow-panel)]">
            @if (hasPending() && hasVerified()) {
              <div data-testid="campaign-legend-pending" class="flex items-center gap-2"><svg width="28" height="8" aria-hidden="true"><line x1="0" y1="4" x2="28" y2="4" [attr.stroke]="frontColor" stroke-width="3" stroke-dasharray="5 4" /></svg>待考證</div>
            }
            <div class="flex items-center gap-2"><svg width="28" height="8" aria-hidden="true"><line x1="0" y1="4" x2="28" y2="4" stroke="#6b7280" stroke-width="1.5" /></svg>政權疆界（階段起日，有出處）</div>
            @if (transition() !== 'none') {
              <div data-testid="campaign-legend-transitional" class="flex items-center gap-2"><svg width="28" height="8" aria-hidden="true"><line x1="0" y1="4" x2="28" y2="4" stroke="#6b7280" stroke-opacity="0.75" stroke-width="1.5" stroke-dasharray="3 3" /></svg>推估過渡，非史料</div>
            }
          </div>
        }
      </div>
      @if (mobile() && !landscape()) {
        <section data-testid="campaign-sheet" class="absolute inset-x-0 bottom-0 z-10 flex flex-col overflow-hidden rounded-t-xl bg-wl-surface shadow-[var(--wl-shadow-panel)]"
          [style.height]="sheetHeight()" [attr.data-snap]="sheet()">
          <button type="button" data-testid="campaign-sheet-handle" class="flex h-5 flex-none items-center justify-center" aria-label="調整說明卡高度" (click)="cycleSheet()">
            <span class="h-1 w-10 rounded-full bg-wl-outline-variant"></span></button>
          <ng-container *ngTemplateOutlet="cardTpl" />
        </section>
      }
    </main>

    <ng-template #cardTpl>
      <wl-campaign-card #card class="min-h-0 flex-1" [campaign]="campaign()" [status]="status()" [phase]="phase()" [touch]="touch()" [sourceKind]="source()"
        [closeLabel]="backLabel()" (closed)="back()" (play)="player?.toggle()" (prev)="player?.prev()" (next)="player?.next()" (go)="goPhase($event)" />
    </ng-template>
  `,
})
export class CampaignPage {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(WorldLineApi);
  private readonly motion = inject(MotionService);
  private readonly returns = inject(CampaignReturn);
  private readonly enabled = inject(CAMPAIGNS_ENABLED);
  protected readonly frontColor = FRONT_COLOR;

  protected readonly campaign = signal<Campaign | null>(null);
  protected readonly source = signal<CampaignSourceKind | null>(null);
  protected readonly status = signal<CampaignStatus>('loading');
  protected readonly phase = signal(1);
  protected readonly mapReady = signal(false);
  protected readonly bordersFor = signal<string | null>(null);
  /** §19.2.4：目前是否在畫漸變中間形狀（'none'＝停在階段，只顯示有出處的疆界）。 */
  protected readonly transition = signal<MorphPlan['mode']>('none');
  private readonly sovCache = new Map<string, Promise<BorderFC>>();
  /** 地圖上目前「落定」的疆界（已只剩有出處）與其階段。 */
  private shown: { phase: number; fc: BorderFC } | null = null;
  private morph: { finish(): void } | null = null;
  /** 返回目標（記憶體一格，其次 history.state；直接開 URL 時為 null → 「開啟地圖」）。 */
  protected readonly snapshot = signal<ReturnSnapshot | null>(this.returns.slot() ?? snapshotFromHistory());
  protected player: CampaignPlayer | null = null;

  private readonly mapEl = viewChild<ElementRef<HTMLElement>>('mapEl');
  private readonly cardEl = viewChild('card', { read: ElementRef });
  private map: MlMap | null = null;
  private readonly size = signal({ w: typeof window !== 'undefined' ? window.innerWidth : 1440, h: typeof window !== 'undefined' ? window.innerHeight : 900 });
  protected readonly mobile = computed(() => this.size().w < 768);
  /** 手機橫放（高 < 500px）：說明卡改放左側 40vw。 */
  protected readonly landscape = computed(() => this.mobile() && this.size().h < 500);
  protected readonly layoutKind = computed(() => (this.landscape() ? 'landscape' : this.mobile() ? 'mobile' : 'desktop'));
  protected readonly touch = signal(typeof matchMedia !== 'undefined' && matchMedia('(hover: none) and (pointer: coarse)').matches);
  protected readonly sheet = signal<'peek' | 'half' | 'full'>('peek');
  protected readonly sheetHeight = computed(() => (this.sheet() === 'peek' ? '140px' : this.sheet() === 'half' ? '50%' : 'calc(100% - 8px)'));
  protected readonly hasVerified = computed(() => { const c = this.campaign(); return !!c && phaseHasVerified(c, this.phase()); });
  protected readonly hasPending = computed(() => { const c = this.campaign(); return !!c && phaseHasPending(c, this.phase()); });
  protected readonly backLabel = computed(() => {
    const s = this.snapshot();
    return s ? `返回 ${s.date} 地圖` : '開啟地圖';
  });

  constructor() {
    const destroy = inject(DestroyRef);
    if (typeof window !== 'undefined') {
      const onResize = () => this.size.set({ w: window.innerWidth, h: window.innerHeight });
      window.addEventListener('resize', onResize);
      destroy.onDestroy(() => window.removeEventListener('resize', onResize));
    }
    destroy.onDestroy(() => { this.player?.dispose(); this.morph?.finish(); this.map?.remove(); this.map = null; });

    const slug = this.route.snapshot.paramMap.get('slug') ?? '';
    void this.load(slug, this.route.snapshot.queryParamMap.get('phase'));

    // 階段 → URL（replaceUrl，重新整理時可還原）＋地圖過濾＋疆界＋說明卡轉場
    effect(() => {
      const c = this.campaign();
      const ph = this.phase();
      if (!c) return;
      untracked(() => {
        void this.router.navigate([], { relativeTo: this.route, queryParams: { phase: ph }, queryParamsHandling: 'merge', replaceUrl: true });
        this.applyPhase(c, ph);
        const el = this.cardEl()?.nativeElement as HTMLElement | undefined;
        const body = el?.querySelector('[data-testid="campaign-summary"]');
        if (body) void this.motion.animate(body, { opacity: [0.2, 1], y: [6, 0] }, { clear: true });
      });
    });
    effect(() => {
      const el = this.mapEl()?.nativeElement;
      const c = this.campaign();
      if (el && c && !this.map) untracked(() => void this.initMap(el, c));
    });
  }

  private async load(slug: string, rawPhase: string | null): Promise<void> {
    if (!this.enabled || !/^[a-z0-9_-]+$/i.test(slug)) { this.status.set('error'); return; }
    try {
      const { campaign, source } = await fetchCampaign(slug);
      this.source.set(source);
      // §19.2.4：播放計時由 GSAP timeline 驅動（經 MotionService）；狀態仍以 player → signal 為準
      this.player = new CampaignPlayer(campaign.phases.length, () => this.sync(), undefined, (ms, tick) => this.motion.phaseClock(ms, tick));
      this.player.go(parsePhase(rawPhase, campaign.phases.length));
      this.campaign.set(campaign);
      this.sync();
    } catch {
      this.status.set('error');
    }
  }
  private sync(): void {
    if (!this.player) return;
    this.status.set(this.player.status);
    this.phase.set(this.player.phase);
    // (ii) 暫停／停止在任一階段 → 漸變立即收尾，只留該階段有出處的疆界
    if (this.player.status !== 'playing') this.morph?.finish();
  }
  protected goPhase(n: number): void { this.player?.pause(); this.player?.go(n); }

  protected onKey(e: KeyboardEvent): void {
    if (!this.player || (e.target as HTMLElement | null)?.closest?.('input,textarea')) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); this.player.next(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); this.player.prev(); }
    else if (e.key === ' ' && !(e.target as HTMLElement | null)?.closest?.('button')) { e.preventDefault(); this.player.toggle(); }
  }
  protected cycleSheet(): void { this.sheet.set(this.sheet() === 'peek' ? 'half' : this.sheet() === 'half' ? 'full' : 'peek'); }

  /**
   * §19.2.5 返回：有快照且上一筆就是地圖 → history.back()（瀏覽器上一頁同路徑）；
   * 有快照但沒有可退的上一筆（例如重新整理後分頁歷史被換掉）→ 依快照開地圖；沒有快照（直接開 URL）→ 開地圖、日期用戰役起日。
   */
  protected back(): void {
    const s = this.snapshot();
    if (s) {
      this.returns.armRestore(s);
      // 記憶體那一格只有「本分頁從地圖進來」才有（戰役 → 戰役用 replaceUrl，上一筆仍是地圖）
      const cameFromAtlas = !!this.returns.slot();
      if (cameFromAtlas && typeof history !== 'undefined' && history.length > 1) { history.back(); return; }
      void this.router.navigate(['/'], { queryParams: atlasQueryFor(s) });
      return;
    }
    void this.router.navigate(['/'], { queryParams: { date: this.campaign()?.start ?? null } });
  }

  private async initMap(el: HTMLElement, c: Campaign): Promise<void> {
    if (typeof WebGLRenderingContext === 'undefined') return;
    const ml = await import('maplibre-gl');
    ml.setWorkerUrl(MAPLIBRE_WORKER_URL);
    const map = new ml.Map({
      container: el, style: buildBaseStyle(), bounds: c.bounds, fitBoundsOptions: { padding: 24 },
      renderWorldCopies: false, dragRotate: false, pitchWithRotate: false, fadeDuration: 0,
      attributionControl: { compact: this.mobile() },
    });
    map.touchZoomRotate.disableRotation();
    this.map = map;
    if (isDevMode()) (window as unknown as { __wlCampaignMap?: MlMap }).__wlCampaignMap = map;
    map.on('load', () => {
      const data = campaignSourceData(c);
      map.addSource('campaign-sov', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({ id: SOV_FILL, type: 'fill', source: 'campaign-sov', paint: { 'fill-color': '#94a3b8', 'fill-opacity': 0.08 } });
      map.addLayer({ id: SOV_LINE, type: 'line', source: 'campaign-sov', paint: { 'line-color': '#6b7280', 'line-width': 1.2 } });
      map.addSource(SOV_TX_SOURCE, { type: 'geojson', data: EMPTY_FC as FeatureCollection });
      map.addLayer({ id: SOV_TX_LAYERS[0], type: 'fill', source: SOV_TX_SOURCE, paint: { 'fill-color': '#94a3b8', 'fill-opacity': ['*', 0.1, ['get', 'o']] } });
      map.addLayer({ id: SOV_TX_LAYERS[1], type: 'line', source: SOV_TX_SOURCE, paint: { 'line-color': '#6b7280', 'line-width': 1.4, 'line-opacity': ['*', 0.75, ['get', 'o']], 'line-dasharray': [2, 2] } });
      for (const id of CAMPAIGN_SOURCES) map.addSource(id, { type: 'geojson', data: data[id] as unknown as FeatureCollection });
      if (!map.hasImage(ARROWHEAD_IMAGE)) map.addImage(ARROWHEAD_IMAGE, arrowheadImage(), { sdf: true });
      const fs = campaignFilters(c, this.phase());
      for (const l of campaignLayers()) map.addLayer({ ...l, filter: fs[l.id] } as LayerSpecification);
      map.fitBounds(c.bounds, { padding: 24, duration: 0, maxZoom: 10 });
      this.applyPhase(c, this.phase());
      map.once('idle', () => this.mapReady.set(true));
    });
  }

  /** 依階段過濾三個圖層，並換上該階段起日的政權疆界（§19.2.4：播放中相鄰階段做 morph，其餘直接切換）。 */
  private applyPhase(c: Campaign, ph: number): void {
    const map = this.map;
    if (!map || !map.getLayer(CAMPAIGN_LAYER_IDS[0])) return;
    const fs = campaignFilters(c, ph);
    // §19.2.7（Tai 2026-11-11 15:27 確認）：這個階段沒有 verified 圖形 → 戰役圖層整個收起，只留疆界
    const show = phaseHasVerified(c, ph) ? 'visible' : 'none';
    for (const id of CAMPAIGN_LAYER_IDS) if (map.getLayer(id)) { map.setFilter(id, fs[id] as FilterSpecification); map.setLayoutProperty(id, 'visibility', show); }
    this.morph?.finish();
    const date = c.phases.find((p) => p.seq === ph)?.start;
    if (!date) return;
    const nextDate = c.phases.find((p) => p.seq === ph + 1)?.start;
    if (nextDate) void this.borders(nextDate).catch(() => undefined); // 預取下一階段，漸變不用等網路
    void this.borders(date).then((fc) => {
      if (this.phase() !== ph || !this.map) return;
      const next = sourcedBorders(fc);
      const prev = this.shown;
      const animate = this.status() === 'playing' && prev?.phase === ph - 1 && !this.motion.reduced() && this.motion.canAnimate();
      const plan = animate ? planMorph(prev!.fc, next) : null;
      if (!plan || plan.mode === 'none') { this.settle(next, ph, date); return; }
      this.setSov('campaign-sov', { type: 'FeatureCollection', features: plan.same });
      this.setSov(SOV_TX_SOURCE, interpolate(plan, 0));
      this.transition.set(plan.mode);
      this.morph = this.motion.progress(MORPH_SEC, (t) => this.setSov(SOV_TX_SOURCE, interpolate(plan, t)), () => this.motion.inside(() => this.settle(next, ph, date)));
    }).catch(() => this.bordersFor.set(null));
  }
  /** 落定在階段：清掉中間形狀，只畫該階段有出處的疆界。 */
  private settle(fc: BorderFC, ph: number, date: string): void {
    this.morph = null;
    this.setSov(SOV_TX_SOURCE, EMPTY_FC);
    this.setSov('campaign-sov', fc);
    this.shown = { phase: ph, fc };
    this.transition.set('none');
    this.bordersFor.set(date);
  }
  private setSov(id: string, fc: BorderFC): void {
    (this.map?.getSource(id) as GeoJSONSource | undefined)?.setData(fc as unknown as FeatureCollection);
  }
  private borders(date: string): Promise<BorderFC> {
    let p = this.sovCache.get(date);
    if (!p) {
      p = this.api.sovereignty(date).then((dto) => dto.featureCollection as unknown as BorderFC);
      p.catch(() => this.sovCache.delete(date));
      this.sovCache.set(date, p);
    }
    return p;
  }
}
