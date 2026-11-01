# 亞洲第二批：東南亞殖民地、日本佔領與蘇聯進攻滿洲 1937-07-07～1945-09-02（開發庫 5442）

- `build/fetch.py`：向 OHM Overpass 抓 27 個 relation（`relation(id);out meta geom;way(r);out tags;`）到 `raw/`（不進版控，28 MB）。
- `build/ohm_geoms.py`：組多邊形 → 框 60～180°E／15°S～75°N → Natural Earth 10m 陸地裁切 → 簡化 0.0005°、精度 1e-4°，產生 `ohm-asia2.geojson`、`ohm-manifest2.json`（全部 CC0）。
- `build/build_asia2.py`：產生 `requests/A1`（來源 3、政權 18、事件 19）、`requests/A2`（主權紀錄 27）、`requests/A3`（佔領歸屬 12、持續關係 4、交戰 5、撤回 1）、`asia2-derived.geojson`、`qa.json`。
  - 輸入 `exp_asia.json`：開發庫唯讀匯出（1937～1946、框 55～185°E，12 MB，不進版控）。
  - 新幾何＝OHM − 開發庫同期既有紀錄 − 本批優先序較高的新紀錄（香港＞海峽殖民地＞馬來亞＞緬甸＞印度支那＞荷屬東印度）。
  - 菲律賓三段沿用既有自由邦紀錄幾何；關島、威克島、阿留申群島取前後兩筆美國紀錄的差；蘇聯佔領下的滿洲沿用滿洲國紀錄幾何（`_readd`，不撤回原紀錄）。
  - 日英開戰交戰紀錄 01a19294-4d12… 先撤後增：地點改為英屬馬來亞（吉蘭丹）範圍內的哥打巴魯。
- 送出：`tools/send_seed2.py --dir requests/A1 --ids .dev/sent-ids.borders-asia-2-dev.json --derived asia2-derived.geojson [--send]`；每一子批先 pg_dump 備份、dry-run。
- 未找到正式出處的事件標「待查證」（timeNote 與 _meta.verification）。
- 範圍外（空白）：英屬婆羅洲（砂拉越、汶萊、北婆羅洲）、葡屬帝汶、澳屬巴布亞／新幾內亞、安達曼群島、印度；廣州灣仍由既有中國紀錄涵蓋；澳門在中國紀錄內（既有問題）。
