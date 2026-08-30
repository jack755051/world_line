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

/**
 * 「同時期、但不相鄰」的其他政權——對應這個對話裡使用者提出的第三塊清單需求：例如聚焦
 * 唐朝時，阿拉伯帝國不接壤（不會出現在 `findNeighboringRegimeIds()` 的結果），但兩者是
 * 同時期存在的政權，PRD §1 的核心動機（「同一個時間點上同時看到多個文明/政權」）講的
 * 就是這種案例，不是只有地理相鄰這一種關係值得呈現。
 *
 * 定義很單純：這批疆域資料裡除了聚焦政權自己、跟已經算出來的周邊政權清單以外，其餘
 * 政權全部算進來——不是重新查一次「全部政權」，用的就是呼叫端已經有的同一批
 * `featureCollection`（當年有效的疆域資料，本來就涵蓋地圖上所有政權，不只聚焦政權
 * 附近的）。
 *
 * **目前種子資料規模下，這個函式對任何聚焦目標大概率都會回傳空集合**——現有的漢/魏/
 * 蜀漢/吳/晉五個政權擠在同一小塊地理範圍，彼此兩兩之間幾乎都地理相鄰，不是這個函式
 * 邏輯有問題，是還沒有真正「同時期、不同地區」的政權資料可以示範（例如唐朝+阿拉伯帝國
 * 那種案例）——等之後真的匯入世界史資料，這個清單才會開始出現東西。
 */
export function findOtherContemporaryRegimeIds(
  featureCollection: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>,
  focusedRegimeId: string,
  neighborRegimeIds: ReadonlySet<string>,
): Set<string> {
  const others = new Set<string>();
  for (const feature of featureCollection.features) {
    const regimeId = feature.properties.regimeId;
    if (regimeId !== focusedRegimeId && !neighborRegimeIds.has(regimeId)) {
      others.add(regimeId);
    }
  }
  return others;
}
