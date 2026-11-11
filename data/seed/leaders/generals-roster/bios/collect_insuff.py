#!/usr/bin/env python3
"""列出將領 S 級已標「來源不足」且未達最低標準的人。

預設只保留日本及其他非英語國家（英國、美國、加拿大、澳洲、紐西蘭、南非、愛爾蘭排除）。
用法：
  python3 -I collect_insuff.py
  python3 -I collect_insuff.py --json > insuff.json
  python3 -I collect_insuff.py --all
"""
import argparse, json, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGLISH = {
    "英國", "美国", "美國", "加拿大", "澳洲", "澳大利亞", "澳大利亚",
    "紐西蘭", "纽西兰", "新西蘭", "新西兰", "南非", "愛爾蘭", "爱尔兰",
    "英國-自治領",
}

def is_english(country: str) -> bool:
    c = (country or "").strip()
    if c in ENGLISH:
        return True
    for e in ENGLISH:
        if c == e or c.startswith(e + "-") or c.startswith(e + "／") or c.startswith(e + "/"):
            return True
    return False

def load_meta():
    sel = json.loads((HERE / "selection.json").read_text(encoding="utf-8"))
    meta = {}
    for tier in ("S", "A"):
        for b in sel.get(tier) or []:
            for p in b.get("people") or []:
                meta[p["key"]] = p
    return meta

def latest_check(batch_dir: Path):
    rounds = sorted(batch_dir.glob("min-check.round*.json"))
    if rounds:
        return rounds[-1]
    plain = batch_dir / "min-check.json"
    return plain if plain.exists() else None

def collect(tier="S", include_english=False):
    meta = load_meta()
    rows = []
    root = HERE / tier
    if not root.exists():
        return rows
    for d in sorted(root.glob("batch*")):
        check = latest_check(d)
        if not check:
            continue
        rep = json.loads(check.read_text(encoding="utf-8"))
        for p in rep.get("people") or []:
            if not p.get("sourceInsufficient"):
                continue
            if p.get("meetsMinimum"):
                continue
            m = meta.get(p["key"], {})
            country = m.get("country") or p.get("country") or "?"
            if not include_english and is_english(country):
                continue
            rows.append({
                "tier": tier,
                "batch": d.name.replace("batch", ""),
                "batch_dir": str(d),
                "rel": f"data/seed/leaders/generals-roster/bios/{tier}/{d.name}",
                "key": p["key"],
                "name_zh": m.get("name_zh") or p.get("name"),
                "name_original": m.get("name_original") or "",
                "country": country,
                "branch": m.get("branch"),
                "highest_rank": m.get("highest_rank"),
                "paragraphs": p.get("paragraphs"),
                "zhChars": p.get("zhChars"),
                "termsFull": p.get("termsFull"),
                "terms": p.get("terms"),
                "hasCommand": p.get("hasCommand"),
                "hasBattle": p.get("hasBattle"),
            })
    return rows

def group_by_batch(rows):
    g = defaultdict(list)
    for r in rows:
        g[(r["tier"], r["batch"])].append(r)
    return g

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true", help="含英語國家")
    ap.add_argument("--tier", default="S")
    args = ap.parse_args()
    rows = collect(tier=args.tier, include_english=args.all)
    if args.json:
        json.dump({"count": len(rows), "people": rows}, sys.stdout, ensure_ascii=False, indent=1)
        sys.stdout.write("\n")
        return
    by = defaultdict(list)
    for r in rows:
        by[r["country"]].append(r)
    print(f"來源不足（未達最低標準）{len(rows)} 人" + ("（含英語國家）" if args.all else "（日本＋其他非英語國家）"))
    for c, items in sorted(by.items(), key=lambda x: (-len(x[1]), x[0])):
        print(f"\n{c}：{len(items)} 人")
        for r in items:
            print(f"  {r['tier']}/batch{r['batch']} {r['name_zh']}（{r['name_original'] or r['key']}）"
                  f"｜{r['paragraphs']}段/{r['zhChars']}字｜任期{r['termsFull']}/{r['terms']}"
                  f"｜指揮={r['hasCommand']} 戰役={r['hasBattle']}")

if __name__ == "__main__":
    main()
