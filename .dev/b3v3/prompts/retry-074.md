# B3 full v3 batch074：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch074/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch074/min-check.round1.json`）：
- 明治天皇（睦仁）｜Emperor Meiji (Mutsuhito)｜01a1b4c1-ce4a-79cf-bc76-f5cd4aa33622｜empire-of-japan｜首任 1908-01-01｜中（離線推定）｜empire-of-japan head_of_state「天皇」1908-01-01～1912-07-30（recordId a6500b61-984c-45c3-bfaf-14d138902406）
- 埃萊夫塞里奧斯·韋尼澤洛斯｜Eleftherios Venizelos｜01a1b4c1-ce54-723d-a25f-167e9fca0d16｜kingdom-of-greece、second-hellenic-republic｜首任 1920-10-25｜厚（離線推定）｜kingdom-of-greece head_of_state「Council of Ministers: President of the Council of Ministers (ex officio)」1920-10-25～1920-10-28（recordId 01a1aa4a-6558-7ad7-bf48-15a6d03c3690）；kingdom-of-greece head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1924-01-11～1924-02-06（recordId 01a1aa4a-65c4-7e99-a195-74eb46cabb9c）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1928-07-04～1929-06-07（recordId 01a1aa4a-65c6-7b14-8519-fb20d44e38ad）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1929-06-07～1929-12-16（recordId 01a1aa4a-65c6-7d67-9057-970e9e7a1543）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1929-12-16～1932-05-26（recordId 01a1aa4a-65c6-7fb9-9194-348a89fc9c7b）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1932-06-05～1932-11-04（recordId 01a1aa4a-65c7-747b-bbf4-925c10685e5b）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1933-01-16～1933-03-06（recordId 01a1aa4a-65c7-7923-929b-a2e25b240e98）
- 何塞·帕爾多｜José Pardo y Barreda｜164b8938-b957-4966-828b-229edf3bc58b｜peru｜首任 1908-01-01｜中（離線推定）｜peru head_of_state「Presidente Constitucional」1908-01-01～1908-09-24（recordId 343eb1b9-b4f3-44d4-9a1e-7b8d4e6a5558）；peru head_of_state「Presidente Constitucional」1915-09-24～1919-07-04（recordId 2fe90e0f-63a5-4806-b53b-963848362e17）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `074`、`/Users/jack755051/wl-source-cache/b3full-v3/batch074/raw`、`data/seed/leaders/b3-trial/full/v3/batch074` 代入），全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch074/raw`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py data/seed/leaders/b3-trial/full/v3/batch074/research.json --report data/seed/leaders/b3-trial/full/v3/batch074/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。
