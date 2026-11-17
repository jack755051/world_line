# B3 full v3 batch027：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch027/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch027/min-check.round1.json`）：
- 斐迪南一世（保加利亞）｜Ferdinand I of Bulgaria｜01a1b4af-e512-7119-99f3-fa7b30658534｜tsardom-of-bulgaria｜首任 1908-10-05｜薄（離線推定）｜tsardom-of-bulgaria head_of_state「Car na Bãlgarija / Car na bãlgarite」1908-10-05～1918-10-03（recordId 01a1aa4a-4de5-7e90-bc3d-b0f4b1a81389）
- ｜José Eligio Ayala｜01a1aa4a-e5f0-7059-8a6c-3f793eb06588｜paraguay｜首任 1923-04-11｜中（離線推定）｜paraguay head_of_government「Presidente Provisorio de la República」1923-04-11～1924-03-17（recordId e5af0194-997f-46b9-8bfd-67689c9d3842）；paraguay head_of_state「Presidente Provisorio de la República」1923-04-11～1924-03-17（recordId 6925a5f6-95bf-44cc-9394-38b5fb2a81a3）；paraguay head_of_government「Presidente de la República」1924-08-15～1928-08-15（recordId 6a90b027-024b-4505-b3c8-eda39baf3c19）；paraguay head_of_state「Presidente de la República」1924-08-15～1928-08-15（recordId 73a66e87-d878-47cc-a915-3863b3df8720）
- 阿爾弗雷多·巴克里索·莫雷諾｜Alfredo Baquerizo Moreno｜01a1b4b5-fa12-71b6-ac1b-4793f524ee01｜ecuador｜首任 1912-08-10｜中（離線推定）｜ecuador head_of_government「Presidente del Senado, en ejercicio del Poder Ejecutivo」1912-08-10～1912-09-01（recordId 596c0565-1d39-4a54-ba63-7a3af8c8aac8）；ecuador head_of_state「Presidente del Senado, en ejercicio del Poder Ejecutivo」1912-08-10～1912-09-01（recordId 59782b9e-d44a-4983-99ac-07be076ceba5）；ecuador head_of_state「Presidente de la República del Ecuador」1916-09-01～1920-09-01（recordId edc8f090-c96c-4e9c-bed5-3002c5b68aff）；ecuador head_of_government「Presidente de la República del Ecuador」1916-09-01～1920-09-01（recordId 1a0b8d48-6238-489f-8145-af6ef80158b3）；ecuador head_of_government「Ministro de Gobierno y Previsión Social, encargado del Poder Ejecutivo」1931-10-15～1931-11-11（recordId 8e7ff552-e6ad-479e-9005-a275f75fbbdb）；ecuador head_of_state「Ministro de Gobierno y Previsión Social, encargado del Poder Ejecutivo」1931-10-15～1931-11-11（recordId 1d45d36c-9d7b-4c7d-aef6-134bee332e9d）；ecuador head_of_government「Encargado del Poder Ejecutivo」1931-11-11～1932-08-28（recordId 001d04e0-449e-4208-b5f3-b36411baf7db）；ecuador head_of_state「Encargado del Poder Ejecutivo」1931-11-11～1932-08-28（recordId d17af1d3-40d2-4d92-9a5b-46442261160e）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `027`、`/Users/jack755051/wl-source-cache/b3full-v3/batch027/raw`、`data/seed/leaders/b3-trial/full/v3/batch027` 代入），全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch027/raw`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py data/seed/leaders/b3-trial/full/v3/batch027/research.json --report data/seed/leaders/b3-trial/full/v3/batch027/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。
