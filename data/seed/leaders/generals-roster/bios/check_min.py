#!/usr/bin/env python3
"""將領生平 v3 最低標準：中文 ≥3 段、≥300 字；每個職位／角色有起迄日；須有指揮職與主要戰役（或已標「來源不足」）。
用法：python3 -I check_min.py <research.json> --out <report.json>；永遠 exit 0。
"""
import json, sys, unicodedata, re

MIN_PARAS, MIN_CHARS = 3, 300
BATTLE_RE = re.compile(r"戰役|會戰|海戰|空戰|圍攻|登陸|進攻|戰役名|battle|offensive|campaign|siege", re.I)

def zh_len(s):
    return sum(1 for ch in unicodedata.normalize("NFC", s or "") if not ch.isspace())

def bodies(p):
    texts = []
    for g in p.get("paragraphs") or []:
        b = (g.get("body") or {})
        texts.append(b.get("zh-Hant") or b.get("zh") or "")
    return texts

def has_command(p):
    for x in p.get("positions") or []:
        if (x.get("positionKind") or "") == "military_command":
            return True
    for x in p.get("roleCandidates") or []:
        if (x.get("role_kind") or "") == "military_commander":
            return True
    if p.get("majorCommands"):
        return True
    return False

def has_battle(p):
    if p.get("majorBattles"):
        return True
    return any(BATTLE_RE.search(t) for t in bodies(p))

def insuff(p):
    for g in p.get("gaps") or []:
        n = g.get("note") or ""
        if n.startswith("來源不足") or n.startswith("篇幅不足："):
            return True
    return bool(p.get("sourceInsufficient"))

def check(p):
    gaps = p.get("gaps") or []
    gnote = {(g.get("target"), (g.get("note") or "")) for g in gaps}
    paras = p.get("paragraphs") or []
    chars = sum(zh_len(t) for t in bodies(p))
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
    cmd, bat = has_command(p), has_battle(p)
    documented = insuff(p)
    ok = (len(paras) >= MIN_PARAS and chars >= MIN_CHARS and missing == 0 and flagged == 0 and cmd and bat)
    return {"key": p.get("key"), "name": p.get("name") or p.get("nameZh"),
            "paragraphs": len(paras), "zhChars": chars, "terms": len(items),
            "termsFull": full, "termsFlagged": flagged, "termsMissing": missing,
            "hasCommand": cmd, "hasBattle": bat, "sourceInsufficient": documented,
            "meetsMinimum": ok,
            "documentedShortfall": documented and not ok}

def main():
    src = sys.argv[1]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    d = json.load(open(src, encoding="utf-8"))
    rows = [check(p) for p in d.get("people") or []]
    # 已標來源不足者不列入 failingKeys（不再重跑、不硬湊）
    failing = [r["key"] for r in rows if not r["meetsMinimum"] and not r["sourceInsufficient"]]
    insuff_keys = [r["key"] for r in rows if r["sourceInsufficient"]]
    rep = {"rule": "zh paragraphs>=3, zh chars>=300, every position/role start+end, command+battle (or 來源不足)",
           "people": rows, "failingKeys": failing, "sourceInsufficientKeys": insuff_keys}
    if out:
        open(out, "w", encoding="utf-8").write(json.dumps(rep, ensure_ascii=False, indent=1) + "\n")
    bits = []
    for r in rows:
        flag = "/OK" if r["meetsMinimum"] else ("/來源不足" if r["sourceInsufficient"] else "/未達")
        bits.append(f"{r['key']}:{r['paragraphs']}段/{r['zhChars']}字/任期{r['termsFull']}+{r['termsFlagged']}待查/{r['terms']}{'/有指揮' if r['hasCommand'] else '/無指揮'}{'/有戰役' if r['hasBattle'] else '/無戰役'}{flag}")
    print(" ".join(bits) if bits else "(no people)")

if __name__ == "__main__":
    main()
