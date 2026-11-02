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
import { staggerOnArcs, worldShiftArc } from './conflict-arc';
import type { FeatureCollection, Geometry, Position } from 'geojson';
import type { GeoJSONSource, GeoJSONSourceDiff, Map as MlMap, MapLayerMouseEvent, StyleSpecification } from 'maplibre-gl';
import { gapDotsImage, hatchImage, patternIds } from './hatch';
import { GAP_IMAGE_ID, GAP_STYLE, MAP_COLORS, type ControlLabel, type DecoratedProps, type GapProps } from './map-style';
import { AtlasState, type Axis } from '../../core/atlas-state';
import { AXIS_TRANSITION_MS } from '../../core/motion';
import { focusMaskPath, focusPadding, geometryBounds, polygonRings, type FocusInset } from './focus';
import type { LngLat, PaddingOptions } from 'maplibre-gl';

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

/** 載入指示顯示期間抵達的新國界淡入時長（毫秒）。 */
export const FADE_IN_MS = 280;

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
        /** maxzoom 限制 worker 切片至 zoom 10（預設 18）；zoom>10 時 overzoom 仍使用 zoom-10 tile，
         *  幾何座標精度不變，視覺無差異。大幅降低 setData 後 worker 的切片計算量。 */
        maxzoom: 10,
        attribution: '國界 Borders: OpenHistoricalMap contributors（CC0）; CNIG, GURS, Kartverket, OCHA/HDX（CC BY 4.0）; 部分線段源自 OpenStreetMap（ODbL）',
      },
    },
    layers: [
      { id: 'sea', type: 'background', paint: { 'background-color': MAP_COLORS.sea } },
      { id: 'land', type: 'fill', source: 'land', paint: { 'fill-color': MAP_COLORS.land } },
      { id: 'coast', type: 'line', source: 'land', paint: { 'line-color': MAP_COLORS.coast, 'line-width': 0.75 } },
      // 主權圖層（國界）：填色依政權；非主權實體（佔領軍政府）用斜線；控制區疊在上面
      { id: 'sov-fill', type: 'fill', source: 'sovereignty', filter: ['==', ['get', 'wlPattern'], ''], paint: { 'fill-color': ['get', 'wlFill'], 'fill-opacity': 0.9 } },
      { id: 'sov-hatch-base', type: 'fill', source: 'sovereignty', filter: ['!=', ['get', 'wlPattern'], ''], paint: { 'fill-color': ['get', 'wlBase'], 'fill-opacity': 1 } },
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
  /** 遠距交戰虛線弧取樣點（雙方不相鄰時才有；lngLat 此時是弧線中點），見 conflict-arc.ts */
  arc?: [number, number][] | null;
  /** 弧線哪一端在被選政權（0＝起點、1＝終點）：決定弧線放在哪一份世界副本、鏡頭以哪一端為準 */
  focusEnd?: 0 | 1 | null;
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
      [attr.data-camp-layer]="showCamps() ? 'on' : 'off'" [attr.data-axis]="appliedAxis()" [attr.data-map-ready]="ready() ? 'true' : null"
      [attr.data-focus-record]="focusedRecord()" [attr.data-focus-occupied]="focusOccupied()" [attr.data-camera]="cameraMoving() ? 'moving' : 'idle'"
      [attr.data-render]="renderBusySig() ? 'busy' : 'idle'" [attr.data-sov-fade]="fadeCount()" [attr.data-arc-fit]="arcFit()" aria-label="主地圖" role="region"></div>
    <!-- 政權名稱標籤（PRD §8.2：預設自稱）：HTML 疊在地圖上，跟著地圖移動；控制區在畫面上太小就不標 -->
    <div class="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      @for (l of placedLabels(); track l.versionId) {
        <span data-testid="map-regime-label" [attr.data-regime-id]="l.regimeId" class="wl-regime-label absolute -translate-x-1/2 -translate-y-1/2 whitespace-nowrap"
          [style.left.px]="l.x" [style.top.px]="l.y">{{ l.text }}</span>
      }
    </div>
    <!--
      聚焦遮罩（Tai 2026-10-31）：點政權後，被選政權以外蓋一層半透明紙色＋backdrop-filter 模糊。
      用一個 HTML 層＋clip-path: path(evenodd, 地圖區矩形＋政權各環) 挖空被選政權：只需一次 GPU 模糊、不必複製地圖，
      地圖移動時（含飛行過場）每幀重算路徑（投影後距離 < 1px 的點略過）。pointer-events: none，不擋地圖點擊。
    -->
    <div #focusMask data-testid="map-focus-mask" aria-hidden="true" [attr.data-active]="focusedRecord() ? 'true' : 'false'"
      class="pointer-events-none absolute inset-0 bg-[rgb(236_228_210/0.42)] backdrop-blur-[3px] transition-opacity duration-200 motion-reduce:transition-none"
      [class.opacity-0]="!focusedRecord()" [class.invisible]="!focusedRecord() && !maskFading()"></div>
    <!-- 衝突圖示（交叉雙劍，自繪 SVG）：只在點選政權後由頁面傳入相關衝突；放在兩國交界，跟著地圖移動 -->
    <div class="pointer-events-none absolute inset-0 overflow-hidden">
      <!-- 遠距交戰虛線弧（雙方不相鄰）：SVG 疊在聚焦遮罩之上，跟著地圖移動；底下一條紙色寬線當描邊，模糊遮罩上也看得清楚 -->
      <svg data-testid="map-conflict-arcs" class="absolute inset-0 h-full w-full overflow-visible text-wl-error" aria-hidden="true">
        @for (c of placedConflicts(); track c.recordId) {
          @if (c.points) {
            <polyline [attr.points]="c.points" fill="none" stroke="rgb(250 246 236 / 0.85)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
            <polyline data-testid="map-conflict-arc" [attr.data-record-id]="c.recordId" [attr.points]="c.points" fill="none" stroke="currentColor"
              stroke-width="2" stroke-dasharray="7 6" stroke-linecap="round" stroke-linejoin="round" />
          }
        }
      </svg>
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
  /** 頁面的「載入中」指示顯示過、尚未消耗：這時抵達的新國界用淡入呈現（reducedMotion 時直接出現），之後送出 fadeConsumed。 */
  readonly fadeArmed = input(false);
  readonly fadeConsumed = output<void>();
  /** 已套用到地圖的檢視軸（過場結束後才更新；e2e 用）。 */
  protected readonly appliedAxis = signal<Axis | null>(null);
  private axisTimer: ReturnType<typeof setTimeout> | undefined;
  readonly selectedRecordId = input<string | null>(null);
  /** 聚焦的主權紀錄（被選政權當前領土）；null＝不聚焦。 */
  readonly focusRecordId = input<string | null>(null);
  /** 聚焦置中時要避開的面板大小（右側面板寬或底部面板高）。 */
  readonly focusInset = input<FocusInset>({ right: 0, bottom: 0 });
  protected readonly focusedRecord = signal<string | null>(null);
  /** 聚焦時一起挖亮的佔領區數（聚焦政權是佔領方） */
  protected readonly focusOccupied = signal(0);
  protected readonly maskFading = signal(false);
  protected readonly cameraMoving = signal(false);
  private readonly focusMask = viewChild<ElementRef<HTMLDivElement>>('focusMask');
  private focusRings: Position[][] = [];
  private focusKey = '';
  private focusBounds: unknown = null;
  /** 聚焦前的視角；關掉聚焦時飛回（使用者聚焦後自己拖過／縮放過就不飛回，只還原邊距）。 */
  private savedCamera: { center: LngLat; zoom: number; padding: PaddingOptions } | null = null;
  private userMoved = false;
  private maskFrame = 0;
  private fadeTimer: ReturnType<typeof setTimeout> | undefined;
  readonly selectedVersionId = input<string | null>(null);
  readonly engineErrorText = input('');
  readonly labels = input<ControlLabel[]>([]);
  /** 要畫的衝突圖示（頁面只傳與點選政權相關的衝突；預設空陣列＝不顯示）。 */
  readonly conflicts = input<MapConflictIcon[]>([]);
  protected readonly placedConflicts = signal<(MapConflictIcon & { x: number; y: number; points: string | null })[]>([]);
  readonly conflictClick = output<MapConflictEvent>();
  protected readonly placedLabels = signal<{ versionId: string; regimeId: string; text: string; x: number; y: number }[]>([]);

  readonly featureClick = output<MapFeatureEvent>();
  readonly emptyClick = output<void>();
  readonly gapClick = output<MapGapEvent>();
  readonly sovereigntyClick = output<MapSovereigntyEvent>();
  readonly featureHover = output<MapFeatureEvent | null>();
  /** MapLibre 還在載入／切片 source（setData 後或平移到新區域）：true；畫面 idle 後 false。 */
  readonly renderBusy = output<boolean>();
  protected readonly renderBusySig = signal(false);
  /** 已播放的國界淡入次數（e2e 檢查用）。 */
  protected readonly fadeCount = signal(0);

  protected readonly renderedCount = signal(0);
  protected readonly renderedGaps = signal(0);
  protected readonly renderedSovereignty = signal(0);
  protected readonly ready = signal(false);
  readonly engineError = signal(false);

  private readonly canvas = viewChild.required<ElementRef<HTMLDivElement>>('canvas');
  private map: MlMap | null = null;
  private readonly destroyRef = inject(DestroyRef);
  private readonly state = inject(AtlasState);
  /** 目前已推送進 sovereignty source 的 feature ID 集合（promoteId = recordId）。
   *  非空時改用 updateData() 差異更新，僅傳送增減的 feature，略過未變的幾何。 */
  private _sovIds = new Set<string>();
  /** 最後一次呼叫 setData/updateData 的時間點（performance.now()），供 setRenderBusy(false) 計算 worker+render 耗時。 */
  private _sovSetDataTs = 0;

  constructor() {
    afterNextRender(() => void this.init());
    this.destroyRef.onDestroy(() => {
      clearTimeout(this.axisTimer);
      clearTimeout(this.fadeTimer);
      cancelAnimationFrame(this.maskFrame);
      this._sovIds = new Set();
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
      untracked(() => {
        this.placeConflicts();
        this.fitArcs();
      });
    });
    effect(() => {
      const data = this.gaps();
      if (!this.ready()) return;
      untracked(() => (this.map?.getSource('gaps') as GeoJSONSource | undefined)?.setData(data ?? EMPTY));
    });
    effect(() => {
      const data = this.sovereignty();
      if (!this.ready()) return;
      untracked(() => {
        performance.mark('wl:sov:effect');
        const armed = this.fadeArmed() && (data?.features.length ?? 0) > 0;
        const fade = armed && !this.reducedMotion();
        if (armed) this.fadeConsumed.emit();
        if (fade) this.fadeSovereignty('start');
        this.ensurePatterns(data);
        this.applySovereigntyData(data);
        performance.mark('wl:sov:setdata');
        this._sovSetDataTs = performance.now();
        if (fade) this.fadeSovereignty('end');
      });
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
      const id = this.focusRecordId();
      const fc = this.sovereignty();
      const inset = this.focusInset();
      const reduced = this.reducedMotion();
      if (!this.ready()) return;
      untracked(() => this.applyFocus(id, fc, inset, reduced));
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
        this.addHatch(GAP_IMAGE_ID);
        this.ensurePatterns(this.sovereignty());
        this.applySovereigntyData(this.sovereignty());
        map.setLayoutProperty('sov-camp-line', 'visibility', this.showCamps() ? 'visible' : 'none');
        this.applyAxis(this.axis(), 0);
        this.applyFocus(this.focusRecordId(), this.sovereignty(), this.focusInset(), this.reducedMotion());
      });
      map.on('movestart', (e) => {
        this.cameraMoving.set(true);
        if ((e as { originalEvent?: unknown }).originalEvent && this.focusedRecord()) this.userMoved = true;
      });
      map.on('moveend', () => {
        this.cameraMoving.set(false);
        this.fitArcs();
        this.scheduleMask();
      });
      map.on('idle', () => {
        this.countRendered();
        this.setRenderBusy(false);
      });
      map.on('dataloading', () => this.setRenderBusy(true));
      map.on('zoomend', () => this.state.mapZoom.set(map.getZoom()));
      map.on('move', () => {
        this.placeLabels();
        this.placeConflicts();
        this.scheduleMask();
      });
      map.on('resize', () => {
        this.placeLabels();
        this.placeConflicts();
        this.scheduleMask();
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

  /**
   * 聚焦：飛到被選政權當前領土的外框、置於可見區中央（四周 48px，右側／下方再扣掉面板），最大縮放 6；
   * 換成別的政權時從目前視角接著飛，原視角只記第一次。取消聚焦時飛回原視角。減少動態時直接跳。
   */
  private applyFocus(id: string | null, fc: FeatureCollection<Geometry, SovereigntyProps> | null, inset: FocusInset, reduced: boolean): void {
    const map = this.map;
    if (!map) return;
    const f = id ? fc?.features.find((x) => x.properties.recordId === id) : undefined;
    const bounds = f ? geometryBounds(f.geometry) : null;
    const duration = reduced ? 0 : 800;
    if (!f || !bounds) {
      this.clearFocus(duration);
      return;
    }
    const key = `${id}|${inset.right}|${inset.bottom}`;
    if (key === this.focusKey) return;
    this.focusKey = key;
    if (!this.savedCamera) {
      this.savedCamera = { center: map.getCenter(), zoom: map.getZoom(), padding: map.getPadding() };
      this.userMoved = false;
    }
    clearTimeout(this.fadeTimer);
    this.maskFading.set(false);
    // 聚焦佔領國（例：德國）時，它佔領／併入的地區一起挖亮（仍保留斜線，看得出不是本土）；鏡頭只框本土，不會拉到全歐
    const occupied = fc?.features.filter((x) => x.properties.occupierRegimeId && x.properties.occupierRegimeId === f.properties.regimeId) ?? [];
    this.focusOccupied.set(occupied.length);
    this.focusRings = [f, ...occupied].flatMap((x) => polygonRings(x.geometry));
    this.focusedRecord.set(id);
    const el = map.getContainer();
    const padding = focusPadding(inset, el.clientWidth, el.clientHeight);
    this.focusBounds = bounds;
    const cam = map.cameraForBounds(bounds, { padding, absolutePadding: true, maxZoom: 6 });
    if (cam) map.easeTo({ ...cam, duration, essential: false });
    this.drawMask();
    if (duration === 0) queueMicrotask(() => this.fitArcs());
  }

  private clearFocus(duration: number): void {
    const map = this.map;
    if (!map || !this.focusedRecord()) return;
    this.focusKey = '';
    this.arcFitKey = '';
    this.focusBounds = null;
    this.focusedRecord.set(null);
    this.focusOccupied.set(0);
    this.focusRings = [];
    // 遮罩淡出（200ms）期間保留原本的挖空路徑
    this.maskFading.set(duration > 0);
    clearTimeout(this.fadeTimer);
    if (duration > 0) this.fadeTimer = setTimeout(() => this.maskFading.set(false), 220);
    const saved = this.savedCamera;
    this.savedCamera = null;
    if (!saved) return;
    if (this.userMoved) map.easeTo({ padding: saved.padding, duration });
    else map.easeTo({ center: saved.center, zoom: saved.zoom, padding: saved.padding, duration });
  }

  private scheduleMask(): void {
    if (!this.focusedRecord() || this.maskFrame) return;
    this.maskFrame = requestAnimationFrame(() => {
      this.maskFrame = 0;
      this.drawMask();
    });
  }

  private drawMask(): void {
    const el = this.focusMask()?.nativeElement;
    const map = this.map;
    if (!el || !map || !this.focusedRecord()) return;
    const d = focusMaskPath(this.focusRings, (p) => map.project(p), el.clientWidth, el.clientHeight);
    el.style.clipPath = `path(evenodd, '${d}')`;
  }

  private setData(data: FeatureCollection<Geometry, DecoratedProps> | null): void {
    const src = this.map?.getSource('control') as GeoJSONSource | undefined;
    if (!src) return;
    this.ensurePatterns(data);
    src.setData(data ?? EMPTY);
  }

  /**
   * 更新 sovereignty source：
   * - 首次（_sovIds 空）或清空（新資料無 feature）→ setData 全量替換並重設 ID 集合。
   * - 否則計算增/刪 diff，以 updateData() 只傳送異動 feature，不重建未改變的幾何。
   *   同一個 recordId 代表相同 DB 紀錄（固定幾何與屬性），出現在兩份資料中即表示不需更新。
   */
  private applySovereigntyData(data: FeatureCollection<Geometry, SovereigntyProps> | null): void {
    const src = this.map?.getSource('sovereignty') as GeoJSONSource | undefined;
    if (!src) return;
    const newFeatures = data?.features ?? [];
    if (this._sovIds.size === 0 || newFeatures.length === 0) {
      src.setData(data ?? EMPTY);
      this._sovIds = new Set(newFeatures.map((f) => f.properties.recordId));
      return;
    }
    const newIds = new Set(newFeatures.map((f) => f.properties.recordId));
    const add = newFeatures.filter((f) => !this._sovIds.has(f.properties.recordId));
    const remove = [...this._sovIds].filter((id) => !newIds.has(id));
    if (add.length === 0 && remove.length === 0) return; // 完全相同（atlas-data sovKey 已去重，此路應極少觸發）
    const diff: GeoJSONSourceDiff = {};
    if (add.length) diff.add = add;
    if (remove.length) diff.remove = remove;
    void src.updateData(diff);
    this._sovIds = newIds;
  }

  /**
   * 斜線圖樣先加進地圖再 setData（Tai 2026-11-01：1945-08-01 滿洲國斜線沒畫出來）。
   * MapLibre 6 的 styleimagemissing 在切片排版之後才補圖，第一次排版缺圖的圖徵不會重排，
   * 所以只靠 styleimagemissing 時，哪些斜線畫得出來要看當天資料重設幾次。
   */
  private ensurePatterns(data: FeatureCollection | null | undefined): void {
    for (const id of patternIds(data)) this.addHatch(id);
  }

  /**
   * 套用檢視軸。常數不透明度圖層：先設 `<prop>-transition`，再設值 → MapLibre 依 duration 淡入淡出。
   * 資料驅動圖層：要顯示時先顯示；要隱藏時等淡出（duration）結束才隱藏。
   */
  private setRenderBusy(v: boolean): void {
    if (this.renderBusySig() === v) return;
    if (!v && this._sovSetDataTs > 0) {
      const workerRenderMs = Math.round(performance.now() - this._sovSetDataTs);
      this._sovSetDataTs = 0;
      performance.mark('wl:sov:idle');
      try {
        performance.measure('wl:sov:fetch',   'wl:sov:fetch-start',  'wl:sov:fetch-end');
        performance.measure('wl:sov:signal',  'wl:sov:fetch-end',    'wl:sov:signal-set');
        performance.measure('wl:sov:effect',  'wl:sov:signal-set',   'wl:sov:effect');
        performance.measure('wl:sov:setdata', 'wl:sov:effect',       'wl:sov:setdata');
        performance.measure('wl:sov:worker',  'wl:sov:setdata',      'wl:sov:idle');
      } catch { /* marks 可能因中止或快取命中而缺失 */ }
      console.log(`[wl:perf:sov] worker+render=${workerRenderMs}ms`, performance.getEntriesByType('measure').filter(m => m.name.startsWith('wl:sov:')).map(m => `${m.name.replace('wl:sov:', '')}=${Math.round(m.duration)}ms`).join(' '));
      performance.clearMarks(); performance.clearMeasures();
    }
    this.renderBusySig.set(v);
    this.renderBusy.emit(v);
  }

  /** 新國界淡入：先把國界層不透明度瞬間降到 15%，換資料後再以 FADE_IN_MS 過渡回目前檢視軸的值。 */
  private fadeSovereignty(phase: 'start' | 'end'): void {
    const map = this.map;
    if (!map) return;
    const setPaint = map.setPaintProperty.bind(map) as (layer: string, name: string, value: unknown) => void;
    const layers = AXIS_PAINT[this.axis()].filter(([l]) => l.startsWith('sov-') && map.getLayer(l));
    if (phase === 'start') {
      for (const [layer, prop, value] of layers) {
        setPaint(layer, `${prop}-transition`, { duration: 0, delay: 0 });
        setPaint(layer, prop, value * 0.15);
      }
      return;
    }
    // 下一幀才設回：讓 0.15 先生效，transition 才有起點
    requestAnimationFrame(() => {
      for (const [layer, prop, value] of layers) {
        setPaint(layer, `${prop}-transition`, { duration: FADE_IN_MS, delay: 0 });
        setPaint(layer, prop, value);
      }
      this.fadeCount.update((n) => n + 1);
    });
  }

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
    const center = map.getCenter().lng;
    const raw = this.conflicts().map((c) => {
      if (!c.arc?.length) return { c, ...map.project(c.lngLat), path: null as { x: number; y: number }[] | null };
      // 弧線（含雙劍）平移到離地圖中心最近的世界副本，跨換日線（例如日本—美國）時不會畫到畫面外
      const k = worldShiftArc(c.arc, center, c.focusEnd);
      const path = c.arc.map(([x, y]) => map.project([x + k, y]));
      return { c, ...map.project([c.lngLat[0] + k, c.lngLat[1]]), path };
    });
    // 幾乎重疊的弧線（美國→歐洲各國）：雙劍沿各自弧線錯開；弧線太長框不下時，雙劍留在弧線可見的那一段（面板左側）
    const el = map.getContainer();
    const right = el.clientWidth - this.focusInset().right;
    const inside = (p: { x: number; y: number }) => p.x >= 20 && p.x <= right - 20 && p.y >= 20 && p.y <= el.clientHeight - 20 - this.focusInset().bottom;
    const pos = staggerOnArcs(raw, 34, 3, inside);
    this.placedConflicts.set(
      raw.map((r, i) => ({
        ...r.c,
        x: pos[i].x,
        y: pos[i].y,
        points: r.path ? r.path.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') : null,
      })),
    );
  }

  /**
   * 弧線留在畫面內（Tai 2026-10-31）：聚焦後鏡頭停下時，若有虛線弧（含雙劍）落在面板以外的可視區之外，
   * 改框「被選政權＋所有弧線」（弧線用目前的世界副本，跨換日線也連續）。每次聚焦／弧線組合只做一次；使用者自己移動過就不再動鏡頭。
   */
  private arcFitKey = '';
  protected readonly arcFit = signal(0);
  private fitArcs(): void {
    const map = this.map;
    if (!map || !this.focusedRecord() || this.userMoved || this.cameraMoving() || !this.focusBounds) return;
    const arcs = this.conflicts().filter((c) => c.arc?.length);
    if (!arcs.length) return;
    const key = `${this.focusKey}|${arcs.map((a) => a.recordId).join(',')}`;
    if (key === this.arcFitKey) return;
    this.arcFitKey = key;
    const el = map.getContainer();
    const w = el.clientWidth;
    const h = el.clientHeight;
    const pad = focusPadding(this.focusInset(), w, h);
    // 展開的圖例（左下角）會蓋住弧線端點（例：1941-12-08 日—英的哥打巴魯端）：左側留白加到圖例右緣，剩餘寬度不足才不讓
    const legend = document.querySelector('[data-testid="legend"][data-state="open"]')?.getBoundingClientRect();
    if (legend) {
      const box = el.getBoundingClientRect();
      const left = Math.round(legend.right - box.left + 16);
      if (legend.top - box.top < h && w - left - pad.right >= 200) pad.left = Math.max(pad.left, left);
    }
    // 參考經度：第一條弧線在被選政權那一端（不用目前畫面中心：美國這類跨換日線的政權聚焦後中心可能在 0 度）
    const a0 = arcs[0];
    const center = a0.focusEnd === 0 || a0.focusEnd === 1 ? a0.arc![a0.focusEnd === 0 ? 0 : a0.arc!.length - 1][0] : map.getCenter().lng;
    // 先框弧線（兩端分別在被選政權與對方領土內），下面再併入被選政權外框（跨換日線的大外框除外）
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    let inside = true;
    for (const c of arcs) {
      const k = worldShiftArc(c.arc!, center, c.focusEnd);
      for (const [x, y] of c.arc!) {
        const lng = x + k;
        x0 = Math.min(x0, lng);
        x1 = Math.max(x1, lng);
        y0 = Math.min(y0, y);
        y1 = Math.max(y1, y);
        const p = map.project([lng, y]);
        if (p.x < pad.left || p.x > w - pad.right || p.y < pad.top || p.y > h - pad.bottom) inside = false;
      }
    }
    // 被選政權本身也要完整入鏡（例：德國聚焦後框英德虛線弧時，德國不能被推到面板底下）。
    // 外框跨度 ≥ 180° 的政權（美國這類跨換日線、屬地把外框撐成全世界）不併入，維持只框弧線
    const fb = this.focusBounds as [[number, number], [number, number]];
    if (fb[1][0] - fb[0][0] < 180) {
      const k = Math.round((center - (fb[0][0] + fb[1][0]) / 2) / 360) * 360;
      for (const [lng, y] of [[fb[0][0] + k, fb[0][1]], [fb[1][0] + k, fb[1][1]], [fb[0][0] + k, fb[1][1]], [fb[1][0] + k, fb[0][1]]]) {
        x0 = Math.min(x0, lng);
        x1 = Math.max(x1, lng);
        y0 = Math.min(y0, y);
        y1 = Math.max(y1, y);
        const p = map.project([lng, y]);
        if (p.x < pad.left || p.x > w - pad.right || p.y < pad.top || p.y > h - pad.bottom) inside = false;
      }
    }
    if (inside) return;
    const cam = map.cameraForBounds([[x0, y0], [x1, y1]], { padding: pad, absolutePadding: true, maxZoom: 6 });
    if (!cam) return;
    this.arcFit.update((n) => n + 1);
    map.easeTo({ ...cam, duration: this.reducedMotion() ? 0 : 600, essential: false });
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
