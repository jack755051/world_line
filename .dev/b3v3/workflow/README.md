# B3 v3 省 token 工作流

研究仍在本機用 Claude Code 跑（這個目錄裡的 dynamic workflow）。原文繼續放在倉庫外面的 `/Users/jack755051/wl-source-cache/b3full-v3/batchNNN/raw/`。不寫資料庫、不呼叫 5052 API。

和上一輪（chunk 003–032，約 1.9 億 token，其中約 95% 是 cache read）的差別：

- 網頁與 PDF 由 `tools/b3v3/fetch_source.py` 抓下來（curl、不加 `-k`、UA `Mozilla/5.0`）。工具只印短摘要和命中關鍵字的段落，有字數上限。已有的 sourceKey 不會重抓。
- 抄引文用同程式的 `lookup`，只印片段和 offset。禁止 Read／cat 整份 raw。WebFetch 只用來找網址。
- 研究改成**一人一個新 agent**，不再三人共用一個 context。單人檔在 `batchNNN/people/<bioId>.json`，工作流合併成原本的 `research.json`（schema 不變）。
- 引文是否逐字在原文，由 `verify.py` 判定（`quote_hit`）。Opus 只讀 `evidence-pack.json`（每筆 claim 的段落文字、quote、sourceKey、verify 結果），不重讀原文、不整批重抓。每批最多 1 次抽查重抓。
- `check_min.py` 固定寫 `check_min-report.json`，由工作流呼叫，不由 agent 呼叫。
- 每波最多 N 批（預設 3）。`limit` 只跑前 N 批。`dryRun` 只印計畫。

來源分級、每人至少 8 次查詢／4 種來源類型／原文語言查詢、不用 Wayback、Cloudflare／403 就放棄，都還在提示詞裡。

## 試跑 2–3 批

在倉庫根目錄。先只看計畫，不啟動 agent：

```bash
cd /Users/jack755051/Project/private/world_line-battle-demo
python3 -I tools/b3v3/plan_work.py \
  --repo "$PWD" \
  --prompt-dir .dev/b3v3/prompts \
  --out-root data/seed/leaders/b3-trial/full/v3 \
  --raw-root /Users/jack755051/wl-source-cache/b3full-v3 \
  --resume .dev/b3v3/partial/chunk4-remaining.json \
  --chunk 122,093,105 \
  --limit 3
```

這三批剛好各走一種階段：122 做研究（21 份原文已在 raw，應顯示 cached、不要重抓）、093 只重跑未達標的人再審查、105 只審查。

用和上次相同的方式把 workflow 交給 Claude Code（腳本仍是 `.dev/b3v3/workflow/b3-v3-chunk1-and-major-retry.js`），args 用 `.dev/b3v3/workflow/trial-args.json`。這份檔的 `dryRun` 是 `true`，第一輪只會印計畫。確認批號與階段後，把 `dryRun` 改成 `false` 再跑一次。

`concurrency` 是每一波最多幾批。試跑這 3 批可以維持 3。

## 續跑第四段（093–122）

剩餘清單是 `.dev/b3v3/partial/chunk4-remaining.json`（已依正規化後的 `check_min-report.json` 重算）。

```bash
python3 -I tools/b3v3/plan_work.py \
  --repo "$PWD" \
  --prompt-dir .dev/b3v3/prompts \
  --out-root data/seed/leaders/b3-trial/full/v3 \
  --raw-root /Users/jack755051/wl-source-cache/b3full-v3 \
  --resume .dev/b3v3/partial/chunk4-remaining.json \
  --concurrency 3
```

Claude Code 的 args 用 `.dev/b3v3/workflow/resume-chunk4-args.json`。建議先把其中的 `dryRun` 改成 `true` 看完整清單，再改回 `false`。預設每波 3 批，避免再把 5 小時額度一次打滿。

續跑規則：

- 已有 `research.json` 和 `verify-report.json` 的批不重跑研究。要整批重做才把 args 的 `forceResearch` 設成 `true`。
- 122 研究結束後，若有人未達最低標準，會自動加強重跑一次，再審查。
- 只重跑清單裡未達最低標準的人。
- 已有 `review.json` 的 097、098、100 不進清單。096 有審查檔，但是上次被中斷，會再審查一次。
- 122 會做研究；提示要求先 `status`，rawmap 裡已有的 sourceKey 不重抓。

## 工具

```bash
python3 -I tools/b3v3/fetch_source.py status --rawdir RAW --rawmap OUT/rawmap.json
python3 -I tools/b3v3/fetch_source.py fetch --rawdir RAW --rawmap OUT/rawmap.json \
  --source-key KEY --url 'https://example.test/a' --keywords '姓名|1920|部長'
python3 -I tools/b3v3/fetch_source.py lookup --rawdir RAW --rawmap OUT/rawmap.json \
  --source-key KEY --keywords '原文片段'
python3 -I tools/b3v3/merge_people.py merge --outdir OUT --rawdir RAW \
  --batch b3-full-v3-batch093 --order bio1,bio2,bio3
python3 -I tools/b3v3/evidence_pack.py OUT/research.json --out OUT/evidence-pack.json
python3 -I data/seed/leaders/b3-trial/full/v3/check_min.py OUT/research.json
```

`check_min.py` 不帶 `--out` 時寫同目錄的 `check_min-report.json`。若 `--out` 指向 `check-min.json` 或 `check-min-report.json`，會改寫到固定檔名。
