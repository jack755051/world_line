#!/usr/bin/env python3
"""B3 full 已研究批次寫入 5442（Tai 2026-11-14 同意先寫 full/ 已研究好的人；續跑其餘待 Tai 決定）。

沿用 run100/write_b3_paragraphs.py 的 plan()／build_sql()（同一套規則：來源以網址對帳、未歸類網域拒寫、X 不入庫、
無引文列不寫、庫內已有的段落／經歷／角色略過）。寫前請先跑 verify.py（含逐字比對）與 dryrun_full.py。
預設只產 SQL 並以 ROLLBACK 演練；--send --allow-write 才在單一交易寫入。寫前 pg_dump，只寫 5442。
用法（repo 根目錄）：python3 -I data/seed/leaders/b3-trial/full/write_full.py batch001 batch002 batch003 [--send --allow-write]
"""
import importlib.util, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
spec = importlib.util.spec_from_file_location("w3", HERE.parent / "run100" / "write_b3_paragraphs.py")
w3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(w3)


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")]
    send, allow = "--send" in sys.argv, "--allow-write" in sys.argv
    opt = lambda k: next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == k and i + 1 < len(sys.argv)), None)
    base = HERE / opt("--dir") if opt("--dir") else HERE          # 例：--dir v3（批次在 full/v3/batchNNN）
    replace = set((opt("--replace") or "").split(",")) - {""}       # 例：--replace <bioId>：先撤回該人既有段落／經歷／角色／缺口，再寫新版（I5 不刪）
    names = [n for n in names if n not in (opt("--dir"), opt("--replace"))]
    if not names:
        raise SystemExit("請指定批次（例：batch001 batch002）")
    batches = [(n, json.loads((base / n / "research.json").read_text(encoding="utf-8"))) for n in names]
    overrides = json.load(open(w3.OVERRIDES)) if os.path.exists(w3.OVERRIDES) else {}
    st = w3.db_state(None)
    for k in ("paragraphs", "positions", "roles"):  # 要取代的人：視為庫內沒有，讓 plan 產出全部新列
        st["existing"][k] = {x for x in st["existing"][k] if x[0] not in replace}
    P = w3.plan(batches, st, overrides)
    if P["unclassified"] or P["bad"] or P["bio_missing"]:
        raise SystemExit("有未歸類網域、驗證不過或庫內無 bio：%s" % json.dumps({"unclassified": list(P["unclassified"]), "bad": P["bad"], "bio_missing": P["bio_missing"]}, ensure_ascii=False))
    P["par"] = [r for r in P["par"] if r["cit"]]; P["pos"] = [r for r in P["pos"] if r["cit"]]; P["role_ok"] = [r for r in P["role_ok"] if r.get("cit")]
    sql = w3.build_sql(P)
    lines = sql.split("\n"); assert lines[0] == "BEGIN;" and lines[-1] == "COMMIT;"
    if replace:
        why = "b3-v3-replace-2026-11-15：由 B3 full v3 規格版本取代（Tai 2026-11-15「好」）"
        L = w3.sql_lit
        pre = []
        for bio in sorted(replace):
            for t, ct, fk in (("leader_bio_paragraphs", "leader_bio_paragraph_citations", "paragraph_id"),
                              ("person_positions", "person_position_citations", "position_id"), ("person_roles", "person_role_citations", "role_id")):
                pre.append("UPDATE %s SET retracted_at=now(), retraction_reason=%s WHERE retracted_at IS NULL AND %s IN (SELECT id FROM %s WHERE bio_id=%s AND retracted_at IS NULL);" % (ct, L(why), fk, t, L(bio)))
                pre.append("UPDATE %s SET retracted_at=now(), retraction_reason=%s WHERE bio_id=%s AND retracted_at IS NULL;" % (t, L(why), L(bio)))
            pre.append("UPDATE leader_bio_gaps SET retracted_at=now(), retraction_reason=%s WHERE bio_id=%s AND retracted_at IS NULL AND resolved_at IS NULL;" % (L(why), L(bio)))
        lines = [lines[0]] + pre + lines[1:]
        sql = "\n".join(lines)
    dev = REPO / ".dev" / "dbwrite"; dev.mkdir(parents=True, exist_ok=True)
    (dev / "b3full-write.sql").write_text(sql + "\n", encoding="utf-8")
    per = {}
    for b, d in batches:
        for p in d["people"]:
            per[p["key"]] = {"bio": p.get("bioId"), "paragraphs": sum(1 for r in P["par"] if r["bio"] == p.get("bioId")),
                             "positions": sum(1 for r in P["pos"] if r["bio"] == p.get("bioId")), "roles": sum(1 for r in P["role_ok"] if r["bio"] == p.get("bioId")),
                             "gaps": sum(1 for g in P["gaps"] if g["bio"] == p.get("bioId"))}
    summ = {"people": P["people"], "paragraphs": len(P["par"]), "positions": len(P["pos"]), "roles": len(P["role_ok"]), "gaps": len(P["gaps"]),
            "sources_new": len(P["sources_new"]), "already": P["already"], "per_person": per}
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    run = lambda body: subprocess.run(["docker", "exec", "-i", w3.CONTAINER, "psql", "-U", w3.DBUSER, "-d", w3.DBNAME, "-v", "ON_ERROR_STOP=1", "-1", "-q"],
                                      input=body, capture_output=True, text=True)
    r = run("\n".join(lines[:-1] + ["ROLLBACK;"]) + "\n")
    if r.returncode:
        raise SystemExit("ROLLBACK 演練失敗：" + r.stderr[:800])
    print("ROLLBACK 演練通過。")
    if not send:
        print("（未寫庫；SQL 見 .dev/dbwrite/b3full-write.sql）"); return
    if not allow:
        raise SystemExit("需 --send --allow-write")
    r = run(sql + "\n")
    if r.returncode:
        raise SystemExit("寫入失敗（整筆交易回滾）：" + r.stderr[:800])
    (dev / "b3full-write-result.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1) + "\n")
    print("已寫入。")


if __name__ == "__main__":
    main()
