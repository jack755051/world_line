#!/usr/bin/env python3
"""只補缺欄位補跑的總報告 → ../REFILL_REPORT.md（唯讀 research.json；讀 .dev/cc-person-refill.state.json 與成本檔）。
用法（repo 根目錄）：python3 -I data/seed/leaders/generals-roster/bios/refill/final_refill_report.py
"""
import json, sys, glob, datetime, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent
BIOS = HERE.parent
REPO = HERE.parents[5]
sys.path.insert(0, str(BIOS))
from check_min import check  # noqa: E402
DEV = REPO / ".dev"
st = json.loads((DEV / "cc-person-refill.state.json").read_text(encoding="utf-8"))
cf = {}
for pat in ("cc-generals-*.json", "cc-person-facts-*.json", "cc-person-refill-*.json"):
    for p in DEV.glob(pat):
        try:
            c = json.loads(p.read_text(errors="replace")).get("total_cost_usd")
        except Exception:
            c = None
        if c is not None:
            cf[p.name] = float(c)
tot = sum(cf.values()); rf = sum(v for k, v in cf.items() if k.startswith("cc-person-refill-"))
cur = {}
cnt = {"S": [0, 0], "A": [0, 0]}
for f in sorted(BIOS.glob("[SA]/batch*/research.json")):
    t = f.parent.parent.name
    for p in json.loads(f.read_text(encoding="utf-8"))["people"]:
        r = check(p); cur[(t, f.parent.name[5:], p["key"])] = (r, p)
        cnt[t][0] += 1; cnt[t][1] += r["meetsMinimum"]

def missing(r):
    if r is None:
        return ["首跑（新人）"]
    m = []
    if r["termsMissing"] or r["termsFlagged"]: m.append(f"任期（缺 {r['termsMissing'] + r['termsFlagged']}）")
    if not r["hasBattle"]: m.append("戰役")
    if not r["hasCommand"]: m.append("指揮職")
    if r["paragraphs"] < 3 or r["zhChars"] < 300: m.append(f"L3（{r['paragraphs']} 段／{r['zhChars']} 字）")
    return m

L = [f"# 將領生平「只補缺欄位」總報告（{datetime.datetime.now().astimezone().isoformat(timespec='seconds')}）", "",
     "授權：Tai 2026-11-12 21:43（World Line 主管轉達）。依 ARCHITECTURE §20 只補缺欄位；不寫庫、不 push、不改 schema。", "",
     "## 達標數（check_min 對現行 research.json 重算）", ""]
for t in ("S", "A"):
    L.append(f"- {t}：{cnt[t][1]}／{cnt[t][0]}")
L.append(f"- 合計：{cnt['S'][1] + cnt['A'][1]}／{cnt['S'][0] + cnt['A'][0]}")
bs = st.get("batches") or {}
L += ["", "## 批次", "", f"- 計畫 {len(st.get('plan') or [])} 批；已 commit {sum(1 for v in bs.values() if v.get('status') == 'committed')}；"
      f"失敗 {sum(1 for v in bs.values() if v.get('status') == 'failed')}；其他 {sum(1 for v in bs.values() if v.get('status') not in ('committed', 'failed'))}", "",
      "| 批 | 狀態 | commit | 成本 | 分 |", "|---|---|---|---|---|"]
for b in st.get("plan") or []:
    v = bs.get(b["id"], {})
    L.append(f"| {b['id']} | {v.get('status', 'not_started')}{('（' + str(v.get('reason')) + '）') if v.get('reason') else ''} | {v.get('commit', '')} | {v.get('cost', '')} | {v.get('minutes', '')} |")
L += ["", "## 每人：補前缺欄 → 補後仍缺（仍缺＝待查證）", "", "| 批 | key | 補前缺 | 補後仍缺 | 補後達標 |", "|---|---|---|---|---|"]
filled_n = 0
for b in st.get("plan") or []:
    t, nn = b["id"].split("/")
    for p in b["people"]:
        now = cur.get((t, nn, p["key"]))
        after = missing(now[0]) if now else ["（research.json 無此人）"]
        ok = bool(now and now[0]["meetsMinimum"])
        filled_n += ok
        L.append(f"| {b['id']} | {p['key']} | {'、'.join(p['missing'])} | {'、'.join(after) or '—'} | {'✓' if ok else ''} |")
L += ["", f"計畫內 {sum(len(b['people']) for b in st.get('plan') or [])} 人，補後達標 {filled_n} 人。", ""]

# ── generals.dk 禁用（主管 2026-11-12 22:08，個人網站）：報告時計算，不改 research.json ──
from urllib.parse import urlparse  # noqa: E402
BANNED = ("generals.dk",)


def _banned(src):
    for u in ((src or {}).get("url"), (src or {}).get("archive_url")):
        h = ((urlparse(u).hostname or "") if u else "").lower()
        if any(h == b or h.endswith("." + b) for b in BANNED):
            return True
    return False


def gendk_scan():
    """回傳 [(tier, batch, key, nameZh, 引用數, 來源鍵, [待替換欄位])]（所有 S/A research.json）。"""
    out = []
    for f in sorted(BIOS.glob("[SA]/batch*/research.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        bad = {k for k, s in (d.get("sources") or {}).items() if _banned(s)}
        if not bad:
            continue
        for p in d["people"]:
            n = 0; keys = set(); only = []
            for kind, items in (("段落", p.get("paragraphs") or []), ("職務", p.get("positions") or [])):
                for i, it in enumerate(items):
                    cs = [c for c in (it.get("citations") or []) if isinstance(c, dict)]
                    hit = [c for c in cs if c.get("sourceKey") in bad]
                    n += len(hit); keys |= {c["sourceKey"] for c in hit}
                    if hit and len(hit) == len(cs):
                        lab = it.get("ord", i + 1) if kind == "段落" else ((it.get("title") or {}).get("zh-Hant") or it.get("key") or i + 1)
                        only.append(f"{kind} {lab}")
            if n:
                out.append((f.parent.parent.name, f.parent.name[5:], p["key"], p.get("nameZh") or "", n, sorted(keys), only))
    return out


gd = gendk_scan()
L += ["## generals.dk 引用（主管 2026-11-12 22:08 禁用：個人網站；既有引用暫不改，待替換）", "",
      f"- 涉及 {len(gd)} 人、{sum(x[4] for x in gd)} 筆引用；其中 {sum(1 for x in gd if x[6])} 人有「只靠 generals.dk 支撐」的欄位（下表「待替換」，報告時計算，未改資料）。",
      "- 生效後開跑的批次：verify.py／apply_refill.py 依來源 addedAt 擋新增；寫庫時 source-kind-overrides 為 null → DROP。", "",
      "| 層 | 批 | key | 中文名 | 引用數 | 來源鍵 | 待替換（只靠 generals.dk） |", "|---|---|---|---|---|---|---|"]
for t, nn, k, zh, n, ks, only in gd:
    L.append(f"| {t} | {nn} | {k} | {zh} | {n} | {'、'.join(ks)} | {'、'.join(map(str, only)) or '—'} |")
L += ["", "## 花費", "", f"- 專案總花費 ${tot:.4f}（補跑本身 ${rf:.4f}；起點 $205.94）；硬停 $330，補跑 >$100 暫停。", ""]
(BIOS / "REFILL_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"generals.dk people={len(gd)} citations={sum(x[4] for x in gd)} only_supported_people={sum(1 for x in gd if x[6])} fields={sum(len(x[6]) for x in gd)}")
print(f"REFILL_REPORT written: S {cnt['S'][1]}/{cnt['S'][0]} A {cnt['A'][1]}/{cnt['A'][0]} planned_met={filled_n} total={tot:.4f} refill={rf:.4f}")
