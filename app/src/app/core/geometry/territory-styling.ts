import { bbox, booleanIntersects } from '@turf/turf';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import { greedyColorAssignment } from './graph-coloring';

/** `GET /api/v1/territories` 回傳的 GeoJSON feature properties（見
    `api/Controllers/TerritoriesController.cs` 的 `ToFeatureCollection`）。 */
export interface TerritoryFeatureProperties {
  id: string;
  regimeId: string;
  startYear: number;
  endYear: number;
  isDisputed: boolean;
  /** 這個模組執行後才會被寫入——色格索引，對應 `TERRITORY_COLOR_SLOTS` 的陣列位置。 */
  colorSlot?: number;
}

/**
 * 把「相鄰計算」＋「圖著色」串起來，套用在一批疆域 GeoJSON feature 上，並把結果
 * （色格索引）直接寫回每個 feature 的 `properties.colorSlot`——MapLibre 的
 * paint expression 直接讀這個欄位，不用另外維護一份 id → 顏色的對照表。
 *
 * **圖著色的節點是「政權」，不是「單筆疆域記錄」**（2026-08-29 修正）：第一版直接把
 * `featureCollection` 裡每一筆疆域記錄當成圖著色的節點，一個政權若同時有多筆疆域記錄
 * （例如 I3 史觀分歧的兩個並存爭議版本，或核心/邊界拆成兩筆），這些記錄彼此幾何上
 * 互相重疊/相鄰，反而被圖著色演算法當成「這幾筆需要分開上色」，變成「同一個政權畫面上
 * 出現兩種顏色」的荒謬結果（使用者實機發現：蜀漢兩個爭議版本一個綠一個黃）。改成先依
 * `regimeId` 分組，相鄰關係在「政權」這個層級計算（只要政權 A 任一筆疆域跟政權 B 任一筆
 * 疆域有實際拓撲相交，這兩個政權就算相鄰），圖著色也在政權層級跑，結果再套用回該政權
 * 底下每一筆疆域記錄——同一個政權，不管底下有幾筆疆域記錄，永遠只有一個顏色。
 *
 * 純函式（`greedyColorAssignment` 本身也是純函式，這裡只是分組、算相鄰、串接跟屬性
 * 寫入），不碰 MapLibre／DOM，方便單元測試；也方便之後接時間拉桿時，疆域資料換了
 * 直接重新呼叫，並傳入 `previousAssignment` 維持顏色穩定性（見 graph-coloring.ts）。
 *
 * @returns 這次執行實際用到的 regimeId → 色格指派（也可以直接從 feature.properties
 *   讀，額外回傳是方便呼叫端下次要重新指派時當 previousAssignment 用）。
 */
export function assignTerritoryColorSlots(
  featureCollection: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>,
  slotCount: number,
  previousAssignment?: Map<string, number>,
): Map<string, number> {
  const rowsByRegime = groupRowsByRegime(featureCollection);
  const adjacency = computeRegimeAdjacency(rowsByRegime);
  const assignment = greedyColorAssignment(adjacency, slotCount, previousAssignment);

  for (const feature of featureCollection.features) {
    feature.properties.colorSlot = assignment.get(feature.properties.regimeId) ?? 0;
  }

  return assignment;
}

/** 把一批疆域 feature 依 `regimeId` 分組——`assignTerritoryColorSlots()`（圖著色）跟
    `regime-focus.ts` 的周邊政權查詢（任務 3.7）共用這個分組結果，不要各自重複寫一次
    同樣的分組迴圈。 */
export function groupRowsByRegime(
  featureCollection: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>,
): Map<string, MultiPolygon[]> {
  const rowsByRegime = new Map<string, MultiPolygon[]>();
  for (const feature of featureCollection.features) {
    const regimeId = feature.properties.regimeId;
    const rows = rowsByRegime.get(regimeId);
    if (rows) {
      rows.push(feature.geometry);
    } else {
      rowsByRegime.set(regimeId, [feature.geometry]);
    }
  }
  return rowsByRegime;
}

/**
 * 政權層級的相鄰關係：政權 A 底下任一筆疆域，跟政權 B 底下任一筆疆域只要有拓撲相交
 * （邊界接觸或範圍重疊都算，跟 `territory-adjacency.ts` 的 `computeAdjacency()`
 * 同一個判斷標準），這兩個政權就算相鄰，需要不同色格。**同一個政權自己底下的多筆
 * 疆域記錄之間互相重疊/相鄰，不會被當成需要分開上色**——因為這個函式一開始就是
 * 用「政權」當節點，同政權的記錄從沒被拿來跟自己比較。
 *
 * 效能：先用每個政權所有疆域記錄合併起來的 bounding box 粗篩，只對候選對做精確的
 * 逐筆拓撲相交測試。
 *
 * **匯出給 `regime-focus.ts` 重用**（任務 3.7）：政權聚焦模式的「周邊政權清單」就是
 * 這裡算出來的相鄰關係——不是另外發明一套「周邊」定義，跟圖著色用同一套判斷標準，
 * 語意一致（會需要不同顏色區分的政權，正好也是地理上真正相鄰、有互動可能的政權）。
 */
export function computeRegimeAdjacency(rowsByRegime: Map<string, MultiPolygon[]>): Map<string, Set<string>> {
  const regimeIds = [...rowsByRegime.keys()];
  const adjacency = new Map<string, Set<string>>();
  for (const id of regimeIds) {
    adjacency.set(id, new Set());
  }

  const boxesByRegime = new Map<string, number[]>();
  for (const [regimeId, geometries] of rowsByRegime) {
    boxesByRegime.set(regimeId, mergeBoxes(geometries.map((g) => bbox(g))));
  }

  for (let i = 0; i < regimeIds.length; i++) {
    for (let j = i + 1; j < regimeIds.length; j++) {
      const regimeA = regimeIds[i];
      const regimeB = regimeIds[j];
      if (!bboxesOverlap(boxesByRegime.get(regimeA)!, boxesByRegime.get(regimeB)!)) {
        continue;
      }

      const rowsA = rowsByRegime.get(regimeA)!;
      const rowsB = rowsByRegime.get(regimeB)!;
      const isAdjacent = rowsA.some((a) => rowsB.some((b) => booleanIntersects(a, b)));
      if (isAdjacent) {
        adjacency.get(regimeA)!.add(regimeB);
        adjacency.get(regimeB)!.add(regimeA);
      }
    }
  }

  return adjacency;
}

function mergeBoxes(boxes: number[][]): number[] {
  return boxes.reduce((merged, box) => [
    Math.min(merged[0], box[0]),
    Math.min(merged[1], box[1]),
    Math.max(merged[2], box[2]),
    Math.max(merged[3], box[3]),
  ]);
}

function bboxesOverlap(a: number[], b: number[]): boolean {
  // [minX, minY, maxX, maxY]
  return a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3];
}

/**
 * 組出 MapLibre `fill-color` paint expression：依 `feature.properties.colorSlot`
 * 對照到 `colors` 陣列裡對應索引的實際色碼。回傳型別故意用 `unknown[]`（MapLibre 的
 * expression 型別在 style spec 裡是遞迴的 tuple union，直接標註太脆弱），呼叫端
 * 賦值給 `fill-color` 時交給 MapLibre 自己的型別檢查。
 */
export function buildColorSlotMatchExpression(colors: readonly string[]): unknown[] {
  return ['match', ['get', 'colorSlot'], ...colors.flatMap((hex, i) => [i, hex]), colors[0]];
}
