#!/usr/bin/env python3
"""只有 C／X 出處的舊格式人物欄位：補上 A／B 出處（Tai 2026-11-14「執行」；補查結果見 scratchpad cfields/q*/result.json）。

只做「新增引文」，不改欄位值（事實列不就地修改，憲法 I5）：
- status added：新出處支撐欄位值 → seed 欄位 sources 追加一筆；庫內 leader_bio_field_citations 新增一筆。
- status precision_lower：新出處只撐到年／月 → 同上追加，引文 datePrecision 記來源能支撐的精度；欄位值與精度不動（待決定）。
- value_differs、not_found：不動，列在報告。
來源：庫內已有同網址就沿用 sources.id，否則新增 sources 列（source_kind 照補查結果；sources.grade 不填，由來源層回填工具處理）。
原文存檔複製到 ~/wl-source-cache/old-format-cfields/，manifest 記 sha256。
預設 dry-run；--apply 改 seed；--send --allow-write 寫開發庫（單一交易）。
用法（repo 根目錄）：python3 -I data/seed/leaders/gap-830/merge_cfield_sources.py <result.json> [...] [--apply] [--send --allow-write]
"""
import json, sys, subprocess, hashlib, shutil, uuid, collections, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
P1 = HERE.parent / "batch-p1-20261107"
CACHE = Path.home() / "wl-source-cache" / "old-format-cfields"
CONTAINER, DBUSER, DBNAME = "worldline-borders-dev-db", "worldline", "worldline_borders_dev"
RUN = "old-format-cfields-2026-11-14"
DEV = REPO / ".dev" / "dbwrite"
KINDS = {"official_record", "official_history", "peer_reviewed", "dataset", "trial_record", "treaty", "encyclopedia", "official_website", "archive"}
KEEP = ("title", "publisher", "url", "sourceKind", "licenseCode", "locator", "evidence", "accessedOn", "grade", "gradeBasis")


def lit(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def qjson(sql):
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", DBUSER, "-d", DBNAME, "-At", "-v", "ON_ERROR_STOP=1"],
                       input="select coalesce(json_agg(t),'[]'::json)::text from (%s) t" % sql, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[:500])
    return json.loads(r.stdout)


def ledger_for(seed):
    seed = Path(seed)
    led = seed.parent / "sent.5052.json" if seed.name == "research.json" else P1 / "sent-p1.5052.json"
    return json.loads(led.read_text()).get("bios") or {}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply, send, allow = "--apply" in sys.argv, "--send" in sys.argv, "--allow-write" in sys.argv
    rows = []
    for rp in args:
        for r in json.load(open(rp)):
            r["_dir"] = str(Path(rp).parent); rows.append(r)
    take = [r for r in rows if r["status"] in ("added", "precision_lower") and r.get("newSource")]
    skipped = collections.Counter(r["status"] for r in rows if r not in take)
    byfile = collections.defaultdict(list)
    for r in take:
        byfile[r["file"]].append(r)
    plan_db, fetches, seed_added = [], [], 0
    for rel, items in sorted(byfile.items()):
        f = REPO / rel; raw = f.read_text(); d = json.loads(raw); bios = ledger_for(f)
        people = {p["key"]: p for p in d.get("people") or []}
        for r in items:
            p = people[r["personKey"]]; fld = p.get(r["field"])
            s = r["newSource"]
            if s.get("sourceKind") not in KINDS:
                raise SystemExit("sourceKind 不合法：%s %s" % (r["personKey"], s.get("sourceKind")))
            obj = {k: s.get(k) for k in KEEP}
            obj["gradeBasis"] = (s.get("gradeBasis") or "") + "（%s）" % RUN
            if r["status"] == "precision_lower":
                obj["datePrecision"] = r.get("supportedPrecision")
            srcs = fld.setdefault("sources", [])
            if not any(x.get("url") == obj["url"] and x.get("locator") == obj["locator"] for x in srcs):
                srcs.append(obj); seed_added += 1
            arch = Path(r["_dir"]) / s["archive"] if not str(s.get("archive", "")).startswith("/") else Path(s["archive"])
            dst = CACHE / Path(r["_dir"]).name / arch.name
            fetches.append((arch, dst, obj["url"]))
            bio = bios.get(r["personKey"])
            if not bio:
                raise SystemExit("找不到 bio：%s" % r["personKey"])
            plan_db.append((bio, r["field"], obj))
        if apply:
            ind = 2 if raw.startswith("{\n  ") else 1
            f.write_text(json.dumps(d, ensure_ascii=False, indent=ind) + ("\n" if raw.endswith("\n") else ""))
    # DB 計畫
    urls = sorted({o["url"] for _, _, o in plan_db})
    have = {}
    for i in range(0, len(urls), 300):
        for x in qjson("select url,id from sources where url in (%s) order by created_at" % ",".join(lit(u) for u in urls[i:i + 300])):
            have.setdefault(x["url"], x["id"])
    bios = sorted({b for b, _, _ in plan_db})
    exist = {(x["bio_id"], x["field"], x["url"], x["locator"]) for x in qjson(
        "select c.bio_id,c.field,s.url,c.locator from leader_bio_field_citations c join sources s on s.id=c.source_id "
        "where c.retracted_at is null and c.bio_id in (%s)" % ",".join(lit(b) for b in bios))}
    q = ["BEGIN;"]; new_src = {}; ins = 0; dup = 0
    for bio, fld, o in plan_db:
        if (bio, fld, o["url"], o["locator"]) in exist:
            dup += 1; continue
        sid = have.get(o["url"]) or new_src.get(o["url"])
        if not sid:
            sid = str(uuid.uuid4()); new_src[o["url"]] = sid
            q.append("INSERT INTO sources (id,source_kind,title,publisher,url,license_code) VALUES (%s,%s,%s,%s,%s,%s);" %
                     (lit(sid), lit(o["sourceKind"]), lit(o["title"]), lit(o["publisher"]), lit(o["url"]), lit(o.get("licenseCode"))))
        q.append("INSERT INTO leader_bio_field_citations (bio_id,field,source_id,locator,evidence_note,accessed_on,grade,date_precision,quote,policy_version) "
                 "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);" % (lit(bio), lit(fld), lit(sid), lit(o["locator"]), lit(o["evidence"]), lit(o["accessedOn"]),
                                                              lit(o["grade"]), lit(o.get("datePrecision")), lit(o["evidence"]), lit("source-2026-11-13")))
        exist.add((bio, fld, o["url"], o["locator"])); ins += 1
    q.append("COMMIT;")
    DEV.mkdir(parents=True, exist_ok=True)
    (DEV / "cfield-sync.sql").write_text("\n".join(q) + "\n")
    summ = {"apply_seed": apply, "results": len(rows), "taken": len(take), "skipped_by_status": dict(skipped), "seed_sources_added": seed_added,
            "db_citations_insert": ins, "db_already_present": dup, "db_new_sources": len(new_src), "db_sources_reused": len({o['url'] for _, _, o in plan_db} & set(have)),
            "grades": dict(collections.Counter(o["grade"] for _, _, o in plan_db))}
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    if apply:
        CACHE.mkdir(parents=True, exist_ok=True)
        with open(CACHE / "manifest.jsonl", "a") as m:
            for src, dst, url in fetches:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists(): shutil.copyfile(src, dst)
                m.write(json.dumps({"url": url, "txt": str(dst), "sha256": hashlib.sha256(dst.read_bytes()).hexdigest(), "run": RUN}) + "\n")
    if not send:
        print("（未寫庫；SQL 見 .dev/dbwrite/cfield-sync.sql）"); return
    if not allow:
        raise SystemExit("需 --send --allow-write")
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", DBUSER, "-d", DBNAME, "-v", "ON_ERROR_STOP=1", "-1", "-q"],
                       input="\n".join(q) + "\n", capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("寫入失敗（整筆交易回滾）：" + r.stderr[:800])
    print("已寫入。")


if __name__ == "__main__":
    main()
