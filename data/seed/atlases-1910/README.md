# 1910 年前後的地圖集（期初既有疆界的出處）

日期：2026-11-14。兩套公有領域的學術地圖集，登記為來源，用來替「1908 年起點時既有」的國界附引文（docs/source-rules.md D5）。

| 代號 | 地圖集 | 等級 | 家族 |
|---|---|---|---|
| SRC_CMHA_1912 | The Cambridge Modern History Atlas（Cambridge University Press, 1912） | B | cambridge-modern-history-atlas |
| SRC_SHEPHERD_1911 | William R. Shepherd, Historical Atlas（Henry Holt, 1911） | B | shepherd-historical-atlas |

兩套是不同家族，同一筆國界兩套都相符時，就達到「兩個獨立家族的 B」的已查證門檻。

這一批只登記來源，**沒有替任何國界附引文**。附引文之前要實際比對圖版與資料庫裡的形狀，逐筆記錄在 `data/seed/source-grading/baseline-borders.csv`；圖版畫的是 1910–1911 年，還要確認 1908 年到那時之間沒有變動。

全文掃描在 archive.org（網址見各來源）。德州大學圖書館也有單張圖版，但該站有防機器人驗證，程式讀不到，沒有繞過。

送出：`python3 send_seed.py --base http://127.0.0.1:5052 --env <開發用 env 檔> [--send]`，預設只預演；只寫開發庫。
