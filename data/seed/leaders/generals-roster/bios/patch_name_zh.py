#!/usr/bin/env python3
"""補將領中文名（name_zh／nameZh）：只取自索引（中文維基百科條目內的跨語言連結模板），並記出處。
背景：roster 由英文維基分類建立，分類成員沒有 zh langlink 時 build_roster.py 寫 name_zh="待查證"（第 532 行），
build_selection.py 照抄（第 32 行）；研究提示當時沒規定 nameZh 怎麼填，模型對這些人自行音譯（無出處）或寫「待查證」，
主迴圈 batch_names() 以 name_zh 組 commit 訊息，故 commit 訊息出現「待查證」。
規則（World Line 主管 2026-11-12 09:36；Wikipedia 只當人名索引，Tai 已允許）：
 1. 只處理 selection.json 中 name_zh=="待查證" 的人。
 2. 在中文維基以 "name_original" 全文搜尋（srlimit=10），讀命中條目的 wikitext，找跨語言連結模板
    {{link-xx|中文名|原文名}}、{{le|中文名|原文名}}、{{tsl|xx|原文名|中文名}}；原文名正規化後（小寫、去逗號句點、
    空白折疊）須與 name_original 或其英文維基正式標題完全相同，才採用。取出現次數最多者（同數時全名（含間隔號）、無爵位前綴者優先，再取較短者）。
 3. 找不到 → 維持「待查證」並列表；不採模型音譯、不採 Wikidata／百度。
 4. selection.json：name_zh ← 索引名，加 name_zh_source；研究檔（只改已 commit 且無未提交變更、批號 < 主迴圈 current_batch 者）
    nameZh ← 索引名或「待查證」，原值若非索引來源存到 nameZhUnsourced，並加 nameZhSource。
用法（repo 根目錄）：python3 data/seed/leaders/generals-roster/bios/patch_name_zh.py [--dry-run]
"""
import json, re, sys, subprocess, collections, os, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import wikilib
from zh_trad import to_trad  # 2026-11-12 10:07：中文名一律正體（s2t 字元轉換）

REPO = HERE.parents[4]
SEL = HERE / "selection.json"
STATE = REPO / ".dev/cc-generals-bios.state.json"
DRY = "--dry-run" in sys.argv
TPL = re.compile(r"\{\{\s*(?:link-[a-z]{2,3}|le|ill)\s*\|\s*([^|{}]+?)\s*\|\s*([^|{}]+?)\s*(?:\||\}\})", re.I)
TSL = re.compile(r"\{\{\s*tsl\s*\|\s*[a-z]{2,3}\s*\|\s*([^|{}]+?)\s*\|\s*([^|{}]+?)\s*(?:\||\}\})", re.I)
CJK = re.compile(r"[\u3400-\u9fff]")

def norm(s):
    s = re.sub(r"-\{|\}-", "", s or "")
    return re.sub(r"\s+", " ", re.sub(r"[,.]", "", s)).strip().lower()

def clean_zh(s):
    s = re.sub(r"-\{(?:[^{}]*?:)?([^{}]*?)\}-", r"\1", s)
    return re.sub(r"\s+", "", s).strip()

def lookup(orig):
    pi = wikilib.pageinfo("en", orig)
    targets = {norm(orig)}
    if pi.get("ok") and pi.get("title"):
        targets.add(norm(pi["title"]))
    if pi.get("ok") and (pi.get("langlinks") or {}).get("zh"):
        return {"name": None, "langlink": pi["langlinks"]["zh"]}  # 有正式 langlink 時另行處理
    sr = wikilib.cached("zhs", "zh", orig, lambda: (lambda r: dict(ok=r[1] is not None, status=r[0],
            titles=[h["title"] for h in ((r[1] or {}).get("query") or {}).get("search", [])]))(
            wikilib.api("zh", action="query", list="search", srsearch=f'"{orig}"', srlimit=10, srprop="")))
    hits = collections.Counter(); where = collections.defaultdict(list)
    for t in sr.get("titles") or []:
        wt = wikilib.wikitext("zh", t)
        if not wt.get("ok"):
            continue
        txt = wt["wikitext"]
        for m in TPL.finditer(txt):
            zh, en = m.group(1), m.group(2)
            if norm(en) in targets and CJK.search(zh):
                z = clean_zh(zh); hits[z] += 1; where[z].append(t)
        for m in TSL.finditer(txt):
            en, zh = m.group(1), m.group(2)
            if norm(en) in targets and CJK.search(zh):
                z = clean_zh(zh); hits[z] += 1; where[z].append(t)
    if not hits:
        return {"name": None, "searched": sr.get("titles") or []}
    def rank(kv):  # 次數多者先；同數時：有間隔號（全名）優先、無爵位前綴／稱謂後綴優先，再取較短、字典序
        z, n = kv
        titled = z.startswith("第一代") or z.endswith(("将军", "將軍", "上将", "上將", "爵士"))
        return (-n, not re.search("[·‧・]", z), titled, len(z), z)
    best = sorted(hits.items(), key=rank)[0][0]
    return {"name": best, "count": hits[best], "articles": sorted(set(where[best])),
            "variants": {k: v for k, v in hits.items() if k != best}}

def git_clean(path):
    rel = str(path.relative_to(REPO))
    tracked = subprocess.run(["git", "-C", str(REPO), "ls-files", "--error-unmatch", rel], capture_output=True).returncode == 0
    clean = subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", "--", rel]).returncode == 0
    return tracked and clean

def atomic_write(path, text):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)

def main():
    today = wikilib.now()
    sel = json.loads(SEL.read_text(encoding="utf-8"))
    cur = json.loads(STATE.read_text()) if STATE.exists() else {}
    cur_tier, cur_nn = cur.get("current_phase"), cur.get("current_batch")
    found, missing = {}, []
    for tier in ("S", "A"):
        for b in sel[tier]:
            for p in b["people"]:
                if p.get("name_zh") != "待查證":
                    continue
                r = lookup(p.get("name_original") or "")
                if r.get("name"):
                    src = {"method": "zhwiki-interlanguage-link-template", "role": "index-only（Wikipedia 只當人名索引，非史料來源）",
                           "kind": "wikipedia-index", "status": "candidate", "verified": False, "isCitation": False,
                           "zhwikiArticles": r["articles"], "occurrences": r["count"], "variants": r["variants"],
                           "matchedOriginal": p.get("name_original"), "retrievedAt": today, "patch": "patch_name_zh.py"}
                    nm = to_trad(r["name"]); src["indexString"] = r["name"]
                    found[p["key"]] = (nm, src, tier, b["batch"])
                    p["name_zh"] = nm; p["name_zh_source"] = src
                else:
                    missing.append({"tier": tier, "batch": b["batch"], "key": p["key"], "name_original": p.get("name_original"),
                                    "searchedArticles": r.get("searched", []), "langlink": r.get("langlink")})
    changed_research = []
    for f in sorted(HERE.glob("[SA]/batch*/research.json")):
        tier, nn = f.parent.parent.name, f.parent.name.replace("batch", "")
        if tier == cur_tier and cur_nn and nn >= cur_nn:
            continue  # 主迴圈進行中或尚未跑的批次不碰
        raw = f.read_text(encoding="utf-8"); d = json.loads(raw); touched = False
        if not git_clean(f):
            continue
        for p in d.get("people") or []:
            k = p.get("key")
            miss = next((m for m in missing if m["key"] == k), None)
            if k not in found and not miss:
                continue
            old = p.get("nameZh")
            new = found[k][0] if k in found else "待查證"
            if old == new and p.get("nameZhSource"):
                continue
            if old not in (None, "", "待查證", new):
                p["nameZhUnsourced"] = old
            p["nameZh"] = new
            p["nameZhSource"] = found[k][1] if k in found else {"method": "none", "note": "名冊／索引無中文名，維持待查證", "retrievedAt": today, "patch": "patch_name_zh.py"}
            touched = True
            changed_research.append({"file": str(f.relative_to(REPO)), "key": k, "old": old, "new": new})
        if touched and not DRY:
            atomic_write(f, json.dumps(d, ensure_ascii=False, indent=1) + ("\n" if raw.endswith("\n") else ""))  # 保留原檔格式
    if not DRY:
        atomic_write(SEL, json.dumps(sel, ensure_ascii=False, indent=1) + "\n")
    rep = {"generatedAt": today, "loopCurrent": f"{cur_tier}/batch{cur_nn}", "found": {k: {"name_zh": v[0], "tier": v[2], "batch": v[3], "source": v[1]} for k, v in found.items()},
           "stillPending": missing, "researchChanged": changed_research, "dryRun": DRY}
    if not DRY:
        (HERE / "patch_name_zh.report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"found": len(found), "pending": len(missing), "researchChanged": len(changed_research)}, ensure_ascii=False))
    for k, v in found.items():
        print(f"FOUND {v[2]}/{v[3]} {k} → {v[0]}  ({v[1]['occurrences']}× {v[1]['zhwikiArticles'][:3]}; variants={v[1]['variants']})")
    for m in missing:
        print(f"PENDING {m['tier']}/{m['batch']} {m['key']} ({m['name_original']})")
    for c in changed_research:
        print(f"RESEARCH {c['file']} {c['key']}: {c['old']} → {c['new']}")

if __name__ == "__main__":
    main()
