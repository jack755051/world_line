import type { FeatureCollection, Point } from 'geojson';

export interface Box { x: number; y: number; w: number; h: number; }

/** 矩形碰撞：中心距離小於寬度之和的一半即為重疊。 */
export function rectsOverlap(a: Box, b: Box): boolean {
  return Math.abs(a.x - b.x) * 2 < a.w + b.w && Math.abs(a.y - b.y) * 2 < a.h + b.h;
}

/**
 * 計算地圖上所有首都的保留框（像素）：
 * - 每座首都貢獻一個圓點框（10×10 px，圓點投影點為中心）。
 * - zoom ≥ 3.5 時額外加上名稱框（charCount×11 寬、14 高，放在圓點右側）。
 * - 世界副本：取離地圖中心 mapCenterLng 最近的副本。
 */
export function capitalObstacleBoxes(
  capitals: FeatureCollection | null,
  project: (lngLat: [number, number]) => { x: number; y: number },
  mapCenterLng: number,
  zoom: number,
): Box[] {
  if (!capitals) return [];
  const showLabel = zoom >= 3.5;
  const boxes: Box[] = [];
  for (const f of capitals.features) {
    if (f.geometry.type !== 'Point') continue;
    const [rawLng, lat] = (f.geometry as Point).coordinates as [number, number];
    // 取離地圖中心最近的世界副本
    const k = Math.round((mapCenterLng - rawLng) / 360) * 360;
    const lng = rawLng + k;
    const p = project([lng, lat]);
    // 圓點框：10×10 px，以投影點為中心
    boxes.push({ x: p.x, y: p.y, w: 10, h: 10 });
    if (showLabel) {
      const label = (f.properties as Record<string, unknown> | null)?.['label'] as string | undefined ?? '';
      const lw = Math.max(label.length * 11, 1);
      // 名稱框中心：圓點中心向右偏移（半圓點 5px + 半名稱框 lw/2）
      boxes.push({ x: p.x + 5 + lw / 2, y: p.y, w: lw, h: 14 });
    }
  }
  return boxes;
}

/**
 * 在 `shifts`（像素，預設 [0, -18, 18, -30, 30]）中找到最小的垂直位移 dy，
 * 使置中於 (cx, cy + dy)、大小 (w × h) 的矩形不與任何 obstacle 重疊。
 *
 * 返回位移量（0 代表原位無衝突），或 null（所有候選皆仍重疊→隱藏標籤）。
 */
export function avoidCapitals(
  cx: number,
  cy: number,
  w: number,
  h: number,
  obstacles: Box[],
  shifts: number[] = [0, -18, 18, -30, 30],
): number | null {
  for (const dy of shifts) {
    const box: Box = { x: cx, y: cy + dy, w, h };
    if (!obstacles.some((o) => rectsOverlap(box, o))) return dy;
  }
  return null;
}

// ─── 浮動 UI 障礙物 ──────────────────────────────────────────────────────────

/** 地圖上方浮動 UI 的 CSS selector 清單（聚焦遮罩與標籤層本身不在此列）。 */
export const UI_OBSTACLE_SELECTORS: readonly string[] = [
  '[data-testid="legend"]',
  '[data-testid="camp-layer-toggle"]',
  '[data-testid="map-incomplete-period-hint"]',
  '.maplibregl-ctrl-attrib',
  'wl-regime-sheet [data-testid="regime-sheet"]',
];

/**
 * 量測浮動 UI 元素相對於地圖容器的障礙框（加 6px 邊距）。
 * 量不到（元素不存在或 size=0）的項目略過；適合每次 placeLabels 呼叫一次。
 */
export function uiObstacleBoxes(containerEl: HTMLElement): Box[] {
  const cr = containerEl.getBoundingClientRect();
  const out: Box[] = [];
  for (const sel of UI_OBSTACLE_SELECTORS) {
    const el = document.querySelector(sel);
    if (!el) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    // 轉換到容器座標；中心座標
    const x = (r.left + r.right) / 2 - cr.left;
    const y = (r.top + r.bottom) / 2 - cr.top;
    out.push({ x, y, w: r.width + 12, h: r.height + 12 });
  }
  return out;
}

// ─── 網格候選點 ──────────────────────────────────────────────────────────────

/** 投影座標環（像素）的點在環內測試（射線法）。 */
export function pointInProjectedRing(
  px: number,
  py: number,
  ring: ReadonlyArray<{ x: number; y: number }>,
): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const { x: xi, y: yi } = ring[i];
    const { x: xj, y: yj } = ring[j];
    if (yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/**
 * 在 GeoJSON 外環（lng/lat）投影到像素後，取 gridSize×gridSize 網格，
 * 篩選落在多邊形內且中心點在地圖可視範圍內的點，
 * 依離 labelPx 由近到遠排序，最多回傳 maxCandidates 筆。
 *
 * 效能：每個 placeLabels 呼叫時才計算（地圖視角已知），每標籤最多 (gridSize+1)² 次 PIP 測試。
 */
export function gridCandidates(
  ring: number[][],
  project: (lngLat: [number, number]) => { x: number; y: number },
  labelPx: { x: number; y: number },
  mapWidth: number,
  mapHeight: number,
  gridSize = 5,
  maxCandidates = 30,
): Array<{ x: number; y: number }> {
  if (ring.length < 3) return [];
  // 投影外環到像素座標
  const projRing = ring.map(([lng, lat]) => project([lng, lat] as [number, number]));
  // 像素外框
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const { x, y } of projRing) {
    if (x < minX) minX = x; if (y < minY) minY = y;
    if (x > maxX) maxX = x; if (y > maxY) maxY = y;
  }
  const candidates: Array<{ x: number; y: number; d2: number }> = [];
  for (let gi = 0; gi <= gridSize; gi++) {
    for (let gj = 0; gj <= gridSize; gj++) {
      const x = minX + (maxX - minX) * gi / gridSize;
      const y = minY + (maxY - minY) * gj / gridSize;
      // 必須落在多邊形內
      if (!pointInProjectedRing(x, y, projRing)) continue;
      // 中心點需在地圖可視範圍內
      if (x < 0 || x > mapWidth || y < 0 || y > mapHeight) continue;
      const dx = x - labelPx.x;
      const dy = y - labelPx.y;
      candidates.push({ x, y, d2: dx * dx + dy * dy });
    }
  }
  candidates.sort((a, b) => a.d2 - b.d2);
  return candidates.slice(0, maxCandidates).map(({ x, y }) => ({ x, y }));
}

// ─── 標籤字型常數 ─────────────────────────────────────────────────────────────

/** 一般字體：每字元估計寬度（px）、框高、左右邊距。 */
export const LABEL_CHAR_PX = 14;
export const LABEL_H = 20;
export const LABEL_PAD = 8;
/** 縮小字體：對應 CSS class wl-regime-label--sm（10px font-size）。 */
export const LABEL_SMALL_CHAR_PX = 12;
export const LABEL_SMALL_H = 16;

/**
 * 為一個標籤找到可放置的位置（含縮小字回退）：
 *
 * 階段 1（一般字體）：在 labelPoint 垂直位移 shifts 中找第一個不與障礙物重疊的位置。
 * 階段 2（一般字體）：依序嘗試 gridPts 中每個網格候選點（dy=0）。
 * 階段 3（縮小字體 wl-regime-label--sm）：同樣再試一輪 shifts + gridPts。
 * 全部失敗則回傳 null（略去標籤）。
 *
 * @param gridPts 由 gridCandidates() 預先產生的網格候選像素座標（依離 labelPoint 由近到遠排序）。
 */
export function findLabelPlacement(
  cx: number,
  cy: number,
  textLen: number,
  obstacles: Box[],
  gridPts: ReadonlyArray<{ x: number; y: number }>,
  shifts: number[] = [0, -18, 18, -30, 30],
): { x: number; y: number; small: boolean } | null {
  for (const small of [false, true] as const) {
    const charPx = small ? LABEL_SMALL_CHAR_PX : LABEL_CHAR_PX;
    const h = small ? LABEL_SMALL_H : LABEL_H;
    const w = textLen * charPx + LABEL_PAD;

    // 階段 1：labelPoint ± shifts
    for (const dy of shifts) {
      const box: Box = { x: cx, y: cy + dy, w, h };
      if (!obstacles.some((o) => rectsOverlap(box, o))) {
        return { x: cx, y: cy + dy, small };
      }
    }
    // 階段 2：網格候選點
    for (const pt of gridPts) {
      const box: Box = { x: pt.x, y: pt.y, w, h };
      if (!obstacles.some((o) => rectsOverlap(box, o))) {
        return { x: pt.x, y: pt.y, small };
      }
    }
  }
  return null;
}
