# 將領生平 batch{{NN}}（{{TIER}} 級）：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 23:11（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/person-cards（不要切換分支）。

`{{OUTDIR}}/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日、須有指揮職與主要戰役；見 `{{OUTDIR}}/min-check.round1.json`）：
{{PEOPLE}}

## 規則
- 完整規則見 `data/seed/leaders/generals-roster/bios/PROMPT_research.md`（以本批 {{NN}}、{{TIER}}、{{RAWDIR}}、{{OUTDIR}} 代入）以及它所引用的 B3 v3／T14／verify 規則，全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `{{RAWDIR}}`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。優先改查 A 級來源（國家級傳記辭典、政府／國防部／議會名錄、官方公報、人名權威檔；日本防衛研究所 nids.mod.go.jp、國史館、Deutsche Biographie、Treccani DBI、Oxford DNB 公開摘要、London Gazette 等）。可抓原文才可當出處（grade A／B）。維基只當索引，不是出處。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。引文 NFC 正規化後不超過 80 字元。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「來源不足：」開頭，寫目前段數／字數、缺的任期／戰役／指揮職，以及本輪已查來源類型。**不要硬湊。** 缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py {{OUTDIR}}/research.json --report {{OUTDIR}}/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。
