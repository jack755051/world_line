"""欄位內標記：預設值、空值、未審中文名直接標在欄位旁，不只記在 gaps.json（共用工具；Tai 2026-11-13 13:39 流程修正第 3 項）。

用法：python3 -I tools/battles/mark_fields.py <battle> [--apply]
主期起日取 data/seed/battles/<battle>/battle.config.json 的 mainPhase.start（沒有就不判「預設起日」）。
標記（寫在該欄位所在物件內，與值並列）：
  period/tenure.startBasis = "default-main-phase-start"  起日等於主期起日，且該筆引文原文沒有出現該日 → 視為套用主期起日的預設值
                           = "empty-no-source"           起日為空：未見出處
  period/tenure.endBasis   = "empty-no-source"           止日為空：未見出處（不是「持續中」）
  nameZhStatus             = "unreviewed"                中文名未經人工審訂（機器譯名或取自他處，待審）
已有的 *Basis／nameZhStatus 不覆寫（人工判定優先）。
"""
import collections, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TARGETS = [("r1-units.json", "units", "period"), ("r5-engagements.json", "engagements", "period"), ("r7-commanders.json", "commanders", "tenure"),
           ("r7-missing-people.json", "people", "tenure"), ("phase-leadin.json", "phases", "period"),
           ("r3-unit-positions.json", "positions", None), ("r6-site-control.json", "sites", None), ("r4-leadin-fronts.json", "fronts", None)]
MONTHS = {"05": "May", "06": "June"}


def date_in_quotes(rec, iso):
    y, m, d = iso.split("-"); d = str(int(d))
    pat = re.compile(rf"\b{d}(st|nd|rd|th)?\s+{MONTHS.get(m, '')}|{MONTHS.get(m, '')}\s+{d}\b|\b{d}(st|nd|rd|th)\b")
    return any(pat.search(c.get("quote") or "") for c in rec.get("citations", []) or [])


def main():
    battle = sys.argv[1]; apply = "--apply" in sys.argv
    D = REPO / "data" / "seed" / "battles" / battle
    cfg = json.loads((D / "battle.config.json").read_text()) if (D / "battle.config.json").exists() else {}
    main_start = (cfg.get("mainPhase") or {}).get("start")
    cnt = collections.defaultdict(collections.Counter)
    for fn, arr, pf in TARGETS:
        p = D / fn
        if not p.exists(): continue
        d = json.loads(p.read_text())
        for r in d.get(arr, []):
            if pf and isinstance(r.get(pf), dict):
                per = r[pf]
                if "startBasis" not in per:
                    if per.get("start") is None:
                        per["startBasis"] = "empty-no-source"; cnt[fn]["startEmpty"] += 1
                    elif main_start and per["start"] == main_start and not date_in_quotes(r, main_start):
                        per["startBasis"] = "default-main-phase-start"; cnt[fn]["startDefault"] += 1
                if "endBasis" not in per and per.get("end") is None:
                    per["endBasis"] = "empty-no-source"; cnt[fn]["endEmpty"] += 1
            if r.get("nameZh") and "nameZhStatus" not in r:
                r["nameZhStatus"] = "unreviewed"; cnt[fn]["nameZhUnreviewed"] += 1
        if apply:
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: dict(v) for k, v in cnt.items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
