---
plan_id: world-line-ww2
status: active
owner: jack755051@gmail.com
last_updated: 2026-10-28
related_constitution: .claude/constitutions/world-line.md
related_prds: [".claude/prds/world-line-ww2.md"]
---

# World Line 二戰第一階段——執行計畫

> 核取方塊是進度的唯一來源。規格以 PRD 為準，本檔只排順序、定驗收。M1 之後的里程碑先列到 PRD §10 的粒度，輪到時再拆細。

## A. 開工前（文件與設計）

| 狀態 | # | 任務 | 產出 | 驗收 |
|---|---|---|---|---|
| [x] | A1 | 二戰史料來源調查 | `docs/research/ww2-data-sources.md` | — |
| [x] | A2 | 憲法依重建與調查更新 | 憲法 R9、§4 政體更替等 | — |
| [x] | A3 | 重寫二戰 PRD | `.claude/prds/world-line-ww2.md` | §12 擋開工的 6 題已拍板 |
| [ ] | A4 | 使用者審查憲法 → `active` | 憲法 status | 使用者確認 |
| [x] | A5 | 風格訪談（2026-10-28）：地圖集／檔案館、標題襯線＋內文無襯線、朱紅強調色、紙色陸地＋灰藍海、陣營四色系、資料缺／推定樣式交 M1 實測、≥1024px、時間軸起點依資料 | 拍板紀錄寫進 DESIGN.md、憲法 §6「陣營」、PRD Q11／Q14／Q15 | 使用者確認 |
| [x] | A6 | 寫 `design/stitch/DESIGN.md`（自有風格，不沿用 sanring 色票）＋地圖樣式節：控制類型五類、斜線網底、推估過渡、控制資料缺、依主權推定、戰線、快照標記 | DESIGN.md | Material 每個 role 都填滿；地圖樣式涵蓋 PRD §8.2／§8.4 所有圖例項；四色系（軸心／同盟／共同交戰／中立）各自有足夠多可區分的色階；資料缺與依主權推定各寫兩種候選樣式，M1 實測後定 |
| [x] | A7 | 寫 `docs/ww2-stitch.md`：PRD §8 每個畫面一段英文 prompt | prompt 文件 | 每個畫面對到 §8 小節、四態、R# |
| [ ] | A8 | 使用者在 Stitch 出稿 | html／png | — |
| [ ] | A9 | 收稿：放進 `design/stitch/<id>-<slug>/`，寫 README 畫面清單與「稿與規格不一致處」 | `design/stitch/README.md` | 每張稿都列出 |

A6 起與 M0 後端部分可並行；M0 前端畫面等 A9 完成。

## B. 資料試做（使用者手做，與 A 並行）

| 狀態 | # | 任務 | 驗收 |
|---|---|---|---|
| [ ] | B1 | 下載並本地保存 West Point 圖檔（官方頁已 404，S3 可能下線）——存放位置見 PRD §12 TODO | 檔案在本機 |
| [ ] | B2 | QGIS 數位化 1940-07 法國（調查報告 §4 來源） | 德佔區、維琪區多邊形＋引用資訊（圖集、圖號）；記下實際工時，回填調查報告 §5.2 |
| [ ] | B3 | 拍板憲法 §10 主權資料集（PRD §12 Q0） | 擋 S 軌開工 |

## C. M0 骨架 vertical slice（PRD §10）

| 狀態 | # | 任務 | 驗收 |
|---|---|---|---|
| [ ] | C1 | 驗證版本：PostGIS image tag、NetTopologySuite、MapLibre、`@sanring/cli` 是否有 slider（PRD §12 技術 TODO） | 版本寫回 PRD §5 |
| [ ] | C2 | `compose.yaml`（PostGIS＋api＋web）＋ `.env.example` | `docker compose up` 起得來 |
| [ ] | C3 | 後端方案骨架：`src/WorldLine.Api`、`src/WorldLine.Contracts`、`tests/`、`.slnx`、`Directory.Build.props`（照 sanring-middle-platform） | `dotnet build`／`dotnet test` 通過 |
| [ ] | C4 | ADR：I5 修正保留機制（Q2）、控制資料缺表達（Q1） | `docs/adr/` 兩份 |
| [ ] | C5 | M0 最小 schema migration（PRD §10 M0 所列表） | migration 可套用 |
| [ ] | C6 | `POST /control-records`（強制 I1、I6）、`GET /control?date=`、`GET /timeline/snapshots`＋OpenAPI | integration test（Testcontainers PostGIS）驗 I6 拒絕無引用 |
| [ ] | C7 | 前端骨架：Angular 22、pnpm、Tailwind 4、sanring UI init、`--wl-*` token（取自 DESIGN.md）、`core/ layout/ pages/ shared/ components/ui` | `pnpm build`／`pnpm test` 通過 |
| [ ] | C8 | 地圖顯示一筆控制區（1940-07-15 德軍佔領區，可用 B2 成果）＋最小圖例＋單一快照標記時間軸＋來源 popover | Playwright E2E：開頁 → 看到多邊形 → 點開來源 |

## D. 之後的里程碑（輪到時再拆細）

| 狀態 | 里程碑 | 開工前要拍板 |
|---|---|---|
| [ ] | M1 法國 1940-07 試做 | Q3 插值方式（spike）、Q8 多語儲存、Q9 紀年顯示、Q12、Q13 |
| [ ] | M2 西歐 1939–40 | Q5 戰區劃分（含戰區範圍是否隨時間變）、Q6 敵對判定 |
| [ ] | M3 東線 | — |
| [ ] | M4 太平洋 | Q7 傀儡代管建模 |
| [ ] | M5 中國 | — |
| [ ] | M6 其餘戰區 | — |
| [ ] | S 軌 全球主權骨架 | B3（Q0） |

Q10（史觀主線建表）在 M1 前決定。
