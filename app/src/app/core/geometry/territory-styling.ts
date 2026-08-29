import type { FeatureCollection, MultiPolygon } from 'geojson';
import { computeAdjacency, type Territory } from './territory-adjacency';
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
 * 純函式（`computeAdjacency`/`greedyColorAssignment` 本身也是純函式，這裡只是串接
 * 跟屬性寫入），不碰 MapLibre／DOM，方便單元測試；也方便之後接時間拉桿時，疆域資料
 * 換了直接重新呼叫，並傳入 `previousAssignment` 維持顏色穩定性（見 graph-coloring.ts）。
 *
 * @returns 這次執行實際用到的 id → 色格指派（也可以直接從 feature.properties 讀，
 *   額外回傳是方便呼叫端下次要重新指派時當 previousAssignment 用）。
 */
export function assignTerritoryColorSlots(
  featureCollection: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>,
  slotCount: number,
  previousAssignment?: Map<string, number>,
): Map<string, number> {
  const territories: Territory[] = featureCollection.features.map((f) => ({
    id: f.properties.id,
    geometry: f.geometry,
  }));

  const adjacency = computeAdjacency(territories);
  const assignment = greedyColorAssignment(adjacency, slotCount, previousAssignment);

  for (const feature of featureCollection.features) {
    feature.properties.colorSlot = assignment.get(feature.properties.id) ?? 0;
  }

  return assignment;
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
