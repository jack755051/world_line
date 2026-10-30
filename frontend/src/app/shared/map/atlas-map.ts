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
import { GAP_IMAGE_ID, GAP_STYLE, MAP_COLORS, type DecoratedProps, type GapProps } from './map-style';

export interface MapGapEvent {
  gapId: string;
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
    },
    layers: [
      { id: 'sea', type: 'background', paint: { 'background-color': MAP_COLORS.sea } },
      { id: 'land', type: 'fill', source: 'land', paint: { 'fill-color': MAP_COLORS.land } },
      { id: 'coast', type: 'line', source: 'land', paint: { 'line-color': MAP_COLORS.coast, 'line-width': 0.75 } },
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
      [attr.data-rendered-gaps]="renderedGaps()" [attr.data-map-ready]="ready() ? 'true' : null" aria-label="主地圖" role="region"></div>
    @if (engineError()) {
      <div data-testid="map-engine-error" class="sr-only">{{ engineErrorText() }}</div>
    }
  `,
})
export class AtlasMap {
  readonly collection = input<FeatureCollection<Geometry, DecoratedProps> | null>(null);
  readonly gaps = input<FeatureCollection<Geometry, GapProps> | null>(null);
  readonly selectedVersionId = input<string | null>(null);
  readonly engineErrorText = input('');

  readonly featureClick = output<MapFeatureEvent>();
  readonly emptyClick = output<void>();
  readonly gapClick = output<MapGapEvent>();
  readonly featureHover = output<MapFeatureEvent | null>();

  protected readonly renderedCount = signal(0);
  protected readonly renderedGaps = signal(0);
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
      const data = this.gaps();
      if (!this.ready()) return;
      untracked(() => (this.map?.getSource('gaps') as GeoJSONSource | undefined)?.setData(data ?? EMPTY));
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
        (map.getSource('gaps') as GeoJSONSource | undefined)?.setData(this.gaps() ?? EMPTY);
      });
      map.on('idle', () => this.countRendered());

      const layers = ['control-fill', 'control-hatch'];
      map.on('click', (e) => {
        const hit = map.queryRenderedFeatures(e.point, { layers });
        const id = hit[0]?.properties?.['versionId'] as string | undefined;
        if (id) {
          this.featureClick.emit({ versionId: id, x: e.point.x, y: e.point.y });
          return;
        }
        const gap = map.queryRenderedFeatures(e.point, { layers: ['gap-base'] })[0]?.properties?.['gapId'] as string | undefined;
        if (gap) this.gapClick.emit({ gapId: gap, x: e.point.x, y: e.point.y });
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

  private countRendered(): void {
    if (!this.map || !this.ready()) return;
    const n = this.map.queryRenderedFeatures({ layers: ['control-fill', 'control-hatch'] }).length;
    this.renderedCount.set(n);
    this.renderedGaps.set(this.map.queryRenderedFeatures({ layers: ['gap-fill'] }).length);
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
