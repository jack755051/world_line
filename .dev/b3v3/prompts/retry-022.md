# B3 full v3 batch022：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch022/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch022/min-check.round1.json`）：
- 林森｜Lín Sēn｜01a1b490-dcec-7c4e-9a70-1998abcae454｜republic-of-china-nationalist｜首任 1931-12-15｜中（離線推定）｜republic-of-china-nationalist head_of_state「代理國民政府主席」1931-12-15～1931-12-28（recordId 01a1a20c-bc79-7d6c-8ff3-74a05b2e3891）；republic-of-china-nationalist head_of_state「國民政府主席」1931-12-28～1943-08-01（recordId 01a1a20c-bc94-747d-af8d-cabf35265299）
- 貝努斯蒂亞諾·卡蘭薩｜Venustiano Carranza｜01a1b488-14b7-79d8-b825-78d8d5c687e0｜mexico｜首任 1914-08-20｜中（離線推定）｜mexico head_of_government「」1914-08-20～1917-05-01（recordId ad20d540-4812-4f64-971b-ad25426acd13）；mexico head_of_state「」1914-08-20～1917-05-01（recordId 1aa4cbbe-5340-4bd8-b5d0-98f16a4a5223）；mexico head_of_government「」1917-05-01～1920-05-21（recordId 6293c719-b285-439e-b455-dd6742c17592）；mexico head_of_state「」1917-05-01～1920-05-21（recordId 7af646fc-e034-48dd-b4d9-c284ba636bd7）
- 約瑟夫·貝希｜Joseph Bech｜01a1b4b0-7015-7c59-8efb-ae8bdd8d10e8｜grand-duchy-of-luxembourg｜首任 1926-07-15｜厚（離線推定）｜grand-duchy-of-luxembourg head_of_government「Ministre d’État, Président du gouvernement」1926-07-15～1937-11-05（recordId 01a1aa4a-59cb-7ccb-8f9e-ee9f1304f21a）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `022`、`/Users/jack755051/wl-source-cache/b3full-v3/batch022/raw`、`data/seed/leaders/b3-trial/full/v3/batch022` 代入），全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch022/raw`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py data/seed/leaders/b3-trial/full/v3/batch022/research.json --report data/seed/leaders/b3-trial/full/v3/batch022/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。
