# 引文重摘（80 字）結果總表

依 ARCHITECTURE §16.7.4（Tai 2026-11-10 21:52）。只產 seed／dry-run 檔，未寫任何資料庫。

| 批次 | gap-830 批 | 筆數 | 直接採用 | 重摘 | 留空 |
|---|---|---|---|---|---|
| r01 | b01–b05 | 465 | 333 | 129 | 3 |
| r02 | b06–b10 | 466 | 298 | 158 | 10 |
| r03 | b11–b15 | 454 | 371 | 82 | 1 |
| r04 | b16–b20 | 385 | 287 | 87 | 11 |
| r05 | b21–b25 | 370 | 175 | 188 | 7 |
| r06 | b26–b30 | 403 | 270 | 128 | 5 |
| r07 | b31–b35 | 289 | 155 | 127 | 7 |
| r08 | b36–b40 | 169 | 146 | 21 | 2 |
| r09 | b41–b45 | 157 | 144 | 13 | 0 |
| r10 | b46–b49 | 107 | 87 | 13 | 7 |
| **合計** | | **3265** | **2266** | **946** | **53** |

- 檔案：`results/rNN.json`（每筆 id＝`leader_bio_field_citations.id`、field、method／methodZh、quote 或 blankReason）；`decisions/rNN.json`（重摘／留空的逐筆判斷與理由）；`worklist.json`（3265 筆來源）。
- 留空清單：`blanks.md`／`blanks.json`。抽查：`spotcheck.md`／`spotcheck.json`。
- 驗證（`requote.py build`）：quote NFC ≤ 80 字、逐字出現在 evidence、起訖不切字、非取前 80 字截斷、重摘附 basis、留空附原因；全量 3265 筆通過。
- 重摘全部取自已存 evidence（逐字抄自該筆原出處）；未換來源、未上網重查。
