# WW1 第二批：1914-07-29 → 1918-11-11 停戰（DRAFT，待 Tai 檢查）

範圍：歐洲、北非、近東（OHM 裁切框 -20,15～60,72）。期間半開區間 [1914-07-29, 1918-11-12)；1918-11-12 是本批試驗期間終點，不是政權迄日（無迄事件）。
**只寫入本機開發庫**（worldline-borders-dev，API 127.0.0.1:5052，DB 5442）；寫入 appdb_ww2（5051）要另取得 Tai 同意。

## 子批

| 子批 | 紀錄起日 | 請求數 |
|---|---|---|
| sub1 | [1914-07-29, 1916-01-01) | 153 |
| sub2 | [1916-01-01, 1918-01-01) | 61 |
| sub3 | [1918-01-01, 1918-11-12) | 57 |

每筆紀錄用真實起訖，依起日分子批；來源、政權、事件放在第一個引用它們的子批。子批要依序送（後面的子批引用前面的 id）。sub1 先撤回第一批迄於 1914-07-29 的 27 筆主權紀錄、義屬愛琴海佔領歸屬與奧匈—塞爾維亞衝突，再以相同內容延長後重送（先撤後增）。

## 檔案

| 檔案 | 說明 |
|---|---|
| `build/fetch.py` | 依 relation id 從 OHM Overpass 抓關係（`out meta geom`＋成員線段 tags），存 `raw/`（不進版控；第一批已抓的沿用） |
| `build/build.py` | 組多邊形 → 框裁切 → Natural Earth 10m 陸地裁切 → 簡化 → `borders-ohm-ww1-2.geojson`＋`ohm-manifest.json`；外框小缺口（盧布林、攝政波蘭）以直線接合並記在清單 `repair` |
| `build/make_requests.py` | 優先序引擎（底層國家扣掉同期佔領區／新國家／開發庫既有紀錄並切段）、手繪近似線、QA、產生 `requests/sub{1,2,3}/*.json`、`ww1-1914-1918-derived.geojson`、`qa.json` |
| `build/readme.py` | 產生本檔 |
| `send_seed.py` | 依子批送出（預設 dry-run；拒絕 5051；API key 從 --env 安靜讀取） |
| `db-export/`（不進版控） | 開發庫唯讀匯出：本期間既有主權紀錄、美國 1937 年紀錄；備份在 `~/01_Projects/world_line_backups/` |

用法（在本目錄）：
```
P="--prior ../../../../.dev/sent-ids.borders-dev.json --prior ../../../../.dev/sent-ids.borders-us-dev.json --prior ../../../../.dev/sent-ids.ww1-balkans-1908-1914-dev.json"
python3 send_seed.py --sub sub1 --base http://127.0.0.1:5052 --env ../../../../.env.borders-dev $P --ids ../../../../.dev/sent-ids.ww1-war-1914-1918-dev.json [--send]
```

OHM Overpass `osm_base`：2026-10-31T16:12:51Z（UTC）。

## 事件

| placeholder | 日期 | 類型 | 摘要 | 出處 | 子批 |
|---|---|---|---|---|---|
| EV_DE_RU_WAR | 1914-08-01 | war | 德國對俄國宣戰 | SRC_FRUS_1914S Doc. 58, pp. 28–29；SRC_FRUS_1914S Doc. 70, p. 33 | sub1 |
| EV_LUX_OCC | 1914-08-02 | campaign | 德軍進入並佔領盧森堡 | **待查證** | sub1 |
| EV_DE_FR_WAR | 1914-08-03 | war | 德國對法國宣戰 | SRC_FRUS_1914S Doc. 88, p. 40；SRC_FRUS_1914S Doc. 209, pp. 112–113 | sub1 |
| EV_DE_BE_INV | 1914-08-04 | war | 德軍入侵比利時 | SRC_FRUS_1914S Doc. 98, p. 45；SRC_FRUS_1914S Doc. 157, pp. 71–72 | sub1 |
| EV_UK_DE_WAR | 1914-08-04 | war | 英國對德國宣戰 | SRC_FRUS_1914S Doc. 96, p. 44 | sub1 |
| EV_AH_RU_WAR | 1914-08-06 | war | 奧匈帝國對俄國宣戰 | SRC_FRUS_1914S Doc. 107, p. 47；SRC_FRUS_1914S Doc. 110, pp. 48–49 | sub1 |
| EV_AH_MN_WAR | 1914-08-09 | war | 奧匈帝國與蒙特內哥羅開戰 | SRC_FRUS_1914S Doc. 120, p. 52 | sub1 |
| EV_FR_AH_WAR | 1914-08-12 | war | 法國對奧匈帝國宣戰 | SRC_FRUS_1914S Doc. 143, pp. 64–65 | sub1 |
| EV_UK_AH_WAR | 1914-08-12 | war | 英國對奧匈帝國宣戰 | SRC_FRUS_1914S Doc. 128, p. 56 | sub1 |
| EV_BRUSSELS | 1914-08-20 | campaign | 德軍進入布魯塞爾，比利時大部被佔領 | SRC_FRUS_1914S Doc. 159, pp. 73–74 | sub1 |
| EV_ANTWERP | 1914-10-10 | campaign | 安特衛普陷落，比利時軍退守伊瑟河 | SRC_FRUS_1914S Doc. 229, pp. 122–123 | sub1 |
| EV_NFR_FRONT | 1914-10-13 | campaign | 德軍佔領里爾，法國北部佔領區大致成形（西線轉入壕溝戰） | **待查證** | sub1 |
| EV_OT_ENTRY | 1914-10-29 | war | 鄂圖曼艦隊砲擊俄國黑海港口，鄂圖曼帝國參戰 | SRC_FRUS_1914S Doc. 239, p. 127；SRC_FRUS_1914S Doc. 238, p. 127 | sub1 |
| EV_ENTENTE_OT_WAR | 1914-11-05 | war | 英、法對鄂圖曼帝國宣戰 | SRC_FRUS_1914S Doc. 243, p. 129 | sub1 |
| EV_CY_ANNEX | 1914-11-05 | political | 英國併吞賽普勒斯 | **待查證** | sub1 |
| EV_EGYPT | 1914-12-18 | political | 英國宣布埃及為保護國，終止鄂圖曼宗主權 | SRC_FRUS_1914S Doc. 274, pp. 152–153；SRC_FRUS_1914S Doc. 275, p. 153 | sub1 |
| EV_IT_AH_WAR | 1915-05-23 | war | 義大利對奧匈帝國宣戰（5 月 24 日起進入戰爭狀態） | SRC_FRUS_1915S Doc. 53, pp. 35–36 | sub1 |
| EV_WARSAW | 1915-08-05 | campaign | 德軍佔領華沙，俄屬波蘭失守 | SRC_FRUS_1915S Doc. 79, pp. 59–61 | sub1 |
| EV_IT_OT_WAR | 1915-08-21 | war | 義大利對鄂圖曼帝國宣戰 | **待查證** | sub1 |
| EV_VILNA | 1915-09-19 | campaign | 德軍佔領維爾紐斯，東方總司令轄區（Ober Ost）成形 | **待查證** | sub1 |
| EV_BG_RS_WAR | 1915-10-14 | war | 保加利亞進攻塞爾維亞，保加利亞參戰 | SRC_FRUS_1915S Doc. 88, p. 65 | sub1 |
| EV_ENTENTE_BG_WAR | 1915-10-15 | war | 協約國對保加利亞宣戰（英 10-15、法 10-16、義 10-19） | SRC_FRUS_1915S Doc. 89, p. 65；SRC_FRUS_1915S Doc. 90, p. 65；SRC_FRUS_1915S Doc. 91, p. 65 | sub1 |
| EV_SERBIA_FALL | 1915-11-28 | campaign | 塞爾維亞全境被同盟國佔領，塞軍經阿爾巴尼亞撤退 | **待查證** | sub1 |
| EV_MN_OCC | 1916-01-13 | campaign | 奧匈軍佔領采蒂涅，蒙特內哥羅被佔領 | **待查證** | sub1 |
| EV_DE_PT_WAR | 1916-03-09 | war | 德國對葡萄牙宣戰 | SRC_FRUS_1916S Doc. 12, p. 18 | sub2 |
| EV_RO_ENTRY | 1916-08-27 | war | 羅馬尼亞對奧匈帝國宣戰 | SRC_FRUS_1916S Doc. 62, p. 48；SRC_FRUS_1916S Doc. 60 | sub2 |
| EV_CP_RO_WAR | 1916-08-28 | war | 德國、鄂圖曼、保加利亞對羅馬尼亞宣戰 | SRC_FRUS_1916S Doc. 65, p. 49 | sub2 |
| EV_IT_DE_WAR | 1916-08-28 | war | 義大利對德國宣戰 | SRC_FRUS_1916S Doc. 63, pp. 48–49 | sub2 |
| EV_DOBRUJA_OCC | 1916-10-22 | campaign | 同盟國軍攻佔康斯坦察，多布羅加被佔領 | **待查證** | sub1 |
| EV_PL_KINGDOM | 1916-11-05 | political | 德、奧兩皇宣布成立波蘭王國（攝政王國） | SRC_FRUS_1916S Doc. 1035, p. 796；SRC_FRUS_1916S Doc. 1036, pp. 796–797 | sub1 |
| EV_BUCHAREST_FALL | 1916-12-06 | campaign | 同盟國軍攻佔布加勒斯特，瓦拉幾亞被佔領 | SRC_FRUS_1916S Doc. 109, pp. 81–82 | sub2 |
| EV_FEB_REV | 1917-03-15 | political | 俄國二月革命：尼古拉二世退位，臨時政府成立 | SRC_FRUS_1917 Doc. 1449, p. 1205；SRC_FRUS_1917 Doc. 1450, pp. 1205–1206 | sub1 |
| EV_US_DE_WAR | 1917-04-06 | war | 美國對德國宣戰 | SRC_FRUS_1917S1 Doc. 240, pp. 207–208 | sub2 |
| EV_GR_WAR | 1917-07-02 | war | 希臘（統一政府）對德國、保加利亞處於戰爭狀態 | SRC_FRUS_1917S2 Doc. 165, p. 117；SRC_FRUS_1917S2 Doc. 159, p. 113 | sub2 |
| EV_RU_REPUBLIC | 1917-09-14 | political | 俄國臨時政府宣布俄國為共和國 | SRC_FRUS_1918R1 Doc. 154, pp. 191–192 | sub2 |
| EV_OCT_REV | 1917-11-07 | political | 俄國十月革命：布爾什維克奪取政權 | SRC_FRUS_1918R1 Doc. 198, p. 224；SRC_FRUS_1918R1 Doc. 199, pp. 224–225 | sub2 |
| EV_TC | 1917-11-15 | political | 外高加索委員會在梯弗里斯成立 | **待查證** | sub2 |
| EV_FI_INDEP | 1917-12-06 | political | 芬蘭宣布獨立 | SRC_FRUS_1918R2 Doc. 864, p. 734 | sub2 |
| EV_US_AH_WAR | 1917-12-07 | war | 美國對奧匈帝國宣戰 | SRC_FRUS_1917S2 Doc. 381, p. 459 | sub2 |
| EV_BREST_UA | 1918-02-09 | treaty | 布列斯特—立陶夫斯克（烏克蘭）和約：同盟國承認烏克蘭人民共和國 | SRC_FRUS_1918R2 Doc. 785, pp. 665–666；SRC_FRUS_1918S1 Doc. 746, p. 757 | sub1 |
| EV_EE_OCC | 1918-02-24 | campaign | 德軍進入愛沙尼亞與利沃尼亞（愛沙尼亞同日宣布獨立） | SRC_FRUS_1918S1 Doc. 84, pp. 135–138 | sub3 |
| EV_BREST | 1918-03-03 | treaty | 布列斯特—立陶夫斯克和約：俄國退出戰爭，放棄波蘭、立陶宛、庫爾蘭、利沃尼亞、愛沙尼亞、芬蘭、烏克蘭 | SRC_FRUS_1918R1 Doc. 443, pp. 442–471；SRC_FRUS_1918R1 Doc. 434, p. 434 | sub2 |
| EV_BY_PR | 1918-03-25 | political | 白俄羅斯人民共和國宣布獨立 | **待查證** | sub3 |
| EV_BESSARABIA | 1918-04-09 | political | 比薩拉比亞（摩爾達維亞民主共和國）議會表決與羅馬尼亞合併 | **待查證** | sub2 |
| EV_TDFR | 1918-04-22 | political | 外高加索民主聯邦共和國宣布獨立 | **待查證** | sub2 |
| EV_BUCH18 | 1918-05-07 | treaty | 布加勒斯特和約（1918）：羅馬尼亞割讓南多布羅加給保加利亞，北多布羅加歸同盟國共管 | SRC_FRUS_1918S1 Doc. 768, pp. 771–777 | sub1 |
| EV_MRNC | 1918-05-11 | political | 北高加索山地共和國宣布獨立 | **待查證** | sub3 |
| EV_GE | 1918-05-26 | political | 喬治亞宣布獨立，外高加索聯邦解體 | **待查證** | sub3 |
| EV_AM_AZ | 1918-05-28 | political | 亞美尼亞、亞塞拜然宣布獨立 | **待查證** | sub3 |
| EV_BG_ARMISTICE | 1918-09-29 | armistice | 薩洛尼卡停戰協定：保加利亞退出戰爭 | SRC_FRUS_1918S1 Doc. 273, p. 331；SRC_FRUS_1918S1 Doc. 275, p. 334 | sub1 |
| EV_CS | 1918-10-28 | political | 捷克斯洛伐克在布拉格宣布獨立 | **待查證** | sub1 |
| EV_SCS | 1918-10-29 | political | 薩格勒布議會宣布脫離奧匈，成立斯洛維尼亞人、克羅埃西亞人和塞爾維亞人國 | **待查證** | sub3 |
| EV_MUDROS | 1918-10-30 | armistice | 穆德羅斯停戰協定：鄂圖曼帝國退出戰爭 | SRC_FRUS_1918S1 Doc. 368, pp. 441–443 | sub1 |
| EV_VILLA_GIUSTI | 1918-11-03 | armistice | 朱斯蒂別墅停戰協定：奧匈帝國退出戰爭 | SRC_FRUS_1918S1 Doc. 373, p. 447；SRC_FRUS_1918S1 Doc. 360, pp. 430–431 | sub1 |
| EV_COMPIEGNE | 1918-11-11 | armistice | 貢比涅停戰協定：德國停戰，西線戰事結束 | SRC_FRUS_1918S1 Doc. 417, p. 492；SRC_FRUS_1918S1 Doc. 384, pp. 463–468；SRC_FRUS_1918S1 Doc. 420, pp. 494–498 | sub1 |
| EV_PL_INDEP | 1918-11-11 | political | 攝政會議把軍權交給畢蘇斯基，波蘭獨立 | **待查證** | sub2 |

## 主權紀錄

| placeholder | 政權 | 期間 | 層級 | 幾何 | 起事件 | 迄事件 | 子批 |
|---|---|---|---|---|---|---|---|
| SOV_AH_R | REGIME_AH | 1908-10-06～1918-10-28 | de_jure | relation/2692361 v267 | EV_BOSNIA | EV_CS | sub1 |
| SOV_AL_PR_R | REGIME_AL_PR | 1914-02-21～1918-11-12 | de_jure | relation/2855613 v8 | EV_AL_PRINCIPALITY | — | sub1 |
| SOV_BE_R | REGIME_BE | 1908-10-06～1914-08-20 | de_jure | relation/2797729 v43 | — | EV_BRUSSELS | sub1 |
| SOV_BE_2 | REGIME_BE | 1914-08-20～1914-10-10 | de_jure | relation/2797729 v43 − 比利時佔領區 | EV_BRUSSELS | EV_ANTWERP | sub1 |
| SOV_BE_3 | REGIME_BE | 1914-10-10～1918-11-11 | de_jure | relation/2797729 v43 − 比利時佔領區 | EV_ANTWERP | EV_COMPIEGNE | sub1 |
| SOV_BG_B_R | REGIME_BG | 1913-08-10～1918-05-07 | de_jure | relation/2746680 v29 | EV_BUCHAREST | EV_BUCH18 | sub1 |
| SOV_CY_ANNEX | REGIME_CY_ANNEX | 1914-11-05～1918-11-12 | de_jure | relation/2848135 v5 | EV_CY_ANNEX | — | sub1 |
| SOV_CY_R | REGIME_CY_BR | 1908-10-06～1914-11-05 | not_sovereign | relation/2848136 v6 | — | EV_CY_ANNEX | sub1 |
| SOV_DE_EMP_R | REGIME_DE_EMP | 1908-10-06～1918-11-12 | de_jure | relation/2692425 v259 | — | — | sub1 |
| SOV_DK_R | REGIME_DK | 1908-10-06～1918-11-12 | de_jure | relation/2869935 v14 | — | — | sub1 |
| SOV_EG | REGIME_EG | 1914-12-18～1918-11-12 | de_jure | relation/2803205 v16 | EV_EGYPT | — | sub1 |
| SOV_ES_B_R | REGIME_ES_K | 1912-11-27～1918-11-12 | de_jure | relation/2860486 v24 − relation/2860424 v10 | EV_ES_MOROCCO | — | sub1 |
| SOV_FR3_R | REGIME_FR3 | 1908-10-06～1914-10-13 | de_jure | relation/2866012 v31 | — | EV_NFR_FRONT | sub1 |
| SOV_FR3_2 | REGIME_FR3 | 1914-10-13～1918-11-11 | de_jure | relation/2866012 v31 − 法國北部佔領區 | EV_NFR_FRONT | EV_COMPIEGNE | sub1 |
| SOV_GG_BE_A | REGIME_GG_BE | 1914-08-20～1914-10-10 | not_sovereign | relation/2797729 v43 ∩ 列日、那慕爾、盧森堡、布拉班、林堡、埃諾六省（OHM 各省 relation） | EV_BRUSSELS | EV_ANTWERP | sub1 |
| SOV_GG_BE_B | REGIME_GG_BE | 1914-10-10～1918-11-11 | not_sovereign | relation/2797729 v43 ∩ 伊瑟河—伊珀爾前線以東（手繪近似線（build/make_requests.py）） | EV_ANTWERP | EV_COMPIEGNE | sub1 |
| SOV_GG_LUBLIN | REGIME_GG_LUBLIN | 1915-08-05～1916-11-05 | not_sovereign | relation/2695683 v50 | EV_WARSAW | EV_PL_KINGDOM | sub1 |
| SOV_GG_WARSAW | REGIME_GG_WARSAW | 1915-08-05～1916-11-05 | not_sovereign | relation/2695682 v37 | EV_WARSAW | EV_PL_KINGDOM | sub1 |
| SOV_GR_B_R | REGIME_GR | 1913-08-10～1918-11-12 | de_jure | relation/2692585 v40 | EV_BUCHAREST | — | sub1 |
| SOV_IT_R | REGIME_IT | 1908-10-06～1918-11-12 | de_jure | relation/2696424 v118 | — | — | sub1 |
| SOV_IT_AEGEAN_R | REGIME_IT_AEGEAN | 1912-04-27～1918-11-12 | not_sovereign | relation/2830316 v10 | EV_DODECANESE | — | sub1 |
| SOV_LY_CY_R | REGIME_LY_CY | 1912-10-18～1918-11-12 | de_jure | relation/2803190 v11 | EV_OUCHY | — | sub1 |
| SOV_LY_TR_R | REGIME_LY_TR | 1912-10-18～1918-11-12 | de_jure | relation/2690837 v18 | EV_OUCHY | — | sub1 |
| SOV_MA_ES_R | REGIME_MA_ES | 1912-11-27～1918-11-12 | de_jure | relation/2860424 v10 | EV_ES_MOROCCO | — | sub1 |
| SOV_MA_FR_B_R | REGIME_MA_FR | 1912-11-27～1918-11-12 | de_jure | (relation/2866016 v9 ∪ 蘇丹國範圍) − relation/2860424 v10 − relation/2860486 v24 | EV_ES_MOROCCO | — | sub1 |
| SOV_MGG_SERBIA | REGIME_MGG_SERBIA | 1915-11-28～1918-11-03 | not_sovereign | relation/2746681 v36 − 保加利亞佔領區（手繪近似線（build/make_requests.py）） | EV_SERBIA_FALL | EV_VILLA_GIUSTI | sub1 |
| SOV_MN_K_B_R | REGIME_MN_K | 1913-05-30～1916-01-13 | de_jure | relation/2739656 v22 | EV_LONDON | EV_MN_OCC | sub1 |
| SOV_MORESNET_R | REGIME_MORESNET | 1908-10-06～1918-11-12 | de_jure | relation/2696520 v6 | — | — | sub1 |
| SOV_MR_R | REGIME_MR | 1912-01-01～1918-11-12 | de_jure | relation/2917211 v3 | — | — | sub1 |
| SOV_NFR_A | REGIME_NFR_OCC | 1914-10-13～1918-11-11 | not_sovereign | relation/2866012 v31 ∩ 1914 年底西線以北／以東（手繪近似線（build/make_requests.py）） | EV_NFR_FRONT | EV_COMPIEGNE | sub1 |
| SOV_NO_R | REGIME_NO | 1908-10-06～1918-11-12 | de_jure | relation/2692537 v28 | — | — | sub1 |
| SOV_OBER_OST_A_1 | REGIME_OBER_OST | 1915-09-19～1918-02-09 | not_sovereign | relation/2696283 v32 | EV_VILNA | EV_BREST_UA | sub1 |
| SOV_OT_E_R | REGIME_OT | 1913-05-30～1918-10-30 | de_jure | relation/2849728 v55 − relation/2848136 v6 − relation/2830316 v10 − 阿爾巴尼亞 | EV_LONDON | EV_MUDROS | sub1 |
| SOV_RO_B_R | REGIME_RO | 1913-08-10～1916-10-22 | de_jure | relation/2693260 v64 | EV_BUCHAREST | EV_DOBRUJA_OCC | sub1 |
| SOV_RS_B_R | REGIME_RS | 1913-08-10～1915-11-28 | de_jure | relation/2746681 v36 | EV_BUCHAREST | EV_SERBIA_FALL | sub1 |
| SOV_RU_EMP_R | REGIME_RU_EMP | 1908-10-06～1915-08-05 | de_jure | relation/2849760 v126 | — | EV_WARSAW | sub1 |
| SOV_RU_EMP_2 | REGIME_RU_EMP | 1915-08-05～1915-09-19 | de_jure | relation/2849760 v126 − 華沙總督府 − 盧布林軍事總督府 | EV_WARSAW | EV_VILNA | sub1 |
| SOV_RU_EMP_3 | REGIME_RU_EMP | 1915-09-19～1916-11-05 | de_jure | relation/2849760 v126 − 華沙總督府 − 盧布林軍事總督府 − Ober Ost | EV_VILNA | EV_PL_KINGDOM | sub1 |
| SOV_SE_R | REGIME_SE | 1908-10-06～1918-11-12 | de_jure | relation/2692524 v33 | — | — | sub1 |
| SOV_SERBIA_BG | REGIME_SERBIA_BG | 1915-11-28～1918-09-29 | not_sovereign | relation/2746681 v36 ∩ 北緯 42.35° 以南（馬其頓）＋東經 21.5° 以東、北緯 43.9° 以南（摩拉瓦）（手繪近似線（build/make_requests.py）） | EV_SERBIA_FALL | EV_BG_ARMISTICE | sub1 |
| SOV_TN_R | REGIME_TN | 1908-10-06～1918-11-12 | de_jure | relation/2690947 v20 | — | — | sub1 |
| SOV_UK_GBI_R | REGIME_UK_GBI | 1908-10-06～1918-11-12 | de_jure | relation/2828388 v26 | — | — | sub1 |
| SOV_US | REGIME_US | 1914-07-29～1918-11-12 | de_jure | relation/2874803 v33 − relation/2889834 v1 | — | — | sub1 |
| SOV_DOB_A | REGIME_DOBRUJA | 1916-10-22～1918-05-07 | not_sovereign | 南多布羅加（relation/2693260 v64 − relation/2692219 v68）∪ 北多布羅加（relation/2692219 v68 ∩ 多瑙河以東，手繪近似線（build/make_requests.py）） | EV_DOBRUJA_OCC | EV_BUCH18 | sub2 |
| SOV_FI_A | REGIME_FI | 1917-12-06～1918-08-31 | de_jure | relation/2696817 v28 | EV_FI_INDEP | — | sub2 |
| SOV_MGG_MN | REGIME_MGG_MN | 1916-01-13～1918-11-03 | not_sovereign | relation/2739656 v22 | EV_MN_OCC | EV_VILLA_GIUSTI | sub2 |
| SOV_PL_REGENCY | REGIME_PL_REGENCY | 1916-11-05～1918-11-11 | not_sovereign | relation/2695684 v79 | EV_PL_KINGDOM | EV_PL_INDEP | sub2 |
| SOV_RO_B_2 | REGIME_RO | 1916-10-22～1916-12-06 | de_jure | relation/2693260 v64 − 多布羅加佔領區 | EV_DOBRUJA_OCC | EV_BUCHAREST_FALL | sub2 |
| SOV_RO_B_3 | REGIME_RO | 1916-12-06～1918-04-09 | de_jure | relation/2693260 v64 − 多布羅加佔領區 − 羅馬尼亞佔領區 | EV_BUCHAREST_FALL | EV_BESSARABIA | sub2 |
| SOV_RO_WAL | REGIME_RO_MILVERW | 1916-12-06～1918-11-12 | not_sovereign | relation/2693260 v64 − 未佔領的摩爾達維亞（手繪近似線（build/make_requests.py））− 多布羅加 | EV_BUCHAREST_FALL | — | sub2 |
| SOV_RSFSR_A_1 | REGIME_RSFSR | 1917-11-07～1917-11-15 | de_jure | relation/2849760 v126 − 波蘭攝政王國 − Ober Ost | EV_OCT_REV | EV_TC | sub2 |
| SOV_RSFSR_A_2 | REGIME_RSFSR | 1917-11-15～1917-12-06 | de_jure | relation/2849760 v126 − 外高加索 − 波蘭攝政王國 − Ober Ost | EV_TC | — | sub2 |
| SOV_RSFSR_B | REGIME_RSFSR | 1917-12-06～1918-01-24 | de_jure | relation/2852344 v118 − 外高加索 − 波蘭攝政王國 − Ober Ost | — | — | sub2 |
| SOV_RU_EMP_4 | REGIME_RU_EMP | 1916-11-05～1917-03-15 | de_jure | relation/2849760 v126 − 波蘭攝政王國 − Ober Ost | EV_PL_KINGDOM | EV_FEB_REV | sub2 |
| SOV_RU_PROV_A | REGIME_RU_PROV | 1917-03-15～1917-09-14 | de_jure | relation/2849760 v126 − 波蘭攝政王國 − Ober Ost | EV_FEB_REV | EV_RU_REPUBLIC | sub2 |
| SOV_RU_PROV_B | REGIME_RU_PROV | 1917-09-14～1917-11-07 | de_jure | relation/2869933 v74 | EV_RU_REPUBLIC | EV_OCT_REV | sub2 |
| SOV_TC | REGIME_TC_COMM | 1917-11-15～1918-04-22 | not_sovereign | relation/2957453 v8 | EV_TC | EV_TDFR | sub2 |
| SOV_AH_2 | REGIME_AH | 1918-10-28～1918-10-29 | de_jure | relation/2692361 v267 − 捷克斯洛伐克 | EV_CS | EV_SCS | sub3 |
| SOV_AH_3 | REGIME_AH | 1918-10-29～1918-11-12 | de_jure | relation/2692361 v267 − 捷克斯洛伐克 − 斯洛維尼亞人、克羅埃西亞人和塞爾維亞人國 | EV_SCS | — | sub3 |
| SOV_AM | REGIME_AM | 1918-05-28～1918-11-12 | de_jure | relation/2698116 v12 | EV_AM_AZ | — | sub3 |
| SOV_AZ | REGIME_AZ | 1918-05-28～1918-11-12 | de_jure | relation/2698117 v13 | EV_AM_AZ | — | sub3 |
| SOV_BALTIC | REGIME_BALTIC_OCC | 1918-03-03～1918-11-12 | not_sovereign | relation/2744426 v18 ∪ relation/2869679 v5 − republic-of-estonia | EV_BREST | — | sub3 |
| SOV_BE_4 | REGIME_BE | 1918-11-11～1918-11-12 | de_jure | relation/2797729 v43 − 比利時佔領區 | EV_COMPIEGNE | — | sub3 |
| SOV_BG_C | REGIME_BG | 1918-05-07～1918-11-12 | de_jure | relation/2746680 v29 ∪ 南多布羅加（relation/2693260 v64 − relation/2692219 v68） | EV_BUCH18 | — | sub3 |
| SOV_BY | REGIME_BY_PR | 1918-03-25～1918-11-12 | not_sovereign | relation/2957449 v6 − 烏克蘭 | EV_BY_PR | — | sub3 |
| SOV_CS | REGIME_CS | 1918-10-28～1918-11-12 | de_jure | relation/2747877 v61 | EV_CS | — | sub3 |
| SOV_DOB_B | REGIME_DOBRUJA | 1918-05-07～1918-11-12 | not_sovereign | relation/2692219 v68 ∩ 多瑙河以東（手繪近似線（build/make_requests.py）） | EV_BUCH18 | — | sub3 |
| SOV_FI_B | REGIME_FI | 1918-08-31～1918-09-12 | de_jure | relation/2959044 v7 | — | — | sub3 |
| SOV_FI_C | REGIME_FI | 1918-09-12～1918-11-12 | de_jure | relation/2959043 v7 | — | — | sub3 |
| SOV_FR3_3 | REGIME_FR3 | 1918-11-11～1918-11-12 | de_jure | relation/2866012 v31 − 法國北部佔領區 | EV_COMPIEGNE | — | sub3 |
| SOV_GE | REGIME_GE | 1918-05-26～1918-11-12 | de_jure | relation/2698086 v23 | EV_GE | — | sub3 |
| SOV_GG_BE_C | REGIME_GG_BE | 1918-11-11～1918-11-12 | not_sovereign | relation/2797729 v43 ∩ 停戰線以東（手繪近似線（build/make_requests.py）） | EV_COMPIEGNE | — | sub3 |
| SOV_LT | REGIME_LT_1918 | 1918-03-03～1918-11-12 | not_sovereign | relation/2744425 v20 | EV_BREST | — | sub3 |
| SOV_MN_K_B_3 | REGIME_MN_K | 1918-11-03～1918-11-12 | de_jure | relation/2739656 v22 | EV_VILLA_GIUSTI | — | sub3 |
| SOV_MRNC | REGIME_MRNC | 1918-05-11～1918-11-12 | de_jure | relation/2891769 v9 | EV_MRNC | — | sub3 |
| SOV_NFR_B | REGIME_NFR_OCC | 1918-11-11～1918-11-12 | not_sovereign | relation/2866012 v31 ∩ 停戰線以東（手繪近似線（build/make_requests.py）） | EV_COMPIEGNE | — | sub3 |
| SOV_OBER_OST_A_2 | REGIME_OBER_OST | 1918-02-09～1918-03-03 | not_sovereign | relation/2696283 v32 − 烏克蘭 | EV_BREST_UA | EV_BREST | sub3 |
| SOV_OBER_OST_B | REGIME_OBER_OST | 1918-03-03～1918-11-12 | not_sovereign | relation/2744424 v7 − 烏克蘭 | EV_BREST | — | sub3 |
| SOV_OT_F | REGIME_OT | 1918-10-30～1918-11-12 | de_jure | relation/2920989 v11 − relation/2848136 v6 − relation/2830316 v10 − relation/2855613 v8 | EV_MUDROS | — | sub3 |
| SOV_PL | REGIME_PL | 1918-11-11～1918-11-12 | de_jure | relation/2695684 v79 | EV_PL_INDEP | — | sub3 |
| SOV_RO_B_4 | REGIME_RO | 1918-04-09～1918-05-07 | de_jure | relation/2693260 v64 − 多布羅加佔領區 − 羅馬尼亞佔領區 ∪ 比薩拉比亞（relation/2694154 v35） | EV_BESSARABIA | EV_BUCH18 | sub3 |
| SOV_RO_C | REGIME_RO | 1918-05-07～1918-11-12 | de_jure | relation/2693260 v64 − 南多布羅加 − 多布羅加佔領區 − 羅馬尼亞佔領區 ∪ 比薩拉比亞（relation/2694154 v35） | EV_BUCH18 | — | sub3 |
| SOV_RS_B_3 | REGIME_RS | 1918-09-29～1918-11-03 | de_jure | relation/2746681 v36 − 奧匈佔領的塞爾維亞 | EV_BG_ARMISTICE | EV_VILLA_GIUSTI | sub3 |
| SOV_RS_B_4 | REGIME_RS | 1918-11-03～1918-11-12 | de_jure | relation/2746681 v36 | EV_VILLA_GIUSTI | — | sub3 |
| SOV_RSFSR_C_1 | REGIME_RSFSR | 1918-01-24～1918-02-09 | de_jure | relation/2850854 v105 − 外高加索 | — | EV_BREST_UA | sub3 |
| SOV_RSFSR_C_2 | REGIME_RSFSR | 1918-02-09～1918-03-25 | de_jure | relation/2850854 v105 − 烏克蘭 − 外高加索 | EV_BREST_UA | EV_BY_PR | sub3 |
| SOV_RSFSR_C_3 | REGIME_RSFSR | 1918-03-25～1918-04-22 | de_jure | relation/2850854 v105 − 烏克蘭 − 白俄羅斯人民共和國 − 外高加索 | EV_BY_PR | — | sub3 |
| SOV_RSFSR_D_1 | REGIME_RSFSR | 1918-04-22～1918-05-11 | de_jure | relation/2957452 v31 − 烏克蘭 − 白俄羅斯人民共和國 | — | EV_MRNC | sub3 |
| SOV_RSFSR_D_2 | REGIME_RSFSR | 1918-05-11～1918-08-31 | de_jure | relation/2957452 v31 − 烏克蘭 − 白俄羅斯人民共和國 − 北高加索山地共和國 | EV_MRNC | — | sub3 |
| SOV_RSFSR_E | REGIME_RSFSR | 1918-08-31～1918-09-12 | de_jure | relation/2959041 v17 − 烏克蘭 − 白俄羅斯人民共和國 − 北高加索山地共和國 | — | — | sub3 |
| SOV_RSFSR_F | REGIME_RSFSR | 1918-09-12～1918-11-12 | de_jure | relation/2959042 v17 − 烏克蘭 − 白俄羅斯人民共和國 − 北高加索山地共和國 | — | — | sub3 |
| SOV_SCS | REGIME_SCS | 1918-10-29～1918-11-12 | not_sovereign | relation/2747879 v43 | EV_SCS | — | sub3 |
| SOV_TDFR_A | REGIME_TDFR | 1918-04-22～1918-05-26 | de_jure | relation/2957454 v8 | EV_TDFR | EV_GE | sub3 |
| SOV_TDFR_B | REGIME_TDFR | 1918-05-26～1918-05-28 | de_jure | relation/2957459 v4 − 喬治亞 | EV_GE | EV_AM_AZ | sub3 |
| SOV_UA_1 | REGIME_UA_PR | 1918-02-09～1918-04-09 | de_jure | relation/2694815 v77 − 波蘭攝政王國 | EV_BREST_UA | EV_BESSARABIA | sub3 |
| SOV_UA_2 | REGIME_UA_PR | 1918-04-09～1918-11-12 | de_jure | relation/2694815 v77 − 比薩拉比亞 − 波蘭攝政王國 | EV_BESSARABIA | — | sub3 |

## 佔領歸屬

| placeholder | 被佔領 | 佔領方 | 管理 | 期間 | 共同 | 子批 |
|---|---|---|---|---|---|---|
| OCC_IT_AEGEAN_R | REGIME_IT_AEGEAN | REGIME_IT | military_administration | 1912-04-27～1918-11-12 |  | sub1 |
| OCC_LU | REGIME_LU | REGIME_DE_EMP | military_administration | 1914-08-02～1918-11-12 |  | sub1 |
| OCC_GG_BE | REGIME_GG_BE | REGIME_DE_EMP | civil_administration | 1914-08-20～1918-11-12 |  | sub1 |
| OCC_NFR | REGIME_NFR_OCC | REGIME_DE_EMP | military_administration | 1914-10-13～1918-11-12 |  | sub1 |
| OCC_GG_WARSAW | REGIME_GG_WARSAW | REGIME_DE_EMP | civil_administration | 1915-08-05～1916-11-05 |  | sub1 |
| OCC_GG_LUBLIN | REGIME_GG_LUBLIN | REGIME_AH | military_administration | 1915-08-05～1916-11-05 |  | sub1 |
| OCC_OBER_OST | REGIME_OBER_OST | REGIME_DE_EMP | military_administration | 1915-09-19～1918-11-12 |  | sub1 |
| OCC_SERBIA_BG | REGIME_SERBIA_BG | REGIME_BG | annexed | 1915-11-28～1918-09-29 |  | sub1 |
| OCC_MGG_SERBIA | REGIME_MGG_SERBIA | REGIME_AH | military_administration | 1915-11-28～1918-11-03 |  | sub1 |
| OCC_PL_REGENCY | REGIME_PL_REGENCY | REGIME_DE_EMP | civil_administration | 1916-11-05～1918-11-11 | 是 | sub2 |
| OCC_MGG_MN | REGIME_MGG_MN | REGIME_AH | military_administration | 1916-01-13～1918-11-03 |  | sub2 |
| OCC_DOBRUJA | REGIME_DOBRUJA | REGIME_BG | military_administration | 1916-10-22～1918-11-12 | 是 | sub2 |
| OCC_RO_WAL | REGIME_RO_MILVERW | REGIME_DE_EMP | military_administration | 1916-12-06～1918-11-12 | 是 | sub2 |
| OCC_LT_1918 | REGIME_LT_1918 | REGIME_DE_EMP | military_administration | 1918-03-03～1918-11-12 |  | sub3 |
| OCC_BALTIC | REGIME_BALTIC_OCC | REGIME_DE_EMP | military_administration | 1918-03-03～1918-11-12 |  | sub3 |
| OCC_EE | REGIME_EE | REGIME_DE_EMP | military_administration | 1918-02-24～1918-11-12 |  | sub3 |
| OCC_BY | REGIME_BY_PR | REGIME_DE_EMP | military_administration | 1918-03-25～1918-11-12 |  | sub3 |

## 衝突紀錄

| placeholder | A | B | 起 | 迄 | 位置 | 子批 |
|---|---|---|---|---|---|---|
| CF_DE_RU | REGIME_DE_EMP | REGIME_RU_EMP | EV_DE_RU_WAR | EV_FEB_REV | [19.9679, 53.2074]：本批主權紀錄在開戰日 1914-08-01 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub1 |
| CF_DE_FR | REGIME_DE_EMP | REGIME_FR3 | EV_DE_FR_WAR | EV_COMPIEGNE | [6.83, 48.6448]：本批主權紀錄在開戰日 1914-08-03 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub1 |
| CF_DE_BE | REGIME_DE_EMP | REGIME_BE | EV_DE_BE_INV | EV_COMPIEGNE | [6.0097, 50.4903]：本批主權紀錄在開戰日 1914-08-04 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub1 |
| CF_UK_DE | REGIME_UK_GBI | REGIME_DE_EMP | EV_UK_DE_WAR | EV_COMPIEGNE | [2.885, 50.85]：伊珀爾（英軍西線主要戰區，固定點） | sub1 |
| CF_AH_RU | REGIME_AH | REGIME_RU_EMP | EV_AH_RU_WAR | EV_FEB_REV | [22.6878, 50.3556]：本批主權紀錄在開戰日 1914-08-06 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub1 |
| CF_AH_MN | REGIME_AH | REGIME_MN_K | EV_AH_MN_WAR | EV_VILLA_GIUSTI | [18.5595, 43.0326]：本批主權紀錄在開戰日 1914-08-09 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub1 |
| CF_FR_AH | REGIME_FR3 | REGIME_AH | EV_FR_AH_WAR | EV_VILLA_GIUSTI | [18.5, 40.2]：奧特朗托海峽（協約國封鎖亞得里亞海，固定點） | sub1 |
| CF_UK_AH | REGIME_UK_GBI | REGIME_AH | EV_UK_AH_WAR | EV_VILLA_GIUSTI | [18.65, 40.05]：奧特朗托海峽（協約國封鎖亞得里亞海，固定點） | sub1 |
| CF_OT_RU | REGIME_OT | REGIME_RU_EMP | EV_OT_ENTRY | EV_FEB_REV | [42.4201, 40.1407]：本批主權紀錄在開戰日 1914-10-29 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub1 |
| CF_UK_OT | REGIME_UK_GBI | REGIME_OT | EV_ENTENTE_OT_WAR | EV_MUDROS | [26.4, 40.2]：加里波利（協約國登陸地，固定點；巴勒斯坦、美索不達米亞戰線未另立） | sub1 |
| CF_FR_OT | REGIME_FR3 | REGIME_OT | EV_ENTENTE_OT_WAR | EV_MUDROS | [26.3, 40.1]：加里波利（協約國登陸地，固定點；巴勒斯坦、美索不達米亞戰線未另立） | sub1 |
| CF_IT_AH | REGIME_IT | REGIME_AH | EV_IT_AH_WAR | EV_VILLA_GIUSTI | [11.8375, 46.271]：本批主權紀錄在開戰日 1915-05-23 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub1 |
| CF_IT_OT | REGIME_IT | REGIME_OT | EV_IT_OT_WAR | EV_MUDROS | [13.19, 32.89]：的黎波里（義軍在利比亞與賽努西部落及鄂圖曼作戰，固定點） | sub1 |
| CF_BG_RS | REGIME_BG | REGIME_RS | EV_BG_RS_WAR | EV_BG_ARMISTICE | [22.3589, 42.7908]：本批主權紀錄在開戰日 1915-10-14 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub1 |
| CF_UK_BG | REGIME_UK_GBI | REGIME_BG | EV_ENTENTE_BG_WAR | EV_BG_ARMISTICE | [22.5, 41.1]：薩洛尼卡戰線（馬其頓前線，固定點） | sub1 |
| CF_FR_BG | REGIME_FR3 | REGIME_BG | EV_ENTENTE_BG_WAR | EV_BG_ARMISTICE | [22.2, 41.15]：薩洛尼卡戰線（馬其頓前線，固定點） | sub1 |
| CF_IT_BG | REGIME_IT | REGIME_BG | EV_ENTENTE_BG_WAR | EV_BG_ARMISTICE | [21.6, 41.05]：薩洛尼卡戰線（馬其頓前線，固定點） | sub1 |
| CF_RU_BG | REGIME_RU_EMP | REGIME_BG | EV_ENTENTE_BG_WAR | EV_FEB_REV | [28.3, 44.2]：多布羅加（1916 年戰區，固定點） | sub1 |
| CF_AH_RS_R | REGIME_AH | REGIME_RS | EV_AH_RS_WAR | EV_VILLA_GIUSTI | [19.6402, 44.96]：本批主權紀錄在開戰日 1914-07-28 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub1 |
| CF_DE_PT | REGIME_DE_EMP | REGIME_PT | EV_DE_PT_WAR | EV_COMPIEGNE | [2.75, 50.62]：利斯河（1918-04 葡萄牙軍在此作戰，固定點） | sub2 |
| CF_RO_AH | REGIME_RO | REGIME_AH | EV_RO_ENTRY | EV_BUCH18 | [26.496, 46.1291]：本批主權紀錄在開戰日 1916-08-27 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub2 |
| CF_RO_DE | REGIME_RO | REGIME_DE_EMP | EV_CP_RO_WAR | EV_BUCH18 | [25.6, 44.6]：阿爾傑什河（1916-12 布加勒斯特戰役，固定點） | sub2 |
| CF_RO_BG | REGIME_RO | REGIME_BG | EV_CP_RO_WAR | EV_BUCH18 | [25.3309, 43.638]：本批主權紀錄在開戰日 1916-08-28 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub2 |
| CF_RO_OT | REGIME_RO | REGIME_OT | EV_CP_RO_WAR | EV_BUCH18 | [28.45, 44.35]：多布羅加（1916 年戰區，固定點） | sub2 |
| CF_IT_DE | REGIME_IT | REGIME_DE_EMP | EV_IT_DE_WAR | EV_COMPIEGNE | [13.55, 46.25]：卡波雷托（1917-10 德奧聯軍突破處，固定點） | sub2 |
| CF_US_DE | REGIME_US | REGIME_DE_EMP | EV_US_DE_WAR | EV_COMPIEGNE | [5.7, 48.9]：聖米耶勒（1918-09 美軍首次獨立攻勢，固定點） | sub2 |
| CF_GR_BG | REGIME_GR | REGIME_BG | EV_GR_WAR | EV_BG_ARMISTICE | [24.1111, 41.5432]：本批主權紀錄在開戰日 1917-07-02 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub2 |
| CF_GR_DE | REGIME_GR | REGIME_DE_EMP | EV_GR_WAR | EV_COMPIEGNE | [22.8, 41.05]：薩洛尼卡戰線（馬其頓前線，固定點） | sub2 |
| CF_US_AH | REGIME_US | REGIME_AH | EV_US_AH_WAR | EV_VILLA_GIUSTI | [12.3, 45.98]：維托里奧威尼托（1918-10 美軍第 332 團參戰，固定點） | sub2 |
| CF_RUP_DE | REGIME_RU_PROV | REGIME_DE_EMP | EV_FEB_REV | EV_OCT_REV | [24.0, 56.8]：里加—德維納河前線（固定點） | sub2 |
| CF_RUP_AH | REGIME_RU_PROV | REGIME_AH | EV_FEB_REV | EV_OCT_REV | [26.2111, 48.8642]：本批主權紀錄在開戰日 1917-03-15 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub2 |
| CF_RUP_OT | REGIME_RU_PROV | REGIME_OT | EV_FEB_REV | EV_OCT_REV | [42.4192, 40.1416]：本批主權紀錄在開戰日 1917-03-15 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub2 |
| CF_RUP_BG | REGIME_RU_PROV | REGIME_BG | EV_FEB_REV | EV_OCT_REV | [27.2, 45.7]：福克沙尼—錫雷特河前線（俄、羅軍與同盟國，固定點） | sub2 |
| CF_RSFSR_DE | REGIME_RSFSR | REGIME_DE_EMP | EV_OCT_REV | EV_BREST | [24.3, 56.9]：里加—德維納河前線（固定點） | sub2 |
| CF_RSFSR_AH | REGIME_RSFSR | REGIME_AH | EV_OCT_REV | EV_BREST | [26.2111, 48.8642]：本批主權紀錄在開戰日 1917-11-07 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub2 |
| CF_RSFSR_OT | REGIME_RSFSR | REGIME_OT | EV_OCT_REV | EV_BREST | [42.4192, 40.1416]：本批主權紀錄在開戰日 1917-11-07 的兩國共同邊界，最長一段的中點（build/make_requests.py border_mid） | sub2 |
| CF_RSFSR_BG | REGIME_RSFSR | REGIME_BG | EV_OCT_REV | EV_BREST | [27.35, 45.8]：福克沙尼—錫雷特河前線（俄、羅軍與同盟國，固定點） | sub2 |

## 近似與未畫（待查證）

- 西線：1914-10-13 起法國北部與比利時佔領區用手繪的 1914 年底穩定前線（`FRONT_1914`），1918-11-11 用手繪停戰線（`ARMISTICE_1918`）。1917 年興登堡防線撤退、1918 年春季攻勢與百日攻勢的前線變化未畫。比利時 8-20～10-10 用六省省界近似。
- 塞爾維亞：保加利亞佔領（併入）區用經緯度方框粗略近似（北緯 42.35° 以南＋東經 21.5° 以東、北緯 43.9° 以南）；1918 年秋的逐步解放未畫（保加利亞區在薩洛尼卡停戰時、奧匈區在朱斯蒂別墅停戰時整塊歸還）。
- 羅馬尼亞：多布羅加以多瑙河近似線、未佔領的摩爾達維亞以錫雷特河—奧伊圖茲近似線手繪；1918 年喀爾巴阡山口割讓、1916 年羅軍進入外西凡尼亞未畫。
- 東線：1914～1915 年俄軍佔領東普魯士與東加利西亞、1916 年布魯西洛夫攻勢、1917-09 德軍佔領里加、1918-02 德軍推進（拉特加萊、白俄羅斯東部）未畫；1918-01-24 起 OHM 俄羅斯蘇維埃共和國不含拉特加萊、維捷布斯克西部與比薩拉比亞，這些地區在 1918-01-24～03-03（比薩拉比亞到 04-09）留白。
- 烏克蘭、喬治亞的德奧駐軍未設佔領歸屬；烏克蘭國（1918-04-29 起）未另立政權；摩爾達維亞民主共和國未畫。
- 中東：鄂圖曼在阿拉伯半島、美索不達米亞、巴勒斯坦的失地（巴格達 1917-03、耶路撒冷 1917-12）與 1916～1917 年俄軍佔領土屬亞美尼亞未畫；巴統條約割地未畫。
- 阿爾巴尼亞 1915～1918 多國分區佔領、義大利 1917 年卡波雷托後失去的威尼托、保加利亞佔領希臘東馬其頓、中立莫雷斯內的德國管理未畫。
- 德國 1918-11-09 革命、奧匈 1918-10 起的瓦解（德意志奧地利、匈牙利、西烏克蘭、加利西亞）未改政權，只在紀錄說明。
- 美國紀錄照抄開發庫 1937 年起的幾何（給衝突弧線用），1914～1918 年差異未處理。
