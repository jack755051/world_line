# B3 full v3 batch065：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch065/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch065/min-check.round1.json`）：
- 阿爾弗雷多·岡薩雷斯·弗洛雷斯｜Alfredo González Flores｜01a1b4bb-07a9-7f47-bb1d-b913b38ae622｜costa-rica｜首任 1914-05-08｜薄（離線推定）｜costa-rica head_of_government「Presidente Constitucional de la República de Costa Rica」1914-05-08～1917-01-27（recordId 01a1aa4a-728c-731f-9165-5900548877b2）；costa-rica head_of_state「Presidente Constitucional de la República de Costa Rica」1914-05-08～1917-01-27（recordId 01a1aa4a-728c-711a-8f9e-7c3dd7f47fe7）
- 阿爾維德·林德曼｜Arvid Lindman｜01a1b4bf-60f2-74e4-829d-0f209fb93efa｜kingdom-of-sweden｜首任 1908-01-01｜中（離線推定）｜kingdom-of-sweden head_of_government「」1908-01-01～1911-10-07（recordId 8e9db32b-ea1f-433b-8032-e3f75aafd8e7）；kingdom-of-sweden head_of_government「Statsminister」1928-10-02～1930-06-07（recordId 01a1aa4a-45bc-716b-b8ca-1d11b940c13f）
- 尼塞托·阿爾卡拉-薩莫拉｜Niceto Alcalá-Zamora y Torres｜01a1b4bf-6119-7cd5-8b47-85c8557e0be2｜spanish-republic｜首任 1931-04-14｜中（離線推定）｜spanish-republic head_of_state「Presidente del Gobierno Provisional de la República」1931-04-14～1931-07-30（recordId 01a1aa4a-4a40-7d0a-82b8-dd357e922c42）；spanish-republic head_of_government「Presidente del Gobierno Provisional de la República」1931-04-14～1931-07-30（recordId 01a1aa4a-4a41-7b09-8e2e-35a535e0646c）；spanish-republic head_of_government「Presidente del Gobierno de la República Española」1931-07-30～1931-10-14（recordId 01a1aa4a-4a43-75b3-8302-bc34bfd9c981）；spanish-republic head_of_state「Presidente del Gobierno de la República Española」1931-07-30～1931-10-14（recordId 01a1aa4a-4a42-7859-bced-14924366f200）；spanish-republic head_of_state「Presidente de la República」1931-12-11～1936-04-07（recordId 01a1aa4a-4a45-7da5-bffb-03cb9e5a301c）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `065`、`/Users/jack755051/wl-source-cache/b3full-v3/batch065/raw`、`data/seed/leaders/b3-trial/full/v3/batch065` 代入），全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch065/raw`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py data/seed/leaders/b3-trial/full/v3/batch065/research.json --report data/seed/leaders/b3-trial/full/v3/batch065/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。
