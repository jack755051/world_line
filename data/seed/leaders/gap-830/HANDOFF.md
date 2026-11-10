# gap-830 交接（只讀本檔即可續做）

- 更新：2026-11-10 11:46（段 6 完成 b36）。分支 feature/person-cards。規則見 `WORKFLOW.md`。
- 計數（`.dev/bio-gap-830.md`）：已寫入 544、待查 **203**、查無來源 32、staging 疑義 8、合議體 43。5052 已寫入 b01–b36；生平有效 767、引用 3466、有生平任期 1527、照片 40。
- 下一批：**b37**（尚無 worklist：`python3 make_worklist.py b37 0 16`）。一段只做一批。
- **研究方式：主程序前景逐筆查證，不用 Sonnet 子程序、不用 Task／背景子代理。**
- 好用來源：vle.lt、sok.riksarkivet.se/sbl/Artikel/<id>、islamansiklopedisi.org.tr/<slug>、istanbulansiklopedisi.org、valitsus.ee、1920.gov.pl（波蘭 1920 前後）、dichp.bnportugal.gov.pt PDF（葡萄牙史家，pdftotext 讀）、lobid GND（curl，bio 欄常載任期）、LoC `.madsrdf.json`（`.html` 一律 403，urlcheck 會列出，屬站方擋爬）。
- 擋住的：infopedia.pt、gov.am（Radware）、armenpress 403、britannica 403、purl.sgmf.pt 拒連、adesp.org、historia-hispanica.rah.es、hellenicparliament.gr、bigenc.ru、ap6.pccu.edu.tw。
- 每批：`send_batch.py bNN` 乾跑 → `review.py bNN | cut -c1-200` → `./urlcheck.sh bNN` → `./run_batch.sh bNN` → `./refresh_bios.sh` → `gap_status.py refresh` → commit → `.dev/person-impl-progress.md` 加一行 → usage.md。
- 注意：run_batch 依 why 是否含「來源」自動標；身分疑義類要手動 `gap_status.py set`。Casa de la Cultura（厄瓜多）權威紀錄自註取自 Wikipedia，不可用。
- 待 Tai 決定（不阻擋續做）：Rosalvo Bobo（海地 2 筆任期）—Gale 百科稱美方阻止其就任總統、未掌行政權，任期紀錄是否保留？已 staging 疑義。Q5 未決，未動；照片未補。
- 可回頭補強：Ivens Ferraz（只有 GND 年份與「將領與政治人物」，缺任期來源）；Skulski 生年 1877/1878、卒年不明；Avlonyalı Ferid 生年 1851/1852；北洋趙秉鈞／孫寶琦／錢能訓；Urriola；Sá Cardoso、Ohanjanyan、Báez、Freile 照舊；b36 Janson、Kondylis 摘要缺總理任期來源（比國總理府頁 403）、Sánchez de Toca 生年 1852/1854 未給、Gaceta 1919-07-21 為掃描 PDF。
