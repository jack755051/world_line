/**
 * 地圖標籤顯示規則（ARCHITECTURE.md §4，Tai 2026-11-03 D9）：
 * 名字寬度對比該國在畫面上的寬度——裝不下就不顯示，放大到裝得下才出現；首都用同一門檻。
 * 零國家特例：只看名字寬度與幾何外框。碰撞由 MapLibre 依 symbol-sort-key（面積）取捨。
 */

/** MapLibre 的世界寬度（zoom 0 時 512px）。 */
export const WORLD_TILE_PX = 512;

/** Web Mercator y（0～1，北為 0）。 */
export function mercatorY(lat: number): number {
  const l = Math.max(-85.05, Math.min(85.05, lat)) * Math.PI / 180;
  return (1 - Math.log(Math.tan(Math.PI / 4 + l / 2)) / Math.PI) / 2;
}

/**
 * 名字裝得進國土外框的最小縮放：國家螢幕寬度 = span × 512 × 2^z ≥ 名字寬度。
 * 旋轉的名字（沿狹長國家主軸）改用外框長邊。外框無效時回傳 Infinity（不顯示）。
 */
export function labelMinZoom(labelPx: number, bbox: [number, number, number, number], rotated = false): number {
  const xSpan = Math.abs(bbox[2] - bbox[0]) / 360;
  const ySpan = Math.abs(mercatorY(bbox[1]) - mercatorY(bbox[3]));
  const span = rotated ? Math.max(xSpan, ySpan) : xSpan;
  if (!(span > 0) || !(labelPx > 0)) return Infinity;
  return Math.log2(labelPx / (span * WORLD_TILE_PX));
}

/** 已知目前縮放下國家的螢幕寬度（px），換算名字的最小縮放（首都用；同一條規則）。 */
export function minZoomFromScreenWidth(labelPx: number, regimeWidthPx: number, zoom: number): number {
  if (!(regimeWidthPx > 0) || !(labelPx > 0)) return Infinity;
  return zoom + Math.log2(labelPx / regimeWidthPx);
}

export interface FitFeature {
  id: string;
  regimeId: string | null | undefined;
  minZoom: number;
}

/** 一般層要顯示的 id：目前縮放裝得下，且不是被選政權（被選政權改由蒙版上方的 HTML 層畫，避免重複）。 */
export function visibleIds(features: readonly FitFeature[], zoom: number, selectedRegimeId: string | null): string[] {
  const out: string[] = [];
  for (const f of features) {
    if (selectedRegimeId && f.regimeId === selectedRegimeId) continue;
    if (f.minZoom <= zoom + 1e-9) out.push(f.id);
  }
  return out;
}
