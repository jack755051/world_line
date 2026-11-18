#!/usr/bin/env python3
"""把研究檔的 people[].key 對回 selection.json 的 key（冪等）。World Line 主管 2026-11-12 21:43（Tai 21:43 授權補跑前置）。
A/batch022 研究時用了短 key（yamaguchi、yamagata、shimada、kimura、matsui），與 selection 不同；對應依原文名（name == name_original）＋短 key 為 selection key 子字串雙重確認。
只改 people[].key（原值存 keyOrig）與同目錄 min-check*.json 的 key；之後重跑 verify.py 產生 verify-report.json。保留原檔 JSON 格式。
用法（repo 根目錄）：python3 -I data/seed/leaders/generals-roster/bios/patch_map_keys.py [--dry-run]
"""
import json, sys, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent
VERIFY = HERE.parent.parent / "b3-trial" / "verify.py"
MAPS = {("A", "022"): {"yamaguchi": "tamonyamaguchi", "yamagata": "yamagataaritomo", "shimada": "shigetaroshimada",
                       "kimura": "heitarokimura", "matsui": "iwanematsui"}}
DRY = "--dry-run" in sys.argv

def fmt_of(raw):
    d = json.loads(raw)
    for ind in (1, 2, None):
        for ea in (False, True):
            if json.dumps(d, ensure_ascii=ea, indent=ind) == raw.rstrip("\n"):
                return ind, ea, raw.endswith("\n")
    return 1, False, raw.endswith("\n")

def dump(d, f):
    return json.dumps(d, ensure_ascii=f[1], indent=f[0]) + ("\n" if f[2] else "")

sel = json.loads((HERE / "selection.json").read_text(encoding="utf-8"))
out = []
for (tier, nn), m in MAPS.items():
    b = next(x for x in sel[tier] if x["batch"] == nn)
    byk = {q["key"]: q for q in b["people"]}
    bd = HERE / tier / f"batch{nn}"
    rj = bd / "research.json"; raw = rj.read_text(encoding="utf-8"); f = fmt_of(raw); d = json.loads(raw)
    for p in d["people"]:
        new = m.get(p["key"])
        if not new:
            continue
        q = byk[new]
        assert (p.get("name") or "").casefold() == (q.get("name_original") or "").casefold()
        assert p["key"] in new, (p["key"], new)
        out.append({"file": str(rj.relative_to(HERE)), "old": p["key"], "new": new, "name": p.get("name"), "sel_name": q.get("name_original")})
        p.setdefault("keyOrig", p["key"]); p["key"] = new
    if not DRY:
        rj.write_text(dump(d, f), encoding="utf-8")
        for mc in sorted(bd.glob("min-check*.json")):
            r = mc.read_text(encoding="utf-8"); g = fmt_of(r); x = json.loads(r)
            for row in x.get("people") or []:
                row["key"] = m.get(row["key"], row["key"])
            for k in ("failingKeys", "sourceInsufficientKeys"):
                if k in x: x[k] = [m.get(v, v) for v in x[k]]
            mc.write_text(dump(x, g), encoding="utf-8")
        v = subprocess.run([sys.executable, "-I", str(VERIFY), str(rj), "--report", str(bd / "verify-report.json")], capture_output=True, text=True)
        out.append({"verify_rc": v.returncode})
print(json.dumps(out, ensure_ascii=False, indent=1))
