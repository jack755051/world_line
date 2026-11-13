# tail-1945-09：(b) 組 64 個政權延到 1945-10-01（開發庫 5442）

- 依據：憲法 Decision 3（第一階段 1908-01-01～1945-09-30）；Tai 2026-11-05「照建議」（plan_1945tail_latam_capitals.md 第 1 題）。
- 原因：asia-1／2／3、borders-us、nafrica-1939-1945、europe-1945-postwar 各批以舊的第一階段終點 1945-09-02 截止（exclusive 09-02 或 09-03），不是歷史終止日；OHM 訖日多在 1945-10-01 之後。
- 做法（I5，不刪除）：先撤回、再以原幾何、原欄位新增 [原起日, 1945-10-01)。provenance 加 replaces／extendedBy，note 加延長註記。
  - 10-*：主權紀錄 64 筆（撤回＋新增）
  - 20-*：佔領歸屬（撤回＋新增）
  - 30-*：首都 11 筆（撤回＋新增）；羅馬尼亞（出處待查證）、重慶（無正式出處）不延長
  - 40-leaders.*.sql：領導人（API 沒有撤回端點，沿用 SQL 撤回＋同交易新增；只延長 seed 原任期超過 1945-09-30 的）
- (a) mauritania-french-1912 保留；(c) 13 個見 /workspace/wl-audit/plan_1945tail_groupC.md。
- 用法：`python3 build/make_requests.py` → `python3 send_seed.py`（dry-run）→ `python3 send_seed.py --send --base http://127.0.0.1:5052`；領導人用 docker psql 跑 40-leaders.commit.sql。
