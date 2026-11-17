# B3 full v3 batch036：加強搜尋重跑（Sonnet，新 session，勿 --resume）

<!-- b3v3-token-2026-11-17 -->
只重跑任務點名的人。抓取與 quote 一律用 `tools/b3v3/fetch_source.py`（先 status，已有的 sourceKey 不要重抓；fetch 只印命中段落；lookup 查片段）。禁止 Read／cat 整份 raw，禁止把整頁貼進上下文。WebFetch 只用於發現網址。不要跑 check_min.py（工作流會寫 `check_min-report.json`）。若任務要你寫單人檔，覆寫 `data/seed/leaders/b3-trial/full/v3/batch036/people/<bioId>.json`，不要重寫整份 research.json。最低搜尋量、來源分級、原文語言查詢、不用 `-k`、不用 Wayback、403 就放棄，全部仍適用。

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch036/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch036/min-check.round1.json`）：
- 尼古拉一世｜Nikola I Petrović-Njegoš｜01a1b4bf-610f-7502-b963-13422303a898｜kingdom-of-montenegro、principality-of-montenegro｜首任 1908-01-01｜薄（離線推定）｜principality-of-montenegro head_of_state「」1908-01-01～1910-08-28（recordId 8f0972e5-7057-479d-959d-7e13fce2dd1d）；kingdom-of-montenegro head_of_state「By the Grace of God, King and Lord of Montenegro」1910-08-28～1916-01-13（recordId 01a1aa4a-655c-7818-8c13-b84cfa48abdd）；kingdom-of-montenegro head_of_state「By the Grace of God, King and Lord of Montenegro」1918-11-03～1918-11-26（recordId 01a1aa4a-655c-79e6-9f75-8ccb5b152be0）
- 哈莫迪奧·阿里亞斯｜Harmodio Arias Madrid｜01a1b4b5-fa26-76c6-a546-d6a8611ccd42｜panama｜首任 1931-01-02｜中（離線推定）｜panama head_of_state「Secretario de Gobierno y Justicia, Encargado del Poder Ejecutivo」1931-01-02～1931-01-16（recordId 01a1aa4a-72a1-7681-8795-1bf0433d5c2c）；panama head_of_government「Secretario de Gobierno y Justicia, Encargado del Poder Ejecutivo」1931-01-02～1931-01-16（recordId 01a1aa4a-72a1-7856-bb7d-c44436e8edef）；panama head_of_state「Presidente de la República」1932-10-01～1936-10-01（recordId 01a1aa4a-72a1-7de3-9f26-d6dcdba7c9e7）；panama head_of_government「Presidente de la República」1932-10-01～1936-10-01（recordId 01a1aa4a-72a1-7fb0-8106-7c0b0e8fe542）
- 泰奧巴爾德·馮·貝特曼·霍爾韋格｜Theobald von Bethmann Hollweg｜01a19f15-369b-7322-8ba3-e8969a578b89｜german-empire｜首任 1909-07-07｜中（離線推定）｜german-empire head_of_government「Reichskanzler」1909-07-07～1917-07-14（recordId 01a1a20a-76d9-71df-9053-2a2f599d72c4）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `036`、`/Users/jack755051/wl-source-cache/b3full-v3/batch036/raw`、`data/seed/leaders/b3-trial/full/v3/batch036` 代入），全部照舊適用；先讀它。若任務給了單人檔，只讀那一份與其中的 searchLog，不要讀整份 research.json。
- **只改上列人物**的條目（任務若指定單人檔，只改該檔的 person，不要重寫整份 research.json；否則才改 research.json。欄位仍是 paragraphs／positions／roleCandidates／gaps／searchLog／sources）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch036/raw`。
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
