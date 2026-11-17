# B3 full v3 batch053：加強搜尋重跑（Sonnet，新 session，勿 --resume）

<!-- b3v3-token-2026-11-17 -->
只重跑任務點名的人。抓取與 quote 一律用 `tools/b3v3/fetch_source.py`（先 status，已有的 sourceKey 不要重抓；fetch 只印命中段落；lookup 查片段）。禁止 Read／cat 整份 raw，禁止把整頁貼進上下文。WebFetch 只用於發現網址。不要跑 check_min.py（工作流會寫 `check_min-report.json`）。若任務要你寫單人檔，覆寫 `data/seed/leaders/b3-trial/full/v3/batch053/people/<bioId>.json`，不要重寫整份 research.json。最低搜尋量、來源分級、原文語言查詢、不用 `-k`、不用 Wayback、403 就放棄，全部仍適用。

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch053/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch053/min-check.round1.json`）：
- 揚尼斯·查克斯特｜Jānis Čakste｜01a1b4b8-ea08-738d-a396-42955eacb7e3｜republic-of-latvia｜首任 1920-05-01｜薄（離線推定）｜republic-of-latvia head_of_state「President of the Constituent Assembly」1920-05-01～1922-11-07（recordId 01a1aa4a-6597-76d0-938a-ef02f0ff5a2e）；republic-of-latvia head_of_state「Acting State President」1922-11-07～1922-11-18（recordId 01a1aa4a-6599-7a5a-a5bb-4431e47eb14c）；republic-of-latvia head_of_state「State President」1922-11-18～1925-11-03（recordId 01a1aa4a-6599-7dcf-924c-472e499859d0）；republic-of-latvia head_of_state「State President」1925-11-10～1927-03-14（recordId 01a1aa4a-659a-73be-b29e-7e5be0c73b82）
- 亨德里克斯·科林｜Hendrikus Colijn｜01a1b4b5-71e3-7cda-8438-a26f4ffb78fc｜kingdom-of-the-netherlands｜首任 1925-08-04｜薄（離線推定）｜kingdom-of-the-netherlands head_of_government「Minister-president / Voorzitter van de ministerraad」1925-08-04～1926-03-08（recordId 01a1aa4a-59af-7d64-bff6-311f0565942e）；kingdom-of-the-netherlands head_of_government「Minister-president / Voorzitter van de ministerraad」1933-05-26～1939-08-10（recordId 01a1aa4a-59b0-7405-ac9a-f89b30c92db8）
- 拉姆齊·麥克唐納｜James Ramsay MacDonald｜01a19f15-3480-7a0d-a003-e8ec492198ce｜united-kingdom｜首任 1924-01-22｜中（離線推定）｜united-kingdom head_of_government「Prime Minister and First Lord of the Treasury」1924-01-22～1924-11-04（recordId 01a19ec8-76e7-7961-b8bd-884fdd67393e）；united-kingdom head_of_government「Prime Minister and First Lord of the Treasury」1929-06-05～1931-08-24（recordId 01a19ec8-76ed-7cb3-aadc-c4b0c20e1d79）；united-kingdom head_of_government「Prime Minister and First Lord of the Treasury」1931-08-24～1935-06-07（recordId 01a19ec8-76f3-7b3c-9479-da14eae234f0）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `053`、`/Users/jack755051/wl-source-cache/b3full-v3/batch053/raw`、`data/seed/leaders/b3-trial/full/v3/batch053` 代入），全部照舊適用；先讀它。若任務給了單人檔，只讀那一份與其中的 searchLog，不要讀整份 research.json。
- **只改上列人物**的條目（任務若指定單人檔，只改該檔的 person，不要重寫整份 research.json；否則才改 research.json。欄位仍是 paragraphs／positions／roleCandidates／gaps／searchLog／sources）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch053/raw`。
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
