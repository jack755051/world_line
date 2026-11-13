/**
 * §19.2.4 相鄰階段政權疆界漸變（C2b）。純函式、無 DOM、無依賴（自寫頂點重採樣，不用 flubber）。
 *
 * 規則（ARCHITECTURE §19.2.4 (i)–(v)）：
 * - 只處理「有出處」的疆界（`properties.geometry.sourceId` 有值）；沒出處的不顯示、也不參與漸變。
 * - 兩階段同一筆紀錄（recordId 相同且幾何不變）→ `same`，留在一般疆界圖層。
 * - 同一政權、拓撲相容（多邊形數、每個多邊形的洞數相同）且頂點數差距 ≤ MAX_VERTEX_RATIO 倍 → `morph`（重採樣後逐點插值）。
 * - 其他（分裂、合併、島嶼增減、頂點數差太多、只出現在一邊）→ `fade`（交叉淡入淡出）。
 * - 中間形狀一律帶 `transitional: true`，只給「推估過渡」圖層用；不入庫、不可點選。
 */
export type Pos = [number, number];
export type Ring = Pos[];
export type Poly = Ring[];
export interface BorderFeature {
  type: 'Feature';
  id?: string | number;
  geometry: { type: string; coordinates: unknown } | null;
  properties: Record<string, unknown> | null;
}
export interface BorderFC { type: 'FeatureCollection'; features: BorderFeature[] }

/** 頂點數差距超過這個倍數就退回淡入淡出（避免重採樣把小形狀拉成鋸齒）。 */
export const MAX_VERTEX_RATIO = 4;
/** 單一環重採樣點數上下限（效能：每格只做 O(點數) 的線性插值）。 */
export const MIN_SAMPLES = 24;
export const MAX_SAMPLES = 1200;

export type MorphReason = 'polygon-count' | 'hole-count' | 'vertex-ratio' | 'unpaired' | 'geometry';
export interface MorphItem { key: string; from: Poly[]; to: Poly[] }
export interface FadeItem { key: string; from: BorderFeature | null; to: BorderFeature | null; reason: MorphReason }
export interface MorphPlan {
  same: BorderFeature[];
  morph: MorphItem[];
  fade: FadeItem[];
  /** 給 UI 標示：全部 morph／全部 fade／混合／沒有變化。 */
  mode: 'none' | 'morph' | 'fade' | 'mixed';
}

/** 「有出處」：幾何帶來源 id（/sovereignty 的 `properties.geometry.sourceId`）。 */
export function isSourced(f: BorderFeature): boolean {
  const g = f.properties?.['geometry'] as { sourceId?: unknown } | null | undefined;
  return !!f.geometry && typeof g?.sourceId === 'string' && g.sourceId.length > 0;
}
/** §19.2.4 (ii)：停在階段時只留有出處的疆界，且去掉任何過渡標記。 */
export function sourcedBorders(fc: BorderFC | null | undefined): BorderFC {
  return { type: 'FeatureCollection', features: (fc?.features ?? []).filter((f) => isSourced(f) && f.properties?.['transitional'] !== true) };
}

export function polysOf(g: BorderFeature['geometry']): Poly[] | null {
  if (!g) return null;
  if (g.type === 'Polygon') return [g.coordinates as Poly];
  if (g.type === 'MultiPolygon') return g.coordinates as Poly[];
  return null;
}

function openRing(r: Ring): Ring {
  const n = r.length;
  return n > 1 && r[0][0] === r[n - 1][0] && r[0][1] === r[n - 1][1] ? r.slice(0, n - 1) : r.slice();
}
export function signedArea(r: Ring): number {
  let s = 0;
  for (let i = 0, n = r.length; i < n; i++) { const a = r[i], b = r[(i + 1) % n]; s += a[0] * b[1] - b[0] * a[1]; }
  return s / 2;
}
const polyArea = (p: Poly) => Math.abs(signedArea(openRing(p[0] ?? [])));

/** 封閉環依周長等距重採樣成 n 點（回傳不重複首點的開放環）。 */
export function resampleRing(ring: Ring, n: number): Ring {
  const r = openRing(ring);
  if (r.length === 0) return [];
  if (r.length === 1) return Array.from({ length: n }, () => [r[0][0], r[0][1]] as Pos);
  const cum = [0];
  for (let i = 0; i < r.length; i++) {
    const a = r[i], b = r[(i + 1) % r.length];
    cum.push(cum[i] + Math.hypot(b[0] - a[0], b[1] - a[1]));
  }
  const total = cum[r.length];
  if (total === 0) return Array.from({ length: n }, () => [r[0][0], r[0][1]] as Pos);
  const out: Ring = [];
  let seg = 0;
  for (let k = 0; k < n; k++) {
    const d = (k / n) * total;
    while (seg < r.length - 1 && cum[seg + 1] < d) seg++;
    const a = r[seg], b = r[(seg + 1) % r.length];
    const len = cum[seg + 1] - cum[seg];
    const t = len > 0 ? (d - cum[seg]) / len : 0;
    out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
  }
  return out;
}

/** 讓 b 跟 a 同方向，並旋轉起點使逐點距離平方和最小（大環只檢查約 240 個候選起點）。 */
export function alignRing(a: Ring, b: Ring): Ring {
  const n = a.length;
  if (n === 0 || b.length !== n) return b;
  const bb = Math.sign(signedArea(a)) !== Math.sign(signedArea(b)) ? b.slice().reverse() : b;
  const step = Math.max(1, Math.ceil(n / 240));
  let best = 0, bestCost = Infinity;
  for (let off = 0; off < n; off += step) {
    let c = 0;
    for (let i = 0; i < n && c < bestCost; i += step) { const p = a[i], q = bb[(i + off) % n]; c += (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2; }
    if (c < bestCost) { bestCost = c; best = off; }
  }
  return best === 0 ? bb : [...bb.slice(best), ...bb.slice(0, best)];
}

/** 拓撲／頂點數相容性；相容回 null，否則回原因（§19.2.4 (iv)）。 */
export function incompatibility(from: Poly[], to: Poly[]): MorphReason | null {
  if (from.length !== to.length || from.length === 0) return 'polygon-count';
  const fs = [...from].sort((x, y) => polyArea(y) - polyArea(x));
  const ts = [...to].sort((x, y) => polyArea(y) - polyArea(x));
  for (let i = 0; i < fs.length; i++) {
    if (fs[i].length !== ts[i].length) return 'hole-count';
    for (let j = 0; j < fs[i].length; j++) {
      const a = openRing(fs[i][j]).length, b = openRing(ts[i][j]).length;
      if (a < 3 || b < 3) return 'geometry';
      if (Math.max(a, b) / Math.min(a, b) > MAX_VERTEX_RATIO) return 'vertex-ratio';
    }
  }
  return null;
}

/** 依面積配對多邊形、逐環重採樣並對齊；回傳等長的 from／to（開放環）。 */
export function prepareMorph(from: Poly[], to: Poly[]): { from: Poly[]; to: Poly[] } {
  const fs = [...from].sort((x, y) => polyArea(y) - polyArea(x));
  const ts = [...to].sort((x, y) => polyArea(y) - polyArea(x));
  const F: Poly[] = [], T: Poly[] = [];
  fs.forEach((fp, i) => {
    const fr: Ring[] = [], tr: Ring[] = [];
    fp.forEach((ring, j) => {
      const n = Math.min(MAX_SAMPLES, Math.max(MIN_SAMPLES, openRing(ring).length, openRing(ts[i][j]).length));
      const a = resampleRing(ring, n);
      fr.push(a);
      tr.push(alignRing(a, resampleRing(ts[i][j], n)));
    });
    F.push(fr); T.push(tr);
  });
  return { from: F, to: T };
}

const keyOf = (f: BorderFeature) => String(f.properties?.['regimeId'] ?? f.properties?.['recordId'] ?? f.id ?? '');
const recOf = (f: BorderFeature) => String(f.properties?.['recordId'] ?? f.id ?? '');

/** 兩個階段（只取有出處的）→ 漸變計畫。 */
export function planMorph(fromFc: BorderFC | null | undefined, toFc: BorderFC | null | undefined): MorphPlan {
  const A = sourcedBorders(fromFc).features, B = sourcedBorders(toFc).features;
  const plan: MorphPlan = { same: [], morph: [], fade: [], mode: 'none' };
  const byKey = (fs: BorderFeature[]) => {
    const m = new Map<string, BorderFeature[]>();
    for (const f of fs) { const k = keyOf(f); m.set(k, [...(m.get(k) ?? []), f]); }
    return m;
  };
  const ma = byKey(A), mb = byKey(B);
  for (const k of new Set([...ma.keys(), ...mb.keys()])) {
    const fa = ma.get(k) ?? [], fb = mb.get(k) ?? [];
    if (fa.length === 1 && fb.length === 1) {
      const [a, b] = [fa[0], fb[0]];
      if (recOf(a) === recOf(b) && JSON.stringify(a.geometry) === JSON.stringify(b.geometry)) { plan.same.push(b); continue; }
      const pa = polysOf(a.geometry), pb = polysOf(b.geometry);
      const why = pa && pb ? incompatibility(pa, pb) : 'geometry';
      if (!why) { const p = prepareMorph(pa!, pb!); plan.morph.push({ key: k, from: p.from, to: p.to }); }
      else plan.fade.push({ key: k, from: a, to: b, reason: why });
      continue;
    }
    // 同一政權多筆紀錄（或只在一邊出現）→ 一律淡入淡出
    for (const a of fa) plan.fade.push({ key: k, from: a, to: null, reason: fb.length ? 'polygon-count' : 'unpaired' });
    for (const b of fb) plan.fade.push({ key: k, from: null, to: b, reason: fa.length ? 'polygon-count' : 'unpaired' });
  }
  plan.mode = plan.morph.length && plan.fade.length ? 'mixed' : plan.morph.length ? 'morph' : plan.fade.length ? 'fade' : 'none';
  return plan;
}

const close = (r: Ring): Ring => (r.length ? [...r, r[0]] : r);
const txProps = (key: string, kind: 'morph' | 'fade', o: number) => ({ key, kind, o, transitional: true });

/** 進度 t（0–1）的中間形狀（只含 morph／fade 部分；`same` 由一般疆界圖層顯示）。 */
export function interpolate(plan: MorphPlan, t: number): BorderFC {
  const u = Math.max(0, Math.min(1, t));
  const features: BorderFeature[] = [];
  for (const m of plan.morph) {
    const coords = m.from.map((poly, i) => poly.map((ring, j) => close(ring.map((p, k) => {
      const q = m.to[i][j][k];
      return [p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u] as Pos;
    }))));
    features.push({ type: 'Feature', geometry: { type: 'MultiPolygon', coordinates: coords }, properties: txProps(m.key, 'morph', 1) });
  }
  for (const f of plan.fade) {
    if (f.from && u < 1) features.push({ type: 'Feature', geometry: f.from.geometry, properties: txProps(f.key, 'fade', 1 - u) });
    if (f.to && u > 0) features.push({ type: 'Feature', geometry: f.to.geometry, properties: txProps(f.key, 'fade', u) });
  }
  return { type: 'FeatureCollection', features };
}
