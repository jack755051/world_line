# gap-830 交接（只讀本檔即可續做）

- 更新：2026-11-10 13:16（段 10 完成 b40）。分支 feature/person-cards。規則見 `WORKFLOW.md`。
- 計數（`.dev/bio-gap-830.md`）：已寫入 607、待查 **133**、查無來源 38、staging 疑義 8、合議體 44。5052 已寫入 b01–b40；生平有效 816（引用／有生平任期本段未重算；b39 時 3684／1584）、照片 40。
- 下一批：**b41**（尚無 worklist：`python3 make_worklist.py b41 0 16`）。一段只做一批。同一人的編號別名組可從 status.json 補進當批 worklist。
- **研究方式：主程序前景逐筆查證，不用 Sonnet 子程序、不用 Task／背景子代理。**
- 好用來源：vle.lt、sok.riksarkivet.se/sbl、snl.no（`<slug>.json` metadata）、islamansiklopedisi.org.tr、arquivo.presidencia.pt（`results?t=`）、mek.oszk.hu/00300/00355（Magyar Életrajzi Lexikon；目錄 `html/toc/<nnnnn>.html`，iso-8859-2）、download.data.public.lu 盧森堡歷屆政府書 PDF、cbdb.fas.harvard.edu（`person.php?name=…&o=json`；民國人物常無）、oac.cdlib.org 胡佛檔案說明（民國人物有職銜）、EHRI portal、秘魯 PCM 史書 tomo I PDF（有每任總理小傳）、catalogue.bnf.fr 人名權威、mites.gob.es 西班牙勞工部長檔、history.state.gov FRUS、lobid GND、LoC `.madsrdf.json`（看 citationSource，引自 Wikipedia 者不採）。
- 擋住的：infopedia.pt、britannica、rae.es、gov.am、armenpress、purl.sgmf.pt、adesp.org、historia-hispanica.rah.es、hellenicparliament.gr、primeminister.gr、bigenc.ru、ap6.pccu.edu.tw、valtioneuvosto.fi、gov.pl、viaf.org、ahm-exercito.defesa.gov.pt、encyklopedia.pwn.pl；repositorio.ulisboa.pt 為 JS 頁拿不到 PDF；Wikidata API 連查會限流（隔幾秒）；id.loc.gov `.html` 對 urlcheck 回 403（bot 擋，`.madsrdf.json` 可開，非死連結）。
- 每批：`send_batch.py bNN` 乾跑 → `review.py bNN | cut -c1-200` → `./urlcheck.sh bNN` → `./run_batch.sh bNN`（**只跑一次**；send 有帳本可重入，但會多備份一份）→ `./refresh_bios.sh` → `gap_status.py refresh` → commit → `.dev/person-impl-progress.md` 加一行 → usage.md。
- 注意：run_batch 會把 staging 標成「staging 疑義」或「查無來源」；合議體要手動 `gap_status.py set <key> "合議體（不建）" …`。Casa de la Cultura（厄瓜多）權威紀錄取自 Wikipedia，不可用。
- 待 Tai 決定（不阻擋續做）：Rosalvo Bobo（海地 2 筆任期，Gale 稱未就任總統）是否保留任期紀錄，已 staging。Q5 未決未動；照片未補。
- 可回頭補強：b40 Bagryanov 卒年（EHRI 1945 vs GND 1944）、Liberato Pinto／A. M. Baptista 無生卒、多人缺 Q 號；b38 Porras 生卒可由 PCM 史書 PDF p.268 小傳補（Lima 1860–1944）；b39 Korizis 卒日（BnF 06-18 vs 他說 04-18）、Chagas／Domingues 只有年、Muñiz 缺 Q 號；b38 Huszár 出生日（MÉL 1882-09-10 vs GND 1892-10-09）、Friedrich 卒年（MÉL 1958 vs 他說 1951）、Pimenta de Castro／Sănătescu 只有年份、Huszár／王士珍缺 Q 號；b37 Gaspar、Vitorino Guimarães、Sousa y Matute、Luna Peralta 缺生卒；Demertzis、Makharadze 等照舊。
