import { Delaunay } from 'd3-delaunay';
import { featureCollection, intersect, polygon, union } from '@turf/turf';
import { interpolate } from 'flubber';
import type { Feature, MultiPolygon, Polygon } from 'geojson';
import type { LngLat, UnitPoint } from './proto-geo';
import { bearingDeg } from './proto-geo';
import type { ProtoSide } from './proto-data';

/** 縮小時大局動畫層的純邏輯（規格 §10）：箭頭曲線／進度、領土多邊形、flubber 變形中間幀、火花取點。 */

export const FX_KEYS = ['arrows', 'territory', 'glow', 'sparks', 'shock', 'tear', 'title'] as const;
export type FxKey = (typeof FX_KEYS)[number];
export type FxState = Record<FxKey, boolean>;
export const defaultFx = (): FxState => ({ arrows: true, territory: true, glow: true, sparks: true, shock: true, tear: true, title: true });

// ───────── 1. 箭頭 ─────────
/** 由 from→to 的二次貝茲曲線（向左偏 bend×長度），取 n+1 個點。 */
export function arrowCurve(from: LngLat, to: LngLat, n = 24, bend = 0.18): LngLat[] {
  const mx = (from[0] + to[0]) / 2, my = (from[1] + to[1]) / 2;
  const dx = to[0] - from[0], dy = to[1] - from[1];
  const c: LngLat = [mx - dy * bend, my + dx * bend];
  const out: LngLat[] = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n, u = 1 - t;
    out.push([u * u * from[0] + 2 * u * t * c[0] + t * t * to[0], u * u * from[1] + 2 * u * t * c[1] + t * t * to[1]]);
  }
  return out;
}

/** 取曲線前 p（0–1，依點數線性）的部分，最後一點內插；回傳線與箭頭朝向。p≤0 回傳空線。 */
export function sliceCurve(curve: LngLat[], p: number): { line: LngLat[]; head: LngLat; bearing: number } {
  const q = Math.min(1, Math.max(0, p));
  const segs = curve.length - 1;
  if (q <= 0 || segs < 1) return { line: [], head: curve[0], bearing: segs >= 1 ? bearingDeg(curve[0], curve[1]) : 0 };
  const f = q * segs, k = Math.min(segs - 1, Math.floor(f)), r = f - k;
  const a = curve[k], b = curve[k + 1];
  const head: LngLat = [a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r];
  const line = [...curve.slice(0, k + 1), head];
  return { line, head, bearing: bearingDeg(a, b) };
}

/** 箭頭進度：段內 f（0–1）。reduced／靜止停在示例日時畫滿；播放中前 80% 的段內時間畫完。 */
export function arrowProgress(f: number, opts: { reduced: boolean; settled: boolean }): number {
  if (opts.reduced || opts.settled) return 1;
  return Math.min(1, Math.max(0, f / 0.8));
}

// ───────── 2. 領土 ─────────
function toRings(g: Polygon | MultiPolygon): LngLat[][] {
  const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
  return polys.map((p) => p[0] as LngLat[]);
}

/** 某陣營 Voronoi 格子合併後與陸地求交；回傳外環（可能多塊），面積大者在前。 */
export function territoryRings(pts: UnitPoint[], side: ProtoSide, theater: [number, number, number, number], land: number[][]): LngLat[][] {
  const mine = pts.map((p, i) => ({ p, i })).filter((x) => x.p.side === side);
  if (pts.length < 2 || !mine.length) return [];
  const vor = Delaunay.from(pts, (p) => p.lng, (p) => p.lat).voronoi(theater);
  const cells: Feature<Polygon>[] = [];
  for (const { i } of mine) { const ring = vor.cellPolygon(i); if (ring && ring.length >= 4) cells.push(polygon([ring.map((c) => [c[0], c[1]])])); }
  if (!cells.length) return [];
  let merged: Feature<Polygon | MultiPolygon> | null = cells.length === 1 ? cells[0] : union(featureCollection(cells));
  if (!merged) return [];
  const clipped = intersect(featureCollection([merged, polygon([land])]));
  merged = clipped ?? null;
  if (!merged) return [];
  return toRings(merged.geometry).sort((a, b) => ringArea(b) - ringArea(a));
}

export function ringArea(r: LngLat[]): number {
  let s = 0;
  for (let i = 0; i < r.length - 1; i++) s += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1];
  return Math.abs(s) / 2;
}

const NUM = /-?\d+(?:\.\d+)?(?:e-?\d+)?/gi;
/** flubber 輸出 "M x,y L x,y … Z" → 閉合環。 */
export function pathToRing(path: string): LngLat[] {
  const n = path.match(NUM)?.map(Number) ?? [];
  const ring: LngLat[] = [];
  for (let i = 0; i + 1 < n.length; i += 2) ring.push([n[i], n[i + 1]]);
  if (ring.length && (ring[0][0] !== ring[ring.length - 1][0] || ring[0][1] !== ring[ring.length - 1][1])) ring.push([ring[0][0], ring[0][1]]);
  return ring;
}

/** 兩環之間的 f（0–1）中間幀：優先 flubber.interpolate；失敗就退回「等點數重取樣＋線性內插」。 */
export function morphRing(a: LngLat[], b: LngLat[], maxSegmentLength = 0.08): (f: number) => LngLat[] {
  try {
    const it = interpolate(a, b, { maxSegmentLength });
    return (f) => (f <= 0 ? a : f >= 1 ? b : pathToRing(it(f)));
  } catch {
    const n = Math.max(a.length, b.length, 32);
    const ra = resample(a, n), rb = resample(b, n);
    return (f) => (f <= 0 ? a : f >= 1 ? b : ra.map((p, i) => [p[0] + (rb[i][0] - p[0]) * f, p[1] + (rb[i][1] - p[1]) * f] as LngLat));
  }
}

/** 沿環等距重取 n 點（退路用）。 */
export function resample(ring: LngLat[], n: number): LngLat[] {
  const len: number[] = [0];
  for (let i = 1; i < ring.length; i++) len.push(len[i - 1] + Math.hypot(ring[i][0] - ring[i - 1][0], ring[i][1] - ring[i - 1][1]));
  const total = len[len.length - 1] || 1;
  const out: LngLat[] = [];
  let k = 1;
  for (let i = 0; i < n; i++) {
    const d = (i / n) * total;
    while (k < len.length - 1 && len[k] < d) k++;
    const seg = len[k] - len[k - 1] || 1, r = (d - len[k - 1]) / seg;
    out.push([ring[k - 1][0] + (ring[k][0] - ring[k - 1][0]) * r, ring[k - 1][1] + (ring[k][1] - ring[k - 1][1]) * r]);
  }
  out.push([out[0][0], out[0][1]]);
  return out;
}

// ───────── 4. 火花取點 ─────────
/** 在多條折線上依總長取點，u∈[0,1)。無線回 null。 */
export function pointOnLines(lines: LngLat[][], u: number): LngLat | null {
  const lens = lines.map((l) => l.slice(1).reduce((s, p, i) => s + Math.hypot(p[0] - l[i][0], p[1] - l[i][1]), 0));
  const total = lens.reduce((s, x) => s + x, 0);
  if (total <= 0) return null;
  let d = Math.min(0.999999, Math.max(0, u)) * total;
  for (let i = 0; i < lines.length; i++) {
    if (d > lens[i]) { d -= lens[i]; continue; }
    const l = lines[i];
    for (let j = 1; j < l.length; j++) {
      const sl = Math.hypot(l[j][0] - l[j - 1][0], l[j][1] - l[j - 1][1]);
      if (d <= sl) { const r = sl ? d / sl : 0; return [l[j - 1][0] + (l[j][0] - l[j - 1][0]) * r, l[j - 1][1] + (l[j][1] - l[j - 1][1]) * r]; }
      d -= sl;
    }
  }
  return null;
}
