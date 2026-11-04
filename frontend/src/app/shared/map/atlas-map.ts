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
import type { FeatureCollection, Geometry, Point as GeoJSONPoint, Position } from 'geojson';
import type { GeoJSONSource, GeoJSONSourceDiff, Map as MlMap, MapLayerMouseEvent, StyleSpecification, LayerSpecification } from 'maplibre-gl';
import { captureMapCanvas } from './scan-snapshot';
import { gapDotsImage, hatchImage, patternIds } from './hatch';
import { GAP_IMAGE_ID, GAP_STYLE, MAP_COLORS, type ControlLabel, type DecoratedProps, type GapProps } from './map-style';
import { AtlasState, type Axis } from '../../core/atlas-state';
import { AXIS_TRANSITION_MS } from '../../core/motion';
import { focusMaskPath, focusPadding, geometryBounds, measuredPadding, polygonRings, type FocusInset, type LngLatBounds, type Padding } from './focus';
import type { LngLat, PaddingOptions } from 'maplibre-gl';
import {
  measureLabelWidth,
  uiObstacleBoxes,
  pickCapitalAnchorSide, pointInProjectedRing,
  type Box,
} from './label-placement';
import { clampMinZoom, labelFilterExpr, labelMinZoom, minZoomFromScreenWidth, NEVER_ZOOM } from './label-fit';
import { geometryPieces, labelBoxPx, placeInViewport, toWorld, type Piece, type Rect } from './viewport-label';
import { byIdExpr, dataDrivenPaint, overlayFilter, OVERLAY_CONTROL_LAYERS, OVERLAY_GAP_LAYERS, OVERLAY_KEEP_FILTER, OVERLAY_SOURCE } from './boundary-tiles';
import { boundaryTileLayers, tileDateFilter, tileFillColor, tileHatchBase, tileHatchPattern, TILE_HATCH, TILE_HATCH_BASE, tileFilterUpdate, tileLabelFilter, tileLabelText, TILE_AXIS_PAINT, TILE_FILL, TILE_LABEL, TILE_SOURCE } from './boundary-tiles';
import { dayNumber, readOverlayTilesUrl, readTilesUrl, type BoundarySource } from '../../core/boundary-source';
import { intervalKey } from '../../core/change-points';

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

export const REGIME_LABEL_BG_ID = 'wl-regime-label-bg';
export const REGIME_OBSTACLE_ICON_ID = 'wl-obstacle-icon';
/** 障礙格：24px 方塊無縫鋪滿 UI 框（誤差 ≤ 半格），不讓障礙比 UI 大太多。 */
export const REGIME_OBSTACLE_ICON_SIZE = 24;
const OBSTACLE_GRID_STEP = REGIME_OBSTACLE_ICON_SIZE;

/** 政權名稱標籤排序鍵：數值越小越優先。控制區標籤（fit 未設）比國名標籤優先；同類中依 bbox 面積降序。 */
export function regimeLabelSortKey(bbox: [number, number, number, number], fit?: number): number {
  const area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]);
  const tier = fit === undefined ? 0 : 10000;
  return tier - Math.log(area + 1);
}

/** 首都名選邊：偏好側優先、碰撞時翻到另一側（MapLibre text-variable-anchor-offset，資料驅動）。 */
export const CAPITAL_ANCHOR_OFFSET = [
  'match', ['get', 'side'],
  'left', ['literal', ['right', [-0.9, 0], 'left', [0.9, 0]]],
  ['literal', ['left', [0.9, 0], 'right', [-0.9, 0]]],
];

/** 國名依視窗定位：moveend 後去抖動時間與畫面邊距（px）。 */
export const VIEWPORT_LABEL_DEBOUNCE_MS = 80;
/** MapLibre 符號淡入淡出時間（ms）。 */
export const SYMBOL_FADE_MS = 100;
export const VIEWPORT_LABEL_MARGIN_PX = 8;
/** 國名框高度（px，含底塊）：polylabel 依名字框長寬比定位用。 */
export const VIEWPORT_LABEL_HEIGHT_PX = 20;
/** regime-label 的字級、text-max-width（em）與行高（px）：視窗定位依此算實際行數。 */
export const REGIME_LABEL_TEXT_SIZE = 12;
export const REGIME_LABEL_MAX_WIDTH_EM = 10;
export const REGIME_LABEL_LINE_PX = 15;
/** 畫面邊障礙列：中心在畫面外 EDGE_OBSTACLE_OUTSIDE_PX，往內只蓋 OBSTACLE_GRID_STEP/2 − 8 = 4px（§4 (c)-6）。 */
export const EDGE_OBSTACLE_OUTSIDE_PX = 8;

/** 畫面四邊外緣的障礙框（容器座標，中心＋寬高）：名字一碰到邊就和障礙相撞。 */
export function edgeObstacleBoxes(w: number, h: number): Box[] {
  const t = OBSTACLE_GRID_STEP, o = EDGE_OBSTACLE_OUTSIDE_PX;
  return [
    { x: w / 2, y: -o, w: w + 2 * t, h: t },
    { x: w / 2, y: h + o, w: w + 2 * t, h: t },
    { x: -o, y: h / 2, w: t, h: h + 2 * t },
    { x: w + o, y: h / 2, w: t, h: h + 2 * t },
  ];
}

/** 兩次視窗定位結果是否不同（門檻或位置）。 */
export function placeChanged(
  a: ReadonlyMap<string, { lngLat: [number, number]; minZoom: number }>,
  b: ReadonlyMap<string, { lngLat: [number, number]; minZoom: number }>,
): boolean {
  if (a.size !== b.size) return true;
  for (const [k, v] of b) {
    const o = a.get(k);
    if (!o || o.minZoom !== v.minZoom || o.lngLat[0] !== v.lngLat[0] || o.lngLat[1] !== v.lngLat[1]) return true;
  }
  return false;
}

/** 政權名稱標籤的 GeoJSON FeatureCollection（Point，供 regime-labels source 使用）。 */
export function buildRegimeLabelFeatureCollection(
  labels: ControlLabel[],
  place?: ReadonlyMap<string, { lngLat: [number, number]; minZoom: number }>,
): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: labels.map((l) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: place?.get(l.versionId)?.lngLat ?? l.lngLat },
      properties: {
        versionId: l.versionId,
        regimeId: l.regimeId,
        text: l.text,
        rotation: l.rotation ?? 0,
        sortKey: regimeLabelSortKey(l.bbox, l.fit),
        // 名字寬度 vs 國家螢幕寬度（ARCHITECTURE.md §4 (c)、D9）：裝不下的縮放不顯示
        // 國名依視窗定位（§4 (c)-5）：有可見塊結果就用它（裝得下 -1、裝不下 99）
        minZoom: place?.get(l.versionId)?.minZoom ?? clampMinZoom(labelMinZoom(measureLabelWidth(l.text, false), l.bbox, !!l.rotation)),
      },
    })),
  };
}

/** 政權名稱標籤底塊圖像資料（圓角矩形，RGBA Uint8Array，40×24 px，含 3px 圓角）。 */
export function buildRegimeLabelBgImageData(): { data: Uint8Array; width: number; height: number } {
  const W = 40, H = 24, R = 3;
  const arr = new Uint8Array(W * H * 4);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      let inside = true;
      const inTL = x < R && y < R, inTR = x >= W - R && y < R;
      const inBL = x < R && y >= H - R, inBR = x >= W - R && y >= H - R;
      if (inTL) inside = Math.hypot(x - R + 1, y - R + 1) <= R;
      else if (inTR) inside = Math.hypot(x - (W - R), y - R + 1) <= R;
      else if (inBL) inside = Math.hypot(x - R + 1, y - (H - R)) <= R;
      else if (inBR) inside = Math.hypot(x - (W - R), y - (H - R)) <= R;
      if (inside) {
        const idx = (y * W + x) * 4;
        arr[idx] = 250; arr[idx + 1] = 246; arr[idx + 2] = 236; arr[idx + 3] = 224;
      }
    }
  }
  return { data: arr, width: W, height: H };
}

/** UI 障礙框轉成 GeoJSON 障礙符號 features（regime-obstacles source 用）。 */
export function obstacleGridFeatures(
  boxes: Box[],
  unproject: (px: [number, number]) => [number, number],
): { type: 'Feature'; geometry: { type: 'Point'; coordinates: number[] }; properties: Record<string, never> }[] {
  const features: { type: 'Feature'; geometry: { type: 'Point'; coordinates: number[] }; properties: Record<string, never> }[] = [];
  for (const box of boxes) {
    const x0 = box.x - box.w / 2;
    const y0 = box.y - box.h / 2;
    const cols = Math.max(1, Math.ceil(box.w / OBSTACLE_GRID_STEP));
    const rows = Math.max(1, Math.ceil(box.h / OBSTACLE_GRID_STEP));
    const half = OBSTACLE_GRID_STEP / 2;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        try {
          const coords = unproject([x0 + half + c * OBSTACLE_GRID_STEP, y0 + half + r * OBSTACLE_GRID_STEP]);
          features.push({ type: 'Feature', geometry: { type: 'Point', coordinates: coords }, properties: {} as Record<string, never> });
        } catch { /* skip */ }
      }
    }
  }
  return features;
}

export interface MapGapEvent {
  gapId: string;
  x: number;
  y: number;
}

/** 點主權圖層（國界）上的國家。 */
export interface MapSovereigntyEvent {
  recordId: string;
  /**
   * tiles 模式：點到的圖磚只帶 regime_id（recordId 為空字串）；同一政權同一天只有一筆主權紀錄（DB EXCLUDE），
   * 頁面取得被選政權幾何後再對回 recordId。圖磚不放 record_id（每塊都帶 UUID 會讓 PMTiles 大約 40%）。
   */
  regimeId?: string;
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
    glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
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
      capitals: { type: 'geojson', data: EMPTY },
      'regime-labels': { type: 'geojson', data: EMPTY },
      'regime-obstacles': { type: 'geojson', data: EMPTY },
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
      {
        id: 'regime-label',
        type: 'symbol',
        source: 'regime-labels',
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        filter: labelFilterExpr(null) as any,
        layout: {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          'text-field': ['get', 'text'] as any,
          'text-font': ['Open Sans Regular', 'Arial Unicode MS Regular'],
          'text-size': REGIME_LABEL_TEXT_SIZE,
          'text-allow-overlap': false,
          'text-ignore-placement': false,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          'text-variable-anchor': ['center', 'top', 'bottom', 'left', 'right'] as any,
          'text-radial-offset': 0.4,
          'text-justify': 'auto',
          'text-max-width': REGIME_LABEL_MAX_WIDTH_EM,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          'symbol-sort-key': ['get', 'sortKey'] as any,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          'text-rotate': ['get', 'rotation'] as any,
          'icon-image': REGIME_LABEL_BG_ID,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          'icon-text-fit': 'both' as any,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          'icon-text-fit-padding': [2, 6, 2, 6] as any,
          'icon-optional': true,
        },
        paint: {
          'text-color': 'rgba(58,47,40,0.85)',
          'text-halo-color': '#faf6ec',
          'text-halo-width': 1.5,
          'icon-opacity': 0.88,
        },
      },
      {
        id: 'regime-label-obstacles',
        type: 'symbol',
        source: 'regime-obstacles',
        layout: {
          'icon-image': REGIME_OBSTACLE_ICON_ID,
          'icon-allow-overlap': true,
          'icon-ignore-placement': false,
        },
        paint: {
          'icon-opacity': 0,
        },
      },
      {
        // 首都小圓點：深色實心＋白色外框，始終顯示
        id: 'capital-dot',
        type: 'circle',
        source: 'capitals',
        paint: {
          'circle-radius': 3.5,
          'circle-color': '#2d2a24',
          'circle-stroke-color': '#faf6ec',
          'circle-stroke-width': 1.5,
        },
      },
      {
        // 首都名稱：與國名同一條規則（名字寬度 vs 所在國螢幕寬度，ARCHITECTURE.md D9），由 applyLabelFilters 設 filter
        id: 'capital-label',
        type: 'symbol',
        source: 'capitals',
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        filter: labelFilterExpr(null) as any,
        layout: {
          'text-field': ['get', 'label'],
          'text-font': ['Open Sans Regular', 'Arial Unicode MS Regular'],
          'text-size': 11,
          // data-driven 選邊＋碰撞時翻邊（§4 (c)-6）：text-variable-anchor-offset 依序嘗試「偏好側 → 另一側」，
          // 兩側都撞（含畫面邊障礙列）就隱藏名字（text-optional，圓點保留）。
          // side='right' → 先試圓點右側（anchor 'left'），再試左側；side='left' 相反；未設 → 右側優先
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          'text-variable-anchor-offset': CAPITAL_ANCHOR_OFFSET as any,
          'text-justify': 'auto',
          'text-optional': true,
          'text-max-width': 8,
        },
        paint: {
          'text-color': '#2d2a24',
          'text-halo-color': '#faf6ec',
          'text-halo-width': 1.5,
        },
      },
    ],
  };
}

/** 地圖上的一個衝突圖示（經緯度＝兩國交界的代表點，來自 API）。 */
export interface MapConflictIcon {
  recordId: string;
  lngLat: [number, number];
  label: string;
  /** 遠距交戰虛線弧（雙方不相鄰時才有；lngLat 此時是弧線中點），見 conflict-arc.ts */
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
    <!--
      聚焦遮罩（Tai 2026-10-31）：點政權後，被選政權以外蓋一層半透明紙色＋backdrop-filter 模糊。
      用一個 HTML 層＋clip-path: path(evenodd, 地圖區矩形＋政權各環) 挖空被選政權：只需一次 GPU 模糊、不必複製地圖，
      地圖移動時（含飛行過場）每幀重算路徑（投影後距離 < 1px 的點略過）。pointer-events: none，不擋地圖點擊。
    -->
    <div #focusMask data-testid="map-focus-mask" aria-hidden="true" [attr.data-active]="focusedRecord() ? 'true' : 'false'"
      class="pointer-events-none absolute inset-0 bg-[rgb(236_228_210/0.42)] backdrop-blur-[3px] transition-opacity duration-200 motion-reduce:transition-none"
      [class.opacity-0]="!focusedRecord()" [class.invisible]="!focusedRecord() && !maskFading()"></div>
    <!--
      被選政權的名字（ARCHITECTURE.md §4 (b)、D2）：畫在聚焦蒙版之上的 HTML 層，一定顯示、不被模糊；
      一般層（GL）同政權的國名與首都用 filter 隱藏避免重複；這些框也加進障礙符號，讓其他標籤讓開。
    -->
    <div data-testid="map-selected-labels" class="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      @for (l of selectedPlaced(); track l.key) {
        @if (l.kind === 'regime') {
          <div data-testid="map-selected-label" data-kind="regime" class="absolute whitespace-nowrap rounded-[3px] bg-[rgb(250_246_236/0.92)] px-1.5 text-[13px] font-semibold leading-[20px] text-[rgb(45_42_36)] shadow-[0_0_0_1px_rgb(45_42_36/0.25)]"
            [style.left.px]="l.x" [style.top.px]="l.y" [style.transform]="'translate(-50%, -50%) rotate(' + l.rotation + 'deg)'">{{ l.text }}</div>
        } @else {
          <div data-testid="map-selected-label" data-kind="capital" class="absolute flex items-center gap-1 whitespace-nowrap text-[11px] leading-[16px] text-[rgb(45_42_36)]"
            [style.left.px]="l.x" [style.top.px]="l.y" [style.transform]="l.side === 'left' ? 'translate(calc(-100% + 5px), -50%)' : 'translate(-5px, -50%)'"
            [class.flex-row-reverse]="l.side === 'left'">
            <span class="inline-block size-[10px] shrink-0 rounded-full border-[1.5px] border-[#faf6ec] bg-[#2d2a24]"></span>
            <span class="rounded-[3px] bg-[rgb(250_246_236/0.92)] px-1">{{ l.text }}</span>
          </div>
        }
      }
    </div>
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
  /** 疆界來源（§9 步驟 4）：tiles 時國界、國名改由向量圖磚畫，換日期只改 filter。 */
  readonly boundarySource = input<BoundarySource>('geojson');
  /** tiles 模式主權圖層的日期相關樣式（佔領區斜線底色／斜線色、陣營外框色），依 regime_id。 */
  readonly tileSovPaint = input<{ base: Record<string, string>; hatch: Record<string, string>; camp: Record<string, string> }>({ base: {}, hatch: {}, camp: {} });
  /** 目前日期（tiles 模式的 filter 用）。 */
  readonly date = input<string | null>(null);
  /** 變動點（tiles 模式：同一變動區間內換日期不重設 filter）。 */
  readonly changePoints = input<readonly string[] | null>(null);
  /** 已知政權的填色（regimeId → 色），tiles 模式覆寫 color_idx 後備色。 */
  readonly regimeColors = input<Record<string, string>>({});
  /** tiles 模式：國名（regimeId → API 自稱，已依語系選好；與 geojson 模式的 sovereigntyLabels 同一來源）。 */
  readonly regimeNames = input<Record<string, string>>({});
  /** tiles 模式：已載入圖磚裡出現的政權 id（新出現時才發），頁面據此補載政權資料（顏色、名稱）。 */
  readonly tileRegimeIds = output<string[]>();
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
  /** 鏡頭聚焦 bounds override（控制區點擊時傳入該控制區 bbox；主權／清除時為 null）。 */
  readonly focusFitBounds = input<LngLatBounds | null>(null);
  protected readonly focusedRecord = signal<string | null>(null);
  /** 被選政權的 regimeId（聚焦時）；一般層排除它、HTML 層畫它。 */
  private focusRegimeId: string | null = null;
  /** 國名依視窗定位（§4 (c)-5）：主權紀錄 → 世界座標多塊國土（紀錄只撤回不改幾何，可長期快取）。 */
  private readonly sovPieces = new Map<string, Piece[]>();
  private sovGeomSrc: unknown = null;
  private sovGeomById = new Map<string, Geometry>();
  /** versionId → 目前視窗下的國名點與顯示門檻 */
  private viewportPlace = new Map<string, { lngLat: [number, number]; minZoom: number; areaPx?: number }>();
  private viewportTimer: ReturnType<typeof setTimeout> | undefined;
  protected readonly selectedPlaced = signal<{ key: string; kind: 'regime' | 'capital'; text: string; x: number; y: number; rotation: number; side: 'left' | 'right' }[]>([]);
  /** 聚焦時一起挖亮的佔領區數（聚焦政權是佔領方） */
  protected readonly focusOccupied = signal(0);
  protected readonly maskFading = signal(false);
  protected readonly cameraMoving = signal(false);
  private readonly focusMask = viewChild<ElementRef<HTMLDivElement>>('focusMask');
  private focusRings: Position[][] = [];
  private focusKey = '';
  private focusBounds: unknown = null;
  /** 目前聚焦由 focusFitBounds override（控制區 bbox）觸發時為 true；此時 fitArcs 不重移鏡頭。 */
  private focusHasOverride = false;
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
  /** 首都 GeoJSON（label 屬性已依語系選好）；null = 不顯示。 */
  readonly capitals = input<FeatureCollection | null>(null);
  protected readonly placedConflicts = signal<(MapConflictIcon & { x: number; y: number; points: string | null })[]>([]);
  readonly conflictClick = output<MapConflictEvent>();

  readonly featureClick = output<MapFeatureEvent>();
  readonly emptyClick = output<void>();
  readonly gapClick = output<MapGapEvent>();
  readonly sovereigntyClick = output<MapSovereigntyEvent>();
  readonly featureHover = output<MapFeatureEvent | null>();
  /** MapLibre 還在載入／切片 source（setData 後或平移到新區域）：true；畫面 idle 後 false。 */
  readonly renderBusy = output<boolean>();
  /** 使用者手動拖曳或縮放地圖（originalEvent 存在）時發出；程式化移動（easeTo 等）不發出。 */
  readonly userMove = output<void>();
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
  private tileFilterKey: string | null = null;
  /** tiles 模式目前套用的整數日。 */
  private tileDay = 0;
  /** tiles 模式：當日各政權最大塊國土的螢幕寬度基準（span_x，世界寬＝1），首都名門檻用；tileSpanDay＝收集時的整數日。 */
  private tileSpans = new Map<string, number>();
  private tileSpanDay: number | null = null;
  private readonly tileIdsSeen = new Set<string>();
  private readonly destroyRef = inject(DestroyRef);
  private readonly state = inject(AtlasState);
  /** 目前已推送進 sovereignty source 的 feature ID 集合（promoteId = recordId）。
   *  非空時改用 updateData() 差異更新，僅傳送增減的 feature，略過未變的幾何。 */
  private _sovIds = new Set<string>();
  /** 最後一次呼叫 setData/updateData 的時間點（performance.now()），供 setRenderBusy(false) 計算 worker+render 耗時。 */
  private _sovSetDataTs = 0;
  /** 注入 side 屬性後的首都 GeoJSON（供 capital-label data-driven 選邊使用）；null 表示尚未計算。 */
  private _enrichedCapitals: FeatureCollection | null = null;

  constructor() {
    afterNextRender(() => void this.init());
    this.destroyRef.onDestroy(() => {
      clearTimeout(this.axisTimer);
      clearTimeout(this.fadeTimer);
      clearTimeout(this.viewportTimer);
      cancelAnimationFrame(this.maskFrame);
      this._sovIds = new Set();
      this.map?.remove();
    });

    effect(() => {
      const d = this.date();
      const pts = this.changePoints();
      if (!this.ready() || this.boundarySource() !== 'tiles' || !d) return;
      // 掃描揭露（§9 步驟 5-4）：正在拍舊畫面快照時先不換 filter，拍完再換（否則快照拍到的已是新日期）
      untracked(() => (this.capturing ? void this.capturing.then(() => this.applyTileFilter(this.date() ?? d, this.changePoints())) : this.applyTileFilter(d, pts)));
    });
    effect(() => {
      const colors = this.regimeColors();
      if (!this.ready() || this.boundarySource() !== 'tiles') return;
      untracked(() => {
        if (!this.map?.getLayer(TILE_FILL)) return;
        this.map.setPaintProperty(TILE_FILL, 'fill-color', tileFillColor(colors));
        this.applyTileHatch();
      });
    });
    effect(() => {
      this.tileSovPaint();
      if (!this.ready() || this.boundarySource() !== 'tiles') return;
      untracked(() => this.applyTileHatch());
    });
    effect(() => {
      const names = this.regimeNames();
      if (!this.ready() || this.boundarySource() !== 'tiles') return;
      untracked(() => {
        if (!this.map?.getLayer(TILE_LABEL)) return;
        this.map.setLayoutProperty(TILE_LABEL, 'text-field', tileLabelText(names));
        this.applyTileLabelFilter(true);
      });
    });
    effect(() => {
      const data = this.collection();
      if (!this.ready()) return;
      untracked(() => this.setData(data));
    });
    effect(() => {
      this.labels();
      if (!this.ready()) return;
      untracked(() => {
        this.updateRegimeLabels();
        this.applyLabelFilters();
        this.placeSelectedLabels();
      });
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
      untracked(() => {
        (this.map?.getSource('gaps') as GeoJSONSource | undefined)?.setData(data ?? EMPTY);
        this.applyOverlayData();
      });
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
      const fitBounds = this.focusFitBounds();
      if (!this.ready()) return;
      untracked(() => this.applyFocus(id, fc, inset, reduced, fitBounds));
    });
    effect(() => {
      const id = this.selectedVersionId() ?? '';
      if (!this.ready()) return;
      this.map?.setFilter('control-selected', ['==', ['get', 'versionId'], id]);
    });
    effect(() => {
      const capitals = this.capitals();
      const sovereignty = this.sovereignty(); // 主權幾何改變時也需重算首都選邊
      if (!this.ready()) return;
      untracked(() => {
        this.computeAndApplyCapitalSides(capitals, sovereignty);
        this.applyLabelFilters();
        this.placeSelectedLabels();
      });
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
        // 符號碰撞淡入淡出：預設 300ms 會讓地圖晚約一個淡入週期才 idle（熱跳 ready 慢 ~255ms 的主因，2026-11-03 量測）
        fadeDuration: SYMBOL_FADE_MS,
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
        this.addRegimeLabelImages();
        this.setData(this.collection());
        this.updateRegimeLabels();
        this.updateObstacleSymbols();
        this.placeConflicts();
        (map.getSource('gaps') as GeoJSONSource | undefined)?.setData(this.gaps() ?? EMPTY);
        this.addHatch(GAP_IMAGE_ID);
        this.ensurePatterns(this.sovereignty());
        this.applySovereigntyData(this.sovereignty());
        map.setLayoutProperty('sov-camp-line', 'visibility', this.showCamps() ? 'visible' : 'none');
        this.applyAxis(this.axis(), 0);
        this.applyFocus(this.focusRecordId(), this.sovereignty(), this.focusInset(), this.reducedMotion(), this.focusFitBounds());
        this.computeAndApplyCapitalSides(this.capitals(), this.sovereignty());
        if (this.boundarySource() === 'tiles') this.addBoundaryTiles();
        // 確保首都圖層永遠在 GL style 最上層（任何後續 addLayer 都須用 beforeId 插在 capital-dot 之下）
        if (map.getLayer('capital-dot')) map.moveLayer('capital-dot');
        if (map.getLayer('capital-label')) map.moveLayer('capital-label');
        // 障礙符號放最上層：碰撞由上往下放置，障礙先佔位，首都與國名都會避開圖例、面板與被選政權名字
        if (map.getLayer('regime-label-obstacles')) map.moveLayer('regime-label-obstacles');
        this.applyLabelFilters();
      });
      map.on('movestart', (e) => {
        this.cameraMoving.set(true);
        if ((e as { originalEvent?: unknown }).originalEvent) {
          if (this.focusedRecord()) this.userMoved = true;
          this.userMove.emit();
        }
      });
      map.on('moveend', () => {
        this.cameraMoving.set(false);
        this.fitArcs();
        this.scheduleMask();
        this.updateObstacleSymbols();
        this.scheduleViewportLabels();
      });
      map.on('idle', () => {
        this.collectTileRegimeIds();
        this.countRendered();
        this.setRenderBusy(false);
      });
      map.on('dataloading', () => this.setRenderBusy(true));
      map.on('zoomend', () => this.state.mapZoom.set(map.getZoom()));
      map.on('move', () => {
        this.placeConflicts();
        this.placeSelectedLabels();
        this.scheduleMask();
      });
      map.on('resize', () => {
        this.placeConflicts();
        this.scheduleMask();
        this.updateObstacleSymbols();
      });

      // 圖例展開/收合、右側 sheet 開關時 data-state 屬性改變 → 重算障礙符號（UI 障礙框尺寸變了）
      const mutObs = new MutationObserver(() => this.updateObstacleSymbols());
      mutObs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-state'], subtree: true });
      this.destroyRef.onDestroy(() => mutObs.disconnect());

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
        // tiles 模式：國界在圖磚（tiles-fill），圖磚帶 regime_id
        const tile = !rec && map.getLayer(TILE_FILL) ? map.queryRenderedFeatures(e.point, { layers: [TILE_FILL, TILE_HATCH_BASE] })[0]?.properties : undefined;
        if (rec) this.sovereigntyClick.emit({ recordId: rec, x: e.point.x, y: e.point.y });
        else if (tile?.['regime_id']) this.sovereigntyClick.emit({ recordId: '', regimeId: String(tile['regime_id']), x: e.point.x, y: e.point.y });
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
      map.on('click', 'regime-label', (e: MapLayerMouseEvent) => {
        const f = e.features?.[0];
        const versionId = f?.properties?.['versionId'] as string | undefined;
        // 主權層國名（versionId＝sov-<regimeId>）交給上面的通用 click（底下的 sov-fill 會開主權卡）；
        // 這裡若再送 featureClick，會把剛開的主權卡清掉（點國名沒反應）。
        if (versionId && !versionId.startsWith('sov-')) this.featureClick.emit({ versionId, x: e.point.x, y: e.point.y });
      });
      map.on('mouseenter', 'regime-label', () => { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', 'regime-label', () => { map.getCanvas().style.cursor = ''; });
    } catch {
      this.engineError.set(true);
    }
  }

  /**
   * 聚焦：飛到被選政權當前領土的外框、置於可見區中央（四周 48px，右側／下方再扣掉面板），最大縮放 6；
   * 換成別的政權時從目前視角接著飛，原視角只記第一次。取消聚焦時飛回原視角。減少動態時直接跳。
   */
  private applyFocus(id: string | null, fc: FeatureCollection<Geometry, SovereigntyProps> | null, inset: FocusInset, reduced: boolean, overrideBounds: LngLatBounds | null = null): void {
    const map = this.map;
    if (!map) return;
    const f = id ? fc?.features.find((x) => x.properties.recordId === id) : undefined;
    // 鏡頭 bounds：有 override（點控制區）時用控制區 bbox，否則用主權 feature 外框
    const cameraBounds = overrideBounds ?? (f ? geometryBounds(f.geometry) : null);
    const duration = reduced ? 0 : 800;
    if (!cameraBounds) {
      this.focusKey = '';   // 確保後續再點同一目標時能重新飛
      this.clearFocus(duration);
      return;
    }
    const overrideKey = overrideBounds ? `${overrideBounds[0][0]},${overrideBounds[0][1]},${overrideBounds[1][0]},${overrideBounds[1][1]}` : '';
    const key = `${id ?? ''}|${inset.right}|${inset.bottom}|${overrideKey}`;
    if (key === this.focusKey) return;
    this.focusKey = key;
    const el = map.getContainer();
    const padding = this.measurePadding(el, inset);
    if (!f) {
      // 控制國沒有主權紀錄：純飛鏡頭，不進入聚焦模式（不畫遮罩）
      const cam = map.cameraForBounds(cameraBounds, { padding, absolutePadding: true, maxZoom: 6 });
      if (cam) map.easeTo({ ...cam, duration, essential: false });
      return;
    }
    if (!this.savedCamera) {
      this.savedCamera = { center: map.getCenter(), zoom: map.getZoom(), padding: map.getPadding() };
      this.userMoved = false;
    }
    clearTimeout(this.fadeTimer);
    this.maskFading.set(false);
    // 聚焦佔領國（例：德國）時，它佔領／併入的地區一起挖亮（仍保留斜線，看得出不是本土）；遮罩仍用主權 feature，鏡頭改用控制區 bbox
    const occupied = fc?.features.filter((x) => x.properties.occupierRegimeId && x.properties.occupierRegimeId === f.properties.regimeId) ?? [];
    this.focusOccupied.set(occupied.length);
    this.focusRings = [f, ...occupied].flatMap((x) => polygonRings(x.geometry));
    this.focusedRecord.set(id);
    this.focusRegimeId = f.properties.regimeId ?? null;
    this.scheduleViewportLabels();
    this.applyLabelFilters();
    this.placeSelectedLabels();
    this.focusBounds = cameraBounds;
    this.focusHasOverride = overrideBounds != null;
    const cam = map.cameraForBounds(cameraBounds, { padding, absolutePadding: true, maxZoom: 6 });
    if (cam) map.easeTo({ ...cam, duration, essential: false });
    this.drawMask();
    if (duration === 0) queueMicrotask(() => this.fitArcs());
  }

  /** 量測圖例與 sheet 面板後計算實際 padding（在 easeTo 前呼叫）。 */
  private measurePadding(el: HTMLElement, inset: FocusInset): Padding {
    const w = el.clientWidth;
    const h = el.clientHeight;
    const base = focusPadding(inset, w, h);
    const box = el.getBoundingClientRect();
    // 量測展開的圖例（左下角）
    const legend = document.querySelector('[data-testid="legend"][data-state="open"]')?.getBoundingClientRect();
    const legendRight = legend ? legend.right - box.left : null;
    const legendInBounds = legend ? (legend.top - box.top) < h : false;
    // 量測 sheet 面板左緣到容器右緣距離（量不到則 null，由 measuredPadding 退回 inset.right）
    const sheetRect = document.querySelector('wl-regime-sheet [data-testid="regime-sheet"]')?.getBoundingClientRect();
    const sheetGap = sheetRect ? box.right - sheetRect.left : null;
    return measuredPadding(base, w, legendRight, legendInBounds, sheetGap);
  }

  private clearFocus(duration: number): void {
    const map = this.map;
    if (!map || !this.focusedRecord()) return;
    this.focusKey = '';
    this.arcFitKey = '';
    this.focusBounds = null;
    this.focusHasOverride = false;
    this.focusedRecord.set(null);
    this.focusRegimeId = null;
    this.scheduleViewportLabels();
    this.applyLabelFilters();
    this.placeSelectedLabels();
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
    this.applyOverlayData();
  }

  /** overlay 圖層原始樣式（geojson 版），換日期時依當日資料重算 filter／paint。 */
  private overlaySpecs = new Map<string, LayerSpecification>();
  /** tiles 模式（§9 步驟 5-5）：控制區、控制資料缺圖層換成 overlay 圖磚，id 不變。 */
  private addOverlayTiles(): void {
    const map = this.map;
    if (!map || map.getSource(OVERLAY_SOURCE)) return;
    map.addSource(OVERLAY_SOURCE, { type: 'vector', url: readOverlayTilesUrl() });
    const order = map.getStyle().layers.map((l) => l.id);
    for (const [ids, sourceLayer] of [[OVERLAY_CONTROL_LAYERS, 'control'], [OVERLAY_GAP_LAYERS, 'gaps']] as const) {
      for (const id of ids) {
        const spec = map.getStyle().layers.find((l) => l.id === id);
        if (!spec) continue;
        this.overlaySpecs.set(id, spec);
        const before = order.slice(order.indexOf(id) + 1).find((x) => map.getLayer(x));
        map.removeLayer(id);
        const { source: _s, ...rest } = spec as LayerSpecification & { source?: string };
        void _s;
        map.addLayer({ ...rest, source: OVERLAY_SOURCE, 'source-layer': sourceLayer, filter: ['boolean', false] } as LayerSpecification, before);
      }
    }
    this.applyOverlayData();
  }

  private applyOverlayData(): void {
    const map = this.map;
    if (!map?.getSource(OVERLAY_SOURCE)) return;
    const control = new Map((this.collection()?.features ?? []).map((f) => [f.properties.versionId, f.properties as unknown as Record<string, unknown>]));
    const gaps = new Map((this.gaps()?.features ?? []).map((f) => [f.properties.gapId, f.properties as unknown as Record<string, unknown>]));
    for (const [id, spec] of this.overlaySpecs) {
      if (!map.getLayer(id)) continue;
      const [idKey, rows] = id.startsWith('gap-') ? ['gapId', gaps] as const : ['versionId', control] as const;
      if (!OVERLAY_KEEP_FILTER.has(id)) map.setFilter(id, overlayFilter((spec as { filter?: unknown }).filter, idKey, rows));
      const paint = (spec as { paint?: Record<string, unknown> }).paint;
      for (const prop of dataDrivenPaint(paint)) map.setPaintProperty(id, prop as never, byIdExpr(paint![prop], idKey, rows) as never);
    }
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
      try { performance.measure('wl:sov:debounce',       'wl:sov:date-change',  'wl:sov:load-start'); } catch { /* 播放模式 debounce=0 時 date-change 可能缺 */ }
      try { performance.measure('wl:sov:cache-or-fetch', 'wl:sov:load-start',   'wl:sov:signal-set'); } catch { /* 首次載入前可能缺 load-start */ }
      try { performance.measure('wl:sov:fetch',          'wl:sov:fetch-start',  'wl:sov:fetch-end'); } catch { /* 快取命中時無 fetch marks */ }
      try { performance.measure('wl:sov:signal',         'wl:sov:fetch-end',    'wl:sov:signal-set'); } catch {}
      try { performance.measure('wl:sov:effect',         'wl:sov:signal-set',   'wl:sov:effect'); } catch {}
      try { performance.measure('wl:sov:setdata',        'wl:sov:effect',       'wl:sov:setdata'); } catch {}
      try { performance.measure('wl:sov:worker',         'wl:sov:setdata',      'wl:sov:idle'); } catch {}
      const ms = (name: string) => { const e = performance.getEntriesByName(name, 'measure')[0]; return e ? `${name.replace('wl:sov:', '')}=${Math.round(e.duration)}ms` : null; };
      const parts = ['debounce','cache-or-fetch','fetch','effect','setdata','worker'].map(n => ms(`wl:sov:${n}`)).filter(Boolean);
      console.log(`[wl:perf:sov] worker+render=${workerRenderMs}ms`, parts.join(' '));
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
    for (const [layer, prop, value] of [...AXIS_PAINT[axis], ...TILE_AXIS_PAINT[axis]]) {
      if (!map.getLayer(layer)) continue;
      setPaint(layer, `${prop}-transition`, { duration, delay: 0 });
      setPaint(layer, prop, value);
    }
    const setControl = (v: 'visible' | 'none') => CONTROL_ONLY_LAYERS.forEach((l) => map.getLayer(l) && map.setLayoutProperty(l, 'visibility', v));
    const done = () => {
      this.appliedAxis.set(axis);
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

  /**
   * 為每座首都計算名稱標籤優先側（right/left），將 side 屬性注入 GeoJSON 並推送至 capitals source。
   * 當 capitals 或 sovereignty（政權外環）改變時呼叫。
   * 策略：在目前 zoom 下以像素座標將政權外環投影，再用 pickCapitalAnchorSide 判斷哪側名稱框中心落在環內。
   * capitalObstacleBoxes 仍保留左右兩側障礙框（確保 HTML 國名標籤在兩側退路下均能避讓）。
   */
  private computeAndApplyCapitalSides(
    capitals: FeatureCollection | null,
    sovereignty: FeatureCollection<Geometry, SovereigntyProps> | null,
  ): void {
    const map = this.map;
    if (!map) return;

    if (!capitals?.features.length) {
      this._enrichedCapitals = null;
      (map.getSource('capitals') as GeoJSONSource | undefined)?.setData(EMPTY);
      return;
    }

    // 投影所有政權多邊形的外環（用於後續點在環內測試）
    const sovRings: ReadonlyArray<{ x: number; y: number }>[] = [];
    for (const sf of sovereignty?.features ?? []) {
      const g = sf.geometry;
      if (g.type === 'Polygon') {
        sovRings.push(g.coordinates[0].map(([lng, lat]) => map.project([lng, lat] as [number, number])));
      } else if (g.type === 'MultiPolygon') {
        for (const poly of g.coordinates) {
          sovRings.push(poly[0].map(([lng, lat]) => map.project([lng, lat] as [number, number])));
        }
      }
    }

    const mapCenterLng = map.getCenter().lng;

    const enriched: FeatureCollection = {
      type: 'FeatureCollection',
      features: capitals.features.map((f) => {
        if (f.geometry.type !== 'Point') {
          return { ...f, properties: { ...(f.properties ?? {}), side: 'right' } };
        }
        const coords = (f.geometry as GeoJSONPoint).coordinates;
        const rawLng = coords[0];
        const lat = coords[1];
        const k = Math.round((mapCenterLng - rawLng) / 360) * 360;
        const dotPx = map.project([rawLng + k, lat] as [number, number]);
        const label = ((f.properties as Record<string, unknown> | null)?.['label'] as string | undefined) ?? '';
        const labelW = measureLabelWidth(label, false);

        // 找包含此首都點的政權外環，依此決定優先側
        let side: 'right' | 'left' = 'right';
        // 所在國沒找到時無法比寬度 → 不顯示名字（圓點照常）
        let minZoom = 99;
        // tiles 模式：國界在圖磚裡（沒有完整多邊形），改用該政權當日最大塊國土的外框寬（圖磚 labels.span_x）比寬度；選邊用預設右側
        const span = this.boundarySource() === 'tiles' ? this.tileSpans.get(String((f.properties as Record<string, unknown> | null)?.['regimeId'] ?? '')) : undefined;
        if (span) minZoom = clampMinZoom(Math.log2((labelW + 10) / (span * 512)));
        for (const ring of span ? [] : sovRings) {
          if (pointInProjectedRing(dotPx.x, dotPx.y, ring)) {
            side = pickCapitalAnchorSide(dotPx, labelW, ring);
            let x0 = Infinity, x1 = -Infinity;
            for (const p of ring) { if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; }
            // 名字＋圓點間距（約 10px）要放得進所在國的螢幕寬度
            minZoom = clampMinZoom(minZoomFromScreenWidth(labelW + 10, x1 - x0, map.getZoom()));
            break;
          }
        }

        return { ...f, properties: { ...(f.properties ?? {}), side, minZoom } };
      }),
    };

    this._enrichedCapitals = enriched;
    (map.getSource('capitals') as GeoJSONSource | undefined)?.setData(enriched);
  }

  private addRegimeLabelImages(): void {
    const map = this.map;
    if (!map) return;
    if (!map.hasImage(REGIME_LABEL_BG_ID)) {
      const bg = buildRegimeLabelBgImageData();
      const R = 3;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (map as any).addImage(REGIME_LABEL_BG_ID, bg, {
        pixelRatio: 1,
        stretchX: [[R, bg.width - R]],
        stretchY: [[R, bg.height - R]],
        content: [R, R, bg.width - R, bg.height - R],
      });
    }
    if (!map.hasImage(REGIME_OBSTACLE_ICON_ID)) {
      const S = REGIME_OBSTACLE_ICON_SIZE;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (map as any).addImage(REGIME_OBSTACLE_ICON_ID,
        { data: new Uint8Array(S * S * 4).fill(255), width: S, height: S },
        { pixelRatio: 1 },
      );
    }
  }

  private updateRegimeLabels(): void {
    const src = this.map?.getSource('regime-labels') as GeoJSONSource | undefined;
    if (!src) return;
    this.viewportPlace = this.computeViewportPlace();
    src.setData(buildRegimeLabelFeatureCollection(this.labels(), this.viewportPlace));
  }

  private scheduleViewportLabels(): void {
    clearTimeout(this.viewportTimer);
    this.viewportTimer = setTimeout(() => this.refreshViewportLabels(), VIEWPORT_LABEL_DEBOUNCE_MS);
  }

  /** moveend 後（去抖動）重算國名位置；結果沒變就不 setData（避免重排符號）。 */
  private refreshViewportLabels(): void {
    const src = this.map?.getSource('regime-labels') as GeoJSONSource | undefined;
    if (!src || this.cameraMoving()) return;
    const next = this.computeViewportPlace();
    if (!placeChanged(this.viewportPlace, next)) return;
    this.viewportPlace = next;
    src.setData(buildRegimeLabelFeatureCollection(this.labels(), next));
    this.placeSelectedLabels();
  }

  /**
   * 國名依視窗定位（ARCHITECTURE.md §4 (c)-5，M1-g）：每個國名放在該政權目前可見國土中最大的一塊，
   * 位置用 polylabel（避開圖例／面板等 UI）；可見塊寬度裝不下名字就不顯示（被選政權例外，由 HTML 層畫）。
   */
  private computeViewportPlace(): Map<string, { lngLat: [number, number]; minZoom: number; areaPx?: number }> {
    const out = new Map<string, { lngLat: [number, number]; minZoom: number; areaPx?: number }>();
    const map = this.map;
    if (!map) return out;
    const fc = this.sovereignty();
    if (fc !== this.sovGeomSrc) {
      this.sovGeomSrc = fc;
      this.sovGeomById = new Map();
      for (const f of fc?.features ?? []) {
        const id = (f.properties as { recordId?: string } | null)?.recordId;
        if (id && f.geometry) this.sovGeomById.set(id, f.geometry as Geometry);
      }
    }
    const el = map.getContainer();
    const w = el.clientWidth, h = el.clientHeight;
    if (!w || !h) return out;
    const worldPx = 512 * 2 ** map.getZoom();
    const c = map.getCenter();
    const [cx, cy] = toWorld(c.lng, c.lat);
    const cp = map.project(c);
    const wx = (px: number) => cx + (px - cp.x) / worldPx;
    const wy = (py: number) => cy + (py - cp.y) / worldPx;
    const cr = el.getBoundingClientRect();
    const sheet = document.querySelector('wl-regime-sheet [data-testid="regime-sheet"]')?.getBoundingClientRect();
    const right = sheet && sheet.width > 0 && sheet.left < cr.right ? Math.min(w, sheet.left - cr.left) : w;
    const m = VIEWPORT_LABEL_MARGIN_PX;
    const view: Rect = [wx(m), wy(m), wx(right - m), wy(h - m)];
    const avoid: Rect[] = uiObstacleBoxes(el).map((b) => [wx(b.x - b.w / 2), wy(b.y - b.h / 2), wx(b.x + b.w / 2), wy(b.y + b.h / 2)]);
    const sel = this.focusRegimeId;
    // 被選政權的國名與首都都畫在 HTML 層（不經 GL 碰撞）：國名要避開自己的首都標籤
    const selAvoid: Rect[] = [];
    if (sel) {
      const near = (lng: number) => lng + Math.round((c.lng - lng) / 360) * 360;
      for (const f of this._enrichedCapitals?.features ?? []) {
        const pr = (f.properties ?? {}) as Record<string, unknown>;
        if (pr['regimeId'] !== sel || f.geometry.type !== 'Point') continue;
        const [lng, lat] = (f.geometry as GeoJSONPoint).coordinates;
        const p = map.project([near(lng), lat]);
        const tw = measureLabelWidth(String(pr['label'] ?? ''), false) + 10;
        const [x0, x1] = pr['side'] === 'left' ? [p.x - tw, p.x + 6] : [p.x - 6, p.x + tw];
        selAvoid.push([wx(x0), wy(p.y - 10), wx(x1), wy(p.y + 10)]);
      }
    }
    for (const l of this.labels()) {
      if (!l.versionId.startsWith('sov-')) continue;
      const rid = l.versionId.slice(4);
      let pieces = this.sovPieces.get(rid);
      if (!pieces) {
        const g = this.sovGeomById.get(rid);
        if (!g) continue;
        pieces = geometryPieces(g);
        if (this.sovPieces.size > 3000) this.sovPieces.delete(this.sovPieces.keys().next().value as string);
        this.sovPieces.set(rid, pieces);
      }
      const labelPx = measureLabelWidth(l.text, false);
      // 名字框依 GL 實際換行（text-max-width）算寬高：兩行名用兩行高（§4 (c)-6）
      const box = labelBoxPx(Math.max(0, labelPx - 12), REGIME_LABEL_MAX_WIDTH_EM * REGIME_LABEL_TEXT_SIZE, REGIME_LABEL_LINE_PX, { x: 6, y: 3 });
      const p = placeInViewport(pieces, view, worldPx, l.regimeId === sel && selAvoid.length ? [...avoid, ...selAvoid] : avoid, l.rotation ? undefined : { w: box.w, h: box.h });
      if (!p) { out.set(l.versionId, { lngLat: l.lngLat, minZoom: NEVER_ZOOM }); continue; }
      const span = l.rotation ? Math.max(p.widthPx, p.heightPx) : p.widthPx;
      const fits = p.clearPx > 0 && span >= labelPx;
      const lng = ((p.lngLat[0] + 540) % 360) - 180;
      out.set(l.versionId, { lngLat: [lng, p.lngLat[1]], minZoom: fits || l.regimeId === sel ? -1 : NEVER_ZOOM, areaPx: p.areaPx });
    }
    return out;
  }

  private updateObstacleSymbols(): void {
    const map = this.map;
    if (!map) return;
    const src = map.getSource('regime-obstacles') as GeoJSONSource | undefined;
    if (!src) return;
    const container = map.getContainer();
    // 畫面四邊障礙列（§4 (c)-6）＋圖例、面板等 UI
    const boxes = [...edgeObstacleBoxes(container.clientWidth, container.clientHeight), ...uiObstacleBoxes(container)];
    // 被選政權的名字（HTML 層）也是障礙：其他標籤要讓開
    const host = container.parentElement ?? container;
    const cr = container.getBoundingClientRect();
    host.querySelectorAll<HTMLElement>('[data-testid="map-selected-label"]').forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.width && r.height) boxes.push({ x: (r.left + r.right) / 2 - cr.left, y: (r.top + r.bottom) / 2 - cr.top, w: r.width + 4, h: r.height + 4 });
    });
    const features = obstacleGridFeatures(boxes, (px) => {
      const ll = map.unproject(px);
      return [ll.lng, ll.lat];
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    src.setData({ type: 'FeatureCollection', features } as any);
  }

  /**
   * 一般層 filter（ARCHITECTURE.md §4 (b)(c)）：縮放門檻寫在 filter 裡（['zoom']），只有選取政權改變時才 setFilter，
   * 把被選政權的國名、首都與圓點從一般層排除（改由 HTML 層畫）。
   */
  private appliedFilterSel: string | null | undefined = undefined;
  private applyLabelFilters(): void {
    const map = this.map;
    if (!map || !map.getLayer('regime-label')) return;
    const sel = this.focusRegimeId;
    if (sel === this.appliedFilterSel) return;
    this.appliedFilterSel = sel;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    map.setFilter('regime-label', labelFilterExpr(sel) as any);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    map.setFilter('capital-label', labelFilterExpr(sel) as any);
    map.setFilter('capital-dot', sel ? ['!=', ['coalesce', ['get', 'regimeId'], ''], sel] : null);
    this.applyTileLabelFilter();
  }

  /** 被選政權的國名（含它的控制區名稱）與首都：投影到螢幕座標，畫在蒙版上方；放好後更新障礙符號。 */
  private placeSelectedLabels(): void {
    const map = this.map;
    const sel = this.focusRegimeId;
    if (!map || !sel) {
      if (this.selectedPlaced().length) {
        this.selectedPlaced.set([]);
        requestAnimationFrame(() => this.updateObstacleSymbols());
      }
      return;
    }
    const center = map.getCenter().lng;
    const near = (lng: number) => lng + Math.round((center - lng) / 360) * 360;
    const out: { key: string; kind: 'regime' | 'capital'; text: string; x: number; y: number; rotation: number; side: 'left' | 'right' }[] = [];
    // 選取政權只顯示一個名字（§4 (c)-7）：國名標籤中可見塊最大的那個（M1-g 位置）；沒有國名標籤才退回第一個控制區名字
    const mine = this.labels().filter((l) => l.regimeId === sel);
    let one: ControlLabel | undefined;
    let bestArea = -1;
    for (const l of mine) {
      const vp = this.viewportPlace.get(l.versionId);
      if (!vp || vp.minZoom >= NEVER_ZOOM) continue;
      if ((vp.areaPx ?? 0) > bestArea) { bestArea = vp.areaPx ?? 0; one = l; }
    }
    if (!one && !mine.some((l) => l.versionId.startsWith('sov-'))) one = mine[0];
    for (const l of one ? [one] : []) {
      const vp = this.viewportPlace.get(l.versionId);
      const ll = vp?.lngLat ?? l.lngLat;
      const p = map.project([near(ll[0]), ll[1]]);
      out.push({ key: `r-${l.versionId}`, kind: 'regime', text: l.text, x: p.x, y: p.y, rotation: l.rotation ?? 0, side: 'right' });
    }
    for (const f of this._enrichedCapitals?.features ?? []) {
      const pr = (f.properties ?? {}) as Record<string, unknown>;
      if (pr['regimeId'] !== sel || f.geometry.type !== 'Point') continue;
      const [lng, lat] = (f.geometry as GeoJSONPoint).coordinates;
      const p = map.project([near(lng), lat]);
      out.push({ key: `c-${String(pr['recordId'])}`, kind: 'capital', text: String(pr['label'] ?? ''), x: p.x, y: p.y, rotation: 0, side: pr['side'] === 'left' ? 'left' : 'right' });
    }
    const wasEmpty = this.selectedPlaced().length === 0;
    this.selectedPlaced.set(out);
    // 第一次出現（或換政權）時，等 DOM 畫好再把框加進障礙；移動中由 moveend 更新
    if (wasEmpty || !this.cameraMoving()) requestAnimationFrame(() => this.updateObstacleSymbols());
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
    // 控制區聚焦（focusFitBounds override）時鏡頭已對準控制區，不再因弧線重移鏡頭；弧線照常顯示。
    if (this.focusHasOverride) return;
    if (!map || !this.focusedRecord() || this.userMoved || this.cameraMoving() || !this.focusBounds) return;
    const arcs = this.conflicts().filter((c) => c.arc?.length);
    if (!arcs.length) return;
    const key = `${this.focusKey}|${arcs.map((a) => a.recordId).join(',')}`;
    if (key === this.arcFitKey) return;
    this.arcFitKey = key;
    const el = map.getContainer();
    const w = el.clientWidth;
    const h = el.clientHeight;
    const pad = this.measurePadding(el, this.focusInset());
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

  /** tiles 模式：加入向量圖磚 source 與圖層（底色、國界線、非主權虛線放在缺口層之下；國名放在一般國名層之下）。 */
  private addBoundaryTiles(): void {
    const map = this.map;
    if (!map || map.getSource(TILE_SOURCE)) return;
    map.addSource(TILE_SOURCE, { type: 'vector', url: readTilesUrl(), attribution: '國界 Borders: OpenHistoricalMap contributors（CC0）等' });
    const d = this.date() ?? this.state.date();
    this.tileDay = dayNumber(d);
    const [fill, hatchBase, hatch, line, lineNs, label] = boundaryTileLayers(this.tileDay, this.regimeColors(), { names: this.regimeNames(), labelPx: this.tileLabelPx(), selectedRegimeId: this.focusRegimeId });
    for (const l of [fill, hatchBase, hatch, line, lineNs]) map.addLayer(l, 'gap-base');
    map.addLayer(label, 'regime-label');
    this.applyTileHatch();
    this.addOverlayTiles();
    this.tileFilterKey = intervalKey(this.changePoints(), d);
    map.on('mouseenter', TILE_FILL, () => (map.getCanvas().style.cursor = 'pointer'));
    map.on('mouseleave', TILE_FILL, () => (map.getCanvas().style.cursor = ''));
    // geojson 主權圖層在 tiles 模式下沒有資料；保持隱藏，避免與圖磚重疊
    for (const id of ['sov-fill', 'sov-hatch-base', 'sov-hatch', 'sov-line', 'sov-line-not-sovereign']) if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', 'none');
    map.on('mouseenter', TILE_HATCH, () => (map.getCanvas().style.cursor = 'pointer'));
    map.on('mouseleave', TILE_HATCH, () => (map.getCanvas().style.cursor = ''));
  }

  /** 非主權斜線（顏色跟著政權色；佔領區另外覆蓋）。 */
  private applyTileHatch(): void {
    if (!this.map?.getLayer(TILE_HATCH)) return;
    const sp = this.tileSovPaint();
    this.map.setPaintProperty(TILE_HATCH, 'fill-pattern', tileHatchPattern(this.regimeColors(), sp.hatch));
    // 佔領區著色：斜線底色改用佔領國色（依控制程度淡化），與 decorateSovereignty 的 wlBase 相同
    this.map.setPaintProperty(TILE_HATCH_BASE, 'fill-color', tileHatchBase(sp.base));
  }

  /** tiles 模式換日期：只在跨越變動區間時 setFilter，不發請求。 */
  /** 進行中的掃描快照（tiles 模式換 filter 要等它拍完）。 */
  private capturing: Promise<unknown> | null = null;
  private applyTileFilter(date: string, points: readonly string[] | null): void {
    const map = this.map;
    if (!map?.getLayer(TILE_FILL)) return;
    const up = tileFilterUpdate(this.tileFilterKey, intervalKey(points, date), dayNumber(date));
    if (!up) return;
    this.tileFilterKey = up.key;
    this.tileDay = dayNumber(date);
    performance.mark('wl:tiles:filter');
    for (const [layer, filter] of Object.entries(up.filters)) map.setFilter(layer, filter);
    this.applyTileLabelFilter(true);
    this.tileSpanDay = null; // 國土寬度（首都名門檻）換區間後重收
  }

  /** 名字寬度（px，與 geojson 國名同一量法）：依名稱字串快取。 */
  private tileLabelPx(): Record<string, number> {
    const out: Record<string, number> = {};
    for (const [id, t] of Object.entries(this.regimeNames())) if (t) out[id] = measureLabelWidth(t, false);
    return out;
  }

  /** tiles 國名 filter（日期、裝得下、排除被選政權）；names 變了才重量寬度。 */
  private tileLabelPxCache: Record<string, number> = {};
  private tileLabelSel: string | null | undefined = undefined;
  private applyTileLabelFilter(force = false): void {
    const map = this.map;
    if (!map?.getLayer(TILE_LABEL)) return;
    if (!force && this.tileLabelSel === this.focusRegimeId) return;
    if (force) this.tileLabelPxCache = this.tileLabelPx();
    this.tileLabelSel = this.focusRegimeId;
    map.setFilter(TILE_LABEL, tileLabelFilter(this.tileDay, this.tileLabelPxCache, this.focusRegimeId));
  }

  private collectTileRegimeIds(): void {
    const map = this.map;
    if (this.boundarySource() !== 'tiles' || !map?.getSource(TILE_SOURCE)) return;
    const fresh: string[] = [];
    const spans = new Map<string, number>();
    for (const f of map.querySourceFeatures(TILE_SOURCE, { sourceLayer: 'labels', filter: tileDateFilter(this.tileDay) })) {
      const id = f.properties?.['regime_id'] as string | undefined;
      if (!id) continue;
      if (!this.tileIdsSeen.has(id)) { this.tileIdsSeen.add(id); fresh.push(id); }
      const span = Number(f.properties?.['span_x'] ?? 0);
      if (span > (spans.get(id) ?? 0)) spans.set(id, span);
    }
    if (fresh.length) this.tileRegimeIds.emit(fresh);
    // 國土寬度變了（換區間或新圖磚進來）→ 重算首都名門檻
    let changed = this.tileSpanDay !== this.tileDay || spans.size !== this.tileSpans.size;
    if (!changed) for (const [k, v] of spans) if (this.tileSpans.get(k) !== v) { changed = true; break; }
    if (!changed) return;
    this.tileSpans = spans;
    this.tileSpanDay = this.tileDay;
    this.computeAndApplyCapitalSides(this.capitals(), this.sovereignty());
    this.applyLabelFilters();
    this.placeSelectedLabels();
  }

  private countRendered(): void {
    if (!this.map || !this.ready()) return;
    const n = this.map.queryRenderedFeatures({ layers: ['control-fill', 'control-hatch'] }).length;
    this.renderedCount.set(n);
    this.renderedGaps.set(this.map.queryRenderedFeatures({ layers: ['gap-fill'] }).length);
    const sovLayers = this.map.getLayer(TILE_FILL) ? [TILE_FILL, TILE_HATCH_BASE] : ['sov-fill', 'sov-hatch-base'];
    this.renderedSovereignty.set(this.map.queryRenderedFeatures({ layers: sovLayers }).length);
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

  /**
   * 拍下目前地圖畫面的快照，供跳年掃描揭露使用。
   * 回傳地圖 WebGL canvas 複本（含疆界、填色、MapLibre 標籤）與 HTML 政權標籤圖層複本。
   * 沒有 map 或 WebGL 時回傳 null（例：jsdom 測試環境）。
   */
  async captureSnapshot(): Promise<{ canvas: HTMLCanvasElement; labels: HTMLElement } | null> {
    if (!this.map || this.engineError()) return null;
    const p = captureMapCanvas(this.map);
    this.capturing = p;
    const canvas = await p.finally(() => { if (this.capturing === p) this.capturing = null; });
    if (!canvas) return null;
    // 標籤現在在 MapLibre canvas 內，不需要額外的 HTML 標籤快照
    return { canvas, labels: document.createElement('div') };
  }
}
