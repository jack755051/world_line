# gap-830 交接（只讀本檔即可續做）

- 更新：2026-11-10 11:59（段 7 完成 b37）。分支 feature/person-cards。規則見 `WORKFLOW.md`。
- 計數（`.dev/bio-gap-830.md`）：已寫入 563、待查 **183**、查無來源 32、staging 疑義 8、合議體 44。5052 已寫入 b01–b37；生平有效 781、引用 3551、有生平任期 1551、照片 40。
- 下一批：**b38**（尚無 worklist：`python3 make_worklist.py b38 0 16`）。一段只做一批。同一人的編號別名組（如 Damad Ferid (1)–(5)）可從 status.json 補進當批 worklist 一併處理。
- **研究方式：主程序前景逐筆查證，不用 Sonnet 子程序、不用 Task／背景子代理。**
- 好用來源：vle.lt、sok.riksarkivet.se/sbl、snl.no（`<slug>.json` 有 metadata 生卒地）、islamansiklopedisi.org.tr、arquivo.presidencia.pt（葡國任命令；`results?t=<姓名>` 可 curl）、intezet.nori.gov.hu（匈牙利國家墓園）、history.ru（histrf）、booksite.ru BSE 全文（cp1251）、cedoc.sisbib.unmsm.edu.pe（祕魯史 PDF）、lobid GND、LoC `.madsrdf.json`（`.html` 403 屬站方擋爬）。
- 擋住的：infopedia.pt、gov.am、armenpress、britannica、purl.sgmf.pt、adesp.org、historia-hispanica.rah.es、hellenicparliament.gr、primeminister.gr、bigenc.ru、ap6.pccu.edu.tw、valtioneuvosto.fi、gov.pl、viaf.org（Cloudflare）、ahm-exercito.defesa.gov.pt、encyklopedia.pwn.pl。
- 每批：`send_batch.py bNN` 乾跑 → `review.py bNN | cut -c1-200` → `./urlcheck.sh bNN` → `./run_batch.sh bNN` → `./refresh_bios.sh` → `gap_status.py refresh` → commit → `.dev/person-impl-progress.md` 加一行 → usage.md。
- 注意：run_batch 會把 staging 標成「staging 疑義」或「查無來源」；合議體要手動 `gap_status.py set <key> "合議體（不建）" …`。Casa de la Cultura（厄瓜多）權威紀錄取自 Wikipedia，不可用。
- 待 Tai 決定（不阻擋續做）：Rosalvo Bobo（海地 2 筆任期，Gale 稱未就任總統）是否保留任期紀錄，已 staging。Q5 未決未動；照片未補。
- 可回頭補強：b37 Gaspar、Vitorino Guimarães、Sousa y Matute、Luna Peralta 缺生卒（葡／祕無可開來源）；Demertzis 只有年份、無出生地；Makharadze 出生地有異說；Ivens Ferraz、Skulski、Avlonyalı Ferid、北洋趙秉鈞／孫寶琦／錢能訓、Urriola、Sá Cardoso、Ohanjanyan、Báez、Freile、Janson、Kondylis、Sánchez de Toca 照舊。
