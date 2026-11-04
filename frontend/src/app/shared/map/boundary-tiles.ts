import type { ExpressionSpecification, FilterSpecification, LayerSpecification } from 'maplibre-gl';
import { MAP_COLORS } from './map-style';
import { REGIME_FALLBACK_COLORS } from './sovereignty-style';

/**
 * 疆界向量圖磚（ARCHITECTURE.md §9，步驟 4：boundarySource=tiles）。
 * 圖磚 schema：`boundaries`（regime_id、start_day、end_day、color_idx、disputed、control_type）、
 * `labels`（regime_id、start_day、end_day、name_zh、name_local、area、span_x）；整數日從 1900-01-01 起算，end_day 不含當日。
 * span_x：該時期最大塊國土外框的經度寬（世界寬＝1），國名「裝得下才顯示」（§4 D9）用。
 * 換日期只呼叫 setFilter（而且只在跨越變動日時），不發任何請求。
 * 步驟 5：國名比照一般國名層（regime-label）的樣式與「名字寬度 vs 國土螢幕寬度」規則，文字用 API 的政權自稱（與 geojson 模式同一來源）。
 */
export const TILE_SOURCE = 'boundary-tiles';
export const TILE_FILL = 'tiles-fill';
export const TILE_LINE = 'tiles-line';
export const TILE_LINE_NOT_SOVEREIGN = 'tiles-line-not-sovereign';
export const TILE_LABEL = 'tiles-label';
export const TILE_LAYER_IDS = [TILE_FILL, TILE_LINE, TILE_LINE_NOT_SOVEREIGN, TILE_LABEL] as const;

/** 實際控制／主權檢視切換時的不透明度（常數，可做 transition；比照 AXIS_PAINT 的 sov-* 圖層）。 */
export const TILE_AXIS_PAINT: Record<'control' | 'sovereignty', [layer: string, prop: string, value: number][]> = {
  control: [[TILE_FILL, 'fill-opacity', 0.35], [TILE_LINE, 'line-opacity', 0.4], [TILE_LINE_NOT_SOVEREIGN, 'line-opacity', 0.45]],
  sovereignty: [[TILE_FILL, 'fill-opacity', 0.9], [TILE_LINE, 'line-opacity', 0.75], [TILE_LINE_NOT_SOVEREIGN, 'line-opacity', 0.8]],
};

/** start_day <= d AND end_day > d（與第 1 層 API valid_period @> d 相同）。 */
export function tileDateFilter(day: number): ExpressionSpecification {
  return ['all', ['<=', ['get', 'start_day'], day], ['>', ['get', 'end_day'], day]];
}

/** 各圖磚圖層在某日的 filter（國界線依 control_type 分實線／虛線）。 */
export function tileFilters(day: number): Record<typeof TILE_FILL | typeof TILE_LINE | typeof TILE_LINE_NOT_SOVEREIGN, FilterSpecification> {
  const when = tileDateFilter(day);
  const notSovereign: ExpressionSpecification = ['==', ['get', 'control_type'], 'not_sovereign'];
  return {
    [TILE_FILL]: when,
    [TILE_LINE]: ['all', when, ['!', notSovereign]],
    [TILE_LINE_NOT_SOVEREIGN]: ['all', when, notSovereign],
  };
}

/** 底色：已知政權依 slug 用前端色表（regimeColor）；其餘用圖磚的 color_idx 取後備色盤（與 regimeColor 的雜湊一致）。 */
export function tileFillColor(colorsByRegimeId: Record<string, string>): ExpressionSpecification {
  // color_idx 0..7 → 後備色盤（'at' 取 literal 陣列會被當成 array<string>，fill-color 不收，所以展開成 match）
  const fallback = ['match', ['get', 'color_idx'], ...REGIME_FALLBACK_COLORS.flatMap((c, i) => [i, c]), REGIME_FALLBACK_COLORS[0]] as unknown as ExpressionSpecification;
  const pairs = Object.entries(colorsByRegimeId).sort(([a], [b]) => a.localeCompare(b));
  if (pairs.length === 0) return fallback;
  return ['match', ['get', 'regime_id'], ...pairs.flat(), fallback] as unknown as ExpressionSpecification;
}

/** 世界寬（zoom 0）px，與 label-fit 的 WORLD_TILE_PX 相同。 */
const WORLD_PX = 512;

/**
 * 國名文字：依 regime_id 對到頁面給的名稱（API 自稱，regimeSelfName，與 geojson 模式相同）；
 * 名稱還沒載入或查不到的政權不標（與 geojson 模式「查不到名稱就不標」一致）。
 */
export function tileLabelText(namesByRegimeId: Record<string, string>): ExpressionSpecification {
  const pairs = Object.entries(namesByRegimeId).filter(([, t]) => t).sort(([a], [b]) => a.localeCompare(b));
  if (pairs.length === 0) return ['literal', ''] as unknown as ExpressionSpecification;
  return ['match', ['get', 'regime_id'], ...pairs.flat(), ''] as unknown as ExpressionSpecification;
}

/**
 * 國名 filter：當日有效 ∧ 名字裝得下（§4 D9：國土螢幕寬 span_x × 512 × 2^zoom ≥ 名字寬，等同 label-fit 的 labelMinZoom）
 * ∧ 不是被選政權（被選政權的名字改由蒙版上方的 HTML 層畫）。名字寬度（px）由頁面量好、依 regime_id 對應。
 */
export function tileLabelFilter(day: number, labelPxByRegimeId: Record<string, number>, selectedRegimeId: string | null = null): FilterSpecification {
  const pairs = Object.entries(labelPxByRegimeId).filter(([, px]) => px > 0).sort(([a], [b]) => a.localeCompare(b));
  if (pairs.length === 0) return ['boolean', false] as unknown as FilterSpecification;
  const px = ['match', ['get', 'regime_id'], ...pairs.flat(), 1e9];
  const minZoom = ['/', ['ln', ['/', px, ['*', ['max', ['coalesce', ['get', 'span_x'], 0], 1e-12], WORLD_PX]]], ['ln2']];
  const parts: unknown[] = [tileDateFilter(day), ['>=', ['zoom'], minZoom]];
  if (selectedRegimeId) parts.push(['!=', ['get', 'regime_id'], selectedRegimeId]);
  return ['all', ...parts] as unknown as FilterSpecification;
}

export interface TileLabelInput { names: Record<string, string>; labelPx: Record<string, number>; selectedRegimeId?: string | null }

export function boundaryTileLayers(day: number, colorsByRegimeId: Record<string, string>, label: TileLabelInput): LayerSpecification[] {
  const f = tileFilters(day);
  return [
    { id: TILE_FILL, type: 'fill', source: TILE_SOURCE, 'source-layer': 'boundaries', filter: f[TILE_FILL],
      paint: { 'fill-color': tileFillColor(colorsByRegimeId), 'fill-opacity': 0.9 } },
    { id: TILE_LINE, type: 'line', source: TILE_SOURCE, 'source-layer': 'boundaries', filter: f[TILE_LINE],
      paint: { 'line-color': MAP_COLORS.ink, 'line-width': 0.8, 'line-opacity': 0.75 } },
    { id: TILE_LINE_NOT_SOVEREIGN, type: 'line', source: TILE_SOURCE, 'source-layer': 'boundaries', filter: f[TILE_LINE_NOT_SOVEREIGN],
      paint: { 'line-color': MAP_COLORS.ink, 'line-width': 0.8, 'line-opacity': 0.8, 'line-dasharray': [3, 2] } },
    // 樣式比照 regime-label（底塊、字級、換行、可變錨點、光暈）；面積大的先放（area 供 symbol-sort-key，§9）
    { id: TILE_LABEL, type: 'symbol', source: TILE_SOURCE, 'source-layer': 'labels',
      filter: tileLabelFilter(day, label.labelPx, label.selectedRegimeId ?? null),
      layout: {
        'text-field': tileLabelText(label.names),
        'text-font': ['Open Sans Regular', 'Arial Unicode MS Regular'],
        'text-size': 12,
        'text-allow-overlap': false,
        'text-ignore-placement': false,
        'text-variable-anchor': ['center', 'top', 'bottom', 'left', 'right'],
        'text-radial-offset': 0.4,
        'text-justify': 'auto',
        'text-max-width': 10,
        'symbol-sort-key': ['-', 10000, ['ln', ['+', ['get', 'area'], 1]]],
        'icon-image': 'wl-regime-label-bg',
        'icon-text-fit': 'both',
        'icon-text-fit-padding': [2, 6, 2, 6],
        'icon-optional': true,
      },
      paint: { 'text-color': 'rgba(58,47,40,0.85)', 'text-halo-color': '#faf6ec', 'text-halo-width': 1.5, 'icon-opacity': 0.88 } },
  ];
}

/** 套用日期時只在跨越變動區間才 setFilter：回傳要套用的 filter，或 null（同一區間，不必動）。 */
export function tileFilterUpdate(prevKey: string | null, key: string, day: number): { key: string; filters: ReturnType<typeof tileFilters> } | null {
  return prevKey === key ? null : { key, filters: tileFilters(day) };
}

/**
 * 控制區、控制資料缺改走 overlay 圖磚（§9 步驟 5-5）：圖層 id、樣式、點選／hover／檢視軸程式都沿用 geojson 版，
 * 只把 source 換成 overlay 圖磚；圖磚只帶 versionId／gapId，原本 ['get', 屬性] 的地方換成「依 id 對到當日裝飾屬性」的 match，
 * filter 再加上「id 在當日清單內」。換日期（跨控制變動區間）只 setFilter／setPaintProperty，不發請求。
 */
export const OVERLAY_SOURCE = 'overlay-tiles';
export const OVERLAY_CONTROL_LAYERS = ['control-fill', 'control-hatch', 'control-regime-outline', 'control-line-solid', 'control-line-dotted', 'control-line-dashed', 'control-selected'] as const;
export const OVERLAY_GAP_LAYERS = ['gap-base', 'gap-fill', 'gap-line'] as const;
/** 這些圖層的 filter 由程式另外設定（被選控制區），換日期不覆蓋。 */
export const OVERLAY_KEEP_FILTER = new Set<string>(['control-selected']);

type Rows = ReadonlyMap<string, Readonly<Record<string, unknown>>>;

/** match 的預設值：用第一個值（型別一定合法，例如顏色）；反正 filter 只放清單內的 id，預設值不會被畫出來。 */
function defaultFor(values: unknown[]): unknown {
  return values.find((x) => x !== null && x !== undefined) ?? null;
}

/** 把運算式裡的 ['get', k]（k ≠ idKey）換成 ['match', ['get', idKey], id1, v1, …, 預設]；沒有資料時保留原樣（filter 為 false，不會畫）。 */
export function byIdExpr(expr: unknown, idKey: string, rows: Rows): unknown {
  if (!Array.isArray(expr)) return expr;
  if (expr[0] === 'get' && expr.length === 2 && typeof expr[1] === 'string' && expr[1] !== idKey) {
    const k = expr[1];
    const ids = [...rows.keys()].sort();
    const vals = ids.map((id) => rows.get(id)![k]);
    if (ids.length === 0) return expr;
    const def = defaultFor(vals);
    return ['match', ['get', idKey], ...ids.flatMap((id, i) => [id, vals[i] ?? def]), def];
  }
  if (expr[0] === 'literal') return expr;
  return expr.map((x) => byIdExpr(x, idKey, rows));
}

/** 當日 filter：id 在清單內 ∧ 原 filter（屬性換成 match）。清單空時什麼都不畫。 */
export function overlayFilter(orig: unknown, idKey: string, rows: Rows): FilterSpecification {
  const ids = [...rows.keys()].sort();
  if (ids.length === 0) return ['boolean', false] as unknown as FilterSpecification;
  const inList = ['in', ['get', idKey], ['literal', ids]];
  return (orig ? ['all', inList, byIdExpr(orig, idKey, rows)] : inList) as unknown as FilterSpecification;
}

/** paint 裡有用到 ['get', …] 的屬性（要依當日資料重設）。 */
export function dataDrivenPaint(paint: Record<string, unknown> | undefined): string[] {
  const uses = (e: unknown): boolean => Array.isArray(e) && (e[0] === 'get' || e.some(uses));
  return Object.entries(paint ?? {}).filter(([, v]) => uses(v)).map(([k]) => k);
}
