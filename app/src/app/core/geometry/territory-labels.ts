import { centroid } from '@turf/turf';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import type { TerritoryFeatureProperties } from './territory-styling';

/**
 * 每個政權在目前這批疆域裡取一個標籤定位點（幾何中心點，Turf.js `centroid`）。
 * 同一個政權可能同時有多筆疆域快照（例如 I3 並存爭議版本），這裡只取第一筆遇到的
 * feature 當代表——避免同一個政權名稱在畫面上重複標好幾次。
 *
 * 純函式，不碰 MapLibre／DOM，方便單元測試；實際渲染成 HTML marker 是 `MapComponent`
 * 的責任（見 map.ts）——**這裡刻意不用 MapLibre 原生 symbol 圖層的 `text-field`**，
 * 因為那需要 glyphs（字型 PBF）服務，這個專案刻意不接外部瓦片/字型服務（同任務 3.2
 * 的底圖決策：零外部依賴），CJK 字型的 glyphs 又特別龐大，自架也不划算。改用
 * `maplibregl.Marker` 掛真正的 HTML 元素，直接吃瀏覽器原生字型渲染跟這個專案自己的
 * design tokens，不需要額外服務。
 */
export function computeTerritoryLabelPoints(
  featureCollection: FeatureCollection<MultiPolygon, TerritoryFeatureProperties>,
): Map<string, [number, number]> {
  const pointByRegimeId = new Map<string, [number, number]>();

  for (const feature of featureCollection.features) {
    const regimeId = feature.properties.regimeId;
    if (pointByRegimeId.has(regimeId)) {
      continue; // 同一政權已經取過標籤點，不重複標
    }
    const [lon, lat] = centroid(feature.geometry).geometry.coordinates;
    pointByRegimeId.set(regimeId, [lon, lat]);
  }

  return pointByRegimeId;
}
