# B3 full v3 batch021：研究（Sonnet，新 session，勿 --resume）

<!-- b3v3-token-2026-11-17 -->
若任務指定了 bioId：只研究那一人，只寫 `data/seed/leaders/b3-trial/full/v3/batch021/people/<bioId>.json`（`person`、`sources`、`rawMap`、`researchedOn`、`policyVersion`、`alignedTo`、`alignNote`、`schemaNote`），不要寫 research.json，不要跑 verify.py 或 check_min.py。抓取一律用下方「抓取與原文」的 fetch_source.py；已有的 sourceKey 不要重抓。禁止 Read／cat 整份 raw。WebFetch 只用於發現網址。

<!-- 範本佔位：021=兩位數批號、- 拉薩羅·卡德納斯｜Lázaro Cárdenas del Río｜01a1aa4a-da74-748f-aea8-7d3802bce69c｜mexico｜首任 1934-12-01｜中（離線推定）｜mexico head_of_government「」1934-12-01～1940-12-01（recordId a16797ba-b80a-4843-b3c5-ddcef0ce73fa）；mexico head_of_state「」1934-12-01～1940-12-01（recordId 77af160a-8dbd-44a9-af1c-3c1e0708755a）
- 馬塞洛·T·德阿爾韋亞爾｜Marcelo Torcuato de Alvear｜42454655-1aae-44f8-a69b-38e14e5b206f｜argentina｜首任 1922-10-12｜中（離線推定）｜argentina head_of_government「Presidente de la Nación Argentina」1922-10-12～1928-10-12（recordId 0cbac751-8bcb-4d3b-9d19-34baded8d29d）；argentina head_of_state「Presidente de la Nación Argentina」1922-10-12～1928-10-12（recordId db9f905f-67b9-4f70-968b-eded4883b30d）
- 穆罕默德·查希爾·沙阿｜Mohammad Zahir Shah｜01a1b4b0-700e-7f42-85f7-aa94c6275d85｜kingdom-of-afghanistan｜首任 1933-11-08｜中（離線推定）｜kingdom-of-afghanistan head_of_state「)」1933-11-08～1945-10-01（recordId 01a1aa96-cf95-72fe-a61f-6a7fe8f6f722）=本批 5 人清單（每人一行：中文名｜原名｜bioId｜地區／政權｜年代｜預估厚薄｜5442 任期與 recordId）、2026-11-15=YYYY-MM-DD、/Users/jack755051/wl-source-cache/b3full-v3/batch021/raw=/tmp/b3full-v3/batch021/raw、data/seed/leaders/b3-trial/full/v3/batch021=data/seed/leaders/b3-trial/full/v3/batch021 -->

授權：Tai 2026-11-11 09:30（Sonnet 查資料、Opus 審查；不寫庫、不 push）、12:12（①先調提示再跑 100 人 ②黨職一律算 de_facto_leader ④候選角色欄位統一 role_kind）、12:47（①黨職維持一律算 de_facto_leader ②薩拉查 1921 議員算黨職 ③同意開跑 100 人 ⑤T14 建議套用）、21:24（全量其餘人物，規格與提示沿用 run100）。你只做本批 3 人的研究，產出 seed 檔。分支 feature/battle-demo-v2（不要切換分支）。

## 本批 3 人（來自 `data/seed/leaders/b3-trial/full/v3/selection-sample.json`，batch="021"）
- 拉薩羅·卡德納斯｜Lázaro Cárdenas del Río｜01a1aa4a-da74-748f-aea8-7d3802bce69c｜mexico｜首任 1934-12-01｜中（離線推定）｜mexico head_of_government「」1934-12-01～1940-12-01（recordId a16797ba-b80a-4843-b3c5-ddcef0ce73fa）；mexico head_of_state「」1934-12-01～1940-12-01（recordId 77af160a-8dbd-44a9-af1c-3c1e0708755a）
- 馬塞洛·T·德阿爾韋亞爾｜Marcelo Torcuato de Alvear｜42454655-1aae-44f8-a69b-38e14e5b206f｜argentina｜首任 1922-10-12｜中（離線推定）｜argentina head_of_government「Presidente de la Nación Argentina」1922-10-12～1928-10-12（recordId 0cbac751-8bcb-4d3b-9d19-34baded8d29d）；argentina head_of_state「Presidente de la Nación Argentina」1922-10-12～1928-10-12（recordId db9f905f-67b9-4f70-968b-eded4883b30d）
- 穆罕默德·查希爾·沙阿｜Mohammad Zahir Shah｜01a1b4b0-700e-7f42-85f7-aa94c6275d85｜kingdom-of-afghanistan｜首任 1933-11-08｜中（離線推定）｜kingdom-of-afghanistan head_of_state「)」1933-11-08～1945-10-01（recordId 01a1aa96-cf95-72fe-a61f-6a7fe8f6f722）

（地區／政權／厚薄是離線推定，可能不準；標「不確定」者以實查為準，並在結尾回覆指出。）

## 必讀（先讀再做）
1. `ARCHITECTURE.md` §16.2、§16.3、§16.3.1、§16.3.2、§16.4 與 T11／T12／T14（用 Grep 找標題，只讀這幾節）。**與 `data/seed/leaders/b3-trial/ARCH_TODO.md` 所列新規則衝突處，以新規則為準**（先讀 ARCH_TODO.md）。
2. `data/seed/leaders/b3-trial/ALIGN.md`（b0b0e0f 對齊格式）與任一 `data/seed/leaders/b3-trial/batch0*/research.aligned.json`（格式範本）。
3. `data/seed/leaders/b3-trial/verify.py`（你的產出必須通過它的對齊檢查）。

## 輸出格式（直接寫 b0b0e0f 對齊格式，不再事後轉換）
- 頂層：`batch`="b3-full-v3-batch021"、`researchedOn`、`policyVersion`="bio-2026-11-v0"、**`alignedTo`="b0b0e0f"**、`schemaNote`、`rawDir`、`rawMap`、`sources`（每筆一個 key，含 title／authors／publisher／published_text／url／archive_url／catalog_id／license_code／grade／gradeBasis）、`people[]`。
- 每人：`key`、`bioId`（照名單）、`name`、`nameZh`、`recordIds`、`thickness`（依實查結果寫厚／中／薄）、`paragraphs`、`positions`、`roleCandidates`、`gaps`、`searchLog`。
- citation 欄位：sourceKey、locator、quote、quoteLang、evidenceNote、accessedOn、grade、datePrecision、claimSpan、policyVersion。
- **positions[]**（一般經歷）：種類欄位叫 `positionKind`（不可用 roleKind）。值參考原 7 種 minister／legislator／military_command／party／diplomat／judicial／other（僅供參考，實作時再定），但**不得**為 head_of_state／head_of_government／de_facto_leader，也**不得為 party**（黨職見下），也不得為任何角色層值（見 T14）；另可用 `police`、`military_education`（T14 邊界個案）。
- **roleCandidates[]**（角色候選）：元首、政府首腦、實際掌權者，以及**所有黨職**都寫在這裡。種類欄位叫 **`role_kind`**（不可用 roleKind／candidateRoleKind），值 ∈ {head_of_state, head_of_government, de_facto_leader, cabinet_minister, military_commander, occupation_administrator, colonial_governor}；每筆必須有 `citations`（照引文規則）、`reason`（非空，說明為何是此角色）、期間、標題（原文＋中文）、organization。
  - **所有黨職一律寫進 roleCandidates，`role_kind=de_facto_leader`**，`t14Rule: "R1"`，reason 寫「Tai 2026-11-11 12:12：黨職一律算 de_facto_leader」（黨主席、總書記、黨魁、黨中央委員會職務等，含統一與進步委員會這類執政組織；不論是否掌權）。**即使與 ARCHITECTURE §16.3.1「party_official 不收」或 de_facto_leader「需來源明說實際掌權」文字衝突，也以此為準**（見 ARCH_TODO.md A1–A2；Tai 12:47 ①）。
  - **職稱或來源明寫以某政黨身分取得的席位**（例：「議員（某黨）」、引文寫 elected as a deputy for 某黨）**也算黨職**，比照 Tai 2026-11-11 12:47「薩拉查 1921 議員算黨職」：寫進 roleCandidates，role_kind=de_facto_leader，`originalPositionKind` 寫原本性質（如 legislator），reason 寫「Tai 2026-11-11 12:47：以政黨身分取得的席位比照黨職（依薩拉查 1921 議員裁決）」。來源只寫「當選」、沒寫以何黨身分 → 不算，照一般 positions。
  - 已在名單 5442 任期內的元首／首腦任期不必重建（在 leader_records）；名單外但來源明寫、落在 1908–1945 的元首／首腦／掌權任期才寫候選。
  - **不明確是否黨職**（例：黨報主編、黨外圍組織職務；以政黨身分取得的席位已不算不明確）→ 不猜：留在 positions，`positionKind` 照實際性質（如 legislator），加 `partyPostAmbiguous: true` 與 `partyPostAmbiguousReason`（說明為何不確定）。
- **T14 R0–R6 研究時即套用**（Tai 2026-11-11 12:47 ⑤「T14 建議套用到試跑資料」；全文見 `data/seed/leaders/b3-trial/T14_RECOMMENDATION.md` §1、§4，格式範本見試跑 `research.aligned.json` 與 `ALIGN.md` 規則 7–9）。**兩層互斥**：一段任期只寫在 roleCandidates 或 positions 其中一處。每段任期依序判斷，**第一條命中就停**：
  - R0 元首／首腦／攝政／代理 → roleCandidates（head_of_state／head_of_government；代理加 `acting: true`）。
  - R1 黨職（含以政黨身分取得的席位，見上）→ roleCandidates，de_facto_leader。
  - R2 佔領／殖民長官：①轄區**最高**行政長官（不是轄區內省／州長）②轄區在系統中是政權或併入地（regimeId 非 NULL）③任期可證明 ≥30 天 → roleCandidates，`occupation_administrator`／`colonial_governor`。
  - R3 閣員：①外交、國防／陸軍／戰爭、財政、內政四部之一（單獨海軍部、空軍部不算；「戰爭兼海軍」算；瑞士部門主管依部門對應）②正職（標題不含副、助理、次、deputy、assistant、vice、adjunto、under-）③任期可證明 ≥90 天 ④政權在系統中 → roleCandidates，`cabinet_minister`。
  - R4 將領：①國家級最高軍職（全軍總司令、參謀總長、軍種總司令；**職位等級須引文明寫**，不推論），或戰區／方面軍司令且至少一筆有日期＋地點＋出處的戰役連結 ②政權在系統中 → roleCandidates，`military_commander`。
  - R5 其他（非四部閣員、副職／助理／次官、副總理、軍校、警察、軍銜、轄區內地方長官、時間窗外）→ positions，加 `t14Rule: "R5"`。
  - R6 類別符合 R2–R4，但門檻無法證明（任一端日期 NULL、精度不足以算出最短任期、來源不足 1 筆 A 或 2 筆獨立 B、regimeId NULL／政權待查證、缺戰役連結、職位等級沒明寫）→ **留 positions**，加 `t14Rule: "R6"`、`roleEligible: true`、`roleEligibleKind`（cabinet_minister／military_commander／occupation_administrator／colonial_governor）、`roleGap`（陣列，值 dates｜source｜regime｜battle_link｜rank）。
  - 共通：時間窗＝與 1908–1945 有交集，窗外一律 R5。「可證明 ≥N 天」＝結束日最早可能值－開始日最晚可能值（year 精度：開始取 12-31、結束取 01-01；month 依此類推；day 照原值；任一端 NULL＝無法證明→R6）。
  - 閣員、將領、佔領殖民長官（positionKind=minister／military_command，或標題含總督／governor 且含殖民／屬地／佔領）留在 positions 時仍加 `t14Overlap`（cabinet／general／occupation_colonial），且**每筆 t14Overlap 都要有 `t14Rule` 與 `t14Reason`**（一句話說明命中哪一條、缺什麼）。進 roleCandidates 的也加 `t14Rule`（R0–R4）。
  - 邊界個案：軍校校長（如黃埔）→ positions，`positionKind: "military_education"`；國家警察首長 → `positionKind: "police"`；兩者 R5。
  - 文件沒涵蓋、判斷不了的 → 不猜：留 positions，加 `t14Ambiguous: true`＋`t14AmbiguousReason`，並在結尾回覆列出。
  - positions 的 positionKind **不得**為任何角色層值（7 種 role_kind）；roleCandidates 不得有 positionKind／roleEligible。

## 規則（全部必守；ARCHITECTURE.md §16.2–§16.4，Tai 2026-11-11 09:30／09:35 定案）
- Q1 戰役／事件只寫進段落正文，不建參與紀錄。
- Q2 每段中文 ≤400 字、英文 ≤800 字元（NFC code point）。段落用自己的話改寫，只寫來源寫到的事；**每個事實句的每個子句（日期、地點、人名、職稱、評語）都要對得到該段某筆 citation 的 quote**，做不到就拆段、刪子句或刪句（試跑審查每批補 20–30 筆引文，本輪要研究者自己補齊）。
- Q3 月／年精度的終點寫下一單位起日（到 1911 年 → 1912-01-01＋year；到 1911 年 5 月 → 1911-06-01＋month）；起點寫該單位起日。半開區間。段落 period 迄點依段內最後一件事定。
- Q4 1908–1945 範圍外的元首／首腦任期只寫正文，不建候選或職位。
- Q5 只有清楚落在 1908–1945、對得到 5442 政權的職位才填 regimeId；其餘 regimeId=null 並填 organization（雙語）。
- Q6 §16.3.1 範圍外的經歷（議員、州長、次官、非四部閣員、非國家級參謀職等）可寫進正文，也可記入 positions（照上方 positionKind／T14 R0–R6 規則）；黨職與 R0–R4 命中者例外，進 roleCandidates。
- Q7 以名簿下一任起日當前任迄日可以，但 evidenceNote 必須寫「依名簿下一任起日推得（推論）」；沒有下一任資料就留空不猜。
- Q8 datePrecision 只在 quote 本身含日期時填。
- Q9 未評等來源（Archontology、rulers.org 類私人彙編；**無具名作者的百科條目，如 Encyclopedia of World Biography 無署名條目；無作者無書目的館藏圖說**）只能放 gap 的 candidateCitations，不能當段落／職位／候選角色出處。出處 grade 只能 A 或 B（A＝國家級傳記辭典、政府／議會／國家圖書館官方頁、人名權威檔；B＝具名作者的機構百科、學術機構傳記、學術出版社專書或期刊論文等；C／X 不收）。
- Q10 同一來源可有多筆 citation，每筆 quote 一句。
- 引文 quote：NFC ≤80 字元、逐字、不截斷不轉述，必須逐字出現在已抓原文；取完整語意片段，不可截掉受詞或謂語。
- gapKind：not_found／conflict／identity_uncertain。conflict 只用於**兩份已抓來源**互相矛盾（單一來源 vs 庫值、只有檢索摘要 → not_found）。原文主語與常識不合時不替原文補主語。
- **不可編造**；查不到一律寫 gap（待查證）。
- 不用 Wikipedia／Wikidata／百度（也不可當線索網址寫進檔案）；不用 `curl -k`／`--insecure`；不登入；遇防機器人驗證（captcha、403 挑戰頁、Anubis／Cloudflare）不繞過，只可改用同一權威資料的官方鏡像（例：GND → lobid.org），並記入 searchLog。
- 絕不寫庫、不連任何資料庫（bioId／recordId 已在名單）；不 git add／commit／push；不改 ARCHITECTURE.md、程式、API、前端、b3-sample、b3-trial 既有批次；不重啟任何服務；只寫 `data/seed/leaders/b3-trial/full/v3/batch021/` 與 /tmp。

## 最低標準（Tai 2026-11-11 22:02；本批每人都適用，優先於下方「1 個 A／B 寫 1 段」「1–6 段」）
1. **篇幅**：每人中文（`body.zh-Hant`）**至少 3 段、合計至少 300 字**（NFC 後去空白的字元數）；英文段落一一對應。
2. **任期**：positions 與 roleCandidates 的每一筆都要有 `period.start` 與 `period.end`，並有 quote 含該日期（或年／月）的 citation。
   - 迄日查不到 → 該筆照寫 start，另加 gap：target=`position:<key>`（角色 `role:<key>`），gapKind=not_found，note 以「待查證：缺迄日；」開頭並寫已查來源。
   - 起日查不到 → 不寫入 positions／roleCandidates，改寫同格式 gap（note 以「待查證：缺起日；」開頭）。
3. **不足時先擴大搜尋**（官方／議會、國家級傳記辭典、權威檔、學術出版），不可用無出處的內容、重複句、空泛評語或常識補述湊字數；每個事實子句仍要對得到 citation（Q2）。
4. **盡力後仍不足**：照實寫，另加一筆 gap：target=`paragraph:length`，gapKind=not_found，note 以「篇幅不足：」開頭，寫目前段數／字數與已查過的來源類型。
5. flags 含 **major★** 者：另套下方「主要領導人加強規格」。

## 主要領導人加強規格（World Line 主管 2026-11-11 21:55，Tai 授權範圍；只適用 flags 含 major★ 者，優先於下方同名規則）
major★ 者是 1908–1945 主要領導人（Tai 2026-11-11 21:25），**不適用「厚人物 2–4 個來源即可」**。
1. **最低搜尋量（取代下方「最低嘗試」）**：每人至少 **5 種**來源類型、至少 **15 次**查詢（原文語言至少 4 次）、至少用 tools/b3v3/fetch_source.py 抓取 **6 個**候選頁；並至少取得 **3 個**可抓原文的 A／B 來源，其中至少 **1 個 A**（官方／議會／國家級傳記辭典／權威檔）。全部寫進 searchLog。
2. **指定來源（先查這些，查不到或被擋也要寫進 searchLog）**：
   - 溫斯頓·邱吉爾（Winston Churchill）：英國：UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…，A，歷任職位與起訖日）、GOV.UK Past Prime Ministers（A）、The London Gazette 任命公告（thegazette.co.uk，A）、Oxford DNB 公開摘要（A）、Churchill Archive Centre（Churchill College, Cambridge）機構傳記（B）、LoC／VIAF 權威檔
   - 阿道夫·希特勒（Adolf Hitler）：德國：Deutsche Biographie（NDB，A）、GND／lobid.org（A）、Bundesarchiv（A）、Reichstag-Abgeordnetendatenbank／Reichstagsprotokolle（BSB，A）、DHM LeMO（B）、Treccani（B）
   - 約瑟夫·史達林（Иосиф Виссарионович Сталин (Джугашвили)）：蘇聯：Президентская библиотека им. Ельцина（prlib.ru，A）、Большая российская энциклопедия（bigenc.ru，具名條目 B）、РГАСПИ 檔案說明（rgaspi.org，A）、DHM LeMO（B）、Treccani（B）、LoC 權威檔
   - 富蘭克林·德拉諾·羅斯福（Franklin D. Roosevelt）：美國：whitehouse.gov 歷任總統頁（A）、Biographical Directory of the U.S. Congress（bioguide.congress.gov，A）、FDR Presidential Library（NARA，fdrlibrary.org，A）、history.state.gov（A）、Miller Center（B）
   - 貝尼托·墨索里尼（Benito Mussolini）：義大利：Treccani Dizionario Biografico degli Italiani（A）、Camera dei deputati Portale storico（storia.camera.it，A）、Senato della Repubblica、Gazzetta Ufficiale（A）
   - 昭和天皇（裕仁）（昭和天皇（裕仁））：日本：宮内庁（kunaicho.go.jp，A）、国立国会図書館（NDL 権威・近代日本人の肖像，A）、アジア歴史資料センター（jacar.go.jp，A）、防衛研究所（nids.mod.go.jp，A）
   - 東條英機（東條英機）：日本：首相官邸 歴代内閣（kantei.go.jp，A）、国立国会図書館 近代日本人の肖像（A）、アジア歴史資料センター（A）、防衛研究所（A）、国立公文書館（A）
   - 蔣中正（Jiǎng Zhōngzhèng）：中華民國：國史館（drnh.gov.tw，A）、總統府（president.gov.tw，A）、中央研究院近代史研究所（mh.sinica.edu.tw，A）、國家圖書館（A）、中正紀念堂（A）
   - 弗拉基米爾·列寧（Владимир Ильич Ленин (Ульянов)）：蘇聯：Президентская библиотека（A）、Большая российская энциклопедия（具名 B）、РГАСПИ（A）、DHM LeMO（B）、Treccani（B）
   - 威廉二世（Wilhelm II）：德國：Deutsche Biographie（NDB，A）、GND／lobid.org（A）、Bundesarchiv（A）、DHM LeMO（B）、Reichsgesetzblatt（官方公報，A）
   - 法蘭茲·約瑟夫一世（Franz Joseph I）：奧匈：Österreichisches Biographisches Lexikon（biographien.ac.at，A）、Österreichische Nationalbibliothek（A）、Parlament Österreich（parlament.gv.at，A）、Deutsche Biographie（A）
   - 尼古拉二世（Nicholas II）：俄羅斯帝國：Президентская библиотека（A）、Большая российская энциклопедия（具名 B）、ГАРФ 檔案說明（A）、1914-1918-online（具名 B）
   - 大衛·勞合·喬治（David Lloyd George）：英國：Historic Hansard 人物頁（A）、GOV.UK Past Prime Ministers（A）、London Gazette（A）、Oxford DNB 公開摘要（A）、National Library of Wales 威爾斯傳記辭典 Dictionary of Welsh Biography（biography.wales，A）
   - 內維爾·張伯倫（Neville Chamberlain）：英國：Historic Hansard 人物頁（A）、GOV.UK Past Prime Ministers（A）、London Gazette（A）、Oxford DNB 公開摘要（A）、University of Birmingham Cadbury Research Library 的 Chamberlain Papers 說明（B）
   - 伍德羅·威爾遜（Woodrow Wilson）：美國：whitehouse.gov（A）、Woodrow Wilson Presidential Library（B）、history.state.gov（A）、Miller Center（B）、Princeton University 校長名錄（B）、New Jersey 州長名錄（A）
   - 喬治·克里蒙梭（Georges Clemenceau）：法國：Assemblée nationale Sycomore（A）、Sénat 前參議員名錄（senat.fr，A）、BnF data（A）、Journal officiel（Gallica，A）
   - 法蘭西斯科·佛朗哥（Francisco Franco Bahamonde）：西班牙：Real Academia de la Historia DB~e（dbe.rah.es，A）、Congreso de los Diputados／Cortes 歷史資料（A）、Boletín Oficial del Estado（boe.es，A）、Biblioteca Nacional de España 權威檔（A）
   - 穆斯塔法·凱末爾·阿塔圖克（Mustafa Kemal Atatürk）：土耳其：TBMM（tbmm.gov.tr，A）、Cumhurbaşkanlığı（tccb.gov.tr，A）、Atatürk Araştırma Merkezi（atam.gov.tr，A）、TDV İslâm Ansiklopedisi（具名 B）
3. **職位任期**：positions 與 roleCandidates 的每一筆都要有 `period.start` 與 `period.end`，並有 quote 含該日期（或年／月）的 citation 支撐（可來自不同來源，各自是一筆 citation）。
   - 迄日查不到（含在職至死亡但來源沒寫）→ 該筆照寫 start，另加一筆 gap：target=`position:<key>`（角色用 `role:<key>`），gapKind=not_found，note 以「待查證：缺迄日；」開頭並寫已查過哪些來源。
   - 起日查不到 → 不寫入 positions／roleCandidates，改寫同樣格式的 gap（note 以「待查證：缺起日；」開頭）。
   - 1908–1945 窗內的主要職位（元首／首腦、四部閣員、黨職、國家級軍職）務必逐一查任期；窗外重要職位可只寫正文。

## 搜尋策略（每人都照做；薄人物必須做完「最低嘗試」才可放棄）
依序嘗試，查到 A／B 就可停止往下（厚人物 2–4 個來源即可，不要逐頁瀏覽）：
1. **權威檔**（確認身分、生卒、原文姓名寫法，兼找連結）：LoC Name Authority（id.loc.gov）、VIAF（viaf.org）、GND（d-nb.info／lobid.org）、BnF（data.bnf.fr）、NDL（id.ndl.go.jp）、各國國家圖書館目錄。用權威檔的原文姓名與異寫再搜。
2. **國家級傳記辭典／官方頁**（A）：
   - 歐洲：Deutsche Biographie（NDB/ADB）、Historisches Lexikon der Schweiz（hls-dhs-dss.ch）、Svenskt biografiskt lexikon（riksarkivet.se/sbl）、Norsk biografisk leksikon（nbl.snl.no）、Dansk Biografisk Leksikon（lex.dk）、Kansallisbiografia／Biografiakeskus（Finland）、Real Academia de la Historia DB~e（dbe.rah.es）、Dizionario Biografico degli Italiani（treccani.it）、Österreichisches Biographisches Lexikon（biographien.ac.at）、Oxford DNB 公開摘要、Dictionary of Irish Biography（dib.ie）、Polski Słownik Biograficzny 相關官方頁、各國議會議員名錄（例：Bundestag／Reichstag 資料庫、Assemblée nationale Sycomore、Sejm、Eduskunta、Stortinget、Riksdagen）、總統府／政府官網的歷任名單。
   - 東歐／前蘇聯：各國議會與國家圖書館人名資料、Encyclopedia of Ukraine（encyclopediaofukraine.com，具名條目 B）、Internet Encyclopedia of Ukraine 具名作者條目。
   - 東亞：中央研究院近代史研究所（近史所人物資料、檔案館）、國史館（國史館館刊、總統副總統文物）、國家圖書館（臺灣）、中國國家圖書館權威檔、日本 国立国会図書館「近代日本人の肖像」（ndl.go.jp/portrait）、国立公文書館アジア歴史資料センター（jacar.go.jp）。
   - 西亞／北非：Encyclopaedia Iranica（iranicaonline.org，具名條目 B）、Encyclopaedia of Islam 公開摘要、TBMM（土耳其大國民議會）官網、İslâm Ansiklopedisi（islamansiklopedisi.org.tr，TDV 具名條目 B）、各國政府歷任名單。
   - 拉丁美洲：各國總統府／國會官網歷任總統頁、Biblioteca Nacional 權威檔、Real Academia de la Historia DB~e（含拉美人物）、學術機構傳記（例：Fundação Getulio Vargas CPDOC 的 DHBB，巴西；Biblioteca del Congreso Nacional de Chile 的 Reseñas Biográficas）。
   - 南亞／東南亞：國家檔案館、Royal Collection／政府官網、Oxford DNB 公開摘要。
3. **具名作者機構百科**（B）：Britannica（具名作者或署名編者條目）、Encyclopedia of the Modern Middle East 具名條目、Treccani Enciclopedia 具名條目、1914-1918-online（具名作者）、Store norske leksikon 具名條目、各大學／研究機構的人物傳記頁。
4. **條約、法律彙編與國際組織文件**（主要供職位與日期）：國聯文件（League of Nations Treaty Series、UN Archives Geneva 公開目錄）、聯合國文件、各國政府公報（Gaceta／Journal officiel／Reichsgesetzblatt／Diário do Governo 等官方數位化版本）、議會紀錄。
5. **學術出版社與期刊**：出版社官方書目頁或開放取用章節（Cambridge、Oxford、Brill、De Gruyter、大學出版社）、JSTOR／Persée／OpenEdition／CEEOL 公開摘要頁。只引用已抓原文中逐字出現的句子。

查詢方式：
- 每人至少用 **原文語言姓名**（含權威檔列出的異寫、轉寫變體，例：Talat／Talât／Tal'at；Duan Qirui／段祺瑞／Tuan Ch'i-jui；Faisal／Feisal／Fayṣal）與 **中文／英文名** 各查一次；中文、日文、阿拉伯文、斯拉夫語人物必須用原文字查。
- 某站 403／挑戰頁 → 記錄後換同類來源（例：Britannica 擋 → 換國家辭典或 Iranica／Treccani），不要卡在同一站。

**最低嘗試（放棄前必須做完，才可寫 0 段）**：
- 至少 **4 種不同來源類型**（上列 1–5 類中至少 4 類），且
- 至少 **8 次查詢**（WebSearch 或站內搜尋，含原文語言至少 2 次），且
- 至少用 tools/b3v3/fetch_source.py 抓取 **3 個**候選頁。
- 每次嘗試都寫進該人的 `searchLog[]`：`{"step": n, "sourceType": "authority|national_dictionary|official|named_encyclopedia|treaty_law|academic|other", "query": "…", "url": "…或null", "result": "found_A|found_B|unrated|not_relevant|blocked_403|challenge_page|no_result", "note": "…"}`（不放 Wikipedia／Wikidata／百度網址）。

**寫作門檻**：
- 有 **1 個 A 或 B** 來源可抓原文 → 至少寫 1 段「生平概略」（只寫該來源寫到的事），其餘寫 gap（待查證）。
- 只有未評等來源 → 0 段，引文放 gap 的 candidateCitations，gap note 說明需要哪類來源。
- 確實查無 → 0 段，gap note 摘要 searchLog（嘗試了哪些來源類型、被擋的網站），讓下一輪能接著查。

## 抓取與原文（引文核對的依據）
- 用 WebSearch／WebFetch **只做發現**（找候選 URL）。引文必須來自已存的 .txt。**禁止** Read／cat／head／sed 整份 raw 檔，**禁止**把整頁貼進上下文或工具參數。
- 先看已抓過的來源，已有的 sourceKey **不要重抓**：`python3 -I tools/b3v3/fetch_source.py status --rawdir /Users/jack755051/wl-source-cache/b3full-v3/batch021/raw --rawmap data/seed/leaders/b3-trial/full/v3/batch021/rawmap.json`
- 抓新頁（工具內建 curl、不加 -k、UA 為 Mozilla/5.0；只印短摘要與關鍵字命中的段落）：`python3 -I tools/b3v3/fetch_source.py fetch --rawdir /Users/jack755051/wl-source-cache/b3full-v3/batch021/raw --rawmap data/seed/leaders/b3-trial/full/v3/batch021/rawmap.json --source-key <sourceKey> --url <url> --keywords '<姓名|原文姓名|生卒年|職稱>'`
- 抄 quote 前只用 lookup，不要打開整檔：`python3 -I tools/b3v3/fetch_source.py lookup --rawdir /Users/jack755051/wl-source-cache/b3full-v3/batch021/raw --rawmap data/seed/leaders/b3-trial/full/v3/batch021/rawmap.json --source-key <sourceKey> --keywords '<想核對的原文片段>'`
- 每個 sourceKey 對一個 .txt。rawmap.json 由 fetch 維護（單人檔也可帶 rawMap）。research.json 頂層填 `"rawDir": "/Users/jack755051/wl-source-cache/b3full-v3/batch021/raw"`、`"rawMap": "rawmap.json"`。
- 原文不進版控。quote 必須是 lookup 印出的那段裡的逐字片段，不要從 WebFetch 的摘要複製。Cloudflare／Anubis／403：工具會放棄，記入 searchLog 後換站；不要加 `-k`，不要用 Wayback 代替。

## 產出
- `data/seed/leaders/b3-trial/full/v3/batch021/research.json`（researchedOn=2026-11-15）。
- 自檢改由工作流執行（verify.py 必須 ok 且 rawChecked=true；check_min.py 固定寫同目錄 `check_min-report.json`）。你不要跑這兩支，也不要為了自檢 Read 原文。只有在沒有工作流、且你寫的是整份 research.json 時才自己跑；不 ok 就修到 ok（修不了的改成 gap 或刪掉，不可放寬規則、不可改 verify.py）。
- 每人視資料厚薄寫 1–6 段；職位與候選角色以來源明寫起訖者為主。
- 結尾回覆：每人段落／職位／候選角色／缺漏數、searchLog 筆數、用到的來源網域、推定屬性與實查不符處、未解問題；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`（verify 不 ok 或有違規才寫 fail）。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。

上述檔首的 2026-11-17 token 節流優先於本文其餘句子，包含文末「優先於上文」的舊追加。
