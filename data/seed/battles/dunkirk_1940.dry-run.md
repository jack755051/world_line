# 戰役 seed dry-run 報表：dunkirk_1940

- 來源：`frontend/public/campaigns/dunkirk_1940.json`（wl-campaign-web/0.1，sha256 `072f237476e8fb30…`）
- 產生：`tools/battles/import_campaign_seed.py`（不連資料庫；本報表不含時間戳，重跑應逐位元相同）
- 全部 status＝pending。TODO(考證)：試做範圍＝發電機行動（1940-05-26～06-04）。憲法 §6 三條件（交戰方、目標、起訖與地區）是否成立由史料考證 bot 查證中；若不成立，改以敦克爾克戰役為 battle、發電機行動為其階段或子事件（§19.5 C1）。結論出來前 status 一律 pending。
- 等級：JSON 只有 `type`，`grade` 一律 null；`grade_hint` 依 §19.4.2（official_history→A）推出，**未經考證確認，不算已有 A／B citation**。

## 摘要

| 項目 | 數量 |
|---|---|
| 階段 | 5 |
| 圖形 front | 5 |
| 圖形 arrow | 7 |
| 圖形 site | 14 |
| citation（階段＋圖形） | 40 |
| 　其中 grade 已確認 A／B | 0 |
| 　其中 grade_hint＝A（候選） | 40 |
| 　quote 超過 80 字 | 21 |
| 　缺 accessed_on | 40 |
| 座標參照（gazetteer，不算出處，放 props.geometry_refs） | 40 |
| 無任何 citation 的圖形 | 2 |
| geom_basis＝derived（不得 verified） | 21 |
| 來源（sources） | 5（publisher 全部待補） |

## 戰役主體（historical_events＋battle_profiles）

| 欄位 | 值 | citation | 狀態 |
|---|---|---|---|
| occurred | 1940-05-26～1940-06-05（半開） | **缺**（web JSON 無起訖日出處） | pending／待查證 |
| 交戰方 | deutsches-reich, french-third-republic, kingdom-of-belgium, united-kingdom | **缺** | pending／待查證（event_citations） |
| name | 敦克爾克撤退（發電機行動） / Dunkirk evacuation (Operation Dynamo) | **缺** | pending |
| objective／objective_kind | null | **缺**（JSON 無此內容） | 待查證；NOT NULL，補齊前不能寫庫 |
| control_change | null | **缺**（JSON 無此內容） | 待查證；NOT NULL，補齊前不能寫庫 |
| outcome_kind／outcome_text | null | 無 | 沒有出處就留 NULL |
| theater_area | JSON bounds 外框 | 無（derived） | 待以出處重畫 |

## 階段（battle_phases）

| seq | 名稱 | 期間（半開） | 精度 | citation | grade_hint | quote>80 | JSON 原標記 | 狀態 |
|---|---|---|---|---|---|---|---|---|
| 1 | 發電機行動啟動與走廊作戰 | 1940-05-26～1940-05-28 | day/day | 3（有） | A | 2 | dates=True, summary=True | pending |
| 2 | 比軍投降後撤入灘頭陣地 | 1940-05-28～1940-05-30 | day/day | 3（有） | A | 2 | dates=True, summary=True | pending |
| 3 | 灘頭陣地防禦 | 1940-05-30～1940-06-01 | day/day | 3（有） | A | 1 | dates=True, summary=True | pending |
| 4 | 縮小周界與英軍最後撤離 | 1940-06-01～1940-06-03 | day/day | 4（有） | A | 1 | dates=True, summary=True | pending |
| 5 | 法軍後衛與敦克爾克陷落 | 1940-06-03～1940-06-05 | day/day | 3（有） | A | 1 | dates=True, summary=True | pending |

## 圖形（battle_map_features）

| feature_key | 種類 | 配色組 | geom_basis | citation | grade_hint | JSON verified | 狀態 |
|---|---|---|---|---|---|---|---|
| dunkirk_1940_p1-front-0 | front | allied | source_text | 1（有） | A | True | pending |
| dunkirk_1940_p2-front-0 | front | allied | source_text | 1（有） | A | True | pending |
| dunkirk_1940_p3-front-0 | front | allied | source_text | 1（有） | A | True | pending |
| dunkirk_1940_p4-front-0 | front | allied | source_text | 1（有） | A | True | pending |
| dunkirk_1940_p4-front-1 | front | unknown | source_text | 1（有） | A | True | pending |
| dunkirk_1940_p1-arrow-0 | arrow | axis | derived | 1（有） | A | True | pending |
| dunkirk_1940_p1-arrow-1 | arrow | axis | derived | 1（有） | A | True | pending |
| dunkirk_1940_p1-arrow-2 | arrow | axis | derived | 1（有） | A | True | pending |
| dunkirk_1940_p2-arrow-0 | arrow | axis | derived | 1（有） | A | False | pending |
| dunkirk_1940_p3-arrow-0 | arrow | axis | derived | 1（有） | A | False | pending |
| dunkirk_1940_p3-arrow-1 | arrow | axis | derived | 1（有） | A | False | pending |
| dunkirk_1940_p4-arrow-0 | arrow | axis | derived | 1（有） | A | False | pending |
| dunkirk_1940_p1-site-0 | site | axis | derived | 1（有） | A | True | pending |
| dunkirk_1940_p1-site-1 | site | axis | derived | 1（有） | A | False | pending |
| dunkirk_1940_p1-site-2 | site | allied | derived | 1（有） | A | True | pending |
| dunkirk_1940_p1-site-3 | site | contested | derived | 1（有） | A | True | pending |
| dunkirk_1940_p2-site-0 | site | contested | derived | 1（有） | A | True | pending |
| dunkirk_1940_p2-site-1 | site | axis | derived | 1（有） | A | True | pending |
| dunkirk_1940_p2-site-2 | site | allied | derived | 1（有） | A | True | pending |
| dunkirk_1940_p3-site-0 | site | contested | derived | 1（有） | A | True | pending |
| dunkirk_1940_p3-site-1 | site | allied | derived | 1（有） | A | True | pending |
| dunkirk_1940_p3-site-2 | site | contested | derived | 1（有） | A | True | pending |
| dunkirk_1940_p4-site-0 | site | axis | derived | 0（**缺**） | — | False | pending；**缺出處** |
| dunkirk_1940_p4-site-1 | site | axis | derived | 1（有） | A | False | pending |
| dunkirk_1940_p5-site-0 | site | axis | derived | 1（有） | A | True | pending |
| dunkirk_1940_p5-site-1 | site | axis | derived | 0（**缺**） | — | False | pending；**缺出處** |

## 未入 C1 的內容

- totals（evacuated_dynamo）：1 筆 citation；battle_figures 屬 C3；metric 值域目前沒有 evacuated，C3 時再議，不在 C1 入庫。
- 階段 5 fronts_note「6月3日法軍最後防線走向於 Ellis 未見具體描述，待查證」→ C3 event_gaps（`phase:5`，not_found），不寫進 battle_phases（I6）。
- 部隊候選（箭頭文字，未建 battle_units）：德軍 A 集團軍群 Kleist 裝甲集群；德軍 B 集團軍群第6軍團（三個師）；德軍 Hoth 集群；德軍（比軍投降後沿海岸推進之部隊，番號待查）；德軍（番號待查）

## 寫庫前必補（blocking）

1. 三條件考證結論（史料考證 bot）與 event_citations。
2. objective／objective_kind／control_change（NOT NULL）與 battle_profile_citations。
3. 每筆 citation 的 accessed_on、grade（確認 A／B）；quote 超過 80 字者改短引。
4. sources.publisher。
5. 無出處圖形補出處或撤除；derived 圖形若要 verified 需改以出處重畫（source_map／source_text）。
