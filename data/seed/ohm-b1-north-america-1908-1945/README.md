# 第 1 批：北美國界 1908-01-01～1945-09-30（OHM admin_level=2 補缺）

- 決定：Tai 2026-11-04 00:40（政權用 OHM 名＋wikidata、採信 OHM 起訖日）、00:53／00:55（沿用拉美做法補其他地區；已有政權掛既有記錄、不重複建；與既有疆界重疊或衝突的不覆蓋，列出待決定）。
- 新政權 3 個：canada（Q16，OHM「Dominion of Canada」／「Canada」）、dominion-of-newfoundland（Q38610，含 1934-02-16 起的 Commission Government，同一 wikidata）、saint-pierre-and-miquelon（Q34617）。
- 既有政權補空檔：united-states-of-america 1908-01-01～1914-07-29（4 段，OHM 美國 relation 含阿拉斯加、夏威夷、波多黎各、運河區、菲律賓等，與既有 1914-07-29 起的紀錄一致）。美國 OHM 在 1910-08-19／08-20 之間空一天，照 OHM 原樣。
- 不覆蓋（扣除）：美國 1908-01-01～1909-02-06 扣掉既有美國古巴臨時政府（古巴約 10.8 萬 km²）；與墨西哥、巴拿馬既有紀錄的邊界細條。
- 同批爭議：拉布拉多內陸 1908-01-01～1927-03-11 加拿大與紐芬蘭的 OHM 範圍重疊（約 20 萬 km²，1927-03-01 樞密院裁決前的爭議區），兩邊都扣除留白，待 Tai 決定歸屬。
- OHM 內部重疊：紐芬蘭 relation 2831077（1927-03-11～1949）與 2830879、2830878 重疊，未使用。
- 未寫入（待決定）：荷蘭海外領地（蘇利南、庫拉索）、丹麥格陵蘭——既有荷蘭／丹麥紀錄只畫歐洲本土，要加須撤回重寫既有紀錄。
- 逐筆報告：report.json（overlaps、skipped、conflicts、low＝日期缺日精度）。
- 重建：build/fetch.py → build/build.py <批次> -180,-60,180,85 → build/plan.py → build/run_overlap.sh（Mac 上 PostGIS，唯讀暫存表）→ build/make.py → send_seed.py（預設 dry-run）。raw/ 沒有進版控。
