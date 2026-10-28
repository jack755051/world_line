# M0 第一筆真實資料：1940-07-15 德國在法國本土的軍事佔領區

> **狀態：DRAFT — 待 Tai 檢查。尚未寫入 appdb_ww2。**
> 檢查通過後才執行 `python3 send_seed.py --send`。預設只做 dry-run。

## 來源與授權

| 角色 | 來源 | 種類 | 授權 | 用途 |
|---|---|---|---|---|
| primary | Éditions André Leconte《Nouvelle carte de France par régions administratives au 1.800.000e (ligne de démarcation)》，Musée de la Libération de Paris – musée Jean Moulin 館藏號 2015.3.1.230，印行於 1940–1943 | map | `cc0`（Paris Musées 開放內容） | 用來目視核對分界線 |
| date_check | USMA West Point Atlas WWII Europe, **Map 15**「Western Europe 1940: Campaign in the West, The Pursuit, 13–25 June」 | atlas_map | `us_federal_pd`（17 U.S.C. §105） | 佐證 6/25 德軍推進範圍超過分界線；**圖上沒有分界線** |
| auxiliary_geometry | Département de l'Ain「Ligne de démarcation」（data.gouv.fr） | dataset | `licence_ouverte_2` | 分界線座標 |
| auxiliary_geometry | Natural Earth 1:10m Admin 0 Countries | dataset | `public_domain`（代碼待拍板） | 法國本土外框（現代國界） |

**West Point 圖集裡找不到分界線圖。** USMA WWII Europe/Med 圖集共 91 張，Map 15、33、43 和 Overview 都沒有畫 1940 分界線，所以 primary 改用同屬允許清單（CC0）的 Leconte 分界線圖。這點要請 Tai 確認。

## 描繪方法

1. 從 Natural Earth 10m 取法國本土部分（box −6,41,10,52）。
2. 用 Ain 分界線（兩端各延長 0.05°）切開本土。不含 Vichy (3.43, 46.13) 的一側即為佔領區，包含巴黎一側和 Gex 地區的飛地（約 372 km²，只以一點與主體相接，保留為獨立 part）。
3. 島嶼歸佔領區；地中海島嶼（含 Corse）除外。
4. 座標四捨五入到 1e-5°，並以 shapely 驗證幾何有效。
5. 把 Leconte 圖以 27 個控制點（城市圓點、岬角）配準，用二次多項式，RMSE ≈ 13 px ≈ 2.4 km。再把描線疊上去目視比對。

結果：MultiPolygon，8 個 part，5,282 個頂點，約 300,789 km²，佔法國本土的 54.9%。

## 精度限制

- 外框用的是**現代**國界和 1:10M 海岸線，海岸誤差達公里級。1940 年的 Alsace-Moselle 邊界與現代相同，影響不大。
- 分界線取自 Ain 資料集（1:200,000 等級）。1940–42 年間的局部調整沒有建模。
- Leconte 配準誤差約 2–3 km，只能用來目視核對，不是座標來源。

## 範圍（待決）

- 包含：北部兩省（Nord、Pas-de-Calais，歸布魯塞爾軍事管理）、Alsace-Moselle、東北禁區、大西洋沿岸帶。是否拆成獨立紀錄，待 Tai 決定。
- 不含：自由區、義大利佔領區、海峽群島（英國王室屬地，另立紀錄）。

## 檔案

- `occupied-zone-1940-07-15.geojson`：描好的佔領區。
- `requests/`：POST 請求，依檔名順序送出。`{{...}}` 由前一步回應的 id 取代。
- `send_seed.py`：送出工具，預設 dry-run，key 從 `.env` 安靜讀取。
- `build/`：產生幾何、預覽、請求的腳本，以及配準控制點。腳本的路徑指向 box 的 `/workspace/world-line-ww2/trace/`，大圖檔不 commit。
- `preview-overview.png`：Natural Earth 底圖總覽。
- 疊在 Leconte 上的大張預覽只放在 box：`/workspace/world-line-ww2/trace/preview-overlay-leconte.png`，另有 `preview-detail-*.png`。
- 測試 `SeedFrance1940Tests` 會把這批請求送到 Testcontainers（不是 appdb_ww2），驗證 API 接受。
