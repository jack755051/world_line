/**
 * 遠距交戰虛線弧（Tai 2026-10-31）：交戰雙方當日不相鄰時，在兩國之間畫一條虛線弧，雙劍放在弧線中點。
 * 端點來自 API（ConflictArcDto：雙方主權紀錄的 ST_PointOnSurface）；本檔只做幾何：
 * - 經度展開：兩端經度差超過 180 度時改走跨換日線的那一側（例如日本—美國走太平洋）；
 * - 二次貝茲曲線（經緯度平面），控制點在中點的垂直方向、往北（高緯）彎，弧高＝弦長 × 0.22；
 * - 緯度上限 85 度（Web Mercator 可投影範圍內）。
 */
export interface ConflictArc {
  /** 弧線取樣點（[經度, 緯度]，經度可能超出 ±180，用來保持連續） */
  path: [number, number][];
  /** 弧線中點（t = 0.5），雙劍放這裡 */
  mid: [number, number];
}

const MAX_LAT = 85;

export function conflictArc(from: [number, number], to: [number, number], samples = 48, bow = 0.22): ConflictArc {
  const [x0, y0] = from;
  let [x2, y2] = to;
  if (x2 - x0 > 180) x2 -= 360;
  else if (x2 - x0 < -180) x2 += 360;
  const dx = x2 - x0;
  const dy = y2 - y0;
  const len = Math.hypot(dx, dy);
  // 垂直向量（-dy, dx）取往北的一側
  let px = -dy;
  let py = dx;
  if (py < 0 || (py === 0 && px < 0)) {
    px = -px;
    py = -py;
  }
  const n = len === 0 ? 1 : len;
  const cx = (x0 + x2) / 2 + (px / n) * len * bow;
  const cy = Math.min(MAX_LAT, (y0 + y2) / 2 + (py / n) * len * bow);
  const at = (t: number): [number, number] => {
    const u = 1 - t;
    const x = u * u * x0 + 2 * u * t * cx + t * t * x2;
    const y = u * u * y0 + 2 * u * t * cy + t * t * y2;
    return [round(x), round(Math.max(-MAX_LAT, Math.min(MAX_LAT, y)))];
  };
  const path: [number, number][] = [];
  for (let i = 0; i <= samples; i++) path.push(at(i / samples));
  return { path, mid: at(0.5) };
}

/** 讓弧線落在離地圖中心最近的那一份世界副本（360 度的整數倍平移），避免跨換日線時畫到畫面外。 */
export function worldShift(midLng: number, centerLng: number): number {
  return Math.round((centerLng - midLng) / 360) * 360;
}

const round = (v: number) => Math.round(v * 1e4) / 1e4;

/**
 * 雙劍錯開（Tai 2026-10-31）：多條弧線幾乎重疊時（例：美國→德、義、羅、保、匈），中點的雙劍會疊在一起。
 * 依序擺放：沒有弧線的圖示固定不動；有弧線的先試中點，與已擺的圖示距離小於 minDist 像素時，
 * 沿著自己的弧線往兩側找取樣點（中點 ±step、±2step…），找到第一個不重疊的位置；都不行就留在中點。
 * 回傳每個圖示的像素位置（順序與輸入相同），雙劍一定在自己的弧線上。
 */
export function staggerOnArcs(
  items: { x: number; y: number; path: { x: number; y: number }[] | null }[],
  minDist = 34,
  step = 3,
  inside: (p: { x: number; y: number }) => boolean = () => true,
): { x: number; y: number }[] {
  const out: ({ x: number; y: number } | null)[] = items.map((it) => (it.path?.length ? null : { x: it.x, y: it.y }));
  const placed = out.filter((p): p is { x: number; y: number } => !!p);
  const free = (p: { x: number; y: number }) => placed.every((q) => Math.hypot(p.x - q.x, p.y - q.y) >= minDist);
  items.forEach((it, i) => {
    const path = it.path;
    if (!path?.length) return;
    const mid = Math.floor((path.length - 1) / 2);
    // 候選：中點，再往兩側；中點在可視區外時（弧線太長、鏡頭框不下），改用弧線上離中點最近、仍在可視區內的取樣點
    const order: number[] = [mid];
    for (let d = 1; d <= path.length; d++) order.push(mid + d, mid - d);
    const cands = order.filter((j) => j >= 0 && j < path.length && inside(path[j]));
    let pick: { x: number; y: number } = cands.length ? path[cands[0]] : { x: it.x, y: it.y };
    if (!free(pick)) {
      const base = cands.length ? cands[0] : mid;
      const lim = Math.floor((path.length - 1) * 0.35);
      for (let d = step; d <= lim; d += step) {
        const cand = [path[base + d], path[base - d]].find((p) => p && inside(p) && free(p));
        if (cand) {
          pick = cand;
          break;
        }
      }
    }
    out[i] = { x: pick.x, y: pick.y };
    placed.push(out[i]!);
  });
  return out as { x: number; y: number }[];
}

/**
 * 弧線放到哪一份世界副本：讓兩端中離地圖中心較近的那一端落在中心所在的副本（例：聚焦美國時，日本—美國弧的珍珠港端留在美國這一側）。
 */
export function worldShiftArc(path: [number, number][], centerLng: number, focusEnd?: 0 | 1 | null): number {
  // 有被選政權那一端時，以那一端為準（弧線從被選政權出發，鏡頭也以它為中心）
  if (focusEnd === 0 || focusEnd === 1) return worldShift(path[focusEnd === 0 ? 0 : path.length - 1][0], centerLng);
  const ends = [path[0][0], path[path.length - 1][0]];
  let best = 0;
  let bestD = Infinity;
  for (const x of ends) {
    const k = worldShift(x, centerLng);
    const d = Math.min(...ends.map((e) => Math.abs(e + k - centerLng)));
    if (d < bestD) {
      bestD = d;
      best = k;
    }
  }
  return best;
}
