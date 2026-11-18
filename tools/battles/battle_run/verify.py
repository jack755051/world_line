"""檢查 agent 寫的候選，彙整成 r3／r4／r5r6／r7 候選檔與一行摘要。

每筆引文：≤80 字元（NFC）、在已快取原文中逐字找到（與 verify_quotes.py 同正規化，不連網）、
不可跨分頁、非禁用網域、sourceKey 已登記且有 family＋side、等級 A/B 且與登記一致。
地點必須是具體城鎮，不可是國家、地區或「前線」。
不呼叫 osm_lookup.py（那支會寫入 repo 的 osm-places.json）；只讀已有的 osm-places.json。
不跑 crosscheck.py --apply、verify_quotes.py --apply。併入後由戰役 session 跑那些腳本。
"""
from __future__ import annotations

import datetime
import json
import re
import unicodedata
from pathlib import Path

from . import paths

TODAY = datetime.date.today().isoformat()
TOOL = "tools/battles/battle_run/verify.py"
OUTF = {
    "R3": "r3-candidates.json",
    "R4": "r4-text-vertex-candidates.json",
    "R5": "r5r6-date-candidates.json",
    "R6": "r5r6-date-candidates.json",
    "R7": "r7-candidates.json",
}

BAD_PLACE = re.compile(
    r"(?i)^(the\s+)?("
    r"poland|germany|east prussia|prussia|pomerania|silesia|upper silesia|"
    r"galicia|slovakia|lithuania|latvia|romania|hungary|russia|soviet union|ussr|"
    r"corridor|polish corridor|danzig corridor|western front|eastern front|front|the front|"
    r"china|japan|france|belgium|flanders|the channel ports|"
    r"中國|日本|波蘭|德國|法國|比利時|江南|江蘇|浙江|華中|華北|上海地區"
    r")$|front\b|\bregion\b|\barea\b|\bline\b|一帶|地區|方面$|戰線|之線|北岸|南岸|沿岸|沿線"
    r"|^.*[－–—-].*[－–—-].*$|、|，| and "
)


def bad_place(name):
    n = (name or "").strip()
    return (not n) or bool(BAD_PLACE.search(n))


def in_period(d, mp):
    return bool(d) and mp.get("start") and mp.get("end") and mp["start"] <= d[:10] <= mp["end"]


def split_pages(text: str):
    return re.split(r"\f|--\s*\d+\s*--|⟨分頁⟩|--pagebreak--", text)


def check_quote(repo, battle, stage, c, src, existing, seen, grades_ok, gid=None):
    why = []
    q = c.get("quote") or ""
    if len(unicodedata.normalize("NFC", q)) > 80:
        why.append(f"引文 {len(unicodedata.normalize('NFC', q))} 字元 > 80")
    url = (c.get("url") or "").split("#")[0]
    if not url:
        why.append("無 url")
    elif paths.banned(url):
        why.append(f"禁用網域 {paths.banned(url)}")
    s = src.get(c.get("sourceKey"))
    if not s:
        why.append(f"sourceKey 未登記：{c.get('sourceKey')}")
    else:
        if not s.get("family") or not s.get("side"):
            why.append("來源缺 family 或 side")
        if s.get("grade") not in grades_ok:
            why.append(f"來源等級 {s.get('grade')} 不是 A/B")
        if c.get("grade") != s.get("grade"):
            why.append(f"引文等級 {c.get('grade')} ≠ 登記 {s.get('grade')}")
    status = None
    if url and not paths.banned(url):
        texts, is_pdf = paths.verify_texts(url, repo, battle, stage)
        if texts is None:
            status = "no_cache"
            why.append("原文不在快取（不連網補抓）")
        else:
            nq = paths.norm(q)
            pages = [pg for t in texts for pg in split_pages(t)]
            # --頁碼-- 在 norm 後不會消失，跨頁要比對「去掉頁標記」的全文
            nopage = [paths.norm(re.sub(r'\f|--\s*\d+\s*--|--pagebreak--|⟨分頁⟩', '', t)) for t in texts]
            if nq and any(nq in paths.norm(pg) for pg in pages):
                status = "verbatim"
            elif nq and (any(nq in paths.norm(t) for t in texts) or any(nq in s for s in nopage)):
                status = "failed"
                why.append("引文跨分頁")
            elif is_pdf and nq and any(nq.replace("-", "") in paths.norm(t).replace("-", "") for t in texts):
                status = "verbatim-pdf-hyphen"
            else:
                status = "failed"
                why.append("原文找不到逐字相同字串")
    k = (url, paths.norm(q))
    if k in existing:
        c["reusesExistingCitation"] = True
    if (gid,) + k in seen:
        why.append("同一缺口內重複引文")
    seen.add((gid,) + k)
    c["quoteCheck"] = {"status": status or "failed", "checkedOn": TODAY, "tool": TOOL}
    return why


def run(repo, battle, stage):
    stage = Path(stage)
    cfg = paths.load_battle(repo, battle, "battle.config.json", {}) or {}
    mp = cfg.get("mainPhase") or {}
    lead = cfg.get("leadIn") or {}
    # 就任日與前置期位置可用 leadIn～mainPhase 的聯集來檢查
    span = {
        "start": min(x for x in (lead.get("start"), mp.get("start")) if x) if (lead or mp) else None,
        "end": max(x for x in (lead.get("end"), mp.get("end")) if x) if (lead or mp) else None,
    }
    grades_ok = cfg.get("battleFactGrades") or ["A", "B"]
    units = {u["unitKey"] for u in (paths.load_battle(repo, battle, "r1-units.json", {}) or {}).get("units") or []}
    cand_src = paths.load_json(stage / "sources-candidates.json", {"sources": []})
    src = paths.source_table(repo, battle, cand_src)
    existing = paths.existing_citations(repo, battle)
    seen = set()
    buckets = {f: [] for f in set(OUTF.values())}
    nofind = []
    conflicts = []
    rep = {"battle": battle, "checkedOn": TODAY, "byType": {}, "rejects": [], "escalate": []}
    out_dir = stage / "out"
    if out_dir.is_dir():
        files = sorted(out_dir.glob("*.json"))
    else:
        files = []
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        nofind += [dict(x, batch=f.stem) for x in d.get("noFind") or []]
        for cand in d.get("candidates") or []:
            t = cand.get("type") or (cand.get("gapId") or "")[:2].upper()
            why = []
            if t in ("R3", "R7") and cand.get("unitKey") not in units:
                why.append(f"unitKey 不在 R1：{cand.get('unitKey')}")
            for k in (cand.get("attackers") or []) + (cand.get("defenders") or []):
                if k not in units:
                    why.append(f"交戰單位不在 R1：{k}")
            dates = []
            if t in ("R3", "R4", "R6"):
                dates = [cand.get("date")]
            if t == "R5":
                dates = [x for x in ((cand.get("period") or {}).get("start"), (cand.get("period") or {}).get("end")) if x]
            for dt in dates:
                if not dt or not re.match(r"\d{4}-\d{2}-\d{2}", dt):
                    why.append(f"日期格式不對：{dt}")
                elif span.get("start") and not in_period(dt, span):
                    why.append(f"日期 {dt} 不在戰役期間 {span['start']}～{span['end']}")
            if t == "R5" and not dates:
                why.append("沒有任何日期")
            if t == "R7":
                st = (cand.get("tenure") or {}).get("start")
                if not st or not re.match(r"\d{4}-\d{2}(-\d{2})?", st):
                    why.append(f"就任日格式不對：{st}")
                elif mp.get("end") and st[:10] > mp["end"]:
                    why.append("就任日晚於主期止日")
                elif mp.get("start") and st[:10] < mp["start"]:
                    cand["verifyNote"] = "就任日早於主期（任期起日，允許）"
            if t in ("R3", "R6") and bad_place(cand.get("placeAsInSource")):
                why.append(f"地點不是具體城鎮／地點：{cand.get('placeAsInSource')}")
            if t == "R4":
                for v in cand.get("vertices") or []:
                    if bad_place(v.get("nearPlace") or v.get("placeAsInSource")):
                        why.append(f"頂點不是城鎮：{v.get('nearPlace')}")
            if t == "R3":
                pl = cand.get("place") or {}
                if not pl.get("osm"):
                    hit = paths.osm_lookup_local(repo, battle, cand.get("placeAsInSource") or pl.get("nameOsm") or "")
                    if hit:
                        cand["place"] = {"nameOsm": hit["nameOsm"], "osm": hit["osm"]}
                        cand["placeOsmBy"] = "osm-places.json 名稱比對（待複核）"
                    else:
                        cand["placeOsmNeeded"] = True
            if t == "R4":
                vs = cand.get("vertices") or []
                for v in vs:
                    if not v.get("osm"):
                        hit = paths.osm_lookup_local(repo, battle, v.get("nearPlace") or v.get("placeAsInSource") or "")
                        if hit:
                            v.update(osm=hit["osm"], lonlat=hit["lonlat"], vertexNote="osm-places.json 名稱比對（待複核）")
                        else:
                            v["osmNeeded"] = True
                if len(vs) < 2:
                    why.append("文字頂點少於 2 個")
            cits = cand.get("citations") or []
            if not cits:
                why.append("沒有引文")
            okc = 0
            for c in cits:
                w = check_quote(repo, battle, stage, c, src, existing, seen, grades_ok, cand.get("gapId"))
                if w:
                    c["verifyFail"] = w
                else:
                    okc += 1
            if cits and okc < len(cits):
                why.append(f"{okc}/{len(cits)} 條引文通過（全部引文都要通過）")
            reuse = bool(cits) and all(c.get("reusesExistingCitation") for c in cits)
            if t == "R3" and cand.get("placeOsmNeeded"):
                cand.setdefault("verifyWarn", []).append(
                    "地名不在 osm-places.json：需戰役 session 用 tools/battles/osm_lookup.py 查；國家／地區／「前線」等非城鎮地名不可用"
                )
            status = ("pass-reuse" if reuse else "pass") if not why else "fail"
            cand["verify"] = {
                "status": status, "why": why, "citationsPassed": okc,
                "checkedOn": TODAY, "tool": TOOL, "batch": f.stem,
            }
            if why:
                rep["rejects"].append({
                    "gapId": cand.get("gapId"), "type": t,
                    "why": why + [w for c in cits for w in c.get("verifyFail") or []],
                })
                # 引文失敗或來源衝突 → 列給升級／Tai
                if any("原文找不到" in x or "跨分頁" in x or "字元 > 80" in x for x in why + [w for c in cits for w in c.get("verifyFail") or []]):
                    rep["escalate"].append({"gapId": cand.get("gapId"), "type": t, "reason": "核對失敗", "why": why})
            if cand.get("note") and "衝突" in str(cand.get("note")):
                conflicts.append(cand)
                rep["escalate"].append({"gapId": cand.get("gapId"), "type": t, "reason": "兩個說法衝突", "note": cand.get("note")})
            cand["staging"] = True
            buckets[OUTF.get(t, "r3-candidates.json")].append(cand)
            r = rep["byType"].setdefault(t, {"written": 0, "pass": 0, "pass-reuse": 0, "fail": 0})
            r["written"] += 1
            r[status] = r.get(status, 0) + 1

    for fn, items in buckets.items():
        paths.write_json(stage / fn, {
            "schema": "wl-battle-run/0.1",
            "battle": battle,
            "note": "候選，未併入戰役資料；verify.status=pass 才可交戰役 session 併入。併入後再跑 tools/battles/verify_quotes.py、crosscheck.py、必要時 osm_lookup.py。",
            "candidates": items,
        })
    g = paths.load_json(stage / "gaps-candidates.json", {}) or {}
    g.update({
        "battle": battle,
        "noFind": nofind,
        "fetch": paths.load_json(Path.home() / "wl-source-cache/battles" / battle / "fetch-status.json", {}) or {},
        "sourcesRejected": (cand_src or {}).get("rejected") or [],
        "conflicts": [{"gapId": c.get("gapId"), "note": c.get("note")} for c in conflicts],
    })
    paths.write_json(stage / "gaps-candidates.json", g)
    paths.write_json(stage / "verify-report.json", rep)
    passed = sum(v.get("pass", 0) + v.get("pass-reuse", 0) for v in rep["byType"].values())
    failed = sum(v.get("fail", 0) for v in rep["byType"].values())
    summary = (
        f"{battle} verify 通過 {passed} 筆、失敗 {failed} 筆、"
        f"rejects {len(rep['rejects'])}、noFind {len(nofind)}、升級／交辦 {len(rep['escalate'])}"
    )
    return rep, summary
