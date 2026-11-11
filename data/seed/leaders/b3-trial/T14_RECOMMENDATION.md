# T14 邊界建議（B3 試跑）

> **建議，待 Tai 決定；未套用到資料。** 本檔不改 `research.json`／`research.aligned.json`、腳本、ARCHITECTURE.md，未寫庫。
> 依據：Tai 2026-11-11 12:12 第 3 項「T14 現在就請史料考證出建議」（經 World Line 主管轉達）。
> 讀過：ARCHITECTURE.md §16.3、§16.3.1、§16.3.2、§16.3.3、§16.9 T13／T14（b0b0e0f 三層）；`ALIGN.md`、`align-report.json`、`batch01–10/research.aligned.json`。
> 相容前提：Tai 12:12 第 2 項「黨職一律算 de_facto_leader」。

## 0. 結論（先講）

1. **兩層互斥，一段任期只存一處**：每一段任期**只**存在角色層 `person_roles` 或經歷層 `person_positions` 其中一層，不兩層都收。
2. **判定方式**：該段任期**符合 §16.3.1 收錄門檻**（類別＋門檻＋時間窗）→ 存角色層；**不符合或無法證明符合** → 存經歷層。元首／首腦／實際掌權者本來就是這個規則的特例（§16.3-3，經歷層不收），T14 只是把同一條規則擴到閣員、將領、佔領／殖民長官。
3. **詳情頁合併成一區「職位與經歷」**：兩層（加上 T13 定案前的 `leader_records`）合起來，依開始日排序成一份清單；角色列加標記（出卡角色），經歷列不加。卡片仍只讀角色層。
4. **理由**：
   - **單一來源真相**：§16.1-2 規定「任期只有一個來源真相」，§16.3-3 也禁止元首任期存兩份；兩層都收會讓同一段閣員／將領任期有兩組日期、兩組 citation，日後一定會不一致。
   - **出卡**：角色層＝出卡（§16.3.3）；只要門檻判定可以機械化，經歷層就不會影響出卡。
   - **地圖**：地圖不讀經歷層（§16.3 R7），所以互斥不影響地圖。
   - **去重**：互斥就不用去重；詳情合併顯示時只要做 union＋排序。
   - **門檻將來改了怎麼辦**：例如 P3 把閣員擴到第五部，就把符合的經歷列搬到角色層。這是可重跑的遷移腳本，不必先存兩份來預留。

## 1. 可機械判定的規則（依序判斷，第一條命中就停）

輸入：一段任期（`title.orig/zh-Hant/en`、`organization`、`positionKind`、`period`、`startPrecision/endPrecision`、`regimeId`、`acting`）。

| 步 | 條件 | 歸屬 | role_kind／position_kind |
|---|---|---|---|
| R0 | 標題是元首／首腦／攝政／代理元首或首腦（現行 `HEAD_PATTERNS`＋`GUARD`） | 角色層（T13 定案前即 `leader_records`） | `head_of_state`／`head_of_government`，代理者 `acting=true` |
| R1 | **黨職**（標題或機構含黨、party、partido、parti、党…） | 角色層 | `de_facto_leader`（Tai 12:12 第 2 項；涵蓋範圍見 §6-1） |
| R2 | 佔領／殖民長官：①是轄區**最高**行政長官（總督、帝國專員、軍政長官；不是轄區內的省／州長）②轄區在系統中是政權或併入地（`regimeId` 非 NULL）③任期可證明 ≥30 天 | 角色層 | `occupation_administrator`／`colonial_governor`；代理 `acting=true`（收、不出卡） |
| R3 | 閣員：①部門屬外交、國防／陸軍／戰爭、財政、內政四部之一 ②正職部長（標題不含副、助理、次、deputy、assistant、vice、adjunto、under-）③任期可證明 ≥90 天 ④內閣所屬政權在系統中 | 角色層 | `cabinet_minister` |
| R4 | 將領：①**國家級最高軍職**（全軍總司令、參謀總長、軍種總司令）；或戰區／方面軍司令，且至少有一筆有日期＋地點＋出處的戰役連結 ②所屬政權在系統中 | 角色層 | `military_commander` |
| R5 | 以上都不符合（含：非四部閣員、副職、軍校、警察、軍銜、轄區內地方長官、時間窗外） | 經歷層 | `position_kind`（見 §5 值域調整） |
| R6 | 類別符合 R2–R4，但**日期不足以證明門檻**（期間 NULL，或精度不足以算出最短任期） | **暫存經歷層**＋標 `roleEligible: "<role_kind>"` | 補到日期後重跑，自動搬到角色層 |

共通條件：
- **時間窗**：角色層的任期須與 1908–1945 有交集（§16.3.1 寫明適用於元首／首腦；建議其他角色比照，見 §6-2）。時間窗外的一律 R5。
- **「可證明 ≥N 天」怎麼算**：最短任期＝「結束日的最早可能值」減「開始日的最晚可能值」。精度 `year` 時開始日取 12-31、結束日取 01-01；`month` 依此類推；`day` 照原值。任一端 NULL → 無法證明 → R6。
- **一個標題兼兩職**（例：內政部長兼外交部長）：拆成兩段，各自判斷。
- **來源門檻**：角色層另須 1 筆 A 或 2 筆獨立 B（§16.3.1-2）；不夠的 → R6（`roleEligible`＋`gap: source`）。

## 2. 31 筆 t14Overlap 逐筆證據與建議歸屬

來源等級＝該筆 citations 的 grade（括號內為筆數）。期間後面是精度（開始/結束）。「角色*」＝符合類別與門檻，但 `regimeId` 目前是 NULL，或要先確認該政權在系統中。

| # | 批 | 人物 key | position key | 職稱（zh／原文） | 期間 | positionKind | 來源 | 建議 | 依據 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 01 | it-mussolini-benito | mussolini-interior-foreign | 內政部長兼外交部長／ministro dell’Interno e degli Esteri | NULL～NULL | minister | A(1) | R6（拆兩段，皆 `roleEligible: cabinet_minister`） | 四部；無日期 |
| 2 | 01 | au-deakin-alfred | deakin-ag | 聯邦總檢察長／Attorney-General | NULL～NULL | minister | A(1) | 經歷層 | 不屬四部 |
| 3 | 02 | su-stalin | stalin-nationalities-commissar | 民族事務人民委員 | 1917～1924（year/year） | minister | B(1) | 經歷層 | 不屬四部 |
| 4 | 02 | su-stalin | stalin-rabkrin-commissar | 工農檢查人民委員 | 1919～1924（year/year） | minister | B(1) | 經歷層 | 不屬四部 |
| 5 | 02 | mx-cardenas-lazaro | cardenas-interior-minister | 內政部長／ministro de Gobernación | NULL～NULL | minister | B(2) | R6 | 四部；無日期 |
| 6 | 02 | mx-cardenas-lazaro | cardenas-war-minister-1933 | 戰爭部長／secretario de Guerra y Marina | 1933～1934（year/year） | minister | B(2) | R6 | 四部；年精度算出的最短任期 <90 天 |
| 7 | 02 | mx-cardenas-lazaro | cardenas-pacific-commander | 太平洋地區軍隊司令 | 1942-07～NULL（month/—） | military_command | B(1) | R6（`military_commander`，需戰役連結） | 戰區司令，沒有戰役連結 |
| 8 | 02 | mx-cardenas-lazaro | cardenas-war-minister-1942 | 國防（戰爭）部長／ministro de Guerra | NULL～1946（—/year） | minister | B(2) | R6 | 四部；開始日 NULL |
| 9 | 03 | pt-ginestal-machado | ginestal-minister-instruction | 教育部長／ministro da Instrução | 1921～1922（year/year） | minister | A(1) | 經歷層 | 不屬四部 |
| 10 | 03 | us-fdr | fdr-asst-sec-navy | 海軍助理部長／Assistant Secretary of the Navy | 1913～NULL（year/—） | minister | B(1) | 經歷層 | 助理職；海軍部也不在四部內 |
| 11 | 05 | cn-chiang-kai-shek | chiang-whampoa-commandant | 黃埔軍校校長 | 1924-05-03～NULL（day/—） | military_command | B(1) | 經歷層 | 軍校，不是指揮職 |
| 12 | 05 | cn-chiang-kai-shek | chiang-nre-commander | 北伐軍總司令 | 1926-07-09～NULL（day/—） | military_command | B(2) | 角色*（`military_commander`） | 全軍總司令；要補 regimeId；終止日 NULL 不影響類別判定 |
| 13 | 06 | ot-talat | interior-minister | 內政大臣／Dahiliye Nazırı | 1909～NULL（year/—） | minister | B(1) | R6（另缺來源：B 只有 1 筆） | 四部；結束日 NULL |
| 14 | 06 | ar-uriburu | army-inspector-general | 陸軍總監／Inspector general del ejército | 1922～NULL（year/—） | military_command | B(1) | R6（待查：是否陸軍最高職） | 來源沒寫明是最高軍職 |
| 15 | 07 | mn-choibalsan | choibalsan-army-cic-1924 | 人民軍總司令 | 1924～NULL（year/—） | military_command | B(1) | 角色（`military_commander`）；另缺來源 → R6 | 全軍總司令；B 只有 1 筆 |
| 16 | 07 | mn-choibalsan | choibalsan-rural-economy-minister | 農牧經濟部長 | 1931～1936（year/year） | minister | B(1) | 經歷層 | 不屬四部 |
| 17 | 07 | mn-choibalsan | choibalsan-deputy-pm | 副總理／vice-Premier ministre | 1935～1940（year/year） | minister | B(1) | 經歷層 | 副職；不是首腦，也不屬四部 |
| 18 | 07 | nl-van-heutsz | heutsz-chief-general-staff | 總參謀長／chef Generale Staf | 1897-06～1899-01（month/month） | military_command | B(1) | 經歷層 | 時間窗外（與 1908–1945 無交集） |
| 19 | 07 | nl-van-heutsz | heutsz-aceh-governor | 亞齊及屬地文武總督 | 1898-12～1904-10（month/day） | other | B(1) | 經歷層 | 時間窗外；而且是殖民地內的地方長官，不是轄區最高長官 |
| 20 | 08 | hu-horthy | fleet-commander-1918 | 海軍艦隊司令（中將） | 1918～NULL（year/—） | military_command | B(1) | R6（待查：是否等於軍種總司令） | 艦隊司令與軍種總司令是否相同，來源沒寫 |
| 21 | 08 | hu-horthy | war-minister-1919 | 陸軍（戰爭）部長／Minister of War | 1919-05～NULL（month/—） | minister | B(2) | R6 | 四部；結束日 NULL |
| 22 | 08 | af-zahir | deputy-defence-1932 | 國防部副部長 | 1932～NULL（year/—） | minister | B(1) | 經歷層 | 副職 |
| 23 | 08 | af-zahir | education-1933 | 教育部長 | 1933～NULL（year/—） | minister | B(1) | 經歷層 | 不屬四部 |
| 24 | 08 | ir-reza | cossack-brigadier-1918 | 哥薩克旅准將 | 1918～NULL（year/—） | military_command | B(1) | 經歷層 | 軍銜／旅級，不是國家級職 |
| 25 | 08 | ir-reza | war-minister-1921 | 戰爭部長 | 1921～NULL（year/—） | minister | B(2) | R6 | 四部；結束日 NULL |
| 26 | 08 | mx-diaz | brigadier-1861 | 准將／General de brigada | 1861-08～NULL（month/—） | military_command | B(1) | 經歷層 | 軍銜；時間窗外 |
| 27 | 09 | do-trujillo | natl-police-chief-1924 | 國家警察首長 | 1924～NULL（year/—） | military_command | B(2) | 經歷層（positionKind 建議改 `police`） | 警察，不是軍職 |
| 28 | 09 | do-trujillo | armed-forces-cic-1928 | 國家武裝部隊總司令 | 1928～NULL（year/—） | military_command | B(2) | 角色*（`military_commander`） | 全軍總司令；要補 regimeId |
| 29 | 10 | ch-motta | head-political-dept | 政治部（外交）主管／Vorsteher des Politischen Departements | 1920～1940-01-24（year/day） | minister | A(3) | 角色*（`cabinet_minister`） | 瑞士外交部門主管＝外交部長；可證明 ≥90 天；要補 regimeId |
| 30 | 10 | ch-motta | head-finance-dept | 財政與關稅部主管 | NULL～NULL | minister | A(1) | R6 | 四部；無日期 |
| 31 | 10 | pe-leguia | finance-minister-candamo-pardo | 財政部長（坎達莫、帕爾多政府） | NULL～NULL | minister | B(1) | R6（另缺來源） | 四部；無日期 |

### 統計（依本建議）

| 原標記 | 角色層（含角色*） | R6 暫存經歷層＋roleEligible | 經歷層 | 合計 |
|---|---|---|---|---|
| cabinet | 1（#29） | 9（#1 #5 #6 #8 #13 #21 #25 #30 #31） | 9（#2 #3 #4 #9 #10 #16 #17 #22 #23） | 19 |
| general | 2（#12 #28） | 4（#7 #14 #15 #20） | 5（#11 #18 #24 #26 #27） | 11 |
| occupation_colonial | 0 | 0 | 1（#19） | 1 |
| **合計** | **3** | **13** | **15** | **31** |

註：#15 類別符合角色層，但 B 級來源只有 1 筆，所以先歸 R6。現有資料沒有任何一筆能直接進角色層：3 筆角色* 都要先補 `regimeId`／確認政權在系統中。

## 3. 各類規則與試跑實例

- **閣員（cabinet_minister）**：只收四部正職、≥90 天。實例：角色 #29（Motta 外交）；R6 #21（Horthy 戰爭部長）；經歷層 #2（總檢察長）、#9（教育）、#16（農牧）。
- **副總理**：一律經歷層（#17）。只有在來源明說「代理總理」時才算角色層 `head_of_government` 且 `acting=true`（R0）。
- **副部長／助理部長／次官**：一律經歷層（#10、#22）；§16.3.2 本來就把「次官」列為經歷層的例子。
- **將領（military_commander）**：國家級最高軍職直接收（#12、#28、#15）；戰區司令要有戰役連結（#7）；軍銜（#24、#26）、軍校（#11）、警察（#27）收經歷層。
- **佔領／殖民長官**：只收轄區最高長官，且轄區須是系統中的政權；殖民地內的省、州長收經歷層（#19）。試跑中沒有符合角色層的實例。
- **代理首腦、攝政**：角色層（R0；攝政依 §16.3.1 屬 `head_of_state`），經歷層永不收。
- **黨職**：依 Tai 12:12 一律算 `de_facto_leader`，歸角色層（R1，在 R2–R4 之前判斷）。試跑實例：`su-stalin/stalin-gensec`、`cn-chiang-kai-shek/chiang-tsung-tsai`（已在 roleCandidates）。ALIGN.md 列出、沒搬的 `cardenas-pnr-president`、`ginestal-nationalist-directorate`、Talat 的 CUP 秘書長，照「一律」應該也搬過去，見 §6-1。
- **外交官、議員、法官、地方首長**：經歷層（§16.3.1 這些類別不收為角色）。

## 4. 邊界個案建議

| 個案 | 建議歸屬 | 理由 |
|---|---|---|
| 黃埔軍校校長（#11） | 經歷層，position_kind 建議 `military_education`（或 `other`） | 校長不是指揮職，也不是國家最高軍職 |
| 多明尼加國家警察首長（#27） | 經歷層，position_kind 改 `police` | 警察，不是軍職；不屬任何 role_kind |
| 陸軍總監（#14） | R6：補到 A／B 來源**明寫**是陸軍最高職，才進角色層；否則經歷層 | 不推論職位等級 |
| 海軍艦隊司令（#20，補充） | R6，同上 | 同上 |
| 海軍助理部長（#10） | 經歷層 | 助理職；海軍部不在四部 |
| 副總理（#17） | 經歷層；代理總理另作 R0 | 不是首腦 |
| 副部長（#22） | 經歷層 | 副職 |
| 瑞士聯邦部門主管（#29、#30） | 視同部長：政治部＝外交、財政與關稅部＝財政，符合門檻就進角色層 | 瑞士聯邦委員以部門主管身分擔任部長職能；部門名稱逐筆對應四部 |
| 「戰爭兼海軍部」（#6） | 算國防／陸軍類 | 含戰爭部 |
| 時間窗外的軍職／總督（#18、#19、#26） | 經歷層 | 角色層比照 1908–1945 交集 |

## 5. 詳情「職位與任期」與「經歷」是否合併顯示

**建議合併成一區「職位與經歷」**：
- 資料來源是 `leader_records`（T13 定案前）＋`person_roles`＋`person_positions` 的 union，依開始日排序（開始日 NULL 的排最後，並標「日期待查證」）。
- 角色列加標記（例：「出卡角色」＋role_kind 中文名）；`acting=true` 的列加「代理」。
- 因為兩層互斥，合併時不用去重。
- 卡片不變：只讀角色層，依 §16.3.1 主標題排序。
- 理由：讀者看到的是完整生涯，也不會出現同一段任期在兩區各出現一次。

## 6. 若採用，需要改的地方（清單；**建議，待 Tai 決定；未套用到資料**）

1. **ARCHITECTURE.md**（由主管改，本任務不動）：§16.3-3「待決（16.9 T14）」改成互斥規則 R0–R6；§16.3.3 表的「經歷」列補「不收符合角色門檻的任期」；§16.3.1 `party_official 不收`與 12:12「黨職一律 de_facto_leader」要對齊；16.9 T14 改為已決。
2. **資料欄位**：
   - 經歷列加 `roleEligible`（role_kind 或 NULL）與 `roleGap`（`dates`｜`source`｜`regime`｜`battle_link`）。
   - `position_kind` 值域：拿掉 `party`（R1 黨職都進角色層）；加 `police`、`military_education`（或併入 `other`）。
   - `roleCandidates[*].roleKind` 改名 `role_kind`（12:12 第 4 項）。
3. **align 腳本**（新版 `align_*.py`，可重跑、輸出逐位元相同）：`t14Overlap` 改成依 R0–R6 輸出 `t14Decision`（`role`｜`role_eligible`｜`position`）；`role` 搬進 roleCandidates；一個標題兼兩職的拆段。
4. **verify 規則**：
   - positions 不得有 R0–R4 命中且門檻可證明的列（命中就報錯）。
   - roleCandidates 必須通過門檻（四部、正職、≥N 天、時間窗、來源數、regimeId 非 NULL）。
   - `roleEligible` 非 NULL 的列必須有 `roleGap`。
5. **研究提示**：
   - 四部閣員與最高軍職，要求起訖日與精度（是判定的關鍵欄位）。
   - 軍職要分清楚是「軍銜」還是「職位」，最高軍職要引文明寫。
   - 總督要寫明轄區是殖民地／保護國本體還是其中一省。
   - 黨職照 12:12 標成 de_facto_leader 候選。
6. **前端／API**（主管負責）：詳情改成合併一區（§5）；這部分不在本任務範圍。

## 7. 不確定、需要 Tai 判斷的點

1. **「黨職一律」的範圍**：是否包含**未掌權**的黨幹部（PNR 主席、CUP 秘書長、國民主義黨領導層）？§16.3.1 寫 `party_official` 不收。照字面「一律」，這些都會變成 `de_facto_leader` 並出卡，可能跟「實際掌權須 A／B 來源明說」衝突。建議澄清為「該政權的**執政黨最高職**一律算 de_facto_leader；其他黨職收經歷層 `party`」。若 Tai 維持字面「一律」，就照 R1 執行。
2. **時間窗**：§16.3.1 只對元首／首腦／實際掌權者寫了「與 1908–1945 交集」。閣員、將領、總督是否比照？本建議比照。
3. **閣員四部是否含海軍部、空軍部**：§16.3.1 只寫「國防／陸軍」。本建議：單獨的海軍部、空軍部不算，「戰爭兼海軍」算。
4. **R6 暫存經歷層**是否可接受？另一個做法是 R6 一律進 roleCandidates 但不出卡。本建議選前者，理由是角色層只放已確認的任期。
5. **合併顯示**是否接受（§5）？若 Tai 偏好保留兩區，互斥規則照樣適用，兩區不會重複。
6. **#14、#20 的職位等級**、**#12、#28、#29 所屬政權**是否在系統中：都**待查證**，本檔沒有查。
7. **T13 未決**：R0 的落點目前是 `leader_records`；T13 定案後要同步改。
