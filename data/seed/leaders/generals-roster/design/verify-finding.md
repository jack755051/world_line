# verify.py 引文核對現況（2026-11-12 09:2x，World Line 史料考證 讀碼結果）

檔案：`data/seed/leaders/b3-trial/verify.py`（294 行；將領 S/A 主迴圈 `.dev/cc-generals-bios-loop.sh` 第 27 行 `VERIFY=` 用的就是這支；verify 非 0 時主迴圈停、不 commit，第 493 行）。

## 有做到的
1. `main()` 第 84–96 行：若 research.json 頂層有 `rawDir`＋`rawMap`（或給 `--raw RAW_DIR RAWMAP`），逐一讀 rawMap 指到的純文字檔，`norm()`（NFC＋空白折疊，第 65–66 行）後存進 `texts[sourceKey]`，並記 `sha256`（報告 `rawFiles`）。檔案不存在 → 錯誤。
2. 內部函式 `chk_quote()`（第 125–138 行）：引文非空、NFC ≤80 字；有原文時，`norm(quote)` 必須是 `texts[sourceKey]` 的子字串，否則錯「引文未逐字出現」；來源沒有原文檔 → 錯「無法核對引文」。
3. `chk_quote` 被套用在：段落 citations、職位 positions citations（第 165–180 行同一迴圈）、roleCandidates citations（第 256 行）、gaps 的 candidateCitations（第 281 行）。
4. 報告 `rawChecked`：S batch001–021、A batch001–015 共 36 份 verify-report.json 全部 `ok=true`、`rawChecked=true`。
5. 另檢：Wikipedia／Wikidata 網址出現即錯（第 118–121 行）；C 級須具名作者或出版機構、論壇／部落格／維基類網域不收（第 107–117 行）；grade 與來源一致。

## 沒做到／缺口
1. 原文快取在 `/tmp/generals-bios/{S,A}/batchNNN/raw/`（.html＋.txt，現約 340 MB），不進版控，只在報告留 sha256；macOS 重開機可能清 /tmp，之後就無法重驗。失敗批次才會被主迴圈 `park_ratelimit()` 移到 .dev 的 partial 目錄；部分已封存於 `.dev/archive/insuff-interrupted-20261112/S-batch004-raw`。
2. 原文 .txt 由同一個 Claude 工作階段自己 `curl` 並用自己的 python 轉文字（PROMPT_research.md「抓取與原文」第 175–178 行）；verify.py 不檢查 .txt 是否真由 .html 轉出、.html 是否真由該 URL 抓得（沒有抓取紀錄：URL、時間、HTTP 狀態、Content-Type、原始位元組 hash）。即「子字串」核對的是工作階段自己存的檔，來源真實性靠流程而非程式保證。
3. `locator` 欄位不驗（只當自由文字），不檢查引文在頁內的位置。
4. 只比對引文，不比對結構化值（日期、職稱）是否出現在原文或與引文一致。
5. 職位引文目前也強制逐字（L2 改版後可放寬為 URL＋定位）。
6. 同一網域在不同批被評不同等級（例：encyclopedia.com B／C、treccani.it A／B、avalon.law.yale.edu B／C，見 stats.md），verify.py 只檢查 citation grade 與該檔 sources grade 一致，不檢查跨檔一致或對照網域政策表。
