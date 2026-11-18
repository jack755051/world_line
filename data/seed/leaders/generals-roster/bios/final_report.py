#!/usr/bin/env python3
"""Final report after S+A biography loop."""
import json, collections, datetime, pathlib, sys, subprocess, unicodedata, re
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TZ = datetime.timezone(datetime.timedelta(hours=8))

def zh_len(s):
    return sum(1 for ch in unicodedata.normalize("NFC", s or "") if not ch.isspace())

def bodies(p):
    out = []
    for g in p.get("paragraphs") or []:
        b = g.get("body") or {}
        out.append(b.get("zh-Hant") or b.get("zh") or "")
    return out

def load_tier(tier):
    people = []
    for d in sorted((HERE/tier).glob("batch*")):
        f = d/"research.json"
        if not f.exists(): continue
        data = json.loads(f.read_text(encoding="utf-8"))
        for p in data.get("people") or []:
            people.append((tier, d.name, p))
    return people

def costs():
    tot, files = 0.0, []
    for p in sorted((ROOT/".dev").glob("cc-generals-*.json")):
        try:
            c = json.loads(p.read_text(errors="replace")).get("total_cost_usd")
            if c is not None:
                tot += float(c)
                files.append((p.name, float(c)))
        except Exception:
            pass
    return tot, files

def commits():
    try:
        out = subprocess.check_output(
            ["git","-C",str(ROOT),"log","--oneline","--","data/seed/leaders/generals-roster/"],
            text=True)
        return [ln for ln in out.splitlines() if ln][:80]
    except Exception:
        return []

def main():
    sys.path.insert(0, str(HERE))
    from check_min import check
    rows = []
    for tier, batch, p in load_tier("S")+load_tier("A"):
        r = check(p)
        r.update(tier=tier, batch=batch, nameZh=p.get("nameZh") or p.get("name"))
        rows.append(r)
    skipped = json.loads((HERE/"selection.json").read_text())["skippedA"]
    tot, costfiles = costs()
    now = datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S+08:00")
    by = collections.Counter(r["tier"] for r in rows)
    insuff = [r for r in rows if r["sourceInsufficient"]]
    fail = [r for r in rows if not r["meetsMinimum"]]
    paras = [r["paragraphs"] for r in rows]
    chars = [r["zhChars"] for r in rows]
    L=[]
    A=L.append
    A("# 將領 S＋A 生平總報告\n")
    A(f"產出時間：{now}（Asia/Taipei）。\n")
    A("## 人數與花費\n")
    A(f"- 完成：S {by['S']} 人、A {by['A']} 人，合計 {len(rows)} 人（A 級另跳過已在 leader_bios 者 {len(skipped)} 人）。")
    A(f"- 累計花費（含名單階段 `.dev/cc-generals-*.json` 的 total_cost_usd）：**${tot:.4f}**。")
    A("\n成本檔：")
    for n,c in costfiles:
        A(f"- `{n}`：${c:.4f}")
    A("\n## 段數分布\n")
    if paras:
        ctr=collections.Counter(paras)
        A("、".join(f"{k} 段：{ctr[k]} 人" for k in sorted(ctr)) + f"。平均 {sum(paras)/len(paras):.1f}。")
    A("\n## 字數分布\n")
    if chars:
        buckets=collections.Counter()
        for n in chars:
            buckets["<300" if n<300 else "300–399" if n<400 else "400–599" if n<600 else "600–799" if n<800 else "≥800"] += 1
        A("、".join(f"{k} {buckets[k]} 人" for k in ["<300","300–399","400–599","600–799","≥800"] if buckets[k]))
        A(f"平均 {sum(chars)/len(chars):.0f}；最低 {min(chars)}、最高 {max(chars)}。")
    A("\n## 「來源不足」名單\n")
    if not insuff:
        A("無。")
    else:
        A("| 級 | 批次 | key | 姓名 | 段數 | 字數 |\n|---|---|---|---|---|---|")
        for r in insuff:
            A(f"| {r['tier']} | {r['batch']} | {r['key']} | {r['nameZh']} | {r['paragraphs']} | {r['zhChars']} |")
    A("\n## 仍未達標且未標來源不足\n")
    left=[r for r in fail if not r["sourceInsufficient"]]
    if not left:
        A("無。")
    else:
        A("| 級 | 批次 | key | 姓名 | 段數 | 字數 |\n|---|---|---|---|---|---|")
        for r in left:
            A(f"| {r['tier']} | {r['batch']} | {r['key']} | {r['nameZh']} | {r['paragraphs']} | {r['zhChars']} |")
    A("\n## 跳過的 A 級（已在 leader_bios）\n")
    A(f"見 `data/seed/leaders/generals-roster/bios/A/skipped.md`，共 {len(skipped)} 人：")
    for p in skipped:
        A(f"- {p['name_zh']}（{p.get('name_original') or '—'}），bio_id={p.get('bio_id')}")
    A("\n## Commit 列表（generals-roster 路徑）\n")
    for ln in commits():
        A(f"- `{ln}`")
    A(f"\n達標 {sum(1 for r in rows if r['meetsMinimum'])}／{len(rows)}。不寫庫、不 push。\n")
    (HERE/"FINAL_REPORT.md").write_text("\n".join(L)+"\n", encoding="utf-8")
    print(f"final report cost=${tot:.4f} S={by['S']} A={by['A']} insuff={len(insuff)}")

if __name__ == "__main__":
    main()
