#!/usr/bin/env python3
"""generals.dk 替換報告 → ../GENDK_REPLACE_REPORT.md（Tai 2026-11-13 10:32）。唯讀：比對替換前 commit（BASE）與現行 research.json。
用法（repo 根目錄）：python3 -I data/seed/leaders/generals-roster/bios/refill/gendk_replace_report.py
"""
import json, subprocess, datetime
from pathlib import Path
from urllib.parse import urlparse
HERE = Path(__file__).resolve().parent; BIOS = HERE.parent; REPO = HERE.parents[5]; DEV = REPO / ".dev"
BASE = "3d645c6"  # 替換前（REFILL_REPORT commit）
RUN_ID = "gendk-replace-2026-11-13"
BATCHES = ["A/019", "A/038", "A/042", "A/049", "S/004", "S/007", "S/011"]
SOLE = [("markwclark", "clark-ii-corps"), ("markwclark", "clark-15th-army-group"),
        ("maxwelldtaylor", "taylor-82nd-artillery"), ("maxwelldtaylor", "taylor-101st-first"), ("maxwelldtaylor", "taylor-101st-second"), ("maxwelldtaylor", "taylor-west-point"),
        ("matthewridgway", "ridgway-82nd-infantry-adc"), ("matthewridgway", "ridgway-82nd-airborne"), ("matthewridgway", "ridgway-xviii-corps"),
        ("erikheinrichs", "heinrichs-iii-corps"), ("henriwinkelman", "winkelman-4div"),
        ("heinzguderian", "guderian-xix-korps"), ("heinzguderian", "guderian-panzergruppe-2"), ("heinzguderian", "guderian-2-panzerarmee")]


def gd(s):
    return any(((urlparse(u).hostname or "") if u else "").lower().endswith("generals.dk") for u in ((s or {}).get("url"), (s or {}).get("archive_url")))


def load(tb, base=False):
    t, nn = tb.split("/"); rel = f"data/seed/leaders/generals-roster/bios/{t}/batch{nn}/research.json"
    return json.loads(subprocess.run(["git", "show", f"{BASE}:{rel}"], capture_output=True, text=True, cwd=REPO).stdout) if base else json.loads((REPO / rel).read_text())


def per(x):
    p = x.get("period") or {}
    return f"{p.get('start') or '—'}（{x.get('startPrecision') or '—'}）～{p.get('end') or '—'}（{x.get('endPrecision') or '—'}）"


def cits(p0, p1, sec, key, bad0):
    o = {(c["sourceKey"], c["quote"]) for x in p0.get(sec) or [] if (x.get("key") if sec != "paragraphs" else x.get("ord")) == key for c in x.get("citations") or []}
    n = [c for x in p1.get(sec) or [] if (x.get("key") if sec != "paragraphs" else x.get("ord")) == key for c in x.get("citations") or []]
    return [c for c in n if (c["sourceKey"], c["quote"]) not in o]


L = [f"# generals.dk 引用替換報告（{datetime.datetime.now().astimezone().isoformat(timespec='seconds')}）", "",
     "決定：Tai 2026-11-13 10:32（World Line 主管轉達）先替換 generals.dk，寫庫另問 Tai。禁用依據：主管 2026-11-12 22:08（個人網站）。",
     "規則：只換來源（A／B／具名 C）；查無合格來源者標「待查證」；新來源與既有職稱／任期不同時以新來源為準；未寫庫、未 push、未改 schema。",
     f"工具：`refill/patch_replace_gendk.py`（套用）、`refill/PROMPT_gendk_replace.md`／`PROMPT_gendk_audit.md`（claude -p Sonnet 兩輪）；基準 commit {BASE}。", ""]
data, base = {tb: load(tb) for tb in BATCHES}, {tb: load(tb, True) for tb in BATCHES}
people = {}
for tb in BATCHES:
    bad0 = {k for k, s in base[tb]["sources"].items() if gd(s)}
    b1 = {p["key"]: p for p in data[tb]["people"]}
    for p0 in base[tb]["people"]:
        n = sum(1 for sec in ("paragraphs", "positions", "roleCandidates") for x in p0.get(sec) or [] for c in x.get("citations") or [] if c.get("sourceKey") in bad0)
        g = sum(1 for x in p0.get("gaps") or [] for c in x.get("candidateCitations") or [] if c.get("sourceKey") in bad0)
        if n or g:
            people[p0["key"]] = (tb, p0, b1[p0["key"]], n, g, bad0, data[tb]["sources"])
L += ["## 一、只靠 generals.dk 支撐的 14 個職位", "", "| # | 人 | 職位 key | 職稱 | 現行期間（精度） | 新出處（key／網域／grade） | 職稱／任期差異 |", "|---|---|---|---|---|---|---|"]
for i, (pk, key) in enumerate(SOLE, 1):
    tb, p0, p1, n, g, bad0, srcs = people[pk]
    x1 = next((x for x in p1.get("positions") or [] if x.get("key") == key), None)
    x0 = next(x for x in p0.get("positions") or [] if x.get("key") == key)
    new = cits(p0, p1, "positions", key, bad0) if x1 else []
    nc = "；".join(f"{c['sourceKey']}／{urlparse(srcs[c['sourceKey']].get('url') or '').hostname}／{c['grade']}" for c in new) or "—"
    logs = [lg for lg in p1.get("sourceReplaceLog") or [] if lg.get("item") == key]
    diff = "；".join(f"{f}：{json.dumps(v['before'], ensure_ascii=False)}→{json.dumps(v['after'], ensure_ascii=False)}" for lg in logs for f, v in lg["changes"].items()) or "無"
    gaps = [g_["note"] for g_ in p1.get("gaps") or [] if g_.get("target") == f"position:{key}" and g_.get("by") == RUN_ID]
    L.append(f"| {i} | {pk} | {key} | {(x0.get('title') or {}).get('zh-Hant')} | {per(x1) if x1 else '（移出）'}{'；' + '、'.join(gaps) if gaps else ''} | {nc} | {diff} |")
L += ["", "## 二、各人 generals.dk 引用處理（移除＝刪除 generals.dk citation；新增＝本次加上的替代 citation）", "",
      "| 層／批 | 人 | 原 generals.dk 引用 | gap 候選引文 | 本次新增 citation | 改值項數 | 新增待查證 gap |", "|---|---|---|---|---|---|---|"]
for pk, (tb, p0, p1, n, g, bad0, srcs) in people.items():
    add = sum(len(cits(p0, p1, sec, (x.get("key") if sec != "paragraphs" else x.get("ord")), bad0)) for sec in ("paragraphs", "positions") for x in p1.get(sec) or [])
    L.append(f"| {tb} | {pk} | {n} 筆全移除 | {g} | {add} | {len(p1.get('sourceReplaceLog') or [])} | {sum(1 for g_ in p1.get('gaps') or [] if g_.get('by') == RUN_ID)} |")
L += ["", "## 三、所有改值（新來源為準／降精度／刪去失去來源的句子）", ""]
for pk, (tb, p0, p1, *_r) in people.items():
    for lg in p1.get("sourceReplaceLog") or []:
        ch = "；".join(f"{f}：{json.dumps(v['before'], ensure_ascii=False)[:160]} → {json.dumps(v['after'], ensure_ascii=False)[:160]}" for f, v in lg["changes"].items())
        L.append(f"- {tb} {pk} {lg['section']}:{lg['item']}（依據 {lg.get('basis') or '—'}）：{lg.get('diff')}｜{ch}")
L += ["", "## 四、仍待查證", ""]
for pk, (tb, p0, p1, *_r) in people.items():
    for g_ in p1.get("gaps") or []:
        if g_.get("by") == RUN_ID:
            L.append(f"- {tb} {pk} {g_['target']}：{g_['note']}")
rem = 0; rem_p = set()
for f in sorted(BIOS.glob("[SA]/batch*/research.json")):
    d = json.loads(f.read_text()); bad = {k for k, s in d.get("sources", {}).items() if gd(s)}
    for p in d["people"]:
        for sec in ("paragraphs", "positions", "roleCandidates"):
            for x in p.get(sec) or []:
                for c in x.get("citations") or []:
                    if c.get("sourceKey") in bad:
                        rem += 1; rem_p.add(p["key"])
    rem += len(bad)
cost = {}
for g in ("g1", "g2", "g3", "a1", "a2"):
    try:
        cost[g] = float(json.loads((DEV / f"cc-gendk-replace-{g}.json").read_text()).get("total_cost_usd") or 0)
    except Exception:
        pass
L += ["", "另：S/batch003 有一筆未被引用、未評等的 generals.dk 來源 `generalsdk-rundstedt`（無 citation），以同一 patch 移除。", "", "## 五、結果", "", f"- 全部 S／A research.json 剩餘 generals.dk 引用＋來源：{rem}（人：{len(rem_p)}）。",
      f"- 本任務花費 ${sum(cost.values()):.4f}（{', '.join(f'{k} ${v:.4f}' for k, v in cost.items())}；上限 $10）。", ""]
(BIOS / "GENDK_REPLACE_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("remaining", rem, len(rem_p), "cost", round(sum(cost.values()), 4))
