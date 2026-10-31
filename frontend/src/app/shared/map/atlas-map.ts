import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  afterNextRender,
  effect,
  inject,
  input,
  isDevMode,
  output,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import type { FeatureCollection, Geometry } from 'geojson';
import type { GeoJSONSource, Map as MlMap, MapLayerMouseEvent, StyleSpecification } from 'maplibre-gl';
import { gapDotsImage, hatchImage } from './hatch';
import { GAP_IMAGE_ID, GAP_STYLE, MAP_COLORS, type ControlLabel, type DecoratedProps, type GapProps } from './map-style';
import type { Axis } from '../../core/atlas-state';
import { AXIS_TRANSITION_MS } from '../../core/motion';

/**
 * 「實際控制」↔「主權」切換：常數不透明度的圖層用 MapLibre paint transition 淡入淡出。
 * 控制區填色／線的不透明度是逐筆資料驅動（['get', …]），MapLibre 不支援資料驅動屬性的 transition，
 * 所以這些圖層改用 visibility（淡出結束後才隱藏、淡入開始時先顯示），國界層負責視覺上的過場。
 */
export const AXIS_PAINT: Record<Axis, [layer: string, prop: string, value: number][]> = {
  control: [
    ['sov-fill', 'fill-opacity', 0.35],
    ['sov-hatch', 'fill-opacity', 0.45],
    ['sov-hatch-base', 'fill-opacity', 0.45],
    ['sov-line', 'line-opacity', 0.4],
    ['sov-line-not-sovereign', 'line-opacity', 0.45],
    ['control-regime-outline', 'line-opacity', 0.7],
    ['control-selected', 'line-opacity', 1],
    ['gap-line', 'line-opacity', 0.45],
  ],
  sovereignty: [
    ['sov-fill', 'fill-opacity', 0.9],
    ['sov-hatch', 'fill-opacity', 1],
    ['sov-hatch-base', 'fill-opacity', 1],
    ['sov-line', 'line-opacity', 0.75],
    ['sov-line-not-sovereign', 'line-opacity', 0.8],
    ['control-regime-outline', 'line-opacity', 0],
    ['control-selected', 'line-opacity', 0],
    ['gap-line', 'line-opacity', 0],
  ],
};
/** 只屬於實際控制檢視、opacity 為資料驅動（無法 transition）的圖層：主權檢視時隱藏。 */
export const CONTROL_ONLY_LAYERS = ['gap-base', 'gap-fill', 'control-fill', 'control-hatch', 'control-line-solid', 'control-line-dotted', 'control-line-dashed'];
/** 地圖標籤矩形互撞檢查（像素）。 */
export function overlaps(a: { x: number; y: number; w: number; h: number }, b: { x: number; y: number; w: number; h: number }): boolean {
  return Math.abs(a.x - b.x) * 2 < a.w + b.w && Math.abs(a.y - b.y) * 2 < a.h + b.h;
}
import type { SovereigntyProps } from './sovereignty-style';

export interface MapGapEvent {
  gapId: string;
  x: number;
  y: number;
}

/** 點主權圖層（國界）上的國家。 */
export interface MapSovereigntyEvent {
  recordId: string;
  x: number;
  y: number;
}

export interface MapFeatureEvent {
  versionId: string;
  /** 相對於地圖容器的像素座標 */
  x: number;
  y: number;
}

/** 底圖：Natural Earth 1:50m 陸地（公有領域），隨前端打包，不用外部圖磚、不需金鑰（PRD §8.2）。 */
export const BASEMAP_URL = '/basemap/ne_50m_land.geojson';
/** MapLibre 6 的 worker 由 angular.json assets 複製到 /maplibre/（打包後 import.meta.url 會失準，須明示）。 */
export const MAPLIBRE_WORKER_URL = '/maplibre/maplibre-gl-worker.mjs';

const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] };

export function buildBaseStyle(): StyleSpecification {
  return {
    version: 8,
    sources: {
      land: { type: 'geojson', data: BASEMAP_URL, attribution: '底圖 Base map: Natural Earth（公有領域 public domain）' },
      control: { type: 'geojson', data: EMPTY, promoteId: 'versionId' },
      gaps: { type: 'geojson', data: EMPTY, promoteId: 'gapId' },
      sovereignty: {
        type: 'geojson',
        data: EMPTY,
        promoteId: 'recordId',
        attribution: '國界 Borders: OpenHistoricalMap contributors（CC0）; CNIG, GURS, Kartverket, OCHA/HDX（CC BY 4.0）; 部分線段源自 OpenStreetMap（ODbL）',
      },
    },
    layers: [
      { id: 'sea', type: 'background', paint: { 'background-color': MAP_COLORS.sea } },
      { id: 'land', type: 'fill', source: 'land', paint: { 'fill-color': MAP_COLORS.land } },
      { id: 'coast', type: 'line', source: 'land', paint: { 'line-color': MAP_COLORS.coast, 'line-width': 0.75 } },
      // 主權圖層（國界）：填色依政權；非主權實體（佔領軍政府）用斜線；控制區疊在上面
      { id: 'sov-fill', type: 'fill', source: 'sovereignty', filter: ['==', ['get', 'wlPattern'], ''], paint: { 'fill-color': ['get', 'wlFill'], 'fill-opacity': 0.9 } },
      { id: 'sov-hatch-base', type: 'fill', source: 'sovereignty', filter: ['!=', ['get', 'wlPattern'], ''], paint: { 'fill-color': MAP_COLORS.land, 'fill-opacity': 1 } },
      { id: 'sov-hatch', type: 'fill', source: 'sovereignty', filter: ['!=', ['get', 'wlPattern'], ''], paint: { 'fill-pattern': ['get', 'wlPattern'] } },
      { id: 'sov-line', type: 'line', source: 'sovereignty', filter: ['==', ['get', 'wlPattern'], ''], paint: { 'line-color': MAP_COLORS.ink, 'line-width': 0.8, 'line-opacity': 0.75 } },
      {
        id: 'sov-line-not-sovereign',
        type: 'line',
        source: 'sovereignty',
        filter: ['!=', ['get', 'wlPattern'], ''],
        paint: { 'line-color': MAP_COLORS.ink, 'line-width': 1, 'line-opacity': 0.8, 'line-dasharray': [2, 2] },
      },
      {
        // 陣營外框（補充，可開關，預設關）：只描有陣營切片的國家，不改填色
        id: 'sov-camp-line',
        type: 'line',
        source: 'sovereignty',
        filter: ['!=', ['get', 'wlCampLine'], ''],
        layout: { visibility: 'none' },
        paint: { 'line-color': ['get', 'wlCampLine'], 'line-width': 3, 'line-opacity': 0.9, 'line-offset': 1.5 },
      },
      { id: 'sov-selected', type: 'line', source: 'sovereignty', filter: ['==', ['get', 'recordId'], ''], paint: { 'line-color': MAP_COLORS.ink, 'line-width': 2 } },
      {
        // 控制資料缺（R9）：紙底＋細墨點，邊框細虛線；不與任何控制類型共用樣式
        id: 'gap-base',
        type: 'fill',
        source: 'gaps',
        paint: { 'fill-color': MAP_COLORS.land, 'fill-opacity': 1 },
      },
      { id: 'gap-fill', type: 'fill', source: 'gaps', paint: { 'fill-pattern': GAP_IMAGE_ID } },
      {
        id: 'gap-line',
        type: 'line',
        source: 'gaps',
        paint: { 'line-color': MAP_COLORS.ink, 'line-width': 0.75, 'line-opacity': 0.45, 'line-dasharray': [2, 2] },
      },
      {
        id: 'control-fill',
        type: 'fill',
        source: 'control',
        filter: ['==', ['get', 'wlPattern'], ''],
        paint: { 'fill-color': ['get', 'wlFill'], 'fill-opacity': ['get', 'wlFillOpacity'] },
      },
      {
        id: 'control-hatch',
        type: 'fill',
        source: 'control',
        filter: ['!=', ['get', 'wlPattern'], ''],
        paint: { 'fill-pattern': ['get', 'wlPattern'], 'fill-opacity': ['get', 'wlFillOpacity'] },
      },
      {
        // 政權邊框：每個控制區都有一圈墨線（同陣營同填色，政權之間靠這條線＋名稱標籤區分）；推估／不明時由下方虛線層負責
        id: 'control-regime-outline',
        type: 'line',
        source: 'control',
        filter: ['==', ['get', 'evidence'], 'attested'],
        paint: { 'line-color': MAP_COLORS.ink, 'line-width': 0.75, 'line-opacity': 0.7 },
      },
      {
        id: 'control-line-solid',
        type: 'line',
        source: 'control',
        filter: ['==', ['get', 'wlLineKind'], 'solid'],
        paint: { 'line-color': ['get', 'wlLine'], 'line-width': ['get', 'wlLineWidth'], 'line-opacity': ['get', 'wlLineOpacity'] },
      },
      {
        id: 'control-line-dotted',
        type: 'line',
        source: 'control',
        filter: ['==', ['get', 'wlLineKind'], 'dotted'],
        layout: { 'line-cap': 'round' },
        paint: { 'line-color': ['get', 'wlLine'], 'line-width': 1.5, 'line-dasharray': [0.1, 2] },
      },
      {
        // 推估過渡／不明：虛線 4–3（以 1.5px 線寬換算）
        id: 'control-line-dashed',
        type: 'line',
        source: 'control',
        filter: ['==', ['get', 'wlLineKind'], 'dashed'],
        paint: { 'line-color': ['get', 'wlLine'], 'line-width': 1.5, 'line-opacity': ['get', 'wlLineOpacity'], 'line-dasharray': [2.67, 2] },
      },
      {
        id: 'control-selected',
        type: 'line',
        source: 'control',
        filter: ['==', ['get', 'versionId'], ''],
        paint: { 'line-color': MAP_COLORS.ink, 'line-width': 1.5 },
      },
    ],
  };
}

/** 地圖上的一個衝突圖示（經緯度＝兩國交界的代表點，來自 API）。 */
export interface MapConflictIcon {
  recordId: string;
  lngLat: [number, number];
  label: string;
}
export interface MapConflictEvent {
  recordId: string;
  x: number;
  y: number;
}

/**
 * 主地圖（PRD §8.2，`shared/map`）。只畫傳入的 API 資料；本元件不產生任何資料。
 * jsdom／無 WebGL 環境下不啟動 MapLibre，改顯示錯誤（單元測試因此不需要 WebGL）。
 */
@Component({
  selector: 'wl-atlas-map',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'absolute inset-0 block overflow-hidden' },
  template: `
    <div #canvas data-testid="map-canvas" class="h-full w-full" [attr.data-rendered-features]="renderedCount()"
      [attr.data-rendered-gaps]="renderedGaps()" [attr.data-rendered-sovereignty]="renderedSovereignty()"
      [attr.data-camp-layer]="showCamps() ? 'on' : 'off'" [attr.data-axis]="appliedAxis()" [attr.data-map-ready]="ready() ? 'true' : null" aria-label="主地圖" role="region"></div>
    <!-- 政權名稱標籤（PRD §8.2：預設自稱）：HTML 疊在地圖上，跟著地圖移動；控制區在畫面上太小就不標 -->
    <div class="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      @for (l of placedLabels(); track l.versionId) {
        <span data-testid="map-regime-label" [attr.data-regime-id]="l.regimeId" class="wl-regime-label absolute -translate-x-1/2 -translate-y-1/2 whitespace-nowrap"
          [style.left.px]="l.x" [style.top.px]="l.y">{{ l.text }}</span>
      }
    </div>
    <!-- 衝突圖示（交叉雙劍，自繪 SVG）：只在點選政權後由頁面傳入相關衝突；放在兩國交界，跟著地圖移動 -->
    <div class="pointer-events-none absolute inset-0 overflow-hidden">
      @for (c of placedConflicts(); track c.recordId) {
        <button type="button" data-testid="map-conflict-icon" [attr.data-record-id]="c.recordId" [attr.aria-label]="c.label" [attr.title]="c.label"
          class="wl-conflict-icon pointer-events-auto absolute flex size-9 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-wl-outline bg-wl-surface shadow-[var(--wl-shadow-panel)] hover:bg-wl-surface-container-high"
          [style.left.px]="c.x" [style.top.px]="c.y" (click)="onConflict($event, c)">
          <svg viewBox="0 0 32 32" class="size-6 text-wl-error" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <!-- 劍一：劍尖右上、劍柄左下（劍身、護手、握把、柄頭） -->
            <path d="M27.5 4.5 L25.8 9 L12.2 22.6 L9.4 19.8 L23 6.2 Z" fill="currentColor" stroke-width="0.8" />
            <path d="M7.2 17.8 L14.2 24.8" stroke-width="2.4" />
            <path d="M10.8 21.2 L6.6 25.4" stroke-width="2.2" />
            <circle cx="5.6" cy="26.4" r="1.6" fill="currentColor" stroke-width="0" />
            <!-- 劍二：劍尖左上、劍柄右下 -->
            <path d="M4.5 4.5 L9 6.2 L22.6 19.8 L19.8 22.6 L6.2 9 Z" fill="currentColor" stroke-width="0.8" />
            <path d="M24.8 17.8 L17.8 24.8" stroke-width="2.4" />
            <path d="M21.2 21.2 L25.4 25.4" stroke-width="2.2" />
            <circle cx="26.4" cy="26.4" r="1.6" fill="currentColor" stroke-width="0" />
          </svg>
        </button>
      }
    </div>
    @if (engineError()) {
      <div data-testid="map-engine-error" class="sr-only">{{ engineErrorText() }}</div>
    }
  `,
})
export class AtlasMap {
  readonly collection = input<FeatureCollection<Geometry, DecoratedProps> | null>(null);
  readonly gaps = input<FeatureCollection<Geometry, GapProps> | null>(null);
  readonly sovereignty = input<FeatureCollection<Geometry, SovereigntyProps> | null>(null);
  readonly showCamps = input(false);
  /** 目前檢視軸；切換時用 MapLibre transition 淡入淡出（reducedMotion 時 0ms）。 */
  readonly axis = input<Axis>('control');
  readonly reducedMotion = input(false);
  /** 已套用到地圖的檢視軸（過場結束後才更新；e2e 用）。 */
  protected readonly appliedAxis = signal<Axis | null>(null);
  private axisTimer: ReturnType<typeof setTimeout> | undefined;
  readonly selectedRecordId = input<string | null>(null);
  readonly selectedVersionId = input<string | null>(null);
  readonly engineErrorText = input('');
  readonly labels = input<ControlLabel[]>([]);
  /** 要畫的衝突圖示（頁面只傳與點選政權相關的衝突；預設空陣列＝不顯示）。 */
  readonly conflicts = input<MapConflictIcon[]>([]);
  protected readonly placedConflicts = signal<(MapConflictIcon & { x: number; y: number })[]>([]);
  readonly conflictClick = output<MapConflictEvent>();
  protected readonly placedLabels = signal<{ versionId: string; regimeId: string; text: string; x: number; y: number }[]>([]);

  readonly featureClick = output<MapFeatureEvent>();
  readonly emptyClick = output<void>();
  readonly gapClick = output<MapGapEvent>();
  readonly sovereigntyClick = output<MapSovereigntyEvent>();
  readonly featureHover = output<MapFeatureEvent | null>();

  protected readonly renderedCount = signal(0);
  protected readonly renderedGaps = signal(0);
  protected readonly renderedSovereignty = signal(0);
  protected readonly ready = signal(false);
  readonly engineError = signal(false);

  private readonly canvas = viewChild.required<ElementRef<HTMLDivElement>>('canvas');
  private map: MlMap | null = null;
  private readonly destroyRef = inject(DestroyRef);

  constructor() {
    afterNextRender(() => void this.init());
    this.destroyRef.onDestroy(() => {
      clearTimeout(this.axisTimer);
      this.map?.remove();
    });

    effect(() => {
      const data = this.collection();
      if (!this.ready()) return;
      untracked(() => this.setData(data));
    });
    effect(() => {
      this.labels();
      if (!this.ready()) return;
      untracked(() => this.placeLabels());
    });
    effect(() => {
      this.conflicts();
      if (!this.ready()) return;
      untracked(() => this.placeConflicts());
    });
    effect(() => {
      const data = this.gaps();
      if (!this.ready()) return;
      untracked(() => (this.map?.getSource('gaps') as GeoJSONSource | undefined)?.setData(data ?? EMPTY));
    });
    effect(() => {
      const data = this.sovereignty();
      if (!this.ready()) return;
      untracked(() => (this.map?.getSource('sovereignty') as GeoJSONSource | undefined)?.setData(data ?? EMPTY));
    });
    effect(() => {
      const axis = this.axis();
      const reduced = this.reducedMotion();
      if (!this.ready()) return;
      untracked(() => this.applyAxis(axis, reduced ? 0 : AXIS_TRANSITION_MS));
    });
    effect(() => {
      const on = this.showCamps();
      if (!this.ready()) return;
      this.map?.setLayoutProperty('sov-camp-line', 'visibility', on ? 'visible' : 'none');
    });
    effect(() => {
      const id = this.selectedRecordId() ?? '';
      if (!this.ready()) return;
      this.map?.setFilter('sov-selected', ['==', ['get', 'recordId'], id]);
    });
    effect(() => {
      const id = this.selectedVersionId() ?? '';
      if (!this.ready()) return;
      this.map?.setFilter('control-selected', ['==', ['get', 'versionId'], id]);
    });
  }

  private async init(): Promise<void> {
    if (typeof WebGLRenderingContext === 'undefined' || typeof window === 'undefined' || !('createObjectURL' in URL)) {
      this.engineError.set(true);
      return;
    }
    try {
      const ml = await import('maplibre-gl');
      ml.setWorkerUrl(MAPLIBRE_WORKER_URL);
      const map = new ml.Map({
        container: this.canvas().nativeElement,
        style: buildBaseStyle(),
        // M0／M1 以法國 1940 為主（計畫 C8）
        center: [2.6, 46.6],
        zoom: 4.7,
        minZoom: 1.5,
        maxZoom: 9,
        attributionControl: { compact: false },
        dragRotate: false,
        pitchWithRotate: false,
      });
      map.touchZoomRotate.disableRotation();
      // 左下圖例 280px＋邊距：讓置中點避開圖例
      map.setPadding({ left: 300, top: 0, right: 0, bottom: 0 });
      this.map = map;
      if (isDevMode()) (window as unknown as { __wlMap?: MlMap }).__wlMap = map;

      map.on('styleimagemissing', (e) => this.addHatch(e.id));
      map.on('load', () => {
        this.ready.set(true);
        this.setData(this.collection());
        this.placeLabels();
        this.placeConflicts();
        (map.getSource('gaps') as GeoJSONSource | undefined)?.setData(this.gaps() ?? EMPTY);
        (map.getSource('sovereignty') as GeoJSONSource | undefined)?.setData(this.sovereignty() ?? EMPTY);
        map.setLayoutProperty('sov-camp-line', 'visibility', this.showCamps() ? 'visible' : 'none');
        this.applyAxis(this.axis(), 0);
      });
      map.on('idle', () => this.countRendered());
      map.on('move', () => {
        this.placeLabels();
        this.placeConflicts();
      });
      map.on('resize', () => {
        this.placeLabels();
        this.placeConflicts();
      });

      const layers = ['control-fill', 'control-hatch'];
      map.on('click', (e) => {
        const hit = map.queryRenderedFeatures(e.point, { layers });
        const id = hit[0]?.properties?.['versionId'] as string | undefined;
        if (id) {
          this.featureClick.emit({ versionId: id, x: e.point.x, y: e.point.y });
          return;
        }
        const gap = map.queryRenderedFeatures(e.point, { layers: ['gap-base'] })[0]?.properties?.['gapId'] as string | undefined;
        if (gap) {
          this.gapClick.emit({ gapId: gap, x: e.point.x, y: e.point.y });
          return;
        }
        const rec = map.queryRenderedFeatures(e.point, { layers: ['sov-fill', 'sov-hatch-base'] })[0]?.properties?.['recordId'] as string | undefined;
        if (rec) this.sovereigntyClick.emit({ recordId: rec, x: e.point.x, y: e.point.y });
        else this.emptyClick.emit();
      });
      for (const layer of layers) {
        map.on('mousemove', layer, (e: MapLayerMouseEvent) => {
          map.getCanvas().style.cursor = 'pointer';
          const id = e.features?.[0]?.properties?.['versionId'] as string | undefined;
          this.featureHover.emit(id ? { versionId: id, x: e.point.x, y: e.point.y } : null);
        });
        map.on('mouseleave', layer, () => {
          map.getCanvas().style.cursor = '';
          this.featureHover.emit(null);
        });
      }
      map.on('mouseenter', 'sov-fill', () => (map.getCanvas().style.cursor = 'pointer'));
      map.on('mouseleave', 'sov-fill', () => (map.getCanvas().style.cursor = ''));
      map.on('mouseenter', 'gap-base', () => (map.getCanvas().style.cursor = 'pointer'));
      map.on('mouseleave', 'gap-base', () => (map.getCanvas().style.cursor = ''));
    } catch {
      this.engineError.set(true);
    }
  }

  private setData(data: FeatureCollection<Geometry, DecoratedProps> | null): void {
    const src = this.map?.getSource('control') as GeoJSONSource | undefined;
    if (!src) return;
    src.setData(data ?? EMPTY);
  }

  /**
   * 套用檢視軸。常數不透明度圖層：先設 `<prop>-transition`，再設值 → MapLibre 依 duration 淡入淡出。
   * 資料驅動圖層：要顯示時先顯示；要隱藏時等淡出（duration）結束才隱藏。
   */
  private applyAxis(axis: Axis, duration: number): void {
    const map = this.map;
    if (!map) return;
    clearTimeout(this.axisTimer);
    // MapLibre 的型別把屬性名限定為字面值；這裡的屬性名來自 AXIS_PAINT（測試檢查過都是常數不透明度）
    const setPaint = map.setPaintProperty.bind(map) as (layer: string, name: string, value: unknown) => void;
    for (const [layer, prop, value] of AXIS_PAINT[axis]) {
      if (!map.getLayer(layer)) continue;
      setPaint(layer, `${prop}-transition`, { duration, delay: 0 });
      setPaint(layer, prop, value);
    }
    const setControl = (v: 'visible' | 'none') => CONTROL_ONLY_LAYERS.forEach((l) => map.getLayer(l) && map.setLayoutProperty(l, 'visibility', v));
    const done = () => {
      this.appliedAxis.set(axis);
      this.placeLabels();
      map.triggerRepaint();
    };
    if (axis === 'control') {
      setControl('visible');
      if (duration === 0) done();
      else this.axisTimer = setTimeout(done, duration);
    } else if (duration === 0) {
      setControl('none');
      done();
    } else {
      this.axisTimer = setTimeout(() => {
        setControl('none');
        done();
      }, duration);
    }
  }

  /** 標籤只在控制區外框投影後放得下文字時顯示（避免小區塊被字蓋住）。 */
  private placeLabels(): void {
    const map = this.map;
    if (!map) return;
    const placed: { versionId: string; regimeId: string; text: string; x: number; y: number }[] = [];
    const boxes: { x: number; y: number; w: number; h: number }[] = [];
    for (const l of this.labels()) {
      const a = map.project([l.bbox[0], l.bbox[1]]);
      const b = map.project([l.bbox[2], l.bbox[3]]);
      const w = Math.abs(b.x - a.x);
      const h = Math.abs(b.y - a.y);
      // 文字寬約每字 14px（12px＋字距）；外框至少要比字寬 1.6 倍、高 32px，避免標籤壓出小區塊
      const textW = l.text.length * 14;
      if (w < textW * (l.fit ?? 1.6) || h < 32) continue;
      const p = map.project(l.lngLat);
      // 國界標籤（fit 有設）放寬了大小門檻，改用互撞檢查避免疊字；控制區標籤維持原規則
      const box = { x: p.x, y: p.y, w: textW + 8, h: 20 };
      if (l.fit !== undefined && boxes.some((b) => overlaps(b, box))) continue;
      boxes.push(box);
      placed.push({ versionId: l.versionId, regimeId: l.regimeId, text: l.text, x: p.x, y: p.y });
    }
    this.placedLabels.set(placed);
  }

  private placeConflicts(): void {
    const map = this.map;
    if (!map) return;
    this.placedConflicts.set(this.conflicts().map((c) => ({ ...c, ...map.project(c.lngLat) })));
  }

  protected onConflict(e: MouseEvent, c: MapConflictIcon & { x: number; y: number }): void {
    e.stopPropagation();
    this.conflictClick.emit({ recordId: c.recordId, x: c.x, y: c.y });
  }

  private countRendered(): void {
    if (!this.map || !this.ready()) return;
    const n = this.map.queryRenderedFeatures({ layers: ['control-fill', 'control-hatch'] }).length;
    this.renderedCount.set(n);
    this.renderedGaps.set(this.map.queryRenderedFeatures({ layers: ['gap-fill'] }).length);
    this.renderedSovereignty.set(this.map.queryRenderedFeatures({ layers: ['sov-fill', 'sov-hatch-base'] }).length);
  }

  private addHatch(id: string): void {
    if (id === GAP_IMAGE_ID && this.map && !this.map.hasImage(id)) {
      const img = gapDotsImage(GAP_STYLE.dotColor, GAP_STYLE.grid);
      if (img) this.map.addImage(id, img, { pixelRatio: 2 });
      return;
    }
    const m = /^wl-hatch-(partial|contested)-([0-9a-f]{6})$/.exec(id);
    if (!m || !this.map || this.map.hasImage(id)) return;
    const img = hatchImage(`#${m[2]}`, m[1] as 'partial' | 'contested');
    if (img) this.map.addImage(id, img, { pixelRatio: 2 });
  }

  /** 讓外部（卡片定位）把經緯度換成像素 */
  project(lngLat: [number, number]): { x: number; y: number } | null {
    return this.map ? this.map.project(lngLat) : null;
  }
}
