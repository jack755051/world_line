# B3 full v3 batch107：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch107/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch107/min-check.round1.json`）：
- 卡爾·斯塔夫｜Karl Staaff｜01a1b51e-6296-7668-a4b7-6017a55a2fda｜kingdom-of-sweden｜首任 1911-10-07｜薄（離線推定）｜kingdom-of-sweden head_of_government「Statsminister」1911-10-07～1914-02-17（recordId 01a1aa4a-45aa-79c9-aaad-0f6cfacfd5e2）
- 埃米利奧·波特斯·希爾｜Emilio Portes Gil｜01a1aa4a-da3f-758c-9cb1-34ad54a82626｜mexico｜首任 1928-12-01｜中（離線推定）｜mexico head_of_state「」1928-12-01～1930-02-05（recordId d2da7ff0-573c-4c02-a490-2085439ef465）；mexico head_of_government「」1928-12-01～1930-02-05（recordId e2615a32-821e-4685-9504-6966228f4637）
- 帕夫洛斯·孔杜里奧蒂斯｜Pavlos Kountouriotis｜01a1b51c-829f-7310-b375-493d6cdb5e3d｜kingdom-of-greece、second-hellenic-republic｜首任 1920-10-28｜中（離線推定）｜kingdom-of-greece head_of_state「Regent」1920-10-28～1920-11-17（recordId 01a1aa4a-6558-7d70-a3a4-88ebdbaef207）；kingdom-of-greece head_of_state「Regent」1923-12-20～1924-03-25（recordId 01a1aa4a-6559-7b86-9500-a0939c207795）；second-hellenic-republic head_of_state「Regent」1924-03-25～1924-04-14（recordId 01a1aa4a-6559-7d70-a893-eb1e3403f674）；second-hellenic-republic head_of_state「Governor」1924-04-14～1924-05-24（recordId 01a1aa4a-6559-7f65-bdb7-668cbcb709cf）；second-hellenic-republic head_of_state「President of the Republic」1924-05-24～1926-04-06（recordId 01a1aa4a-655a-716b-8b9f-e04d036803f3）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `107`、`/Users/jack755051/wl-source-cache/b3full-v3/batch107/raw`、`data/seed/leaders/b3-trial/full/v3/batch107` 代入），全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch107/raw`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py data/seed/leaders/b3-trial/full/v3/batch107/research.json --report data/seed/leaders/b3-trial/full/v3/batch107/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。
