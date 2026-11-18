# tail-1945-09c：(c) 組 13 個政權＋USAMGIK、泰國、spanish-state、蘇丹（開發庫 5442）

- 依據：/workspace/wl-audit/plan_1945tail_groupC.md 第 1～15 題；Tai 2026-11-05「照建議」（含新建政權 usamgik，1945-09-08 起）。
- 做法（I5，不刪除）：先撤回、再重寫。衍生幾何在 PostGIS 算出後寫進 tail-1945-09c-derived.geojson。
  - 00-*：新政權 usamgik（Q484104）與事件（美軍仁川登陸／第 1 號布告，FRUS 1945 VI Doc. 776）
  - 10-*：主權紀錄；20-*：佔領歸屬；30-*：首都（東京、莫斯科）；40-leaders.*.sql：裕仁、東久邇宮、史達林延到 1945-10-01
- 備案（出處未找到）：廣州灣接收日、葡屬帝汶移交日 → 佔領段延到 1945-10-01；曼谷首都（sourceRef 待查證）不延；
  南樺太、千島蘇軍佔領（需新政權，未獲同意）不寫。
- 用法：`python3 build/make_requests.py` → `python3 send_seed.py --base http://127.0.0.1:5052`（dry-run）→ sim.dry.sql（整批模擬＋QA，ROLLBACK）
  → 備份 → `python3 send_seed.py --send --base http://127.0.0.1:5052` → docker psql 跑 40-leaders.commit.sql。
