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
