# B3 full v3 batch024：加強搜尋重跑（Sonnet，新 session，勿 --resume）

<!-- b3v3-token-2026-11-17 -->
只重跑任務點名的人。抓取與 quote 一律用 `tools/b3v3/fetch_source.py`（先 status，已有的 sourceKey 不要重抓；fetch 只印命中段落；lookup 查片段）。禁止 Read／cat 整份 raw，禁止把整頁貼進上下文。WebFetch 只用於發現網址。不要跑 check_min.py（工作流會寫 `check_min-report.json`）。若任務要你寫單人檔，覆寫 `data/seed/leaders/b3-trial/full/v3/batch024/people/<bioId>.json`，不要重寫整份 research.json。最低搜尋量、來源分級、原文語言查詢、不用 `-k`、不用 Wayback、403 就放棄，全部仍適用。

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch024/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch024/min-check.round1.json`）：
- 彼得一世｜Petar I Karađorđević｜01a1b4b5-fa1f-795d-bad5-3703dfd0736d｜kingdom-of-serbia、kingdom-of-serbs-croats-and-slovenes｜首任 1908-01-01｜薄（離線推定）｜kingdom-of-serbia head_of_state「By the Grace of God and by the Will of the People, King of Serbia」1908-01-01～1915-11-28（recordId 01a1aa4a-655c-746a-a3e2-1ff93c934430）；kingdom-of-serbia head_of_state「By the Grace of God and by the Will of the People, King of Serbia」1918-09-29～1918-12-01（recordId 01a1aa4a-655c-764a-8b21-ca7300fef9fa）；kingdom-of-serbs-croats-and-slovenes head_of_state「By the Grace of God and People's Will, King of the Serbs, Croats and Slovenes」1918-12-01～1921-08-16（recordId 01a1aa4a-655b-7726-a81f-2b9fc10c9f3c）
- 埃萊亞薩爾·洛佩斯·孔特雷拉斯｜Eleazar López Contreras｜01a1aa4a-da75-71d2-9b14-f5b9feaed5f8｜united-states-of-venezuela｜首任 1935-12-18｜中（離線推定）｜united-states-of-venezuela head_of_government「」1935-12-18～1935-12-31（recordId 085017b6-c331-4564-8133-47099eca2e41）；united-states-of-venezuela head_of_state「」1935-12-18～1935-12-31（recordId 2674040f-7438-48e2-9c17-148f1902729e）；united-states-of-venezuela head_of_state「」1935-12-31～1936-04-19（recordId d4801348-c346-4060-96e1-836980f62b87）；united-states-of-venezuela head_of_government「」1935-12-31～1936-04-19（recordId d371bddd-db2b-472d-b90d-8792f99effa5）；united-states-of-venezuela head_of_government「」1936-04-29～1941-04-19（recordId 86c7831a-17fd-4712-86c8-25f69915952e）；united-states-of-venezuela head_of_state「」1936-04-29～1941-04-19（recordId f42d3cf5-886e-4eab-af63-c6f3e5c37d82）；united-states-of-venezuela head_of_state「」1941-04-19～1941-05-05（recordId 6a89c106-0f85-4e79-bb44-4242d38c9d28）；united-states-of-venezuela head_of_government「」1941-04-19～1941-05-05（recordId 2b5ca284-970b-4b9b-a406-756db1395547）
- 查爾斯·勒伊斯·德貝倫布魯克｜Charles Ruijs de Beerenbrouck｜01a1b4ae-0ddc-79c6-ad25-0cddd7bc4cf4｜kingdom-of-the-netherlands｜首任 1918-09-09｜薄（離線推定）｜kingdom-of-the-netherlands head_of_government「Minister-president / Voorzitter van de ministerraad」1918-09-09～1925-08-04（recordId 01a1aa4a-59af-7b34-a928-7cbcdcff0c45）；kingdom-of-the-netherlands head_of_government「Minister-president / Voorzitter van de ministerraad」1929-08-10～1933-05-26（recordId 01a1aa4a-59b0-71c0-8e46-56e1695a2819）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `024`、`/Users/jack755051/wl-source-cache/b3full-v3/batch024/raw`、`data/seed/leaders/b3-trial/full/v3/batch024` 代入），全部照舊適用；先讀它。若任務給了單人檔，只讀那一份與其中的 searchLog，不要讀整份 research.json。
- **只改上列人物**的條目（任務若指定單人檔，只改該檔的 person，不要重寫整份 research.json；否則才改 research.json。欄位仍是 paragraphs／positions／roleCandidates／gaps／searchLog／sources）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch024/raw`。
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
