# Stitch 二戰設計稿（W1–W7）

由 Google Stitch 依 `docs/ww2-stitch.md` 的 prompt 產出、套用 `design/stitch/DESIGN.md`（Atlas Paper）的第一版畫面。只供設計參考，**不是實作規格，也不是史料**。

> ⚠️ **此版尚未修正。** 畫面中的地圖都是示意圖，邊界、範圍與位置不代表任何史實判斷；畫面上的數字、編號、日期也不可當作史料引用。

## 檔案清單

每張畫面通常有三種檔案：`.png`（首屏截圖，1440×900）、`-full.png`（整頁截圖）、`.html`（Stitch 匯出的原始碼）。

| 畫面 | 內容（見 `docs/ww2-stitch.md`） | 檔案 |
|---|---|---|
| 校正卡 | Atlas Paper 元件與地圖編碼校正卡（v2） | `atlas-calibration-v2.png`、`atlas-calibration-v2.html` |
| W1 | 主地圖・實際控制（1940-07-15） | `w1.png`、`w1-full.png`、`w1.html` |
| W2 | 推估過渡與資料缺 | `w2.png`、`w2-full.png`、`w2.html` |
| W3 | 主權檢視＋地區主權詳情 | `w3.png`、`w3-full.png`、`w3.html` |
| W4 | 政權聚焦面板（維琪法國） | `w4.png`、`w4-full.png`、`w4.html` |
| W5 | 事件詳情＋爭議點（二戰起點） | `w5.png`、`w5-full.png`、`w5.html` |
| W6 | 來源 popover | `w6.png`、`w6.html`（Stitch 沒有產出 `w6-full.png`） |
| W7 | 全域與錯誤狀態（總覽） | `w7.png` |
| W7-1 | 首次載入 | `w7-1-first-load.png`、`w7-1-first-load.html` |
| W7-2 | API 離線 | `w7-2-api-offline.png`、`w7-2-api-offline.html` |
| W7-3 | 找不到頁面 | `w7-3-not-found.png`、`w7-3-not-found.html` |
| W7-4 | 無效日期 | `w7-4-invalid-date.png`、`w7-4-invalid-date.html` |
| W7-5 | 早期時段（資料範圍之前） | `w7-5-early-period.png`、`w7-5-early-period.html` |
| 封存 | 舊 Slate 版校正卡，已由 Atlas Paper 取代 | `archive/calibration.png` |

## 已知偏差（尚未修正）

實作時以 `design/stitch/DESIGN.md`、PRD 和憲法為準，不要照抄以下內容：

1. **第三色 `#006b91`**：Stitch 自行加入的藍色，不在 Atlas Paper 色票裡。
2. **Material 圖示**：畫面使用 Material Symbols，不是 DESIGN.md 指定的圖示風格。
3. **朱紅過度使用**：朱紅應只出現在按鈕與選取狀態，畫面中用在太多地方。
4. **雙時間軸**：部分畫面同時出現兩條時間軸，應只有一條。
5. **W2、W5 頂欄日期錯誤**：頂欄顯示的日期與該畫面設定的日期不符。
6. **編造的數字和編號**：例如 W5「動員逾一億」、W6「338,000 km²」，以及其他圖號、編號，都是 Stitch 自行編造，**不可當作史料**。

## 備註

- 地圖為示意圖，不代表任何疆域或控制範圍的判定。
- `.html` 為 Stitch 匯出原樣，會從 Google Fonts 等外部網址載入資源；`atlas-calibration-v2.html` 另外夾帶 Stitch 編輯器的程式碼。
