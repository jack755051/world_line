import { bbox, featureCollection, intersect } from '@turf/turf';
import type { MultiPolygon, Polygon } from 'geojson';
import type { Territory } from './territory-adjacency';

/**
 * 計算一批疆域兩兩之間**實際幾何重疊**的區域，回傳交集多邊形陣列——不是「有沒有相鄰」
 * （那是 territory-adjacency.ts 的 `computeAdjacency()`，只回答 true/false，邊界接觸
 * 也算相鄰，服務對象是圖著色演算法），這裡回傳真正有面積的交集，給爭議控制區斜線網底用。
 *
 * **2026-08-29 拍板，取代原本「靠 `regime_territories.is_disputed` 整筆記錄畫網底」的
 * 做法**：使用者指出「一整筆爭議記錄就整塊畫斜線」邏輯上站不住腳——例如蜀漢在 208-215
 * 年借荊州期間，西邊（跟東吳完全不重疊的部分）從沒被任何人質疑過，只有跟東吳宣稱重疊
 * 的那一小塊才是真正的爭議地帶；若整筆記錄都畫網底，類比到二戰後英法美蘇瓜分德國，
 * 佔領區邊界是條約明訂、沒有史料分歧，套用同一套判斷會荒謬地把整個佔領區都畫成爭議。
 * 改成即時算幾何交集，斜線只出現在真正重疊的地方，不管未來匯入任何真實史料、任兩個
 * 政權疆域重疊，都會自動正確顯示，不需要再手動判斷或標記哪一筆該標 `is_disputed`。
 *
 * 不分「同政權不同版本」（I3 史觀分歧，例如蜀漢自己兩個爭議版本互相重疊）還是「不同
 * 政權」（真正的邊界爭奪，例如蜀漢跟東吳的宣稱重疊）——兩種情況都代表「這塊地同時有
 * 一個以上的宣稱」，語意上是同一件事，用同一套機制處理，不特別區分。
 *
 * 效能：先用 bounding box 粗篩，只對 bbox 有重疊的候選對呼叫真正的幾何交集運算
 * （`turf.intersect()` 比 `booleanIntersects()` 貴很多），避免 O(n²) 全對全都跑。
 * 邊界只是接觸（不是真的有面積重疊）的情況，`turf.intersect()` 本身就會回傳 `null`
 * （已用測試驗證），不需要另外過濾。
 */
export function computeTerritoryOverlaps(territories: Territory[]): (Polygon | MultiPolygon)[] {
  const boxes = territories.map((t) => bbox(t.geometry));
  const overlaps: (Polygon | MultiPolygon)[] = [];

  for (let i = 0; i < territories.length; i++) {
    for (let j = i + 1; j < territories.length; j++) {
      if (!bboxesOverlap(boxes[i], boxes[j])) {
        continue;
      }

      const a = { type: 'Feature' as const, properties: {}, geometry: territories[i].geometry };
      const b = { type: 'Feature' as const, properties: {}, geometry: territories[j].geometry };
      const result = intersect(featureCollection([a, b]));
      if (result) {
        overlaps.push(result.geometry);
      }
    }
  }

  return overlaps;
}

function bboxesOverlap(a: number[], b: number[]): boolean {
  // [minX, minY, maxX, maxY]
  return a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3];
}
