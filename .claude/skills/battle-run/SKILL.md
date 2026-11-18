---
name: battle-run
description: 便宜地跑戰役文字資料（部隊位置、前線城鎮、交戰與易手日期、指揮官就任日）。主 session 用 Sonnet，只調度；Python 規劃缺口並從已快取原文切片段；R3 先刷掉附近沒有地名的片段；一次 claude -p（不給工具）抄格式化紀錄；Python 驗收。核對失敗或兩個說法衝突才升級或列給 Tai。不讀圖。
---

# 戰役文字流程（省 token）

主 session 只用來調度。不要把原文、片段檔、提示詞全文或 research 檔讀進主 session。規則本文是 `docs/source-rules.md`，操作版是 `.claude/skills/source-rules/SKILL.md`，步驟與完成條件是 `demos/battle-v2.5/DATA-WORKFLOW.md`。本技能只管「讀已有來源的文字」這一半；讀圖（控制點、標註、配準）仍按 DATA-WORKFLOW 步驟 3，以後另做。

產出一律寫到 repo 外的 staging（預設 `~/wl-battle-staging/<battle>/`）。不要改 `data/seed/battles/`。通過驗收的候選交給戰役 session 依 MERGE 說明併入。

## 主 session

```bash
cd /Users/jack755051/Project/private/world_line-battle-demo
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0
export PYTHONDONTWRITEBYTECODE=1
claude --model sonnet
```

`claude -p` 會在最後一輪結束 10 分鐘後停掉背景 agent。上面的環境變數讓它一直等到結束。沒設就不要用 `-p`。同時最多 3 個 agent（與其他工作流共用這個上限）。

## 先看費用與缺口（不啟動 agent）

```bash
python3 -I tools/battles/battle_run/cli.py dry-run \
  --repo "$PWD" \
  --battle dunkirk_1940 \
  --pilot ellis-ch10-calais \
  --stage "$HOME/wl-battle-staging/dunkirk_1940"
```

dry-run 只跑 Python 規劃與片段預篩，寫 `gap-list.json`、`dry-run-snippets.json`、`dry-run-summary.txt`。它印缺口數、有命中的片段字數、以及相對整章原文的比例。

第一個試跑任務是「把 Ellis 第 10 章的加萊補完」（敦克爾克 1940，5/22–5/26，只讀已快取的 `UK-NWE-Flanders-10.html`）。

## 續跑一批

先 `prep` 每一批，再用 `run` 把一批或幾批合成**一次 `claude -p` 呼叫**：

```bash
for b in b03 b04 b05 b06; do
  python3 -I tools/battles/battle_run/cli.py prep \
    --repo "$PWD" --battle dunkirk_1940 --batch $b \
    --stage "$HOME/wl-battle-staging/dunkirk_1940"
done

python3 -I tools/battles/battle_run/cli.py run \
  --repo "$PWD" --battle dunkirk_1940 --batch b03,b04,b05,b06 --model sonnet \
  --stage "$HOME/wl-battle-staging/dunkirk_1940"

python3 -I tools/battles/battle_run/cli.py verify \
  --repo "$PWD" --battle dunkirk_1940 \
  --stage "$HOME/wl-battle-staging/dunkirk_1940"
```

- `prep` 對部隊位置（R3）多做一道**地名鄰近篩選**：片段裡部隊名前後 150 字元內沒有已知地名（`osm-places.json`）、也沒有「介系詞＋專有名詞」，就丟掉；片段被丟光的缺口直接記查無，不送模型。國名、地區名（France、Kent、Flanders…）不算地名。要關掉加 `--no-loc-filter`。
- `run` 把片段直接放進提示詞，模型**不給任何工具、不載 MCP、不讀 CLAUDE.md**，只輸出 JSON，由 Python 寫 `out/<名稱>.json`，用量附加到 `usage.jsonl`。工作目錄設在 staging。印一行：缺口數、token、花費、候選、查無。
- 一次合併多少批：以提示詞約 3 萬字元為上限（`run --dry` 只寫提示詞並印字數，不呼叫模型）。
- 不要再用開完整子 agent 的做法（舊的 `prompts/<批>.md`）。2026-11-18 實測：子 agent 一批約 5 萬 token，九成是固定成本；`run` 合併四批只用 7.7 千 token。
- 主 session 只看 `run` 與 `verify` 各印的一行。看到該看的批次都跑完、升級清單已列給 Tai，才停。

### 模型

預設 `--model sonnet`。`haiku` 約便宜十倍；引文逐字、地點是否為城鎮、座標都由 `verify` 驗收，模型只負責找出那一句。2026-11-18 拿 b03–b06 對照，兩者都判 5 個缺口查無、理由相同，但沒有產生任何候選，所以還不能確定 Haiku 抄引文的準確度。等第一批有候選的來源時，先兩個都跑一次比對，`verify` 失敗率相同再改預設。

### 搜尋範圍

`--pilot` 只搜一章（試跑用）。正式跑不要加 `--pilot`，預篩會搜 `sources.json`、既有引文網址與 fetch-status 裡全部已快取的原文。

## 哪一步用什麼

| 步驟 | 誰做 |
| --- | --- |
| 從名冊、gaps.json、匯入報告算出缺口並切批 | `tools/battles/battle_run` 的 `plan`（Python，不耗模型） |
| 在已快取原文裡用部隊名、別名、日期搜尋，只交出命中段落 | `snippets`／`prep`（Python） |
| R3 片段部隊名附近沒有地名的，先刷掉 | `prep` 的地名鄰近篩選（Python） |
| 按格式抄錄：部隊代號、日期、地名、逐字引文、sourceKey | `run`：一次 `claude -p`（Sonnet，不給工具），可合併多批；Python 寫 staging |
| 引文逐字核對、跨頁檢查、地點是否為城鎮、座標對已有 osm-places、來源等級 | `verify`（Python）。主 session 只看一行摘要 |
| 升較強模型，或列給 Tai | 該筆 verify 失敗，或兩筆來源說法衝突 |
| 併入戰役資料、`verify_quotes.py`、`crosscheck.py`、缺的地名跑 `osm_lookup.py`、匯入展示頁 | 戰役 session。本技能不改 seed、不跑 `--apply` |

找新來源（可選）：`context` 寫精簡上下文 → 子 agent 用 `prompts/discovery.md` 寫 `sources-candidates.json` → `fetch` 抓原文（已快取不重抓，同站間隔 ≥ 1.1 秒，遇到 Cloudflare／Anubis／403／登入頁記 blocked，不繞過，不用 Wayback）。這一步不能取代「先把已有來源讀完」。

## 用量與停損

每跑完一批（或每開新 agent 之前）查一次：

```bash
python3 -I tools/battles/battle_run/cli.py tokens \
  --since 2026-11-18T08:00:00+08:00 \
  --stop-tokens 5000000
```

統計範圍包含 staging 資料夾，以及 `--repo` 指的戰役 repo（主 session 與它開的子 agent 都記在那裡；2026-11-18 以前漏算）。主 session 本身也算進去，所以數字會比 `run` 的總和大很多，這是正確的。別的工作目錄用 `--project-dir` 加。

五小時額度約 68.75M tokens。預設停損 5M（約 7%）。超過就停，先回報，不要再開新 agent。門檻可用 `--stop-tokens` 改。

## 抄錄與驗收規則（試跑後訂的）

- 地點必須是具體城鎮或村莊，不能是國家、地區或「前線／the front」。
- 引文不可跨分頁（PDF 換頁符、HyperWar 的 `--頁碼--`）。
- 引文 ≤ 80 字元（NFC），且須在存檔原文裡逐字出現。
- 不用 Wikipedia、Wikidata 當出處（只能當索引）。不用 Wayback。不繞過機器人防線。
- 已快取的原文不要重抓。對同一主機兩次請求至少隔 1 秒。
- 沒有出處的資料不寫入。兩個說法衝突時兩筆都留，不要自己選。

## 不要做的事

- 不要 git add、commit、push。
- 不要寫資料庫，不要呼叫 5052 API。
- 不要繞過 Cloudflare、Anubis、403、captcha 或登入頁，不要用 Wayback 代替被擋的頁。
- 不要 Read、cat、head 整份 raw 或整章原文進主 session。
- 不要改 `data/seed/battles/`，不要對 `verify_quotes.py`／`crosscheck.py`／`osm_lookup.py` 加 `--apply`（那些會寫回戰役資料或 osm-places）。
- 不要動戰役 session 未提交的檔（`demos/battle-v2.3` 等）或其他工作流正在用的 staging。
- 地圖讀圖不在本技能範圍。
