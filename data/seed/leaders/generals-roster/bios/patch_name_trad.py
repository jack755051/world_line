#!/usr/bin/env python3
"""將領中文名一律正體（OpenCC s2t 字元轉換＋PROTECT 逐字保留，見 ../zh_trad.py），並把維基索引名標成候選值。
World Line 主管 2026-11-12 10:07；10:20 起 zh_trad 改為 s2t→t2tw 台灣標準字形＋PRE（冲→沖），本腳本重跑即升級。冪等：已是正體者不動；原字串只在第一次變更時記錄（name_zh_orig／nameZhOrig），另全數列在報告。
範圍：roster.json people[].name_zh；bios/selection.json S／A people[].name_zh；bios/{S,A}/batch*/research.json people[].nameZh
（只改已 commit、無未提交變更、且不是主迴圈進行中／未跑的批次）。nameZhUnsourced 不轉（原樣保存，永不入庫）。
nameZhSource／name_zh_source：維基索引名 → kind=wikipedia-index、status=candidate、verified=false、isCitation=false。
用法（repo 根目錄）：python3 data/seed/leaders/generals-roster/bios/patch_name_trad.py [--dry-run]
"""
import json, sys, subprocess, os, tempfile, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from zh_trad import to_trad
import zh_trad as _zt

def legacy_10_07(s):
    """10:07 版轉法（s2t＋PROTECT，無 t2tw／PRE），只用來判斷現值是否由原字串機械轉出。"""
    t = _zt._load().convert(s)
    return t if len(t) != len(s) else "".join(a if a in _zt.PROTECT else b for a, b in zip(s, t))

REPO = HERE.parents[4]
DRY = "--dry-run" in sys.argv
NOW = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
REVIEW_CHARS = {"衝": "冲→衝（人名多為「沖」，例 彭沖）", "衆": "众→衆（台灣通行「眾」）"}  # 10:20 起 PRE／t2tw 已處理，留作回歸檢查
CAND = {"kind": "wikipedia-index", "status": "candidate", "verified": False, "isCitation": False,
        "candidateRule": "維基百科只當人名索引，與 Wikidata 同規則：候選值、非出處；A／B／C 來源有中文譯名時以來源為準（附 citation，verified=true）"}
PEND = {"kind": "none", "status": "pending", "verified": False, "isCitation": False}

def fmt_of(raw):
    d = json.loads(raw)
    for ind in (1, 2, None):
        for ea in (False, True):
            s = json.dumps(d, ensure_ascii=ea, indent=ind)
            if s == raw.rstrip("\n"):
                return (ind, ea, raw.endswith("\n"))
    return (1, False, raw.endswith("\n"))

def dump(d, fmt):
    ind, ea, nl = fmt
    return json.dumps(d, ensure_ascii=ea, indent=ind) + ("\n" if nl else "")

def atomic_write(path, text):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)

def git_clean(path):
    rel = str(path.relative_to(REPO))
    tracked = subprocess.run(["git", "-C", str(REPO), "ls-files", "--error-unmatch", rel], capture_output=True).returncode == 0
    return tracked and subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", "--", rel]).returncode == 0

def norm_source(src):
    if not isinstance(src, dict):
        return src, False
    add = CAND if src.get("method") == "zhwiki-interlanguage-link-template" else (PEND if src.get("method") == "none" else None)
    if not add or all(src.get(k) == v for k, v in add.items()):
        return src, False
    src = dict(src); src.update(add)
    return src, True

changes = {"roster": [], "selection": [], "research": [], "sourceStatus": []}
review = []

def conv(rec, field, origf, where, bucket):
    old = rec.get(field)
    if not isinstance(old, str) or not old:
        return False
    orig = rec.get(origf)
    # 現值若是原字串機械轉出（10:07 版或現行版），以原字串重轉（例 张冲→張衝 改為 張沖）；否則（例 日後依來源改名）只轉現值
    base = orig if isinstance(orig, str) and orig and old in (legacy_10_07(orig), to_trad(orig)) else old
    new = to_trad(base)
    if new == old:
        return False
    rec.setdefault(origf, old)
    rec[field] = new
    changes[bucket].append({"where": where, "old": old, "new": new})
    for ch, why in REVIEW_CHARS.items():
        if ch in new and ch not in old:
            review.append({"where": where, "new": new, "why": why})
    return True

def main():
    # roster
    rp = HERE.parent / "roster.json"; raw = rp.read_text(encoding="utf-8"); fmt = fmt_of(raw); d = json.loads(raw); t = False
    for i, p in enumerate(d["people"]):
        t |= conv(p, "name_zh", "name_zh_orig", f"roster.json#{i} {p.get('name_original')}", "roster")
    if t and not DRY: atomic_write(rp, dump(d, fmt))
    # selection
    sp = HERE / "selection.json"; raw = sp.read_text(encoding="utf-8"); fmt = fmt_of(raw); d = json.loads(raw); t = False
    for tier in ("S", "A"):
        for b in d[tier]:
            for p in b["people"]:
                t |= conv(p, "name_zh", "name_zh_orig", f"selection {tier}/{b['batch']} {p['key']}", "selection")
                s2, ch = norm_source(p.get("name_zh_source"))
                if ch: p["name_zh_source"] = s2; t = True; changes["sourceStatus"].append(f"selection {p['key']}")
    if t and not DRY: atomic_write(sp, dump(d, fmt))
    # research
    st = json.loads((REPO / ".dev/cc-generals-bios.state.json").read_text())
    cur_tier, cur_nn = st.get("current_phase"), st.get("current_batch")
    skipped = []
    for f in sorted(HERE.glob("[SA]/batch*/research.json")):
        tier, nn = f.parent.parent.name, f.parent.name.replace("batch", "")
        if (tier == cur_tier and nn >= cur_nn) or not git_clean(f):
            skipped.append(str(f.relative_to(REPO))); continue
        raw = f.read_text(encoding="utf-8"); fmt = fmt_of(raw); d = json.loads(raw); t = False
        for p in d.get("people") or []:
            t |= conv(p, "nameZh", "nameZhOrig", f"{tier}/batch{nn} {p.get('key')}", "research")
            s2, ch = norm_source(p.get("nameZhSource"))
            if ch: p["nameZhSource"] = s2; t = True; changes["sourceStatus"].append(f"{tier}/batch{nn} {p.get('key')}")
        if t and not DRY: atomic_write(f, dump(d, fmt))
    # 累計（冪等重跑也保留完整紀錄）：由 *_orig 欄位重建全部已轉換的名字
    cum = {"roster": [], "selection": [], "research": []}
    for i, p in enumerate(json.loads(rp.read_text(encoding="utf-8"))["people"]):
        if p.get("name_zh_orig"): cum["roster"].append({"where": f"roster.json#{i} {p.get('name_original')}", "old": p["name_zh_orig"], "new": p["name_zh"]})
    for tier in ("S", "A"):
        for b in json.loads(sp.read_text(encoding="utf-8"))[tier]:
            for p in b["people"]:
                if p.get("name_zh_orig"): cum["selection"].append({"where": f"selection {tier}/{b['batch']} {p['key']}", "old": p["name_zh_orig"], "new": p["name_zh"]})
    for f in sorted(HERE.glob("[SA]/batch*/research.json")):
        for p in json.loads(f.read_text(encoding="utf-8")).get("people") or []:
            if p.get("nameZhOrig"): cum["research"].append({"where": f"{f.parent.parent.name}/{f.parent.name} {p.get('key')}", "old": p["nameZhOrig"], "new": p.get("nameZh")})
    allrev = [{"where": c["where"], "new": c["new"], "why": why} for k in cum for c in cum[k] for ch, why in REVIEW_CHARS.items() if ch in (c["new"] or "") and ch not in c["old"]]
    rep = {"generatedAt": NOW, "cumulativeCounts": {k: len(v) for k, v in cum.items()}, "cumulative": cum, "cumulativeNeedsReview": allrev, "converter": "OpenCC 1.4.2 s2t→t2tw（台灣標準字形，非 s2twp 詞彙）＋zh_trad.PRE（冲→沖）＋zh_trad.PROTECT 逐字保留（含「台」不轉「臺」）", "loopCurrent": f"{cur_tier}/batch{cur_nn}",
           "counts": {k: len(v) for k, v in changes.items()}, "needsReview": review, "skippedResearch": skipped, "changes": changes, "dryRun": DRY}
    if not DRY:
        (HERE / "patch_name_trad.report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"counts": rep["counts"], "needsReview": review, "skipped": skipped}, ensure_ascii=False, indent=1))
    for k in ("roster", "selection", "research"):
        for c in changes[k][:5]:
            print(k, c["where"], c["old"], "→", c["new"])

if __name__ == "__main__":
    main()
