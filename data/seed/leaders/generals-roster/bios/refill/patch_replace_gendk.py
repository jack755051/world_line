#!/usr/bin/env python3
"""generals.dk 替換（Tai 2026-11-13 10:32 決定，World Line 主管轉達；禁用依據：主管 2026-11-12 22:08，個人網站）。
把替換 session 產出的 replace.json 套進某批 research.json：
- 新增替代來源（key 前綴 rg-；grade A／B／C，C 須具名作者或機構；generals.dk、Wikipedia／Wikidata／百度／維基類一律拒收）。
- 對指定段落／職位新增 citation；新來源與既有職稱／任期不同時「以新來源為準」改值，改前改後記在 person.sourceReplaceLog。
- 本批所有 generals.dk citation（含 gap candidateCitations）一律移除；generals.dk source 與 rawmap 條目移除。
- 移除後沒有任何 citation 的職位：移出 positions，改記為 gap（gapKind not_found，note「待查證：…」，原職位內容存 heldItem）；段落不可變成 0 citation（報錯）。
- 先在暫存目錄跑 verify.py（含 zh_trad 正體檢查與引文逐字比對），通過才寫回；--apply 時把 fetches 寫入 ~/wl-source-cache/manifest.jsonl（含 sha256）。
用法（repo 根目錄）：
  python3 -I data/seed/leaders/generals-roster/bios/refill/patch_replace_gendk.py --check|--apply <TIER> <NN> <replace.json>
  python3 -I data/seed/leaders/generals-roster/bios/refill/patch_replace_gendk.py --check|--apply <TIER> <NN> -   （無替代來源，只移除 generals.dk）
replace.json：
{"sources": {"rg-x": {title, authors, publisher, published_text, url, archive_url, catalog_id, license_code, grade, gradeBasis}},
 "fetches": [{"sourceKey","url","file"(~/wl-source-cache 內 .txt),"html","fetchedAt"}],
 "people": {"<key>": {"items": [{"section": "positions|paragraphs|roleCandidates", "key": "<職位 key>" 或 "ord": <段落序>,
     "addCitations": [<citation>], "set": {"title"|"organization"|"period"|"startPrecision"|"endPrecision"|"heading"|"body": 新值},
     "diff": "與既有值不同之處（說明）", "basis": "<rg- sourceKey>"}],
   "addGaps": [{"target": "position:<key>", "gapKind": "not_found", "note": "待查證：…"}],
   "addSearchLog": [...]}}}
"""
import json, sys, shutil, subprocess, tempfile, hashlib, datetime
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
BIOS = HERE.parent
VERIFY = BIOS.parent.parent / "b3-trial" / "verify.py"
CACHE = Path.home() / "wl-source-cache"
TZ = datetime.timezone(datetime.timedelta(hours=8))
NOW = datetime.datetime.now(TZ).replace(microsecond=0).isoformat()
TODAY = NOW[:10]
RUN_ID = "gendk-replace-2026-11-13"
BANNED = ("generals.dk",)
BAD_URL = ("wikipedia.org", "wikidata.org", "baidu.com", "wikiwand", "fandom.com")
SET_OK = {"positions": {"title", "organization", "period", "startPrecision", "endPrecision"},
          "roleCandidates": {"title", "organization", "period", "startPrecision", "endPrecision"},
          "paragraphs": {"heading", "body", "period", "periodStartPrecision", "periodEndPrecision"}}


def host_banned(s):
    for u in ((s or {}).get("url"), (s or {}).get("archive_url")):
        h = ((urlparse(u).hostname or "") if u else "").lower()
        if any(h == b or h.endswith("." + b) for b in BANNED):
            return True
    return False


def fmt_of(raw):
    d = json.loads(raw)
    for ind in (1, 2, None):
        for ea in (False, True):
            if json.dumps(d, ensure_ascii=ea, indent=ind) == raw.rstrip("\n"):
                return ind, ea, raw.endswith("\n")
    return 1, False, raw.endswith("\n")


def dump(d, f):
    return json.dumps(d, ensure_ascii=f[1], indent=f[0]) + ("\n" if f[2] else "")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest() if p and Path(p).exists() else None


def find_item(p, it):
    sec = it.get("section")
    if sec not in SET_OK:
        return None, sec
    if sec == "paragraphs":
        return next((x for x in p.get(sec) or [] if x.get("ord") == it.get("ord")), None), sec
    return next((x for x in p.get(sec) or [] if x.get("key") == it.get("key")), None), sec


def patch(d, rawmap, rp, errs):
    srcs = d.setdefault("sources", {})
    summary = {"added_sources": [], "replaced": {}, "removed": {}, "unverified": [], "changes": []}
    for k, s in (rp.get("sources") or {}).items():
        s = dict(s); s["addedAt"] = NOW; s["addedBy"] = RUN_ID
        if not k.startswith("rg-"):
            errs.append(f"新 source key 須以 rg- 開頭：{k}")
        if k in srcs:
            errs.append(f"source key 已存在：{k}"); continue
        if host_banned(s):
            errs.append(f"source {k} 為 generals.dk（禁用）")
        if any(b in (s.get("url") or "").lower() for b in BAD_URL):
            errs.append(f"source {k} 網址屬禁用來源：{s.get('url')}")
        if s.get("grade") not in ("A", "B", "C"):
            errs.append(f"source {k} grade 必須是 A／B／C：{s.get('grade')}")
        if s.get("grade") == "C" and not (s.get("authors") or s.get("publisher")):
            errs.append(f"source {k} 為 C 級但 authors／publisher 皆空")
        srcs[k] = s; summary["added_sources"].append(k)
    for fe in rp.get("fetches") or []:
        k, f = fe.get("sourceKey"), fe.get("file")
        if not k or not f or not fe.get("url"):
            errs.append(f"fetches 缺 sourceKey／file／url：{fe}"); continue
        fp = Path(f).expanduser().resolve()
        if CACHE.resolve() not in fp.parents or not fp.exists():
            errs.append(f"原文檔須存在於 ~/wl-source-cache/：{f}"); continue
        if k not in srcs:
            errs.append(f"fetches 的 sourceKey 不在 sources：{k}"); continue
        rawmap[k] = str(fp)
    bad = {k for k, s in srcs.items() if host_banned(s)}
    byk = {p.get("key"): p for p in d.get("people") or []}
    for key, add in (rp.get("people") or {}).items():
        p = byk.get(key)
        if p is None:
            errs.append(f"人物不在本批：{key}"); continue
        for it in add.get("items") or []:
            x, sec = find_item(p, it)
            if x is None:
                errs.append(f"{key} 找不到 {sec}:{it.get('key', it.get('ord'))}"); continue
            for c in it.get("addCitations") or []:
                if c.get("sourceKey") in bad:
                    errs.append(f"{key} 新 citation 用了 generals.dk：{c.get('sourceKey')}")
                if c.get("sourceKey") not in srcs:
                    errs.append(f"{key} citation sourceKey 不存在：{c.get('sourceKey')}")
                x.setdefault("citations", []).append(c)
            st = it.get("set") or {}
            if st:
                body_only = sec == "paragraphs" and set(st) <= {"body", "heading"}
                if not it.get("diff") or (not body_only and (not it.get("basis") or it["basis"] not in srcs)):
                    errs.append(f"{key} {sec}:{it.get('key', it.get('ord'))} 改值須附 diff 說明；職稱／任期改值另須 basis（來源 key）")
                ch = {}
                for f_, v in st.items():
                    if f_ not in SET_OK[sec]:
                        errs.append(f"{key} {sec} 不可改欄位 {f_}"); continue
                    if x.get(f_) != v:
                        ch[f_] = {"before": x.get(f_), "after": v}; x[f_] = v
                if ch:
                    log = {"run": RUN_ID, "on": TODAY, "section": sec, "item": it.get("key", it.get("ord")), "basis": it.get("basis"),
                           "diff": it.get("diff"), "changes": ch, "rule": "新來源與既有值不同時以新來源為準（Tai 2026-11-13 10:32）"}
                    p.setdefault("sourceReplaceLog", []).append(log); summary["changes"].append({"person": key, **log})
        have = {(g.get("target"), g.get("note")) for g in p.get("gaps") or []}
        for g in add.get("addGaps") or []:
            if not str(g.get("note") or "").startswith("待查證："):
                errs.append(f"{key} addGaps note 須以「待查證：」開頭：{g.get('note')}"); continue
            if (g.get("target"), g.get("note")) in have:
                continue
            g = dict(g); g.setdefault("gapKind", "not_found"); g.setdefault("candidateCitations", []); g.setdefault("checkedOn", TODAY); g["by"] = RUN_ID
            p.setdefault("gaps", []).append(g); have.add((g.get("target"), g.get("note")))
            summary.setdefault("addedGaps", []).append(f"{key} {g.get('target')}：{g.get('note')}")
        p.setdefault("searchLog", []).extend(add.get("addSearchLog") or [])
    # 移除所有 generals.dk citation
    for p in d.get("people") or []:
        key = p.get("key")
        for sec in ("paragraphs", "positions", "roleCandidates"):
            keep_items = []
            for x in p.get(sec) or []:
                cs = x.get("citations") or []
                n_bad = sum(1 for c in cs if c.get("sourceKey") in bad)
                if n_bad:
                    x["citations"] = [c for c in cs if c.get("sourceKey") not in bad]
                    summary["removed"][key] = summary["removed"].get(key, 0) + n_bad
                if n_bad and not x["citations"]:
                    if sec == "paragraphs":
                        errs.append(f"{key} 段{x.get('ord')} 移除 generals.dk 後沒有 citation（段落須補來源或改寫）"); keep_items.append(x); continue
                    tgt = ("position:" if sec == "positions" else "position:") + str(x.get("key"))
                    held = {k2: v2 for k2, v2 in x.items() if k2 != "citations"}
                    p.setdefault("gaps", []).append({"target": tgt, "gapKind": "not_found",
                        "note": "待查證：此職位原僅 generals.dk 支撐（個人網站，主管 2026-11-12 22:08 禁用），替換時查無 A／B／具名 C 來源；職位暫移出 positions，原內容存 heldItem",
                        "candidateCitations": [], "checkedOn": TODAY, "heldItem": held, "heldSection": sec, "by": RUN_ID})
                    summary["unverified"].append(f"{key} {sec}:{x.get('key')}")
                    continue
                keep_items.append(x)
            if sec in p:
                p[sec] = keep_items
        for g in p.get("gaps") or []:
            cc = g.get("candidateCitations") or []
            n_bad = sum(1 for c in cc if c.get("sourceKey") in bad)
            if n_bad:
                g["candidateCitations"] = [c for c in cc if c.get("sourceKey") not in bad]
                summary["removed"][key] = summary["removed"].get(key, 0) + n_bad
    # replaced counts（本次新增 rg- citation 數）
    for key, add in (rp.get("people") or {}).items():
        summary["replaced"][key] = sum(len(it.get("addCitations") or []) for it in add.get("items") or [])
    # 移除 generals.dk sources 與 rawmap 條目（已無引用）
    blob = json.dumps(d.get("people"), ensure_ascii=False)
    for k in sorted(bad):
        if f'"sourceKey": "{k}"' in blob:
            errs.append(f"{k} 仍被引用，未移除")
            continue
        srcs.pop(k, None); rawmap.pop(k, None)
    summary["removed_sources"] = sorted(bad)
    return summary


def main():
    mode, tier, nn, rpp = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    bdir = BIOS / tier / f"batch{nn}"
    rj = bdir / "research.json"
    raw = rj.read_text(encoding="utf-8"); f = fmt_of(raw); d = json.loads(raw)
    rmp = bdir / (d.get("rawMap") or "rawmap.json")
    rraw = rmp.read_text(encoding="utf-8"); rf_fmt = fmt_of(rraw); rawmap = json.loads(rraw)
    errs = []
    try:
        rp = {} if rpp == "-" else json.loads(Path(rpp).read_text(encoding="utf-8"))
    except Exception as e:
        print(json.dumps({"ok": False, "errors": [f"replace.json 讀取失敗：{e}"]}, ensure_ascii=False)); return 1
    summ = patch(d, rawmap, rp, errs)
    res = {"ok": False, "mode": mode, "batch": f"{tier}/{nn}", "errors": errs, "summary": summ}
    with tempfile.TemporaryDirectory(prefix="wl-gendk-") as td:
        tj = Path(td) / "research.json"
        tj.write_text(dump(d, f), encoding="utf-8")
        (Path(td) / rmp.name).write_text(dump(rawmap, rf_fmt), encoding="utf-8")
        v = subprocess.run([sys.executable, "-I", str(VERIFY), str(tj), "--report", str(Path(td) / "v.json")], capture_output=True, text=True)
        res["verify_rc"] = v.returncode
        try:
            res["verify_errors"] = (json.loads((Path(td) / "v.json").read_text()).get("errors") or [])[:40]
        except Exception:
            res["verify_errors"] = [(v.stdout + v.stderr)[-1500:]]
    res["ok"] = not errs and res["verify_rc"] == 0
    if mode == "--apply" and res["ok"]:
        rj.write_text(dump(d, f), encoding="utf-8")
        rmp.write_text(dump(rawmap, rf_fmt), encoding="utf-8")
        subprocess.run([sys.executable, "-I", str(VERIFY), str(rj), "--report", str(bdir / "verify-report.json")], capture_output=True, text=True)
        with open(CACHE / "manifest.jsonl", "a", encoding="utf-8") as m:
            for fe in rp.get("fetches") or []:
                m.write(json.dumps({"batch": f"{tier}/batch{nn}", "sourceKey": fe["sourceKey"], "url": fe.get("url"), "txt": fe.get("file"),
                                    "html": fe.get("html"), "sha256_txt": sha(fe.get("file")), "sha256_html": sha(fe.get("html")),
                                    "fetchedAt": fe.get("fetchedAt"), "recordedAt": NOW, "run": RUN_ID}, ensure_ascii=False) + "\n")
        res["applied"] = True
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
