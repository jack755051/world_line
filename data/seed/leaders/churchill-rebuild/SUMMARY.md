# 邱吉爾補建（待寫資料＋送出腳本，尚未寫庫；2026-11-11）

> 授權：Tai 2026-11-11 09:30（Asia/Taipei）決定照 gap-830 流程補建邱吉爾的有效人物資料與 1940–45 首相任期，只產出待寫資料；**寫庫前由 World Line 主管回報 Tai**（§16.3.2 第 5 點 Q8）。
> 依據：ARCHITECTURE.md §16（16.3.2 B3 寫法、16.4.1 citation 欄位、16.9.1 T1 等級）、`gap-830/{WORKFLOW,SCHEMA}.md`、`b3-sample/`。
> 寫入授權：Tai 2026-11-11 10:13（Asia/Taipei，經 World Line 主管轉達）「邱吉爾 6 項全照史料考證建議；同意修 2 處瑕疵、寫送出腳本、檢查、試跑、備份後寫入本機開發庫 5052，不 push」。第一階段（本次）只修瑕疵、寫 `send.py`／`counts.sql` 並乾跑；試跑與寫入是下一階段。
> 範圍：只在本目錄新增檔案。沒有寫庫（5442 只用 `default_transaction_read_only=on` 做 SELECT），沒改程式、API、前端、ARCHITECTURE.md，沒重啟服務。

## 檔案

| 檔案 | 內容 |
|---|---|
| `build.py` | builder：讀 `/tmp/churchill-raw/` 的原始頁面文字，檢查引文後產生下面三個檔（種子不手改） |
| `research.json` | gap-830 P 格式；來源用頂層 `sources`＋`sourceKey`（B3 規則）；`bioId: null`、`recordIds: []`，新任期放 `newRecords` |
| `pending-write.json` | 待寫內容：步驟 1–3（5052 API 請求本體）、步驟 4（SQL 補 quote／grade 與 `leader_record_citations`）、不得動的 4 筆撤回列 |
| `verify-report.json` | 檢查結果（**ok，0 錯誤；13 筆引文，最長 62 字元；name 引文與 Hansard `<h1>` 逐字相符**）與原始頁面 sha256；原始頁面不進版控 |
| `WRITE_PLAN.md` | 寫哪些表、幾筆、dry-run、回滾 |
| `send.py` | 送出腳本（預設乾跑、`--send` 才寫；步驟 1–4；帳本 `sent.<port>.json`） |
| `counts.sql` | 寫入後 5 條計數＋撤回列不變核對（全 SELECT） |

## 5442 唯讀查證結果

- 正確政權：`united-kingdom`（`01a18e71-cba5-7726-90e3-9b90ab344afd`，大不列顛及北愛爾蘭聯合王國，主權紀錄自 1922-12-05）。張伯倫、艾德禮的有效任期都掛在這裡。
- 1940–45 英國首相：**沒有有效紀錄**（只有已撤回 `01a19efa-769a-…`）。張伯倫止於 1940-05-10、艾德禮始於 1945-07-26，新任期剛好接上。
- 邱吉爾有效 bio：**無**（3 筆已撤回測試 bio）。這 3 筆與 1 筆撤回任期都不動。

## 待寫資料

**人物（leader_bios 1 筆）**

| 欄位 | 值 | 出處（locator） | 等級 |
|---|---|---|---|
| name | Winston Churchill | Hansard（Page heading；引文「Mr Winston Churchill」＝頁面 `<h1>`） | A |
| nameZh | 溫斯頓·邱吉爾 | 無（沿用撤回任期與 b3-sample 的中文名，前端顯示待補來源） | — |
| birthDate | 1874-11-30（day） | GOV.UK（Fact box: Born） | A |
| deathDate | 1965-01-24（day） | GOV.UK（Died）、Hansard（life dates）、Nobel（closing line） | A、A、B |
| birthPlace | 牛津郡布倫亨宮／Blenheim Palace, Oxfordshire | GOV.UK（Born） | A |
| party | 保守黨／Conservative Party | GOV.UK（page subtitle、Fact box: Political party） | A |
| summary | 英國保守黨政治人物，1940年至1945年及1951年至1955年兩度出任首相；1965年逝世並獲國葬。 | GOV.UK（subtitle、Dates in office、Biography 末段） | A |

- 黨派：邱吉爾曾轉黨（GOV.UK 同頁：1904 轉自由黨、戰間期回保守黨）。GOV.UK 副標題寫「Conservative 1940 to 1945, 1951 to 1955」，把保守黨限定在首相任內，所以給值；兩筆 party citation 的 evidenceNote 都註明「只代表首相任內黨籍」（Tai 2026-11-11 10:13 已決 ③）。
- 出生地譯名「布倫亨宮」：2026-11-11 在 repo 內（排除 node_modules、.git、建置輸出）grep「布倫亨宮」「布倫海姆宮」「布萊尼姆」「布倫翰」「布倫漢」「Blenheim」等，既有資料與前端都沒有用到任何譯名，只出現在本目錄與 `b3-sample/research.json`（「布倫亨宮」），故保留「布倫亨宮」。
- 存取日期：全部 2026-11-11。

**任期（leader_records 1 筆）**

| regime | role | title | valid_period（半開） | verified | 出處 |
|---|---|---|---|---|---|
| united-kingdom | head_of_government | Prime Minister | `[1940-05-10,1945-07-26)` | true | Hansard「May 10, 1940 - July 25, 1945」（A，day）；GOV.UK「1940 to 1945, 1951 to 1955」（A，year） |

- 原始卸任日 1945-07-26：Hansard 寫閉區間（最後在任日 7 月 25 日），換成半開終點即 1945-07-26，與艾德禮任期起日一致。
- 地圖規則：範圍內迄日最晚到 1945-10-01（不含）；1945-07-26 早於此，**不需截斷**，範圍內迄日＝原始卸任日。
- 1951–55 任期屬範圍外，依 Q4 只寫正文，不建紀錄。

**引用**：leader_bio_field_citations 11、leader_record_citations 2（都附 locator、≤80 字逐字 quote、grade、date_precision、policy_version `bio-2026-11-v0`）。

## 來源與等級

| sourceKey | 來源 | URL | 等級 | 理由 |
|---|---|---|---|---|
| govuk-churchill | GOV.UK, History of Sir Winston Churchill | https://www.gov.uk/government/history/past-prime-ministers/winston-churchill | A | 政府官方傳記頁 |
| hansard-churchill | UK Parliament, Historic Hansard 人物頁 | https://api.parliament.uk/historic-hansard/people/mr-winston-churchill/index.html | A | 議會官方紀錄 |
| nobel-churchill | Nobel Foundation, Churchill – Biographical | https://www.nobelprize.org/prizes/literature/1953/churchill/biographical/ | B | 機構傳記、無具名作者，保守評 B（同 b3-sample） |

試過、沒用的：
- House of Commons Library SN04256、SN05650 PDF 與 commonslibrary.parliament.uk 頁面：Cloudflare 防機器人驗證（403「Just a moment...」），**未繞過**；parliament.uk living-heritage 頁同樣 403。現有張伯倫、艾德禮任期的出處就是這兩份 PDF，邱吉爾任期未能用同一份核對。
- The London Gazette 第 34854 期整期 PDF（1940 年 5 月）：只搜到同姓他人，沒找到首相任命公告；未使用。
- National Archives 推測網址 404。
- 未使用 Wikipedia、Wikidata；curl 未用 `-k`、未登入。

## 修正紀錄（2026-11-11 第一階段）

- (a) name 引文：原為「Mr Winston Churchill (Hansard)」，那是 Hansard 頁 `<title>`，與 locator「Page heading」不符。改為引文「Mr Winston Churchill」、locator「Page heading」。`build.py` 新增檢查：locator 為 Page heading 的引文必須逐字等於原始頁 `hansard.html` 第一個 `<h1>` 的純文字（去標籤、空白合併）；`verify-report.json` 記 `h1` 與 html 的 sha256。另以 curl（不帶 -k）重抓 Hansard 頁，`<h1>` 文字同為「Mr Winston Churchill」。
- (b) 出生地譯名：見上方「出生地譯名」，保留「布倫亨宮」。

## 已決項目（Tai 2026-11-11 10:13）

1. **任期拆筆**——已決：只建一筆 `[1940-05-10,1945-07-26)`，不拆 1945-05-23 看守內閣。拆點記在 research.json `unverified`（待查證；手上 A 級來源只給一段連續任期，要拆需 Commons Library 名錄等來源，目前被防機器人擋）。
2. **職銜**——已決：「Prime Minister」（照 Hansard）。相鄰任期的「Prime Minister and First Lord of the Treasury」出自 Commons Library PDF，本次不比照。
3. **黨派**——已決：Conservative；evidenceNote 註明只代表首相任內黨籍。
4. **卒地**——已決：這次不寫，記在 research.json `unverified`；不寫任何 `death_place` SQL（超出計畫）。
5. **b3-sample 連結**——已決：寫庫後另開 commit 補 `b3-sample/research.json` 邱吉爾的 `bioId`、`relatedRecordIds`；寫入第一、二階段都不改 b3-sample。
6. **nameZh／wikidataQid／照片**——已決：nameZh 無出處保留（溫斯頓·邱吉爾）；wikidataQid 與照片 null。

## 寫入進度

- 第一階段（本次）：修 2 處瑕疵、寫 `send.py`、`counts.sql`；`send.py` 對 5052／`worldline_borders_dev` 乾跑一次（只有唯讀查詢）。**未寫庫**。
- 第二階段（下一個任務）：備份 → 試跑庫 5062／`worldline_person_dryrun` → 核對 `counts.sql` → 寫入 5052 → 核對。
