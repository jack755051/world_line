# B3 試跑對齊 ARCHITECTURE.md b0b0e0f（人物／角色／經歷三層）

## 做法
- `python3 -I align_b0b0e0f.py`：讀 `batchNN/research.json`（原檔不動），輸出 `batchNN/research.aligned.json` 與 `align-report.json`。冪等：連跑兩次，所有輸出逐位元相同（已驗，無時間戳）。
- 只搬移／改名／加標記；不新增或改寫引文、日期、出處。未建任何角色資料、未寫庫。
- `verify.py` 偵測頂層 `alignedTo == "b0b0e0f"` 時加跑對齊檢查（見檔頭 11–13），其餘原檢查保留；對齊檔報告為 `batchNN/verify-aligned-report.json`（含原文逐字核對，rawChecked=true）。原 `research.json` 仍可用舊規則驗證。

## 轉換規則
1. `positions[*].roleKind` → `positionKind`，值照搬（值域仍為原 7 種，僅供參考）。
2. 元首／首腦／實際掌權者 → 移入 `roleCandidates`（保留原欄位含 citations、期間、標題、sourceKey；原 `positionKind` 原位改名 `originalPositionKind`（值照搬）；加 `role_kind`、`reason`）。判斷（腳本內 `HEAD_PATTERNS`／`GUARD`／`PERSON_OVERRIDES`）：
   - 任一語種標題含副職／機構內職務字樣（副、議長、主席、黨、house of、governor…）一律不算首腦；
   - 標題起首為總統／國王／皇帝／首相／總理／攝政／獨裁者…等才算 head_of_state／head_of_government／de_facto_leader；
   - 標題無法判斷、需依內容者，用個案覆寫表（目前 0 筆；原 2 筆黨職已改由規則 4 涵蓋）。
3. T14 重疊類別留在 positions，加 `t14Overlap`：`positionKind=minister`→`cabinet`；`military_command`→`general`；標題含總督／governor 且標題或機構含殖民／屬地／佔領字樣→`occupation_colonial`（優先於前兩者）。

4. **黨職一律算 de_facto_leader**（Tai 2026-11-11 12:12 第 2 項）：`positionKind=party` 的項目一律移入 `roleCandidates`，`role_kind=de_facto_leader`，`reason`＝「Tai 2026-11-11 12:12：黨職一律算 de_facto_leader」；原欄位不改寫。先於規則 2 判斷。
   - `positionKind` 非 party、但標題／機構含政黨字樣（黨、party、partido、總書記…，見 `PARTY_HINT`）者**不猜**：留在 positions，加 `partyPostAmbiguous: true` 與 `partyPostAmbiguousReason`。
5. **候選角色欄位統一為 `role_kind`**（Tai 同日第 4 項）：取代 `candidateRoleKind`；舊 `roleKind` 改存 `originalPositionKind`。同一物件不會同時有 roleKind 與 role_kind（verify 第 12 項擋）。
6. verify 對齊檔另檢查（第 12、14 項）：roleCandidates 必有 `role_kind`、不得有 `roleKind`／`candidateRoleKind`；positions 不得含 `positionKind=party`（標 `partyPostAmbiguous` 者除外）。值域已由規則 9 擴充。
7. **以政黨身分取得的席位算黨職**（Tai 2026-11-11 12:47 第 2 項「薩拉查 1921 議員算黨職」，規則化）：`positionKind=legislator` 且標題／機構明寫政黨（`PARTY_HINT`）→ 比照規則 4 移入 `roleCandidates`，`role_kind=de_facto_leader`，原 citations／期間／標題照搬，`originalPositionKind=legislator`，`reason` 見 `PARTY_SEAT_REASONS`（薩拉查：「Tai 2026-11-11 12:47：薩拉查 1921 議員算黨職」）。不再產生 `partyPostAmbiguous`。全 10 批掃描（含 14 筆 legislator 的標題、機構、引文）只有薩拉查一筆標題明寫政黨；其他議員的引文只有 elected／當選，未寫以何黨身分，不算。
8. **T14 R0–R6 兩層互斥**（Tai 2026-11-11 12:47 第 5 項「T14 建議套用到試跑資料」；規則與判斷順序照 `T14_RECOMMENDATION.md` §1，第一條命中即停）：
   - 每筆 `t14Overlap` 項加 `t14Rule` 與 `t14Reason`（引文件 §2 列號）；逐筆判定在腳本 `T14_DECISIONS`，是文件 §2 表與 §4 邊界個案的機械化，未另加判斷。腳本會 assert 表內 31 筆全部對到。
   - R0–R4 命中且門檻可證明 → 移入 `roleCandidates`（`role_kind` 用文件 §1 的值：cabinet_minister、military_commander、occupation_administrator、colonial_governor）。**本批 0 筆**。
   - R6（類別符合 R2–R4，門檻無法證明）→ 留 positions，加 `roleEligible: true`、`roleEligibleKind`（文件寫 `roleEligible: "<role_kind>"`；依任務指示 roleEligible 用 true，角色種類另放 roleEligibleKind）、`roleGap`（dates｜source｜regime｜battle_link｜rank）。
   - R5 → 留 positions。
   - 邊界個案（文件 §4）：黃埔軍校校長 `positionKind` → `military_education`、國家警察首長 → `police`，原值存 `originalPositionKind`。
   - 黨職候選（規則 4、7）加 `t14Rule: "R1"`。
   - 文件標「角色*」的 #12、#28、#29（類別與日期門檻都符合，但 `regimeId` NULL、政權是否在系統中待查證）：R3④／R4②「政權在系統中」無法證明，依「類別符合但門檻無法證明」歸 **R6**，`roleGap=regime`。文件 §6-2 的 roleGap 值域含 regime，§2 註也寫「沒有任何一筆能直接進角色層」，所以這不算猜測。
   - #1 墨索里尼「內政部長兼外交部長」：文件建議拆兩段。兩段結論相同（都是 R6 cabinet_minister），但拆段要新建 key／標題，等於改寫資料，所以**未拆**，理由寫在 t14Reason。
   - `rank` gap（#14 陸軍總監、#20 艦隊司令）：文件寫「R6（待查：是否最高職）」，照列 R6，gap 名稱 `rank` 是我取的（文件 §6-2 未列此值）。
9. verify 對齊檔再加第 15–18 項：role_kind 值域擴為 7 種角色層值；positions.positionKind 不得為任何角色層值，值域加 police、military_education；每筆 t14Overlap 必有 t14Rule（R0–R6）或 t14Ambiguous；positions 內 R0–R4 一律報錯（兩層互斥）；R6 必有 roleEligible=true＋roleEligibleKind＋roleGap，非 R6 不得有；originalPositionKind 必須屬原值域。已用注入錯誤測過會報錯。

## Tai 12:12 第 2、4 項變更清單（黨職→de_facto_leader 候選，共 5 筆）
| 批 | 人物 | 職稱（原文） | 期間 | 原 positionKind → role_kind |
|---|---|---|---|---|
| b02 | 約瑟夫·史達林（su-stalin） | 黨中央總書記（segretario generale del comitato centrale） | 1922– | party → de_facto_leader（原已在候選，改欄位） |
| b02 | 拉薩羅·卡德納斯（mx-cardenas-lazaro） | 國民革命黨主席（presidente del Partido Nacional Revolucionario） | 1930– | party → de_facto_leader（新移） |
| b03 | 安東尼奧·吉內斯塔爾·馬沙多（pt-ginestal-machado） | 民族黨執行委員會主席（presidente do directório do Partido Nacionalista） | 1923–1928 | party → de_facto_leader（新移） |
| b05 | 蔣中正（cn-chiang-kai-shek） | 國民黨總裁（總裁） | 1938-03– | party → de_facto_leader（原已在候選，改欄位） |
| b06 | 塔拉特帕夏（ot-talat） | 統一與進步委員會總書記（Cemiyet-i Umumiye Kâtibi） | 1912– | party → de_facto_leader（新移；依主管指示，統一與進步委員會照黨職處理） |

期間迄日空白者為研究檔原本就是 null（待查證），未補。

## partyPostAmbiguous 清單（0 筆）
- ~~b09 薩拉查 `deputy-1921`~~ → Tai 2026-11-11 12:47 已決：算黨職，移入 roleCandidates（規則 7）。

## Tai 12:47 第 2、5 項逐筆變更表（32 筆：黨籍席位 1＋T14 31）
年份取期間起訖的年；NULL 表示研究檔原本就是 null（待查證）。

| 批 | 人物 | 職位 key | 職稱 | 年份 | 規則 | 去向 |
|---|---|---|---|---|---|---|
| 09 | 安東尼奧·薩拉查（pt-salazar） | deputy-1921 | 議員（天主教中央黨） | 1921–1921 | R1（黨籍席位） | roleCandidates：de_facto_leader |
| 01 | 貝尼托·墨索里尼（it-mussolini-benito） | mussolini-interior-foreign | 內政部長兼外交部長 | NULL–NULL | R6 | positions（roleEligible）：roleEligibleKind=cabinet_minister，roleGap=dates |
| 01 | 阿爾弗雷德·迪金（au-deakin-alfred） | deakin-ag | 聯邦總檢察長 | NULL–NULL | R5 | positions |
| 02 | 約瑟夫·史達林（su-stalin） | stalin-nationalities-commissar | 民族事務人民委員 | 1917–1924 | R5 | positions |
| 02 | 約瑟夫·史達林（su-stalin） | stalin-rabkrin-commissar | 工農檢查人民委員 | 1919–1924 | R5 | positions |
| 02 | 拉薩羅·卡德納斯（mx-cardenas-lazaro） | cardenas-interior-minister | 內政部長 | NULL–NULL | R6 | positions（roleEligible）：roleEligibleKind=cabinet_minister，roleGap=dates |
| 02 | 拉薩羅·卡德納斯（mx-cardenas-lazaro） | cardenas-war-minister-1933 | 戰爭部長 | 1933–1934 | R6 | positions（roleEligible）：roleEligibleKind=cabinet_minister，roleGap=dates |
| 02 | 拉薩羅·卡德納斯（mx-cardenas-lazaro） | cardenas-pacific-commander | 太平洋地區軍隊司令 | 1942–NULL | R6 | positions（roleEligible）：roleEligibleKind=military_commander，roleGap=battle_link |
| 02 | 拉薩羅·卡德納斯（mx-cardenas-lazaro） | cardenas-war-minister-1942 | 國防（戰爭）部長 | NULL–1946 | R6 | positions（roleEligible）：roleEligibleKind=cabinet_minister，roleGap=dates |
| 03 | 安東尼奧·吉內斯塔爾·馬沙多（pt-ginestal-machado） | ginestal-minister-instruction | 教育部長（公共教育部長） | 1921–1922 | R5 | positions |
| 03 | 富蘭克林·德拉諾·羅斯福（us-fdr） | fdr-asst-sec-navy | 海軍助理部長 | 1913–NULL | R5 | positions |
| 05 | 蔣中正（cn-chiang-kai-shek） | chiang-whampoa-commandant | 黃埔軍校校長 | 1924–NULL | R5 | positions；positionKind→military_education |
| 05 | 蔣中正（cn-chiang-kai-shek） | chiang-nre-commander | 北伐軍總司令 | 1926–NULL | R6 | positions（roleEligible）：roleEligibleKind=military_commander，roleGap=regime |
| 06 | 塔拉特帕夏（ot-talat） | interior-minister | 內政大臣 | 1909–NULL | R6 | positions（roleEligible）：roleEligibleKind=cabinet_minister，roleGap=dates+source |
| 06 | 何塞·費利克斯·烏里布魯（ar-uriburu） | army-inspector-general | 陸軍總監 | 1922–NULL | R6 | positions（roleEligible）：roleEligibleKind=military_commander，roleGap=rank |
| 07 | 霍爾洛基·喬巴山（mn-choibalsan） | choibalsan-army-cic-1924 | 人民軍總司令 | 1924–NULL | R6 | positions（roleEligible）：roleEligibleKind=military_commander，roleGap=source |
| 07 | 霍爾洛基·喬巴山（mn-choibalsan） | choibalsan-rural-economy-minister | 農牧經濟部長 | 1931–1936 | R5 | positions |
| 07 | 霍爾洛基·喬巴山（mn-choibalsan） | choibalsan-deputy-pm | 副總理 | 1935–1940 | R5 | positions |
| 07 | 范·赫茨（nl-van-heutsz） | heutsz-chief-general-staff | 總參謀長 | 1897–1899 | R5 | positions |
| 07 | 范·赫茨（nl-van-heutsz） | heutsz-aceh-governor | 亞齊及屬地文武總督 | 1898–1904 | R5 | positions |
| 08 | 霍爾蒂·米克洛什（hu-horthy） | fleet-commander-1918 | 海軍艦隊司令（中將） | 1918–NULL | R6 | positions（roleEligible）：roleEligibleKind=military_commander，roleGap=rank |
| 08 | 霍爾蒂·米克洛什（hu-horthy） | war-minister-1919 | 陸軍（戰爭）部長 | 1919–NULL | R6 | positions（roleEligible）：roleEligibleKind=cabinet_minister，roleGap=dates |
| 08 | 穆罕默德·查希爾·沙阿（af-zahir） | deputy-defence-1932 | 國防部副部長 | 1932–NULL | R5 | positions |
| 08 | 穆罕默德·查希爾·沙阿（af-zahir） | education-1933 | 教育部長 | 1933–NULL | R5 | positions |
| 08 | 禮薩·沙阿·巴勒維（ir-reza） | cossack-brigadier-1918 | 哥薩克旅准將 | 1918–NULL | R5 | positions |
| 08 | 禮薩·沙阿·巴勒維（ir-reza） | war-minister-1921 | 戰爭部長 | 1921–NULL | R6 | positions（roleEligible）：roleEligibleKind=cabinet_minister，roleGap=dates |
| 08 | 波費里奧·迪亞斯（mx-diaz） | brigadier-1861 | 准將 | 1861–NULL | R5 | positions |
| 09 | None（do-trujillo） | natl-police-chief-1924 | 國家警察首長 | 1924–NULL | R5 | positions；positionKind→police |
| 09 | None（do-trujillo） | armed-forces-cic-1928 | 國家武裝部隊總司令 | 1928–NULL | R6 | positions（roleEligible）：roleEligibleKind=military_commander，roleGap=regime |
| 10 | 朱塞佩·莫塔（ch-motta） | head-political-dept | 政治部（外交）主管 | 1920–1940 | R6 | positions（roleEligible）：roleEligibleKind=cabinet_minister，roleGap=regime |
| 10 | 朱塞佩·莫塔（ch-motta） | head-finance-dept | 財政與關稅部主管 | NULL–NULL | R6 | positions（roleEligible）：roleEligibleKind=cabinet_minister，roleGap=dates |
| 10 | 奧古斯托·萊吉亞（pe-leguia） | finance-minister-candamo-pardo | 財政部長（坎達莫、帕爾多政府） | NULL–NULL | R6 | positions（roleEligible）：roleEligibleKind=cabinet_minister，roleGap=dates+source |

## t14Ambiguous 清單（0 筆）
文件 §2 表涵蓋全部 31 筆 t14Overlap，每筆都有明確結論，所以沒有標 t14Ambiguous。以下是有詮釋空間、已在上方規則 8 寫明處理方式的點：① #12 #28 #29「角色*」歸 R6／regime；② #1 未拆段；③ #14 #20 roleGap 命名 `rank`；④ 文件 §1 R6 寫 `roleEligible: "<role_kind>"`，本檔用 true＋roleEligibleKind。

## 統計（詳見 `align-report.json`，含每筆人物 key＋職稱）
- 改名（roleKind→positionKind）：**63** 筆（b01 5、b02 13、b03 9、b04 2、b05 5、b06 4、b07 5、b08 9、b09 3、b10 8）。
- 移成候選角色：**6** 筆（de_facto_leader 6：黨職 5＋黨籍席位 1（b09 薩拉查）；head_of_state 0、head_of_government 0）。各批：b02 2、b03 1、b05 1、b06 1、b09 1。
- T14 套用（31 筆）：移到角色層 **0**（R0–R4 依 role_kind 細分：cabinet_minister 0、military_commander 0、occupation_administrator 0、colonial_governor 0）；R6 標 roleEligible **16**（cabinet_minister 10、military_commander 6；roleGap：dates 9、source 3、regime 3、battle_link 1、rank 2，可重複）；R5 留經歷層 **15**（其中 2 筆改 positionKind：military_education 1、police 1）；t14Ambiguous **0**。依原標記：cabinet 19＝R6 10＋R5 9；general 11＝R6 6＋R5 5；occupation_colonial 1＝R5 1。元首／首腦 0 筆，原因：試跑研究時 verify 已禁止元首／首腦職位，故 positions 本來就幾乎沒有這類項。
- partyPostAmbiguous：**0** 筆（原 b09 一筆已依 Tai 12:47 移走）。
- T14 標記：**31** 筆（cabinet 19、general 11、occupation_colonial 1）。
- verify（對齊檔）：10 批全部 ok，無錯誤。

## 需 Tai 決定的個案
1. ~~**蘇共總書記**（`su-stalin` / `stalin-gensec`）、**國民黨總裁**（`cn-chiang-kai-shek` / `chiang-tsung-tsai`）：標題無法自動判斷，我以個案覆寫為 `de_facto_leader` 候選。黨職是否算「實際掌權者」角色、或留在經歷層為 `party`，請決定。同類的 `cardenas-pnr-president`、`ginestal-nationalist-directorate`（黨主席）、`talat cup-secretary-general` 我**沒**移，理由是當時並非實際掌權者；標準是我主觀判斷。~~ → Tai 2026-11-11 12:12 已決：黨職一律算 de_facto_leader（見規則 4）。
2. **`general` 標記的邊界**：`military_command` 全標 general，其中含非嚴格將領者：黃埔軍校校長、多明尼加國家警察首長（`natl-police-chief-1924`）、陸軍總監等。T14 若只收「將領」，這幾筆要改。
3. **`cabinet` 的邊界**：含海軍助理部長（`fdr-asst-sec-navy`）、副總理（`choibalsan-deputy-pm`）、副部長（`deputy-defence-1932`）、瑞士聯邦部門主管。是否算閣員待 T14。
4. **尚未捕捉的元首／首腦任期**：positions 內若有以非標題形式（如「總統府」、君主的任期）描述的，規則不會抓到；`roleCandidates` 的完整度只涵蓋 positions 現有項目。元首／首腦任期仍依 §16.9 T13 另案處理。
5. ~~**`roleCandidates` 內仍保留原名 `roleKind`**~~ → Tai 2026-11-11 12:12 已決：統一為 `role_kind`，原值改存 `originalPositionKind`（見規則 5）。
6. ~~**薩拉查「議員（天主教中央黨）」**是否算黨職~~ → Tai 2026-11-11 12:47 已決：算黨職（規則 7）。
7. 第 2、3 項（general／cabinet 邊界）→ Tai 2026-11-11 12:47 第 5 項：套用 T14 建議（規則 8）。
