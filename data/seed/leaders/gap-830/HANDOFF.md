# gap-830 交接（只讀本檔即可續做）

- 更新：2026-11-10 11:13。Tai 決定回到 b31 主程序逐筆查的做法。分支 feature/person-cards。規則見 `WORKFLOW.md`。
- 計數以 `.dev/bio-gap-830.md` 為準（先前 HANDOFF 寫待查 256／staging 3，與名單不符，已更正）：已寫入 505、待查 **252**、查無來源 26、staging 疑義 **4**、合議體 43。已寫入 5052：b01–b33。先前另記生平有效 731、引用 3280、有生平任期 1474、照片 40（本次未重算）。
- 下一批：**b34**（尚無 worklist，先 `make_worklist.py` 產生 16 組）。一段只做一批。
- **研究方式：主程序前景逐筆查證，不用 Sonnet 子程序、不用 Task／背景子代理。**（b33 試驗已完成；Tai 11:11 決定不沿用。）
- 好用來源：vle.lt、gob.pe PCM 史 PDF（秘魯，只有生卒年）、islamansiklopedisi.org.tr、encyclopediaofukraine.com、deutsche-biographie.de、LoC madsrdf.json（看 citationSource）、lobid.org GND。
- 擋住的：infopedia.pt、adesp.org、historia-hispanica.rah.es、hellenicparliament.gr／hellenicnavy.gr（403）、portugal.gov.pt 舊連結 404、vlada.gov.cz DNS 不穩。
- 每批：`send_batch.py bNN` 乾跑 → `review.py bNN | cut -c1-200` → `./urlcheck.sh bNN` → `./run_batch.sh bNN` → commit → `.dev/person-impl-progress.md` 加一行 → usage.md。
- 注意：send_batch 不接受「欄位在 conflicts 又有值」；合議體的 staging 標記可能錯，需手動 `gap_status.py set`。
- 阻擋：無。Q5 未決，未動；照片未補。
- 可回頭補強：Voulgaris、Ribeiro de Castro、Guerrero Martínez（來源擋住）；Mironescu（需載明總理職的來源）；Cooreman 只有生卒年；秘魯 5 位生卒只到年；先前 Estrada Carmona、Borrero González、Ponce Vaides、Mayr 卒日等照舊。
