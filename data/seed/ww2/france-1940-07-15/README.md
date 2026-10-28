# M0 第一批真實資料：1940 德國在法國本土的控制區（v2，各區獨立紀錄）

> **狀態：DRAFT v2 — 待 Tai 檢查。尚未寫入 appdb_ww2。**
> 預設 dry-run：`python3 send_seed.py`；檢查通過後 `--send`。東北禁區兩筆待決，另需 `--include-pending`。

## Tai 的決定（2026-10-28）

- 主要引用用 Leconte（CC0）；西點 Map 15 只當 date_check。
- 混合做法：分界線照原圖描，不沿省界；其他區塊用 1940 年省界組合；拆成獨立紀錄；每筆註明邊界來源。

## 各區紀錄

| 紀錄 | 區塊 | 面積 | 有效期間 [start, end) | 控制類型 | 邊界來源 |
|---|---|---|---|---|---|
| CR_MAIN | 本體軍事佔領區 | 228,776 km² | 1940-07-15 – 1942-11-11（起始不確定 06-25～07-15） | military_occupation | 分界線圖描＋東北線＋省界＋TRF 外框 |
| CR_NORD | 北部兩省（Nord、Pas-de-Calais，布魯塞爾軍管） | 12,439 km² | 1940-06-04 – 1944-07-16 | military_occupation | 省界組合（59＋62） |
| CR_AM_MIL | 亞爾薩斯－摩澤爾（CdZ 之前） | 14,581 km² | 1940-07-15 – 1940-08-02 | military_occupation | 省界組合（57＋67＋68） |
| CR_AM_CDZ | 亞爾薩斯－摩澤爾（CdZ，事實併入） | 同上 | 1940-08-02 – 1944-11-22（結束不確定至 1945-03） | direct_rule | 省界組合（57＋67＋68） |
| CR_ZI_PRE ⚠ | 東北禁區（東北線生效前） | 45,945 km² | 1940-07-15 – 1940-07-20 | military_occupation | 東北線（Perseus112）＋分界線＋省界 |
| CR_ZI ⚠ | 東北禁區（zone réservée） | 同上 | 1940-07-20 – 1942-11-11 | military_occupation | 同上 |

⚠ 表示 `requiresDecision`：primary 只能用 Perseus112 的現代自製圖（CC BY-SA），依 R7 精神不採用自製來源。

- 四個區塊彼此只共用邊界：在 1e-5° 網格上做疊合運算，兩兩交集面積為 0（I3）。
- 大西洋沿岸帶不拆：「zone côtière interdite」1941-04 才設立，在本批之外；目前也只有自製圖可描。

## 來源與授權

| 來源 | 種類 | 授權 | 角色 |
|---|---|---|---|
| Leconte《Nouvelle carte de France… (ligne de démarcation)》，館藏號 2015.3.1.230 | map | cc0 | primary（分界線、省界） |
| USMA WWII Europe Map 15 | atlas_map | us_federal_pd | date_check |
| Ain「Ligne de démarcation」 | dataset | licence_ouverte_2 | auxiliary_geometry |
| **TRF-GIS Départements 1940**（Victor Gay，doi:10.7910/DVN/ULQYM5） | dataset | **cc_by**（在允許清單） | auxiliary_geometry（外框、省界） |
| Perseus112《Carte régionale et zonale de la France occupée de 1940 à 1943》（Commons） | map | cc_by_sa | 東北線線形；東北禁區兩筆暫列 primary（待決） |
| Dejonghe 1994, *Revue du Nord* 76(306):487–499 | peer_reviewed | — | date_check |
| Bundesarchiv RWD 20 館藏說明（EHRI） | official_record | — | date_check |
| 《Alzacja i Lotaryngia w latach 1940–1945》, *Czasopismo Prawno-Historyczne* | peer_reviewed | — | date_check（作者與頁碼待核） |

- Natural Earth 已不再用於幾何，只當總覽圖的鄰國底圖，所以不再送出這個來源。
- CC BY 要求署名，前端需標「TRF-GIS, Victor Gay (CC BY 4.0)」。

## 方法與精度

1. **外框與省界**：TRF-GIS 1940（Lambert-93 轉 WGS84）。由現代市鎮界組成，Gay 2021 自述這是主要限制。
2. **分界線**：Ain 資料集座標，對照 Leconte 原圖（配準 RMSE ≈ 2.4 km）。只用這條線切割，不沿省界。
3. **東北線**：從 Perseus112 原圖抽出核心色像素，骨架化後取最短路徑。
   - 配準用 37 個控制點，RMSE 1.2 px ≈ 0.2 km。
   - Abbeville 以西沿索姆河口手動補 4 點。
   - 線的終點是 Dole 以南與分界線交會處。
4. **各區**：北部兩省、亞爾薩斯－摩澤爾直接取 1940 年省界；其餘佔領區用東北線切成本體和東北禁區。Pays de Gex 依史料歸東北禁區。

## 檔案

- `zones-1940-v2.geojson`：四個區塊，含邊界來源與期間。
- `requests/`：依檔名順序送出。
- `send_seed.py`：送出工具。
- `build/`：腳本、控制點、東北線。
- `preview-v2-overview.png`：總覽預覽。
- 大圖只放在 box 的 `/workspace/world-line-ww2/trace/`：`preview-v2-overlay-leconte.png`、`preview-v2-detail-*.png`。
- 測試 `SeedFrance1940Tests` 在 Testcontainers 重播兩種情境（含待決、不含待決）。
