# B3 full 計畫（Tai 2026-11-11 21:24 全量；21:25 主要領導人優先）

- 人數：5442 現行 leader_bios 924 人（`gap-830/existing_bios.tsv` 923 人＋2026-11-11 重建的邱吉爾 `01a1c86e-c89b-70af-afe0-1ad0f4be2bf8`，tsv 無邱吉爾）扣 run100 的 100 人（已寫入 98＋零段落 2）＝**824 人**，165 批（最後一批 4 人）。與指示的 823 差 1，即邱吉爾（新 bio 不在 923 人 tsv）。
- 試跑 50 人（`b3-trial/selection.json`）與 b3-sample 5 人未寫入 5442，依「923 扣 run100」一併重跑（新規格）。
- 優先（Tai 21:25）：庫內有的 18 人依指定順序排在 batch001–004；**孫中山、袁世凱、貝當、戴高樂不在 5442 現行 leader_bios**（以 name／name_zh 唯讀查詢核對）。指定名單中無人在 run100（史達林、蔣中正亦不在）。
- 其餘依 1908–1945 窗內 leader_records 任期日數、任期數、厚薄、姓名排序（`pool-snapshot.tsv` 由 `export_pool_snapshot.sql` 唯讀匯出）。
- 規格、§16 規則、提示沿用 run100：`build_full.py` 只替換路徑與批次標籤（REPLACE 表；對 run100 版 diff 只有 1、3、5、7、18 行與審查 1、12、32 行）。
- 迴圈：`.dev/cc-b3full-loop.sh`（本機、不 commit）；輸出 `full/batchNNN/`；每批只 commit 該批目錄；不寫庫、不 push。
- 重現：`python3 -I build_full.py` 連跑兩次輸出逐位元相同。
