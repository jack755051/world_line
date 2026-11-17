# B3 full v3 batch047：加強搜尋重跑（Sonnet，新 session，勿 --resume）

<!-- b3v3-token-2026-11-17 -->
只重跑任務點名的人。抓取與 quote 一律用 `tools/b3v3/fetch_source.py`（先 status，已有的 sourceKey 不要重抓；fetch 只印命中段落；lookup 查片段）。禁止 Read／cat 整份 raw，禁止把整頁貼進上下文。WebFetch 只用於發現網址。不要跑 check_min.py（工作流會寫 `check_min-report.json`）。若任務要你寫單人檔，覆寫 `data/seed/leaders/b3-trial/full/v3/batch047/people/<bioId>.json`，不要重寫整份 research.json。最低搜尋量、來源分級、原文語言查詢、不用 `-k`、不用 Wayback、403 就放棄，全部仍適用。

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch047/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch047/min-check.round1.json`）：
- 拉蒙·卡塞雷斯｜Ramón Cáceres Vásquez｜01a1b4b8-e97b-73a9-9693-22f309cc77bb｜dominican-republic｜首任 1908-01-01｜中（離線推定）｜dominican-republic head_of_state「Presidente de la República」1908-01-01～1911-11-19（recordId 58b726e7-de63-48d3-a24f-4b5c330b8bc4）；dominican-republic head_of_government「Presidente de la República」1908-01-01～1911-11-19（recordId 82f9fd16-5263-45ee-a542-c0b6546f42d2）
- 佩爾·埃溫德·斯溫胡武德｜Pehr Evind Svinhufvud｜01a1b4bb-072b-763e-abc4-50f0d1067d7e｜republic-of-finland｜首任 1917-12-06｜中（離線推定）｜republic-of-finland head_of_government「Pääministeri / Senaatin (vara)puheenjohtaja（政府首腦）」1917-12-06～1918-05-27（recordId 01a1aa4a-4c33-720b-adb3-33e5553690ff）；republic-of-finland head_of_state「Suomen Senaatin puheenjohtaja（maan korkeimman vallan haltija）」1918-05-18～1918-12-12（recordId 01a1aa4a-4c31-7bba-a133-0cc7843197fd）；republic-of-finland head_of_government「Pääministeri / Senaatin (vara)puheenjohtaja（政府首腦）」1930-07-04～1931-03-21（recordId 01a1aa4a-4c35-7541-8955-d995d7ba714d）；republic-of-finland head_of_state「President of the Republic」1931-03-01～1937-03-01（recordId 01a1aa4a-4c32-7631-a650-5af92c450431）
- 羅克·薩恩斯·佩尼亞｜Roque Sáenz Peña｜dece85ed-1168-4d8c-bc1a-1a2f6bf3e65a｜argentina｜首任 1910-10-12｜中（離線推定）｜argentina head_of_government「Presidente de la Nación Argentina」1910-10-12～1914-08-09（recordId 607936ae-fbc7-48ba-8614-fe50bdf5bc94）；argentina head_of_state「Presidente de la Nación Argentina」1910-10-12～1914-08-09（recordId 1be1ecad-e5f4-4802-9360-425134929fd7）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `047`、`/Users/jack755051/wl-source-cache/b3full-v3/batch047/raw`、`data/seed/leaders/b3-trial/full/v3/batch047` 代入），全部照舊適用；先讀它。若任務給了單人檔，只讀那一份與其中的 searchLog，不要讀整份 research.json。
- **只改上列人物**的條目（任務若指定單人檔，只改該檔的 person，不要重寫整份 research.json；否則才改 research.json。欄位仍是 paragraphs／positions／roleCandidates／gaps／searchLog／sources）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch047/raw`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少用 tools/b3v3/fetch_source.py 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 不要自己跑 verify.py 或 check_min.py（單人檔尚未合併）。工作流合併後會跑這兩支。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。

上述檔首的 2026-11-17 token 節流優先於本文其餘句子，包含文末「優先於上文」的舊追加。
