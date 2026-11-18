# 邱吉爾補建：寫入結果（第二階段，已寫入本機開發庫 5052）

## 授權

Tai 本人 2026-11-11 10:13（Asia/Taipei，經 World Line 主管轉達）原話：
「邱吉爾 6 項全照史料考證建議；同意修 2 處瑕疵、寫送出腳本、檢查、試跑、備份後寫入本機開發庫 5052，不 push」。
第一階段（修瑕疵、send.py、counts.sql）見 commit `9820a4d`。

## 版本

- `send.py`：commit `9820a4d`，未修改（sha256 `65530d5f987fe8a7c42f82a91a7ddfc988d1dee214029135828ffdabef35d4b9`）。
- `pending-write.json`／`build.py`／`verify-report.json`：同 `9820a4d`，未修改。
- 試跑沒有發生任何問題，**未進入 E（修 send.py）**，0 輪修正。

## 時間軸（2026-11-11，Asia/Taipei）

| 時間 | 步驟 | 結果 |
|---|---|---|
| 10:25:57 | A 寫入前狀態（worldline_borders_dev，唯讀） | counts 與 Q 如下（DEV_BEFORE），符合預期 |
| 10:26:01–10:26:28 | B 備份（pg_dump -Fc） | 成功，`pg_restore -l` 可讀（TOC 286） |
| 10:26:35–10:26:50 | C `trial_env.sh up <備份>` | 5062 healthz 200，API PID 85317；事前 5062 無人聽、無舊 `sent.5062.json` |
| 10:26:5x | D TRIAL_BEFORE＋乾跑 | 與 DEV_BEFORE 完全相同；乾跑核對全過 |
| 10:27:02–10:27:06 | D 試跑 `--send`（5062） | 步驟 1–4 全成功（`CHURCHILL STEP4 OK: update 11, insert 2`） |
| 10:27:25 | D 冪等重跑 `--send`（5062） | 全部「沿用／已完成／略過」；帳本、Q、counts 完全不變 |
| 10:27:33 | F 停 5062 | `kill 85317`，5062 不再聽；`worldline_person_dryrun` **保留**（未 dropdb、未執行 `trial_env.sh down`） |
| 10:27:37 | G 寫入前再查＋乾跑（5052） | Q 與 DEV_BEFORE 相同（期間無其他寫入，不需再備份）；乾跑核對全過 |
| 10:27:43–10:27:47 | G 寫入 `--send`（5052，**只跑一次**） | 步驟 1–4 全成功 |
| 10:27:55 | H 寫入後核對＋乾跑確認狀態 | counts、Q 增量與試跑相同；乾跑顯示 4 步皆「已完成」 |

## 備份

- 路徑：`~/wl-backups/worldline_borders_dev-20261111-102601-pre-churchill-write.dump`
- 大小：107,384,664 bytes（上一份 `…-20261110-224041-pre-requote80-quote-write.dump` 107,360,382 bytes，差 +24,282）
- `pg_restore -l`：可讀，Archive created at 2026-11-11 02:26:02 UTC，dbname worldline_borders_dev，TOC Entries 286，PostgreSQL 18.6。
- G 時 Q 未變，沿用此備份，未再備份。

## 全庫快照 Q

Q＝`leader_bios 有效/總`、`leader_bio_field_citations`、`leader_records 有效`、`leader_record_citations`、`sources`

| | bios | bio cits | records 有效 | record cits | sources |
|---|---|---|---|---|---|
| DEV_BEFORE（10:25:57） | 923/968 | 4319 | 2035 | 0 | 1206 |
| TRIAL_BEFORE | 923/968 | 4319 | 2035 | 0 | 1206 |
| TRIAL_AFTER（試跑後） | 924/969 | 4330 | 2036 | 2 | 1209 |
| TRIAL 冪等重跑後 | 924/969 | 4330 | 2036 | 2 | 1209 |
| DEV 寫入前再查（10:27:37） | 923/968 | 4319 | 2035 | 0 | 1206 |
| DEV_AFTER（10:27:55） | 924/969 | 4330 | 2036 | 2 | 1209 |
| 增量（試跑＝寫入） | +1/+1 | +11 | +1 | +2 | +3 |

## counts.sql

| 項目 | 預期前 | DEV_BEFORE | TRIAL_BEFORE | 預期後 | TRIAL_AFTER | 冪等重跑後 | DEV_AFTER |
|---|---|---|---|---|---|---|---|
| ① sources | 0 | 0 | 0 | 3 | 3 | 3 | 3 |
| ② bio_live | 0 | 0 | 0 | 1 | 1 | 1 | 1 |
| ③ bio_citations total\|quoted | 0\|0 | 0\|0 | 0\|0 | 11\|11 | 11\|11 | 11\|11 | 11\|11 |
| ④ uk_hog_1940_45 | 0 | 0 | 0 | 1 | 1 | 1 | 1 |
| ⑤ record_citations | 0 | 0 | 0 | 2 | 2 | 2 | 2 |
| 附 retracted_unchanged | 3\|1 | 3\|1 | 3\|1 | 3\|1 | 3\|1 | 3\|1 | 3\|1 |

寫入後 counts.sql 帶 `-v bio=<新 bio id> -v rec=<新 record id>` 執行。

## 其他唯讀核對（試跑庫與開發庫結果相同）

- 新 bio 的 11 列 `leader_bio_field_citations`：quote 全部非空，NFC 後最長 62 字（≤80）。
- 新 record 的 2 列 `leader_record_citations`：quote 全部非空，NFC 後最長 28 字。
- 新 record：`valid_period=[1940-05-10,1945-07-26)`、`person_id`＝新 bio、`verified=true`、`title=Prime Minister`、`role=head_of_government`。
- 相接：張伯倫 `01a19eb7-b33e-788a-be1e-de6d70bbcaae` `[1937-05-28,1940-05-10)` 止日＝新任期起日；艾德禮 `01a19ec8-76ff-77a1-a64f-ee3cebf08f7d` `[1945-07-26,1951-10-26)` 起日＝新任期止日。
- 3 個新 source 的 `note` 欄有寫入（POST /sources 接受 note 欄位）。
- 3 筆撤回測試 bio 與撤回任期 `01a19efa-769a-7615-9705-89c66d803905` 仍為撤回，未動。

## 開發庫 worldline_borders_dev（5052）新 id

| 類別 | id |
|---|---|
| source govuk-churchill | `01a1c86e-c80f-7ba2-9763-20f1ab2ab2f0` |
| source hansard-churchill | `01a1c86e-c889-754b-990e-d02043f0d1b4` |
| source nobel-churchill | `01a1c86e-c88d-72b2-b670-b22c64855a49` |
| leader_bios（Winston Churchill） | `01a1c86e-c89b-70af-afe0-1ad0f4be2bf8` |
| leader_records（1940–45 首相） | `01a1c86e-c9a8-774a-92a1-bcf284ffe54d` |
| leader_record_citations | `f7377eba-952b-4438-a6ad-ce243cfaae2f`、`023bc45b-e97e-407e-b835-ab650dac16d0` |

leader_bio_field_citations（11）：
`01a1c86e-c8a9-74eb-95a4-8485972d84ac`、`01a1c86e-c8a9-7bd0-82ac-9436d0b4b8d8`、`01a1c86e-c8aa-7aa9-a601-a5054394e645`、
`01a1c86e-c8aa-76b0-8119-80b02670ee10`、`01a1c86e-c8aa-7f58-a0e1-437020d81cf2`、`01a1c86e-c8aa-7a0a-ac19-e6d382353675`、
`01a1c86e-c8ab-789f-aebd-3eb6983e5e78`、`01a1c86e-c8ab-7424-83b4-e1e4f2b89614`、`01a1c86e-c8ab-7157-b90e-7f8fda4ae2be`、
`01a1c86e-c8ab-77a8-9dd6-1627d16f5d9c`、`01a1c86e-c8ab-79e3-90a3-41fb5033b6b7`

帳本：`sent.5052.json`（開發庫）、`sent.5062.json`（試跑庫，id 只在 `worldline_person_dryrun` 有效）。

## 偏差與備註

- 無功能偏差：試跑一次通過，未修 send.py、未重還原；5052 `--send` 只跑一次，之後只乾跑確認狀態。
- 冪等重跑前把 `sent.5062.json` 複製到 `/tmp/wlq/churchill-sent5062-before-rerun.json` 供 diff 比對（結果相同），未納入 repo。
- `leader_record_citations` 的 id 是 UUIDv4（表預設值產生，INSERT 未指定 id），其他新列為 API 產生的 UUIDv7；屬既有 schema 行為，未處理。
- `worldline_person_dryrun` 保留（含試跑寫入的邱吉爾資料），5062 臨時 API 已停。
- 未寫 death_place、leader_bio_gaps、照片、wikidata_qid；未改 b3-sample（已決 ⑤：另開 commit 補 bioId／relatedRecordIds）。
- 未 push。
