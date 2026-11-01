# 開發庫控制層 fixture（1940 法國，西歐戰區）

> 只寫開發庫 `worldline_borders_dev`（API 5052）。**不寫 appdb_ww2／5051。**

## 為什麼

`frontend/e2e/atlas.e2e.ts` 的 M0、快照、資料缺、陣營圖例等測試需要控制層資料（戰區、快照、控制紀錄、涵蓋備註、陣營切片）。
這些資料原本只在正式庫；borders 開發庫只有主權層，所以這幾個測試在 borders 設定下一直失敗。

## 內容（全部是既有 seed 請求檔的 symlink，內容不改）

| 來源批次 | 送出的請求 |
|---|---|
| `ww2/france-1940-07-15` | 8 個來源、西歐戰區、快照 1940-07-15／08-15、控制紀錄 CR_MAIN、CR_NORD、CR_AM_MIL、CR_AM_CDZ |
| `ww2/fr-uk-1940` | 來源 JO 1940-07-11、DGFP D9、FRUS 1942 I；維琪自由區；陣營 法蘭西國＝共同交戰、英國＝同盟（1942）；阿爾卑斯五省資料缺 |
| `ww2/alignments` | 來源 NCA V、FRUS Japan II、DGFP D6（GPO 版）；德國軸心兩段（鋼鐵條約 GPO 版、三國同盟） |

不送：
- 政權（五個 slug 已在開發庫，`build.sh` 以 slug 查 id 預填）。
- 東北禁區兩筆（`requiresDecision`，正式庫也未送）。
- 已撤回的 AL_DE_AXIS_1939 與它的 HMSO 版來源（直接送取代後的 GPO 版）。
- `fr-uk-1940` 的三個事件（宣戰、承認自由法國）：開發庫的事件另有來源，避免重複。

## 用法

```
data/seed/dev-fixtures/control-1940/build.sh
python3 data/seed/ww2/borders-asia-3/tools/send_seed2.py --dir tmp/fixture-control-1940/requests/F1 \
  --base http://127.0.0.1:5052 --env .env.borders-dev --ids .dev/sent-ids.fixture-control-1940-dev.json      # dry-run
# 先 pg_dump 開發庫，再加 --send
```
