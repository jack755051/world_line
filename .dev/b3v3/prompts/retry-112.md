# B3 full v3 batch112：加強搜尋重跑（Sonnet，新 session，勿 --resume）

<!-- b3v3-token-2026-11-17 -->
只重跑任務點名的人。抓取與 quote 一律用 `tools/b3v3/fetch_source.py`（先 status，已有的 sourceKey 不要重抓；fetch 只印命中段落；lookup 查片段）。禁止 Read／cat 整份 raw，禁止把整頁貼進上下文。WebFetch 只用於發現網址。不要跑 check_min.py（工作流會寫 `check_min-report.json`）。若任務要你寫單人檔，覆寫 `data/seed/leaders/b3-trial/full/v3/batch112/people/<bioId>.json`，不要重寫整份 research.json。最低搜尋量、來源分級、原文語言查詢、不用 `-k`、不用 Wayback、403 就放棄，全部仍適用。

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch112/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch112/min-check.round1.json`）：
- 特奧菲洛·布拉加｜Teófilo Braga｜01a1b539-97cc-7903-9991-9d647bd5a572｜portuguese-republic｜首任 1910-10-05｜薄（離線推定）｜portuguese-republic head_of_government「Presidente do Governo Provisório da República Portuguesa」1910-10-05～1911-09-03（recordId 01a1aa4a-45bf-753a-b1db-5957aa08b498）；portuguese-republic head_of_state「Presidente do Governo Provisório da República Portuguesa」1910-10-05～1911-08-24（recordId 01a1aa4a-45bc-7ff4-861b-b0bdb59e5d1d）；portuguese-republic head_of_state「Presidente da República」1915-05-29～1915-10-05（recordId 01a1aa4a-45bd-73e8-a250-f2c1f850cf53）
- 阿斯蓋爾·阿斯蓋爾鬆｜Ásgeir Ásgeirsson｜01a1b51c-8340-7f58-8799-6e1f516dbc88｜kingdom-of-iceland｜首任 1932-06-03｜中（離線推定）｜kingdom-of-iceland head_of_government「forsætisráðherra」1932-06-03～1934-07-28（recordId 01a1aa4a-669d-793a-b478-c44c20dbb479）
- 路易斯·桑切斯·塞羅｜Luis Miguel Sánchez Cerro｜eb6e6997-c44d-40fe-85a7-2ba4d0b324dd｜peru｜首任 1930-08-28｜中（離線推定）｜peru head_of_government「Presidente del Consejo de Ministros」1930-08-28～1930-11-24（recordId 96cc0e9f-dfbe-4d54-a546-83cdc399becf）；peru head_of_state「Presidente de la Junta de Gobierno」1930-08-28～1931-03-01（recordId 59ae8d10-4ba8-436f-8b39-2d7d54ee2355）；peru head_of_state「Presidente Constitucional」1931-12-08～1933-04-30（recordId f98a8fea-6fda-4e7b-8822-fdea94e1ac38）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `112`、`/Users/jack755051/wl-source-cache/b3full-v3/batch112/raw`、`data/seed/leaders/b3-trial/full/v3/batch112` 代入），全部照舊適用；先讀它。若任務給了單人檔，只讀那一份與其中的 searchLog，不要讀整份 research.json。
- **只改上列人物**的條目（任務若指定單人檔，只改該檔的 person，不要重寫整份 research.json；否則才改 research.json。欄位仍是 paragraphs／positions／roleCandidates／gaps／searchLog／sources）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch112/raw`。
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
