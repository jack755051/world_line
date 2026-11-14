#!/usr/bin/env python3
"""元首、首腦任期接上結構化出處（source-rules §6 D6；Tai 2026-11-14「開始處理」）。

輸入：補查結果（scratchpad terms/t*/result.json），每筆任期 1～3 筆引文，引文逐字核對、只收 A／B。
- build：產出 citations-20261114.json（seed，記 _id、dbId、引文與備註），原文複製到 ~/wl-source-cache/leader-terms/（manifest 記 sha256）。
- 迄日慣例（source-rules §6，Tai 2026-11-14）：迄日記繼任者就任日；來源記本人卸任日不同（value_differs）時不改日期，備註寫明。
- 寫庫：sources 以網址對帳（已有就沿用），leader_record_citations 新增（同任期、同網址、同 locator 已有就略過）。任期本身不改。
預設 dry-run；--build 產 seed；--send --allow-write 寫 5442（單一交易）。寫入前請先 pg_dump，並通知另一個 session。
用法（repo 根目錄）：python3 -I data/seed/leaders/leader-record-citations/build_and_write.py <terms 資料夾> [--build] [--send --allow-write]
"""
import json, sys, subprocess, hashlib, shutil, unicodedata, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SEED = HERE / "citations-20261114.json"
CACHE = Path.home() / "wl-source-cache" / "leader-terms"
CONTAINER, DBUSER, DBNAME = "worldline-borders-dev-db", "worldline", "worldline_borders_dev"
RUN = "leader-terms-2026-11-14"
CONVENTION = "迄日依繼任者就任日（source-rules §6，Tai 2026-11-14）"


def lit(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def qjson(sql):
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", DBUSER, "-d", DBNAME, "-At", "-v", "ON_ERROR_STOP=1"],
                       input="select coalesce(json_agg(t),'[]'::json)::text from (%s) t" % sql, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[:500])
    return json.loads(r.stdout)


def note_for(r):
    n = (r.get("note") or "").strip()
    if r["status"] == "value_differs":
        return "%s；來源記：%s。%s" % (CONVENTION, (r.get("sourceValue") or "").strip(), n)
    return n


def main():
    tdir = Path([a for a in sys.argv[1:] if not a.startswith("--")][0])
    build, send, allow = "--build" in sys.argv, "--send" in sys.argv, "--allow-write" in sys.argv
    entries, fetches = [], []
    for g in ("t1", "t2", "t3", "t4"):
        for r in json.loads((tdir / g / "result.json").read_text()):
            cits = []
            for c in r.get("citations") or []:
                s = c["source"]; arch = tdir / g / c["archive"]
                t = arch.read_text(encoding="utf-8", errors="replace")
                assert c["quote"] in t or unicodedata.normalize("NFC", c["quote"]) in unicodedata.normalize("NFC", t), (r["_id"], c["quote"])
                assert s.get("grade") in ("A", "B") and len(unicodedata.normalize("NFC", c["quote"])) <= 80
                dst = CACHE / g / arch.name
                fetches.append((arch, dst, s.get("url")))
                cits.append({"source": {k: s.get(k) for k in ("title", "publisher", "authors", "url", "sourceKind", "grade", "gradeBasis")},
                             "locator": c["locator"], "quote": c["quote"], "quoteLang": c.get("quoteLang"), "datePrecision": c.get("datePrecision"),
                             "supports": c.get("supports"), "archive": str(dst)})
            entries.append({"_id": r["_id"], "dbId": r["dbId"], "status": r["status"], "note": note_for(r), "citations": cits})
    # 資料庫已撤回（被新版本取代）的任期：seed 送出程式仍留舊版，記下來讓稽核分開列，不再算自由文字落差
    retracted = [{"_id": r["_id"], "dbId": r["dbId"], "status": "retracted_in_db", "note": "資料庫中此任期已撤回（後續版本取代），不需另接出處", "citations": []}
                 for r in json.loads((tdir / "records.json").read_text()) if r.get("dbRetracted")]
    if build:
        SEED.write_text(json.dumps({"run": RUN, "convention": CONVENTION, "records": entries + retracted}, ensure_ascii=False, indent=1) + "\n")
        CACHE.mkdir(parents=True, exist_ok=True)
        with open(CACHE / "manifest.jsonl", "a") as m:
            for src, dst, url in fetches:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists(): shutil.copyfile(src, dst)
                m.write(json.dumps({"url": url, "txt": str(dst), "sha256": hashlib.sha256(dst.read_bytes()).hexdigest(), "run": RUN}) + "\n")
    ids = [e["dbId"] for e in entries]
    active = {x["id"] for x in qjson("select id from leader_records where retracted_at is null and id in (%s)" % ",".join(lit(i) for i in ids))}
    urls = sorted({c["source"]["url"] for e in entries for c in e["citations"]})
    have = {x["url"]: x["id"] for x in qjson("select url,id from sources where url in (%s) order by created_at desc" % ",".join(lit(u) for u in urls))}
    exist = {(x["record_id"], x["url"], x["locator"]) for x in qjson(
        "select c.record_id,s.url,c.locator from leader_record_citations c join sources s on s.id=c.source_id where c.retracted_at is null and c.record_id in (%s)" % ",".join(lit(i) for i in ids))}
    q = ["BEGIN;"]; new_src = set(); ins = 0; skip_inactive = 0; dup = 0; grades = collections.Counter()
    for e in entries:
        if e["dbId"] not in active:
            skip_inactive += 1; continue
        for c in e["citations"]:
            s = c["source"]
            if (e["dbId"], s["url"], c["locator"]) in exist:
                dup += 1; continue
            if s["url"] not in have and s["url"] not in new_src:
                new_src.add(s["url"])
                q.append("INSERT INTO sources (id,source_kind,title,publisher,authors,url) VALUES (gen_random_uuid(),%s,%s,%s,%s,%s);"
                         % (lit(s["sourceKind"]), lit(s["title"]), lit(s["publisher"]), lit("; ".join(s.get("authors") or []) or None), lit(s["url"])))
            note = "；".join(x for x in (e["note"], "支撐：" + "、".join(c.get("supports") or [])) if x)
            q.append("INSERT INTO leader_record_citations (record_id,source_id,locator,quote,quote_lang,evidence_note,accessed_on,grade,date_precision,policy_version) "
                     "VALUES (%s,(SELECT id FROM sources WHERE url=%s ORDER BY created_at DESC LIMIT 1),%s,%s,%s,%s,'2026-11-14',%s,%s,'source-2026-11-13');"
                     % (lit(e["dbId"]), lit(s["url"]), lit(c["locator"]), lit(c["quote"]), lit(c.get("quoteLang")), lit(note[:2000]),
                        lit(s["grade"]), lit(c.get("datePrecision"))))
            exist.add((e["dbId"], s["url"], c["locator"])); ins += 1; grades[s["grade"]] += 1
    q.append("COMMIT;")
    (REPO / ".dev" / "dbwrite").mkdir(parents=True, exist_ok=True)
    (REPO / ".dev" / "dbwrite" / "leader-terms.sql").write_text("\n".join(q) + "\n")
    print(json.dumps({"build": build, "records": len(entries), "status": dict(collections.Counter(e["status"] for e in entries)),
                      "citations_insert": ins, "already_present": dup, "inactive_skipped": skip_inactive, "new_sources": len(new_src),
                      "grades": dict(grades)}, ensure_ascii=False, indent=1))
    if not send:
        print("（未寫庫；SQL 見 .dev/dbwrite/leader-terms.sql）"); return
    if not allow:
        raise SystemExit("需 --send --allow-write")
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", DBUSER, "-d", DBNAME, "-v", "ON_ERROR_STOP=1", "-1", "-q"],
                       input="\n".join(q) + "\n", capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("寫入失敗（整筆交易回滾）：" + r.stderr[:800])
    print("已寫入。")


if __name__ == "__main__":
    main()
