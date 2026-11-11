# 邱吉爾補建：寫入計畫（**未執行**）

> 狀態：待寫（**已核准、尚未寫庫**）。Tai 2026-11-11 09:30（Asia/Taipei）決定照 gap-830 流程補建；**已決：Tai 2026-11-11 10:13**（經 World Line 主管轉達）「邱吉爾 6 項全照史料考證建議；同意修 2 處瑕疵、寫送出腳本、檢查、試跑、備份後寫入本機開發庫 5052，不 push」。
> 第一階段（已完成）：修 2 處瑕疵、寫 `send.py`／`counts.sql`，`send.py` 只乾跑過一次；5442 只做過 `default_transaction_read_only=on` 的 SELECT。試跑與寫入是第二階段。
> 待寫內容：`pending-write.json`（由 `build.py` 產生，不手改）。

## 1. 寫入目標與前提（2026-11-11 唯讀查得）

- 資料庫：5442 `worldline_borders_dev`，經 5052 API；**不碰 5051／5432**。
- 政權：`regimes.slug = united-kingdom`，id `01a18e71-cba5-7726-90e3-9b90ab344afd`（`regime_names`：United Kingdom of Great Britain and Northern Ireland；`sovereignty_records` `[1922-12-05,1987-05-15)`）。1940 年屬此政權；另一個 `united-kingdom-of-great-britain-and-ireland`（`01a192dc-749e-…`）只到 1922，不用。
- 現有相鄰任期（有效、verified）：張伯倫 `01a19eb7-b33e-…` `[1937-05-28,1940-05-10)`、艾德禮 `01a19ec8-76ff-…` `[1945-07-26,1951-10-26)`。新任期 `[1940-05-10,1945-07-26)` 剛好接上，不重疊、不留空。
- 1940–45 英國首相：**沒有任何有效紀錄**；只有已撤回的 `01a19efa-769a-7615-9705-89c66d803905`（出處 Britannica）。
- 邱吉爾生平：只有 3 筆已撤回測試 bio（`01a19efa-758c-…`、`01a19ef6-b466-…`、`01a19ef9-1c0b-…`，`is_test=true`）。**這 4 筆都不動、不刪、不撤回重寫**（新建全新 bio，不走 `/revisions`）。

## 2. 會寫哪些表、幾筆

| 步驟 | 方式 | 表 | 筆數 | 說明 |
|---|---|---|---|---|
| 1 | `POST /sources` | `sources` | ≤ 3 | GOV.UK、Historic Hansard、Nobel；同網址已存在就沿用（2026-11-11 查：三個網址目前都不在 `sources`） |
| 2 | `POST /leader-bios` | `leader_bios` | 1 | `isTest=false`；生卒（day）、出生地、黨派、簡介 |
| 2 | （同上，內含 `citations`） | `leader_bio_field_citations` | 11 | name 1、birthDate 1、deathDate 3、birthPlace 1、party 2、summary 3 |
| 3 | `POST /leader-records` | `leader_records` | 1 | regime `united-kingdom`、`head_of_government`、`Prime Minister`（已決 ②）、`[1940-05-10,1945-07-26)`（只建一筆，已決 ①）、`verified=true`、`personId`＝步驟 2 新 id |
| 4a | SQL `UPDATE`（單一交易） | `leader_bio_field_citations` | 11 | 補 `quote`、`quote_lang`、`grade`、`date_precision`、`policy_version`（API 建立時不收這些欄位）；只動步驟 2 剛建的 11 列 |
| 4b | SQL `INSERT`（同一交易） | `leader_record_citations` | 2 | Hansard（A，day）、GOV.UK（A，year） |

合計 INSERT：sources ≤3、leader_bios 1、leader_bio_field_citations 11、leader_records 1、leader_record_citations 2；UPDATE 11（只限新列）。不 DELETE。

不寫：`leader_bio_gaps`（本次無衝突）、`death_place`（已決 ④：只記 research.json `unverified`，不另寫 SQL）、照片與 `wikidata_qid`（已決 ⑥：null）、B3 段落／職位（`b3-sample` 的邱吉爾段落在 B3 建表前仍只留 seed；已決 ⑤：寫庫後另開 commit 補 `b3-sample` 的 `bioId`／`relatedRecordIds`）。

### 已決事項（Tai 2026-11-11 10:13）

| # | 項目 | 已決 |
|---|---|---|
| ① | 任期拆筆 | 只建一筆 `[1940-05-10,1945-07-26)`，不拆 1945-05-23 看守內閣；拆點記待查證（research.json `unverified`） |
| ② | 職銜 | `Prime Minister`（照 Hansard） |
| ③ | 黨派 | Conservative；evidenceNote 註明只代表首相任內黨籍 |
| ④ | 卒地 | 這次不寫，記 research.json `unverified`；不寫任何 `death_place` SQL |
| ⑤ | b3-sample | 寫庫後另開 commit 補邱吉爾 `bioId`／`relatedRecordIds`；寫入第一、二階段都不改 b3-sample |
| ⑥ | nameZh 等 | nameZh 無出處保留；wikidataQid 與照片 null |

## 3. 執行前要做的事

1. ~~Tai 核准本計畫~~ → **已決：Tai 2026-11-11 10:13**。
2. ~~寫送出腳本~~ → **已完成**：本目錄 `send.py`（比照 `gap-830/send_batch.py`、`b2_backfill.py`）。
   - `--base`、`--db` 必填無預設；只接受 127.0.0.1／localhost；拒絕 5051；port↔db 必須配對（5052↔`worldline_borders_dev`、5062↔`worldline_person_dryrun`）；容器固定 `worldline-borders-dev-db`（5442）。
   - 預設乾跑（`--dry-run` 同義）：只印計畫與唯讀核對（regime、期間內無有效首相、張伯倫／艾德禮相接、三個 source 網址、邱吉爾無有效 bio、4 筆撤回列不變）；`--send` 才寫。
   - 步驟 1→2→3 走 API，回傳 id 代入 `<step1:…>`、`<step2:bioId>`、`<step3:recordId>`；步驟 4 單一交易，11 個 UPDATE 逐列以 citation id＋bio id 指定（每列核對 1 筆、合計 11），INSERT `leader_record_citations` 2 筆（核對 2）；任一不符即 RAISE，整筆回復。
   - 冪等：帳本 `sent.<port>.json`；sources 先查網址、bio／record 先查帳本與庫；步驟 4 若 11 列 quote 已填且 2 筆 record citations 已存在就跳過，部分完成則停止待人工檢查。
   - 失敗即停、印出已寫入的 id（軟撤回見 §5）、exit 2。全檔無刪除／DDL 語句；API key 只放 header。
3. `python3 -I build.py` 重跑 → **ok**（13 筆引文，name 引文與 Hansard `<h1>` 逐字相符）。
4. 寫入後核對：`counts.sql`（5 條計數＋撤回列不變；全 SELECT；可帶 `-v bio=… -v rec=…`）。

## 4. Dry-run

1. 乾跑：`python3 send.py --base http://127.0.0.1:5052/api/v1 --db worldline_borders_dev`（不帶 `--send`）。**2026-11-11 第一階段已跑一次**：regime ✓、三個 source 都不存在（將新建 3）、無有效邱吉爾 bio、期間內有效首相 0、張伯倫／艾德禮相接 ✓、撤回列 3/3＋1/1。
2. 試跑庫（第二階段）：比照 gap-830 每批流程用 `gap-830/trial_env.sh` 從 5442 的 `pg_dump` 還原到 `worldline_person_dryrun`，`python3 send.py --base http://127.0.0.1:5062/api/v1 --db worldline_person_dryrun --send`（試跑庫每次重建，先移除舊的 `sent.5062.json`）；以 `counts.sql` 核對（預期 3、1、11|11、1、2、3|1）。原計數草稿：
   ```sql
   select count(*) from leader_bios where name='Winston Churchill' and retracted_at is null;            -- 1
   select count(*) from leader_records r join regimes g on g.id=r.regime_id
    where g.slug='united-kingdom' and r.retracted_at is null
      and r.valid_period && daterange('1940-05-10','1945-07-26');                                       -- 1
   select count(*) from leader_bio_field_citations where bio_id=:bio and quote is not null;             -- 11
   select count(*) from leader_record_citations where record_id=:rec;                                  -- 2
   select count(*) from leader_bios where id in ('01a19efa-758c-718a-b1ec-27916469f239',
     '01a19ef6-b466-7e2e-94e1-8ec3c0e5ac10','01a19ef9-1c0b-781a-911b-adc230abbeaf') and retracted_at is not null;  -- 3（不變）
   ```
3. 試跑通過後，比照 `run_batch.sh`：先 `pg_dump -Fc` 備份 5442，再對 5052 送一次（只跑一次）。

## 5. 回滾

- 依憲法 I5，事實表不可 DELETE（觸發器擋）。回滾＝**軟撤回**：
  - `leader_records`：撤回新任期（`retracted_at`＋`retraction_reason`，比照 `retract_leaders.py`）；
  - `leader_bios`：撤回新 bio（比照 `retract_test_bios_2.py`）；
  - `leader_bio_field_citations`：`POST /leader-bio-field-citations/{id}/retraction`；
  - `leader_record_citations`：SQL 設 `retracted_at`、`retraction_reason`。
- 步驟 4 交易失敗會自動 `ROLLBACK`，步驟 1–3 已寫入的列再以上面方式撤回。`sources` 列保留（可被其他資料共用）。
- 最後手段：用步驟 4.3 前的 `pg_dump` 備份還原（需 Tai 同意）。
