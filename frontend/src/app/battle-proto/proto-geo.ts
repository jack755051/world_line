import { Delaunay } from 'd3-delaunay';
import { bezierSpline, booleanPointInPolygon, lineString, polygon, simplify } from '@turf/turf';
import type { ProtoData, ProtoSide, ProtoStatus, ProtoUnit } from './proto-data';

/** 純邏輯：逐日內插、縮放聚合、Voronoi 前線。不依賴 Angular／MapLibre，方便單測。 */
export type LngLat = [number, number];
export interface UnitPoint { id: string; side: ProtoSide; lng: number; lat: number; status: ProtoStatus }

/** 600ms 單步／1x＝兩示例日之間 3 秒（規格 §3）。 */
export const SECONDS_PER_DAY_GAP = 3;
export const AGGREGATE_ZOOM = 7;
export const FRONT_RECOMPUTE_EVERY_N_FRAMES = 6;

/** reduced-motion：不內插，進度四捨五入到整日。 */
export function effectiveT(t: number, reduced: boolean): number {
  return reduced ? Math.round(t) : t;
}
export function isInterpolating(t: number): boolean {
  return Math.abs(t - Math.round(t)) > 1e-3;
}
export function levelForZoom(z: number): 'corps' | 'division' {
  return z < AGGREGATE_ZOOM ? 'corps' : 'division';
}

/** 日期（YYYY-MM-DD）→ 進度 t（索引）。不在清單內取最近的日子，無效字串回 0。 */
export function dateToIndex(dates: string[], iso: string | null | undefined): number {
  if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return 0;
  const exact = dates.indexOf(iso);
  if (exact >= 0) return exact;
  const ms = (s: string) => Date.parse(s + 'T00:00:00Z');
  let best = 0;
  dates.forEach((d, i) => { if (Math.abs(ms(d) - ms(iso)) < Math.abs(ms(dates[best]) - ms(iso))) best = i; });
  return best;
}

function positionOn(data: ProtoData, unitId: string, date: string): { lng: number; lat: number; status: ProtoStatus } | undefined {
  return data.positions.find((p) => p.unit_id === unitId && p.date === date);
}

/** 師級單位在進度 t（0…N-1）的位置：整數＝記錄日（取該日狀態），小數＝兩日線性內插（status 一律 inferred）。缺漏日沿用最近有資料的日子。 */
export function interpolateUnits(data: ProtoData, t: number): UnitPoint[] {
  const dates = data.meta.dates;
  const tc = Math.min(Math.max(t, 0), dates.length - 1);
  const i0 = Math.floor(tc), i1 = Math.min(i0 + 1, dates.length - 1), f = tc - i0;
  const out: UnitPoint[] = [];
  for (const u of data.units) {
    if (u.echelon !== 'division') continue;
    const nearest = (i: number) => {
      for (let d = 0; d < dates.length; d++) {
        const p = positionOn(data, u.id, dates[i - d]) ?? positionOn(data, u.id, dates[i + d]);
        if (p) return p;
      }
      return undefined;
    };
    const a = positionOn(data, u.id, dates[i0]) ?? nearest(i0);
    const b = positionOn(data, u.id, dates[i1]) ?? nearest(i1);
    if (!a || !b) continue;
    if (!isInterpolating(tc)) {
      const p = f > 0.5 ? b : a;
      out.push({ id: u.id, side: u.side, lng: p.lng, lat: p.lat, status: p.status });
    } else {
      out.push({ id: u.id, side: u.side, lng: a.lng + (b.lng - a.lng) * f, lat: a.lat + (b.lat - a.lat) * f, status: 'inferred' });
    }
  }
  return out;
}

export interface DisplayUnit { id: string; side: ProtoSide; lng: number; lat: number; level: 'corps' | 'division'; count: number; status: ProtoStatus }

/** z<7 聚合到軍級：同 parent 的師取平均位置；沒有 parent 的師維持原樣。z≥7 直接回師級。 */
export function aggregateUnits(units: ProtoUnit[], pts: UnitPoint[], level: 'corps' | 'division'): DisplayUnit[] {
  if (level === 'division') return pts.map((p) => ({ ...p, level, count: 1 }));
  const byId = new Map(units.map((u) => [u.id, u]));
  const groups = new Map<string, UnitPoint[]>();
  const loose: DisplayUnit[] = [];
  for (const p of pts) {
    const parent = byId.get(p.id)?.parent_id;
    if (!parent) { loose.push({ ...p, level: 'division', count: 1 }); continue; }
    (groups.get(parent) ?? groups.set(parent, []).get(parent)!).push(p);
  }
  const out = [...loose];
  for (const [parent, g] of groups) {
    out.push({
      id: parent, side: g[0].side, level: 'corps', count: g.length,
      lng: g.reduce((s, p) => s + p.lng, 0) / g.length, lat: g.reduce((s, p) => s + p.lat, 0) / g.length,
      status: g.every((p) => p.status === 'recorded') ? 'recorded' : 'inferred',
    });
  }
  return out;
}

// ───────── 前線 ─────────
export interface FrontResult {
  /** MultiLineString 座標（已平滑、簡化、丟掉海上線段）。無交界則為空陣列。 */
  lines: LngLat[][];
  /** 兩側半透明色帶（每條線兩側各一個多邊形）。 */
  bands: { side: ProtoSide; ring: LngLat[] }[];
  manual: boolean;
}
export interface FrontOptions {
  theater: [number, number, number, number];
  land: number[][];
  /** 取代自動結果的人工 MultiLineString 座標。 */
  override?: number[][][] | null;
  simplifyTolerance?: number;
  bandWidth?: number;
}

const key = (p: number[]) => `${Math.round(p[0] * 1e5)},${Math.round(p[1] * 1e5)}`;

function inLand(land: number[][], p: number[]): boolean {
  return booleanPointInPolygon(p, polygon([land]));
}

/** 把線依「點是否在陸地」切開，丟掉海上的部分；先以 ≤0.05° 加密才不會漏掉跨岸線段。 */
export function clipLineToLand(coords: number[][], land: number[][]): LngLat[][] {
  const poly = polygon([land]);
  const dense: number[][] = [];
  for (let i = 0; i < coords.length - 1; i++) {
    const [a, b] = [coords[i], coords[i + 1]];
    const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 0.05));
    for (let k = 0; k < n; k++) dense.push([a[0] + ((b[0] - a[0]) * k) / n, a[1] + ((b[1] - a[1]) * k) / n]);
  }
  dense.push(coords[coords.length - 1]);
  const out: LngLat[][] = [];
  let cur: LngLat[] = [];
  for (const p of dense) {
    if (booleanPointInPolygon(p, poly, { ignoreBoundary: false })) cur.push([p[0], p[1]]);
    else { if (cur.length > 1) out.push(cur); cur = []; }
  }
  if (cur.length > 1) out.push(cur);
  return out;
}

function chain(segs: [number[], number[]][]): number[][][] {
  const lines: number[][][] = [];
  for (const [a, b] of segs) {
    let placed = false;
    for (const l of lines) {
      if (key(l[l.length - 1]) === key(a)) { l.push(b); placed = true; break; }
      if (key(l[l.length - 1]) === key(b)) { l.push(a); placed = true; break; }
      if (key(l[0]) === key(b)) { l.unshift(a); placed = true; break; }
      if (key(l[0]) === key(a)) { l.unshift(b); placed = true; break; }
    }
    if (!placed) lines.push([a, b]);
  }
  // 第二輪：把端點相接的線合併
  let merged = true;
  while (merged) {
    merged = false;
    outer: for (let i = 0; i < lines.length; i++) for (let j = i + 1; j < lines.length; j++) {
      const A = lines[i], B = lines[j];
      const [a0, a1, b0, b1] = [key(A[0]), key(A[A.length - 1]), key(B[0]), key(B[B.length - 1])];
      let next: number[][] | null = null;
      if (a1 === b0) next = [...A, ...B.slice(1)];
      else if (a1 === b1) next = [...A, ...[...B].reverse().slice(1)];
      else if (a0 === b1) next = [...B, ...A.slice(1)];
      else if (a0 === b0) next = [...[...B].reverse(), ...A.slice(1)];
      if (next) { lines.splice(j, 1); lines[i] = next; merged = true; break outer; }
    }
  }
  return lines;
}

/** 兩側色帶：沿線左右各偏移 width，軸心側由「該側單位質心在線的哪一邊」決定。 */
function buildBands(lines: LngLat[][], pts: UnitPoint[], width: number): FrontResult['bands'] {
  const centroid = (s: ProtoSide): LngLat | null => {
    const g = pts.filter((p) => p.side === s);
    return g.length ? [g.reduce((a, p) => a + p.lng, 0) / g.length, g.reduce((a, p) => a + p.lat, 0) / g.length] : null;
  };
  const axisC = centroid('axis');
  const bands: FrontResult['bands'] = [];
  for (const l of lines) {
    if (l.length < 2) continue;
    const offset = (sign: number): LngLat[] => l.map((p, i) => {
      const a = l[Math.max(0, i - 1)], b = l[Math.min(l.length - 1, i + 1)];
      const dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy) || 1;
      return [p[0] + (sign * -dy * width) / len, p[1] + (sign * dx * width) / len];
    });
    const mid = l[Math.floor(l.length / 2)], a = l[Math.max(0, Math.floor(l.length / 2) - 1)], b = l[Math.min(l.length - 1, Math.floor(l.length / 2) + 1)];
    const nx = -(b[1] - a[1]), ny = b[0] - a[0];
    const axisPositive = axisC ? (axisC[0] - mid[0]) * nx + (axisC[1] - mid[1]) * ny > 0 : true;
    const pos = offset(1), neg = offset(-1);
    const ring = (side: LngLat[]): LngLat[] => [...l, ...[...side].reverse(), l[0]];
    bands.push({ side: axisPositive ? 'axis' : 'allied', ring: ring(pos) });
    bands.push({ side: axisPositive ? 'allied' : 'axis', ring: ring(neg) });
  }
  return bands;
}

/**
 * 自動前線：當日師級點 → Voronoi（裁切到戰區）→ 兩陣營格子的共用邊 → 丟掉不在陸地的部分 → 串線 → bezierSpline 平滑＋簡化。
 * `override` 非 null 時改用人工線（仍依陸地裁切，色帶與軸心側判定照舊）。
 */
export function generateFront(pts: UnitPoint[], opts: FrontOptions): FrontResult {
  const tol = opts.simplifyTolerance ?? 0.004;
  const width = opts.bandWidth ?? 0.1;
  if (opts.override && opts.override.length) {
    const lines = opts.override.flatMap((l) => clipLineToLand(l, opts.land));
    return { lines, bands: buildBands(lines, pts, width), manual: true };
  }
  if (pts.length < 2 || !pts.some((p) => p.side === 'axis') || !pts.some((p) => p.side === 'allied')) return { lines: [], bands: [], manual: false };
  const voronoi = Delaunay.from(pts, (p) => p.lng, (p) => p.lat).voronoi(opts.theater);
  const edges = new Map<string, { a: number[]; b: number[]; sides: Set<ProtoSide>; n: number }>();
  pts.forEach((p, i) => {
    const ring = voronoi.cellPolygon(i);
    if (!ring) return;
    for (let k = 0; k < ring.length - 1; k++) {
      const [a, b] = [ring[k], ring[k + 1]];
      const [ka, kb] = [key(a), key(b)];
      if (ka === kb) continue;
      const id = ka < kb ? `${ka}|${kb}` : `${kb}|${ka}`;
      const e = edges.get(id) ?? { a: [a[0], a[1]], b: [b[0], b[1]], sides: new Set<ProtoSide>(), n: 0 };
      e.sides.add(p.side); e.n++;
      edges.set(id, e);
    }
  });
  const front: [number[], number[]][] = [];
  for (const e of edges.values()) if (e.n === 2 && e.sides.size === 2) front.push([e.a, e.b]);
  const smooth: LngLat[][] = [];
  for (const raw of chain(front)) {
    for (const piece of clipLineToLand(raw, opts.land)) {
      let coords: number[][] = piece;
      if (piece.length >= 3) {
        const sp = bezierSpline(lineString(piece), { resolution: 300, sharpness: 0.6 });
        coords = simplify(sp, { tolerance: tol, highQuality: false }).geometry.coordinates;
      }
      for (const seg of clipLineToLand(coords, opts.land)) smooth.push(seg);
    }
  }
  return { lines: smooth, bands: buildBands(smooth, pts, width), manual: false };
}

export function bearingDeg(a: LngLat, b: LngLat): number {
  return (Math.atan2(b[0] - a[0], b[1] - a[1]) * 180) / Math.PI;
}

/** 推進箭頭：第 seg 段（日 seg → seg+1）位移夠大的單位／軍級，回傳起訖點。 */
export function buildArrows(data: ProtoData, level: 'corps' | 'division', seg: number, minDeg = 0.35): { id: string; side: ProtoSide; from: LngLat; to: LngLat; bearing: number }[] {
  const A = aggregateUnits(data.units, interpolateUnits(data, seg), level);
  const B = new Map(aggregateUnits(data.units, interpolateUnits(data, seg + 1), level).map((u) => [u.id, u]));
  const out: { id: string; side: ProtoSide; from: LngLat; to: LngLat; bearing: number }[] = [];
  for (const a of A) {
    const b = B.get(a.id);
    if (!b || Math.hypot(b.lng - a.lng, b.lat - a.lat) < minDeg) continue;
    out.push({ id: a.id, side: a.side, from: [a.lng, a.lat], to: [b.lng, b.lat], bearing: bearingDeg([a.lng, a.lat], [b.lng, b.lat]) });
  }
  return out;
}

export { inLand };
