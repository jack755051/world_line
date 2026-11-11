import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, NgZone, afterNextRender, inject, isDevMode, signal, viewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { gsap } from 'gsap';
import type { GeoJSONSource, Map as MlMap, MapLayerMouseEvent, Popup } from 'maplibre-gl';
import type { Feature, FeatureCollection } from 'geojson';
import { prefersReducedMotion } from '../core/motion';
import { BASEMAP_URL, MAPLIBRE_WORKER_URL } from '../shared/map/atlas-map';
import { validateProtoData, type ProtoData, type ProtoEngagement, type ProtoUnit } from './proto-data';
import {
  FRONT_RECOMPUTE_EVERY_N_FRAMES, SECONDS_PER_DAY_GAP, aggregateUnits, buildArrows, dateToIndex, effectiveT, generateFront,
  interpolateUnits, isInterpolating, levelForZoom, type FrontResult,
} from './proto-geo';
import { SIDE_COLOR, buildArrowHead, buildSymbolImages, symbolId } from './proto-symbols';

const DATA_URL = '/assets/proto/dunkirk-1940.json';
const SPEEDS = [1, 2, 4] as const;
const FADE_MS = 300;
const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] };
const BRANCH_ZH: Record<string, string> = { armor: '裝甲', infantry: '步兵', motorized: '摩托化' };
const ECHELON_ZH: Record<string, string> = { division: '師', corps: '軍' };
const SIDE_ZH = { axis: '軸心', allied: '盟軍' } as const;
const SOURCES = ['bp-theater', 'bp-fronts', 'bp-arrows', 'bp-engagements', 'bp-units'] as const;
const LAYERS = ['bp-theater-line', 'bp-fronts-band', 'bp-fronts-line-inferred', 'bp-fronts-line-manual', 'bp-arrows-line', 'bp-arrows-head', 'bp-eng-pulse', 'bp-eng-dot', 'bp-units-sel', 'bp-units-corps', 'bp-units-div'] as const;

/** 戰役 P0 手感原型頁（/campaigns/dunkirk-1940/proto）。示例資料，非史料；僅 dev＋feature flag 可進入。 */
@Component({
  selector: 'wl-battle-proto-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'block', style: 'position:relative;height:100%;background:#16202E;color:#E6EDF5;overflow:hidden', '(window:keydown)': 'onKey($event)' },
  template: `
    <div #mapEl data-testid="bp-map" [attr.data-ready]="ready()" style="position:absolute;inset:0 0 72px 0"></div>
    <div data-testid="bp-banner" style="position:absolute;top:8px;left:50%;transform:translateX(-50%);z-index:5;background:#F5A524;color:#1B1200;font-weight:700;padding:4px 16px;border-radius:4px;font-size:13px">示例資料，非史料</div>
    <aside data-testid="bp-legend" style="position:absolute;top:44px;left:12px;z-index:4;background:rgba(22,32,46,.88);padding:10px 12px;border-radius:8px;font-size:12px;line-height:1.7">
      <div><span class="sw" style="background:#3F6FD0"></span>盟軍　<span class="sw" style="background:#C24444"></span>軸心</div>
      <div>兵種：裝甲／步兵／摩托化（符號內圖示）</div>
      <div><svg width="36" height="6"><line x1="0" y1="3" x2="36" y2="3" stroke="#fff" stroke-width="2" stroke-dasharray="6 4"/></svg> 推估前線　<svg width="36" height="6"><line x1="0" y1="3" x2="36" y2="3" stroke="#fff" stroke-width="2"/></svg> 人工校正</div>
      <div>虛線外框符號＝位置內插（推估）</div>
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
  private lastArrowKey = '';
  private lastPulseIdx = -1;
  private pulse = { r: 10, o: 0 };
  private imageIds: string[] = [];
  private handlers: { type: string; layer?: string; fn: (e: never) => void }[] = [];
  private destroyed = false;
  private reduced = false;

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
    for (const s of ['bp-fronts', 'bp-arrows', 'bp-engagements', 'bp-units'] as const) map.addSource(s, { type: 'geojson', data: EMPTY });
    const side = (a: string, b: string) => ['match', ['get', 'side'], 'axis', a, b] as never;
    // 由下而上：戰區 → 前線帶 → 前線線 → 箭頭 → 交戰 → 單位
    map.addLayer({ id: 'bp-theater-line', type: 'line', source: 'bp-theater', paint: { 'line-color': '#4A6080', 'line-width': 1, 'line-dasharray': [2, 3] } });
    map.addLayer({ id: 'bp-fronts-band', type: 'fill', source: 'bp-fronts', filter: ['==', ['get', 'kind'], 'band'], paint: { 'fill-color': side(SIDE_COLOR.axis.fill, SIDE_COLOR.allied.fill), 'fill-opacity': 0.28 } });
    map.addLayer({ id: 'bp-fronts-line-inferred', type: 'line', source: 'bp-fronts', filter: ['all', ['==', ['get', 'kind'], 'line'], ['!=', ['get', 'manual'], true]], paint: { 'line-color': '#F2F5F8', 'line-width': 2.5, 'line-dasharray': [3, 2] } });
    map.addLayer({ id: 'bp-fronts-line-manual', type: 'line', source: 'bp-fronts', filter: ['all', ['==', ['get', 'kind'], 'line'], ['==', ['get', 'manual'], true]], paint: { 'line-color': '#F2F5F8', 'line-width': 3 } });
    map.addLayer({ id: 'bp-arrows-line', type: 'line', source: 'bp-arrows', filter: ['==', ['geometry-type'], 'LineString'], paint: { 'line-color': side(SIDE_COLOR.axis.fill, SIDE_COLOR.allied.fill), 'line-width': 3, 'line-opacity': 0.9 } });
    map.addLayer({ id: 'bp-arrows-head', type: 'symbol', source: 'bp-arrows', filter: ['==', ['geometry-type'], 'Point'], layout: { 'icon-image': ['concat', 'bp-arrowhead-', ['get', 'side']], 'icon-rotate': ['get', 'bearing'], 'icon-rotation-alignment': 'map', 'icon-allow-overlap': true, 'icon-size': 0.6 } });
    map.addLayer({ id: 'bp-eng-pulse', type: 'circle', source: 'bp-engagements', paint: { 'circle-radius': 10, 'circle-color': '#F5A524', 'circle-opacity': 0, 'circle-stroke-color': '#F5A524', 'circle-stroke-width': 2, 'circle-stroke-opacity': 0 } });
    map.addLayer({ id: 'bp-eng-dot', type: 'circle', source: 'bp-engagements', paint: { 'circle-radius': 6, 'circle-color': '#F5A524', 'circle-stroke-color': '#16202E', 'circle-stroke-width': 2 } });
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
      if (l !== this.level) { this.level = l; this.applyLevelOpacity(map); this.lastArrowKey = ''; this.render(); }
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
    this.render(true);
    this.zone.run(() => this.ready.set(true));
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

    // 推進箭頭：每段（日→日）固定，段或層級變了才重算
    const seg = Math.min(Math.floor(this.state.t + 1e-6), data.meta.dates.length - 2);
    const arrowKey = `${seg}|${this.level}`;
    if (arrowKey !== this.lastArrowKey) {
      this.lastArrowKey = arrowKey;
      const af: Feature[] = [];
      for (const a of buildArrows(data, this.level, seg)) {
        af.push({ type: 'Feature', properties: { side: a.side }, geometry: { type: 'LineString', coordinates: [a.from, a.to] } });
        af.push({ type: 'Feature', properties: { side: a.side, bearing: a.bearing }, geometry: { type: 'Point', coordinates: a.to } });
      }
      (map.getSource('bp-arrows') as GeoJSONSource).setData({ type: 'FeatureCollection', features: af });
    }

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
