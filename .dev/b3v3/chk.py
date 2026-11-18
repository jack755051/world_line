import json, subprocess, sys
from pathlib import Path
B = Path("data/seed/leaders/b3-trial"); a, b = int(sys.argv[1]), int(sys.argv[2])
out = Path(".dev/b3v3/chk"); out.mkdir(exist_ok=True)
tot = {"people":0,"min_fail":0,"returned":0}; short=[]; nogap=[]
for n in range(a, b+1):
    d = B/"full/v3"/f"batch{n:03d}"; t = d.name
    r = subprocess.run([sys.executable,"-I",str(B/"verify.py"),str(d/"research.json"),"--report",str(out/f"{t}-verify.json")],capture_output=True,text=True)
    vr = json.load(open(out/f"{t}-verify.json"))
    subprocess.run([sys.executable,"-I",str(B/"full/v3/check_min.py"),str(d/"research.json"),"--out",str(out/f"{t}-min.json")],capture_output=True)
    mn = json.load(open(out/f"{t}-min.json")); rv = json.load(open(d/"review.json")); res = json.load(open(d/"research.json"))
    ret = [p.get("key") or p.get("name") for p in rv.get("people",[]) if p.get("verdict")=="returned"]
    fails = mn.get("failingKeys",[])
    for p in mn["people"]:
        if not p["meetsMinimum"] and (p["paragraphs"]<3 or p["zhChars"]<300): short.append(p["key"])
        if p.get("termsMissing"): nogap.append((p["key"],p["termsMissing"]))
    tot["people"]+=len(res["people"]); tot["min_fail"]+=len(fails); tot["returned"]+=len(ret)
    print(t, r.returncode, vr.get("ok"), vr.get("rawChecked"), len(res["people"]), fails, ret, sep=" | ")
print(tot); print("short", short); print("missing-end-no-gap", nogap)
