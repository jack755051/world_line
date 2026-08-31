/**
 * 把經緯度換算成螢幕點擊座標的最小 Web Mercator 投影公式——跟 `map.ts` 的
 * `initMap()` 固定的 `center: [110, 32], zoom: 3` 配對使用（見該檔案說明：暫定中心點，
 * 之後接上疆域範圍自動置中時再改成動態計算）。E2E 測試需要真的點擊地圖上的政權疆域
 * 觸發 `MapComponent.handleMapClick()`，MapLibre 沒有提供「幫我點某個經緯度」的測試
 * API，只能自己算出對應的螢幕像素、用 Playwright 的 `page.mouse.click()` 點下去。
 *
 * 算法跟 MapLibre 內部一致：Web Mercator，`worldSize = 512 * 2^zoom`，這是 tile-based
 * 地圖的標準投影公式，不是這個專案自創的近似值。
 */
export function projectLngLat(lng: number, lat: number, zoom: number): { x: number; y: number } {
  const worldSize = 512 * 2 ** zoom;
  const x = (worldSize * (lng + 180)) / 360;
  const latRad = (lat * Math.PI) / 180;
  const mercY = 0.5 - Math.log(Math.tan(Math.PI / 4 + latRad / 2)) / (2 * Math.PI);
  const y = worldSize * mercY;
  return { x, y };
}

export const MAP_CENTER: { lng: number; lat: number } = { lng: 110, lat: 32 };
export const MAP_ZOOM = 3;

/** 把「目標經緯度」換算成相對於地圖畫布中心的像素偏移量——呼叫端拿到 canvas 的
    `boundingBox()` 之後，加上這個偏移量就是可以直接丟給 `page.mouse.click()` 的
    頁面座標。 */
export function projectOffsetFromCenter(lng: number, lat: number): { dx: number; dy: number } {
  const center = projectLngLat(MAP_CENTER.lng, MAP_CENTER.lat, MAP_ZOOM);
  const target = projectLngLat(lng, lat, MAP_ZOOM);
  return { dx: target.x - center.x, dy: target.y - center.y };
}
