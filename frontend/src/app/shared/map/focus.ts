import type { Geometry, Position } from 'geojson';

/**
 * 政權聚焦（Tai 2026-10-31）：點政權 → 地圖移到該政權當前領土、置於可見區中央（扣掉側邊面板），
 * 其他地方蓋一層半透明紙色並模糊。這裡放純函式（好測），MapLibre 與 DOM 的部分在 atlas-map.ts。
 */
export type LngLatBounds = [[number, number], [number, number]];
export interface FocusInset {
  right: number;
  bottom: number;
}
export interface Padding {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

/** Polygon／MultiPolygon／GeometryCollection 的所有環（外環與內環都要，遮罩用 evenodd 處理洞）。 */
export function polygonRings(g: Geometry | null | undefined): Position[][] {
  if (!g) return [];
  switch (g.type) {
    case 'Polygon':
      return g.coordinates;
    case 'MultiPolygon':
      return g.coordinates.flat();
    case 'GeometryCollection':
      return g.geometries.flatMap((x) => polygonRings(x));
    default:
      return [];
  }
}

export function geometryBounds(g: Geometry | null | undefined): LngLatBounds | null {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const ring of polygonRings(g))
    for (const [x, y] of ring) {
      if (x < x0) x0 = x;
      if (y < y0) y0 = y;
      if (x > x1) x1 = x;
      if (y > y1) y1 = y;
    }
  return x0 <= x1 && y0 <= y1 ? [[x0, y0], [x1, y1]] : null;
}

/**
 * 遮罩的 clip-path：整個地圖區的矩形＋被選政權的各環，用 evenodd 挖空政權（洞與飛地也正確）。
 * 投影後相鄰點距離不到 minStep 像素就略過，降低每一幀的路徑長度。
 */
export function focusMaskPath(
  rings: Position[][],
  project: (p: [number, number]) => { x: number; y: number },
  w: number,
  h: number,
  minStep = 1,
): string {
  let d = `M0 0H${w}V${h}H0Z`;
  for (const ring of rings) {
    let s = '';
    let n = 0;
    let lx = NaN, ly = NaN;
    for (const c of ring) {
      const p = project([c[0], c[1]]);
      if (n > 0 && Math.abs(p.x - lx) < minStep && Math.abs(p.y - ly) < minStep) continue;
      s += `${n ? 'L' : 'M'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`;
      lx = p.x;
      ly = p.y;
      n++;
    }
    if (n >= 3) d += `${s}Z`;
  }
  return d;
}

/** 置中時的邊距：四周留 margin，右側（或下方）再扣掉面板；可見區至少留 minSize，不夠時縮小邊距。 */
export function focusPadding(inset: FocusInset, w: number, h: number, margin = 48, minSize = 120): Padding {
  const fit = (a: number, b: number, total: number): [number, number] => {
    const room = total - a - b;
    if (room >= minSize) return [a, b];
    const k = Math.max(0, total - minSize) / Math.max(1, a + b);
    return [Math.floor(a * k), Math.floor(b * k)];
  };
  const [left, right] = fit(margin, margin + inset.right, w);
  const [top, bottom] = fit(margin, margin + inset.bottom, h);
  return { top, right, bottom, left };
}

/**
 * 根據實際量測結果，在 focusPadding 基礎上調整左右邊距：
 * - 左側：若圖例已展開（legendRight 非 null）且頂部在容器高度範圍內，
 *   取 max(base.left, legendRight + 16)，但剩餘可見寬度仍需 ≥ 200。
 * - 右側：若量到 sheet 面板（sheetGap 非 null，即容器右緣 − sheet 左緣），
 *   取 max(base.right, sheetGap + margin)。
 */
export function measuredPadding(
  base: Padding,
  w: number,
  legendRight: number | null,   // 圖例右緣到容器左緣（px），null = 未展開
  legendInBounds: boolean,      // 圖例頂部在容器高度範圍內
  sheetGap: number | null,      // 容器右緣 − sheet 左緣（px），null = 量不到
  margin = 48,
): Padding {
  let { left, right } = base;
  if (legendRight !== null && legendInBounds) {
    const proposedLeft = Math.round(legendRight + 16);
    if (w - proposedLeft - right >= 200) left = Math.max(left, proposedLeft);
  }
  if (sheetGap !== null) {
    right = Math.max(right, sheetGap + margin);
  }
  return { ...base, left, right };
}

/** 政權面板寬度規則（ARCHITECTURE.md §10-2）。 */
export const SHEET_WIDTH = { wide: 400, min: 360, max: 480, mid: 360, narrow: 320 } as const;
/** 小於 768px 的底部 bottom sheet 三段高度：96px、50vh、90vh。 */
export type SheetSnap = 'peek' | 'half' | 'full';
export const SHEET_SNAPS: readonly SheetSnap[] = ['peek', 'half', 'full'];
export function snapHeight(snap: SheetSnap, vh: number): number {
  return snap === 'peek' ? 96 : Math.round(vh * (snap === 'half' ? 0.5 : 0.9));
}
export function clampSheetWidth(px: number): number {
  return Math.round(Math.min(SHEET_WIDTH.max, Math.max(SHEET_WIDTH.min, px)));
}
export interface SheetLayout {
  side: 'right' | 'bottom';
  size: number;
  /** 只有 ≥1440px 可拖拉（360–480px）。 */
  resizable: boolean;
  /** 768–1023px 蓋在地圖上、不推擠地圖（不設 map padding）。 */
  overlay: boolean;
}
/**
 * 面板位置與寬度（§10-2 響應式規則；w＝視窗寬）：
 * ≥1440 寬 400（可拖拉 360–480，記在 localStorage）；1024–1439 寬 360；768–1023 寬 320 蓋在地圖上；
 * <768 改成底部 bottom sheet（96px／50vh／90vh，高度不超過可用高 maxH）。
 */
export function sheetLayout(w: number, vh: number, stored: number | null = null, snap: SheetSnap = 'half', maxH = Infinity): SheetLayout {
  const vw = w || 1280;
  if (vw < 768) return { side: 'bottom', size: Math.min(snapHeight(snap, vh), maxH), resizable: false, overlay: false };
  if (vw >= 1440) return { side: 'right', size: clampSheetWidth(stored ?? SHEET_WIDTH.wide), resizable: true, overlay: false };
  if (vw >= 1024) return { side: 'right', size: SHEET_WIDTH.mid, resizable: false, overlay: false };
  return { side: 'right', size: SHEET_WIDTH.narrow, resizable: false, overlay: true };
}
