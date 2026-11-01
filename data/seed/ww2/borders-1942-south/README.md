# 1942 後期南歐、東南歐與法國國界試驗（1942-07-01～1942-12-31）

範圍：義大利、匈牙利、羅馬尼亞（含比薩拉比亞、北布科維納與外涅斯特里亞）、保加利亞、克羅埃西亞、塞爾維亞、希臘、蒙特內哥羅、阿爾巴尼亞，以及 1942-11-11 起的法國。

- 幾何：固定版本 OHM（`ohm-manifest.json`，Overpass osm_base 2026-10-31T03:13:48Z），先由 `build/fetch.py`、`build/build.py` 組成 `borders-ohm-1942-south.geojson`，再由 `build/derive.py` 切出 `borders-1942-south-derived.geojson`（FIXS_*，互不重疊）。
- 海岸線：Natural Earth 陸地（沿用 SRC_NE_LAND）。
- 佔領行政區（外涅斯特里亞、塞爾維亞軍事指揮官轄區、蒙特內哥羅總督轄區、軸心佔領的希臘、義大利佔領的法國地區、1942-11-11 起的法國）一律標 `not_sovereign`，前端以斜線呈現。
- 送出：`send_seed.py` 預設只預演；`--send` 只接受開發庫 API（5052），拒絕 5051。
  `python3 send_seed.py --send --base http://127.0.0.1:5052 --env <開發 env> --prior .dev/sent-ids.borders-dev.json --prior .dev/sent-ids.borders-1942-dev.json --ids .dev/sent-ids.borders-1942-south-dev.json`

## 衍生規則
| 代號 | 來源 | 圖層 |
|---|---|---|
| FIXS_IT | 2747829 v93（1941-04-18～1942-11-11 的義大利），整段期間沿用 | de_jure |
| FIXS_IT_OCC_FR | 2747832 v91 − 2747829 v93（科西嘉與法國東南部），1942-11-11 起 | not_sovereign |
| FIXS_FR | 2747869 v89，1942-11-11 起（第一次送出，誤含阿爾及利亞北部，已撤回） | — |
| FIXS_FR_EU | FIXS_FR ∩ 北緯 40 度以北（法國本土），1942-11-11 起 | not_sovereign |
| FIXS_HU | 2692359 v89 | de_jure |
| FIXS_RO | 2693255 v79 − 外涅斯特里亞 | de_jure |
| FIXS_TRANSNISTRIA | 2693255 v79 − 2693259 v71，只留德涅斯特河以東（重心經度 > 28.5） | not_sovereign |
| FIXS_BG | 2695478 v30 | de_jure |
| FIXS_GR | 2920398 v5 − 保加利亞 | not_sovereign |
| FIXS_HR | 2692713 v65 | de_jure |
| FIXS_RS | 2692357 v43 | not_sovereign |
| FIXS_ME | 2695479 v15 | not_sovereign |
| FIXS_AL | 2695459 v22 | de_jure |

## 修正
- `05-retract-01-sovs_fr.json` 撤回 SOVS_FR（OHM 2747869 仍含阿爾及利亞北部；1942-11-08 起盟軍登陸北非，不該畫成德國佔領），`06-sovereignty-01-sovs_fr_eu.json` 改送只含法國本土的紀錄。紀錄不刪除，只撤回。

## 待查證（沒有正式出處，事件不附引用，送出後為 pending；不補造）
- EV_ME_GOV：義大利設蒙特內哥羅總督轄區（OHM 1941-10-03）。
- EV_AL_1941：科索沃等地併入義屬阿爾巴尼亞（OHM 1941-06-07）。
- EV_IT_OCC_FR：義大利佔領科西嘉與法國東南部（OHM 1942-11-11）。
- EV_HU_YU_1941：引用只涵蓋斯洛維尼亞部分；巴奇卡、巴拉尼亞併入的文件與日期待查。
- 多數事件日期依 OHM 國界變動日（timeNote 已註明），出處只證明事件本身。
- 外涅斯特里亞的羅文名稱「Guvernământul Transnistriei」為通行稱呼，原文出處待查。

## 未畫
- 法國境內德、義佔領區的分界（OHM 沒有分區幾何；1942-11-11 前的維琪紀錄沿用既有資料）。
- 希臘境內德、義佔領區的分界。
- 1942-11-11 後的阿爾及利亞北部（盟軍登陸後的行政歸屬，留白待查證）。
- 1942-11-11 後的摩納哥（OHM 2956943 v1 只有佔領標記，本批不畫）。
