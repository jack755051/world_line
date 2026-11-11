# 將領生平：來源不足補跑（S 級、新來源範圍，Sonnet，新 session，勿 --resume）

授權：World Line 主管 2026-11-12 03:03（Tai 轉達）。S 級已跑完後，對日本及其他非英語國家、先前判「來源不足」的人，用新納入的國家圖書館權威檔／官方戰史／具名百科各補跑一次。不寫庫、不 push、不 commit。分支 feature/person-cards（不要切換分支）。

`{{OUTDIR}}/research.json` 已存在。本批只改下列人物：
{{PEOPLE}}

## 規則
- 完整規則見 `data/seed/leaders/generals-roster/bios/PROMPT_research.md`（以本批 {{NN}}、{{TIER}}、{{RAWDIR}}、{{OUTDIR}} 代入）以及它所引用的 B3 v3／T14／verify 規則，全部照舊適用；先讀它、現有 research.json 與 searchLog，尤其是「日本及其他非英語國家將領：補充搜尋範圍」（主管 2026-11-12 03:03，§16 T1）。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `{{RAWDIR}}`。
- **本輪最低搜尋量（每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "insuff-rerun"`。
- **日本將領必查（可抓原文才可當出處）**：Web NDL Authorities（id.ndl.go.jp，A）、JACAR（jacar.go.jp、jacar.archives.go.jp，A）、防衛研究所（nids.mod.go.jp，A）、Kotobank 上『日本大百科全書』／『国史大辞典』／『世界大百科事典』的具名條目（kotobank.jp，B）。
- **其他非英語國家**：改查該國國家圖書館權威檔或官方戰史（A）與具名機構百科（B），見 PROMPT_research.md 同節；不要只查英語來源。維基只當索引。
- 最低標準不變：中文 ≥3 段、合計 ≥300 字；每個職位／角色都要有起迄日；須有指揮職與主要戰役。不可用無出處內容湊字數；每個事實子句都要有 citation。引文 NFC 正規化後不超過 80 字元。
- 補完後若已達標：可移除或改寫先前「來源不足：」gap（若該項已補上），並將 `sourceInsufficient` 設為 false（或刪除該欄）。
- 補完後仍未達標 → 更新 gap：target=`paragraph:length`、gapKind=not_found、note 以「來源不足：」開頭，寫目前段數／字數、缺的任期／戰役／指揮職，以及本輪已查的新網域與結果。**不要硬湊。** 缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py {{OUTDIR}}/research.json --report {{OUTDIR}}/verify-report.json`，須 exit 0。
- 結尾回覆：每人是否達標、新增段落／字數／任期、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。
