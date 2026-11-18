# generals.dk 引用替換：{{BATCHES}}（Sonnet，新 session）

授權：Tai 2026-11-13 10:32（World Line 主管轉達）：generals.dk 是個人網站（主管 2026-11-12 22:08 禁用），**先替換**它的引用。只換來源；不寫庫、不 push、不改 schema、不 git add／commit、不切分支。

## 要處理的引用（由程式列出；「僅靠」＝該職位只有這一筆 citation）
{{INVENTORY}}

## 做法
1. 讀各批 research.json（唯讀）：`data/seed/leaders/generals-roster/bios/<TIER>/batch<NN>/research.json`，看該人的 paragraphs／positions、既有 sources 與 rawmap（同目錄 rawmap.json，值為原文 .txt 路徑；相對路徑以 research.json 的 rawDir 為底）。
2. **優先**：標「僅靠」的職位——必須找 A／B／具名 C 來源，quote 要載明該職務（及能找到的起訖日）。
3. 其他 generals.dk citation：若同一段落／職位的其他 citation 已支撐同一事實（職稱、日期），不用處理（程式會自動移除 generals.dk citation）；若那個事實只有 generals.dk 撐（例如某段的任職日期），就找替代來源加 citation；找不到則用 `set.body` 刪改段落中失去來源的句子（diff 寫明刪了什麼）。
4. 來源：A／B／具名 C（官方紀錄、公報、國家傳記辭典、官方戰史、學術書、具名百科／博物館／大學）；每筆 citation 必寫 `grade` 且與 source 一致；C 須有 authors 或 publisher。**禁用**：generals.dk 及所有個人網站、Wikipedia／Wikidata（只可當候選值線索，不寫入檔案）、百度、維基類、論壇、部落格、AI 站、無署名內容。不用 `curl -k`／`--insecure`，不登入，不繞過防機器人頁。
   參考：美軍 history.army.mil、army.mil、Arlington／West Point 官方頁、Eisenhower Library、Library of Congress；德國 LeMO（DHM）、Deutsche Biographie（NDB）、Bundesarchiv；芬蘭 Kansallisbiografia（BLF）、Sotamuseo、Puolustusvoimat；荷蘭 Huygens／Parlement.com、NIMH；英國 IWM、NAM、Liddell Hart Centre（KCL）；俄國 encyclopedia.mil.ru；義大利 Treccani DBI。既有 sources 的 .txt 若已含所需句子，可直接用既有 sourceKey 引用，不必重抓。
5. 新抓原文存 `~/wl-source-cache/gendk-<TIER>-b<NN>/`（不是 /tmp）：`curl -sSL --max-time 60 -A 'Mozilla/5.0' -o <dir>/<key>.html '<url>'`，再 `python3 ~/wl-source-cache/totxt.py <dir>/<key>.html <dir>/<key>.txt`。新 source key 一律 `rg-` 前綴。
6. quote 逐字取自 .txt、NFC 後 ≤80 字元。**不可編造**；查不到就不要加（程式會把失去全部來源的職位移到 gap，標「待查證」）。每個「僅靠」職位放棄前至少試 4 個不同來源／查詢。
7. 新來源與既有職稱或任期不同 → **以新來源為準**：在該 item 寫 `set`（title／organization／period／startPrecision／endPrecision），`basis` 填新 sourceKey，`diff` 寫「原：…；新來源：…」。Q3：月／年精度的迄日寫下一單位起日（到 1941 年 → "1942-01-01"＋year），起日寫該單位第一天。精度欄必須與 period 端點一致（端點 null ↔ 精度 null）。

## 產出（每批一檔）：`.dev/gendk/<TIER>-b<NN>/replace.json`
```json
{"sources": {"rg-xxx": {"title": "...", "authors": [], "publisher": "...", "published_text": null, "url": "...", "archive_url": null, "catalog_id": null, "license_code": null, "grade": "A|B|C", "gradeBasis": "..."}},
 "fetches": [{"sourceKey": "rg-xxx", "url": "...", "file": "/Users/jack755051/wl-source-cache/gendk-<TIER>-b<NN>/rg-xxx.txt", "html": ".../rg-xxx.html", "fetchedAt": "ISO"}],
 "people": {"<key>": {"items": [{"section": "positions|paragraphs", "key": "<職位 key>（段落改用 \"ord\": n）",
     "addCitations": [{"sourceKey": "rg-xxx", "locator": "...", "quote": "...", "quoteLang": "en", "evidenceNote": null, "accessedOn": "{{TODAY}}", "grade": "A|B|C", "datePrecision": "day|month|year|null", "claimSpan": null, "policyVersion": "bio-2026-11-v0"}],
     "set": {}, "basis": null, "diff": null}],
   "addSearchLog": [{"step": 1, "sourceType": "official|national_dictionary|academic|named_encyclopedia|other", "query": "...", "url": "...或null", "result": "found_A|found_B|found_C|no_result|blocked_403|not_relevant", "note": "generals.dk 替換"}]}}}
```

## 自檢（每批必做，直到 ok=true）
`python3 -I data/seed/leaders/generals-roster/bios/refill/patch_replace_gendk.py --check <TIER> <NN> .dev/gendk/<TIER>-b<NN>/replace.json`
`ok` 必須為 true；`summary.unverified` 列出會被移到「待查證」的職位。不可改程式、不可放寬規則；修不好的 citation 刪掉。

## 結尾
每批回覆：每個「僅靠」職位用了哪個來源（key、網域、grade）、職稱／任期差異、其他 generals.dk 引用是替換還是移除、仍待查證的職位；最後每批一行 `BATCH_RESULT <TIER>/<NN>=ok|fail`。
