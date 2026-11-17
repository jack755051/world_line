# B3 full v3 batch075：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch075/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch075/min-check.round1.json`）：
- 弗洛倫西奧·阿爾莫迪奧·阿羅塞梅納｜Florencio Harmodio Arosemena｜01a1b4c1-ce67-7a1d-bb23-5cc005fd8f68｜panama｜首任 1928-10-01｜薄（離線推定）｜panama head_of_state「Presidente de la República」1928-10-01～1931-01-02（recordId 01a1aa4a-72a1-7270-91bb-9be873d16d80）；panama head_of_government「Presidente de la República」1928-10-01～1931-01-02（recordId 01a1aa4a-72a1-7491-84da-a876d8de8729）
- 亞歷山大·切爾維亞科夫｜Aleksandr Grigoryevich Chervyakov｜01a1b4c1-ce6e-73f1-812c-7901dde51d5b｜byelorussian-ssr-1919｜首任 1920-07-30｜中（離線推定）｜byelorussian-ssr-1919 head_of_state「Chairman of the Military Revolutionary Committee」1920-07-30～1920-12-18（recordId 01a1aa4a-954b-7be3-95e1-1fd9a60da5c6）；byelorussian-ssr-1919 head_of_government「Chairman of the Council of People's Commissars」1920-12-18～1922-12-30（recordId 01a1aa4a-954b-7fa2-8dbd-843fdbc0014e）；byelorussian-ssr-1919 head_of_state「Chairman of the Central Executive Committee」1920-12-18～1922-12-30（recordId 01a1aa4a-954b-7dca-a7e5-670a3c5cdffd）
- 亞歷山大·米勒蘭｜Alexandre Millerand｜d39b770b-d2d7-4d8e-93db-229e37b5adbc｜french-third-republic｜首任 1920-01-20｜中（離線推定）｜french-third-republic head_of_government「Président du Conseil des ministres」1920-01-20～1920-02-18（recordId 01a1a20c-b8fa-7cab-8c88-90554561aef9）；french-third-republic head_of_government「Président du Conseil des ministres」1920-02-18～1920-09-24（recordId 01a1a20c-b900-75f4-a156-40cc85caf76b）；french-third-republic head_of_state「Président du Conseil des ministres（依 1875 年憲法由部長會議代行總統職權）」1920-09-21～1920-09-23（recordId 01a19eb7-af98-733e-81a0-80d5097f027d）；french-third-republic head_of_state「Président de la République française」1920-09-23～1924-06-11（recordId 01a19eb7-afae-75f2-a8d0-637a4bb44360）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `075`、`/Users/jack755051/wl-source-cache/b3full-v3/batch075/raw`、`data/seed/leaders/b3-trial/full/v3/batch075` 代入），全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch075/raw`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py data/seed/leaders/b3-trial/full/v3/batch075/research.json --report data/seed/leaders/b3-trial/full/v3/batch075/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。
