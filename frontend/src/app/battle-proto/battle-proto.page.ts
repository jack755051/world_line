import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, NgZone, afterNextRender, inject, isDevMode, signal, viewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { gsap } from 'gsap';
import type { GeoJSONSource, Map as MlMap, MapLayerMouseEvent, Popup } from 'maplibre-gl';
import type { Feature, FeatureCollection } from 'geojson';
import { prefersReducedMotion } from '../core/motion';
import { BASEMAP_URL, MAPLIBRE_WORKER_URL } from '../shared/map/atlas-map';
import { validateProtoData, type ProtoData, type ProtoEngagement, type ProtoUnit } from './proto-data';
import {
  FRONT_RECOMPUTE_EVERY_N_FRAMES, SECONDS_PER_DAY_GAP, aggregateUnits, bearingDeg, buildArrows, dateToIndex, effectiveT, generateFront,
  interpolateUnits, isInterpolating, levelForZoom, type FrontResult,
} from './proto-geo';
import { FX_KEYS, arrowCurve, arrowProgress, defaultFx, morphRing, pointOnLines, sliceCurve, territoryRings, type FxKey, type FxState } from './proto-fx';
import { SIDE_COLOR, buildArrowHead, buildSymbolImages, symbolId } from './proto-symbols';

const DATA_URL = '/assets/proto/dunkirk-1940.json';
const SPEEDS = [1, 2, 4] as const;
const FADE_MS = 300;
const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] };
const BRANCH_ZH: Record<string, string> = { armor: '裝甲', infantry: '步兵', motorized: '摩托化' };
const ECHELON_ZH: Record<string, string> = { division: '師', corps: '軍' };
const SIDE_ZH = { axis: '軸心', allied: '盟軍' } as const;
const SOURCES = ['bp-theater', 'bp-fronts', 'bp-arrows', 'bp-engagements', 'bp-units', 'bp-fx-terr', 'bp-fx-shock'] as const;
const FX_ZH: Record<FxKey, string> = { arrows: '箭頭', territory: '領土', glow: '光暈', sparks: '火花', shock: '衝擊波', tear: '撕裂色偏', title: '標題' };
const CAMPAIGN_TITLE = '敦克爾克 1940（示例）';
const MAX_SPARKS = 140;
const LAYERS = ['bp-theater-line', 'bp-fx-terr-fill', 'bp-fronts-band', 'bp-fx-glow-3', 'bp-fx-glow-2', 'bp-fx-glow-1', 'bp-fronts-line-inferred', 'bp-fronts-line-manual', 'bp-arrows-line', 'bp-arrows-head', 'bp-eng-pulse', 'bp-eng-dot', 'bp-units-sel', 'bp-units-corps', 'bp-units-div', 'bp-fx-shock'] as const;

/** 戰役 P0 手感原型頁（/campaigns/dunkirk-1940/proto）。示例資料，非史料；僅 dev＋feature flag 可進入。 */
@Component({
  selector: 'wl-battle-proto-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'block', style: 'position:relative;height:100%;background:#16202E;color:#E6EDF5;overflow:hidden', '(window:keydown)': 'onKey($event)' },
  template: `
    <div #mapEl data-testid="bp-map" [attr.data-ready]="ready()" style="position:absolute;inset:0 0 72px 0"></div>
    <div data-testid="bp-banner" style="position:absolute;top:8px;left:50%;transform:translateX(-50%);z-index:5;background:#F5A524;color:#1B1200;font-weight:700;padding:4px 16px;border-radius:4px;font-size:13px">示例資料，非史料</div>
    <canvas #sparkEl data-testid="bp-sparks" style="position:absolute;left:0;top:0;pointer-events:none;z-index:3" [style.display]="fx().sparks && !reducedFx ? 'block' : 'none'"></canvas>
    @if (fx().title) {
      <div data-testid="bp-date-hud" style="position:absolute;top:8px;left:12px;z-index:4;font-size:22px;font-weight:700;font-variant-numeric:tabular-nums;text-shadow:0 1px 4px #000;pointer-events:none">{{ dateLabel() }}</div>
      <div data-testid="bp-title" style="position:absolute;left:16px;bottom:88px;z-index:3;pointer-events:none;text-shadow:0 2px 8px #000">
        <div style="font-size:34px;font-weight:800;letter-spacing:2px;opacity:.9">{{ campaignTitle }}</div>
        <div data-testid="bp-day-title" style="font-size:16px;opacity:.85">{{ dayTitle() }}</div>
      </div>
    }
    <aside data-testid="bp-legend" style="position:absolute;top:44px;left:12px;z-index:4;background:rgba(22,32,46,.88);padding:10px 12px;border-radius:8px;font-size:12px;line-height:1.7">
      <div><span class="sw" style="background:#3F6FD0"></span>盟軍　<span class="sw" style="background:#C24444"></span>軸心</div>
      <div>兵種：裝甲／步兵／摩托化（符號內圖示）</div>
      <div><svg width="36" height="6"><line x1="0" y1="3" x2="36" y2="3" stroke="#fff" stroke-width="2" stroke-dasharray="6 4"/></svg> 推估前線　<svg width="36" height="6"><line x1="0" y1="3" x2="36" y2="3" stroke="#fff" stroke-width="2"/></svg> 人工校正</div>
      <div>虛線外框符號＝位置內插（推估）</div>
      <div data-testid="bp-fx-panel" style="margin-top:4px;border-top:1px solid #2A394C;padding-top:4px">
        @for (k of fxKeys; track k) {
          <label style="display:inline-block;margin-right:8px;white-space:nowrap"><input type="checkbox" [attr.data-testid]="'bp-fx-' + k" [checked]="fx()[k]" [disabled]="reducedFx && (k === 'tear' || k === 'sparks')" (change)="setFx(k, $any($event.target).checked)" /> {{ fxZh[k] }}</label>
        }
      </div>
      @if (fx().sparks && !reducedFx) { <div data-testid="bp-sparks-note" style="font-size:11px;opacity:.8">火花為氣氛效果，不代表實際交戰位置</div> }
    </aside>
    @if (interp()) {
      <div data-testid="bp-interp-badge" style="position:absolute;top:44px;right:12px;z-index:4;background:rgba(22,32,46,.9);border:1px dashed #fff;padding:4px 10px;border-radius:4px;font-size:12px" [style.right]="card() ? '372px' : '12px'">位置內插（推估）</div>
    }
    @if (error()) { <div data-testid="bp-error" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;z-index:6;background:#16202E">示例資料載入失敗：{{ error() }}</div> }
    @if (card(); as c) {
      <aside data-testid="bp-card" style="position:absolute;top:0;right:0;bottom:72px;width:360px;z-index:5;background:#1E2B3C;padding:20px;overflow:auto;box-shadow:-4px 0 16px rgba(0,0,0,.35)">
        <button type="button" data-testid="bp-card-close" (click)="selected.set(null)" style="float:right;background:none;border:0;color:inherit;font-size:20px;cursor:pointer" aria-label="關閉">×</button>
        <h2 data-testid="bp-card-name" style="font-size:20px;font-weight:700;margin:0 0 12px">{{ c.name }}</h2>
        <dl style="display:grid;grid-template-columns:80px 1fr;gap:8px;font-size:14px;margin:0">
          <dt>梯隊</dt><dd>{{ c.echelon }}</dd><dt>兵種</dt><dd>{{ c.branch }}</dd><dt>陣營</dt><dd>{{ c.side }}</dd>
          <dt>當日狀態</dt><dd data-testid="bp-card-status">{{ c.status }}</dd><dt>來源</dt><dd>{{ c.source }}</dd>
          @if (c.members) { <dt>下轄</dt><dd>{{ c.members }}</dd> }
        </dl>
        <p style="margin-top:16px;font-size:12px;opacity:.7">示例資料，非史料。</p>
      </aside>
    }
    <footer data-testid="bp-timeline" style="position:absolute;left:0;right:0;bottom:0;height:72px;z-index:5;background:#101823;display:flex;align-items:center;gap:12px;padding:0 16px;border-top:1px solid #2A394C">
      <button type="button" data-testid="bp-prev" class="btn" (click)="step(-1)" aria-label="上一日">⏮</button>
      <button type="button" data-testid="bp-play" class="btn" (click)="togglePlay()" [attr.aria-pressed]="playing()">{{ playing() ? '⏸' : '▶' }}</button>
      <button type="button" data-testid="bp-next" class="btn" (click)="step(1)" aria-label="下一日">⏭</button>
      <span style="display:flex;gap:4px">
        @for (s of speeds; track s) { <button type="button" class="btn" [attr.data-testid]="'bp-speed-' + s" [style.outline]="speed() === s ? '2px solid #8BD3DD' : 'none'" (click)="setSpeed(s)">{{ s }}x</button> }
      </span>
      <div style="flex:1;position:relative;display:flex;flex-direction:column;gap:2px">
        <input data-testid="bp-slider" type="range" min="0" [max]="maxSlider" step="1" [value]="slider()" (input)="onSlide($event)" (change)="commitUrl()" style="width:100%" aria-label="時間軸" />
        <div style="display:flex;justify-content:space-between;font-size:11px;opacity:.8">@for (d of dates(); track d) { <span>{{ d }}</span> }</div>
      </div>
      <span data-testid="bp-date" style="min-width:92px;text-align:right;font-variant-numeric:tabular-nums">{{ dateLabel() }}</span>
    </footer>
  `,
  styles: [`
    .btn{background:#26364A;color:#E6EDF5;border:0;border-radius:6px;min-width:36px;height:32px;cursor:pointer;font-size:14px}
    .btn:hover{background:#31465F}
    .sw{display:inline-block;width:12px;height:12px;border-radius:2px;vertical-align:-1px;margin-right:4px}
  `],
})
export class BattleProtoPage {
  private readonly zone = inject(NgZone);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly mapEl = viewChild.required<ElementRef<HTMLElement>>('mapEl');
  private readonly sparkEl = viewChild.required<ElementRef<HTMLCanvasElement>>('sparkEl');

  protected readonly fxKeys = FX_KEYS;
  protected readonly fxZh = FX_ZH;
  protected readonly campaignTitle = CAMPAIGN_TITLE;
  protected readonly fx = signal<FxState>(defaultFx());
  protected reducedFx = false;
  protected readonly dayTitle = () => `${this.dateLabel()}　示例日 ${this.dayIdx() + 1}／${this.dates().length}`;

  protected readonly speeds = SPEEDS;
  protected readonly ready = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly playing = signal(false);
  protected readonly speed = signal<number>(1);
  protected readonly interp = signal(false);
  protected readonly dayIdx = signal(0);
  protected readonly slider = signal(0);
  protected readonly dates = signal<string[]>([]);
  protected readonly selected = signal<string | null>(null);
  protected maxSlider = 1000;
  protected readonly dateLabel = () => this.dates()[this.dayIdx()] ?? '';
  protected readonly card = () => this.buildCard();

  private data: ProtoData | null = null;
  private unitById = new Map<string, ProtoUnit>();
  private map: MlMap | null = null;
  private popup: Popup | null = null;
  private tl: gsap.core.Timeline | null = null;
  private ctx: gsap.Context | null = null;
  private readonly state = { t: 0 };
  private level: 'corps' | 'division' = 'division';
  private frame = 0;
  private lastFront: FrontResult | null = null;
  private lastPulseIdx = -1;
  private pulse = { r: 10, o: 0 };
  private imageIds: string[] = [];
  private handlers: { type: string; layer?: string; fn: (e: never) => void }[] = [];
  private destroyed = false;
  private reduced = false;
  private curves = new Map<string, { id: string; side: string; curve: [number, number][] }[]>();
  private terrCache = new Map<string, { axis: ReturnType<typeof morphRing> | null; allied: ReturnType<typeof morphRing> | null }>();
  private sparks: { lng: number; lat: number; vx: number; vy: number; life: number; max: number; side: string }[] = [];
  private sparkTick: (() => void) | null = null;
  private ro: ResizeObserver | null = null;
  private hostEl: HTMLElement | null = null;
  private shockFired = false;
  private tearFired = false;
  private shock = { r: 0, o: 0 };

  constructor() {
    inject(DestroyRef).onDestroy(() => this.teardown());
    afterNextRender(() => { void this.zone.runOutsideAngular(() => this.init()); });
  }

  // ───────── 初始化 ─────────
  private async init(): Promise<void> {
    try {
      const res = await fetch(DATA_URL);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = validateProtoData(await res.json());
      if (this.destroyed) return;
      this.data = data;
      this.unitById = new Map(data.units.map((u) => [u.id, u]));
      this.reduced = prefersReducedMotion();
      this.reducedFx = this.reduced;
      if (this.reduced) this.fx.update((f) => ({ ...f, tear: false, sparks: false }));
      this.dates.set(data.meta.dates);
      this.maxSlider = (data.meta.dates.length - 1) * 1000;
      const q = this.route.snapshot.queryParamMap;
      const sp = Number(q.get('speed'));
      if ((SPEEDS as readonly number[]).includes(sp)) this.speed.set(sp);
      this.state.t = dateToIndex(data.meta.dates, q.get('date'));
      const ml = await import('maplibre-gl');
      if (this.destroyed) return;
      ml.setWorkerUrl(MAPLIBRE_WORKER_URL);
      const map = new ml.Map({
        container: this.mapEl().nativeElement,
        style: {
          version: 8,
          sources: { 'bp-land': { type: 'geojson', data: BASEMAP_URL, attribution: '底圖 Natural Earth（公有領域）' } },
          layers: [
            { id: 'bp-bg', type: 'background', paint: { 'background-color': '#16202E' } },
            { id: 'bp-land-fill', type: 'fill', source: 'bp-land', paint: { 'fill-color': '#243449' } },
            { id: 'bp-land-line', type: 'line', source: 'bp-land', paint: { 'line-color': '#3B506B', 'line-width': 1 } },
          ],
        },
        center: [3.9, 50.7], zoom: 7.2, minZoom: 5, maxZoom: 10, renderWorldCopies: false, dragRotate: false, fadeDuration: 0,
        attributionControl: { compact: true },
      });
      map.touchZoomRotate.disableRotation();
      this.map = map;
      this.popup = new ml.Popup({ closeButton: true, maxWidth: '260px' });
      if (isDevMode()) {
        (window as unknown as Record<string, unknown>)['__bpDebug'] = {
          map,
          sources: () => Object.keys(map.getStyle().sources).filter((s) => s.startsWith('bp-')),
          layers: () => map.getStyle().layers.map((l) => l.id).filter((l) => l.startsWith('bp-')),
          images: () => this.imageIds.slice(),
          t: () => this.state.t,
          fx: () => ({ ...this.fx() }),
          sparkCount: () => this.sparks.length,
        };
      }
      map.on('load', () => this.onLoad(map, data));
    } catch (e) {
      this.zone.run(() => this.error.set(e instanceof Error ? e.message : String(e)));
    }
  }

  private on<K extends string>(map: MlMap, type: K, layerOrFn: string | ((e: never) => void), fn?: (e: never) => void): void {
    if (typeof layerOrFn === 'string') { map.on(type as 'click', layerOrFn, fn as never); this.handlers.push({ type, layer: layerOrFn, fn: fn! }); }
    else { map.on(type as 'zoom', layerOrFn as never); this.handlers.push({ type, fn: layerOrFn }); }
  }

  private onLoad(map: MlMap, data: ProtoData): void {
    // 符號圖像：啟動時一次產生
    for (const im of [...buildSymbolImages(data.units), buildArrowHead('axis'), buildArrowHead('allied')]) {
      map.addImage(im.id, im.image, { pixelRatio: im.pixelRatio });
      this.imageIds.push(im.id);
    }
    const [x0, y0, x1, y1] = data.meta.theater;
    map.addSource('bp-theater', { type: 'geojson', data: { type: 'FeatureCollection', features: [
      { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]] } },
      { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: data.meta.land_mask } },
    ] } });
    for (const s of ['bp-fronts', 'bp-arrows', 'bp-engagements', 'bp-units', 'bp-fx-terr', 'bp-fx-shock'] as const) map.addSource(s, { type: 'geojson', data: EMPTY });
    const side = (a: string, b: string) => ['match', ['get', 'side'], 'axis', a, b] as never;
    // 由下而上：戰區 → 前線帶 → 前線線 → 箭頭 → 交戰 → 單位
    map.addLayer({ id: 'bp-theater-line', type: 'line', source: 'bp-theater', paint: { 'line-color': '#4A6080', 'line-width': 1, 'line-dasharray': [2, 3] } });
    // 縮小（z<7）時強調大局層：領土色塊與光暈在 z 6.5→7 之間淡出到較淡的值
    const zoomOp = (hi: number, lo: number) => ['interpolate', ['linear'], ['zoom'], 6.5, hi, 7, lo] as never;
    const vis = (k: FxKey) => (this.fx()[k] ? 'visible' : 'none') as 'visible' | 'none';
    map.addLayer({ id: 'bp-fx-terr-fill', type: 'fill', source: 'bp-fx-terr', layout: { visibility: vis('territory') }, paint: { 'fill-color': side(SIDE_COLOR.axis.fill, SIDE_COLOR.allied.fill), 'fill-opacity': zoomOp(0.4, 0.14), 'fill-antialias': false } }, 'bp-fronts-band');
    map.addLayer({ id: 'bp-fronts-band', type: 'fill', source: 'bp-fronts', filter: ['==', ['get', 'kind'], 'band'], paint: { 'fill-color': side(SIDE_COLOR.axis.fill, SIDE_COLOR.allied.fill), 'fill-opacity': 0.28 } });
    // 邊界霓虹光暈：多層不同寬度＋模糊的線（未用 WebGL 泛光，見報告）
    for (const [i, w, b, o] of [[3, 16, 10, 0.16], [2, 9, 5, 0.28], [1, 4.5, 1.5, 0.5]] as const) {
      map.addLayer({ id: `bp-fx-glow-${i}`, type: 'line', source: 'bp-fronts', filter: ['==', ['get', 'kind'], 'line'], layout: { visibility: vis('glow'), 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': '#7FE9FF', 'line-width': w, 'line-blur': b, 'line-opacity': zoomOp(o * 1.5, o * 0.6) } });
    }
    map.addLayer({ id: 'bp-fronts-line-inferred', type: 'line', source: 'bp-fronts', filter: ['all', ['==', ['get', 'kind'], 'line'], ['!=', ['get', 'manual'], true]], paint: { 'line-color': '#F2F5F8', 'line-width': 2.5, 'line-dasharray': [3, 2] } });
    map.addLayer({ id: 'bp-fronts-line-manual', type: 'line', source: 'bp-fronts', filter: ['all', ['==', ['get', 'kind'], 'line'], ['==', ['get', 'manual'], true]], paint: { 'line-color': '#F2F5F8', 'line-width': 3 } });
    map.addLayer({ id: 'bp-arrows-line', type: 'line', source: 'bp-arrows', filter: ['==', ['geometry-type'], 'LineString'], paint: { 'line-color': side(SIDE_COLOR.axis.fill, SIDE_COLOR.allied.fill), 'line-width': ['interpolate', ['linear'], ['zoom'], 6.5, 5, 7, 3] as never, 'line-opacity': 0.9 } });
    map.addLayer({ id: 'bp-arrows-head', type: 'symbol', source: 'bp-arrows', filter: ['==', ['geometry-type'], 'Point'], layout: { 'icon-image': ['concat', 'bp-arrowhead-', ['get', 'side']], 'icon-rotate': ['get', 'bearing'], 'icon-rotation-alignment': 'map', 'icon-allow-overlap': true, 'icon-size': 0.6 } });
    map.addLayer({ id: 'bp-eng-pulse', type: 'circle', source: 'bp-engagements', paint: { 'circle-radius': 10, 'circle-color': '#F5A524', 'circle-opacity': 0, 'circle-stroke-color': '#F5A524', 'circle-stroke-width': 2, 'circle-stroke-opacity': 0 } });
    map.addLayer({ id: 'bp-eng-dot', type: 'circle', source: 'bp-engagements', paint: { 'circle-radius': 6, 'circle-color': '#F5A524', 'circle-stroke-color': '#16202E', 'circle-stroke-width': 2 } });
    map.addLayer({ id: 'bp-fx-shock', type: 'circle', source: 'bp-fx-shock', paint: { 'circle-radius': 0, 'circle-color': '#FFFFFF', 'circle-opacity': 0, 'circle-stroke-color': '#FFD27A', 'circle-stroke-width': 3, 'circle-stroke-opacity': 0, 'circle-pitch-alignment': 'map' } });
    map.addLayer({ id: 'bp-units-sel', type: 'circle', source: 'bp-units', filter: ['==', ['get', 'id'], ''], paint: { 'circle-radius': 26, 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': 2 } });
    const unitLayer = (id: string, level: string) => map.addLayer({
      id, type: 'symbol', source: 'bp-units', filter: ['==', ['get', 'level'], level],
      layout: { 'icon-image': ['get', 'icon'], 'icon-allow-overlap': true, 'icon-ignore-placement': true },
      paint: { 'icon-opacity': 1, 'icon-opacity-transition': { duration: this.reduced ? 0 : FADE_MS, delay: 0 } },
    });
    unitLayer('bp-units-corps', 'corps');
    unitLayer('bp-units-div', 'division');

    this.level = levelForZoom(map.getZoom());
    this.applyLevelOpacity(map);
    this.on(map, 'zoom', () => {
      const l = levelForZoom(map.getZoom());
      if (l !== this.level) { this.level = l; this.applyLevelOpacity(map); this.render(); }
    });
    for (const layer of ['bp-units-div', 'bp-units-corps']) {
      this.on(map, 'click', layer, (e: MapLayerMouseEvent) => {
        const id = e.features?.[0]?.properties?.['id'] as string | undefined;
        if (id) { this.popup?.remove(); this.zone.run(() => this.selected.set(id)); this.updateSelection(); }
      });
      this.on(map, 'mouseenter', layer, () => (map.getCanvas().style.cursor = 'pointer'));
      this.on(map, 'mouseleave', layer, () => (map.getCanvas().style.cursor = ''));
    }
    this.on(map, 'click', 'bp-eng-dot', (e: MapLayerMouseEvent) => {
      const id = e.features?.[0]?.properties?.['id'] as string | undefined;
      const eng = data.engagements.find((x) => x.id === id);
      if (eng && this.popup) this.popup.setLngLat([eng.lng, eng.lat]).setDOMContent(this.engagementDom(eng)).addTo(map);
    });

    // GSAP：timeline 驅動 0…N-1 進度（1x＝兩示例日之間 3 秒）
    this.ctx = gsap.context(() => {
      const n = data.meta.dates.length - 1;
      this.tl = gsap.timeline({ paused: true, onUpdate: () => this.render(), onComplete: () => { this.zone.run(() => this.playing.set(false)); this.render(true); this.commitUrl(); } });
      this.tl.to(this.state, { t: n, duration: n * SECONDS_PER_DAY_GAP, ease: 'none' }, 0);
      this.tl.timeScale(this.speed());
      this.tl.time(this.state.t * SECONDS_PER_DAY_GAP, true);
    });
    (map.getSource('bp-fx-shock') as GeoJSONSource).setData({ type: 'FeatureCollection', features: [{ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: [(x0 + x1) / 2, (y0 + y1) / 2] } }] });
    this.startSparks(map);
    this.render(true);
    this.zone.run(() => this.ready.set(true));
    if (this.state.t < 0.05) this.fireShock(map);
  }

  private applyLevelOpacity(map: MlMap): void {
    map.setPaintProperty('bp-units-corps', 'icon-opacity', this.level === 'corps' ? 1 : 0);
    map.setPaintProperty('bp-units-div', 'icon-opacity', this.level === 'division' ? 1 : 0);
  }

  // ───────── 每幀渲染 ─────────
  private render(settled = false): void {
    const map = this.map, data = this.data;
    if (!map || !data || this.destroyed) return;
    const t = effectiveT(this.state.t, this.reduced);
    const interp = isInterpolating(t);
    const idx = Math.round(t);
    this.frame++;
    const pts = interpolateUnits(data, t);

    // 單位（師級＋軍級同一 source，layer filter 切層級；淡入淡出由 icon-opacity transition）
    const feats: Feature[] = [];
    for (const lv of ['division', 'corps'] as const) {
      for (const u of aggregateUnits(data.units, pts, lv)) {
        const meta = this.unitById.get(u.id);
        if (!meta) continue;
        feats.push({ type: 'Feature', properties: { id: u.id, level: u.level, side: u.side, icon: symbolId(meta.sidc, interp) }, geometry: { type: 'Point', coordinates: [u.lng, u.lat] } });
      }
    }
    (map.getSource('bp-units') as GeoJSONSource).setData({ type: 'FeatureCollection', features: feats });

    // 前線：整日用資料（override 優先）；內插中不做形狀插值，每 N 幀依單位位置重算
    if (!interp || settled || !this.lastFront || this.frame % FRONT_RECOMPUTE_EVERY_N_FRAMES === 0) {
      const override = !interp ? data.fronts.find((f) => f.date === data.meta.dates[idx])?.override?.coordinates ?? null : null;
      this.lastFront = generateFront(pts, { theater: data.meta.theater, land: data.meta.land_mask, override });
      const ff: Feature[] = [];
      for (const b of this.lastFront.bands) ff.push({ type: 'Feature', properties: { kind: 'band', side: b.side }, geometry: { type: 'Polygon', coordinates: [b.ring] } });
      for (const l of this.lastFront.lines) ff.push({ type: 'Feature', properties: { kind: 'line', manual: this.lastFront.manual }, geometry: { type: 'LineString', coordinates: l } });
      (map.getSource('bp-fronts') as GeoJSONSource).setData({ type: 'FeatureCollection', features: ff });
    }

    // 推進箭頭：曲線＋進度（開關關閉時回到整條直線）。曲線每段／層級快取，進度每幀切片
    let seg = Math.min(Math.floor(this.state.t + 1e-6), data.meta.dates.length - 2);
    let f = Math.min(1, Math.max(0, this.state.t - seg));
    // 剛抵達某示例日（f≈0）時顯示「抵達這天的那一段」畫滿，避免靜止時箭頭消失；首日無前段則整段畫滿
    let rest = false;
    if (f < 1e-6) { if (seg > 0) { seg -= 1; f = 1; } else rest = true; }
    const arrowKey = `${seg}|${this.level}`;
    let curves = this.curves.get(arrowKey);
    if (!curves) {
      curves = buildArrows(data, this.level, seg).map((a) => ({ id: a.id, side: a.side, curve: arrowCurve(a.from, a.to) }));
      this.curves.set(arrowKey, curves);
    }
    const fxA = this.fx().arrows;
    const p = fxA ? arrowProgress(f, { reduced: this.reduced, settled: rest }) : 1;
    const af: Feature[] = [];
    for (const c of curves) {
      const sl = sliceCurve(c.curve, p);
      if (!sl.line.length) continue;
      af.push({ type: 'Feature', properties: { side: c.side }, geometry: { type: 'LineString', coordinates: fxA ? sl.line : [c.curve[0], c.curve[c.curve.length - 1]] } });
      af.push({ type: 'Feature', properties: { side: c.side, bearing: fxA ? sl.bearing : bearingDeg(c.curve[0], c.curve[c.curve.length - 1]) }, geometry: { type: 'Point', coordinates: sl.head } });
    }
    (map.getSource('bp-arrows') as GeoJSONSource).setData({ type: 'FeatureCollection', features: af });

    // 領土：前後兩示例日的陣營多邊形，flubber 依段內進度變形（reduced 跳格、不內插）
    this.renderTerritory(map, data, t);

    // 交戰：靠近某示例日才顯示；抵達該日脈動 2 次
    const near = Math.abs(t - idx) < 0.25;
    const engs = near ? data.engagements.filter((e) => e.date === data.meta.dates[idx]) : [];
    (map.getSource('bp-engagements') as GeoJSONSource).setData({ type: 'FeatureCollection', features: engs.map((e) => ({ type: 'Feature', properties: { id: e.id }, geometry: { type: 'Point', coordinates: [e.lng, e.lat] } })) });
    if (!interp && engs.length && this.lastPulseIdx !== idx) { this.lastPulseIdx = idx; this.firePulse(map); }
    if (interp) this.lastPulseIdx = -1;

    this.zone.run(() => {
      this.interp.set(interp);
      this.dayIdx.set(idx);
      this.slider.set(Math.round(this.state.t * 1000));
    });
  }

  // ───────── 大局動畫層（規格 §10） ─────────
  /** 領土：兩示例日各陣營最大塊多邊形，flubber 依段內進度變形；reduced 時取最近示例日、不內插。 */
  private renderTerritory(map: MlMap, data: ProtoData, t: number): void {
    if (!this.fx().territory) return;
    const last = data.meta.dates.length - 1;
    const seg = Math.min(Math.floor(t + 1e-6), last - 1);
    const f = this.reduced ? Math.round(t - seg) : Math.min(1, Math.max(0, t - seg));
    let m = this.terrCache.get(String(seg));
    if (!m) {
      const ring = (i: number, side: 'axis' | 'allied') => territoryRings(interpolateUnits(data, i), side, data.meta.theater, data.meta.land_mask)[0];
      const mk = (side: 'axis' | 'allied') => { const a = ring(seg, side), b = ring(seg + 1, side); return a && b ? morphRing(a, b) : null; };
      m = { axis: mk('axis'), allied: mk('allied') };
      this.terrCache.set(String(seg), m);
    }
    const feats: Feature[] = [];
    for (const side of ['allied', 'axis'] as const) {
      const fn = m[side];
      if (fn) feats.push({ type: 'Feature', properties: { side }, geometry: { type: 'Polygon', coordinates: [fn(f)] } });
    }
    (map.getSource('bp-fx-terr') as GeoJSONSource | undefined)?.setData({ type: 'FeatureCollection', features: feats });
  }

  protected setFx(k: FxKey, on: boolean): void {
    this.fx.update((v) => ({ ...v, [k]: on }));
    const map = this.map;
    if (!map) return;
    const set = (ids: string[]) => { for (const id of ids) if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none'); };
    if (k === 'territory') { set(['bp-fx-terr-fill']); if (on) this.render(); }
    if (k === 'glow') set(['bp-fx-glow-3', 'bp-fx-glow-2', 'bp-fx-glow-1']);
    if (k === 'arrows') this.render();
    if (k === 'sparks' && !on) this.sparks = [];
  }

  /** 火花粒子：獨立 canvas，沿當天前線撒；用 gsap.ticker 驅動，離開頁面移除。純氣氛，不代表交戰位置。 */
  private startSparks(map: MlMap): void {
    const cv = this.sparkEl().nativeElement;
    const host = this.mapEl().nativeElement;
    this.hostEl = host;
    const resize = () => { const r = host.getBoundingClientRect(), d = window.devicePixelRatio || 1; cv.width = Math.round(r.width * d); cv.height = Math.round(r.height * d); cv.style.width = `${r.width}px`; cv.style.height = `${r.height}px`; };
    resize();
    this.ro = new ResizeObserver(resize);
    this.ro.observe(host);
    const g = cv.getContext('2d');
    this.sparkTick = () => {
      if (!g || this.destroyed) return;
      const d = cv.width / (cv.clientWidth || 1);
      g.setTransform(1, 0, 0, 1, 0, 0);
      g.clearRect(0, 0, cv.width, cv.height);
      if (!this.fx().sparks || this.reduced) { this.sparks.length = 0; return; }
      const dt = Math.min(0.05, gsap.ticker.deltaRatio(60) / 60);
      const lines = this.lastFront?.lines ?? [];
      for (let i = 0; i < 3 && this.sparks.length < MAX_SPARKS && lines.length; i++) {
        const p = pointOnLines(lines, Math.random());
        if (p) this.sparks.push({ lng: p[0], lat: p[1], vx: (Math.random() - 0.5) * 50, vy: -20 - Math.random() * 50, life: 0, max: 0.5 + Math.random() * 0.8, side: 'x' });
      }
      g.setTransform(d, 0, 0, d, 0, 0);
      g.globalCompositeOperation = 'lighter';
      this.sparks = this.sparks.filter((s) => (s.life += dt) < s.max);
      for (const s of this.sparks) {
        const pt = map.project([s.lng, s.lat]);
        const k = s.life / s.max;
        const x = pt.x + s.vx * s.life, y = pt.y + s.vy * s.life + 40 * s.life * s.life;
        g.fillStyle = `rgba(255,${Math.round(210 - 120 * k)},90,${(1 - k) * 0.9})`;
        g.beginPath(); g.arc(x, y, 2.2 * (1 - k * 0.6), 0, 6.283); g.fill();
      }
    };
    gsap.ticker.add(this.sparkTick);
  }

  /** 開戰衝擊波：圓圈放大再淡出，整頁只一次；reduced 不做。 */
  private fireShock(map: MlMap): void {
    if (this.shockFired || !this.fx().shock || this.reduced) return;
    this.shockFired = true;
    const s = this.shock;
    this.ctx?.add(() => {
      gsap.fromTo(s, { r: 10, o: 0.95 }, {
        r: 520, o: 0, duration: 1.4, ease: 'power2.out',
        onUpdate: () => { if (this.map === map && map.getLayer('bp-fx-shock')) { map.setPaintProperty('bp-fx-shock', 'circle-radius', s.r); map.setPaintProperty('bp-fx-shock', 'circle-stroke-opacity', s.o); } },
        onComplete: () => { if (this.map === map && map.getLayer('bp-fx-shock')) map.setPaintProperty('bp-fx-shock', 'circle-stroke-opacity', 0); },
      });
    });
  }

  /** 畫面撕裂＋色偏：整段體驗只一次、0.36 秒；reduced 不做。位移＋色偏無亮度閃爍。 */
  private fireTear(): void {
    if (this.tearFired || !this.fx().tear || this.reduced) return;
    this.tearFired = true;
    const el = this.mapEl().nativeElement;
    const split = 'drop-shadow(5px 0 0 rgba(255,40,60,.5)) drop-shadow(-5px 0 0 rgba(40,220,255,.5))';
    this.ctx?.add(() => {
      const tl = gsap.timeline({ onComplete: () => { gsap.set(el, { clearProps: 'transform,filter' }); } });
      tl.set(el, { x: -9, skewX: 2, filter: split })
        .set(el, { x: 7, skewX: -1.5 }, 0.09)
        .set(el, { x: -3, skewX: 0.8, filter: 'drop-shadow(2px 0 0 rgba(255,40,60,.4)) drop-shadow(-2px 0 0 rgba(40,220,255,.4))' }, 0.18)
        .set(el, { clearProps: 'transform,filter' }, 0.36);
    });
  }

  private firePulse(map: MlMap): void {
    if (this.reduced) return;
    const p = this.pulse;
    p.r = 8; p.o = 0.9;
    this.ctx?.add(() => {
      gsap.fromTo(p, { r: 8, o: 0.9 }, {
        r: 30, o: 0, duration: 0.7, ease: 'power1.out', repeat: 1, overwrite: true,
        onUpdate: () => { if (this.map === map && map.getLayer('bp-eng-pulse')) { map.setPaintProperty('bp-eng-pulse', 'circle-radius', p.r); map.setPaintProperty('bp-eng-pulse', 'circle-stroke-opacity', p.o); } },
      });
    });
  }

  // ───────── 控制 ─────────
  protected togglePlay(): void {
    const tl = this.tl;
    if (!tl) return;
    if (this.playing()) { tl.pause(); this.playing.set(false); this.snapRest(); return; }
    if (this.state.t >= this.dates().length - 1 - 1e-6) tl.time(0, true);
    tl.timeScale(this.speed());
    this.zone.runOutsideAngular(() => tl.play());
    this.playing.set(true);
    if (this.map) this.fireShock(this.map);
    this.fireTear();
  }

  /** 暫停時停在目前位置（可停在兩日之間）；URL 寫最近的示例日。 */
  private snapRest(): void { this.render(true); this.commitUrl(); }

  protected step(dir: -1 | 1): void {
    const tl = this.tl;
    if (!tl) return;
    tl.pause(); this.playing.set(false);
    const t = this.state.t, last = this.dates().length - 1;
    const target = Math.min(last, Math.max(0, dir > 0 ? Math.floor(t + 1e-3) + 1 : Math.ceil(t - 1e-3) - 1));
    gsap.killTweensOf(tl);
    const to = target * SECONDS_PER_DAY_GAP;
    if (this.reduced) { tl.time(to, false); this.render(true); this.commitUrl(); return; }
    this.zone.runOutsideAngular(() => gsap.to(tl, { time: to, duration: 0.7, ease: 'power2.inOut', overwrite: true, onComplete: () => { this.render(true); this.commitUrl(); } }));
  }

  protected setSpeed(s: number): void {
    this.speed.set(s);
    this.tl?.timeScale(s);
    this.commitUrl();
  }

  protected onSlide(e: Event): void {
    const tl = this.tl;
    if (!tl) return;
    gsap.killTweensOf(tl);
    tl.pause(); this.playing.set(false);
    const v = Number((e.target as HTMLInputElement).value) / 1000;
    tl.time(v * SECONDS_PER_DAY_GAP, false);
    this.render();
  }

  protected onKey(e: KeyboardEvent): void {
    const el = e.target as HTMLElement | null;
    if (el && (el.tagName === 'INPUT' && (el as HTMLInputElement).type !== 'range' || el.tagName === 'TEXTAREA')) return;
    if (e.code === 'Space') { if (el?.tagName === 'BUTTON') return; e.preventDefault(); this.togglePlay(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); this.step(-1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); this.step(1); }
  }

  protected commitUrl(): void {
    if (this.destroyed || !this.data) return;
    const date = this.data.meta.dates[Math.round(this.state.t)];
    void this.router.navigate([], { relativeTo: this.route, queryParams: { date, speed: this.speed() }, queryParamsHandling: 'merge', replaceUrl: true });
  }

  // ───────── 資訊卡／Popup ─────────
  private updateSelection(): void {
    this.map?.setFilter('bp-units-sel', ['==', ['get', 'id'], this.selected() ?? '']);
  }

  private buildCard(): { name: string; echelon: string; branch: string; side: string; status: string; source: string; members: string } | null {
    const id = this.selected(), data = this.data;
    if (!id || !data) return null;
    const u = this.unitById.get(id);
    if (!u) return null;
    const idx = this.dayIdx();
    const date = data.meta.dates[idx];
    const kids = u.echelon === 'corps' ? data.units.filter((k) => k.parent_id === id) : [];
    const ids = kids.length ? kids.map((k) => k.id) : [id];
    const pos = data.positions.filter((p) => ids.includes(p.unit_id) && p.date === date);
    const status = this.interp() ? 'inferred（位置內插）' : pos.length && pos.every((p) => p.status === 'recorded') ? 'recorded' : 'inferred';
    return {
      name: u.name_zh, echelon: ECHELON_ZH[u.echelon] ?? u.echelon, branch: u.echelon === 'corps' ? '綜合' : BRANCH_ZH[u.branch] ?? u.branch,
      side: SIDE_ZH[u.side], status, source: pos.every((p) => p.source === 'example') ? '示例' : '—', members: kids.map((k) => k.name_zh).join('、'),
    };
  }

  private engagementDom(e: ProtoEngagement): HTMLElement {
    const root = document.createElement('div');
    root.setAttribute('data-testid', 'bp-engagement-popup');
    root.style.cssText = 'color:#16202E;font-size:13px;line-height:1.6';
    const name = (r: string) => e.units.filter((x) => x.role === r).map((x) => this.unitById.get(x.unit_id)?.name_zh ?? x.unit_id).join('、');
    const [a, b] = e.interaction_tag.split('_vs_').map((x) => BRANCH_ZH[x] ?? x);
    for (const [k, v] of [['進攻', name('attacker')], ['防守', name('defender')], ['兵種配對', `${a} vs ${b}`], ['結果', e.outcome ?? '—'], ['來源', '示例']]) {
      const row = document.createElement('div');
      row.textContent = `${k}：${v}`;
      root.appendChild(row);
    }
    return root;
  }

  // ───────── 清理（驗收 7：離開後不殘留 source／layer／image／監聽） ─────────
  private teardown(): void {
    this.destroyed = true;
    this.tl?.kill();
    this.ctx?.revert();
    this.tl = null; this.ctx = null;
    if (this.sparkTick) gsap.ticker.remove(this.sparkTick);
    this.sparkTick = null; this.sparks = [];
    this.ro?.disconnect(); this.ro = null;
    gsap.killTweensOf(this.shock);
    if (this.hostEl) gsap.set(this.hostEl, { clearProps: 'transform,filter' });
    this.curves.clear(); this.terrCache.clear();
    this.popup?.remove();
    const map = this.map;
    if (map) {
      for (const h of this.handlers) { if (h.layer) map.off(h.type as 'click', h.layer, h.fn as never); else map.off(h.type as 'zoom', h.fn as never); }
      for (const l of LAYERS) if (map.getLayer(l)) map.removeLayer(l);
      for (const s of SOURCES) if (map.getSource(s)) map.removeSource(s);
      for (const i of this.imageIds) if (map.hasImage(i)) map.removeImage(i);
      map.remove();
    }
    this.handlers = []; this.imageIds = []; this.map = null; this.popup = null;
    delete (window as unknown as Record<string, unknown>)['__bpDebug'];
  }
}
