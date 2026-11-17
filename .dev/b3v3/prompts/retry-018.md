# B3 full v3 batch018：加強搜尋重跑（Sonnet，新 session，勿 --resume）

<!-- b3v3-token-2026-11-17 -->
只重跑任務點名的人。抓取與 quote 一律用 `tools/b3v3/fetch_source.py`（先 status，已有的 sourceKey 不要重抓；fetch 只印命中段落；lookup 查片段）。禁止 Read／cat 整份 raw，禁止把整頁貼進上下文。WebFetch 只用於發現網址。不要跑 check_min.py（工作流會寫 `check_min-report.json`）。若任務要你寫單人檔，覆寫 `data/seed/leaders/b3-trial/full/v3/batch018/people/<bioId>.json`，不要重寫整份 research.json。最低搜尋量、來源分級、原文語言查詢、不用 `-k`、不用 Wayback、403 就放棄，全部仍適用。

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch018/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch018/min-check.round1.json`）：
- 安塔納斯·斯梅托納｜Antanas Smetona｜01a1b4b0-6fb0-74de-9782-9ddf646af24a｜republic-of-lithuania｜首任 1918-11-12｜中（離線推定）｜republic-of-lithuania head_of_state「Chairman of the State Council of Lithuania」1918-11-12～1919-04-04（recordId 01a1aa4a-659b-73f3-95a6-f8eaefb595c3）；republic-of-lithuania head_of_state「President of the Republic」1926-12-19～1940-06-16（recordId 01a1aa4a-659b-7e9f-856d-164312053281）
- ｜Sténio Joseph Vincent｜01a1b488-14ab-7c0d-ac90-6de4edf3f6a2｜haiti｜首任 1934-08-01｜中（離線推定）｜haiti head_of_state「Président de la République」1934-08-01～1941-05-15（recordId f07b3b6b-d332-47b2-8bc8-11067f8c3bb9）；haiti head_of_government「Président de la République」1934-08-01～1941-05-15（recordId e89e24e8-7242-4a26-aff0-89d0f211235c）
- 雷蒙·普恩加萊｜Raymond Poincaré｜fd700a99-a8ac-4166-8fa5-43411fd03113｜french-third-republic｜首任 1912-01-14｜中（離線推定）｜french-third-republic head_of_government「Président du Conseil des ministres」1912-01-14～1913-01-21（recordId 01a19eb7-afca-7b57-a23e-f7d714e2a6c5）；french-third-republic head_of_state「Président de la République française」1913-02-18～1920-02-18（recordId 01a19eb7-af17-7cce-8cc7-c8d727efe22f）；french-third-republic head_of_government「Président du Conseil des ministres」1922-01-15～1924-03-29（recordId 01a1a20c-b910-787b-a522-e072721b388e）；french-third-republic head_of_government「Président du Conseil des ministres」1924-03-29～1924-06-09（recordId 01a1a20c-b916-7b50-8d50-34b0a5dd82f6）；french-third-republic head_of_government「Président du Conseil des ministres」1926-07-23～1928-11-11（recordId 01a1a20c-b9bb-7c13-8ac7-f8c3a44edb3b）；french-third-republic head_of_government「Président du Conseil des ministres」1928-11-11～1929-07-29（recordId 01a1a20c-b9bf-745a-9ccf-37693f70eb32）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `018`、`/Users/jack755051/wl-source-cache/b3full-v3/batch018/raw`、`data/seed/leaders/b3-trial/full/v3/batch018` 代入），全部照舊適用；先讀它。若任務給了單人檔，只讀那一份與其中的 searchLog，不要讀整份 research.json。
- **只改上列人物**的條目（任務若指定單人檔，只改該檔的 person，不要重寫整份 research.json；否則才改 research.json。欄位仍是 paragraphs／positions／roleCandidates／gaps／searchLog／sources）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch018/raw`。
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
