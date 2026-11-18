# 引文重摘抽查（2026-11-10）

- 抽樣：results/r01–r10 中「直接採用」「重摘」各 24 筆（依 md5(id) 排序取前 24，確定性），共 48 筆。
- 原文核對：以一般 `curl`（無 `-k`、不登入）抓該筆**原本**的出處 URL；HTML 去標籤、PDF 以 pdftotext 抽字，NFC＋空白正規化後找 quote。
- 支持判讀：人工逐筆對照欄位值（明細 `spotcheck.json` 的 supports／note）。

| 類別 | 抽樣 | 原文逐字相符 | 無法取得原文 | 支持欄位值 | 部分支持 |
|---|---|---|---|---|---|
| 直接採用 | 24 | 20 | 4 | 24 | 0 |
| 重摘 | 24 | 20 | 4 | 22 | 2 |

**可核對原文 40 筆，40 筆通過（逐字出現；其中 2 筆僅 HTML 空白差異、1 筆 PDF OCR 文字層差異）；不符 0 筆。**
所有 48 筆的 quote 也都逐字出現在已存 evidence（程式全量檢查 3265 筆亦同）。

無法取得原文 8 筆：id.loc.gov ×4、valtioneuvosto.fi ×1 回 403（拒絕自動抓取，未繞過）；historia-hispanica.rah.es、kansallisbiografia.fi 需 JavaScript 載入內文。

## 問題與備註

- #0（直接採用／deathDate，`01a1c30e-dcd8-7bc1-9acc-c2ea29001289`）：403 無法取頁；LoC 標目含生卒年 1874-1945，支持卒年（值為年精度）
- #7（直接採用／birthDate，`01a1b4b7-28ec-7b8c-a2d7-32d18c61ae8f`）：403 無法取頁；標目含 1900-1970，支持生年（年精度）
- #11（直接採用／birthPlace，`01a1b52c-f94a-7e83-8bb4-62d476c72dca`）：403 無法取頁；含 Date and place of birth … Oulu
- #18（直接採用／name，`01a1b51c-82eb-73ea-8a53-0c433bd8cd42`）：403 無法取頁；含人名 Manuel Bonilla Chirinos
- #24（重摘／deathDate，`01a1c35f-1823-7a6d-b5d2-5d8779714539`）：人名後接生卒年區間 1870-1948，支持卒年（年精度）；同條 birthPlace 已改留空
- #25（重摘／summary，`01a1c41f-dcd2-7d0f-82ec-f6cf6f43346e`）：支持 summary 次要主張（1944 莫斯科停戰委員會）；evidence 前半「Rumanian Prime Minister, 1927–1930;」更貼核心主張，屬選段偏好，非錯誤
- #28（重摘／name，`01a1b4b5-7216-7331-b46b-4acd08fa8598`）：403 無法取頁；含 George II
- #29（重摘／name，`01a1b4af-e4d4-7d70-8289-a9154e8b7b4f`）：原頁為「( b.」（HTML 標籤處空白），忽略空白後逐字相符
- #36（重摘／birthDate，`01a1b4ae-0df8-768e-b4f7-bceca08788ea`）：含日期 October 15, 1893 與 Peleş 城堡，但片段（及 evidence 全文）無 born 字樣，靠上下文判讀為出生——需 Tai 決定是否接受
- #38（重摘／name，`01a1b4b7-2907-7a0f-8888-5cea80f7ae63`）：403 無法取頁；含 King Michael of Romania
- #39（重摘／birthDate，`01a1b545-5f88-776f-8f92-f696acb9fee1`）：RAH 頁面需 JavaScript 才載入內文（curl 只得 5.6KB 外框），無法核對；格式為「出生地, 日期 – 卒地, 日期」
- #40（重摘／birthPlace，`01a1b4ae-0e2f-7f5f-9005-4a460c1e3a53`）：PDF 文字層為 OCR，原頁作「Chon±ales」，evidence／quote 作「Chontales」，其餘逐字相符；支持出生地
- #41（重摘／summary，`01a1b4b7-291d-784c-b1fc-b798ed0f524a`）：支持 1888–1915 主政；完整句（含 as prime minister）99 字放不下，片段未寫 prime minister
- #43（重摘／summary，`01a1b538-0ca2-7224-a438-67797ef84a92`）：kansallisbiografia 英文頁未直接提供內文（curl 只得 450 字外框），無法核對；片段支持任經濟部（即總理）
- #46（重摘／name，`01a1b4af-e4f7-724d-aa46-97c7b4c496f3`）：原頁空白差異（HTML 標籤），忽略空白後逐字相符
