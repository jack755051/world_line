# 波蘭戰役 1939（`poland_1939`）：戰役資料取得計畫（R1–R8）

日期：2026-11-13。依據：主管 2026-11-13 14:15 指示（Tai 14:14 確認維持原順序：敦克爾克 → 波蘭 → 淞滬）、
展示 worktree `demos/battle-v2.5/DATA-REQUESTS.md`（唯讀）波蘭一節、敦克爾克的做法與裁示（`../dunkirk_1940/PLAN.md`、`DATA-REQUESTS-crosswalk.md`）。
本計畫寫完即接著執行 R1–R8（不等裁示）；只在寫庫、改 schema 或碰到費用上限時停。

## 0. 範圍與共同規則

- **主期 1939-09-01 至 10-06**，含 9/17 蘇聯入侵；不另設前段（`battle.config.json` 的 `mainPhase`）。
- **疆界切片**：9/1，加主權資料實際有變的日期（R8）。
- **來源**：戰役事實只收 A／B；C 只當候選。至少一個德方獨立來源家族（官方或學術）＋ 一個波方家族；拿不到就記 gaps。
  維基百科、Wikidata 只當索引；不用個人網站與禁用網域（generals.dk 與 10 個個人網域）；不用 curl -k、不登入、不繞反爬蟲。
  引文逐字、≤ 80 字；舊檔 `data/campaigns/poland_1939.json` 與展示頁 `battle.json` 只當候選線索。
- **單一來源**不得標已查證；**來源家族**設定在 `battle.config.json`，`tools/battles/crosscheck.py` 依此算獨立來源。
- **地圖**：配準留一法 P95 ≤ 2 km 才可用於部隊位置與前線頂點；未過者僅參考。數位化座標一律標「推估」並記精度。
- **工具**：只用 `tools/battles/` 共用工具；本資料夾只放設定與資料，不放工具副本。
- **人物**：指揮官以 personKey 對既有生平主檔；缺的列清單，本輪不補。
- 不寫庫、不 push、不刪任何檔案（含快取）；只提交自己的路徑；`.dev/` 已不進版控，要保留的東西不放那裡。

## 1. 來源盤點（本輪實測可取得者）

| sourceKey | 內容 | 等級 | 來源家族 | 取得情況 |
|---|---|---|---|---|
| `kennedy-dapam-20-255` | Robert M. Kennedy, *The German Campaign in Poland (1939)*, DA Pamphlet 20-255（1956）；HyperWar 全文 HTML（Campaign-I／II／III、Chronology）＋ 圖 1–10 | A（美國陸軍官方研究） | `us-army-dapam` | 可取得；圖 7（9/1 04:45）、8（北方集團軍群 9/3）、9（南方集團軍群 9/6）、10（9/17 德軍態勢） |
| `usma-atlas-wwii-europe` | 西點軍校二戰歐洲圖集（數位版 WWIIEurope04–07，5100×3300） | B（沿用敦克爾克評等） | `usma-atlas` | 可取得；圖號與圖題於 R2 讀圖確認 |
| `okh-lagekarten-1939` | 德軍 OKH 波蘭戰線態勢略圖（德國歷史研究所莫斯科分所與俄國檔案館合作數位化，wwii.germandocsinrussia.org，如 Дело 354「6–9.09.1939，1:500 000，疊圖用」） | A（德軍原始檔案） | `de-okh-records` | 頁面可開；疊圖用略圖可能沒有城鎮圓點，能否配準於 R2 確認 |
| `bpb-vogel-lieb-blitzkriege` | bpb〈Die deutschen "Blitzkriege" 1939–1941〉，作者 Thomas Vogel、Peter Lieb（ZMSBw） | B（具名德方軍史學者） | `de-academic` | 可取得 |
| `lemo-scriba-polen-1939` | DHM LeMO〈Der Überfall auf Polen 1939〉，Arnulf Scriba（2015） | B（具名作者條目） | `de-academic` | 可取得 |
| `ipn-suleja-wrzesien-1939` | IPN Przystanek Historia〈Wrzesień 1939 roku〉，Włodzimierz Suleja（2022） | B（具名波方史學者） | `pl-ipn` | 可取得 |
| `ipn-biuletyn-2019-9` | *Biuletyn IPN* 2019 nr 9〈1939. Agresja sąsiadów〉（PDF，164 頁；含 Wingert 等文） | B | `pl-ipn` | 可取得 |
| （不可得）*Polskie Siły Zbrojne w drugiej wojnie światowej* t. I（倫敦 1951–1986） | 波方官方戰史 | A | — | 未見合法線上全文 → gaps |
| （不可得）WBH《Przegląd Historyczno-Wojskowy》、BazHum | 波方軍史期刊 | B | — | 站方反爬蟲（Incapsula／403），依規不繞 → gaps |
| （不可得）MGFA *DRZW* Bd. 2 | 德方官方戰史 | A | — | 無線上全文 → 以 bpb／LeMO 代德方家族，記 gaps |

## 2. 各需求項目

### R1 部隊名冊（做到師；展示頁候選 38 單位）
- 要：原文名、中文名、層級、上級、陣營、在戰役中的起訖。德軍集團軍群／集團軍／軍／師；波軍集團軍（Armia）／作戰群（SGO）／師與騎兵旅；蘇軍方面軍／集團軍；斯洛伐克野戰集團軍。
- 來源：Kennedy 第 4–7、9 章與圖 7–10 圖例（主）；德方 bpb／LeMO、波方 IPN 補第二家族（集團軍級以上）。
- 輸出 `r1-units.json`（沿用 dunkirk 欄位：unitKey、nameOrig、nameZh、echelon、parentKey、side、nation、regimeSlug、period、citations、status）。

### R2 地圖
- Kennedy 圖 7–10、USMA 04–07、OKH 略圖：記圖號、圖上日期、網址、授權、有無城鎮圓點。
- 先試配準 Kennedy 圖 9 或 7；小比例尺（全波蘭約 900 km／1200 px）預期 P95 很難 ≤ 2 km。未過者只作參考：部隊標註仍讀（雙讀＋對名冊），但不得當位置或前線頂點。
- 輸出 `digitized/<mapKey>.readings.json` 與 `tools/battles/georef.py` 產出的 `<mapKey>.json`；第二次獨立判讀放 `checks/label-reading2/`。

### R3 部隊位置（文字）
- Kennedy 文字「某部隊某日在某地」，地名對 OSM 物件；`r3-unit-positions.json`。

### R4 前線
- 只取通過門檻圖的頂點；否則依 Kennedy 文字的地名頂點（推估、標精度），`r4-fronts.json`（map）／`r4-text-fronts.json`（文字）。
- 10/1 之後德蘇分界線：需出處（Kennedy 第 118 頁附近）；找不到記 gaps。

### R5 交戰（候選 16 場）
- 名稱、起訖、地點、攻守雙方（對 R1）；華沙（9/27 對 9/28）、利沃夫（9/21 對 9/22）、科克（10/6 對 10/5）三筆矛盾要第二家族。`r5-engagements.json`。

### R6 據點易手日
- Westerplatte、Mława、Hel、Radom、Kutno、Lwów、Warszawa、Modlin、Gdynia、Brześć、Kock 等；`r6-site-control.json`。

### R7 指揮官（候選 38 位）
- 對 R1 單位與既有生平主檔 personKey；`r7-commanders.json`、缺的列 `r7-missing-people.json`（本輪不補生平）。
- 初步對照（person-index，以名字比對，執行時再核）：有主檔 — fedorvonbock、gerdvonrundstedt、georgvonkuchler、gunthervonkluge、wilhelmlist、heinzguderian、walthervonbrauchitsch、franzhalder、albertkesselring、paulludwigewaldvonkleist、edwardsmigły-rydz、władysławanders、semyontimoshenko、ferdinandcatlos；
  缺 — Blaskowitz、Reichenau、Löhr、Hoepner、Kutrzeba、Bortnowski、Rómmel、Szylling、Fabrycy、Dąb-Biernacki、Przedrzymirski、Młot-Fijałkowski、Sosnkowski、Kleeberg、Piskor、Kovalyov 等。

### R8 當年疆界
- `tools/battles/build_r8.py poland_1939`：開發 API 唯讀 GET 主權資料，9/1 全切片＋有變日期；`r8-borders.manifest.json`。
- 已知：9/1 切片無「但澤自由市」紀錄（德國紀錄 9/1 起）→ gaps。

### 共用檔
`sources.json`、`gaps.json`、`name.json`、`unit-label-aliases.json`、`checks/`。

## 3. 推估標記與精度
- 地圖數位化：`estimate: "推估"`、`basis: "map-digitized"`、`usable`（是否過門檻）、`precision_m`（留一 P95＋標註框誤差）。
- 文字頂點前線：`basis: "text-vertices"`、`estimate: "推估"`，精度以地名物件大小與敘述粒度說明。
- 欄位內標記：`tools/battles/mark_fields.py`（預設起日＝9/1、空起止日、未審中文名）。

## 4. 五項檢查（每部分完成後重跑）
1. `verify_quotes.py`：引文逐字自檢。
2. `compare_readings.py`：地圖標註兩次獨立判讀比對。
3. `match_units.py`：標註對 R1 名冊填 unitKey。
4. `crosscheck.py`：單一來源不得已查證、來源家族、降級後低於 B 不當事實。
5. `mark_fields.py`：欄位內預設值與空值標記。

## 5. 步驟與費用（本機 claude -p；上限 $15）
| 步驟 | 低 | 中 | 高 |
|---|---|---|---|
| R1＋R7（Kennedy＋德波家族核對） | 1.5 | 2.5 | 3.5 |
| R2 地圖：讀圖 4 張＋控制點 | 1.5 | 2.5 | 3.5 |
| R2 第二次獨立判讀 | 1.0 | 1.5 | 2.5 |
| R3＋R5＋R6 | 1.5 | 2.5 | 3.5 |
| R4 文字前線 | 0.5 | 1.0 | 1.5 |
| R8、檢查、整理（不用 claude） | 0 | 0 | 0 |
| 合計 | 6.0 | 10.0 | 14.5 |
claude 撞到 5 小時用量上限時，由包裝腳本等到重置時間後以 `--resume` 繼續，不中斷。

## 6. 風險
- 德、波家族只拿到概述性文章（bpb／LeMO／IPN），多數師級細節只有 Kennedy 一家 → 大量單一來源（標 needs-check，不當已查證）。
- 小比例尺地圖配準大概率過不了 2 km → 地圖位置與前線多半只能參考，R4 以文字頂點為主。
- 蘇軍部分 A／B 出處少（Kennedy 第 9 章與 IPN 引用的蘇方文件集）。
- 波方官方戰史（PSZ）與 WBH 期刊拿不到，矛盾裁決可能缺第二家族。

## 7. 待主管決定
1. Kennedy 評 A（美國陸軍官方研究，非交戰國官方戰史）是否同意？
2. bpb（ZMSBw 作者）與 LeMO 合為一個德方家族是否同意？
3. WBH／BazHum 因反爬蟲不可取得，是否由 Tai 或主管手動下載特定 PDF 放入本機？
4. OKH 原始略圖若無城鎮圓點、只能疊圖，是否值得另行以底圖配準？

## 完成狀態（2026-11-13 執行者）

| 項目 | 狀態 | 檔案 |
|---|---|---|
| R1 部隊 | 完成到師級（德 42、波 34、蘇 2 方面軍，共 78；德軍步兵師只列文字點名者） | r1-units.json |
| R2 地圖 | Kennedy 圖 7–10 兩次獨立判讀＋配準；P95 6.83–25.71 km 全未過 2 km，僅參考；USMA 04–07 只登錄；OKH 略圖未取得 | digitized/、map-catalog.json、checks/label-*.json |
| R3 文字位置 | 26 筆（地圖不可用，全為文字） | r3-unit-positions.json |
| R4 前線 | 地圖頂點 0；只有 10/1 德蘇分界線北段 2 個文字頂點（推估）；其餘日期為缺口 | r4-fronts.json、r4-text-vertices.json |
| R5 交戰 | 18 場（14 有日期、4 場只留候選） | r5-engagements.json |
| R6 據點 | 16 處（2 處日期未載） | r6-site-control.json |
| R7 指揮官 | 35 筆，10 人連到既有主檔，24 人列待補（本輪不補） | r7-commanders.json、r7-missing-people.json |
| R8 疆界 | 9/1 與 10/6 兩個切片；分區（9/17–9/28）主權資料未反映，列缺口 | r8-borders.manifest.json |

來源家族引文數：us-army-dapam（Kennedy）211、pl-ipn（Suleja）93、de-academic（LeMO）20；bpb 與 Biuletyn IPN 本輪未引用。
待主管決定的 4 問（Kennedy 是否 A、bpb+LeMO 同族、WBH PDF 手動取得、OKH 圖配準）仍待回覆。

## 主管決定（2026-11-13 14:58）

1. Kennedy DA Pam 20-255 視同官方戰史 A 級（比照 Ellis）；211 條 Kennedy 引文原已標 A，crosscheck 重跑。
2. bpb 與 LeMO 維持同一家族 de-academic。
3. WBH PDF 不下載，留在 gaps（source:pl-wbh-phw）。
4. OKH 略圖下載並配準；USMA 04–07 配準並各做兩次判讀；過 P95 ≤ 2 km 者補 R4 前線（推估），未過者僅參考。
5. 輔助腳本複製到 tools/battles/（以戰役代碼為參數），.dev 原檔保留。

## 進度（2026-11-13 15:40，主管 14:58 決定第 4、5 項）
- 輔助腳本複製到 `tools/battles/`（citelib、fetch_readable、osm_lookup、run_claude、builders/poland_1939_*），以戰役代碼為參數；`.dev` 原檔保留。builders 重跑輸出與已提交資料相同。
- 地圖配準（門檻留一 P95 ≤ 2 km）：USMA 04 21.09、05 25.76、06 19.91、07 20.02 km（未過，僅參考；底圖城鎮位置本身偏差大）；OKH д.354 Lagekarte 4 為無底圖覆蓋圖，無法配準；OKH д.355 Luftgau IV 圖 1.77 km（通過）。
- R4：通過的 д.355 圖沒有地面前線，只加 2 條 9/6 德軍 Armeegrenze（boundary，12 個頂點，推估，限控制點凸包內）。前線缺口 13 天不變。
- USMA 04–07 標註兩次判讀：113 筆中 110 筆一致，1 筆文字不同（MODLIN AND NAREW GROUP／MODLIN），2 筆師級未檢查。
