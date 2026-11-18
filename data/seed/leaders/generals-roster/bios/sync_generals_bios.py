#!/usr/bin/env python3
"""將領生平 seed → 5442 開發庫同步（banned-replace-2026-11-14 之後；Tai 2026-11-14「繼續處理」）。

write_generals_bios.py 只補庫內沒有的列（同 bio＋ord／seed_key 就略過），seed 改過的列不會更新。本腳本補上「改過的列」：
- 用 write_b3_paragraphs.plan() 算出 seed 現在應該寫成的列（同一套正規化、來源對帳、X／禁用不入庫、無引文列不寫）。
- 與庫內有效列（retracted_at IS NULL）逐列比對：
  * 只差 citation 的 grade（其餘全同）→ 就地 UPDATE grade（轉錄本 A→B 等，不是事實改動）。
  * 其餘有差 → 撤回舊列與其 citation（I5：不刪），寫入新列，舊列 superseded_by＝新列。
  * 庫內有、seed 已無（刪段、職位移為缺口）→ 撤回。
  * seed 有、庫內無 → 新增。
- gaps 以 (bio, target, gap_kind) 對帳：note／候選／checked_on 不同就撤回重寫；seed 已無就撤回；新的就新增。
- 角色層（person_roles）只比對、不改（本次 seed 沒有改角色；有差就列出並拒絕寫入）。
預設 dry-run（只做 SELECT），輸出 .dev/dbwrite/sync-dryrun.json 與 sync.sql；--send --allow-write 才在單一交易寫入。
寫入前請先 pg_dump 備份（~/wl-db-backups/）。
用法（repo 根目錄）：python3 -I data/seed/leaders/generals-roster/bios/sync_generals_bios.py [--send --allow-write]
"""
import argparse, json, sys, subprocess, uuid, datetime, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "data/seed/leaders/b3-trial/run100"))
import write_b3_paragraphs as W  # noqa: E402

DEV = REPO / ".dev" / "dbwrite"
RUN = "banned-replace-2026-11-14"
WHY_REPLACE = RUN + "：seed 修訂（禁用網域替換、依合法來源修正內容或精度），由新列取代"
WHY_REMOVE = RUN + "：seed 已移除此列（無合法來源支撐，改記缺口或刪句）"
WHY_GAP = RUN + "：缺口內容更新（移除禁用網域候選或改寫說明），由新列取代"
WHY_GAP_REMOVE = RUN + "：seed 已移除此缺口"
DUP_RETRACTED = {"williamdleahy", "何应钦", "孙立人", "陈诚"}
APPROVE_NAME_MATCH = {"kuniakikoiso"}


def qjson(sql):
    r = subprocess.run(["docker", "exec", "-i", W.CONTAINER, "psql", "-U", W.DBUSER, "-d", W.DBNAME, "-At", "-v", "ON_ERROR_STOP=1"],
                       input="select coalesce(json_agg(t),'[]'::json)::text from (%s) t" % sql, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[:500])
    return json.loads(r.stdout)


def load_batches(st):
    match = {r["key"]: r for r in json.loads((HERE / "match-bios.json").read_text())["people"]}
    wf = HERE / "bios-written-20261113.json"
    written = {b["key"]: b["id"] for b in json.loads(wf.read_text())["new_bios"]} if wf.exists() else {}
    batches, skipped = [], []
    for f in sorted(HERE.glob("[SA]/batch*/research.json")):
        d = json.loads(f.read_text()); keep = []
        for p in d["people"]:
            m = match.get(p["key"], {})
            if p["key"] in DUP_RETRACTED:
                skipped.append((p["key"], "重複人物已撤回")); continue
            bio = written.get(p["key"])
            if not bio and m.get("status") in ("existing_seed", "match_qid"):
                bio = m["bioId"]
            if not bio and m.get("status") == "questionable" and p["key"] in APPROVE_NAME_MATCH and len(m.get("candidates") or []) == 1:
                bio = m["candidates"][0][0]
            if not bio or bio not in st["bios"]:
                skipped.append((p["key"], "庫內無 bio（未寫過的人不在本腳本範圍）")); continue
            q = dict(p); q["bioId"] = bio
            for k in ("positions", "roleCandidates", "gaps"):
                q.setdefault(k, [])
            q["gaps"] = [g for g in q["gaps"] if g.get("checkedOn")] + [dict(g, checkedOn=None) for g in q["gaps"] if not g.get("checkedOn")]
            keep.append(q)
        d = dict(d); d["people"] = keep
        batches.append((f.parent.parent.name + "/" + f.parent.name, d))
    return batches, skipped


def changed_rows(since):
    """since 之後 seed 改過的列：{人物 key: {"par": {ord}, "pos": {seed_key}, "gap": {(target, gap_kind)}}}。
    新增、修改、刪除都算（逐列比對 JSON）；沒改過的列即使與庫內不同也不動（可能是別條流程寫的）。"""
    files = subprocess.run(["git", "diff", "--name-only", since, "HEAD", "--", str(HERE)], capture_output=True, text=True, cwd=REPO).stdout.split()
    out = {}
    def rows(p):
        par = {g["ord"]: g for g in p.get("paragraphs") or []}
        pos = {x["key"]: x for x in p.get("positions") or []}
        gap = {}
        for g in p.get("gaps") or []:
            t, _ = W.norm_field_target(g.get("target"))
            gap[(t or g.get("target"), g.get("gapKind"))] = g
        return {"par": par, "pos": pos, "gap": gap}
    for f in files:
        if not f.endswith("research.json"): continue
        old = subprocess.run(["git", "show", since + ":" + f], capture_output=True, text=True, cwd=REPO)
        o = {p["key"]: p for p in json.loads(old.stdout)["people"]} if old.returncode == 0 else {}
        for p in json.loads((REPO / f).read_text())["people"]:
            a, b = rows(o.get(p["key"]) or {}), rows(p)
            ch = {k: {i for i in set(a[k]) | set(b[k]) if json.dumps(a[k].get(i), sort_keys=True) != json.dumps(b[k].get(i), sort_keys=True)} for k in a}
            if any(ch.values()):
                out[p["key"]] = ch
    return out


def cit_key(c, with_grade=True):
    return (c["source_id"], c["locator"], c["quote"], c.get("quote_lang"), c.get("evidence_note"), str(c["accessed_on"])[:10],
            c.get("grade") if with_grade else None, c.get("date_precision"), c.get("policy_version"))


def period_of(row):
    if row["lo"] is None:
        return None
    return "[%s,%s)" % (row["lo"], row["hi"] or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true"); ap.add_argument("--allow-write", action="store_true")
    ap.add_argument("--since", default="bccf24d", help="只同步這個 commit 之後 seed 有改動的人物（預設：banned-replace 之前）")
    a = ap.parse_args()
    rowscope = changed_rows(a.since)
    scope = set(rowscope)
    st = W.db_state(None)
    st["existing"] = {"paragraphs": set(), "positions": set(), "roles": st["existing"]["roles"]}  # 段落／經歷全部重算，角色照舊略過
    batches, skipped = load_batches(st)
    batches = [(b, dict(d, people=[p for p in d["people"] if p["key"] in scope])) for b, d in batches]
    match = {r["key"]: r for r in json.loads((HERE / "match-bios.json").read_text())["people"]}
    # 既有 bio（別條流程建立、可能有別的 seed 寫入的列）：只更新／新增將領 seed 有的列，不撤回 seed 沒有的列
    shared = {p["bioId"] for _, d in batches for p in d["people"] if match.get(p["key"], {}).get("status") == "existing_seed"}
    ov = json.load(open(W.OVERRIDES))
    P = W.plan(batches, st, ov)
    if P["unclassified"] or P["bad"]:
        print(json.dumps({"unclassified": {k: len(v) for k, v in P["unclassified"].items()}, "bad": P["bad"]}, ensure_ascii=False, indent=1))
        raise SystemExit("有未歸類網域或驗證不過")
    key_of = {p["bioId"]: p["key"] for _, d in batches for p in d["people"]}
    inrow = lambda bio, kind, k: k in rowscope.get(key_of.get(bio), {}).get(kind, set())
    want_par = {(r["bio"], r["ord"]): r for r in P["par"] if r["cit"] and inrow(r["bio"], "par", r["ord"])}
    want_pos = {(r["bio"], r["key"]): r for r in P["pos"] if r["cit"] and inrow(r["bio"], "pos", r["key"])}
    gseen, want_gap = set(), {}
    for g in P["gaps"]:
        k = (g["bio"], g["target"], g["kind"])
        if k not in gseen and inrow(g["bio"], "gap", (g["target"], g["kind"])):
            gseen.add(k); want_gap[k] = g
    bios = sorted({b for b, _ in want_par} | {b for b, _ in want_pos} | {b for b, _, _ in want_gap} | {p["bioId"] for _, d in batches for p in d["people"]})
    inb = "'" + "','".join(bios) + "'"
    db_par = {(r["bio_id"], r["ord"]): r for r in qjson(
        "select id,bio_id,ord,lower(period) lo,upper(period) hi,period_start_precision sp,period_end_precision ep,heading,body "
        "from leader_bio_paragraphs where retracted_at is null and bio_id in (%s)" % inb) if inrow(r["bio_id"], "par", r["ord"])}
    db_pos = {(r["bio_id"], r["seed_key"]): r for r in qjson(
        "select id,bio_id,seed_key,regime_id,organization,title,position_kind,lower(period) lo,upper(period) hi,start_precision sp,end_precision ep,note "
        "from person_positions where retracted_at is null and bio_id in (%s)" % inb) if inrow(r["bio_id"], "pos", r["seed_key"])}
    pc = collections.defaultdict(list)
    for r in qjson("select c.* from leader_bio_paragraph_citations c join leader_bio_paragraphs p on p.id=c.paragraph_id "
                   "where c.retracted_at is null and p.retracted_at is null and p.bio_id in (%s)" % inb):
        pc[r["paragraph_id"]].append(r)
    qc = collections.defaultdict(list)
    for r in qjson("select c.* from person_position_citations c join person_positions p on p.id=c.position_id "
                   "where c.retracted_at is null and p.retracted_at is null and p.bio_id in (%s)" % inb):
        qc[r["position_id"]].append(r)
    db_gap = {(r["bio_id"], r["target"], r["gap_kind"]): r for r in qjson(
        "select id,bio_id,target,gap_kind,note,candidate_citations,checked_on from leader_bio_gaps "
        "where retracted_at is null and resolved_at is null and bio_id in (%s)" % inb) if inrow(r["bio_id"], "gap", (r["target"], r["gap_kind"]))}

    plan = {"par_insert": [], "par_replace": [], "par_retract": [], "pos_insert": [], "pos_replace": [], "pos_retract": [],
            "grade_update": [], "gap_insert": [], "gap_replace": [], "gap_retract": []}

    def compare(want, dbrow, dbcits, fields):
        same_fields = all(want[w] == dbrow[d] for w, d in fields) and (want["period"] or None) == period_of(dbrow)
        wc = collections.Counter(cit_key(c) for c in want["cit"]); dc = collections.Counter(cit_key(c) for c in dbcits)
        if same_fields and wc == dc:
            return "same", []
        wcg = collections.Counter(cit_key(c, False) for c in want["cit"]); dcg = collections.Counter(cit_key(c, False) for c in dbcits)
        if same_fields and wcg == dcg:  # 只差等級
            upd = []
            for c in dbcits:
                tgt = [w for w in want["cit"] if cit_key(w, False) == cit_key(c, False)]
                if tgt and tgt[0]["grade"] != c["grade"]:
                    upd.append((c["id"], c["grade"], tgt[0]["grade"]))
            return "grade", upd
        return "diff", []

    PF = [("sp", "sp"), ("ep", "ep"), ("heading", "heading"), ("body", "body")]
    QF = [("regime", "regime_id"), ("org", "organization"), ("title", "title"), ("kind", "position_kind"), ("sp", "sp"), ("ep", "ep"), ("note", "note")]
    for k, w in want_par.items():
        if k not in db_par:
            plan["par_insert"].append(w); continue
        v, upd = compare(w, db_par[k], pc[db_par[k]["id"]], PF)
        if v == "diff": plan["par_replace"].append((db_par[k], w))
        elif v == "grade": plan["grade_update"] += [("leader_bio_paragraph_citations",) + u for u in upd]
    for k, r in db_par.items():
        if k not in want_par and k[0] not in shared: plan["par_retract"].append(r)
    for k, w in want_pos.items():
        if k not in db_pos:
            plan["pos_insert"].append(w); continue
        v, upd = compare(w, db_pos[k], qc[db_pos[k]["id"]], QF)
        if v == "diff": plan["pos_replace"].append((db_pos[k], w))
        elif v == "grade": plan["grade_update"] += [("person_position_citations",) + u for u in upd]
    for k, r in db_pos.items():
        if k not in want_pos and k[0] not in shared: plan["pos_retract"].append(r)
    for k, g in want_gap.items():
        if not g.get("checked"):
            continue  # 缺 checkedOn 的 seed gap 由 write_generals_bios 規則處理，本腳本不動
        r = db_gap.get(k)
        if r is None:
            plan["gap_insert"].append(g)
        elif (r["note"], r["candidate_citations"] or [], str(r["checked_on"])[:10]) != (g["note"], g["cand"] or [], g["checked"]):
            plan["gap_replace"].append((r, g))
    for k, r in db_gap.items():
        if k not in want_gap and k[0] not in shared: plan["gap_retract"].append(r)

    bio_name = {p["bioId"]: p["key"] for _, d in batches for p in d["people"]}
    def who(rows, getbio):
        return sorted({bio_name.get(getbio(x), getbio(x)) for x in rows})
    summ = {k: len(v) for k, v in plan.items()}
    summ["people_touched"] = sorted(set(who(plan["par_insert"], lambda x: x["bio"]) + who(plan["par_replace"], lambda x: x[0]["bio_id"]) +
                                        who(plan["par_retract"], lambda x: x["bio_id"]) + who(plan["pos_insert"], lambda x: x["bio"]) +
                                        who(plan["pos_replace"], lambda x: x[0]["bio_id"]) + who(plan["pos_retract"], lambda x: x["bio_id"]) +
                                        who(plan["gap_insert"], lambda x: x["bio"]) + who(plan["gap_replace"], lambda x: x[0]["bio_id"]) +
                                        who(plan["gap_retract"], lambda x: x["bio_id"])))
    summ["scope_people"] = len(scope); summ["shared_bios_protected"] = len(shared)
    summ["sources_new"] = len(P["sources_new"]); summ["citations_dropped"] = len(P["cit_dropped"]); summ["skipped"] = len(skipped)

    # SQL
    q = ["BEGIN;"]; A = q.append; L = W.sql_lit
    for s in P["sources_new"].values():
        A("INSERT INTO sources (id,source_kind,title,publisher,authors,published_text,url,archive_url,catalog_id,license_code) VALUES (%s);" %
          ",".join(L(s[k]) for k in ("id", "kind", "title", "publisher", "authors", "published_text", "url", "archive_url", "catalog_id", "license_code")))
    def cit(table, fk, pid, c):
        A("INSERT INTO %s (%s,source_id,locator,quote,quote_lang,evidence_note,accessed_on,grade,date_precision,policy_version) VALUES (%s);" %
          (table, fk, ",".join(L(x) for x in (pid, c["source_id"], c["locator"], c["quote"], c["quote_lang"], c["evidence_note"],
                                              c["accessed_on"], c["grade"], c["date_precision"], c["policy_version"]))))
    def ins_par(g):
        pid = str(uuid.uuid4())
        A("INSERT INTO leader_bio_paragraphs (id,bio_id,ord,period,period_start_precision,period_end_precision,heading,body) VALUES (%s,%s,%s,%s,%s,%s,%s,%s);" %
          (L(pid), L(g["bio"]), g["ord"], L(g["period"]) + ("::daterange" if g["period"] else ""), L(g["sp"]), L(g["ep"]), W.sql_jsonb(g["heading"]), W.sql_jsonb(g["body"])))
        for c in g["cit"]: cit("leader_bio_paragraph_citations", "paragraph_id", pid, c)
        return pid
    def ins_pos(r):
        pid = str(uuid.uuid4())
        A("INSERT INTO person_positions (id,bio_id,seed_key,regime_id,organization,title,position_kind,period,start_precision,end_precision,note) VALUES (%s);" %
          ",".join([L(pid), L(r["bio"]), L(r["key"]), L(r["regime"]), W.sql_jsonb(r["org"]), W.sql_jsonb(r["title"]), L(r["kind"]),
                    L(r["period"]) + "::daterange", L(r["sp"]), L(r["ep"]), L(r["note"])]))
        for c in r["cit"]: cit("person_position_citations", "position_id", pid, c)
        return pid
    def retract(table, ctable, fk, rid, why):
        A("UPDATE %s SET retracted_at=now(), retraction_reason=%s WHERE %s=%s AND retracted_at IS NULL;" % (ctable, L(why), fk, L(rid)))
        A("UPDATE %s SET retracted_at=now(), retraction_reason=%s WHERE id=%s AND retracted_at IS NULL;" % (table, L(why), L(rid)))
    for r in plan["par_retract"]: retract("leader_bio_paragraphs", "leader_bio_paragraph_citations", "paragraph_id", r["id"], WHY_REMOVE)
    for r in plan["pos_retract"]: retract("person_positions", "person_position_citations", "position_id", r["id"], WHY_REMOVE)
    for old, new in plan["par_replace"]:
        retract("leader_bio_paragraphs", "leader_bio_paragraph_citations", "paragraph_id", old["id"], WHY_REPLACE)
        nid = ins_par(new); A("UPDATE leader_bio_paragraphs SET superseded_by=%s WHERE id=%s;" % (L(nid), L(old["id"])))
    for old, new in plan["pos_replace"]:
        retract("person_positions", "person_position_citations", "position_id", old["id"], WHY_REPLACE)
        nid = ins_pos(new); A("UPDATE person_positions SET superseded_by=%s WHERE id=%s;" % (L(nid), L(old["id"])))
    for g in plan["par_insert"]: ins_par(g)
    for r in plan["pos_insert"]: ins_pos(r)
    for tbl, cid, old, new in plan["grade_update"]:
        A("UPDATE %s SET grade=%s WHERE id=%s AND grade=%s;" % (tbl, L(new), L(cid), L(old)))
    for r in plan["gap_retract"]:
        A("UPDATE leader_bio_gaps SET retracted_at=now(), retraction_reason=%s WHERE id=%s AND retracted_at IS NULL;" % (L(WHY_GAP_REMOVE), L(r["id"])))
    def ins_gap(g):
        A("INSERT INTO leader_bio_gaps (bio_id,target,gap_kind,note,candidate_citations,checked_on) VALUES (%s,%s,%s,%s,%s::jsonb,%s);" %
          (L(g["bio"]), L(g["target"]), L(g["kind"]), L(g["note"]), L(g["cand"]), L(g["checked"])))
    for old, new in plan["gap_replace"]:
        A("UPDATE leader_bio_gaps SET retracted_at=now(), retraction_reason=%s WHERE id=%s AND retracted_at IS NULL;" % (L(WHY_GAP), L(old["id"])))
        ins_gap(new)
    for g in plan["gap_insert"]: ins_gap(g)
    A("COMMIT;")
    DEV.mkdir(parents=True, exist_ok=True)
    (DEV / "sync.sql").write_text("\n".join(q) + "\n", encoding="utf-8")
    detail = {"par_replace": [(bio_name.get(o["bio_id"]), o["ord"]) for o, _ in plan["par_replace"]],
              "par_retract": [(bio_name.get(r["bio_id"]), r["ord"]) for r in plan["par_retract"]],
              "par_insert": [(bio_name.get(r["bio"]), r["ord"]) for r in plan["par_insert"]],
              "pos_replace": [(bio_name.get(o["bio_id"]), o["seed_key"]) for o, _ in plan["pos_replace"]],
              "pos_retract": [(bio_name.get(r["bio_id"]), r["seed_key"]) for r in plan["pos_retract"]],
              "pos_insert": [(bio_name.get(r["bio"]), r["key"]) for r in plan["pos_insert"]],
              "gap_replace": [(bio_name.get(o["bio_id"]), o["target"]) for o, _ in plan["gap_replace"]],
              "gap_retract": [(bio_name.get(r["bio_id"]), r["target"]) for r in plan["gap_retract"]],
              "gap_insert": [(bio_name.get(r["bio"]), r["target"]) for r in plan["gap_insert"]],
              "grade_update": collections.Counter("%s→%s" % (x[2], x[3]) for x in plan["grade_update"]),
              "cit_dropped": P["cit_dropped"]}
    (DEV / ("sync-result.json" if a.send else "sync-dryrun.json")).write_text(json.dumps(
        {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "summary": summ, "detail": detail}, ensure_ascii=False, indent=1, default=list) + "\n")
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    if not a.send:
        print("（dry-run；未寫庫；SQL 見 .dev/dbwrite/sync.sql）"); return
    if not a.allow_write:
        raise SystemExit("需 --send --allow-write")
    r = subprocess.run(["docker", "exec", "-i", W.CONTAINER, "psql", "-U", W.DBUSER, "-d", W.DBNAME, "-v", "ON_ERROR_STOP=1", "-1", "-q"],
                       input="\n".join(q) + "\n", capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("寫入失敗（整筆交易回滾）：" + r.stderr[:800])
    print("已寫入。")


if __name__ == "__main__":
    main()
