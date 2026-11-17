# B3 full v3 batch150：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch150/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch150/min-check.round1.json`）：
- 阿道夫·德拉韋爾塔｜Adolfo de la Huerta｜01a1aa4a-da3e-7c67-aee0-cb3cb0bcae4f｜mexico｜首任 1920-04-23｜中（離線推定）｜mexico head_of_state「［對立政府 rival_government］」1920-04-23～1920-06-01（recordId 24802667-8af2-4271-8b2e-f5174d8e3e9d）；mexico head_of_government「［對立政府 rival_government］」1920-04-23～1920-06-01（recordId 509a1800-e9f2-4308-9b5b-dc710046eed2）；mexico head_of_state「」1920-06-01～1920-12-01（recordId c1b6801d-3d2e-4260-b30c-fc5ba9179594）；mexico head_of_government「」1920-06-01～1920-12-01（recordId 8526df7f-de78-4e41-a563-c233361617cb）
- 加藤友三郎｜加藤友三郎｜9fce0e98-df01-428d-8137-cdd2aeb239e7｜empire-of-japan｜首任 1922-06-12｜中（離線推定）｜empire-of-japan head_of_government「内閣総理大臣」1922-06-12～1923-08-24（recordId 01a19eb7-b1bc-7801-8809-8ee58d3eb955）
- 米格爾·馬里亞諾·戈麥斯｜Miguel Mariano Gómez y Arias｜01a1b533-d7ba-7da7-80e1-37d8051ddf18｜cuba｜首任 1936-05-20｜薄（離線推定）｜cuba head_of_state「Presidente de la República」1936-05-20～1936-12-24（recordId 78ed3cec-bc59-423e-8140-f1ab42956c5f）；cuba head_of_government「Presidente de la República」1936-05-20～1936-12-24（recordId b9439128-a0b3-478a-9dbf-2dc1a9759795）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `150`、`/Users/jack755051/wl-source-cache/b3full-v3/batch150/raw`、`data/seed/leaders/b3-trial/full/v3/batch150` 代入），全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch150/raw`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py data/seed/leaders/b3-trial/full/v3/batch150/research.json --report data/seed/leaders/b3-trial/full/v3/batch150/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。
