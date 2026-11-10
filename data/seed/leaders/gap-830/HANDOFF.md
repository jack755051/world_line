# gap-830 交接（只讀本檔即可續做）

- 更新：2026-11-10 11:28（段 4 完成 b34）。分支 feature/person-cards。規則見 `WORKFLOW.md`。
- 計數（`.dev/bio-gap-830.md`）：已寫入 518、待查 **235**、查無來源 27、staging 疑義 7、合議體 43。5052 已寫入 b01–b34；生平有效 742、引用 3334、有生平任期 1494、照片 40。
- 下一批：**b35**（尚無 worklist：`python3 make_worklist.py b35 0 16`）。一段只做一批。
- **研究方式：主程序前景逐筆查證，不用 Sonnet 子程序、不用 Task／背景子代理。**
- 好用來源：vle.lt、gob.pe PCM 史 PDF（秘魯，只有年）、islamansiklopedisi.org.tr、valitsus.ee、georgianencyclopedia.ge（pdf-export）、history.state.gov FRUS、cbdb.fas.harvard.edu API（只當線索，不載官職）。lobid GND：WebFetch 被 Anubis 擋，用 curl 可以。LoC：`.madsrdf.json` 用 curl 可讀；`.html` 現在一律 403（含舊批已用網址），urlcheck 會列出，屬站方擋爬蟲。
- 擋住的：infopedia.pt、adesp.org、historia-hispanica.rah.es、hellenicparliament.gr、archives.sinica.edu.tw PDF、bigenc.ru、ap6.pccu.edu.tw（中華百科全書連不上）。
- 每批：`send_batch.py bNN` 乾跑 → `review.py bNN | cut -c1-200` → `./urlcheck.sh bNN` → `./run_batch.sh bNN` → `./refresh_bios.sh` → commit → `.dev/person-impl-progress.md` 加一行 → usage.md。
- 注意：run_batch 依 why 是否含「來源」自動標查無來源／疑義，身分疑義類要手動 `gap_status.py set`（b34 趙秉鈞已改）。同一人另一群組不在名單時可併入當批 worklist（b34 併 Hilmi Paşa (1)）。
- 阻擋：無。Q5 未決，未動；照片未補。
- 可回頭補強：北洋趙秉鈞／孫寶琦／錢能訓（需載明總理職的來源）；Urriola（巴拿馬官方）；Bográn 只有摘要；Théodore 生年衝突；Hilmi Paşa 卒年衝突（TDV 1923 vs GND 1922）；Voulgaris、Ribeiro de Castro、Guerrero Martínez、Mironescu 等照舊。
