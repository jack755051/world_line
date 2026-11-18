# B3 full v3 batch074：審查（Opus，新 session，勿 --resume）

<!-- b3v3-token-2026-11-17 -->
逐字引文以 verify.py 為準。先讀同目錄 `evidence-pack.json`（工作流已產生：每個 claim 單位寫一次 text，其下 citations 逐筆含 index、quote、sourceKey、grade、verify），不要整批重讀 raw、不要重抓網頁。全批最多 1 次 spot refetch，且必須走 fetch_source.py。不要跑 check_min.py；最低標準看同目錄 `check_min-report.json`。來源分級、T14、Q1–Q10、最低嘗試仍然要查。

<!-- 佔位同 PROMPT_research.md：074、- 明治天皇（睦仁）｜Emperor Meiji (Mutsuhito)｜01a1b4c1-ce4a-79cf-bc76-f5cd4aa33622｜empire-of-japan｜首任 1908-01-01｜中（離線推定）｜empire-of-japan head_of_state「天皇」1908-01-01～1912-07-30（recordId a6500b61-984c-45c3-bfaf-14d138902406）
- 埃萊夫塞里奧斯·韋尼澤洛斯｜Eleftherios Venizelos｜01a1b4c1-ce54-723d-a25f-167e9fca0d16｜kingdom-of-greece、second-hellenic-republic｜首任 1920-10-25｜厚（離線推定）｜kingdom-of-greece head_of_state「Council of Ministers: President of the Council of Ministers (ex officio)」1920-10-25～1920-10-28（recordId 01a1aa4a-6558-7ad7-bf48-15a6d03c3690）；kingdom-of-greece head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1924-01-11～1924-02-06（recordId 01a1aa4a-65c4-7e99-a195-74eb46cabb9c）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1928-07-04～1929-06-07（recordId 01a1aa4a-65c6-7b14-8519-fb20d44e38ad）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1929-06-07～1929-12-16（recordId 01a1aa4a-65c6-7d67-9057-970e9e7a1543）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1929-12-16～1932-05-26（recordId 01a1aa4a-65c6-7fb9-9194-348a89fc9c7b）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1932-06-05～1932-11-04（recordId 01a1aa4a-65c7-747b-bbf4-925c10685e5b）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1933-01-16～1933-03-06（recordId 01a1aa4a-65c7-7923-929b-a2e25b240e98）
- 何塞·帕爾多｜José Pardo y Barreda｜164b8938-b957-4966-828b-229edf3bc58b｜peru｜首任 1908-01-01｜中（離線推定）｜peru head_of_state「Presidente Constitucional」1908-01-01～1908-09-24（recordId 343eb1b9-b4f3-44d4-9a1e-7b8d4e6a5558）；peru head_of_state「Presidente Constitucional」1915-09-24～1919-07-04（recordId 2fe90e0f-63a5-4806-b53b-963848362e17）、2026-11-15、/Users/jack755051/wl-source-cache/b3full-v3/batch074/raw、data/seed/leaders/b3-trial/full/v3/batch074 -->

授權：Tai 2026-11-11 09:30（Sonnet 查資料、Opus 審查；不寫庫、不 push）、12:12（①②④）。你是審查者：逐條核對 Sonnet 產出的 `data/seed/leaders/b3-trial/full/v3/batch074/research.json`，不合格就改成待查證（移到 gaps）或刪段，不要替它補寫新內容（只可在原文已抓、且你親自核對過的範圍內修正字句、日期、精度、欄位歸類）。分支 feature/battle-demo-v2（不要切換分支）。

## 本批 5 人
- 明治天皇（睦仁）｜Emperor Meiji (Mutsuhito)｜01a1b4c1-ce4a-79cf-bc76-f5cd4aa33622｜empire-of-japan｜首任 1908-01-01｜中（離線推定）｜empire-of-japan head_of_state「天皇」1908-01-01～1912-07-30（recordId a6500b61-984c-45c3-bfaf-14d138902406）
- 埃萊夫塞里奧斯·韋尼澤洛斯｜Eleftherios Venizelos｜01a1b4c1-ce54-723d-a25f-167e9fca0d16｜kingdom-of-greece、second-hellenic-republic｜首任 1920-10-25｜厚（離線推定）｜kingdom-of-greece head_of_state「Council of Ministers: President of the Council of Ministers (ex officio)」1920-10-25～1920-10-28（recordId 01a1aa4a-6558-7ad7-bf48-15a6d03c3690）；kingdom-of-greece head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1924-01-11～1924-02-06（recordId 01a1aa4a-65c4-7e99-a195-74eb46cabb9c）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1928-07-04～1929-06-07（recordId 01a1aa4a-65c6-7b14-8519-fb20d44e38ad）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1929-06-07～1929-12-16（recordId 01a1aa4a-65c6-7d67-9057-970e9e7a1543）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1929-12-16～1932-05-26（recordId 01a1aa4a-65c6-7fb9-9194-348a89fc9c7b）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1932-06-05～1932-11-04（recordId 01a1aa4a-65c7-747b-bbf4-925c10685e5b）；second-hellenic-republic head_of_government「Πρόεδρος του Υπουργικού Συμβουλίου / Prime Minister」1933-01-16～1933-03-06（recordId 01a1aa4a-65c7-7923-929b-a2e25b240e98）
- 何塞·帕爾多｜José Pardo y Barreda｜164b8938-b957-4966-828b-229edf3bc58b｜peru｜首任 1908-01-01｜中（離線推定）｜peru head_of_state「Presidente Constitucional」1908-01-01～1908-09-24（recordId 343eb1b9-b4f3-44d4-9a1e-7b8d4e6a5558）；peru head_of_state「Presidente Constitucional」1915-09-24～1919-07-04（recordId 2fe90e0f-63a5-4806-b53b-963848362e17）

## 必讀
1. `ARCHITECTURE.md` §16.2、§16.3、§16.3.1、§16.3.2、§16.4 與 T11／T12／T14（只讀這幾節）。**與 `data/seed/leaders/b3-trial/ARCH_TODO.md` 所列新規則衝突處，以新規則為準**；另讀 `data/seed/leaders/b3-trial/T14_RECOMMENDATION.md` §1、§4。
2. `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（研究者收到的完整規則，**所有規則同樣適用於審查**）、`data/seed/leaders/b3-trial/ALIGN.md`、`data/seed/leaders/b3-trial/verify.py`。
3. `data/seed/leaders/b3-trial/full/v3/batch074/research.json`、`data/seed/leaders/b3-trial/full/v3/batch074/rawmap.json`、以及同目錄的 `evidence-pack.json`（每個 claim 單位的 text 只寫一次，citations 逐筆含 index、quote、sourceKey、grade、verify）。不要 Read／cat 整份 raw 原文。

## 審查項目（每段、每職位、每筆候選角色、每筆 citation）
1. 出處：sourceKey 存在、URL 真實可開（全批最多 1 次抽查重抓，而且只能呼叫 tools/b3v3/fetch_source.py（只看它印出的短摘））、不是 Wikipedia／Wikidata／百度、不是用防機器人繞過取得。
2. 引文逐字出現在已抓原文（逐字是否在原文以 verify.py 與 evidence-pack 的 verify 為準，不要打開 raw 對子字串；仍須用該 claim 單位只寫一次的 text 判斷 quote 是否支撐該句；**每個子句**都要有 quote 支撐，缺的刪子句或刪句，不要自己補新引文以外的內容）。
3. 來源等級 A／B 合理（gradeBasis 說得通）；無具名作者的百科條目、無作者館藏圖說、私人彙編 → 降為未評等，只能在 gaps 候選。
4. 無編造：日期、精度、半開區間、Q3 終點寫法、段落 period 迄點正確；datePrecision 只在 quote 含日期時填；conflict 只用於兩份已抓來源矛盾。
5. **對齊格式**：`alignedTo`="b0b0e0f"；positions 用 positionKind（無 roleKind、無三種角色值、無 party）；元首／首腦／實際掌權者與**所有黨職**在 roleCandidates，`role_kind` 正確（黨職一律 de_facto_leader、t14Rule=R1，reason 註明 Tai 12:12；即使與 ARCHITECTURE §16.3.1 衝突也以此為準）；**職稱或來源明寫以某政黨身分取得的席位**也必須在 roleCandidates（de_facto_leader、originalPositionKind 照原性質，比照 Tai 12:47 薩拉查裁決），逐一檢查 legislator 類 positions 的標題與引文有沒有漏掉；不明確黨職留 positions 並有 partyPostAmbiguous＋理由（審查可把明確黨職改移候選、或把誤移的非黨職移回並標 ambiguous，但不可新增事實）。
5b. **T14 R0–R6 逐條檢查**（每筆閣員／將領／佔領殖民長官／軍職都要過一次）：①判斷順序 R0→R6、第一條命中就停；②R0–R4 只能在 roleCandidates（role_kind 對應正確），positions 內不得出現門檻可證明的 R0–R4 任期（兩層互斥）；③門檻逐項核：四部、正職（無副／助理／次）、可證明天數（照精度算）、時間窗 1908–1945、來源 1A 或 2 獨立 B、regimeId／政權、戰役連結、職位等級引文明寫；④R6 留 positions 且有 `roleEligible: true`、`roleEligibleKind`、`roleGap`（缺什麼寫什麼）；R5 不得有 roleEligible；⑤每筆 t14Overlap 有 t14Rule＋t14Reason；⑥邊界個案：軍校→positionKind=military_education、警察→police（原值放 originalPositionKind 若是由研究者改的）；⑦判斷不了的要有 t14Ambiguous＋理由，不可硬判；⑧positionKind 不得為任何角色層值。審查可在兩層間搬移、改 t14Rule，但不可新增事實或引文以外的日期。
6. **薄人物／0 段人物**：檢查 searchLog 是否達最低嘗試（≥4 種來源類型、≥8 次查詢含原文語言 ≥2、≥3 個實抓頁），每筆有 url（或 null）與結果；未達標 → 該人 verdict=returned，returnedReasons 寫「最低嘗試未達：缺 X」並列出建議的下一個具體來源。searchLog 裡有 A／B 來源卻寫 0 段 → returned。
6b. **主要領導人加強規格（只對 flags 含 major★ 者，見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md` 的「主要領導人加強規格」）**：逐人檢查 searchLog 是否達 ≥5 種來源類型、≥15 次查詢（原文 ≥4）、≥6 個實抓頁、≥3 個 A／B 來源（≥1 個 A），並檢查指定來源是否有查（查過被擋也算）；未達 → verdict=returned 並寫缺什麼。逐筆檢查 positions／roleCandidates 是否都有起迄日與含日期的引文；缺迄日者須有「待查證：缺迄日」gap，缺起日者不得留在 positions／roleCandidates。
6c. **最低標準（Tai 2026-11-11 22:02，本批每人適用；見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md` 的「最低標準」）**：逐人核對中文段數 ≥3、合計 ≥300 字、每筆 positions／roleCandidates 有起迄日與含日期引文（缺迄日者須有「待查證：缺迄日」gap）。未達者必須有「篇幅不足：」gap 且 searchLog 顯示確實做過加強搜尋（`round: retry`），否則 verdict=returned。**為湊字數而寫的無出處句、重複句、空泛評語一律刪除並記入 changes**。flags 含 major★ 者另依 6b 檢查。
7. 符合 Q1–Q10。
8. 修改後跑 `python3 -I data/seed/leaders/b3-trial/verify.py data/seed/leaders/b3-trial/full/v3/batch074/research.json --report data/seed/leaders/b3-trial/full/v3/batch074/verify-report.json`，必須 ok（rawChecked=true、對齊檢查 11–18 通過）。不可改 verify.py、不可放寬規則。

## 限制
- 不用 Wikipedia／Wikidata／百度；不用 `curl -k`／`--insecure`；不登入；不繞過防機器人驗證。
- 絕不寫庫、不連任何資料庫；不 git add／commit／push；不改 ARCHITECTURE.md、程式、API、前端、b3-sample、b3-trial 既有批次；不重啟任何服務；只寫 `data/seed/leaders/b3-trial/full/v3/batch074/` 與 /tmp。

## 產出 `data/seed/leaders/b3-trial/full/v3/batch074/review.json`
{
  "batch": "074", "reviewedOn": "2026-11-15", "reviewer": "opus", "researcher": "sonnet", "promptVersion": "full-v3",
  "counts": {"returned": n, "toUnverified": n, "deletedParagraphs": n, "deletedPositions": n, "deletedRoleCandidates": n, "movedToRoleCandidates": n, "movedToPositions": n, "deletedCitations": n, "addedCitations": n, "editedSentences": n, "spotRefetched": n, "searchLogShort": <最低嘗試未達人數>},
  "people": [{"key": "...", "bioId": "...", "verdict": "pass|pass_with_changes|returned", "paragraphs": n, "positions": n, "roleCandidates": n, "gaps": n, "searchLogSteps": n, "changes": ["…"], "returnedReasons": ["…"]}],
  "issues": ["跨人共通問題…"],
  "verify": {"ok": true/false, "rawChecked": true/false, "quoteMax": n}
}
- 結尾回覆摘要，最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`（verify 不 ok、或 research.json 整體不可用才寫 fail）。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。

上述檔首的 2026-11-17 token 節流優先於本文其餘句子，包含文末「優先於上文」的舊追加。
