---
name: b3v3-run
description: 便宜地跑或續跑 B3 v3 人物生平。主 session 用 Sonnet，Python 做計畫與檢查，Sonnet 補缺欄或審查一個人，只有 verify 報錯或重跑後仍未達才升 Opus。
---

# B3 v3 便宜續跑

主 session 只用來調度。研究與審查交給 workflow 裡的 agent。不要把 research.json、證據包、原文或提示詞全文讀進主 session。

交接現況在 `.dev/b3v3/HANDOFF.md`。第四段剩餘清單是 `.dev/b3v3/partial/chunk4-remaining.json`。

## 主 session

```bash
cd /Users/jack755051/Project/private/world_line-battle-demo
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0
claude --model sonnet
```

`claude -p` 會在最後一輪結束 10 分鐘後停掉背景 workflow。上面的環境變數讓它一直等到 agent 結束。沒設就不要用 `-p`。

## 先看費用

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

dry-run 不寫檔、不啟動 agent。它印每一波的模型與人數。

## 續跑一波

參數與 dry-run 相同，指令改成 `next`：

```bash
python3 -I tools/b3v3/run_chunk.py next \
  --repo "$PWD" \
  --prompt-dir .dev/b3v3/prompts \
  --out-root data/seed/leaders/b3-trial/full/v3 \
  --raw-root "$HOME/wl-source-cache/b3full-v3" \
  --resume .dev/b3v3/partial/chunk4-remaining.json \
  --concurrency 3
```

- `ACTION spawn`：用 workflow `.dev/b3v3/workflow/b3-v3-chunk1-and-major-retry.js`。args 只用 `---workflow-args---` 到 `---end---` 那一段。不要把 spec 檔讀進對話，不要展開提示詞。
- workflow 只負責啟動 agent。agent 自己跑 `show-prompt` 取得任務。
- 同時最多 3 個 agent。
- agent 結束後再跑一次 `next`。它會合併、跑 verify 與 check_min，並印下一波。看到 `ACTION done` 才停。
- `ACTION waiting`：這一波的 `people/<bioId>.agent-done.json` 還沒齊。不要再 prepare。確認 workflow 真的跑完、只是沒寫標記時，才加 `--accept`。

## 哪一步用什麼

| 步驟 | 誰做 |
| --- | --- |
| 計畫、抽單人檔、合併、verify、check_min、證據切片 | `tools/b3v3/run_chunk.py`（Python，不耗模型） |
| 研究、只補缺的欄位 | Sonnet，一人一個 agent |
| 審查 | 預設 Sonnet，一人一個 agent，只讀自己的 `people/<bioId>.evidence.json` |
| 升 Opus | 該人的 verify 有錯，或補欄之後 check_min 仍是「未達」 |

模型可以改：`--research-model`、`--retry-model`、`--review-model`、`--escalate-model`。預設是 sonnet、sonnet、sonnet、opus。

## 證據切片

`run_chunk.py` 為每個審查對象寫 `people/<bioId>.evidence.json`。`claims` 的一筆是一個主張單位（段落、職位、候選角色或 gap）。`where` 是 `段<ord>`、`職位 <key>`、`候選角色 <key>` 或 `gap <target>`，不再附 `c0`、`c1`。`text` 只寫一次。`citations` 逐筆含 `index`、`quote`、`sourceKey`、`grade`、`verify`（`ok`、`normOffset`，沒過則有 `reason`）。同檔頂層保留 `checkMin`、`verifyErrors`。整批 `evidence-pack.json` 用同一形狀，另有 `claimCount`（單位數）、`citationCount`（引文數）、`failedClaimIndexes`（有引文沒過的單位在 `claims` 裡的索引）。

## 重跑與篇幅不足

- 只重跑補得了的缺欄：缺起日、缺迄日、缺引文、引文空白。提示詞會列出欄位，不要重做整份研究。
- `documentedShortfall` 或只差段數／字數的人不要重跑。審查時帶「篇幅不足」，verdict 可寫篇幅不足。
- 試跑已經重跑過的 122（Schober、Mosquera）不要再補欄。
- 已審查的 093、097、098、100、105 不要再進清單。093 的佩納被拿掉推論迄日，維持現況。
- 審查不要把已有出處或標成推論的起迄日改成 null。要改就留下「待查證：缺迄日」或「待查證：缺起日」，並寫原因。

## 不要做的事

- 不要 git add、commit、push。
- 不要寫資料庫，不要呼叫 5052 API。
- 不要繞過 Cloudflare、Anubis 或 403，不要用 Wayback 代替被擋的頁。
- 不要 Read、cat、head 整份 raw。
- `~/wl-source-cache/b3full-v3` 裡已有的 sourceKey 不要重抓。先 `fetch_source.py status`，再用 lookup。
- 單人檔的 `rawMap` 必須是物件（sourceKey → 檔名），不可以寫成字串 `"rawmap.json"`。
