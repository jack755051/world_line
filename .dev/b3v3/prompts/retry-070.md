# B3 full v3 batch070：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch070/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch070/min-check.round1.json`）：
- 彼得·科特·范德林登｜Pieter Wilhelm Adriaan Cort van der Linden｜01a1b4c0-2f69-7df2-983c-0d454a7e2c71｜kingdom-of-the-netherlands｜首任 1913-08-30｜中（離線推定）｜kingdom-of-the-netherlands head_of_government「Minister-president / Voorzitter van de ministerraad」1913-08-30～1918-09-09（recordId 01a1aa4a-59af-7901-9e40-3cc16ecf6356）
- 伊格納茨·賽佩爾｜Ignaz Seipel｜01a1b4c0-2f6f-790c-bf2d-a2848d1295b8｜federal-state-of-austria、republic-of-austria-1918｜首任 1922-05-31｜薄（離線推定）｜republic-of-austria-1918 head_of_government「Bundeskanzler」1922-05-31～1922-10-01（recordId 01a1aa4a-a0b9-7a8e-ac73-c03b9b0da46d）；federal-state-of-austria head_of_government「Bundeskanzler」1922-10-01～1924-11-20（recordId 01a1aa4a-a0bc-73ba-a541-61b40a241b38）；federal-state-of-austria head_of_government「Bundeskanzler」1926-10-20～1929-05-04（recordId 01a1aa4a-a0bc-78e6-aa32-70533c19ed60）
- 朱塞佩·莫塔｜Giuseppe Motta｜01a1b4c0-2f7a-7550-9122-c9dbf6f853f9｜swiss-confederation｜首任 1915-01-01｜中（離線推定）｜swiss-confederation head_of_state「Presidente della Confederazione（Bundespräsident）」1915-01-01～1916-01-01（recordId 01a1aa4a-4ded-7db9-bb2a-4fe076678ded）；swiss-confederation head_of_state「Presidente della Confederazione（Bundespräsident）」1920-01-01～1921-01-01（recordId 01a1aa4a-4df0-770c-b764-c0171b75a22f）；swiss-confederation head_of_state「Presidente della Confederazione（Bundespräsident）」1927-01-01～1928-01-01（recordId 01a1aa4a-4df3-7b1f-9bc2-9ef7228baf20）；swiss-confederation head_of_state「Presidente della Confederazione（Bundespräsident）」1932-01-01～1933-01-01（recordId 01a1aa4a-4df6-710b-8dfb-02be26219bb9）；swiss-confederation head_of_state「Presidente della Confederazione（Bundespräsident）」1937-01-01～1938-01-01（recordId 01a1aa4a-4df8-70d0-af56-a5531ca6767e）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `070`、`/Users/jack755051/wl-source-cache/b3full-v3/batch070/raw`、`data/seed/leaders/b3-trial/full/v3/batch070` 代入），全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch070/raw`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py data/seed/leaders/b3-trial/full/v3/batch070/research.json --report data/seed/leaders/b3-trial/full/v3/batch070/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。
