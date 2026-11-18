# B3 v3 第四段交接（批次 093–122）

給新 session 讀。不要接著 2026-11-17 那場長對話。主 session 用 `claude --model sonnet`。

試跑是台北時間 2026-11-17 19:52–20:19，批次 093、105、122，9 人，做到一半。約 1300 萬 token，大約 Claude Max 五小時額度的兩成。單次上下文已降到 Sonnet 平均 52K、Opus 70K，尖峰 125K，總量仍然高。主 session 當時用 Opus 只為了派工與跑腳本，約 180 萬 token。

## 現況

重算來源是各批 `research.json`（`plan_work.py --recompute-remaining`），沒有改研究檔。清單在 `.dev/b3v3/partial/chunk4-remaining.json`。

- 略過：097、098、100、093（試跑已重跑並審查）、105（試跑已審查）。
- 093 的佩納：審查把推論迄日改成 null，現在是「已標註缺迄日」。Averescu、Uriburu 仍是篇幅不足。這一批不再動。
- 122：研究與加強重跑已做完，只審查。Schober、Mosquera 不再補欄。孔祥熙是篇幅不足。三人 verify 仍有錯，審查用 Opus。
- 096：上次審查中斷，重查。三人達標且 verify 通過，用 Sonnet。
- 只審查（達標）：107、108、112、113、114、118、121。
- 只審查（整批都是篇幅不足，不重跑）：095、101、103、116、119。
- 先補缺欄再審查：094、099、102、104、106、109、110、111、115、117、120。共 16 人，欄位都是缺迄日。同批裡 Laagan（110）、Goremykin（120）是篇幅不足，不重跑，審查時帶旗標。

094、095、099、101–104、106、109–111、115–117、119、120 這些尚未審查的批，未達標共 27 人：16 人只補缺迄日，11 人篇幅不足、直接送審。122 的孔祥熙另計，也是篇幅不足。

## 下一道指令

在已包含這次改動的工作目錄：

```bash
cd /Users/jack755051/Project/private/world_line-battle-demo
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0
claude --model sonnet -p '讀 .claude/skills/b3v3-run/SKILL.md 與 .dev/b3v3/HANDOFF.md。你是主 session，用 Sonnet 調度，不要自己做研究。依技能續跑第四段：先跑 dry-run，確認和交接檔一致，然後重複 python3 -I tools/b3v3/run_chunk.py next（參數見技能），再用 workflow .dev/b3v3/workflow/b3-v3-chunk1-and-major-retry.js 只啟動該波 args 裡的 agent。同時 3 個。不要 git、不要寫庫、不要呼叫 5052、不要重抓已快取的原文。'
```

沒有 `-p` 也可以，進 session 後把同一段話貼上。環境變數仍然要設：`claude -p` 否則會在最後一輪 10 分鐘後停掉背景 workflow。

只看費用、不啟動 agent：

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

## dry-run（2026-11-17 重算後）

研究 0、重跑 16（Sonnet，6 波）、審查 75（Sonnet 72、Opus 3，25 波），同時 3。Opus 只有 122 的三人。補欄那 16 人目前的審查預估是 Sonnet；若補完後 check_min 變成「未達」或 verify 報錯，該人改 Opus。

重跑欄位：

- 094 Milan Hodža：`role:hodza-sns-1906.end`
- 099 Juho Emil Sunila：農業部長、農業總監、1922 副職，三筆迄日
- 102 Emiliano Figueroa Larraín：駐秘魯、央行，兩筆迄日
- 104 Marģers Skujenieks：統計局長迄日
- 106 Nikoloz Chkheidze：杜馬、議會，兩筆迄日
- 106 Thomas Madsen-Mygdal：農業委員會迄日
- 109 Antonio Salandra：國聯代表、議員、參議員，三筆迄日
- 109 田中義一：貴族院、政友會總裁，兩筆迄日
- 109 Duan Qirui：1916 陸軍總長迄日
- 110 Manuel Teixeira Gomes：駐倫敦、國聯代表，兩筆迄日
- 111 Heinrich Brüning：中央黨團迄日
- 111 Carl Gustaf Ekman：自由黨主席迄日
- 115 Sigurður Eggerz：冰島事務大臣、財政大臣，兩筆迄日
- 117 Władysław Grabski：制憲議會、1923 財政，兩筆迄日
- 117 Afonso Augusto da Costa：民主黨主席迄日
- 120 Hermann Müller：社民黨主席、黨執行委員，兩筆迄日

篇幅不足、不重跑：095 Reyes、Teleki、Rauschning；101 Mushanov；103 Oliveira；110 Laagan；116 Leconte、Eenpalu、González Valencia；119 Jin Yunpeng；120 Goremykin；122 孔祥熙。

## 用量教訓

- 一人一個新 agent、原文只走 `fetch_source.py` 之後，單次上下文降下來了，總 token 仍高。主 session 不要用 Opus，也不要自己讀原文。
- workflow 執行環境不能 `import('node:fs')` 或 `node:child_process`。計畫與檢查放在 `tools/b3v3/run_chunk.py`，workflow 只啟動 agent。
- 篇幅不足的人整份重跑補不出字（Averescu、Uriburu）。這種人直接送審。
- 研究 agent 會把單人檔 `rawMap` 寫成字串 `"rawmap.json"`。合併程式會改成物件；提示詞仍要求寫物件。
- 審查不要為了「這是推論」就拿掉已寫上的迄日。佩納因此從達標變成已標註缺迄日。
- 每人證據切片 `people/<bioId>.evidence.json` 的 `claims` 以段、職位、候選角色、gap 為單位：`where` 與 `text` 只寫一次，`citations` 逐筆含 `index`、`quote`、`sourceKey`、`grade`、`verify`（`ok`、`normOffset` 或 `reason`）。`checkMin`、`verifyErrors` 仍在檔案頂層。整批 `evidence-pack.json` 同形，`failedClaimIndexes` 是沒過的單位索引。
