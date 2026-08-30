import type { FeatureCollection, MultiPolygon } from 'geojson';
import { computeRegimeAdjacency, groupRowsByRegime, type TerritoryFeatureProperties } from './territory-styling';

/**
 * 政權聚焦模式（任務 3.7，對應 PRD Story 2）的「同時期周邊政權清單」——重用圖著色也在
 * 用的同一套政權層級相鄰關係判斷（`territory-styling.ts` 的 `computeRegimeAdjacency()`：
 * 政權 A 任一筆疆域跟政權 B 任一筆疆域有實際拓撲相交才算相鄰），不是另外發明一套「周邊」
 * 定義——會需要不同顏色區分的政權，正好也是地理上真正相鄰、有互動可能的政權，語意一致。
 *
 * 純函式，不碰 MapLibre／DOM，方便單元測試；`focusedRegimeId` 不在這批疆域資料裡（理論上
 * 不該發生，除非點擊當下的年份跟聚焦政權的存續區間不重疊）時回傳空集合，不拋例外——
 * 呼叫端（`MapComponent`）自行決定沒有周邊政權時面板要顯示什麼文案。
 */
export function findNeighboringRegimeIds(
  featureCollection: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>,
  focusedRegimeId: string,
): Set<string> {
  const rowsByRegime = groupRowsByRegime(featureCollection);
  const adjacency = computeRegimeAdjacency(rowsByRegime);
  return adjacency.get(focusedRegimeId) ?? new Set();
}
