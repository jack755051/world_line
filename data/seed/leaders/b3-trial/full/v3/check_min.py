#!/usr/bin/env python3
"""B3 full v3 最低標準檢查（Tai 2026-11-11 22:02）：中文 ≥3 段、合計 ≥300 字（NFC、去空白）、每筆 positions／roleCandidates 有起迄日。
迄日缺而有「待查證：缺迄日」gap 者算已標註（不算達標，計入 termsFlagged），verdict 寫「已標註缺迄日」，不要和「未達」混在一起。
未達標但有「篇幅不足：」gap（target=paragraph:length）者記 documentedShortfall，verdict 寫「篇幅不足」。
只有起迄日或引文仍缺、且沒有標成篇幅不足時，verdict 才是「未達」。
用法：python3 -I check_min.py <research.json> [--out <report.json>]
報告檔名固定為與 research.json 同目錄的 check_min-report.json。
--out 若指向 check-min.json 或 check-min-report.json，會改寫到上述固定檔名。
stdout 印摘要；永遠 exit 0（判定交給呼叫端讀 failingKeys）。
"""
import json, sys, unicodedata
from pathlib import Path

MIN_PARAS, MIN_CHARS = 3, 300
CANONICAL_NAME = "check_min-report.json"
ALIAS_NAMES = {"check-min.json", "check-min-report.json"}

def zh_len(s):
    return sum(1 for ch in unicodedata.normalize("NFC", s or "") if not ch.isspace())

def _gap_note(gnote, target, prefix):
    return any(t == target and n.startswith(prefix) for t, n in gnote)


def check(p):
    gaps = p.get("gaps") or []
    gnote = {(g.get("target"), (g.get("note") or "")) for g in gaps}
    paras = p.get("paragraphs") or []
    chars = sum(zh_len((g.get("body") or {}).get("zh-Hant")) for g in paras)
    items = [("position", x) for x in p.get("positions") or []] + [("role", x) for x in p.get("roleCandidates") or []]
    full = flagged = missing = 0
    open_terms = []
    for kind, x in items:
        per = x.get("period") or {}
        target = f"{kind}:{x.get('key')}"
        if per.get("start") and per.get("end"):
            full += 1
        elif per.get("start") and _gap_note(gnote, target, "待查證：缺迄日"):
            flagged += 1
        else:
            missing += 1
        if not per.get("start"):
            open_terms.append({"kind": kind, "key": x.get("key"), "missing": "start", "flagged": False})
        if not per.get("end"):
            open_terms.append({
                "kind": kind, "key": x.get("key"), "missing": "end",
                "flagged": bool(per.get("start")) and _gap_note(gnote, target, "待查證：缺迄日"),
            })
    short = any(t == "paragraph:length" and n.startswith("篇幅不足：") for t, n in gnote)
    ok = len(paras) >= MIN_PARAS and chars >= MIN_CHARS and missing == 0 and flagged == 0
    row = {"key": p["key"], "name": p.get("name"), "paragraphs": len(paras), "zhChars": chars, "terms": len(items),
            "termsFull": full, "termsFlagged": flagged, "termsMissing": missing,
            "termCoverage": round(full / len(items), 3) if items else None, "meetsMinimum": ok, "documentedShortfall": short and not ok,
            "startGapsInGaps": sum(1 for t, n in gnote if n.startswith("待查證：缺起日")),
            "openTerms": open_terms}
    row["verdict"] = verdict_of(row)
    return row


def verdict_of(row):
    """OK／篇幅不足／已標註缺迄日／未達。已標註缺迄日不是未達，呼叫端不要為此再整份重跑。"""
    if row.get("meetsMinimum"):
        return "OK"
    if row.get("documentedShortfall"):
        return "篇幅不足"
    length_ok = row.get("paragraphs", 0) >= MIN_PARAS and row.get("zhChars", 0) >= MIN_CHARS
    if length_ok and (row.get("termsMissing") or 0) == 0 and (row.get("termsFlagged") or 0) > 0:
        return "已標註缺迄日"
    return "未達"

def report_for(data):
    rows = [check(p) for p in data["people"]]
    return {"rule": f"zh paragraphs>={MIN_PARAS}, zh chars>={MIN_CHARS}, every position/role start+end", "people": rows,
            "failingKeys": [r["key"] for r in rows if not r["meetsMinimum"]]}


def render(rep):
    return json.dumps(rep, ensure_ascii=False, indent=1) + "\n"


def resolve_out(src, out_arg):
    """固定寫 check_min-report.json。別名檔名改指到同目錄的固定檔。"""
    sibling = Path(src).parent / CANONICAL_NAME
    if not out_arg:
        return sibling
    out = Path(out_arg)
    if out.name in ALIAS_NAMES:
        fixed = out.parent / CANONICAL_NAME
        sys.stderr.write(f"check_min: 報告檔名固定為 {fixed}（不寫 {out.name}）\n")
        return fixed
    if out.name != CANONICAL_NAME:
        sys.stderr.write(f"check_min: 批次報告請用 {CANONICAL_NAME}；這次依 --out 寫到 {out}\n")
    return out


def main():
    src = sys.argv[1]
    out_arg = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    with open(src, encoding="utf-8") as handle:
        d = json.load(handle)
    rep = report_for(d)
    out = resolve_out(src, out_arg)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(rep), encoding="utf-8")
    print(" ".join(
        f"{r['key']}:{r['paragraphs']}段/{r['zhChars']}字/任期{r['termsFull']}+{r['termsFlagged']}待查/{r['terms']}/{r['verdict']}"
        for r in rep["people"]
    ))

if __name__ == "__main__":
    main()
