#!/usr/bin/env python3
"""禁用網域替換（主管 2026-11-13 11:31 禁用 historyofwar.org、rafweb.org 等；清單見 pending-banned-domains-20261113.md）。
第一階段：只套用 status == "replaced" 的項目（替代來源直接支撐原主張，正文與日期不變）。
降精度、說法衝突、查無三類另批處理（要改正文或職位起訖，需逐筆確認）。

輸入：補查 session 產出的 result.json（每組一份），格式見 PROMPT 同目錄 banned-replace-20261114/README.md。
做法（每個 research.json）：
- 把 path 指到的禁用來源 citation 換成 replacements（一換多時插在原位置）。
- 新來源寫進 sources（addedAt／addedBy）；原文（多檔則串接）存到 ~/wl-source-cache/banned-<T>-b<NN>/<key>.txt，rawmap 用絕對路徑，manifest.jsonl 記 sha256。
- 等級統一（Tai 2026-11-14 同意）：讀到的是第三方轉錄本（HyperWar、NZETC、Thayer、第三方公報站等）→ 原著 A 一律記 B；
  Wayback 存檔的原頁不算轉錄。具名學生演講稿不收（wellington-college-anzac-2026）。
- 本檔若已無任何 citation 引用某禁用來源，連同 rawmap 條目一起移除。
- 先在暫存目錄跑 b3-trial/verify.py，通過才寫回。
用法（repo 根目錄）：
  python3 -I data/seed/leaders/generals-roster/bios/refill/patch_replace_banned.py --check|--apply <result.json> [<result.json> ...]
"""
import json, sys, re, shutil, subprocess, tempfile, hashlib, datetime, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIOS = HERE.parent
REPO = BIOS.parents[4]
sys.path.insert(0, str(REPO / "tools"))
from source_policy import banned  # noqa: E402

VERIFY = BIOS.parent.parent / "b3-trial" / "verify.py"
CACHE = Path.home() / "wl-source-cache"
TZ = datetime.timezone(datetime.timedelta(hours=8))
NOW = datetime.datetime.now(TZ).replace(microsecond=0).isoformat()
RUN_ID = "banned-replace-2026-11-14"
ACCESSED = "2026-11-14"
REJECT = {"wellington-college-anzac-2026"}
TRANSCRIBED = re.compile(r"ibiblio\.org/hyperwar|nzetc\.victoria\.ac\.nz|penelope\.uchicago\.edu|gazette\.howison\.co\.nz|generalstaff\.org")


def fmt_of(raw):
    d = json.loads(raw)
    for ind in (1, 2, None):
        for ea in (False, True):
            if json.dumps(d, ensure_ascii=ea, indent=ind) == raw.rstrip("\n"):
                return ind, ea, raw.endswith("\n")
    return 1, False, raw.endswith("\n")


def dump(d, f):
    return json.dumps(d, ensure_ascii=f[1], indent=f[0]) + ("\n" if f[2] else "")


def quote_lang(q):
    if re.search(r"[Ѐ-ӿ]", q): return "ru"
    if re.search(r"[àâçéèêëîïôûùüÿœ]", q) or re.search(r"\b(puis|commandant|de la|en juin)\b", q): return "fr"
    if re.search(r"[äöüß]", q): return "de"
    return "en"


def clean_source(s, key):
    url = (s.get("url") or "").split("（")[0].strip()
    extra = (s.get("url") or "")[len(url):].strip()
    basis = s.get("gradeBasis") or ""
    grade = s.get("grade")
    if TRANSCRIBED.search(url) and grade == "A":
        grade = "B"
        basis += "；讀到的是第三方轉錄本，原著 A 依轉錄降為 B（Tai 2026-11-14）"
    if extra:
        basis += f"；其他章節／頁：{extra}"
    out = {"title": s.get("title"), "authors": s.get("authors") or [], "publisher": s.get("publisher"),
           "published_text": s.get("published_text"), "url": url, "archive_url": None, "catalog_id": None,
           "license_code": None, "grade": grade, "gradeBasis": basis, "addedAt": NOW, "addedBy": RUN_ID}
    if banned(url):
        raise SystemExit(f"新來源落在禁用網域：{key} {url}")
    return out


def resolve(o, path):
    parts = re.findall(r"/(\w+)(?:\[(\d+)\])?", path)
    for k, i in parts[:-1]:
        o = o[k]
        if i: o = o[int(i)]
    k, i = parts[-1]
    return o[k], int(i)


def main(argv):
    if len(argv) < 2 or argv[0] not in ("--check", "--apply"):
        print(__doc__); return 2
    apply = argv[0] == "--apply"
    results = [(Path(p), json.load(open(p))) for p in argv[1:]]
    # 所有組的新來源（跨組、跨人共用 key）
    allnew = {}
    for rp, r in results:
        for n, p in r["people"].items():
            for k, s in (p.get("newSources") or {}).items():
                arch = [a if a.startswith("/") else str(rp.parent / a) for a in s.get("archive") or []]
                allnew.setdefault(k, (s, arch))
    # 依檔案分組
    byfile = collections.defaultdict(list)
    for rp, r in results:
        for n, p in r["people"].items():
            for it in p["items"]:
                if it["status"] != "replaced": continue
                reps = [x for x in it.get("replacements", []) if x["sourceKey"] not in REJECT]
                if not reps: continue
                byfile[p["file"]].append((p["personKey"], it["path"], it["bannedSourceKey"], reps, rp))
    report, errors = [], []
    tmp = Path(tempfile.mkdtemp(prefix="banned-replace-"))
    for rel, items in sorted(byfile.items()):
        rj = BIOS / rel
        raw = rj.read_text(); f = fmt_of(raw); d = json.loads(raw)
        rmp = rj.parent / "rawmap.json"; rm = json.loads(rmp.read_text()) if rmp.exists() else {}
        tier, nn = rel.split("/")[0], rel.split("/")[1].replace("batch", "")
        cdir = CACHE / f"banned-{tier}-b{nn}"
        fetches = []
        # 由大到小的 index 取代，避免位移
        def sortkey(t):
            return [int(x) for x in re.findall(r"\[(\d+)\]", t[1])]
        replaced = 0
        for pk, path, bkey, reps, rp in sorted(items, key=sortkey, reverse=True):
            person = next(x for x in d["people"] if x["key"] == pk)
            lst, idx = resolve(person, path)
            old = lst[idx]
            if old.get("sourceKey") != bkey:
                errors.append(f"{rel} {pk}{path}: 預期 {bkey}，實際 {old.get('sourceKey')}"); continue
            new = []
            for x in reps:
                k = x["sourceKey"]
                if k not in d["sources"]:
                    if k in allnew:
                        s, arch = allnew[k]
                        d["sources"][k] = clean_source(s, k)
                        cdir.mkdir(parents=True, exist_ok=True) if apply else None
                        txt = cdir / f"{k}.txt"
                        body = "\n\n".join(Path(a).read_text(encoding="utf-8", errors="replace") for a in arch)
                        (txt.write_text(body) if apply else None)
                        tmpt = tmp / f"{tier}-{nn}-{k}.txt"; tmpt.write_text(body)
                        rm[k] = str(txt) if apply else str(tmpt)
                        fetches.append({"sourceKey": k, "url": d["sources"][k]["url"], "txt": str(txt),
                                        "sha256_txt": hashlib.sha256(body.encode()).hexdigest()})
                    else:  # 其他批次檔已登記的來源（跨檔重用）
                        hit = None
                        for other in BIOS.glob("[SA]/batch*/research.json"):
                            od = json.loads(other.read_text())
                            if k in (od.get("sources") or {}):
                                om = json.loads((other.parent / "rawmap.json").read_text())
                                hit = (od["sources"][k], om.get(k), other.parent); break
                        if not hit:
                            errors.append(f"{rel}: 找不到來源 {k}"); continue
                        src, rmv, odir = hit
                        d["sources"][k] = dict(src, addedAt=NOW, addedBy=RUN_ID)
                        rm[k] = rmv if rmv and rmv.startswith("/") else str(odir / "raw" / (rmv or ""))
                grade = d["sources"][k]["grade"]
                new.append({"sourceKey": k, "locator": old.get("locator") or "全文", "quote": x["quote"],
                            "quoteLang": quote_lang(x["quote"]), "evidenceNote": None, "accessedOn": ACCESSED,
                            "grade": grade, "datePrecision": x.get("datePrecision") if x.get("datePrecision") is not None else old.get("datePrecision"),
                            "claimSpan": old.get("claimSpan"), "policyVersion": old.get("policyVersion") or d.get("policyVersion")})
            lst[idx:idx + 1] = new
            replaced += 1
        # 不再被引用的禁用來源移除
        used = collections.Counter(c for c in re.findall(r'"sourceKey": "([^"]+)"', json.dumps(d["people"], ensure_ascii=False)))
        dropped = [k for k, s in list(d["sources"].items()) if banned(s.get("url")) and not used[k]]
        for k in dropped:
            d["sources"].pop(k); rm.pop(k, None)
        still = sorted(k for k, s in d["sources"].items() if banned(s.get("url")))
        # 驗證（暫存）
        t = tmp / rel.replace("/", "-"); t.mkdir(parents=True, exist_ok=True)
        (t / "research.json").write_text(dump(d, f)); (t / "rawmap.json").write_text(json.dumps(rm, ensure_ascii=False, indent=1) + "\n")
        dd = json.loads((t / "research.json").read_text()); dd["rawMap"] = "rawmap.json"; (t / "research.json").write_text(dump(dd, f))
        v = subprocess.run([sys.executable, "-I", str(VERIFY), str(t / "research.json"), "--report", str(t / "verify.json")], capture_output=True, text=True)
        vr = json.loads((t / "verify.json").read_text()) if (t / "verify.json").exists() else {}
        report.append({"file": rel, "replacedItems": replaced, "newSources": len(fetches), "droppedBanned": dropped,
                       "stillBanned": still, "verifyOk": vr.get("ok"), "rawChecked": vr.get("rawChecked"),
                       "verifySummary": {k: v for k, v in vr.items() if k not in ("errors", "warnings", "files", "sha256")} if vr else None,
                       "verifyErrors": (vr.get("errors") or [])[:5]})
        if apply and not errors and vr.get("ok"):
            rj.write_text(dump(d, f))
            rmp.write_text(json.dumps(rm, ensure_ascii=False, indent=1) + "\n")
            subprocess.run([sys.executable, "-I", str(VERIFY), str(rj), "--report", str(rj.parent / "verify-report.json")], capture_output=True, text=True)
            with open(CACHE / "manifest.jsonl", "a") as m:
                for fe in fetches:
                    m.write(json.dumps({"batch": f"{tier}/batch{nn}", "run": RUN_ID, **fe}, ensure_ascii=False) + "\n")
    print(json.dumps({"apply": apply, "errors": errors, "files": report}, ensure_ascii=False, indent=1))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
