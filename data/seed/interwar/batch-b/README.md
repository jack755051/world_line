# 兩次大戰之間 B 批：1924 → 1938（DRAFT，待 Tai 檢查）

範圍：歐洲、北非、近東（OHM 裁切框同 A 批，北緯 15° 以北、西經 20°～東經 60°）。把 A 批迄於 1924-01-01（試驗終點）的 34 筆主權紀錄與魯爾佔領歸屬**先撤後增**延長迄日，接上開發庫既有 1924～1939 紀錄（波蘭 1924-06-22、土耳其 1924-08-06、挪威 1925-08-14、蘇聯 1926-01-01、阿爾巴尼亞王國 1928-09-01、義大利 1929-06-07、南斯拉夫 1929-10-03、丹麥與瑞典 1932-01-30、德國與捷克斯洛伐克 1936-07-03、希臘 1936-09-17、美國 1937-07-07、愛爾 1937-12-29、西班牙國 1939-04-01、土耳其 1939-06-29 起）。沒有後續資料的北非、近東、冰島暫迄 1939-01-01（本批試驗終點，不是政權迄日）。
**只寫入本機開發庫**（worldline-borders-dev，API 127.0.0.1:5052，DB 5442）；寫入 appdb_ww2（5051）要另取得 Tai 同意。安卡拉／鄂圖曼 1920～1922 年紀錄未動（等 Tai 決定）。

## 子批

| 子批 | 紀錄起日 | 請求數 |
|---|---|---|
| B1 | [（A 批延長紀錄的原起日）, 1929-01-01) | 154 |
| B2 | [1929-01-01, 1936-01-01) | 14 |
| B3 | [1936-01-01, （1939-06-29）) | 33 |

每筆紀錄用真實起訖，依起日分子批；來源、政權、事件放在第一個引用它們的子批。子批要依序送。撤回請求放在重送紀錄最早的子批：B1 撤回 A 批 34 筆主權紀錄與 OCC_RUHR，B2 撤回開發庫既有西班牙共和國紀錄 SOV_R2860484（起日 1931-01-01 是 OHM 年份）後以 1931-04-14 起重送。

## 檔案

| 檔案 | 說明 |
|---|---|
| `build/fetch.py` | 依 relation id 從 OHM Overpass 抓關係，存 `raw/`（不進版控） |
| `build/build.py` | 組多邊形 → 框裁切 → Natural Earth 陸地裁切 → 簡化 → `borders-ohm-interwar-b.geojson`＋`ohm-manifest.json` |
| `build/make_requests.py` | 優先序引擎（高優先紀錄扣出低優先、低優先在高優先起訖日切段；開發庫既有紀錄為最高優先）、手繪近似、QA（每個切點日檢查重疊）、產生 `requests/B{1,2,3}/*.json`、`interwar-b-derived.geojson`、`qa.json`；需要 A 批目錄（`../batch-a`，或環境變數 IWA） |
| `build/readme.py` | 產生本檔 |
| `send_seed.py` | 依子批送出（預設 dry-run；拒絕 5051；API key 從 --env 安靜讀取） |
| `db-export/`（不進版控） | 開發庫唯讀匯出：1918-11～1939-07 間既有主權紀錄、西班牙共和國紀錄、A 批 id 表；備份在 `~/01_Projects/world_line_backups/` |

用法（在本目錄）：
```
P="--prior ../../../../.dev/sent-ids.borders-dev.json --prior ../../../../.dev/sent-ids.borders-us-dev.json --prior ../../../../.dev/sent-ids.ww1-balkans-1908-1914-dev.json --prior ../../../../.dev/sent-ids.ww1-war-1914-1918-dev.json --prior ../../../../.dev/sent-ids.interwar-a-dev.json"
python3 send_seed.py --sub B1 --base http://127.0.0.1:5052 --env ../../../../.env.borders-dev $P --ids ../../../../.dev/sent-ids.interwar-b-dev.json [--send]
```

OHM Overpass `osm_base`：2026-10-31T20:43:39Z（UTC）。來源：條約原文（國際聯盟條約集 LNTS 第 2、28、54 卷 PDF）、FRUS 巴黎和會第 XIII 卷（凡爾賽和約）、FRUS 1925 第 I 卷、1931 第 II 卷、1936 第 I、II 卷；找不到正式出處的事件標 **待查證**。

## 事件

| placeholder | 日期 | 類型 | 摘要 | 出處 | 子批 |
|---|---|---|---|---|---|
| EV_ROME_1924 | 1924-01-27 | treaty | 義大利與塞爾維亞人、克羅埃西亞人和斯洛維尼亞人王國簽羅馬條約：阜姆歸義大利、蘇沙克歸南方 | **待查證** | B1 |
| EV_FIUME_ANNEX | 1924-02-22 | political | 阜姆正式併入義大利 | **待查證** | B1 |
| EV_JAVORINA | 1924-03-12 | political | 波蘭與捷克斯洛伐克在亞沃日納（塔特拉山區）的邊界依國際聯盟／大使會議裁定調整 | **待查證** | B1 |
| EV_GR_REP | 1924-03-25 | political | 希臘國民議會廢除君主制，宣布成立共和國 | **待查證** | B1 |
| EV_LAUSANNE_INFORCE | 1924-08-06 | treaty | 洛桑條約生效：英、義、日交存批准書 | SRC_LNTS_28 No. 701, p. 13, note (1) | B1 |
| EV_SU_UZ_TM | 1924-10-27 | political | 中亞民族劃界：成立烏茲別克與土庫曼蘇維埃社會主義共和國 | **待查證** | B1 |
| EV_SY_STATE | 1925-01-01 | political | 大馬士革國與阿勒坡國合併為敘利亞國 | **待查證** | B1 |
| EV_SU_1925 | 1925-01-20 | treaty | 蘇日基本條約（北京）：日本撤出北庫頁島 | **待查證** | B1 |
| EV_AL_REP | 1925-01-21 | political | 阿爾巴尼亞制憲議會宣布成立共和國 | SRC_FRUS_1925V1 Doc. 329, p. 491 | B1 |
| EV_RIF_FR | 1925-04-12 | war | 里夫軍進攻法屬摩洛哥沃爾加河谷，法國參戰 | **待查證** | B1 |
| EV_CY_COLONY | 1925-05-01 | political | 賽普勒斯成為英國直轄殖民地 | **待查證** | B1 |
| EV_TANGIER | 1925-06-01 | treaty | 丹吉爾國際共管區規約生效 | SRC_LNTS_28 No. 729, p. 541 | B1 |
| EV_SVALBARD | 1925-08-14 | treaty | 斯匹茨卑爾根條約生效：挪威正式接管斯瓦巴 | SRC_LNTS_2 No. 41, p. 7 | B1 |
| EV_RUHR_END | 1925-08-25 | political | 法比軍撤出魯爾區（道威斯計畫後） | **待查證** | B1 |
| EV_LOCARNO | 1925-10-16 | treaty | 洛迦諾公約簽字：德、法、比、英、義萊茵保證公約 | SRC_LNTS_54 No. 1292, p. 289 | B1 |
| EV_COLOGNE_EVAC | 1926-01-31 | political | 協約國撤出萊茵蘭科隆區 | **待查證** | B1 |
| EV_LB_REP | 1926-05-23 | political | 大黎巴嫩頒布憲法，改稱黎巴嫩共和國（仍為法國委任統治） | **待查證** | B1 |
| EV_RIF_END | 1926-05-27 | war | 阿卜杜勒—克里姆向法軍投降，里夫戰爭結束 | **待查證** | B1 |
| EV_AL_YU_1926 | 1926-07-26 | political | 阿爾巴尼亞與南斯拉夫邊界依大使會議裁定調整（聖瑙姆等地） | **待查證** | B1 |
| EV_AL_KINGDOM | 1928-09-01 | political | 阿爾巴尼亞改制王國，索古稱國王索古一世 | **待查證** | B1 |
| EV_LATERAN | 1929-06-07 | treaty | 拉特朗條約批准書交換生效，梵蒂岡城國成立 | **待查證** | B1 |
| EV_YU | 1929-10-03 | political | 塞爾維亞人、克羅埃西亞人和斯洛維尼亞人王國改稱南斯拉夫王國 | **待查證** | B1 |
| EV_SU_TJ | 1929-10-16 | political | 塔吉克升格為加盟共和國 | **待查證** | B2 |
| EV_KOBLENZ_EVAC | 1929-11-30 | political | 協約國撤出萊茵蘭科布倫茨區（海牙會議後） | **待查證** | B1 |
| EV_SY_REP | 1930-05-14 | political | 法國高級專員頒布敘利亞憲法，敘利亞國改稱敘利亞共和國 | **待查證** | B1 |
| EV_MAINZ_EVAC | 1930-06-30 | political | 法軍撤出萊茵蘭美因茲區，協約國萊茵蘭佔領結束 | **待查證** | B1 |
| EV_ES_REPUBLIC | 1931-04-14 | political | 西班牙宣布成立共和國，國王阿方索十三世離境 | SRC_FRUS_1931V2 Doc. 1056, p. 985 | B1 |
| EV_IQ_INDEP | 1932-10-03 | political | 伊拉克加入國際聯盟，委任統治結束 | **待查證** | B1 |
| EV_LY_UNIFY | 1934-01-01 | political | 的黎波里塔尼亞與昔蘭尼加合為義屬利比亞 | **待查證** | B1 |
| EV_SAAR_PLEB | 1935-01-13 | political | 薩爾公民投票：九成選民贊成回歸德國 | SRC_FRUS_PPC13 凡爾賽和約 Part III, Section IV, Annex, Chapter III, §§34–35 | B2 |
| EV_SAAR_RETURN | 1935-03-01 | political | 薩爾回歸德國 | **待查證** | B1 |
| EV_GR_MONARCHY | 1935-11-03 | political | 希臘公民投票恢復君主制（喬治二世復位） | **待查證** | B1 |
| EV_RHINE_REMIL | 1936-03-07 | campaign | 德軍開進萊茵非軍事區，德國宣布廢止洛迦諾公約 | SRC_FRUS_1936V1 Doc. 183, pp. 214–216；SRC_FRUS_1936V1 Doc. 182 | B3 |
| EV_ES_COUP | 1936-07-17 | war | 摩洛哥西班牙駐軍起事，西班牙內戰開始 | SRC_FRUS_1936V2 Doc. 357, p. 440 | B2 |
| EV_SY_1936 | 1936-09-09 | treaty | 法敘條約簽字：德魯茲山與拉塔基亞併入敘利亞 | **待查證** | B1 |
| EV_ES_MADRID | 1936-11-07 | campaign | 國民軍兵臨馬德里，馬德里保衛戰開始 | **待查證** | B3 |
| EV_SU_1936 | 1936-12-05 | political | 蘇聯新憲法：外高加索聯邦解散，哈薩克、吉爾吉斯升格加盟共和國 | **待查證** | B3 |
| EV_MALAGA | 1937-02-08 | campaign | 國民軍攻佔馬拉加 | **待查證** | B3 |
| EV_BILBAO | 1937-06-19 | campaign | 國民軍攻佔畢爾包 | **待查證** | B3 |
| EV_SANTANDER | 1937-08-26 | campaign | 國民軍攻佔桑坦德 | **待查證** | B3 |
| EV_GIJON | 1937-10-21 | campaign | 國民軍攻佔希洪，北方戰線結束 | **待查證** | B3 |
| EV_IE_CONST | 1937-12-29 | political | 愛爾蘭新憲法生效，愛爾蘭自由邦改稱愛爾（Éire） | **待查證** | B1 |
| EV_VINAROS | 1938-04-15 | campaign | 國民軍抵達比納羅斯地中海岸，共和國控制區被切成兩半 | **待查證** | B3 |
| EV_HATAY_STATE | 1938-09-02 | political | 亞歷山大勒塔桑賈克議會宣布成立哈塔伊國（法土共管下） | **待查證** | B3 |
| EV_CATALONIA | 1939-02-10 | campaign | 國民軍抵達法國邊境，加泰隆尼亞戰役結束（梅諾卡島 2-09 投降） | **待查證** | B3 |

## 主權紀錄

| placeholder | 政權 | 期間 | 層級 | 幾何 | 起事件 | 迄事件 | 子批 |
|---|---|---|---|---|---|---|---|
| SOV_ALAWITE | REGIME_ALAWITE | 1925-01-01～1936-09-09 | not_sovereign | relation/2863987 v5 | — | EV_SY_1936 | B1 |
| SOV_AL_B_X | REGIME_AL_PR | 1918-11-24～1925-01-21 | de_jure | relation/2800556 v23 − kingdom-of-serbia | — | EV_AL_REP | B1 |
| SOV_AL_REP_A | REGIME_AL_REP | 1925-01-21～1926-07-26 | de_jure | relation/2885839 v4 | EV_AL_REP | EV_AL_YU_1926 | B1 |
| SOV_AL_REP_B | REGIME_AL_REP | 1926-07-26～1928-09-01 | de_jure | relation/2800555 v24 | EV_AL_YU_1926 | EV_AL_KINGDOM | B1 |
| SOV_CS_D_2_X | REGIME_CS | 1920-08-28～1924-03-12 | de_jure | relation/2747893 v63 | — | EV_JAVORINA | B1 |
| SOV_CS_E | REGIME_CS | 1924-03-12～1936-07-03 | de_jure | relation/2692233 v107 | EV_JAVORINA | — | B1 |
| SOV_CY_IWA_X | REGIME_CY_ANNEX | 1918-11-12～1925-05-01 | de_jure | relation/2848135 v5 | — | EV_CY_COLONY | B1 |
| SOV_CY_COL | REGIME_CY_COL | 1925-05-01～1939-01-01 | de_jure | relation/2801349 v5 | EV_CY_COLONY | — | B1 |
| SOV_DE_H_2_X_1 | REGIME_DE | 1923-01-11～1924-01-01 | de_jure | relation/2696515 v214 − 魯爾佔領區 | EV_RUHR | — | B1 |
| SOV_DE_H_2_X_2 | REGIME_DE | 1924-01-01～1925-08-25 | de_jure | relation/2696515 v214 − 魯爾佔領區 − 萊茵蘭科隆區 − 萊茵蘭科布倫茨區 − 萊茵蘭美因茲區 | — | EV_RUHR_END | B1 |
| SOV_DE_H_2_X_3 | REGIME_DE | 1925-08-25～1926-01-31 | de_jure | relation/2696515 v214 − 萊茵蘭科隆區 − 萊茵蘭科布倫茨區 − 萊茵蘭美因茲區 | EV_RUHR_END | EV_COLOGNE_EVAC | B1 |
| SOV_DE_H_2_X_4 | REGIME_DE | 1926-01-31～1929-11-30 | de_jure | relation/2696515 v214 − 萊茵蘭科布倫茨區 − 萊茵蘭美因茲區 | EV_COLOGNE_EVAC | EV_KOBLENZ_EVAC | B1 |
| SOV_DK_C_X | REGIME_DK | 1921-05-21～1932-01-30 | de_jure | relation/2850547 v24 − 冰島 | — | — | B1 |
| SOV_DRUZE_B_X | REGIME_DRUZE | 1922-03-04～1927-06-01 | not_sovereign | relation/2864006 v1 | — | — | B1 |
| SOV_DRUZE_C | REGIME_DRUZE | 1927-06-01～1936-09-09 | not_sovereign | relation/2864005 v2 | — | EV_SY_1936 | B1 |
| SOV_EG_K_X | REGIME_EG_K | 1922-02-28～1939-01-01 | de_jure | relation/2803204 v15 | EV_EG_K | — | B1 |
| SOV_ES_B_IWA_X | REGIME_ES_K | 1921-06-01～1926-05-27 | de_jure | relation/2860485 v24 − 西屬摩洛哥 | — | — | B1 |
| SOV_ES_C | REGIME_ES_K | 1926-05-27～1931-04-14 | de_jure | relation/2862762 v19 − 西屬摩洛哥 | — | EV_ES_REPUBLIC | B1 |
| SOV_FIUME_FS_X | REGIME_FIUME_FS | 1920-12-30～1924-02-22 | de_jure | relation/2696321 v25 | EV_FIUME_FS | EV_FIUME_ANNEX | B1 |
| SOV_GR_C_X | REGIME_GR | 1922-10-11～1924-03-25 | de_jure | relation/2863749 v19 − 阿爾巴尼亞 | EV_MUDANYA | EV_GR_REP | B1 |
| SOV_GR_REP_A | REGIME_GR_REP | 1924-03-25～1924-08-06 | de_jure | relation/2863749 v19 − 阿爾巴尼亞 | EV_GR_REP | EV_LAUSANNE_INFORCE | B1 |
| SOV_GR_REP_B | REGIME_GR_REP | 1924-08-06～1935-11-03 | de_jure | relation/2801340 v30 | EV_LAUSANNE_INFORCE | EV_GR_MONARCHY | B1 |
| SOV_IFS_X | REGIME_IFS | 1922-12-06～1937-12-29 | de_jure | relation/2697727 v27 | EV_IFS | EV_IE_CONST | B1 |
| SOV_IRAQ_X_1 | REGIME_IRAQ | 1920-08-10～1924-08-06 | not_sovereign | relation/2839465 v22 | EV_SEVRES | — | B1 |
| SOV_IRAQ_X_2 | REGIME_IRAQ | 1924-08-06～1932-10-03 | not_sovereign | relation/2839465 v22 − republic-of-turkey | — | EV_IQ_INDEP | B1 |
| SOV_IS_X | REGIME_IS | 1918-12-01～1939-01-01 | de_jure | relation/2801981 v5 | EV_IS | — | B1 |
| SOV_IT_B_X | REGIME_IT | 1920-07-16～1924-02-22 | de_jure | relation/2696325 v128 | EV_SAINT_GERMAIN | EV_FIUME_ANNEX | B1 |
| SOV_IT_C | REGIME_IT | 1924-02-22～1929-06-07 | de_jure | relation/2747870 v103 | EV_FIUME_ANNEX | EV_LATERAN | B1 |
| SOV_KSCS_B_X | REGIME_KSCS | 1922-10-01～1924-01-27 | de_jure | relation/2858752 v11 | — | EV_ROME_1924 | B1 |
| SOV_KSCS_C_1 | REGIME_KSCS | 1924-01-27～1924-02-22 | de_jure | relation/2885838 v10 − 阜姆自由邦 | EV_ROME_1924 | EV_FIUME_ANNEX | B1 |
| SOV_KSCS_C_2 | REGIME_KSCS | 1924-02-22～1926-07-26 | de_jure | relation/2885838 v10 | EV_FIUME_ANNEX | EV_AL_YU_1926 | B1 |
| SOV_KSCS_D | REGIME_KSCS | 1926-07-26～1929-10-03 | de_jure | relation/2693463 v108 | EV_AL_YU_1926 | EV_YU | B1 |
| SOV_LB_REP | REGIME_LB_REP | 1926-05-23～1939-01-01 | not_sovereign | relation/2831358 v15 | EV_LB_REP | — | B1 |
| SOV_LEBANON_X | REGIME_LEBANON | 1920-09-01～1926-05-23 | not_sovereign | relation/2831357 v14 | — | EV_LB_REP | B1 |
| SOV_LY_CY_IWA_X | REGIME_LY_CY | 1918-11-12～1934-01-01 | de_jure | relation/2803190 v11 | — | EV_LY_UNIFY | B1 |
| SOV_LY_TR_IWA_X | REGIME_LY_TR | 1918-11-12～1934-01-01 | de_jure | relation/2690837 v18 | — | EV_LY_UNIFY | B1 |
| SOV_MA_ES_B_X | REGIME_MA_ES | 1921-06-01～1926-05-27 | de_jure | relation/2860423 v10 | — | EV_RIF_END | B1 |
| SOV_MA_ES_C | REGIME_MA_ES | 1926-05-27～1939-01-01 | de_jure | relation/2860422 v10 | EV_RIF_END | — | B1 |
| SOV_MA_FR_B_IWA_X | REGIME_MA_FR | 1921-01-01～1926-05-27 | de_jure | relation/2866015 v9 | — | EV_RIF_END | B1 |
| SOV_MA_FR_C | REGIME_MA_FR | 1926-05-27～1939-01-01 | de_jure | relation/2690949 v24 | EV_RIF_END | — | B1 |
| SOV_MR_IWA_X | REGIME_MR | 1918-11-12～1939-01-01 | de_jure | relation/2917211 v3 | — | — | B1 |
| SOV_NO_B_X | REGIME_NO | 1921-01-01～1925-08-14 | de_jure | relation/2851797 v14 | — | EV_SVALBARD | B1 |
| SOV_PALESTINE_X | REGIME_PALESTINE | 1920-08-10～1939-01-01 | not_sovereign | relation/2848316 v14 | EV_SEVRES | — | B1 |
| SOV_PL_B_X | REGIME_PL | 1922-06-20～1924-03-12 | de_jure | relation/2741472 v117 | EV_USIL_TRANSFER | EV_JAVORINA | B1 |
| SOV_PL_C | REGIME_PL | 1924-03-12～1924-06-22 | de_jure | relation/2747892 v92 | EV_JAVORINA | — | B1 |
| SOV_RHZ1_1 | REGIME_RHZ1 | 1924-01-01～1925-08-25 | not_sovereign | relation/2696515 v214 ∩ 萊茵蘭科隆區（手繪近似線（build/make_requests.py）） − 魯爾佔領區 | — | EV_RUHR_END | B1 |
| SOV_RHZ1_2 | REGIME_RHZ1 | 1925-08-25～1926-01-31 | not_sovereign | relation/2696515 v214 ∩ 萊茵蘭科隆區（手繪近似線（build/make_requests.py）） | EV_RUHR_END | EV_COLOGNE_EVAC | B1 |
| SOV_RHZ2 | REGIME_RHZ2 | 1924-01-01～1929-11-30 | not_sovereign | relation/2696515 v214 ∩ 萊茵蘭科布倫茨區（手繪近似線（build/make_requests.py）） | — | EV_KOBLENZ_EVAC | B1 |
| SOV_RHZ3 | REGIME_RHZ3 | 1924-01-01～1930-06-30 | not_sovereign | relation/2696515 v214 ∩ 萊茵蘭美因茲區（手繪近似線（build/make_requests.py）） | — | EV_MAINZ_EVAC | B1 |
| SOV_RIF_X | REGIME_RIF | 1921-09-18～1926-05-27 | not_sovereign | relation/2860425 v5 | EV_RIF | EV_RIF_END | B1 |
| SOV_RUHR_X | REGIME_RUHR | 1923-01-11～1925-08-25 | not_sovereign | relation/2696515 v214 ∩ 魯爾區（手繪近似線（build/make_requests.py）） | EV_RUHR | EV_RUHR_END | B1 |
| SOV_SAAR_X | REGIME_SAAR | 1920-01-10～1935-03-01 | not_sovereign | relation/2690373 v23 | EV_VERSAILLES | EV_SAAR_RETURN | B1 |
| SOV_SE_IWA_X | REGIME_SE | 1918-11-12～1932-01-30 | de_jure | relation/2692524 v33 | — | — | B1 |
| SOV_SU_X_1 | REGIME_SU | 1922-12-30～1924-08-06 | de_jure | relation/2800978 v112 | EV_USSR | — | B1 |
| SOV_SU_X_2 | REGIME_SU | 1924-08-06～1925-01-20 | de_jure | relation/2800978 v112 − republic-of-turkey | — | EV_SU_1925 | B1 |
| SOV_SU_B | REGIME_SU | 1925-01-20～1926-01-01 | de_jure | relation/2851271 v89 − republic-of-turkey | EV_SU_1925 | — | B1 |
| SOV_SYR_FED_X | REGIME_SYR_FED | 1922-06-28～1924-08-06 | not_sovereign | relation/2863992 v8 | — | — | B1 |
| SOV_SYR_FED_B | REGIME_SYR_FED | 1924-08-06～1925-01-01 | not_sovereign | relation/2864020 v8 | — | EV_SY_STATE | B1 |
| SOV_SY_STATE | REGIME_SY_STATE | 1925-01-01～1930-05-14 | not_sovereign | relation/2863991 v6 | EV_SY_STATE | EV_SY_REP | B1 |
| SOV_TANGIER | REGIME_TANGIER | 1925-06-01～1939-01-01 | not_sovereign | relation/2848366 v6 | EV_TANGIER | — | B1 |
| SOV_TN_IWA_X | REGIME_TN | 1918-11-12～1939-01-01 | de_jure | relation/2690947 v20 | — | — | B1 |
| SOV_TR_A_X | REGIME_TR | 1923-10-29～1924-08-06 | de_jure | relation/2958039 v3 − italian-aegean-islands | EV_TR_REPUBLIC | EV_LAUSANNE_INFORCE | B1 |
| SOV_TRANSJORDAN_X | REGIME_TRANSJORDAN | 1920-08-10～1939-01-01 | not_sovereign | relation/2848317 v15 | EV_SEVRES | — | B1 |
| SOV_US_IWA_X | REGIME_US | 1918-11-12～1937-07-07 | de_jure | relation/2874803 v33 − relation/2889834 v1 | — | — | B1 |
| SOV_DE_H_2_X_5 | REGIME_DE | 1929-11-30～1930-06-30 | de_jure | relation/2696515 v214 − 萊茵蘭美因茲區 | EV_KOBLENZ_EVAC | EV_MAINZ_EVAC | B2 |
| SOV_DE_H_2_X_6 | REGIME_DE | 1930-06-30～1935-03-01 | de_jure | relation/2696515 v214 | EV_MAINZ_EVAC | EV_SAAR_RETURN | B2 |
| SOV_DE_I | REGIME_DE | 1935-03-01～1936-07-03 | de_jure | relation/2694638 v245 | EV_SAAR_RETURN | — | B2 |
| SOV_ES_REP_B_1 | REGIME_ES_REP | 1931-04-14～1936-07-17 | de_jure | relation/2860484 v25 ∪ relation/2862762 v19 | EV_ES_REPUBLIC | EV_ES_COUP | B2 |
| SOV_GR_D | REGIME_GR | 1935-11-03～1936-09-17 | de_jure | relation/2801340 v30 | EV_GR_MONARCHY | — | B2 |
| SOV_IQ_K | REGIME_IQ_K | 1932-10-03～1939-01-01 | de_jure | relation/2839466 v22 − republic-of-turkey | EV_IQ_INDEP | — | B2 |
| SOV_LY_IT | REGIME_LY_IT | 1934-01-01～1939-01-01 | de_jure | relation/2803189 v17 | EV_LY_UNIFY | — | B2 |
| SOV_SY_REP_A | REGIME_SY_REP | 1930-05-14～1936-09-09 | not_sovereign | relation/2863990 v7 | EV_SY_REP | EV_SY_1936 | B2 |
| SOV_ESNAT_1 | REGIME_ES_NAT | 1936-07-17～1936-11-07 | not_sovereign | relation/2860484 v25 ∩ 國民軍控制區第 1 階段（手繪近似線（build/make_requests.py）） | EV_ES_COUP | EV_ES_MADRID | B3 |
| SOV_ESNAT_2 | REGIME_ES_NAT | 1936-11-07～1937-02-08 | not_sovereign | relation/2860484 v25 ∩ 國民軍控制區第 2 階段（手繪近似線（build/make_requests.py）） | EV_ES_MADRID | EV_MALAGA | B3 |
| SOV_ESNAT_3 | REGIME_ES_NAT | 1937-02-08～1937-06-19 | not_sovereign | relation/2860484 v25 ∩ 國民軍控制區第 3 階段（手繪近似線（build/make_requests.py）） | EV_MALAGA | EV_BILBAO | B3 |
| SOV_ESNAT_4 | REGIME_ES_NAT | 1937-06-19～1937-08-26 | not_sovereign | relation/2860484 v25 ∩ 國民軍控制區第 4 階段（手繪近似線（build/make_requests.py）） | EV_BILBAO | EV_SANTANDER | B3 |
| SOV_ESNAT_5 | REGIME_ES_NAT | 1937-08-26～1937-10-21 | not_sovereign | relation/2860484 v25 ∩ 國民軍控制區第 5 階段（手繪近似線（build/make_requests.py）） | EV_SANTANDER | EV_GIJON | B3 |
| SOV_ESNAT_6 | REGIME_ES_NAT | 1937-10-21～1938-04-15 | not_sovereign | relation/2860484 v25 ∩ 國民軍控制區第 6 階段（手繪近似線（build/make_requests.py）） | EV_GIJON | EV_VINAROS | B3 |
| SOV_ESNAT_7 | REGIME_ES_NAT | 1938-04-15～1939-02-10 | not_sovereign | relation/2860484 v25 ∩ 國民軍控制區第 7 階段（手繪近似線（build/make_requests.py）） | EV_VINAROS | EV_CATALONIA | B3 |
| SOV_ESNAT_8 | REGIME_ES_NAT | 1939-02-10～1939-04-01 | not_sovereign | relation/2860484 v25 − 共和國控制區（手繪近似線（build/make_requests.py）） | EV_CATALONIA | EV_SPAIN_1939 | B3 |
| SOV_ES_REP_B_2 | REGIME_ES_REP | 1936-07-17～1936-11-07 | de_jure | relation/2860484 v25 ∪ relation/2862762 v19 − 國民軍控制區 | EV_ES_COUP | EV_ES_MADRID | B3 |
| SOV_ES_REP_B_3 | REGIME_ES_REP | 1936-11-07～1937-02-08 | de_jure | relation/2860484 v25 ∪ relation/2862762 v19 − 國民軍控制區 | EV_ES_MADRID | EV_MALAGA | B3 |
| SOV_ES_REP_B_4 | REGIME_ES_REP | 1937-02-08～1937-06-19 | de_jure | relation/2860484 v25 ∪ relation/2862762 v19 − 國民軍控制區 | EV_MALAGA | EV_BILBAO | B3 |
| SOV_ES_REP_B_5 | REGIME_ES_REP | 1937-06-19～1937-08-26 | de_jure | relation/2860484 v25 ∪ relation/2862762 v19 − 國民軍控制區 | EV_BILBAO | EV_SANTANDER | B3 |
| SOV_ES_REP_B_6 | REGIME_ES_REP | 1937-08-26～1937-10-21 | de_jure | relation/2860484 v25 ∪ relation/2862762 v19 − 國民軍控制區 | EV_SANTANDER | EV_GIJON | B3 |
| SOV_ES_REP_B_7 | REGIME_ES_REP | 1937-10-21～1938-04-15 | de_jure | relation/2860484 v25 ∪ relation/2862762 v19 − 國民軍控制區 | EV_GIJON | EV_VINAROS | B3 |
| SOV_ES_REP_B_8 | REGIME_ES_REP | 1938-04-15～1939-02-10 | de_jure | relation/2860484 v25 ∪ relation/2862762 v19 − 國民軍控制區 | EV_VINAROS | EV_CATALONIA | B3 |
| SOV_ES_REP_B_9 | REGIME_ES_REP | 1939-02-10～1939-04-01 | de_jure | relation/2860484 v25 ∪ relation/2862762 v19 − 國民軍控制區 | EV_CATALONIA | EV_SPAIN_1939 | B3 |
| SOV_HATAY | REGIME_HATAY | 1938-09-02～1939-06-29 | not_sovereign | relation/2864001 v4 | EV_HATAY_STATE | EV_HATAY | B3 |
| SOV_SY_REP_B_1 | REGIME_SY_REP | 1936-09-09～1938-09-02 | not_sovereign | relation/2863989 v8 | EV_SY_1936 | EV_HATAY_STATE | B3 |
| SOV_SY_REP_B_2 | REGIME_SY_REP | 1938-09-02～1938-09-07 | not_sovereign | relation/2863989 v8 − 哈塔伊國 | EV_HATAY_STATE | — | B3 |
| SOV_SY_REP_C | REGIME_SY_REP | 1938-09-07～1939-01-01 | not_sovereign | relation/2863988 v8 | — | — | B3 |

## 佔領歸屬

| placeholder | 被佔領 | 佔領方 | 管理 | 期間 | 共同 | 子批 |
|---|---|---|---|---|---|---|
| OCC_RUHR_X | REGIME_RUHR | REGIME_FR3 | military_administration | 1923-01-11～1925-08-25 | 是 | B1 |
| OCC_RHZ1 | REGIME_RHZ1 | REGIME_UK | military_administration | 1924-01-01～1926-01-31 | 是 | B1 |
| OCC_RHZ2 | REGIME_RHZ2 | REGIME_FR3 | military_administration | 1924-01-01～1929-11-30 |  | B1 |
| OCC_RHZ3 | REGIME_RHZ3 | REGIME_FR3 | military_administration | 1924-01-01～1930-06-30 |  | B1 |

## 衝突紀錄

| placeholder | A | B | 起 | 迄 | 位置 | 子批 |
|---|---|---|---|---|---|---|
| CF_ES_RIF | REGIME_ES_K | REGIME_RIF | EV_RIF | EV_RIF_END | [-3.93, 35.2]：阿日迪爾—阿盧塞馬斯灣（里夫共和國首府，固定點） | B1 |
| CF_FR_RIF | REGIME_FR3 | REGIME_RIF | EV_RIF_FR | EV_RIF_END | [-4.5, 34.6]：沃爾加河谷（1925 里夫軍進攻法屬摩洛哥處，固定點） | B1 |
| CF_ES_CW | REGIME_ES_REP | REGIME_ES_NAT | EV_ES_COUP | EV_SPAIN_1939 | [-3.72, 40.45]：馬德里大學城前線（固定點） | B3 |

## 近似與未畫（待查證）

- 萊茵蘭三個佔領區（科隆、科布倫茨、美因茲）與魯爾佔領區：萊茵河線、分區線與橋頭堡圓都是手繪粗略近似，再與 OHM 德國外框求交；從 1924-01-01（B 批起點）起畫，1918-12～1923 未畫。杜塞道夫、杜伊斯堡等 1921 年制裁佔領未另分。
- 西班牙內戰國民軍控制區：八個階段（1936-07-17、11-07、1937-02-08、06-19、08-26、10-21、1938-04-15、1939-02-10）各用手繪多邊形與西班牙範圍求交，只是粗略近似；1938-06 卡斯特利翁、1938-07 拉塞雷納口袋等中間變化未分。共和國控制區＝西班牙減國民軍區。西屬撒哈拉、伊夫尼 1936-07 起歸國民軍；西屬摩洛哥維持原紀錄。革命加泰隆尼亞等自治未另列。
- 開發庫既有西班牙共和國紀錄缺西屬撒哈拉、伊夫尼與特內里費、富埃特文圖拉等加那利島嶼；重送時從 OHM 2862762 補上。但開發庫既有「西班牙國」紀錄（1939-04-01 起，二戰資料）同樣缺這些地方，1939-04-01 接點在那裡會留白（既有資料，本批未改，待 Tai 決定是否修）。
- 蘇聯 1925-01-20～1926-01-01 用 OHM 2851271（框外裁掉），1926 年起接開發庫既有紀錄；海岸與北極島嶼有零星細縫（合計約 0.44 平方度）。蘇聯內部各加盟共和國（1924 中亞劃界、1929 塔吉克、1936 新憲法）只記事件，未分範圍。
- 土耳其 1924-08-06、阿爾巴尼亞 1925-01-21、南斯拉夫 1929-10-03 接點有 OHM 版本間的小細縫（各 0.01～0.04 平方度），沒有重疊。
- 義大利—衣索比亞戰爭（1935～1936）不在地圖框內（框南界北緯 15°），未做。沙烏地、葉門、伊朗、蘇丹、里奧德奧羅等 A 批也沒畫的地方仍未畫。
- 北非、近東、冰島、埃及、突尼西亞、茅利塔尼亞沒有後續資料，暫迄 1939-01-01。哈塔伊國 1938-09-02 起，1939-06-29 接開發庫既有土耳其紀錄；1938-07 起法土共同駐軍未另列佔領。
- 德國 1935-03-01 起用含薩爾的 OHM 2694638；萊茵蘭再軍事化（1936-03-07）只記事件，不改範圍。德奧合併（1938-03-13）與蘇台德（1938-10）沿用開發庫既有紀錄。
- 希臘 1924-03-25～1935-11-03 為希臘第二共和國；1926 潘加洛斯獨裁未分。阿爾巴尼亞共和國依 FRUS 從 1925-01-21 起（OHM 為 01-31）。
- 事件標待查證者（見上表）只有日期與摘要，沒有正式出處，送出時不附引用。
