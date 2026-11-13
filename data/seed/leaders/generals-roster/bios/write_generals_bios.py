#!/usr/bin/env python3
"""將領生平寫入 5442 開發庫（Tai 2026-11-13 11:01「可以，備份後寫入開發庫」、11:05「migration 加 C 級，並為 348 位將領新增生平主檔」；ARCHITECTURE §20.12、N11）。
沿用 b3-trial/run100/write_b3_paragraphs.py 的 plan()／build_sql()（段落、經歷、角色、citation、sources、gaps；已移除 C 過濾、X 不入庫、generals.dk 經 overrides=null DROP）。
本腳本另做：
- 依 match-bios.json 決定 bio：existing_seed／match_qid 沿用既有 bio；questionable 只有在名字唯一且完全相同時沿用（APPROVE_NAME_MATCH），其餘略過；create 新建 leader_bios。
- 新 bio：name＝原文名；name_zh＝nameZh（「待查證」→ NULL；nameZhUnsourced 一律不用）；field_sources.nameZh＝nameZhSource（Wikipedia 只當人名索引）；wikidata_qid 只當識別碼。
- 零段落者照 write_b3_paragraphs 規則整人略過（也不建 bio）。
- 只連 5442（docker exec worldline-borders-dev-db）；預設 dry-run；--send --allow-write 才在單一交易（psql -1）寫入。
用法（repo 根目錄）：python3 -I data/seed/leaders/generals-roster/bios/write_generals_bios.py [--send --allow-write]
"""
import argparse, json, os, sys, subprocess, uuid, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "data/seed/leaders/b3-trial/run100"))
sys.path.insert(0, str(HERE.parent))
import write_b3_paragraphs as W  # noqa: E402
from zh_trad import to_trad  # noqa: E402
APPROVE_NAME_MATCH = {"kuniakikoiso"}  # 名字唯一且完全相同（小磯國昭），既有 bio 無 QID；主管規則：無歧義才寫
DEV = REPO / ".dev" / "dbwrite"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true"); ap.add_argument("--allow-write", action="store_true")
    a = ap.parse_args()
    match = {r["key"]: r for r in json.loads((HERE / "match-bios.json").read_text())["people"]}
    ov = json.load(open(W.OVERRIDES))
    roster_idx = {(r.get("name_original"), r.get("name_zh")): r.get("index_url") for r in json.loads((HERE.parent / "roster.json").read_text())["people"] if r.get("index_url")}
    st = W.db_state(None)
    batches, new_bios, skipped, used, fixed_gaps = [], [], [], {}, []
    cdate = lambda f: subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(f)], capture_output=True, text=True, cwd=REPO).stdout.strip()
    for f in sorted(HERE.glob("[SA]/batch*/research.json")):
        d = json.loads(f.read_text())
        keep = []
        for p in d["people"]:
            m = match[p["key"]]
            if not p.get("paragraphs"):
                skipped.append((p["key"], "零段落（write_b3_paragraphs 規則整人略過）")); continue
            if m["status"] in ("existing_seed", "match_qid"):
                bio = m["bioId"]
            elif m["status"] == "questionable":
                if p["key"] in APPROVE_NAME_MATCH and len(m.get("candidates") or []) == 1:
                    bio = m["candidates"][0][0]
                else:
                    skipped.append((p["key"], "比對可疑：" + m.get("why", ""))); continue
            else:
                nz = p.get("nameZh")
                nz = None if not nz or nz == "待查證" else nz
                if nz and to_trad(nz) != nz:
                    raise SystemExit(f"{p['key']} nameZh 未通過 zh_trad：{nz}")
                fs = None
                if p.get("nameZhSource"):  # 研究時以出處確認的中文名（主管 11:05：nameZhSource 放 field_sources.nameZh）
                    s = dict(p["nameZhSource"]); s["status"] = "index-only"
                    src = d["sources"].get(s.get("sourceKey")) or {}
                    if src.get("url"): s["url"] = src["url"]
                    fs = {"nameZh": s}
                elif nz:  # 其餘：中文名來自將領名冊的 Wikipedia 列表頁（只當人名索引，非出處）
                    u = roster_idx.get((p.get("name"), p.get("nameZhOrig"))) or roster_idx.get((p.get("name"), p.get("nameZh")))
                    u = u if u and "zh.wikipedia.org" in u else None  # 只有中文維基列表頁才是中文名的索引
                    if u:
                        fs = {"nameZh": {"kind": "index", "status": "index-only", "url": u,
                                         "note": "將領名冊人名索引（Wikipedia 列表頁，只當索引、非出處）；zh_trad 轉台灣正體"}}
                bio = str(uuid.uuid4())
                new_bios.append({"id": bio, "key": p["key"], "name": (p.get("name") or m["title"]).strip(), "name_zh": nz, "qid": m.get("qid"), "fs": fs})
                st["bios"].add(bio)
            if bio in used.values():
                raise SystemExit(f"bio 重複指派：{p['key']}")
            used[p["key"]] = bio
            q = dict(p); q["bioId"] = bio
            for k in ("positions", "roleCandidates", "gaps"):
                q.setdefault(k, [])
            gs = []
            for g in q["gaps"]:
                if not g.get("checkedOn"):  # 4 筆 seed gap 缺 checkedOn（DB NOT NULL）：以該 research.json 最後 commit 日期補（查核不晚於此日），note 註明
                    g = dict(g); g["checkedOn"] = cdate(f)
                    g["note"] = ((g.get("note") or "") + "（checkedOn 缺，以研究檔 commit 日期補）").strip()
                    fixed_gaps.append((p["key"], g.get("target")))
                gs.append(g)
            q["gaps"] = gs
            keep.append(q)
        d = dict(d); d["people"] = keep
        batches.append((f.parent.parent.name + "/" + f.parent.name, d))
    P = W.plan(batches, st, ov)
    # 引文全被捨棄（來源屬個人網站等 null 網域）的段落／任期／角色不寫：無出處不入庫，留待重查
    uncited = [("paragraph", r["bio"], r["ord"]) for r in P["par"] if not r["cit"]] + [("position", r["bio"], r["key"]) for r in P["pos"] if not r["cit"]] \
        + [("role", r["bio"], r["key"]) for r in P["role_ok"] if not r.get("cit")]
    P["par"] = [r for r in P["par"] if r["cit"]]; P["pos"] = [r for r in P["pos"] if r["cit"]]; P["role_ok"] = [r for r in P["role_ok"] if r.get("cit")]
    qids = {b["qid"] for b in new_bios if b["qid"]}
    clash = [r for r in W.psql("select wikidata_qid from leader_bios where wikidata_qid is not null") if r[0] in qids]
    if clash:
        raise SystemExit(f"新 bio 的 QID 已存在於庫內：{clash}")
    nc = lambda rows: sum(len(r.get("cit", [])) for r in rows)
    from collections import Counter
    gc = Counter(c["grade"] for rows in (P["par"], P["pos"], P["role_ok"]) for r in rows for c in r.get("cit", []))
    summ = {"bios_new": len(new_bios), "bios_existing_used": len(used) - len(new_bios), "people_planned": P["people"], "people_skipped": skipped,
            "bio_missing": P["bio_missing"], "paragraphs": len(P["par"]), "paragraph_citations": nc(P["par"]), "positions": len(P["pos"]), "position_citations": nc(P["pos"]),
            "roles": len(P["role_ok"]), "role_citations": nc(P["role_ok"]), "roles_blocked_dup": len(P["role_conflict"]), "roles_pending": len(P["role_pending"]),
            "gaps": len(P["gaps"]), "gaps_missing_start": P["gaps_missing"], "gaps_left_in_seed": len(P["gaps_seed"]), "sources_new": len(P["sources_new"]),
            "sources_reused": len(P["sources_reused"]), "sources_dropped": len(P["sources_dropped"]), "unclassified": {k: len(v) for k, v in P["unclassified"].items()},
            "citations_dropped": len(P["cit_dropped"]), "citations_dropped_reasons": dict(Counter(c[2] for c in P["cit_dropped"])), "parents_without_citation": len(P["parents_nocit"]), "uncited_skipped": len(uncited),
            "already_in_db": P["already"], "bad": P["bad"], "citation_grades": dict(gc), "new_bios_no_name_zh": sum(1 for b in new_bios if not b["name_zh"]),
            "new_bios_with_qid": len(qids), "gaps_checkedOn_filled": fixed_gaps, "new_bios_field_sources_nameZh": sum(1 for b in new_bios if b["fs"])}
    DEV.mkdir(parents=True, exist_ok=True)
    (DEV / ("write-result.json" if a.send else "dryrun.json")).write_text(json.dumps({"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "summary": summ,
        "new_bios": new_bios, "cit_dropped": P["cit_dropped"], "parents_nocit": P["parents_nocit"], "role_conflict": [(r["person"], r["key"], r["why"]) for r in P["role_conflict"]],
        "gaps_seed": P["gaps_seed"]}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    if not a.send:
        print("（dry-run；未寫庫）"); return
    if not (a.send and a.allow_write):
        raise SystemExit("需 --send --allow-write")
    if P["unclassified"] or P["bad"]:
        raise SystemExit("有未歸類網域或驗證不過，拒絕寫入")
    if "'C'" not in W.psql("select pg_get_constraintdef(oid) from pg_constraint where conname='ck_person_position_citations_grade'")[0][0]:
        raise SystemExit("migration BioCitationGradeC 尚未套用")
    body = W.build_sql(P).split("\n")
    assert body[0] == "BEGIN;" and body[-1] == "COMMIT;"
    sql = ["BEGIN;"]
    for b in new_bios:
        sql.append("INSERT INTO leader_bios (id,name,name_zh,wikidata_qid,field_sources) VALUES (%s,%s,%s,%s,%s);" % (
            W.sql_lit(b["id"]), W.sql_lit(b["name"]), W.sql_lit(b["name_zh"]), W.sql_lit(b["qid"]), W.sql_jsonb(b["fs"])))
    sql += body[1:]
    (DEV / "write.sql").write_text("\n".join(sql) + "\n", encoding="utf-8")
    r = subprocess.run(["docker", "exec", "-i", W.CONTAINER, "psql", "-U", W.DBUSER, "-d", W.DBNAME, "-v", "ON_ERROR_STOP=1", "-1", "-q"],
                       input="\n".join(sql) + "\n", capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("寫入失敗（整筆交易回滾）：" + r.stderr[:800])
    print("已寫入（單一交易）。")


if __name__ == "__main__":
    main()
