# 主權圖層補充：1942 後期德國、蘇聯與東方佔領行政區（DRAFT，待 Tai 檢查）

分支 `feature/borders-1938-1940`。**只寫入開發資料庫 worldline-borders-dev（API 127.0.0.1:5052）**；`send_seed.py` 拒送 5051（appdb_ww2）。
送出前已備份開發庫（見下方）。紀錄期間一律 `[1942-07-01, 1943-01-01)`，期間外不追溯。

## 範圍與做法

- 幾何：固定版本 OpenHistoricalMap（Overpass `osm_base` 2026-10-31T02:32:24Z，台北時間 10:32），逐筆釘選關係 id＋版本＋抓取時間（`ohm-manifest.json`）。
  裁切同 1938–1940 批次（歐陸框 −12～42°E、34～72°N；Natural Earth 10m 陸地；簡化 0.0005°；精度 1e-4°）。
- 沿用 Tai 決定 1「事實國界」：德意志國照 OHM relation/2692712 v266 原樣（**含總督府〔含加利西亞區〕、比亞韋斯托克區、波希米亞—摩拉維亞保護國**）。
- 佔領行政區畫成非主權斜線：東方總督轄區（relation/2692529 v46）、烏克蘭總督轄區（relation/2693267 v68）。
- 蘇聯＝relation/2851156 v94（1941 年國界）− 德意志國 − 兩個總督轄區 − 羅馬尼亞 1941-08-19 起的範圍（relation/2693255 v79：比薩拉比亞、北布科維納、外涅斯特里亞）。
  德軍佔領但未設總督轄區的地區（軍政區）仍畫為蘇聯（法理）。
- 同一天不重疊（`build/derive.py` 有斷言）；`qa.json` 記各區面積與從蘇聯扣掉的面積。

## 事件與出處

| 事件 | 日期 | 用在 | 狀態 | 出處 |
|---|---|---|---|---|
| EV_BARBAROSSA 德國進攻蘇聯 | 1941-06-22 | 蘇聯 1942 紀錄的起始變動 | 已查證 | FRUS 1941 I, Doc. 620, p. 625；Doc. 157, pp. 152–153 |
| EV_OST_DECREE 新佔東方領土行政命令／東方總督轄區 | 1941-07-17 | 東方總督轄區 | 已查證 | NCA IV, Doc. 1997-PS, pp. 634–635；FRUS 1942 III, Doc. 350, pp. 406–407 |
| EV_RKU_CIVIL 烏克蘭總督轄區移交民政 | 1941-09-01 | 烏克蘭總督轄區 | 已查證 | NCA III, Doc. 197-PS, p. 210 |
| EV_GALICIA_BIALYSTOK 東加利西亞併入總督府、比亞韋斯托克區 | 1941-08-01 | 德意志國 1942 紀錄 | **待查證** | —（日期依 OHM start_date） |

FRUS 頁碼以 history.state.gov 的 pg_N 頁面核對；NCA（美國政府印刷局 1946）依紙本頁碼。各紀錄的結束變動皆為「本試驗範圍內未結束」。

## 不在本批（地圖上 1942 後期留白）

義大利、匈牙利、羅馬尼亞、保加利亞、克羅埃西亞、塞爾維亞軍政區、希臘、蒙特內哥羅、阿爾巴尼亞、1942-11-11 後的法國（安東行動）等。
OHM 的總督府（2693084）、比亞韋斯托克區（2693091）、保護國（2704750）只作比對（已含在德意志國內），未另建紀錄。

## 授權

OHM 整體 CC0；含 CC BY 4.0 線段者整筆標 `cc_by` 並署名：德意志國（GURS、OCHA／HDX COD-AB Ukraine）、烏克蘭總督轄區與蘇聯（OCHA／HDX）。
本批 8 筆關係都沒有 OSM 匯入線段。

## 檔案與重建

`build/fetch.py`（抓 8 筆關係，記抓取時間）→ `build/build.py`（組多邊形、裁切 → `borders-ohm-1942.geojson`、`ohm-manifest.json`）→
`build/derive.py`（衍生 → `borders-1942-derived.geojson`、`qa.json`）→ `build/make_requests.py`（→ `requests/`）。OHM 持續被編輯，重抓會得到不同版本；以 manifest 為準。

```
python3 send_seed.py --base http://127.0.0.1:5052 --env ../../../../.env.borders-dev \
  --prior ../../../../.dev/sent-ids.borders-dev.json --ids ../../../../.dev/sent-ids.borders-1942-dev.json   # dry-run；加 --send 才送出
```
