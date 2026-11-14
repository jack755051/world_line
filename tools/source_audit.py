"""全專案資料來源稽核（唯讀）：照 docs/source-rules.md 與 data/source-policy.json 檢查 data/seed 下所有資料建置檔。
用法：python3 -I tools/source_audit.py [--json] [--list 類別]
只讀檔案、不連資料庫、不改任何東西。數字是資料建置檔的狀態，不是資料庫的狀態。
回傳碼：有「違規」（禁用網域、不到最低等級卻標可寫入）時為 1，否則 0；「落差」（還沒有等級／出處欄位）不算違規。
"""
import collections, glob, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from source_policy import POLICY, REPO, banned, grade_ok

SEED = REPO / "data" / "seed"
R = collections.OrderedDict()   # 類別 → Counter
LISTS = collections.defaultdict(list)


def hit(kind, key, path=None):
    R.setdefault(kind, collections.Counter())[key] += 1
    if path: LISTS[f"{kind}:{key}"].append(str(path))


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def requests():
    """疆界、政權、事件、首都、控制、陣營等：requests/**/NN-*.json（一檔一個 API 請求）。"""
    src_by_dir, events = collections.defaultdict(dict), {}
    files = [Path(f) for f in glob.glob(str(SEED / "**" / "requests" / "**" / "*.json"), recursive=True) if "/battles/" not in f and "/leaders/" not in f]
    docs = []
    for f in files:
        d = load(f)
        if not isinstance(d, dict) or "body" not in d: continue
        post = str(d.get("_post", "")).split("?")[0]; b = d.get("body") or {}
        docs.append((f, d, post, b))
        if post.endswith("/sources"): src_by_dir[d.get("_placeholder")] = b
        if post.endswith("/events"): events[d.get("_placeholder")] = b
    def src_of(ref): return src_by_dir.get(str(ref or "").strip("{}"))
    for f, d, post, b in docs:
        if post.endswith("/sources"):
            hit("來源登記", "總數")
            bh = banned(b.get("url"))
            if bh == "wikimedia.org" and b.get("sourceKind") in ("map", "atlas_map") and b.get("publisher"): hit("來源登記", "地圖掃描檔放在 Commons（允許：出版者另有登記）")
            elif bh: hit("來源登記", "違規：禁用網域", f)
            if not b.get("licenseCode"): hit("來源登記", "落差：沒有授權碼", f)
            hit("來源登記", "落差：沒有等級")
        elif post.endswith("/sovereignty-records"):
            if d.get("_readd"): continue
            hit("主權疆界", "總數")
            s = src_of(b.get("geometrySourceId"))
            ds = bool(s and s.get("sourceKind") in POLICY["datasetSourceKinds"])
            ev = events.get(str(b.get("startEventId") or "").strip("{}"))
            if ev and ev.get("citations"): hit("主權疆界", "起始事件有引文")
            elif ds or s is None: hit("主權疆界", "待查證：只有資料集，起訖日沒有 A/B 出處", f)
            else: hit("主權疆界", "幾何出處不是資料集，但起始事件沒有引文", f)
            if b.get("geometryLicense") not in POLICY["geometryLicenses"]: hit("主權疆界", "違規：幾何授權不在允許清單", f)
        elif post.endswith("/events"):
            hit("事件", "總數")
            cs = b.get("citations") or []
            if not cs: hit("事件", "不可寫入：沒有引文", f)
            else: hit("事件", "有引文（沒有等級欄位）")
        elif post.endswith("/regimes"):
            hit("政權", "總數"); hit("政權", "落差：沒有出處欄位")
        elif post.endswith("/capital-records"):
            hit("首都", "總數")
            ref = (b.get("sourceRef") or "").strip()
            if not ref: hit("首都", "不可寫入：沒有出處", f)
            elif ref.startswith("待查證"): hit("首都", "不可寫入：出處寫「待查證」", f)
            else: hit("首都", "落差：出處是自由文字，沒有等級")
        elif post.endswith("/control-records"):
            hit("實際控制", "總數")
            cs = b.get("citations") or []
            if not any(c.get("role") == "primary" for c in cs): hit("實際控制", "違規：沒有主要出處", f)
            else: hit("實際控制", "有主要出處（沒有等級欄位）")
        elif post.endswith("/alignments"):
            hit("陣營", "總數")
            hit("陣營", "有引文（沒有等級欄位）" if b.get("citations") else "違規：沒有引文", None if b.get("citations") else f)
        elif post.endswith("/occupation-attributions"):
            hit("佔領歸屬", "總數")
            ev = events.get(str(b.get("basisEventId") or "").strip("{}"))
            if not b.get("basisEventId"): hit("佔領歸屬", "落差：沒有依據事件", f)
            elif ev is not None and not ev.get("citations"): hit("佔領歸屬", "落差：依據事件沒有引文", f)
            else: hit("佔領歸屬", "依據事件有引文或在別批")
        elif post.endswith("/conflict-records"):
            hit("衝突", "總數")
            ev = events.get(str(b.get("startEventId") or "").strip("{}"))
            if ev is not None and not ev.get("citations"): hit("衝突", "落差：起始事件沒有引文", f)
            else: hit("衝突", "起始事件有引文或在別批")


def capitals_py():
    n = t = 0
    for f in glob.glob(str(SEED / "capitals" / "*.py")):
        s = Path(f).read_text(encoding="utf-8")
        n += s.count('"sourceRef"') + s.count("'sourceRef'"); t += s.count('"待查證') + s.count("'待查證")
    if n:
        R.setdefault("首都", collections.Counter())["另有寫在送出程式裡的紀錄（自由文字）"] = n
        R["首都"]["其中出處以「待查證」開頭"] = t


def citations_in(o, candidate=False, with_flag=False):
    """走過所有 citation；with_flag=True 時回傳 (citation, 是否為缺口候選)。
    缺口候選（gaps[].candidateCitations）本來就不是出處，可放未達最低等級的來源（Q9）。"""
    if isinstance(o, dict):
        if "sourceKey" in o and ("quote" in o or "locator" in o): yield (o, candidate) if with_flag else o
        for k, v in o.items(): yield from citations_in(v, candidate or k == "candidateCitations", with_flag)
    elif isinstance(o, list):
        for v in o: yield from citations_in(v, candidate, with_flag)


def bios():
    for kind, pat, pol in [("將領生平", "leaders/generals-roster/bios/[SA]/*/research.json", "bio_general"),
                           ("人物生平（b3 格式）", "leaders/b3-trial/**/research.json", "bio"), ("人物生平（b3 格式）", "leaders/churchill-rebuild/**/research.json", "bio")]:
        for f in glob.glob(str(SEED / pat), recursive=True):
            d = load(f)
            if not isinstance(d, dict): continue
            src = d.get("sources") if isinstance(d.get("sources"), dict) else {}
            for c, cand in citations_in(d.get("people") or d, with_flag=True):
                hit(kind, "引文總數"); g = c.get("grade"); u = (src.get(c.get("sourceKey")) or {}).get("url")
                if banned(u): hit(kind, "違規：禁用網域", f)
                if g is None: hit(kind, "落差：沒有等級")
                elif cand and not grade_ok(g, pol): hit(kind, f"缺口候選（不是出處）：等級 {g}")
                elif not grade_ok(g, pol): hit(kind, f"不可寫入：等級 {g} 不到這類資料的最低等級", f)
                else: hit(kind, f"等級 {g}")
    for f in glob.glob(str(SEED / "leaders/gap-830/*/research.json")) + glob.glob(str(SEED / "leaders/batch-p1-20261107/**/research.json"), recursive=True) + [str(SEED / "leaders/batch-p1-20261107" / n) for n in ("roc.json", "su-tr.json", "us-es.json", "death-precision.json")]:
        d = load(f)
        def walk(o):
            if isinstance(o, dict):
                if "url" in o and "sourceKind" in o:
                    hit("人物生平（舊格式）", "出處總數")
                    if banned(o.get("url")): hit("人物生平（舊格式）", "違規：禁用網域", f)
                    if "grade" not in o: hit("人物生平（舊格式）", "落差：沒有等級")
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for v in o: walk(v)
        walk(d)
    for f in ("leaders/send_leaders.py", "leaders/send_leaders_batch2.py"):
        p = SEED / f
        if p.exists():
            n = len(__import__("re").findall(r"""["']verified["']\s*:\s*True""", p.read_text(encoding="utf-8")))
            R.setdefault("元首任期", collections.Counter())["落差：標已查證但出處是自由文字、沒有等級"] += n


def battles():
    for D in sorted((SEED / "battles").iterdir()):
        if not (D / "sources.json").exists(): continue
        kind = f"戰役 {D.name}"; src = load(D / "sources.json") or {}; src = src.get("sources", src)
        for k, v in src.items():
            if isinstance(v, dict) and banned(v.get("url")) and v.get("grade") != "C": hit(kind, "違規：禁用網域的來源評為 A/B", D / "sources.json")
        for fn in ("r1-units", "r3-unit-positions", "r4-fronts", "r4-leadin-fronts", "r5-engagements", "r6-site-control", "r7-commanders", "phase-leadin"):
            d = load(D / (fn + ".json"))
            if not isinstance(d, dict): continue
            for r in next((v for v in d.values() if isinstance(v, list) and v and isinstance(v[0], dict) and ("citations" in v[0] or "mapRef" in v[0])), []):
                hit(kind, "紀錄總數"); cf = r.get("confidence") or {}
                hit(kind, {"verified": "已查證", "needs-check": "待查證", "estimate": "推估或查無"}.get(cf.get("level"), "落差：沒有可信程度"))
                if cf.get("opposingOnly"): hit(kind, "其中只有對手方說法")
                for c in r.get("citations") or []:
                    if (c.get("quoteCheck") or {}).get("status", "verbatim") not in ("verbatim", "verbatim-pdf-hyphen"): hit(kind, "引文沒通過逐字核對（不計入）")
                    if len(c.get("quote") or "") > POLICY["quoteMaxChars"]: hit(kind, "引文超過長度上限（不寫入）")


def main():
    requests(); capitals_py(); bios(); battles()
    if "--list" in sys.argv:
        key = sys.argv[sys.argv.index("--list") + 1]
        for k, v in LISTS.items():
            if key in k: print(f"## {k}（{len(v)}）"); print("\n".join(sorted(set(v))))
        return 0
    if "--json" in sys.argv: print(json.dumps({"policy": POLICY["version"], "result": R}, ensure_ascii=False, indent=1))
    else:
        print(f"來源稽核（政策 {POLICY['version']}；資料建置檔，不是資料庫）")
        for kind, c in R.items():
            print(f"\n{kind}")
            for k, v in c.items(): print(f"  {v:6d}  {k}")
    return 1 if any(k.startswith("違規") for c in R.values() for k in c) else 0


if __name__ == "__main__":
    sys.exit(main())
