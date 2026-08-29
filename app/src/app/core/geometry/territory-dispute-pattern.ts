/**
 * 爭議控制區的斜線網底圖樣（PRD §5「斜線網底配色」，任務 3.5 完成後補上——使用者實際
 * 看到蜀漢/東吳在荊州爭議期間（208-215 年）的疆域重疊、問「這是什麼意思」才發現資料裡
 * 早就有 `isDisputed` 欄位，但前端從沒把它畫出來，看起來就像資料錯誤重疊）。**Phase 1
 * 定案用 Canvas Pattern，不是 WebGL Shader**（見 PRD §5/§9 風險表：Shader 方案在大量
 * 爭議區同時繪製時有效能疑慮，Phase 1 用 Canvas Pattern 規避，成熟階段再評估升級）。
 *
 * 畫 45 度對角線，色相跟這塊疆域自己的識別色一樣、只是更深一階（tone-on-tone），不是
 * 另外挑一個全域固定的網底顏色——這樣同一個政權的爭議疆域跟非爭議疆域一眼就能看出是
 * 同一個政權（色相沒變），只是多了一層「有爭議」的視覺標記，不會誤以為是另一個政權。
 */

/** 簡單的線性 RGB darken，不是 design-tokens.scss 用的 OKLab 數學——這裡只是同一色相
    自己加深一階的裝飾性網底線，不需要拿來跟別的色相比對色盲安全性，不需要那個精確度。 */
export function darkenHex(hex: string, amount: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const dr = Math.round(r * (1 - amount));
  const dg = Math.round(g * (1 - amount));
  const db = Math.round(b * (1 - amount));
  return `rgb(${dr}, ${dg}, ${db})`;
}

/**
 * 畫一張可以無縫拼接的 45 度斜線 tile，回傳 MapLibre `map.addImage()` 需要的 `ImageData`。
 *
 * **不在單元測試涵蓋範圍**：JSDOM 測試環境沒有真的 Canvas 2D context（`getContext('2d')`
 * 回傳 `null`，除非額外裝 `canvas` npm 套件）——為了一個裝飾性網底裝一個原生編譯依賴不
 * 划算，跟 MapLibre/WebGL 本身在測試裡被 mock 掉是同一個處理原則；已在瀏覽器/容器實際
 * 部署驗證過會正確渲染。這個檔案只有 `darkenHex()`（純函式，不碰 Canvas）有單元測試。
 */
export function createDiagonalHatchImageData(baseColorHex: string, size = 8): ImageData {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    throw new Error('createDiagonalHatchImageData: 無法取得 2d context');
  }

  ctx.strokeStyle = darkenHex(baseColorHex, 0.35);
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  // 主對角線 + 兩側各一條偏移半格的對角線，讓 tile 邊界拼接時線條視覺連續，不會在
  // 相鄰兩塊 tile 交界處斷開。
  ctx.moveTo(0, size);
  ctx.lineTo(size, 0);
  ctx.moveTo(-size / 2, size / 2);
  ctx.lineTo(size / 2, -size / 2);
  ctx.moveTo(size / 2, size * 1.5);
  ctx.lineTo(size * 1.5, size / 2);
  ctx.stroke();

  return ctx.getImageData(0, 0, size, size);
}

/** 給定色格索引產生對應的 MapLibre image id——跟 `territories-fill` 用同一組色格索引，
    不用另外維護一份「爭議網底該用哪個顏色」的對照表。 */
export function territoryHatchImageId(colorSlot: number): string {
  return `territory-hatch-${colorSlot}`;
}
