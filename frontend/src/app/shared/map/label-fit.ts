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

/** 門檻上限：外框無效或找不到所在國時用（GeoJSON 屬性不放 Infinity）。 */
export const NEVER_ZOOM = 99;

/** 屬性用的最小縮放（Infinity／NaN → NEVER_ZOOM）。 */
export function clampMinZoom(z: number): number {
  return Number.isFinite(z) ? Math.min(z, NEVER_ZOOM) : NEVER_ZOOM;
}

/**
 * 一般層（GL）的 filter：目前縮放裝得下才顯示（['zoom'] 由 MapLibre 在 worker 依圖磚縮放評估，不必每次縮放 setFilter），
 * 並排除被選政權（它改由蒙版上方的 HTML 層畫，避免重複）。
 */
/**
 * 首都名 filter：沒有被選政權時同 labelFilterExpr；有被選政權時一般層的首都名全部不畫（被選政權的首都由 HTML 層畫），
 * 其他政權的首都名會跨在聚焦蒙版挖空邊緣，一半清楚一半模糊（例：1024 寬選德國時的考納斯）；圓點照常保留。
 */
export function capitalLabelFilterExpr(selectedRegimeId: string | null): unknown[] {
  return selectedRegimeId ? ['boolean', false] : labelFilterExpr(null);
}

export function labelFilterExpr(selectedRegimeId: string | null): unknown[] {
  const fits = ['>=', ['zoom'], ['coalesce', ['get', 'minZoom'], NEVER_ZOOM]];
  if (!selectedRegimeId) return fits;
  return ['all', fits, ['!=', ['coalesce', ['get', 'regimeId'], ''], selectedRegimeId]];
}
