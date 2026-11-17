# B3 full v3 batch060：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch060/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch060/min-check.round1.json`）：
- 喬瓦尼·焦利蒂｜Giovanni Giolitti｜02c63ee6-5546-4b01-a428-e85bfc003b7d｜kingdom-of-italy｜首任 1908-01-01｜中（離線推定）｜kingdom-of-italy head_of_government「Presidente del Consiglio dei ministri」1908-01-01～1909-12-11（recordId 881e1b24-bc74-4eea-b370-e58944135820）；kingdom-of-italy head_of_government「Presidente del Consiglio dei ministri」1911-03-30～1914-03-21（recordId 01a19eb7-b010-7173-abe3-5cd708a0e6ab）；kingdom-of-italy head_of_government「Presidente del Consiglio dei ministri」1920-06-15～1921-07-04（recordId 01a19eb7-b04c-70aa-96db-c2a512fc7e09）
- 亞歷山德拉斯·斯圖爾金斯基斯｜Aleksandras Stulginskis｜01a1b4bb-0746-7c81-86c9-aeddd27fff40｜republic-of-lithuania｜首任 1920-06-19｜薄（離線推定）｜republic-of-lithuania head_of_state「Acting President of the Republic」1920-06-19～1922-12-21（recordId 01a1aa4a-659b-76a0-9f74-74ff4c0eb7d1）；republic-of-lithuania head_of_state「President of the Republic」1922-12-21～1926-06-07（recordId 01a1aa4a-659b-794e-a6c5-cbe47715871c）
- 佩德羅·阿吉雷·塞爾達｜Pedro Aguirre Cerda｜aecd36be-887c-4c7f-9310-38678f016443｜chile｜首任 1938-12-24｜中（離線推定）｜chile head_of_state「Presidente de la República de Chile」1938-12-24～1941-11-25（recordId 78bc2607-d9cc-493c-8748-703e6c008812）；chile head_of_government「Presidente de la República de Chile」1938-12-24～1941-11-25（recordId 044dd194-4ff5-4d10-826b-847026379b05）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `060`、`/Users/jack755051/wl-source-cache/b3full-v3/batch060/raw`、`data/seed/leaders/b3-trial/full/v3/batch060` 代入），全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch060/raw`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py data/seed/leaders/b3-trial/full/v3/batch060/research.json --report data/seed/leaders/b3-trial/full/v3/batch060/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。
