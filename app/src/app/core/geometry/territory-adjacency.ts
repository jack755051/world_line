import { bbox, booleanIntersects } from '@turf/turf';
import type { MultiPolygon } from 'geojson';

export interface Territory {
  id: string;
  geometry: MultiPolygon;
}

/**
 * 計算一組疆域彼此的相鄰關係（邊界接觸或範圍重疊都算相鄰）。
 *
 * 用的是向量幾何的拓撲相交測試（Turf.js `booleanIntersects`），不是格子/像素資料常見的
 * 「四鄰（4-connectivity）」概念——那是給網格資料用的技術，這裡的疆域是 PostGIS
 * MultiPolygon 向量圖形，兩者不能混用。
 *
 * 效能：先用 bounding box 粗篩（便宜），只對 bbox 有重疊的候選對做精確幾何測試（較貴），
 * 避免 O(n²) 全對全都跑完整拓撲運算。
 *
 * @returns 從疆域 id 對應到「與它相鄰的疆域 id 集合」的 Map。
 */
export function computeAdjacency(territories: Territory[]): Map<string, Set<string>> {
  const adjacency = new Map<string, Set<string>>();
  for (const t of territories) {
    adjacency.set(t.id, new Set());
  }

  const boxes = territories.map((t) => bbox(t.geometry));

  for (let i = 0; i < territories.length; i++) {
    for (let j = i + 1; j < territories.length; j++) {
      if (!bboxesOverlap(boxes[i], boxes[j])) {
        continue;
      }
      if (booleanIntersects(territories[i].geometry, territories[j].geometry)) {
        adjacency.get(territories[i].id)!.add(territories[j].id);
        adjacency.get(territories[j].id)!.add(territories[i].id);
      }
    }
  }

  return adjacency;
}

function bboxesOverlap(a: number[], b: number[]): boolean {
  // [minX, minY, maxX, maxY]
  return a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3];
}
