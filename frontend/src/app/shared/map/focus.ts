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

/** 面板位置：桌面從右側滑出（寬 3/4、最多 384px，同 sanring sheet 的 w-3/4 sm:max-w-sm）；窄螢幕（< 640px）改從底部，高度 55%。 */
export function sheetLayout(w: number, h: number): { side: 'right' | 'bottom'; size: number } {
  return w > 0 && w < 640 ? { side: 'bottom', size: Math.round(h * 0.55) } : { side: 'right', size: Math.min(384, Math.round((w || 1280) * 0.75)) };
}
