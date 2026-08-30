import {
  DISPUTE_HATCH_DARKEN_AMOUNT,
  DISPUTE_HATCH_LINE_WIDTH,
  DISPUTE_HATCH_TILE_SIZE,
} from '../design/territory-dispute-constants';

/**
 * 疆域重疊區的斜線網底圖樣（PRD §5「斜線網底配色」，任務 3.5 完成後補上——使用者實際
 * 看到蜀漢/東吳在荊州爭議期間（208-215 年）的疆域重疊、問「這是什麼意思」才發現資料裡
 * 有 `isDisputed` 欄位、但前端從沒把它畫出來，看起來就像資料錯誤重疊）。**Phase 1
 * 定案用 Canvas Pattern，不是 WebGL Shader**（見 PRD §5/§9 風險表：Shader 方案在大量
 * 重疊區同時繪製時有效能疑慮，Phase 1 用 Canvas Pattern 規避，成熟階段再評估升級）。
 *
 * **2026-08-29 修正過一次語意**：第一版直接讀 `regime_territories.is_disputed` 整筆
 * 記錄畫網底，同色相加深一階（tone-on-tone）。使用者指出這樣邏輯站不住腳——例如蜀漢
 * 借荊州期間，西邊完全沒人質疑的部分也會被畫成整塊爭議，類比二戰後英法美蘇瓜分德國
 * （佔領區邊界是條約明訂，沒有史料分歧）會荒謬地把整個佔領區都畫成爭議。改成不依賴
 * `is_disputed` 這個手動標記的旗標，**改用即時計算的幾何交集**（見
 * `territory-overlap.ts`）決定斜線該畫在哪——只有真的有面積重疊的那塊地才畫。既然重疊
 * 區可能同時牽涉兩個以上不同色相的政權（不像修正前那樣一定對應到單一政權自己的顏色），
 * 這裡的網底改用**單一色**，不再是 tone-on-tone——重疊區本身代表「這裡有一個以上的
 * 宣稱」，不屬於任何單一政權的識別色。
 *
 * **2026-08-30 再調整一次底色**：原本這個單一色借用 `--wl-territory-border` 中性灰
 * （純結構語意，跟邊界線同色），後來改成 design-tokens.scss 新增的 `--wl-dispute-*`
 * 紅色階（錨點沿用既有的 `--wl-status-critical`）——「這裡有政權主張衝突」是需要被
 * 看見的內容語意，不該跟純結構性的邊界線共用同一個中性色 token。這個檔案本身完全
 * 不關心呼叫端傳進來的 `baseColorHex` 是什麼顏色，只負責把它加深一階畫網底，所以
 * 這次調色不需要改這個檔案的邏輯，只需要呼叫端（map.ts）改傳色。
 *
 * **2026-08-31（任務 3.15）**：tile 尺寸/線寬/加深比例改讀
 * `core/design/territory-dispute-constants.ts`，不再是這個檔案自己寫死的數字——
 * `map.ts` 的網底相關圖層/圖片/來源 id 字串也搬到同一份常數檔，兩邊共用同一個真相
 * 來源，避免其中一處調整時忘記同步改另一處。
 */

/** 簡單的線性 RGB darken，不是 design-tokens.scss 用的 OKLab 數學——這裡只是把中性色
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
export function createDiagonalHatchImageData(baseColorHex: string, size = DISPUTE_HATCH_TILE_SIZE): ImageData {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    throw new Error('createDiagonalHatchImageData: 無法取得 2d context');
  }

  ctx.strokeStyle = darkenHex(baseColorHex, DISPUTE_HATCH_DARKEN_AMOUNT);
  ctx.lineWidth = DISPUTE_HATCH_LINE_WIDTH;
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
