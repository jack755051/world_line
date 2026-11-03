/**
 * 國名依視窗定位（ARCHITECTURE.md §4 (c)-5，M1-g，Tai 2026-11-03 21:27；精神依 Imhof）：
 * 國名放在該政權「目前畫面可見國土」中面積最大的那一塊，位置取該塊的 pole of inaccessibility（polylabel）。
 * 全部在 Web Mercator 世界座標（0～1）計算，再乘上世界寬度換成螢幕像素；零國家特例。
 */
import type { Geometry } from 'geojson';

export type Pt = [number, number];
export type Ring = Pt[];
/** 一塊國土：外環＋洞（世界座標 0～1）。 */
export interface Piece { rings: Ring[]; bbox: [number, number, number, number]; }

/** 世界座標：x = (lng+180)/360，y = Mercator（北 0、南 1）。 */
export function toWorld(lng: number, lat: number): Pt {
  const l = Math.max(-85.05, Math.min(85.05, lat)) * Math.PI / 180;
  return [(lng + 180) / 360, (1 - Math.log(Math.tan(Math.PI / 4 + l / 2)) / Math.PI) / 2];
}
export function fromWorld(x: number, y: number): Pt {
  const lat = (Math.atan(Math.exp(Math.PI * (1 - 2 * y))) * 2 - Math.PI / 2) * 180 / Math.PI;
  return [x * 360 - 180, lat];
}

/** 幾何轉成世界座標的多塊國土（只做一次，依紀錄快取）。 */
export function geometryPieces(g: Geometry | null | undefined): Piece[] {
  if (!g) return [];
  if (g.type === 'GeometryCollection') return g.geometries.flatMap((x) => geometryPieces(x));
  const polys = g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : [];
  const out: Piece[] = [];
  for (const poly of polys) {
    const rings = poly.map((r) => r.map(([lng, lat]) => toWorld(lng, lat)));
    if (!rings.length || rings[0].length < 3) continue;
    out.push({ rings, bbox: ringBbox(rings[0]) });
  }
  return out;
}

export function ringBbox(r: Ring): [number, number, number, number] {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const [x, y] of r) { if (x < x0) x0 = x; if (y < y0) y0 = y; if (x > x1) x1 = x; if (y > y1) y1 = y; }
  return [x0, y0, x1, y1];
}

export function ringArea(r: Ring): number {
  let a = 0;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += (r[j][0] + r[i][0]) * (r[j][1] - r[i][1]);
  return Math.abs(a / 2);
}

/** Sutherland–Hodgman：把一個環裁到矩形 [x0,y0,x1,y1]。 */
export function clipRing(ring: Ring, [x0, y0, x1, y1]: [number, number, number, number]): Ring {
  let out = ring;
  const edges: [(p: Pt) => boolean, (a: Pt, b: Pt) => Pt][] = [
    [(p) => p[0] >= x0, (a, b) => [x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0])]],
    [(p) => p[0] <= x1, (a, b) => [x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0])]],
    [(p) => p[1] >= y0, (a, b) => [a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0]],
    [(p) => p[1] <= y1, (a, b) => [a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1]],
  ];
  for (const [inside, cut] of edges) {
    if (!out.length) break;
    const next: Ring = [];
    for (let i = 0; i < out.length; i++) {
      const cur = out[i], prev = out[(i + out.length - 1) % out.length];
      const ci = inside(cur), pi = inside(prev);
      if (ci) { if (!pi) next.push(cut(prev, cur)); next.push(cur); } else if (pi) next.push(cut(prev, cur));
    }
    out = next;
  }
  return out;
}

function segDist2(px: number, py: number, a: Pt, b: Pt): number {
  let x = a[0], y = a[1], dx = b[0] - x, dy = b[1] - y;
  if (dx !== 0 || dy !== 0) {
    const t = ((px - x) * dx + (py - y) * dy) / (dx * dx + dy * dy);
    if (t > 1) { x = b[0]; y = b[1]; } else if (t > 0) { x += dx * t; y += dy * t; }
  }
  dx = px - x; dy = py - y;
  return dx * dx + dy * dy;
}

/** 點到矩形的帶號距離（矩形外為正、內為負）。 */
function rectOutsideDist(x: number, y: number, [x0, y0, x1, y1]: Rect): number {
  const dx = Math.max(x0 - x, 0, x - x1), dy = Math.max(y0 - y, 0, y - y1);
  if (dx > 0 || dy > 0) return Math.hypot(dx, dy);
  return -Math.min(x - x0, x1 - x, y - y0, y1 - y);
}

/** 點到多邊形邊界的帶號距離（內正外負）。 */
function signedDist(x: number, y: number, rings: Ring[]): number {
  let inside = false, d = Infinity;
  for (const r of rings) {
    for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
      const a = r[i], b = r[j];
      if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) inside = !inside;
      d = Math.min(d, segDist2(x, y, a, b));
    }
  }
  return (inside ? 1 : -1) * Math.sqrt(d);
}

export type Rect = [number, number, number, number];

/**
 * polylabel（Mapbox 演算法，ISC）：多邊形內離邊界最遠的點；precision 與座標同單位。
 * avoid：要避開的矩形（圖例、面板等 UI）；距離取「離國界」與「離 UI」的最小值（皆 1-Lipschitz，界限仍成立）。
 */
export function polylabel(rings: Ring[], precision: number, avoid: Rect[] = []): { pt: Pt; dist: number } {
  const [x0, y0, x1, y1] = ringBbox(rings[0]);
  const w = x1 - x0, h = y1 - y0, size = Math.min(w, h);
  if (!(size > 0)) return { pt: [x0, y0], dist: 0 };
  type Cell = { x: number; y: number; h: number; d: number; max: number };
  const cell = (x: number, y: number, hh: number): Cell => { let d = signedDist(x, y, rings); for (const a of avoid) d = Math.min(d, rectOutsideDist(x, y, a)); return { x, y, h: hh, d, max: d + hh * Math.SQRT2 }; };
  const queue: Cell[] = [];
  const push = (c: Cell) => { queue.push(c); };
  const pop = () => { let bi = 0; for (let i = 1; i < queue.length; i++) if (queue[i].max > queue[bi].max) bi = i; return queue.splice(bi, 1)[0]; };
  const hs = size / 2;
  for (let x = x0; x < x1; x += size) for (let y = y0; y < y1; y += size) push(cell(x + hs, y + hs, hs));
  // 以面積重心當初始最佳解
  let area = 0, cx = 0, cy = 0; const r0 = rings[0];
  for (let i = 0, j = r0.length - 1; i < r0.length; j = i++) { const f = r0[i][0] * r0[j][1] - r0[j][0] * r0[i][1]; cx += (r0[i][0] + r0[j][0]) * f; cy += (r0[i][1] + r0[j][1]) * f; area += f * 3; }
  let best = area === 0 ? cell(x0 + w / 2, y0 + h / 2, 0) : cell(cx / area, cy / area, 0);
  const bboxCell = cell(x0 + w / 2, y0 + h / 2, 0); if (bboxCell.d > best.d) best = bboxCell;
  let guard = 0;
  while (queue.length && guard++ < 4000) {
    const c = pop();
    if (c.d > best.d) best = c;
    if (c.max - best.d <= precision) continue;
    const q = c.h / 2;
    push(cell(c.x - q, c.y - q, q)); push(cell(c.x + q, c.y - q, q)); push(cell(c.x - q, c.y + q, q)); push(cell(c.x + q, c.y + q, q));
  }
  return { pt: [best.x, best.y], dist: best.d };
}

export interface ViewportPlacement {
  /** 標籤點（WGS84，已平移到離畫面中心最近的世界副本） */
  lngLat: Pt;
  /** 可見塊的螢幕寬、高（px） */
  widthPx: number;
  heightPx: number;
  /** 標籤點離國界／畫面邊／UI 的最近距離（px）；≤0 代表可見塊全被 UI 蓋住 */
  clearPx: number;
}

/**
 * 在可見範圍 view（世界座標 0～1 可超出，代表世界副本）內，找面積最大的可見塊並取 polylabel。
 * worldPx＝目前縮放的世界寬度（512×2^z）。沒有可見塊回傳 null。
 */
export function placeInViewport(
  pieces: Piece[],
  view: Rect,
  worldPx: number,
  avoid: Rect[] = [],
  label?: { w: number; h: number },
): ViewportPlacement | null {
  const cxView = (view[0] + view[2]) / 2;
  let best: { rings: Ring[]; area: number } | null = null;
  for (const p of pieces) {
    // 平移到離畫面中心最近的世界副本
    const k = Math.round(cxView - (p.bbox[0] + p.bbox[2]) / 2);
    const bx0 = p.bbox[0] + k, bx1 = p.bbox[2] + k;
    if (bx1 < view[0] || bx0 > view[2] || p.bbox[3] < view[1] || p.bbox[1] > view[3]) continue;
    if ((p.bbox[2] - p.bbox[0]) * worldPx < MIN_PIECE_PX && (p.bbox[3] - p.bbox[1]) * worldPx < MIN_PIECE_PX) continue;
    const src = simplified(p, worldPx);
    const shifted = k === 0 ? src : src.map((r) => r.map(([x, y]) => [x + k, y] as Pt));
    const inside = bx0 >= view[0] && bx1 <= view[2] && p.bbox[1] >= view[1] && p.bbox[3] <= view[3];
    const rings = inside ? shifted : shifted.map((r) => clipRing(r, view)).filter((r) => r.length >= 3);
    if (!rings.length || rings[0].length < 3) continue;
    const area = ringArea(rings[0]) - rings.slice(1).reduce((s, r) => s + ringArea(r), 0);
    if (area > 0 && (!best || area > best.area)) best = { rings, area };
  }
  if (!best) return null;
  // 名字是橫長方形：x 方向依「字高／字寬」壓縮後再求 pole of inaccessibility → 找到最能容納整個名字框的位置
  const a = label && label.w > 0 ? Math.min(1, label.h / label.w) : 1;
  const sx = (r: Ring): Ring => (a === 1 ? r : r.map(([x, y]) => [x * a, y] as Pt));
  const pl = polylabel(best.rings.map(sx), 1 / worldPx, avoid.map(([ax0, ay0, ax1, ay1]) => [ax0 * a, ay0, ax1 * a, ay1] as Rect));
  let px = pl.pt[0] / a;
  const [x0, y0, x1, y1] = ringBbox(best.rings[0]);
  // 名字框不超出畫面左右
  if (label) {
    const half = label.w / 2 / worldPx;
    if (view[2] - view[0] > 2 * half) px = Math.min(view[2] - half, Math.max(view[0] + half, px));
  }
  return { lngLat: fromWorld(px, pl.pt[1]), widthPx: (x1 - x0) * worldPx, heightPx: (y1 - y0) * worldPx, clearPx: pl.dist * worldPx };
}

/** 小於這個螢幕尺寸（px）的塊直接略過（裝不下任何名字）。 */
const MIN_PIECE_PX = 6;

/** 依縮放簡化：相鄰點距離小於 1px 的點略去（radial distance）；每塊、每個整數縮放級快取一次。 */
const simplifyCache = new WeakMap<Piece, Map<number, Ring[]>>();
export function simplifyRing(r: Ring, tol: number): Ring {
  if (r.length <= 8) return r;
  const t2 = tol * tol, out: Ring = [r[0]];
  let prev = r[0];
  for (let i = 1; i < r.length - 1; i++) {
    const p = r[i], dx = p[0] - prev[0], dy = p[1] - prev[1];
    if (dx * dx + dy * dy >= t2) { out.push(p); prev = p; }
  }
  out.push(r[r.length - 1]);
  return out.length >= 4 ? out : r;
}
function simplified(p: Piece, worldPx: number): Ring[] {
  const z = Math.floor(Math.log2(worldPx / 512));
  let m = simplifyCache.get(p);
  if (!m) { m = new Map(); simplifyCache.set(p, m); }
  let hit = m.get(z);
  if (!hit) {
    const tol = 1 / (512 * 2 ** (z + 1));
    hit = p.rings.map((r) => simplifyRing(r, tol));
    m.set(z, hit);
  }
  return hit;
}
