/**
 * 政權識別色的實際色碼（2026-08-29 拍板，任務 3.5 動工時定案——之前刻意擱置，見
 * design-tokens.scss、graph-coloring.ts 開頭說明）。
 *
 * 來源：dataviz 技能驗證過的預設 8 色分類色盤（skill `references/palette.md`）。
 * 第 1 格（藍）、第 2 格（橙）保留給 UI 主色/次色（design-tokens.scss 的
 * `--wl-primary-*`/`--wl-secondary-*`），不進這個陣列。
 *
 * **色盲安全性重新驗證，修正了先前 PRD 記錄的一個誤判**：先前記錄「因為這裡是真正算
 * 相鄰關係後才分配，只需要『相鄰配對』等級的寬鬆標準，8 色都能過」——這個推論套用錯了
 * dataviz 技能的 `--pairs adjacent` 模式。那個模式是給堆疊圖/折線圖這種「畫面上只有
 * 固定順序相鄰的兩個顏色會真的貼在一起」的圖表用的；地圖是任意拓撲，兩塊疆域會不會
 * 實際相鄰是史料資料決定的，不是色盤陣列順序決定的——任何兩個色格理論上都可能在某張
 * 地圖上真的碰在一起，正確的標準其實是 `--pairs all`（嚴格版），不是 adjacent。
 *
 * 實測：分類色第 3-8 格（aqua/yellow/magenta/green/violet/red）六色跑 all-pairs 會
 * FAIL（red 對 magenta 只有 13.2 ΔE，低於 15 的下限）；拿掉 magenta 之後剩下五色
 * （aqua/yellow/green/violet/red）all-pairs 全數過關（CVD 落在 6-8 的 WARN 帶，依
 * 規則需要「次要編碼」才合法——這個專案本來就有：疆域邊界統一中性色 + 點擊/hover
 * 顯示名稱是身份辨識的主要管道，色彩本來就只是輔助，滿足這個要求，見 PRD §6）。
 *
 * 5 色仍遠高於四色定理需要的下限（4）。跟 `graph-coloring.ts` 的 `slotCount` 參數對應
 * ——這裡的陣列長度就是實際要傳入的 `slotCount`，不要兩處各自維護數字。
 */
export const TERRITORY_COLOR_SLOTS: readonly string[] = [
  '#1baf7a', // aqua（分類色第 3 格）
  '#eda100', // yellow（分類色第 4 格）
  '#008300', // green（分類色第 6 格，跳過 magenta 第 5 格——all-pairs 驗證未過）
  '#4a3aa7', // violet（分類色第 7 格）
  '#e34948', // red（分類色第 8 格）
];
