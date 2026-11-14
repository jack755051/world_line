#!/usr/bin/env python3
"""禁用網域替換第二階段合併（banned-replace-2026-11-14）。
補查 session 在 scratchpad 副本（work/<T>-batch<NN>/research.json＋rawmap.json）上只改自己負責的人物；
本程式把那些人物物件逐人換回 repo 檔案（同檔其他人物不動），新增來源與 rawmap 條目，
原文從副本 rawmap 指向的 .txt 複製到 ~/wl-source-cache/banned-<T>-b<NN>/（rawmap 改指向這裡），
最後移除檔內已無人引用的禁用來源，在暫存目錄跑 b3-trial/verify.py（含逐字比對），全部通過才寫回。
用法（repo 根目錄）：
  python3 -I data/seed/leaders/generals-roster/bios/refill/merge_banned_stage2.py --check|--apply <group_dir>:<remaining.json> [...]
"""
import json, sys, re, shutil, subprocess, tempfile, hashlib, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIOS = HERE.parent
REPO = BIOS.parents[4]
sys.path.insert(0, str(REPO / "tools"))
from source_policy import banned  # noqa: E402

VERIFY = BIOS.parent.parent / "b3-trial" / "verify.py"
CACHE = Path.home() / "wl-source-cache"
RUN_ID = "banned-replace-2026-11-14"


def fmt_of(raw):
    d = json.loads(raw)
    for ind in (1, 2, None):
        for ea in (False, True):
            if json.dumps(d, ensure_ascii=ea, indent=ind) == raw.rstrip("\n"):
                return ind, ea, raw.endswith("\n")
    return 1, False, raw.endswith("\n")


def dump(d, f):
    return json.dumps(d, ensure_ascii=f[1], indent=f[0]) + ("\n" if f[2] else "")


def main(argv):
    if len(argv) < 2 or argv[0] not in ("--check", "--apply"):
        print(__doc__); return 2
    apply = argv[0] == "--apply"
    # rel file -> list of (personKey, work_dir)
    plan = collections.defaultdict(list)
    for spec in argv[1:]:
        gdir, rem = spec.split(":")
        for name, e in json.load(open(rem)).items():
            plan[e["file"]].append((e["personKey"], Path(gdir)))
    errors, report = [], []
    tmp = Path(tempfile.mkdtemp(prefix="banned-merge-"))
    staged = []
    for rel, who in sorted(plan.items()):
        tier, nn = rel.split("/")[0], rel.split("/")[1].replace("batch", "")
        rj = BIOS / rel; raw = rj.read_text(); f = fmt_of(raw); d = json.loads(raw)
        rmp = rj.parent / "rawmap.json"; rm = json.loads(rmp.read_text())
        cdir = CACHE / f"banned-{tier}-b{nn}"
        copies, fetches = [], []
        for pk, gdir in who:
            wd = gdir / "work" / f"{tier}-batch{nn}"
            if not (wd / "research.json").exists():
                errors.append(f"{rel}: 找不到副本 {wd}"); continue
            wdoc = json.loads((wd / "research.json").read_text())
            wrm = json.loads((wd / "rawmap.json").read_text())
            idx = next((i for i, x in enumerate(d["people"]) if x["key"] == pk), None)
            wp = next((x for x in wdoc["people"] if x["key"] == pk), None)
            if idx is None or wp is None:
                errors.append(f"{rel}: 人物 {pk} 不在 repo 或副本"); continue
            d["people"][idx] = wp
            for k, s in wdoc["sources"].items():
                if banned(s.get("url")) and k not in d["sources"]:
                    errors.append(f"{rel}: 副本新增了禁用來源 {k}"); continue
                if k not in d["sources"] or s.get("addedBy") == RUN_ID:
                    d["sources"][k] = s
                if k not in rm or (s.get("addedBy") == RUN_ID and wrm.get(k) and wrm.get(k) != rm.get(k)):
                    src = wrm.get(k)
                    if not src: continue
                    sp = Path(src) if src.startswith("/") else wd / src
                    if not sp.exists():
                        sp2 = Path(wdoc.get("rawDir") or "") / src
                        sp = sp2 if sp2.exists() else sp
                    if not sp.exists():
                        errors.append(f"{rel}: 原文不存在 {k} → {src}"); continue
                    if str(sp).startswith(str(CACHE)):
                        rm[k] = str(sp); continue
                    dst = cdir / f"{k}.txt"
                    copies.append((sp, dst)); rm[k] = str(dst)
                    fetches.append({"sourceKey": k, "url": s.get("url"), "txt": str(dst),
                                    "sha256_txt": hashlib.sha256(sp.read_bytes()).hexdigest()})
        # sourceReplaceLog 裡的「改前」citation 快照：sourceKey 改名為 removedSourceKey 並附網址，
        # 避免稽核把歷史快照當成現行引文，也讓禁用來源定義移除後仍看得出原出處。
        def defang(o):
            if isinstance(o, dict):
                if "sourceKey" in o:
                    k = o.pop("sourceKey"); o["removedSourceKey"] = k
                    o["removedSourceUrl"] = (d["sources"].get(k) or {}).get("url") or o.get("removedSourceUrl")
                for v in o.values(): defang(v)
            elif isinstance(o, list):
                for v in o: defang(v)
        for p in d["people"]:
            if p["key"] in {pk for pk, _ in who}:
                defang(p.get("sourceReplaceLog"))
        # 禁用來源：檔內無人引用就移除
        used =set(re.findall(r'"sourceKey": "([^"]+)"', json.dumps(d["people"], ensure_ascii=False)))
        dropped = [k for k, s in list(d["sources"].items()) if banned(s.get("url")) and k not in used]
        for k in dropped:
            d["sources"].pop(k); rm.pop(k, None)
        still = [k for k, s in d["sources"].items() if banned(s.get("url"))]
        # 暫存驗證：rawmap 指向暫存位置（尚未複製的原文用來源路徑）
        t = tmp / rel.replace("/", "-"); t.mkdir(parents=True)
        trm = dict(rm)
        for sp, dst in copies:
            trm[[k for k, v in rm.items() if v == str(dst)][0]] = str(sp)
        td = json.loads(json.dumps(d)); td["rawMap"] = "rawmap.json"
        (t / "research.json").write_text(dump(td, f)); (t / "rawmap.json").write_text(json.dumps(trm, ensure_ascii=False, indent=1) + "\n")
        subprocess.run([sys.executable, "-I", str(VERIFY), str(t / "research.json"), "--report", str(t / "v.json")], capture_output=True, text=True)
        vr = json.loads((t / "v.json").read_text()) if (t / "v.json").exists() else {}
        report.append({"file": rel, "people": [p for p, _ in who], "droppedBanned": dropped, "stillBanned": still,
                       "newRaw": len(copies), "verifyOk": vr.get("ok"), "rawChecked": vr.get("rawChecked"),
                       "verifyErrors": (vr.get("errors") or [])[:8]})
        if not vr.get("ok") or still:
            errors.append(f"{rel}: verify ok={vr.get('ok')} stillBanned={still}")
        staged.append((rj, d, f, rmp, rm, copies, fetches, tier, nn))
    if apply and not errors:
        for rj, d, f, rmp, rm, copies, fetches, tier, nn in staged:
            for sp, dst in copies:
                dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(sp, dst)
            rj.write_text(dump(d, f)); rmp.write_text(json.dumps(rm, ensure_ascii=False, indent=1) + "\n")
            subprocess.run([sys.executable, "-I", str(VERIFY), str(rj), "--report", str(rj.parent / "verify-report.json")], capture_output=True, text=True)
            with open(CACHE / "manifest.jsonl", "a") as m:
                for fe in fetches:
                    m.write(json.dumps({"batch": f"{tier}/batch{nn}", "run": RUN_ID, **fe}, ensure_ascii=False) + "\n")
    print(json.dumps({"apply": apply and not errors, "errors": errors, "files": report}, ensure_ascii=False, indent=1))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
