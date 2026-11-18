# B3 v3 省 token 工作流

研究仍在本機用 Claude Code 跑。原文放在倉庫外面的 `~/wl-source-cache/b3full-v3/batchNNN/raw/`。不寫資料庫、不呼叫 5052 API。

主 session 用 `claude --model sonnet`，並設定 `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`，否則 `claude -p` 會在最後一輪 10 分鐘後停掉背景 workflow。操作步驟在 `.claude/skills/b3v3-run/SKILL.md`，第四段現況在 `.dev/b3v3/HANDOFF.md`。

和上一輪把整頁原文送進上下文的差別：

- 網頁與 PDF 由 `tools/b3v3/fetch_source.py` 抓（curl、不加 `-k`、UA `Mozilla/5.0`）。已有的 sourceKey 不重抓。
- 抄引文用 `lookup`。禁止 Read／cat 整份 raw。
- 研究是一人一個新 agent。單人檔在 `batchNNN/people/<bioId>.json`，`rawMap` 必須是物件。`merge_people.py` 若收到字串 `"rawmap.json"` 會改成物件再合併。
- 只補 check_min 裡補得了的缺欄（缺起迄日、缺引文）。篇幅不足的人不再重跑，審查時帶旗標。
- 審查預設 Sonnet，一人一份證據切片。verify 有錯，或補欄後仍是「未達」，才升 Opus。
- `verify.py` 與 `check_min.py` 由 `tools/b3v3/run_chunk.py` 呼叫，不由 agent 呼叫。
- workflow `.dev/b3v3/workflow/b3-v3-chunk1-and-major-retry.js` 不讀檔、不跑 Python。它只依 `run_chunk.py next` 印出的 args 啟動 agent。

## 先看計畫

```bash
cd /Users/jack755051/Project/private/world_line-battle-demo
python3 -I tools/b3v3/run_chunk.py dry-run \
  --repo "$PWD" \
  --prompt-dir .dev/b3v3/prompts \
  --out-root data/seed/leaders/b3-trial/full/v3 \
  --raw-root "$HOME/wl-source-cache/b3full-v3" \
  --resume .dev/b3v3/partial/chunk4-remaining.json \
  --concurrency 3
```

## 續跑第四段

```bash
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0
claude --model sonnet
```

session 裡重複 `run_chunk.py next`（參數與 dry-run 相同）。`ACTION spawn` 時把印出的 workflow args 交給上面的 workflow，同時 3 個 agent。`ACTION done` 才停。

重算剩餘清單（只寫 `chunk4-remaining.json`）：

```bash
python3 -I tools/b3v3/plan_work.py \
  --repo "$PWD" \
  --out-root data/seed/leaders/b3-trial/full/v3 \
  --recompute-remaining .dev/b3v3/partial/chunk4-remaining.json
```

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
python3 -I tools/b3v3/evidence_pack.py OUT/research.json --person KEY --out OUT/people/BIO.evidence.json
python3 -I data/seed/leaders/b3-trial/full/v3/check_min.py OUT/research.json
```

`check_min.py` 的 verdict 是 `OK`、`篇幅不足`、`已標註缺迄日` 或 `未達`。補欄之後只有「未達」會把該人的審查升到 Opus。
