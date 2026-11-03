# 拉丁美洲國界 1908-01-01～1945-09-30（OHM admin_level=2）

- 決定（Tai 2026-11-04 00:40）：政權直接用 OHM 國名（official_name，沒有就 name）加 OHM 的 wikidata 建立；起訖日比照歐洲批次，採信 OHM 的 start_date／end_date。
- 範圍：墨西哥、中美洲、加勒比、南美，共 66 個 relation，對應 37 個政權（含殖民地與美軍佔領／臨時政府）。期間裁到 [1908-01-01, 1945-10-01)。
- 不含：United States、Koninkrijk der Nederlanden 這兩個 relation（波多黎各、運河區、荷屬蘇利南、庫拉索等屬地）。OHM 查無馬丁尼克、福克蘭群島，列為缺口。
- 佔領與臨時政府（美國佔領海地 1915–34、聖多明哥美國軍政府 1916–24、美國古巴臨時政府 1906–09）記為 not_sovereign；國家與殖民地記為 de_jure（比照既有的英屬印度）。
- 日期缺日精度（7 段）：見 low-precision.json；補為該年第一天，並寫在該筆 note。
- 授權：CC0。尼加拉瓜、哥斯大黎加有 1 條共界線段標示 CC BY 4.0（OCHA／HDX COD-AB），這 3 筆標 cc_by 並附 attribution。另有 105 條線段標「CCO 4.0」（字母 O），視為 CC0，記在 provenance.licenseReview。
- 重建流程：build/fetch.py（每筆間隔 2 秒）→ build/build.py（Natural Earth 10m 陸地裁切）→ build/make_requests.py → send_seed.py（預設 dry-run）。raw/ 沒有進版控。
