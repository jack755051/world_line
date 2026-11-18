#!/usr/bin/env python3
"""列出將領生平「來源不足／未達標」補跑名單（新規則：具名 C 級＋英語國家官方來源）。

依據：World Line 主管 2026-11-12 03:03、06:32；Tai 本人 2026-11-12 06:34（主管轉達）「將領生平來源放寬到具名 C 級」。
名單規則（不分國家，含英語國家）：
- S 級：全部「未達最低標準」或「已標來源不足」者，外加 selection.json 有、research.json 卻沒有條目者（例：S/batch004 heinzguderian）。
- A 級：只取新規則生效**之前**跑的批次（batch < FIRST_NEW_RULES["A"]），條件同上；生效後的批次照主迴圈的批內重跑一次規則，不進本名單。
- 重複人物（DUPLICATES）只列保留的那一筆；合併由 patch_merge_duplicates.py 在補跑後執行。
判定一律用 check_min.check() 即時讀 research.json（不讀舊的 min-check 檔，補跑後重算才準）。
用法：
  python3 -I collect_insuff.py                # 摘要
  python3 -I collect_insuff.py --json         # 補跑腳本用（.dev/cc-generals-insuff-rerun.sh 在主迴圈結束後呼叫）
相容：collect(tier=..., include_english=...) 的舊參數保留但不再過濾（補跑腳本的 write_report 仍以舊參數呼叫）。
"""
import argparse, json, os, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_min import check  # noqa: E402

# 新提示檔 2026-11-12 06:38:04（Asia/Taipei）寫入、b853c06 06:39:20 commit；當時 A/batch011 重跑中（06:32:37 已渲染舊提示），
# 第一個用新提示的批次是 A/batch012。S 全部在舊規則下跑完。
FIRST_NEW_RULES = {"S": None, "A": os.environ.get("GENERALS_FIRST_NEW_RULES_A", "012")}
DUPLICATES = {"chesternimitz": "chesterwnimitz"}  # 丟棄 key → 保留 key（主管 2026-11-12 06:32）
ENGLISH = {"英國", "美国", "美國", "加拿大", "澳洲", "澳大利亞", "澳大利亚", "紐西蘭", "纽西兰", "新西蘭", "新西兰",
           "南非", "愛爾蘭", "爱尔兰", "英國-自治領"}


def is_english(country: str) -> bool:
    c = (country or "").strip()
    return any(c == e or c.startswith(e + "-") or c.startswith(e + "／") or c.startswith(e + "/") for e in ENGLISH)


def load_selection():
    return json.loads((HERE / "selection.json").read_text(encoding="utf-8"))


def pre_change(tier: str, batch: str) -> bool:
    cut = FIRST_NEW_RULES.get(tier)
    return cut is None or batch < cut


def collect(tier=None, include_english=None, tiers=("S", "A")):
    """tier／include_english 為舊參數，已不過濾。"""
    sel = load_selection()
    rows = []
    for t in tiers:
        for b in sel.get(t) or []:
            nn = b["batch"]
            if not pre_change(t, nn):
                continue
            d = HERE / t / f"batch{nn}"
            rj = d / "research.json"
            if not rj.exists():
                continue  # 尚未跑到的批次
            people = {p.get("key"): p for p in json.loads(rj.read_text(encoding="utf-8")).get("people") or []}
            for m in b.get("people") or []:
                key = m["key"]
                if key in DUPLICATES:
                    continue
                p = people.get(key)
                if p is None:
                    r = {"paragraphs": None, "zhChars": None, "termsFull": None, "terms": None,
                         "hasCommand": None, "hasBattle": None, "sourceInsufficient": None, "meetsMinimum": False}
                    reason = "missing_entry"
                else:
                    r = check(p)
                    if r["meetsMinimum"] and not r["sourceInsufficient"]:
                        continue
                    reason = "below_standard" if not r["meetsMinimum"] else "flagged_insufficient_but_meets"
                rows.append({
                    "tier": t, "batch": nn, "batch_dir": str(d),
                    "rel": f"data/seed/leaders/generals-roster/bios/{t}/batch{nn}",
                    "key": key, "name_zh": m.get("name_zh") or (p or {}).get("nameZh"),
                    "name_original": m.get("name_original") or "", "country": m.get("country") or "?",
                    "english": is_english(m.get("country") or ""), "branch": m.get("branch"),
                    "highest_rank": m.get("highest_rank"), "reason": reason,
                    "paragraphs": r["paragraphs"], "zhChars": r["zhChars"], "termsFull": r["termsFull"],
                    "terms": r["terms"], "hasCommand": r["hasCommand"], "hasBattle": r["hasBattle"],
                    "sourceInsufficient": r["sourceInsufficient"], "meetsMinimum": r["meetsMinimum"],
                })
    order = {"S": 0, "A": 1}
    rows.sort(key=lambda x: (order.get(x["tier"], 9), x["batch"]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true", help="舊參數，已無作用（一律含英語國家）")
    ap.add_argument("--tier", default=None, help="舊參數，已無作用（一律 S＋規則變更前的 A）")
    args = ap.parse_args()
    rows = collect()
    if args.json:
        json.dump({"count": len(rows), "rule": "S 全部未達標／來源不足／漏條目＋A 級 batch<%s 同條件；不分國家；重複只列保留者" % FIRST_NEW_RULES["A"],
                   "first_new_rules": FIRST_NEW_RULES, "duplicates": DUPLICATES, "people": rows},
                  sys.stdout, ensure_ascii=False, indent=1)
        sys.stdout.write("\n")
        return
    by = defaultdict(list)
    for r in rows:
        by[(r["tier"], r["country"])].append(r)
    cnt = defaultdict(int)
    for r in rows:
        cnt[(r["tier"], r["reason"])] += 1
    print(f"補跑名單 {len(rows)} 人（S 全部＋A 級 batch<{FIRST_NEW_RULES['A']}；含英語國家）：" + "、".join(f"{t}/{k} {v}" for (t, k), v in sorted(cnt.items())))
    for (t, c), items in sorted(by.items(), key=lambda x: (x[0][0] != "S", -len(x[1]), x[0][1])):
        print(f"\n{t}｜{c}：{len(items)} 人")
        for r in items:
            print(f"  {t}/batch{r['batch']} {r['name_zh']}（{r['name_original'] or r['key']}）[{r['reason']}]"
                  f"｜{r['paragraphs']}段/{r['zhChars']}字｜任期{r['termsFull']}/{r['terms']}"
                  f"｜指揮={r['hasCommand']} 戰役={r['hasBattle']}")


if __name__ == "__main__":
    main()
