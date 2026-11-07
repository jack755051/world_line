# gap-830 用量紀錄

規則見 `WORKFLOW.md` §3。數字由 `python3 usage_tally.py <session_id> [since]` 從本機 transcript 加總（含 subagents，依 message id 去重）；時間為 UTC。USD 欄：API 牌價估算，非訂閱實扣；牌價未入檔時標「缺」。

| 批次／事項 | session_id | 起 | 訖 | input | output | cache_creation | cache_read | 估 USD |
|---|---|---|---|---|---|---|---|---|
