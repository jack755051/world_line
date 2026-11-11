#!/usr/bin/env python3
"""B3 full v3 最低標準檢查（Tai 2026-11-11 22:02）：中文 ≥3 段、合計 ≥300 字（NFC、去空白）、每筆 positions／roleCandidates 有起迄日。
迄日缺而有「待查證：缺迄日」gap 者算已標註（不算達標，計入 termsFlagged）。未達標但有「篇幅不足：」gap（target=paragraph:length）者記 documentedShortfall。
用法：python3 -I check_min.py <research.json> --out <report.json>；stdout 印摘要；永遠 exit 0（判定交給呼叫端讀 failingKeys）。
"""
import json, sys, unicodedata

MIN_PARAS, MIN_CHARS = 3, 300

def zh_len(s):
    return sum(1 for ch in unicodedata.normalize("NFC", s or "") if not ch.isspace())

def check(p):
    gaps = p.get("gaps") or []
    gnote = {(g.get("target"), (g.get("note") or "")) for g in gaps}
    paras = p.get("paragraphs") or []
    chars = sum(zh_len((g.get("body") or {}).get("zh-Hant")) for g in paras)
    items = [("position", x) for x in p.get("positions") or []] + [("role", x) for x in p.get("roleCandidates") or []]
    full = flagged = missing = 0
    for kind, x in items:
        per = x.get("period") or {}
        if per.get("start") and per.get("end"):
            full += 1
        elif per.get("start") and any(t == f"{kind}:{x.get('key')}" and n.startswith("待查證：缺迄日") for t, n in gnote):
            flagged += 1
        else:
            missing += 1
    short = any(t == "paragraph:length" and n.startswith("篇幅不足：") for t, n in gnote)
    ok = len(paras) >= MIN_PARAS and chars >= MIN_CHARS and missing == 0 and flagged == 0
    return {"key": p["key"], "name": p.get("name"), "paragraphs": len(paras), "zhChars": chars, "terms": len(items),
            "termsFull": full, "termsFlagged": flagged, "termsMissing": missing,
            "termCoverage": round(full / len(items), 3) if items else None, "meetsMinimum": ok, "documentedShortfall": short and not ok,
            "startGapsInGaps": sum(1 for t, n in gnote if n.startswith("待查證：缺起日"))}

def main():
    src = sys.argv[1]; out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    d = json.load(open(src, encoding="utf-8"))
    rows = [check(p) for p in d["people"]]
    rep = {"rule": f"zh paragraphs>={MIN_PARAS}, zh chars>={MIN_CHARS}, every position/role start+end", "people": rows,
           "failingKeys": [r["key"] for r in rows if not r["meetsMinimum"]]}
    if out:
        open(out, "w", encoding="utf-8").write(json.dumps(rep, ensure_ascii=False, indent=1) + "\n")
    print(" ".join(f"{r['key']}:{r['paragraphs']}段/{r['zhChars']}字/任期{r['termsFull']}+{r['termsFlagged']}待查/{r['terms']}{'/OK' if r['meetsMinimum'] else ('/篇幅不足' if r['documentedShortfall'] else '/未達')}" for r in rows))

if __name__ == "__main__":
    main()
