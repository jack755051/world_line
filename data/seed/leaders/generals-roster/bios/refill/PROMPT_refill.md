# 將領生平「只補缺欄位」：{{TIER}}/batch{{NN}}（Sonnet，新 session）

授權：Tai 2026-11-12 21:43（World Line 主管轉達）：對未達最低標準的人**只補缺的欄位**（ARCHITECTURE §20：L1／L2 事實＋L3 敘述）。不寫庫、不 push、不改 schema、不 git add／commit。分支 feature/person-cards（不要切換）。

## 本批要補的人與缺欄（由程式依 check_min 算出）
{{PEOPLE}}

## 檔案
- 既有研究檔（**唯讀，不可修改**）：`{{RESEARCH}}`。先讀這幾個人的 paragraphs／positions／roleCandidates／gaps／searchLog，了解已查過什麼、已有哪些來源（頂層 sources）。
- 既有原文快取（唯讀，可重用）：`{{OLDRAW}}`（rawmap：`{{RAWMAP}}`）。既有 sourceKey 的 .txt 若已含你要的句子，可直接引用既有 sourceKey，不必重抓。
- 新抓原文一律存 `{{CACHE}}/`（**不是 /tmp**）：`curl -sSL --max-time 60 -A 'Mozilla/5.0' -o {{CACHE}}/<sourceKey>.html '<url>'`，再用 python3 轉成純文字 `{{CACHE}}/<sourceKey>.txt`（去 script/style、unescape entity；PDF／JSON 也轉文字）。
- 你的唯一產出：`{{OUT}}`（refill.json，格式見下）。不要改任何其他檔。

## 必守規則（全文見 `data/seed/leaders/generals-roster/bios/PROMPT_research.md`，先用 Grep 讀其中「## 規則」「英語國家官方來源與具名 C 級」「日本及其他非英語國家將領」「## 搜尋策略」「## 抓取與原文」與 T14 R0–R6 段落）
- 只補缺：**不重寫、不改、不刪既有段落／職位／來源**；只新增，或替既有職位補上空著的起／迄日。
- 出處只能 A、B 或具名 C；每筆 citation 必寫 `grade`，且與 `sources[sourceKey].grade` 一致；C 級 source 的 authors 或 publisher 至少一項非空，gradeBasis 寫出具名作者／機構。Wikipedia／Wikidata／百度／維基類／論壇／部落格／AI 站／無署名內容一律不收（Wikidata 只可當候選值線索，不寫進檔案）。不用 `curl -k`／`--insecure`，不登入，不繞過防機器人頁（403／挑戰頁照實寫 searchLog）。
- quote：逐字取自 .txt、NFC 後 ≤80 字元、完整語意片段；每個事實子句都要對得到該段／該職位的某筆 citation quote。不可編造；查不到寫 gap（note 以「待查證：」開頭）＋searchLog。
- 新 source key 一律用 `rf-` 前綴（例 `rf-ndl-yamaguchi`），不可與既有 key 相同。
- 任期：補迄日時 quote 必須含該日期（或年／月）；Q3 月／年精度終點寫下一單位起日（例：到 1941 年 → "1942-01-01"＋endPrecision "year"）；Q7 推論須寫 evidenceNote「依名簿下一任起日推得（推論）」。
- 戰役：只寫進段落正文（Q1）。缺戰役者新增一段（≤400 中文字＋英文對應）寫來源明載的主要戰役／作戰與其角色，heading 與 body 至少一處含「戰役／會戰／海戰／空戰／作戰／登陸／圍攻」等字或 battle／campaign／offensive。
- 指揮職：缺指揮職者，若來源明載指揮職，新增 position（`positionKind: "military_command"`，依 T14 規則加 t14Overlap／t14Rule／t14Reason），附起迄日與 citation；查不到就寫 gap（新規不要求指揮職，不硬湊）。
- 篇幅（L3）：段落不足 3 段或中文不足 300 字者，新增段落補到 ≥3 段且 ≥300 字（中文去空白計），只寫來源寫到的事。標「全面重跑」者（0 段）照 PROMPT_research.md 的研究流程完整研究，但產出仍寫成下方 refill.json 的新增項目。
- 範圍：每個缺欄先查既有來源與快取，再查 2–6 次新來源（權威檔、國家級辭典、官方戰史、具名機構百科、具名 C）；找到即停。全批控制在預算內。

## refill.json 格式
```json
{
 "tier": "{{TIER}}", "batch": "{{NN}}",
 "sources": {"rf-xxx": {"title": "...", "authors": [], "publisher": "...", "published_text": null, "url": "...", "archive_url": null, "catalog_id": null, "license_code": null, "grade": "A|B|C", "gradeBasis": "..."}},
 "fetches": [{"sourceKey": "rf-xxx", "url": "實際抓取網址", "file": "{{CACHE}}/rf-xxx.txt", "html": "{{CACHE}}/rf-xxx.html", "fetchedAt": "ISO 時間"}],
 "people": {
  "<person key>": {
   "fillPeriods": [{"section": "positions|roleCandidates", "key": "<既有職位 key>", "start": null, "end": "YYYY-MM-DD", "endPrecision": "day|month|year", "citations": [<citation>]}],
   "addPositions": [<完整 position 物件，格式同既有 positions>],
   "addRoleCandidates": [<完整 roleCandidate 物件>],
   "addParagraphs": [{"period": {"start": null, "end": null}, "periodStartPrecision": null, "periodEndPrecision": null, "heading": {"zh-Hant": "...", "en": "..."}, "body": {"zh-Hant": "...", "en": "..."}, "relatedRecordIds": [], "citations": [<citation>]}],
   "addGaps": [{"target": "...", "gapKind": "not_found", "note": "待查證：...", "candidateCitations": [], "checkedOn": "{{TODAY}}"}],
   "addSearchLog": [{"step": 1, "sourceType": "authority|national_dictionary|official|named_encyclopedia|treaty_law|academic|other", "query": "...", "url": "...或null", "result": "found_A|found_B|found_C|unrated|not_relevant|blocked_403|challenge_page|no_result", "note": "..."}],
   "personFields": {"name": "原文名", "thickness": "厚|中|薄"}
  }
 }
}
```
- citation 欄位：sourceKey、locator、quote、quoteLang、evidenceNote、accessedOn（{{TODAY}}）、grade、datePrecision、claimSpan、policyVersion（"bio-2026-11-v0"）。
- personFields 只用於本批 research.json 裡還沒有的人（新建）。
- 段落 ord 由程式依序編號，不要填。

## 自檢（必做，直到 ok=true）
`python3 -I data/seed/leaders/generals-roster/bios/refill/apply_refill.py --check {{TIER}} {{NN}} {{OUT}}`
輸出 JSON 的 `ok` 必須為 true（含 verify.py 引文逐字比對）；`after` 顯示每人補完後的 check_min。修不好的項目改成 gap 或刪掉，不可改程式、不可放寬規則。

## 結尾
回覆每人：補到哪些欄位、仍待查證的欄位、用到的來源網域；最後單獨一行 `BATCH_RESULT=ok`（自檢 ok）或 `BATCH_RESULT=fail`。
