# 將領生平：來源不足／未達標補跑（新規則，Sonnet，新 session，勿 --resume）

授權：World Line 主管 2026-11-12 03:03（日本／非英語來源）、06:32（英語國家也補跑；NARA／英國國家檔案館／官方戰史＝A，ODNB／ANB 公開內容＝B）；Tai 本人 2026-11-12 06:34（主管轉達）「將領生平來源放寬到具名 C 級」。每人只補跑這一次。不寫庫、不 push、不 commit。分支 feature/person-cards（不要切換分支）。

`{{OUTDIR}}/research.json` 已存在。本批只改下列人物（{{TIER}} 級 batch{{NN}}）：
{{PEOPLE}}

若某人在 research.json 裡**沒有條目**（名單上標「目前 None 段」者；例：S/batch004 的 heinzguderian，該批主 session 漏寫，只留下 sources），請依 PROMPT_research.md 為他**新增完整條目**（key 用名單上的 key），可沿用頂層 sources 裡已有的他的來源。

## 規則
- 完整規則見 `data/seed/leaders/generals-roster/bios/PROMPT_research.md`（以本批 {{NN}}、{{TIER}}、{{RAWDIR}}、{{OUTDIR}} 代入）以及它所引用的 B3 v3／T14／verify 規則，全部照舊適用；先讀它、現有 research.json 與 searchLog，尤其是「日本及其他非英語國家將領：補充搜尋範圍」與「英語國家官方來源與具名 C 級」兩節（後者優先於舊的「只收 A／B」文字）。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `{{RAWDIR}}`。頂層加（或保留）`"gradePolicy": "ABC-2026-11-12"`。
- **本輪最低搜尋量（每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "insuff-rerun"`。
- **日本將領必查**：Web NDL Authorities（id.ndl.go.jp，A）、JACAR（jacar.go.jp、jacar.archives.go.jp，A）、防衛研究所（nids.mod.go.jp，A）、Kotobank『日本大百科全書』／『国史大辞典』／『世界大百科事典』具名條目（kotobank.jp，B）。
- **英語國家將領必查**：NARA（www.archives.gov、catalog.archives.gov，A）、英國國家檔案館（www.nationalarchives.gov.uk、discovery.nationalarchives.gov.uk，A）、各軍種官方戰史（history.army.mil、www.history.navy.mil、www.afhra.af.mil、www.usmcu.edu、www.raf.mod.uk，A）、London Gazette（A）；ODNB（oxforddnb.com）／ANB（anb.org）只用未登入可見的摘要或首段（B），不登入、不繞付費牆。
- **其他非英語國家**：該國國家圖書館權威檔或官方戰史（A）與具名機構百科（B），見 PROMPT_research.md；不要只查英語來源。
- **具名 C 級**：有具名作者或具名出版機構的報紙、大學、博物館、軍事史網站等（每頁判斷，gradeBasis 寫出具名者）。**可只靠 C 達標；不可因缺 A／B 就標來源不足。** 維基（含任何維基類）、Wikidata、百度、無署名、AI 生成、論壇、部落格、個人網站一律不收；維基只當索引。每筆 citation 都寫 grade（A／B／C），與 sources 一致。
- 最低標準不變：中文 ≥3 段、合計 ≥300 字；每個職位／角色都要有起迄日（缺迄日也算未達標，要盡量補齊）；須有指揮職與主要戰役。不可用無出處內容湊字數；每個事實子句都要有 citation。引文 NFC 正規化後不超過 80 字元，逐字出現在已抓原文。
- 補完後若已達標：移除或改寫先前「來源不足：」「篇幅不足：」gap（已補上的項目），並將 `sourceInsufficient` 設為 false（或刪除該欄）。
- 補完後仍未達標 → 更新 gap：target=`paragraph:length`、gapKind=not_found、note 以「來源不足：」開頭，寫目前段數／字數、缺的任期／戰役／指揮職，以及本輪已查的新網域（A／B／C）與結果。**不要硬湊。** 缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 不用 `curl -k`／`--insecure`；不登入；遇防機器人驗證不繞過。
- **預算**：本 session 上限 USD 6（到上限 session 會被中止、整批作廢）。本批最多 5 人，每人控制在約 USD 1 以內：先查最可能補上缺口的來源（缺迄日先查官方任免／公報，缺戰役先查官方戰史），補到達標就停，不要逐頁瀏覽。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py {{OUTDIR}}/research.json --report {{OUTDIR}}/verify-report.json`，須 exit 0。
- 結尾回覆：每人是否達標、新增段落／字數／任期、新增 searchLog 筆數、用到的新網域與等級（A／B／C）；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。
