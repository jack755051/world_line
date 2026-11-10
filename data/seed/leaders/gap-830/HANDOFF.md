# gap-830 交接（只讀本檔即可續做）

- 更新：2026-11-10 10:55（b33 試驗段，session d5ce48e7）。分支 feature/person-cards，HEAD 621a036 之後的收尾 commit。規則見 `WORKFLOW.md`。
- 已寫入 5052：b01–b33。生平有效 731、引用 3280、有生平任期 1474、照片 40。無研究中批次。待查 256、查無來源 26、staging 疑義 3。
- 下一批：**b34**（尚無 worklist，先 `make_worklist.py` 產生 16 組）。一段只做一批。
- b33 試驗做法：主程序只審核／乾跑／寫入；逐人前景跑 `b33/run_person.sh`（`claude -p --model sonnet`，窄 JSON 存 `bNN/people/<key>.json`、子程序 json 存 `bNN/sub/`）。是否沿用待 Tai 比較 `usage.md` 後決定。
- 試驗心得：子程序常把 Q 號／一個可開來源以外的東西漏掉；給明確 URL（如 vle.lt slug）能救回（Fierlinger 第 2 次成功）。主程序審查仍須抽查（Bistras 生卒同日屬實；Mironescu 只靠 GND 無總理職→staging）。
- 好用來源：vle.lt、gob.pe PCM 史 PDF（秘魯，只有生卒年）、islamansiklopedisi.org.tr、encyclopediaofukraine.com、deutsche-biographie.de、LoC madsrdf.json（看 citationSource）、lobid.org GND。
- 擋住的：infopedia.pt、adesp.org、historia-hispanica.rah.es、hellenicparliament.gr／hellenicnavy.gr（403）、portugal.gov.pt 舊連結 404、vlada.gov.cz DNS 不穩。
- 每批：`send_batch.py bNN` 乾跑 → `review.py bNN | cut -c1-200` → `./urlcheck.sh bNN` → `./run_batch.sh bNN` → commit → `.dev/person-impl-progress.md` 加一行 → usage.md。
- 注意：send_batch 不接受「欄位在 conflicts 又有值」；合議體的 staging 標記可能錯，需手動 `gap_status.py set`。
- 阻擋：無。Q5 未決，未動；照片未補。
- 可回頭補強：Voulgaris、Ribeiro de Castro、Guerrero Martínez（來源擋住）；Mironescu（需載明總理職的來源）；Cooreman 只有生卒年；秘魯 5 位生卒只到年；先前 Estrada Carmona、Borrero González、Ponce Vaides、Mayr 卒日等照舊。
