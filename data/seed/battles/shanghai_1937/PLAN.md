# 淞滬會戰 1937（`shanghai_1937`）：戰役資料取得計畫（R1–R8）

日期：2026-11-13。依據：主管 2026-11-13 14:58 指示（Tai 15:33 轉達）、主管 15:33 控制點排除規則裁示、
展示 worktree `demos/battle-v2.5/DATA-REQUESTS.md`（唯讀）淞滬一節、敦克爾克與波蘭的做法（`../poland_1939/PLAN.md`）。
本計畫寫完即接著執行 R1–R8，每部分完成即提交；只在寫庫、改 schema 或碰到費用上限（$15）時停。問題記在 §7 與最終報告。

## 0. 範圍與共同規則

- **主期 1937-08-13 至 11-26**（`battle.config.json` 的 `mainPhase`）；不設前段。
- **疆界切片**：8/13，加主權資料實際有變的日期（R8，只用主專案主權資料，不手描）。
- **來源**：戰役事實只收 A／B；C 只當候選。至少一個中方獨立來源家族＋一個日方獨立來源家族；拿不到記 gaps。
  不用個人網站、generals.dk 與 10 個禁用網域、百度；維基百科、Wikidata 只當索引；不用 curl -k、不登入、不繞反爬蟲。
  引文逐字、≤ 80 字（JM-179 掃描 OCR 品質差：只挑乾淨片段，照 OCR 原樣逐字）。舊檔 `data/campaigns/shanghai_1937.json` 只當候選線索。
- **中文名**：保留繁體；每個中文名的出處記在 `field_sources.nameZh`（出處原文用字／本專案譯名／未審）。
- **單一來源**不得標已查證，且降一級；**來源家族**設定在 `battle.config.json`，`tools/battles/crosscheck.py` 依此算獨立來源。
- **地圖**：配準留一法 P95 ≤ 2 km 才可用於部隊位置與前線頂點；未過者僅參考。數位化座標一律標「推估」並記精度；捨棄的控制點逐一記理由。地圖影像不進版控，雜湊記 `maps/SHA256SUMS.txt`。
- **工具**：只用 `tools/battles/` 共用工具（以戰役代碼為參數）；本資料夾只放設定與資料；新增的共用小工具放 `tools/battles/`，不放 `.dev/`。
- **人物**：指揮官以 personKey 對既有生平主檔；缺的列清單，本輪不補。
- 不寫庫、不 push、不刪任何檔案（含快取）；只在暫存區為空時以 `git commit -- <路徑>` 提交自己的路徑；不碰 `.dev/run-api.sh` 與 `/tmp/wl-pl-*`（本戰役第二次判讀用新資料夾 `/tmp/wl-sh-*`）。

### 控制點排除規則（主管裁示 2026-11-13 15:33，本戰役同樣適用）
**排除控制點的理由必須在看殘差之前確定。任何在看過殘差之後才捨棄控制點的地圖，一律僅參考。**
- 做法：每張圖先寫 `digitized/<mapKey>.readings.json` 的 `controlPointExclusions`（每點 `name`、`reason`、`decidedBeforeResiduals`），再跑 `tools/battles/georef.py`。
- `georef.py` 強制執行：任一排除點 `decidedBeforeResiduals` 不是 `true`，輸出 `threshold.referenceOnly=true`、`passes=false`（即使 P95 ≤ 2 km）。
- 看過殘差後只能「重讀像素」（記在 `controlPointRereads`，原讀值保留），不能刪點；重讀也要記理由。

## 1. 來源盤點（本輪實測可取得者）

| sourceKey | 內容 | 等級 | 來源家族 | 取得情況 |
|---|---|---|---|---|
| `jm179` | Japanese Monograph No. 179 *Central China Area Operations Record 1937–1941*（前日軍軍官撰、美軍發行）；PDF 第 12–19 頁為上海作戰，第 18 頁 Map No. 1「SHANGHAI OPERATION 23 AUG–24 NOV 1937」 | B | `jp-monographs` | 可取得（ibiblio HyperWar PDF）；OCR 雜訊多 |
| `jm70` | Japanese Monograph No. 70（China Expeditionary Army 指揮紀錄）上海段概述 | B | `jp-monographs` | 可取得 |
| `jacar-c13071346000` | 陸軍省『支那事変陸戦概史 上編』第6篇第4章（防衛研究所藏） | A | `jp-jacar` | 可取得：JACAR 目錄頁「内容」欄有翻刻全文段落；影像檢視器不抓 |
| `jacar-c11112056100` | 「第１０軍作戦経過の概要」（11A参謀部作戦課，防衛研究所藏） | A | `jp-jacar` | 可取得：「内容」欄有第十軍杭州灣登陸段落 |
| `su2015` | 蘇聖雄〈蔣中正對淞滬會戰之戰略再探〉，《國史館館刊》46（2015） | B | `tw-roc` | 可取得 |
| `chang2016` | 張鑄勳〈析論蔣中正在中國抗日戰爭初期的戰略指導〉，《國史館館刊》50（2016） | B | `tw-roc` | 可取得 |
| `mnd2017` | 張琪閔、蕭新民〈從孫子兵法「虛實」觀點淺談1937年淞滬會戰〉，國防部《海軍學術雙月刊》51:4（2017）；戰況引《抗日戰史（四）華東地區作戰》（史政編譯局 1994）；表三／四為開戰初期中日指揮系統表；圖一至六轉載蔣緯國《國民革命戰史》第三部第五卷（1979）附圖 | B | `tw-roc` | 可取得；附圖 646 px 寬，有公里比例尺 |
| `old-campaign-file` | 主專案舊考證檔 | C | 只當線索 | — |
| （不可得）國防部史政編譯局《抗日戰史》淞滬會戰各冊 | 中方官方戰史 | A | — | 無合法線上全文 → gaps（以 mnd2017 轉引代之） |
| （不可得）防衛研修所『戦史叢書086 支那事変陸軍作戦〈1〉』 | 日方官方戰史 | A | — | NIDS 僅公開目次 → gaps（以 JACAR 原始檔案代之） |
| （不可得）Hsu Long-hsuen & Chang Ming-kai, *History of the Sino-Japanese War* | 中方官方戰史英譯 | A | — | 無可取得全文 → gaps |
| （待找）中研院近史所 | 中方學術 | B | — | 本輪找到的中研院檔（蘇聖雄 2020 臺大歷史學報）以華北為主，未收；記 gaps |

## 2. 各需求項目

### R1 部隊名冊（做到師／師團）
- 日方：中支那方面軍、上海派遣軍、第十軍；第3、9、11、13、16、101、6、18、114 師團；重藤支隊、國崎支隊、天谷支隊；上海海軍特別陸戰隊、第三艦隊（海軍只到艦隊／陸戰隊）。主：JM-179＋JACAR；第二家族：tw-roc（mnd2017／chang2016 寫日軍番號）。
- 中方：第三戰區；左翼軍／中央軍／右翼軍；第8、9、10、15、19、21 集團軍；有出處的軍與師（第36、87、88、56、57、98、11、14、67 師、第十八軍、第七十八軍、獨立第20旅、教導總隊等）。主：tw-roc；第二家族：JM-179（中方番號極少 → 多為單一來源）。
- 開戰初期指揮系統表（mnd2017 表三、表四，圖片）只做「表格判讀」補番號與主官，標 needs-check、不當引文。
- 輸出 `r1-units.json`（沿用波蘭欄位＋`field_sources.nameZh`）。builder：`tools/battles/builders/shanghai_1937_r1r7.py`。

### R2 地圖
- `jm179-map1`（JM-179 Map No. 1，3299×2540，300 dpi 由 PDF 轉出）：示意圖，預期過不了 2 km。
- `mnd2017-fig1`…`fig6`（蔣緯國附圖轉載，各附公里比例尺）：小區域、可能有機會；逐張試配準。
- 每張：先定控制點與排除理由（§0 規則）→ `georef.py` → 未過者僅參考；標註雙讀（我讀＋claude -p 獨立讀，`/tmp/wl-sh-*` 新資料夾），對 R1。
- 輸出 `map-catalog.json`、`georef.config.json`、`digitized/`、`maps/SHA256SUMS.txt`、`checks/label-reading2/`。

### R3 部隊位置（文字）
- 文字「某部隊某日在某地」（JM-179、JACAR、mnd2017、su2015），地名對 OSM（`tools/battles/osm_lookup.py`）；`r3-unit-positions.json`。

### R4 前線
- 只取通過門檻圖的頂點；否則用文字頂點（推估、標精度）：mnd2017 的 9/14「瀏河鎮－羅店－蘊藻濱－江灣－北站之線」、10/1「楊涇河西岸－陳家行－蘊藻濱之線」、11/5「瀏河鎮－羅店西方－蘇州河左岸至南站之線」等；吳福線、錫澄線另找出處。JM-179 11/19「Changshu–Suchou–Chiahsing」日軍控制線。

### R5 交戰
- 虹口／楊樹浦圍攻（8/13–8/22）、吳淞至瀏河反登陸（8/23–9/10）、羅店、大場（10/26）、四行倉庫、杭州灣登陸（11/5）、白茆口登陸（11/13）等；`r5-engagements.json`。

### R6 據點易手日
- 閘北、吳淞、羅店、寶山、大場鎮、金山衛、南市、松江、蘇州、嘉興、無錫等；結束日 11/26；`r6-site-control.json`。

### R7 指揮官
- 松井石根、朝香宮鳩彥、柳川平助、藤田進、山室宗武、谷壽夫等；蔣中正、顧祝同、陳誠、張治中、朱紹良、張發奎、薛岳、宋希濂、王敬久、孫元良等；對生平主檔（person-index＋`data/seed/leaders` 提到淞滬的檔案）；`r7-commanders.json`、`r7-missing-people.json`（本輪不補）。

### R8 當年疆界
- `tools/battles/build_r8.py shanghai_1937`：開發 API 唯讀 GET，8/13 切片＋有變日期；`r8-borders.manifest.json`。

### 共用檔
`sources.json`、`gaps.json`、`name.json`、`unit-label-aliases.json`、`checks/`。

## 3. 推估標記與精度
同波蘭：地圖數位化 `estimate: "推估"`、`basis: "map-digitized"`、`usable`、`precision_m`；文字頂點 `basis: "text-vertices"`；欄位內標記用 `tools/battles/mark_fields.py`（預設起日＝8/13、空起止日、未審中文名）。

## 4. 五項檢查（每部分完成後重跑）
1. `verify_quotes.py shanghai_1937 --apply`：引文逐字自檢。
2. `compare_readings.py`：地圖標註兩次獨立判讀比對。
3. `match_units.py`：標註對 R1 名冊填 unitKey。
4. `crosscheck.py`：單一來源不得已查證並降一級、來源家族、降級後低於 B 不當事實。
5. `mark_fields.py`：欄位內預設值與空值、未審中文名標記。

## 5. 步驟與費用（上限 $15；先寫腳本再跑，claude -p 只做第二次讀圖）
| 步驟 | 低 | 中 | 高 |
|---|---|---|---|
| R1＋R7（Python builder＋citelib，不用 claude） | 0 | 0 | 0 |
| R2 控制點與我方讀圖 | 0 | 0 | 0 |
| R2 第二次獨立判讀（claude -p，7 張圖切片） | 1.5 | 3.0 | 5.0 |
| R3–R6（builder） | 0 | 0 | 0 |
| R8、檢查、整理 | 0 | 0 | 0 |
| 合計 | 1.5 | 3.0 | 5.0 |

## 6. 風險
- 中方番號細節多只有 tw-roc 一家、日方細節多只有 JM-179／JACAR → 大量單一來源（needs-check）。
- JM-179 圖為示意圖，大概率過不了 2 km；mnd2017 附圖解析度低（646 px），控制點讀取誤差大。
- 中方官方戰史（《抗日戰史》）與戦史叢書 086 拿不到全文。

## 7. 待主管決定
1. 國史館館刊兩文與國防部期刊一文保守合為一族 `tw-roc`，是否同意？（拆開則中方內部可互證，但兩者同承史政編譯局戰史脈絡）
2. JM-179／JM-70 評 B（前日軍軍官戰後撰、美軍發行）、JACAR 陸軍省檔案評 A，是否同意？
3. mnd2017 表三／表四（圖片表格）只做判讀、不當引文，是否同意？
4. 是否要 Tai 手動取得《抗日戰史》淞滬各冊或戦史叢書 086 的特定頁？
