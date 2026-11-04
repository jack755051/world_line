import type { ExpressionSpecification, FilterSpecification, LayerSpecification } from 'maplibre-gl';
import type { Lang } from '../../core/i18n';
import { MAP_COLORS } from './map-style';
import { REGIME_FALLBACK_COLORS } from './sovereignty-style';

/**
 * 疆界向量圖磚（ARCHITECTURE.md §9，步驟 4：boundarySource=tiles）。
 * 圖磚 schema：`boundaries`（regime_id、start_day、end_day、color_idx、disputed、control_type）、
 * `labels`（regime_id、start_day、end_day、name_zh、name_local、area）；整數日從 1900-01-01 起算，end_day 不含當日。
 * 換日期只呼叫 setFilter（而且只在跨越變動日時），不發任何請求。
 * 步驟 4 只做底色、國界線、國名；佔領淡化色、非主權斜線、選取、蒙版、高亮、掃描動畫屬步驟 5。
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
export function tileFilters(day: number): Record<(typeof TILE_LAYER_IDS)[number], FilterSpecification> {
  const when = tileDateFilter(day);
  const notSovereign: ExpressionSpecification = ['==', ['get', 'control_type'], 'not_sovereign'];
  return {
    [TILE_FILL]: when,
    [TILE_LINE]: ['all', when, ['!', notSovereign]],
    [TILE_LINE_NOT_SOVEREIGN]: ['all', when, notSovereign],
    [TILE_LABEL]: when,
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

/** 國名：中文介面用 name_zh（沒有就原文），其他語言用原文（自稱）。 */
export function tileLabelText(lang: Lang): ExpressionSpecification {
  return lang === 'zh-Hant' ? ['coalesce', ['get', 'name_zh'], ['get', 'name_local']] : ['coalesce', ['get', 'name_local'], ['get', 'name_zh']];
}

export function boundaryTileLayers(day: number, colorsByRegimeId: Record<string, string>, lang: Lang): LayerSpecification[] {
  const f = tileFilters(day);
  return [
    { id: TILE_FILL, type: 'fill', source: TILE_SOURCE, 'source-layer': 'boundaries', filter: f[TILE_FILL],
      paint: { 'fill-color': tileFillColor(colorsByRegimeId), 'fill-opacity': 0.9 } },
    { id: TILE_LINE, type: 'line', source: TILE_SOURCE, 'source-layer': 'boundaries', filter: f[TILE_LINE],
      paint: { 'line-color': MAP_COLORS.ink, 'line-width': 0.8, 'line-opacity': 0.75 } },
    { id: TILE_LINE_NOT_SOVEREIGN, type: 'line', source: TILE_SOURCE, 'source-layer': 'boundaries', filter: f[TILE_LINE_NOT_SOVEREIGN],
      paint: { 'line-color': MAP_COLORS.ink, 'line-width': 0.8, 'line-opacity': 0.8, 'line-dasharray': [3, 2] } },
    { id: TILE_LABEL, type: 'symbol', source: TILE_SOURCE, 'source-layer': 'labels', filter: f[TILE_LABEL],
      layout: {
        'text-field': tileLabelText(lang),
        'text-font': ['Open Sans Regular', 'Arial Unicode MS Regular'],
        'text-size': 12,
        'text-max-width': 8,
        // 面積大的先放（§9：area 供 symbol-sort-key）
        'symbol-sort-key': ['-', 0, ['get', 'area']],
        'text-allow-overlap': false,
      },
      paint: { 'text-color': MAP_COLORS.ink, 'text-halo-color': '#ffffff', 'text-halo-width': 1.2 } },
  ];
}

/** 套用日期時只在跨越變動區間才 setFilter：回傳要套用的 filter，或 null（同一區間，不必動）。 */
export function tileFilterUpdate(prevKey: string | null, key: string, day: number): { key: string; filters: ReturnType<typeof tileFilters> } | null {
  return prevKey === key ? null : { key, filters: tileFilters(day) };
}
