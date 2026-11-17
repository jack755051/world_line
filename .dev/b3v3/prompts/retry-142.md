# B3 full v3 batch142：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch142/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch142/min-check.round1.json`）：
- 勒內·維維亞尼｜René Viviani｜4de5c8a0-5e5f-4b10-b598-e71258d51ca0｜french-third-republic｜首任 1914-06-13｜中（離線推定）｜french-third-republic head_of_government「Président du Conseil des ministres」1914-06-13～1914-08-26（recordId 01a1a20c-b8b7-7ef0-af5f-e7d6b285be80）；french-third-republic head_of_government「Président du Conseil des ministres」1914-08-26～1915-10-29（recordId 01a1a20c-b8bc-7304-b16c-d854758cc2c7）
- 曼努埃爾·加西亞·普列托（阿盧塞馬斯侯爵）｜Manuel García Prieto, marqués de Alhucemas｜01a1b538-0c92-7b6e-a884-2855f168c5b1｜kingdom-of-spain｜首任 1912-11-12｜薄（離線推定）｜kingdom-of-spain head_of_government「Presidente interino del Consejo de Ministros」1912-11-12～1912-11-14（recordId 01a1aa4a-4856-7201-9868-cfd999a9edb1）；kingdom-of-spain head_of_government「Presidente del Consejo de Ministros」1917-04-19～1917-06-11（recordId 01a1aa4a-4857-7e09-af99-b6fbb2a5426e）；kingdom-of-spain head_of_government「Presidente del Consejo de Ministros」1917-11-03～1918-03-22（recordId 01a1aa4a-4858-7951-8898-da712826654e）；kingdom-of-spain head_of_government「Presidente del Consejo de Ministros」1918-11-09～1918-12-05（recordId 01a1aa4a-4858-7e03-94d2-bec45e5b1500）；kingdom-of-spain head_of_government「Presidente del Consejo de Ministros」1922-12-07～1923-09-15（recordId 01a1aa4a-485a-72db-a602-92ed50e7a078）
- 尤霍·庫斯蒂·巴錫基維｜Juho Kusti Paasikivi｜01a1b538-0ca1-7863-a610-a665be8898a5｜republic-of-finland｜首任 1918-05-27｜薄（離線推定）｜republic-of-finland head_of_government「Pääministeri / Senaatin (vara)puheenjohtaja（政府首腦）」1918-05-27～1918-11-27（recordId 01a1aa4a-4c33-741a-9eeb-6448ad6a54a1）；republic-of-finland head_of_government「Pääministeri / Senaatin (vara)puheenjohtaja（政府首腦）」1944-11-17～1945-04-17（recordId 01a1aa4a-4c36-7946-ad25-30c03b6ee9fe）；republic-of-finland head_of_government「Pääministeri / Senaatin (vara)puheenjohtaja（政府首腦）」1945-04-17～1945-10-01（recordId 01a1aa96-cf95-7062-9523-02bceb042412）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `142`、`/Users/jack755051/wl-source-cache/b3full-v3/batch142/raw`、`data/seed/leaders/b3-trial/full/v3/batch142` 代入），全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch142/raw`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py data/seed/leaders/b3-trial/full/v3/batch142/research.json --report data/seed/leaders/b3-trial/full/v3/batch142/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。
