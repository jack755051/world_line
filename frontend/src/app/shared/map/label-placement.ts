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
