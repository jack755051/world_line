---
name: b3v3-run
description: 便宜地跑或續跑 B3 v3 人物生平。run_loop.py 用 Python 預查、計畫與檢查，Sonnet 研究與審查一個人，只有審查後 verify 仍有錯才升 Opus。
---

# B3 v3 便宜續跑

主 session 只用來調度。研究與審查交給 workflow 裡的 agent。不要把 research.json、證據包、原文或提示詞全文讀進主 session。

交接現況在 `.dev/b3v3/HANDOFF.md`。第四段剩餘清單是 `.dev/b3v3/partial/chunk4-remaining.json`。

## 低成本迴圈（建議）

不用主 session 調度，直接在 repo 跑：

```bash
cd /Users/jack755051/Project/private/world_line-battle-demo
nohup python3 -u tools/b3v3/run_loop.py --chunk <NN> [--people <bioId,...>] \
  --state .dev/b3v3/run/loop-state.json --spec-out .dev/b3v3/run/loop-spec.json \
  --log-dir ~/wl-b3v3-runs/loop > ~/wl-b3v3-runs/loop/loop.out 2>&1 &
python3 tools/b3v3/session_cost.py --journal ~/wl-b3v3-runs/loop/journal.jsonl   # 每個 agent 的 token
```

- 研究前 `prefilter.py` 先用索引（Wikidata 只當索引，不當出處）、LoC、lobid 找權威檔／傳記辭典網址，抓頁、挑含人名段落，寫 `people/<bioId>.snippets.md`、`.prefilter.json`。其他批抓過的網址複製原文，不重抓。
- 有傳記敘述的命中來源少於 2 個或段落少於 2500 字時，先跑一次 haiku（只 WebSearch，回網址），再預查一次。
- 研究 agent 只寫 `people/<bioId>.draft.json`，用 `person_draft.py check` 自檢；Python 組回原格式的單人檔。審查只讀證據切片，用 `person_patch.py` 改欄位，用 `person_draft.py review-done` 收尾。
- 每次啟動都固定模型、`--max-turns`、精簡工具與系統提示（不載 MCP、slash 指令）：研究 sonnet 11 輪、補欄 sonnet 9、審查 sonnet 6、升級 opus 6、找網址 haiku 4。
- 網路錯誤（ENOTFOUND 等）連 3 次或 DNS 連 3 分鐘失敗就殺掉，等網路回來再重開；額度用完等 20 分鐘。
- 要停：`touch ~/wl-b3v3-runs/loop/STOP`。

## 主 session（舊流程）

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
| 升 Opus | Sonnet 審查改完後該人的 verify 仍有錯（只此一種） |

模型可以改：`--research-model`、`--retry-model`、`--review-model`、`--escalate-model`。預設是 sonnet、sonnet、sonnet、opus。

## 證據切片

`run_chunk.py` 為每個審查對象寫 `people/<bioId>.evidence.json`。`claims` 的一筆是一個主張單位（段落、職位、候選角色或 gap）。`where` 是 `段<ord>`、`職位 <key>`、`候選角色 <key>` 或 `gap <target>`，不再附 `c0`、`c1`。`text` 只寫一次。`citations` 逐筆含 `index`、`quote`、`sourceKey`、`grade`、`verify`（`ok`、`normOffset`，沒過則有 `reason`）。同檔頂層保留 `checkMin`、`verifyErrors`。整批 `evidence-pack.json` 用同一形狀，另有 `claimCount`（單位數）、`citationCount`（引文數）、`failedClaimIndexes`（有引文沒過的單位在 `claims` 裡的索引）。

## 重跑與篇幅不足

- 只重跑補得了的缺欄：缺起日、尚未標「待查證：缺迄日」的缺迄日、缺引文、引文空白。提示詞只列這些欄位，不要重做整份研究。
- 同一 target 的 gap note 已含「待查證：缺迄日」時，這個缺迄日不重跑，仍留在 missingFields（`fixable` 為 false、`alreadyFlagged`）供檢查與審查看。只剩這種缺迄日的人直接送審，不標篇幅不足。
- `documentedShortfall` 或只差段數／字數的人不要重跑。審查時帶「篇幅不足」，verdict 可寫篇幅不足。和已標註缺迄日同時存在時也不重跑。
- 試跑已經重跑過的 122（Schober、Mosquera）不要再補欄。
- 已審查的 093、097、098、100、105 不要再進清單。093 的佩納被拿掉推論迄日，維持現況。
- 審查不要把已有出處或標成推論的起迄日改成 null。要改就留下「待查證：缺迄日」或「待查證：缺起日」，並寫原因。

## 分層補查（tools/b3v3/tiers.py，2026-11-18）

- 第一階段：原本的便宜 A／B 流程。結果是「篇幅不足」或有缺迄日的人，才進第二階段。
- 第二階段（`deep`，Sonnet）：再做一次較大的 A／B 補查。預查會用索引上所有語言的原文姓名；日本人另外先抓コトバンク與首相官邸歷代內閣頁。agent 再用 WebSearch 查 3–5 次，至少 2 次用原文姓名，日本人加查 JACAR／NDL。已被 403 擋過的網域不再試。新的起迄日年份必須出現在引文裡，民國與日本年號會換算。
- 第三階段（`csupp`，Sonnet，不能 WebSearch）：第二階段仍不夠才做。用 Wikipedia（從 Wikidata sitelinks 找頁面）寫 `person.supplementC`，只補到最低篇幅，以及補起迄日。
- 審查：沿用原本的 Sonnet 審查，只在內容有改時才審。接著由 Python 找主段落裡沒有出處的句子（`tools/b3v3/uncited.py`）。有找到才給 Sonnet 1–2 輪補 claimSpan（`citefix`）；補不到的就刪掉（中英句數一致時），否則標「待補」，兩種情況都會加 `paragraph:<ord>` gap。
- 用法：`python3 tools/b3v3/tiers.py candidates`，以及 `python3 tools/b3v3/tiers.py run --people NNN:bioId,... --work-root .dev/b3v3/run/tiers-xxx --log-dir ~/wl-b3v3-runs/tiers-xxx`。結果寫在工作目錄，不會自動併回 research.json。

### supplementC（C 級補充區，加在 person 下，不改主 schema）

```json
"supplementC": {
  "grade": "C", "status": "A/B不足，已用C補", "displayFlag": "未查證・維基百科補充",
  "note": "…", "addedOn": "2026-11-18",
  "sources": {"c-wp-ja-xxxxxx": {"url": "https://ja.wikipedia.org/wiki/…", "title": "…", "grade": "C"}},
  "clauses": [{"target": "paragraph:length", "zh-Hant": "…", "en": "…",
               "cKey": "c-wp-ja-xxxxxx", "url": "https://…", "quote": "逐字 ≤80 字"}],
  "dates": [{"target": "position:<key>.end", "value": "1929-09-29", "cKey": "…", "url": "…",
             "quote": "…", "status": "待查證（只有 C 級來源）", "confirmed": false}]
}
```

- 主段落、職位、角色都不能引 C（verify 規則 19）。check_min 與查證程度只算 A／B；有 C 時 verdict 是「A/B不足，已用C補」。
- C 引文仍要逐字、≤80 字。verify 會查，但錯誤另外列在 `supplementCErrors`。
- 只有 C 的日期一律待查證，不算已確認。之後 A／B 補到同一欄位，`tiers.py prune` 會刪掉對應的 C。
- 前端或匯入要顯示 C 內容時，必須加註 `displayFlag`「未查證・維基百科補充」。前端還沒做。

### A／B 為準與引文支撐（tools/c_rules.py，verify 與 tiers 共用）

- C 和 A／B 衝突就以 A／B 為準。以下情況算衝突：同一端 A／B 已有不同值；C 迄日早於 A／B 起日，或 C 起日晚於 A／B 迄日；C 引文寫的年–年任期和 A／B 任期不重疊；C 日期落在另一筆同名 A／B 任期裡；C 句子提到 A／B 職稱，但年份都在任期外。
- 衝突的 C 會被 Python 移到 `supplementC.conflictNotes`，並附 `conflictsWithAB`（ref、abValue、reason），不顯示、不計入。verify 對還留在 clauses／dates 的衝突報 C 錯誤。
- C 句子的年份、月日、數字、拉丁專名、「」《》裡的詞都要出現在引文裡，比對前會換算民國、日本年號、漢數字、外文月名、新舊字形。整條字數也不能超過引文份量（1.6 倍＋12 字）。沒有支撐的句子會被刪掉，全條都沒有就改成「維基百科（ja）原文：「…」」。每次處理都記在 `supplementC.auditLog`。漢字人名、地名無法自動認出來，所以沒查。
- 第二階段新寫的 A／B 句子也查：年份不在 claimSpan 指到的引文裡，就自動刪掉；只缺月日或數字的，回報給 agent 改。
- 缺迄日的找法：預查附上 Wikidata 的職務、起訖與後任（只當線索），agent 用來搜後任就任日、官方歷任名單、在任中去世。用後任就任日推出的迄日，要在 evidenceNote 標「推論：下一任…」。只有 C 的迄日一律待查證。
- 併回正式批次用 `python3 tools/b3v3/tiers.py merge --people NNN:bioId,... --work-root <工作目錄> [--report out.json]`。預設是 dry-run：在暫存複本上合併，再跑 verify 與 check_min，正式檔不動。加 `--apply` 才會寫 research.json、people/<id>.json、rawmap.json。
- 第二階段的條件只有篇幅不足或缺迄日；搜尋紀錄裡的 403 不算條件。

### 第二階段日期的把關（2026-11-19，段祺瑞陸軍總長案後加）

- 第二階段改日期時，Python 會退回三種改法，並在 problems 記 `REFUSED`／`CAPPED`：
  - 改成 day 精度，但引文沒寫那一天：退回該端，保留原值、原精度和 gap。
  - 任期中間有免職、辭職或復任：本人段落裡同一子句同時有中斷詞和職稱，而且那個日期落在新任期內。這可能是兩段任期被合成一段，整筆退回，gap 保留。唯讀檢查用 `python3 tools/b3v3/tiers.py terms --file <research.json|單人檔>`。
  - 推論迄日（evidenceNote 有「推論」）是 day 精度，但沒有引文同時寫「任命／就任」和那一天：封頂成 `YYYY-MM-01`、month 精度，evidenceNote 加註「推論上限：不晚於 …」。
- 審查切片 `<bio>.evidence.json` 多了兩項。`units` 列每個職位／角色的起訖精度、evidenceNote 和 termBreaks。`stage2Changes` 是和 `.stage1.json` 的逐欄差異。有改動時，審查提示會加一段說明：第二階段改過的日期不適用「維持原日期」，day 精度要引文寫出那一天，推論迄日要寫出後任任命那一天。
- 這段說明讓每人審查成本約多 $0.003–0.01（原本約 $0.04–0.06）。termBreaks 在全部 v3 批次的唯讀掃描中有 6 筆誤報，例如別人辭職、職稱末兩字相同。誤報只會讓修改被退回、gap 保留，不會寫進錯誤資料。

### pilot5 後修正（2026-11-19）

- **gaps 整理（`sync_gaps`）。** 第二階段套用後和收尾各跑一次：
  - 同一個 target、同一類的 gap 只留最新一筆。類別看 note 冒號前；「待查證」再分缺迄日／缺起日。
  - 篇幅已達 3 段、300 字，就移除 `paragraph:length`。
  - 正式批次裡有 49 人掛著這種舊的篇幅 gap（39 人 verdict 因此顯示「篇幅不足」）。這次沒動正式資料，等這些人跑分層補查時會順手清掉。
- **候選分類。** `candidates` 多一個 `category`：篇幅不足／只缺迄日／兩者，依實際段數、字數和缺的迄日算，不看 check_min 的 verdict 字樣。`--exclude-results a.json,b.json` 會排除已跑過的人。
- **斷網重試。** 每次重試前，把 person、stage2、supplementC、review、done 這幾個檔還原成第一次啟動前的樣子。中斷那輪寫了一半的檔留作 `.attemptN-partial`，journal 記 `retry_restore`。
  - 中斷那輪的用量從串流估算，記在 `partialUsage.estCostUSD`。Sonnet 費率對 pilot 實際費用校準過，誤差在 +20% 以內；Haiku 搜尋子呼叫沒算。
  - results 每人多記 `cost`（各階段 actual／estimatedPartial）和 `costTotal`。
- **`run --skip-stage2-end-only`（備而未用）。** 篇幅已夠、只缺迄日的人跳過第二階段，直接進 C 補充。這些人的迄日只會拿到 C，一律待查證。

## 不要做的事

- 不要 git add、commit、push。
- 不要寫資料庫，不要呼叫 5052 API。
- 不要繞過 Cloudflare、Anubis 或 403，不要用 Wayback 代替被擋的頁。
- 不要 Read、cat、head 整份 raw。
- `~/wl-source-cache/b3full-v3` 裡已有的 sourceKey 不要重抓。先 `fetch_source.py status`，再用 lookup。
- 單人檔的 `rawMap` 必須是物件（sourceKey → 檔名），不可以寫成字串 `"rawmap.json"`。

## pilot6 前修正（2026-11-19）
- watchdog 只數 stderr／system 事件的網路錯誤，不看 agent 或工具輸出的文字。
- fetch_source：解 gzip／deflate（br 要有 brotli 模組）；快取原文 <500 字且不是擋頁／登入頁時會重抓。
- 推論上限改成「下一個月第一天」（寫作規則）；已合併資料沒有用到舊上限。
- 階段二缺迄日：搜完跑 `tiers.py harvest --spec --id`（從搜尋結果挑 A／B 網域、自動抓前 3 頁、同 host 間隔 1 秒、只回姓名＋年份片段；host 解析不到只換同站 www.）。self-check 要 harvest.json 存在，且至少 2 個非 wiki 候選網址已抓或寫明略過原因（`<bio>.harvest.json`＋searchLog url/result）。
- 原文姓名只給本人語言（key 前綴對照）＋英文。deep maxTurns 20、工具呼叫上限 18。
