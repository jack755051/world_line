# B3 run100 batch{{NN}}：審查（Opus，新 session，勿 --resume）

<!-- 佔位同 PROMPT_research.md：{{NN}}、{{PEOPLE}}、{{TODAY}}、{{RAWDIR}}、{{OUTDIR}} -->

授權：Tai 2026-11-11 09:30（Sonnet 查資料、Opus 審查；不寫庫、不 push）、12:12（①②④）。你是審查者：逐條核對 Sonnet 產出的 `{{OUTDIR}}/research.json`，不合格就改成待查證（移到 gaps）或刪段，不要替它補寫新內容（只可在原文已抓、且你親自核對過的範圍內修正字句、日期、精度、欄位歸類）。分支 feature/person-cards（不要切換分支）。

## 本批 5 人
{{PEOPLE}}

## 必讀
1. `ARCHITECTURE.md` §16.2、§16.3、§16.3.1、§16.3.2、§16.4 與 T11／T12／T14（只讀這幾節）。**與 `data/seed/leaders/b3-trial/ARCH_TODO.md` 所列新規則衝突處，以新規則為準**；另讀 `data/seed/leaders/b3-trial/T14_RECOMMENDATION.md` §1、§4。
2. `data/seed/leaders/b3-trial/run100/PROMPT_research.md`（研究者收到的完整規則，**所有規則同樣適用於審查**）、`data/seed/leaders/b3-trial/ALIGN.md`、`data/seed/leaders/b3-trial/verify.py`。
3. `{{OUTDIR}}/research.json`、`{{OUTDIR}}/rawmap.json`、原文 `{{RAWDIR}}/*.txt`。

## 審查項目（每段、每職位、每筆候選角色、每筆 citation）
1. 出處：sourceKey 存在、URL 真實可開（每人至少抽 1 個來源重抓比對）、不是 Wikipedia／Wikidata／百度、不是用防機器人繞過取得。
2. 引文逐字出現在已抓原文（不能只信 verify.py：再人工比對引文與它支撐的句子；**每個子句**都要有 quote 支撐，缺的刪子句或刪句，不要自己補新引文以外的內容）。
3. 來源等級 A／B 合理（gradeBasis 說得通）；無具名作者的百科條目、無作者館藏圖說、私人彙編 → 降為未評等，只能在 gaps 候選。
4. 無編造：日期、精度、半開區間、Q3 終點寫法、段落 period 迄點正確；datePrecision 只在 quote 含日期時填；conflict 只用於兩份已抓來源矛盾。
5. **對齊格式**：`alignedTo`="b0b0e0f"；positions 用 positionKind（無 roleKind、無三種角色值、無 party）；元首／首腦／實際掌權者與**所有黨職**在 roleCandidates，`role_kind` 正確（黨職一律 de_facto_leader、t14Rule=R1，reason 註明 Tai 12:12；即使與 ARCHITECTURE §16.3.1 衝突也以此為準）；**職稱或來源明寫以某政黨身分取得的席位**也必須在 roleCandidates（de_facto_leader、originalPositionKind 照原性質，比照 Tai 12:47 薩拉查裁決），逐一檢查 legislator 類 positions 的標題與引文有沒有漏掉；不明確黨職留 positions 並有 partyPostAmbiguous＋理由（審查可把明確黨職改移候選、或把誤移的非黨職移回並標 ambiguous，但不可新增事實）。
5b. **T14 R0–R6 逐條檢查**（每筆閣員／將領／佔領殖民長官／軍職都要過一次）：①判斷順序 R0→R6、第一條命中就停；②R0–R4 只能在 roleCandidates（role_kind 對應正確），positions 內不得出現門檻可證明的 R0–R4 任期（兩層互斥）；③門檻逐項核：四部、正職（無副／助理／次）、可證明天數（照精度算）、時間窗 1908–1945、來源 1A 或 2 獨立 B、regimeId／政權、戰役連結、職位等級引文明寫；④R6 留 positions 且有 `roleEligible: true`、`roleEligibleKind`、`roleGap`（缺什麼寫什麼）；R5 不得有 roleEligible；⑤每筆 t14Overlap 有 t14Rule＋t14Reason；⑥邊界個案：軍校→positionKind=military_education、警察→police（原值放 originalPositionKind 若是由研究者改的）；⑦判斷不了的要有 t14Ambiguous＋理由，不可硬判；⑧positionKind 不得為任何角色層值。審查可在兩層間搬移、改 t14Rule，但不可新增事實或引文以外的日期。
6. **薄人物／0 段人物**：檢查 searchLog 是否達最低嘗試（≥4 種來源類型、≥8 次查詢含原文語言 ≥2、≥3 個實抓頁），每筆有 url（或 null）與結果；未達標 → 該人 verdict=returned，returnedReasons 寫「最低嘗試未達：缺 X」並列出建議的下一個具體來源。searchLog 裡有 A／B 來源卻寫 0 段 → returned。
7. 符合 Q1–Q10。
8. 修改後跑 `python3 -I data/seed/leaders/b3-trial/verify.py {{OUTDIR}}/research.json --report {{OUTDIR}}/verify-report.json`，必須 ok（rawChecked=true、對齊檢查 11–18 通過）。不可改 verify.py、不可放寬規則。

## 限制
- 不用 Wikipedia／Wikidata／百度；不用 `curl -k`／`--insecure`；不登入；不繞過防機器人驗證。
- 絕不寫庫、不連任何資料庫；不 git add／commit／push；不改 ARCHITECTURE.md、程式、API、前端、b3-sample、b3-trial 既有批次；不重啟任何服務；只寫 `{{OUTDIR}}/` 與 /tmp。

## 產出 `{{OUTDIR}}/review.json`
{
  "batch": "{{NN}}", "reviewedOn": "{{TODAY}}", "reviewer": "opus", "researcher": "sonnet", "promptVersion": "run100-v1",
  "counts": {"returned": n, "toUnverified": n, "deletedParagraphs": n, "deletedPositions": n, "deletedRoleCandidates": n, "movedToRoleCandidates": n, "movedToPositions": n, "deletedCitations": n, "addedCitations": n, "editedSentences": n, "spotRefetched": n, "searchLogShort": <最低嘗試未達人數>},
  "people": [{"key": "...", "bioId": "...", "verdict": "pass|pass_with_changes|returned", "paragraphs": n, "positions": n, "roleCandidates": n, "gaps": n, "searchLogSteps": n, "changes": ["…"], "returnedReasons": ["…"]}],
  "issues": ["跨人共通問題…"],
  "verify": {"ok": true/false, "rawChecked": true/false, "quoteMax": n}
}
- 結尾回覆摘要，最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`（verify 不 ok、或 research.json 整體不可用才寫 fail）。不要 commit。
