#!/usr/bin/env python3
"""From roster.json, build S/A batch selection (5 per batch). Skip A-tier already in leader_bios."""
import json, datetime, pathlib, re, unicodedata
HERE = pathlib.Path(__file__).resolve().parent
ROSTER = HERE.parent / "roster.json"
TZ = datetime.timezone(datetime.timedelta(hours=8))
COUNTRY_ORDER = [
    "德國", "英國", "法國", "義大利", "美國", "日本",
    "中華民國-北洋", "中華民國-國民政府", "中國共產黨",
    "俄羅斯帝國", "蘇聯", "奧匈帝國", "鄂圖曼帝國", "土耳其",
    "波蘭", "羅馬尼亞", "芬蘭", "加拿大", "澳洲", "紐西蘭",
    "希臘", "荷蘭", "南斯拉夫", "捷克斯洛伐克", "南非", "泰國",
]
def slug(p):
    s = p.get("name_original") or p.get("name_zh") or "unknown"
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if c.isalnum() or c in "-_")
    return (s[:60] or "unknown").lower()
def sort_key(p):
    c = p.get("country") or ""
    try:
        ci = COUNTRY_ORDER.index(c)
    except ValueError:
        ci = 1000
    return (ci, c, p.get("name_zh") or "", p.get("name_original") or "")
def chunks(xs, n=5):
    for i in range(0, len(xs), n):
        yield xs[i:i+n]
def rec(p, key):
    return {
        "key": key,
        "name_zh": p.get("name_zh") or "待查證",
        "name_original": p.get("name_original"),
        "bio_id": p.get("bio_id"),
        "country": p.get("country"),
        "regime": p.get("regime"),
        "branch": p.get("branch"),
        "highest_rank": p.get("highest_rank"),
        "war": p.get("war"),
        "fame_tier": p.get("fame_tier"),
        "in_leader_bios": bool(p.get("in_leader_bios")),
        "index_url": p.get("index_url"),
    }
def main():
    people = json.loads(ROSTER.read_text())["people"]
    S = sorted([p for p in people if p["fame_tier"] == "S"], key=sort_key)
    A_all = sorted([p for p in people if p["fame_tier"] == "A"], key=sort_key)
    skipped = [p for p in A_all if p.get("in_leader_bios")]
    A = [p for p in A_all if not p.get("in_leader_bios")]
    used = set()
    def keys_for(xs):
        out = []
        for p in xs:
            k, i = slug(p), 2
            base = k
            while k in used:
                k = f"{base}{i}"; i += 1
            used.add(k)
            out.append(rec(p, k))
        return out
    S_r, A_r, sk_r = keys_for(S), keys_for(A), keys_for(skipped)
    def batches(rows, tier):
        bs = []
        for i, ch in enumerate(chunks(rows, 5), 1):
            nn = f"{i:03d}"
            bs.append({
                "batch": nn,
                "tier": tier,
                "dir": f"data/seed/leaders/generals-roster/bios/{tier}/batch{nn}",
                "people": ch,
            })
        return bs
    sel = {
        "generatedOn": datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S+08:00"),
        "sourceRoster": "data/seed/leaders/generals-roster/roster.json",
        "rule": "S 級全部（含已在 leader_bios 者做新版）；A 級跳過已在 leader_bios 者",
        "counts": {
            "S": len(S_r), "A_run": len(A_r), "A_skipped": len(sk_r),
            "S_batches": (len(S_r)+4)//5, "A_batches": (len(A_r)+4)//5,
            "total_run": len(S_r)+len(A_r),
        },
        "S": batches(S_r, "S"),
        "A": batches(A_r, "A"),
        "skippedA": sk_r,
    }
    (HERE/"selection.json").write_text(json.dumps(sel, ensure_ascii=False, indent=1)+"\n", encoding="utf-8")
    lines = ["# A 級已在 leader_bios、本輪跳過\n", f"產生時間：{sel['generatedOn']}（Asia/Taipei）。共 {len(sk_r)} 人。\n",
             "| 中文名 | 原名 | bio_id | 國家／政權 | 軍種 | 最高軍階 |\n|---|---|---|---|---|---|"]
    for p in sk_r:
        lines.append(f"| {p['name_zh']} | {p['name_original'] or '—'} | {p['bio_id'] or '—'} | {p['country']} | {p['branch']} | {p['highest_rank']} |")
    (HERE/"A").mkdir(exist_ok=True)
    (HERE/"A"/"skipped.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"S {len(S_r)} in {sel['counts']['S_batches']} batches; A run {len(A_r)} in {sel['counts']['A_batches']} batches; A skipped {len(sk_r)}")
if __name__ == "__main__":
    main()
