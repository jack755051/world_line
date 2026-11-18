"""待補清單：因引文全部來自禁用網域而未寫入開發庫的段落／任期／角色（主管 2026-11-13 11:31）。

禁用網域取自 b3-trial/full/domain-policy.json 中 source_kind=null 者（generals.dk 與 2026-11-13 判定的 10 個個人／無署名網域）。
判定與 write_generals_bios.py 一致：該列原有引文，但每一筆的來源網址都落在禁用網域 → 未寫入、列為待補。
只讀研究檔，不改資料、不連資料庫、不跑補查。

用法：python3 -I build_pending_banned.py   → 產出 pending-banned-domains-20261113.json／.md
"""
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
BIOS = HERE.parent
POLICY = BIOS.parents[1] / "b3-trial" / "full" / "domain-policy.json"
DUP_RETRACTED = {"williamdleahy", "何应钦", "孙立人", "陈诚"}  # 重複人物，bio 已軟撤回（patch_dup_bios.py）
OUT = HERE / "pending-banned-domains-20261113"
DECISION = "主管 2026-11-13 11:31：10 個個人／無署名網域比照 generals.dk 禁用；未寫入列待補，補查另行指派"


def main():
    banned = {x["domain"] for x in json.loads(POLICY.read_text()) if x["source_kind"] is None}
    written = {b["key"] for b in json.loads((BIOS / "bios-written-20261113.json").read_text())["new_bios"]}
    items, partial = [], Counter()
    for f in sorted(BIOS.glob("[SA]/batch*/research.json")):
        d = json.loads(f.read_text())
        host = lambda sk: (urlparse((d["sources"].get(sk) or {}).get("url") or "").hostname or "").lower()
        for p in d["people"]:
            if p["key"] in DUP_RETRACTED:
                continue
            for sec, rows, idf in (("paragraph", p.get("paragraphs") or [], "ord"), ("position", p.get("positions") or [], "key"),
                                   ("role", p.get("roleCandidates") or [], "key")):
                for x in rows:
                    cs = x.get("citations") or []
                    if not cs:
                        continue
                    if sec != "paragraph" and not (x.get("period") or {}).get("start"):
                        continue  # 缺起日者已轉待查證（gap），不在此清單
                    hs = [host(c.get("sourceKey")) for c in cs]
                    nb = [h for h in hs if h in banned]
                    if nb and len(nb) < len(hs):
                        partial[sec] += 1
                    if nb and len(nb) == len(hs):
                        items.append({"person": p["key"], "name": p.get("name"), "nameZh": p.get("nameZh"), "file": str(f.relative_to(BIOS)),
                                      "bioWritten": p["key"] in written, "kind": sec, "id": x[idf],
                                      "label": (x.get("heading") or x.get("title") or {}).get("zh-Hant") if isinstance(x.get("heading") or x.get("title"), dict) else None,
                                      "period": x.get("period"), "citations": len(cs), "droppedDomains": dict(Counter(nb)),
                                      "sourceKeys": sorted({c.get("sourceKey") for c in cs})})
    tot = Counter(i["kind"] for i in items)
    dom = Counter()
    for i in items:
        dom.update(i["droppedDomains"])
    per = defaultdict(lambda: Counter())
    for i in items:
        per[i["person"]][i["kind"]] += 1
    summary = {"decision": DECISION, "bannedDomains": sorted(banned), "items": dict(tot), "people": len(per),
               "citationsInItems": sum(i["citations"] for i in items), "byDomain": dict(dom.most_common()),
               "partiallyAffectedWritten": dict(partial), "status": "pending（未補查）"}
    OUT.with_suffix(".json").write_text(json.dumps({"summary": summary, "items": items}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    L = ["# 禁用網域待補清單（2026-11-13）", "", f"- 決定：{DECISION}",
         f"- 未寫入：段落 {tot['paragraph']}、任期 {tot['position']}、角色 {tot['role']}；涉及 {len(per)} 人；這些列原有引文 {summary['citationsInItems']} 筆，全數來自禁用網域",
         "- 各網域引文數：" + "、".join(f"{k} {v}" for k, v in dom.most_common()),
         f"- 另有部分引文來自禁用網域、但仍有其他來源而已寫入的列：{dict(partial)}（不列入待補）",
         "- 狀態：待補查，尚未指派；補查時只用 A／B／具名 C 來源", "",
         "| 人物 key | 中文名 | 類別 | 段落 ord／任期 key | 標題 | 引文數 | 禁用網域（引文數） |", "|---|---|---|---|---|---|---|"]
    for i in items:
        L.append(f"| {i['person']} | {i['nameZh'] or ''} | {'段落' if i['kind']=='paragraph' else '任期' if i['kind']=='position' else '角色'} | {i['id']} | {i['label'] or ''} | {i['citations']} | "
                 + "、".join(f"{k}（{v}）" for k, v in i["droppedDomains"].items()) + " |")
    L += ["", "## 每人統計", "", "| 人物 key | 段落 | 任期 | 角色 |", "|---|---|---|---|"]
    for k, c in sorted(per.items(), key=lambda kv: -sum(kv[1].values())):
        L.append(f"| {k} | {c['paragraph']} | {c['position']} | {c['role']} |")
    OUT.with_suffix(".md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
