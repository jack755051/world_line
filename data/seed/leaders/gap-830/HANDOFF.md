# gap-830 交接（只讀本檔即可續做）

- 更新：2026-11-07 16:31（session 87ef0865）。分支 feature/person-cards。規則見 `WORKFLOW.md`。
- 已寫入 5052：b01–b18（b14–b18 本段）。生平有效 520、引用 2024、有生平任期 1115。
- 研究中／待審：b19、b20、b21（subagent 寫 `bNN/research.json`；若檔案不存在＝未完成，重派即可）。
- 每批流程：`python3 send_batch.py bNN`（乾跑）→ `python3 review.py bNN | cut -c1-230`（人工審：身分、來源品質、僅新聞/hobby 站的欄位降精度或移除）→ `./urlcheck.sh bNN` → `./run_batch.sh bNN` → commit → `.dev/person-impl-progress.md` 加一行 → `usage_tally.py` 記 usage.md。
- 派新批前：`./refresh_bios.sh`，再 `python3 make_worklist.py bNN 0 16`。研究員 prompt 照前批（BRIEF＋SCHEMA，乾跑驗證，回報 ≤15 行）。
- 阻擋：無。待查約 490 組；查無來源／staging 名單見 `.dev/bio-gap-830.md`。Q5（授權清單是否套用生平引用）未決，未動。
