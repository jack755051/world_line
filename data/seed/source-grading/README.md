# 來源評等清單：事件引用的 60 個未評等來源

日期：2026-11-13。資料取自開發庫（`worldline_borders_dev`）。規則：`docs/source-rules.md` §2。

這 60 個來源被 197 筆事件引用（共 299 筆引文），其中 187 筆事件只有這一個來源。評完後，這些事件與靠它們支撐的國界才有機會從「待查證」升為「已查證」。

## 目前狀態（2026-11-13）

已做過一輪初評並寫入開發庫與資料建置檔：276 筆有等級（A 124、B 151、C 1），23 筆未評。

- 初評由 Claude 逐筆依「引用說明」判斷，**沒有重讀原文**，每筆的評等依據都標了「初評……待考證複核」。考證複核時直接改清單再重跑套用程式即可。
- 未評的 17 筆：引用說明只寫「相關電報」「後續報告」之類，看不出文件是誰發的。
- 未評的 6 筆：引用的是條約本文，只證明條約的規定，不證明事件的結果（例：用公投條款支持「公投結果」）。要另找記載結果的出處。
- 寫入後，開發庫已查證的事件 23 → 112 筆，已查證的國界 22 → 144 筆。
- 初評的三個取捨（Tai 2026-11-13 同意）：官方文書彙編的編者註算 A；美國是被正式通知的一方時算 A，經第三國轉報的算 B；只證明規定的條約本文先不評。

## 怎麼填

填 `events-60.csv`，一列是一筆引文（某事件引用某來源的某份文件）。只填三欄：

| 欄位 | 填什麼 |
|---|---|
| 這份文件的等級 | **評被引用的那一份文件**，不是整冊。A＝當事機關的原始文件（條約、照會、政府聲明、當事國自己的電報）；B＝第三方當時的官方紀錄（例：美國外交官轉述別國發生的事）；C＝不到 B |
| 評等依據 | 一句話：這份文件是誰發的、講誰的事 |
| 建議家族 | 同機構、同底稿的來源填同一個代號。美國國務院外交文書已預填 `us-frus`，可改 |

「美國是否為當事方」是從事件登記的參與方算出來的，只是提示：標「否」的多半是第三方轉述（B），但冊內也收錄別國的照會與條約原文，那些仍是 A，要看引用位置那一份。標「未登記參與方」的 44 筆要自己判斷。

## 填完之後

```
python3 -I tools/db/apply_source_grades.py data/seed/source-grading/events-60.csv          # 預演，不寫入
python3 -I tools/db/apply_source_grades.py data/seed/source-grading/events-60.csv --apply  # 寫入開發庫與資料建置檔
```

等級記在**每一筆引文**上（資料表 `event_citation_grades`），所以：

- 可以只填一部分，填了的列就生效，不用等整冊填完。
- 同一冊裡可以有的文件是 A、有的是 B，互不影響。
- 填錯了改清單重跑即可：程式會把舊的等級標為撤回、另寫一筆新的，不會直接覆蓋。
- 某一冊全部填完時，程式另外把整冊的預設等級設成其中最低的一級，只用在以後新增、還沒逐筆評等的引文。

用假填的資料預演過一次：只把 49 筆「美國為當事方」的引文評為 A，已查證的事件會從 23 筆變 52 筆，已查證的國界從 22 筆變 58 筆。實際結果以考證填的為準。

注意：同一個家族只算一個獨立來源。只引 `us-frus` 一族的事件，等級是 B 的話仍然是待查證，要另有第二個獨立來源才會升為已查證。

## 來源一覽（依影響的事件數排序）

| 編號 | 來源 | 引文 | 事件 | 美國為當事方的引文 | 靠這些事件的國界 | 預填家族 |
|---|---|---|---|---|---|---|
| S01 | Foreign Relations of the United States, Diplomatic Papers, 1940, Gener | 23 | 15 | 0 | 33 | us-frus |
| S02 | Papers Relating to the Foreign Relations of the United States, 1914, S | 19 | 13 | 0 | 8 | us-frus |
| S03 | Papers Relating to the Foreign Relations of the United States, The Par | 20 | 13 | 2 | 31 | us-frus |
| S04 | Foreign Relations of the United States, Diplomatic Papers, 1944, The B | 16 | 11 | 5 | 28 | us-frus |
| S05 | Foreign Relations of the United States, Diplomatic Papers, 1939, Gener | 13 | 9 | 0 | 20 | us-frus |
| S06 | Foreign Relations of the United States: Diplomatic Papers, 1945, The B | 11 | 9 | 5 | 18 | us-frus |
| S07 | Foreign Relations of the United States, Diplomatic Papers, 1941, Europ | 11 | 8 | 1 | 7 | us-frus |
| S08 | Foreign Relations of the United States, Diplomatic Papers, 1941, Gener | 14 | 8 | 10 | 5 | us-frus |
| S09 | Papers Relating to the Foreign Relations of the United States, 1918, S | 12 | 8 | 0 | 30 | us-frus |
| S10 | Foreign Relations of the United States, Diplomatic Papers, 1941, The B | 7 | 6 | 0 | 4 | us-frus |
| S11 | Papers Relating to the Foreign Relations of the United States, 1916, S | 8 | 6 | 0 | 8 | us-frus |
| S12 | Papers Relating to the Foreign Relations of the United States, The Par | 5 | 5 | 0 | 11 | us-frus |
| S13 | Foreign Relations of the United States, Diplomatic Papers, 1938, Gener | 9 | 4 | 0 | 9 | us-frus |
| S14 | Foreign Relations of the United States, Diplomatic Papers, 1942, Europ | 4 | 4 | 1 | 8 | us-frus |
| S15 | Papers Relating to the Foreign Relations of the United States, 1915, S | 6 | 4 | 0 | 4 | us-frus |
| S16 | Foreign Relations of the United States, Diplomatic Papers, 1940, Gener | 3 | 3 | 0 | 0 | us-frus |
| S17 | Foreign Relations of the United States, Diplomatic Papers, 1940, The B | 4 | 3 | 0 | 2 | us-frus |
| S18 | Foreign Relations of the United States, Diplomatic Papers, 1940, The F | 4 | 3 | 0 | 0 | us-frus |
| S19 | Foreign Relations of the United States, Diplomatic Papers, 1942, Gener | 6 | 3 | 3 | 0 | us-frus |
| S20 | Foreign Relations of the United States, Diplomatic Papers, 1943, Europ | 4 | 3 | 2 | 16 | us-frus |
| S21 | Foreign Relations of the United States, Diplomatic Papers, 1944, Europ | 4 | 3 | 2 | 10 | us-frus |
| S22 | Foreign Relations of the United States, Diplomatic Papers, 1945, Europ | 4 | 3 | 4 | 30 | us-frus |
| S23 | Foreign Relations of the United States, Diplomatic Papers, 1945, Europ | 3 | 3 | 0 | 11 | us-frus |
| S24 | Papers Relating to the Foreign Relations of the United States, 1918, R | 5 | 3 | 0 | 8 | us-frus |
| S25 | Papers Relating to the Foreign Relations of the United States, With th | 3 | 3 | 0 | 5 | us-frus |
| S26 | Papers Relating to the Foreign Relations of the United States, With th | 5 | 3 | 0 | 4 | us-frus |
| S27 | Documents on German Foreign Policy 1918–1945, Series D (1937–1945), Vo | 6 | 3 | 0 | 10 | us-frus |
| S28 | Documents on German Foreign Policy 1918–1945, Series D (1937–1945), Vo | 3 | 3 | 0 | 8 | us-frus |
| S29 | French Yellow Book, Chapter IV: From the Rupture of Diplomatic Relatio | 3 | 2 | 0 | 0 | — |
| S30 | Foreign Relations of the United States, Diplomatic Papers, 1937, The F | 3 | 2 | 0 | 1 | us-frus |
| S31 | Foreign Relations of the United States, Diplomatic Papers, 1942, Europ | 8 | 2 | 5 | 5 | us-frus |
| S32 | Foreign Relations of the United States, Diplomatic Papers, 1945, Europ | 2 | 2 | 1 | 5 | us-frus |
| S33 | Foreign Relations of the United States: Diplomatic Papers, 1945, The F | 4 | 2 | 0 | 2 | us-frus |
| S34 | Papers Relating to the Foreign Relations of the United States, 1917, S | 3 | 2 | 1 | 0 | us-frus |
| S35 | Papers Relating to the Foreign Relations of the United States, 1918, R | 2 | 2 | 0 | 6 | us-frus |
| S36 | Papers Relating to the Foreign Relations of the United States, 1922, V | 3 | 2 | 0 | 5 | us-frus |
| S37 | Papers Relating to the Foreign Relations of the United States, Japan,  | 3 | 2 | 2 | 0 | us-frus |
| S38 | Papers Relating to the Foreign Relations of the United States, With th | 3 | 2 | 0 | 5 | us-frus |
| S39 | Papers Relating to the Foreign Relations of the United States, With th | 2 | 2 | 0 | 2 | us-frus |
| S40 | Nazi Conspiracy and Aggression, Volume III（Office of United States Chi | 2 | 2 | 0 | 7 | — |
| S41 | Nazi Conspiracy and Aggression, Volume IV（Office of United States Chie | 2 | 2 | 0 | 5 | — |
| S42 | Foreign Relations of the United States: Diplomatic Papers, 1936, Europ | 1 | 1 | 0 | 3 | us-frus |
| S43 | Foreign Relations of the United States: Diplomatic Papers, 1936, Gener | 2 | 1 | 0 | 0 | us-frus |
| S44 | Foreign Relations of the United States, Diplomatic Papers, 1939, Gener | 2 | 1 | 0 | 2 | us-frus |
| S45 | Foreign Relations of the United States: Diplomatic Papers, 1941, The F | 1 | 1 | 0 | 0 | us-frus |
| S46 | Foreign Relations of the United States, Diplomatic Papers, 1943, The B | 1 | 1 | 0 | 2 | us-frus |
| S47 | Foreign Relations of the United States, Diplomatic Papers, 1943, The N | 2 | 1 | 0 | 0 | us-frus |
| S48 | Foreign Relations of the United States, Diplomatic Papers, 1944, The N | 2 | 1 | 0 | 2 | us-frus |
| S49 | Foreign Relations of the United States: Diplomatic Papers, The Confere | 2 | 1 | 2 | 2 | us-frus |
| S50 | Foreign Relations of the United States: Diplomatic Papers, The Confere | 2 | 1 | 2 | 6 | us-frus |
| S51 | Papers Relating to the Foreign Relations of the United States, 1917, S | 1 | 1 | 1 | 0 | us-frus |
| S52 | Papers Relating to the Foreign Relations of the United States, 1923, V | 2 | 1 | 0 | 3 | us-frus |
| S53 | Papers Relating to the Foreign Relations of the United States, 1925, V | 1 | 1 | 0 | 2 | us-frus |
| S54 | Papers Relating to the Foreign Relations of the United States, 1931, V | 1 | 1 | 0 | 2 | us-frus |
| S55 | Papers Relating to the Foreign Relations of the United States, The Par | 1 | 1 | 0 | 2 | us-frus |
| S56 | Papers Relating to the Foreign Relations of the United States, With th | 2 | 1 | 0 | 2 | us-frus |
| S57 | Papers Relating to the Foreign Relations of the United States, With th | 1 | 1 | 0 | 0 | us-frus |
| S58 | Nazi Conspiracy and Aggression, Volume VIII（Office of United States Ch | 1 | 1 | 0 | 2 | — |
| S59 | Documents on German Foreign Policy 1918–1945, Series D (1937–1945), Vo | 1 | 1 | 0 | 1 | us-frus |
| S60 | 北方領土問題の経緯（領土問題の発生まで） | 1 | 1 | 0 | 6 | — |

# 沒有起始事件的國界

日期：2026-11-13。開發庫裡有 550 筆主權紀錄沒有起始事件。先用資料本身判定每一筆的來歷（`tools/db/classify_sovereignty_origin.py`，不查資料、不推測事件）：

| 來歷 | 筆數 | 意思 | 要做什麼 |
|---|---|---|---|
| 期初既有 | 165 | 起始日在 1908-01-01 或更早 | 不需要事件。要的是「1908 年當時疆界」的出處，目前沒有地方可以記，仍是待查證 |
| 接續、形狀相同 | 156 | 同一政權的前一筆在同一天結束，形狀一樣，只是資料分段 | 不需要事件，可信程度自動沿用前一筆 |
| 疆界有變動 | 88 | 接續前一筆，形狀差 2% 以上 | 需要有出處的事件 |
| 新出現 | 93 | 同一政權沒有前一筆 | 需要有出處的事件（成立、獨立、佔領、改制） |
| 細微差異 | 48 | 接續前一筆，形狀差 0.1%–2% | 要人看：是資料版本差異，還是真的小幅調整 |

後三類共 229 筆列在 `borders-without-event.csv`，每筆附同一天資料庫裡已有的事件當提示。

- 其中 12 筆同一天剛好有該政權參與的事件，已由 Claude 判定並連上（備註欄有標，待複核）。
- 其餘 217 筆：156 筆同一天沒有任何事件，61 筆同一天有別的事件但沒有列這個政權為參與方。
- 很多起始日是 1 月 1 日或資料批次的接縫（例：1937-07-07、1918-11-12），那是資料集只記到年、或批次切換造成的，不一定是真的變動日。遇到這種，判定填「不是真的變動」並在備註寫明。

清單另有兩欄資料面的提示：「起始日與資料集的關係」（資料集記的起始日就是這一天／只記到年或月／較早，表示這一天是截斷或重新分段的日子）與「與前一段是否同一個資料集關聯」。

期初既有的國界沒有事件可補，改用「國界本身的引文」：`POST /api/v1/sovereignty-records/{id}/citations`（來源、引用位置、說明、等級、依據），例如 1908 年前後出版的地圖集圖版或劃界條約。一筆 A 級，或兩個獨立家族的 B 級，就算已查證。資料集不能當出處。

更新（2026-11-14）：Tai 同意 Wikisource 的官方文件轉錄本可收、記 B 之後，四個馬來邦已補上事件並連好，現在是已查證。下面是當初卡住時的紀錄。

試做紀錄（2026-11-14，四個馬來邦 1909-07-09）：條約本文找到了 A 級出處，但批准書互換日只出現在不可當出處的網站，原件沒有可讀的線上全文，所以事件還沒有建立；細節寫在清單那四列的備註。這一組花了六次查詢，可以當作估工的參考。

精確日期查不到時降低精度（Tai 2026-11-14）：出處只能把起始日確定到月或年，就在「起始日可確定到」填 month 或 year，照樣可以連上事件；畫面會標示「起始日只確定到年」。但如果連事情有沒有發生都沒有出處，就不能靠降低精度解決（四個馬來邦就是這種情況，見那四列的備註）。

填法：判定欄三選一。要連到既有事件就填它的 event_id；需要新事件的，先照一般流程建立事件（附引文與等級），拿到 event_id 再填。

```
python3 -I tools/db/apply_border_events.py data/seed/source-grading/borders-without-event.csv          # 預演
python3 -I tools/db/apply_border_events.py data/seed/source-grading/borders-without-event.csv --apply
```

注意：來歷與「國界 → 事件」的連結只存在開發庫（表 `sovereignty_record_links`）。重建資料庫後，來歷要重跑判定程式；清單裡的 event_id 會跟著重建而改變，要重新對應。

# 期初既有的國界（1908 年起點）

日期：2026-11-14。165 筆（另有 48 筆沿用它們）。這些國界沒有事件可補，要靠「國界本身的引文」。

已登記兩套公有領域的學術地圖集當來源（`data/seed/atlases-1910/`），兩套是不同家族，都評為 B：

- The Cambridge Modern History Atlas（Cambridge University Press, 1912）
- William R. Shepherd, Historical Atlas（Henry Holt, 1911）

同一筆國界兩套都相符，就達到已查證的門檻。**目前還沒有替任何國界附引文**，要先逐筆比對。

比對清單是 `baseline-borders.csv`，每筆已依位置填好兩套地圖集的候選圖版：

| 區域 | 筆數 |
|---|---|
| 非洲 | 58 |
| 歐洲 | 29 |
| 中美洲與加勒比海 | 21 |
| 亞洲 | 18 |
| 大洋洲與太平洋 | 15 |
| 南美洲 | 12 |
| 南亞 | 8 |
| 北美洲 | 4 |

比對時要注意：

1. 圖版畫的是 1910–1911 年，不是 1908 年。1908 到 1910 之間有變動的（例：1908 年 10 月奧匈併吞波士尼亞、保加利亞獨立；1908 年 11 月剛果自由邦改為比屬剛果；1910 年日本併吞韓國、南非聯邦成立），圖版不能支持 1908 年初的形狀，要記在備註、不附引文。
2. 圖版比例尺很小（歐洲圖是 1:20,000,000），只能確認到「國家層級的輪廓與鄰國關係相符」，不能確認邊界細節。引文的說明要照實寫到這個程度。
3. 已實際開過一張確認掃描可用：Shepherd 頁 166–167「Europe at the Present Time」，archive.org 的掃描頁是 n158、n159，國名、著色與國界線都看得清楚。
4. 德州大學圖書館也有單張圖版，但該站有防機器人驗證，程式讀不到，沒有繞過。

比對相符後，用 `POST /api/v1/sovereignty-records/{id}/citations` 附引文（來源、圖版編號、說明、等級 B、依據）。

## 歐洲第一批比對結果（2026-11-14，29 筆）

做法：把資料庫 1908-01-01 的形狀畫出來，和圖版的高解析掃描逐國對照（Claude 目視，待考證複核）。結果逐筆寫在 `baseline-borders.csv`。

| 結果 | 筆數 | 說明 |
|---|---|---|
| 相符，已附引文 | 17 | 德、盧、比、荷、瑞士、義、希、挪、瑞典、葡、羅、塞、蒙特內哥羅、聯合王國、賽普勒斯、直布羅陀、馬爾他 |
| 不符 | 2 | 奧匈帝國（圖版是併吞波士尼亞之後）；丹麥（資料庫缺陷，見下） |
| 部分相符 | 1 | 西班牙（本土相符；這一筆還包含西屬撒哈拉與加那利群島，要另比對非洲圖版） |
| 圖上無法判斷或沒有畫 | 9 | 克里特、根西、澤西、曼島、安道爾、列支敦斯登、摩納哥、聖馬利諾、中立莫雷斯內 |

**只有 Shepherd 1911 一套可用。** 劍橋 1912 圖 141 手上的彩色掃描（archive.org `india.history.resource.92049`，掃描頁 n528）解析度太低，另一份掃描是黑白的、政治著色全失。所以這 17 筆目前是「有一個 B 級出處」，還是待查證；要升為已查證，需要第二套地圖集的高解析圖版。

比對時發現的資料問題：

1. **丹麥**：冰島被切在西經 20 度，冰島西部不在資料裡。
2. **葡萄牙**：含馬德拉但不含亞速群島。
3. **西班牙**：同一筆紀錄把本土、加那利群島與西屬撒哈拉合在一起。
4. 上面第 1、2 點都剛好斷在西經 20 度附近，可能是某一批資料取用時的範圍框造成的，其他跨越這條線的紀錄也該檢查。

引文的資料建置檔在 `data/seed/atlases-1910/citations.json`，用 `send_citations.py` 送出（以政權代號＋日期對應主權紀錄）。

## 非洲第二批比對結果（2026-11-14，58 筆）

圖版：Shepherd 1911 頁 174–175「The Partition of Africa」（archive.org 掃描頁 n166–n167；掃描是橫放的，要轉正）。比例尺 1:40,000,000，是歐洲圖版的一半。這張掃描在北緯 10–12 度一帶貼有膠帶、中間有一道書頁摺痕，蓋住蘇丹中段、阿比西尼亞與索馬利蘭的一部分。劍橋 1912 圖 130 的掃描同樣解析度不足，沒有用上。

| 結果 | 筆數 | 說明 |
|---|---|---|
| 相符，已附引文 | 27 | 德屬四地（東非、西南非、喀麥隆、多哥蘭）、剛果、葡屬東非、卡賓達、葡屬幾內亞、聖多美普林西比、南部非洲各殖民地與保護地（開普、納塔爾、德蘭士瓦、奧蘭治河、貝專納、巴蘇托蘭、史瓦濟蘭、南羅德西亞、尼亞薩蘭）、英屬東非、桑吉巴、厄利垂亞、突尼西亞、獅子山、甘比亞、馬達加斯加、馬約特、塞席爾 |
| 不符 | 3 | 葡屬安哥拉、巴羅策蘭—西北羅德西亞、義屬索馬利蘭（都是資料庫有疑問，見下） |
| 待查 | 1 | 賴比瑞亞（面積比一般記載少一成多） |
| 部分相符 | 2 | 法蘭西共和國（本土＋阿爾及利亞）、鄂圖曼帝國（橫跨三洲） |
| 圖上無法判斷或沒有畫 | 25 | 多數是圖版沒有畫出殖民地內部的分界（法屬西非、法屬剛果、奈及利亞、黃金海岸各拆成的幾筆），其餘是被膠帶蓋住或範圍太小 |

和歐洲一樣，只有 Shepherd 一套可用，這 27 筆目前是「有一個 B 級出處」，仍是待查證。

比對時發現的資料問題：

1. **安哥拉與巴羅策蘭的界線在東經 20 度整。** 圖版上兩者的界線是 1905 年仲裁線（標「1905」的虛線），在更東邊。資料庫裡安哥拉少了約 23 萬平方公里，巴羅策蘭—西北羅德西亞多了差不多同樣大的一塊；安哥拉東部（例如東經 21 度、南緯 12.5 度）現在被算在巴羅策蘭名下。看起來資料集用的是仲裁之前的主張線。**已修正**（2026-11-14，`data/seed/barotse-1905`）：找到 1905-05-30 仲裁裁決本文（A 級），三筆紀錄改用裁決線，安哥拉與巴羅策蘭現在是已查證。
2. **義屬索馬利蘭只有約 1 萬平方公里的沿岸細條**，內陸（含摩加迪休附近）在 1908 年沒有任何紀錄涵蓋。
3. **1908 年有幾塊空白**：茅利塔尼亞（紀錄從 1912 年才開始）、查德北部（提貝斯提、博爾庫）、蘇丹南方的拉多飛地一帶。
4. **賴比瑞亞**面積 95,747 平方公里，比一般記載少一成多，原因未查。

## 第二套地圖集找到了（2026-11-14）

劍橋地圖集在 archive.org 另有一份清楚的彩色掃描：1924 年第二版（`cambridgemodernh0000sira_i1w3`）。1910 年各圖與 1912 年初版同題，已另外登記為來源（與初版同一個家族）。這份掃描把跨頁的地圖掃成左右兩頁，要自己拼起來；中間書脊一帶看不到。

| 圖 | 掃描頁 | 用途 |
|---|---|---|
| 141 Europe in 1910 | n627、n628 | 歐洲，已核對 |
| 130 Africa in 1910 | n589、n590（橫放，要轉正） | 非洲，已核對 |
| 132 Egypt and the Anglo-Egyptian Sudan | n594 | 尚未使用 |
| 134 The West Indies and Central America in 1910 | n600 起 | 尚未使用 |
| 135 South America in 1910 | n602 起 | 尚未使用 |
| 140 The World, Colonial Possessions and Commercial Highways in 1910 | n624 起 | 尚未使用（上面有格陵蘭） |

用它複核之後：

| 區域 | 兩套都相符（已查證） | 只有一套相符（待查證） |
|---|---|---|
| 歐洲 | 14 | 3（塞爾維亞、蒙特內哥羅、希臘：在劍橋圖的書脊處看不到） |
| 非洲 | 21 | 9（6 筆只有 Shepherd、3 筆只有劍橋） |

連同沿用它們的紀錄，由地圖集支持而達到已查證的國界有 53 筆。

劍橋的非洲圖比 Shepherd 的多畫了一些內部分界與標名（南北奈及利亞、黃金海岸三區、東北與西北羅德西亞、拉多飛地），但在放大圖上有幾處還不夠清楚，我只把看得清楚的算相符，其餘留在備註。

先前記下的三個資料疑點，第二套地圖集都得到同樣的結果：安哥拉與巴羅策蘭的界線不在東經 20 度；義屬索馬利蘭不是只有沿岸細條；衣索比亞的東南界因此也與圖不同。

## 美洲比對結果（2026-11-14，中美洲與加勒比海 21 筆、南美洲 12 筆）

圖版（兩套都有，都很清楚）：

| 區域 | Shepherd 1911 | 劍橋 1924 年第二版 |
|---|---|---|
| 中美洲與加勒比海 | 頁 213（掃描頁 n196，橫放） | 圖 134（掃描頁 n600，橫放） |
| 南美洲 | 頁 214–215（掃描頁 n198，橫放） | 圖 135（掃描頁 n603、n604，橫放） |

| 區域 | 兩套都相符（已查證） | 只有一套相符 | 不符或不適用 |
|---|---|---|---|
| 中美洲與加勒比海 | 18 | 3（古巴、開曼群島、百慕達） | 0 |
| 南美洲 | 6（阿根廷、智利、烏拉圭、委內瑞拉、英屬圭亞那、法屬圭亞那） | 0 | 6 |

小島（牙買加、巴哈馬、各背風與向風島嶼等）在圖上只是用顏色或底線標示歸屬，引文只支持「屬於誰」，不支持範圍，引文說明裡都有註明。

南美洲不符的 6 筆是同一類問題——**資料庫把爭議區劃給了單一國家**：

1. **亞馬遜西北部（厄瓜多、秘魯、哥倫比亞）**：兩套地圖集都把這一帶標成爭議中（Shepherd 寫「Claimed by Peru」「Claimed by Ecuador」，劍橋用斜線）。資料庫把整塊算給厄瓜多，厄瓜多因此有 60 萬平方公里、向東延伸到西經 70 度。
2. **查科（玻利維亞、巴拉圭）**：兩套地圖集都把查科北部畫在玻利維亞境內；資料庫把大半算給巴拉圭。
3. **巴西**：1908 年初那一筆早於圖版所畫的 1909 年巴西—秘魯劃界，圖版不適用。

照憲法 R6，這些地方應該是多筆主張並存，而不是選一個。這不是補出處能解決的，要改資料。

比對時另外發現：**蘇利南（荷屬圭亞那）在 1908 年沒有任何紀錄**，兩套地圖集上都有畫。

## 亞洲、南亞、大洋洲、北美洲比對結果（2026-11-14，45 筆）與總表

圖版：

| 區域 | Shepherd 1911 | 劍橋 1924 年第二版 |
|---|---|---|
| 亞洲、南亞 | 頁 170–171（掃描頁 n162） | 圖 138 中華帝國 1910（n615、n616）；圖 140 世界 1910（n623、n624） |
| 大洋洲 | 頁 172（n163，橫放） | 圖 140 世界 1910 |
| 北美洲 | 頁 212（n195，橫放） | 圖 140 世界 1910 |

這一批的圖版比例尺更小（1:40,000,000 以下，劍橋的世界圖更小），所以只確認輪廓與歸屬。Shepherd 的世界殖民地圖（頁 179–182）在這份掃描裡是黑頁，沒有掃到。

45 筆的結果：兩套都相符 17 筆、只有一套相符 19 筆、不符或待查 2 筆、無法判斷 7 筆。

只有一套相符的，多半是因為另一套不適用：劍橋的中國圖畫的是 1910 年併吞韓國之後，不能當 1908 年日本與韓國的出處；Shepherd 的亞洲圖只畫到赤道附近，荷屬東印度與新幾內亞只有劍橋的世界圖畫到。

資料問題：

1. **暹羅**：資料庫從 1908 年起就用 1909 年之後的形狀。吉打、吉蘭丹、登嘉樓、玻璃市在 1909-07-09 移交英國之前屬暹羅，但那段期間這四邦在資料庫裡沒有任何紀錄涵蓋。**已修正**（2026-11-14，`data/seed/siam-1909`）：拆成 1909-07-09 前後兩筆，之前那一筆含四邦（形狀為推估）。
2. **希瓦汗國**：面積 37,033 平方公里，比一般記載的約 6 萬少很多，原因未查。

### 比對之後的資料修正（2026-11-14）

| 批次 | 修了什麼 | 結果 |
|---|---|---|
| `data/seed/siam-1909` | 暹羅拆成 1909-07-09 前後兩筆，之前那一筆含馬來四邦 | 之後那一筆已查證；之前那一筆待查證（形狀為推估） |
| `data/seed/barotse-1905` | 安哥拉、巴羅策蘭—西北羅德西亞、北羅德西亞（1911–1915）改用 1905 年仲裁裁決線 | 安哥拉、巴羅策蘭已查證 |
| `data/seed/italian-somaliland-1908` | 義屬索馬利蘭 1908–1920 補上內陸 | 已查證；內陸界線只是大致位置 |

另外：`data/seed/australia-1914` 補上澳洲 1914 年上半年的空白；四筆跨洲紀錄補比對完（丹麥、鄂圖曼各附一筆引文；西班牙的撒哈拉北段、法國的阿爾及利亞南界無法確認）。全面檢查「陸地上沒有紀錄的地方」的結果在 `coverage-gaps.md`。

下面的總表是修正之前的比對結果；修正之後，非洲的「已查證」多 3 筆、「不符或待查」少 3 筆，亞洲的暹羅仍算待查。逐筆現況以 `baseline-borders.csv` 為準。

### 165 筆期初既有國界的總表

| 區域 | 筆數 | 已查證（兩套都相符） | 一個出處 | 不符或待查 | 無法判斷 |
|---|---|---|---|---|---|
| 非洲 | 58 | 21 | 9 | 6 | 22 |
| 歐洲 | 29 | 14 | 3 | 3 | 9 |
| 中美洲與加勒比海 | 21 | 18 | 3 | 0 | 0 |
| 亞洲 | 18 | 2 | 10 | 2 | 4 |
| 大洋洲與太平洋 | 15 | 7 | 5 | 0 | 3 |
| 南美洲 | 12 | 6 | 0 | 6 | 0 |
| 南亞 | 8 | 5 | 3 | 0 | 0 |
| 北美洲 | 4 | 3 | 1 | 0 | 0 |
| **合計** | 165 | 76 | 34 | 17 | 38 |

「不符或待查」這一欄是要改資料的；「無法判斷」多數是圖版沒有畫出殖民地內部的分界，或範圍太小，要找比例尺更大的專圖。
