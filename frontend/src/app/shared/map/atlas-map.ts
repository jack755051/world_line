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
import { hatchImage } from './hatch';
import { MAP_COLORS, type ControlLabel, type DecoratedProps } from './map-style';

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
    },
    layers: [
      { id: 'sea', type: 'background', paint: { 'background-color': MAP_COLORS.sea } },
      { id: 'land', type: 'fill', source: 'land', paint: { 'fill-color': MAP_COLORS.land } },
      { id: 'coast', type: 'line', source: 'land', paint: { 'line-color': MAP_COLORS.coast, 'line-width': 0.75 } },
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
      [attr.data-map-ready]="ready() ? 'true' : null" aria-label="主地圖" role="region"></div>
    <!-- 政權名稱標籤（PRD §8.2：預設自稱）：HTML 疊在地圖上，跟著地圖移動；控制區在畫面上太小就不標 -->
    <div class="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      @for (l of placedLabels(); track l.versionId) {
        <span data-testid="map-regime-label" [attr.data-regime-id]="l.regimeId" class="wl-regime-label absolute -translate-x-1/2 -translate-y-1/2 whitespace-nowrap"
          [style.left.px]="l.x" [style.top.px]="l.y">{{ l.text }}</span>
      }
    </div>
    @if (engineError()) {
      <div data-testid="map-engine-error" class="sr-only">{{ engineErrorText() }}</div>
    }
  `,
})
export class AtlasMap {
  readonly collection = input<FeatureCollection<Geometry, DecoratedProps> | null>(null);
  readonly selectedVersionId = input<string | null>(null);
  readonly engineErrorText = input('');
  readonly labels = input<ControlLabel[]>([]);
  protected readonly placedLabels = signal<{ versionId: string; regimeId: string; text: string; x: number; y: number }[]>([]);

  readonly featureClick = output<MapFeatureEvent>();
  readonly emptyClick = output<void>();
  readonly featureHover = output<MapFeatureEvent | null>();

  protected readonly renderedCount = signal(0);
  protected readonly ready = signal(false);
  readonly engineError = signal(false);

  private readonly canvas = viewChild.required<ElementRef<HTMLDivElement>>('canvas');
  private map: MlMap | null = null;
  private readonly destroyRef = inject(DestroyRef);

  constructor() {
    afterNextRender(() => void this.init());
    this.destroyRef.onDestroy(() => this.map?.remove());

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
      });
      map.on('idle', () => this.countRendered());
      map.on('move', () => this.placeLabels());
      map.on('resize', () => this.placeLabels());

      const layers = ['control-fill', 'control-hatch'];
      map.on('click', (e) => {
        const hit = map.queryRenderedFeatures(e.point, { layers });
        const id = hit[0]?.properties?.['versionId'] as string | undefined;
        if (id) this.featureClick.emit({ versionId: id, x: e.point.x, y: e.point.y });
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
    } catch {
      this.engineError.set(true);
    }
  }

  private setData(data: FeatureCollection<Geometry, DecoratedProps> | null): void {
    const src = this.map?.getSource('control') as GeoJSONSource | undefined;
    if (!src) return;
    src.setData(data ?? EMPTY);
  }

  /** 標籤只在控制區外框投影後放得下文字時顯示（避免小區塊被字蓋住）。 */
  private placeLabels(): void {
    const map = this.map;
    if (!map) return;
    const placed = [];
    for (const l of this.labels()) {
      const a = map.project([l.bbox[0], l.bbox[1]]);
      const b = map.project([l.bbox[2], l.bbox[3]]);
      const w = Math.abs(b.x - a.x);
      const h = Math.abs(b.y - a.y);
      // 文字寬約每字 14px（12px＋字距）；外框至少要比字寬 1.6 倍、高 32px，避免標籤壓出小區塊
      if (w < l.text.length * 14 * 1.6 || h < 32) continue;
      const p = map.project(l.lngLat);
      placed.push({ versionId: l.versionId, regimeId: l.regimeId, text: l.text, x: p.x, y: p.y });
    }
    this.placedLabels.set(placed);
  }

  private countRendered(): void {
    if (!this.map || !this.ready()) return;
    const n = this.map.queryRenderedFeatures({ layers: ['control-fill', 'control-hatch'] }).length;
    this.renderedCount.set(n);
  }

  private addHatch(id: string): void {
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
