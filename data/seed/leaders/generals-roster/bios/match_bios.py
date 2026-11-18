#!/usr/bin/env python3
"""將領 → 既有 leader_bios 比對（Tai 2026-11-13 11:05：為 348 位將領新增生平主檔；不得重複）。
1. QID（只當識別碼，非事實出處）：以 selection 的 name_original 查英文維基條目（redirects），取 pageprops.wikibase_item；
   消歧義頁、查無條目 → 無 QID。英文維基只當索引（§20.6）。
2. QID 與 5442 leader_bios.wikidata_qid 相同 → match_qid（沿用既有 bio）。
3. 無 QID 命中：正規化原文名或中文名與既有 bio 相同 → questionable（列出，不寫）。
4. 都不中 → create（新 bio；wikidata_qid 只存識別碼）。
只 SELECT 5442；輸出 bios/match-bios.json。用法（repo 根目錄）：python3 -I data/seed/leaders/generals-roster/bios/match_bios.py
"""
import json, glob, re, subprocess, time, unicodedata, urllib.parse, urllib.request, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent
UA = "WorldLineResearch/0.1 (index lookup only; contact: repo owner)"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(sir|graf|freiherr|baron|count|1st|2nd|viscount|earl|lord|von|van|de|der|jr|marshal|general)\b", " ", s)
    return re.sub(r"[^a-z]+", "", s)


def psql(sql):
    r = subprocess.run(["docker", "exec", "-i", "worldline-borders-dev-db", "psql", "-U", "worldline", "-d", "worldline_borders_dev", "-At", "-F", "\t"],
                       input=sql, capture_output=True, text=True, check=True)
    return [l.split("\t") for l in r.stdout.splitlines() if l]


def qids(titles):
    out = {}
    for i in range(0, len(titles), 40):
        chunk = titles[i:i + 40]
        q = urllib.parse.urlencode({"action": "query", "format": "json", "redirects": 1, "prop": "pageprops", "ppprop": "wikibase_item|disambiguation", "titles": "|".join(chunk)})
        d = json.load(urllib.request.urlopen(urllib.request.Request("https://en.wikipedia.org/w/api.php?" + q, headers={"User-Agent": UA}), timeout=60))["query"]
        m = {t: t for t in chunk}
        for n in d.get("normalized", []):
            for k, v in m.items():
                if v == n["from"]: m[k] = n["to"]
        for r in d.get("redirects", []):
            for k, v in m.items():
                if v == r["from"]: m[k] = r["to"]
        pages = {p["title"]: p for p in d.get("pages", {}).values()}
        for t, fin in m.items():
            p = pages.get(fin) or {}
            pp = p.get("pageprops") or {}
            out[t] = None if ("missing" in p or "disambiguation" in pp) else {"qid": pp.get("wikibase_item"), "title": fin}
        time.sleep(1)
    return out


sel = json.loads((HERE / "selection.json").read_text())
selp = {q["key"]: q for t in ("S", "A") for b in sel[t] for q in b["people"]}
people = []
for f in sorted(HERE.glob("[SA]/batch*/research.json")):
    for p in json.loads(f.read_text())["people"]:
        people.append((f.parent.parent.name + "/" + f.parent.name[5:], p))
bios = psql("select id,name,coalesce(name_zh,''),coalesce(wikidata_qid,''),is_test from leader_bios where retracted_at is null")
by_q = {}
for b in bios:
    if b[3]: by_q.setdefault(b[3], []).append(b)
by_n, by_z = {}, {}
for b in bios:
    by_n.setdefault(norm(b[1]), []).append(b)
    if b[2]: by_z.setdefault(b[2], []).append(b)
titles = sorted({(selp.get(p["key"], {}).get("name_original") or p.get("name") or "").strip() for _, p in people} - {""})
Q = qids(titles)
res = {"generatedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "rule": "QID 只當識別碼（英文維基 pageprops），非事實出處", "people": []}
for tb, p in people:
    title = (selp.get(p["key"], {}).get("name_original") or p.get("name") or "").strip()
    qi = Q.get(title) or {}
    qid = qi.get("qid")
    row = {"batch": tb, "key": p["key"], "name": p.get("name"), "nameZh": p.get("nameZh"), "title": title, "enwikiTitle": qi.get("title"), "qid": qid, "seedBioId": p.get("bioId")}
    hits_q = by_q.get(qid, []) if qid else []
    hits_n = [b for b in by_n.get(norm(p.get("name") or title), []) + by_n.get(norm(title), []) if norm(b[1])] + (by_z.get(p.get("nameZh"), []) if p.get("nameZh") not in (None, "", "待查證") else [])
    hits_n = list({b[0]: b for b in hits_n}.values())
    if p.get("bioId"):
        row["status"] = "existing_seed"; row["bioId"] = p["bioId"]
        b = next((x for x in bios if x[0] == p["bioId"]), None)
        row["check"] = "ok" if b and (not qid or not b[3] or b[3] == qid) else ("bio_missing" if not b else f"qid_mismatch db={b[3]}")
    elif len(hits_q) == 1:
        row["status"] = "match_qid"; row["bioId"] = hits_q[0][0]; row["dbName"] = hits_q[0][1]; row["dbNameZh"] = hits_q[0][2]
    elif len(hits_q) > 1:
        row["status"] = "questionable"; row["why"] = "QID 對到多筆 bio"; row["candidates"] = [h[:3] for h in hits_q]
    elif hits_n:
        row["status"] = "questionable"; row["why"] = "無 QID 命中，但名字與既有 bio 相同"; row["candidates"] = [h[:4] for h in hits_n]
    else:
        row["status"] = "create"
    res["people"].append(row)
from collections import Counter
res["counts"] = dict(Counter(r["status"] for r in res["people"]))
res["noQid"] = sum(1 for r in res["people"] if not r["qid"])
(HERE / "match-bios.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({"counts": res["counts"], "noQid": res["noQid"]}, ensure_ascii=False))
for r in res["people"]:
    if r["status"] in ("questionable", "match_qid") or r.get("check", "ok") != "ok":
        print(r["status"], r["key"], r["name"], r["nameZh"], r.get("qid"), r.get("dbName"), r.get("dbNameZh"), r.get("why", ""), r.get("candidates", ""), r.get("check", ""))
