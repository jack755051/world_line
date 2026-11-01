# 兩次大戰之間 A 批：1918-11-12 → 1923（DRAFT，待 Tai 檢查）

範圍：歐洲、北非、近東（OHM 裁切框同 WW1 第二批）。期間半開區間 [1918-11-12, 1924-01-01)；1924-01-01 是本批試驗期間終點，不是政權迄日。接 WW1 第二批（迄 1918-11-12）與開發庫既有 1918～1938 紀錄（例如法國 1918-11-22、保加利亞 1919-11-27、比利時 1920-01-10、匈牙利 1921-11-10、奧地利 1922-10-01、立陶宛 1923-01-19 起；波蘭 1924-06-22、土耳其 1924-08-06 起不在本批窗內）。
**只寫入本機開發庫**（worldline-borders-dev，API 127.0.0.1:5052，DB 5442）；寫入 appdb_ww2（5051）要另取得 Tai 同意。

## 子批

| 子批 | 紀錄起日 | 請求數 |
|---|---|---|
| A1 | [1918-11-12, 1920-01-10) | 166 |
| A2 | [1920-01-10, 1921-03-18) | 90 |
| A3 | [1921-03-18, 1924-01-01) | 55 |

每筆紀錄用真實起訖，依起日分子批；來源、政權、事件放在第一個引用它們的子批。子批要依序送。A1 先撤回第二批的德意志帝國主權紀錄 SOV_DE_EMP_R（迄 1918-11-12 試驗終點），再以迄 1918-11-09（EV_DE_REV）重送 SOV_DE_EMP_R2，11-09 起由德意志國 SOV_DE_A 接續（先撤後增）。

## 檔案

| 檔案 | 說明 |
|---|---|
| `build/fetch.py` | 依 relation id 從 OHM Overpass 抓關係，存 `raw/`（不進版控） |
| `build/build.py` | 組多邊形 → 框裁切 → Natural Earth 陸地裁切 → 簡化 → `borders-ohm-interwar-a.geojson`＋`ohm-manifest.json` |
| `build/make_requests.py` | 優先序引擎（高優先紀錄扣出低優先、低優先在高優先起訖日切段；開發庫既有紀錄為最高優先）、手繪近似、QA（每個切點日檢查重疊）、產生 `requests/A{1,2,3}/*.json`、`interwar-a-derived.geojson`、`qa.json`；需要 WW1 第二批目錄（`../../ww1/war-1914-1918`，或環境變數 WW1B2） |
| `build/readme.py` | 產生本檔 |
| `send_seed.py` | 依子批送出（預設 dry-run；拒絕 5051；API key 從 --env 安靜讀取） |
| `db-export/`（不進版控） | 開發庫唯讀匯出：本期間既有主權紀錄；備份在 `~/01_Projects/world_line_backups/` |

用法（在本目錄）：
```
P="--prior ../../../../.dev/sent-ids.borders-dev.json --prior ../../../../.dev/sent-ids.borders-us-dev.json --prior ../../../../.dev/sent-ids.ww1-balkans-1908-1914-dev.json --prior ../../../../.dev/sent-ids.ww1-war-1914-1918-dev.json"
python3 send_seed.py --sub A1 --base http://127.0.0.1:5052 --env ../../../../.env.borders-dev $P --ids ../../../../.dev/sent-ids.interwar-a-dev.json [--send]
```

OHM Overpass `osm_base`：2026-10-31T19:28:28Z（UTC）。來源：條約原文（國際聯盟條約集 LNTS 各卷 PDF）、FRUS 巴黎和會第 II、XII、XIII 卷、FRUS 1918 補編一、FRUS 1922 第 II 卷、1923 第 II 卷；找不到正式出處的事件標 **待查證**。

## 事件

| placeholder | 日期 | 類型 | 摘要 | 出處 | 子批 |
|---|---|---|---|---|---|
| EV_DE_REV | 1918-11-09 | political | 德國十一月革命：德皇退位、宣布共和，艾伯特出任總理 | SRC_FRUS_1918S1 Doc. 418, pp. 492–493 | A1 |
| EV_DEAT | 1918-11-12 | political | 德意志奧地利臨時國民議會宣布成立民主共和國 | SRC_FRUS_PPC2 Doc. 117, pp. 189–190 | A1 |
| EV_ZUNR | 1918-11-13 | political | 西烏克蘭人民共和國在利沃夫定名（11-01 起與波蘭爭奪東加利西亞） | **待查證** | A1 |
| EV_HU_PR | 1918-11-16 | political | 匈牙利宣布成立共和國（卡羅伊政府） | SRC_FRUS_PPC2 Doc. 136, pp. 204–205 | A1 |
| EV_FIUME_OCC | 1918-11-17 | campaign | 義大利軍進入阜姆，協約國共同佔領 | **待查證** | A1 |
| EV_LV | 1918-11-18 | political | 拉脫維亞宣布獨立 | **待查證** | A1 |
| EV_SCS_SERBIA | 1918-11-24 | political | 斯洛維尼亞人、克羅埃西亞人和塞爾維亞人國決議與塞爾維亞合併 | **待查證** | A1 |
| EV_PODGORICA | 1918-11-26 | political | 波德戈里察議會廢黜蒙特內哥羅國王、決議與塞爾維亞合併 | SRC_FRUS_PPC2 Doc. 274, pp. 349–350 | A1 |
| EV_EE_WAR | 1918-11-28 | war | 紅軍進攻納爾瓦，愛沙尼亞獨立戰爭開始 | **待查證** | A1 |
| EV_KSCS | 1918-12-01 | political | 塞爾維亞人、克羅埃西亞人和斯洛維尼亞人王國在貝爾格勒宣布成立 | SRC_FRUS_PPC2 Doc. 276, pp. 351–354 | A1 |
| EV_ALBA_IULIA | 1918-12-01 | political | 阿爾巴尤利亞國民大會決議外西凡尼亞等地與羅馬尼亞合併 | SRC_FRUS_PPC2 Doc. 326, pp. 395–396 | A1 |
| EV_IS | 1918-12-01 | political | 丹冰聯合法生效，冰島成為與丹麥共主的主權王國 | **待查證** | A1 |
| EV_LV_WAR | 1918-12-01 | war | 紅軍進入拉脫維亞，拉脫維亞獨立戰爭（1919-01-03 里加失守） | **待查證** | A1 |
| EV_LT_WAR | 1918-12-15 | war | 紅軍進入立陶宛，立陶宛—蘇維埃戰爭開始 | **待查證** | A1 |
| EV_BY_SSR | 1919-01-01 | political | 白俄羅斯蘇維埃社會主義共和國宣布成立 | **待查證** | A1 |
| EV_PL_SOV_WAR | 1919-02-14 | war | 波蘭與蘇俄軍在別廖扎首次交火，波蘇戰爭開始 | **待查證** | A1 |
| EV_UA_SSR | 1919-03-10 | political | 烏克蘭蘇維埃社會主義共和國第一部憲法通過（OHM 起日） | **待查證** | A1 |
| EV_HU_SR | 1919-03-21 | political | 匈牙利蘇維埃共和國成立（庫恩·貝拉） | SRC_FRUS_PPC12 Doc. 157, pp. 424–427 | A1 |
| EV_HU_WAR | 1919-04-16 | war | 羅馬尼亞軍（及 4 月底起捷克斯洛伐克軍）進攻匈牙利蘇維埃共和國 | **待查證** | A1 |
| EV_SMYRNA | 1919-05-15 | campaign | 希臘軍在士麥那登陸 | **待查證** | A1 |
| EV_VERSAILLES_SIGN | 1919-06-28 | treaty | 凡爾賽和約簽字 | SRC_FRUS_PPC13 Treaty of Peace with Germany（全文與註解） | A1 |
| EV_ZUNR_END | 1919-07-17 | campaign | 西烏克蘭軍撤過茲布魯奇河，東加利西亞全歸波蘭軍控制 | **待查證** | A1 |
| EV_HU_SR_END | 1919-08-01 | political | 匈牙利蘇維埃共和國垮台，羅馬尼亞軍逼近布達佩斯 | **待查證** | A1 |
| EV_SAINT_GERMAIN_SIGN | 1919-09-10 | treaty | 聖日耳曼條約簽字 | SRC_FRUS_PPC13 Status of the Treaties：Treaty of Saint-Germain-en-Laye, p. 30 | A1 |
| EV_DANNUNZIO | 1919-09-12 | campaign | 鄧南遮率志願軍佔領阜姆 | **待查證** | A1 |
| EV_VERSAILLES | 1920-01-10 | treaty | 凡爾賽和約生效：德國割讓領土，薩爾、但澤、梅梅爾交國際管理，什列斯威、上西里西亞等地待公投 | SRC_FRUS_PPC13 Status of the Treaties, p. 29；SRC_FRUS_PPC13 凡爾賽和約 Part III, Section I，Arts. 27–30；SRC_FRUS_PPC13 凡爾賽和約 Part III, Section IV，Arts. 45–50；SRC_FRUS_PPC13 凡爾賽和約 Part III, Section V，Art. 51；SRC_FRUS_PPC13 凡爾賽和約 Part III, Section VIII，Arts. 87–93；SRC_FRUS_PPC13 凡爾賽和約 Part III, Section X，Art. 99；SRC_FRUS_PPC13 凡爾賽和約 Part III, Section XI，Arts. 100–108；SRC_FRUS_PPC13 凡爾賽和約 Part III, Section XII，Arts. 109–114 | A1 |
| EV_TARTU_EE | 1920-02-02 | treaty | 塔爾圖和約：蘇俄承認愛沙尼亞獨立 | SRC_LNTS_11 No. 289, p. 3 | A1 |
| EV_SCHLESWIG_1 | 1920-02-10 | political | 北什列斯威（第一區）公投，多數贊成歸丹麥 | SRC_FRUS_PPC13 凡爾賽和約 Part III, Section XII，Arts. 109–110 | A2 |
| EV_HU_KINGDOM | 1920-03-01 | political | 匈牙利國會選霍爾蒂為攝政，恢復王國 | **待查證** | A1 |
| EV_SCHLESWIG_2 | 1920-03-14 | political | 中什列斯威（第二區）公投，多數贊成留在德國 | SRC_FRUS_PPC13 凡爾賽和約 Part III, Section XII，Arts. 109–110 | A2 |
| EV_GNA | 1920-04-23 | political | 土耳其大國民議會在安卡拉開議 | **待查證** | A2 |
| EV_AZ_SSR | 1920-04-28 | political | 紅軍進入巴庫，亞塞拜然蘇維埃社會主義共和國成立 | **待查證** | A1 |
| EV_SCHLESWIG_TRANSFER | 1920-06-15 | political | 北什列斯威正式移交丹麥 | SRC_FRUS_PPC13 凡爾賽和約 Part III, Section XII，Arts. 110–111 | A1 |
| EV_BATUMI_END | 1920-07-07 | campaign | 英軍撤出巴統，移交喬治亞 | **待查證** | A1 |
| EV_MOSCOW_LT | 1920-07-12 | treaty | 莫斯科和約：蘇俄承認立陶宛獨立 | SRC_LNTS_3 No. 94, p. 105 | A1 |
| EV_SAINT_GERMAIN | 1920-07-16 | treaty | 聖日耳曼條約生效：奧地利承認繼承國，南提洛、的里雅斯特、伊斯特里亞歸義大利 | SRC_FRUS_PPC13 Status of the Treaties：Treaty of Saint-Germain-en-Laye, p. 30 | A1 |
| EV_SPA | 1920-07-28 | political | 協約國大使會議裁定切申西里西亞分割（捷克斯洛伐克、波蘭） | **待查證** | A2 |
| EV_NEUILLY | 1920-08-09 | treaty | 納伊條約生效：保加利亞割讓西色雷斯等地 | SRC_FRUS_PPC13 Status of the Treaties：Treaty of Neuilly-sur-Seine, p. 33 | A2 |
| EV_SEVRES | 1920-08-10 | treaty | 色佛爾條約簽字（從未生效）；同日起委任統治地依 OHM 劃分 | SRC_FRUS_PPC13 Status of the Treaties, p. 35 | A1 |
| EV_RIGA_LV | 1920-08-11 | treaty | 里加和約：蘇俄承認拉脫維亞獨立 | SRC_LNTS_2 No. 67, p. 195 | A1 |
| EV_AM_TR_WAR | 1920-09-24 | war | 土耳其（安卡拉）軍進攻亞美尼亞 | **待查證** | A2 |
| EV_CARINTHIA | 1920-10-10 | political | 克恩頓公投：A 區多數贊成留在奧地利 | **待查證** | A2 |
| EV_CLT | 1920-10-12 | political | 熱利戈夫斯基佔領維爾紐斯，宣布中立陶宛共和國 | **待查證** | A2 |
| EV_TARTU_FI | 1920-10-14 | treaty | 塔爾圖（多爾帕特）和約：芬蘭與蘇俄劃界，佩琴加歸芬蘭 | SRC_LNTS_3 No. 91, p. 5 | A1 |
| EV_RAPALLO | 1920-11-12 | treaty | 拉帕洛條約：義大利與塞爾維亞人克羅埃西亞人和斯洛維尼亞人王國劃界，阜姆成為自由邦 | SRC_LNTS_18 No. 477, p. 387 | A2 |
| EV_DANZIG_IWA | 1920-11-15 | political | 但澤自由市成立 | SRC_FRUS_PPC13 凡爾賽和約 Part III, Section XI，Arts. 100–102 | A2 |
| EV_CRIMEA | 1920-11-17 | campaign | 弗蘭格爾軍撤出克里米亞，南俄政府結束 | **待查證** | A2 |
| EV_ALEXANDROPOL | 1920-12-02 | treaty | 亞歷山德羅波爾條約；同日亞美尼亞蘇維埃化 | **待查證** | A1 |
| EV_FIUME_FS | 1920-12-30 | political | 義軍驅逐鄧南遮（「血腥聖誕」），阜姆自由邦依拉帕洛條約成立 | SRC_LNTS_18 No. 477, p. 387（第 4 條） | A1 |
| EV_GE_INV | 1921-02-12 | war | 紅軍進攻喬治亞 | **待查證** | A2 |
| EV_GE_SSR | 1921-02-25 | political | 紅軍佔領提比里斯，喬治亞蘇維埃社會主義共和國成立 | **待查證** | A2 |
| EV_MOSCOW_TR | 1921-03-16 | treaty | 莫斯科條約（蘇俄與安卡拉政府） | **待查證** | A2 |
| EV_RIGA_IWA | 1921-03-18 | treaty | 里加和約：波蘭與蘇俄、蘇烏克蘭劃界，波蘇戰爭結束 | SRC_LNTS_6 No. 149, p. 51 | A1 |
| EV_USIL_PLEB | 1921-03-20 | political | 上西里西亞公投 | SRC_FRUS_PPC13 凡爾賽和約 Part III, Section VIII，Art. 88 與附件 | A3 |
| EV_TRIANON | 1921-07-26 | treaty | 特里阿農條約生效：匈牙利承認新邊界 | SRC_FRUS_PPC13 Status of the Treaties：Treaty of Trianon, p. 34；SRC_LNTS_6 No. 152, p. 187 | A3 |
| EV_RIF | 1921-09-18 | political | 里夫共和國宣布成立 | **待查證** | A3 |
| EV_LAJTA | 1921-10-04 | political | 布爾根蘭的匈牙利非正規軍宣布萊塔班國 | **待查證** | A1 |
| EV_KARS | 1921-10-13 | treaty | 卡爾斯條約：安卡拉政府與外高加索三蘇維埃共和國劃界 | **待查證** | A2 |
| EV_ANKARA | 1921-10-20 | treaty | 安卡拉協定：法國與安卡拉政府停戰，法軍撤出奇里乞亞 | **待查證** | A2 |
| EV_USIL_DIV | 1921-10-20 | political | 國際聯盟建議、大使會議決定分割上西里西亞 | **待查證** | A3 |
| EV_BURGENLAND | 1921-11-10 | political | 布爾根蘭移交奧地利（萊塔班國結束） | **待查證** | A3 |
| EV_EG_K | 1922-02-28 | political | 英國單方面宣布埃及獨立（3-15 福阿德一世稱王） | **待查證** | A1 |
| EV_TSFSR | 1922-03-12 | political | 外高加索社會主義蘇維埃共和國聯盟成立 | **待查證** | A2 |
| EV_CLT_ANNEX | 1922-04-18 | political | 中立陶宛併入波蘭（依 OHM 換版日） | **待查證** | A2 |
| EV_USIL_TRANSFER | 1922-06-20 | political | 上西里西亞東部移交波蘭 | **待查證** | A2 |
| EV_SMYRNA_FALL | 1922-09-09 | campaign | 土耳其軍進入士麥那，希臘佔領結束 | SRC_FRUS_1922V2 Doc. 328；SRC_FRUS_1922V2 Doc. 330 | A1 |
| EV_MUDANYA | 1922-10-11 | armistice | 穆達尼亞停戰協定：希臘撤出東色雷斯 | **待查證** | A1 |
| EV_SULTANATE_END | 1922-11-01 | political | 大國民議會廢除蘇丹制，鄂圖曼帝國結束 | **待查證** | A3 |
| EV_IFS | 1922-12-06 | political | 愛爾蘭自由邦成立 | **待查證** | A3 |
| EV_USSR | 1922-12-30 | political | 蘇聯成立：俄、烏、白俄、外高加索組成蘇維埃社會主義共和國聯盟 | **待查證** | A1 |
| EV_RUHR | 1923-01-11 | campaign | 法、比軍佔領魯爾區 | SRC_FRUS_1923V2 Doc. 32；SRC_FRUS_1923V2 Doc. 34 | A3 |
| EV_MEMEL_IWA | 1923-01-15 | campaign | 梅梅爾起事，立陶宛控制梅梅爾地區 | **待查證** | A2 |
| EV_LAUSANNE | 1923-07-24 | treaty | 洛桑條約簽字：土耳其新邊界（取代色佛爾條約） | SRC_LNTS_28 No. 701, p. 11 | A3 |
| EV_TR_REPUBLIC | 1923-10-29 | political | 土耳其共和國宣布成立 | **待查證** | A3 |

## 主權紀錄

| placeholder | 政權 | 期間 | 層級 | 幾何 | 起事件 | 迄事件 | 子批 |
|---|---|---|---|---|---|---|---|
| SOV_DE_EMP_R2 | REGIME_DE_EMP | 1908-10-06～1918-11-09 | de_jure | relation/2692425 v259 | — | EV_DE_REV | A1 |
| SOV_AL_A | REGIME_AL_PR | 1918-11-12～1918-11-24 | de_jure | relation/2855613 v8 | — | — | A1 |
| SOV_AL_B | REGIME_AL_PR | 1918-11-24～1924-01-01 | de_jure | relation/2800556 v23 − 塞爾維亞 | — | — | A1 |
| SOV_AM_A | REGIME_AM | 1918-11-12～1920-12-02 | de_jure | relation/2698116 v12 | — | EV_ALEXANDROPOL | A1 |
| SOV_AT_R1_A_1 | REGIME_AT_R1 | 1918-11-12～1921-10-04 | de_jure | relation/2692711 v75 | EV_DEAT | EV_LAJTA | A1 |
| SOV_AZ_A | REGIME_AZ | 1918-11-12～1920-04-28 | de_jure | relation/2698117 v13 | — | EV_AZ_SSR | A1 |
| SOV_BALTIC_A | REGIME_BALTIC_OCC | 1918-11-12～1918-11-18 | not_sovereign | relation/2744426 v18 ∪ relation/2869679 v5 − republic-of-estonia − 立陶宛 | — | EV_LV | A1 |
| SOV_BATUMI | REGIME_BATUMI | 1918-12-01～1920-07-07 | not_sovereign | relation/2698257 v6 | — | EV_BATUMI_END | A1 |
| SOV_BE_A | REGIME_BE | 1918-11-12～1920-01-10 | de_jure | relation/2797729 v43 | — | EV_VERSAILLES | A1 |
| SOV_BG_A_IWA | REGIME_BG | 1918-11-12～1919-11-27 | de_jure | relation/2746680 v29 | — | — | A1 |
| SOV_BY_PR | REGIME_BY_PR | 1918-11-12～1919-01-01 | not_sovereign | relation/2957449 v6 − 烏克蘭 | — | EV_BY_SSR | A1 |
| SOV_BY_SSR_1 | REGIME_BY_SSR | 1919-01-01～1919-03-10 | de_jure | relation/2848186 v17 − 烏克蘭 | EV_BY_SSR | EV_UA_SSR | A1 |
| SOV_BY_SSR_2 | REGIME_BY_SSR | 1919-03-10～1922-12-30 | de_jure | relation/2848186 v17 | EV_UA_SSR | EV_USSR | A1 |
| SOV_CARNARO | REGIME_CARNARO | 1919-09-12～1920-12-30 | not_sovereign | relation/2696321 v25 | EV_DANNUNZIO | EV_FIUME_FS | A1 |
| SOV_CIESZYN | REGIME_CIESZYN | 1918-11-12～1920-08-28 | not_sovereign | relation/2747891 v13 | — | — | A1 |
| SOV_CS_A | REGIME_CS | 1918-11-12～1920-02-04 | de_jure | relation/2747877 v61 − 切申爭議區 | — | — | A1 |
| SOV_CY_IWA | REGIME_CY_ANNEX | 1918-11-12～1924-01-01 | de_jure | relation/2848135 v5 | — | — | A1 |
| SOV_DE_A | REGIME_DE | 1918-11-09～1918-11-12 | de_jure | relation/2692425 v259 | EV_DE_REV | — | A1 |
| SOV_DE_B | REGIME_DE | 1918-11-12～1920-01-10 | de_jure | relation/2696519 v184 | — | EV_VERSAILLES | A1 |
| SOV_DK_A_1 | REGIME_DK | 1918-11-12～1918-12-01 | de_jure | relation/2869935 v14 | — | EV_IS | A1 |
| SOV_DK_A_2 | REGIME_DK | 1918-12-01～1920-06-15 | de_jure | relation/2869935 v14 − 冰島 | EV_IS | EV_SCHLESWIG_TRANSFER | A1 |
| SOV_EG_A | REGIME_EG | 1918-11-12～1922-02-28 | de_jure | relation/2803205 v16 | — | EV_EG_K | A1 |
| SOV_ES_A_IWA | REGIME_ES_K | 1918-11-12～1921-06-01 | de_jure | relation/2860486 v24 − 西屬摩洛哥 | — | — | A1 |
| SOV_FI_D | REGIME_FI | 1918-11-12～1920-10-14 | de_jure | relation/2959043 v7 | — | EV_TARTU_FI | A1 |
| SOV_FIUME_IA | REGIME_FIUME_IA | 1918-11-17～1919-09-12 | not_sovereign | relation/2696321 v25 | EV_FIUME_OCC | EV_DANNUNZIO | A1 |
| SOV_FR3_A | REGIME_FR3 | 1918-11-12～1918-11-22 | de_jure | relation/2866012 v31 | — | — | A1 |
| SOV_GE_A_1 | REGIME_GE | 1918-11-12～1918-12-01 | de_jure | relation/2698086 v23 | — | — | A1 |
| SOV_GE_A_2 | REGIME_GE | 1918-12-01～1920-07-07 | de_jure | relation/2698086 v23 − 巴統 | — | EV_BATUMI_END | A1 |
| SOV_GR_A_1 | REGIME_GR | 1918-11-12～1918-11-24 | de_jure | relation/2863749 v19 − 保加利亞 | — | — | A1 |
| SOV_GR_A_2 | REGIME_GR | 1918-11-24～1919-11-27 | de_jure | relation/2863749 v19 − 阿爾巴尼亞 − 保加利亞 | — | — | A1 |
| SOV_GR_A_3 | REGIME_GR | 1919-11-27～1920-08-10 | de_jure | relation/2863749 v19 − 阿爾巴尼亞 | — | EV_SEVRES | A1 |
| SOV_HU_PR_A_1 | REGIME_HU_PR | 1918-11-12～1918-12-01 | de_jure | relation/2693462 v49 − 斯洛維尼亞人、克羅埃西亞人和塞爾維亞人國 | — | EV_KSCS | A1 |
| SOV_HU_PR_A_2 | REGIME_HU_PR | 1918-12-01～1919-03-21 | de_jure | relation/2693462 v49 | EV_KSCS | EV_HU_SR | A1 |
| SOV_HU_PR_B | REGIME_HU_PR | 1919-08-01～1920-03-01 | de_jure | relation/2693462 v49 | EV_HU_SR_END | EV_HU_KINGDOM | A1 |
| SOV_HU_SR | REGIME_HU_SR | 1919-03-21～1919-08-01 | de_jure | relation/2693462 v49 | EV_HU_SR | EV_HU_SR_END | A1 |
| SOV_IS | REGIME_IS | 1918-12-01～1924-01-01 | de_jure | relation/2801981 v5 | EV_IS | — | A1 |
| SOV_IT_A | REGIME_IT | 1918-11-12～1920-07-16 | de_jure | relation/2696424 v118 | — | EV_SAINT_GERMAIN | A1 |
| SOV_IT_AEGEAN_IWA | REGIME_IT_AEGEAN | 1918-11-12～1921-01-01 | not_sovereign | relation/2830316 v10 | — | — | A1 |
| SOV_IT_JULIAN | REGIME_IT_JULIAN | 1918-11-12～1920-07-16 | not_sovereign | relation/2696325 v128 − relation/2696424 v118 | — | EV_SAINT_GERMAIN | A1 |
| SOV_KSCS_A_1 | REGIME_KSCS | 1918-12-01～1919-11-27 | de_jure | relation/2747828 v61 − 保加利亞 | EV_KSCS | — | A1 |
| SOV_KSCS_A_2 | REGIME_KSCS | 1919-11-27～1922-10-01 | de_jure | relation/2747828 v61 | — | — | A1 |
| SOV_LT_A | REGIME_LT | 1918-11-12～1923-01-19 | de_jure | relation/2693086 v44 | — | — | A1 |
| SOV_LV_A | REGIME_LV | 1918-11-18～1920-01-01 | de_jure | relation/2704702 v61 | EV_LV | — | A1 |
| SOV_LY_CY_IWA | REGIME_LY_CY | 1918-11-12～1924-01-01 | de_jure | relation/2803190 v11 | — | — | A1 |
| SOV_LY_TR_IWA | REGIME_LY_TR | 1918-11-12～1924-01-01 | de_jure | relation/2690837 v18 | — | — | A1 |
| SOV_MA_ES_A | REGIME_MA_ES | 1918-11-12～1921-06-01 | de_jure | relation/2860424 v10 | — | — | A1 |
| SOV_MA_FR_A_IWA | REGIME_MA_FR | 1918-11-12～1921-01-01 | de_jure | relation/2866016 v9 | — | — | A1 |
| SOV_MN | REGIME_MN_K | 1918-11-12～1918-11-26 | de_jure | relation/2739656 v22 | — | EV_PODGORICA | A1 |
| SOV_MORESNET_IWA | REGIME_MORESNET | 1918-11-12～1920-01-10 | de_jure | relation/2696520 v6 | — | EV_VERSAILLES | A1 |
| SOV_MR_IWA | REGIME_MR | 1918-11-12～1924-01-01 | de_jure | relation/2917211 v3 | — | — | A1 |
| SOV_MRNC_IWA | REGIME_MRNC | 1918-11-12～1919-09-01 | de_jure | relation/2891769 v9 | — | — | A1 |
| SOV_NO_A | REGIME_NO | 1918-11-12～1921-01-01 | de_jure | relation/2692537 v28 | — | — | A1 |
| SOV_OT_G_1 | REGIME_OT | 1918-11-12～1919-05-15 | de_jure | relation/2920989 v11 − relation/2848136 v6 − relation/2830316 v10 − relation/2855613 v8 | — | EV_SMYRNA | A1 |
| SOV_OT_G_2 | REGIME_OT | 1919-05-15～1920-08-10 | de_jure | relation/2920989 v11 − relation/2848136 v6 − relation/2830316 v10 − relation/2855613 v8 − 士麥那區 | EV_SMYRNA | EV_SEVRES | A1 |
| SOV_PL_A_1 | REGIME_PL | 1918-11-12～1918-11-13 | de_jure | relation/2855672 v42 − 德國 − 切申爭議區 − 烏克蘭 | — | EV_ZUNR | A1 |
| SOV_PL_A_2 | REGIME_PL | 1918-11-13～1919-03-10 | de_jure | relation/2855672 v42 − 德國 − 切申爭議區 − 西烏克蘭 − 烏克蘭 | EV_ZUNR | EV_UA_SSR | A1 |
| SOV_PL_A_3 | REGIME_PL | 1919-03-10～1919-07-17 | de_jure | relation/2855672 v42 − 德國 − 切申爭議區 − 西烏克蘭 | EV_UA_SSR | EV_ZUNR_END | A1 |
| SOV_PL_A_4 | REGIME_PL | 1919-07-17～1920-01-10 | de_jure | relation/2855672 v42 − 德國 − 切申爭議區 | EV_ZUNR_END | EV_VERSAILLES | A1 |
| SOV_RO_A_IWA | REGIME_RO | 1918-11-12～1918-12-01 | de_jure | relation/2693260 v64 ∪ 比薩拉比亞（WW1 第二批 SOV_RO_BESS 幾何） | — | EV_ALBA_IULIA | A1 |
| SOV_RO_B_1 | REGIME_RO | 1918-12-01～1919-11-27 | de_jure | relation/2693464 v67 − 保加利亞 | EV_ALBA_IULIA | — | A1 |
| SOV_RO_B_2_IWA | REGIME_RO | 1919-11-27～1920-08-10 | de_jure | relation/2693464 v67 | — | — | A1 |
| SOV_RS_A_IWA | REGIME_RS | 1918-11-12～1918-11-26 | de_jure | relation/2746681 v36 | — | EV_PODGORICA | A1 |
| SOV_RS_B_IWA | REGIME_RS | 1918-11-26～1918-12-01 | de_jure | relation/2746681 v36 ∪ relation/2739656 v22 | EV_PODGORICA | EV_KSCS | A1 |
| SOV_RSFSR_G | REGIME_RSFSR | 1918-11-12～1919-03-10 | de_jure | relation/2959042 v17 − 烏克蘭 − 白俄羅斯 − 北高加索山地共和國 | — | — | A1 |
| SOV_RSFSR_H_1 | REGIME_RSFSR | 1919-03-10～1919-09-01 | de_jure | relation/2957450 v41 − 白俄羅斯 − 北高加索山地共和國 | — | — | A1 |
| SOV_RSFSR_H_2 | REGIME_RSFSR | 1919-09-01～1920-04-04 | de_jure | relation/2957450 v41 − 白俄羅斯 | — | — | A1 |
| SOV_SCS_A | REGIME_SCS | 1918-11-12～1918-11-24 | not_sovereign | relation/2747879 v43 − 義大利佔領的原奧匈領土 | — | EV_SCS_SERBIA | A1 |
| SOV_SCS_B | REGIME_SCS | 1918-11-24～1918-12-01 | not_sovereign | relation/2747878 v41 − 義大利佔領的原奧匈領土 | EV_SCS_SERBIA | EV_KSCS | A1 |
| SOV_SE_IWA | REGIME_SE | 1918-11-12～1924-01-01 | de_jure | relation/2692524 v33 | — | — | A1 |
| SOV_SMYRNA | REGIME_SMYRNA | 1919-05-15～1922-09-09 | not_sovereign | (relation/2863750 v21 − relation/2863749 v19) 的安納托利亞部分 | EV_SMYRNA | EV_SMYRNA_FALL | A1 |
| SOV_TN_IWA | REGIME_TN | 1918-11-12～1924-01-01 | de_jure | relation/2690947 v20 | — | — | A1 |
| SOV_UA_PR_1 | REGIME_UA_PR | 1918-11-12～1918-11-13 | de_jure | relation/2694815 v77 − 羅馬尼亞 | — | EV_ZUNR | A1 |
| SOV_UA_PR_2 | REGIME_UA_PR | 1918-11-13～1919-03-10 | de_jure | relation/2694815 v77 − 羅馬尼亞 − 西烏克蘭 | EV_ZUNR | EV_UA_SSR | A1 |
| SOV_UA_SSR_1 | REGIME_UA_SSR | 1919-03-10～1920-04-04 | de_jure | relation/2848214 v43 | EV_UA_SSR | — | A1 |
| SOV_UK_GBI_1 | REGIME_UK_GBI | 1918-11-12～1922-12-05 | de_jure | relation/2828388 v26 | — | — | A1 |
| SOV_US_IWA | REGIME_US | 1918-11-12～1924-01-01 | de_jure | relation/2874803 v33 − relation/2889834 v1 | — | — | A1 |
| SOV_ZUNR | REGIME_ZUNR | 1918-11-13～1919-07-17 | not_sovereign | relation/2855672 v42 ∩ 東加利西亞（手繪近似線（build/make_requests.py）） | EV_ZUNR | EV_ZUNR_END | A1 |
| SOV_ALEPPO | REGIME_ALEPPO | 1920-09-01～1922-06-28 | not_sovereign | relation/2864000 v6 | — | — | A2 |
| SOV_AM_SSR | REGIME_AM_SSR | 1920-12-02～1922-03-12 | de_jure | relation/2698022 v11 | EV_ALEXANDROPOL | EV_TSFSR | A2 |
| SOV_AZ_SSR_A | REGIME_AZ_SSR | 1920-04-28～1921-10-13 | de_jure | relation/2697987 v15 | EV_AZ_SSR | EV_KARS | A2 |
| SOV_CLT | REGIME_CLT | 1920-10-12～1922-04-18 | not_sovereign | relation/2855672 v42 ∩ 維爾紐斯地區（手繪近似線（build/make_requests.py）） | EV_CLT | EV_CLT_ANNEX | A2 |
| SOV_CS_B | REGIME_CS | 1920-02-04～1920-05-19 | de_jure | relation/2747876 v57 − 切申爭議區 | — | — | A2 |
| SOV_CS_C | REGIME_CS | 1920-05-19～1920-08-10 | de_jure | relation/2693465 v92 − 切申爭議區 | — | — | A2 |
| SOV_CS_D_1 | REGIME_CS | 1920-08-10～1920-08-28 | de_jure | relation/2747893 v63 − 切申爭議區 | — | — | A2 |
| SOV_CS_D_2 | REGIME_CS | 1920-08-28～1924-01-01 | de_jure | relation/2747893 v63 | — | — | A2 |
| SOV_DAMASCUS_A | REGIME_DAMASCUS | 1920-09-01～1921-05-01 | not_sovereign | relation/2863995 v5 | — | — | A2 |
| SOV_DANZIG_A | REGIME_DANZIG | 1920-11-15～1920-12-24 | de_jure | relation/2696571 v16 | EV_DANZIG_IWA | — | A2 |
| SOV_DANZIG_ALLIED | REGIME_DANZIG_ALLIED | 1920-01-10～1920-11-15 | not_sovereign | relation/2696571 v16 | EV_VERSAILLES | EV_DANZIG_IWA | A2 |
| SOV_DE_C | REGIME_DE | 1920-01-10～1920-02-04 | de_jure | relation/2692483 v307 | EV_VERSAILLES | — | A2 |
| SOV_DE_D | REGIME_DE | 1920-02-04～1920-06-15 | de_jure | relation/2696518 v212 | — | EV_SCHLESWIG_TRANSFER | A2 |
| SOV_DE_E | REGIME_DE | 1920-06-15～1920-08-15 | de_jure | relation/2696517 v219 | EV_SCHLESWIG_TRANSFER | — | A2 |
| SOV_DE_F | REGIME_DE | 1920-08-15～1920-12-24 | de_jure | relation/2741459 v192 | — | — | A2 |
| SOV_DE_G | REGIME_DE | 1920-12-24～1922-06-20 | de_jure | relation/2696516 v221 | — | EV_USIL_TRANSFER | A2 |
| SOV_DK_B | REGIME_DK | 1920-06-15～1921-05-21 | de_jure | relation/2692238 v45 − 冰島 | EV_SCHLESWIG_TRANSFER | — | A2 |
| SOV_ETHRACE | REGIME_ETHRACE | 1920-08-10～1922-10-11 | not_sovereign | (relation/2863750 v21 − relation/2863749 v19) 的歐洲部分 | EV_SEVRES | EV_MUDANYA | A2 |
| SOV_FIUME_FS | REGIME_FIUME_FS | 1920-12-30～1924-01-01 | de_jure | relation/2696321 v25 | EV_FIUME_FS | — | A2 |
| SOV_GE_A_3 | REGIME_GE | 1920-07-07～1921-02-25 | de_jure | relation/2698086 v23 | EV_BATUMI_END | EV_GE_SSR | A2 |
| SOV_GE_SSR_A | REGIME_GE_SSR | 1921-02-25～1921-03-31 | de_jure | relation/2698086 v23 | EV_GE_SSR | — | A2 |
| SOV_GR_B_1 | REGIME_GR | 1920-08-10～1922-09-09 | de_jure | relation/2863750 v21 − 阿爾巴尼亞 − 士麥那區 − 東色雷斯 | EV_SEVRES | EV_SMYRNA_FALL | A2 |
| SOV_HU_A | REGIME_HU | 1920-03-01～1921-11-10 | de_jure | relation/2693462 v49 | EV_HU_KINGDOM | — | A2 |
| SOV_IRAQ | REGIME_IRAQ | 1920-08-10～1924-01-01 | not_sovereign | relation/2839465 v22 | EV_SEVRES | — | A2 |
| SOV_IT_B | REGIME_IT | 1920-07-16～1924-01-01 | de_jure | relation/2696325 v128 | EV_SAINT_GERMAIN | — | A2 |
| SOV_LEBANON | REGIME_LEBANON | 1920-09-01～1924-01-01 | not_sovereign | relation/2831357 v14 | — | — | A2 |
| SOV_LEVANT | REGIME_LEVANT | 1920-08-10～1920-09-01 | not_sovereign | relation/2863754 v9 | EV_SEVRES | — | A2 |
| SOV_MA_FR_B_IWA | REGIME_MA_FR | 1921-01-01～1924-01-01 | de_jure | relation/2866015 v9 | — | — | A2 |
| SOV_MEMEL | REGIME_MEMEL | 1920-01-10～1923-01-19 | not_sovereign | relation/2691476 v25 | EV_VERSAILLES | EV_MEMEL_IWA | A2 |
| SOV_NO_B | REGIME_NO | 1921-01-01～1924-01-01 | de_jure | relation/2851797 v14 | — | — | A2 |
| SOV_OT_H_1 | REGIME_OT | 1920-08-10～1920-12-02 | de_jure | relation/2958040 v3 − 喬治亞 − 亞美尼亞 | EV_SEVRES | EV_ALEXANDROPOL | A2 |
| SOV_OT_H_2 | REGIME_OT | 1920-12-02～1921-01-01 | de_jure | relation/2958040 v3 − 喬治亞 | EV_ALEXANDROPOL | — | A2 |
| SOV_OT_H_3 | REGIME_OT | 1921-01-01～1921-10-13 | de_jure | relation/2958040 v3 − 喬治亞 − italian-aegean-islands | — | — | A2 |
| SOV_PALESTINE | REGIME_PALESTINE | 1920-08-10～1924-01-01 | not_sovereign | relation/2848316 v14 | EV_SEVRES | — | A2 |
| SOV_PL_A_5 | REGIME_PL | 1920-01-10～1920-08-15 | de_jure | relation/2855672 v42 − 德國 − 切申爭議區 | EV_VERSAILLES | — | A2 |
| SOV_PL_A_6 | REGIME_PL | 1920-08-15～1920-08-28 | de_jure | relation/2855672 v42 − 切申爭議區 | — | — | A2 |
| SOV_PL_A_7 | REGIME_PL | 1920-08-28～1920-10-12 | de_jure | relation/2855672 v42 | — | EV_CLT | A2 |
| SOV_PL_A_8 | REGIME_PL | 1920-10-12～1922-04-18 | de_jure | relation/2855672 v42 − 中立陶宛 | EV_CLT | EV_CLT_ANNEX | A2 |
| SOV_RO_B_3_IWA | REGIME_RO | 1920-08-10～1921-01-01 | de_jure | relation/2693464 v67 − 捷克斯洛伐克 | — | — | A2 |
| SOV_RSFSR_H_3 | REGIME_RSFSR | 1920-04-04～1920-04-06 | de_jure | relation/2957450 v41 − 白俄羅斯 − 南俄政府 | — | — | A2 |
| SOV_RSFSR_I | REGIME_RSFSR | 1920-04-06～1920-04-28 | de_jure | relation/2958036 v34 − 白俄羅斯 − 南俄政府 | — | — | A2 |
| SOV_RSFSR_J | REGIME_RSFSR | 1920-04-28～1920-10-14 | de_jure | relation/2957458 v41 − 白俄羅斯 − 南俄政府 − 亞塞拜然 | — | — | A2 |
| SOV_RSFSR_K_1 | REGIME_RSFSR | 1920-10-14～1920-11-17 | de_jure | relation/2959040 v28 − 白俄羅斯 − 南俄政府 − 亞塞拜然 | — | EV_CRIMEA | A2 |
| SOV_RSFSR_K_2 | REGIME_RSFSR | 1920-11-17～1921-08-14 | de_jure | relation/2959040 v28 − 白俄羅斯 − 亞塞拜然 | EV_CRIMEA | — | A2 |
| SOV_SAAR | REGIME_SAAR | 1920-01-10～1924-01-01 | not_sovereign | relation/2690373 v23 | EV_VERSAILLES | — | A2 |
| SOV_SOUTH_RUSSIA | REGIME_SOUTH_RUSSIA | 1920-04-04～1920-11-17 | not_sovereign | relation/2854270 v10 | — | EV_CRIMEA | A2 |
| SOV_TRANSJORDAN | REGIME_TRANSJORDAN | 1920-08-10～1924-01-01 | not_sovereign | relation/2848317 v15 | EV_SEVRES | — | A2 |
| SOV_UA_SSR_2 | REGIME_UA_SSR | 1920-04-04～1920-11-17 | de_jure | relation/2848214 v43 − 南俄政府 | — | EV_CRIMEA | A2 |
| SOV_UA_SSR_3 | REGIME_UA_SSR | 1920-11-17～1922-12-30 | de_jure | relation/2848214 v43 | EV_CRIMEA | EV_USSR | A2 |
| SOV_ABKHAZ | REGIME_ABKHAZ_SSR | 1921-03-31～1921-12-16 | not_sovereign | relation/2957464 v2 | — | — | A3 |
| SOV_AT_R1_A_2 | REGIME_AT_R1 | 1921-10-04～1921-11-10 | de_jure | relation/2692711 v75 − 萊塔班國 | EV_LAJTA | EV_BURGENLAND | A3 |
| SOV_AT_R1_B | REGIME_AT_R1 | 1921-11-10～1922-10-01 | de_jure | relation/2695634 v67 | EV_BURGENLAND | — | A3 |
| SOV_AZ_SSR_B | REGIME_AZ_SSR | 1921-10-13～1922-03-12 | de_jure | relation/2697988 v13 | EV_KARS | EV_TSFSR | A3 |
| SOV_DAMASCUS_B | REGIME_DAMASCUS | 1921-05-01～1922-06-28 | not_sovereign | relation/2863994 v4 | — | — | A3 |
| SOV_DE_H_1 | REGIME_DE | 1922-06-20～1923-01-11 | de_jure | relation/2696515 v214 | EV_USIL_TRANSFER | EV_RUHR | A3 |
| SOV_DE_H_2 | REGIME_DE | 1923-01-11～1924-01-01 | de_jure | relation/2696515 v214 − 魯爾佔領區 | EV_RUHR | — | A3 |
| SOV_DK_C | REGIME_DK | 1921-05-21～1924-01-01 | de_jure | relation/2850547 v24 − 冰島 | — | — | A3 |
| SOV_DRUZE_A | REGIME_DRUZE | 1921-05-01～1922-03-04 | not_sovereign | relation/2864007 v2 | — | — | A3 |
| SOV_DRUZE_B | REGIME_DRUZE | 1922-03-04～1924-01-01 | not_sovereign | relation/2864006 v1 | — | — | A3 |
| SOV_EG_K | REGIME_EG_K | 1922-02-28～1924-01-01 | de_jure | relation/2803204 v15 | EV_EG_K | — | A3 |
| SOV_ES_B_IWA | REGIME_ES_K | 1921-06-01～1924-01-01 | de_jure | relation/2860485 v24 − 西屬摩洛哥 | — | — | A3 |
| SOV_GE_SSR_B | REGIME_GE_SSR | 1921-03-31～1921-10-13 | de_jure | relation/2957462 v4 | — | — | A3 |
| SOV_GE_SSR_C | REGIME_GE_SSR | 1921-10-13～1921-12-16 | de_jure | relation/2957465 v4 | EV_KARS | — | A3 |
| SOV_GE_SSR_D | REGIME_GE_SSR | 1921-12-16～1922-03-12 | de_jure | relation/2957461 v5 | — | EV_TSFSR | A3 |
| SOV_GNA | REGIME_GNA | 1922-11-01～1923-10-29 | de_jure | relation/2958039 v3 − italian-aegean-islands | EV_SULTANATE_END | EV_TR_REPUBLIC | A3 |
| SOV_GR_B_2 | REGIME_GR | 1922-09-09～1922-10-11 | de_jure | relation/2863750 v21 − 阿爾巴尼亞 − 東色雷斯 | EV_SMYRNA_FALL | EV_MUDANYA | A3 |
| SOV_GR_C | REGIME_GR | 1922-10-11～1924-01-01 | de_jure | relation/2863749 v19 − 阿爾巴尼亞 | EV_MUDANYA | — | A3 |
| SOV_IFS | REGIME_IFS | 1922-12-06～1924-01-01 | de_jure | relation/2697727 v27 | EV_IFS | — | A3 |
| SOV_KSCS_B | REGIME_KSCS | 1922-10-01～1924-01-01 | de_jure | relation/2858752 v11 | — | — | A3 |
| SOV_LAJTA | REGIME_LAJTA | 1921-10-04～1921-11-10 | not_sovereign | relation/2747802 v11 | EV_LAJTA | EV_BURGENLAND | A3 |
| SOV_MA_ES_B | REGIME_MA_ES | 1921-06-01～1924-01-01 | de_jure | relation/2860423 v10 | — | — | A3 |
| SOV_OT_H_4 | REGIME_OT | 1921-10-13～1922-11-01 | de_jure | relation/2958040 v3 − italian-aegean-islands | — | EV_SULTANATE_END | A3 |
| SOV_PL_A_9 | REGIME_PL | 1922-04-18～1922-06-20 | de_jure | relation/2855672 v42 | EV_CLT_ANNEX | EV_USIL_TRANSFER | A3 |
| SOV_PL_B | REGIME_PL | 1922-06-20～1924-01-01 | de_jure | relation/2741472 v117 | EV_USIL_TRANSFER | — | A3 |
| SOV_RIF | REGIME_RIF | 1921-09-18～1924-01-01 | not_sovereign | relation/2860425 v5 | EV_RIF | — | A3 |
| SOV_RSFSR_L_1 | REGIME_RSFSR | 1921-08-14～1921-10-13 | de_jure | relation/2957470 v41 − 白俄羅斯 − 亞塞拜然 | — | EV_KARS | A3 |
| SOV_RSFSR_L_2 | REGIME_RSFSR | 1921-10-13～1922-03-12 | de_jure | relation/2957470 v41 − 白俄羅斯 − 亞塞拜然 | EV_KARS | — | A3 |
| SOV_RSFSR_M | REGIME_RSFSR | 1922-03-12～1922-11-15 | de_jure | relation/2957457 v42 − 白俄羅斯 | — | — | A3 |
| SOV_RSFSR_N | REGIME_RSFSR | 1922-11-15～1922-12-30 | de_jure | relation/2958035 v35 − 白俄羅斯 | — | EV_USSR | A3 |
| SOV_RUHR | REGIME_RUHR | 1923-01-11～1924-01-01 | not_sovereign | relation/2696515 v214 ∩ 魯爾區（手繪近似線（build/make_requests.py）） | EV_RUHR | — | A3 |
| SOV_SU | REGIME_SU | 1922-12-30～1924-01-01 | de_jure | relation/2800978 v112 | EV_USSR | — | A3 |
| SOV_SYR_FED | REGIME_SYR_FED | 1922-06-28～1924-01-01 | not_sovereign | relation/2863992 v8 | — | — | A3 |
| SOV_TR_A | REGIME_TR | 1923-10-29～1924-01-01 | de_jure | relation/2958039 v3 − italian-aegean-islands | EV_TR_REPUBLIC | — | A3 |
| SOV_TSFSR | REGIME_TSFSR | 1922-03-12～1922-12-30 | de_jure | relation/2698093 v24 | EV_TSFSR | EV_USSR | A3 |
| SOV_UK_GBI_2 | REGIME_UK_GBI | 1922-12-05～1922-12-06 | de_jure | relation/2828388 v26 − united-kingdom | — | EV_IFS | A3 |

## 佔領歸屬

| placeholder | 被佔領 | 佔領方 | 管理 | 期間 | 共同 | 子批 |
|---|---|---|---|---|---|---|
| OCC_IT_AEGEAN_2 | REGIME_IT_AEGEAN | REGIME_IT | military_administration | 1918-11-12～1921-01-01 |  | A1 |
| OCC_IT_JULIAN | REGIME_IT_JULIAN | REGIME_IT | military_administration | 1918-11-12～1920-07-16 |  | A1 |
| OCC_FIUME_IA | REGIME_FIUME_IA | REGIME_IT | military_administration | 1918-11-17～1919-09-12 | 是 | A1 |
| OCC_SMYRNA | REGIME_SMYRNA | REGIME_GR | military_administration | 1919-05-15～1922-09-09 |  | A1 |
| OCC_BATUMI | REGIME_BATUMI | REGIME_UK_GBI | military_administration | 1918-12-01～1920-07-07 |  | A1 |
| OCC_MEMEL | REGIME_MEMEL | REGIME_FR3 | civil_administration | 1920-01-10～1923-01-19 |  | A2 |
| OCC_DANZIG_ALLIED | REGIME_DANZIG_ALLIED | REGIME_UK_GBI | civil_administration | 1920-01-10～1920-11-15 | 是 | A2 |
| OCC_ETHRACE | REGIME_ETHRACE | REGIME_GR | military_administration | 1920-08-10～1922-10-11 |  | A2 |
| OCC_CLT | REGIME_CLT | REGIME_PL | military_administration | 1920-10-12～1922-04-18 |  | A2 |
| OCC_RUHR | REGIME_RUHR | REGIME_FR3 | military_administration | 1923-01-11～1924-01-01 | 是 | A3 |

## 衝突紀錄

| placeholder | A | B | 起 | 迄 | 位置 | 子批 |
|---|---|---|---|---|---|---|
| CF_EE_RSFSR | REGIME_EE | REGIME_RSFSR | EV_EE_WAR | EV_TARTU_EE | [28.2, 59.37]：納爾瓦（1918-11-28 紅軍進攻處，固定點） | A1 |
| CF_LV_RSFSR | REGIME_LV | REGIME_RSFSR | EV_LV_WAR | EV_RIGA_LV | [24.1, 56.95]：里加（1919-01 失守、1919-05 收復，固定點） | A1 |
| CF_LT_RSFSR | REGIME_LT | REGIME_RSFSR | EV_LT_WAR | EV_MOSCOW_LT | [25.28, 54.69]：維爾紐斯（固定點） | A1 |
| CF_PL_ZUNR | REGIME_PL | REGIME_ZUNR | EV_ZUNR | EV_ZUNR_END | [24.03, 49.84]：利沃夫（1918-11 巷戰處，固定點） | A1 |
| CF_PL_RSFSR | REGIME_PL | REGIME_RSFSR | EV_PL_SOV_WAR | EV_RIGA_IWA | [21.0, 52.25]：華沙（1920-08 華沙戰役，固定點） | A1 |
| CF_RO_HUSR | REGIME_RO | REGIME_HU_SR | EV_HU_WAR | EV_HU_SR_END | [20.2, 46.25]：提薩河（羅、匈前線，固定點） | A1 |
| CF_CS_HUSR | REGIME_CS | REGIME_HU_SR | EV_HU_WAR | EV_HU_SR_END | [20.8, 48.3]：米什科爾茨—斯洛伐克南部（固定點） | A1 |
| CF_GR_GNA | REGIME_GR | REGIME_GNA | EV_SMYRNA | EV_MUDANYA | [30.5, 39.6]：薩卡里亞河—埃斯基謝希爾（希土戰爭主戰場，固定點） | A1 |
| CF_FR_GNA | REGIME_FR3 | REGIME_GNA | EV_GNA | EV_ANKARA | [36.93, 37.58]：馬拉什—奇里乞亞（法土戰爭，固定點） | A2 |
| CF_AM_GNA | REGIME_AM | REGIME_GNA | EV_AM_TR_WAR | EV_ALEXANDROPOL | [43.1, 40.6]：卡爾斯（固定點） | A2 |
| CF_RSFSR_GE | REGIME_RSFSR | REGIME_GE | EV_GE_INV | EV_GE_SSR | [44.8, 41.7]：提比里斯（固定點） | A2 |

## 近似與未畫（待查證）

- 波蘭：1918-11～1922-06 用 OHM 1922 年波蘭外框（2855672）扣掉同期較高優先的德國、西烏克蘭、切欣、中立陶宛、白俄、烏克蘭；OHM 1920～1921 年波蘭關係是未閉合環，不能用。波蘇戰爭 1920 年前線往返（基輔、華沙）未畫。
- 西烏克蘭人民共和國（ZUNR）、中立陶宛（Central Lithuania）、魯爾佔領區：經緯度點手繪近似，再與 OHM 外框求交。
- 色佛爾條約未生效，不照它畫：鄂圖曼 [1918-11-12, 1920-08-10) 沿用第二批停戰後外框，之後用 OHM 2958040 到 1922-11-01 蘇丹制廢除；安卡拉大國民議會政府用 OHM 2958039 到 1923-10-29，之後由土耳其共和國接續。士麥那與東色雷斯從希臘 1920 年外框（2863750 − 2863749）依代表點切出（北緯 40.45° 以北，或 39.95° 以北且東經 26.9° 以西算東色雷斯）。
- 匈牙利 1918-11～1921 全期用特里亞農條約界線；羅馬尼亞軍 1919 年進佔布達佩斯、塞爾維亞軍佔領佩奇—巴蘭尼亞（到 1921-08）未畫。
- 外西凡尼亞與布科維納 1918-11-12～12-01（阿爾巴尤利亞決議前）、亞爾薩斯—洛林 11-12～11-22、伏伊伏丁那的歸屬過渡用最接近的政權，日期待查證。
- 開發庫既有法國紀錄（1918-11-22 起）只到北緯 34°，阿爾及利亞南部撒哈拉在 1918-11-22 後留白（既有資料，本批未改）。
- 高加索：喬治亞、亞美尼亞、亞塞拜然 1920～1921 年蘇維埃化用政權切換，1920 年土亞戰爭的卡爾斯割讓以 1921 年卡爾斯條約線一次處理；阿布哈茲、巴統另立。
- 北非里夫共和國用 OHM 外框（1921-09-18 起）；敘利亞託管地內畫大馬士革、阿勒坡、德魯茲山、大黎巴嫩與 1922 年敘利亞聯邦，阿拉維國未另立（併在黎凡特／聯邦外框，待查證）。
- 阿爾巴尼亞與希臘在北伊庇魯斯的小片重疊以阿爾巴尼亞優先；保加利亞西部邊區在納伊條約生效（1919-11-27）前歸保加利亞。
- 事件標待查證者（見上表）只有日期與摘要，沒有正式出處，送出時不附引用。
