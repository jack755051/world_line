#!/usr/bin/env python3
"""寫庫前段落人名校正（主管 2026-11-12 10:07 決定；Tai 2026-11-13 11:05 寫庫授權前置）。
- 對 nameZhUnsourced（模型音譯、無出處）已被索引名 nameZh 取代的人：把段落正文（zh-Hant 正文與標題）中的舊音譯換成現行 nameZh。
  只換「姓（最後一段）不同」或「全名不同且非只差爵位前綴／括號」者；姓相同者不動（例：凱斯、托維）。舊姓字串夠長（≥3 字）才在全部 S／A 段落替換，否則只換本人段落。
- nameZh 為「待查證」者（無索引名）不替換，列入報告（寫庫時 name_zh 留空）。
- 段落另只修正明確殘留的簡體字（萨兰温卧 → 薩蘭溫臥；日文書名的「国」不動）；不對全文套 s2t／t2tw（會把「准將」「游擊」等正確用字改錯）。
- 新名須通過 zh_trad.to_trad 恆等（台灣字形）。改動寫 sourceReplaceLog 式紀錄 person.nameFixLog。
用法（repo 根目錄）：python3 -I data/seed/leaders/generals-roster/bios/patch_para_names.py [--apply]
"""
import json, glob, sys, re, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from zh_trad import to_trad  # noqa: E402
sys.path.insert(0, str(HERE / "refill"))
from apply_refill import fmt_of, dump  # noqa: E402
APPLY = "--apply" in sys.argv
TODAY = datetime.datetime.now().astimezone().strftime("%Y-%m-%d")
SIMP = {"萨": "薩", "兰": "蘭", "温": "溫", "卧": "臥"}  # 不含「国」：日文書名（帝国、国際）照原文
files = sorted(HERE.glob("[SA]/batch*/research.json"))
docs = {f: (lambda raw: (fmt_of(raw), json.loads(raw)))(f.read_text(encoding="utf-8")) for f in files}
strip = lambda s: re.sub(r"（.*?）|^第.代.+?(男爵|子爵|伯爵|侯爵)", "", s)
rules, pending = [], []
for f, (_, d) in docs.items():
    for p in d["people"]:
        old, new = p.get("nameZhUnsourced"), p.get("nameZh")
        if not old:
            continue
        if not new or new == "待查證":
            pending.append((p["key"], old)); continue
        assert to_trad(new) == new, (p["key"], new)
        o, n = strip(old), strip(new)
        osn, nsn = o.split("·")[-1], n.split("·")[-1]
        if o != n and osn == nsn:
            rules.append((p["key"], o, n, "global" if len(o) >= 3 else "own"))
        if osn != nsn:
            rules.append((p["key"], osn, nsn, "global" if len(osn) >= 3 else "own"))
log = []
for f, (fmt, d) in docs.items():
    ch = False
    for p in d["people"]:
        for g in p["paragraphs"]:
            for fld in ("body", "heading"):
                obj = g.get(fld) or {}
                z = obj.get("zh-Hant")
                if not z:
                    continue
                z2 = z
                for key, o, n, scope in rules:
                    if scope == "own" and key != p["key"]:
                        continue
                    if o in z2 and n not in o:
                        z2 = z2.replace(o, n)
                    elif o in z2 and n in o:  # 新名是舊名子字串時避免重複套
                        z2 = re.sub(re.escape(o), n, z2)
                for a, b in SIMP.items():
                    z2 = z2.replace(a, b)
                if z2 != z:
                    log.append({"file": str(f.relative_to(HERE)), "person": p["key"], "ord": g["ord"], "field": fld, "before": z, "after": z2})
                    obj["zh-Hant"] = z2; ch = True
                    p.setdefault("nameFixLog", []).append({"on": TODAY, "ord": g["ord"], "field": fld, "rule": "主管 2026-11-12 10:07：段落模型音譯人名換成索引名／殘留簡體字", "by": "patch_para_names.py"})
    if ch and APPLY:
        f.write_text(dump(d, fmt), encoding="utf-8")
rep = {"generatedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "rules": rules, "pendingNoIndexName": pending, "changes": log, "applied": APPLY}
(HERE / "patch_para_names.report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({"rules": rules, "pending": pending, "changed_paragraph_fields": len(log), "applied": APPLY}, ensure_ascii=False))
for x in log:
    import difflib
    print(x["person"], x["ord"], [t for t in difflib.ndiff([x["before"]], [x["after"]]) if t[0] in "?"][:0] or "", x["before"][:0])
