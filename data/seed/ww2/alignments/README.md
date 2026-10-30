# 陣營歸屬（regime_alignments）第一批

> **狀態：DRAFT — 待 Tai 檢查。尚未寫入 appdb_ww2。**
> 預設 dry-run：`python3 send_seed.py`；Tai 同意後才 `--send`（API 預設 `http://127.0.0.1:5051`）。
> 前置 id `REGIME_DE` 從 `../france-1940-07-15/sent-ids.json` 讀取。

## 依據

- 憲法 §6「陣營」（2026-10-28 拍板）：陣營分軸心、同盟、共同交戰／合作、中立／未結盟四類；軸心與同盟只依**有文件的正式加入**（例：三國同盟條約簽署日）判定；每段歸類都須附來源；不由系統依交戰關係推導。
- 憲法 R8：觀點須有合格史料；R7：來源要有明確出版者，不收「自製」。
- 使用者 2026-10-29：史實資料必須有使用權、經得起查證（feature/literature-perspective 的 R11 草案）。
- PRD §6.3 `regime_alignments`：`valid_period` 起點＝條約簽署／參戰日。

## 範圍

只為 appdb_ww2 **目前已有**的政權建切片。目前 DB 只有一個政權：`deutsches-reich`（REGIME_DE）。

| 紀錄 | 政權 | 陣營 | 有效期間 [start, end) | primary 引用 | date_check |
|---|---|---|---|---|---|
| AL_DE_AXIS | 德意志國（Deutsches Reich） | axis | 1940-09-27 – （未定） | NCA Vol. V, Doc. 2643-PS, pp. 355–356 | FRUS Japan 1931–41 v. II, Doc. 100, pp. 165–166 |

- 起日 1940-09-27：三國同盟條約在柏林簽署，第 6 條「簽署即生效」。
- 迄日留空：德國退出軸心或政權終止的日期涉及爭議（憲法 §4：1945 年是終止還是國家延續，記為爭議點，不裁定），不推測。

## 來源與授權

| 來源 | 種類 | 授權 | 核對 |
|---|---|---|---|
| *Nazi Conspiracy and Aggression*, Vol. V（US GPO 1946） | trial_record | us_federal_pd（17 U.S.C. §105；IA 標 Public Domain Mark 1.0） | 2026-10-30 在 archive.org 全文核對 2643-PS 在 p. 355 起 |
| *FRUS, Japan 1931–1941*, Vol. II（US GPO 1943） | official_record | us_federal_pd（17 U.S.C. §105；國務院著作權聲明） | 2026-10-30 在 history.state.gov 核對 Doc. 100、p. 166 分頁 |

只引用日期與事實，不轉載條文全文。

## 沒有寫的（查不到可靠出處，或需要 Tai 決定）

- **德國 1940-09-27 以前**：1940-07-15、08-15 兩個法國快照的日期早於三國同盟條約，所以地圖上德國在這兩天仍顯示「陣營未建置」。
  可能的依據是 1939-05-22 德義《友好同盟條約》（鋼鐵條約），但憲法 §6 只舉三國同盟條約為例，要不要把鋼鐵條約當作「正式加入軸心」需 Tai 拍板。
  另外，NCA Vol. V Doc. 2818-PS（p. 453 起）只收秘密附加議定書，條約本文的公有領域出處還要再找（候選：DGFP Series D Vol. VI No. 426），找到之前不寫。
- 其他政權（義大利、日本、維琪法國等）：目前 DB 沒有這些政權，依指示不建。

## 檔案

- `requests/`：依檔名順序送出。
- `send_seed.py`：送出工具（dry-run 預設；成功一筆就寫入 `sent-ids.json`，補寫時跳過已送的）。
- 測試 `SeedAlignmentsTests` 在 Testcontainers 重播（先建德國，再送本批），確認 API 接受，且 `/control` 的 `controllerAlignment` 依日期出現或為 null。
