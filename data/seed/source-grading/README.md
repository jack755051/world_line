# 來源評等清單：事件引用的 60 個未評等來源

日期：2026-11-13。資料取自開發庫（`worldline_borders_dev`）。規則：`docs/source-rules.md` §2。

這 60 個來源被 197 筆事件引用（共 299 筆引文），其中 187 筆事件只有這一個來源。評完後，這些事件與靠它們支撐的國界才有機會從「待查證」升為「已查證」。

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
