# 北非、近東與冰島 1939-01-01～1945-09-02（開發庫 5442）

- `build/build_naf.py`：產生 `requests/N1`（來源、政權、事件）、`requests/N2`（主權紀錄：14 筆 B 批暫迄 1939-01-01 的紀錄先撤後增延長／分段，西班牙國戰時段扣掉西屬摩洛哥，伊朗與佔領區新紀錄）、`requests/N3`（佔領歸屬、交戰）。
- 輸入 `exp_39.json`（開發庫唯讀匯出，24 MB，不進版控）、`rows14.json`、`raw/r2694890.json`（OHM 伊朗 relation 2694890）。
- 送出：`tools/send_seed2.py --dir requests/N1 --ids .dev/sent-ids.nafrica-1939-1945-dev.json --derived nafrica-derived.geojson [--send]`，每一子批先 pg_dump 備份、dry-run。
- 手繪範圍（佔領區、戰線）都是近似，記在 provenance.handDrawn／handDrawnSubtract，待查證。
- `qa.json`：各段面積與重疊檢查（0 筆重疊）。
