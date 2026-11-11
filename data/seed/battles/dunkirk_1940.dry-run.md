# 戰役 seed dry-run 報表：dunkirk_1940（敦克爾克橋頭堡戰役）

- 圖形來源：`frontend/public/campaigns/dunkirk_1940.json`（sha256 `072f237476e8fb30…`）
- 考證輸入：`data/seed/battles/dunkirk_1940.research.json`（dynamo-research/0.1（seed 提案，未入庫），sha256 `a7cc516f22a12671…`）
- raw 原文 sha256：ellis-11 `7c67433e7839…`、ellis-12 `fd398b60d9fe…`、ellis-13 `35e6cac20855…`、ellis-14 `7c1b4e88eaa0…`、ellis-15 `19e3019011be…`、ellis-16 `fdd3b2ca3823…`、ramsay `e43d24cf35e3…`
- 產生：`tools/battles/import_campaign_seed.py`（不連資料庫；不含時間戳，重跑逐位元相同）
- 定性：battle：敦克爾克橋頭堡戰役（1940-05-26～06-04）；發電機行動為子事件（parent_event_id），不是階段（Tai 2026-11-11 13:47（併入考證、橋頭堡戰役、六階段、A 級引文））
- 全部 status＝pending；寫庫與 verified 判定需 Tai 另行核准。
- 等級規則：來源為 A、raw 逐字找得到、NFC 後 ≤80 字 → A；其餘 pending。超過 80 字者截成 raw 逐字子句。

## 摘要

| 項目 | 數量 |
|---|---|
| citation 總數（含 deferred） | 67 |
| 　A | 62 |
| 　B | 0 |
| 　pending（無等級） | 5 |
| 　其中截成逐字子句後標 A | 10 |
| 　考證輸入引文（research） | 42（A 42） |
| 　前端舊引文（web-json） | 25（A 20） |
| 　quote 超過 80 字 | 5 |
| 　缺 accessed_on | 0 |
| 階段 | 6 |
| 圖形 front（已配階段） | 5 |
| 圖形 arrow（已配階段） | 7 |
| 圖形 site（已配階段） | 12 |
| 圖形 deferred（P6 不配圖） | 2 |
| geom_basis＝derived（推估幾何，pending） | 21 |
| 無任何 citation 的圖形 | 2 |
| 來源（sources） | 2（publisher 已填） |

## 戰役主體（historical_events＋battle_profiles）

| 欄位 | 值 | citation（A／全部） | 狀態 |
|---|---|---|---|
| event_kind | battle | — | 憲法 §6 三條件皆有 A 級出處 |
| occurred | 1940-05-26～1940-06-05（半開；含終點 1940-06-04） | 7／7 | pending（符合 verified 門檻：是） |
| 交戰方 deutsches-reich | axis | 2／2 | pending |
| 交戰方 french-third-republic | allied | 2／2 | pending |
| 交戰方 kingdom-of-belgium（至 1940-05-28，半開） | allied | 2／2 | pending |
| 交戰方 united-kingdom | allied | 1／1 | pending |
| name | 敦克爾克橋頭堡戰役 / Battle of Dunkirk bridgehead | 0／0 | pending（Tai 2026-11-11 13:47 指定名稱；Ellis 與 Ramsay 均未用 'Battle of Dunkirk' 一詞；戰役名稱的 A／B 出處待查證（名稱不影響 §6 判定）） |
| objective | 同盟國：守住掩護敦克爾克的橋頭堡，以便自敦克爾克港與海灘撤出部隊；德國：殲滅被圍於敦克爾克以南、東南之敵軍並奪取該地區 | 5／5 | pending |
| objective_kind | null（候選 place） | — | 待人確認；NOT NULL，未決前不能寫庫 |
| control_change | 周界逐步縮小（5/31 夜放棄東段，6/1–6/3 退至 Dunkirk–Furnes 運河線），6/4 上午 9 時殘餘法軍投降，敦克爾克落入德軍控制 | 3／3 | pending |
| 範圍（文字） | 敦克爾克橋頭堡：沿運河線自 Mardyck 經 Spycker、Bergues、Furnes 至 Nieuport，全長約 30 英里；含敦克爾克港與以東海灘 | 2／2 | pending |
| theater_area（幾何） | 前端 bounds 外框 | 無（derived） | 待依出處圖重畫 |
| outcome_kind／outcome_text | null | 無 | 沒有出處就留 NULL |
| 子事件 發電機行動（Operation Dynamo） | 1940-05-26～1940-06-05（半開），parent＝本戰役 | 4／4 | pending；event_kind 待決 |

## 階段（battle_phases）

| seq | 名稱 | 期間（半開） | 精度 | citation（A／全部） | 出處圖 | 圖形數 | 狀態 |
|---|---|---|---|---|---|---|---|
| P1 | 決定撤退、發電機行動啟動與周界編成 | 1940-05-26～1940-05-28 | day | 3／3 | Ellis Situation Map 'Situation on the evening of 26th May, 1940', facing p. 182；Ellis Situation Map 'Situation on the evening of 27th May, 1940', facing p. 200 | 8 | pending（門檻：是） |
| P2 | 比軍投降後撤向海岸 | 1940-05-28～1940-05-29 | day | 1／1 | Ellis Situation Map 'The Withdrawal to the Coast', facing p. 202；Ellis Situation Map 'Situation on the evening of 28th May, 1940', facing p. 214 | 5 | pending（門檻：是） |
| P3 | 最後撤入橋頭堡 | 1940-05-29～1940-05-30 | day | 1／1 | Ellis Situation Map 'Situation on the evening of 29th May, 1940', facing p. 224 | 0 | pending（門檻：是） |
| P4 | 橋頭堡防禦 | 1940-05-30～1940-06-01 | day | 3／3 | Ellis Situation Map 'Situation on the evening of 30th May, 1940', facing p. 238 | 6 | pending（門檻：是） |
| P5 | 縮小周界與英軍最後撤離 | 1940-06-01～1940-06-03 | day | 3／3 | Ellis Situation Map 'Situation on the evening of 1st June, 1940', facing p. 244 | 5 | pending（門檻：是） |
| P6 | 法軍後衛與敦克爾克陷落 | 1940-06-03～1940-06-05 | day | 3／3 | **pending**（待查證：Ellis 無 6/2–6/4 situation map；候選 USMA 'Campaign in the West, Situation 4 June 1940'（見 mapSources）） | 0 | pending（門檻：是） |

## 圖形（battle_map_features）

| feature_key | 前端舊段→新段 | 種類 | 配色組 | geom_basis | citation（A／全部） | 部隊番號 | 狀態 |
|---|---|---|---|---|---|---|---|
| dunkirk_1940_p1-front-0 | P1→P1 | front | allied | source_text | 1／1 | — | pending |
| dunkirk_1940_p2-front-0 | P2→P2 | front | allied | source_text | 1／1 | — | pending |
| dunkirk_1940_p3-front-0 | P3→P4 | front | allied | source_text | 1／1 | — | pending |
| dunkirk_1940_p4-front-0 | P4→P5 | front | allied | source_text | 1／1 | — | pending |
| dunkirk_1940_p4-front-1 | P4→P5 | front | unknown | source_text | 1／1 | — | pending |
| dunkirk_1940_p1-arrow-0 | P1→P1 | arrow | axis | derived | 1／1 | 德軍 A 集團軍群 Kleist 裝甲集群（待查證） | pending |
| dunkirk_1940_p1-arrow-1 | P1→P1 | arrow | axis | derived | 1／1 | 德軍 B 集團軍群第6軍團（三個師）（待查證） | pending |
| dunkirk_1940_p1-arrow-2 | P1→P1 | arrow | axis | derived | 0／1 | 德軍 Hoth 集群（待查證） | pending |
| dunkirk_1940_p2-arrow-0 | P2→P2 | arrow | axis | derived | 0／1 | 德軍（比軍投降後沿海岸推進之部隊，番號待查）（待查證） | pending |
| dunkirk_1940_p3-arrow-0 | P3→P4 | arrow | axis | derived | 1／1 | 德軍（番號待查）（待查證） | pending |
| dunkirk_1940_p3-arrow-1 | P3→P4 | arrow | axis | derived | 1／1 | 德軍（番號待查）（待查證） | pending |
| dunkirk_1940_p4-arrow-0 | P4→P5 | arrow | axis | derived | 0／1 | 德軍（番號待查）（待查證） | pending |
| dunkirk_1940_p1-site-0 | P1→P1 | site | axis | derived | 1／1 | — | pending |
| dunkirk_1940_p1-site-1 | P1→P1 | site | axis | derived | 1／1 | — | pending |
| dunkirk_1940_p1-site-2 | P1→P1 | site | allied | derived | 1／1 | — | pending |
| dunkirk_1940_p1-site-3 | P1→P1 | site | contested | derived | 1／1 | — | pending |
| dunkirk_1940_p2-site-0 | P2→P2 | site | contested | derived | 0／1 | — | pending |
| dunkirk_1940_p2-site-1 | P2→P2 | site | axis | derived | 1／1 | — | pending |
| dunkirk_1940_p2-site-2 | P2→P2 | site | allied | derived | 1／1 | — | pending |
| dunkirk_1940_p3-site-0 | P3→P4 | site | contested | derived | 0／1 | — | pending |
| dunkirk_1940_p3-site-1 | P3→P4 | site | allied | derived | 1／1 | — | pending |
| dunkirk_1940_p3-site-2 | P3→P4 | site | contested | derived | 1／1 | — | pending |
| dunkirk_1940_p4-site-0 | P4→P5 | site | axis | derived | 0／0 | — | pending；**缺出處** |
| dunkirk_1940_p4-site-1 | P4→P5 | site | axis | derived | 1／1 | — | pending |
| dunkirk_1940_p5-site-0 | P5→不配（deferred） | site | axis | derived | 1／1 | — | pending |
| dunkirk_1940_p5-site-1 | P5→不配（deferred） | site | axis | derived | 0／0 | — | pending；**缺出處** |

## pending 引文明細

| 所屬 | 引文（前 60 字） | 原因 |
|---|---|---|
| feature:dunkirk_1940_p1-arrow-2 | Hoth Group, starting from the Béthune–La Bassée area, also s… | 原引文 102 字超過 80，且 raw 原文中找不到逐字相符的子句 |
| feature:dunkirk_1940_p2-arrow-0 | advanced troops of the enemy reached the perimeter between N… | 原引文 85 字超過 80，截不出 raw 逐字存在的子句 |
| feature:dunkirk_1940_p4-arrow-0 | At Hoymille the attack penetrated the front held by a compan… | 原引文 85 字超過 80，截不出 raw 逐字存在的子句 |
| feature:dunkirk_1940_p2-site-0 | capturing and holding an undestroyed bridge and a small brid… | 原引文 90 字超過 80，截不出 raw 逐字存在的子句 |
| feature:dunkirk_1940_p3-site-0 | There had been fighting all day at Nieuport and while attack… | 原引文 106 字超過 80，截不出 raw 逐字存在的子句 |

## 截成逐字子句的引文

- feature:dunkirk_1940_p2-front-0：「perimeter from Dunkirk through Bergues to Warhem」（ch. XIII, p. 211；原 149 字）
- feature:dunkirk_1940_p3-front-0：「II Corps for the eastern half from the frontier to the sea at Nieuport.」（ch. XV, p. 225；原 120 字）
- feature:dunkirk_1940_p4-front-0：「their forces joining up with the British on the Bergues Canal」（ch. XVI, p. 239；原 109 字）
- feature:dunkirk_1940_p4-front-1：「which is called above the intermediate line.」（ch. XVI, p. 239；原 177 字）
- feature:dunkirk_1940_p1-arrow-0：「There they sought to break through to the Poperinghe–Kemmel line」（ch. XII, p. 187；原 124 字）
- feature:dunkirk_1940_p1-arrow-1：「three enemy divisions—the northern claw of the German pincer movement」（ch. XII, p. 194；原 104 字）
- feature:dunkirk_1940_p1-site-3：「held out in a 'keep' in the centre of the town, isolated and surrounded」（ch. XII, p. 188；原 98 字）
- feature:dunkirk_1940_p2-site-1：「the enemy was across their line of march」（ch. XIV, p. 215；原 82 字）
- deferred:dunkirk_1940_p5-site-0：「the remaining French troops surrendered at nine o'clock that morning」（ch. XVI, p. 246；原 82 字）
- deferred:totals：「When the operation ended 338,226 had been evacuated」（ch. XVI, p. 247；原 111 字）

## 來源與註記

- `src-ellis`（official_history，A）：L. F. Ellis, The War in France and Flanders 1939–1940 (History of the Second World War, UK Military Series, ed. J. R. M. Butler)；publisher＝HMSO。
  - 出版年分歧：1953 vs 1954——前端 JSON 作 1953（初版）；HyperWar 封面頁作 LONDON 1954。依考證輸入：出版年待核對，未決前不填。
- `src-ramsay`（official_record，A）：Vice-Admiral Sir Bertram H. Ramsay, 'The Evacuation of the Allied Armies from Dunkirk and Neighbouring Beaches' (despatch dated 18 June 1940), Supplement to The London Gazette no. 38017, 17 July 1947；publisher＝The London Gazette。
- 撤出人數 338,226：英方數字（英國官方戰史 Ellis 所載；非各方共同統計）；battle_figures 屬 C3；metric 值域目前沒有 evacuated，C3 時再議，不在 C1 入庫。
- 部隊番號（箭頭文字，保留在 props，verification＝pending，未建 battle_units）：德軍 A 集團軍群 Kleist 裝甲集群；德軍 B 集團軍群第6軍團（三個師）；德軍 Hoth 集群；德軍（比軍投降後沿海岸推進之部隊，番號待查）；德軍（番號待查）

## 缺口（→ C3 event_gaps）

- `field:name`（not_found）：'Battle of Dunkirk' 名稱的 A／B 出處
- `regime:deutsches-reich objective`（partial）：德方目標只有 Ellis 英譯引述德方日誌；德國官方戰史（Das Deutsche Reich und der Zweite Weltkrieg Bd. 2）未取得
- `phase:6 map`（not_found）：6/2–6/4 戰線圖；USMA 4 June 圖待核對
- `field:end time`（note）：6/4 法軍 09:00 投降與 14:23 海軍部結束訊號；精度取 day
- `source:ramsay narrative`（not_fetched）：Ramsay 報告逐日敘述（p. 3296 起）與 Appendix 未逐頁取用
- `source:B 級`（blocked）：Britannica 'Dunkirk evacuation' 403／逾時，未繞過；本案 A 級已滿足門檻，B 級僅備援
- `source:ellis edition`（conflict）：出版年 1953 vs HyperWar 封面 1954
- `phase:3 map`（not_found）：前端舊圖形沒有對應 5/29–5/30 的要素；Ellis 29 May situation map 已列，待依圖重畫
- `feature:dunkirk_1940_p4-site-0`（not_found）：Bergues：無出處，德軍完全佔領日期待查證
- `feature:dunkirk_1940_p5-site-1`（not_found）：Malo-les-Bains：無出處，日期待查證
- `unit:arrows`（not_found）：箭頭部隊番號未逐字對照出處
- `subevent:operation-dynamo event_kind`（note）：event_kind 值域無 operation，待決

## 入庫前還差什麼（blocking）

1. Tai 核准寫庫與 verified 判定（本 seed 全部 pending）。
2. `objective_kind`（NOT NULL）：候選 place，需人確認。
3. 子事件「發電機行動」的 event_kind：值域沒有 operation，需決定（或擴值域）。
4. 戰役名稱的 A／B 出處（Ellis、Ramsay 均未用 “Battle of Dunkirk”）。
5. 參戰 regime 是否已在開發庫（united-kingdom、french-third-republic、kingdom-of-belgium、deutsches-reich）與比利時 until 的寫法（event_participants 無期間欄，需決定）。
6. 圖形：derived 幾何需依 Ellis situation map 重畫才能 verified；P3、P6 無圖形；Bergues、Malo-les-Bains 無出處；部隊番號待查證。
7. Ellis 出版年 1953／1954 分歧待核對；theater_area 待依出處圖重畫。
