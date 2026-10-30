# 陣營歸屬（regime_alignments）第一批

> **狀態：已寫入 appdb_ww2**（2026-10-30 AL_DE_AXIS、AL_DE_AXIS_1939；2026-10-31 改指向 GPO 版，見「寫入紀錄」）。
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
| ~~AL_DE_AXIS_1939~~（2026-10-31 撤回） | 德意志國（Deutsches Reich） | axis | 1939-05-22 – 1940-09-27 | DGFP Series D vol. VI（英國 HMSO 版，pd_expired）, Doc. No. 426, pp. 561–563 | NCA Vol. V, Doc. 2818-PS, p. 453 |
| AL_DE_AXIS_1939_GPO | 德意志國（Deutsches Reich） | axis | 1939-05-22 – 1940-09-27（最後一天 09-26） | DGFP Series D vol. VI（美國國務院／GPO 版，us_federal_pd）, Doc. No. 426 | NCA Vol. V, Doc. 2818-PS, p. 453 |
| AL_DE_AXIS | 德意志國（Deutsches Reich） | axis | 1940-09-27 – （未定） | NCA Vol. V, Doc. 2643-PS, pp. 355–356 | FRUS Japan 1931–41 v. II, Doc. 100, pp. 165–166 |

- 起日 1939-05-22：德義《友好同盟條約》（鋼鐵條約）在柏林簽署，第 VII 條「簽署即生效」（Tai 2026-10-30 拍板以此為三國同盟條約前的依據）。
- 1940-09-27：三國同盟條約在柏林簽署，第 6 條「簽署即生效」。
- 兩段分開記錄、各自附依據；半開區間相接，不重疊，也不必撤回已寫入的 AL_DE_AXIS。
- 迄日留空：德國退出軸心或政權終止的日期涉及爭議（憲法 §4：1945 年是終止還是國家延續，記為爭議點，不裁定），不推測。

## 來源與授權

| 來源 | 種類 | 授權 | 核對 |
|---|---|---|---|
| *Nazi Conspiracy and Aggression*, Vol. V（US GPO 1946） | trial_record | us_federal_pd（17 U.S.C. §105；IA 標 Public Domain Mark 1.0） | 2026-10-30 在 archive.org 全文核對 2643-PS 在 p. 355 起 |
| *FRUS, Japan 1931–1941*, Vol. II（US GPO 1943） | official_record | us_federal_pd（17 U.S.C. §105；國務院著作權聲明） | 2026-10-30 在 history.state.gov 核對 Doc. 100、p. 166 分頁 |
| *DGFP* Series D vol. VI（HMSO 1956，SRC_DGFP_D6） | official_record | pd_expired（英國皇家著作權 50 年已屆滿） | 2026-10-30 在 archive.org 全文核對 Doc. No. 426 在 pp. 561–563。已寫入，不再被有效切片引用（來源表沒有撤回欄位，列保留） |
| *DGFP* Series D vol. VI（U.S. Department of State／GPO 1956，SRC_DGFP_D6_GPO） | official_record | us_federal_pd（17 U.S.C. §105；HathiTrust 標 pdus） | ⚠ 美國版原書未親眼核對：HathiTrust 對自動化連線一律 403、archive.org 的 GPO 版是借閱限定。引用以文件號 Doc. No. 426 為準（兩版文件編號相同）；英國版頁碼 pp. 561–563 寫在 locator 備註，美國版頁碼未比對 |

只引用日期與事實，不轉載條文全文。

## 沒有寫的

- 其他政權（義大利、日本、維琪法國等）：目前 DB 沒有這些政權，依指示不建。
- 1939-05-22 以前（例：1936 年羅馬－柏林軸心議定書、反共產國際協定）：沒有拍板，也還沒查出處，不寫。

## 寫入紀錄

- 2026-10-30：AL_DE_AXIS 與兩個來源已寫入 appdb_ww2（Tai 同意）。
- AL_DE_AXIS_1939 與 SRC_DGFP_D6 依 Tai 2026-10-30 拍板新增。
- 2026-10-31（Tai 同意直接改 appdb_ww2）：主要引用改指向美國政府印刷局版。已寫入的資料不可覆蓋（I5），所以走「撤回＋新增」：
  1. `03`：新增來源 SRC_DGFP_D6_GPO（us_federal_pd）。
  2. `04`：`POST /regimes/{id}/alignments/{alignmentId}/retraction` 撤回 AL_DE_AXIS_1939（寫 retracted_at＋原因，列保留）。
  3. `05`：新增 AL_DE_AXIS_1939_GPO（同陣營、同期間，primary 改為 GPO 版）。
  寫入前先 pg_dump 備份，並先在由備份還原的暫時資料庫演練。

## 檔案

- `requests/`：依檔名順序送出。
- `send_seed.py`：送出工具（dry-run 預設；成功一筆就寫入 `sent-ids.json`，補寫時跳過已送的）。
- 測試 `SeedAlignmentsTests` 在 Testcontainers 重播（先建德國，再送本批），確認 API 接受，且 `/control` 的 `controllerAlignment` 依日期出現或為 null。
