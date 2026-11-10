# gap-830 交接（只讀本檔即可續做）

- 更新：2026-11-10 10:40（段 3，session cc3cb417）。分支 feature/person-cards，HEAD d234fcc 之後的收尾 commit。規則見 `WORKFLOW.md`。
- 已寫入 5052：b01–b32。生平有效 719、引用 3220、有生平任期 1458、照片 40。無研究中批次。待查 268、查無來源 23。
- 下一批：**b33**（`b33/worklist.json` 已有 16 組、全為待查、與 b32 不重疊，沿用即可）。一段只做一批。
- 研究方式：**主程序前景依序查證，不用背景任務／subagent**。抽原文用 curl＋去標籤後 grep 關鍵字，比 WebFetch 摘要可靠。
- 好用來源：vle.lt（立陶宛、也收波蘭／羅馬尼亞人物）、vestnesis.lv（拉脫維亞總理系列）、tekst.devb.be（NEVB PDF）、encyclopediaofukraine.com、deutsche-biographie.de（NDB 全文）、portugal.gov.pt「chefes-do-governo-desde-1821」（葡萄牙任期）、秘魯 PCM 史 PDF、encyclopedia.com（Gale）、LoC marcxml（看 670，引 Wikipedia 者不用）、OAC／Hoover 檔案指南。
- 擋住的：infopedia.pt（403）、adesp.org（連不上；厄瓜多總統傳 PDF 在此）、historia-hispanica.rah.es（需 JS）、gov.am、primeminister.gr／minfin.bg／dzieje.pl（403）。Wikidata API 連打會限流，間隔幾秒。
- 每批：`send_batch.py bNN` 乾跑 → `review.py bNN | cut -c1-200` → `./urlcheck.sh bNN`（LoC 403 正常）→ `./run_batch.sh bNN` → commit → `.dev/person-impl-progress.md` 加一行 → `usage_tally.py <sid>` 記 usage.md。
- 注意：send_batch 不接受「欄位在 conflicts 又有值」；兩源只在日不同時，給月／年精度並寫進 unverified。合議體的 staging 標記可能錯，需手動 `gap_status.py set`。
- 阻擋：無。Q5（授權清單是否套用生平引用）未決，未動；照片未補。
- 可回頭補強：Estrada Carmona、Borrero González（adesp.org 可連時）、Ponce Vaides 生卒；Mayr 卒日（5-21 或 5-26）；Alberings 生日（曆法）；Štefan Tiso 卒年；Michalakopoulos 生卒日；Osóbka-Morawski 卒日；Largo Caballero 出生地。
