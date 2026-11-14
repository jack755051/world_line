#!/usr/bin/env python3
"""舊格式人物生平（gap-830）欄位出處等級 → 5442 開發庫 leader_bio_field_citations.grade（Tai 2026-11-14 做法 3「繼續做」）。

- 以各批 sent.5052.json 的「人物 key → bio id」對照，依 (bio, 欄位, 來源網址, locator) 對到庫內有效的欄位引文。
- seed 等級 A／B／C 與庫內不同 → 就地 UPDATE grade（欄位引文表允許改等級；保護機制只擋刪除與撤銷撤回）。
- seed 等級 X（個人網站、私人彙編）→ 撤回該筆引文（等級欄不收 X；來源規則 §2 X＝不收）。
- 只有 C 的欄位不撤回（做法 3：先照實記等級，日後補 A／B 出處再決定）。欄位值與 leader_bios 不動。
預設 dry-run；--send --allow-write 才在單一交易寫入。寫入前請先 pg_dump 備份。
用法（repo 根目錄）：python3 -I data/seed/leaders/gap-830/sync_field_grades.py [--send --allow-write]
"""
import json, sys, subprocess, collections, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
CONTAINER, DBUSER, DBNAME = "worldline-borders-dev-db", "worldline", "worldline_borders_dev"
FIELDS = ("name", "nameZh", "birthDate", "deathDate", "birthPlace", "deathPlace", "party", "summary", "portrait")
RUN = "old-format-grade-sync-2026-11-14"
WHY_X = RUN + "：出處評為 X（個人網站／私人彙編，來源規則 §2 不收），撤回此引文"
DEV = REPO / ".dev" / "dbwrite"


def lit(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def qjson(sql):
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", DBUSER, "-d", DBNAME, "-At", "-v", "ON_ERROR_STOP=1"],
                       input="select coalesce(json_agg(t),'[]'::json)::text from (%s) t" % sql, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[:500])
    return json.loads(r.stdout)


def sources_of(v):
    out = []
    def walk(o):
        if isinstance(o, dict):
            if "url" in o and "sourceKind" in o: out.append(o)
            for x in o.values(): walk(x)
        elif isinstance(o, list):
            for x in o: walk(x)
    walk(v)
    return out


def main():
    send = "--send" in sys.argv; allow = "--allow-write" in sys.argv
    want = collections.defaultdict(set)  # (bio, field, url, locator) -> {grade}
    no_bio = 0
    for d in sorted(HERE.glob("b[0-9][0-9]")):
        led = d / "sent.5052.json"
        if not (d / "research.json").exists() or not led.exists():
            continue
        bios = json.loads(led.read_text()).get("bios") or {}
        for p in json.loads((d / "research.json").read_text()).get("people") or []:
            bio = bios.get(p["key"])
            if not bio:
                no_bio += 1; continue
            for f in FIELDS:
                for s in sources_of(p.get(f)):
                    if s.get("grade"):
                        want[(bio, f, s["url"], s.get("locator"))].add(s["grade"])
    bios = sorted({k[0] for k in want})
    rows = []
    for i in range(0, len(bios), 400):
        chunk = "','".join(bios[i:i + 400])
        rows += qjson("select c.id,c.bio_id,c.field,s.url,c.locator,c.grade from leader_bio_field_citations c join sources s on s.id=c.source_id "
                      "where c.retracted_at is null and c.bio_id in ('%s')" % chunk)
    upd, retract, same, ambiguous, unmatched_db = [], [], 0, [], 0
    matched = set()
    for r in rows:
        k = (r["bio_id"], r["field"], r["url"], r["locator"])
        g = want.get(k)
        if not g:
            unmatched_db += 1; continue
        matched.add(k)
        if len(g) > 1:
            ambiguous.append((k, sorted(g))); continue
        g = next(iter(g))
        if g == "X":
            retract.append(r)
        elif r["grade"] != g:
            upd.append((r, g))
        else:
            same += 1
    q = ["BEGIN;"]
    for r, g in upd:
        q.append("UPDATE leader_bio_field_citations SET grade=%s WHERE id=%s AND retracted_at IS NULL;" % (lit(g), lit(r["id"])))
    for r in retract:
        q.append("UPDATE leader_bio_field_citations SET retracted_at=now(), retraction_reason=%s WHERE id=%s AND retracted_at IS NULL;" % (lit(WHY_X), lit(r["id"])))
    # 撤回後沒有任何有效引文的欄位：field_sources 標待查證（同 send_batch 對無出處欄位的記法），值不動
    left = collections.Counter((r["bio_id"], r["field"]) for r in rows)
    gone = collections.Counter((r["bio_id"], r["field"]) for r in retract)
    orphan = sorted(k for k, n in gone.items() if n >= left[k])
    for bio, f in orphan:
        note = json.dumps({"status": "待查證", "note": "原出處評為 X（個人網站／私人彙編，來源規則 §2 不收），引文已撤回；待補 A／B 出處（%s）" % RUN}, ensure_ascii=False)
        q.append("UPDATE leader_bios SET field_sources = jsonb_set(coalesce(field_sources,'{}'::jsonb), %s, %s::jsonb) WHERE id=%s AND retracted_at IS NULL;"
                 % (lit("{%s}" % f), lit(note), lit(bio)))
    q.append("COMMIT;")
    DEV.mkdir(parents=True, exist_ok=True)
    (DEV / "field-grade-sync.sql").write_text("\n".join(q) + "\n")
    summ = {"seed_citations": len(want), "db_rows_for_these_bios": len(rows), "update_grade": len(upd),
            "update_by_grade": dict(collections.Counter(g for _, g in upd)), "retract_X": len(retract),
            "fields_marked_unverified": ["%s:%s" % k for k in orphan], "already_same": same,
            "ambiguous_skipped": len(ambiguous), "seed_not_in_db": len(set(want) - matched), "db_rows_not_in_seed": unmatched_db,
            "people_without_bio": no_bio}
    (DEV / ("field-grade-sync-result.json" if send else "field-grade-sync-dryrun.json")).write_text(json.dumps(
        {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "summary": summ,
         "retract": [(r["bio_id"], r["field"], r["url"]) for r in retract], "ambiguous": [list(k) + [g] for k, g in ambiguous]},
        ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    if not send:
        print("（dry-run；未寫庫；SQL 見 .dev/dbwrite/field-grade-sync.sql）"); return
    if not allow:
        raise SystemExit("需 --send --allow-write")
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", DBUSER, "-d", DBNAME, "-v", "ON_ERROR_STOP=1", "-1", "-q"],
                       input="\n".join(q) + "\n", capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("寫入失敗（整筆交易回滾）：" + r.stderr[:800])
    print("已寫入。")


if __name__ == "__main__":
    main()
