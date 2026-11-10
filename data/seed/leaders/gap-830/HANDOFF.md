# gap-830 交接（只讀本檔即可續做）

- 更新：2026-11-10 09:30（段 2b，session b2a8bc92）。分支 feature/person-cards，HEAD 00447bc 之後的收尾 commit。規則見 `WORKFLOW.md`。
- 已寫入 5052：b01–b31。生平有效 706、引用 3136、有生平任期 1442、照片 40。無研究中批次。待查 284。
- 下一批：**b32**（`b32/worklist.json` 已有，與 b31 不重疊，可沿用；b33 同）。一段只做一批。
- 研究方式（段 2b 起）：**主程序前景依序查證，不用背景任務／subagent**（段 2 的背景子任務逾時被殺、無產出）。
- 好用來源：valitsus.ee、president.ee（愛沙尼亞元首頁有生卒地）、libr.sejm.gov.pl（波蘭議長）、IPN katalog（PRL 官員）、秘魯 PCM 史 PDF（`pdftotext` 後 grep 人名，locator 寫 PDF 頁）、encyclopedia.com（Gale／Columbia）、LoC marcxml（看 670，引 Wikipedia 者不用）。
- 擋住的：historia-hispanica.rah.es（需 JS，抓不到內文）、encyclopedia.pwn.pl（停用）、gov.am（captcha）、primeminister.gr／minfin.bg／dzieje.pl（403）。Wikidata API 連打會限流，間隔幾秒。
- 每批：`send_batch.py bNN` 乾跑 → `review.py bNN | cut -c1-200` → `./urlcheck.sh bNN`（LoC 403 正常）→ `./run_batch.sh bNN` → commit → `.dev/person-impl-progress.md` 加一行 → `usage_tally.py <sid>` 記 usage.md。
- 注意：run_batch 對「合議體」的 staging 標記可能錯，需手動 `gap_status.py set <key> "合議體（不建）" <note>`。只有通訊社來源者日期降為年精度（b31 Bozhilov）。
- 阻擋：無。Q5（授權清單是否套用生平引用）未決，未動；照片未補。
- 可回頭補強：Michalakopoulos 生卒日（LoC 1875／1938-03-27 vs 他處 1876／03-07，未給）；Osóbka-Morawski 卒日；Largo Caballero 出生地（RAH 可讀時）；Choibalsan、Aharonyan 摘要偏薄；查無來源 20／staging 疑義 3 見 `.dev/bio-gap-830.md`。
