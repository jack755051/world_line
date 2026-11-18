# B3 豐富生平段落：樣本 5 人（2026-11-11）

> 依據：ARCHITECTURE.md §16（§16.2 段落、§16.3 職位、§16.4 出處／缺漏、§16.7 B3、§16.9.1 決議）與業務憲法 §1、I5、I6。
> 授權：Tai 2026-11-11 08:39（Asia/Taipei）在 World Line 主管聊天中同意開始 B3 樣本。
> 範圍：只在本目錄新增檔案。**沒有寫庫**（5442 只用 `default_transaction_read_only=on` 做 SELECT），沒改程式、API、前端、ARCHITECTURE.md，沒重啟任何服務。

## 開工三問

| 問題 | 回答 |
|---|---|
| 已做過嗎？ | 沒有。`data/seed/leaders/b3-sample/` 原本不存在；§16.7 的 B3（段落／職位表）尚未建表；`leader_bio_paragraphs`、`person_positions` 在程式與 DB 都沒有。B1、B2、80 字引文已完成（§16.7.1–16.7.5），本樣本沿用它們的 citation 欄位與 80 字規則。 |
| 衝突嗎？ | (1) §14.0-3「戰役先不做」、T5 未決：戰役或事件只寫進段落正文，**不建 `person_event_participations`**（那是 B4）。(2) T3：開工時未決；工作期間 HEAD 新增 `e41a78c`（§16.3.1，Tai 2026-11-11 09:11 已決人物範圍與 role_kind）。§16.3.1 寫明 `person_roles` 與 `person_positions` 的分工「未定」、16.3 原文未改，所以樣本的 `positions` 仍照 §16.3 結構與 7 種值域，並在下方「與 §16.3.1 的對照」列出差異，不自行合併兩套。(3) T2／Q5 未決：只套硬性排除層（`bio-2026-11-v0`），不套白名單。(4) I6：本樣本是 seed，不進 DB；查不到 A／B 來源的內容只記 gaps，不寫進正文。(5) 同分支另一個 Claude Code 在改 API 與彈窗：本次只動本目錄，commit 只含本目錄。 |
| 如何驗收？ | `verify.py` 離線檢查（不連 DB、不連網）：引文 NFC ≤ 80 字、逐字出現在當天抓下的原文；每段落、職位至少 1 筆 A／B citation；硬性排除網域；中文正文 ≤ 400 字；role_kind 不得為元首／首腦；gap 的 target／kind 格式。結果在 `verify-report.json`：**ok，0 錯誤；220 筆引文，最長 79 字**。commit 前確認 `git diff --cached --name-only` 只有本目錄的檔案。 |

## 檔案

| 檔案 | 內容 |
|---|---|
| `research.json` | 樣本本體。`people[]` 每人有 `paragraphs`（§16.2）、`positions`（§16.3）、`gaps`（§16.4.2）；citation 欄位照 §16.4.1（`locator`、`quote`、`quoteLang`、`evidenceNote`、`accessedOn`、`grade`、`datePrecision`、`claimSpan`、`policyVersion`）。來源集中在頂層 `sources`，用 `sourceKey` 對應（代表 §16.4.1 的 `source_id → sources`）。 |
| `verify.py` | 離線檢查腳本（上述規則）。 |
| `verify-report.json` | 檢查結果，以及各原始頁面文字檔的 sha256。原始頁面不進版控（著作權），存在本機 `/tmp/b3raw/`。 |
| `SUMMARY.md` | 本文件。 |

## 人物與段落

選人原則：希特勒、邱吉爾（指定），另外 3 位的地區、角色、資料厚薄都不同，而且都是 5442 已有的人物。

| 人物 | bio_id（5442） | 地區／角色 | 資料量 | 段落 | 職位 | 缺漏 | citation |
|---|---|---|---|---|---|---|---|
| 阿道夫·希特勒 | `01a19f15-35f4-7d9a-847a-aeccc98305ec` | 歐洲／獨裁者 | 厚 | 6 | 4 | 2 | 67 |
| 溫斯頓·邱吉爾 | **無有效 bio**（見下） | 歐洲／議會制首相 | 厚 | 6 | 15 | 3 | 66 |
| 東條英機 | `62241525-b2f1-4931-bfb3-30ecf9dd3094` | 東亞／軍人首相 | 中 | 4 | 10 | 3 | 33 |
| 熱圖利奧·瓦加斯 | `1b13259b-f739-4d2e-b0a7-693a20e1412f` | 拉丁美洲／總統 | 中厚 | 5 | 6 | 2 | 48 |
| 納旺道爾吉·扎丹巴 | `01a1c446-a421-72a6-8d95-7c0372400146` | 內亞／一日元首 | **很薄** | 1 | 0 | 3 | 6 |
| **合計** | | | | **22** | **35** | **13** | **220** |

**邱吉爾的 DB 狀態**：5442 只有 3 筆已撤回的測試種子 bio（`01a19efa-758c-718a-b1ec-27916469f239` 等，撤回原因「測試種子，未經考證」）和 1 筆已撤回任期（`01a19efa-769a-7615-9705-89c66d803905`）。所以 `bioId` 留 null、`relatedRecordIds` 留空。1940 年英國首相在 5442 沒有任何有效的 `leader_records`。

### 各段與出處

| 人物 | 段 | 標題 | 期間（半開） | 來源（等級） |
|---|---|---|---|---|
| 希特勒 | 1 | 早年：林茨與維也納 | 1889-04-20 – 1913-05-24 | NDB 1972 (A)、LeMO (B) |
| | 2 | 第一次世界大戰與國防軍 | 1914-08-16 – 1920-04-01 | NDB 1972 (A)、LeMO (B) |
| | 3 | 進入政黨與慕尼黑政變 | 1919-09-12 – 1924-12-21 | NDB 1972、NDB-online (A)、LeMO (B) |
| | 4 | 重建黨與選舉崛起 | 1925-02-27 – 1933-01-30 | 同上 |
| | 5 | 總理、元首與戰前擴張 | 1933-01-30 – 1939-09-01 | NDB 1972 (A)、LeMO (B) |
| | 6 | 第二次世界大戰與死亡 | 1939-09-01 – 1945-05-01 | NDB 1972 (A)、LeMO (B) |
| 邱吉爾 | 1 | 出身與從軍 | 1874-11-30 – 1900-10-01 | GOV.UK (A)、Nobel (B) |
| | 2 | 進入下議院與自由黨內閣 | 1900-10-01 – 1911（年） | GOV.UK、Hansard (A) |
| | 3 | 海軍大臣與第一次世界大戰 | 1911（年） – 1918（年） | GOV.UK、Hansard (A) |
| | 4 | 戰間期 | 1919（年） – 1939（年） | GOV.UK、Hansard (A) |
| | 5 | 第二次世界大戰：海軍大臣與首相 | 1939（年） – 1945-07-26 | GOV.UK、Hansard (A)、Nobel (B) |
| | 6 | 戰後、第二次組閣與晚年 | 1945-07-26 – 1965-01-25 | GOV.UK、Hansard (A)、Nobel (B) |
| 東條 | 1 | 出身與軍事教育 | 1884-12-30 – （迄未知） | NDL (A) |
| | 2 | 關東軍參謀長至陸軍大臣 | 1937（年） – 1941-10-18 | NDL、首相官邸 038／039 (A) |
| | 3 | 首相任內 | 1941-10-18 – 1944-07-22 | NDL、首相官邸 040 (A) |
| | 4 | 戰敗後與東京審判 | 1945（年） – 1948-12-24 | NDL (A) |
| 瓦加斯 | 1 | 出生與早年 | （起：來源矛盾） – 1909（年） | CPDOC、總統府 (A) |
| | 2 | 州與聯邦政壇 | 1909（年） – 1930-11-03 | 總統府 (A) |
| | 3 | 臨時政府與憲政時期 | 1930-11-03 – 1937-11-10 | 總統府 (A) |
| | 4 | 新國家體制與第二次世界大戰 | 1937-11-10 – 1945-10-30 | 總統府 (A) |
| | 5 | 參議員、第二任總統與死亡 | 1946（年） – 1954-08-25 | 總統府 (A) |
| 扎丹巴 | 1 | 生平概略 | 1900（年） – 1939（年） | LoC、GND (A) |

每段都寫了生平事蹟、職位任期、經歷的戰役或事件（例：希特勒段 2 的西線作戰、段 3 的慕尼黑政變；邱吉爾段 3 的加里波利戰役；東條段 3 的對美英開戰與翼贊選舉；瓦加斯段 3、4 的 1932 立憲革命、1942 對軸心國宣戰與 1944 遠征軍赴義）。事件只寫在正文，沒有建參與紀錄（見待決 Q1）。

## 來源清單（全部存取日 2026-11-11；curl 未用 -k、未登入；不用 Wikipedia）

| sourceKey | 來源 | URL | 等級 | 評等理由 |
|---|---|---|---|---|
| ndb1972-hitler | Fest, „Hitler, Adolf“, NDB 9 (1972) S. 250-266 | https://www.deutsche-biographie.de/gnd118551655.html#ndbcontent | A | 國家級傳記辭典 |
| ndbonline-hitler | Pyta, „Hitler, Adolf“, NDB-online 2024-07-01 | https://www.deutsche-biographie.de/gnd118551655.html#dbocontent | A | 國家級傳記辭典 |
| lemo-hitler | Wosnitzka, LeMO（德國歷史博物館），1998 | https://www.dhm.de/lemo/biografie/adolf-hitler | B | 具名作者的機構百科條目 |
| govuk-churchill | GOV.UK, History of Sir Winston Churchill | https://www.gov.uk/government/history/past-prime-ministers/winston-churchill | A | 政府官方傳記頁 |
| hansard-churchill | UK Parliament, Historic Hansard 人物頁 | https://api.parliament.uk/historic-hansard/people/mr-winston-churchill/index.html | A | 議會官方紀錄 |
| nobel-churchill | Nobel Foundation, Churchill – Biographical | https://www.nobelprize.org/prizes/literature/1953/churchill/biographical/ | B | 機構傳記、無具名作者，保守評 B |
| ndl-tojo | 国立国会図書館「近代日本人の肖像」 | https://www.ndl.go.jp/portrait/datas/142/ | A | 國家圖書館官方解說 |
| kantei-038／039／040 | 首相官邸「歴代内閣」第 38、39、40 代 | https://www.kantei.go.jp/jp/rekidainaikaku/038.html 等 | A | 政府官方頁 |
| govbr-vargas | 巴西總統府 Biblioteca da Presidência（出處：Arquivo Nacional） | https://www.gov.br/secretariageral/pt-br/centrais-de-conteudo/biblioteca-da-pr/galeria-dos-ex-presidentes/Vargas/biografia-completa | A | 政府官方傳記頁 |
| cpdoc-vargas | FGV CPDOC《巴西歷史傳記辭典》 | https://www18.fgv.br/cpdoc/acervo/dicionarios/verbete-biografico/getulio-dornelles-vargas | A | 國家級傳記辭典 |
| loc-jadambaa | LoC Name Authority no2010034324 | https://id.loc.gov/authorities/names/no2010034324.json | A | 人名權威檔（HTML 頁回 403，改取同筆 JSON） |
| gnd-jadambaa | GND 1115681419（經 hbz lobid） | https://lobid.org/gnd/1115681419.json | A | 人名權威檔（d-nb.info 有防機器人驗證，未繞過） |
| archon-jadambaa | Archontology.org | https://www.archontology.org/nations/mongolia/00_1924_92_td_s.php | 未評等 | 無具名作者的私人彙編，只當缺漏候選，不當段落出處 |

## 待查證項目（gaps，共 13 筆）

| 人物 | target | 種類 | 說明 |
|---|---|---|---|
| 希特勒 | paragraph:rise-1925-1933 | conflict | 杜塞道夫工業俱樂部演講：NDB 1972 作 27.1.1932，LeMO 作 26.1.1932。正文不寫這件事 |
| 希特勒 | position:hitler-wehrmacht-supreme | conflict | 國防軍最高統帥起日：NDB-online 作 2.8.1934；NDB 1972 與 LeMO 記 4.2.1938 才接掌 Oberbefehl。起日留空 |
| 邱吉爾 | paragraph:interwar-1919-1939 | conflict | gov.uk 說 1929 年「lost his seat」；Hansard 記埃平選區 1924–1945 連續在任。正文不寫失去議席 |
| 邱吉爾 | position:churchill-chancellor | not_found | 財政大臣迄日 |
| 邱吉爾 | position:churchill-first-lord-1939 | not_found | 1939 年再任海軍大臣的起訖日 |
| 東條 | paragraph:early-career | not_found | 1884–1937 的軍歷細節與年份 |
| 東條 | position:tojo-aviation-inspector | not_found | 航空總監兼航空本部長起訖 |
| 東條 | position:tojo-army-minister | not_found | 陸軍大臣卸任日 |
| 瓦加斯 | paragraph:birth-early-years | conflict | 出生年：CPDOC 1882、總統府 1883。段落起日留空 |
| 瓦加斯 | position:vargas-rs-president | not_found | 南大河州主席卸任日 |
| 扎丹巴 | paragraph:1924-great-khural-chair | not_found | 1924 年第一屆國家大呼拉爾主席、通過首部憲法：官方憲法原文 legalinfo.mn 連線逾時，沒有 A／B 來源可開，**正文不寫** |
| 扎丹巴 | position:1920s-ministries | not_found | LoC 只寫「1920 年代在數個部會任高職」，沒有部會名稱與起訖 |
| 扎丹巴 | paragraph:death-circumstances | not_found | 死亡日期、地點、經過 |

職位中有 5 項完整職銜待查證：邱吉爾的 Under-Secretary（1906–08）、Minister（1917）、Secretary of State（1919–21），Hansard 都沒寫部門，`title` 照原文；evidenceNote 已標註。

順帶看到、但不在本次範圍（沒有處理）：
- 瓦加斯 DB `birthDate` 為 1882，來源有矛盾，但 `leader_bio_gaps` 沒有對應列。
- 瓦加斯 `leader_records` 最後一任迄日是 1945-10-01（看起來是被地圖範圍截掉），總統府記被推翻日為 1945-10-29。
- 希特勒 bio 的欄位 citation 在 5442 是 0 筆（出處只在 `field_sources` 文字欄）。
- 扎丹巴的 summary 仍靠 iKon.mn（新聞網站）。

## 待決問題（§16 沒定義或定義不清，本次沒有自創欄位）

| # | 問題 | 本次暫行做法 |
|---|---|---|
| Q1 | 段落提到的戰役或事件要不要結構化？`person_event_participations` 屬 B4，需 T5 解禁與 D13 定案 | 只寫在正文，沒有建參與紀錄 |
| Q2 | 「段落 ≤ 400 字」對英文怎麼算（字元或詞）？本樣本中文都在 400 字內（最長 241），但英文 22 段有 13 段超過 400 字元（最長 808 字元／136 詞） | 中文判 ≤ 400；英文只記錄數字不判錯 |
| Q3 | 年精度的半開區間終點怎麼表示（`1911-01-01`＋year 會把 1911 年本身排除在外） | 沿用 gap-830 的 `YYYY-01-01`＋precision |
| Q4 | 元首／首腦任期在 1908–1945 之外（邱吉爾 1951–55、瓦加斯 1951–54）該放哪裡？§16.3 禁止放進 `person_positions`，而 `leader_records` 是地圖用、只收範圍內 | 只寫在段落正文，沒有建職位 |
| Q5 | `regime_id` 的對應規則：超出 1908–1945 的職位、跨政權改名（英國 1922 前後兩個 regime）、黨職 | 只有明確落在範圍內的才填（德、日、巴西）；邱吉爾全部填 null＋organization |
| Q6 | `person_positions`（§16.3，7 種值域）與 `person_roles`（§16.3.1，T3 已決）的分工：樣本裡的參謀長、次官、州長、議員、議會榮銜在 16.3.1 沒有對應或屬「不收」類別，還能放進生平的「經歷」嗎？ | 照 §16.3 放進 `positions`（military_command／other／other／legislator／other），evidenceNote 標註；對照見下節 |
| Q7 | 以閣僚名簿「下一任起日」當前任迄日，算直接讀取還是推論？ | 東條的內相、外相、文相 4 項採用，並在 evidenceNote 標明；其他沒有下一任的留空 |
| Q8 | 庫裡沒有有效 bio 的人（邱吉爾）能不能做段落？B3 寫入需要 `bio_id` | 樣本照做，`bioId` 留 null；正式寫入前要先依 gap-830 流程建立有效 bio |
| Q9 | 未評等來源（Archontology）能不能當缺漏的候選證據？ | 只放在 gap 的 candidateCitations，不當段落出處 |
| Q10 | 同一段可以有多筆來自同一來源、不同句子的 citation 嗎？（§16.4.1 沒有禁止） | 可以，每筆一句 |

## 與 §16.3.1（Tai 2026-11-11 09:11 決議）的對照

這是開工後才進 HEAD 的決議（`e41a78c`）。樣本資料沒有改成 16.3.1 的值域，原因是 16.3.1 明寫「與 `leader_records`、`person_positions` 的分工：未定」。以下只是對照，不是資料：

| 樣本職位 | §16.3 值（樣本用） | 16.3.1 可能對應 | 備註 |
|---|---|---|---|
| 希特勒 NSDAP 主席（1921、1925–45） | party | `de_facto_leader`？ | 16.3.1 要求 A／B 來源明說「實際掌權」；NDB-online 寫「Parteivorsitzender mit diktatorischen Vollmachten」，是否算「實際掌權」待判 |
| 希特勒 國防軍最高統帥、陸軍總司令 | military_command | `military_commander` | 國家級最高軍職，符合將領門檻 |
| 東條 參謀總長（1944） | military_command | `military_commander` | 同上 |
| 東條 關東軍參謀長 | military_command | `military_commander`？ | 方面軍參謀長不在 16.3.1 列舉內（列舉的是參謀總長、軍種總司令、方面軍司令） |
| 東條 陸軍大臣、內務大臣 | minister | `cabinet_minister` | 四部之一，任期 ≥ 90 天 |
| 東條 外務（16 天）、文部、商工、軍需大臣 | minister | 不符 | 外務任期 < 90 天；文部、商工、軍需不在四部 |
| 邱吉爾 內政大臣、財政大臣、國防大臣、海軍大臣 | minister | `cabinet_minister`（前三者）／不符（海軍） | 內政、財政、國防在四部；海軍大臣不在 |
| 瓦加斯 財政部長（1926-11 – 1927-12） | minister | `cabinet_minister` | 四部之一，任期 > 90 天 |
| 瓦加斯 南大河州主席 | other | 無 | 16.3.1 沒有地方首長類 |
| 邱吉爾、瓦加斯 各級議員；Father of the House | legislator／other | 無 | 16.3.1 沒有議員類 |

另外，扎丹巴 1924 年那一日任期是否算代理（16.3.1 的 `acting`），來源沒有直接寫（既有 gap 已記）；如果是代理，依 16.3.1 第 2 題只收資料、不出卡。

## 對 §16 的建議（只是建議，ARCHITECTURE.md 沒改）

1. §16.2 明定 400 字的計法：建議「中文 400 字；英文 ≤ 120 詞或 ≤ 800 字元」，或改以 token 數定義（同時也是 RAG chunk 上限）。
2. §16.2 定義半開區間在 month／year 精度時的終點寫法（建議終點寫成下一個單位的起日，例：1911 年迄 → `1912-01-01`＋year）。
3. §16.3 補一條：範圍外的元首／首腦任期放哪裡（選項：`leader_records` 允許範圍外但地圖篩掉；或 `person_positions` 例外收但標 `outside_map_range`）。
4. 明定 §16.3 `person_positions`（生平「經歷」，7 種值域）與 §16.3.1 `person_roles`（收錄與出卡，T3 已決值域）的分工。建議：`person_roles` 管「收不收、出不出卡」，`person_positions` 管生平經歷全集（可以收議員、地方首長、非四部閣員），兩表的 role_kind 值域分開命名，避免混用。
5. §16.4.1 明定 seed 中 `sources` 的表示方式（本樣本用頂層 `sources`＋`sourceKey`），B3 寫入腳本才有固定格式可解析。
6. §16.7 的 P 格式（gap-830 `research.json`）補 `bioId` 鍵：B3 是掛在既有 bio 下，不是建立新 bio。
7. 建議在 §16.4.4 硬性排除層旁記錄「被防機器人驗證擋下的網站不繞過、改用同一權威檔的官方鏡像（例：GND → lobid）」的作法。

## 全量預估

**人物數**：5442 有效、非測試、未被取代的 `leader_bios` 有 **923** 人（另有已撤回或測試 45 筆，合計 968）。§16.3.1 的 P2／P3 擴大範圍後人數會再增加，下面只算現有 923 人。§16.3.1 粗估 P1「查證約 20–40 分鐘／人」，與下面的機器時間（約 2 分鐘／人）不是同一個量：下面沒有算人工審查。

**段落數**：本樣本平均每人 4.4 段，但樣本刻意偏向有名的人物。依 gap-830 的分布（多數是資料薄的小國閣揆或短期元首），假設厚 5%（6 段）、中 25%（4 段）、薄 70%（1–2 段）：
- 923 ×（0.05×6 ＋ 0.25×4 ＋ 0.70×1.5）≈ **2,200 段**（區間約 1,400–4,000）；職位約 2,000–5,000 筆；缺漏約 1,500–2,500 筆。

**本次實際用量**（`gap-830/usage_tally.py`，session `29cdcead-65c6-46ea-90ff-d0b47742a256`，2026-11-11T00:58:08Z – 01:13:23Z，截至寫本文件前，之後的 commit 幾輪沒算進去）：

| input | output | cache_creation | cache_read |
|---|---|---|---|
| 96 | 86,649 | 222,556 | 6,530,488 |

其中約三分之一是一次性的開銷（讀 §16、憲法，確認 DB，寫抓取與驗證工具），全量時可以攤掉。

**推算**（假設全量平均每人 = 樣本每人的 0.6 倍，因為大多數人很薄；仍沿用 Opus 主程序前景逐人做）：
- 每人 ≈ output 1 萬、cache_creation 2.7 萬、cache_read 78 萬
- 923 人 ≈ **output 0.96 千萬、cache_creation 2.5 千萬、cache_read 7.2 億 tokens**
- **USD：缺**。牌價沒有入檔（沿用 `gap-830/usage.md` 慣例，不憑記憶填）。公式：`USD = output×P_out + cache_creation×P_cw + cache_read×P_cr + input×P_in`（單位：每 token 單價）。cache_read 量最大，成本主要由 P_cr 決定。參考：gap-830 b33 用 Sonnet 子程序做較簡單的欄位研究，每人 USD 0.12–0.23（json `total_cost_usd`）；B3 每人工作量約是那時的 3–5 倍。
- **時間**：本次 5 人約 15 分鐘（含工具準備）→ 全量每人平均約 2 分鐘 × 923 ≈ **30 小時連續運算**；加上每批審查、寫入與 commit，比照 gap-830 每批約 10–15 分鐘的節奏，約 **60–80 批、4–6 個工作天**（單一 session 序列執行；並行子程序可以縮短，但要先試算成本）。

## 需 Tai 決定的事

1. **邱吉爾**：庫裡沒有有效 bio。要先用 gap-830 流程建立他（以及 1940–45 的英國首相任期），B3 段落才能寫入嗎？
2. **待決 Q1–Q10**，尤其 Q2（英文 400 字的計法）、Q3（年精度終點）、Q4（範圍外的元首任期）、Q7（名簿下一任起日）會影響全量格式。
3. **`person_positions` 與 `person_roles` 的分工**（§16.3.1 寫「未定」）：決定樣本裡不在 16.3.1 值域內的經歷（議員、州長、非四部閣員、參謀長）要不要保留。
4. **B3 建表**（`leader_bio_paragraphs`、`person_positions` 與引用表，§16.7）要不要開始？目前樣本只在 seed。
5. **全量方式**：Opus 主程序前景逐人做，或 Sonnet 子程序研究＋Opus 審查？請先給牌價或預算上限，才能算 USD。
6. 扎丹巴這類資料極薄的人，只有 1 段「生平概略」加缺漏紀錄，可以接受嗎？還是全量時跳過這類人？
