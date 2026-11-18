#!/usr/bin/env python3
"""將領生平「只補缺欄位」補跑費用估算（ARCHITECTURE §20.2／20.10 的欄位補跑方式；主迴圈 2026-11-12 21:29 結束後）。
World Line 主管 2026-11-12 21:34（Tai 同意重估）。**只估算**：不補跑、不寫庫、不改 research.json。
輸入：stats.json（collect_stats.py 產生；min-check 以 check_min 對現行 research.json 重算）、../bios/selection.json、
      .dev 成本檔、/tmp/generals-bios 快取是否存在。輸出：refill-estimate.md、refill-estimate.json（本目錄）。
用法（repo 根目錄）：python3 -I data/seed/leaders/generals-roster/design/refill_estimate.py

所有比例／倍數都是**假設**（下方 ASSUME），金額＝人數×每人平均（實測）×比例×重抓倍數。
"""
import json, glob, collections, datetime, os
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
st = json.loads((HERE / "stats.json").read_text(encoding="utf-8"))
sel = json.loads((HERE.parent / "bios" / "selection.json").read_text(encoding="utf-8"))
CAP = 340.0
SC = ("低", "中", "高")

# ---------- 假設 ----------
ASSUME = {
    # 每種欄位、每人的相對成本（× 該級每人平均整人成本）；沿用 §20.10.1 C1／C3／C4／C5 的比例
    "unit": {
        "任期": (0.15, 0.30, 0.50),    # 缺起或迄（含「待查證：缺迄日」）：重讀已抓來源補日期，常需新抓下一任／任命頁
        "戰役": (0.15, 0.30, 0.50),    # 無戰役：多可由既有來源萃取；需新來源者較貴
        "指揮職": (0.05, 0.25, 0.50),  # 無指揮職：新規不要求，低檔只記 no_command_role gap；高檔需新來源
        "L3": (0.60, 0.85, 1.00),      # 段落 <3 或字數 <300：補敘述幾乎等於整人重寫
        "段落0": (1.00, 1.00, 1.30),   # 0 段：整人重跑；高檔含平均 retry
        "引文": (0.10, 0.20, 0.30),    # 段落缺 quote（本次實測 0 人，金額必為 0）
    },
    "secondary": 0.5,                   # 同一人有多種缺欄：最貴那項全額，其餘各 ×0.5（同一個 session、共用已讀來源）
    "refetch_rate": (0.0, 0.25, 1.0),   # 需重抓的已抓頁面比例：低＝快取全在；中＝四分之一要重抓；高＝快取被清（/tmp 重開機會清）
    "refetch_penalty": 0.4,             # 重抓全部頁面時成本 +40%（倍數＝1＋0.4×重抓比例）
}
L12 = ("任期", "戰役", "指揮職")
L3S = ("L3", "段落0", "引文")

cost = st["cost"]
AVG = {"S": cost["S_usdPerPerson"], "A": cost["A_usdPerPerson"]}

def mult(i):
    return 1 + ASSUME["refetch_penalty"] * ASSUME["refetch_rate"][i]

def fields(f):
    out = []
    if f["termsMissing"] or f["termsFlagged"]: out.append("任期")
    if not f["hasBattle"]: out.append("戰役")
    if not f["hasCommand"]: out.append("指揮職")
    if f["paragraphs"] == 0: out.append("段落0")
    elif f["paragraphs"] < 3 or f["zhChars"] < 300: out.append("L3")
    if f.get("missingQuote"): out.append("引文")
    return out

def person_cost(f, i):
    fs = fields(f)
    if "段落0" in fs:
        fs = ["段落0"]  # 整人重跑已涵蓋其他欄位
    units = sorted(((ASSUME["unit"][x][i], x) for x in fs), reverse=True)
    alloc = {}
    for j, (u, x) in enumerate(units):
        alloc[x] = AVG[f["tier"]] * u * (1 if j == 0 else ASSUME["secondary"]) * mult(i)
    return alloc

# ---------- 名單 ----------
fail_rows = st["failing"]
fail = [f for f in fail_rows if not f.get("duplicateOf")]
# 以 key 比對；對不上時在同一批的 research.json 內以原文名（name_original == name）或 key 包含關係對應
# （A/batch022 研究檔用了短 key：yamaguchi、yamagata、shimada、kimura、matsui，與 selection 不同）
never, key_mismatch = [], []
for t in ("S", "A"):
    for b in sel[t]:
        rf = HERE.parent / "bios" / t / f"batch{b['batch']}" / "research.json"
        rp = json.loads(rf.read_text(encoding="utf-8")).get("people") or [] if rf.exists() else []
        for q in b["people"]:
            if any(p.get("key") == q["key"] for p in rp):
                continue
            hit = next((p for p in rp if (p.get("name") or "").casefold() == (q.get("name_original") or "").casefold()
                        or (p.get("key") and p["key"] in q["key"])), None)
            if hit:
                key_mismatch.append(f"{t}/batch{b['batch']} {q['key']}→{hit['key']}")
            else:
                never.append((t, q["key"]))

# 戰役指揮官代理名單（無可靠清單：data/seed/battles 只有 Dunkirk 1940 一場、且無人物層；§20.8：戰役指揮官名單尚不存在）
# 代理 P1（嚴）＝有 military_command 職位且正文提到戰役（check_min hasCommand ∧ hasBattle）；P2（寬）＝有 military_command 職位
def proxy(f, strict):
    return f["hasCommand"] and (f["hasBattle"] if strict else True)

# ---------- 分類 ----------
excl = collections.Counter(); over = collections.Counter()
for f in fail:
    fs = fields(f)
    for x in fs: over[x] += 1
    excl["＋".join(fs)] += 1
terms_people = sum(1 for f in fail if "任期" in fields(f))
terms_cnt = {"缺起或迄": sum(f["termsMissing"] for f in fail), "缺迄待查": sum(f["termsFlagged"] for f in fail)}

def total(group, i):
    by = collections.Counter()
    for f in group:
        for k, v in person_cost(f, i).items(): by[k] += v
    return by

res = {}
for name, grp in (("全部未達標", fail), ("戰役指揮官優先 P1（嚴，代理）", [f for f in fail if proxy(f, True)]),
                  ("戰役指揮官優先 P2（寬，代理）", [f for f in fail if proxy(f, False)])):
    rows = []
    for i in range(3):
        by = total(grp, i)
        a = sum(by[k] for k in L12); b = sum(by[k] for k in L3S)
        rows.append({"scenario": SC[i], "people": len(grp), "byField": {k: round(by[k], 2) for k in L12 + L3S},
                     "a_L1L2": round(a, 2), "b_L3": round(b, 2), "total": round(a + b, 2)})
    res[name] = rows
never_cost = [round(sum(AVG[t] * ASSUME["unit"]["段落0"][i] * mult(i) for t, _ in never), 2) for i in range(3)]

# ---------- 花費與上限 ----------
spent_files = {}
for f in sorted(glob.glob(str(REPO / ".dev/cc-generals-*.json"))) + [str(REPO / ".dev/cc-person-facts-design.json"), str(REPO / ".dev/cc-person-facts-estimate.json")]:
    try:
        c = json.load(open(f)).get("total_cost_usd")
    except Exception:
        c = None
    if c is not None:
        spent_files[Path(f).name] = float(c)
gen = sum(v for k, v in spent_files.items() if k.startswith("cc-generals-"))
spent = sum(spent_files.values())
caps = {}
for name, rows in res.items():
    caps[name] = [{"scenario": r["scenario"], "estimate": r["total"], "after": round(spent + r["total"], 2),
                   "headroom": round(CAP - spent - r["total"], 2), "exceeds340": spent + r["total"] > CAP} for r in rows]

cache = {t: len(glob.glob(f"/tmp/generals-bios/{t}/batch*/raw")) for t in ("S", "A")}
batches = {t: len(glob.glob(str(HERE.parent / "bios" / t / "batch*" / "research.json"))) for t in ("S", "A")}

out = {"generatedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
       "statsGeneratedAt": st["generatedAt"], "assumptions": ASSUME, "avgPerPerson": AVG,
       "minCheck": {t: {k: st["minCheck"][t][k] for k in ("rows", "meets", "fail", "uniquePeople", "uniqueMeets", "uniqueFail", "knownDuplicatesPresent")} for t in ("S", "A")},
       "staleMinCheckJson": len(st["minCheck"]["staleMinCheckJson"]),
       "failRows": len(fail_rows), "failUnique": len(fail), "neverWritten": [f"{t}/{k}" for t, k in never], "keyMismatchWithSelection": key_mismatch,
       "exclusiveBuckets": dict(excl.most_common()), "overlapping": dict(over), "termsPeople": terms_people, "termsCount": terms_cnt,
       "missingQuoteParagraphs": 0, "estimates": res, "neverWrittenCost": never_cost,
       "spent": {"generalsGlob": round(gen, 4), "files": len(spent_files), "total": round(spent, 4),
                 "personFacts": {k: round(v, 4) for k, v in spent_files.items() if not k.startswith("cc-generals-")}},
       "cap": caps, "tmpRawCache": {"dirs": cache, "batches": batches}}
(HERE / "refill-estimate.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

L = [f"# 將領生平欄位補跑費用估算（{out['generatedAt']}）", "",
     "依 ARCHITECTURE §20 欄位補跑方式；**只估算**，未補跑、未寫庫。由 `refill_estimate.py` 產生；輸入 `stats.json`（"
     + st["generatedAt"] + "）。所有比例為假設，見文末。", "",
     "## 人數", ""]
for t in ("S", "A"):
    m = out["minCheck"][t]
    L.append(f"- {t}：{m['rows']} 列，達標 {m['meets']}、未達標 {m['fail']}；扣已知重複 {m['knownDuplicatesPresent']} → {m['uniquePeople']} 人，達標 {m['uniqueMeets']}、未達標 {m['uniqueFail']}")
L += [f"- 未達標：{len(fail_rows)} 列／{len(fail)} 人（去重）。批次目錄的 min-check.json 是 retry 前結果，與重算不同者 {out['staleMinCheckJson']} 人。",
      f"- 從未寫出（selection 有、research.json 無）：{out['neverWritten']}（不在 358 內；整人首跑 低／中／高 ${never_cost[0]}／${never_cost[1]}／${never_cost[2]}，未計入下表）",
      f"- research.json key 與 selection 不同（以原文名／key 對上，已寫出，寫庫前需對應）：{key_mismatch}",
      f"- 段落缺 quote：0 段（1445 段、9017 筆 citation 皆有 quote）", "",
      "## 未達標原因（互斥組合，去重）", "", "| 組合 | 人數 |", "|---|---|"]
L += [f"| {k} | {v} |" for k, v in excl.most_common()]
L += ["", f"可重複計數：{dict(over)}；任期：{terms_people} 人、{terms_cnt}", "", "## 估算（USD）", ""]
for name, rows in res.items():
    L += [f"### {name}（{rows[0]['people']} 人）", "", "| 檔 | 任期 | 戰役 | 指揮職 | (a) L1/L2 小計 | L3 | 段落0 | (b) L3 小計 | 合計 | 累計後 | 距 $340 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r, c in zip(rows, caps[name]):
        bf = r["byField"]
        L.append(f"| {r['scenario']} | {bf['任期']} | {bf['戰役']} | {bf['指揮職']} | {r['a_L1L2']} | {bf['L3']} | {bf['段落0']} | {r['b_L3']} | **{r['total']}** | {c['after']} | {c['headroom']}{'（超過）' if c['exceeds340'] else ''} |")
    L.append("")
L += ["## 花費", "", f"- 已花：${out['spent']['total']}（`.dev/cc-generals-*.json` ${out['spent']['generalsGlob']}＋{out['spent']['personFacts']}；{len(spent_files)} 檔）", "",
      "## 假設", "",
      f"- 每人平均（主迴圈 sonnet＋retry，實測）：S ${AVG['S']}、A ${AVG['A']}。",
      "- 各欄位相對成本（低／中／高）：" + "；".join(f"{k} {v[0]}／{v[1]}／{v[2]}" for k, v in ASSUME["unit"].items()) + "（沿用 §20.10.1）。",
      f"- 同一人多種缺欄：最貴那項全額，其餘 ×{ASSUME['secondary']}；有 L3 缺口者，任期／戰役／指揮職以 ×{ASSUME['secondary']} 計入 (a)。0 段者整人重跑，不另計其他欄位。",
      f"- 重抓：比例 低／中／高 = {ASSUME['refetch_rate']}，倍數 = 1＋{ASSUME['refetch_penalty']}×比例（{mult(0)}／{mult(1)}／{mult(2):.1f}）。",
      f"- /tmp 原文快取：S {cache['S']}/{batches['S']}、A {cache['A']}/{batches['A']} 批的 raw 目錄仍在（估算時）；/tmp 在 macOS 重開機後可能被清，若清除應取高檔。",
      "- 戰役指揮官：repo 內沒有可靠的人物層戰役指揮官名單（data/seed/battles 只有 Dunkirk 1940、無人物欄；§20.8）。改用**代理**：P1＝有 military_command 職位且正文提到戰役；P2＝有 military_command 職位。",
      "- 未計：Opus 審查、補登（20.4，只讀檔）、L1 典據查詢、從未寫出的 1 人（另列）。"]
(HERE / "refill-estimate.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
