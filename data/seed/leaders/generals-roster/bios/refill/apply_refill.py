#!/usr/bin/env python3
"""將領生平「只補缺欄位」：把補跑 session 產出的 refill.json **加法式**併入既有 research.json（ARCHITECTURE §20；Tai 2026-11-12 21:43）。
規則（程式強制，不靠模型自律）：
- 不覆寫既有值：period.start／end 只在原本為空時才填；既有 positions／roleCandidates／paragraphs／sources 不改不刪。
- 新增的 source key 不可與既有 key 衝突；每筆 citation 的 sourceKey 必須存在，grade 必須與 sources[key].grade 一致，且只能 A／B／C（C 須有 authors 或 publisher）。
- 新抓原文必須在 ~/wl-source-cache/ 底下，fetches 記錄 sourceKey→url→檔案（Q5），正式套用時寫入 ~/wl-source-cache/manifest.jsonl（含 sha256）。
- 填到迄日（或起日）的職位，原本「待查證：缺迄日／缺起日」gap 移到 person.resolvedGaps（保留紀錄）。
- 新人（只限 selection 有、research.json 沒有者，例 Guderian）：以 selection 建骨架（key、bioId、name、nameZh 取自 selection）再套加法。
- 套用後跑 check_min 與 verify.py；--check 模式只在暫存目錄試套，不動 repo。
用法（repo 根目錄）：
  python3 -I data/seed/leaders/generals-roster/bios/refill/apply_refill.py --check <TIER> <NN> <refill.json>
  python3 -I data/seed/leaders/generals-roster/bios/refill/apply_refill.py --apply <TIER> <NN> <refill.json>
輸出一行 JSON：{"ok":bool,"errors":[...],"before":{key:min},"after":{key:min},"verify_rc":int,...}
"""
import json, sys, shutil, subprocess, tempfile, hashlib, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIOS = HERE.parent
sys.path.insert(0, str(BIOS))
from check_min import check  # noqa: E402
VERIFY = BIOS.parent.parent / "b3-trial" / "verify.py"
CACHE = Path.home() / "wl-source-cache"
TODAY = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")
RUN_ID = "refill-2026-11-12"
# 主管 2026-11-12 22:08：generals.dk（個人網站）禁用；只對生效後開跑的批次擋新增來源（與 verify.py DATED_BANNED_HOSTS 同一時間）
DATED_BANNED_HOSTS = {"generals.dk": "2026-11-12T22:10:05+08:00"}
STATE = BIOS.parents[4] / ".dev" / "cc-person-refill.state.json"


def batch_started(tier, nn):
    """補跑批開跑時間（ISO，+08:00）；state 沒有就用現在。"""
    try:
        st = json.loads(STATE.read_text(encoding="utf-8"))
        v = (st.get("batches") or {}).get(f"{tier}/{nn}", {}).get("started")
        if v:
            return datetime.datetime.strptime(v.replace(" CST", ""), "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    except Exception:
        pass
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).replace(microsecond=0).isoformat()


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


def merge(d, rawmap, rf, sel_people, errs, started=None):
    srcs = d.setdefault("sources", {})
    for k, s in (rf.get("sources") or {}).items():
        s = dict(s)
        s.setdefault("addedAt", started); s.setdefault("addedBy", RUN_ID)
        from urllib.parse import urlparse
        for u in (s.get("url"), s.get("archive_url")):
            host = ((urlparse(u).hostname or "") if u else "").lower()
            for h, since in DATED_BANNED_HOSTS.items():
                if (host == h or host.endswith("." + h)) and started and started >= since:
                    errs.append(f"source {k} 網域已禁用：{h}（主管 2026-11-12 22:08，個人網站）")
        if k in srcs:
            if {x: y for x, y in srcs[k].items() if x not in ("addedAt", "addedBy")} != {x: y for x, y in s.items() if x not in ("addedAt", "addedBy")}:
                errs.append(f"source key 已存在且內容不同：{k}（新 key 請用 rf- 前綴）")
            continue
        if s.get("grade") not in ("A", "B", "C"):
            errs.append(f"source {k} grade 必須是 A／B／C：{s.get('grade')}")
        if s.get("grade") == "C" and not (s.get("authors") or s.get("publisher")):
            errs.append(f"source {k} 為 C 級但 authors／publisher 皆空")
        u = (s.get("url") or "").lower()
        if any(b in u for b in ("wikipedia.org", "wikidata.org", "baidu.com", "wikiwand", "fandom.com")):
            errs.append(f"source {k} 網址屬禁用來源：{u}")
        srcs[k] = s
    for fe in rf.get("fetches") or []:
        k, f = fe.get("sourceKey"), fe.get("file")
        if not k or not f:
            errs.append(f"fetches 缺 sourceKey／file：{fe}"); continue
        fp = Path(f).expanduser().resolve()
        if CACHE.resolve() not in fp.parents:
            errs.append(f"原文檔不在 ~/wl-source-cache/：{f}"); continue
        if not fp.exists():
            errs.append(f"原文檔不存在：{f}"); continue
        if not fe.get("url"):
            errs.append(f"fetches 缺 url：{k}")
        if k in rawmap and Path(rawmap[k]) != fp and rawmap[k] != str(fp):
            errs.append(f"rawmap 已有 {k} 指向別的檔"); continue
        rawmap[k] = str(fp)
    people = d.setdefault("people", [])
    byk = {p.get("key"): p for p in people}
    for key, add in (rf.get("people") or {}).items():
        p = byk.get(key)
        if p is None:
            q = sel_people.get(key)
            if not q:
                errs.append(f"人物 {key} 不在本批 research.json，也不在本批 selection"); continue
            pf = add.get("personFields") or {}
            p = {"key": key, "bioId": q.get("bio_id"), "name": pf.get("name") or q.get("name_original"),
                 "nameZh": q.get("name_zh") or "待查證", "recordIds": [], "thickness": pf.get("thickness") or "薄",
                 "paragraphs": [], "positions": [], "roleCandidates": [], "gaps": [], "searchLog": []}
            people.append(p); byk[key] = p
        for fp_ in add.get("fillPeriods") or []:
            sec = fp_.get("section") or "positions"
            if sec not in ("positions", "roleCandidates"):
                errs.append(f"{key} fillPeriods section 錯：{sec}"); continue
            item = next((x for x in p.get(sec) or [] if x.get("key") == fp_.get("key")), None)
            if item is None:
                errs.append(f"{key} fillPeriods 找不到 {sec}:{fp_.get('key')}（新職位請用 addPositions）"); continue
            per = item.setdefault("period", {"start": None, "end": None})
            filled = []
            for end in ("start", "end"):
                v = fp_.get(end)
                if not v:
                    continue
                if per.get(end):
                    if per[end] != v:
                        errs.append(f"{key} {sec}:{item['key']} 已有 {end}={per[end]}，不可覆寫為 {v}")
                    continue
                per[end] = v
                prec = fp_.get(end + "Precision")
                if prec and not item.get(end + "Precision"):
                    item[end + "Precision"] = prec
                filled.append(end)
            if not fp_.get("citations"):
                errs.append(f"{key} {sec}:{item['key']} 補日期必須附 citation")
            item.setdefault("citations", []).extend(fp_.get("citations") or [])
            if filled:
                pre = ("position:" if sec == "positions" else "role:") + item["key"]
                keep, moved = [], []
                for g in p.get("gaps") or []:
                    n = g.get("note") or ""
                    hit = g.get("target") == pre and (("end" in filled and n.startswith("待查證：缺迄日")) or ("start" in filled and n.startswith("待查證：缺起日")))
                    (moved if hit else keep).append(g)
                if moved:
                    p["gaps"] = keep
                    for g in moved:
                        g = dict(g); g["resolvedOn"] = TODAY; g["resolvedBy"] = RUN_ID
                        p.setdefault("resolvedGaps", []).append(g)
        for sec, fld in (("positions", "addPositions"), ("roleCandidates", "addRoleCandidates")):
            have = {x.get("key") for x in p.get(sec) or []}
            for x in add.get(fld) or []:
                if x.get("key") in have:
                    errs.append(f"{key} {fld} key 已存在：{x.get('key')}（補既有職位日期請用 fillPeriods）"); continue
                p.setdefault(sec, []).append(x); have.add(x.get("key"))
        if add.get("addParagraphs"):
            n = max([g.get("ord") or 0 for g in p.get("paragraphs") or []] + [0])
            for g in add["addParagraphs"]:
                n += 1; g = dict(g); g["ord"] = n
                p.setdefault("paragraphs", []).append(g)
        have_t = {g.get("target") for g in p.get("gaps") or []}
        for g in add.get("addGaps") or []:
            if g.get("target") in have_t:  # 同 target 已有 gap：不重複新增（查詢紀錄在 searchLog）
                continue
            p.setdefault("gaps", []).append(g); have_t.add(g.get("target"))
        p.setdefault("searchLog", []).extend(add.get("addSearchLog") or [])
        p.setdefault("refill", []).append({"run": RUN_ID, "on": TODAY})
    # citation 檢查（只檢查新增的引文所屬人物整體）
    for key in (rf.get("people") or {}):
        p = byk.get(key)
        if not p:
            continue
        for sec in ("paragraphs", "positions", "roleCandidates"):
            for x in p.get(sec) or []:
                for c in x.get("citations") or []:
                    s = srcs.get(c.get("sourceKey"))
                    if s is None:
                        errs.append(f"{key} citation sourceKey 不存在：{c.get('sourceKey')}")
                    elif c.get("grade") and s.get("grade") and c["grade"] != s["grade"] and c.get("sourceKey", "").startswith("rf-"):
                        errs.append(f"{key} citation grade {c['grade']} 與 source {c['sourceKey']} grade {s['grade']} 不一致")


def main():
    mode, tier, nn, rfp = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
    bdir = BIOS / tier / f"batch{nn}"
    rj = bdir / "research.json"
    raw = rj.read_text(encoding="utf-8"); f = fmt_of(raw); d = json.loads(raw)
    rmp = bdir / (d.get("rawMap") or "rawmap.json")
    rraw = rmp.read_text(encoding="utf-8"); rf_fmt = fmt_of(rraw); rawmap = json.loads(rraw)
    sel = json.loads((BIOS / "selection.json").read_text(encoding="utf-8"))
    sb = next((b for b in sel[tier] if b["batch"] == nn), {"people": []})
    sel_people = {q["key"]: q for q in sb["people"]}
    errs = []
    try:
        rf = json.loads(rfp.read_text(encoding="utf-8"))
    except Exception as e:
        print(json.dumps({"ok": False, "errors": [f"refill.json 讀取失敗：{e}"]}, ensure_ascii=False)); return 1
    before = {p["key"]: check(p) for p in d.get("people") or []}
    started = batch_started(tier, nn)
    merge(d, rawmap, rf, sel_people, errs, started)
    after = {p["key"]: check(p) for p in d.get("people") or [] if p["key"] in (rf.get("people") or {})}
    res = {"ok": False, "mode": mode, "errors": errs,
           "before": {k: {x: before[k][x] for x in ("paragraphs", "zhChars", "termsFull", "termsFlagged", "termsMissing", "hasCommand", "hasBattle", "meetsMinimum")} for k in after if k in before},
           "after": {k: {x: v[x] for x in ("paragraphs", "zhChars", "termsFull", "termsFlagged", "termsMissing", "hasCommand", "hasBattle", "meetsMinimum")} for k, v in after.items()}}
    with tempfile.TemporaryDirectory(prefix="wl-refill-") as td:
        tj = Path(td) / "research.json"
        tj.write_text(dump(d, f), encoding="utf-8")
        (Path(td) / rmp.name).write_text(dump(rawmap, rf_fmt), encoding="utf-8")
        v = subprocess.run([sys.executable, "-I", str(VERIFY), str(tj), "--report", str(Path(td) / "verify-report.json")], capture_output=True, text=True)
        res["verify_rc"] = v.returncode
        try:
            vr = json.loads((Path(td) / "verify-report.json").read_text())
            res["verify_errors"] = (vr.get("errors") or [])[:40]
        except Exception:
            res["verify_errors"] = [(v.stdout + v.stderr)[-1500:]]
    res["ok"] = not errs and res["verify_rc"] == 0
    if mode == "--apply" and res["ok"]:
        rj.write_text(dump(d, f), encoding="utf-8")
        rmp.write_text(dump(rawmap, rf_fmt), encoding="utf-8")
        subprocess.run([sys.executable, "-I", str(VERIFY), str(rj), "--report", str(bdir / "verify-report.json")], capture_output=True, text=True)
        rows = [check(p) for p in d["people"]]
        (bdir / "min-check.refill.json").write_text(json.dumps({"rule": "check_min after refill " + RUN_ID, "people": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        CACHE.mkdir(parents=True, exist_ok=True)
        with open(CACHE / "manifest.jsonl", "a", encoding="utf-8") as m:
            for fe in rf.get("fetches") or []:
                m.write(json.dumps({"batch": f"{tier}/batch{nn}", "sourceKey": fe["sourceKey"], "url": fe.get("url"), "txt": fe.get("file"),
                                    "html": fe.get("html"), "sha256_txt": sha(fe.get("file")), "sha256_html": sha(fe.get("html")),
                                    "fetchedAt": fe.get("fetchedAt"), "recordedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "run": RUN_ID}, ensure_ascii=False) + "\n")
        res["applied"] = True
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
