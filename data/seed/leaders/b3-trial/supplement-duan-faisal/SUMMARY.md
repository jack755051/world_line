# 段祺瑞、費薩爾一世補查（Tai 2026-11-11 12:12 第 5 項；未寫庫）

- 產物：`build.py` → `research.json`（b0b0e0f 對齊格式）、`rawmap.json`；`../verify.py research.json --report verify-report.json` → **ok: true，rawChecked: true**，25 筆段落／候選角色引文逐字核對通過（引文長度 16–80）。build.py 另外核對 fields 與 gaps 候選的全部引文，也都逐字存在。
- 原文放在 `/tmp/b3supp2-raw/`（不進版控）。FRUS 頁面從 HTML 轉成純文字；LoC 權威檔用 suggest2 JSON 解碼成純文字。verify-report.json 記有各檔的 sha256。
- 沒有連資料庫：5442 既有任期取自離線檔 `../selection.json`。
- 可重現：連跑 build.py＋verify.py 兩次，三個產物的 sha256 都相同（research.json `a4910d7a…`、rawmap.json `c3108315…`、verify-report.json `181b47b1…`）。

## 來源與等級（全部 A）

| sourceKey | 來源 | 等級依據 |
|---|---|---|
| loc-duan | LC Name Authority nr94033282「Duan, Qirui, 1865-1936」 | 國家圖書館權威檔（670 欄引 Chi, Y.《段祺瑞傳》1992） |
| loc-faisal | LC Name Authority n90649742「Faysal I, King of Iraq, 1885-1933」 | 國家圖書館權威檔（670 欄引 Encyc. Brit. 15th ed. 1983、al-Aʻlām） |
| frus1916-d82、frus1916-d98、frus1917-d111、frus1917-d128、frus1917-d145、frus1924v01-d364、frus1924v01-d366、frus1926v01-d445、frus1926v01-d451、frus1926v01-d533 | Foreign Relations of the United States（history.state.gov）駐華使館電報與報告 | 美國國務院官方外交紀錄 |
| frus1921v02-d100、frus1925v02-d188、frus1927v02-d753 | FRUS：英國關於美索不達米亞委任統治的備忘錄、伊拉克委任統治電報、美英伊公約草案（含附表與註腳） | 同上 |

注意：LoC 670 欄是權威檔編目員摘錄的「來源所載」，內容實際上出自 Britannica 等書。本次照權威檔評為 A 級，evidenceNote／locator 都標明了引的是哪一本書。

## 段祺瑞（cn-duan-qirui）：試跑 0 段 → 本次 3 段

**欄位**
| 欄位 | 值 | 出處 |
|---|---|---|
| 姓名原文／中文名 | 段祺瑞 | loc-duan nonlatinLabels「段祺瑞, 1865-1936」 |
| 羅馬拼音 | Duan, Qirui（舊拼法 Tuan Chʻi-jui；FRUS 作 Tuan Chi-jui） | loc-duan 標目 |
| 生 | 1865-03-06（day） | loc-duan 670「b. 3/6/1865; d. 11/2/1936」，按美式月/日讀；與 5442 一致；來源沒有說明是否已換算成公曆 |
| 卒 | 1936-11-02（day） | 同上 |
| 出生地 | 待查證 | — |
| 黨派 | 待查證 | — |
| 簡介 | 北洋軍人政治家；1916 年任總理兼陸軍總長，1917 年被免職，同年討伐復辟時再任總理，1924–1926 年任臨時執政 | 由段落 1–3 濃縮 |

**段落**：①出任國務總理 1916–1917（FRUS 1916-04-24、06-30、1917-07-03）；②討伐復辟與再度組閣 1917（FRUS 1917-08-09、11-20）；③臨時執政 1924–1926（FRUS 1924-11-21、11-24、1926-04-10、04-21、06-16 註腳）。
**經歷層（positions）**：陸軍總長（兼，1916-04，minister）；總司令（1917-07，military_command）。
**候選角色（roleCandidates）**：國務總理 1916-04〜1916-06-29、國務總理 1916-06-29〜1917-05-23、國務總理 1917-07〜（迄日不明），都是 head_of_government；臨時執政 1924-11-24〜1926-04（month），列 head_of_state 候選，理由是 FRUS 記載內閣把「總理與總統職權」交給他。他是否同時算政府首腦，留給角色層定案。

**與 5442 逐筆比對（只報告，不改庫）**
| 5442 recordId | 5442 職稱／期間 | 本次 | 差異 |
|---|---|---|---|
| …bbf4… | 代理國務總理 1913-05-01〜1913-07-31 | — | 沒有取得 A／B 原文，無法核對 |
| …bc03… | 國務卿 1916-04-22〜1916-06-29 | Premier 1916-04（month）〜1916-06-29 | 起點同月（FRUS 電報日期是 04-24，任命日沒有寫明）；迄日相同（本次迄日是推論：同一人在 6/29 再獲任命）；**職稱不同**：5442 作「國務卿」，FRUS 作 Premier，中文原職稱沒查到，不選邊 |
| …bc06… | 國務總理 1916-06-29〜1917-05-23 | 同 | 起訖都相同 |
| …bc0b… | 國務總理 1917-07-06〜1917-11-22 | 1917-07（month）〜？ | FRUS 記黎元洪在 7 月 2 日**或之前**就下令任命，和 5442 的 07-06 可能不同，因為原文沒寫確切日，本次只記月；迄日 FRUS 只寫到 11-16 辭職、11-17 撤回，11-22 未能核對 |
| …bc16… | 國務總理 1918-03-23〜1918-10-10 | — | 沒有取得原文（FRUS 1918 年 3–4 月搜尋 0 筆） |
| （無） | — | 臨時執政 1924-11-24〜1926-04 | **5442 缺這筆任期** |

**gaps（7）**：field:birthplace、field:party、position:duan-premier-1913、position:duan-premier-1918、position:duan-premier-1917-jul（迄日）、position:duan-chief-executive-1924（迄日：4/10 電報說他已辭職，但同一封電報又說政變沒有完全成功；4/21 電報說他「離開前」頒布命令，都是 not_found）、paragraph:early-life。

## 費薩爾一世（iq-faisal1）：試跑 0 段 → 本次 3 段

**欄位**
| 欄位 | 值 | 出處 |
|---|---|---|
| 姓名原文 | فيصل | loc-faisal nonlatinLabels「فيصل، ملك العراق」 |
| 中文名 | 待查證 | 沒有取得 A／B 中文譯名來源 |
| 羅馬拼音 | Faysal I, King of Iraq | loc-faisal 標目 |
| 生 | **待查證（conflict）** | loc-faisal 引 Brit.：「b. May 20, 1885」；引 al-Aʻlām：「b. 1883」 |
| 卒 | 1933-09-08（day） | loc-faisal「d. Sept. 8, 1933」；與 5442 一致 |
| 出生地 | 待查證 | — |
| 黨派 | 不適用（君主） | — |
| 簡介 | 麥加謝里夫侯賽因之子；1918–1920 年為敘利亞國王，1921–1933 年為伊拉克國王；與英國締結 1922、1926 年條約 | 由段落 1–3 濃縮 |

**段落**：①出身（LoC）；②敘利亞與伊拉克國王（LoC、FRUS 1921-12-30 英國備忘錄提到「coronation of King Feisal」）；③與英國的條約（FRUS：1922-10-10 英伊同盟條約、1926-01-13 英伊條約、Cmd. 2587「Iraq, Treaty with King Feisal」）。
**經歷層**：無（鄂圖曼議會議員仍待查證）。
**候選角色**：敘利亞國王 1918〜1920（year，head_of_state）；伊拉克國王 1921（year）〜1933-09-08（head_of_state，regimeId 伊拉克王國）。

**與 5442 比對**
| 5442 recordId | 5442 | 本次 | 差異 |
|---|---|---|---|
| …c325… | King of Iraq 1932-10-03〜1933-09-08 | 1921（year）〜1933-09-08 | 職稱一致、迄日相同；起點不同：5442 依選人說明只收 1932 年獨立後，來源載 1921 年起在位 |
| （無） | — | 敘利亞國王 1918〜1920 | 5442 沒有這筆（而且起年有矛盾，見 gaps） |

**gaps（7）**：field:birthDate（conflict）、field:birthplace、field:nameZh、position:faisal-king-syria（conflict：Brit. 作 1918–1920，試跑時未評等的 EWB 作 1920）、position:faisal-king-iraq（加冕確切日）、paragraph:iraq-reign-details（1930 年條約、1932 年加入國聯）、paragraph:early-life。

## 與試跑結果的差異
- 試跑兩人都是 0 段。當時段祺瑞只有港大館藏說明，被降為未評等；費薩爾只有未具名的 EWB。
- 本次改用政府官方紀錄（FRUS）和國家圖書館權威檔（LoC），兩人都各有 3 段，引文全部 A 級。
- 試跑時 EWB 的候選引文（1883 年生、1920 年稱敘利亞王）沒有拿來當出處，只在 conflict gap 的說明裡提到。

## 嘗試過但失敗的來源（詳見 research.json gaps[].attempts）
- Britannica（兩人）HTTP 403；VIAF 403；Oxford Reference 403：都不繞過。
- encyclopedia.com：段祺瑞的三種網址都是 404；費薩爾的頁面只有未具名的 EWB，不採用。
- NDL 權威 API 沒有結果；Avalon 沒有收錄英伊條約（iraq001.asp 404）。
- FRUS 搜尋：1918 年段祺瑞復任、1920 年敘利亞、1932 年入國聯、1933 年費薩爾逝世都沒有可用文件。
- 試跑時遇到的 Chinese Text Project／1914-1918-online 驗證挑戰頁，這次沒有重試。

## 仍待查證
- 段祺瑞：出生地、黨派／派系、早年經歷、1913 年代理總理、1918 年總理、1917 年第二次去職日、1926 年下野確切日、各職的中文原職稱（包括 1916 年 4 月是「國務卿」還是「國務總理」）。
- 費薩爾：出生年（矛盾）、出生地、中文譯名、敘利亞王位起訖日（矛盾）、伊拉克加冕確切日、1930 年條約、1932 年加入國聯、早年經歷。
- 可以往這些方向找：中華民國政府公報影像（需要 OCR、人工判讀）、國史館、臺灣國家圖書館權威檔、League of Nations Treaty Series、英國 Hansard／Cmd. 文件。

## 自我抽查（2026-11-11 重新抓取，存在 /tmp/b3supp2-recheck/，逐字比對）
- 段祺瑞（3 個來源）：frus1916-d82「Tuan Chi-jui, Premier and Minister of War」OK；frus1924v01-d366「Tuan Chi-jui assumed office this morning」OK；frus1917-d111「The dismissal of the Premier Tuan Chi-jui on May 23」OK；loc-duan「段祺瑞, 1865-1936」「b. 3/6/1865; d. 11/2/1936」OK。
- 費薩爾（3 個來源）：loc-faisal「b. May 20, 1885」「Fayṣal al-Awwal; b. 1883; d. 1933」「d. Sept. 8, 1933」「فيصل، ملك العراق」「was King of Syria from 1918-1920 and later King of Iraq from 1921-1933」OK；frus1921v02-d100「the coronation of King Feisal and the appointment of the Arab cabinet」OK；frus1927v02-d753 三則引文 OK。
