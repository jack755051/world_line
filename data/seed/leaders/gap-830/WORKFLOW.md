# gap-830 派工與用量規則（Tai 2026-11-07 16:09 核准）

主控 session（審查、寫入、commit）與研究員 subagent 都適用。

## 1. 有界上下文
- 每個小批次（bNN）只有一個明確交付物：審過的 `bNN/research.json` → 寫入 5052 → 小 commit。
- 交接精簡：下一段只需讀 `HANDOFF.md`（≤15 行），不把全工作史帶入。可開乾淨批次 session，但不強制；重點是上下文有界、不重讀全 repo。

## 2. 只讀必要的東西
- 只讀必要檔案路徑與範圍（本資料夾的 BRIEF／SCHEMA／腳本、當批 worklist／research）；不通讀 repo、ARCHITECTURE 全文。
- 指令輸出限長（`| tail`、`grep -E '✗|完成'`），但錯誤證據要保留（失敗行原文）。
- 用增量待辦名單（`status.json`／`make_worklist.py`），已寫入或已判定的群組不重複全量查證。

## 3. 檢查點與用量紀錄
- 每批的檢查點：worklist → research → 審查 → 試跑 5062 → 寫入 5052 → 計數比對 → commit；每點完成才進下一點。
- 同一失敗先歸納證據（錯誤原文、受影響群組）再進下一輪，不盲目重試。
- 批次完成在 `usage.md` 記一行：session_id、起訖時間、input／output／cache_creation／cache_read tokens、估算 USD（API 牌價，非訂閱實扣）。取不到的欄位標「缺」，不捏造。

背景：11/2–3 全專案 ccusage 共 269,999,216 tokens，cache_read 259,350,906（96.06%），估 $153.67。證據只支持「多輪快取上下文讀取」占大量 token；日後只拿紀錄比較，不宣稱必然省多少。
