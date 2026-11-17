# B3 full v3 batch006：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch006/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch006/min-check.round1.json`）：
- 哈康七世｜Haakon VII｜01a1b4af-e4c4-7b77-902a-f3ab6333bdeb｜kingdom-of-norway｜首任 1908-01-01｜薄（離線推定）｜kingdom-of-norway head_of_state「」1908-01-01～1940-04-09（recordId bbe2536e-104a-4dc7-b7ee-8c805179c849）；kingdom-of-norway head_of_state「」1945-05-08～1945-10-01（recordId 387d3549-1d29-4b19-8593-c6c19b913d1d）
- 熱圖利奧·瓦加斯｜Getúlio Dornelles Vargas｜1b13259b-f739-4d2e-b0a7-693a20e1412f｜brazil｜首任 1930-11-03｜中（離線推定）｜brazil head_of_government「Presidente da República dos Estados Unidos do Brasil」1930-11-03～1934-07-16（recordId 0c517c0c-50b6-4251-aba7-315f5426d330）；brazil head_of_state「Presidente da República dos Estados Unidos do Brasil」1930-11-03～1934-07-16（recordId 6f161008-b118-47f2-ba17-c9614a5987c7）；brazil head_of_state「Presidente da República dos Estados Unidos do Brasil」1934-07-16～1934-07-20（recordId e72520c8-7f11-4d3a-a0be-257fc055b575）；brazil head_of_government「Presidente da República dos Estados Unidos do Brasil」1934-07-16～1934-07-20（recordId e6fc49ba-f227-46cf-813e-2307a10f3b9e）；brazil head_of_government「Presidente da República dos Estados Unidos do Brasil」1934-07-20～1937-11-10（recordId 1eb907b7-83bf-41c6-95ed-618c81537a47）；brazil head_of_state「Presidente da República dos Estados Unidos do Brasil」1934-07-20～1937-11-10（recordId cecb19de-1793-41d7-a769-6f9fd35e2751）；brazil head_of_government「Presidente da República dos Estados Unidos do Brasil」1937-11-10～1945-10-01（recordId 7bae4a7c-7f3a-45e6-a576-1dadd8279b19）；brazil head_of_state「Presidente da República dos Estados Unidos do Brasil」1937-11-10～1945-10-01（recordId 47cd3ee9-81f0-410c-bbd4-7b62805b226a）
- 蒂武西奧·卡里亞斯·安迪諾｜Tiburcio Carías Andino｜01a1b4af-e4d3-7ad2-9ffc-12ef64db0a69｜honduras｜首任 1933-02-01｜中（離線推定）｜honduras head_of_government「Presidente de la República de Honduras」1933-02-01～1945-10-01（recordId 01a1aa4a-727c-700f-b741-18cba3f969e1）；honduras head_of_state「Presidente de la República de Honduras」1933-02-01～1945-10-01（recordId 01a1aa4a-727b-7e35-8f4a-c1e6e6799a66）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `006`、`/Users/jack755051/wl-source-cache/b3full-v3/batch006/raw`、`data/seed/leaders/b3-trial/full/v3/batch006` 代入），全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch006/raw`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py data/seed/leaders/b3-trial/full/v3/batch006/research.json --report data/seed/leaders/b3-trial/full/v3/batch006/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。
