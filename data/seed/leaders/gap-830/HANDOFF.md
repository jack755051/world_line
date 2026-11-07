# gap-830 交接（只讀本檔即可續做）

- 更新：2026-11-07 17:25（段 1，session 87ef0865 收尾）。分支 feature/person-cards。規則見 `WORKFLOW.md`。
- 已寫入 5052：b01–b30。生平有效 691、引用 3044、有生平任期 1420、照片 40。無研究中批次。
- 下一批：`./refresh_bios.sh` → `python3 make_worklist.py b31 0 16`（再 b32、b33…）。待查 300 組。同時跑 ≤3 個研究員 subagent。
- 研究員 prompt：照 b30（BRIEF＋SCHEMA、不寫 DB、不開瀏覽器、避免新聞/hobby 站、LoC 引 Wikipedia 者不用、摘要寫職位且不提來源名、乾跑驗證、回報 ≤15 行）。
- 每批：`send_batch.py bNN` 乾跑 → `review.py bNN | cut -c1-200` 審（身分、僅新聞/hobby 來源欄位降精度或移除、摘要勿含 worklist/來源名、只有姓名者改 staging）→ `./urlcheck.sh bNN`（LoC 403 屬正常）→ `./run_batch.sh bNN` → commit → `.dev/person-impl-progress.md` 加一行 → `usage_tally.py <sid> <since>` 記 usage.md。
- 注意：run_batch 的 staging 標記對「合議體」會標成 staging 疑義或漏標，需手動 `gap_status.py set <key> "合議體（不建）" <note>`。
- 阻擋：無。Q5（授權清單是否套用生平引用）未決，未動；照片未補。
- 可回頭補強：Choibalsan、Aharonyan 摘要偏薄；查無來源 20 組／staging 疑義 3 組見 `.dev/bio-gap-830.md`。
